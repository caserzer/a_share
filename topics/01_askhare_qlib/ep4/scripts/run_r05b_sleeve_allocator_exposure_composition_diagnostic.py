#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_csv, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r05b_sleeve_allocator_exposure_composition_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
POLICIES = [
    "full_exposure_primary_baseline",
    "market_state_cash_allocator_v1",
    "market_state_cash_plus_basebreakout_secondary_v1",
]
SELECTABLE_POLICIES = ["market_state_cash_allocator_v1", "market_state_cash_plus_basebreakout_secondary_v1"]
SLEEVE_CANDIDATES = {
    "base_breakout_vcp_secondary_sleeve": "base_breakout_vcp_preflight",
    "low_vol_uptrend_diagnostic_sleeve": "low_vol_uptrend_preflight",
    "low_beta_low_vol_diagnostic_sleeve": "cross_sectional_low_beta_low_vol_preflight",
}
SLEEVE_ROLES = {
    "r04e_union_primary_sleeve": "primary",
    "base_breakout_vcp_secondary_sleeve": "conditional secondary",
    "low_vol_uptrend_diagnostic_sleeve": "diagnostic",
    "low_beta_low_vol_diagnostic_sleeve": "diagnostic",
    "cash_sleeve": "cash",
    "benchmark_reporting_sleeve": "benchmark",
}
FINAL_DECISION_CONTRACT = {
    "r05b_sleeve_allocator_passed_diagnostic_only": (False, "oos_roll_forward_retest_only"),
    "r05b_mostly_cash_illusion": (True, "ep5_escape_hatch_only"),
    "r05b_risk_on_full_exposure_failed": (True, "ep5_escape_hatch_only"),
    "r05b_allocator_not_viable_validation": (True, "ep5_escape_hatch_only"),
    "r05b_blocked_upstream_state_changed": (False, "rerun_upstream_or_refresh_requirement"),
    "r05b_blocked_validation_failed": (False, "fix_validation_failure_only"),
}


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: str | Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _read_csv(path: str | Path) -> pd.DataFrame:
    resolved = topic_path(path)
    return pd.read_csv(resolved) if resolved.exists() and resolved.stat().st_size else pd.DataFrame()


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_json(value: Any) -> str:
    return _hash_text(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str))


def _hash_file(path: str | Path) -> str:
    resolved = topic_path(path)
    digest = hashlib.sha256()
    with resolved.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_hashes(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        if path.exists() and path.is_file():
            out[relpath(path)] = _hash_file(path)
    return out


def _safe_div(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return np.nan
    return float(numerator) / float(denominator)


def _product_return(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").fillna(0.0)
    return float(np.prod(1.0 + clean.to_numpy(dtype=float)) - 1.0) if len(clean) else np.nan


def _quantile(values: pd.Series, q: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.quantile(q)) if len(clean) else np.nan


def _max_drawdown(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if len(clean) == 0:
        return np.nan
    equity = np.cumprod(1.0 + clean.to_numpy(dtype=float))
    running = np.maximum.accumulate(equity)
    drawdown = 1.0 - equity / running
    return float(np.nanmax(drawdown))


def _worst_20d(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if len(clean) < 20:
        return np.nan
    rolling = clean.rolling(20, min_periods=20).apply(lambda s: np.prod(1.0 + s) - 1.0, raw=True)
    return float(rolling.min())


def _monthly_returns(df: pd.DataFrame, return_col: str) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    work = df[["trade_date", return_col]].copy()
    work["month"] = pd.to_datetime(work["trade_date"]).dt.to_period("M").astype(str)
    return work.groupby("month")[return_col].apply(_product_return)


def _split_bounds(config: dict[str, Any]) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    split = config["split"]
    return {
        "train": (pd.Timestamp(split["train_start"]), pd.Timestamp(split["train_end"])),
        "validation": (pd.Timestamp(split["validation_start"]), pd.Timestamp(split["validation_end"])),
        "robustness": (pd.Timestamp(split["robustness_start"]), pd.Timestamp(split["robustness_end"])),
    }


def _split_for_date(value: Any, bounds: dict[str, tuple[pd.Timestamp, pd.Timestamp]]) -> str:
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return "out_of_scope"
    dt = pd.Timestamp(dt).normalize()
    for split, (start, end) in bounds.items():
        if start <= dt <= end:
            return split
    return "out_of_scope"


def _load_calendar(path: str | Path) -> pd.DatetimeIndex:
    resolved = topic_path(path)
    values = [line.strip() for line in resolved.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values).normalize()).sort_values()


def _output_calendar(config: dict[str, Any], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    bounds = _split_bounds(config)
    rows: list[dict[str, Any]] = []
    for idx, trade_date in enumerate(calendar):
        if idx == 0:
            continue
        split = _split_for_date(trade_date, bounds)
        if split == "out_of_scope":
            continue
        rows.append(
            {
                "trade_date": pd.Timestamp(trade_date).normalize(),
                "split": split,
                "state_signal_date": pd.Timestamp(calendar[idx - 1]).normalize(),
                "exposure_effective_date": pd.Timestamp(trade_date).normalize(),
            }
        )
    return pd.DataFrame(rows)


def _load_close_panel(config: dict[str, Any], instruments: list[str], start: pd.Timestamp, end: pd.Timestamp, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(topic_path(config["price_provider"]["price_source_path"])), region=REG_CN)
    data = D.features(
        sorted(set(instruments)),
        ["$close"],
        start_time=start.date().isoformat(),
        end_time=end.date().isoformat(),
        freq="day",
    )
    if data.empty:
        raise RuntimeError("qlib close provider returned empty data")
    out = data.rename(columns={"$close": "adjusted_close"}).reset_index()
    out = out.rename(columns={"instrument": "instrument_id", "datetime": "trade_date"})
    out["instrument_id"] = out["instrument_id"].astype(str).str.upper()
    out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.normalize()
    out["adjusted_close"] = pd.to_numeric(out["adjusted_close"], errors="coerce")
    cal_map = {pd.Timestamp(date).normalize(): idx for idx, date in enumerate(calendar)}
    out["calendar_index"] = out["trade_date"].map(cal_map)
    out = out[out["calendar_index"].notna()].copy()
    out["calendar_index"] = out["calendar_index"].astype(int)
    out = out.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)
    out["prior_adjusted_close"] = out.groupby("instrument_id", sort=False)["adjusted_close"].shift(1)
    out["daily_simple_return"] = out["adjusted_close"] / out["prior_adjusted_close"] - 1.0
    return out


def _upstream_state(config: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    reasons: list[str] = []
    r04e_validation = _read_json(config["upstream_r04e"]["validation"])
    r04e_final = _read_csv(config["upstream_r04e"]["final_decision"])
    r05_validation = _read_json(config["upstream_r05_preflight"]["validation"])
    r05_final = _read_csv(config["upstream_r05_preflight"]["final_decision"])
    r05a_status = _read_json(config["upstream_r05a"]["status"])
    formula = _read_csv(config["upstream_r05_preflight"]["candidate_formula_frozen"])
    r04e_final_decision = "" if r04e_final.empty else str(r04e_final.iloc[0].get("final_decision", ""))
    r05_final_decision = "" if r05_final.empty else str(r05_final.iloc[0].get("final_decision", ""))
    r05_candidate_pass_count = np.nan if r05_final.empty else pd.to_numeric(r05_final.iloc[0].get("candidate_pass_count"), errors="coerce")
    if r04e_validation.get("validation_status") != "passed":
        reasons.append("r04e_validation_not_passed")
    if r04e_final_decision != "r04e_union_not_viable_validation":
        reasons.append("r04e_final_decision_changed")
    if r05_validation.get("validation_status") != "passed":
        reasons.append("r05_preflight_validation_not_passed")
    if r05_final_decision != "r05_preflight_stop_no_absolute_floor":
        reasons.append("r05_preflight_final_decision_changed")
    if not np.isfinite(r05_candidate_pass_count) or int(r05_candidate_pass_count) != 0:
        reasons.append("r05_preflight_candidate_pass_count_not_zero")
    if formula.empty or not {"candidate_id", "round_trip_cost_bp"}.issubset(set(formula.columns)):
        reasons.append("r05_preflight_candidate_formula_missing_cost")
    if r05a_status.get("status") != "abandoned_preflight_blocked":
        reasons.append("r05a_status_not_abandoned_preflight_blocked")
    if r05a_status.get("active_implementation_allowed") is not False:
        reasons.append("r05a_active_implementation_allowed_not_false")
    if r05a_status.get("allowed_next_requirement") != "sleeve_allocator_direction_requirement":
        reasons.append("r05a_allowed_next_requirement_changed")
    return (
        {
            "r04e_validation_status": r04e_validation.get("validation_status"),
            "r04e_final_decision": r04e_final_decision,
            "r05_preflight_validation_status": r05_validation.get("validation_status"),
            "r05_preflight_final_decision": r05_final_decision,
            "r05_preflight_candidate_pass_count": None if not np.isfinite(r05_candidate_pass_count) else int(r05_candidate_pass_count),
            "r05a_status": r05a_status.get("status"),
            "r05a_active_implementation_allowed": r05a_status.get("active_implementation_allowed"),
            "r05a_allowed_next_requirement": r05a_status.get("allowed_next_requirement"),
        },
        reasons,
    )


def _market_state_panel(config: dict[str, Any], calendar_frame: pd.DataFrame, close: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    index_id = config["price_provider"]["index_instrument"].upper()
    idx = close.loc[close["instrument_id"].eq(index_id)].copy().sort_values("trade_date")
    if idx.empty:
        raise RuntimeError("missing SH000300 close series")
    idx["index_close"] = idx["adjusted_close"]
    idx["index_ma20"] = idx["index_close"].rolling(20, min_periods=20).mean()
    idx["index_ma60"] = idx["index_close"].rolling(60, min_periods=60).mean()
    idx["index_ret20"] = idx["index_close"] / idx["index_close"].shift(20) - 1.0
    idx["index_one_day_return"] = idx["index_close"] / idx["index_close"].shift(1) - 1.0
    idx["index_realized_vol20"] = idx["index_one_day_return"].rolling(20, min_periods=20).std(ddof=0)
    idx["index_drawdown60"] = idx["index_close"] / idx["index_close"].rolling(60, min_periods=60).max() - 1.0
    features = idx[
        [
            "trade_date",
            "index_close",
            "index_ma20",
            "index_ma60",
            "index_ret20",
            "index_realized_vol20",
            "index_drawdown60",
        ]
    ].rename(columns={"trade_date": "state_signal_date"})
    panel = calendar_frame.merge(features, on="state_signal_date", how="left")
    required_features = ["index_close", "index_ma20", "index_ma60", "index_ret20", "index_realized_vol20", "index_drawdown60"]
    if panel[required_features].isna().any().any():
        missing = panel.loc[panel[required_features].isna().any(axis=1), ["trade_date", "state_signal_date"]].head(5)
        raise RuntimeError(f"missing market-state features inside output rows: {missing.to_dict(orient='records')}")
    bounds = _split_bounds(config)
    train_feature = features.loc[
        (features["state_signal_date"] >= bounds["train"][0])
        & (features["state_signal_date"] <= bounds["train"][1])
        & features[required_features].notna().all(axis=1)
    ]
    threshold = float(train_feature["index_realized_vol20"].quantile(float(config["market_state"]["vol20_high_quantile"])))
    drawdown_threshold = float(config["market_state"]["drawdown60_hard_threshold"])
    trend_positive = (panel["index_close"] > panel["index_ma60"]) & (panel["index_ret20"] > 0)
    trend_negative = (panel["index_close"] < panel["index_ma60"]) | (panel["index_ret20"] < 0)
    panel["market_state"] = np.select(
        [
            panel["index_drawdown60"] <= drawdown_threshold,
            trend_negative & (panel["index_realized_vol20"] >= threshold),
            trend_positive & (panel["index_realized_vol20"] < threshold),
        ],
        ["risk_off", "risk_off", "risk_on"],
        default="risk_neutral",
    )
    classifier_id = config["market_state"]["classifier_id"]
    panel["classifier_id"] = classifier_id
    classifier = pd.DataFrame(
        [
            {
                "classifier_id": classifier_id,
                "fit_split": "train",
                "index_instrument": index_id,
                "feature_set_json": json.dumps(required_features, separators=(",", ":"), ensure_ascii=True),
                "thresholds_json": json.dumps(
                    {
                        "vol20_high_threshold": threshold,
                        "drawdown60_hard_threshold": drawdown_threshold,
                        "vol20_high_quantile": float(config["market_state"]["vol20_high_quantile"]),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "state_rule_text": "drawdown60<=-10% => risk_off; trend_negative and vol20>=train_q70 => risk_off; trend_positive and vol20<train_q70 => risk_on; else risk_neutral",
                "state_rule_hash": _hash_text("r05b_sh000300_train_q70_drawdown10_v1"),
                "state_count": int(panel["market_state"].nunique()),
                "signal_timing": "D close",
                "execution_timing": "next tradable open after D",
                "active_flag": True,
            }
        ]
    )
    return panel[
        [
            "trade_date",
            "split",
            "state_signal_date",
            "exposure_effective_date",
            "market_state",
            "index_close",
            "index_ma20",
            "index_ma60",
            "index_ret20",
            "index_realized_vol20",
            "index_drawdown60",
            "classifier_id",
        ]
    ], classifier


def _primary_sleeve(config: dict[str, Any], calendar_frame: pd.DataFrame) -> pd.DataFrame:
    source = topic_path(config["upstream_r04e"]["portfolio_daily_return_panel"])
    daily = pd.read_parquet(source)
    required = {"split", "trade_date", "portfolio_daily_net_return", "active_count", "gross_exposure", "portfolio_id", "policy_id"}
    missing = required - set(daily.columns)
    if missing:
        raise RuntimeError(f"R04e primary panel missing columns: {sorted(missing)}")
    keep = (
        daily["portfolio_id"].astype(str).eq(config["upstream_r04e"]["primary_portfolio_id"])
        & daily["policy_id"].astype(str).eq(config["upstream_r04e"]["primary_policy_id"])
    )
    primary = daily.loc[keep].copy()
    primary["trade_date"] = pd.to_datetime(primary["trade_date"]).dt.normalize()
    primary = calendar_frame[["trade_date", "split"]].merge(primary, on=["trade_date", "split"], how="left")
    if primary["portfolio_daily_net_return"].isna().any():
        raise RuntimeError("R04e primary path missing output trade dates")
    primary["sleeve_id"] = "r04e_union_primary_sleeve"
    primary["sleeve_role"] = "primary"
    primary["sleeve_daily_return"] = pd.to_numeric(primary["portfolio_daily_net_return"], errors="coerce").fillna(0.0)
    primary["sleeve_active_count"] = pd.to_numeric(primary["active_count"], errors="coerce").fillna(0).astype(int)
    primary["sleeve_gross_exposure_before_allocator"] = pd.to_numeric(primary["gross_exposure"], errors="coerce")
    if not primary["sleeve_gross_exposure_before_allocator"].between(0, 1).all():
        raise RuntimeError("R04e primary gross_exposure outside [0,1]")
    zero = primary["sleeve_active_count"].eq(0)
    if (primary.loc[zero, "sleeve_daily_return"].abs() > 1e-12).any() or (primary.loc[zero, "sleeve_gross_exposure_before_allocator"].abs() > 1e-12).any():
        raise RuntimeError("R04e active_count==0 semantics inconsistent with return/gross exposure")
    primary["source_artifact"] = relpath(source)
    primary["source_candidate_id"] = ""
    primary["source_policy_id"] = config["upstream_r04e"]["primary_policy_id"]
    primary["source_portfolio_id"] = config["upstream_r04e"]["primary_portfolio_id"]
    primary["position_replay_method"] = "r04e_frozen_portfolio_daily_path"
    return primary[
        [
            "trade_date",
            "split",
            "sleeve_id",
            "sleeve_role",
            "sleeve_daily_return",
            "sleeve_active_count",
            "sleeve_gross_exposure_before_allocator",
            "source_artifact",
            "source_candidate_id",
            "source_policy_id",
            "source_portfolio_id",
            "position_replay_method",
        ]
    ]


def _replay_preflight_sleeves(
    config: dict[str, Any],
    calendar_frame: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    close: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = pd.read_parquet(topic_path(config["upstream_r05_preflight"]["candidate_event_panel"]))
    forward = pd.read_parquet(topic_path(config["upstream_r05_preflight"]["forward_return_panel"]))
    formulas = _read_csv(config["upstream_r05_preflight"]["candidate_formula_frozen"])
    needed = {"candidate_id", "event_key", "instrument_id", "decision_date", "actual_entry_execution_date"}
    if not needed.issubset(events.columns):
        raise RuntimeError(f"preflight event panel missing columns: {sorted(needed - set(events.columns))}")
    if not {"candidate_id", "event_key", "actual_exit_date", "actual_entry_price", "actual_exit_price", "path_complete_flag"}.issubset(forward.columns):
        raise RuntimeError("preflight forward panel missing replay columns")
    cost_by_candidate = {
        str(row.candidate_id): float(row.round_trip_cost_bp)
        for row in formulas.itertuples(index=False)
        if pd.notna(row.candidate_id)
    }
    merged = events.merge(
        forward[
            [
                "candidate_id",
                "event_key",
                "actual_entry_price",
                "actual_exit_date",
                "actual_exit_price",
                "path_complete_flag",
                "exit_executable_flag",
            ]
        ],
        on=["candidate_id", "event_key"],
        how="left",
    )
    for col in ["decision_date", "actual_entry_execution_date", "actual_exit_date"]:
        merged[col] = pd.to_datetime(merged[col], errors="coerce").dt.normalize()
    merged["instrument_id"] = merged["instrument_id"].astype(str).str.upper()
    bool_cols = ["kept_event_flag", "entry_executable_flag", "path_complete_flag"]
    for col in bool_cols:
        merged[col] = merged[col].astype(bool)
    close_lookup = close.set_index(["instrument_id", "trade_date"])[["adjusted_close", "prior_adjusted_close"]]
    output_dates = set(pd.to_datetime(calendar_frame["trade_date"]).dt.normalize())
    split_by_date = dict(zip(calendar_frame["trade_date"], calendar_frame["split"], strict=False))
    cal_pos = {pd.Timestamp(date).normalize(): idx for idx, date in enumerate(calendar)}
    rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    complete_min = float(config["thresholds"]["preflight_replay_complete_share_min"])
    for sleeve_id, candidate_id in SLEEVE_CANDIDATES.items():
        part = merged.loc[merged["candidate_id"].astype(str).eq(candidate_id)].copy()
        complete = part.loc[
            part["kept_event_flag"] & part["entry_executable_flag"] & part["path_complete_flag"]
        ].copy()
        valid_event_keys: set[str] = set()
        lookahead_unsafe_event_keys: set[str] = set()
        replay_invalid_event_keys: set[str] = set()
        for event in complete.itertuples(index=False):
            event_key = str(event.event_key)
            entry = pd.Timestamp(event.actual_entry_execution_date).normalize()
            exit_date = pd.Timestamp(event.actual_exit_date).normalize()
            decision = pd.Timestamp(event.decision_date).normalize()
            start_pos = cal_pos.get(entry)
            end_pos = cal_pos.get(exit_date)
            if start_pos is None or end_pos is None:
                replay_invalid_event_keys.add(event_key)
                continue
            round_trip_cost_bp = cost_by_candidate[candidate_id]
            entry_cost = round_trip_cost_bp / 20000.0
            exit_cost = round_trip_cost_bp / 20000.0
            event_rows: list[dict[str, Any]] = []
            event_valid = True
            for pos in range(start_pos, end_pos + 1):
                t = pd.Timestamp(calendar[pos]).normalize()
                if t not in output_dates:
                    continue
                prev_date = pd.Timestamp(calendar[pos - 1]).normalize() if pos > 0 else pd.NaT
                if pd.isna(prev_date) or decision > prev_date:
                    lookahead_unsafe_event_keys.add(event_key)
                    event_valid = False
                    break
                key = (event.instrument_id, t)
                if key not in close_lookup.index:
                    replay_invalid_event_keys.add(event_key)
                    event_valid = False
                    break
                close_row = close_lookup.loc[key]
                current_close = float(close_row["adjusted_close"])
                prior_close = float(close_row["prior_adjusted_close"])
                if t == entry and t == exit_date:
                    daily_return = float(event.actual_exit_price) / float(event.actual_entry_price) - 1.0 - entry_cost - exit_cost
                elif t == entry:
                    daily_return = current_close / float(event.actual_entry_price) - 1.0 - entry_cost
                elif t == exit_date:
                    daily_return = float(event.actual_exit_price) / prior_close - 1.0 - exit_cost
                else:
                    daily_return = current_close / prior_close - 1.0
                if not np.isfinite(daily_return):
                    replay_invalid_event_keys.add(event_key)
                    event_valid = False
                    break
                event_rows.append(
                    {
                        "trade_date": t,
                        "split": split_by_date[t],
                        "sleeve_id": sleeve_id,
                        "sleeve_role": SLEEVE_ROLES[sleeve_id],
                        "position_daily_net_return": daily_return,
                    }
                )
            if event_valid:
                valid_event_keys.add(event_key)
                rows.extend(event_rows)
        for split in SPLITS:
            raw_split = part.loc[part["split"].astype(str).eq(split)]
            complete_split = complete.loc[complete["split"].astype(str).eq(split)]
            kept = int(raw_split["kept_event_flag"].sum()) if len(raw_split) else 0
            valid_split = complete_split.loc[complete_split["event_key"].astype(str).isin(valid_event_keys)]
            lookahead_unsafe_split = complete_split.loc[complete_split["event_key"].astype(str).isin(lookahead_unsafe_event_keys)]
            complete_count = int(len(valid_split))
            lookahead_safe = int(complete_count)
            share = _safe_div(complete_count, kept) if kept else 0.0
            is_diagnostic = SLEEVE_ROLES[sleeve_id] == "diagnostic"
            replay_status = "pass" if share >= complete_min else ("diagnostic_decomposition_blocked" if is_diagnostic else "fail")
            audit_rows.append(
                {
                    "sleeve_id": sleeve_id,
                    "candidate_id": candidate_id,
                    "split": split,
                    "source_event_count": int(len(raw_split)),
                    "kept_event_count": kept,
                    "entry_executable_event_count": int((raw_split["kept_event_flag"] & raw_split["entry_executable_flag"]).sum()) if len(raw_split) else 0,
                    "complete_replay_event_count": complete_count,
                    "complete_replay_event_share": share,
                    "complete_share_min": complete_min,
                    "lookahead_safe_event_count": lookahead_safe,
                    "lookahead_censored_event_count": int(len(lookahead_unsafe_split)),
                    "lookahead_audit_status": "pass" if len(lookahead_unsafe_split) == 0 else "fail",
                    "replay_censor_status": replay_status,
                    "blocking_reason": "" if replay_status == "pass" else "preflight_replay_complete_share_below_min",
                }
            )
    position_daily = pd.DataFrame(rows)
    base = calendar_frame[["trade_date", "split"]].copy()
    sleeve_frames: list[pd.DataFrame] = []
    for sleeve_id, candidate_id in SLEEVE_CANDIDATES.items():
        if position_daily.empty:
            agg = pd.DataFrame(columns=["trade_date", "split", "sleeve_daily_return", "sleeve_active_count"])
        else:
            agg = (
                position_daily.loc[position_daily["sleeve_id"].eq(sleeve_id)]
                .groupby(["trade_date", "split"], as_index=False)
                .agg(sleeve_daily_return=("position_daily_net_return", "mean"), sleeve_active_count=("position_daily_net_return", "size"))
            )
        daily = base.merge(agg, on=["trade_date", "split"], how="left")
        daily["sleeve_id"] = sleeve_id
        daily["sleeve_role"] = SLEEVE_ROLES[sleeve_id]
        daily["sleeve_daily_return"] = pd.to_numeric(daily["sleeve_daily_return"], errors="coerce").fillna(0.0)
        daily["sleeve_active_count"] = pd.to_numeric(daily["sleeve_active_count"], errors="coerce").fillna(0).astype(int)
        daily["sleeve_gross_exposure_before_allocator"] = np.where(daily["sleeve_active_count"] > 0, 1.0, 0.0)
        daily["source_artifact"] = relpath(topic_path(config["upstream_r05_preflight"]["candidate_event_panel"]))
        daily["source_candidate_id"] = candidate_id
        daily["source_policy_id"] = ""
        daily["source_portfolio_id"] = ""
        daily["position_replay_method"] = "r05_preflight_frozen_event_qlib_pit_daily_replay"
        sleeve_frames.append(daily)
    return pd.concat(sleeve_frames, ignore_index=True), pd.DataFrame(audit_rows)


def _cash_and_benchmark_sleeves(config: dict[str, Any], calendar_frame: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    index_id = config["price_provider"]["index_instrument"].upper()
    bench = close.loc[close["instrument_id"].eq(index_id), ["trade_date", "daily_simple_return"]].rename(columns={"daily_simple_return": "benchmark_daily_return"})
    bench = calendar_frame[["trade_date", "split"]].merge(bench, on="trade_date", how="left")
    if bench["benchmark_daily_return"].isna().any():
        raise RuntimeError("missing benchmark close-to-close return inside output rows")
    frames: list[pd.DataFrame] = []
    for sleeve_id, role, ret_col in [
        ("cash_sleeve", "cash", None),
        ("benchmark_reporting_sleeve", "benchmark", "benchmark_daily_return"),
    ]:
        daily = calendar_frame[["trade_date", "split"]].copy()
        daily["sleeve_id"] = sleeve_id
        daily["sleeve_role"] = role
        daily["sleeve_daily_return"] = 0.0 if ret_col is None else bench[ret_col].to_numpy(float)
        daily["sleeve_active_count"] = 0
        daily["sleeve_gross_exposure_before_allocator"] = 0.0
        daily["source_artifact"] = "zero_return_cash" if role == "cash" else config["price_provider"]["index_feature_path"]
        daily["source_candidate_id"] = ""
        daily["source_policy_id"] = ""
        daily["source_portfolio_id"] = ""
        daily["position_replay_method"] = "zero_return_cash" if role == "cash" else "sh000300_close_to_close_adjusted_return"
        frames.append(daily)
    return pd.concat(frames, ignore_index=True)


def _sleeve_registry(config: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "sleeve_id": "r04e_union_primary_sleeve",
            "sleeve_role": "primary",
            "source_artifact": config["upstream_r04e"]["portfolio_daily_return_panel"],
            "source_filter": "portfolio_id=active_equal_weight_uncapped;policy_id=hold_120d__no_exit__none",
            "allocation_status": "allocation eligible",
            "max_weight": 1.0,
            "formula_hash": _hash_text("r04e_primary_daily_return_active_count_gross_exposure"),
            "blocking_reason": "",
        },
        {
            "sleeve_id": "base_breakout_vcp_secondary_sleeve",
            "sleeve_role": "conditional secondary",
            "source_artifact": config["upstream_r05_preflight"]["candidate_event_panel"],
            "source_filter": "candidate_id=base_breakout_vcp_preflight;kept=true;entry_executable=true;path_complete=true",
            "allocation_status": "capped secondary only",
            "max_weight": 0.20,
            "formula_hash": _hash_text("base_breakout_preflight_daily_replay_weight_cap_20"),
            "blocking_reason": "",
        },
        {
            "sleeve_id": "low_vol_uptrend_diagnostic_sleeve",
            "sleeve_role": "diagnostic",
            "source_artifact": config["upstream_r05_preflight"]["candidate_event_panel"],
            "source_filter": "candidate_id=low_vol_uptrend_preflight;decomposition_only",
            "allocation_status": "no allocation",
            "max_weight": 0.0,
            "formula_hash": _hash_text("low_vol_uptrend_preflight_decomposition_only"),
            "blocking_reason": "",
        },
        {
            "sleeve_id": "low_beta_low_vol_diagnostic_sleeve",
            "sleeve_role": "diagnostic",
            "source_artifact": config["upstream_r05_preflight"]["candidate_event_panel"],
            "source_filter": "candidate_id=cross_sectional_low_beta_low_vol_preflight;decomposition_only",
            "allocation_status": "no allocation",
            "max_weight": 0.0,
            "formula_hash": _hash_text("low_beta_low_vol_preflight_decomposition_only"),
            "blocking_reason": "",
        },
        {
            "sleeve_id": "cash_sleeve",
            "sleeve_role": "cash",
            "source_artifact": "zero_return_cash",
            "source_filter": "return=0;gross_exposure=0",
            "allocation_status": "allocation eligible",
            "max_weight": 1.0,
            "formula_hash": _hash_text("cash_zero_return_zero_gross"),
            "blocking_reason": "",
        },
        {
            "sleeve_id": "benchmark_reporting_sleeve",
            "sleeve_role": "benchmark",
            "source_artifact": config["price_provider"]["index_feature_path"],
            "source_filter": "SH000300 adjusted close-to-close reporting baseline",
            "allocation_status": "no allocation",
            "max_weight": 0.0,
            "formula_hash": _hash_text("sh000300_close_to_close_adjusted_reporting"),
            "blocking_reason": "",
        },
    ]
    return pd.DataFrame(rows)


def _policy_registry() -> pd.DataFrame:
    rows = [
        {
            "allocator_policy_id": "full_exposure_primary_baseline",
            "policy_role": "baseline_reference",
            "allowed_sleeve_ids_json": json.dumps(["r04e_union_primary_sleeve"], separators=(",", ":")),
            "state_weight_rule_text": "primary=1.0 for all states; cash=0; secondary=0",
            "secondary_activation_rule_text": "not_applicable",
            "gross_exposure_formula_text": "primary_weight * primary_gross_before_allocator",
            "cash_excluded_from_gross_exposure_flag": True,
            "is_selectable": False,
            "formula_hash": _hash_text("full_exposure_primary_baseline_v1"),
            "blocking_reason": "baseline_reference_only",
        },
        {
            "allocator_policy_id": "market_state_cash_allocator_v1",
            "policy_role": "allocator_candidate",
            "allowed_sleeve_ids_json": json.dumps(["r04e_union_primary_sleeve", "cash_sleeve"], separators=(",", ":")),
            "state_weight_rule_text": "risk_on primary=1; risk_neutral primary=0.5,cash=0.5; risk_off cash=1",
            "secondary_activation_rule_text": "not_applicable",
            "gross_exposure_formula_text": "primary_weight * primary_gross_before_allocator",
            "cash_excluded_from_gross_exposure_flag": True,
            "is_selectable": True,
            "formula_hash": _hash_text("market_state_cash_allocator_v1"),
            "blocking_reason": "",
        },
        {
            "allocator_policy_id": "market_state_cash_plus_basebreakout_secondary_v1",
            "policy_role": "allocator_candidate_with_secondary",
            "allowed_sleeve_ids_json": json.dumps(["r04e_union_primary_sleeve", "base_breakout_vcp_secondary_sleeve", "cash_sleeve"], separators=(",", ":")),
            "state_weight_rule_text": "start with market_state_cash_allocator_v1",
            "secondary_activation_rule_text": "risk_on and primary_active_count<20 and secondary_active_count>0 => secondary=0.20, primary reduced by 0.20",
            "gross_exposure_formula_text": "primary_weight*primary_gross_before_allocator + secondary_weight*secondary_gross_before_allocator",
            "cash_excluded_from_gross_exposure_flag": True,
            "is_selectable": True,
            "formula_hash": _hash_text("market_state_cash_plus_basebreakout_secondary_v1"),
            "blocking_reason": "",
        },
    ]
    return pd.DataFrame(rows)


def _weights(policy: str, market_state: str, primary_count: int, secondary_count: int) -> tuple[float, float, float]:
    if policy == "full_exposure_primary_baseline":
        return 1.0, 0.0, 0.0
    if market_state == "risk_on":
        primary, cash = 1.0, 0.0
    elif market_state == "risk_neutral":
        primary, cash = 0.5, 0.5
    else:
        primary, cash = 0.0, 1.0
    secondary = 0.0
    if policy == "market_state_cash_plus_basebreakout_secondary_v1":
        if market_state == "risk_on" and primary_count < 20 and secondary_count > 0:
            before = primary
            if before < 0.20:
                raise RuntimeError("secondary branch underfunded primary weight")
            secondary = 0.20
            primary = max(0.0, before - 0.20)
    return primary, secondary, cash


def _allocator_daily(
    config: dict[str, Any],
    calendar_frame: pd.DataFrame,
    market_state: pd.DataFrame,
    sleeves: pd.DataFrame,
    close: pd.DataFrame,
) -> pd.DataFrame:
    def sleeve(sleeve_id: str, prefix: str) -> pd.DataFrame:
        part = sleeves.loc[sleeves["sleeve_id"].eq(sleeve_id), ["trade_date", "sleeve_daily_return", "sleeve_active_count", "sleeve_gross_exposure_before_allocator"]].copy()
        return part.rename(
            columns={
                "sleeve_daily_return": f"{prefix}_daily_return",
                "sleeve_active_count": f"{prefix}_active_count",
                "sleeve_gross_exposure_before_allocator": f"{prefix}_gross_exposure_before_allocator",
            }
        )

    base = calendar_frame[["trade_date", "split"]].merge(
        market_state[["trade_date", "state_signal_date", "exposure_effective_date", "market_state"]],
        on="trade_date",
        how="left",
    )
    base = base.merge(sleeve("r04e_union_primary_sleeve", "primary"), on="trade_date", how="left")
    base = base.merge(sleeve("base_breakout_vcp_secondary_sleeve", "secondary"), on="trade_date", how="left")
    bench = close.loc[close["instrument_id"].eq(config["price_provider"]["index_instrument"].upper()), ["trade_date", "daily_simple_return"]].rename(columns={"daily_simple_return": "benchmark_daily_return"})
    base = base.merge(bench, on="trade_date", how="left")
    rows: list[dict[str, Any]] = []
    for row in base.itertuples(index=False):
        primary_count = int(row.primary_active_count)
        secondary_count = int(row.secondary_active_count)
        for policy in POLICIES:
            primary_w, secondary_w, cash_w = _weights(policy, row.market_state, primary_count, secondary_count)
            primary_gross = primary_w * float(row.primary_gross_exposure_before_allocator)
            secondary_gross = secondary_w * float(row.secondary_gross_exposure_before_allocator)
            total_gross = primary_gross + secondary_gross
            allocator_return = primary_w * float(row.primary_daily_return) + secondary_w * float(row.secondary_daily_return)
            rows.append(
                {
                    "trade_date": row.trade_date,
                    "split": row.split,
                    "allocator_policy_id": policy,
                    "state_signal_date": row.state_signal_date,
                    "exposure_effective_date": row.exposure_effective_date,
                    "market_state": row.market_state,
                    "r04e_union_primary_sleeve_active_count": primary_count,
                    "base_breakout_vcp_secondary_sleeve_active_count": secondary_count,
                    "r04e_union_primary_sleeve_gross_exposure_before_allocator": float(row.primary_gross_exposure_before_allocator),
                    "base_breakout_vcp_secondary_sleeve_gross_exposure_before_allocator": float(row.secondary_gross_exposure_before_allocator),
                    "r04e_union_primary_effective_gross_exposure": primary_gross,
                    "base_breakout_vcp_secondary_effective_gross_exposure": secondary_gross,
                    "r04e_union_primary_sleeve_weight": primary_w,
                    "base_breakout_vcp_secondary_sleeve_weight": secondary_w,
                    "cash_sleeve_weight": cash_w,
                    "total_gross_exposure": total_gross,
                    "allocator_daily_return": allocator_return,
                    "full_exposure_primary_daily_return": float(row.primary_daily_return),
                    "benchmark_daily_return": float(row.benchmark_daily_return),
                    "cash_only_flag": bool(total_gross == 0),
                }
            )
    return pd.DataFrame(rows)


def _right_tail(split: str, allocator_p90: float, full_p90: float, config: dict[str, Any]) -> dict[str, Any]:
    suffix = "validation" if split == "validation" else "robustness"
    retention_min = float(config["thresholds"][f"right_tail_retention_min_{suffix}"])
    floor_min = float(config["thresholds"][f"absolute_p90_floor_min_{suffix}"])
    if np.isfinite(full_p90) and full_p90 > 0:
        retention = _safe_div(allocator_p90, full_p90)
        status = "right_tail_pass" if np.isfinite(retention) and retention >= retention_min else "right_tail_fail"
        mode = "retention_vs_full_exposure"
    else:
        retention = np.nan
        status = "right_tail_pass" if np.isfinite(allocator_p90) and allocator_p90 >= floor_min else "right_tail_fail"
        mode = "absolute_p90_floor"
    return {
        "right_tail_gate_mode": mode,
        "right_tail_gate_status": status,
        "right_tail_retention_vs_full_exposure": retention,
        "absolute_p90_floor_min": floor_min,
    }


def _metric_row(part: pd.DataFrame, return_col: str, gross_col: str | None = None, cash_col: str | None = None) -> dict[str, float]:
    monthly = _monthly_returns(part, return_col)
    return {
        "period_return": _product_return(part[return_col]),
        "daily_mean": float(pd.to_numeric(part[return_col], errors="coerce").mean()) if len(part) else np.nan,
        "monthly_p10": _quantile(monthly, 0.10),
        "monthly_p90": _quantile(monthly, 0.90),
        "max_drawdown": _max_drawdown(part[return_col]),
        "worst_20d_return": _worst_20d(part[return_col]),
        "average_gross_exposure": float(pd.to_numeric(part[gross_col], errors="coerce").mean()) if gross_col else np.nan,
        "cash_only_day_share": float(part[cash_col].astype(bool).mean()) if cash_col else np.nan,
    }


def _build_reports(config: dict[str, Any], sleeves: pd.DataFrame, allocator: pd.DataFrame, market_state: pd.DataFrame, replay_audit: pd.DataFrame) -> dict[str, pd.DataFrame]:
    thresholds = config["thresholds"]
    full_metrics_by_split: dict[str, dict[str, float]] = {}
    policy_metrics: dict[tuple[str, str], dict[str, float]] = {}
    right_tail_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for split in SPLITS:
        full_part = allocator.loc[
            allocator["allocator_policy_id"].eq("full_exposure_primary_baseline") & allocator["split"].eq(split)
        ].copy()
        full_metrics = _metric_row(full_part, "full_exposure_primary_daily_return", "total_gross_exposure", "cash_only_flag")
        full_metrics_by_split[split] = full_metrics
    summary_rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        for split in SPLITS:
            part = allocator.loc[allocator["allocator_policy_id"].eq(policy) & allocator["split"].eq(split)].copy()
            metrics = _metric_row(part, "allocator_daily_return", "total_gross_exposure", "cash_only_flag")
            policy_metrics[(policy, split)] = metrics
            tail_split = "validation" if split != "robustness" else "robustness"
            tail = _right_tail(tail_split, metrics["monthly_p90"], full_metrics_by_split[split]["monthly_p90"], config)
            right_tail_by_key[(policy, split)] = tail
            summary_rows.append(
                {
                    "allocator_policy_id": policy,
                    "split": split,
                    "period_return": metrics["period_return"],
                    "daily_mean": metrics["daily_mean"],
                    "monthly_p10": metrics["monthly_p10"],
                    "monthly_p90": metrics["monthly_p90"],
                    "right_tail_gate_mode": tail["right_tail_gate_mode"],
                    "right_tail_gate_status": tail["right_tail_gate_status"],
                    "absolute_p90_floor_min": tail["absolute_p90_floor_min"],
                    "max_drawdown": metrics["max_drawdown"],
                    "worst_20d_return": metrics["worst_20d_return"],
                    "average_gross_exposure": metrics["average_gross_exposure"],
                    "cash_only_day_share": metrics["cash_only_day_share"],
                    "right_tail_retention_vs_full_exposure": tail["right_tail_retention_vs_full_exposure"],
                    "secondary_activation_status": "",
                    "robustness_secondary_activation_status": "",
                    "validation_gate_status": "",
                    "robustness_readonly_status": "",
                    "blocking_reason": "",
                }
            )
    policy_summary = pd.DataFrame(summary_rows)

    monthly_rows: list[dict[str, Any]] = []
    for (policy, month, split), part in allocator.assign(month=allocator["trade_date"].dt.to_period("M").astype(str)).groupby(
        ["allocator_policy_id", "month", "split"], sort=False
    ):
        full_part = part
        monthly_rows.append(
            {
                "allocator_policy_id": policy,
                "month": month,
                "split": split,
                "monthly_return": _product_return(part["allocator_daily_return"]),
                "full_exposure_primary_monthly_return": _product_return(full_part["full_exposure_primary_daily_return"]),
                "monthly_return_delta_vs_full_exposure": _product_return(part["allocator_daily_return"]) - _product_return(full_part["full_exposure_primary_daily_return"]),
                "average_gross_exposure": float(part["total_gross_exposure"].mean()),
                "cash_only_day_share": float(part["cash_only_flag"].astype(bool).mean()),
                "risk_on_day_count": int(part["market_state"].eq("risk_on").sum()),
                "risk_neutral_day_count": int(part["market_state"].eq("risk_neutral").sum()),
                "risk_off_day_count": int(part["market_state"].eq("risk_off").sum()),
            }
        )
    monthly_summary = pd.DataFrame(monthly_rows)

    risk_rows: list[dict[str, Any]] = []
    for split in SPLITS:
        part = allocator.loc[allocator["allocator_policy_id"].eq("full_exposure_primary_baseline") & allocator["split"].eq(split)].copy()
        risk_on = part.loc[part["market_state"].eq("risk_on")]
        all_full = _metric_row(part, "full_exposure_primary_daily_return")
        risk_period = _product_return(risk_on["full_exposure_primary_daily_return"])
        risk_mean = float(risk_on["full_exposure_primary_daily_return"].mean()) if len(risk_on) else np.nan
        risk_rows.append(
            {
                "split": split,
                "risk_on_day_count": int(len(risk_on)),
                "risk_on_day_share": _safe_div(len(risk_on), len(part)),
                "full_exposure_primary_period_return": all_full["period_return"],
                "full_exposure_primary_daily_mean": all_full["daily_mean"],
                "full_exposure_primary_monthly_p10": all_full["monthly_p10"],
                "full_exposure_primary_max_drawdown": all_full["max_drawdown"],
                "risk_on_full_exposure_period_return": risk_period,
                "risk_on_full_exposure_daily_mean": risk_mean,
                "risk_on_full_exposure_gate_status": "pass" if np.isfinite(risk_period) and risk_period > 0 and np.isfinite(risk_mean) and risk_mean > 0 else "fail",
                "blocking_reason": "" if split != "validation" or (np.isfinite(risk_period) and risk_period > 0 and np.isfinite(risk_mean) and risk_mean > 0) else "risk_on_full_exposure_not_positive",
            }
        )
    risk_audit = pd.DataFrame(risk_rows)

    activation_rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        for split in ["validation", "robustness"]:
            part = allocator.loc[allocator["allocator_policy_id"].eq(policy) & allocator["split"].eq(split)].copy()
            eligible = (
                part["market_state"].eq("risk_on")
                & (part["r04e_union_primary_sleeve_active_count"] < 20)
                & (part["base_breakout_vcp_secondary_sleeve_active_count"] > 0)
            )
            day_count = int(eligible.sum())
            share = _safe_div(day_count, len(part))
            min_days = int(thresholds[f"secondary_activation_min_{split}_active_days"])
            min_share = float(thresholds[f"secondary_activation_min_{split}_active_share"])
            status = "secondary_activation_sufficient"
            if day_count < min_days or (np.isfinite(share) and share < min_share):
                status = "secondary_sleeve_insufficient_activation" if split == "validation" else "robustness_secondary_sleeve_insufficient_activation"
            if policy != "market_state_cash_plus_basebreakout_secondary_v1":
                status = "not_applicable"
            activation_rows.append(
                {
                    "allocator_policy_id": policy,
                    "split": split,
                    "validation_trading_day_count": int(len(part)),
                    "risk_on_day_count": int(part["market_state"].eq("risk_on").sum()),
                    "primary_active_lt20_day_count": int((part["r04e_union_primary_sleeve_active_count"] < 20).sum()),
                    "secondary_active_day_count": int((part["base_breakout_vcp_secondary_sleeve_active_count"] > 0).sum()),
                    "secondary_activation_day_count": day_count,
                    "secondary_activation_day_share": share,
                    "activation_day_count_min": min_days,
                    "activation_day_share_min": min_share,
                    "secondary_activation_status": status if split == "validation" else "",
                    "robustness_secondary_activation_status": status if split == "robustness" else "",
                    "policy_blocking_reason": "" if status in {"secondary_activation_sufficient", "not_applicable"} else status,
                }
            )
    secondary_activation = pd.DataFrame(activation_rows)

    mostly_rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        for split in SPLITS:
            metrics = policy_metrics[(policy, split)]
            risk = risk_audit.loc[risk_audit["split"].eq(split)].iloc[0]
            status = "baseline_reference_only" if policy == "full_exposure_primary_baseline" else "pass"
            reason = ""
            if policy in SELECTABLE_POLICIES and (
                metrics["average_gross_exposure"] < float(thresholds["average_gross_exposure_min"])
                or metrics["cash_only_day_share"] > float(thresholds["cash_only_day_share_max"])
            ):
                status = "mostly_cash_illusion_fail"
                reason = "gross_exposure_or_cash_only_threshold_failed"
            mostly_rows.append(
                {
                    "allocator_policy_id": policy,
                    "split": split,
                    "average_gross_exposure": metrics["average_gross_exposure"],
                    "average_gross_exposure_min": float(thresholds["average_gross_exposure_min"]),
                    "cash_only_day_share": metrics["cash_only_day_share"],
                    "cash_only_day_share_max": float(thresholds["cash_only_day_share_max"]),
                    "risk_on_full_exposure_period_return": risk["risk_on_full_exposure_period_return"],
                    "risk_on_full_exposure_daily_mean": risk["risk_on_full_exposure_daily_mean"],
                    "overall_allocator_period_return": metrics["period_return"],
                    "overall_allocator_daily_mean": metrics["daily_mean"],
                    "mostly_cash_illusion_status": status,
                    "blocking_reason": reason,
                }
            )
    mostly_audit = pd.DataFrame(mostly_rows)

    gate_rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        val = policy_metrics[(policy, "validation")]
        rob = policy_metrics[(policy, "robustness")]
        full_val = full_metrics_by_split["validation"]
        tail_val = right_tail_by_key[(policy, "validation")]
        tail_rob = right_tail_by_key[(policy, "robustness")]
        risk_val = risk_audit.loc[risk_audit["split"].eq("validation")].iloc[0]
        p10_delta = val["monthly_p10"] - full_val["monthly_p10"]
        dd_delta = full_val["max_drawdown"] - val["max_drawdown"]
        worst_delta = val["worst_20d_return"] - full_val["worst_20d_return"]
        robust_ok = (
            rob["period_return"] >= float(thresholds["robustness_period_return_min"])
            and tail_rob["right_tail_gate_status"] == "right_tail_pass"
            and rob["average_gross_exposure"] >= float(thresholds["average_gross_exposure_min"])
        )
        validation_ok = (
            val["period_return"] > 0
            and val["daily_mean"] > 0
            and p10_delta > 0
            and dd_delta > 0
            and worst_delta > 0
            and val["average_gross_exposure"] >= float(thresholds["average_gross_exposure_min"])
            and val["cash_only_day_share"] <= float(thresholds["cash_only_day_share_max"])
            and risk_val["risk_on_full_exposure_period_return"] > 0
            and risk_val["risk_on_full_exposure_daily_mean"] > 0
            and tail_val["right_tail_gate_status"] == "right_tail_pass"
        )
        status = "validation_pass"
        reason = ""
        robustness_status = "robustness_readonly_pass" if robust_ok else "robustness_readonly_failed"
        if policy == "full_exposure_primary_baseline":
            status = "baseline_reference_only"
            robustness_status = "baseline_reference_only"
        elif policy == "market_state_cash_plus_basebreakout_secondary_v1":
            val_activation = secondary_activation.loc[
                (secondary_activation["allocator_policy_id"].eq(policy)) & (secondary_activation["split"].eq("validation"))
            ].iloc[0]["secondary_activation_status"]
            rob_activation = secondary_activation.loc[
                (secondary_activation["allocator_policy_id"].eq(policy)) & (secondary_activation["split"].eq("robustness"))
            ].iloc[0]["robustness_secondary_activation_status"]
            complete_base = replay_audit.loc[
                replay_audit["sleeve_id"].eq("base_breakout_vcp_secondary_sleeve") & replay_audit["split"].eq("validation")
            ]
            if not complete_base.empty and str(complete_base.iloc[0]["replay_censor_status"]) != "pass":
                status = "blocked_preflight_replay_complete_share"
                reason = "base_breakout_replay_complete_share_below_min"
            elif val_activation == "secondary_sleeve_insufficient_activation":
                status = "blocked_secondary_sleeve_insufficient_activation"
                reason = val_activation
            elif not validation_ok:
                status = "validation_fail"
                reason = "validation_gate_condition_failed"
            elif rob_activation == "robustness_secondary_sleeve_insufficient_activation":
                status = "robustness_secondary_sleeve_insufficient_activation"
                robustness_status = rob_activation
                reason = rob_activation
            elif not robust_ok:
                status = "robustness_readonly_failed"
                reason = "robustness_guardrail_failed"
        elif not validation_ok:
            status = "validation_fail"
            reason = "validation_gate_condition_failed"
        elif not robust_ok:
            status = "robustness_readonly_failed"
            reason = "robustness_guardrail_failed"
        gate_rows.append(
            {
                "allocator_policy_id": policy,
                "split": "validation",
                "validation_gate_status": status,
                "period_return": val["period_return"],
                "daily_mean": val["daily_mean"],
                "monthly_p10": val["monthly_p10"],
                "monthly_p10_delta_vs_full_exposure": p10_delta,
                "max_drawdown": val["max_drawdown"],
                "max_drawdown_delta_vs_full_exposure": dd_delta,
                "worst_20d_delta_vs_full_exposure": worst_delta,
                "average_gross_exposure": val["average_gross_exposure"],
                "cash_only_day_share": val["cash_only_day_share"],
                "risk_on_full_exposure_period_return": risk_val["risk_on_full_exposure_period_return"],
                "risk_on_full_exposure_daily_mean": risk_val["risk_on_full_exposure_daily_mean"],
                "right_tail_retention_vs_full_exposure": tail_val["right_tail_retention_vs_full_exposure"],
                "absolute_p90_floor_min": tail_val["absolute_p90_floor_min"],
                "allocator_monthly_p90": val["monthly_p90"],
                "full_exposure_primary_monthly_p90": full_val["monthly_p90"],
                "right_tail_gate_mode": tail_val["right_tail_gate_mode"],
                "right_tail_gate_status": tail_val["right_tail_gate_status"],
                "robustness_readonly_status": robustness_status,
                "robustness_period_return": rob["period_return"],
                "robustness_allocator_monthly_p90": rob["monthly_p90"],
                "robustness_full_exposure_primary_monthly_p90": full_metrics_by_split["robustness"]["monthly_p90"],
                "robustness_right_tail_gate_mode": tail_rob["right_tail_gate_mode"],
                "robustness_right_tail_gate_status": tail_rob["right_tail_gate_status"],
                "robustness_right_tail_retention_vs_full_exposure": tail_rob["right_tail_retention_vs_full_exposure"],
                "robustness_absolute_p90_floor_min": tail_rob["absolute_p90_floor_min"],
                "robustness_average_gross_exposure": rob["average_gross_exposure"],
                "blocking_reason": reason,
            }
        )
    gate_audit = pd.DataFrame(gate_rows)
    gate_map = dict(zip(gate_audit["allocator_policy_id"], gate_audit["validation_gate_status"], strict=False))
    robustness_map = dict(zip(gate_audit["allocator_policy_id"], gate_audit["robustness_readonly_status"], strict=False))
    val_act_map = dict(
        zip(
            secondary_activation.loc[secondary_activation["split"].eq("validation"), "allocator_policy_id"],
            secondary_activation.loc[secondary_activation["split"].eq("validation"), "secondary_activation_status"],
            strict=False,
        )
    )
    rob_act_map = dict(
        zip(
            secondary_activation.loc[secondary_activation["split"].eq("robustness"), "allocator_policy_id"],
            secondary_activation.loc[secondary_activation["split"].eq("robustness"), "robustness_secondary_activation_status"],
            strict=False,
        )
    )
    policy_summary["validation_gate_status"] = policy_summary["allocator_policy_id"].map(gate_map).fillna("")
    policy_summary["robustness_readonly_status"] = policy_summary["allocator_policy_id"].map(robustness_map).fillna("")
    policy_summary["secondary_activation_status"] = policy_summary["allocator_policy_id"].map(val_act_map).fillna("")
    policy_summary["robustness_secondary_activation_status"] = policy_summary["allocator_policy_id"].map(rob_act_map).fillna("")
    policy_summary["blocking_reason"] = policy_summary["allocator_policy_id"].map(
        dict(zip(gate_audit["allocator_policy_id"], gate_audit["blocking_reason"], strict=False))
    ).fillna("")

    decomp_rows: list[dict[str, Any]] = []
    sleeve_state = sleeves.merge(market_state[["trade_date", "market_state"]], on="trade_date", how="left")
    registry = _sleeve_registry(config)[["sleeve_id", "allocation_status"]]
    sleeve_state = sleeve_state.merge(registry, on="sleeve_id", how="left")
    for (sleeve_id, split, state), part in sleeve_state.groupby(["sleeve_id", "split", "market_state"], sort=False):
        monthly = _monthly_returns(part, "sleeve_daily_return")
        active = part.loc[part["sleeve_active_count"] > 0]
        decomp_rows.append(
            {
                "sleeve_id": sleeve_id,
                "split": split,
                "market_state": state,
                "active_day_count": int((part["sleeve_active_count"] > 0).sum()),
                "active_day_share": _safe_div(int((part["sleeve_active_count"] > 0).sum()), len(part)),
                "sleeve_period_return": _product_return(part["sleeve_daily_return"]),
                "all_day_period_return": _product_return(part["sleeve_daily_return"]),
                "active_only_period_return": _product_return(active["sleeve_daily_return"]) if len(active) else np.nan,
                "sleeve_daily_mean": float(part["sleeve_daily_return"].mean()) if len(part) else np.nan,
                "sleeve_monthly_p10": _quantile(monthly, 0.10),
                "sleeve_monthly_p90": _quantile(monthly, 0.90),
                "sleeve_max_drawdown": _max_drawdown(part["sleeve_daily_return"]),
                "sleeve_return_contribution": _product_return(part["sleeve_daily_return"]),
                "allocation_status": part["allocation_status"].iloc[0],
                "decomposition_status": "available" if len(part) else "missing",
                "blocking_reason": "",
            }
        )
    decomp = pd.DataFrame(decomp_rows)
    return {
        "policy_summary": policy_summary,
        "monthly_summary": monthly_summary,
        "risk_audit": risk_audit,
        "secondary_activation": secondary_activation,
        "mostly_audit": mostly_audit,
        "gate_audit": gate_audit,
        "decomposition": decomp,
    }


def _final_decision(config: dict[str, Any], upstream_reasons: list[str], reports: dict[str, pd.DataFrame]) -> tuple[str, str, str, bool, str, pd.DataFrame]:
    gate = reports["gate_audit"]
    risk = reports["risk_audit"].loc[reports["risk_audit"]["split"].eq("validation")].iloc[0]
    mostly = reports["mostly_audit"]
    selected_policy = ""
    selected_gate = ""
    decision_rows: list[dict[str, Any]] = []
    final_decision = "r05b_allocator_not_viable_validation"
    reason = "no_selectable_allocator_policy_passed"
    if upstream_reasons:
        final_decision = "r05b_blocked_upstream_state_changed"
        reason = ";".join(upstream_reasons)
    elif risk["risk_on_full_exposure_period_return"] <= 0:
        final_decision = "r05b_risk_on_full_exposure_failed"
        reason = "risk_on_full_exposure_validation_net_not_positive"
    else:
        val_mostly = mostly.loc[mostly["split"].eq("validation") & mostly["allocator_policy_id"].isin(SELECTABLE_POLICIES)]
        all_mostly = bool(val_mostly["mostly_cash_illusion_status"].eq("mostly_cash_illusion_fail").all())
        if all_mostly:
            final_decision = "r05b_mostly_cash_illusion"
            reason = "all_selectable_policies_mostly_cash_illusion"
        else:
            passed = gate.loc[gate["allocator_policy_id"].isin(SELECTABLE_POLICIES) & gate["validation_gate_status"].eq("validation_pass")].copy()
            if len(passed):
                passed = passed.sort_values("period_return", ascending=False)
                selected_policy = str(passed.iloc[0]["allocator_policy_id"])
                selected_gate = "validation_pass"
                final_decision = "r05b_sleeve_allocator_passed_diagnostic_only"
                reason = ""
            else:
                final_decision = "r05b_allocator_not_viable_validation"
                failed = gate.loc[gate["allocator_policy_id"].isin(SELECTABLE_POLICIES), ["allocator_policy_id", "validation_gate_status"]]
                reason = json.dumps(failed.to_dict(orient="records"), ensure_ascii=True, separators=(",", ":"))
    terminal, allowed_next = FINAL_DECISION_CONTRACT[final_decision]
    checks = [
        ("required_upstream_state_changed", bool(upstream_reasons), "r05b_blocked_upstream_state_changed"),
        ("validator_failed", False, "r05b_blocked_validation_failed"),
        ("risk_on_full_exposure_validation_net_le_0", bool(risk["risk_on_full_exposure_period_return"] <= 0), "r05b_risk_on_full_exposure_failed"),
        (
            "all_selectable_policies_mostly_cash",
            bool(
                reports["mostly_audit"]
                .loc[
                    reports["mostly_audit"]["split"].eq("validation")
                    & reports["mostly_audit"]["allocator_policy_id"].isin(SELECTABLE_POLICIES),
                    "mostly_cash_illusion_status",
                ]
                .eq("mostly_cash_illusion_fail")
                .all()
            ),
            "r05b_mostly_cash_illusion",
        ),
        (
            "no_allocator_policy_passes_validation_and_robustness",
            not gate.loc[gate["allocator_policy_id"].isin(SELECTABLE_POLICIES), "validation_gate_status"].eq("validation_pass").any(),
            "r05b_allocator_not_viable_validation",
        ),
        (
            "one_fixed_allocator_policy_passes",
            gate.loc[gate["allocator_policy_id"].isin(SELECTABLE_POLICIES), "validation_gate_status"].eq("validation_pass").any(),
            "r05b_sleeve_allocator_passed_diagnostic_only",
        ),
    ]
    for priority, (name, met, candidate) in enumerate(checks, start=1):
        decision_rows.append(
            {
                "decision_priority": priority,
                "condition_name": name,
                "condition_met": bool(met),
                "candidate_final_decision": candidate,
                "selected_final_decision": final_decision,
                "terminal_stop_flag": terminal,
                "allowed_next_requirement": allowed_next,
                "blocking_reason": reason,
            }
        )
    return final_decision, selected_policy, selected_gate, terminal, allowed_next, pd.DataFrame(decision_rows)


def _fmt_pct(value: Any) -> str:
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return ""
    return f"{float(num) * 100:.2f}%"


def _fmt_num(value: Any, digits: int = 4) -> str:
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return ""
    return f"{float(num):.{digits}f}"


def _fmt_int(value: Any) -> str:
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return ""
    return str(int(num))


def _markdown_table(df: pd.DataFrame, columns: list[str], percent_cols: set[str] | None = None, int_cols: set[str] | None = None) -> str:
    percent_cols = percent_cols or set()
    int_cols = int_cols or set()
    out = df.loc[:, columns].copy()
    for col in out.columns:
        if col in percent_cols:
            out[col] = out[col].map(_fmt_pct)
        elif col in int_cols:
            out[col] = out[col].map(_fmt_int)
        elif pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].map(lambda value: _fmt_num(value, 4))
        else:
            out[col] = out[col].fillna("")
    return out.to_markdown(index=False)


def _write_report(
    path: Path,
    upstream_state: dict[str, Any],
    final_decision: str,
    selected_policy: str,
    terminal: bool,
    allowed_next: str,
    reports: dict[str, pd.DataFrame],
) -> None:
    gate = reports["gate_audit"]
    policy_summary = reports["policy_summary"]
    risk = reports["risk_audit"]
    activation = reports["secondary_activation"]
    mostly = reports["mostly_audit"]
    replay = reports["r05b_preflight_replay_censor_audit"] if "r05b_preflight_replay_censor_audit" in reports else reports.get("preflight_replay")
    monthly = reports["monthly_summary"]

    risk_validation = risk.loc[risk["split"].astype(str).eq("validation")].iloc[0]
    risk_train = risk.loc[risk["split"].astype(str).eq("train")].iloc[0]
    risk_robustness = risk.loc[risk["split"].astype(str).eq("robustness")].iloc[0]
    cash_gate = gate.loc[gate["allocator_policy_id"].astype(str).eq("market_state_cash_allocator_v1")].iloc[0]
    secondary_gate = gate.loc[gate["allocator_policy_id"].astype(str).eq("market_state_cash_plus_basebreakout_secondary_v1")].iloc[0]
    baseline_gate = gate.loc[gate["allocator_policy_id"].astype(str).eq("full_exposure_primary_baseline")].iloc[0]
    cash_mostly = mostly.loc[
        mostly["allocator_policy_id"].astype(str).eq("market_state_cash_allocator_v1")
        & mostly["split"].astype(str).eq("validation")
    ].iloc[0]
    secondary_activation = activation.loc[
        activation["allocator_policy_id"].astype(str).eq("market_state_cash_plus_basebreakout_secondary_v1")
        & activation["split"].astype(str).eq("validation")
    ].iloc[0]
    secondary_activation_robust = activation.loc[
        activation["allocator_policy_id"].astype(str).eq("market_state_cash_plus_basebreakout_secondary_v1")
        & activation["split"].astype(str).eq("robustness")
    ].iloc[0]
    replay_validation = replay.loc[replay["split"].astype(str).eq("validation")].copy() if replay is not None else pd.DataFrame()

    validation_focus = gate[
        [
            "allocator_policy_id",
            "validation_gate_status",
            "period_return",
            "daily_mean",
            "monthly_p10_delta_vs_full_exposure",
            "max_drawdown_delta_vs_full_exposure",
            "worst_20d_delta_vs_full_exposure",
            "average_gross_exposure",
            "cash_only_day_share",
            "right_tail_gate_status",
            "right_tail_retention_vs_full_exposure",
            "blocking_reason",
        ]
    ].copy()
    validation_focus = validation_focus.rename(
        columns={
            "allocator_policy_id": "policy",
            "validation_gate_status": "gate_status",
            "period_return": "validation_return",
            "daily_mean": "daily_mean",
            "monthly_p10_delta_vs_full_exposure": "p10_delta",
            "max_drawdown_delta_vs_full_exposure": "drawdown_delta",
            "worst_20d_delta_vs_full_exposure": "worst20d_delta",
            "average_gross_exposure": "avg_gross",
            "cash_only_day_share": "cash_only_share",
            "right_tail_gate_status": "right_tail",
            "right_tail_retention_vs_full_exposure": "right_tail_retention",
            "blocking_reason": "blocking_reason",
        }
    )
    validation_focus_table = _markdown_table(
        validation_focus,
        [
            "policy",
            "gate_status",
            "validation_return",
            "daily_mean",
            "p10_delta",
            "drawdown_delta",
            "worst20d_delta",
            "avg_gross",
            "cash_only_share",
            "right_tail",
            "right_tail_retention",
            "blocking_reason",
        ],
        percent_cols={"validation_return", "daily_mean", "p10_delta", "drawdown_delta", "worst20d_delta", "avg_gross", "cash_only_share"},
    )

    risk_focus = risk[
        [
            "split",
            "risk_on_day_count",
            "risk_on_day_share",
            "full_exposure_primary_period_return",
            "risk_on_full_exposure_period_return",
            "risk_on_full_exposure_daily_mean",
            "risk_on_full_exposure_gate_status",
            "blocking_reason",
        ]
    ].copy()
    risk_focus_table = _markdown_table(
        risk_focus,
        [
            "split",
            "risk_on_day_count",
            "risk_on_day_share",
            "full_exposure_primary_period_return",
            "risk_on_full_exposure_period_return",
            "risk_on_full_exposure_daily_mean",
            "risk_on_full_exposure_gate_status",
            "blocking_reason",
        ],
        percent_cols={
            "risk_on_day_share",
            "full_exposure_primary_period_return",
            "risk_on_full_exposure_period_return",
            "risk_on_full_exposure_daily_mean",
        },
        int_cols={"risk_on_day_count"},
    )

    activation_focus = activation.loc[
        activation["allocator_policy_id"].astype(str).eq("market_state_cash_plus_basebreakout_secondary_v1"),
        [
            "split",
            "validation_trading_day_count",
            "risk_on_day_count",
            "primary_active_lt20_day_count",
            "secondary_active_day_count",
            "secondary_activation_day_count",
            "secondary_activation_day_share",
            "activation_day_count_min",
            "activation_day_share_min",
            "secondary_activation_status",
            "robustness_secondary_activation_status",
        ],
    ].copy()
    activation_focus_table = _markdown_table(
        activation_focus,
        list(activation_focus.columns),
        percent_cols={"secondary_activation_day_share", "activation_day_share_min"},
        int_cols={
            "validation_trading_day_count",
            "risk_on_day_count",
            "primary_active_lt20_day_count",
            "secondary_active_day_count",
            "secondary_activation_day_count",
            "activation_day_count_min",
        },
    )

    replay_focus_table = ""
    if not replay_validation.empty:
        replay_focus = replay_validation[
            [
                "sleeve_id",
                "candidate_id",
                "source_event_count",
                "complete_replay_event_count",
                "complete_replay_event_share",
                "lookahead_censored_event_count",
                "replay_censor_status",
            ]
        ].copy()
        replay_focus_table = _markdown_table(
            replay_focus,
            list(replay_focus.columns),
            percent_cols={"complete_replay_event_share"},
            int_cols={"source_event_count", "complete_replay_event_count", "lookahead_censored_event_count"},
        )

    validation_months = monthly.loc[monthly["split"].astype(str).eq("validation")].copy()
    worst_full = validation_months.loc[
        validation_months["allocator_policy_id"].astype(str).eq("full_exposure_primary_baseline")
    ].nsmallest(6, "monthly_return")
    worst_cash = validation_months.loc[
        validation_months["allocator_policy_id"].astype(str).eq("market_state_cash_allocator_v1")
    ].nsmallest(6, "monthly_return")
    worst_months = pd.concat(
        [
            worst_full.assign(view="full_exposure_primary_baseline"),
            worst_cash.assign(view="market_state_cash_allocator_v1"),
        ],
        ignore_index=True,
    )
    worst_months_table = _markdown_table(
        worst_months[
            [
                "view",
                "month",
                "monthly_return",
                "full_exposure_primary_monthly_return",
                "monthly_return_delta_vs_full_exposure",
                "average_gross_exposure",
                "cash_only_day_share",
                "risk_on_day_count",
                "risk_neutral_day_count",
                "risk_off_day_count",
            ]
        ],
        [
            "view",
            "month",
            "monthly_return",
            "full_exposure_primary_monthly_return",
            "monthly_return_delta_vs_full_exposure",
            "average_gross_exposure",
            "cash_only_day_share",
            "risk_on_day_count",
            "risk_neutral_day_count",
            "risk_off_day_count",
        ],
        percent_cols={
            "monthly_return",
            "full_exposure_primary_monthly_return",
            "monthly_return_delta_vs_full_exposure",
            "average_gross_exposure",
            "cash_only_day_share",
        },
        int_cols={"risk_on_day_count", "risk_neutral_day_count", "risk_off_day_count"},
    )

    lines = [
        "# R05b Sleeve Allocator / Exposure Composition Diagnostic Final Report",
        "",
        "R05b does not discover alpha.",
        "R05b does not reinterpret R04e union as alpha.",
        "R05b does not rescue R05 Preflight failed primitives.",
        "R05b only tests whether failed / relative-improvement pools have limited sleeve value.",
        "",
        "## 结论",
        "",
        f"本次 R05b 的最终决策是 `{final_decision}`，不是因为上游 artifact 或 validator 失败，而是因为 validation 期的 `risk_on` 全仓 primary sleeve 本身不赚钱，触发了 §8 的 hard kill。具体证据是 validation 期 `risk_on_full_exposure_period_return = {_fmt_pct(risk_validation['risk_on_full_exposure_period_return'])}`，`risk_on_full_exposure_daily_mean = {_fmt_pct(risk_validation['risk_on_full_exposure_daily_mean'])}`。",
        "",
        "这意味着 market-state allocator 的核心前提没有成立：即使只在模型判定为 `risk_on` 的日期给 R04e primary sleeve 满 exposure，primary path 仍然是负收益。后续 cash allocator 虽然降低了回撤和左尾，但它没有把 validation 期组合收益变成正数，也没有保住足够的右尾收益，因此不能构成 diagnostic pass。",
        "",
        "## 上游状态",
        "",
        f"- R04e validation: {upstream_state.get('r04e_validation_status')} / {upstream_state.get('r04e_final_decision')}",
        f"- R05 Preflight validation: {upstream_state.get('r05_preflight_validation_status')} / {upstream_state.get('r05_preflight_final_decision')}",
        f"- R05 Preflight candidate pass count: {upstream_state.get('r05_preflight_candidate_pass_count')}",
        f"- R05a status: {upstream_state.get('r05a_status')}",
        "",
        "这些状态满足 R05b 的进入条件：R04e 已经是 portfolio-level not viable，R05 Preflight 没有 standalone candidate pass，R05a 已被 preflight-blocked。因此本报告解释的是 sleeve allocator 诊断失败，而不是上游状态漂移。",
        "",
        "## 决策结果",
        "",
        f"- final_decision: `{final_decision}`",
        f"- selected_allocator_policy_id: `{selected_policy}`",
        f"- terminal_stop_flag: `{terminal}`",
        f"- allowed_next_requirement: `{allowed_next}`",
        f"- blocking_reason: `risk_on_full_exposure_validation_net_not_positive`",
        "",
        "## 失败原因 1: Risk-on full exposure 先验失败",
        "",
        "R05b 要求 allocator 不能只是靠降 exposure 避开亏损；如果 `risk_on` 日期里的 full-exposure primary sleeve 本身不赚钱，则不能把 cash allocator 解释为有效的组合层修复。这个 hard kill 在 validation 期被触发。",
        "",
        risk_focus_table,
        "",
        f"在 validation 期，`risk_on` 共有 {_fmt_int(risk_validation['risk_on_day_count'])} 个交易日，占 {_fmt_pct(risk_validation['risk_on_day_share'])}。但这些日期上 full-exposure primary 的累计收益是 {_fmt_pct(risk_validation['risk_on_full_exposure_period_return'])}，日均收益是 {_fmt_pct(risk_validation['risk_on_full_exposure_daily_mean'])}。这不是单纯 exposure 太高的问题，而是 `risk_on` 状态没有筛出正期望 primary exposure。",
        "",
        f"对比来看，train 期同一口径为 {_fmt_pct(risk_train['risk_on_full_exposure_period_return'])}，robustness 期为 {_fmt_pct(risk_robustness['risk_on_full_exposure_period_return'])}。validation 的失败说明这个 market-state rule 在关键验证区间不稳定，robustness 的好表现按需求只能作为只读信息，不能救回 validation failure。",
        "",
        "## 失败原因 2: Cash allocator 降低损失，但没有通过 validation gate",
        "",
        "`market_state_cash_allocator_v1` 的确降低了风险暴露：validation 平均 gross exposure 为 "
        f"{_fmt_pct(cash_gate['average_gross_exposure'])}，cash-only day share 为 {_fmt_pct(cash_gate['cash_only_day_share'])}，没有触发 mostly-cash illusion 阈值。它也改善了左尾和回撤：monthly p10 delta 为 {_fmt_pct(cash_gate['monthly_p10_delta_vs_full_exposure'])}，max drawdown delta 为 {_fmt_pct(cash_gate['max_drawdown_delta_vs_full_exposure'])}。",
        "",
        "但是它仍然没有满足 pass 条件：validation period return 仍为 "
        f"{_fmt_pct(cash_gate['period_return'])}，daily mean 为 {_fmt_pct(cash_gate['daily_mean'])}。同时 right-tail retention 只有 {_fmt_num(cash_gate['right_tail_retention_vs_full_exposure'], 4)}，低于 validation 阈值 0.60，`right_tail_gate_status = {cash_gate['right_tail_gate_status']}`。因此它只是把亏损压小，并没有形成可通过 gate 的正收益 allocator。",
        "",
        "## 失败原因 3: Secondary sleeve 没有形成有效激活样本",
        "",
        "`market_state_cash_plus_basebreakout_secondary_v1` 在 validation 期被 `secondary_sleeve_insufficient_activation` 阻断。虽然 base breakout secondary sleeve 在很多日期内部有 active positions，但 policy 只有在 `market_state == risk_on` 且 primary active_count < 20 且 secondary active_count > 0 时才允许占用 20% sleeve。这个三条件交集在 validation 期为 0 天。",
        "",
        activation_focus_table,
        "",
        f"具体看 validation：risk_on 日期 {_fmt_int(secondary_activation['risk_on_day_count'])} 天，primary active_count < 20 的日期只有 {_fmt_int(secondary_activation['primary_active_lt20_day_count'])} 天，secondary active 日期 {_fmt_int(secondary_activation['secondary_active_day_count'])} 天，但三者交集 `secondary_activation_day_count = {_fmt_int(secondary_activation['secondary_activation_day_count'])}`。这低于要求的 20 天和 2% active share。robustness 期同样是 0 天，因此 secondary sleeve 没有证明可复用。",
        "",
        "## 失败原因 4: 不是 replay 或数据完整性导致的假失败",
        "",
        "R05 Preflight-derived sleeves 的 replay censor audit 通过，base breakout validation complete share 为 95.89%，lookahead censored event count 为 0。Diagnostic sleeves 也满足 complete share 阈值。因此失败主要来自 allocator/gate 经济含义，而不是 frozen event replay 不完整。",
        "",
        replay_focus_table,
        "",
        "## Validation Gate 细节",
        "",
        validation_focus_table,
        "",
        "表中可以看到：baseline 只是 reference，不参与 pass/fail；cash allocator 是 `validation_fail`；secondary policy 是 `blocked_secondary_sleeve_insufficient_activation`。两条 selectable policies 都没有通过 validation。",
        "",
        "## Mostly-cash illusion 检查",
        "",
        f"本次失败不是因为 allocator 过度空仓。`market_state_cash_allocator_v1` 在 validation 期 average gross exposure 为 {_fmt_pct(cash_mostly['average_gross_exposure'])}，高于 35% 下限；cash-only day share 为 {_fmt_pct(cash_mostly['cash_only_day_share'])}，低于 65% 上限。也就是说，allocator 失败不是因为暴露过低，而是在足够暴露下仍没有正收益和右尾保留。",
        "",
        "## Validation 期最差月份",
        "",
        "下表列出 full exposure baseline 和 cash allocator 在 validation 期各自最差的月份。cash allocator 能缓解部分月份的损失，但不能改变整段 validation 为负的事实。",
        "",
        worst_months_table,
        "",
        "## Robustness 为什么不能救回",
        "",
        f"robustness 期 cash allocator period return 为 {_fmt_pct(cash_gate['robustness_period_return'])}，right-tail 通过，平均 gross exposure 为 {_fmt_pct(cash_gate['robustness_average_gross_exposure'])}。但 requirement 明确规定 robustness 是 read-only guardrail，不能用 robustness 好表现反向选择或救回 validation failure。因此 robustness 只能说明该现象在后续区间有反弹，不能推翻 validation hard kill。",
        "",
        "## 实验含义",
        "",
        "R05b 原问题是：失败的 alpha pools 是否还能在 sleeve / exposure composition 层面产生有限诊断价值。结果显示，在当前 frozen market-state classifier、R04e primary path 和 R05 Preflight sleeves 下，答案是否定的：",
        "",
        "- primary 的 `risk_on` exposure 在 validation 期不是正期望；",
        "- cash allocator 主要减少亏损和回撤，但仍为负收益，右尾 retention 不足；",
        "- base breakout secondary 的 activation 条件过窄，validation 和 robustness 都没有有效激活样本；",
        "- replay 完整性和 lookahead audit 没有解释失败。",
        "",
        "因此当前 R05b 不能支持继续做 R05c/R05d 的 sleeve variant。若要继续，需要进入 EP5，改变 universe、horizon、hedge leg、execution model 或问题 framing。",
        "",
        "## 完整 Policy Summary",
        "",
        policy_summary.loc[policy_summary["split"].isin(["validation", "robustness"])].to_markdown(index=False),
        "",
        "## Terminal Stop",
        "",
    ]
    if terminal:
        lines.extend(
            [
                "EP4 terminated.",
                "Do not create R05c/R05d sleeve variants.",
                "Further work requires EP5 with a changed universe, horizon, hedge leg, execution model, or problem framing.",
            ]
        )
    else:
        lines.append("Diagnostic allocator passed only as a frozen diagnostic; production allocation is not approved.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for directory in [cache_dir, reports_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    upstream_state, upstream_reasons = _upstream_state(config)
    calendar = _load_calendar(config["price_provider"]["calendar_source_path"])
    calendar_frame = _output_calendar(config, calendar)
    event_panel = pd.read_parquet(topic_path(config["upstream_r05_preflight"]["candidate_event_panel"]))
    instruments = sorted(set(event_panel["instrument_id"].astype(str).str.upper()) | {config["price_provider"]["index_instrument"].upper()})
    start_pos = max(0, int(calendar.searchsorted(pd.Timestamp(config["split"]["train_start"]), side="left")) - 90)
    start = pd.Timestamp(calendar[start_pos]).normalize()
    end = pd.Timestamp(config["split"]["robustness_end"]).normalize()
    close = _load_close_panel(config, instruments, start, end, calendar)

    market_state, classifier = _market_state_panel(config, calendar_frame, close)
    primary = _primary_sleeve(config, calendar_frame)
    preflight_sleeves, replay_audit = _replay_preflight_sleeves(config, calendar_frame, calendar, close)
    cash_benchmark = _cash_and_benchmark_sleeves(config, calendar_frame, close)
    sleeve_daily = pd.concat([primary, preflight_sleeves, cash_benchmark], ignore_index=True)
    allocator_daily = _allocator_daily(config, calendar_frame, market_state, sleeve_daily, close)

    reports = _build_reports(config, sleeve_daily, allocator_daily, market_state, replay_audit)
    reports["preflight_replay"] = replay_audit
    final_decision, selected_policy, selected_gate, terminal, allowed_next, terminal_audit = _final_decision(config, upstream_reasons, reports)
    terminal_audit["selected_final_decision"] = final_decision
    final_df = pd.DataFrame(
        [
            {
                "requirement_id": config["requirement_id"],
                "final_decision": final_decision,
                "selected_allocator_policy_id": selected_policy,
                "validation_gate_status": selected_gate,
                "terminal_stop_flag": terminal,
                "allowed_next_requirement": allowed_next,
                "blocking_reason": "" if final_decision == "r05b_sleeve_allocator_passed_diagnostic_only" else terminal_audit.iloc[0]["blocking_reason"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )

    _write_parquet(sleeve_daily, cache_dir / "r05b_sleeve_daily_return_panel.parquet")
    _write_parquet(allocator_daily, cache_dir / "r05b_allocator_daily_return_panel.parquet")
    write_csv(_sleeve_registry(config), reports_dir / "r05b_sleeve_registry_frozen.csv")
    write_csv(classifier, reports_dir / "r05b_market_state_classifier_frozen.csv")
    write_csv(market_state, reports_dir / "r05b_market_state_panel.csv")
    write_csv(_policy_registry(), reports_dir / "r05b_allocator_policy_registry_frozen.csv")
    write_csv(replay_audit, reports_dir / "r05b_preflight_replay_censor_audit.csv")
    write_csv(reports["secondary_activation"], reports_dir / "r05b_secondary_sleeve_activation_audit.csv")
    write_csv(reports["decomposition"], reports_dir / "r05b_sleeve_return_decomposition.csv")
    write_csv(reports["risk_audit"], reports_dir / "r05b_risk_on_full_exposure_audit.csv")
    write_csv(reports["mostly_audit"], reports_dir / "r05b_mostly_cash_illusion_audit.csv")
    write_csv(reports["policy_summary"], reports_dir / "r05b_allocator_policy_summary.csv")
    write_csv(reports["monthly_summary"], reports_dir / "r05b_allocator_monthly_summary.csv")
    write_csv(reports["gate_audit"], reports_dir / "r05b_validation_gate_audit.csv")
    write_csv(terminal_audit, reports_dir / "r05b_terminal_decision_audit.csv")
    write_csv(final_df, reports_dir / "r05b_final_decision.csv")
    _write_report(
        reports_dir / "r05b_sleeve_allocator_exposure_composition_final_report.md",
        upstream_state,
        final_decision,
        selected_policy,
        terminal,
        allowed_next,
        reports,
    )

    artifacts = [
        cache_dir / "r05b_sleeve_daily_return_panel.parquet",
        cache_dir / "r05b_allocator_daily_return_panel.parquet",
        *sorted(reports_dir.glob("r05b_*.csv")),
        reports_dir / "r05b_sleeve_allocator_exposure_composition_final_report.md",
    ]
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "requirement_path": config["requirement_path"],
        "config_path": relpath(topic_path(config_path)),
        "config_hash": _hash_file(config_path),
        "runner_hash": _hash_file(Path(__file__)),
        "validator_hash": _hash_file(EP4_DIR / "scripts" / "validate_r05b_sleeve_allocator_exposure_composition_diagnostic.py")
        if (EP4_DIR / "scripts" / "validate_r05b_sleeve_allocator_exposure_composition_diagnostic.py").exists()
        else "",
        "output_root": config["output_root"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "split_definition_hash": _hash_json(config["split"]),
        "price_provider_hash": _hash_json(
            {
                "provider_type": config["price_provider"]["provider_type"],
                "price_source_path": config["price_provider"]["price_source_path"],
                "index_instrument": config["price_provider"]["index_instrument"],
                "instrument_count": len(instruments),
            }
        ),
        "upstream_state": upstream_state,
        "upstream_state_reasons": upstream_reasons,
        "final_decision": final_decision,
        "selected_allocator_policy_id": selected_policy,
        "terminal_stop_flag": terminal,
        "allowed_next_requirement": allowed_next,
        "artifact_hashes": _artifact_hashes(artifacts),
    }
    write_json(manifest, manifests_dir / "r05b_sleeve_allocator_exposure_composition_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EP4 R05b sleeve allocator exposure composition diagnostic.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    manifest = run(args.config)
    print(json.dumps({"final_decision": manifest["final_decision"], "output_root": manifest["output_root"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

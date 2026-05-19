#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from run_r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic import (  # noqa: E402
    _artifact_hashes,
    _hash_file,
    _hash_text,
    _load_calendar,
    _load_price_panel,
    _price_source_hash,
    _quantile,
    _safe_div,
    _split_bounds,
    _split_for_date,
)


DEFAULT_CONFIG = EP4_DIR / "configs" / "r05_preflight_alpha_pool_quick_feasibility_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
FINAL_DECISIONS = {
    "r05_preflight_go_r05a_full_protocol",
    "r05_preflight_stop_no_absolute_floor",
    "r05_preflight_insufficient_sample",
    "r05_preflight_execution_blocked",
}
CANDIDATE_STATUSES = {
    "preflight_pass",
    "preflight_fail_no_absolute_floor",
    "preflight_fail_insufficient_sample",
    "preflight_fail_execution_blocked",
}
FORMULA_TEXT = {
    "low_vol_uptrend_preflight": "\n".join(
        [
            "close_D > ma120_D",
            "ma60_D > ma120_D",
            "ret60_D >= 0",
            "close_D >= ma60_D * 0.98",
            "avg_money20_rank_pct_D >= 0.30",
            "realized_vol60_rank_pct_D <= 0.40",
            "abs(close_D / ma20_D - 1) <= 0.10",
            "atr20_pct_D <= 0.08",
            "money_ratio5_to20_D <= 2.50",
            "abs(ret1_D) <= 0.08",
        ]
    ),
    "base_breakout_vcp_preflight": "\n".join(
        [
            "base_length = 20",
            "base_high_D = max(high[D-20:D-1])",
            "base_low_D = min(low[D-20:D-1])",
            "base_drawdown_pct_D = base_low_D / base_high_D - 1",
            "breakout_ret_pct_D = close_D / base_high_D - 1",
            "pre_base_vol20_D = std(log_return[D-20:D-1])",
            "recent_vol10_D = std(log_return[D-9:D])",
            "vol_contraction_ratio_D = recent_vol10_D / pre_base_vol20_D",
            "base_drawdown_pct_D >= -0.12",
            "breakout_ret_pct_D >= 0.00",
            "breakout_ret_pct_D <= 0.08",
            "vol_contraction_ratio_D <= 0.80",
            "abs(close_D / ma20_D - 1) <= 0.12",
            "atr20_pct_D <= 0.10",
            "money_ratio5_to20_D >= 1.10",
            "money_ratio5_to20_D <= 2.50",
            "avg_money20_rank_pct_D >= 0.30",
        ]
    ),
    "cross_sectional_low_beta_low_vol_preflight": "\n".join(
        [
            "beta120_rank_pct_D <= 0.40",
            "realized_vol60_rank_pct_D <= 0.40",
            "avg_money20_rank_pct_D >= 0.30",
            "close_D >= ma120_D * 0.95",
            "ret20_D >= -0.03",
            "money_ratio5_to20_D <= 2.00",
            "abs(ret1_D) <= 0.08",
            "atr20_pct_D <= 0.08",
        ]
    ),
}


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: str | Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")


def _load_instrument_ranges(path: str | Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for line in topic_path(path).read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        rows.append(
            {
                "instrument_id": parts[0].upper(),
                "instrument_start": pd.Timestamp(parts[1]).normalize(),
                "instrument_end": pd.Timestamp(parts[2]).normalize(),
            }
        )
    return pd.DataFrame(rows)


def _add_trading_days(calendar: pd.DatetimeIndex, date: Any, offset: int) -> pd.Timestamp:
    dt = pd.to_datetime(date, errors="coerce")
    if pd.isna(dt):
        return pd.NaT
    pos = int(calendar.searchsorted(pd.Timestamp(dt).normalize(), side="left"))
    target = pos + offset
    if target < 0 or target >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[target]).normalize()


def _next_trading_day(calendar: pd.DatetimeIndex, date: Any) -> pd.Timestamp:
    dt = pd.to_datetime(date, errors="coerce")
    if pd.isna(dt):
        return pd.NaT
    pos = int(calendar.searchsorted(pd.Timestamp(dt).normalize(), side="right"))
    if pos >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[pos]).normalize()


def _calendar_gap(calendar_index: dict[pd.Timestamp, int], start: Any, end: Any) -> float:
    s = pd.to_datetime(start, errors="coerce")
    e = pd.to_datetime(end, errors="coerce")
    if pd.isna(s) or pd.isna(e):
        return np.nan
    si = calendar_index.get(pd.Timestamp(s).normalize())
    ei = calendar_index.get(pd.Timestamp(e).normalize())
    if si is None or ei is None:
        return np.nan
    return float(ei - si)


def _price_bounds(config: dict[str, Any], calendar: pd.DatetimeIndex) -> tuple[pd.Timestamp, pd.Timestamp]:
    split = config["split"]
    train_start = pd.Timestamp(split["train_start"])
    robustness_end = pd.Timestamp(split["robustness_end"])
    start_pos = max(0, int(calendar.searchsorted(train_start, side="left")) - 140)
    end_pos = min(len(calendar) - 1, int(calendar.searchsorted(robustness_end, side="right")) + 30)
    return pd.Timestamp(calendar[start_pos]).normalize(), pd.Timestamp(calendar[end_pos]).normalize()


def _split_end(split: str, bounds: dict[str, tuple[pd.Timestamp, pd.Timestamp]]) -> pd.Timestamp:
    if split not in bounds:
        return pd.NaT
    return bounds[split][1]


def _rank_pct(frame: pd.DataFrame, value_col: str, output_col: str) -> None:
    frame[output_col] = np.nan
    valid = frame["tradable_instrument_universe_flag"] & pd.to_numeric(frame[value_col], errors="coerce").notna()
    ranked = frame.loc[valid].groupby("trade_date", sort=False)[value_col].rank(method="average", pct=True)
    frame.loc[valid, output_col] = ranked


def _prepare_features(price: pd.DataFrame, instrument_ranges: pd.DataFrame) -> pd.DataFrame:
    out = price.merge(instrument_ranges, on="instrument_id", how="left")
    out["instrument_active_flag"] = (
        out["instrument_start"].notna()
        & out["instrument_end"].notna()
        & (out["trade_date"] >= out["instrument_start"])
        & (out["trade_date"] <= out["instrument_end"])
    )
    out["log_return"] = np.log(out["adjusted_close"] / out["prior_adjusted_close"])
    out.loc[~np.isfinite(out["log_return"]), "log_return"] = np.nan
    out["tradable_instrument_universe_flag"] = (
        out["instrument_active_flag"]
        & out[["adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close", "money", "volume"]].notna().all(axis=1)
        & (out["adjusted_open"] > 0)
        & (out["adjusted_high"] > 0)
        & (out["adjusted_low"] > 0)
        & (out["adjusted_close"] > 0)
        & (out["money"] > 0)
        & (out["volume"] > 0)
        & out["prior_adjusted_close"].notna()
    )
    group = out.groupby("instrument_id", sort=False)
    out["ma20_D"] = group["adjusted_close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    out["ma60_D"] = group["adjusted_close"].transform(lambda s: s.rolling(60, min_periods=60).mean())
    out["ma120_D"] = group["adjusted_close"].transform(lambda s: s.rolling(120, min_periods=120).mean())
    out["ret1_D"] = out["adjusted_close"] / group["adjusted_close"].shift(1) - 1.0
    out["ret20_D"] = out["adjusted_close"] / group["adjusted_close"].shift(20) - 1.0
    out["ret60_D"] = out["adjusted_close"] / group["adjusted_close"].shift(60) - 1.0
    out["realized_vol60_D"] = group["log_return"].transform(lambda s: s.rolling(60, min_periods=60).std(ddof=0))
    out["atr20_pct_D"] = group["true_range"].transform(lambda s: s.rolling(20, min_periods=20).mean()) / out["adjusted_close"]
    out["avg_money20_D"] = group["money"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    out["money5_D"] = group["money"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    out["money_ratio5_to20_D"] = out["money5_D"] / out["avg_money20_D"]
    out["base_high_D"] = group["adjusted_high"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).max())
    out["base_low_D"] = group["adjusted_low"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).min())
    out["base_drawdown_pct_D"] = out["base_low_D"] / out["base_high_D"] - 1.0
    out["breakout_ret_pct_D"] = out["adjusted_close"] / out["base_high_D"] - 1.0
    out["pre_base_vol20_D"] = group["log_return"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).std(ddof=0))
    out["recent_vol10_D"] = group["log_return"].transform(lambda s: s.rolling(10, min_periods=10).std(ddof=0))
    out["vol_contraction_ratio_D"] = out["recent_vol10_D"] / out["pre_base_vol20_D"]
    out.loc[out["pre_base_vol20_D"] <= 0, "vol_contraction_ratio_D"] = np.nan

    market = (
        out.loc[out["tradable_instrument_universe_flag"]]
        .groupby("trade_date", sort=False)["log_return"]
        .mean()
        .rename("market_log_return")
    )
    out = out.merge(market, on="trade_date", how="left")
    out["stock_market_log_return"] = out["log_return"] * out["market_log_return"]
    out["market_log_return_sq"] = out["market_log_return"] * out["market_log_return"]
    group = out.groupby("instrument_id", sort=False)
    mean_xy = group["stock_market_log_return"].transform(lambda s: s.rolling(120, min_periods=120).mean())
    mean_x = group["log_return"].transform(lambda s: s.rolling(120, min_periods=120).mean())
    mean_y = group["market_log_return"].transform(lambda s: s.rolling(120, min_periods=120).mean())
    mean_y2 = group["market_log_return_sq"].transform(lambda s: s.rolling(120, min_periods=120).mean())
    var_y = mean_y2 - mean_y * mean_y
    out["beta120_D"] = (mean_xy - mean_x * mean_y) / var_y
    out.loc[(var_y <= 0) | ~np.isfinite(out["beta120_D"]), "beta120_D"] = np.nan

    _rank_pct(out, "avg_money20_D", "avg_money20_rank_pct_D")
    _rank_pct(out, "realized_vol60_D", "realized_vol60_rank_pct_D")
    _rank_pct(out, "beta120_D", "beta120_rank_pct_D")
    return out


def _formula_frozen(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in config["candidates"]:
        candidate_id = str(item["candidate_id"])
        text = FORMULA_TEXT[candidate_id]
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_family": item["candidate_family"],
                "formula_text": text,
                "formula_hash": _hash_text(text),
                "parameter_json": _canonical_json({"fixed_formula_point": candidate_id}),
                "decision_date_policy": "D_after_close",
                "entry_policy": "next_tradable_open_after_D_with_5d_lag",
                "exit_policy": "close_after_20_trading_days_with_5d_lag_same_split",
                "round_trip_cost_bp": int(config["execution"]["round_trip_cost_bp"]),
                "active_flag": True,
            }
        )
    return pd.DataFrame(rows)


def _candidate_mask(features: pd.DataFrame, candidate_id: str) -> pd.Series:
    f = features
    if candidate_id == "low_vol_uptrend_preflight":
        return (
            f["tradable_instrument_universe_flag"]
            & (f["adjusted_close"] > f["ma120_D"])
            & (f["ma60_D"] > f["ma120_D"])
            & (f["ret60_D"] >= 0)
            & (f["adjusted_close"] >= f["ma60_D"] * 0.98)
            & (f["avg_money20_rank_pct_D"] >= 0.30)
            & (f["realized_vol60_rank_pct_D"] <= 0.40)
            & ((f["adjusted_close"] / f["ma20_D"] - 1.0).abs() <= 0.10)
            & (f["atr20_pct_D"] <= 0.08)
            & (f["money_ratio5_to20_D"] <= 2.50)
            & (f["ret1_D"].abs() <= 0.08)
        )
    if candidate_id == "base_breakout_vcp_preflight":
        return (
            f["tradable_instrument_universe_flag"]
            & (f["base_drawdown_pct_D"] >= -0.12)
            & (f["breakout_ret_pct_D"] >= 0.00)
            & (f["breakout_ret_pct_D"] <= 0.08)
            & (f["vol_contraction_ratio_D"] <= 0.80)
            & ((f["adjusted_close"] / f["ma20_D"] - 1.0).abs() <= 0.12)
            & (f["atr20_pct_D"] <= 0.10)
            & (f["money_ratio5_to20_D"] >= 1.10)
            & (f["money_ratio5_to20_D"] <= 2.50)
            & (f["avg_money20_rank_pct_D"] >= 0.30)
        )
    if candidate_id == "cross_sectional_low_beta_low_vol_preflight":
        return (
            f["tradable_instrument_universe_flag"]
            & (f["beta120_rank_pct_D"] <= 0.40)
            & (f["realized_vol60_rank_pct_D"] <= 0.40)
            & (f["avg_money20_rank_pct_D"] >= 0.30)
            & (f["adjusted_close"] >= f["ma120_D"] * 0.95)
            & (f["ret20_D"] >= -0.03)
            & (f["money_ratio5_to20_D"] <= 2.00)
            & (f["ret1_D"].abs() <= 0.08)
            & (f["atr20_pct_D"] <= 0.08)
        )
    raise ValueError(f"unknown candidate_id: {candidate_id}")


def _build_raw_triggers(
    features: pd.DataFrame,
    formula: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    split = config["split"]
    start = pd.Timestamp(split["train_start"])
    end = pd.Timestamp(split["robustness_end"])
    date_scope = (features["trade_date"] >= start) & (features["trade_date"] <= end)
    frames: list[pd.DataFrame] = []
    next_day = {pd.Timestamp(calendar[idx]).normalize(): pd.Timestamp(calendar[idx + 1]).normalize() for idx in range(len(calendar) - 1)}
    meta = formula.set_index("candidate_id").to_dict("index")
    for item in config["candidates"]:
        candidate_id = str(item["candidate_id"])
        mask = date_scope & _candidate_mask(features, candidate_id)
        part = features.loc[mask, ["instrument_id", "trade_date"]].copy()
        if part.empty:
            continue
        part["candidate_id"] = candidate_id
        part["candidate_family"] = str(item["candidate_family"])
        part["decision_date"] = part["trade_date"]
        part["entry_target_date"] = part["decision_date"].map(next_day)
        part = part[part["entry_target_date"].notna()].copy()
        part["formula_hash"] = meta[candidate_id]["formula_hash"]
        part["event_key"] = [
            _hash_text(f"{candidate_id}|{inst}|{dt.date().isoformat()}|{meta[candidate_id]['formula_hash']}")
            for inst, dt in zip(part["instrument_id"], part["decision_date"], strict=False)
        ]
        frames.append(
            part[
                [
                    "candidate_id",
                    "candidate_family",
                    "instrument_id",
                    "decision_date",
                    "entry_target_date",
                    "event_key",
                    "formula_hash",
                ]
            ]
        )
    if not frames:
        return pd.DataFrame(
            columns=["candidate_id", "candidate_family", "instrument_id", "decision_date", "entry_target_date", "event_key", "formula_hash"]
        )
    return pd.concat(frames, ignore_index=True, sort=False).sort_values(
        ["candidate_id", "instrument_id", "decision_date", "entry_target_date", "event_key"]
    )


def _collapse_events(raw: pd.DataFrame, config: dict[str, Any], calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    window = int(config["execution"]["event_collapse_window_trading_days"])
    kept_rows: list[dict[str, Any]] = []
    if raw.empty:
        audit = pd.DataFrame(
            columns=[
                "candidate_id",
                "candidate_family",
                "instrument_id",
                "raw_trigger_count",
                "kept_event_count",
                "suppressed_by_collapse_count",
                "collapse_window_trading_days",
                "first_raw_trigger_date",
                "last_raw_trigger_date",
                "collapse_audit_status",
                "blocking_reason",
            ]
        )
        return raw.copy(), audit

    for (_candidate_id, _instrument), part in raw.groupby(["candidate_id", "instrument_id"], sort=False):
        current: dict[str, Any] | None = None
        current_count = 0
        window_end = pd.NaT
        for row in part.sort_values(["decision_date", "entry_target_date", "event_key"]).itertuples(index=False):
            decision_date = pd.Timestamp(row.decision_date).normalize()
            if current is None or decision_date > window_end:
                if current is not None:
                    current["raw_trigger_count_in_window"] = current_count
                    current["suppressed_trigger_count_in_window"] = current_count - 1
                    kept_rows.append(current)
                current = row._asdict()
                current["raw_trigger_date"] = decision_date
                current["collapse_anchor_date"] = decision_date
                current["collapse_window_trading_days"] = window
                current["kept_event_flag"] = 1
                current_count = 1
                window_end = _add_trading_days(calendar, decision_date, window)
            else:
                current_count += 1
        if current is not None:
            current["raw_trigger_count_in_window"] = current_count
            current["suppressed_trigger_count_in_window"] = current_count - 1
            kept_rows.append(current)

    kept = pd.DataFrame(kept_rows)
    audit_rows: list[dict[str, Any]] = []
    kept_counts = kept.groupby(["candidate_id", "instrument_id"], sort=False).size().rename("kept_event_count")
    for (candidate_id, instrument_id), part in raw.groupby(["candidate_id", "instrument_id"], sort=False):
        kept_count = int(kept_counts.get((candidate_id, instrument_id), 0))
        raw_count = int(len(part))
        audit_rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_family": str(part["candidate_family"].iloc[0]),
                "instrument_id": instrument_id,
                "raw_trigger_count": raw_count,
                "kept_event_count": kept_count,
                "suppressed_by_collapse_count": raw_count - kept_count,
                "collapse_window_trading_days": window,
                "first_raw_trigger_date": part["decision_date"].min(),
                "last_raw_trigger_date": part["decision_date"].max(),
                "collapse_audit_status": "passed" if raw_count >= kept_count else "failed",
                "blocking_reason": "" if raw_count >= kept_count else "raw_kept_count_mismatch",
            }
        )
    return kept, pd.DataFrame(audit_rows)


def _price_record_map(price: pd.DataFrame) -> dict[str, dict[pd.Timestamp, dict[str, float]]]:
    cols = [
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
        "money",
        "volume",
        "prior_adjusted_close",
    ]
    out: dict[str, dict[pd.Timestamp, dict[str, float]]] = {}
    for row in price[["instrument_id", "trade_date", *cols]].itertuples(index=False):
        inst = str(row.instrument_id).upper()
        date = pd.Timestamp(row.trade_date).normalize()
        values = {col: float(getattr(row, col)) if pd.notna(getattr(row, col)) else np.nan for col in cols}
        out.setdefault(inst, {})[date] = values
    return out


def _candidate_dates(calendar: pd.DatetimeIndex, start: Any, max_lag: int) -> list[pd.Timestamp]:
    dt = pd.to_datetime(start, errors="coerce")
    if pd.isna(dt):
        return []
    pos = int(calendar.searchsorted(pd.Timestamp(dt).normalize(), side="left"))
    return [pd.Timestamp(calendar[idx]).normalize() for idx in range(pos, min(len(calendar), pos + max_lag + 1))]


def _entry_flags(record: dict[str, float] | None) -> tuple[bool, bool, bool]:
    if record is None:
        return False, False, False
    open_price = record.get("adjusted_open", np.nan)
    money = record.get("money", np.nan)
    volume = record.get("volume", np.nan)
    prior_close = record.get("prior_adjusted_close", np.nan)
    available = bool(np.isfinite(open_price) and open_price > 0 and np.isfinite(money) and money > 0 and np.isfinite(volume) and volume > 0)
    limit_up = bool(available and np.isfinite(prior_close) and prior_close > 0 and open_price >= prior_close * 1.095)
    return available, limit_up, bool(available and not limit_up)


def _exit_flags(record: dict[str, float] | None) -> tuple[bool, bool, bool]:
    if record is None:
        return False, False, False
    close_price = record.get("adjusted_close", np.nan)
    money = record.get("money", np.nan)
    volume = record.get("volume", np.nan)
    prior_close = record.get("prior_adjusted_close", np.nan)
    available = bool(np.isfinite(close_price) and close_price > 0 and np.isfinite(money) and money > 0 and np.isfinite(volume) and volume > 0)
    limit_down = bool(available and np.isfinite(prior_close) and prior_close > 0 and close_price <= prior_close * 0.905)
    return available, limit_down, bool(available and not limit_down)


def _execute_events(
    kept: pd.DataFrame,
    price: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bounds = _split_bounds(config)
    calendar_idx = {pd.Timestamp(date).normalize(): idx for idx, date in enumerate(calendar)}
    records = _price_record_map(price)
    entry_lag = int(config["execution"]["max_entry_execution_lag_trading_days"])
    exit_lag = int(config["execution"]["max_exit_execution_lag_trading_days"])
    hold_days = int(config["execution"]["hold_days"])
    cost = float(config["execution"]["round_trip_cost_bp"]) / 10000.0
    event_rows: list[dict[str, Any]] = []
    forward_rows: list[dict[str, Any]] = []

    for row in kept.itertuples(index=False):
        inst = str(row.instrument_id).upper()
        inst_records = records.get(inst, {})
        entry_target = pd.Timestamp(row.entry_target_date).normalize()
        entry_candidates = _candidate_dates(calendar, entry_target, entry_lag)
        target_entry_record = inst_records.get(entry_target)
        target_entry_open, target_entry_limit, target_entry_exec = _entry_flags(target_entry_record)
        actual_entry_date = pd.NaT
        actual_entry_price = np.nan
        entry_limit_up_any = False
        for candidate_date in entry_candidates:
            available, limit_up, executable = _entry_flags(inst_records.get(candidate_date))
            entry_limit_up_any = entry_limit_up_any or limit_up
            if executable:
                actual_entry_date = candidate_date
                actual_entry_price = inst_records[candidate_date]["adjusted_open"]
                break

        split_assignment_date = actual_entry_date if pd.notna(actual_entry_date) else entry_target
        split_name = _split_for_date(split_assignment_date, bounds)
        split_end = _split_end(split_name, bounds)
        path_complete = 0
        path_censor_reason = ""
        exit_target = pd.NaT
        actual_exit_date = pd.NaT
        actual_exit_price = np.nan
        exit_available_flag = False
        exit_limit_down_flag = False
        exit_executable_flag = False
        exit_limit_down_any = False
        hold20_gross = np.nan
        hold20_net = np.nan
        exit_execution_lag = np.nan

        if pd.isna(actual_entry_date):
            path_censor_reason = "entry_unavailable_after_lag"
        elif split_name == "out_of_scope":
            path_censor_reason = "split_assignment_out_of_scope"
        else:
            exit_target = _add_trading_days(calendar, actual_entry_date, hold_days)
            lag_end = _add_trading_days(calendar, exit_target, exit_lag)
            if pd.isna(exit_target) or exit_target > split_end:
                path_censor_reason = "split_boundary_exit_out_of_split"
            else:
                for candidate_date in _candidate_dates(calendar, exit_target, exit_lag):
                    if candidate_date > split_end:
                        break
                    available, limit_down, executable = _exit_flags(inst_records.get(candidate_date))
                    exit_available_flag = exit_available_flag or available
                    exit_limit_down_any = exit_limit_down_any or limit_down
                    if executable:
                        actual_exit_date = candidate_date
                        actual_exit_price = inst_records[candidate_date]["adjusted_close"]
                        exit_executable_flag = True
                        exit_execution_lag = _calendar_gap(calendar_idx, exit_target, actual_exit_date)
                        break
                if pd.notna(actual_exit_date):
                    path_complete = 1
                    hold20_gross = actual_exit_price / actual_entry_price - 1.0
                    hold20_net = hold20_gross - cost
                elif pd.isna(lag_end) or lag_end > split_end:
                    path_censor_reason = "split_boundary_exit_out_of_split"
                else:
                    path_censor_reason = "exit_unavailable_after_lag"
        if path_complete:
            path_censor_reason = ""

        entry_execution_lag = _calendar_gap(calendar_idx, entry_target, actual_entry_date)
        common = {
            "candidate_id": row.candidate_id,
            "candidate_family": row.candidate_family,
            "instrument_id": inst,
            "event_key": row.event_key,
            "split": split_name,
            "decision_date": row.decision_date,
            "entry_target_date": entry_target,
            "split_assignment_date": split_assignment_date,
            "formula_hash": row.formula_hash,
            "membership_flag": True,
            "missing_feature_flag": 0,
            "raw_trigger_date": row.raw_trigger_date,
            "collapse_anchor_date": row.collapse_anchor_date,
            "collapse_window_trading_days": row.collapse_window_trading_days,
            "raw_trigger_count_in_window": int(row.raw_trigger_count_in_window),
            "suppressed_trigger_count_in_window": int(row.suppressed_trigger_count_in_window),
            "kept_event_flag": 1,
            "entry_open_available_flag": bool(target_entry_open),
            "entry_limit_up_inferred_flag": bool(target_entry_limit),
            "entry_executable_flag": bool(target_entry_exec),
            "actual_entry_execution_date": actual_entry_date,
            "entry_execution_lag_trading_days": entry_execution_lag,
            "path_censor_reason": path_censor_reason,
            "entry_limit_up_blocked_any_flag": entry_limit_up_any,
        }
        event_rows.append(common)
        forward_rows.append(
            {
                "candidate_id": row.candidate_id,
                "candidate_family": row.candidate_family,
                "instrument_id": inst,
                "event_key": row.event_key,
                "split": split_name,
                "decision_date": row.decision_date,
                "actual_entry_execution_date": actual_entry_date,
                "actual_entry_price": actual_entry_price,
                "exit_target_date": exit_target,
                "actual_exit_date": actual_exit_date,
                "actual_exit_price": actual_exit_price,
                "split_assignment_date": split_assignment_date,
                "split_end_date": split_end,
                "exit_available_flag": bool(exit_available_flag),
                "exit_limit_down_inferred_flag": bool(exit_limit_down_flag or exit_limit_down_any),
                "exit_executable_flag": bool(exit_executable_flag),
                "exit_execution_lag_trading_days": exit_execution_lag,
                "hold20_gross_return": hold20_gross,
                "hold20_net_return": hold20_net,
                "path_complete_flag": int(path_complete),
                "path_censor_reason": path_censor_reason,
                "entry_limit_up_blocked_any_flag": bool(entry_limit_up_any),
                "exit_limit_down_blocked_any_flag": bool(exit_limit_down_any),
            }
        )

    event_panel = pd.DataFrame(event_rows)
    forward_panel = pd.DataFrame(forward_rows)
    return event_panel, forward_panel


def _split_return_summary(event_panel: pd.DataFrame, forward_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in config["candidates"]:
        candidate_id = str(item["candidate_id"])
        candidate_family = str(item["candidate_family"])
        for split in SPLITS:
            events = event_panel[event_panel["candidate_id"].eq(candidate_id) & event_panel["split"].eq(split)]
            paths = forward_panel[forward_panel["candidate_id"].eq(candidate_id) & forward_panel["split"].eq(split)]
            complete = paths[paths["path_complete_flag"].eq(1)].copy()
            returns = pd.to_numeric(complete["hold20_net_return"], errors="coerce").dropna()
            event_count = int(len(paths))
            complete_count = int(len(complete))
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_family": candidate_family,
                    "split": split,
                    "event_count": event_count,
                    "raw_trigger_count": int(pd.to_numeric(events.get("raw_trigger_count_in_window", pd.Series(dtype=float)), errors="coerce").sum()),
                    "suppressed_by_collapse_count": int(pd.to_numeric(events.get("suppressed_trigger_count_in_window", pd.Series(dtype=float)), errors="coerce").sum()),
                    "complete_event_count": complete_count,
                    "complete_event_share": _safe_div(complete_count, event_count),
                    "hold20_net_mean": float(returns.mean()) if len(returns) else np.nan,
                    "hold20_net_median": float(returns.median()) if len(returns) else np.nan,
                    "hold20_net_p10": _quantile(returns, 0.10),
                    "loss_le_5_rate": _safe_div(int((returns <= -0.05).sum()), len(returns)),
                }
            )
    return pd.DataFrame(rows)


def _execution_audit(forward_panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    min_complete_share = float(config["thresholds"]["validation_complete_event_share_min"])
    rows: list[dict[str, Any]] = []
    for item in config["candidates"]:
        candidate_id = str(item["candidate_id"])
        candidate_family = str(item["candidate_family"])
        for split in SPLITS:
            part = forward_panel[forward_panel["candidate_id"].eq(candidate_id) & forward_panel["split"].eq(split)]
            event_count = int(len(part))
            complete = int(part["path_complete_flag"].eq(1).sum()) if event_count else 0
            complete_share = _safe_div(complete, event_count)
            status = "passed" if event_count and complete_share >= min_complete_share else ("insufficient_sample" if not event_count else "execution_blocked")
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_family": candidate_family,
                    "split": split,
                    "event_count": event_count,
                    "entry_unavailable_after_lag_count": int(part["path_censor_reason"].eq("entry_unavailable_after_lag").sum()) if event_count else 0,
                    "entry_limit_up_block_count": int(part["entry_limit_up_blocked_any_flag"].sum()) if event_count else 0,
                    "exit_unavailable_after_lag_count": int(part["path_censor_reason"].eq("exit_unavailable_after_lag").sum()) if event_count else 0,
                    "exit_limit_down_block_count": int(part["exit_limit_down_blocked_any_flag"].sum()) if event_count else 0,
                    "split_boundary_exit_out_of_split_count": int(part["path_censor_reason"].eq("split_boundary_exit_out_of_split").sum()) if event_count else 0,
                    "complete_event_count": complete,
                    "complete_event_share": complete_share,
                    "execution_audit_status": status,
                    "blocking_reason": "" if status == "passed" else status,
                }
            )
    return pd.DataFrame(rows)


def _gate_audit(summary: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    thresholds = config["thresholds"]
    rows: list[dict[str, Any]] = []
    validation = summary[summary["split"].eq("validation")].set_index("candidate_id")
    for item in config["candidates"]:
        candidate_id = str(item["candidate_id"])
        candidate_family = str(item["candidate_family"])
        row = validation.loc[candidate_id] if candidate_id in validation.index else pd.Series(dtype=object)
        event_count = int(row.get("event_count", 0) or 0)
        complete_share = float(row.get("complete_event_share", 0) or 0)
        mean = float(row.get("hold20_net_mean", np.nan))
        median = float(row.get("hold20_net_median", np.nan))
        p10 = float(row.get("hold20_net_p10", np.nan))
        if event_count < int(thresholds["validation_event_count_min"]):
            status = "preflight_fail_insufficient_sample"
            reason = "validation_event_count_below_min"
        elif complete_share < float(thresholds["validation_complete_event_share_min"]):
            status = "preflight_fail_execution_blocked"
            reason = "validation_complete_event_share_below_min"
        elif (
            mean > float(thresholds["validation_hold20_net_mean_min"])
            and median > float(thresholds["validation_hold20_net_median_min"])
            and p10 > float(thresholds["validation_hold20_net_p10_min"])
        ):
            status = "preflight_pass"
            reason = ""
        else:
            status = "preflight_fail_no_absolute_floor"
            reason = "validation_absolute_floor_failed"
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_family": candidate_family,
                "validation_event_count": event_count,
                "validation_complete_event_share": complete_share,
                "validation_hold20_net_mean": mean,
                "validation_hold20_net_median": median,
                "validation_hold20_net_p10": p10,
                "validation_loss_le_5_rate": float(row.get("loss_le_5_rate", np.nan)),
                "preflight_gate_status": status,
                "blocking_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def _final_decision(gate: pd.DataFrame) -> tuple[str, str, list[str], list[str]]:
    passed = gate[gate["preflight_gate_status"].eq("preflight_pass")]
    if not passed.empty:
        return (
            "r05_preflight_go_r05a_full_protocol",
            "",
            passed["candidate_id"].astype(str).tolist(),
            passed["candidate_family"].astype(str).tolist(),
        )
    if gate["preflight_gate_status"].eq("preflight_fail_insufficient_sample").all():
        return "r05_preflight_insufficient_sample", "all_candidates_insufficient_validation_sample", [], []
    if gate["preflight_gate_status"].eq("preflight_fail_execution_blocked").any():
        return "r05_preflight_execution_blocked", "candidate_execution_complete_share_below_min", [], []
    return "r05_preflight_stop_no_absolute_floor", "no_candidate_validation_absolute_floor", [], []


def _report_text(final: pd.DataFrame, summary: pd.DataFrame, gate: pd.DataFrame, execution: pd.DataFrame) -> str:
    decision = str(final.iloc[0]["final_decision"]) if not final.empty else ""
    lines = [
        "# R05 Preflight 快速可行性最终报告",
        "",
        "R05 Preflight 是低成本方向筛查，只判断 fixed primitive 是否值得进入完整 R05a 协议；本报告不批准任何可交易规则。",
        "",
        f"Final decision: `{decision}`",
        "",
        "## Candidate Gate",
        "",
        "| candidate_id | family | validation_events | complete_share | mean | median | p10 | status |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in gate.itertuples(index=False):
        lines.append(
            f"| `{row.candidate_id}` | {row.candidate_family} | {int(row.validation_event_count)} | "
            f"{row.validation_complete_event_share:.2%} | {row.validation_hold20_net_mean:.2%} | "
            f"{row.validation_hold20_net_median:.2%} | {row.validation_hold20_net_p10:.2%} | `{row.preflight_gate_status}` |"
        )
    lines += [
        "",
        "## Split Return Summary",
        "",
        "| candidate_id | split | events | raw | suppressed | complete | mean | median | p10 | loss<=-5 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.sort_values(["candidate_id", "split"]).itertuples(index=False):
        lines.append(
            f"| `{row.candidate_id}` | {row.split} | {int(row.event_count)} | {int(row.raw_trigger_count)} | "
            f"{int(row.suppressed_by_collapse_count)} | {int(row.complete_event_count)} | "
            f"{row.hold20_net_mean:.2%} | {row.hold20_net_median:.2%} | {row.hold20_net_p10:.2%} | {row.loss_le_5_rate:.2%} |"
        )
    lines += [
        "",
        "## Execution Audit",
        "",
        "| candidate_id | split | events | entry_unavailable | exit_unavailable | split_boundary | complete_share | status |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in execution.sort_values(["candidate_id", "split"]).itertuples(index=False):
        lines.append(
            f"| `{row.candidate_id}` | {row.split} | {int(row.event_count)} | "
            f"{int(row.entry_unavailable_after_lag_count)} | {int(row.exit_unavailable_after_lag_count)} | "
            f"{int(row.split_boundary_exit_out_of_split_count)} | {row.complete_event_share:.2%} | `{row.execution_audit_status}` |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- `preflight_pass` 只表示该 candidate 有足够 validation floor 进入完整 R05a protocol。",
        "- 当前未通过 preflight 的 candidate 应保持 R05a blocked，除非后续有独立 sample extension 或 execution repair requirement 改变上游证据。",
        "",
    ]
    return "\n".join(lines)


def _empty_outputs(config: dict[str, Any], reports_dir: Path, cache_dir: Path, final_decision: str, reason: str) -> pd.DataFrame:
    formula = _formula_frozen(config)
    write_csv(formula, reports_dir / "r05_preflight_candidate_formula_frozen.csv")
    final = pd.DataFrame(
        [
            {
                "requirement_id": config["requirement_id"],
                "final_decision": final_decision,
                "candidate_pass_count": 0,
                "passed_candidate_ids": "",
                "passed_candidate_families": "",
                "blocking_reason": reason,
                "allowed_next_requirement": "blocked_until_required_input_repaired",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    write_csv(final, reports_dir / "r05_preflight_final_decision.csv")
    _write_parquet(pd.DataFrame(), cache_dir / "r05_preflight_candidate_event_panel.parquet")
    _write_parquet(pd.DataFrame(), cache_dir / "r05_preflight_forward_return_panel.parquet")
    return final


def _load_upstream_state(config: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    validation_path = topic_path(config["upstream_r04e"]["validation"])
    final_path = topic_path(config["upstream_r04e"]["final_decision"])
    if not validation_path.exists() or not final_path.exists():
        return False, "missing_r04e_upstream_artifact", {}
    validation = _read_json(validation_path)
    final = pd.read_csv(final_path)
    final_decision = "" if final.empty else str(final.iloc[0].get("final_decision", ""))
    state = {
        "r04e_validation_status": validation.get("validation_status", ""),
        "r04e_validation_final_decision": validation.get("final_decision", ""),
        "r04e_csv_final_decision": final_decision,
    }
    if state["r04e_validation_status"] != "passed":
        return False, "r04e_validation_not_passed", state
    if state["r04e_csv_final_decision"] != "r04e_union_not_viable_validation":
        return False, "r04e_final_decision_not_frozen", state
    return True, "", state


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for directory in [cache_dir, reports_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    upstream_ok, upstream_reason, upstream_state = _load_upstream_state(config)
    if not upstream_ok:
        final = _empty_outputs(config, reports_dir, cache_dir, "r05_preflight_stop_no_absolute_floor", upstream_reason)
        manifest = {
            "requirement_id": config["requirement_id"],
            "requirement_path": config["requirement_path"],
            "config_path": relpath(topic_path(config_path)),
            "output_root": relpath(output_root),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "split_definition_hash": _hash_text(_canonical_json(config["split"])),
            "price_provider_hash": "",
            "upstream_artifact_hashes_json": _canonical_json({}),
            "formula_hashes_json": _canonical_json({}),
            "final_decision": str(final.iloc[0]["final_decision"]),
            "artifact_hashes_json": _canonical_json(_artifact_hashes(list(reports_dir.glob("*")) + list(cache_dir.glob("*")))),
            "upstream_state": upstream_state,
        }
        write_json(manifest, manifests_dir / "r05_preflight_alpha_pool_quick_feasibility_manifest.json")
        return manifest

    calendar = _load_calendar(config["price_provider"]["calendar_source_path"])
    instrument_ranges = _load_instrument_ranges(config["price_provider"]["instrument_source_path"])
    instruments = sorted(instrument_ranges["instrument_id"].astype(str).str.upper().unique().tolist())
    start, end = _price_bounds(config, calendar)
    print(f"loading price panel for {len(instruments)} instruments from {start.date()} to {end.date()}", flush=True)
    price = _load_price_panel(config, instruments, start, end, calendar)
    print("building as-of features", flush=True)
    features = _prepare_features(price, instrument_ranges)
    formula = _formula_frozen(config)
    raw = _build_raw_triggers(features, formula, config, calendar)
    print(f"raw triggers: {len(raw):,}", flush=True)
    kept, collapse_audit = _collapse_events(raw, config, calendar)
    print(f"kept events after collapse: {len(kept):,}", flush=True)
    event_panel, forward_panel = _execute_events(kept, price, config, calendar)
    summary = _split_return_summary(event_panel, forward_panel, config)
    execution = _execution_audit(forward_panel, config)
    gate = _gate_audit(summary, config)
    final_decision, blocking_reason, passed_ids, passed_families = _final_decision(gate)
    allowed_next = (
        "ep4/requirement_05a_alpha_pool_discovery_protocol_v1.md"
        if final_decision == "r05_preflight_go_r05a_full_protocol"
        else (
            "sample_extension_only"
            if final_decision == "r05_preflight_insufficient_sample"
            else ("execution_model_repair_only" if final_decision == "r05_preflight_execution_blocked" else "sleeve_allocator_direction_requirement")
        )
    )
    final = pd.DataFrame(
        [
            {
                "requirement_id": config["requirement_id"],
                "final_decision": final_decision,
                "candidate_pass_count": len(passed_ids),
                "passed_candidate_ids": ",".join(passed_ids),
                "passed_candidate_families": ",".join(passed_families),
                "blocking_reason": blocking_reason,
                "allowed_next_requirement": allowed_next,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )

    write_csv(formula, reports_dir / "r05_preflight_candidate_formula_frozen.csv")
    write_csv(summary, reports_dir / "r05_preflight_split_return_summary.csv")
    write_csv(execution, reports_dir / "r05_preflight_execution_audit.csv")
    write_csv(collapse_audit, reports_dir / "r05_preflight_event_collapse_audit.csv")
    write_csv(gate, reports_dir / "r05_preflight_gate_audit.csv")
    write_csv(final, reports_dir / "r05_preflight_final_decision.csv")
    (reports_dir / "r05_preflight_alpha_pool_quick_feasibility_final_report.md").write_text(
        _report_text(final, summary, gate, execution),
        encoding="utf-8",
    )
    _write_parquet(event_panel, cache_dir / "r05_preflight_candidate_event_panel.parquet")
    _write_parquet(forward_panel, cache_dir / "r05_preflight_forward_return_panel.parquet")

    artifact_paths = (
        list(cache_dir.glob("*.parquet"))
        + list(reports_dir.glob("*.csv"))
        + [reports_dir / "r05_preflight_alpha_pool_quick_feasibility_final_report.md"]
    )
    formula_hashes = dict(zip(formula["candidate_id"], formula["formula_hash"], strict=False))
    upstream_hashes = {
        config["upstream_r04e"]["validation"]: _hash_file(topic_path(config["upstream_r04e"]["validation"])),
        config["upstream_r04e"]["final_decision"]: _hash_file(topic_path(config["upstream_r04e"]["final_decision"])),
    }
    validator_path = EP4_DIR / "scripts" / "validate_r05_preflight_alpha_pool_quick_feasibility.py"
    manifest = {
        "requirement_id": config["requirement_id"],
        "requirement_path": config["requirement_path"],
        "config_path": relpath(topic_path(config_path)),
        "config_hash": _hash_file(topic_path(config_path)),
        "runner_hash": _hash_file(Path(__file__).resolve()),
        "validator_hash": _hash_file(validator_path) if validator_path.exists() else "",
        "output_root": relpath(output_root),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "split_definition_hash": _hash_text(_canonical_json(config["split"])),
        "price_provider_hash": _price_source_hash(config, instruments),
        "upstream_artifact_hashes_json": _canonical_json(upstream_hashes),
        "formula_hashes_json": _canonical_json(formula_hashes),
        "final_decision": final_decision,
        "candidate_pass_count": len(passed_ids),
        "passed_candidate_ids": passed_ids,
        "passed_candidate_families": passed_families,
        "artifact_hashes_json": _canonical_json(_artifact_hashes(artifact_paths)),
        "upstream_state": upstream_state,
    }
    write_json(manifest, manifests_dir / "r05_preflight_alpha_pool_quick_feasibility_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    manifest = run(args.config)
    print(
        json.dumps(
            {
                "final_decision": manifest.get("final_decision"),
                "candidate_pass_count": manifest.get("candidate_pass_count"),
                "passed_candidate_families": manifest.get("passed_candidate_families"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

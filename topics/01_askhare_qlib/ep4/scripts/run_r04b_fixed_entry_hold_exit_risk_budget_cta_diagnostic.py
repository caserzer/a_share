#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
FINAL_DECISIONS = {
    "blocked_upstream_r04_validation_failed",
    "blocked_missing_required_input",
    "blocked_gate0_metric_replay_spec_failed",
    "blocked_policy_matrix_invalid",
    "blocked_selection_leakage_detected",
    "r04b_no_policy_family_passed_validation",
    "r04b_policy_not_robust_hold_exit_diagnostic_complete",
    "r04b_hold_exit_risk_budget_candidate_passed_diagnostic_only",
}
MARKET_SIZING_KNOWN = {
    "downtrend_low_breadth",
    "normal_range",
    "normal_uptrend",
    "missing_market_regime",
    "post_drawdown_rebound",
    "post_drawdown_rebound_hypothesis",
}


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_json(value: Any) -> str:
    return _hash_text(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")


def _safe_div(numerator: float, denominator: float) -> float:
    if not np.isfinite(denominator) or denominator == 0:
        return np.nan
    if not np.isfinite(numerator):
        return np.nan
    return float(numerator) / float(denominator)


def _to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _bool_series(values: pd.Series, default: bool = False) -> pd.Series:
    return values.map(lambda value: default if pd.isna(value) else _to_bool(value)).astype(bool)


def _quantile(values: pd.Series, q: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.quantile(q)) if len(clean) else np.nan


def _wilson(success: int, denominator: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if denominator <= 0:
        return np.nan, np.nan
    phat = success / denominator
    denom = 1 + z * z / denominator
    center = (phat + z * z / (2 * denominator)) / denom
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * denominator)) / denominator) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def _date_str(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(ts) else ts.date().isoformat()


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _load_calendar(path: str | Path) -> pd.DatetimeIndex:
    resolved = topic_path(path)
    values = [line.strip() for line in resolved.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values).normalize()).sort_values()


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
    dt = dt.normalize()
    for split, (start, end) in bounds.items():
        if start <= dt <= end:
            return split
    return "out_of_scope"


def _add_trading_days(calendar: pd.DatetimeIndex, date: pd.Timestamp, offset: int) -> pd.Timestamp:
    pos = int(calendar.searchsorted(date, side="left"))
    target = pos + offset
    if target < 0 or target >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[target])


def _artifact_hashes(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        if path.exists() and path.is_file():
            out[relpath(path)] = _hash_file(path)
    return out


def _price_source_hash(config: dict[str, Any], instruments: list[str]) -> str:
    provider = topic_path(config["price_provider"]["price_source_path"])
    required = [field.strip("$") for field in config["price_provider"]["required_qlib_fields"]]
    digest = hashlib.sha256()
    for instrument in sorted({i.lower() for i in instruments}):
        for field in required:
            path = provider / "features" / instrument / f"{field}.day.bin"
            if path.exists():
                digest.update(str(path.relative_to(provider)).encode())
                digest.update(_hash_file(path).encode())
            else:
                digest.update(f"missing:{instrument}:{field}".encode())
    return digest.hexdigest()


def _load_price_panel(config: dict[str, Any], instruments: list[str], start: pd.Timestamp, end: pd.Timestamp, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(topic_path(config["price_provider"]["price_source_path"])), region=REG_CN)
    fields = config["price_provider"]["required_qlib_fields"]
    data = D.features(
        sorted(set(instruments)),
        fields,
        start_time=start.date().isoformat(),
        end_time=end.date().isoformat(),
        freq="day",
    )
    if data.empty:
        raise RuntimeError("Qlib price provider returned empty frame")
    rename = {
        "$open": "adjusted_open",
        "$high": "adjusted_high",
        "$low": "adjusted_low",
        "$close": "adjusted_close",
        "$volume": "volume",
        "$money": "money",
        "$factor": "factor",
    }
    out = data.rename(columns=rename).reset_index().rename(columns={"instrument": "instrument_id", "datetime": "trade_date"})
    out["instrument_id"] = out["instrument_id"].astype(str).str.upper()
    out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.normalize()
    cal_map = {pd.Timestamp(date): idx for idx, date in enumerate(calendar)}
    out["calendar_index"] = out["trade_date"].map(cal_map)
    out = out[out["calendar_index"].notna()].copy()
    out["calendar_index"] = out["calendar_index"].astype(int)
    for col in ["adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close", "volume", "money", "factor"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    clean_ohlc = (
        (out["adjusted_open"] > 0)
        & (out["adjusted_high"] > 0)
        & (out["adjusted_low"] > 0)
        & (out["adjusted_close"] > 0)
        & (out["volume"] > 0)
        & (out["money"] > 0)
    )
    out["suspended_or_dirty_bar"] = ~clean_ohlc
    out["adjustment_policy"] = config["price_provider"]["adjustment_policy"]
    out = out.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)
    group = out.groupby("instrument_id", sort=False)
    out["prior_adjusted_close"] = group["adjusted_close"].shift(1)
    out["daily_simple_return"] = out["adjusted_close"] / out["prior_adjusted_close"] - 1.0
    out.loc[~np.isfinite(out["daily_simple_return"]), "daily_simple_return"] = np.nan
    prev_close = out["prior_adjusted_close"]
    out["true_range"] = np.maximum.reduce(
        [
            (out["adjusted_high"] - out["adjusted_low"]).to_numpy(float),
            (out["adjusted_high"] - prev_close).abs().to_numpy(float),
            (out["adjusted_low"] - prev_close).abs().to_numpy(float),
        ]
    )
    out["ATR_14_asof_t"] = group["true_range"].transform(lambda s: s.rolling(14, min_periods=14).mean())
    out["stock_realized_vol_20d_asof_entry"] = group["daily_simple_return"].transform(
        lambda s: s.shift(1).rolling(20, min_periods=20).std(ddof=0)
    )
    for span in [10, 20]:
        out[f"EMA_{span}_t"] = group["adjusted_close"].transform(lambda s, span=span: s.ewm(span=span, adjust=False, min_periods=span).mean())
    return out


def _exit_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    grid = config["policy_grid"]["exits"]
    specs: list[dict[str, Any]] = [{"exit_rule_id": "no_exit", "exit_rule_family_id": "no_exit", "params": {}, "is_sensitivity": False}]
    for stop in grid["fixed_stop"]["stop_loss_pct"]:
        specs.append(
            {
                "exit_rule_id": f"fixed_stop_{abs(int(round(stop * 100)))}pct",
                "exit_rule_family_id": "fixed_stop",
                "params": {"stop_loss_pct": float(stop)},
                "is_sensitivity": False,
            }
        )
    for days in grid["time_stop"]["time_stop_days"]:
        specs.append(
            {
                "exit_rule_id": f"time_stop_{int(days)}d",
                "exit_rule_family_id": "time_stop",
                "params": {"time_stop_days": int(days)},
                "is_sensitivity": False,
            }
        )
    for activation in grid["break_even_after_gain"]["activation_gain_pct"]:
        specs.append(
            {
                "exit_rule_id": f"break_even_after_gain_{int(round(activation * 100))}pct",
                "exit_rule_family_id": "break_even_after_gain",
                "params": {"activation_gain_pct": float(activation)},
                "is_sensitivity": False,
            }
        )
    for activation in grid["profit_lock_after_gain"]["activation_gain_pct"]:
        for locked in grid["profit_lock_after_gain"]["locked_gain_pct"]:
            specs.append(
                {
                    "exit_rule_id": f"profit_lock_after_gain_{int(round(activation * 100))}pct_lock_{int(round(locked * 100))}pct",
                    "exit_rule_family_id": "profit_lock_after_gain",
                    "params": {"activation_gain_pct": float(activation), "locked_gain_pct": float(locked)},
                    "is_sensitivity": False,
                }
            )
    for activation in grid["ATR_trailing"]["min_activation_gain_pct_for_selection"]:
        for k_atr in grid["ATR_trailing"]["k_atr"]:
            specs.append(
                {
                    "exit_rule_id": f"ATR_trailing_k{k_atr:g}_activation_{activation:g}",
                    "exit_rule_family_id": "ATR_trailing",
                    "params": {"k_atr": float(k_atr), "min_activation_gain_pct": float(activation)},
                    "is_sensitivity": False,
                }
            )
    for activation in grid["ATR_trailing"]["min_activation_gain_pct_sensitivity_only"]:
        for k_atr in grid["ATR_trailing"]["k_atr"]:
            specs.append(
                {
                    "exit_rule_id": f"ATR_trailing_k{k_atr:g}_activation_{activation:g}_sensitivity",
                    "exit_rule_family_id": "ATR_trailing",
                    "params": {"k_atr": float(k_atr), "min_activation_gain_pct": float(activation)},
                    "is_sensitivity": True,
                }
            )
    for window in grid["EMA_trailing"]["ema_window"]:
        for confirm in grid["EMA_trailing"]["confirm_days"]:
            specs.append(
                {
                    "exit_rule_id": f"EMA_trailing_{int(window)}d_confirm_{int(confirm)}d",
                    "exit_rule_family_id": "EMA_trailing",
                    "params": {"ema_window": int(window), "confirm_days": int(confirm)},
                    "is_sensitivity": False,
                }
            )
    return specs


def _rule_formula(family: str, params: dict[str, Any], max_holding_days: int) -> str:
    if family == "no_exit":
        return f"signal=close_offset_{max_holding_days};execution=next_open"
    if family == "fixed_stop":
        return f"first close_return_from_entry <= {params['stop_loss_pct']} else max_hold"
    if family == "time_stop":
        return f"signal=close_offset_{params['time_stop_days']};execution=next_open"
    if family == "break_even_after_gain":
        return f"activate close_return >= {params['activation_gain_pct']}; stop_floor=0"
    if family == "profit_lock_after_gain":
        return f"activate close_return >= {params['activation_gain_pct']}; stop_floor={params['locked_gain_pct']}"
    if family == "ATR_trailing":
        return f"trail=max(prev,highest_close-k_atr({params['k_atr']})*ATR14);activation={params['min_activation_gain_pct']}"
    if family == "EMA_trailing":
        return f"exit close < EMA{params['ema_window']} for {params['confirm_days']} consecutive closes"
    return family


def _build_policy_matrix(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    base_policy_id = config["baseline"]["hold120_baseline_policy_id"]
    validation_ref = config["baseline"]["validation_family_reference_set_id"]
    for hold in config["policy_grid"]["holds"]:
        hold_rule_id = hold["hold_rule_id"]
        max_holding_days = int(hold["max_holding_days"])
        for sizing_rule_id in config["policy_grid"]["sizing"].keys():
            for spec in _exit_specs(config):
                params = dict(spec["params"])
                family = spec["exit_rule_family_id"]
                invalid_reason = ""
                if family == "profit_lock_after_gain" and params["locked_gain_pct"] >= params["activation_gain_pct"]:
                    invalid_reason = "locked_gain_pct_ge_activation_gain_pct"
                if family == "time_stop" and int(params["time_stop_days"]) >= max_holding_days:
                    invalid_reason = "time_stop_days_ge_max_holding_days"
                policy_family_id = f"{hold_rule_id}|{family}|{sizing_rule_id}"
                parameter_values_json = _canonical_json(params)
                parameter_set_id = _hash_text(f"{family}|{parameter_values_json}")[:16]
                param_suffix = "no_params" if not params else "_".join(f"{k}={v}" for k, v in sorted(params.items()))
                policy_id = f"{hold_rule_id}|{spec['exit_rule_id']}|{sizing_rule_id}|{param_suffix}"
                if hold_rule_id == "hold_120d" and family == "no_exit" and sizing_rule_id == "fixed_size":
                    policy_id = base_policy_id
                formulas = {
                    "entry": "R04 baseline_A episode-first-trigger next-open",
                    "hold": f"max_holding_days={max_holding_days}",
                    "exit": _rule_formula(family, params, max_holding_days),
                    "sizing": sizing_rule_id,
                    "cost": config["cost_model"],
                }
                rows.append(
                    {
                        "policy_id": policy_id,
                        "hold_rule_id": hold_rule_id,
                        "max_holding_days": max_holding_days,
                        "exit_rule_id": spec["exit_rule_id"],
                        "exit_rule_family_id": family,
                        "sizing_rule_id": sizing_rule_id,
                        "policy_family_id": policy_family_id,
                        "parameter_set_id": parameter_set_id,
                        "parameter_values_json": parameter_values_json,
                        "is_baseline_policy": policy_id == base_policy_id,
                        "is_train_selectable": (not invalid_reason) and (not spec["is_sensitivity"]),
                        "is_validation_selectable": (not invalid_reason) and (not spec["is_sensitivity"]),
                        "is_sensitivity_policy": bool(spec["is_sensitivity"]),
                        "parameter_reference_group_id": policy_family_id,
                        "validation_family_reference_set_id": validation_ref,
                        "selection_family_key": policy_family_id,
                        "invalid_policy_reason": invalid_reason,
                        "entry_rule_text": formulas["entry"],
                        "hold_rule_formula": formulas["hold"],
                        "exit_rule_formula": formulas["exit"],
                        "sizing_rule_formula": sizing_rule_id,
                        "cost_model_id": config["cost_model"]["cost_model_id"],
                        "formula_hash": _hash_json(formulas),
                    }
                )
    return pd.DataFrame(rows)


def _load_candidates(config: dict[str, Any], price: pd.DataFrame, calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate = pd.read_parquet(topic_path(config["upstream_r04"]["candidate_panel"]))
    regime = pd.read_parquet(topic_path(config["upstream_r04"]["regime_join_panel"]))
    keep = (
        candidate["r04_inclusion_status"].astype(str).eq(config["candidate"]["required_inclusion_status"])
        & candidate["split"].astype(str).isin(SPLITS)
        & candidate["episode_entry_valid"].astype(bool)
        & candidate["entry_execution_date"].notna()
        & (pd.to_numeric(candidate["entry_price"], errors="coerce") > 0)
    )
    base = candidate.loc[keep].copy()
    base["instrument_id"] = base["instrument_id"].astype(str).str.upper()
    base["entry_execution_date"] = pd.to_datetime(base["entry_execution_date"]).dt.normalize()
    base["anchor_signal_date"] = pd.to_datetime(base["anchor_signal_date"]).dt.normalize()
    base["entry_price"] = pd.to_numeric(base["entry_price"], errors="coerce")
    regime = regime.loc[regime["denominator_scope"].astype(str).eq("rps_episode_primary")].copy()
    regime = regime[
        [
            "r04_candidate_event_id",
            "market_regime_bucket",
            "industry_regime_bucket",
            "industry_target_key",
            "stock_rps_60d",
            "stock_rps_minus_industry_rps_60d",
        ]
    ].drop_duplicates("r04_candidate_event_id")
    base = base.merge(regime, on="r04_candidate_event_id", how="left")
    base["market_regime_bucket"] = base["market_regime_bucket"].fillna("missing_market_regime")
    base["industry_regime_bucket"] = base["industry_regime_bucket"].fillna("missing_industry")
    base["market_regime_bucket_for_sizing"] = np.where(
        base["market_regime_bucket"].isin(MARKET_SIZING_KNOWN),
        base["market_regime_bucket"],
        "other_unrecognized_market_regime",
    )
    cal_map = {pd.Timestamp(date): idx for idx, date in enumerate(calendar)}
    base["entry_calendar_index"] = base["entry_execution_date"].map(cal_map)
    entry_price = price[
        [
            "instrument_id",
            "trade_date",
            "adjusted_open",
            "volume",
            "money",
            "suspended_or_dirty_bar",
            "calendar_index",
        ]
    ].rename(columns={"trade_date": "entry_execution_date", "adjusted_open": "r04b_replay_entry_price"})
    base = base.merge(entry_price, on=["instrument_id", "entry_execution_date"], how="left")
    base["r04_source_entry_price"] = base["entry_price"]
    base["entry_price_rel_diff"] = (base["r04b_replay_entry_price"] / base["r04_source_entry_price"] - 1.0).abs()
    executable = (
        (base["r04b_replay_entry_price"] > 0)
        & (base["volume"] > 0)
        & (base["money"] > 0)
        & (~_bool_series(base["suspended_or_dirty_bar"], default=True))
    )
    tol = float(config["candidate"]["max_entry_price_rel_diff"])
    base["entry_price_reconciliation_status"] = np.where(
        base["r04b_replay_entry_price"].isna(),
        "missing_r04b_entry_price",
        np.where(base["entry_price_rel_diff"] > tol, "failed_price_mismatch", "passed"),
    )
    base["entry_valid_r04b"] = executable & base["entry_price_reconciliation_status"].eq("passed")
    base = base.drop(columns=["volume", "money", "suspended_or_dirty_bar", "calendar_index"], errors="ignore")

    rec_rows: list[dict[str, Any]] = []
    for split in SPLITS:
        raw_split = candidate.loc[candidate["split"].astype(str).eq(split)]
        part = base.loc[base["split"].astype(str).eq(split)]
        mismatch = int(part["entry_price_reconciliation_status"].eq("failed_price_mismatch").sum())
        rec_rows.append(
            {
                "split": split,
                "r04_candidate_rows": int(len(raw_split)),
                "included_rows": int(raw_split["r04_inclusion_status"].astype(str).eq("included").sum()),
                "valid_entry_rows": int(part["entry_valid_r04b"].sum()),
                "policy_replay_eligible_rows": int(len(part)),
                "excluded_invalid_entry": int((~part["entry_valid_r04b"]).sum()),
                "excluded_entry_price_mismatch": mismatch,
                "excluded_missing_price_path": int(part["r04b_replay_entry_price"].isna().sum()),
                "excluded_missing_required_indicator": 0,
                "excluded_split_boundary": 0,
                "other_unrecognized_market_regime_rows": int(part["market_regime_bucket_for_sizing"].eq("other_unrecognized_market_regime").sum()),
                "entry_price_rel_diff_p50": _quantile(part["entry_price_rel_diff"], 0.50),
                "entry_price_rel_diff_p95": _quantile(part["entry_price_rel_diff"], 0.95),
                "entry_price_rel_diff_max": float(pd.to_numeric(part["entry_price_rel_diff"], errors="coerce").max()) if len(part) else np.nan,
                "source_manifest_hash": _hash_file(topic_path(config["upstream_r04"]["manifest"])),
                "source_candidate_panel_hash": _hash_file(topic_path(config["upstream_r04"]["candidate_panel"])),
            }
        )
    return base.reset_index(drop=True), pd.DataFrame(rec_rows)


def _build_daily_path(base: pd.DataFrame, price: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    lookback = int(config["execution"]["pre_entry_lookback_trading_days"])
    max_offset = int(config["execution"]["max_holding_days"]) + int(config["execution"]["max_exit_execution_lag_trading_days"])
    offsets = np.arange(-lookback, max_offset + 1, dtype=int)
    left = pd.DataFrame(
        {
            "r04_candidate_event_id": np.repeat(base["r04_candidate_event_id"].to_numpy(), len(offsets)),
            "instrument_id": np.repeat(base["instrument_id"].to_numpy(), len(offsets)),
            "split": np.repeat(base["split"].to_numpy(), len(offsets)),
            "entry_execution_date": np.repeat(base["entry_execution_date"].to_numpy(), len(offsets)),
            "entry_calendar_index": np.repeat(base["entry_calendar_index"].to_numpy(), len(offsets)),
            "r04b_replay_entry_price": np.repeat(base["r04b_replay_entry_price"].to_numpy(), len(offsets)),
            "calendar_offset": np.tile(offsets, len(base)),
        }
    )
    left["calendar_index"] = left["entry_calendar_index"].astype(float) + left["calendar_offset"]
    left = left[left["calendar_index"].notna()].copy()
    left["calendar_index"] = left["calendar_index"].astype(int)
    keep_cols = [
        "instrument_id",
        "calendar_index",
        "trade_date",
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
        "volume",
        "money",
        "factor",
        "adjustment_policy",
        "suspended_or_dirty_bar",
        "ATR_14_asof_t",
        "stock_realized_vol_20d_asof_entry",
        "EMA_10_t",
        "EMA_20_t",
    ]
    out = left.merge(price[keep_cols], on=["instrument_id", "calendar_index"], how="left")
    out["executable_open_flag"] = (
        (out["adjusted_open"] > 0)
        & (out["volume"] > 0)
        & (out["money"] > 0)
        & (~_bool_series(out["suspended_or_dirty_bar"], default=True))
    )
    out["gross_adjusted_close_return_from_entry"] = out["adjusted_close"] / out["r04b_replay_entry_price"] - 1.0
    return out.sort_values(["r04_candidate_event_id", "calendar_offset"]).reset_index(drop=True)


def _attach_hold120_labels(base: pd.DataFrame, daily_path: pd.DataFrame, threshold: float) -> pd.DataFrame:
    post = daily_path[(daily_path["calendar_offset"] >= 0) & (daily_path["calendar_offset"] <= 120)].copy()
    agg = (
        post.groupby("r04_candidate_event_id", as_index=False)
        .agg(
            gross_max_adjusted_close_return_from_entry_to_day120=("gross_adjusted_close_return_from_entry", "max"),
            path_close_count_0_120=("adjusted_close", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
        )
    )
    hits = post.loc[post["gross_adjusted_close_return_from_entry"] >= threshold].sort_values(
        ["r04_candidate_event_id", "calendar_offset"]
    )
    first_hit = hits.drop_duplicates("r04_candidate_event_id")[
        ["r04_candidate_event_id", "trade_date", "calendar_offset"]
    ].rename(columns={"trade_date": "hold120_first_plus50_hit_date", "calendar_offset": "hold120_first_plus50_hit_offset"})
    out = base.merge(agg, on="r04_candidate_event_id", how="left").merge(first_hit, on="r04_candidate_event_id", how="left")
    out["hold120_max_gain50_flag"] = out["gross_max_adjusted_close_return_from_entry_to_day120"] >= threshold
    out["path_complete_0_120_r04b"] = out["path_close_count_0_120"].eq(121)
    return out


def _event_data(path: pd.DataFrame) -> dict[str, Any]:
    offsets = path["calendar_offset"].to_numpy(int)
    order = np.argsort(offsets)
    offsets = offsets[order]
    idx = {int(offset): i for i, offset in enumerate(offsets)}
    data = {"offsets": offsets, "idx": idx}
    for col in [
        "trade_date",
        "adjusted_open",
        "adjusted_close",
        "volume",
        "money",
        "suspended_or_dirty_bar",
        "executable_open_flag",
        "gross_adjusted_close_return_from_entry",
        "ATR_14_asof_t",
        "stock_realized_vol_20d_asof_entry",
        "EMA_10_t",
        "EMA_20_t",
    ]:
        data[col] = path[col].to_numpy()[order]
    return data


def _value(data: dict[str, Any], col: str, offset: int) -> Any:
    pos = data["idx"].get(int(offset))
    if pos is None:
        return np.nan
    return data[col][pos]


def _valid_closes(data: dict[str, Any], max_offset: int) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
    offsets = np.arange(0, max_offset + 1)
    values = np.array([_value(data, "gross_adjusted_close_return_from_entry", int(offset)) for offset in offsets], dtype=float)
    if not np.isfinite(values).all():
        return None, None
    return offsets, values


def _first_executable(data: dict[str, Any], signal_offset: int, max_lag: int) -> tuple[int | None, Any]:
    for offset in range(signal_offset + 1, signal_offset + max_lag + 1):
        flag = _value(data, "executable_open_flag", offset)
        price = _value(data, "adjusted_open", offset)
        date = _value(data, "trade_date", offset)
        if bool(flag) and np.isfinite(float(price)) and float(price) > 0:
            return offset, date
    return None, pd.NaT


def _position_weight(row: pd.Series, data: dict[str, Any], sizing_rule_id: str, config: dict[str, Any]) -> tuple[float, str]:
    sizing = config["policy_grid"]["sizing"]
    if sizing_rule_id == "fixed_size":
        return 1.0, ""
    if sizing_rule_id == "volatility_scaled":
        vol = _value(data, "stock_realized_vol_20d_asof_entry", 0)
        if not np.isfinite(float(vol)) or float(vol) <= 0:
            return np.nan, "censored_by_missing_required_indicator"
        cfg = sizing["volatility_scaled"]
        return float(np.clip(float(cfg["target_vol"]) / float(vol), float(cfg["min_weight"]), float(cfg["max_weight"]))), ""
    if sizing_rule_id == "market_state_scaled":
        bucket = str(row.get("market_regime_bucket_for_sizing", "missing_market_regime"))
        if bucket == "post_drawdown_rebound_hypothesis":
            bucket = "post_drawdown_rebound"
        mapping = sizing["market_state_scaled"]
        return float(mapping.get(bucket, mapping["other_unrecognized_market_regime"])), ""
    return np.nan, "invalid_entry"


def _signal_offset(data: dict[str, Any], policy: pd.Series) -> tuple[int | None, str]:
    family = str(policy["exit_rule_family_id"])
    params = json.loads(policy["parameter_values_json"]) if str(policy["parameter_values_json"]) else {}
    max_hold = int(policy["max_holding_days"])
    offsets, returns = _valid_closes(data, max_hold)
    if offsets is None:
        return None, "censored_by_missing_price"
    if family == "no_exit":
        return max_hold, ""
    if family == "fixed_stop":
        hit = np.where(returns <= float(params["stop_loss_pct"]))[0]
        return int(offsets[hit[0]]) if len(hit) else max_hold, ""
    if family == "time_stop":
        return int(params["time_stop_days"]), ""
    if family == "break_even_after_gain":
        activated = False
        for offset, ret in zip(offsets, returns):
            if not activated and ret >= float(params["activation_gain_pct"]):
                activated = True
            if activated and ret <= 0.0:
                return int(offset), ""
        return max_hold, ""
    if family == "profit_lock_after_gain":
        activated = False
        for offset, ret in zip(offsets, returns):
            if not activated and ret >= float(params["activation_gain_pct"]):
                activated = True
            if activated and ret <= float(params["locked_gain_pct"]):
                return int(offset), ""
        return max_hold, ""
    if family == "ATR_trailing":
        active = float(params.get("min_activation_gain_pct", 0.0)) <= 0.0
        highest_close = -np.inf
        trail_stop = -np.inf
        for offset, ret in zip(offsets, returns):
            close_price = _value(data, "adjusted_close", int(offset))
            if not np.isfinite(float(close_price)):
                return None, "censored_by_missing_price"
            highest_close = max(highest_close, float(close_price))
            if not active and ret >= float(params["min_activation_gain_pct"]):
                active = True
            if active:
                atr = _value(data, "ATR_14_asof_t", int(offset))
                if not np.isfinite(float(atr)):
                    return None, "censored_by_missing_required_indicator"
                trail_stop = max(trail_stop, highest_close - float(params["k_atr"]) * float(atr))
                if float(close_price) <= trail_stop:
                    return int(offset), ""
        return max_hold, ""
    if family == "EMA_trailing":
        window = int(params["ema_window"])
        confirm_days = int(params["confirm_days"])
        ema_col = f"EMA_{window}_t"
        confirm = 0
        for offset in offsets:
            close_price = _value(data, "adjusted_close", int(offset))
            ema = _value(data, ema_col, int(offset))
            if not np.isfinite(float(close_price)):
                return None, "censored_by_missing_price"
            if not np.isfinite(float(ema)):
                return None, "censored_by_missing_required_indicator"
            confirm = confirm + 1 if float(close_price) < float(ema) else 0
            if confirm >= confirm_days:
                return int(offset), ""
        return max_hold, ""
    return None, "invalid_entry"


def _replay_event_policy(
    row: pd.Series,
    data: dict[str, Any],
    policy: pd.Series,
    config: dict[str, Any],
    bounds: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
) -> dict[str, Any]:
    base = {
        "r04_candidate_event_id": row["r04_candidate_event_id"],
        "policy_id": policy["policy_id"],
        "policy_family_id": policy["policy_family_id"],
        "hold_rule_id": policy["hold_rule_id"],
        "exit_rule_id": policy["exit_rule_id"],
        "exit_rule_family_id": policy["exit_rule_family_id"],
        "sizing_rule_id": policy["sizing_rule_id"],
        "parameter_set_id": policy["parameter_set_id"],
        "parameter_values_json": policy["parameter_values_json"],
        "split": row["split"],
        "instrument_id": row["instrument_id"],
        "entry_execution_date": row["entry_execution_date"],
        "entry_price": row["r04b_replay_entry_price"],
        "market_regime_bucket": row["market_regime_bucket"],
        "industry_regime_bucket": row["industry_regime_bucket"],
        "calendar_year": int(pd.Timestamp(row["entry_execution_date"]).year),
        "hold120_max_gain50_flag": bool(row["hold120_max_gain50_flag"]),
        "hold120_first_plus50_hit_date": row.get("hold120_first_plus50_hit_date", pd.NaT),
        "legacy_plus10_before_minus5_rate": bool(row.get("hit_plus10_before_minus5", False)),
        "legacy_bad_path_rate": bool(row.get("bad_path_flag", False)),
        "legacy_early_failure_rate": bool(row.get("early_failure_flag", False)),
        "legacy_race_ambiguous_rate": bool(row.get("race_ambiguous_flag", False)),
    }
    if not bool(row.get("entry_valid_r04b", False)):
        return {**base, "replay_status": "invalid_entry", "replay_complete": False}
    weight, weight_status = _position_weight(row, data, str(policy["sizing_rule_id"]), config)
    if weight_status:
        return {**base, "position_weight": np.nan, "replay_status": weight_status, "replay_complete": False}
    signal_offset, signal_status = _signal_offset(data, policy)
    if signal_status:
        return {**base, "position_weight": weight, "replay_status": signal_status, "replay_complete": False}
    max_lag = int(config["execution"]["max_exit_execution_lag_trading_days"])
    exec_offset, exec_date = _first_executable(data, int(signal_offset), max_lag)
    if exec_offset is None:
        return {**base, "position_weight": weight, "exit_signal_offset": signal_offset, "replay_status": "censored_by_no_exit_execution", "replay_complete": False}
    split = str(row["split"])
    if _split_for_date(exec_date, bounds) != split:
        return {
            **base,
            "position_weight": weight,
            "exit_signal_offset": signal_offset,
            "exit_execution_offset": exec_offset,
            "exit_execution_date": exec_date,
            "replay_status": "censored_by_split_boundary",
            "replay_complete": False,
        }
    exit_price = _value(data, "adjusted_open", int(exec_offset))
    entry_price = float(row["r04b_replay_entry_price"])
    gross_return = float(exit_price) / entry_price - 1.0
    cost = config["cost_model"]
    entry_cost = (float(cost["entry_slippage_bps"]) + float(cost["commission_bps_per_side"])) / 10000.0
    exit_cost = (float(cost["exit_slippage_bps"]) + float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])) / 10000.0
    total_cost_bps = float(cost["entry_slippage_bps"]) + float(cost["exit_slippage_bps"]) + 2 * float(cost["commission_bps_per_side"]) + float(cost["stamp_tax_bps_on_exit"])
    unweighted_net_return = gross_return - entry_cost - exit_cost
    weighted_net_return = float(weight) * unweighted_net_return
    offsets, close_returns = _valid_closes(data, int(signal_offset))
    mae = float(np.nanmin(close_returns)) if offsets is not None else np.nan
    first_hit = pd.to_datetime(row.get("hold120_first_plus50_hit_date"), errors="coerce")
    retained = bool(row["hold120_max_gain50_flag"]) and not pd.isna(first_hit) and pd.Timestamp(exec_date) > first_hit
    return {
        **base,
        "position_weight": weight,
        "exit_signal_offset": int(signal_offset),
        "exit_signal_date": _value(data, "trade_date", int(signal_offset)),
        "exit_execution_offset": int(exec_offset),
        "exit_execution_date": exec_date,
        "exit_price": float(exit_price),
        "gross_return": gross_return,
        "entry_cost": entry_cost,
        "exit_cost": exit_cost,
        "total_cost_bps": total_cost_bps,
        "unweighted_net_return": unweighted_net_return,
        "weighted_net_return": weighted_net_return,
        "realized_loss_le_minus5_flag": weighted_net_return <= -0.05,
        "realized_loss_le_minus10_flag": weighted_net_return <= -0.10,
        "max_adverse_excursion": mae,
        "avg_holding_days": int(exec_offset),
        "policy_retained_max_gain50_flag": retained,
        "replay_status": "replay_complete",
        "replay_complete": True,
    }


def _replay_policies(base: pd.DataFrame, daily_path: pd.DataFrame, policy_matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    bounds = _split_bounds(config)
    valid_policies = policy_matrix[policy_matrix["invalid_policy_reason"].fillna("").eq("")].reset_index(drop=True)
    path_groups = {eid: _event_data(part) for eid, part in daily_path.groupby("r04_candidate_event_id", sort=False)}
    rows: list[dict[str, Any]] = []
    for idx, event in base.iterrows():
        data = path_groups.get(event["r04_candidate_event_id"])
        if data is None:
            for _, policy in valid_policies.iterrows():
                rows.append(
                    {
                        "r04_candidate_event_id": event["r04_candidate_event_id"],
                        "policy_id": policy["policy_id"],
                        "policy_family_id": policy["policy_family_id"],
                        "hold_rule_id": policy["hold_rule_id"],
                        "exit_rule_id": policy["exit_rule_id"],
                        "exit_rule_family_id": policy["exit_rule_family_id"],
                        "sizing_rule_id": policy["sizing_rule_id"],
                        "parameter_set_id": policy["parameter_set_id"],
                        "parameter_values_json": policy["parameter_values_json"],
                        "split": event["split"],
                        "instrument_id": event["instrument_id"],
                        "replay_status": "censored_by_missing_price",
                        "replay_complete": False,
                    }
                )
            continue
        for _, policy in valid_policies.iterrows():
            rows.append(_replay_event_policy(event, data, policy, config, bounds))
        if (idx + 1) % 1000 == 0:
            print(f"replayed {idx + 1}/{len(base)} candidate events", flush=True)
    replay = pd.DataFrame(rows)
    replay["replay_complete"] = _bool_series(replay["replay_complete"])
    return replay


def _summarize_policy(replay: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = [
        "policy_id",
        "policy_family_id",
        "hold_rule_id",
        "exit_rule_id",
        "exit_rule_family_id",
        "sizing_rule_id",
        "parameter_set_id",
        "parameter_values_json",
        "split",
    ]
    for keys, part in replay.groupby(group_cols, dropna=False, sort=False):
        rec = dict(zip(group_cols, keys))
        complete = part[_bool_series(part["replay_complete"])].copy()
        event_count = int(len(part))
        replay_complete_count = int(len(complete))
        hold_winners = part[_bool_series(part["hold120_max_gain50_flag"])]
        retained = int(_bool_series(hold_winners["policy_retained_max_gain50_flag"]).sum())
        hold_count = int(len(hold_winners))
        lo, hi = _wilson(retained, hold_count)
        winner_complete = complete[_bool_series(complete["hold120_max_gain50_flag"])]
        rec.update(
            {
                "event_count": event_count,
                "replay_complete_count": replay_complete_count,
                "censored_count": int(event_count - replay_complete_count),
                "replay_complete_rate": _safe_div(replay_complete_count, event_count),
                "censored_share": _safe_div(event_count - replay_complete_count, event_count),
                "weighted_event_count": float(complete["position_weight"].sum()) if replay_complete_count else 0.0,
                "position_weight_mean": float(complete["position_weight"].mean()) if replay_complete_count else np.nan,
                "unweighted_net_return_mean": float(complete["unweighted_net_return"].mean()) if replay_complete_count else np.nan,
                "net_return_mean": float(complete["weighted_net_return"].mean()) if replay_complete_count else np.nan,
                "net_return_median": _quantile(complete["weighted_net_return"], 0.50),
                "net_return_p10": _quantile(complete["weighted_net_return"], 0.10),
                "net_return_p25": _quantile(complete["weighted_net_return"], 0.25),
                "net_return_p75": _quantile(complete["weighted_net_return"], 0.75),
                "net_return_p90": _quantile(complete["weighted_net_return"], 0.90),
                "realized_loss_le_minus5_rate": float(complete["realized_loss_le_minus5_flag"].mean()) if replay_complete_count else np.nan,
                "realized_loss_le_minus10_rate": float(complete["realized_loss_le_minus10_flag"].mean()) if replay_complete_count else np.nan,
                "max_adverse_excursion_p50": _quantile(complete["max_adverse_excursion"], 0.50),
                "max_adverse_excursion_p75": _quantile(complete["max_adverse_excursion"], 0.75),
                "max_adverse_excursion_p90": _quantile(complete["max_adverse_excursion"], 0.90),
                "max_gain50_retention_vs_hold120": _safe_div(retained, hold_count),
                "max_gain50_retention_wilson_lower": lo,
                "max_gain50_retention_wilson_upper": hi,
                "hold120_max_gain50_count": hold_count,
                "policy_retained_max_gain50_count": retained,
                "winner_exit_efficiency": np.nan,
                "avg_holding_days": float(complete["avg_holding_days"].mean()) if replay_complete_count else np.nan,
                "turnover_proxy": _safe_div(252.0, float(complete["avg_holding_days"].mean()) if replay_complete_count else np.nan),
                "cost_bps_mean": float(complete["total_cost_bps"].mean()) if replay_complete_count else np.nan,
                "winner_net_return_mean": float(winner_complete["weighted_net_return"].mean()) if len(winner_complete) else np.nan,
            }
        )
        rows.append(rec)
    summary = pd.DataFrame(rows)
    baseline_id = config["baseline"]["hold120_baseline_policy_id"]
    baseline = summary[summary["policy_id"].eq(baseline_id)][
        [
            "split",
            "net_return_mean",
            "net_return_p10",
            "realized_loss_le_minus5_rate",
            "winner_net_return_mean",
            "avg_holding_days",
        ]
    ].rename(
        columns={
            "net_return_mean": "hold120_net_return_mean",
            "net_return_p10": "hold120_net_return_p10",
            "realized_loss_le_minus5_rate": "hold120_realized_loss_le_minus5_rate",
            "winner_net_return_mean": "hold120_winner_net_return_mean",
            "avg_holding_days": "hold120_avg_holding_days",
        }
    )
    summary = summary.merge(baseline, on="split", how="left")
    summary["net_return_mean_delta_vs_hold120"] = summary["net_return_mean"] - summary["hold120_net_return_mean"]
    summary["left_tail_net_return_p10_delta_vs_hold120"] = summary["net_return_p10"] - summary["hold120_net_return_p10"]
    summary["bad_path_loss_compression_vs_hold120"] = summary["hold120_realized_loss_le_minus5_rate"] - summary["realized_loss_le_minus5_rate"]
    summary["winner_exit_efficiency"] = summary["winner_net_return_mean"] / summary["hold120_winner_net_return_mean"]
    summary["avg_holding_days_increase_penalty"] = np.maximum(summary["avg_holding_days"] - summary["hold120_avg_holding_days"], 0)
    thresholds = config["thresholds"]
    min_replay = {
        "train": thresholds["minimum_train_replay_complete_count"],
        "validation": thresholds["minimum_validation_replay_complete_count"],
        "robustness": thresholds["minimum_robustness_replay_complete_count"],
    }
    summary["denominator_status"] = [
        "sufficient" if row.replay_complete_count >= min_replay.get(row.split, thresholds["minimum_validation_replay_complete_count"]) else "insufficient_replay_complete"
        for row in summary.itertuples(index=False)
    ]
    summary["winner_retention_status"] = np.where(
        summary["max_gain50_retention_vs_hold120"] >= thresholds["min_max_gain50_retention_vs_hold120"],
        "passed",
        "failed_winner_retention_gate",
    )
    return summary


def _zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    std = values.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (values - values.mean()) / std


def _selection(summary: pd.DataFrame, policy_matrix: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str, str]:
    thresholds = config["thresholds"]
    matrix_cols = [
        "policy_id",
        "is_train_selectable",
        "is_validation_selectable",
        "is_sensitivity_policy",
        "invalid_policy_reason",
        "parameter_reference_group_id",
        "validation_family_reference_set_id",
    ]
    selectable = summary.merge(policy_matrix[matrix_cols], on="policy_id", how="left")
    train = selectable[
        selectable["split"].eq("train")
        & _bool_series(selectable["is_train_selectable"])
        & (~_bool_series(selectable["is_sensitivity_policy"]))
        & selectable["invalid_policy_reason"].fillna("").eq("")
    ].copy()
    train["train_gate_pass"] = (
        train["replay_complete_count"].ge(thresholds["minimum_train_replay_complete_count"])
        & train["max_gain50_retention_vs_hold120"].ge(thresholds["min_max_gain50_retention_vs_hold120"])
        & train["censored_share"].le(thresholds["max_censored_share"])
    )
    train["train_selection_score"] = np.nan
    trace_rows: list[dict[str, Any]] = []
    selected_train_ids: set[str] = set()
    for family, part in train.groupby("policy_family_id", sort=False):
        idx = part.index
        train.loc[idx, "_z_net"] = _zscore(part["net_return_mean_delta_vs_hold120"])
        train.loc[idx, "_z_tail"] = _zscore(part["left_tail_net_return_p10_delta_vs_hold120"])
        train.loc[idx, "_z_bad"] = _zscore(part["bad_path_loss_compression_vs_hold120"])
        train.loc[idx, "_z_hold"] = _zscore(part["avg_holding_days_increase_penalty"])
        train.loc[idx, "train_selection_score"] = train.loc[idx, "_z_net"] + train.loc[idx, "_z_tail"] + train.loc[idx, "_z_bad"] - train.loc[idx, "_z_hold"]
        eligible = train.loc[idx][train.loc[idx, "train_gate_pass"]]
        selected_policy = ""
        if not eligible.empty:
            selected_policy = str(eligible.sort_values(["train_selection_score", "net_return_mean_delta_vs_hold120"], ascending=False).iloc[0]["policy_id"])
            selected_train_ids.add(selected_policy)
        ranked = train.loc[idx].sort_values("train_selection_score", ascending=False)
        for rank, row in enumerate(ranked.itertuples(index=False), start=1):
            trace_rows.append(
                {
                    "selection_stage": "train_parameter_selection",
                    "split_used": "train",
                    "policy_family_id": row.policy_family_id,
                    "exit_rule_family_id": row.exit_rule_family_id,
                    "candidate_policy_id": row.policy_id,
                    "parameter_set_id": row.parameter_set_id,
                    "parameter_values_json": row.parameter_values_json,
                    "selection_metric_name": "train_selection_score",
                    "selection_metric_value": row.train_selection_score,
                    "selection_rank": rank,
                    "z_reference_set_id": row.parameter_reference_group_id,
                    "z_reference_set_size": int(len(part)),
                    "selected_flag": row.policy_id == selected_policy,
                    "rejection_reason": "" if row.policy_id == selected_policy else ("failed_train_gate" if not row.train_gate_pass else "lower_train_score"),
                }
            )
    val = selectable[
        selectable["split"].eq("validation")
        & selectable["policy_id"].isin(selected_train_ids)
        & _bool_series(selectable["is_validation_selectable"])
    ].copy()
    val["validation_gate_pass"] = (
        val["replay_complete_count"].ge(thresholds["minimum_validation_replay_complete_count"])
        & val["hold120_max_gain50_count"].ge(thresholds["minimum_validation_hold120_max_gain50_count"])
        & val["max_gain50_retention_vs_hold120"].ge(thresholds["min_max_gain50_retention_vs_hold120"])
        & val["bad_path_loss_compression_vs_hold120"].gt(0)
        & val["left_tail_net_return_p10_delta_vs_hold120"].ge(0)
        & val["net_return_mean_delta_vs_hold120"].gt(0)
        & val["censored_share"].le(thresholds["max_censored_share"])
    )
    for col, zcol in [
        ("net_return_mean_delta_vs_hold120", "_z_net"),
        ("left_tail_net_return_p10_delta_vs_hold120", "_z_tail"),
        ("bad_path_loss_compression_vs_hold120", "_z_bad"),
        ("max_gain50_retention_vs_hold120", "_z_retention"),
    ]:
        val[zcol] = _zscore(val[col])
    val["validation_selection_score"] = val["_z_net"] + val["_z_tail"] + val["_z_bad"] + val["_z_retention"]
    selected_policy_id = ""
    selected_family_id = ""
    passing = val[val["validation_gate_pass"]]
    if not passing.empty:
        selected = passing.sort_values(["validation_selection_score", "net_return_mean_delta_vs_hold120"], ascending=False).iloc[0]
        selected_policy_id = str(selected["policy_id"])
        selected_family_id = str(selected["policy_family_id"])
    ranked_val = val.sort_values("validation_selection_score", ascending=False)
    for rank, row in enumerate(ranked_val.itertuples(index=False), start=1):
        trace_rows.append(
            {
                "selection_stage": "validation_family_selection",
                "split_used": "validation",
                "policy_family_id": row.policy_family_id,
                "exit_rule_family_id": row.exit_rule_family_id,
                "candidate_policy_id": row.policy_id,
                "parameter_set_id": row.parameter_set_id,
                "parameter_values_json": row.parameter_values_json,
                "selection_metric_name": "validation_selection_score",
                "selection_metric_value": row.validation_selection_score,
                "selection_rank": rank,
                "z_reference_set_id": row.validation_family_reference_set_id,
                "z_reference_set_size": int(len(val)),
                "selected_flag": row.policy_id == selected_policy_id,
                "rejection_reason": "" if row.policy_id == selected_policy_id else ("failed_validation_gate" if not row.validation_gate_pass else "lower_validation_score"),
            }
        )
    selection_trace = pd.DataFrame(trace_rows)
    selection_panel = selectable.merge(
        selection_trace[["candidate_policy_id", "selection_stage", "selected_flag"]].rename(columns={"candidate_policy_id": "policy_id"}),
        on="policy_id",
        how="left",
    )
    return selection_trace, selection_panel, selected_policy_id, selected_family_id


def _final_decision(summary: pd.DataFrame, selected_policy_id: str, config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not selected_policy_id:
        return "r04b_no_policy_family_passed_validation", {}
    thresholds = config["thresholds"]
    selected = summary[summary["policy_id"].eq(selected_policy_id)].set_index("split")
    robustness = selected.loc["robustness"].to_dict() if "robustness" in selected.index else {}
    pass_robustness = bool(
        robustness
        and robustness.get("replay_complete_count", 0) >= thresholds["minimum_robustness_replay_complete_count"]
        and robustness.get("hold120_max_gain50_count", 0) >= thresholds["minimum_robustness_hold120_max_gain50_count"]
        and robustness.get("max_gain50_retention_vs_hold120", np.nan) >= thresholds["min_max_gain50_retention_vs_hold120"]
        and robustness.get("bad_path_loss_compression_vs_hold120", np.nan) > 0
        and robustness.get("left_tail_net_return_p10_delta_vs_hold120", np.nan) >= 0
        and robustness.get("net_return_mean_delta_vs_hold120", np.nan) > 0
        and robustness.get("censored_share", np.nan) <= thresholds["max_censored_share"]
    )
    if pass_robustness:
        return "r04b_hold_exit_risk_budget_candidate_passed_diagnostic_only", robustness
    return "r04b_policy_not_robust_hold_exit_diagnostic_complete", robustness


def _censored_audit(replay: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    policy_split_counts = replay.groupby(["policy_id", "split"], dropna=False).size().to_dict()
    for keys, part in replay.groupby(["policy_id", "split", "replay_status"], dropna=False):
        policy_id, split, status = keys
        rows.append(
            {
                "policy_id": policy_id,
                "split": split,
                "replay_status": status,
                "event_count": int(len(part)),
                "share_of_policy_split": _safe_div(len(part), policy_split_counts.get((policy_id, split), 0)),
            }
        )
    return pd.DataFrame(rows)


def _interaction_audit(replay: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    complete = replay[_bool_series(replay["replay_complete"])].copy()
    dims = [
        ("market_regime_bucket", ["market_regime_bucket"]),
        ("industry_regime_bucket", ["industry_regime_bucket"]),
        ("market_regime_bucket x industry_regime_bucket", ["market_regime_bucket", "industry_regime_bucket"]),
    ]
    rows: list[dict[str, Any]] = []
    baseline_id = config["baseline"]["hold120_baseline_policy_id"]
    baseline = complete[complete["policy_id"].eq(baseline_id)]
    for dim_name, cols in dims:
        event_counts = replay.groupby(["policy_id", "split"] + cols, dropna=False).size().to_dict()
        base_metrics = {}
        for keys, part in baseline.groupby(["split"] + cols, dropna=False):
            key = keys if isinstance(keys, tuple) else (keys,)
            base_metrics[key] = {
                "net": float(part["weighted_net_return"].mean()),
                "loss": float(part["realized_loss_le_minus5_flag"].mean()),
            }
        for keys, part in complete.groupby(["policy_id", "split"] + cols, dropna=False):
            key = keys if isinstance(keys, tuple) else (keys,)
            policy_id = key[0]
            split = key[1]
            values = key[2:]
            base = base_metrics.get((split, *values), {})
            years = part["calendar_year"].value_counts(normalize=True)
            instruments = part["instrument_id"].value_counts(normalize=True)
            winners = part[_bool_series(part["hold120_max_gain50_flag"])]
            retained = int(_bool_series(winners["policy_retained_max_gain50_flag"]).sum())
            denom = int(len(winners))
            replay_count = int(len(part))
            top_year = float(years.iloc[0]) if len(years) else np.nan
            enough = replay_count >= config["thresholds"]["interaction_min_replay_complete_count"]
            year_ok = np.isfinite(top_year) and top_year <= config["thresholds"]["interaction_max_top1_calendar_year_share"]
            rows.append(
                {
                    "policy_id": policy_id,
                    "split": split,
                    "interaction_dimension": dim_name,
                    "interaction_value": "|".join(str(v) for v in values),
                    "event_count": int(event_counts.get((policy_id, split, *values), 0)),
                    "replay_complete_count": replay_count,
                    "net_return_mean_delta_vs_hold120": float(part["weighted_net_return"].mean()) - base.get("net", np.nan),
                    "bad_path_loss_compression_vs_hold120": base.get("loss", np.nan) - float(part["realized_loss_le_minus5_flag"].mean()),
                    "max_gain50_retention_vs_hold120": _safe_div(retained, denom),
                    "subgroup_denominator_status": "sufficient" if enough else "insufficient_replay_complete",
                    "top1_calendar_year_share": top_year,
                    "top1_instrument_share": float(instruments.iloc[0]) if len(instruments) else np.nan,
                    "research_lead_eligible_flag": bool(enough and year_ok),
                    "research_lead_ineligible_reason": "" if enough and year_ok else ("insufficient_denominator" if not enough else "year_concentrated"),
                }
            )
    return pd.DataFrame(rows)


def _reports(
    config: dict[str, Any],
    base: pd.DataFrame,
    policy_matrix: pd.DataFrame,
    summary: pd.DataFrame,
    replay: pd.DataFrame,
    selection_trace: pd.DataFrame,
    selected_policy_id: str,
    final_decision: str,
    output_root: Path,
) -> None:
    reports = output_root / "reports"
    baseline_id = config["baseline"]["hold120_baseline_policy_id"]
    selected_summary = summary[summary["policy_id"].eq(selected_policy_id)] if selected_policy_id else pd.DataFrame()
    hold = summary[summary["policy_id"].eq(baseline_id)]
    validation_pass = False
    robustness_pass = False
    selected_meta = {}
    if selected_policy_id and not selected_summary.empty:
        val = selected_summary[selected_summary["split"].eq("validation")]
        rob = selected_summary[selected_summary["split"].eq("robustness")]
        validation_pass = bool(len(val) and val.iloc[0]["max_gain50_retention_vs_hold120"] >= config["thresholds"]["min_max_gain50_retention_vs_hold120"])
        robustness_pass = final_decision == "r04b_hold_exit_risk_budget_candidate_passed_diagnostic_only"
        selected_meta = selected_summary.iloc[0].to_dict()
    final = pd.DataFrame(
        [
            {
                "final_decision": final_decision,
                "selected_policy_id": selected_policy_id,
                "selected_policy_family_id": selected_meta.get("policy_family_id", ""),
                "selected_exit_rule_family_id": selected_meta.get("exit_rule_family_id", ""),
                "selected_parameter_values_json": selected_meta.get("parameter_values_json", ""),
                "validation_gate_pass": validation_pass,
                "robustness_gate_pass": robustness_pass,
                "validation_max_gain50_retention_vs_hold120": _split_metric(selected_summary, "validation", "max_gain50_retention_vs_hold120"),
                "robustness_max_gain50_retention_vs_hold120": _split_metric(selected_summary, "robustness", "max_gain50_retention_vs_hold120"),
                "validation_bad_path_loss_compression_vs_hold120": _split_metric(selected_summary, "validation", "bad_path_loss_compression_vs_hold120"),
                "robustness_bad_path_loss_compression_vs_hold120": _split_metric(selected_summary, "robustness", "bad_path_loss_compression_vs_hold120"),
                "validation_net_return_mean_delta_vs_hold120": _split_metric(selected_summary, "validation", "net_return_mean_delta_vs_hold120"),
                "robustness_net_return_mean_delta_vs_hold120": _split_metric(selected_summary, "robustness", "net_return_mean_delta_vs_hold120"),
                "decision_reason": final_decision,
            }
        ]
    )
    write_csv(final, reports / "r04b_final_decision.csv")

    write_csv(summary, reports / "r04b_policy_replay_summary.csv")
    write_csv(summary, reports / "r04b_policy_vs_hold120_summary.csv")
    winner = summary[
        [
            "policy_id",
            "split",
            "hold120_max_gain50_count",
            "policy_retained_max_gain50_count",
            "max_gain50_retention_vs_hold120",
            "max_gain50_retention_wilson_lower",
            "max_gain50_retention_wilson_upper",
            "winner_exit_efficiency",
            "winner_retention_status",
        ]
    ].rename(columns={"max_gain50_retention_wilson_lower": "wilson_lower", "max_gain50_retention_wilson_upper": "wilson_upper"})
    winner["first_plus50_hit_before_exit_count"] = winner["policy_retained_max_gain50_count"]
    winner["exit_before_first_plus50_count"] = winner["hold120_max_gain50_count"] - winner["policy_retained_max_gain50_count"]
    winner["retention_gate_threshold"] = config["thresholds"]["min_max_gain50_retention_vs_hold120"]
    winner["retention_gate_pass"] = winner["max_gain50_retention_vs_hold120"] >= config["thresholds"]["min_max_gain50_retention_vs_hold120"]
    write_csv(winner, reports / "r04b_winner_retention_audit.csv")
    write_csv(summary[["policy_id", "split", "bad_path_loss_compression_vs_hold120", "realized_loss_le_minus5_rate", "realized_loss_le_minus10_rate", "net_return_p10", "left_tail_net_return_p10_delta_vs_hold120"]], reports / "r04b_bad_path_compression_audit.csv")
    write_csv(_censored_audit(replay), reports / "r04b_censored_replay_audit.csv")
    interaction = _interaction_audit(replay, config)
    write_csv(interaction, reports / "r04b_market_industry_interaction_audit.csv")
    concentration = (
        replay[_bool_series(replay["replay_complete"])]
        .groupby(["policy_id", "split"], as_index=False)
        .agg(
            top1_calendar_year_share=("calendar_year", lambda s: float(s.value_counts(normalize=True).iloc[0]) if len(s) else np.nan),
            top1_instrument_share=("instrument_id", lambda s: float(s.value_counts(normalize=True).iloc[0]) if len(s) else np.nan),
        )
    )
    write_csv(concentration, reports / "r04b_year_instrument_concentration_audit.csv")
    write_csv(summary[["policy_id", "split", "weighted_event_count", "avg_holding_days", "turnover_proxy", "cost_bps_mean"]], reports / "r04b_cost_turnover_audit.csv")
    legacy_cols = ["policy_id", "split", "legacy_plus10_before_minus5_rate", "legacy_bad_path_rate", "legacy_early_failure_rate", "legacy_race_ambiguous_rate"]
    legacy = replay.groupby(["policy_id", "split"], as_index=False).agg(
        legacy_plus10_before_minus5_rate=("legacy_plus10_before_minus5_rate", "mean"),
        legacy_bad_path_rate=("legacy_bad_path_rate", "mean"),
        legacy_early_failure_rate=("legacy_early_failure_rate", "mean"),
        legacy_race_ambiguous_rate=("legacy_race_ambiguous_rate", "mean"),
    )
    write_csv(legacy[legacy_cols], reports / "r04b_legacy_metric_audit.csv")

    report = _final_report_text(config, base, policy_matrix, hold, summary, selection_trace, interaction, final)
    (reports / "r04b_fixed_entry_hold_exit_risk_budget_cta_final_report.md").write_text(report, encoding="utf-8")


def _split_metric(df: pd.DataFrame, split: str, col: str) -> Any:
    if df.empty:
        return np.nan
    part = df[df["split"].eq(split)]
    return np.nan if part.empty or col not in part.columns else part.iloc[0][col]


def _pct(value: Any) -> str:
    try:
        if not np.isfinite(float(value)):
            return "NA"
        return f"{float(value):.2%}"
    except Exception:
        return "NA"


def _final_report_text(
    config: dict[str, Any],
    base: pd.DataFrame,
    policy_matrix: pd.DataFrame,
    hold: pd.DataFrame,
    summary: pd.DataFrame,
    selection_trace: pd.DataFrame,
    interaction: pd.DataFrame,
    final: pd.DataFrame,
) -> str:
    selected_policy = str(final.iloc[0]["selected_policy_id"])
    decision = str(final.iloc[0]["final_decision"])
    lines = [
        "# R04b 固定入场 Hold / Exit / Risk-Budget CTA 诊断报告",
        "",
        "R04b is fixed-entry policy replay, not entry eligibility.",
        "CTA/trailing is an exit_rule family, not a separate strategy track.",
        "Market and industry states are interaction diagnostics only, not selection gates.",
        "+10 before -5 is legacy diagnostic only for R04b.",
        "max_gain50_retention_vs_hold120 gate threshold = 0.60.",
        "No production entry gate, sizing rule, or CTA strategy is emitted by this diagnostic.",
        "",
        "## 结论",
        "",
        f"- final_decision: `{decision}`",
        f"- selected_policy_id: `{selected_policy}`" if selected_policy else "- selected_policy_id: 无",
        f"- 主池样本数: {len(base):,}",
        f"- policy matrix rows: {len(policy_matrix):,}",
        "",
        "## Hold120 baseline",
        "",
    ]
    for row in hold.sort_values("split").itertuples(index=False):
        lines.append(
            f"- {row.split}: net_return_mean={_pct(row.net_return_mean)}, "
            f"p10={_pct(row.net_return_p10)}, loss<=-5={_pct(row.realized_loss_le_minus5_rate)}, "
            f"max_gain50_count={int(row.hold120_max_gain50_count)}"
        )
    lines.extend(["", "## Train / Validation 选择", ""])
    train_selected = selection_trace[(selection_trace["selection_stage"].eq("train_parameter_selection")) & _bool_series(selection_trace["selected_flag"])]
    for row in train_selected.head(20).itertuples(index=False):
        lines.append(f"- train selected: `{row.candidate_policy_id}` score={row.selection_metric_value:.4f}")
    val_selected = selection_trace[(selection_trace["selection_stage"].eq("validation_family_selection")) & _bool_series(selection_trace["selected_flag"])]
    if len(val_selected):
        row = val_selected.iloc[0]
        lines.append(f"- validation selected: `{row['candidate_policy_id']}` score={row['selection_metric_value']:.4f}")
    else:
        lines.append("- validation 没有 policy family 通过全部 hard gates。")
    lines.extend(["", "## Selected policy OOS readout", ""])
    if selected_policy:
        selected = summary[summary["policy_id"].eq(selected_policy)].sort_values("split")
        for row in selected.itertuples(index=False):
            lines.append(
                f"- {row.split}: net_delta={_pct(row.net_return_mean_delta_vs_hold120)}, "
                f"p10_delta={_pct(row.left_tail_net_return_p10_delta_vs_hold120)}, "
                f"bad_path_compression={_pct(row.bad_path_loss_compression_vs_hold120)}, "
                f"max_gain50_retention={_pct(row.max_gain50_retention_vs_hold120)}, "
                f"censored_share={_pct(row.censored_share)}"
            )
    lines.extend(["", "## CTA / trailing 对照", ""])
    compare = summary[summary["split"].eq("validation")].groupby("exit_rule_family_id", as_index=False).agg(
        best_net_delta=("net_return_mean_delta_vs_hold120", "max"),
        best_bad_path_compression=("bad_path_loss_compression_vs_hold120", "max"),
        best_retention=("max_gain50_retention_vs_hold120", "max"),
    )
    for row in compare.sort_values("best_net_delta", ascending=False).itertuples(index=False):
        lines.append(
            f"- {row.exit_rule_family_id}: best_net_delta={_pct(row.best_net_delta)}, "
            f"best_bad_path_compression={_pct(row.best_bad_path_compression)}, "
            f"best_retention={_pct(row.best_retention)}"
        )
    lines.extend(["", "## Interaction audit", ""])
    insufficient_winner_share = float(summary["winner_retention_status"].eq("failed_winner_retention_gate").mean()) if len(summary) else np.nan
    ineligible_share = float((~_bool_series(interaction["research_lead_eligible_flag"])).mean()) if len(interaction) else np.nan
    lines.append(f"- winner_efficiency / retention failed cell 占比: {_pct(insufficient_winner_share)}")
    lines.append(f"- research_lead_eligible_flag == false 的 interaction cell 占比: {_pct(ineligible_share)}")
    lines.append("- downtrend_low_breadth 与 industry_lagging 只作为 interaction lead 阅读，不参与 selection。")
    lines.extend(["", "## 后续判断", ""])
    if decision == "r04b_hold_exit_risk_budget_candidate_passed_diagnostic_only":
        lines.append("R04b 只支持进入下一版 production-like replay requirement，不支持直接上线。")
    elif decision == "r04b_policy_not_robust_hold_exit_diagnostic_complete":
        lines.append("validation 有候选，但 robustness 未满足全部 gate；下一步应检查失败来自 retention、左尾还是均值 payoff。")
    else:
        lines.append("没有 policy family 通过 validation hard gates；R04b 诊断完成，不能升级为 entry 或 CTA 策略结论。")
    lines.append("")
    return "\n".join(lines)


def _gate0_spec(config: dict[str, Any]) -> pd.DataFrame:
    rows = [
        ("return", "simple_return", {"return_type": "simple_return"}, "gross_return=exit_price/entry_price-1;net=gross-cost"),
        ("cost", "a_share_daily_replay_default_v1", config["cost_model"], "entry/exit bps frozen in config"),
        ("sizing", "weighted_net_return", {"formula": "position_weight * unweighted_net_return"}, "headline net_return_* uses weighted_net_return"),
        ("execution", "close_signal_next_open", config["execution"], "signal at close, execute first executable next open"),
        ("price_adjustment", "qlib_adjusted_ohlc_fields", config["price_provider"], "Qlib adjusted OHLC interpreted as executable adjusted prices"),
        ("censored", "status_set", {"statuses": ["replay_complete", "censored_by_split_boundary", "censored_by_missing_price", "censored_by_missing_required_indicator", "censored_by_suspension_or_dirty_bar", "censored_by_no_exit_execution", "invalid_entry"]}, "headline uses replay_complete only"),
        ("max_gain50_retention", "hold120", {"threshold": config["thresholds"]["max_gain50_threshold"]}, "policy_exit_execution_date > hold120_first_plus50_hit_date"),
        ("baseline_delta", "hold120_no_exit_fixed_size", {"baseline_policy_id": config["baseline"]["hold120_baseline_policy_id"]}, "same split / same subgroup baseline comparisons"),
    ]
    out = pd.DataFrame(
        [
            {
                "spec_section": section,
                "spec_item": item,
                "frozen_value_json": _canonical_json(value),
                "formula_text": formula,
                "source_config_key": section,
                "formula_hash": _hash_json({"section": section, "item": item, "value": value, "formula": formula}),
            }
            for section, item, value, formula in rows
        ]
    )
    return out


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for directory in [cache_dir, reports_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    upstream_validation = _read_json(Path(config["upstream_r04"]["validation"]))
    if upstream_validation.get("validation_status") != "passed":
        decision = "blocked_upstream_r04_validation_failed"
        manifest = {"final_decision": decision, "validation_status": "not_run", "reason": "upstream R04 validation not passed"}
        write_json(manifest, manifests_dir / "r04b_fixed_entry_hold_exit_risk_budget_cta_manifest.json")
        return manifest

    candidate_preview = pd.read_parquet(topic_path(config["upstream_r04"]["candidate_panel"]), columns=["instrument_id", "entry_execution_date", "r04_inclusion_status", "split"])
    candidate_preview = candidate_preview[candidate_preview["r04_inclusion_status"].astype(str).eq("included")]
    candidate_preview["entry_execution_date"] = pd.to_datetime(candidate_preview["entry_execution_date"]).dt.normalize()
    calendar = _load_calendar(config["price_provider"]["calendar_source_path"])
    lookback = int(config["execution"]["pre_entry_lookback_trading_days"])
    max_forward = int(config["execution"]["max_holding_days"]) + int(config["execution"]["max_exit_execution_lag_trading_days"])
    start = _add_trading_days(calendar, candidate_preview["entry_execution_date"].min(), -lookback)
    end = _add_trading_days(calendar, candidate_preview["entry_execution_date"].max(), max_forward)
    instruments = sorted(candidate_preview["instrument_id"].astype(str).str.upper().unique().tolist())
    price = _load_price_panel(config, instruments, start, end, calendar)
    base, input_reconciliation = _load_candidates(config, price, calendar)
    mismatch_share = input_reconciliation["excluded_entry_price_mismatch"] / input_reconciliation["policy_replay_eligible_rows"].replace(0, np.nan)
    gate0_blocked = bool((mismatch_share > float(config["candidate"]["max_split_entry_price_mismatch_share"])).any())

    policy_matrix = _build_policy_matrix(config)
    gate0_spec = _gate0_spec(config)
    daily_path = _build_daily_path(base, price, config)
    base = _attach_hold120_labels(base, daily_path, float(config["thresholds"]["max_gain50_threshold"]))
    replay = _replay_policies(base, daily_path, policy_matrix, config)
    summary = _summarize_policy(replay, config)
    selection_trace, selection_panel, selected_policy_id, selected_family_id = _selection(summary, policy_matrix, config)
    final_decision, robustness = _final_decision(summary, selected_policy_id, config)
    if gate0_blocked:
        final_decision = "blocked_gate0_metric_replay_spec_failed"

    write_csv(gate0_spec, reports_dir / "r04b_gate0_metric_replay_spec_frozen.csv")
    write_csv(input_reconciliation, reports_dir / "r04b_input_reconciliation_audit.csv")
    write_csv(policy_matrix, reports_dir / "r04b_policy_matrix_frozen.csv")
    write_csv(selection_trace, reports_dir / "r04b_policy_selection_trace.csv")
    _write_parquet(base, cache_dir / "r04b_candidate_replay_base_panel.parquet")
    _write_parquet(daily_path, cache_dir / "r04b_daily_policy_path_panel.parquet")
    _write_parquet(replay, cache_dir / "r04b_policy_replay_panel.parquet")
    _write_parquet(selection_panel, cache_dir / "r04b_policy_selection_panel.parquet")
    interaction_panel = _interaction_audit(replay, config)
    _write_parquet(interaction_panel, cache_dir / "r04b_subgroup_interaction_panel.parquet")
    _reports(config, base, policy_matrix, summary, replay, selection_trace, selected_policy_id, final_decision, output_root)

    artifacts = list(cache_dir.glob("*.parquet")) + list(reports_dir.glob("*.csv")) + [reports_dir / "r04b_fixed_entry_hold_exit_risk_budget_cta_final_report.md"]
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "config_path": relpath(topic_path(config_path)),
        "requirement_path": config["requirement_path"],
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "final_decision": final_decision,
        "selected_policy_id": selected_policy_id,
        "selected_policy_family_id": selected_family_id,
        "candidate_event_count": int(len(base)),
        "policy_matrix_rows": int(len(policy_matrix)),
        "valid_policy_rows": int(policy_matrix["invalid_policy_reason"].fillna("").eq("").sum()),
        "price_source_path": config["price_provider"]["price_source_path"],
        "price_source_hash": _price_source_hash(config, instruments),
        "calendar_source_path": config["price_provider"]["calendar_source_path"],
        "calendar_source_hash": _hash_file(topic_path(config["price_provider"]["calendar_source_path"])),
        "adjustment_policy": config["price_provider"]["adjustment_policy"],
        "cost_model": config["cost_model"],
        "cost_model_hash": _hash_json(config["cost_model"]),
        "artifact_hashes": _artifact_hashes(artifacts),
    }
    write_json(manifest, manifests_dir / "r04b_fixed_entry_hold_exit_risk_budget_cta_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EP4 R04b fixed-entry hold/exit/risk-budget CTA diagnostic.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    manifest = run(Path(args.config))
    print(json.dumps({"final_decision": manifest.get("final_decision"), "selected_policy_id": manifest.get("selected_policy_id")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

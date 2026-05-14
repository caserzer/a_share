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
TOPIC_DIR = EP4_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import (  # noqa: E402
    load_config as load_r01_config,
    load_provider_spine,
    prepare_stock_day_panel,
    relpath,
    topic_path,
    write_csv,
    write_json,
)
from run_r02_big_winner_coverage_ratio_search import enrich_features  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_family_signal_120d_path_query_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
ATR_OFFSETS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]
FIXED_RETURN_OFFSETS = [1, 3, 5, 10, 20, 40, 60, 120]
EXCURSION_OFFSETS = [5, 10, 20, 40, 60, 120]
RACE_STATUSES = {
    "upside_first",
    "downside_first",
    "same_offset",
    "upside_only_complete",
    "downside_only_complete",
    "neither_hit_complete",
    "censored_incomplete",
}
R03_THRESHOLDS = {
    "min_episode_count_for_handoff": 200,
    "min_path_complete_rate": 0.70,
    "min_atr_usable_rate_for_atr_evidence": 0.80,
    "continue_min_hit_plus10_before_minus5_rate": 0.45,
    "continue_max_early_failure_rate": 0.35,
    "continue_max_severe_drawdown_rate": 0.55,
    "continue_min_close_return_t20_p50": 0.00,
    "stop_min_early_failure_rate": 0.55,
    "stop_max_hit_plus10_before_minus5_rate": 0.30,
    "background_max_episode_count": 199,
}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_json(value: Any, n: int = 16) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()[:n]


def _finite_positive(value: Any) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return bool(np.isfinite(numeric) and numeric > 0.0)


def _normalize_condition(text: str) -> str:
    return " ".join(str(text).strip().split())


def load_config(config_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cfg_path = topic_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    r01_config, _, ep2_config = load_r01_config(topic_path(config["upstream_r01"]["config"]))
    return config, r01_config, ep2_config


def validate_signal_lineage(config: dict[str, Any]) -> pd.DataFrame:
    all_results_path = topic_path(config["upstream_r02_coverage"]["all_results"])
    all_results = pd.read_csv(all_results_path)
    indexed = all_results.set_index("condition_group_id")
    rows: list[dict[str, Any]] = []
    for item in config["single_signals"]:
        condition_group_id = item["condition_group_id"]
        if condition_group_id not in indexed.index:
            raise RuntimeError(f"missing upstream condition_group_id: {condition_group_id}")
        upstream = indexed.loc[condition_group_id]
        if _normalize_condition(upstream["condition_text"]) != _normalize_condition(item["condition_text"]):
            raise RuntimeError(f"condition text drift for {condition_group_id}")
        descriptor = item["source_descriptors"]
        coverage_pct = float(upstream["coverage_t0_t30"]) * 100.0
        density_pct = float(upstream["eligible_day_density"]) * 100.0
        median_first_hit = float(upstream["median_earliest_hit_offset"])
        for label, actual, expected, tolerance in [
            ("coverage_pct", coverage_pct, float(descriptor["coverage_pct"]), 0.01),
            ("density_pct", density_pct, float(descriptor["density_pct"]), 0.01),
            ("median_first_hit", median_first_hit, float(descriptor["median_first_hit"]), 0.01),
        ]:
            if abs(actual - expected) > tolerance:
                raise RuntimeError(
                    f"source descriptor drift for {condition_group_id} {label}: "
                    f"upstream={actual:.6f}, config={expected:.6f}"
                )
        rows.append(
            {
                "signal_id": item["signal_id"],
                "signal_type": "single_family",
                "family_id": item["family_id"],
                "condition_group_id": condition_group_id,
                "required_family_set": "",
                "condition_text": item["condition_text"],
                "source_coverage_pct": float(descriptor["coverage_pct"]),
                "source_density_pct": float(descriptor["density_pct"]),
                "source_mean_first_hit": float(descriptor["mean_first_hit"]),
                "source_median_first_hit": float(descriptor["median_first_hit"]),
                "source_split_stability": descriptor["split_stability"],
                "upstream_coverage_t0_t30": float(upstream["coverage_t0_t30"]),
                "upstream_eligible_day_density": float(upstream["eligible_day_density"]),
                "upstream_median_earliest_hit_offset": float(upstream["median_earliest_hit_offset"]),
                "lineage_check_status": "passed",
            }
        )
    for item in config["review_composite_signals"]:
        rows.append(
            {
                "signal_id": item["signal_id"],
                "signal_type": "same_day_family_and4",
                "family_id": "",
                "condition_group_id": "",
                "required_family_set": "|".join(item["required_family_set"]),
                "condition_text": " AND ".join(item["required_family_set"]),
                "source_coverage_pct": np.nan,
                "source_density_pct": np.nan,
                "source_mean_first_hit": np.nan,
                "source_median_first_hit": np.nan,
                "source_split_stability": "",
                "upstream_coverage_t0_t30": np.nan,
                "upstream_eligible_day_density": np.nan,
                "upstream_median_earliest_hit_offset": np.nan,
                "lineage_check_status": "not_applicable_composite",
            }
        )
    return pd.DataFrame(rows).sort_values(["signal_type", "signal_id"]).reset_index(drop=True)


def load_stock(config: dict[str, Any], r01_config: dict[str, Any], ep2_config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    panel, calendar = load_provider_spine(r01_config, ep2_config)
    stock = prepare_stock_day_panel(r01_config, ep2_config, panel, calendar)
    stock = enrich_features(stock, [int(v) for v in config["allowed_windows"]])
    stock = add_wilder_atr(stock, int(config["atr"]["period"]))
    stock = stock.sort_values(["instrument", "date"]).reset_index(drop=True)
    return stock, calendar


def add_wilder_atr(stock: pd.DataFrame, period: int) -> pd.DataFrame:
    out = stock.sort_values(["instrument", "date"]).reset_index(drop=True).copy()
    group = out.groupby("instrument", group_keys=False)
    prev_close = group["close"].shift(1)
    true_range = pd.concat(
        [(out["high"] - out["low"]).abs(), (out["high"] - prev_close).abs(), (out["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    out[f"tr_for_atr{period}"] = true_range
    out[f"atr{period}_wilder"] = np.nan
    for _, idx in out.groupby("instrument", sort=False).groups.items():
        idx_arr = np.asarray(list(idx), dtype=int)
        tr = out.loc[idx_arr, f"tr_for_atr{period}"].to_numpy(dtype=float)
        atr = np.full(len(tr), np.nan, dtype=float)
        for i in range(period - 1, len(tr)):
            window = tr[i - period + 1 : i + 1]
            if np.isfinite(window).all():
                atr[i] = float(window.mean())
                start = i + 1
                break
        else:
            out.loc[idx_arr, f"atr{period}_wilder"] = atr
            continue
        for i in range(start, len(tr)):
            if np.isfinite(tr[i]) and np.isfinite(atr[i - 1]):
                atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        out.loc[idx_arr, f"atr{period}_wilder"] = atr
    out[f"atr{period}_pct_wilder"] = out[f"atr{period}_wilder"] / out["close"]
    return out


def _eval_term(series: pd.Series, operator: str, threshold: float) -> pd.Series:
    if operator == ">=":
        return series >= threshold
    if operator == ">":
        return series > threshold
    if operator == "<=":
        return series <= threshold
    if operator == "<":
        return series < threshold
    if operator == "==":
        return series == threshold
    raise ValueError(f"unsupported operator: {operator}")


def build_signal_events(stock: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, int]]:
    base_mask = (
        stock["split"].isin(SPLITS)
        & stock["eligible_stock_day"].astype(bool)
        & np.isfinite(pd.to_numeric(stock["close"], errors="coerce"))
    )
    base = stock.loc[base_mask].copy()
    base["signal_date"] = pd.to_datetime(base["date"]).dt.normalize()
    family_masks: dict[str, pd.Series] = {}
    rows: list[pd.DataFrame] = []
    signal_counts: dict[str, int] = {}
    for item in config["single_signals"]:
        complete = pd.Series(True, index=base.index)
        signal = pd.Series(True, index=base.index)
        for term in item["terms"]:
            feature = term["feature"]
            if feature not in base.columns:
                raise RuntimeError(f"feature column missing for frozen condition: {feature}")
            series = pd.to_numeric(base[feature], errors="coerce")
            complete &= series.notna() & np.isfinite(series)
            signal &= _eval_term(series, term["operator"], float(term["threshold"])).fillna(False)
        mask = complete & signal
        family_masks[item["family_id"]] = mask
        event = base.loc[mask, ["instrument", "signal_date", "split"]].copy()
        event = event.rename(columns={"instrument": "instrument_id"})
        event["signal_id"] = item["signal_id"]
        event["signal_type"] = "single_family"
        event["family_id"] = item["family_id"]
        event["required_family_set"] = ""
        rows.append(event)
        signal_counts[item["signal_id"]] = int(mask.sum())
    for item in config["review_composite_signals"]:
        composite = pd.Series(True, index=base.index)
        for family_id in item["required_family_set"]:
            if family_id not in family_masks:
                raise RuntimeError(f"composite references unknown family: {family_id}")
            composite &= family_masks[family_id]
        event = base.loc[composite, ["instrument", "signal_date", "split"]].copy()
        event = event.rename(columns={"instrument": "instrument_id"})
        event["signal_id"] = item["signal_id"]
        event["signal_type"] = "same_day_family_and4"
        event["family_id"] = ""
        event["required_family_set"] = "|".join(item["required_family_set"])
        rows.append(event)
        signal_counts[item["signal_id"]] = int(composite.sum())
    events = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return events.sort_values(["signal_id", "instrument_id", "signal_date"]).reset_index(drop=True), signal_counts


def _empty_path_metrics() -> dict[str, Any]:
    payload = {
        "path_complete_120d": False,
        "available_forward_trading_days": 0,
        "path_incomplete_reason": "",
        "first_minus5_date": pd.NA,
        "first_minus5_offset": np.nan,
        "first_minus5_low_return": np.nan,
        "first_minus5_hit_flag": False,
        "first_close_minus5_date": pd.NA,
        "first_close_minus5_offset": np.nan,
        "first_close_minus5_return": np.nan,
        "first_close_minus5_hit_flag": False,
        "max_gain_120d": np.nan,
        "max_gain_date": pd.NA,
        "max_gain_offset": np.nan,
        "max_loss_120d": np.nan,
        "max_loss_date": pd.NA,
        "max_loss_offset": np.nan,
        "max_drawdown_120d": np.nan,
        "max_drawdown_start_date": pd.NA,
        "max_drawdown_end_date": pd.NA,
        "max_drawdown_start_offset": np.nan,
        "max_drawdown_end_offset": np.nan,
        "max_drawdown_peak_price": np.nan,
        "max_drawdown_trough_price": np.nan,
        "max_drawdown_trough_return_from_entry": np.nan,
        "max_drawdown_ohlc_order_policy": "prior_peak_only",
        "atr_missing_offsets": "",
    }
    for offset in ATR_OFFSETS:
        payload[f"atr14_t{offset}"] = np.nan
        payload[f"atr14_pct_t{offset}"] = np.nan
    for offset in FIXED_RETURN_OFFSETS:
        payload[f"close_return_t{offset}"] = np.nan
    for offset in EXCURSION_OFFSETS:
        payload[f"mae_low_t{offset}"] = np.nan
        payload[f"mfe_high_t{offset}"] = np.nan
        payload[f"mae_atr_t{offset}"] = np.nan
        payload[f"mfe_atr_t{offset}"] = np.nan
    payload.update(
        {
            "first_plus5_date": pd.NA,
            "first_plus5_offset": np.nan,
            "first_plus5_high_return": np.nan,
            "first_plus5_hit_flag": False,
            "first_plus10_date": pd.NA,
            "first_plus10_offset": np.nan,
            "first_plus10_high_return": np.nan,
            "first_plus10_hit_flag": False,
            "first_plus20_date": pd.NA,
            "first_plus20_offset": np.nan,
            "first_plus20_high_return": np.nan,
            "first_plus20_hit_flag": False,
            "first_minus10_date": pd.NA,
            "first_minus10_offset": np.nan,
            "first_minus10_low_return": np.nan,
            "first_minus10_hit_flag": False,
            "hit_plus5_before_minus5": pd.NA,
            "hit_plus10_before_minus5": pd.NA,
            "hit_plus20_before_minus10": pd.NA,
            "minus5_before_plus10": pd.NA,
            "race_plus5_minus5_status": pd.NA,
            "race_plus10_minus5_status": pd.NA,
            "race_plus20_minus10_status": pd.NA,
            "max_loss_before_first_plus10": np.nan,
            "max_loss_before_first_plus10_offset": np.nan,
            "max_loss_before_first_plus10_censored": pd.NA,
            "max_drawdown_before_first_plus20": np.nan,
            "max_drawdown_before_first_plus20_end_offset": np.nan,
            "max_drawdown_before_first_plus20_eval_end_offset": np.nan,
            "max_drawdown_before_first_plus20_censored": pd.NA,
            "days_close_below_entry_120d": np.nan,
            "share_days_close_below_entry_120d": np.nan,
            "max_consecutive_days_close_below_entry_120d": np.nan,
            "first_recover_entry_date": pd.NA,
            "first_recover_entry_offset": np.nan,
            "close_t120_above_entry_flag": pd.NA,
            "peak_to_t120_giveback": np.nan,
            "close_return_20d_after_max_gain": np.nan,
            "path_quality_flag": "incomplete",
            "early_failure_flag": pd.NA,
            "tradable_continuation_flag": pd.NA,
            "transient_spike_flag": pd.NA,
            "severe_drawdown_flag": pd.NA,
            "whipsaw_after_profit_flag": pd.NA,
            "clean_continuation_flag": pd.NA,
            "late_drawdown_flag": pd.NA,
            "incomplete_flag": True,
        }
    )
    return payload


def _first_threshold_hit(
    values: np.ndarray,
    positions: np.ndarray,
    entry_pos: int,
    entry_price: float,
    threshold: float,
    direction: str,
    dates: np.ndarray,
) -> dict[str, Any]:
    returns = values / entry_price - 1.0
    if direction == "up":
        hits = np.flatnonzero(np.isfinite(returns) & (returns >= threshold))
    elif direction == "down":
        hits = np.flatnonzero(np.isfinite(returns) & (returns <= threshold))
    else:
        raise ValueError(direction)
    if not len(hits):
        return {"hit": False, "date": pd.NA, "offset": np.nan, "return": np.nan, "pos": None}
    idx = int(hits[0])
    pos = int(positions[idx])
    return {
        "hit": True,
        "date": pd.Timestamp(dates[pos]).date().isoformat(),
        "offset": int(pos - entry_pos),
        "return": float(returns[idx]),
        "pos": pos,
    }


def _race_status(up: dict[str, Any], down: dict[str, Any], path_complete: bool) -> str:
    if up["hit"] and down["hit"]:
        if int(up["offset"]) < int(down["offset"]):
            return "upside_first"
        if int(up["offset"]) > int(down["offset"]):
            return "downside_first"
        return "same_offset"
    if up["hit"] and not down["hit"]:
        return "upside_only_complete" if path_complete else "censored_incomplete"
    if down["hit"] and not up["hit"]:
        return "downside_only_complete" if path_complete else "censored_incomplete"
    return "neither_hit_complete" if path_complete else "censored_incomplete"


def _race_bool(status: str) -> Any:
    if status in {"upside_first", "upside_only_complete"}:
        return True
    if status in {"downside_first", "downside_only_complete", "neither_hit_complete"}:
        return False
    return pd.NA


def _first_executable_entry(arrays: dict[str, np.ndarray], signal_pos: int) -> tuple[int | None, str]:
    dates = arrays["date"]
    n = len(dates)
    for pos in range(signal_pos + 1, n):
        prev_pos = pos - 1
        if not bool(arrays["is_buy_executable_next_open"][prev_pos]):
            continue
        if not _finite_positive(arrays["open"][pos]):
            continue
        if "not_suspended_or_dirty_bar" in arrays and not bool(arrays["not_suspended_or_dirty_bar"][pos]):
            continue
        if "eligible_stock_day" in arrays and not bool(arrays["eligible_stock_day"][pos]):
            continue
        return pos, ""
    return None, "no_executable_entry_after_signal"


def _compute_one_path(arrays: dict[str, np.ndarray], signal_pos: int, signal_split: str, horizon: int, atr_period: int) -> dict[str, Any]:
    entry_pos, invalid_reason = _first_executable_entry(arrays, signal_pos)
    if entry_pos is None:
        payload = _empty_path_metrics()
        payload.update({"entry_date": pd.NA, "entry_price": np.nan, "entry_valid": False, "entry_invalid_reason": invalid_reason})
        return payload

    entry_price = float(arrays["open"][entry_pos])
    dates = arrays["date"]
    split = arrays["split"]
    high = arrays["high"].astype(float)
    low = arrays["low"].astype(float)
    close = arrays["close"].astype(float)
    atr = arrays[f"atr{atr_period}_wilder"].astype(float)
    atr_pct = arrays[f"atr{atr_period}_pct_wilder"].astype(float)
    n = len(dates)
    available = max(0, min(horizon, n - entry_pos - 1))
    end_pos = entry_pos + available
    same_split_complete = available >= horizon and str(split[entry_pos + horizon]) == signal_split
    path_complete = bool(same_split_complete)
    if available < horizon:
        incomplete_reason = "insufficient_forward_trading_days"
    elif not same_split_complete:
        incomplete_reason = "split_boundary"
    else:
        incomplete_reason = ""
    metric_end = entry_pos + min(available, horizon)
    positions = np.arange(entry_pos, metric_end + 1, dtype=int)

    payload = _empty_path_metrics()
    payload.update(
        {
            "entry_date": pd.Timestamp(dates[entry_pos]).date().isoformat(),
            "entry_price": entry_price,
            "entry_valid": True,
            "entry_invalid_reason": "",
            "path_complete_120d": path_complete,
            "available_forward_trading_days": int(available),
            "path_incomplete_reason": incomplete_reason,
        }
    )
    if len(positions) == 0:
        return payload

    lows = low[positions]
    highs = high[positions]
    closes = close[positions]
    low_returns = lows / entry_price - 1.0
    close_returns = closes / entry_price - 1.0
    hit_idx = np.flatnonzero(np.isfinite(low_returns) & (low_returns <= -0.05))
    if len(hit_idx):
        pos = int(positions[hit_idx[0]])
        payload.update(
            {
                "first_minus5_date": pd.Timestamp(dates[pos]).date().isoformat(),
                "first_minus5_offset": int(pos - entry_pos),
                "first_minus5_low_return": float(low[pos] / entry_price - 1.0),
                "first_minus5_hit_flag": True,
            }
        )
    close_hit_idx = np.flatnonzero(np.isfinite(close_returns) & (close_returns <= -0.05))
    if len(close_hit_idx):
        pos = int(positions[close_hit_idx[0]])
        payload.update(
            {
                "first_close_minus5_date": pd.Timestamp(dates[pos]).date().isoformat(),
                "first_close_minus5_offset": int(pos - entry_pos),
                "first_close_minus5_return": float(close[pos] / entry_price - 1.0),
                "first_close_minus5_hit_flag": True,
            }
        )

    plus5 = _first_threshold_hit(highs, positions, entry_pos, entry_price, 0.05, "up", dates)
    plus10 = _first_threshold_hit(highs, positions, entry_pos, entry_price, 0.10, "up", dates)
    plus20 = _first_threshold_hit(highs, positions, entry_pos, entry_price, 0.20, "up", dates)
    minus5 = {
        "hit": bool(payload["first_minus5_hit_flag"]),
        "date": payload["first_minus5_date"],
        "offset": payload["first_minus5_offset"],
        "return": payload["first_minus5_low_return"],
        "pos": entry_pos + int(payload["first_minus5_offset"]) if payload["first_minus5_hit_flag"] else None,
    }
    minus10 = _first_threshold_hit(lows, positions, entry_pos, entry_price, -0.10, "down", dates)
    payload.update(
        {
            "first_plus5_date": plus5["date"],
            "first_plus5_offset": plus5["offset"],
            "first_plus5_high_return": plus5["return"],
            "first_plus5_hit_flag": plus5["hit"],
            "first_plus10_date": plus10["date"],
            "first_plus10_offset": plus10["offset"],
            "first_plus10_high_return": plus10["return"],
            "first_plus10_hit_flag": plus10["hit"],
            "first_plus20_date": plus20["date"],
            "first_plus20_offset": plus20["offset"],
            "first_plus20_high_return": plus20["return"],
            "first_plus20_hit_flag": plus20["hit"],
            "first_minus10_date": minus10["date"],
            "first_minus10_offset": minus10["offset"],
            "first_minus10_low_return": minus10["return"],
            "first_minus10_hit_flag": minus10["hit"],
        }
    )
    race_plus5_minus5 = _race_status(plus5, minus5, path_complete)
    race_plus10_minus5 = _race_status(plus10, minus5, path_complete)
    race_plus20_minus10 = _race_status(plus20, minus10, path_complete)
    payload.update(
        {
            "race_plus5_minus5_status": race_plus5_minus5,
            "race_plus10_minus5_status": race_plus10_minus5,
            "race_plus20_minus10_status": race_plus20_minus10,
            "hit_plus5_before_minus5": _race_bool(race_plus5_minus5),
            "hit_plus10_before_minus5": _race_bool(race_plus10_minus5),
            "hit_plus20_before_minus10": _race_bool(race_plus20_minus10),
            "minus5_before_plus10": True
            if race_plus10_minus5 in {"downside_first", "downside_only_complete"}
            else False
            if race_plus10_minus5 in {"upside_first", "upside_only_complete", "neither_hit_complete"}
            else pd.NA,
        }
    )

    finite_high = np.isfinite(highs)
    if finite_high.any():
        rel = np.where(finite_high, highs / entry_price - 1.0, -np.inf)
        max_i = int(np.argmax(rel))
        pos = int(positions[max_i])
        payload.update({"max_gain_120d": float(rel[max_i]), "max_gain_date": pd.Timestamp(dates[pos]).date().isoformat(), "max_gain_offset": int(pos - entry_pos)})
    finite_low = np.isfinite(lows)
    if finite_low.any():
        rel = np.where(finite_low, lows / entry_price - 1.0, np.inf)
        min_i = int(np.argmin(rel))
        pos = int(positions[min_i])
        payload.update({"max_loss_120d": float(rel[min_i]), "max_loss_date": pd.Timestamp(dates[pos]).date().isoformat(), "max_loss_offset": int(pos - entry_pos)})

    peak_price = entry_price
    peak_pos = entry_pos
    best_dd = np.inf
    best: dict[str, Any] | None = None
    for pos in positions:
        if np.isfinite(low[pos]) and np.isfinite(peak_price) and peak_price > 0:
            dd = float(low[pos] / peak_price - 1.0)
            if dd < best_dd:
                best_dd = dd
                best = {
                    "max_drawdown_120d": dd,
                    "max_drawdown_start_date": pd.Timestamp(dates[peak_pos]).date().isoformat(),
                    "max_drawdown_end_date": pd.Timestamp(dates[pos]).date().isoformat(),
                    "max_drawdown_start_offset": int(peak_pos - entry_pos),
                    "max_drawdown_end_offset": int(pos - entry_pos),
                    "max_drawdown_peak_price": float(peak_price),
                    "max_drawdown_trough_price": float(low[pos]),
                    "max_drawdown_trough_return_from_entry": float(low[pos] / entry_price - 1.0),
                }
        if np.isfinite(high[pos]) and high[pos] > peak_price:
            peak_price = float(high[pos])
            peak_pos = int(pos)
    if best:
        payload.update(best)

    for offset in FIXED_RETURN_OFFSETS:
        pos = entry_pos + offset
        if pos <= end_pos and pos < n and str(split[pos]) == signal_split and np.isfinite(close[pos]):
            payload[f"close_return_t{offset}"] = float(close[pos] / entry_price - 1.0)

    atr0_pct = float(atr_pct[entry_pos]) if entry_pos < n and np.isfinite(atr_pct[entry_pos]) and atr_pct[entry_pos] > 0 else np.nan
    for offset in EXCURSION_OFFSETS:
        offset_end = min(offset, available)
        if offset_end < 0:
            continue
        window_pos = np.arange(entry_pos, entry_pos + offset_end + 1, dtype=int)
        window_lows = low[window_pos]
        window_highs = high[window_pos]
        if len(window_lows) and np.isfinite(window_lows).any():
            mae = float(np.nanmin(window_lows / entry_price - 1.0))
            payload[f"mae_low_t{offset}"] = mae
            if np.isfinite(atr0_pct):
                payload[f"mae_atr_t{offset}"] = mae / atr0_pct
        if len(window_highs) and np.isfinite(window_highs).any():
            mfe = float(np.nanmax(window_highs / entry_price - 1.0))
            payload[f"mfe_high_t{offset}"] = mfe
            if np.isfinite(atr0_pct):
                payload[f"mfe_atr_t{offset}"] = mfe / atr0_pct

    plus10_end_pos = int(plus10["pos"]) if plus10["hit"] else metric_end
    if plus10_end_pos >= entry_pos:
        window_pos = np.arange(entry_pos, plus10_end_pos + 1, dtype=int)
        rel = low[window_pos] / entry_price - 1.0
        if np.isfinite(rel).any():
            min_value = float(np.nanmin(rel))
            first_idx = int(np.flatnonzero(np.isfinite(rel) & np.isclose(rel, min_value, rtol=0, atol=1e-12))[0])
            payload["max_loss_before_first_plus10"] = min_value
            payload["max_loss_before_first_plus10_offset"] = int(window_pos[first_idx] - entry_pos)
            payload["max_loss_before_first_plus10_censored"] = not bool(plus10["hit"])

    plus20_eval_end_pos = int(plus20["pos"]) if plus20["hit"] else metric_end
    if plus20_eval_end_pos >= entry_pos:
        payload["max_drawdown_before_first_plus20_eval_end_offset"] = int(plus20_eval_end_pos - entry_pos)
        dd_best = np.inf
        dd_best_pos: int | None = None
        local_peak = entry_price
        for pos in np.arange(entry_pos, plus20_eval_end_pos + 1, dtype=int):
            if np.isfinite(low[pos]) and np.isfinite(local_peak) and local_peak > 0:
                dd = float(low[pos] / local_peak - 1.0)
                if dd < dd_best:
                    dd_best = dd
                    dd_best_pos = int(pos)
            if np.isfinite(high[pos]) and high[pos] > local_peak:
                local_peak = float(high[pos])
        if dd_best_pos is not None:
            payload["max_drawdown_before_first_plus20"] = float(dd_best)
            payload["max_drawdown_before_first_plus20_end_offset"] = int(dd_best_pos - entry_pos)
            payload["max_drawdown_before_first_plus20_censored"] = not bool(plus20["hit"])

    missing_offsets: list[str] = []
    for offset in ATR_OFFSETS:
        pos = entry_pos + int(offset)
        if pos <= end_pos and pos < n and str(split[pos]) == signal_split and np.isfinite(atr[pos]):
            payload[f"atr14_t{offset}"] = float(atr[pos])
            payload[f"atr14_pct_t{offset}"] = float(atr_pct[pos]) if np.isfinite(atr_pct[pos]) else np.nan
        else:
            missing_offsets.append(str(offset))
    payload["atr_missing_offsets"] = "|".join(missing_offsets)

    below = np.isfinite(closes) & (closes < entry_price)
    payload["days_close_below_entry_120d"] = int(below.sum())
    payload["share_days_close_below_entry_120d"] = float(below.sum() / len(positions)) if len(positions) else np.nan
    max_streak = streak = 0
    for value in below:
        streak = streak + 1 if bool(value) else 0
        max_streak = max(max_streak, streak)
    payload["max_consecutive_days_close_below_entry_120d"] = int(max_streak)
    below_idx = np.flatnonzero(below)
    if len(below_idx):
        recover_idx = np.flatnonzero(np.isfinite(closes[below_idx[0] + 1 :]) & (closes[below_idx[0] + 1 :] >= entry_price))
        if len(recover_idx):
            pos = int(positions[below_idx[0] + 1 + recover_idx[0]])
            payload["first_recover_entry_date"] = pd.Timestamp(dates[pos]).date().isoformat()
            payload["first_recover_entry_offset"] = int(pos - entry_pos)
    if "close_return_t120" in payload and np.isfinite(payload["close_return_t120"]):
        payload["close_t120_above_entry_flag"] = bool(payload["close_return_t120"] >= 0)
        if np.isfinite(payload["max_gain_120d"]):
            max_high_price = entry_price * (1.0 + float(payload["max_gain_120d"]))
            if max_high_price > 0:
                payload["peak_to_t120_giveback"] = float((entry_price * (1.0 + payload["close_return_t120"])) / max_high_price - 1.0)
    if np.isfinite(payload["max_gain_offset"]):
        max_gain_pos = entry_pos + int(payload["max_gain_offset"])
        after_pos = max_gain_pos + 20
        if after_pos <= end_pos and after_pos < n and np.isfinite(close[after_pos]) and np.isfinite(close[max_gain_pos]) and close[max_gain_pos] > 0:
            payload["close_return_20d_after_max_gain"] = float(close[after_pos] / close[max_gain_pos] - 1.0)

    required_for_quality = [
        "path_complete_120d",
        "first_minus5_hit_flag",
        "hit_plus10_before_minus5",
        "close_return_t20",
        "max_gain_120d",
        "close_return_t120",
        "max_drawdown_120d",
        "first_plus10_hit_flag",
        "max_drawdown_before_first_plus20",
        "max_drawdown_end_offset",
    ]
    missing_quality_input = any(pd.isna(payload.get(key)) for key in required_for_quality)
    if payload["first_minus5_hit_flag"] and pd.isna(payload.get("first_minus5_offset")):
        missing_quality_input = True
    if payload["first_plus10_hit_flag"] and pd.isna(payload.get("first_plus10_offset")):
        missing_quality_input = True
    incomplete = (not path_complete) or missing_quality_input
    payload["incomplete_flag"] = bool(incomplete)
    payload["early_failure_flag"] = bool(payload["first_minus5_hit_flag"] and float(payload["first_minus5_offset"]) <= 10) if not pd.isna(payload["first_minus5_offset"]) else False
    payload["tradable_continuation_flag"] = bool(payload["hit_plus10_before_minus5"] is True and np.isfinite(payload["close_return_t20"]) and payload["close_return_t20"] >= 0)
    payload["transient_spike_flag"] = bool(np.isfinite(payload["max_gain_120d"]) and payload["max_gain_120d"] >= 0.20 and np.isfinite(payload["close_return_t120"]) and payload["close_return_t120"] < 0)
    payload["severe_drawdown_flag"] = bool(np.isfinite(payload["max_drawdown_120d"]) and payload["max_drawdown_120d"] <= -0.20)
    payload["whipsaw_after_profit_flag"] = bool(
        payload["first_plus10_hit_flag"]
        and payload["first_minus5_hit_flag"]
        and float(payload["first_plus10_offset"]) < float(payload["first_minus5_offset"])
        and float(payload["first_minus5_offset"]) <= float(payload["first_plus10_offset"]) + 20
    ) if not (pd.isna(payload["first_plus10_offset"]) or pd.isna(payload["first_minus5_offset"])) else False
    payload["clean_continuation_flag"] = bool(
        payload["hit_plus10_before_minus5"] is True
        and np.isfinite(payload["close_return_t20"])
        and payload["close_return_t20"] >= 0
        and np.isfinite(payload["max_drawdown_before_first_plus20"])
        and payload["max_drawdown_before_first_plus20"] > -0.10
    )
    payload["late_drawdown_flag"] = bool(
        payload["first_plus10_hit_flag"]
        and np.isfinite(payload["max_drawdown_120d"])
        and payload["max_drawdown_120d"] <= -0.20
        and np.isfinite(payload["max_drawdown_end_offset"])
        and float(payload["max_drawdown_end_offset"]) > float(payload["first_plus10_offset"])
    ) if not pd.isna(payload["first_plus10_offset"]) else False
    if incomplete:
        payload["path_quality_flag"] = "incomplete"
    elif payload["early_failure_flag"]:
        payload["path_quality_flag"] = "early_failure"
    elif payload["clean_continuation_flag"]:
        payload["path_quality_flag"] = "clean_continuation"
    elif payload["whipsaw_after_profit_flag"]:
        payload["path_quality_flag"] = "whipsaw_after_profit"
    elif payload["tradable_continuation_flag"]:
        payload["path_quality_flag"] = "tradable_continuation"
    elif payload["transient_spike_flag"]:
        payload["path_quality_flag"] = "transient_spike"
    elif payload["late_drawdown_flag"]:
        payload["path_quality_flag"] = "late_drawdown"
    elif payload["severe_drawdown_flag"]:
        payload["path_quality_flag"] = "severe_drawdown"
    else:
        payload["path_quality_flag"] = "mixed"
    return payload


def build_instrument_arrays(stock: pd.DataFrame, atr_period: int) -> dict[str, dict[str, np.ndarray]]:
    out: dict[str, dict[str, np.ndarray]] = {}
    cols = [
        "date",
        "split",
        "open",
        "high",
        "low",
        "close",
        "eligible_stock_day",
        "not_suspended_or_dirty_bar",
        "is_buy_executable_next_open",
        f"atr{atr_period}_wilder",
        f"atr{atr_period}_pct_wilder",
    ]
    for instrument, grp in stock.sort_values(["instrument", "date"]).groupby("instrument", sort=False):
        data = {col: grp[col].to_numpy() for col in cols if col in grp.columns}
        data["date_pos"] = {pd.Timestamp(value).normalize(): i for i, value in enumerate(data["date"])}
        out[str(instrument)] = data
    return out


def attach_path_metrics(events: pd.DataFrame, stock: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    horizon = int(config["path_horizon_trading_days"])
    atr_period = int(config["atr"]["period"])
    arrays_by_instrument = build_instrument_arrays(stock, atr_period)
    rows: list[dict[str, Any]] = []
    for row in events.itertuples(index=False):
        payload = row._asdict()
        signal_date = pd.Timestamp(payload["signal_date"]).normalize()
        instrument_id = str(payload["instrument_id"])
        arrays = arrays_by_instrument.get(instrument_id)
        if arrays is None or signal_date not in arrays["date_pos"]:
            metrics = _empty_path_metrics()
            metrics.update({"entry_date": pd.NA, "entry_price": np.nan, "entry_valid": False, "entry_invalid_reason": "signal_date_missing_from_stock"})
        else:
            metrics = _compute_one_path(arrays, int(arrays["date_pos"][signal_date]), str(payload["split"]), horizon, atr_period)
        payload.update(metrics)
        rows.append(payload)
    out = pd.DataFrame(rows)
    out["signal_date"] = pd.to_datetime(out["signal_date"]).dt.date.astype(str)
    return out.sort_values(["instrument_id", "signal_date", "signal_id"]).reset_index(drop=True)


def required_output_columns() -> list[str]:
    cols = [
        "signal_id",
        "signal_type",
        "family_id",
        "required_family_set",
        "instrument_id",
        "signal_date",
        "split",
        "entry_date",
        "entry_price",
        "entry_valid",
        "entry_invalid_reason",
        "path_complete_120d",
        "available_forward_trading_days",
        "path_incomplete_reason",
        "first_minus5_date",
        "first_minus5_offset",
        "first_minus5_low_return",
        "first_minus5_hit_flag",
        "first_close_minus5_date",
        "first_close_minus5_offset",
        "first_close_minus5_return",
        "first_close_minus5_hit_flag",
        "max_gain_120d",
        "max_gain_date",
        "max_gain_offset",
        "max_loss_120d",
        "max_loss_date",
        "max_loss_offset",
        "max_drawdown_120d",
        "max_drawdown_start_date",
        "max_drawdown_end_date",
        "max_drawdown_start_offset",
        "max_drawdown_end_offset",
        "max_drawdown_peak_price",
        "max_drawdown_trough_price",
        "max_drawdown_trough_return_from_entry",
        "max_drawdown_ohlc_order_policy",
        "atr_missing_offsets",
    ]
    for offset in ATR_OFFSETS:
        cols += [f"atr14_t{offset}", f"atr14_pct_t{offset}"]
    for offset in FIXED_RETURN_OFFSETS:
        cols.append(f"close_return_t{offset}")
    for offset in EXCURSION_OFFSETS:
        cols += [f"mae_low_t{offset}", f"mfe_high_t{offset}", f"mae_atr_t{offset}", f"mfe_atr_t{offset}"]
    cols += [
        "first_plus5_date",
        "first_plus5_offset",
        "first_plus5_high_return",
        "first_plus5_hit_flag",
        "first_plus10_date",
        "first_plus10_offset",
        "first_plus10_high_return",
        "first_plus10_hit_flag",
        "first_plus20_date",
        "first_plus20_offset",
        "first_plus20_high_return",
        "first_plus20_hit_flag",
        "first_minus10_date",
        "first_minus10_offset",
        "first_minus10_low_return",
        "first_minus10_hit_flag",
        "hit_plus5_before_minus5",
        "hit_plus10_before_minus5",
        "hit_plus20_before_minus10",
        "minus5_before_plus10",
        "race_plus5_minus5_status",
        "race_plus10_minus5_status",
        "race_plus20_minus10_status",
        "max_loss_before_first_plus10",
        "max_loss_before_first_plus10_offset",
        "max_loss_before_first_plus10_censored",
        "max_drawdown_before_first_plus20",
        "max_drawdown_before_first_plus20_end_offset",
        "max_drawdown_before_first_plus20_eval_end_offset",
        "max_drawdown_before_first_plus20_censored",
        "days_close_below_entry_120d",
        "share_days_close_below_entry_120d",
        "max_consecutive_days_close_below_entry_120d",
        "first_recover_entry_date",
        "first_recover_entry_offset",
        "close_t120_above_entry_flag",
        "peak_to_t120_giveback",
        "close_return_20d_after_max_gain",
        "path_quality_flag",
        "early_failure_flag",
        "tradable_continuation_flag",
        "transient_spike_flag",
        "severe_drawdown_flag",
        "whipsaw_after_profit_flag",
        "clean_continuation_flag",
        "late_drawdown_flag",
        "incomplete_flag",
    ]
    return cols


def build_episode_audits(path_events: pd.DataFrame, stock: pd.DataFrame) -> pd.DataFrame:
    date_pos_by_instrument: dict[str, dict[pd.Timestamp, int]] = {}
    for instrument, grp in stock.sort_values(["instrument", "date"]).groupby("instrument", sort=False):
        date_pos_by_instrument[str(instrument)] = {
            pd.Timestamp(value).normalize(): idx for idx, value in enumerate(pd.to_datetime(grp["date"]))
        }
    rows: list[dict[str, Any]] = []
    for (signal_id, instrument_id, split), grp in path_events.sort_values(["signal_id", "instrument_id", "split", "signal_date"]).groupby(
        ["signal_id", "instrument_id", "split"], sort=False
    ):
        date_pos = date_pos_by_instrument.get(str(instrument_id), {})
        current: list[pd.Series] = []
        previous_pos: int | None = None
        for _, row in grp.iterrows():
            pos = date_pos.get(pd.Timestamp(row["signal_date"]).normalize())
            starts_new = previous_pos is None or pos is None or previous_pos is None or pos != previous_pos + 1
            if starts_new and current:
                rows.append(_episode_row(current))
                current = []
            current.append(row)
            previous_pos = pos
        if current:
            rows.append(_episode_row(current))
    return pd.DataFrame(rows)


def _episode_row(rows: list[pd.Series]) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    valid_mask = frame["entry_valid"].astype(bool) if "entry_valid" in frame else pd.Series(False, index=frame.index)
    selected = frame.loc[valid_mask].iloc[0] if valid_mask.any() else frame.iloc[0]
    out = selected.to_dict()
    start_date = str(pd.to_datetime(frame["signal_date"]).min().date())
    end_date = str(pd.to_datetime(frame["signal_date"]).max().date())
    episode_id_payload = {
        "signal_id": selected["signal_id"],
        "instrument_id": selected["instrument_id"],
        "split": selected["split"],
        "episode_start_signal_date": start_date,
        "episode_end_signal_date": end_date,
    }
    out.update(
        {
            "episode_id": _hash_json(episode_id_payload, 16),
            "episode_start_signal_date": start_date,
            "episode_end_signal_date": end_date,
            "episode_trigger_count": int(len(frame)),
            "first_raw_signal_date": start_date,
            "last_raw_signal_date": end_date,
            "episode_entry_date": selected.get("entry_date", pd.NA),
            "episode_entry_price": selected.get("entry_price", np.nan),
            "episode_entry_valid": bool(selected.get("entry_valid", False)),
            "episode_entry_invalid_reason": selected.get("entry_invalid_reason", ""),
            "episode_path_quality_flag": selected.get("path_quality_flag", "incomplete"),
        }
    )
    if not out["episode_entry_valid"]:
        for col in required_output_columns():
            if col not in {"signal_id", "signal_type", "family_id", "required_family_set", "instrument_id", "signal_date", "split", "entry_date", "entry_price", "entry_valid", "entry_invalid_reason"}:
                out[col] = pd.NA
    return out


def _valid_subset(df: pd.DataFrame) -> pd.DataFrame:
    if "entry_valid" in df.columns:
        return df.loc[df["entry_valid"].astype(bool)].copy()
    if "episode_entry_valid" in df.columns:
        return df.loc[df["episode_entry_valid"].astype(bool)].copy()
    return df.iloc[0:0].copy()


def _truthy_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _rate(series: pd.Series, denom: int) -> float:
    if denom <= 0:
        return np.nan
    return float(_truthy_series(series).sum() / denom)


def _q(series: pd.Series, q: float) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.quantile(q)) if len(numeric) else np.nan


def summarize_path_quality(raw_events: pd.DataFrame, episode_events: pd.DataFrame, signal_dictionary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for grain, source in [("raw_trigger", raw_events), ("episode_first_trigger", episode_events)]:
        for item in signal_dictionary[["signal_id", "signal_type"]].itertuples(index=False):
            part = source.loc[source["signal_id"].eq(item.signal_id)].copy() if not source.empty else pd.DataFrame()
            valid = _valid_subset(part)
            row_count = int(len(part))
            valid_count = int(len(valid))
            complete_count = int(_truthy_series(valid["path_complete_120d"]).sum()) if valid_count and "path_complete_120d" in valid else 0
            atr_usable_count = int((pd.to_numeric(valid.get("atr14_pct_t0", pd.Series(dtype=float)), errors="coerce") > 0).sum()) if valid_count else 0
            atr_usable_rate = float(atr_usable_count / valid_count) if valid_count else np.nan
            atr_status = "usable" if np.isfinite(atr_usable_rate) and atr_usable_rate >= R03_THRESHOLDS["min_atr_usable_rate_for_atr_evidence"] else "low_coverage_audit_only"
            rows.append(
                {
                    "signal_id": item.signal_id,
                    "signal_type": item.signal_type,
                    "grain": grain,
                    "row_count": row_count,
                    "episode_count": row_count if grain == "episode_first_trigger" else np.nan,
                    "entry_valid_count": valid_count,
                    "path_complete_120d_count": complete_count,
                    "entry_invalid_rate": float((row_count - valid_count) / row_count) if row_count else np.nan,
                    "path_incomplete_rate": float((valid_count - complete_count) / valid_count) if valid_count else np.nan,
                    "atr_t0_missing_rate": float(1.0 - atr_usable_rate) if np.isfinite(atr_usable_rate) else np.nan,
                    "atr_t0_usable_count": atr_usable_count,
                    "atr_t0_usable_rate": atr_usable_rate,
                    "atr_evidence_status": atr_status,
                    "first_minus5_hit_rate": _rate(valid.get("first_minus5_hit_flag", pd.Series(dtype=bool)), valid_count),
                    "first_minus5_t10_rate": _rate((pd.to_numeric(valid.get("first_minus5_offset", pd.Series(dtype=float)), errors="coerce") <= 10), valid_count),
                    "first_plus10_hit_rate": _rate(valid.get("first_plus10_hit_flag", pd.Series(dtype=bool)), valid_count),
                    "hit_plus10_before_minus5_rate": _rate(valid.get("hit_plus10_before_minus5", pd.Series(dtype=bool)), valid_count),
                    "hit_plus20_before_minus10_rate": _rate(valid.get("hit_plus20_before_minus10", pd.Series(dtype=bool)), valid_count),
                    "race_plus10_minus5_censored_rate": _rate(valid.get("race_plus10_minus5_status", pd.Series(dtype=str)).eq("censored_incomplete"), valid_count),
                    "race_plus20_minus10_censored_rate": _rate(valid.get("race_plus20_minus10_status", pd.Series(dtype=str)).eq("censored_incomplete"), valid_count),
                    "early_failure_rate": _rate(valid.get("early_failure_flag", pd.Series(dtype=bool)), valid_count),
                    "clean_continuation_rate": _rate(valid.get("clean_continuation_flag", pd.Series(dtype=bool)), valid_count),
                    "whipsaw_after_profit_rate": _rate(valid.get("whipsaw_after_profit_flag", pd.Series(dtype=bool)), valid_count),
                    "tradable_continuation_rate": _rate(valid.get("tradable_continuation_flag", pd.Series(dtype=bool)), valid_count),
                    "transient_spike_rate": _rate(valid.get("transient_spike_flag", pd.Series(dtype=bool)), valid_count),
                    "late_drawdown_rate": _rate(valid.get("late_drawdown_flag", pd.Series(dtype=bool)), valid_count),
                    "severe_drawdown_rate": _rate(valid.get("severe_drawdown_flag", pd.Series(dtype=bool)), valid_count),
                    "close_return_t20_p25": _q(valid.get("close_return_t20", pd.Series(dtype=float)), 0.25),
                    "close_return_t20_p50": _q(valid.get("close_return_t20", pd.Series(dtype=float)), 0.50),
                    "close_return_t20_p75": _q(valid.get("close_return_t20", pd.Series(dtype=float)), 0.75),
                    "close_return_t60_p25": _q(valid.get("close_return_t60", pd.Series(dtype=float)), 0.25),
                    "close_return_t60_p50": _q(valid.get("close_return_t60", pd.Series(dtype=float)), 0.50),
                    "close_return_t60_p75": _q(valid.get("close_return_t60", pd.Series(dtype=float)), 0.75),
                    "close_return_t120_p25": _q(valid.get("close_return_t120", pd.Series(dtype=float)), 0.25),
                    "close_return_t120_p50": _q(valid.get("close_return_t120", pd.Series(dtype=float)), 0.50),
                    "close_return_t120_p75": _q(valid.get("close_return_t120", pd.Series(dtype=float)), 0.75),
                    "mae_low_t10_p50": _q(valid.get("mae_low_t10", pd.Series(dtype=float)), 0.50),
                    "mae_low_t20_p50": _q(valid.get("mae_low_t20", pd.Series(dtype=float)), 0.50),
                    "mae_low_t120_p50": _q(valid.get("mae_low_t120", pd.Series(dtype=float)), 0.50),
                    "mfe_high_t10_p50": _q(valid.get("mfe_high_t10", pd.Series(dtype=float)), 0.50),
                    "mfe_high_t20_p50": _q(valid.get("mfe_high_t20", pd.Series(dtype=float)), 0.50),
                    "mfe_high_t120_p50": _q(valid.get("mfe_high_t120", pd.Series(dtype=float)), 0.50),
                    "max_drawdown_120d_p50": _q(valid.get("max_drawdown_120d", pd.Series(dtype=float)), 0.50),
                    "peak_to_t120_giveback_p50": _q(valid.get("peak_to_t120_giveback", pd.Series(dtype=float)), 0.50),
                }
            )
    return pd.DataFrame(rows)


def summarize_episodes(episode_events: pd.DataFrame, raw_events: pd.DataFrame, signal_dictionary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for item in signal_dictionary[["signal_id", "signal_type"]].itertuples(index=False):
        ep = episode_events.loc[episode_events["signal_id"].eq(item.signal_id)].copy() if not episode_events.empty else pd.DataFrame()
        raw = raw_events.loc[raw_events["signal_id"].eq(item.signal_id)].copy() if not raw_events.empty else pd.DataFrame()
        valid = _valid_subset(ep)
        valid_count = len(valid)
        rows.append(
            {
                "signal_id": item.signal_id,
                "signal_type": item.signal_type,
                "raw_trigger_row_count": int(len(raw)),
                "episode_count": int(len(ep)),
                "episode_compression_ratio": float(len(ep) / len(raw)) if len(raw) else np.nan,
                "episode_trigger_count_p50": _q(ep.get("episode_trigger_count", pd.Series(dtype=float)), 0.50),
                "episode_trigger_count_p90": _q(ep.get("episode_trigger_count", pd.Series(dtype=float)), 0.90),
                "episode_entry_valid_count": int(valid_count),
                "episode_path_complete_120d_count": int(_truthy_series(valid.get("path_complete_120d", pd.Series(dtype=bool))).sum()) if valid_count else 0,
                "episode_atr_t0_usable_count": int((pd.to_numeric(valid.get("atr14_pct_t0", pd.Series(dtype=float)), errors="coerce") > 0).sum()) if valid_count else 0,
                "episode_atr_t0_usable_rate": float((pd.to_numeric(valid.get("atr14_pct_t0", pd.Series(dtype=float)), errors="coerce") > 0).sum() / valid_count) if valid_count else np.nan,
                "episode_early_failure_rate": _rate(valid.get("early_failure_flag", pd.Series(dtype=bool)), valid_count),
                "episode_clean_continuation_rate": _rate(valid.get("clean_continuation_flag", pd.Series(dtype=bool)), valid_count),
                "episode_whipsaw_after_profit_rate": _rate(valid.get("whipsaw_after_profit_flag", pd.Series(dtype=bool)), valid_count),
                "episode_tradable_continuation_rate": _rate(valid.get("tradable_continuation_flag", pd.Series(dtype=bool)), valid_count),
                "episode_transient_spike_rate": _rate(valid.get("transient_spike_flag", pd.Series(dtype=bool)), valid_count),
                "episode_late_drawdown_rate": _rate(valid.get("late_drawdown_flag", pd.Series(dtype=bool)), valid_count),
                "episode_severe_drawdown_rate": _rate(valid.get("severe_drawdown_flag", pd.Series(dtype=bool)), valid_count),
                "episode_hit_plus10_before_minus5_rate": _rate(valid.get("hit_plus10_before_minus5", pd.Series(dtype=bool)), valid_count),
                "episode_close_return_t20_p50": _q(valid.get("close_return_t20", pd.Series(dtype=float)), 0.50),
                "episode_close_return_t60_p50": _q(valid.get("close_return_t60", pd.Series(dtype=float)), 0.50),
                "episode_close_return_t120_p50": _q(valid.get("close_return_t120", pd.Series(dtype=float)), 0.50),
                "episode_mae_low_t20_p50": _q(valid.get("mae_low_t20", pd.Series(dtype=float)), 0.50),
                "episode_mfe_high_t20_p50": _q(valid.get("mfe_high_t20", pd.Series(dtype=float)), 0.50),
                "episode_max_drawdown_120d_p50": _q(valid.get("max_drawdown_120d", pd.Series(dtype=float)), 0.50),
            }
        )
    return pd.DataFrame(rows)


def _metric(row: pd.Series, key: str) -> float:
    value = pd.to_numeric(pd.Series([row.get(key, np.nan)]), errors="coerce").iloc[0]
    return float(value) if np.isfinite(value) else np.nan


def _cmp(value: float, operator: str, threshold: float) -> bool:
    if not np.isfinite(value):
        return False
    if operator == ">=":
        return value >= threshold
    if operator == "<=":
        return value <= threshold
    if operator == ">":
        return value > threshold
    if operator == "<":
        return value < threshold
    raise ValueError(operator)


def build_r03_handoff(path_summary: pd.DataFrame, episode_summary: pd.DataFrame) -> pd.DataFrame:
    episode_rows = path_summary.loc[path_summary["grain"].eq("episode_first_trigger")].copy()
    rows: list[dict[str, Any]] = []
    for _, row in episode_rows.iterrows():
        signal_id = row["signal_id"]
        ep_extra = episode_summary.loc[episode_summary["signal_id"].eq(signal_id)]
        raw_trigger_row_count = int(ep_extra["raw_trigger_row_count"].iloc[0]) if not ep_extra.empty else np.nan
        episode_compression_ratio = float(ep_extra["episode_compression_ratio"].iloc[0]) if not ep_extra.empty else np.nan
        episode_count = int(row["episode_count"]) if pd.notna(row["episode_count"]) else 0
        entry_valid_count = int(row["entry_valid_count"]) if pd.notna(row["entry_valid_count"]) else 0
        path_complete_rate = float(row["path_complete_120d_count"] / entry_valid_count) if entry_valid_count else np.nan
        atr_status = row["atr_evidence_status"]
        primary_blocker = "none"
        primary_opportunity = "none"
        basis: list[str] = []
        if episode_count <= R03_THRESHOLDS["background_max_episode_count"]:
            status = "background_only"
            primary_blocker = "insufficient_episode_sample"
            basis.append(f"episode_count={episode_count}<={R03_THRESHOLDS['background_max_episode_count']}")
        elif entry_valid_count == 0:
            status = "background_only"
            primary_blocker = "no_valid_executable_entries"
            basis.append("entry_valid_count=0")
        elif not np.isfinite(path_complete_rate) or path_complete_rate < R03_THRESHOLDS["min_path_complete_rate"]:
            status = "background_only"
            primary_blocker = "insufficient_complete_path_sample"
            basis.append(f"path_complete_rate={path_complete_rate:.6g}<{R03_THRESHOLDS['min_path_complete_rate']}")
        elif _cmp(_metric(row, "early_failure_rate"), ">=", R03_THRESHOLDS["stop_min_early_failure_rate"]) and _cmp(
            _metric(row, "hit_plus10_before_minus5_rate"), "<=", R03_THRESHOLDS["stop_max_hit_plus10_before_minus5_rate"]
        ):
            status = "stop_candidate"
            primary_blocker = "early_failure_without_enough_prior_upside"
            basis.append(f"early_failure_rate={_metric(row, 'early_failure_rate'):.6g}>={R03_THRESHOLDS['stop_min_early_failure_rate']}")
            basis.append(
                f"hit_plus10_before_minus5_rate={_metric(row, 'hit_plus10_before_minus5_rate'):.6g}<={R03_THRESHOLDS['stop_max_hit_plus10_before_minus5_rate']}"
            )
        elif (
            _cmp(_metric(row, "hit_plus10_before_minus5_rate"), ">=", R03_THRESHOLDS["continue_min_hit_plus10_before_minus5_rate"])
            and _cmp(_metric(row, "early_failure_rate"), "<=", R03_THRESHOLDS["continue_max_early_failure_rate"])
            and _cmp(_metric(row, "severe_drawdown_rate"), "<=", R03_THRESHOLDS["continue_max_severe_drawdown_rate"])
            and _cmp(_metric(row, "close_return_t20_p50"), ">=", R03_THRESHOLDS["continue_min_close_return_t20_p50"])
        ):
            status = "continue_to_r03_design"
            primary_opportunity = "clean_continuation_candidate"
            basis.append(
                f"hit_plus10_before_minus5_rate={_metric(row, 'hit_plus10_before_minus5_rate'):.6g}>={R03_THRESHOLDS['continue_min_hit_plus10_before_minus5_rate']}"
            )
            basis.append(f"early_failure_rate={_metric(row, 'early_failure_rate'):.6g}<={R03_THRESHOLDS['continue_max_early_failure_rate']}")
            basis.append(f"severe_drawdown_rate={_metric(row, 'severe_drawdown_rate'):.6g}<={R03_THRESHOLDS['continue_max_severe_drawdown_rate']}")
            basis.append(f"close_return_t20_p50={_metric(row, 'close_return_t20_p50'):.6g}>={R03_THRESHOLDS['continue_min_close_return_t20_p50']}")
        elif _cmp(_metric(row, "first_plus10_hit_rate"), ">=", 0.40) or _cmp(_metric(row, "mfe_high_t20_p50"), ">=", 0.10) or _cmp(
            _metric(row, "transient_spike_rate"), ">=", 0.25
        ):
            status = "needs_entry_delay_or_stop_design"
            primary_opportunity = "upside_exists_but_path_needs_risk_design"
            basis.append(
                f"first_plus10_hit_rate={_metric(row, 'first_plus10_hit_rate'):.6g};mfe_high_t20_p50={_metric(row, 'mfe_high_t20_p50'):.6g};transient_spike_rate={_metric(row, 'transient_spike_rate'):.6g}"
            )
        else:
            status = "background_only"
            primary_blocker = "no_clear_path_edge"
            basis.append("no_clear_path_edge=true")
        needs_entry_delay = _cmp(_metric(row, "early_failure_rate"), ">=", 0.35) or _cmp(_metric(row, "first_minus5_t10_rate"), ">=", 0.35)
        needs_stop = _cmp(_metric(row, "severe_drawdown_rate"), ">=", 0.45) or _cmp(_metric(row, "max_drawdown_120d_p50"), "<=", -0.15)
        needs_take_profit = _cmp(_metric(row, "transient_spike_rate"), ">=", 0.25) or _cmp(_metric(row, "peak_to_t120_giveback_p50"), "<=", -0.20)
        needs_hold = _cmp(_metric(row, "close_return_t20_p50"), ">=", 0.0) and _cmp(
            _metric(row, "close_return_t120_p50") - _metric(row, "close_return_t20_p50"), "<", 0.0
        )
        rows.append(
            {
                "signal_id": signal_id,
                "raw_trigger_row_count": raw_trigger_row_count,
                "episode_count": episode_count,
                "episode_compression_ratio": episode_compression_ratio,
                "recommended_r03_status": status,
                "primary_blocker": primary_blocker,
                "primary_opportunity": primary_opportunity,
                "status_basis_metrics": "; ".join(basis),
                "atr_evidence_status": atr_status,
                "needs_entry_delay_test": bool(needs_entry_delay),
                "needs_stop_loss_test": bool(needs_stop),
                "needs_take_profit_test": bool(needs_take_profit),
                "needs_hold_window_test": bool(needs_hold),
                "notes": "descriptive_handoff_only",
            }
        )
    return pd.DataFrame(rows)


def write_markdown_report(path: Path, path_summary: pd.DataFrame, episode_summary: pd.DataFrame, handoff: pd.DataFrame) -> None:
    lines = [
        "# R02 Family Signal 120D Path Analysis",
        "",
        "This report is descriptive evidence for R03 design. It is not an entry rule, strategy validation, or trading instruction.",
        "",
        "## Raw Trigger Vs Episode",
        "",
    ]
    for _, row in episode_summary.iterrows():
        lines.append(
            f"- `{row['signal_id']}`: raw={int(row['raw_trigger_row_count'])}, episodes={int(row['episode_count'])}, compression={row['episode_compression_ratio']:.4f}"
        )
    lines += ["", "## R03 Handoff", ""]
    for _, row in handoff.iterrows():
        lines.append(
            f"- `{row['signal_id']}`: {row['recommended_r03_status']}; blocker={row['primary_blocker']}; opportunity={row['primary_opportunity']}; basis={row['status_basis_metrics']}"
        )
    lines += ["", "## Episode Path Quality", ""]
    ep = path_summary.loc[path_summary["grain"].eq("episode_first_trigger")]
    for _, row in ep.iterrows():
        lines.append(
            f"- `{row['signal_id']}`: early_failure={row['early_failure_rate']:.4f}, clean_continuation={row['clean_continuation_rate']:.4f}, "
            f"transient_spike={row['transient_spike_rate']:.4f}, severe_drawdown={row['severe_drawdown_rate']:.4f}, atr={row['atr_evidence_status']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> dict[str, Any]:
    config, r01_config, ep2_config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    signals_dir = reports_dir / "signals"
    episode_signals_dir = reports_dir / "episode_signals"
    manifests_dir = output_root / "manifests"
    for directory in [signals_dir, episode_signals_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    signal_dictionary = validate_signal_lineage(config)
    write_csv(signal_dictionary, reports_dir / "r02_family_signal_120d_signal_dictionary.csv")
    stock, _calendar = load_stock(config, r01_config, ep2_config)
    events, signal_counts = build_signal_events(stock, config)
    path_events = attach_path_metrics(events, stock, config)
    episode_events = build_episode_audits(path_events, stock)
    path_quality_summary = summarize_path_quality(path_events, episode_events, signal_dictionary)
    episode_summary = summarize_episodes(episode_events, path_events, signal_dictionary)
    r03_handoff = build_r03_handoff(path_quality_summary, episode_summary)

    required_cols = required_output_columns()
    per_signal_paths: dict[str, str] = {}
    per_signal_episode_audit_paths: dict[str, str] = {}
    per_signal_row_counts: dict[str, int] = {}
    per_signal_episode_counts: dict[str, int] = {}
    per_signal_entry_invalid_counts: dict[str, int] = {}
    per_signal_incomplete_120d_counts: dict[str, int] = {}
    for signal_id in signal_dictionary["signal_id"].tolist():
        part = path_events.loc[path_events["signal_id"].eq(signal_id)].copy()
        if part.empty:
            part = pd.DataFrame(columns=required_cols)
        else:
            part = part[required_cols]
        out_path = signals_dir / f"{signal_id}_120d_path.csv"
        write_csv(part, out_path)
        per_signal_paths[signal_id] = relpath(out_path)
        per_signal_row_counts[signal_id] = int(len(part))
        per_signal_entry_invalid_counts[signal_id] = int((~part["entry_valid"].astype(bool)).sum()) if "entry_valid" in part else 0
        per_signal_incomplete_120d_counts[signal_id] = int((~part["path_complete_120d"].astype(bool)).sum()) if "path_complete_120d" in part else 0
        episode_part = episode_events.loc[episode_events["signal_id"].eq(signal_id)].copy() if not episode_events.empty else pd.DataFrame()
        episode_out_path = episode_signals_dir / f"{signal_id}_120d_episode_audit.csv"
        write_csv(episode_part, episode_out_path)
        per_signal_episode_audit_paths[signal_id] = relpath(episode_out_path)
        per_signal_episode_counts[signal_id] = int(len(episode_part))

    path_quality_summary_path = reports_dir / "r02_family_signal_120d_path_quality_summary.csv"
    episode_summary_path = reports_dir / "r02_family_signal_120d_episode_summary.csv"
    r03_handoff_path = reports_dir / "r02_family_signal_120d_r03_handoff_diagnostics.csv"
    report_path = reports_dir / "r02_family_signal_120d_path_analysis_report.md"
    write_csv(path_quality_summary, path_quality_summary_path)
    write_csv(episode_summary, episode_summary_path)
    write_csv(r03_handoff, r03_handoff_path)
    write_markdown_report(report_path, path_quality_summary, episode_summary, r03_handoff)

    upstream_manifest_path = topic_path(config["upstream_r02_coverage"]["manifest"])
    upstream_manifest = json.loads(upstream_manifest_path.read_text(encoding="utf-8"))
    validation_audit = pd.DataFrame(
        [
            {"check_id": "lineage_check", "status": "passed", "detail": f"{len(signal_dictionary)} signals"},
            {"check_id": "per_signal_csv_count", "status": "passed", "detail": str(len(per_signal_paths))},
            {"check_id": "episode_audit_csv_count", "status": "passed", "detail": str(len(per_signal_episode_audit_paths))},
            {"check_id": "r03_handoff_diagnostics_generated", "status": "passed", "detail": relpath(r03_handoff_path)},
        ]
    )
    write_csv(validation_audit, reports_dir / "r02_family_signal_120d_validation_audit.csv")
    manifest = {
        "phase": config["phase"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement_path": config["requirement_path"],
        "config_path": relpath(topic_path(config_path)),
        "config_hash": _hash_file(topic_path(config_path)),
        "output_root": relpath(output_root),
        "upstream_r02_output_root": config["upstream_r02_coverage"]["output_root"],
        "upstream_r02_manifest_path": relpath(upstream_manifest_path),
        "upstream_r02_manifest_hash": _hash_file(upstream_manifest_path),
        "upstream_parallel_result_hash": upstream_manifest.get("parallel_result_hash"),
        "single_signal_count": int(len(config["single_signals"])),
        "review_composite_signal_count": int(len(config["review_composite_signals"])),
        "total_signal_count": int(len(signal_dictionary)),
        "primary_grain": config["primary_grain"],
        "entry_anchor": config["entry_anchor"],
        "entry_executable_filter_policy": config["entry_executable_filter_policy"],
        "path_horizon_trading_days": int(config["path_horizon_trading_days"]),
        "path_offsets_inclusive": [0, int(config["path_horizon_trading_days"])],
        "path_complete_bar_count": int(config["path_horizon_trading_days"]) + 1,
        "minus5_trigger_price": "low",
        "max_gain_price": "high",
        "max_loss_price": "low",
        "max_drawdown_ohlc_order_policy": "prior_peak_only",
        "atr_method": config["atr"]["method"],
        "atr_period": int(config["atr"]["period"]),
        "atr_offsets": [int(v) for v in config["atr"]["offsets"]],
        "per_signal_csv_paths": per_signal_paths,
        "per_signal_episode_audit_paths": per_signal_episode_audit_paths,
        "per_signal_row_counts": per_signal_row_counts,
        "per_signal_episode_counts": per_signal_episode_counts,
        "per_signal_entry_invalid_counts": per_signal_entry_invalid_counts,
        "per_signal_incomplete_120d_counts": per_signal_incomplete_120d_counts,
        "path_quality_summary_path": relpath(path_quality_summary_path),
        "episode_summary_path": relpath(episode_summary_path),
        "r03_handoff_diagnostics_path": relpath(r03_handoff_path),
        "path_analysis_report_path": relpath(report_path),
        "fixed_return_offsets": FIXED_RETURN_OFFSETS,
        "excursion_offsets": EXCURSION_OFFSETS,
        "upside_thresholds": [0.05, 0.10, 0.20],
        "downside_race_thresholds": [-0.05, -0.10],
        "path_quality_classification_policy": "incomplete_early_clean_whipsaw_tradable_transient_late_severe_mixed",
        "race_status_policy": sorted(RACE_STATUSES),
        "atr_evidence_policy": {"min_atr_usable_rate_for_atr_evidence": R03_THRESHOLDS["min_atr_usable_rate_for_atr_evidence"]},
        "r03_handoff_policy": "deterministic_episode_first_trigger",
        "r03_handoff_thresholds": R03_THRESHOLDS,
        "r03_handoff_boundary": "descriptive_analysis_only",
        "signal_trigger_counts_before_path": signal_counts,
        "row_level_output_policy": "per_signal_raw_csv_only_no_merged_all_signal_csv",
        "validation_status": "not_run",
        "artifact_hash": _hash_json({"paths": per_signal_paths, "row_counts": per_signal_row_counts, "episodes": per_signal_episode_counts}, 16),
    }
    write_json(manifest, manifests_dir / "r02_family_signal_120d_path_query_manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EP4 R02 family signal 120D path query.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    manifest = run(Path(args.config))
    print(json.dumps(manifest, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

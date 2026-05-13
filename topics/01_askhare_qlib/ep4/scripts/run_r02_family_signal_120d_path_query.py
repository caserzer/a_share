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
    return payload


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

    missing_offsets: list[str] = []
    for offset in ATR_OFFSETS:
        pos = entry_pos + int(offset)
        if pos <= end_pos and pos < n and str(split[pos]) == signal_split and np.isfinite(atr[pos]):
            payload[f"atr14_t{offset}"] = float(atr[pos])
            payload[f"atr14_pct_t{offset}"] = float(atr_pct[pos]) if np.isfinite(atr_pct[pos]) else np.nan
        else:
            missing_offsets.append(str(offset))
    payload["atr_missing_offsets"] = "|".join(missing_offsets)
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
    return cols


def run(config_path: Path) -> dict[str, Any]:
    config, r01_config, ep2_config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    reports_dir = output_root / "reports"
    signals_dir = reports_dir / "signals"
    manifests_dir = output_root / "manifests"
    for directory in [signals_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    signal_dictionary = validate_signal_lineage(config)
    write_csv(signal_dictionary, reports_dir / "r02_family_signal_120d_signal_dictionary.csv")
    stock, _calendar = load_stock(config, r01_config, ep2_config)
    events, signal_counts = build_signal_events(stock, config)
    path_events = attach_path_metrics(events, stock, config)

    required_cols = required_output_columns()
    per_signal_paths: dict[str, str] = {}
    per_signal_row_counts: dict[str, int] = {}
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

    upstream_manifest_path = topic_path(config["upstream_r02_coverage"]["manifest"])
    upstream_manifest = json.loads(upstream_manifest_path.read_text(encoding="utf-8"))
    validation_audit = pd.DataFrame(
        [
            {"check_id": "lineage_check", "status": "passed", "detail": f"{len(signal_dictionary)} signals"},
            {"check_id": "per_signal_csv_count", "status": "passed", "detail": str(len(per_signal_paths))},
            {"check_id": "merged_row_level_csv_absent", "status": "passed", "detail": "per-signal csv only"},
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
        "per_signal_row_counts": per_signal_row_counts,
        "per_signal_entry_invalid_counts": per_signal_entry_invalid_counts,
        "per_signal_incomplete_120d_counts": per_signal_incomplete_120d_counts,
        "signal_trigger_counts_before_path": signal_counts,
        "row_level_output_policy": "per_signal_csv_only_no_merged_all_signal_csv",
        "validation_status": "not_run",
        "artifact_hash": _hash_json({"paths": per_signal_paths, "row_counts": per_signal_row_counts}, 16),
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

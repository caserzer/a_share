#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r03e_family_signal_bad_shape_filter_diagnostic_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
ALL_SPLITS = SPLITS + ["all"]
EVENT_SCOPES = ["r02_signal_episode_start", "r03_seed_family_event", "r03_clean_fresh_family_event"]
PATH_LABELS = ["good_path", "neutral_path", "bad_path"]
FINAL_DECISIONS = {
    "badshape_filter_supported",
    "badshape_filter_reduces_bad_path_but_costs_winners",
    "badshape_filter_no_incremental_edge",
    "insufficient_denominator",
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_validation_failed",
}
DETAILED_FLAGS = [
    "volume_stall_flag",
    "failed_breakout_flag",
    "dense_upper_shadow_flag",
    "down_volume_dominance_flag",
    "ma20_break_no_reclaim_flag",
    "large_bearish_engulf_flag",
    "volatility_up_no_price_flag",
    "low_upside_efficiency_flag",
    "lower_low_lower_high_flag",
    "gap_up_fade_flag",
]
BAD_ITEMS = [
    "bad_item_01_ret20_lt0",
    "bad_item_02_close_below_ma20",
    "bad_item_03_ma20_slope_negative",
    "bad_item_04_recent5_low_below_prior15_low",
    "bad_item_05_down_volume_gt_up_volume",
    "bad_item_06_max_down_abs_gt_max_up",
    "bad_item_07_atr_rank_up_ret20_low",
    "bad_item_08_upper_shadow_count_ge3",
    "bad_item_09_volume_down_day_ge2",
    "bad_item_10_failed_breakout_3d",
]
COMPONENT_POLICIES = {
    "drop_volume_stall": "volume_stall_flag",
    "drop_failed_breakout": "failed_breakout_flag",
    "drop_dense_upper_shadow": "dense_upper_shadow_flag",
    "drop_down_volume_dominance": "down_volume_dominance_flag",
    "drop_ma20_break_no_reclaim": "ma20_break_no_reclaim_flag",
    "drop_large_bearish_engulf": "large_bearish_engulf_flag",
    "drop_volatility_up_no_price": "volatility_up_no_price_flag",
    "drop_low_upside_efficiency": "low_upside_efficiency_flag",
    "drop_lower_low_lower_high": "lower_low_lower_high_flag",
    "drop_gap_up_fade": "gap_up_fade_flag",
}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _safe_float(value: Any, default: float = np.nan) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return float(numeric) if np.isfinite(numeric) else default


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _finite_positive(value: Any) -> bool:
    return _finite(value) and float(value) > 0.0


def _safe_div(numerator: float, denominator: float) -> float:
    if not _finite(denominator) or float(denominator) == 0.0:
        return np.nan
    if not _finite(numerator):
        return np.nan
    return float(numerator) / float(denominator)


def _to_bool(value: Any) -> bool:
    if value is pd.NA or value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    return bool(value)


def _nullable_bool(value: Any) -> Any:
    if value is pd.NA or value is None:
        return pd.NA
    try:
        if pd.isna(value):
            return pd.NA
    except TypeError:
        pass
    if isinstance(value, str):
        if value.strip().lower() in {"true", "1", "yes"}:
            return True
        if value.strip().lower() in {"false", "0", "no"}:
            return False
        return pd.NA
    return bool(value)


def _date_str(value: Any) -> str:
    if value is pd.NA or value is None:
        return ""
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return ""
    return ts.normalize().date().isoformat()


def _normalize_date_or_nat(value: Any) -> Any:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    return ts.normalize()


def _family_list(value: Any) -> list[str]:
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except TypeError:
        pass
    text = str(value)
    if not text or text == "none":
        return []
    return [part for part in text.split("|") if part and part != "none"]


def _hash_id(parts: list[Any], n: int = 16) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:n]


def _weighted_sum(df: pd.DataFrame, mask: pd.Series, weight_col: str) -> float:
    if df.empty:
        return 0.0
    return float(df.loc[mask.fillna(False), weight_col].sum())


def _weighted_rate(df: pd.DataFrame, mask: pd.Series, weight_col: str) -> float:
    denom = float(df[weight_col].sum()) if not df.empty else 0.0
    if denom <= 0:
        return np.nan
    return _weighted_sum(df, mask, weight_col) / denom


def _path_label_from_components(
    entry_valid: Any,
    path_complete: Any,
    first_minus5_offset: Any,
    first_plus10_offset: Any,
    max_loss_before_first_plus10: Any,
    max_drawdown_120d: Any,
    path_quality_flag: Any,
    early_failure_flag: Any = None,
) -> str:
    if not _to_bool(entry_valid) or not _to_bool(path_complete):
        return "invalid_or_incomplete"
    minus5 = _safe_float(first_minus5_offset)
    plus10 = _safe_float(first_plus10_offset)
    max_loss = _safe_float(max_loss_before_first_plus10)
    max_dd = _safe_float(max_drawdown_120d)
    quality = str(path_quality_flag)
    if _to_bool(early_failure_flag):
        return "bad_path"
    if _finite(minus5) and (not _finite(plus10) or minus5 <= plus10):
        return "bad_path"
    if _finite(max_loss) and max_loss <= -0.06:
        return "bad_path"
    if _finite(max_dd) and max_dd <= -0.20:
        return "bad_path"
    if quality in {"clean_continuation", "tradable_continuation", "good_path"}:
        return "good_path"
    if _finite(plus10) and (not _finite(minus5) or plus10 < minus5):
        if (not _finite(max_loss) or max_loss > -0.06) and (not _finite(max_dd) or max_dd > -0.20):
            return "good_path"
    return "neutral_path"


def _load_condition_map(config: dict[str, Any]) -> dict[str, str]:
    precision_config = _read_yaml(Path(config["upstream_precision"]["config"]))
    rows = precision_config.get("frozen_conditions", [])
    mapping: dict[str, list[str]] = {}
    for row in rows:
        mapping.setdefault(str(row["family_id"]), []).append(str(row["condition_group_id"]))
    bad = {family: values for family, values in mapping.items() if len(values) != 1}
    expected = set(config["family_universe"])
    missing = expected - set(mapping)
    extra = set(mapping) - expected
    if bad or missing or extra:
        raise RuntimeError(f"condition_group_id family mapping is not 1:1: bad={bad}, missing={sorted(missing)}, extra={sorted(extra)}")
    return {family: values[0] for family, values in mapping.items()}


def _input_readiness(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group, payload in [
        ("upstream_precision", config["upstream_precision"]),
        ("upstream_path_query", config["upstream_path_query"]),
        ("upstream_r03b", config["upstream_r03b"]),
        ("upstream_r03c", config["upstream_r03c"]),
    ]:
        for key in ["manifest", "validation"]:
            path = topic_path(Path(payload[key]))
            status = "present" if path.exists() else "missing"
            validation_status = ""
            if key == "validation" and path.exists():
                validation_status = _read_json(Path(payload[key])).get("validation_status", "")
            rows.append(
                {
                    "input_group": group,
                    "input_name": key,
                    "input_path": relpath(path),
                    "status": status,
                    "validation_status": validation_status,
                    "failure_reason": "" if status == "present" else "missing required input",
                }
            )
    for group, key in [
        ("upstream_precision", "action_time_panel"),
        ("upstream_path_query", "signal_dir"),
        ("upstream_r03b", "seed_episode_panel"),
        ("upstream_r03c", "fresh_step_price_panel"),
    ]:
        path = topic_path(Path(config[group][key]))
        rows.append(
            {
                "input_group": group,
                "input_name": key,
                "input_path": relpath(path),
                "status": "present" if path.exists() else "missing",
                "validation_status": "",
                "failure_reason": "" if path.exists() else "missing required input",
            }
        )
    return pd.DataFrame(rows)


def _load_r02_paths(config: dict[str, Any]) -> pd.DataFrame:
    signal_dir = topic_path(Path(config["upstream_path_query"]["signal_dir"]))
    frames: list[pd.DataFrame] = []
    for path in sorted(signal_dir.glob("single_*_120d_path.csv")):
        df = pd.read_csv(path)
        df["source_path_file"] = relpath(path)
        frames.append(df)
    if not frames:
        raise RuntimeError(f"no single-family R02 path-query CSVs found in {signal_dir}")
    out = pd.concat(frames, ignore_index=True)
    out["signal_date"] = pd.to_datetime(out["signal_date"]).dt.normalize()
    out["entry_date"] = pd.to_datetime(out["entry_date"], errors="coerce").dt.normalize()
    dup = out.duplicated(["instrument_id", "family_id", "signal_date"], keep=False)
    if bool(dup.any()):
        sample = out.loc[dup, ["instrument_id", "family_id", "signal_date"]].head(5).to_dict("records")
        raise RuntimeError(f"R02 path-query rows are not unique for primary key; sample={sample}")
    return out


def _rolling_last_pct_rank(values: np.ndarray) -> float:
    if len(values) == 0:
        return np.nan
    last = values[-1]
    if not np.isfinite(last):
        return np.nan
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return np.nan
    return float(np.sum(finite <= last) / len(finite))


def _prepare_stock(config: dict[str, Any]) -> pd.DataFrame:
    r01_config, _, ep2_config = load_r01_config(topic_path(Path(config["upstream_r01"]["config"])))
    panel, calendar = load_provider_spine(r01_config, ep2_config)
    stock = prepare_stock_day_panel(r01_config, ep2_config, panel, calendar)
    stock = stock.sort_values(["instrument", "date"]).reset_index(drop=True).copy()
    group = stock.groupby("instrument", group_keys=False)
    stock["instrument_id"] = stock["instrument"].astype(str).str.upper()
    stock["prev_close"] = group["close"].shift(1)
    stock["daily_return"] = stock["close"] / stock["prev_close"] - 1.0
    stock["ma20_asof"] = group["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    stock["ma20_slope5_asof"] = stock["ma20_asof"] / group["ma20_asof"].shift(5) - 1.0
    stock["volume_mean20_asof"] = group["volume"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    stock["volume_mean60_asof"] = group["volume"].transform(lambda s: s.rolling(60, min_periods=60).mean())
    stock["prior20_high_before"] = group["high"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).max())
    stock["prior52w_high_before"] = group["high"].transform(lambda s: s.shift(1).rolling(252, min_periods=120).max())
    stock["atr20_wilder"] = group["true_range"].transform(lambda s: s.ewm(alpha=1.0 / 20.0, adjust=False, min_periods=20).mean())
    stock["atr20_pct_wilder"] = stock["atr20_wilder"] / stock["close"]
    stock["atr20_pct_rank252"] = group["atr20_pct_wilder"].transform(
        lambda s: s.rolling(252, min_periods=252).apply(_rolling_last_pct_rank, raw=True)
    )
    stock["date"] = pd.to_datetime(stock["date"]).dt.normalize()
    stock["date_str"] = stock["date"].dt.date.astype(str)
    return stock


def _build_stock_arrays(stock: pd.DataFrame) -> dict[str, dict[str, Any]]:
    cols = [
        "date",
        "date_str",
        "split",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "prev_close",
        "daily_return",
        "ma20_asof",
        "ma20_slope5_asof",
        "volume_mean20_asof",
        "volume_mean60_asof",
        "prior20_high_before",
        "prior52w_high_before",
        "atr20_wilder",
        "atr20_pct_wilder",
        "atr20_pct_rank252",
        "ret60_asof",
        "is_buy_executable_next_open",
        "not_suspended_or_dirty_bar",
        "eligible_stock_day",
    ]
    arrays: dict[str, dict[str, Any]] = {}
    for instrument, frame in stock.groupby("instrument_id", sort=False):
        frame = frame.sort_values("date").reset_index(drop=True)
        payload = {col: frame[col].to_numpy() for col in cols if col in frame.columns}
        payload["date_to_pos"] = {str(date): idx for idx, date in enumerate(frame["date_str"].tolist())}
        arrays[str(instrument)] = payload
    return arrays


def _stock_signal_prices(arrays_by_instrument: dict[str, dict[str, Any]], instrument: str, signal_date: Any) -> tuple[float, float]:
    arrays = arrays_by_instrument.get(str(instrument))
    if not arrays:
        return np.nan, np.nan
    pos = arrays["date_to_pos"].get(_date_str(signal_date))
    if pos is None:
        return np.nan, np.nan
    close = _safe_float(arrays["close"][pos])
    next_open = _safe_float(arrays["open"][pos + 1]) if pos + 1 < len(arrays["date"]) else np.nan
    return close, next_open


def _load_event_panel(config: dict[str, Any], arrays_by_instrument: dict[str, dict[str, Any]]) -> pd.DataFrame:
    condition_map = _load_condition_map(config)
    r02_paths = _load_r02_paths(config)
    action_cols = [
        "instrument_id",
        "trade_date",
        "split",
        "close_t",
        "next_open_t1",
        "complete_h120_flag",
        "forward_close_peak_h120_return_from_close",
        "big_winner_forward_from_signal_close",
        "forward_close_peak_h120_return_from_next_open",
        "big_winner_forward_from_next_open",
        "condition_group_id",
        "family_id",
        "signal_episode_id",
        "is_episode_start",
        "episode_signal_date",
        "episode_occurrence_price_t",
        "episode_entry_price_t",
    ]
    action = pd.read_parquet(topic_path(Path(config["upstream_precision"]["action_time_panel"])), columns=action_cols)
    action = action[action["is_episode_start"].astype(bool)].copy()
    action["signal_date"] = pd.to_datetime(action["episode_signal_date"]).dt.normalize()
    action["instrument_id"] = action["instrument_id"].astype(str).str.upper()
    merged = action.merge(
        r02_paths,
        on=["instrument_id", "family_id", "signal_date"],
        how="left",
        suffixes=("", "_path"),
        validate="one_to_one",
    )
    path_complete = merged["path_complete_120d"].fillna(False).astype(bool)
    action_complete = merged["complete_h120_flag"].fillna(False).astype(bool)
    r02 = pd.DataFrame(
        {
            "event_scope": "r02_signal_episode_start",
            "event_stage": "r02_episode_start",
            "source_event_id": merged["signal_episode_id"].astype(str),
            "seed_episode_id": "",
            "instrument_id": merged["instrument_id"],
            "split": merged["split"],
            "signal_date": merged["signal_date"],
            "family_id": merged["family_id"],
            "condition_group_id": merged["condition_group_id"],
            "signal_offset_from_seed": np.nan,
            "t0_entry_date": merged["entry_date"],
            "t0_entry_price": merged["entry_price"],
            "signal_close_price": merged["episode_occurrence_price_t"],
            "signal_next_open_price": merged["episode_entry_price_t"],
            "signal_anchor_complete_h120_flag": action_complete & path_complete,
            "signal_anchor_big_winner_next_open": merged["big_winner_forward_from_next_open"],
            "signal_anchor_big_winner_close": merged["big_winner_forward_from_signal_close"],
            "signal_anchor_forward_peak_next_open": merged["forward_close_peak_h120_return_from_next_open"],
            "signal_anchor_forward_peak_close": merged["forward_close_peak_h120_return_from_close"],
            "signal_anchor_path_label": [
                _path_label_from_components(
                    row.entry_valid,
                    row.path_complete_120d,
                    row.first_minus5_offset,
                    row.first_plus10_offset,
                    row.max_loss_before_first_plus10,
                    row.max_drawdown_120d,
                    row.path_quality_flag,
                    row.early_failure_flag,
                )
                for row in merged.itertuples(index=False)
            ],
        }
    )

    seed = pd.read_parquet(topic_path(Path(config["upstream_r03b"]["seed_episode_panel"])))
    seed_rows: list[dict[str, Any]] = []
    for row in seed.itertuples(index=False):
        families = _family_list(getattr(row, "seed_family_set"))
        signal_close, signal_next_open = _stock_signal_prices(arrays_by_instrument, row.instrument_id, row.seed_trade_date)
        for family in families:
            seed_rows.append(
                {
                    "event_scope": "r03_seed_family_event",
                    "event_stage": "seed_family",
                    "source_event_id": str(row.seed_episode_id),
                    "seed_episode_id": str(row.seed_episode_id),
                    "instrument_id": str(row.instrument_id).upper(),
                    "split": str(row.split),
                    "signal_date": pd.to_datetime(row.seed_trade_date).normalize(),
                    "family_id": family,
                    "condition_group_id": condition_map[family],
                    "signal_offset_from_seed": 0,
                    "t0_entry_date": _normalize_date_or_nat(row.seed_entry_date),
                    "t0_entry_price": _safe_float(row.seed_entry_price),
                    "signal_close_price": signal_close,
                    "signal_next_open_price": signal_next_open,
                    "signal_anchor_complete_h120_flag": _to_bool(row.path_complete_120d) and _to_bool(row.entry_valid),
                    "signal_anchor_big_winner_next_open": _nullable_bool(row.big_winner_forward_h120_next_open_anchor),
                    "signal_anchor_big_winner_close": _nullable_bool(row.big_winner_forward_h120_close_anchor),
                    "signal_anchor_forward_peak_next_open": _safe_float(row.forward_close_peak_h120_return_from_seed_next_open),
                    "signal_anchor_forward_peak_close": _safe_float(row.forward_close_peak_h120_return_from_seed_close),
                    "signal_anchor_path_label": _path_label_from_components(
                        row.entry_valid,
                        row.path_complete_120d,
                        row.first_minus5_offset,
                        np.nan,
                        row.max_loss_before_first_plus10,
                        row.max_drawdown_120d,
                        row.path_quality_flag,
                        row.early_failure_flag,
                    ),
                }
            )
    seed_panel = pd.DataFrame(seed_rows)

    fresh = pd.read_parquet(topic_path(Path(config["upstream_r03c"]["fresh_step_price_panel"])))
    if "included_in_primary_fresh_count" in fresh.columns:
        fresh = fresh[fresh["included_in_primary_fresh_count"].astype(bool)].copy()
    fresh = fresh[fresh["step_status"].isin(["fresh_distinct_family_step", "same_offset_multi_family_step"])].copy()
    fresh = fresh[(fresh["step_offset"] >= 3) & (fresh["step_offset"] <= 30)].copy()
    if "observable_failure_offset" in fresh.columns:
        observable = pd.to_numeric(fresh["observable_failure_offset"], errors="coerce")
        fresh = fresh[observable.isna() | (fresh["step_offset"] < observable)].copy()
    fresh_rows: list[dict[str, Any]] = []
    for row in fresh.itertuples(index=False):
        families = _family_list(getattr(row, "added_family_set"))
        step_idx = _safe_float(getattr(row, "kth_fresh_step_index_raw", getattr(row, "sequence_step_index", np.nan)))
        if _finite(step_idx):
            if step_idx <= 1:
                stage = "fresh_1"
            elif step_idx == 2:
                stage = "fresh_2"
            elif step_idx == 3:
                stage = "fresh_3"
            else:
                stage = "fresh_4plus"
        else:
            stage = "fresh_unknown"
        for family in families:
            fresh_rows.append(
                {
                    "event_scope": "r03_clean_fresh_family_event",
                    "event_stage": stage,
                    "source_event_id": f"{row.seed_episode_id}:{row.sequence_step_index}:{family}",
                    "seed_episode_id": str(row.seed_episode_id),
                    "instrument_id": str(row.instrument_id).upper(),
                    "split": str(row.split),
                    "signal_date": pd.to_datetime(row.step_signal_date).normalize(),
                    "family_id": family,
                    "condition_group_id": condition_map[family],
                    "signal_offset_from_seed": int(row.step_offset),
                    "t0_entry_date": _normalize_date_or_nat(row.fresh_entry_date),
                    "t0_entry_price": _safe_float(row.fresh_entry_price),
                    "signal_close_price": _safe_float(row.fresh_signal_close_price),
                    "signal_next_open_price": _safe_float(row.fresh_signal_next_open_price),
                    "signal_anchor_complete_h120_flag": _to_bool(row.fresh_path_complete_120d) and _to_bool(row.fresh_entry_valid),
                    "signal_anchor_big_winner_next_open": _nullable_bool(row.fresh_big_winner_forward_h120_next_open_anchor),
                    "signal_anchor_big_winner_close": _nullable_bool(row.fresh_big_winner_forward_h120_close_anchor),
                    "signal_anchor_forward_peak_next_open": _safe_float(row.fresh_forward_close_peak_h120_return_from_next_open),
                    "signal_anchor_forward_peak_close": _safe_float(row.fresh_forward_close_peak_h120_return_from_signal_close),
                    "signal_anchor_path_label": str(row.fresh_path_label),
                }
            )
    fresh_panel = pd.DataFrame(fresh_rows)

    events = pd.concat([r02, seed_panel, fresh_panel], ignore_index=True)
    events["signal_date"] = pd.to_datetime(events["signal_date"]).dt.normalize()
    events["t0_entry_date"] = pd.to_datetime(events["t0_entry_date"], errors="coerce").dt.normalize()
    events["year"] = events["signal_date"].dt.year
    events["family_signal_event_id"] = [
        _hash_id([row.event_scope, row.source_event_id, row.instrument_id, row.signal_date.date(), row.family_id])
        for row in events.itertuples(index=False)
    ]
    counts = events.groupby(["event_scope", "instrument_id", "signal_date"])["family_id"].transform("count")
    events["same_date_family_count"] = counts.astype(int)
    events["dedup_weight"] = 1.0 / events["same_date_family_count"].clip(lower=1)
    return events.sort_values(["event_scope", "instrument_id", "signal_date", "family_id"]).reset_index(drop=True)


def _position_for_date(arrays: dict[str, Any], date_value: Any) -> int | None:
    key = _date_str(date_value)
    if not key:
        return None
    pos = arrays["date_to_pos"].get(key)
    return int(pos) if pos is not None else None


def _first_executable_entry_after(arrays: dict[str, Any], anchor_pos: int) -> tuple[int | None, str]:
    n = len(arrays["date"])
    if anchor_pos is None or anchor_pos < 0:
        return None, "missing_anchor_pos"
    anchor_split = str(arrays["split"][anchor_pos])
    for prev_pos in range(anchor_pos, n - 1):
        if str(arrays["split"][prev_pos]) != anchor_split:
            return None, "split_boundary_before_filter_entry"
        entry_pos = prev_pos + 1
        if str(arrays["split"][entry_pos]) != anchor_split:
            return None, "split_boundary_before_filter_entry"
        if not _to_bool(arrays["is_buy_executable_next_open"][prev_pos]):
            continue
        if not _finite_positive(arrays["open"][entry_pos]):
            continue
        if "not_suspended_or_dirty_bar" in arrays and not _to_bool(arrays["not_suspended_or_dirty_bar"][entry_pos]):
            continue
        return entry_pos, ""
    return None, "no_executable_next_open_after_shape_eval"


def _relative_window_positions(arrays: dict[str, Any], t0_pos: int, offsets: list[int], expected_split: str) -> tuple[list[int], list[int]]:
    positions: list[int] = []
    missing_offsets: list[int] = []
    n = len(arrays["date"])
    for offset in offsets:
        pos = t0_pos + offset
        if pos < 0 or pos >= n or str(arrays["split"][pos]) != expected_split:
            missing_offsets.append(offset)
            continue
        positions.append(pos)
    return positions, missing_offsets


def _series_at(arrays: dict[str, Any], col: str, positions: list[int]) -> np.ndarray:
    if not positions:
        return np.asarray([], dtype=float)
    return np.asarray(arrays[col][positions], dtype=float)


def _date_at(arrays: dict[str, Any], pos: int) -> str:
    return pd.Timestamp(arrays["date"][pos]).date().isoformat()


def _candidate_followup_offsets(day_offset: int, n: int) -> list[int]:
    offsets: list[int] = []
    current = day_offset + 1
    while len(offsets) < n and current <= 10:
        if current == 0:
            current += 1
            continue
        offsets.append(current)
        current += 1
    return offsets


def _flag_or_na(value: Any, complete: bool = True) -> Any:
    if not complete:
        return pd.NA
    return bool(value)


def _compute_failed_breakout(core: dict[int, int], arrays: dict[str, Any]) -> tuple[Any, int]:
    count = 0
    candidates = 0
    for offset, pos in core.items():
        if offset == 0:
            continue
        prior_high = max(_safe_float(arrays["prior20_high_before"][pos]), _safe_float(arrays["prior52w_high_before"][pos]))
        if not _finite(prior_high):
            continue
        high = _safe_float(arrays["high"][pos])
        close = _safe_float(arrays["close"][pos])
        vol = _safe_float(arrays["volume"][pos])
        vol60 = _safe_float(arrays["volume_mean60_asof"][pos])
        if not (_finite(high) and _finite(close) and _finite(vol) and _finite(vol60)):
            continue
        if high < prior_high and close < prior_high:
            continue
        if vol < 1.2 * vol60:
            continue
        follow_offsets = _candidate_followup_offsets(offset, 3)
        if not follow_offsets:
            continue
        candidates += 1
        fell_back = False
        for follow_offset in follow_offsets:
            follow_pos = core.get(follow_offset)
            if follow_pos is None:
                continue
            follow_close = _safe_float(arrays["close"][follow_pos])
            if _finite(follow_close) and follow_close < prior_high:
                fell_back = True
                break
        if fell_back:
            count += 1
    if candidates == 0:
        return pd.NA, 0
    return count > 0, count


def _compute_ma20_break_no_reclaim(core: dict[int, int], arrays: dict[str, Any]) -> tuple[Any, int]:
    triggers = 0
    candidates = 0
    for offset, pos in core.items():
        if offset == 0:
            continue
        close = _safe_float(arrays["close"][pos])
        ma20 = _safe_float(arrays["ma20_asof"][pos])
        if not (_finite(close) and _finite(ma20)) or close >= ma20:
            continue
        follow_offsets = _candidate_followup_offsets(offset, 5)
        if len(follow_offsets) < 3:
            continue
        candidates += 1
        follow_closes = []
        follow_ma = []
        for follow_offset in follow_offsets[:5]:
            follow_pos = core.get(follow_offset)
            if follow_pos is None:
                continue
            follow_closes.append(_safe_float(arrays["close"][follow_pos]))
            follow_ma.append(_safe_float(arrays["ma20_asof"][follow_pos]))
        usable = [(c, m) for c, m in zip(follow_closes, follow_ma) if _finite(c) and _finite(m)]
        if len(usable) < 3:
            continue
        no_reclaim = all(c < m for c, m in usable[:3])
        slope_end = _safe_float(arrays["ma20_slope5_asof"][core.get(10, pos)])
        if no_reclaim and (_finite(slope_end) and slope_end <= 0.0):
            triggers += 1
    if candidates == 0:
        return pd.NA, 0
    return triggers > 0, triggers


def _compute_large_bearish(core_offsets: list[int], core_positions: list[int], arrays: dict[str, Any]) -> tuple[Any, int]:
    returns = _series_at(arrays, "daily_return", core_positions)
    mean_abs = float(np.nanmean(np.abs(returns))) if len(returns) else np.nan
    if not _finite(mean_abs) or mean_abs <= 0:
        return pd.NA, 0
    triggers = 0
    for offset, pos in zip(core_offsets, core_positions):
        ret = _safe_float(arrays["daily_return"][pos])
        vol = _safe_float(arrays["volume"][pos])
        vol60 = _safe_float(arrays["volume_mean60_asof"][pos])
        high = _safe_float(arrays["high"][pos])
        low = _safe_float(arrays["low"][pos])
        close = _safe_float(arrays["close"][pos])
        if not all(_finite(v) for v in [ret, vol, vol60, high, low, close]) or high <= low:
            continue
        close_location = (close - low) / (high - low)
        if ret <= -2.0 * mean_abs and vol >= 1.5 * vol60 and close_location <= 0.25:
            start_offset = max(-10, offset - 10)
            prior_offsets = [v for v in range(start_offset, offset) if v != 0]
            prior_positions = [core_positions[core_offsets.index(v)] for v in prior_offsets if v in core_offsets]
            if prior_positions:
                start_close = _safe_float(arrays["close"][prior_positions[0]])
                prior_high = float(np.nanmax(_series_at(arrays, "close", prior_positions)))
                if _finite(start_close) and _finite(prior_high) and prior_high > start_close:
                    if close <= start_close + 0.25 * (prior_high - start_close):
                        triggers += 1
                        continue
            triggers += 1
    return triggers > 0, triggers


def _compute_filter_path(arrays: dict[str, Any], shape_eval_pos: int, config: dict[str, Any]) -> dict[str, Any]:
    horizon = int(config["outcome"]["horizon_td"])
    threshold = float(config["outcome"]["big_winner_threshold"])
    payload: dict[str, Any] = {
        "filter_entry_date": "",
        "filter_entry_price": np.nan,
        "filter_entry_relative_offset": np.nan,
        "filter_entry_valid": False,
        "filter_entry_incomplete_reason": "",
        "filter_path_complete_120d": False,
        "filter_available_forward_trading_days": 0,
        "filter_path_label": "invalid_or_incomplete",
        "filter_anchor_forward_peak_h120_next_open": np.nan,
        "filter_anchor_big_winner_next_open": pd.NA,
        "filter_anchor_forward_peak_h120_close": np.nan,
        "filter_anchor_big_winner_close": pd.NA,
        "filter_first_minus5_offset": np.nan,
        "filter_first_plus10_offset": np.nan,
        "filter_max_loss_before_first_plus10": np.nan,
        "filter_max_drawdown_120d": np.nan,
    }
    if shape_eval_pos is None:
        payload["filter_entry_incomplete_reason"] = "missing_shape_eval_pos"
        return payload
    entry_pos, reason = _first_executable_entry_after(arrays, shape_eval_pos)
    if entry_pos is None:
        payload["filter_entry_incomplete_reason"] = reason
        return payload
    entry_price = _safe_float(arrays["open"][entry_pos])
    if not _finite_positive(entry_price):
        payload["filter_entry_incomplete_reason"] = "invalid_filter_entry_price"
        return payload
    payload["filter_entry_valid"] = True
    payload["filter_entry_date"] = _date_at(arrays, entry_pos)
    payload["filter_entry_price"] = entry_price
    payload["filter_entry_relative_offset"] = int(entry_pos - shape_eval_pos + 10)
    anchor_split = str(arrays["split"][entry_pos])
    end_pos = min(entry_pos + horizon, len(arrays["date"]) - 1)
    positions: list[int] = []
    for pos in range(entry_pos, end_pos + 1):
        if str(arrays["split"][pos]) != anchor_split:
            break
        positions.append(pos)
    available = len(positions) - 1
    payload["filter_available_forward_trading_days"] = int(max(0, available))
    payload["filter_path_complete_120d"] = available >= horizon
    if available < horizon:
        payload["filter_entry_incomplete_reason"] = "insufficient_120d_filter_path"
    highs = _series_at(arrays, "high", positions)
    lows = _series_at(arrays, "low", positions)
    closes = _series_at(arrays, "close", positions)
    offsets = np.asarray([pos - entry_pos for pos in positions], dtype=int)
    high_returns = highs / entry_price - 1.0
    low_returns = lows / entry_price - 1.0
    close_returns = closes / entry_price - 1.0
    if len(high_returns):
        peak_idx = int(np.nanargmax(high_returns)) if np.isfinite(high_returns).any() else 0
        payload["filter_anchor_forward_peak_h120_next_open"] = float(high_returns[peak_idx]) if np.isfinite(high_returns[peak_idx]) else np.nan
        payload["filter_anchor_big_winner_next_open"] = bool(
            _finite(payload["filter_anchor_forward_peak_h120_next_open"])
            and payload["filter_anchor_forward_peak_h120_next_open"] >= threshold
        )
    shape_eval_close = _safe_float(arrays["close"][shape_eval_pos])
    if _finite_positive(shape_eval_close) and len(closes):
        close_anchor_returns = closes / shape_eval_close - 1.0
        close_peak = float(np.nanmax(close_anchor_returns)) if np.isfinite(close_anchor_returns).any() else np.nan
        payload["filter_anchor_forward_peak_h120_close"] = close_peak
        payload["filter_anchor_big_winner_close"] = bool(_finite(close_peak) and close_peak >= threshold)
    minus_hits = np.flatnonzero(np.isfinite(low_returns) & (low_returns <= -0.05))
    plus_hits = np.flatnonzero(np.isfinite(high_returns) & (high_returns >= 0.10))
    first_minus_offset = int(offsets[minus_hits[0]]) if len(minus_hits) else np.nan
    first_plus_offset = int(offsets[plus_hits[0]]) if len(plus_hits) else np.nan
    payload["filter_first_minus5_offset"] = first_minus_offset
    payload["filter_first_plus10_offset"] = first_plus_offset
    if _finite(first_plus_offset):
        eval_positions = offsets < int(first_plus_offset)
    else:
        eval_positions = np.ones(len(offsets), dtype=bool)
    if eval_positions.any():
        max_loss = float(np.nanmin(low_returns[eval_positions])) if np.isfinite(low_returns[eval_positions]).any() else np.nan
        payload["filter_max_loss_before_first_plus10"] = max_loss
    peak = -np.inf
    max_dd = np.nan
    for high, low in zip(highs, lows):
        if not (_finite(high) and _finite(low)):
            continue
        if not np.isfinite(peak):
            peak = high
            continue
        if _finite_positive(peak):
            dd = low / peak - 1.0
            if not _finite(max_dd) or dd < max_dd:
                max_dd = float(dd)
        if high > peak:
            peak = high
    payload["filter_max_drawdown_120d"] = max_dd
    payload["filter_path_label"] = _path_label_from_components(
        True,
        payload["filter_path_complete_120d"],
        payload["filter_first_minus5_offset"],
        payload["filter_first_plus10_offset"],
        payload["filter_max_loss_before_first_plus10"],
        payload["filter_max_drawdown_120d"],
        "good_path" if (_finite(first_plus_offset) and (not _finite(first_minus_offset) or first_plus_offset < first_minus_offset)) else "mixed",
        False,
    )
    return payload


def _compute_shape_for_event(row: pd.Series, arrays_by_instrument: dict[str, dict[str, Any]], config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    event_id = str(row["family_signal_event_id"])
    arrays = arrays_by_instrument.get(str(row["instrument_id"]).upper())
    empty = {
        "family_signal_event_id": event_id,
        "shape_eval_date": "",
        "shape_eval_complete_flag": False,
        "shape_eval_incomplete_reason": "missing_instrument",
        "shape_core_window_complete_flag": False,
        "shape_core_window_bar_count": 0,
        "shape_core_missing_offsets": "",
        "bad_score_complete_flag": False,
        "bad_score_v1": np.nan,
        "bad_score_bucket": "incomplete",
        "pass_primary_badshape_filter": pd.NA,
        "drop_primary_badshape_filter": pd.NA,
    }
    for flag in DETAILED_FLAGS + BAD_ITEMS:
        empty[flag] = pd.NA
    empty.update(_compute_filter_path({} if arrays is None else arrays, None, config))
    if arrays is None:
        return empty, []
    t0_pos = _position_for_date(arrays, row["t0_entry_date"])
    if t0_pos is None:
        empty["shape_eval_incomplete_reason"] = "missing_t0_entry_date_in_spine"
        return empty, []
    t0_split = str(arrays["split"][t0_pos])
    eval_pos = t0_pos + int(config["shape"]["observation_horizon_td"])
    if eval_pos >= len(arrays["date"]) or str(arrays["split"][eval_pos]) != t0_split:
        empty["shape_eval_incomplete_reason"] = "missing_t_plus10_in_same_split"
        return empty, []
    shape_eval_date = _date_at(arrays, eval_pos)
    offsets = list(range(-10, 0)) + list(range(1, 11))
    core_positions, missing_offsets = _relative_window_positions(arrays, t0_pos, offsets, t0_split)
    core = {offset: t0_pos + offset for offset in offsets if (t0_pos + offset) in core_positions}
    output: dict[str, Any] = {
        "family_signal_event_id": event_id,
        "shape_eval_date": shape_eval_date,
        "shape_eval_close": _safe_float(arrays["close"][eval_pos]),
        "shape_eval_next_open": _safe_float(arrays["open"][eval_pos + 1]) if eval_pos + 1 < len(arrays["date"]) else np.nan,
        "shape_eval_complete_flag": True,
        "shape_eval_incomplete_reason": "",
        "shape_core_window_complete_flag": not missing_offsets,
        "shape_core_window_bar_count": len(core_positions),
        "shape_core_missing_offsets": "|".join(str(v) for v in missing_offsets),
        "core_window_excludes_t0_flag": 0 not in offsets,
        "core_pre_bar_count": 10 - len([v for v in missing_offsets if v < 0]),
        "core_post_bar_count": 10 - len([v for v in missing_offsets if v > 0]),
    }
    window_rows: list[dict[str, Any]] = []
    if missing_offsets:
        for flag in DETAILED_FLAGS + BAD_ITEMS:
            output[flag] = pd.NA
        output.update(
            {
                "bad_score_complete_flag": False,
                "bad_score_v1": np.nan,
                "bad_score_bucket": "incomplete",
                "pass_primary_badshape_filter": pd.NA,
                "drop_primary_badshape_filter": pd.NA,
            }
        )
        output.update(_compute_filter_path(arrays, eval_pos, config))
        return output, window_rows

    core_offsets = offsets
    core_positions = [core[offset] for offset in core_offsets]
    closes = _series_at(arrays, "close", core_positions)
    highs = _series_at(arrays, "high", core_positions)
    lows = _series_at(arrays, "low", core_positions)
    opens = _series_at(arrays, "open", core_positions)
    volumes = _series_at(arrays, "volume", core_positions)
    returns = _series_at(arrays, "daily_return", core_positions)
    volume20 = _safe_float(arrays["volume_mean20_asof"][eval_pos])
    volume60 = _safe_float(arrays["volume_mean60_asof"][eval_pos])
    ret20 = _safe_float(arrays["close"][eval_pos] / arrays["close"][t0_pos - 10] - 1.0) if t0_pos - 10 >= 0 else np.nan
    ma20_eval = _safe_float(arrays["ma20_asof"][eval_pos])
    ma20_slope = _safe_float(arrays["ma20_slope5_asof"][eval_pos])
    close_eval = _safe_float(arrays["close"][eval_pos])
    output.update(
        {
            "ret20_core_t_minus10_to_t_plus10": ret20,
            "volume_mean20_at_t10": volume20,
            "volume_mean60_at_t10": volume60,
            "volume20_to_volume60_ratio": _safe_div(volume20, volume60),
            "ma20_at_t10": ma20_eval,
            "ma20_slope5_at_t10": ma20_slope,
            "atr20_pct_rank252_t_minus10": _safe_float(arrays["atr20_pct_rank252"][core[-10]]),
            "atr20_pct_rank252_t_plus10": _safe_float(arrays["atr20_pct_rank252"][core[10]]),
            "atr20_pct_t_minus10": _safe_float(arrays["atr20_pct_wilder"][core[-10]]),
            "atr20_pct_t_plus10": _safe_float(arrays["atr20_pct_wilder"][core[10]]),
        }
    )

    volume_stall_complete = _finite(volume20) and _finite(volume60) and _finite(ret20)
    volume_stall = volume20 > volume60 and ret20 <= 0.02 if volume_stall_complete else pd.NA
    failed_breakout, failed_breakout_count = _compute_failed_breakout(core, arrays)
    ranges = highs - lows
    upper_shadows = highs - np.maximum(opens, closes)
    upper_shadow_ratio = np.divide(upper_shadows, ranges, out=np.full_like(upper_shadows, np.nan, dtype=float), where=ranges > 0)
    upper_shadow_count = int(np.nansum(upper_shadow_ratio > 0.50))
    dense_upper_shadow = upper_shadow_count >= 3
    up_mask = returns > 0
    down_mask = returns < 0
    up_count = int(np.nansum(up_mask))
    down_count = int(np.nansum(down_mask))
    up_avg_volume = float(np.nanmean(volumes[up_mask])) if up_count else np.nan
    down_avg_volume = float(np.nanmean(volumes[down_mask])) if down_count else np.nan
    up_avg_abs_return = float(np.nanmean(np.abs(returns[up_mask]))) if up_count else np.nan
    down_avg_abs_return = float(np.nanmean(np.abs(returns[down_mask]))) if down_count else np.nan
    down_volume_complete = up_count >= 3 and down_count >= 3 and _finite(up_avg_volume) and _finite(down_avg_volume)
    down_volume_dominance = down_avg_volume > up_avg_volume if down_volume_complete else pd.NA
    ma20_break, ma20_break_count = _compute_ma20_break_no_reclaim(core, arrays)
    large_bear, large_bear_count = _compute_large_bearish(core_offsets, core_positions, arrays)
    atr_rank_minus10 = output["atr20_pct_rank252_t_minus10"]
    atr_rank_plus10 = output["atr20_pct_rank252_t_plus10"]
    volatility_complete = _finite(atr_rank_minus10) and _finite(atr_rank_plus10) and _finite(ret20)
    volatility_up_no_price = atr_rank_plus10 > atr_rank_minus10 + 0.10 and ret20 <= 0.05 if volatility_complete else pd.NA
    abs_sum = float(np.nansum(np.abs(returns))) if len(returns) else np.nan
    upside_efficiency = _safe_div(abs(ret20), abs_sum)
    low_efficiency_complete = _finite(upside_efficiency) and _finite(output["volume20_to_volume60_ratio"]) and volatility_complete
    low_upside_efficiency = (
        upside_efficiency < 0.20 and output["volume20_to_volume60_ratio"] > 1.0 and atr_rank_plus10 > atr_rank_minus10
        if low_efficiency_complete
        else pd.NA
    )
    recent5_lows = [core[o] for o in range(6, 11)]
    prior15_lows = [core[o] for o in list(range(-10, 0)) + list(range(1, 6))]
    recent5_low = float(np.nanmin(_series_at(arrays, "low", recent5_lows)))
    prior15_low = float(np.nanmin(_series_at(arrays, "low", prior15_lows)))
    recent_high = float(np.nanmax(_series_at(arrays, "high", recent5_lows)))
    prior_high = float(np.nanmax(_series_at(arrays, "high", prior15_lows)))
    lower_low_lower_high = recent5_low < prior15_low and recent_high <= prior_high
    gap_count = 0
    gap_fade_high_level_count = 0
    for pos in core_positions:
        prev_close = _safe_float(arrays["prev_close"][pos])
        open_v = _safe_float(arrays["open"][pos])
        high_v = _safe_float(arrays["high"][pos])
        close_v = _safe_float(arrays["close"][pos])
        ret60 = _safe_float(arrays["ret60_asof"][pos])
        if not all(_finite(v) for v in [prev_close, open_v, high_v, close_v]):
            continue
        if open_v > prev_close * 1.01 and high_v > open_v and close_v < open_v:
            gap_count += 1
            if _finite(ret60) and ret60 > 0.20:
                gap_fade_high_level_count += 1
    gap_up_fade = gap_count >= 2
    output.update(
        {
            "volume_stall_flag": _flag_or_na(volume_stall, volume_stall_complete),
            "failed_breakout_flag": failed_breakout,
            "dense_upper_shadow_flag": dense_upper_shadow,
            "down_volume_dominance_flag": _flag_or_na(down_volume_dominance, down_volume_complete),
            "ma20_break_no_reclaim_flag": ma20_break,
            "large_bearish_engulf_flag": large_bear,
            "volatility_up_no_price_flag": _flag_or_na(volatility_up_no_price, volatility_complete),
            "low_upside_efficiency_flag": _flag_or_na(low_upside_efficiency, low_efficiency_complete),
            "lower_low_lower_high_flag": lower_low_lower_high,
            "gap_up_fade_flag": gap_up_fade,
            "failed_breakout_count": failed_breakout_count,
            "upper_shadow_count": upper_shadow_count,
            "up_day_count": up_count,
            "down_day_count": down_count,
            "up_day_avg_volume": up_avg_volume,
            "down_day_avg_volume": down_avg_volume,
            "up_day_avg_abs_return": up_avg_abs_return,
            "down_day_avg_abs_return": down_avg_abs_return,
            "ma20_break_no_reclaim_count": ma20_break_count,
            "large_bearish_engulf_count": large_bear_count,
            "upside_efficiency": upside_efficiency,
            "recent5_low": recent5_low,
            "prior15_low": prior15_low,
            "recent5_high": recent_high,
            "prior15_high": prior_high,
            "gap_up_fade_count": gap_count,
            "gap_up_fade_high_level_count": gap_fade_high_level_count,
        }
    )
    volume_down_days = int(
        np.nansum((returns < 0) & (volumes >= 1.5 * np.asarray([_safe_float(arrays["volume_mean60_asof"][p]) for p in core_positions])))
    )
    max_up = float(np.nanmax(returns)) if np.isfinite(returns).any() else np.nan
    max_down = float(np.nanmin(returns)) if np.isfinite(returns).any() else np.nan
    bad_items: dict[str, Any] = {
        "bad_item_01_ret20_lt0": _flag_or_na(ret20 < 0.0, _finite(ret20)),
        "bad_item_02_close_below_ma20": _flag_or_na(close_eval < ma20_eval, _finite(close_eval) and _finite(ma20_eval)),
        "bad_item_03_ma20_slope_negative": _flag_or_na(ma20_slope < 0.0, _finite(ma20_slope)),
        "bad_item_04_recent5_low_below_prior15_low": _flag_or_na(recent5_low < prior15_low, _finite(recent5_low) and _finite(prior15_low)),
        "bad_item_05_down_volume_gt_up_volume": _flag_or_na(down_avg_volume > up_avg_volume, down_volume_complete),
        "bad_item_06_max_down_abs_gt_max_up": _flag_or_na(abs(max_down) > max_up, _finite(max_down) and _finite(max_up)),
        "bad_item_07_atr_rank_up_ret20_low": _flag_or_na(volatility_up_no_price, volatility_complete),
        "bad_item_08_upper_shadow_count_ge3": _flag_or_na(upper_shadow_count >= 3, True),
        "bad_item_09_volume_down_day_ge2": _flag_or_na(volume_down_days >= 2, True),
        "bad_item_10_failed_breakout_3d": failed_breakout,
    }
    output.update(bad_items)
    complete = all(pd.notna(output[item]) for item in BAD_ITEMS)
    output["bad_score_complete_flag"] = complete
    if complete:
        score = int(sum(1 for item in BAD_ITEMS if bool(output[item])))
        output["bad_score_v1"] = score
        if score <= 2:
            bucket = "0_2"
        elif score <= 4:
            bucket = "3_4"
        elif score <= 6:
            bucket = "5_6"
        else:
            bucket = "7plus"
        output["bad_score_bucket"] = bucket
        threshold = int(config["badscore"]["primary_drop_bad_score_gte"])
        output["drop_primary_badshape_filter"] = score >= threshold
        output["pass_primary_badshape_filter"] = score < threshold
    else:
        output["bad_score_v1"] = np.nan
        output["bad_score_bucket"] = "incomplete"
        output["drop_primary_badshape_filter"] = pd.NA
        output["pass_primary_badshape_filter"] = pd.NA
    output.update(_compute_filter_path(arrays, eval_pos, config))
    return output, window_rows


def _compute_feature_panels(events: pd.DataFrame, arrays_by_instrument: dict[str, dict[str, Any]], config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    total = len(events)
    for idx, row in events.iterrows():
        if idx and idx % 25000 == 0:
            print(f"computed R03e shape features for {idx}/{total} events", flush=True)
        features, windows = _compute_shape_for_event(row, arrays_by_instrument, config)
        feature_rows.append(features)
        window_rows.extend(windows)
    return pd.DataFrame(feature_rows), pd.DataFrame(window_rows)


def _window_rows_for_event(row: pd.Series, arrays_by_instrument: dict[str, dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    event_id = str(row["family_signal_event_id"])
    arrays = arrays_by_instrument.get(str(row["instrument_id"]).upper())
    t0_pos = _position_for_date(arrays, row["t0_entry_date"]) if arrays is not None else None
    t0_split = str(arrays["split"][t0_pos]) if arrays is not None and t0_pos is not None else ""
    start = int(config["shape"].get("write_window_offsets", {}).get("start", -252))
    end = int(config["shape"].get("write_window_offsets", {}).get("end", 131))
    rows: list[dict[str, Any]] = []
    for offset in range(start, end + 1):
        pos = t0_pos + offset if t0_pos is not None else None
        present = arrays is not None and pos is not None and 0 <= pos < len(arrays["date"])
        split = str(arrays["split"][pos]) if present else ""
        rows.append(
            {
                "family_signal_event_id": event_id,
                "relative_offset": int(offset),
                "is_shape_core_window_20d": bool(offset != 0 and -10 <= offset <= 10),
                "is_t0_entry_bar": bool(offset == 0),
                "within_t0_split": bool(present and split == t0_split),
                "date": _date_at(arrays, pos) if present else "",
                "split": split,
                "open": _safe_float(arrays["open"][pos]) if present else np.nan,
                "high": _safe_float(arrays["high"][pos]) if present else np.nan,
                "low": _safe_float(arrays["low"][pos]) if present else np.nan,
                "close": _safe_float(arrays["close"][pos]) if present else np.nan,
                "volume": _safe_float(arrays["volume"][pos]) if present else np.nan,
                "money": _safe_float(arrays["money"][pos]) if present else np.nan,
                "atr20_pct_rank252": _safe_float(arrays["atr20_pct_rank252"][pos]) if present else np.nan,
            }
        )
    return rows


def _write_window_panel(
    events: pd.DataFrame,
    arrays_by_instrument: dict[str, dict[str, Any]],
    config: dict[str, Any],
    path: Path,
    chunk_events: int = 1000,
) -> None:
    writer: pq.ParquetWriter | None = None
    try:
        for start_idx in range(0, len(events), chunk_events):
            end_idx = min(start_idx + chunk_events, len(events))
            rows: list[dict[str, Any]] = []
            for _, row in events.iloc[start_idx:end_idx].iterrows():
                rows.extend(_window_rows_for_event(row, arrays_by_instrument, config))
            frame = pd.DataFrame(rows)
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(path, table.schema, compression="zstd")
            writer.write_table(table)
            if start_idx and start_idx % (chunk_events * 25) == 0:
                print(f"wrote R03e OHLCV window rows for {start_idx}/{len(events)} events", flush=True)
    finally:
        if writer is not None:
            writer.close()


def _baseline1_mask(panel: pd.DataFrame) -> pd.Series:
    return (
        panel["shape_eval_complete_flag"].astype(bool)
        & panel["shape_core_window_complete_flag"].astype(bool)
        & panel["bad_score_complete_flag"].astype(bool)
        & panel["filter_entry_valid"].astype(bool)
        & panel["filter_path_complete_120d"].astype(bool)
        & panel["filter_path_label"].isin(PATH_LABELS)
    )


def _policy_mask(panel: pd.DataFrame, policy: str) -> tuple[pd.Series, pd.Series, str]:
    base = _baseline1_mask(panel)
    if policy == "no_badshape_filter_t10_survivor":
        return base, pd.Series(False, index=panel.index), "baseline_1"
    if policy.startswith("drop_score_ge"):
        threshold = int(policy.replace("drop_score_ge", ""))
        drop = base & (panel["bad_score_v1"] >= threshold)
        return base & ~drop, drop, "baseline_1"
    if policy in COMPONENT_POLICIES:
        col = COMPONENT_POLICIES[policy]
        eligible = base & panel[col].notna()
        drop = eligible & panel[col].astype(bool)
        return eligible & ~drop, drop, f"component_non_null:{col}"
    raise ValueError(policy)


def _add_group_keys(df: pd.DataFrame) -> list[tuple[str, str, str, str, pd.DataFrame, str]]:
    groups: list[tuple[str, str, str, str, pd.DataFrame, str]] = []
    for split in ALL_SPLITS:
        split_df = df if split == "all" else df[df["split"].eq(split)]
        if split_df.empty:
            continue
        for (event_scope, event_stage, family_id), group in split_df.groupby(["event_scope", "event_stage", "family_id"], dropna=False):
            g = group.copy()
            g["_agg_weight"] = 1.0
            groups.append((split, str(event_scope), str(event_stage), str(family_id), g, "per_family"))
        for (event_scope, event_stage), group in split_df.groupby(["event_scope", "event_stage"], dropna=False):
            g = group.copy()
            g["_agg_weight"] = g["dedup_weight"].astype(float)
            groups.append((split, str(event_scope), str(event_stage), "ALL", g, "all_families_dedup_weighted"))
    return groups


def _summary_metrics(group: pd.DataFrame, label_prefix: str = "filter") -> dict[str, Any]:
    weight_col = "_agg_weight"
    denominator = float(group[weight_col].sum()) if not group.empty else 0.0
    p_good = _weighted_rate(group, group[f"{label_prefix}_path_label"].eq("good_path"), weight_col)
    p_bad = _weighted_rate(group, group[f"{label_prefix}_path_label"].eq("bad_path"), weight_col)
    p_neutral = _weighted_rate(group, group[f"{label_prefix}_path_label"].eq("neutral_path"), weight_col)
    big_col = (
        "filter_anchor_big_winner_next_open"
        if label_prefix == "filter"
        else "signal_anchor_big_winner_next_open"
    )
    big_rate = _weighted_rate(group, group[big_col].astype("boolean").fillna(False), weight_col) if big_col in group else np.nan
    return {
        "event_count": int(len(group)),
        "weighted_event_count": denominator,
        "unique_instrument_count": int(group["instrument_id"].nunique()) if "instrument_id" in group else 0,
        "unique_signal_date_count": int(group["signal_date"].nunique()) if "signal_date" in group else 0,
        "p_good": p_good,
        "p_bad": p_bad,
        "p_neutral": p_neutral,
        "p_good_minus_p_bad": p_good - p_bad if _finite(p_good) and _finite(p_bad) else np.nan,
        "big_winner_rate": big_rate,
    }


def _component_definition_audit() -> pd.DataFrame:
    rows = [
        ("volume_stall_flag", "20日均量大于60日均量且核心20日净涨幅不高"),
        ("failed_breakout_flag", "核心窗口内突破前20日或52周高点后3日内跌回突破位"),
        ("dense_upper_shadow_flag", "核心20日上影线/振幅大于50%的天数不少于3天"),
        ("down_volume_dominance_flag", "下跌日均量大于上涨日均量且上下跌日样本均不少于3天"),
        ("ma20_break_no_reclaim_flag", "跌破MA20后3至5日内无法收回且MA20斜率不强"),
        ("large_bearish_engulf_flag", "大阴线放量且收盘接近日低，吞没前期涨幅"),
        ("volatility_up_no_price_flag", "ATR20百分位上升但20日收益不高"),
        ("low_upside_efficiency_flag", "波动和成交抬升但上涨效率低"),
        ("lower_low_lower_high_flag", "最近5日低点低于前15日低点且高点未突破"),
        ("gap_up_fade_flag", "多次跳空高开冲高后收在开盘价下方"),
    ]
    return pd.DataFrame(
        [
            {
                "component_id": component,
                "definition": definition,
                "primary_window": "T-10..T-1 + T+1..T+10",
                "t0_included_in_shape_count": False,
                "null_handling": "component policy excludes null rows from its own denominator",
            }
            for component, definition in rows
        ]
    )


def _component_summary(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    base = panel.copy()
    for split, event_scope, event_stage, family_id, group, family_group in _add_group_keys(base):
        for component in DETAILED_FLAGS:
            eligible = group[group[component].notna()].copy()
            eligible["_agg_weight"] = eligible["_agg_weight"].astype(float)
            rows.append(
                {
                    "split": split,
                    "event_scope": event_scope,
                    "event_stage": event_stage,
                    "family_group": family_group,
                    "family_id": family_id,
                    "component_id": component,
                    "non_null_event_count": int(len(eligible)),
                    "null_event_count": int(group[component].isna().sum()),
                    "weighted_non_null_event_count": float(eligible["_agg_weight"].sum()) if not eligible.empty else 0.0,
                    "component_true_rate": _weighted_rate(eligible, eligible[component].astype(bool), "_agg_weight") if not eligible.empty else np.nan,
                    "component_true_count": int(eligible[component].astype(bool).sum()) if not eligible.empty else 0,
                }
            )
    return pd.DataFrame(rows)


def _bad_score_bucket_summary(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, event_scope, event_stage, family_id, group, family_group in _add_group_keys(panel):
        group = group[_baseline1_mask(group)].copy()
        for bucket, bucket_df in group.groupby("bad_score_bucket", dropna=False):
            rows.append(
                {
                    "split": split,
                    "event_scope": event_scope,
                    "event_stage": event_stage,
                    "family_group": family_group,
                    "family_id": family_id,
                    "bad_score_bucket": str(bucket),
                    **_summary_metrics(bucket_df, "filter"),
                }
            )
    return pd.DataFrame(rows)


def _threshold_tradeoff(panel: pd.DataFrame) -> pd.DataFrame:
    policies = ["no_badshape_filter_t10_survivor"] + [f"drop_score_ge{v}" for v in [3, 5, 7]] + sorted(COMPONENT_POLICIES)
    rows: list[dict[str, Any]] = []
    parent_index: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for split, event_scope, event_stage, family_id, group, family_group in _add_group_keys(panel):
        for policy in policies:
            pass_mask, drop_mask, denominator_policy = _policy_mask(group, policy)
            denom_mask = pass_mask | drop_mask
            denom = group[denom_mask].copy()
            passed = group[pass_mask].copy()
            dropped = group[drop_mask].copy()
            metrics = _summary_metrics(passed, "filter") if not passed.empty else {
                "event_count": 0,
                "weighted_event_count": 0.0,
                "unique_instrument_count": 0,
                "unique_signal_date_count": 0,
                "p_good": np.nan,
                "p_bad": np.nan,
                "p_neutral": np.nan,
                "p_good_minus_p_bad": np.nan,
                "big_winner_rate": np.nan,
            }
            signal_big = group["signal_anchor_big_winner_next_open"].astype("boolean").fillna(False)
            dropped_signal_big = float(group.loc[drop_mask & signal_big, "_agg_weight"].sum())
            total_signal_big = float(group.loc[denom_mask & signal_big, "_agg_weight"].sum())
            row = {
                "split": split,
                "event_scope": event_scope,
                "event_stage": event_stage,
                "family_group": family_group,
                "family_id": family_id,
                "filter_policy": policy,
                "denominator_policy": denominator_policy,
                "baseline_event_count": int(denom_mask.sum()),
                "baseline_weighted_event_count": float(group.loc[denom_mask, "_agg_weight"].sum()),
                "passed_event_count": int(pass_mask.sum()),
                "dropped_event_count": int(drop_mask.sum()),
                "dropped_weighted_event_count": float(group.loc[drop_mask, "_agg_weight"].sum()),
                "dropped_event_rate": _safe_div(float(group.loc[drop_mask, "_agg_weight"].sum()), float(group.loc[denom_mask, "_agg_weight"].sum())),
                "signal_anchor_big_winner_weight": total_signal_big,
                "signal_anchor_big_winner_dropped_weight": dropped_signal_big,
                "signal_anchor_big_winner_retention_rate": 1.0 - _safe_div(dropped_signal_big, total_signal_big)
                if total_signal_big > 0
                else np.nan,
                "dropped_p_bad": _weighted_rate(dropped, dropped["filter_path_label"].eq("bad_path"), "_agg_weight") if not dropped.empty else np.nan,
                **metrics,
            }
            key = (split, event_scope, event_stage, family_group, family_id)
            if policy == "no_badshape_filter_t10_survivor":
                parent_index[key] = row
                row["delta_p_bad_vs_parent"] = 0.0
                row["delta_p_good_vs_parent"] = 0.0
                row["delta_p_good_minus_p_bad_vs_parent"] = 0.0
                row["delta_big_winner_rate_vs_parent"] = 0.0
            else:
                parent = parent_index.get(key)
                row["delta_p_bad_vs_parent"] = row["p_bad"] - parent["p_bad"] if parent and _finite(row["p_bad"]) and _finite(parent["p_bad"]) else np.nan
                row["delta_p_good_vs_parent"] = row["p_good"] - parent["p_good"] if parent and _finite(row["p_good"]) and _finite(parent["p_good"]) else np.nan
                row["delta_p_good_minus_p_bad_vs_parent"] = (
                    row["p_good_minus_p_bad"] - parent["p_good_minus_p_bad"]
                    if parent and _finite(row["p_good_minus_p_bad"]) and _finite(parent["p_good_minus_p_bad"])
                    else np.nan
                )
                row["delta_big_winner_rate_vs_parent"] = (
                    row["big_winner_rate"] - parent["big_winner_rate"]
                    if parent and _finite(row["big_winner_rate"]) and _finite(parent["big_winner_rate"])
                    else np.nan
                )
            rows.append(row)
    return pd.DataFrame(rows)


def _filtered_outcome_summary(panel: pd.DataFrame) -> pd.DataFrame:
    policies = ["no_badshape_filter_t10_survivor"] + [f"drop_score_ge{v}" for v in [3, 5, 7]]
    outcome_defs = [
        ("signal_anchor_retention_audit", "signal_anchor_big_winner_next_open", "signal_anchor_path_label"),
        ("filter_decision_next_open_anchor", "filter_anchor_big_winner_next_open", "filter_path_label"),
        ("filter_decision_close_anchor", "filter_anchor_big_winner_close", "filter_path_label"),
    ]
    rows: list[dict[str, Any]] = []
    parent_index: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
    for split, event_scope, event_stage, family_id, group, family_group in _add_group_keys(panel):
        for outcome_anchor, big_col, path_col in outcome_defs:
            for policy in policies:
                pass_mask, drop_mask, denominator_policy = _policy_mask(group, policy)
                denom_mask = pass_mask | drop_mask
                kept = group[pass_mask].copy()
                dropped = group[drop_mask].copy()
                metrics = {
                    "event_count": int(len(kept)),
                    "weighted_event_count": float(kept["_agg_weight"].sum()) if not kept.empty else 0.0,
                    "unique_instrument_count": int(kept["instrument_id"].nunique()) if not kept.empty else 0,
                    "unique_signal_date_count": int(kept["signal_date"].nunique()) if not kept.empty else 0,
                    "p_good": _weighted_rate(kept, kept[path_col].eq("good_path"), "_agg_weight") if not kept.empty else np.nan,
                    "p_bad": _weighted_rate(kept, kept[path_col].eq("bad_path"), "_agg_weight") if not kept.empty else np.nan,
                    "p_neutral": _weighted_rate(kept, kept[path_col].eq("neutral_path"), "_agg_weight") if not kept.empty else np.nan,
                    "big_winner_rate": _weighted_rate(kept, kept[big_col].astype("boolean").fillna(False), "_agg_weight") if not kept.empty else np.nan,
                }
                metrics["p_good_minus_p_bad"] = (
                    metrics["p_good"] - metrics["p_bad"] if _finite(metrics["p_good"]) and _finite(metrics["p_bad"]) else np.nan
                )
                row = {
                    "split": split,
                    "event_scope": event_scope,
                    "event_stage": event_stage,
                    "family_group": family_group,
                    "family_id": family_id,
                    "outcome_anchor": outcome_anchor,
                    "filter_policy": policy,
                    "denominator_policy": denominator_policy,
                    "baseline_event_count": int(denom_mask.sum()),
                    "baseline_weighted_event_count": float(group.loc[denom_mask, "_agg_weight"].sum()),
                    "passed_event_count": int(pass_mask.sum()),
                    "dropped_event_count": int(drop_mask.sum()),
                    "dropped_p_bad": _weighted_rate(dropped, dropped[path_col].eq("bad_path"), "_agg_weight") if not dropped.empty else np.nan,
                    **metrics,
                }
                key = (split, event_scope, event_stage, family_group, family_id, outcome_anchor)
                if policy == "no_badshape_filter_t10_survivor":
                    parent_index[key] = row
                    row["delta_p_bad_vs_parent"] = 0.0
                    row["delta_p_good_vs_parent"] = 0.0
                    row["delta_p_good_minus_p_bad_vs_parent"] = 0.0
                    row["delta_big_winner_rate_vs_parent"] = 0.0
                else:
                    parent = parent_index.get(key)
                    row["delta_p_bad_vs_parent"] = row["p_bad"] - parent["p_bad"] if parent and _finite(row["p_bad"]) and _finite(parent["p_bad"]) else np.nan
                    row["delta_p_good_vs_parent"] = row["p_good"] - parent["p_good"] if parent and _finite(row["p_good"]) and _finite(parent["p_good"]) else np.nan
                    row["delta_p_good_minus_p_bad_vs_parent"] = (
                        row["p_good_minus_p_bad"] - parent["p_good_minus_p_bad"]
                        if parent and _finite(row["p_good_minus_p_bad"]) and _finite(parent["p_good_minus_p_bad"])
                        else np.nan
                    )
                    row["delta_big_winner_rate_vs_parent"] = (
                        row["big_winner_rate"] - parent["big_winner_rate"]
                        if parent and _finite(row["big_winner_rate"]) and _finite(parent["big_winner_rate"])
                        else np.nan
                    )
                rows.append(row)
    return pd.DataFrame(rows)


def _component_overlap_audit(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, event_scope, event_stage, family_id, group, family_group in _add_group_keys(panel):
        base = group[_baseline1_mask(group)].copy()
        if base.empty:
            continue
        for a, b in itertools.combinations(DETAILED_FLAGS, 2):
            eligible = base[base[a].notna() & base[b].notna()].copy()
            if eligible.empty:
                continue
            a_true = eligible[a].astype(bool)
            b_true = eligible[b].astype(bool)
            both = a_true & b_true
            union = a_true | b_true
            rows.append(
                {
                    "split": split,
                    "event_scope": event_scope,
                    "event_stage": event_stage,
                    "family_group": family_group,
                    "family_id": family_id,
                    "component_a": a,
                    "component_b": b,
                    "eligible_event_count": int(len(eligible)),
                    "component_a_true_rate": _weighted_rate(eligible, a_true, "_agg_weight"),
                    "component_b_true_rate": _weighted_rate(eligible, b_true, "_agg_weight"),
                    "both_true_rate": _weighted_rate(eligible, both, "_agg_weight"),
                    "jaccard_true": _safe_div(float(eligible.loc[both, "_agg_weight"].sum()), float(eligible.loc[union, "_agg_weight"].sum())),
                }
            )
    return pd.DataFrame(rows)


def _survival_and_timing_bias_audit(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, event_scope, event_stage, family_id, group, family_group in _add_group_keys(panel):
        baseline0 = group.copy()
        baseline0["_agg_weight"] = baseline0["_agg_weight"].astype(float)
        baseline1 = group[_baseline1_mask(group)].copy()
        baseline1["_agg_weight"] = baseline1["_agg_weight"].astype(float)
        for label, data in [("baseline_0_all_events", baseline0), ("baseline_1_t10_survivor_badscore_evaluable", baseline1)]:
            rows.append(
                {
                    "split": split,
                    "event_scope": event_scope,
                    "event_stage": event_stage,
                    "family_group": family_group,
                    "family_id": family_id,
                    "baseline": label,
                    "event_count": int(len(data)),
                    "weighted_event_count": float(data["_agg_weight"].sum()) if not data.empty else 0.0,
                    "shape_eval_complete_rate": _weighted_rate(data, data["shape_eval_complete_flag"].astype(bool), "_agg_weight") if not data.empty else np.nan,
                    "bad_score_complete_rate": _weighted_rate(data, data["bad_score_complete_flag"].astype(bool), "_agg_weight") if not data.empty else np.nan,
                    "filter_path_complete_rate": _weighted_rate(data, data["filter_path_complete_120d"].astype(bool), "_agg_weight") if not data.empty else np.nan,
                    "signal_anchor_big_winner_rate": _weighted_rate(data, data["signal_anchor_big_winner_next_open"].astype("boolean").fillna(False), "_agg_weight") if not data.empty else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _split_stability_audit(outcome: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    primary = config["primary_decision"]
    rows: list[dict[str, Any]] = []
    for (event_scope, event_stage, family_group, family_id, outcome_anchor, filter_policy), group in outcome.groupby(
        ["event_scope", "event_stage", "family_group", "family_id", "outcome_anchor", "filter_policy"], dropna=False
    ):
        group = group.set_index("split")
        if "validation" not in group.index or "robustness" not in group.index:
            continue
        val = group.loc["validation"]
        rob = group.loc["robustness"]
        for metric in ["p_bad", "p_good", "p_good_minus_p_bad", "big_winner_rate"]:
            val_value = _safe_float(val[metric])
            rob_value = _safe_float(rob[metric])
            rows.append(
                {
                    "event_scope": event_scope,
                    "event_stage": event_stage,
                    "family_group": family_group,
                    "family_id": family_id,
                    "outcome_anchor": outcome_anchor,
                    "filter_policy": filter_policy,
                    "metric": metric,
                    "validation_value": val_value,
                    "robustness_value": rob_value,
                    "robustness_minus_validation": rob_value - val_value if _finite(val_value) and _finite(rob_value) else np.nan,
                    "primary_decision_grain": bool(
                        event_scope == primary["event_scope"]
                        and event_stage == primary["event_stage"]
                        and family_group == primary["family_group"]
                        and family_id == "ALL"
                        and outcome_anchor == primary["outcome_anchor"]
                        and filter_policy == primary["filter_policy"]
                    ),
                }
            )
    return pd.DataFrame(rows)


def _make_decision(outcome: pd.DataFrame, threshold: pd.DataFrame, config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    primary = config["primary_decision"]
    sample = config["sample_sufficiency"]
    rows = outcome[
        (outcome["event_scope"] == primary["event_scope"])
        & (outcome["event_stage"] == primary["event_stage"])
        & (outcome["family_group"] == primary["family_group"])
        & (outcome["family_id"] == "ALL")
        & (outcome["outcome_anchor"] == primary["outcome_anchor"])
        & (outcome["filter_policy"] == primary["filter_policy"])
        & (outcome["split"].isin(["validation", "robustness"]))
    ].copy()
    parent = outcome[
        (outcome["event_scope"] == primary["event_scope"])
        & (outcome["event_stage"] == primary["event_stage"])
        & (outcome["family_group"] == primary["family_group"])
        & (outcome["family_id"] == "ALL")
        & (outcome["outcome_anchor"] == primary["outcome_anchor"])
        & (outcome["filter_policy"] == primary["parent_policy"])
        & (outcome["split"].isin(["validation", "robustness"]))
    ].copy()
    details: dict[str, Any] = {
        "primary_rows": rows.to_dict("records"),
        "parent_rows": parent.to_dict("records"),
        "primary_decision_config": primary,
    }
    if len(rows) != 2 or len(parent) != 2:
        return "insufficient_denominator", details | {"failure_reason": "missing primary validation/robustness rows"}
    if (rows["baseline_event_count"] < int(sample["min_split_denominator"])).any():
        return "insufficient_denominator", details | {"failure_reason": "primary split denominator below minimum"}
    pbad_reductions = -rows["delta_p_bad_vs_parent"].astype(float)
    edge_lifts = rows["delta_p_good_minus_p_bad_vs_parent"].astype(float)
    pgood_drops = -rows["delta_p_good_vs_parent"].astype(float)
    big_retention = []
    for split in ["validation", "robustness"]:
        thresh_row = threshold[
            (threshold["split"] == split)
            & (threshold["event_scope"] == primary["event_scope"])
            & (threshold["event_stage"] == primary["event_stage"])
            & (threshold["family_group"] == primary["family_group"])
            & (threshold["family_id"] == "ALL")
            & (threshold["filter_policy"] == primary["filter_policy"])
        ]
        if thresh_row.empty:
            big_retention.append(np.nan)
        else:
            big_retention.append(_safe_float(thresh_row.iloc[0]["signal_anchor_big_winner_retention_rate"]))
    details["pbad_reductions"] = pbad_reductions.tolist()
    details["edge_lifts"] = edge_lifts.tolist()
    details["pgood_drops"] = pgood_drops.tolist()
    details["signal_anchor_big_winner_retention_rates"] = big_retention
    reduces_bad = bool((pbad_reductions >= float(sample["min_material_pbad_reduction_pp"])).all())
    lifts_edge = bool((edge_lifts >= float(sample["min_material_pgood_minus_pbad_lift_pp"])).all())
    preserves_pgood = bool((pgood_drops <= float(sample["max_allowed_pgood_drop_pp"])).all())
    retains_winners = bool(np.all(np.asarray(big_retention, dtype=float) >= float(sample["min_signal_anchor_big_winner_retention_rate"])))
    if reduces_bad and lifts_edge and preserves_pgood and retains_winners:
        return "badshape_filter_supported", details
    if reduces_bad and (not preserves_pgood or not retains_winners):
        return "badshape_filter_reduces_bad_path_but_costs_winners", details
    return "badshape_filter_no_incremental_edge", details


def _write_final_report(
    path: Path,
    manifest: dict[str, Any],
    readiness: pd.DataFrame,
    survival: pd.DataFrame,
    bucket: pd.DataFrame,
    threshold: pd.DataFrame,
    outcome: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    primary = config["primary_decision"]
    primary_outcome = outcome[
        (outcome["event_scope"] == primary["event_scope"])
        & (outcome["event_stage"] == primary["event_stage"])
        & (outcome["family_group"] == primary["family_group"])
        & (outcome["family_id"] == "ALL")
        & (outcome["outcome_anchor"] == primary["outcome_anchor"])
        & (outcome["filter_policy"].isin([primary["parent_policy"], primary["filter_policy"]]))
        & (outcome["split"].isin(["validation", "robustness"]))
    ].copy()
    primary_threshold = threshold[
        (threshold["event_scope"] == primary["event_scope"])
        & (threshold["event_stage"] == primary["event_stage"])
        & (threshold["family_group"] == primary["family_group"])
        & (threshold["family_id"] == "ALL")
        & (threshold["filter_policy"].isin([primary["parent_policy"], primary["filter_policy"]]))
        & (threshold["split"].isin(["validation", "robustness"]))
    ].copy()
    bucket_primary = bucket[
        (bucket["event_scope"] == primary["event_scope"])
        & (bucket["event_stage"] == primary["event_stage"])
        & (bucket["family_group"] == primary["family_group"])
        & (bucket["family_id"] == "ALL")
        & (bucket["split"].isin(["validation", "robustness"]))
    ].copy()
    lines = [
        "# R03e family signal bad-shape filter 诊断报告",
        "",
        f"- final_decision: `{manifest['final_decision']}`",
        f"- primary grain: `{primary['event_scope']} / {primary['event_stage']} / {primary['family_group']} / {primary['outcome_anchor']}`",
        "- 核心形态窗口: `T-10..T-1 + T+1..T+10`，T0 只作为开仓锚点，不进入 BadScore。",
        "- materialized OHLCV 窗口: `-252..+131`；长历史 ATR/MA as-of 用 provider full history 计算。",
        "- baseline_1: T+10 survivor + BadScore 可评估 + filter next-open 120d path complete。",
        "",
        "## 输入 readiness",
        "",
        readiness.to_markdown(index=False),
        "",
        "## Primary threshold tradeoff",
        "",
        primary_threshold[
            [
                "split",
                "filter_policy",
                "baseline_event_count",
                "passed_event_count",
                "dropped_event_rate",
                "p_good",
                "p_bad",
                "p_good_minus_p_bad",
                "big_winner_rate",
                "delta_p_bad_vs_parent",
                "delta_p_good_vs_parent",
                "delta_p_good_minus_p_bad_vs_parent",
                "signal_anchor_big_winner_retention_rate",
            ]
        ].to_markdown(index=False),
        "",
        "## Primary outcome",
        "",
        primary_outcome[
            [
                "split",
                "filter_policy",
                "baseline_event_count",
                "passed_event_count",
                "p_good",
                "p_bad",
                "p_good_minus_p_bad",
                "big_winner_rate",
                "delta_p_bad_vs_parent",
                "delta_p_good_vs_parent",
                "delta_p_good_minus_p_bad_vs_parent",
                "delta_big_winner_rate_vs_parent",
            ]
        ].to_markdown(index=False),
        "",
        "## BadScore 分桶",
        "",
        bucket_primary[
            [
                "split",
                "bad_score_bucket",
                "event_count",
                "p_good",
                "p_bad",
                "p_good_minus_p_bad",
                "big_winner_rate",
            ]
        ].sort_values(["split", "bad_score_bucket"]).to_markdown(index=False),
        "",
        "## Survival / timing bias",
        "",
        survival[
            (survival["event_scope"] == primary["event_scope"])
            & (survival["event_stage"] == primary["event_stage"])
            & (survival["family_group"] == primary["family_group"])
            & (survival["family_id"] == "ALL")
            & (survival["split"].isin(["validation", "robustness"]))
        ][
            [
                "split",
                "baseline",
                "event_count",
                "weighted_event_count",
                "shape_eval_complete_rate",
                "bad_score_complete_rate",
                "filter_path_complete_rate",
                "signal_anchor_big_winner_rate",
            ]
        ].to_markdown(index=False),
        "",
        "## 初步结论",
        "",
        "- 该诊断只回答 “family 信号后 T+10 才观察到的坏形态是否值得作为新开仓过滤器”，不把它解释为原 T0 信号本身的纯预测能力。",
        "- `drop_score_ge5` 的可用性由 validation 与 robustness 同时决定；如果 P_bad 下降但 P_good 或 signal-anchor big winner 保留率损失过大，决策会落到成本过高而非 supported。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _artifact_hashes(paths: list[Path]) -> dict[str, str]:
    return {relpath(path): _hash_file(path) for path in paths if path.exists()}


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(Path(config["output_root"]))
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    cache_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    readiness = _input_readiness(config)
    write_csv(readiness, reports_dir / "r03e_input_readiness_audit.csv")
    missing = readiness["status"].ne("present").any()
    upstream_failed = False
    for row in readiness.itertuples(index=False):
        if row.input_name == "validation" and row.validation_status and row.validation_status != "passed":
            upstream_failed = True
    if missing or upstream_failed:
        decision = "blocked_missing_required_input" if missing else "blocked_upstream_validation_failed"
        manifest = {
            "phase": config["phase"],
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "final_decision": decision,
            "failure_reason": "missing input" if missing else "upstream validation failed",
        }
        write_json(manifest, manifests_dir / "r03e_family_signal_bad_shape_filter_manifest.json")
        return manifest

    print("loading PIT stock spine and computing R03e as-of features", flush=True)
    stock = _prepare_stock(config)
    arrays = _build_stock_arrays(stock)
    print("loading event scopes", flush=True)
    events = _load_event_panel(config, arrays)
    event_path = cache_dir / "r03e_family_signal_event_panel.parquet"
    events.to_parquet(event_path, index=False)

    feature_path = cache_dir / "r03e_bad_shape_feature_panel.parquet"
    window_path = cache_dir / "r03e_ohlcv_shape_window_panel.parquet"
    if feature_path.exists():
        print("reusing existing R03e feature cache", flush=True)
        features = pd.read_parquet(feature_path)
        if len(features) != len(events) or not events["family_signal_event_id"].reset_index(drop=True).equals(
            features["family_signal_event_id"].reset_index(drop=True)
        ):
            print("existing R03e feature cache is stale; recomputing", flush=True)
            features, _ = _compute_feature_panels(events, arrays, config)
            features.to_parquet(feature_path, index=False)
    else:
        print(f"computing bad-shape features for {len(events)} family signal events", flush=True)
        features, _ = _compute_feature_panels(events, arrays, config)
        features.to_parquet(feature_path, index=False)

    window_start = int(config["shape"].get("write_window_offsets", {}).get("start", -252))
    window_end = int(config["shape"].get("write_window_offsets", {}).get("end", 131))
    window_stale = True
    if window_path.exists():
        try:
            offsets = pd.read_parquet(window_path, columns=["relative_offset"])["relative_offset"]
            window_stale = int(offsets.min()) > window_start or int(offsets.max()) < window_end
        except Exception:
            window_stale = True
    if window_stale:
        if window_path.exists():
            window_path.unlink()
        print(f"writing R03e OHLCV event window cache offsets {window_start}..{window_end}", flush=True)
        _write_window_panel(events, arrays, config, window_path)
    else:
        print("reusing existing R03e OHLCV window cache", flush=True)

    if len(events) != len(features) or not events["family_signal_event_id"].reset_index(drop=True).equals(
        features["family_signal_event_id"].reset_index(drop=True)
    ):
        raise RuntimeError("feature panel is not aligned 1:1 with event panel")
    filter_panel = pd.concat(
        [events.reset_index(drop=True), features.drop(columns=["family_signal_event_id"]).reset_index(drop=True)],
        axis=1,
    )
    filter_panel["baseline_1_t10_survivor_no_badshape_filter"] = _baseline1_mask(filter_panel)
    filter_path = cache_dir / "r03e_bad_shape_filter_panel.parquet"
    filter_panel.to_parquet(filter_path, index=False)

    component_def = _component_definition_audit()
    component_summary = _component_summary(filter_panel)
    bucket_summary = _bad_score_bucket_summary(filter_panel)
    threshold = _threshold_tradeoff(filter_panel)
    outcome = _filtered_outcome_summary(filter_panel)
    overlap = _component_overlap_audit(filter_panel)
    survival = _survival_and_timing_bias_audit(filter_panel)
    stability = _split_stability_audit(outcome, config)

    report_paths = {
        "component_definition": reports_dir / "r03e_bad_shape_component_definition_audit.csv",
        "component_summary": reports_dir / "r03e_bad_shape_component_summary.csv",
        "bucket_summary": reports_dir / "r03e_bad_score_bucket_summary.csv",
        "threshold": reports_dir / "r03e_bad_score_threshold_tradeoff.csv",
        "outcome": reports_dir / "r03e_filtered_outcome_summary.csv",
        "overlap": reports_dir / "r03e_component_overlap_audit.csv",
        "survival": reports_dir / "r03e_survival_and_timing_bias_audit.csv",
        "stability": reports_dir / "r03e_split_stability_audit.csv",
    }
    for df, path in [
        (component_def, report_paths["component_definition"]),
        (component_summary, report_paths["component_summary"]),
        (bucket_summary, report_paths["bucket_summary"]),
        (threshold, report_paths["threshold"]),
        (outcome, report_paths["outcome"]),
        (overlap, report_paths["overlap"]),
        (survival, report_paths["survival"]),
        (stability, report_paths["stability"]),
    ]:
        write_csv(df, path)

    decision, decision_details = _make_decision(outcome, threshold, config)
    artifact_paths = [
        event_path,
        window_path,
        feature_path,
        filter_path,
        reports_dir / "r03e_input_readiness_audit.csv",
        *report_paths.values(),
    ]
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": relpath(topic_path(config_path)),
        "requirement_path": config["requirement_path"],
        "output_root": relpath(output_root),
        "event_scope_counts": events["event_scope"].value_counts().sort_index().to_dict(),
        "baseline_1_event_count": int(filter_panel["baseline_1_t10_survivor_no_badshape_filter"].sum()),
        "bad_score_complete_rate": float(filter_panel["bad_score_complete_flag"].mean()),
        "final_decision": decision,
        "decision_details": decision_details,
        "artifact_hashes": _artifact_hashes(artifact_paths),
    }
    report_path = reports_dir / "r03e_family_signal_bad_shape_filter_final_report.md"
    _write_final_report(report_path, manifest, readiness, survival, bucket_summary, threshold, outcome, config)
    artifact_paths.append(report_path)
    manifest["artifact_hashes"] = _artifact_hashes(artifact_paths)
    write_json(manifest, manifests_dir / "r03e_family_signal_bad_shape_filter_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    manifest = run(Path(args.config))
    print(json.dumps({"final_decision": manifest.get("final_decision"), "output_root": manifest.get("output_root")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

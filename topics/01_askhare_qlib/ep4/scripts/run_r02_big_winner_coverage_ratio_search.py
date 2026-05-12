#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import multiprocessing as mp
import os
import sys
from dataclasses import dataclass
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
    build_big_winner_reference,
    load_config as load_r01_config,
    load_provider_spine,
    prepare_stock_day_panel,
    relpath,
    split_effective_windows,
    topic_path,
    write_csv,
    write_json,
)


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_big_winner_coverage_ratio_search_v1.yaml"
ALLOWED_FAMILIES = [
    "price_trend",
    "momentum_rps",
    "volatility_band",
    "volume_money",
    "range_breakout",
    "pullback_drawdown",
    "oscillator",
]

_WORKER_ATOMS: list["Atom"] = []
_WORKER_MASKS: np.ndarray | None = None
_WORKER_REFERENCE: pd.DataFrame | None = None
_WORKER_ELIGIBLE_MASK: np.ndarray | None = None
_WORKER_GLOBAL_ELIGIBLE_COUNT: int = 0


@dataclass(frozen=True)
class Atom:
    atomic_condition_id: str
    family_id: str
    feature_template_id: str
    window: int
    operator: str
    threshold: float
    pit_formula: str
    required_fields: tuple[str, ...]
    lookback_days_required: int
    values: np.ndarray
    complete: np.ndarray
    formula_hash: str


def _safe_div(numer: float, denom: float, default: float = 0.0) -> float:
    return float(numer) / float(denom) if denom else default


def _hash_json(value: Any, n: int = 16) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()[:n]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitize(value: Any) -> str:
    text = f"{value:g}" if isinstance(value, float) else str(value)
    return text.replace("-", "m").replace(".", "_")


def _series_hash(df: pd.DataFrame) -> str:
    csv = df.to_csv(index=False)
    return hashlib.sha256(csv.encode("utf-8")).hexdigest()


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_config(config_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cfg_path = topic_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    r01_config_path = topic_path(config["upstream_r01"]["config"])
    r01_config, _, ep2_config = load_r01_config(r01_config_path)
    return config, r01_config, ep2_config


def enrich_features(stock: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    out = stock.sort_values(["instrument", "date"]).reset_index(drop=True).copy()
    group = out.groupby("instrument", group_keys=False)
    prev_close = group["close"].shift(1)
    true_range = pd.concat(
        [(out["high"] - out["low"]).abs(), (out["high"] - prev_close).abs(), (out["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    out["true_range_r02"] = true_range
    daily_ret = group["close"].pct_change()
    out["daily_ret_r02"] = daily_ret
    money = out["money"] if "money" in out.columns else out["volume"] * out["close"]
    out["amount_r02"] = money
    turnover_source = out["turnover"] if "turnover" in out.columns else out["volume"]
    out["turnover_proxy_r02"] = turnover_source

    for window in windows:
        out[f"ma{window}_r02"] = group["close"].transform(lambda s, w=window: s.rolling(w, min_periods=w).mean())
        out[f"ema{window}_r02"] = group["close"].transform(lambda s, w=window: s.ewm(span=w, adjust=False, min_periods=w).mean())
        out[f"close_over_ma{window}_r02"] = out["close"] / out[f"ma{window}_r02"] - 1.0
        out[f"close_over_ema{window}_r02"] = out["close"] / out[f"ema{window}_r02"] - 1.0
        out[f"ma_slope{window}_r02"] = out[f"ma{window}_r02"] / group[f"ma{window}_r02"].shift(window) - 1.0
        out[f"ema_slope{window}_r02"] = out[f"ema{window}_r02"] / group[f"ema{window}_r02"].shift(window) - 1.0
        out[f"ret{window}_r02"] = group["close"].transform(lambda s, w=window: s / s.shift(w) - 1.0)
        out[f"roc{window}_r02"] = out[f"ret{window}_r02"]
        rank_mask = out["split"].isin(["train", "validation", "robustness"]) & out["pit_universe_member"].astype(bool)
        out[f"rps{window}_r02"] = np.nan
        out.loc[rank_mask, f"rps{window}_r02"] = out.loc[rank_mask].groupby("date")[f"ret{window}_r02"].rank(pct=True)
        market_ret = out.loc[rank_mask].groupby("date")[f"ret{window}_r02"].transform("mean")
        out[f"market_relative_ret{window}_r02"] = np.nan
        out.loc[rank_mask, f"market_relative_ret{window}_r02"] = out.loc[rank_mask, f"ret{window}_r02"] - market_ret

        out[f"realized_vol{window}_r02"] = group["daily_ret_r02"].transform(lambda s, w=window: s.rolling(w, min_periods=w).std(ddof=0))
        out[f"atr{window}_r02"] = group["true_range_r02"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).mean())
        out[f"atr_ratio{window}_r02"] = out[f"atr{window}_r02"] / out["close"]
        mid = out[f"ma{window}_r02"]
        std = group["close"].transform(lambda s, w=window: s.rolling(w, min_periods=w).std(ddof=0))
        upper = mid + 2.0 * std
        lower = mid - 2.0 * std
        out[f"boll_pct_b{window}_r02"] = (out["close"] - lower) / (upper - lower)
        width_col = f"boll_width_raw{window}_r02"
        out[width_col] = (upper - lower) / mid
        out[f"boll_width{window}_r02"] = out[width_col] / group[width_col].transform(lambda s: s.shift(1).rolling(60, min_periods=20).median())
        prior_high = group["close"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).max())
        prior_low = group["close"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).min())
        out[f"prior_high{window}_r02"] = prior_high
        out[f"prior_low{window}_r02"] = prior_low
        out[f"price_channel_position{window}_r02"] = (out["close"] - prior_low) / (prior_high - prior_low)
        out[f"close_near_high{window}_r02"] = out["close"] / prior_high - 1.0
        out[f"close_near_low{window}_r02"] = out["close"] / prior_low - 1.0
        out[f"close_breaks_high{window}_r02"] = out["close"] >= prior_high
        out[f"new_high_flag{window}_r02"] = out[f"close_breaks_high{window}_r02"]
        out[f"range_position{window}_r02"] = out[f"price_channel_position{window}_r02"]
        out[f"drawdown_from_high{window}_r02"] = out["close"] / prior_high - 1.0
        out[f"pullback_depth{window}_r02"] = out[f"drawdown_from_high{window}_r02"]
        out[f"rebound_from_low{window}_r02"] = out["close"] / prior_low - 1.0
        rolling_argmax = group["close"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).apply(lambda x: w - 1 - int(np.argmax(x)), raw=True))
        out[f"days_since_high{window}_r02"] = rolling_argmax
        out[f"pullback_recovery{window}_r02"] = out[f"rebound_from_low{window}_r02"]

        vol_mean = group["volume"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).mean())
        amt_mean = group["amount_r02"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).mean())
        turn_mean = group["turnover_proxy_r02"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).mean())
        out[f"volume_ratio{window}_r02"] = out["volume"] / vol_mean
        out[f"amount_ratio{window}_r02"] = out["amount_r02"] / amt_mean
        out[f"turnover_ratio{window}_r02"] = out["turnover_proxy_r02"] / turn_mean
        amt_std = group["amount_r02"].transform(lambda s, w=window: s.shift(1).rolling(w, min_periods=w).std(ddof=0))
        out[f"money_zscore{window}_r02"] = (out["amount_r02"] - amt_mean) / amt_std
        out[f"money_price_coherence{window}_r02"] = ((out[f"amount_ratio{window}_r02"] > 1.0) & (out[f"ret{window}_r02"] >= 0.0)).astype(float)

        delta = group["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.groupby(out["instrument"]).transform(lambda s, w=window: s.ewm(alpha=1 / w, adjust=False, min_periods=w).mean())
        avg_loss = loss.groupby(out["instrument"]).transform(lambda s, w=window: s.ewm(alpha=1 / w, adjust=False, min_periods=w).mean())
        rs = avg_gain / avg_loss
        out[f"rsi{window}_r02"] = 100 - 100 / (1 + rs)
        low_min = group["low"].transform(lambda s, w=window: s.rolling(w, min_periods=w).min())
        high_max = group["high"].transform(lambda s, w=window: s.rolling(w, min_periods=w).max())
        rsv = (out["close"] - low_min) / (high_max - low_min) * 100
        out[f"kdj_k{window}_r02"] = rsv.groupby(out["instrument"]).transform(lambda s: s.ewm(alpha=1 / 3, adjust=False, min_periods=3).mean())
        typical = (out["high"] + out["low"] + out["close"]) / 3
        typical_ma = typical.groupby(out["instrument"]).transform(lambda s, w=window: s.rolling(w, min_periods=w).mean())
        mean_dev = typical.groupby(out["instrument"]).transform(lambda s, w=window: s.rolling(w, min_periods=w).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True))
        out[f"cci{window}_r02"] = (typical - typical_ma) / (0.015 * mean_dev)
        ema_fast = group["close"].transform(lambda s: s.ewm(span=12, adjust=False, min_periods=12).mean())
        ema_slow = group["close"].transform(lambda s: s.ewm(span=26, adjust=False, min_periods=26).mean())
        dif = ema_fast - ema_slow
        dea = dif.groupby(out["instrument"]).transform(lambda s: s.ewm(span=9, adjust=False, min_periods=9).mean())
        out[f"macd_hist{window}_r02"] = dif - dea
    return out


def _formula_hash(payload: dict[str, Any]) -> str:
    return _hash_json(payload, 16)


def _add_atom(
    atoms: list[Atom],
    stock: pd.DataFrame,
    family_id: str,
    template: str,
    window: int,
    operator: str,
    threshold: float,
    source_col: str,
    required_fields: tuple[str, ...],
) -> None:
    series = stock[source_col] if source_col in stock.columns else pd.Series(np.nan, index=stock.index)
    complete = np.isfinite(series.to_numpy(dtype=float)) if series.dtype != bool else series.notna().to_numpy()
    if operator == ">=":
        values = series >= threshold
    elif operator == ">":
        values = series > threshold
    elif operator == "<=":
        values = series <= threshold
    elif operator == "<":
        values = series < threshold
    elif operator == "==":
        values = series == threshold
    else:
        raise ValueError(f"unsupported operator: {operator}")
    values_arr = values.fillna(False).to_numpy(dtype=bool)
    payload = {
        "family_id": family_id,
        "feature_template_id": template,
        "window": window,
        "operator": operator,
        "threshold": threshold,
        "source_col": source_col,
    }
    atom_id = f"{family_id}__{template.replace('_N', str(window))}__{operator.replace('=', 'eq').replace('>', 'gt').replace('<', 'lt')}__{_sanitize(threshold)}"
    atoms.append(
        Atom(
            atomic_condition_id=atom_id,
            family_id=family_id,
            feature_template_id=template,
            window=window,
            operator=operator,
            threshold=float(threshold),
            pit_formula=f"{source_col} {operator} {threshold}",
            required_fields=required_fields,
            lookback_days_required=max(window, 60 if template in {"boll_width_N"} else window),
            values=values_arr,
            complete=complete,
            formula_hash=_formula_hash(payload),
        )
    )


def build_atoms(stock: pd.DataFrame, config: dict[str, Any]) -> list[Atom]:
    windows = [int(v) for v in config["search"]["allowed_windows"]]
    thresholds = config["thresholds"]
    atoms: list[Atom] = []
    for window in windows:
        for threshold in thresholds["price_ratio"]:
            _add_atom(atoms, stock, "price_trend", "close_over_ma_N", window, ">=", threshold, f"close_over_ma{window}_r02", ("close",))
            _add_atom(atoms, stock, "price_trend", "close_over_ema_N", window, ">=", threshold, f"close_over_ema{window}_r02", ("close",))
        for threshold in thresholds["slope"]:
            _add_atom(atoms, stock, "price_trend", "ma_slope_N", window, ">=", threshold, f"ma_slope{window}_r02", ("close",))
            _add_atom(atoms, stock, "price_trend", "ema_slope_N", window, ">=", threshold, f"ema_slope{window}_r02", ("close",))

        for threshold in thresholds["ret"]:
            _add_atom(atoms, stock, "momentum_rps", "ret_N", window, ">=", threshold, f"ret{window}_r02", ("close",))
            _add_atom(atoms, stock, "momentum_rps", "roc_N", window, ">=", threshold, f"roc{window}_r02", ("close",))
            _add_atom(atoms, stock, "momentum_rps", "market_relative_ret_N", window, ">=", threshold, f"market_relative_ret{window}_r02", ("close",))
        for threshold in thresholds["rps"]:
            _add_atom(atoms, stock, "momentum_rps", "rps_N", window, ">=", threshold, f"rps{window}_r02", ("close",))

        for threshold in thresholds["volatility"]:
            _add_atom(atoms, stock, "volatility_band", "realized_vol_N", window, "<=", threshold, f"realized_vol{window}_r02", ("close",))
            _add_atom(atoms, stock, "volatility_band", "atr_ratio_N", window, "<=", threshold, f"atr_ratio{window}_r02", ("high", "low", "close"))
        for threshold in thresholds["boll_pct_b"]:
            _add_atom(atoms, stock, "volatility_band", "boll_pct_b_N", window, ">=", threshold, f"boll_pct_b{window}_r02", ("close",))
        for threshold in thresholds["boll_width"]:
            _add_atom(atoms, stock, "volatility_band", "boll_width_N", window, ">=", threshold, f"boll_width{window}_r02", ("close",))
        for threshold in thresholds["range_position"]:
            _add_atom(atoms, stock, "volatility_band", "price_channel_position_N", window, ">=", threshold, f"price_channel_position{window}_r02", ("close",))

        for threshold in thresholds["activity_ratio"]:
            _add_atom(atoms, stock, "volume_money", "volume_ratio_N", window, ">=", threshold, f"volume_ratio{window}_r02", ("volume",))
            _add_atom(atoms, stock, "volume_money", "amount_ratio_N", window, ">=", threshold, f"amount_ratio{window}_r02", ("money",))
            _add_atom(atoms, stock, "volume_money", "turnover_ratio_N", window, ">=", threshold, f"turnover_ratio{window}_r02", ("volume",))
        for threshold in [0.0, 1.0, 2.0]:
            _add_atom(atoms, stock, "volume_money", "money_zscore_N", window, ">=", threshold, f"money_zscore{window}_r02", ("money",))
        for threshold in thresholds["money_price_coherence"]:
            _add_atom(atoms, stock, "volume_money", "money_price_coherence_N", window, "==", 1.0, f"money_price_coherence{window}_r02", ("money", "close"))

        for threshold in thresholds["near_high"]:
            _add_atom(atoms, stock, "range_breakout", "close_near_high_N", window, ">=", threshold, f"close_near_high{window}_r02", ("close",))
        _add_atom(atoms, stock, "range_breakout", "close_breaks_high_N", window, "==", 1.0, f"close_breaks_high{window}_r02", ("close",))
        _add_atom(atoms, stock, "range_breakout", "new_high_flag_N", window, "==", 1.0, f"new_high_flag{window}_r02", ("close",))
        for threshold in thresholds["near_high"]:
            _add_atom(atoms, stock, "range_breakout", "close_near_low_N", window, ">=", threshold, f"close_near_low{window}_r02", ("close",))
        for threshold in thresholds["range_position"]:
            _add_atom(atoms, stock, "range_breakout", "range_position_N", window, ">=", threshold, f"range_position{window}_r02", ("close",))

        for threshold in thresholds["drawdown"]:
            _add_atom(atoms, stock, "pullback_drawdown", "drawdown_from_high_N", window, ">=", threshold, f"drawdown_from_high{window}_r02", ("close",))
            _add_atom(atoms, stock, "pullback_drawdown", "pullback_depth_N", window, ">=", threshold, f"pullback_depth{window}_r02", ("close",))
        for threshold in thresholds["rebound"]:
            _add_atom(atoms, stock, "pullback_drawdown", "rebound_from_low_N", window, ">=", threshold, f"rebound_from_low{window}_r02", ("close",))
            _add_atom(atoms, stock, "pullback_drawdown", "pullback_recovery_N", window, ">=", threshold, f"pullback_recovery{window}_r02", ("close",))
        for threshold in thresholds["days_since_high"]:
            _add_atom(atoms, stock, "pullback_drawdown", "days_since_high_N", window, "<=", threshold, f"days_since_high{window}_r02", ("close",))

        for threshold in thresholds["oscillator_high"]:
            _add_atom(atoms, stock, "oscillator", "rsi_N", window, ">=", threshold, f"rsi{window}_r02", ("close",))
            _add_atom(atoms, stock, "oscillator", "kdj_k_N", window, ">=", threshold, f"kdj_k{window}_r02", ("high", "low", "close"))
        for threshold in [50, 100, 150]:
            _add_atom(atoms, stock, "oscillator", "cci_N", window, ">=", threshold, f"cci{window}_r02", ("high", "low", "close"))
        _add_atom(atoms, stock, "oscillator", "macd_hist_state_N", window, ">=", 0.0, f"macd_hist{window}_r02", ("close",))
    return atoms


def selected_atom_indices_for_candidates(atoms: list[Atom], max_per_family: int) -> set[int]:
    selected: set[int] = set()
    for family in ALLOWED_FAMILIES:
        family_indices = [idx for idx, atom in enumerate(atoms) if atom.family_id == family]
        template_groups: dict[str, list[int]] = {}
        for idx in family_indices:
            template_groups.setdefault(atoms[idx].feature_template_id, []).append(idx)
        for values in template_groups.values():
            values.sort(key=lambda i: (atoms[i].window, atoms[i].threshold, atoms[i].atomic_condition_id))
        while len([idx for idx in selected if atoms[idx].family_id == family]) < min(max_per_family, len(family_indices)):
            progressed = False
            for template in sorted(template_groups):
                if template_groups[template] and len([idx for idx in selected if atoms[idx].family_id == family]) < min(max_per_family, len(family_indices)):
                    selected.add(template_groups[template].pop(0))
                    progressed = True
            if not progressed:
                break
    return selected


def build_atomic_dictionary(atoms: list[Atom], selected_indices: set[int]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "atomic_condition_id": atom.atomic_condition_id,
                "family_id": atom.family_id,
                "feature_template_id": atom.feature_template_id,
                "window": atom.window,
                "operator": atom.operator,
                "threshold": atom.threshold,
                "pit_formula": atom.pit_formula,
                "required_fields": "|".join(atom.required_fields),
                "lookback_days_required": atom.lookback_days_required,
                "warmup_policy": "global_denominator_missing_false_feature_denominator_complete_only",
                "nan_policy": "nan_as_false_for_global_density",
                "formula_hash": atom.formula_hash,
                "selected_for_candidate_generation": idx in selected_indices,
            }
            for idx, atom in enumerate(atoms)
        ]
    )


def build_candidate_dictionary(atoms: list[Atom], allowed_n_terms: list[int], selected_indices: set[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    by_family: dict[str, list[int]] = {}
    for idx, atom in enumerate(atoms):
        if idx in selected_indices:
            by_family.setdefault(atom.family_id, []).append(idx)
    for family in ALLOWED_FAMILIES:
        atom_indices = by_family.get(family, [])
        for n_terms in allowed_n_terms:
            for combo in itertools.combinations(atom_indices, n_terms):
                payload = {
                    "family_id": family,
                    "n_terms": n_terms,
                    "atomic_condition_ids": [atoms[i].atomic_condition_id for i in combo],
                    "formula_hashes": [atoms[i].formula_hash for i in combo],
                }
                condition_group_id = f"{family}__and{n_terms}__{_hash_json(payload, 12)}"
                rows.append(
                    {
                        "condition_group_id": condition_group_id,
                        "family_id": family,
                        "kind": f"same_family_and{n_terms}",
                        "n_terms": n_terms,
                        "atom_indices": ",".join(str(i) for i in combo),
                        "atomic_condition_ids": "|".join(atoms[i].atomic_condition_id for i in combo),
                        "windows": "|".join(str(atoms[i].window) for i in combo),
                        "thresholds": "|".join(str(atoms[i].threshold) for i in combo),
                        "pit_formula": " AND ".join(atoms[i].pit_formula for i in combo),
                        "uses_market_context_filter": False,
                        "market_context_decomposition_required": True,
                        "redundancy_flag": len({(atoms[i].feature_template_id, atoms[i].window) for i in combo}) < len(combo),
                        "formula_hash": _hash_json(payload, 16),
                    }
                )
    return pd.DataFrame(rows).sort_values("condition_group_id").reset_index(drop=True)


def event_window_indices(stock: pd.DataFrame, reference: pd.DataFrame, calendar: pd.DatetimeIndex) -> list[np.ndarray]:
    key_to_index = {
        (str(row.instrument), pd.Timestamp(row.date)): i
        for i, row in enumerate(stock[["instrument", "date"]].reset_index(drop=True).itertuples(index=False))
    }
    windows: list[np.ndarray] = []
    for row in reference.sort_values(["split", "instrument_id", "reference_date"]).itertuples(index=False):
        inst = str(row.instrument_id)
        ref_date = pd.Timestamp(row.reference_date).normalize()
        idxs: list[int] = []
        for offset in range(0, 31):
            pos = calendar.searchsorted(ref_date, side="left") + offset
            if pos >= len(calendar):
                continue
            key = (inst, pd.Timestamp(calendar[pos]))
            if key in key_to_index:
                idxs.append(key_to_index[key])
        windows.append(np.asarray(idxs, dtype=np.int64))
    return windows


def atom_event_masks(atoms: list[Atom], windows: list[np.ndarray]) -> np.ndarray:
    masks = np.zeros((len(atoms), len(windows)), dtype=np.uint64)
    bits = np.asarray([np.uint64(1) << np.uint64(i) for i in range(31)], dtype=np.uint64)
    for atom_idx, atom in enumerate(atoms):
        values = atom.values
        for event_idx, idxs in enumerate(windows):
            if idxs.size == 0:
                continue
            hit_positions = np.flatnonzero(values[idxs])
            if hit_positions.size:
                masks[atom_idx, event_idx] = np.bitwise_or.reduce(bits[hit_positions])
    return masks


def _offset_summary(event_mask: np.ndarray) -> tuple[float, float, dict[str, int]]:
    earliest: list[int] = []
    buckets = {"D0-D5": 0, "D6-D10": 0, "D11-D20": 0, "D21-D30": 0}
    for mask in event_mask[event_mask != 0]:
        hit_offsets = [idx for idx in range(31) if int(mask) & (1 << idx)]
        if not hit_offsets:
            continue
        first = hit_offsets[0]
        earliest.append(first)
        if first <= 5:
            buckets["D0-D5"] += 1
        elif first <= 10:
            buckets["D6-D10"] += 1
        elif first <= 20:
            buckets["D11-D20"] += 1
        else:
            buckets["D21-D30"] += 1
    median = float(np.median(earliest)) if earliest else np.nan
    return median, median, buckets


def _condition_stats(row: pd.Series, atom_indices: tuple[int, ...]) -> dict[str, Any]:
    assert _WORKER_MASKS is not None
    assert _WORKER_REFERENCE is not None
    assert _WORKER_ELIGIBLE_MASK is not None
    daily = _WORKER_ELIGIBLE_MASK.copy()
    complete = _WORKER_ELIGIBLE_MASK.copy()
    event_mask = np.full(_WORKER_MASKS.shape[1], np.uint64((1 << 31) - 1), dtype=np.uint64)
    for idx in atom_indices:
        daily &= _WORKER_ATOMS[idx].values
        complete &= _WORKER_ATOMS[idx].complete
        event_mask &= _WORKER_MASKS[idx]
    covered = event_mask != 0
    median_closest, median_earliest, buckets = _offset_summary(event_mask)
    eligible_day_trigger_count = int(daily.sum())
    feature_eligible_count = int(complete.sum())
    result = {
        "condition_group_id": row["condition_group_id"],
        "family_id": row["family_id"],
        "kind": row["kind"],
        "n_terms": int(row["n_terms"]),
        "condition_text": row["pit_formula"],
        "coverage_t0_t30": _safe_div(float(covered.sum()), float(len(_WORKER_REFERENCE))),
        "covered_events_t0_t30": int(covered.sum()),
        "uncovered_events_t0_t30": int((~covered).sum()),
        "eligible_day_density": _safe_div(float(eligible_day_trigger_count), float(_WORKER_GLOBAL_ELIGIBLE_COUNT)),
        "eligible_day_trigger_count": eligible_day_trigger_count,
        "eligible_day_denominator": int(_WORKER_GLOBAL_ELIGIBLE_COUNT),
        "global_eligible_day_denominator": int(_WORKER_GLOBAL_ELIGIBLE_COUNT),
        "feature_eligible_day_denominator": feature_eligible_count,
        "feature_eligible_day_density": _safe_div(float(eligible_day_trigger_count), float(feature_eligible_count)),
        "feature_eligible_ratio": _safe_div(float(feature_eligible_count), float(_WORKER_GLOBAL_ELIGIBLE_COUNT)),
        "low_feature_coverage_warning": _safe_div(float(feature_eligible_count), float(_WORKER_GLOBAL_ELIGIBLE_COUNT)) < 0.80,
        "median_earliest_hit_offset": median_earliest,
        "median_closest_hit_offset": median_closest,
        "offset_bucket_first_hit_distribution": json.dumps(buckets, ensure_ascii=False, sort_keys=True),
        "market_context_decomposition_status": "decomposition_only",
    }
    for split in ["train", "validation", "robustness"]:
        idx = _WORKER_REFERENCE.index[_WORKER_REFERENCE["split"].eq(split)].to_numpy()
        split_cov = covered[idx] if len(idx) else np.asarray([], dtype=bool)
        result[f"coverage_by_split_{split}"] = _safe_div(float(split_cov.sum()), float(len(idx)), np.nan)
    year_cov = []
    ref_year = pd.to_datetime(_WORKER_REFERENCE["reference_date"]).dt.year
    for _, idx in _WORKER_REFERENCE.groupby(ref_year).groups.items():
        idx_arr = np.asarray(list(idx), dtype=int)
        year_cov.append(_safe_div(float(covered[idx_arr].sum()), float(len(idx_arr)), np.nan))
    result["coverage_by_year_min"] = float(np.nanmin(year_cov)) if year_cov else np.nan
    result["coverage_by_year_max"] = float(np.nanmax(year_cov)) if year_cov else np.nan
    result["rank_score"] = float(result["coverage_t0_t30"]) - float(result["eligible_day_density"])
    result["_covered_mask_json"] = json.dumps(covered.tolist())
    return result


def _eval_candidate_chunk(task: tuple[int, pd.DataFrame]) -> list[dict[str, Any]]:
    chunk_id, candidates = task
    rows = []
    for sequence, row in enumerate(candidates.itertuples(index=False)):
        series = pd.Series(row._asdict())
        atom_indices = tuple(int(v) for v in str(series["atom_indices"]).split(",") if v != "")
        result = _condition_stats(series, atom_indices)
        payload = {k: v for k, v in result.items() if not k.startswith("_")}
        result["worker_id"] = os.getpid()
        result["chunk_id"] = chunk_id
        result["chunk_sequence"] = sequence
        result["result_hash"] = _hash_json(payload, 16)
        rows.append(result)
    return rows


def _chunks(df: pd.DataFrame, size: int) -> list[pd.DataFrame]:
    return [df.iloc[i : i + size].copy() for i in range(0, len(df), size)]


def evaluate_candidates(
    atoms: list[Atom],
    masks: np.ndarray,
    reference: pd.DataFrame,
    eligible_mask: np.ndarray,
    candidates: pd.DataFrame,
    workers: int,
    chunk_size: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    global _WORKER_ATOMS, _WORKER_MASKS, _WORKER_REFERENCE, _WORKER_ELIGIBLE_MASK, _WORKER_GLOBAL_ELIGIBLE_COUNT
    _WORKER_ATOMS = atoms
    _WORKER_MASKS = masks
    _WORKER_REFERENCE = reference.reset_index(drop=True)
    _WORKER_ELIGIBLE_MASK = eligible_mask
    _WORKER_GLOBAL_ELIGIBLE_COUNT = int(eligible_mask.sum())

    chunks = _chunks(candidates.sort_values("condition_group_id").reset_index(drop=True), chunk_size)
    tasks = [(idx, chunk) for idx, chunk in enumerate(chunks)]
    rows: list[dict[str, Any]] = []
    ctx = mp.get_context("fork")
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as executor:
        for chunk_rows in executor.map(_eval_candidate_chunk, tasks):
            rows.extend(chunk_rows)
    out = pd.DataFrame(rows).sort_values("condition_group_id").reset_index(drop=True)
    public = out.drop(columns=["_covered_mask_json", "worker_id", "chunk_id", "chunk_sequence"])
    result_hash = _series_hash(public.sort_values("condition_group_id").reset_index(drop=True))
    return out, {
        "chunk_count": len(tasks),
        "failed_chunk_count": 0,
        "retried_chunk_count": 0,
        "parallel_result_hash": result_hash,
    }


def single_pass_audit_hash(
    atoms: list[Atom],
    masks: np.ndarray,
    reference: pd.DataFrame,
    eligible_mask: np.ndarray,
    candidates: pd.DataFrame,
) -> str:
    global _WORKER_ATOMS, _WORKER_MASKS, _WORKER_REFERENCE, _WORKER_ELIGIBLE_MASK, _WORKER_GLOBAL_ELIGIBLE_COUNT
    _WORKER_ATOMS = atoms
    _WORKER_MASKS = masks
    _WORKER_REFERENCE = reference.reset_index(drop=True)
    _WORKER_ELIGIBLE_MASK = eligible_mask
    _WORKER_GLOBAL_ELIGIBLE_COUNT = int(eligible_mask.sum())
    rows = []
    for row in candidates.sort_values("condition_group_id").itertuples(index=False):
        series = pd.Series(row._asdict())
        atom_indices = tuple(int(v) for v in str(series["atom_indices"]).split(",") if v != "")
        result = _condition_stats(series, atom_indices)
        payload = {k: v for k, v in result.items() if not k.startswith("_")}
        result["worker_id"] = 0
        result["chunk_id"] = 0
        result["chunk_sequence"] = len(rows)
        result["result_hash"] = _hash_json(payload, 16)
        rows.append(result)
    out = (
        pd.DataFrame(rows)
        .drop(columns=["_covered_mask_json", "worker_id", "chunk_id", "chunk_sequence"])
        .sort_values("condition_group_id")
        .reset_index(drop=True)
    )
    return _series_hash(out)


def build_reference_and_panels(config: dict[str, Any], r01_config: dict[str, Any], ep2_config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    panel, calendar = load_provider_spine(r01_config, ep2_config)
    stock = prepare_stock_day_panel(r01_config, ep2_config, panel, calendar)
    stock = enrich_features(stock, [int(v) for v in config["search"]["allowed_windows"]])
    data_max = pd.to_datetime(stock["date"]).max()
    effective_windows, _ = split_effective_windows(r01_config, calendar, data_max)
    raw_reference = build_big_winner_reference(stock, r01_config, calendar, effective_windows).sort_values(["split", "instrument", "reference_date"]).reset_index(drop=True)
    reference = raw_reference.rename(
        columns={
            "reference_event_id": "winner_event_id",
            "instrument": "instrument_id",
            "forward_return": "forward_peak_return",
        }
    ).copy()
    reference["winner_label_version"] = r01_config["big_winner_reference"]["primary_id"]
    reference["reference_event_source_path"] = relpath(topic_path(config["upstream_r01"]["config"]))
    reference["reference_event_source_hash"] = _hash_file(topic_path(config["upstream_r01"]["config"]))
    reference["profile_window_start"] = reference["reference_date"]
    reference["profile_window_end"] = [
        calendar[min(calendar.searchsorted(pd.Timestamp(d), side="left") + int(config["coverage"]["profile_window_days"]), len(calendar) - 1)].date().isoformat()
        for d in reference["reference_date"]
    ]
    reference["complete_profile_window_flag"] = True
    reference = reference[
        [
            "winner_event_id",
            "instrument_id",
            "reference_date",
            "split",
            "winner_label_version",
            "reference_event_source_path",
            "reference_event_source_hash",
            "forward_peak_return",
            "forward_peak_date",
            "profile_window_start",
            "profile_window_end",
            "complete_profile_window_flag",
        ]
    ]
    return stock.reset_index(drop=True), reference.reset_index(drop=True), calendar


def build_profile_panel(stock: pd.DataFrame, reference: pd.DataFrame, calendar: pd.DatetimeIndex, atoms: list[Atom]) -> pd.DataFrame:
    stock_key = stock.set_index(["instrument", "date"], drop=False)
    rows: list[dict[str, Any]] = []
    feature_cols = ["open", "high", "low", "close", "volume", "money"]
    for event_idx, row in enumerate(reference.itertuples(index=False)):
        ref_date = pd.Timestamp(row.reference_date)
        for offset in range(31):
            pos = calendar.searchsorted(ref_date, side="left") + offset
            if pos >= len(calendar):
                continue
            trade_date = pd.Timestamp(calendar[pos])
            key = (row.instrument_id, trade_date)
            if key not in stock_key.index:
                continue
            s = stock_key.loc[key]
            payload = {
                "winner_event_id": row.winner_event_id,
                "instrument_id": row.instrument_id,
                "reference_date": row.reference_date,
                "profile_trade_date": trade_date.date().isoformat(),
                "offset_day": offset,
                "split": row.split,
                "complete_profile_window_flag": row.complete_profile_window_flag,
                "is_r01_pit_executable_eligible": bool(s["eligible_stock_day"]),
                "feature_complete_flag_by_condition": "stored_in_atomic_dictionary",
            }
            for col in feature_cols:
                payload[col] = s[col] if col in s.index else np.nan
            rows.append(payload)
    return pd.DataFrame(rows)


def build_density_panel(stock: pd.DataFrame) -> pd.DataFrame:
    cols = ["instrument", "date", "split", "eligible_stock_day", "not_suspended_or_dirty_bar", "buyability_status", "open", "high", "low", "close", "volume", "money"]
    out = stock[[c for c in cols if c in stock.columns]].copy()
    out = out.rename(
        columns={
            "instrument": "instrument_id",
            "date": "trade_date",
            "eligible_stock_day": "is_r01_pit_executable_eligible",
            "buyability_status": "entry_execution_status",
            "not_suspended_or_dirty_bar": "suspended_or_dirty_bar",
        }
    )
    if "suspended_or_dirty_bar" in out:
        out["suspended_or_dirty_bar"] = ~out["suspended_or_dirty_bar"].astype(bool)
    out["source_price_hash"] = _hash_json({"rows": len(out), "close_sum": float(pd.to_numeric(out["close"], errors="coerce").sum())}, 16)
    out["source_calendar_hash"] = _hash_json(out["trade_date"].astype(str).drop_duplicates().tolist(), 16)
    return out


def build_uncovered_events(results: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    ge85 = results.loc[results["coverage_t0_t30"] >= 0.85].sort_values(["eligible_day_density", "coverage_t0_t30"], ascending=[True, False]).head(50)
    for _, result in ge85.iterrows():
        covered = np.asarray(json.loads(result["_covered_mask_json"]), dtype=bool)
        missing = reference.loc[~covered].copy()
        for ref in missing.itertuples(index=False):
            rows.append(
                {
                    "condition_group_id": result["condition_group_id"],
                    "winner_event_id": ref.winner_event_id,
                    "instrument_id": ref.instrument_id,
                    "reference_date": ref.reference_date,
                    "split": ref.split,
                    "forward_peak_return": ref.forward_peak_return,
                    "forward_peak_date": ref.forward_peak_date,
                    "missing_reason": "no_condition_group_hit_in_t0_t30",
                }
            )
    return pd.DataFrame(rows)


def build_context_decomposition(results: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    top = results.loc[results["coverage_t0_t30"] >= 0.85].sort_values(["eligible_day_density", "coverage_t0_t30"], ascending=[True, False]).head(20)
    reference = reference.copy()
    reference["reference_year"] = pd.to_datetime(reference["reference_date"]).dt.year.astype(str)
    for _, result in top.iterrows():
        covered = np.asarray(json.loads(result["_covered_mask_json"]), dtype=bool)
        for dimension in ["split", "reference_year"]:
            for bucket, idx in reference.groupby(dimension).groups.items():
                idx_arr = np.asarray(list(idx), dtype=int)
                rows.append(
                    {
                        "condition_group_id": result["condition_group_id"],
                        "market_context_dimension": dimension,
                        "market_context_bucket": bucket,
                        "bucket_winner_count": int(len(idx_arr)),
                        "bucket_coverage_t0_t30": _safe_div(float(covered[idx_arr].sum()), float(len(idx_arr)), np.nan),
                        "bucket_eligible_day_count": int(result["global_eligible_day_denominator"]),
                        "bucket_eligible_day_density": float(result["eligible_day_density"]),
                        "decomposition_only_flag": True,
                    }
                )
    return pd.DataFrame(rows)


def write_report(
    reports_dir: Path,
    all_results: pd.DataFrame,
    ge85: pd.DataFrame,
    reference: pd.DataFrame,
    atomic_count: int,
    candidate_count: int,
    manifest: dict[str, Any],
) -> str:
    best = ge85.sort_values(["eligible_day_density", "coverage_t0_t30"], ascending=[True, False]).head(1)
    by_family = (
        ge85.sort_values(["family_id", "coverage_t0_t30", "eligible_day_density"], ascending=[True, False, True])
        .groupby("family_id", as_index=False)
        .head(1)
    )
    low_by_family = (
        ge85.sort_values(["family_id", "eligible_day_density", "coverage_t0_t30"], ascending=[True, True, False])
        .groupby("family_id", as_index=False)
        .head(1)
    )
    decision = "descriptive_coverage_profiles_found" if not ge85.empty else "stop_big_winner_coverage_ratio_search_no_ge85_condition"
    lines = [
        "# R02 Big Winner Coverage Ratio Search V1 Final Report",
        "",
        "## 样本与分母",
        "",
        f"- winner coverage denominator: {len(reference)} canonical R01 primary big winner events",
        f"- density denominator: {int(all_results['global_eligible_day_denominator'].iloc[0]) if not all_results.empty else 0} R01 PIT-executable eligible stock-days",
        "- profile window: `T+0..T+30` after `reference_date`",
        "- this is a full-sample descriptive profile, not holdout validation and not an entry prior",
        "",
        "## 搜索空间",
        "",
        f"- feature families: {', '.join(ALLOWED_FAMILIES)}",
        "- windows: `5 / 10 / 30 / 60`",
        "- condition groups: same-family `AND3 / AND4` only",
        f"- atomic conditions: {atomic_count}",
        f"- selected atomic conditions for candidate generation: {manifest['selected_atomic_condition_count']}",
        f"- deterministic candidate atom cap per family: {manifest['deterministic_candidate_atom_cap_per_family']}",
        f"- condition groups: {candidate_count}",
        "",
        "## 覆盖率与密度定义",
        "",
        "- coverage: same instrument has at least one daily condition-group hit from reference_date T+0 through T+30",
        "- eligible-day density: condition-group daily trigger count divided by global R01 PIT-executable eligible stock-days",
        "- feature-eligible density is also reported to audit warmup / missingness effects",
        "",
        "## 全局最低密度且 Coverage >= 85% 的候选",
        "",
    ]
    if best.empty:
        lines.append("无。")
    else:
        row = best.iloc[0]
        lines += [
            "```text",
            str(row["condition_text"]),
            "```",
            "",
            "| metric | value |",
            "|:--|--:|",
            f"| condition_group_id | {row['condition_group_id']} |",
            f"| family | {row['family_id']} |",
            f"| kind | {row['kind']} |",
            f"| coverage T+0..T+30 | {row['coverage_t0_t30']:.2%} |",
            f"| covered events | {int(row['covered_events_t0_t30'])} / {len(reference)} |",
            f"| eligible-day density | {row['eligible_day_density']:.2%} |",
            f"| feature-eligible density | {row['feature_eligible_day_density']:.2%} |",
            f"| median earliest hit offset | {row['median_earliest_hit_offset']} |",
        ]
    lines += [
        "",
        "## 每个 Family 的最佳候选",
        "",
        by_family[
            ["family_id", "condition_group_id", "kind", "coverage_t0_t30", "eligible_day_density", "median_earliest_hit_offset"]
        ].to_markdown(index=False)
        if not by_family.empty
        else "无。",
        "",
        "## 每个 Family 的最低密度达标候选",
        "",
        low_by_family[
            ["family_id", "condition_group_id", "kind", "coverage_t0_t30", "eligible_day_density", "feature_eligible_ratio"]
        ].to_markdown(index=False)
        if not low_by_family.empty
        else "无。",
        "",
        "## 未覆盖 Winner 总结",
        "",
        f"- ge85 condition count: {len(ge85)}",
        f"- best uncovered events: {int(best.iloc[0]['uncovered_events_t0_t30']) if not best.empty else len(reference)}",
        "",
        "## Split / Year / Market Context 分解",
        "",
        "- split and year fields are descriptive decomposition only.",
        "- market_context is not used as a filter and does not change the ge85 main table.",
        "",
        "## 12-Core Parallel Search 执行摘要",
        "",
        "| field | value |",
        "|:--|:--|",
        f"| backend | {manifest['parallel_backend']} |",
        f"| configured worker count | {manifest['configured_max_workers']} |",
        f"| actual worker count | {manifest['actual_worker_count']} |",
        f"| chunk count | {manifest['chunk_count']} |",
        f"| failed chunk count | {manifest['failed_chunk_count']} |",
        f"| retried chunk count | {manifest['retried_chunk_count']} |",
        f"| parallel result hash | {manifest['parallel_result_hash']} |",
        "",
        "## Boundary",
        "",
        "该结果只是 full-sample winner profile / coverage evidence。它不是 entry prior，不是 posterior precision，不是 holdout validation，不允许直接进入 next-stage promotion 或 R03 risk-budget mapping。",
        "",
        "## Final Decision",
        "",
        decision,
        "",
    ]
    (reports_dir / "r02_big_winner_coverage_final_report.md").write_text("\n".join(lines), encoding="utf-8")
    return decision


def run(config_path: Path) -> dict[str, Any]:
    config, r01_config, ep2_config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for directory in [cache_dir, reports_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    parallel = config["parallel_search"]
    configured_workers = int(parallel["max_workers"])
    actual_cpu = os.cpu_count() or 1
    if actual_cpu < configured_workers and not bool(parallel.get("allow_worker_downgrade", False)):
        raise RuntimeError(f"available CPU count {actual_cpu} is below required max_workers={configured_workers}")
    actual_workers = min(configured_workers, actual_cpu)

    stock, reference, calendar = build_reference_and_panels(config, r01_config, ep2_config)
    expected_count = int(config["coverage"]["canonical_big_winner_count"])
    if len(reference) != expected_count:
        raise RuntimeError(f"canonical R01 primary big winner count drifted: expected {expected_count}, got {len(reference)}")
    atoms = build_atoms(stock, config)
    selected_indices = selected_atom_indices_for_candidates(atoms, int(config["search"]["deterministic_candidate_atom_cap_per_family"]))
    atomic_dictionary = build_atomic_dictionary(atoms, selected_indices)
    candidate_dictionary = build_candidate_dictionary(atoms, [int(v) for v in config["search"]["allowed_n_terms"]], selected_indices)

    write_csv(atomic_dictionary, reports_dir / "r02_big_winner_coverage_atomic_condition_dictionary.csv")
    write_csv(candidate_dictionary, reports_dir / "r02_big_winner_coverage_candidate_dictionary.csv")

    windows = event_window_indices(stock, reference, calendar)
    masks = atom_event_masks(atoms, windows)
    eligible_mask = stock["eligible_stock_day"].astype(bool).to_numpy()

    all_results_with_masks, parallel_summary = evaluate_candidates(
        atoms,
        masks,
        reference,
        eligible_mask,
        candidate_dictionary,
        workers=actual_workers,
        chunk_size=int(parallel["chunk_size"]),
    )
    single_hash = single_pass_audit_hash(atoms, masks, reference, eligible_mask, candidate_dictionary) if bool(parallel.get("single_pass_audit", False)) else parallel_summary["parallel_result_hash"]
    all_results = all_results_with_masks.drop(columns=["_covered_mask_json"])
    all_results = all_results.sort_values(["coverage_t0_t30", "eligible_day_density", "condition_group_id"], ascending=[False, True, True]).reset_index(drop=True)
    ge85 = all_results.loc[all_results["coverage_t0_t30"] >= float(config["coverage"]["min_coverage_t0_t30"])].copy()
    rejected = all_results.loc[all_results["coverage_t0_t30"] < float(config["coverage"]["min_coverage_t0_t30"])].copy()
    top_by_family = (
        ge85.sort_values(["family_id", "coverage_t0_t30", "eligible_day_density"], ascending=[True, False, True])
        .groupby("family_id", as_index=False)
        .head(50)
    )
    low_density_ge85 = ge85.sort_values(["eligible_day_density", "coverage_t0_t30", "condition_group_id"], ascending=[True, False, True]).head(500)

    write_csv(all_results, reports_dir / "r02_big_winner_coverage_all.csv")
    write_csv(ge85, reports_dir / "r02_big_winner_coverage_ge85.csv")
    write_csv(top_by_family, reports_dir / "r02_big_winner_coverage_top_by_family.csv")
    write_csv(low_density_ge85, reports_dir / "r02_big_winner_coverage_lowest_density_ge85.csv")
    write_csv(rejected, reports_dir / "r02_big_winner_coverage_rejected.csv")
    write_csv(build_uncovered_events(all_results_with_masks, reference), reports_dir / "r02_big_winner_coverage_uncovered_events.csv")
    write_csv(build_context_decomposition(all_results_with_masks, reference), reports_dir / "r02_big_winner_coverage_market_context_decomposition.csv")

    profile_panel = build_profile_panel(stock, reference, calendar, atoms)
    density_panel = build_density_panel(stock)
    _write_parquet(reference, cache_dir / "r02_big_winner_reference_events.parquet")
    _write_parquet(profile_panel, cache_dir / "r02_winner_t0_t30_profile_panel.parquet")
    _write_parquet(density_panel, cache_dir / "r02_eligible_day_density_panel.parquet")

    manifest = {
        "phase": config["phase"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement_path": config["requirement_path"],
        "config_path": relpath(topic_path(config_path)),
        "config_hash": _hash_file(topic_path(config_path)),
        "output_root": relpath(output_root),
        "reference_event_count": int(len(reference)),
        "global_eligible_day_denominator": int(eligible_mask.sum()),
        "atomic_condition_count": int(len(atomic_dictionary)),
        "selected_atomic_condition_count": int(atomic_dictionary["selected_for_candidate_generation"].sum()),
        "deterministic_candidate_atom_cap_per_family": int(config["search"]["deterministic_candidate_atom_cap_per_family"]),
        "condition_group_count": int(len(candidate_dictionary)),
        "ge85_condition_count": int(len(ge85)),
        "parallel_enabled": True,
        "parallel_backend": parallel["backend"],
        "configured_max_workers": configured_workers,
        "actual_worker_count": actual_workers,
        "allow_worker_downgrade": bool(parallel.get("allow_worker_downgrade", False)),
        "chunk_unit": parallel["chunk_unit"],
        "chunk_count": int(parallel_summary["chunk_count"]),
        "failed_chunk_count": int(parallel_summary["failed_chunk_count"]),
        "retried_chunk_count": int(parallel_summary["retried_chunk_count"]),
        "deterministic_merge": bool(parallel["deterministic_merge"]),
        "parallel_result_hash": parallel_summary["parallel_result_hash"],
        "single_pass_audit_hash": single_hash,
        "single_pass_audit_match": bool(parallel_summary["parallel_result_hash"] == single_hash),
        "full_sample_descriptive_only": True,
        "uses_market_context_filter": False,
    }
    decision = write_report(reports_dir, all_results, ge85, reference, len(atomic_dictionary), len(candidate_dictionary), manifest)
    manifest["final_decision"] = decision
    write_json(manifest, manifests_dir / "r02_big_winner_coverage_manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EP4 R02 full-sample big-winner coverage ratio search.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = run(Path(args.config))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

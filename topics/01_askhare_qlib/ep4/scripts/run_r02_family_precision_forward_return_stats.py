#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
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


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_family_precision_forward_return_stats_v1.yaml"
SPLITS = ["train", "validation", "robustness"]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_json(value: Any, n: int = 16) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()[:n]


def _safe_div(numer: float, denom: float, default: float = 0.0) -> float:
    return float(numer) / float(denom) if denom else default


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_config(config_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cfg_path = topic_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    r01_config, _, ep2_config = load_r01_config(topic_path(config["upstream_r01"]["config"]))
    return config, r01_config, ep2_config


def validate_frozen_conditions(config: dict[str, Any]) -> pd.DataFrame:
    frozen = pd.DataFrame(config["frozen_conditions"])
    expected_ids = set(frozen["condition_group_id"].astype(str))
    if len(expected_ids) != 7:
        raise RuntimeError(f"expected exactly 7 frozen condition groups, got {len(expected_ids)}")

    all_results_path = topic_path(config["upstream_r02_coverage"]["all_results"])
    all_results = pd.read_csv(all_results_path)
    indexed = all_results.set_index("condition_group_id")
    missing = sorted(expected_ids - set(indexed.index))
    if missing:
        raise RuntimeError(f"frozen condition groups missing from upstream R02 results: {missing}")

    rows: list[dict[str, Any]] = []
    for item in config["frozen_conditions"]:
        condition_group_id = item["condition_group_id"]
        upstream_text = str(indexed.loc[condition_group_id, "condition_text"])
        if upstream_text != item["condition_text"]:
            raise RuntimeError(f"condition_text drift for {condition_group_id}: {upstream_text} != {item['condition_text']}")
        rows.append(
            {
                "condition_group_id": condition_group_id,
                "family_id": item["family_id"],
                "condition_text": item["condition_text"],
                "coverage_t0_t30": float(indexed.loc[condition_group_id, "coverage_t0_t30"]),
                "eligible_day_density": float(indexed.loc[condition_group_id, "eligible_day_density"]),
                "coverage_by_split_train": float(indexed.loc[condition_group_id, "coverage_by_split_train"]),
                "coverage_by_split_validation": float(indexed.loc[condition_group_id, "coverage_by_split_validation"]),
                "coverage_by_split_robustness": float(indexed.loc[condition_group_id, "coverage_by_split_robustness"]),
            }
        )
    return pd.DataFrame(rows).sort_values("condition_group_id").reset_index(drop=True)


def load_stock(config: dict[str, Any], r01_config: dict[str, Any], ep2_config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    panel, calendar = load_provider_spine(r01_config, ep2_config)
    stock = prepare_stock_day_panel(r01_config, ep2_config, panel, calendar)
    stock = enrich_features(stock, [int(v) for v in config["allowed_windows"]])
    stock = stock.sort_values(["instrument", "date"]).reset_index(drop=True)
    return stock, calendar


def add_forward_fields(stock: pd.DataFrame, horizons: list[int], label_horizon: int) -> pd.DataFrame:
    out = stock.sort_values(["instrument", "date"]).reset_index(drop=True).copy()
    for horizon in horizons:
        out[f"close_t{horizon}"] = np.nan
        out[f"date_t{horizon}"] = pd.NaT
        out[f"split_t{horizon}"] = pd.NA
        out[f"complete_h{horizon}_flag"] = False
        out[f"return_close_t{horizon}"] = np.nan
        out[f"path_max_return_to_{horizon}"] = np.nan
        out[f"path_min_return_to_{horizon}"] = np.nan
    out["next_open_t1"] = np.nan
    out["complete_h120_flag"] = False
    out["forward_close_peak_h120_return_from_close"] = np.nan
    out["big_winner_forward_from_signal_close"] = False
    out["forward_close_peak_h120_return_from_next_open"] = np.nan
    out["big_winner_forward_from_next_open"] = False
    out["incomplete_forward_reason"] = ""

    for _, idx in out.groupby("instrument", sort=False).groups.items():
        idx_arr = np.asarray(list(idx), dtype=int)
        close = out.loc[idx_arr, "close"].to_numpy(dtype=float)
        open_ = out.loc[idx_arr, "open"].to_numpy(dtype=float)
        split = out.loc[idx_arr, "split"].astype(str).to_numpy()
        dates = pd.to_datetime(out.loc[idx_arr, "date"]).to_numpy()
        n = len(idx_arr)
        finite_close = np.isfinite(close)
        out.loc[idx_arr, "next_open_t1"] = np.r_[open_[1:], np.nan]
        for horizon in horizons:
            if n <= horizon:
                continue
            dest = idx_arr[:-horizon]
            future_close = close[horizon:]
            same_split = split[:-horizon] == split[horizon:]
            complete = finite_close[:-horizon] & np.isfinite(future_close) & same_split
            out.loc[dest, f"close_t{horizon}"] = future_close
            out.loc[dest, f"date_t{horizon}"] = dates[horizon:]
            out.loc[dest, f"split_t{horizon}"] = split[horizon:]
            out.loc[dest, f"complete_h{horizon}_flag"] = complete
            returns = np.full(len(dest), np.nan)
            returns[complete] = future_close[complete] / close[:-horizon][complete] - 1.0
            out.loc[dest, f"return_close_t{horizon}"] = returns
            path_max = np.full(len(dest), np.nan)
            path_min = np.full(len(dest), np.nan)
            for pos in range(n - horizon):
                window = close[pos + 1 : pos + horizon + 1]
                if complete[pos] and np.isfinite(window).all():
                    path_max[pos] = np.max(window) / close[pos] - 1.0
                    path_min[pos] = np.min(window) / close[pos] - 1.0
            out.loc[dest, f"path_max_return_to_{horizon}"] = path_max
            out.loc[dest, f"path_min_return_to_{horizon}"] = path_min

        if n > label_horizon:
            dest = idx_arr[:-label_horizon]
            peak_ret_close = np.full(len(dest), np.nan)
            peak_ret_open = np.full(len(dest), np.nan)
            complete_h = np.zeros(len(dest), dtype=bool)
            for pos in range(n - label_horizon):
                window = close[pos + 1 : pos + label_horizon + 1]
                same_split = split[pos] == split[pos + label_horizon]
                complete = finite_close[pos] and same_split and np.isfinite(window).all()
                complete_h[pos] = complete
                if complete:
                    peak = float(np.max(window))
                    peak_ret_close[pos] = peak / close[pos] - 1.0
                    next_open = open_[pos + 1] if pos + 1 < n else np.nan
                    if np.isfinite(next_open):
                        peak_ret_open[pos] = peak / next_open - 1.0
            out.loc[dest, "complete_h120_flag"] = complete_h
            out.loc[dest, "forward_close_peak_h120_return_from_close"] = peak_ret_close
            out.loc[dest, "big_winner_forward_from_signal_close"] = np.nan_to_num(peak_ret_close, nan=-np.inf) >= 0.50
            out.loc[dest, "forward_close_peak_h120_return_from_next_open"] = peak_ret_open
            out.loc[dest, "big_winner_forward_from_next_open"] = np.nan_to_num(peak_ret_open, nan=-np.inf) >= 0.50

    incomplete = []
    for row in out.itertuples(index=False):
        reasons: list[str] = []
        if not bool(getattr(row, "complete_h120_flag")):
            reasons.append("incomplete_h120")
        for horizon in horizons:
            if not bool(getattr(row, f"complete_h{horizon}_flag")):
                reasons.append(f"incomplete_h{horizon}")
        incomplete.append("|".join(reasons))
    out["incomplete_forward_reason"] = incomplete
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


def build_action_time_panel(stock: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    horizons = [int(v) for v in config["horizons"]]
    base_mask = (
        stock["split"].isin(SPLITS)
        & stock["eligible_stock_day"].astype(bool)
        & np.isfinite(pd.to_numeric(stock["close"], errors="coerce"))
    )
    base = stock.loc[base_mask].copy()
    base["trade_date"] = pd.to_datetime(base["date"])
    base["year"] = base["trade_date"].dt.year.astype(int)
    base_cols = [
        "instrument",
        "trade_date",
        "split",
        "year",
        "close",
        "next_open_t1",
        "complete_h120_flag",
        "forward_close_peak_h120_return_from_close",
        "big_winner_forward_from_signal_close",
        "forward_close_peak_h120_return_from_next_open",
        "big_winner_forward_from_next_open",
        "incomplete_forward_reason",
    ]
    for horizon in horizons:
        base_cols += [
            f"complete_h{horizon}_flag",
            f"return_close_t{horizon}",
            f"path_max_return_to_{horizon}",
            f"path_min_return_to_{horizon}",
        ]

    panels: list[pd.DataFrame] = []
    for item in config["frozen_conditions"]:
        part = base[base_cols].copy()
        complete = pd.Series(True, index=base.index)
        signal = pd.Series(True, index=base.index)
        for term in item["terms"]:
            feature = term["feature"]
            if feature not in base.columns:
                raise RuntimeError(f"feature column missing for frozen condition: {feature}")
            series = base[feature]
            term_complete = series.notna() & np.isfinite(pd.to_numeric(series, errors="coerce"))
            complete &= term_complete
            signal &= _eval_term(series, term["operator"], float(term["threshold"])).fillna(False)
        part = part.rename(columns={"instrument": "instrument_id", "close": "close_t"})
        part["condition_group_id"] = item["condition_group_id"]
        part["family_id"] = item["family_id"]
        part["condition_text"] = item["condition_text"]
        part["base_action_time_eligible_flag"] = True
        part["feature_complete_flag"] = complete.to_numpy(dtype=bool)
        part["signal_occurs"] = (complete & signal).to_numpy(dtype=bool)
        panels.append(part)
    panel = pd.concat(panels, ignore_index=True)
    signal_counts = panel.loc[panel["signal_occurs"]].groupby(["instrument_id", "trade_date"]).size()
    panel["same_day_family_count"] = [
        int(signal_counts.get((row.instrument_id, row.trade_date), 0)) for row in panel[["instrument_id", "trade_date"]].itertuples(index=False)
    ]
    return panel


def add_episode_fields(panel: pd.DataFrame, calendar: pd.DatetimeIndex, merge_gap: int) -> pd.DataFrame:
    out = panel.sort_values(["condition_group_id", "instrument_id", "trade_date"]).reset_index(drop=True).copy()
    cal_pos = {pd.Timestamp(d).normalize(): i for i, d in enumerate(calendar)}
    out["signal_episode_id"] = pd.NA
    out["is_episode_start"] = False
    out["episode_signal_date"] = pd.NaT
    out["episode_occurrence_price_t"] = np.nan
    out["episode_entry_price_t"] = np.nan
    out["episode_length_trading_days"] = np.nan
    out["episode_trigger_day_count"] = 0

    signal_idx = out.index[out["signal_occurs"].astype(bool)].to_numpy()
    if len(signal_idx) == 0:
        return out
    signal = out.loc[signal_idx, ["condition_group_id", "instrument_id", "trade_date", "close_t", "next_open_t1"]].copy()
    for (condition_group_id, instrument_id), grp in signal.groupby(["condition_group_id", "instrument_id"], sort=False):
        grp = grp.sort_values("trade_date")
        current: list[int] = []
        current_start_date: pd.Timestamp | None = None
        last_pos: int | None = None
        for idx, row in grp.iterrows():
            date = pd.Timestamp(row["trade_date"]).normalize()
            pos = cal_pos.get(date)
            if pos is None:
                continue
            start_new = last_pos is None or (pos - last_pos) > merge_gap
            if start_new and current:
                _write_episode(out, current, current_start_date, condition_group_id, instrument_id, cal_pos)
                current = []
            if start_new:
                current_start_date = date
            current.append(idx)
            last_pos = pos
        if current:
            _write_episode(out, current, current_start_date, condition_group_id, instrument_id, cal_pos)
    return out


def _write_episode(
    out: pd.DataFrame,
    indices: list[int],
    start_date: pd.Timestamp | None,
    condition_group_id: str,
    instrument_id: str,
    cal_pos: dict[pd.Timestamp, int],
) -> None:
    if not indices or start_date is None:
        return
    start_idx = indices[0]
    end_date = pd.Timestamp(out.loc[indices[-1], "trade_date"]).normalize()
    length = cal_pos.get(end_date, cal_pos[start_date]) - cal_pos[start_date] + 1
    episode_id = f"{condition_group_id}__{instrument_id}__{start_date.date().isoformat()}__{_hash_json(indices, 8)}"
    out.loc[indices, "signal_episode_id"] = episode_id
    out.loc[indices, "episode_signal_date"] = start_date
    out.loc[indices, "episode_occurrence_price_t"] = float(out.loc[start_idx, "close_t"])
    out.loc[indices, "episode_entry_price_t"] = float(out.loc[start_idx, "next_open_t1"])
    out.loc[indices, "episode_length_trading_days"] = int(length)
    out.loc[indices, "episode_trigger_day_count"] = int(len(indices))
    out.loc[start_idx, "is_episode_start"] = True


def _with_all_split(df: pd.DataFrame, group_cols: list[str], value_func) -> pd.DataFrame:
    rows = []
    for keys, grp in df.groupby(group_cols, dropna=False):
        key_tuple = keys if isinstance(keys, tuple) else (keys,)
        rows.append(value_func(dict(zip(group_cols, key_tuple)), grp))
    all_group_cols = [c for c in group_cols if c != "split"]
    if "split" in group_cols:
        for keys, grp in df.groupby(all_group_cols, dropna=False):
            key_tuple = keys if isinstance(keys, tuple) else (keys,)
            payload = dict(zip(all_group_cols, key_tuple))
            payload["split"] = "all"
            rows.append(value_func(payload, grp))
    return pd.DataFrame(rows)


def precision_rows(panel: pd.DataFrame, grain: str, bootstrap_ci: pd.DataFrame | None = None) -> pd.DataFrame:
    if grain == "stock_day":
        metric = panel.loc[panel["signal_occurs"].astype(bool)].copy()
    else:
        metric = panel.loc[panel["signal_occurs"].astype(bool) & panel["is_episode_start"].astype(bool)].copy()
    group_cols = ["condition_group_id", "family_id", "split"]

    def calc(keys: dict[str, Any], signal_grp: pd.DataFrame) -> dict[str, Any]:
        cond = keys["condition_group_id"]
        split = keys["split"]
        bg = panel.loc[panel["condition_group_id"].eq(cond)]
        if split != "all":
            bg = bg.loc[bg["split"].eq(split)]
        complete_signal = signal_grp.loc[signal_grp["complete_h120_flag"].astype(bool)]
        bg_global = bg.loc[bg["complete_h120_flag"].astype(bool)]
        bg_matched = bg.loc[bg["feature_complete_flag"].astype(bool) & bg["complete_h120_flag"].astype(bool)]
        precision = _safe_div(complete_signal["big_winner_forward_from_signal_close"].sum(), len(complete_signal), np.nan)
        prior_global = _safe_div(bg_global["big_winner_forward_from_signal_close"].sum(), len(bg_global), np.nan)
        prior_matched = _safe_div(bg_matched["big_winner_forward_from_signal_close"].sum(), len(bg_matched), np.nan)
        lift = _safe_div(precision, prior_matched, np.nan)
        precision_open = _safe_div(complete_signal["big_winner_forward_from_next_open"].sum(), len(complete_signal), np.nan)
        return {
            **keys,
            "grain": grain,
            "signal_count": int(len(signal_grp)),
            "complete_h120_count": int(len(complete_signal)),
            "positive_h120_count": int(complete_signal["big_winner_forward_from_signal_close"].sum()),
            "precision_h120_close_anchor": precision,
            "background_prior_global_h120_close_anchor": prior_global,
            "background_prior_feature_matched_h120_close_anchor": prior_matched,
            "precision_lift_feature_matched_h120_close_anchor": lift,
            "precision_h120_next_open_anchor": precision_open,
            "incomplete_h120_count": int(len(signal_grp) - len(complete_signal)),
            "feature_complete_ratio": float(bg["feature_complete_flag"].mean()) if len(bg) else np.nan,
            "positive_h120_count_min_gate_pass": bool(int(complete_signal["big_winner_forward_from_signal_close"].sum()) >= 20),
        }

    out = _with_all_split(metric, group_cols, calc)
    if bootstrap_ci is not None and not bootstrap_ci.empty:
        out = out.merge(
            bootstrap_ci.loc[bootstrap_ci["grain"].eq(grain)],
            on=["condition_group_id", "family_id", "split", "grain"],
            how="left",
        )
    else:
        out["bootstrap_precision_lift_ci90_lower"] = np.nan
        out["bootstrap_precision_lift_ci90_upper"] = np.nan
    return out.sort_values(["grain", "condition_group_id", "split"]).reset_index(drop=True)


def precision_by_year_rows(panel: pd.DataFrame, grain: str) -> pd.DataFrame:
    if grain == "stock_day":
        metric = panel.loc[panel["signal_occurs"].astype(bool)].copy()
    else:
        metric = panel.loc[panel["signal_occurs"].astype(bool) & panel["is_episode_start"].astype(bool)].copy()
    rows: list[dict[str, Any]] = []
    for (condition_group_id, family_id, year), signal_grp in metric.groupby(["condition_group_id", "family_id", "year"], sort=True):
        bg = panel.loc[panel["condition_group_id"].eq(condition_group_id) & panel["year"].eq(year)]
        complete_signal = signal_grp.loc[signal_grp["complete_h120_flag"].astype(bool)]
        bg_global = bg.loc[bg["complete_h120_flag"].astype(bool)]
        bg_matched = bg.loc[bg["feature_complete_flag"].astype(bool) & bg["complete_h120_flag"].astype(bool)]
        precision = _safe_div(complete_signal["big_winner_forward_from_signal_close"].sum(), len(complete_signal), np.nan)
        prior_global = _safe_div(bg_global["big_winner_forward_from_signal_close"].sum(), len(bg_global), np.nan)
        prior_matched = _safe_div(bg_matched["big_winner_forward_from_signal_close"].sum(), len(bg_matched), np.nan)
        rows.append(
            {
                "condition_group_id": condition_group_id,
                "family_id": family_id,
                "grain": grain,
                "year": int(year),
                "signal_count": int(len(signal_grp)),
                "complete_h120_count": int(len(complete_signal)),
                "positive_h120_count": int(complete_signal["big_winner_forward_from_signal_close"].sum()),
                "precision_h120_close_anchor": precision,
                "background_prior_global_h120_close_anchor": prior_global,
                "background_prior_feature_matched_h120_close_anchor": prior_matched,
                "precision_lift_feature_matched_h120_close_anchor": _safe_div(precision, prior_matched, np.nan),
                "incomplete_h120_count": int(len(signal_grp) - len(complete_signal)),
                "feature_complete_ratio": float(bg["feature_complete_flag"].mean()) if len(bg) else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["grain", "condition_group_id", "year"]).reset_index(drop=True)


def bootstrap_lift(panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, int]]:
    boot = config["bootstrap"]
    iterations = int(boot["iterations"])
    seed = int(boot["random_seed"])
    confidence = float(boot["confidence_level"])
    lower_q = (1.0 - confidence) / 2.0
    upper_q = 1.0 - lower_q
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    sample_counts: dict[str, int] = {}
    base = panel.copy()
    base["instrument_year"] = base["instrument_id"].astype(str) + "_" + base["year"].astype(str)
    for grain in ["stock_day", "episode"]:
        for (condition_group_id, family_id, split), grp in base.loc[base["split"].isin(SPLITS)].groupby(["condition_group_id", "family_id", "split"], sort=True):
            if grain == "stock_day":
                sig_mask = grp["signal_occurs"].astype(bool) & grp["complete_h120_flag"].astype(bool)
            else:
                sig_mask = grp["signal_occurs"].astype(bool) & grp["is_episode_start"].astype(bool) & grp["complete_h120_flag"].astype(bool)
            bg_mask = grp["feature_complete_flag"].astype(bool) & grp["complete_h120_flag"].astype(bool)
            agg = grp.assign(
                sig_count=sig_mask.astype(int),
                sig_pos=(sig_mask & grp["big_winner_forward_from_signal_close"].astype(bool)).astype(int),
                bg_count=bg_mask.astype(int),
                bg_pos=(bg_mask & grp["big_winner_forward_from_signal_close"].astype(bool)).astype(int),
            ).groupby("instrument_year", as_index=False)[["sig_count", "sig_pos", "bg_count", "bg_pos"]].sum()
            sample_counts[f"{grain}:{condition_group_id}:{split}"] = int(len(agg))
            if agg.empty:
                lower = np.nan
                upper = np.nan
            else:
                values = agg[["sig_count", "sig_pos", "bg_count", "bg_pos"]].to_numpy(dtype=float)
                lifts = np.empty(iterations, dtype=float)
                for i in range(iterations):
                    sample = values[rng.integers(0, len(values), size=len(values))]
                    sig_count, sig_pos, bg_count, bg_pos = sample.sum(axis=0)
                    precision = _safe_div(sig_pos, sig_count, np.nan)
                    prior = _safe_div(bg_pos, bg_count, np.nan)
                    lifts[i] = _safe_div(precision, prior, np.nan)
                clean = lifts[np.isfinite(lifts)]
                lower = float(np.quantile(clean, lower_q, method="nearest")) if len(clean) else np.nan
                upper = float(np.quantile(clean, upper_q, method="nearest")) if len(clean) else np.nan
            rows.append(
                {
                    "condition_group_id": condition_group_id,
                    "family_id": family_id,
                    "split": split,
                    "grain": grain,
                    "bootstrap_precision_lift_ci90_lower": lower,
                    "bootstrap_precision_lift_ci90_upper": upper,
                }
            )
    return pd.DataFrame(rows), sample_counts


def forward_return_stats(panel: pd.DataFrame, config: dict[str, Any], grain: str) -> pd.DataFrame:
    if grain == "stock_day":
        metric = panel.loc[panel["signal_occurs"].astype(bool)].copy()
    else:
        metric = panel.loc[panel["signal_occurs"].astype(bool) & panel["is_episode_start"].astype(bool)].copy()
    rows: list[dict[str, Any]] = []
    for split_value in SPLITS + ["all"]:
        base = metric if split_value == "all" else metric.loc[metric["split"].eq(split_value)]
        for (condition_group_id, family_id), grp in base.groupby(["condition_group_id", "family_id"], sort=True):
            for horizon in [int(v) for v in config["horizons"]]:
                complete = grp.loc[grp[f"complete_h{horizon}_flag"].astype(bool)]
                endpoint = pd.to_numeric(complete[f"return_close_t{horizon}"], errors="coerce").dropna()
                path_max = pd.to_numeric(complete[f"path_max_return_to_{horizon}"], errors="coerce").dropna()
                path_min = pd.to_numeric(complete[f"path_min_return_to_{horizon}"], errors="coerce").dropna()
                rows.append(
                    {
                        "condition_group_id": condition_group_id,
                        "family_id": family_id,
                        "grain": grain,
                        "split": split_value,
                        "horizon": horizon,
                        "signal_count": int(len(grp)),
                        "complete_horizon_count": int(len(complete)),
                        "incomplete_horizon_count": int(len(grp) - len(complete)),
                        "endpoint_return_max": float(endpoint.max()) if len(endpoint) else np.nan,
                        "endpoint_return_min": float(endpoint.min()) if len(endpoint) else np.nan,
                        "endpoint_return_mean": float(endpoint.mean()) if len(endpoint) else np.nan,
                        "endpoint_return_median": float(endpoint.median()) if len(endpoint) else np.nan,
                        "endpoint_return_p25": float(endpoint.quantile(0.25)) if len(endpoint) else np.nan,
                        "endpoint_return_p75": float(endpoint.quantile(0.75)) if len(endpoint) else np.nan,
                        "endpoint_return_positive_rate": float((endpoint > 0).mean()) if len(endpoint) else np.nan,
                        "path_max_return_mean": float(path_max.mean()) if len(path_max) else np.nan,
                        "path_max_return_median": float(path_max.median()) if len(path_max) else np.nan,
                        "path_min_return_mean": float(path_min.mean()) if len(path_min) else np.nan,
                        "path_min_return_median": float(path_min.median()) if len(path_min) else np.nan,
                    }
                )
    return pd.DataFrame(rows).sort_values(["grain", "condition_group_id", "split", "horizon"]).reset_index(drop=True)


def background_prior_audit(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split_value in SPLITS + ["all"]:
        base = panel if split_value == "all" else panel.loc[panel["split"].eq(split_value)]
        for (condition_group_id, family_id), grp in base.groupby(["condition_group_id", "family_id"], sort=True):
            global_rows = grp.loc[grp["complete_h120_flag"].astype(bool)]
            matched = grp.loc[grp["feature_complete_flag"].astype(bool) & grp["complete_h120_flag"].astype(bool)]
            for role, role_df in [("global", global_rows), ("feature_matched", matched)]:
                rows.append(
                    {
                        "condition_group_id": condition_group_id,
                        "family_id": family_id,
                        "split": split_value,
                        "background_denominator_role": role,
                        "denominator_count": int(len(role_df)),
                        "positive_h120_count": int(role_df["big_winner_forward_from_signal_close"].sum()),
                        "background_prior_h120_close_anchor": _safe_div(role_df["big_winner_forward_from_signal_close"].sum(), len(role_df), np.nan),
                    }
                )
    return pd.DataFrame(rows)


def missingness_audit(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split_value in SPLITS + ["all"]:
        base = panel if split_value == "all" else panel.loc[panel["split"].eq(split_value)]
        for (condition_group_id, family_id), grp in base.groupby(["condition_group_id", "family_id"], sort=True):
            row = {
                "condition_group_id": condition_group_id,
                "family_id": family_id,
                "split": split_value,
                "base_action_time_row_count": int(len(grp)),
                "feature_complete_count": int(grp["feature_complete_flag"].sum()),
                "feature_incomplete_count": int((~grp["feature_complete_flag"].astype(bool)).sum()),
                "signal_count": int(grp["signal_occurs"].sum()),
                "complete_h120_count": int(grp["complete_h120_flag"].sum()),
                "incomplete_h120_count": int((~grp["complete_h120_flag"].astype(bool)).sum()),
            }
            for horizon in config["horizons"]:
                h = int(horizon)
                row[f"complete_h{h}_count"] = int(grp[f"complete_h{h}_flag"].sum())
                row[f"incomplete_h{h}_count"] = int((~grp[f"complete_h{h}_flag"].astype(bool)).sum())
            rows.append(row)
    return pd.DataFrame(rows)


def overlap_matrix(panel: pd.DataFrame) -> pd.DataFrame:
    signal = panel.loc[panel["signal_occurs"].astype(bool), ["instrument_id", "trade_date", "condition_group_id", "complete_h120_flag", "big_winner_forward_from_signal_close"]].copy()
    conditions = sorted(panel["condition_group_id"].unique().tolist())
    rows: list[dict[str, Any]] = []
    by_condition = {cid: signal.loc[signal["condition_group_id"].eq(cid)].set_index(["instrument_id", "trade_date"]) for cid in conditions}
    for a in conditions:
        idx_a = by_condition[a].index
        for b in conditions:
            idx_b = by_condition[b].index
            joint_idx = idx_a.intersection(idx_b)
            joint = by_condition[a].loc[joint_idx] if len(joint_idx) else pd.DataFrame()
            complete = joint.loc[joint["complete_h120_flag"].astype(bool)] if len(joint) else joint
            rows.append(
                {
                    "condition_a": a,
                    "condition_b": b,
                    "signal_count_a": int(len(idx_a)),
                    "joint_signal_count": int(len(joint_idx)),
                    "p_b_given_a": _safe_div(len(joint_idx), len(idx_a), np.nan),
                    "joint_complete_h120_count": int(len(complete)),
                    "joint_precision_h120": _safe_div(complete["big_winner_forward_from_signal_close"].sum(), len(complete), np.nan) if len(complete) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _family_wide_panel(panel: pd.DataFrame) -> pd.DataFrame:
    base_cols = [
        "instrument_id",
        "trade_date",
        "split",
        "year",
        "complete_h120_flag",
        "big_winner_forward_from_signal_close",
        "big_winner_forward_from_next_open",
    ]
    base = panel[base_cols].drop_duplicates(["instrument_id", "trade_date"]).copy()
    signal = (
        panel.pivot_table(
            index=["instrument_id", "trade_date"],
            columns="family_id",
            values="signal_occurs",
            aggfunc="max",
            fill_value=False,
        )
        .astype(bool)
        .sort_index(axis=1)
    )
    complete = (
        panel.pivot_table(
            index=["instrument_id", "trade_date"],
            columns="family_id",
            values="feature_complete_flag",
            aggfunc="max",
            fill_value=False,
        )
        .astype(bool)
        .sort_index(axis=1)
    )
    wide = base.set_index(["instrument_id", "trade_date"]).join(signal.add_prefix("signal__")).join(complete.add_prefix("feature_complete__"))
    return wide.reset_index()


def _binary_phi(a: pd.Series, b: pd.Series) -> tuple[float, str]:
    a_int = a.astype(int)
    b_int = b.astype(int)
    if a_int.nunique(dropna=False) < 2:
        return np.nan, "family_a_zero_variance"
    if b_int.nunique(dropna=False) < 2:
        return np.nan, "family_b_zero_variance"
    return float(a_int.corr(b_int)), ""


def signal_redundancy(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wide = _family_wide_panel(panel)
    families = sorted(panel["family_id"].astype(str).unique().tolist())
    rows: list[dict[str, Any]] = []
    for family_a in families:
        signal_a_col = f"signal__{family_a}"
        complete_a_col = f"feature_complete__{family_a}"
        for family_b in families:
            signal_b_col = f"signal__{family_b}"
            complete_b_col = f"feature_complete__{family_b}"
            denom_mask = wide[complete_a_col].astype(bool) & wide[complete_b_col].astype(bool)
            pair = wide.loc[denom_mask]
            signal_a = pair[signal_a_col].astype(bool)
            signal_b = pair[signal_b_col].astype(bool)
            joint_mask = signal_a & signal_b
            union_mask = signal_a | signal_b
            complete_joint = pair.loc[joint_mask & pair["complete_h120_flag"].astype(bool)]
            phi, phi_null_reason = _binary_phi(signal_a, signal_b) if len(pair) else (np.nan, "empty_pair_denominator")
            rows.append(
                {
                    "family_a": family_a,
                    "family_b": family_b,
                    "pair_denominator_count": int(len(pair)),
                    "pair_feature_incomplete_count": int(len(wide) - len(pair)),
                    "signal_count_a": int(signal_a.sum()),
                    "signal_count_b": int(signal_b.sum()),
                    "joint_signal_count": int(joint_mask.sum()),
                    "union_signal_count": int(union_mask.sum()),
                    "p_b_given_a": _safe_div(float(joint_mask.sum()), float(signal_a.sum()), np.nan),
                    "p_a_given_b": _safe_div(float(joint_mask.sum()), float(signal_b.sum()), np.nan),
                    "phi_correlation": phi,
                    "jaccard_overlap": _safe_div(float(joint_mask.sum()), float(union_mask.sum()), np.nan),
                    "joint_precision_h120_close_anchor": _safe_div(
                        float(complete_joint["big_winner_forward_from_signal_close"].sum()), float(len(complete_joint)), np.nan
                    ),
                    "joint_complete_h120_count": int(len(complete_joint)),
                    "joint_positive_h120_count": int(complete_joint["big_winner_forward_from_signal_close"].sum()) if len(complete_joint) else 0,
                    "phi_null_reason": phi_null_reason,
                }
            )
    long = pd.DataFrame(rows)
    phi = long.pivot(index="family_a", columns="family_b", values="phi_correlation").reset_index()
    jaccard = long.pivot(index="family_a", columns="family_b", values="jaccard_overlap").reset_index()
    return long, phi, jaccard


def _precision_for_mask(wide: pd.DataFrame, mask: pd.Series, label_col: str = "big_winner_forward_from_signal_close") -> tuple[int, int, int, float]:
    signal_count = int(mask.sum())
    complete = wide.loc[mask & wide["complete_h120_flag"].astype(bool)]
    positive = int(complete[label_col].sum()) if len(complete) else 0
    precision = _safe_div(float(positive), float(len(complete)), np.nan)
    return signal_count, int(len(complete)), positive, precision


def signal_incremental_precision(panel: pd.DataFrame) -> pd.DataFrame:
    wide_all = _family_wide_panel(panel)
    families = sorted(panel["family_id"].astype(str).unique().tolist())
    rows: list[dict[str, Any]] = []
    for split_value in SPLITS + ["all"]:
        wide = wide_all if split_value == "all" else wide_all.loc[wide_all["split"].eq(split_value)]
        for base_family in families:
            for added_family in families:
                if base_family == added_family:
                    continue
                base_signal_col = f"signal__{base_family}"
                added_signal_col = f"signal__{added_family}"
                base_complete_col = f"feature_complete__{base_family}"
                added_complete_col = f"feature_complete__{added_family}"
                denom = wide[base_complete_col].astype(bool) & wide[added_complete_col].astype(bool)
                pair = wide.loc[denom]
                base = pair[base_signal_col].astype(bool)
                added = pair[added_signal_col].astype(bool)
                base_and_added = base & added
                base_only = base & ~added
                added_only = added & ~base
                base_signal_count, _, _, base_precision = _precision_for_mask(pair, base)
                added_signal_count, _, _, _ = _precision_for_mask(pair, added)
                base_and_signal_count, base_and_complete, base_and_positive, base_and_precision = _precision_for_mask(pair, base_and_added)
                base_only_signal_count, _, _, base_only_precision = _precision_for_mask(pair, base_only)
                added_only_signal_count, _, _, added_only_precision = _precision_for_mask(pair, added_only)
                rows.append(
                    {
                        "split": split_value,
                        "base_family": base_family,
                        "added_family": added_family,
                        "pair_denominator_count": int(len(pair)),
                        "base_signal_count": base_signal_count,
                        "added_signal_count": added_signal_count,
                        "base_and_added_signal_count": base_and_signal_count,
                        "base_only_signal_count": base_only_signal_count,
                        "added_only_signal_count": added_only_signal_count,
                        "base_precision_h120_close_anchor": base_precision,
                        "base_and_added_precision_h120_close_anchor": base_and_precision,
                        "base_only_precision_h120_close_anchor": base_only_precision,
                        "added_only_precision_h120_close_anchor": added_only_precision,
                        "delta_precision_base_and_added_minus_base": base_and_precision - base_precision
                        if np.isfinite(base_and_precision) and np.isfinite(base_precision)
                        else np.nan,
                        "lift_base_and_added_vs_base": _safe_div(base_and_precision, base_precision, np.nan),
                        "signal_retention_base_and_added_vs_base": _safe_div(float(base_and_signal_count), float(base_signal_count), np.nan),
                        "positive_h120_count_base_and_added": base_and_positive,
                        "complete_h120_count_base_and_added": base_and_complete,
                    }
                )
    return pd.DataFrame(rows)


def top4_independent_combined_precision(panel: pd.DataFrame, redundancy_long: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    wide_all = _family_wide_panel(panel)
    families = sorted(panel["family_id"].astype(str).unique().tolist())
    metric_lookup = {
        tuple(sorted((str(row.family_a), str(row.family_b)))): {
            "phi": float(row.phi_correlation) if np.isfinite(row.phi_correlation) else np.nan,
            "jaccard": float(row.jaccard_overlap) if np.isfinite(row.jaccard_overlap) else np.nan,
        }
        for row in redundancy_long.itertuples(index=False)
        if str(row.family_a) != str(row.family_b)
    }
    audit_rows: list[dict[str, Any]] = []
    for combo in itertools.combinations(families, 4):
        pair_values = [metric_lookup[tuple(sorted(pair))] for pair in itertools.combinations(combo, 2)]
        abs_phi = [abs(v["phi"]) for v in pair_values if np.isfinite(v["phi"])]
        jaccard = [v["jaccard"] for v in pair_values if np.isfinite(v["jaccard"])]
        audit_rows.append(
            {
                "selected_family_set": "|".join(combo),
                "combo_pair_count": 6,
                "combo_mean_abs_phi": float(np.mean(abs_phi)) if abs_phi else np.nan,
                "combo_max_abs_phi": float(np.max(abs_phi)) if abs_phi else np.nan,
                "combo_mean_jaccard": float(np.mean(jaccard)) if jaccard else np.nan,
                "combo_max_jaccard": float(np.max(jaccard)) if jaccard else np.nan,
                "sorted_family_id_tuple": "|".join(combo),
            }
        )
    audit = pd.DataFrame(audit_rows).sort_values(
        ["combo_mean_abs_phi", "combo_max_abs_phi", "combo_mean_jaccard", "combo_max_jaccard", "sorted_family_id_tuple"],
        ascending=[True, True, True, True, True],
        na_position="last",
    )
    audit["selection_rank"] = np.arange(1, len(audit) + 1, dtype=int)
    top = audit.iloc[0]
    selected = str(top["selected_family_set"]).split("|")

    rows: list[dict[str, Any]] = []
    for split_value in SPLITS + ["all"]:
        wide = wide_all if split_value == "all" else wide_all.loc[wide_all["split"].eq(split_value)]
        common = pd.Series(True, index=wide.index)
        combined = pd.Series(True, index=wide.index)
        selected_counts = []
        for family in selected:
            common &= wide[f"feature_complete__{family}"].astype(bool)
            family_signal = wide[f"signal__{family}"].astype(bool)
            selected_counts.append(int((wide[f"feature_complete__{family}"].astype(bool) & family_signal).sum()))
            combined &= family_signal
        common_wide = wide.loc[common]
        combined_mask = combined.loc[common_wide.index]
        signal_count, complete_count, positive_count, precision = _precision_for_mask(common_wide, combined_mask)
        _, _, positive_open, precision_open = _precision_for_mask(common_wide, combined_mask, "big_winner_forward_from_next_open")
        bg = common_wide.loc[common_wide["complete_h120_flag"].astype(bool)]
        prior = _safe_div(float(bg["big_winner_forward_from_signal_close"].sum()), float(len(bg)), np.nan)
        rows.append(
            {
                "split": split_value,
                "selected_family_set": str(top["selected_family_set"]),
                "selection_rank": int(top["selection_rank"]),
                "combo_mean_abs_phi": float(top["combo_mean_abs_phi"]),
                "combo_max_abs_phi": float(top["combo_max_abs_phi"]),
                "combo_mean_jaccard": float(top["combo_mean_jaccard"]),
                "combo_max_jaccard": float(top["combo_max_jaccard"]),
                "top4_common_denominator_count": int(len(common_wide)),
                "top4_combined_signal_count": signal_count,
                "top4_combined_complete_h120_count": complete_count,
                "top4_combined_positive_h120_count": positive_count,
                "top4_combined_precision_h120_close_anchor": precision,
                "top4_background_prior_common_denominator_h120_close_anchor": prior,
                "top4_precision_lift_vs_common_denominator": _safe_div(precision, prior, np.nan),
                "top4_precision_h120_next_open_anchor": precision_open,
                "top4_positive_h120_count_next_open_anchor": positive_open,
                "top4_signal_retention_vs_min_single_family": _safe_div(float(signal_count), float(min(selected_counts)), np.nan)
                if selected_counts
                else np.nan,
                "top4_signal_retention_vs_max_single_family": _safe_div(float(signal_count), float(max(selected_counts)), np.nan)
                if selected_counts
                else np.nan,
                "sample_sufficiency_status": "fragile_low_sample"
                if complete_count < 200 or positive_count < 10
                else "sufficient_for_diagnostic",
            }
        )
    meta = {
        "top4_independence_selection_rule": "rank C(7,4) by combo_mean_abs_phi, combo_max_abs_phi, combo_mean_jaccard, combo_max_jaccard, sorted_family_id_tuple ascending; no outcome fields",
        "top4_independent_family_set": selected,
        "top4_independence_score": float(top["combo_mean_abs_phi"]),
        "top4_combined_signal_count": int(pd.DataFrame(rows).loc[lambda df: df["split"].eq("all"), "top4_combined_signal_count"].iloc[0]),
    }
    return audit, pd.DataFrame(rows), meta


def decision_gate_audit(precision: pd.DataFrame, returns: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    decision_cfg = config["decision"]
    grain = decision_cfg["decision_grain"]
    p = precision.loc[precision["grain"].eq(grain) & precision["split"].isin(["validation", "robustness"])].copy()
    r20 = returns.loc[(returns["grain"].eq(grain)) & (returns["horizon"].eq(20)) & returns["split"].isin(["validation", "robustness"])][
        ["condition_group_id", "split", "endpoint_return_median"]
    ]
    p = p.merge(r20, on=["condition_group_id", "split"], how="left")
    rows: list[dict[str, Any]] = []
    pass_by_family: dict[str, bool] = {}
    any_lift = False
    for condition_group_id, grp in p.groupby("condition_group_id"):
        family_id = str(grp["family_id"].iloc[0])
        split_passes = []
        for row in grp.itertuples(index=False):
            signal_ok = int(row.signal_count) >= int(decision_cfg["min_signal_count"])
            complete_ok = int(row.complete_h120_count) >= int(decision_cfg["min_complete_h120_count"])
            positive_ok = int(row.positive_h120_count) >= int(decision_cfg["min_positive_h120_count"])
            lift_threshold = float(decision_cfg["min_lift_validation"] if row.split == "validation" else decision_cfg["min_lift_robustness"])
            lift = float(row.precision_lift_feature_matched_h120_close_anchor)
            any_lift = any_lift or bool(np.isfinite(lift) and lift > 1.0)
            lift_ok = np.isfinite(lift) and lift >= lift_threshold
            ci_ok = np.isfinite(row.bootstrap_precision_lift_ci90_lower) and float(row.bootstrap_precision_lift_ci90_lower) > float(decision_cfg["min_bootstrap_lift_ci90_lower"])
            ret_ok = np.isfinite(row.endpoint_return_median) and (float(row.endpoint_return_median) > 0 if decision_cfg["require_t20_median_positive"] else True)
            split_pass = bool(signal_ok and complete_ok and positive_ok and lift_ok and ci_ok and ret_ok)
            split_passes.append(split_pass)
            rows.append(
                {
                    "condition_group_id": condition_group_id,
                    "family_id": family_id,
                    "split": row.split,
                    "decision_grain": grain,
                    "signal_count": int(row.signal_count),
                    "complete_h120_count": int(row.complete_h120_count),
                    "positive_h120_count": int(row.positive_h120_count),
                    "precision_lift_feature_matched_h120_close_anchor": lift,
                    "bootstrap_precision_lift_ci90_lower": float(row.bootstrap_precision_lift_ci90_lower) if np.isfinite(row.bootstrap_precision_lift_ci90_lower) else np.nan,
                    "endpoint_return_median_t20": float(row.endpoint_return_median) if np.isfinite(row.endpoint_return_median) else np.nan,
                    "signal_count_gate_pass": signal_ok,
                    "complete_h120_gate_pass": complete_ok,
                    "positive_h120_gate_pass": positive_ok,
                    "lift_gate_pass": lift_ok,
                    "bootstrap_gate_pass": ci_ok,
                    "t20_median_gate_pass": ret_ok,
                    "split_gate_pass": split_pass,
                }
            )
        pass_by_family[condition_group_id] = len(split_passes) == 2 and all(split_passes)
    passed = sum(pass_by_family.values())
    if passed >= int(decision_cfg["min_passing_family_count"]):
        decision = "statistical_calibration_positive"
    elif any_lift:
        decision = "mixed_precision_keep_as_lifecycle_tags"
    else:
        decision = "precision_not_supported"
    return pd.DataFrame(rows), decision


def write_report(
    reports_dir: Path,
    precision: pd.DataFrame,
    returns: pd.DataFrame,
    episode_precision: pd.DataFrame,
    redundancy_long: pd.DataFrame,
    incremental: pd.DataFrame,
    top4_audit: pd.DataFrame,
    top4_combined: pd.DataFrame,
    decision_audit: pd.DataFrame,
    manifest: dict[str, Any],
    decision: str,
) -> None:
    headline = precision.loc[(precision["grain"].eq("stock_day")) & (precision["split"].eq("all"))].copy()
    headline = headline.sort_values("precision_lift_feature_matched_h120_close_anchor", ascending=False)
    ret20 = returns.loc[(returns["grain"].eq("stock_day")) & (returns["split"].eq("all")) & (returns["horizon"].eq(20))][
        ["condition_group_id", "endpoint_return_mean", "endpoint_return_median"]
    ]
    headline = headline.merge(ret20, on="condition_group_id", how="left")
    precision_cols = [
        "family_id",
        "condition_group_id",
        "signal_count",
        "complete_h120_count",
        "positive_h120_count",
        "precision_h120_close_anchor",
        "background_prior_feature_matched_h120_close_anchor",
        "precision_lift_feature_matched_h120_close_anchor",
        "endpoint_return_mean",
        "endpoint_return_median",
    ]
    split_table = precision.loc[(precision["grain"].eq("stock_day")) & precision["split"].isin(["validation", "robustness"])][
        [
            "family_id",
            "split",
            "signal_count",
            "precision_h120_close_anchor",
            "precision_lift_feature_matched_h120_close_anchor",
            "bootstrap_precision_lift_ci90_lower",
        ]
    ].sort_values(["family_id", "split"])
    return_table = returns.loc[(returns["grain"].eq("stock_day")) & (returns["split"].eq("all"))][
        [
            "family_id",
            "horizon",
            "complete_horizon_count",
            "endpoint_return_max",
            "endpoint_return_min",
            "endpoint_return_mean",
            "endpoint_return_median",
            "endpoint_return_positive_rate",
        ]
    ].sort_values(["family_id", "horizon"])
    episode_table = episode_precision.loc[episode_precision["split"].eq("all")][
        ["family_id", "signal_count", "complete_h120_count", "precision_h120_close_anchor", "precision_lift_feature_matched_h120_close_anchor"]
    ].sort_values("family_id")
    redundancy_pairs = redundancy_long.loc[redundancy_long["family_a"].ne(redundancy_long["family_b"])].copy()
    redundancy_summary = redundancy_pairs[
        [
            "family_a",
            "family_b",
            "pair_denominator_count",
            "joint_signal_count",
            "p_b_given_a",
            "phi_correlation",
            "jaccard_overlap",
            "joint_precision_h120_close_anchor",
        ]
    ].sort_values(["phi_correlation", "jaccard_overlap"], ascending=[False, False]).head(12)
    incremental_all = incremental.loc[incremental["split"].eq("all")].copy()
    incremental_summary = incremental_all[
        [
            "base_family",
            "added_family",
            "base_signal_count",
            "base_and_added_signal_count",
            "base_precision_h120_close_anchor",
            "base_and_added_precision_h120_close_anchor",
            "delta_precision_base_and_added_minus_base",
            "signal_retention_base_and_added_vs_base",
            "complete_h120_count_base_and_added",
        ]
    ].sort_values(["delta_precision_base_and_added_minus_base", "complete_h120_count_base_and_added"], ascending=[False, False]).head(12)
    top4_selection = top4_audit.head(10)[
        [
            "selection_rank",
            "selected_family_set",
            "combo_mean_abs_phi",
            "combo_max_abs_phi",
            "combo_mean_jaccard",
            "combo_max_jaccard",
        ]
    ].copy()
    top4_selection["selected_family_set"] = top4_selection["selected_family_set"].astype(str).str.replace("|", ", ", regex=False)
    top4_table = top4_combined[
        [
            "split",
            "selected_family_set",
            "top4_combined_signal_count",
            "top4_combined_complete_h120_count",
            "top4_combined_positive_h120_count",
            "top4_combined_precision_h120_close_anchor",
            "top4_background_prior_common_denominator_h120_close_anchor",
            "top4_precision_lift_vs_common_denominator",
            "top4_signal_retention_vs_min_single_family",
            "sample_sufficiency_status",
        ]
    ].sort_values("split").copy()
    top4_table["selected_family_set"] = top4_table["selected_family_set"].astype(str).str.replace("|", ", ", regex=False)
    lines = [
        "# R02 Family Precision And Forward Return Statistics V1 Final Report",
        "",
        "## 结论摘要",
        "",
        f"- Final decision: `{decision}`",
        f"- frozen family count: {manifest['frozen_condition_group_count']}",
        f"- action-time rows per condition: {manifest['eligible_stock_day_count']}",
        "- headline precision uses post-close close-anchor statistics; next-open precision is audit-only.",
        "- headline lift uses feature-matched background prior, not winner-window recall.",
        "",
        "## Headline Precision",
        "",
        headline[precision_cols].to_markdown(index=False),
        "",
        "## Validation / Robustness Precision",
        "",
        split_table.to_markdown(index=False),
        "",
        "## T+1 / T+3 / T+5 / T+10 / T+20 Endpoint Return",
        "",
        return_table.to_markdown(index=False),
        "",
        "## Episode De-dup Audit",
        "",
        episode_table.to_markdown(index=False),
        "",
        "## Signal Redundancy Diagnostics",
        "",
        "下表为 action-time stock-day 上的 family 信号冗余诊断。Phi / Jaccard 越高，越说明两个 family 可能在描述相近状态。",
        "",
        redundancy_summary.to_markdown(index=False),
        "",
        "## Pairwise Incremental Precision Diagnostics",
        "",
        "下表为 ordered pair 的诊断性 AND / only 统计。它只用于判断 added family 是否可能提供额外确认，不构成新信号。",
        "",
        incremental_summary.to_markdown(index=False),
        "",
        "## Top-4 Independent Combined Precision",
        "",
        "top-4 independent family set 只按信号独立性排序选择，不使用 precision、future return 或 big winner label。",
        "",
        top4_selection.to_markdown(index=False),
        "",
        top4_table.to_markdown(index=False),
        "",
        "## Decision Gate Audit",
        "",
        decision_audit.to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "这些统计只说明 frozen family 在 action-time 分母上的 posterior / forward-return 行为。pairwise AND / only 和 top-4 combined-AND 都是诊断性压力测试，不是当日可执行入场信号，也不直接生成 R03 promotion gate。",
        "",
    ]
    (reports_dir / "r02_family_precision_forward_return_final_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(config_path: Path) -> dict[str, Any]:
    config, r01_config, ep2_config = load_config(config_path)
    output_root = topic_path(config["output_root"])
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for directory in [cache_dir, reports_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    frozen_audit = validate_frozen_conditions(config)
    write_csv(frozen_audit, reports_dir / "r02_family_frozen_condition_audit.csv")
    stock, calendar = load_stock(config, r01_config, ep2_config)
    stock = add_forward_fields(stock, [int(v) for v in config["horizons"]], int(config["forward_label_horizon"]))
    action_panel = build_action_time_panel(stock, config)
    action_panel = add_episode_fields(action_panel, calendar, int(config["episode"]["merge_gap_trading_days"]))

    bootstrap_ci, bootstrap_sample_counts = bootstrap_lift(action_panel, config)
    precision_stock = precision_rows(action_panel, "stock_day", bootstrap_ci)
    precision_episode = precision_rows(action_panel, "episode", bootstrap_ci)
    precision_all = pd.concat([precision_stock, precision_episode], ignore_index=True)
    precision_year = pd.concat([precision_by_year_rows(action_panel, "stock_day"), precision_by_year_rows(action_panel, "episode")], ignore_index=True)
    returns_stock = forward_return_stats(action_panel, config, "stock_day")
    returns_episode = forward_return_stats(action_panel, config, "episode")
    returns_all = pd.concat([returns_stock, returns_episode], ignore_index=True)
    background = background_prior_audit(action_panel)
    missing = missingness_audit(action_panel, config)
    overlap = overlap_matrix(action_panel)
    redundancy_long, phi_matrix, jaccard_matrix = signal_redundancy(action_panel)
    incremental = signal_incremental_precision(action_panel)
    top4_audit, top4_combined, top4_manifest = top4_independent_combined_precision(action_panel, redundancy_long)
    decision_audit, decision = decision_gate_audit(precision_all, returns_all, config)

    background_base_cols = [
        "instrument_id",
        "trade_date",
        "split",
        "year",
        "condition_group_id",
        "family_id",
        "base_action_time_eligible_flag",
        "feature_complete_flag",
        "signal_occurs",
        "complete_h120_flag",
        "close_t",
        "forward_close_peak_h120_return_from_close",
        "big_winner_forward_from_signal_close",
    ]
    background_global = action_panel[background_base_cols].copy()
    background_global["background_denominator_role"] = "global"
    background_feature_matched = action_panel.loc[action_panel["feature_complete_flag"].astype(bool), background_base_cols].copy()
    background_feature_matched["background_denominator_role"] = "feature_matched"
    background_panel = pd.concat([background_global, background_feature_matched], ignore_index=True)

    _write_parquet(action_panel, cache_dir / "r02_family_action_time_panel.parquet")
    _write_parquet(background_panel, cache_dir / "r02_family_background_prior_panel.parquet")
    write_csv(precision_all, reports_dir / "r02_family_precision_summary.csv")
    write_csv(precision_all.loc[precision_all["split"].isin(SPLITS)], reports_dir / "r02_family_precision_by_split.csv")
    write_csv(precision_year, reports_dir / "r02_family_precision_by_year.csv")
    write_csv(returns_all, reports_dir / "r02_family_forward_return_stats.csv")
    write_csv(returns_all.loc[returns_all["split"].isin(SPLITS)], reports_dir / "r02_family_forward_return_stats_by_split.csv")
    write_csv(precision_episode, reports_dir / "r02_family_episode_precision_summary.csv")
    write_csv(returns_episode, reports_dir / "r02_family_episode_forward_return_stats.csv")
    write_csv(overlap, reports_dir / "r02_family_signal_overlap_matrix.csv")
    write_csv(redundancy_long, reports_dir / "r02_family_signal_redundancy_long.csv")
    write_csv(phi_matrix, reports_dir / "r02_family_signal_phi_correlation_matrix.csv")
    write_csv(jaccard_matrix, reports_dir / "r02_family_signal_jaccard_matrix.csv")
    write_csv(incremental, reports_dir / "r02_family_signal_incremental_precision.csv")
    write_csv(top4_audit, reports_dir / "r02_family_top4_independence_selection_audit.csv")
    write_csv(top4_combined, reports_dir / "r02_family_top4_combined_precision.csv")
    write_csv(missing, reports_dir / "r02_family_missingness_audit.csv")
    write_csv(background, reports_dir / "r02_family_background_prior_audit.csv")
    write_csv(decision_audit, reports_dir / "r02_family_decision_gate_audit.csv")

    upstream_manifest_path = topic_path(config["upstream_r02_coverage"]["manifest"])
    upstream_manifest = json.loads(upstream_manifest_path.read_text(encoding="utf-8"))
    base_counts = action_panel.groupby("condition_group_id").size().astype(int).to_dict()
    signal_counts = action_panel.loc[action_panel["signal_occurs"].astype(bool)].groupby("condition_group_id").size().astype(int).to_dict()
    episode_counts = action_panel.loc[action_panel["is_episode_start"].astype(bool)].groupby("condition_group_id").size().astype(int).to_dict()
    matched_counts = (
        action_panel.loc[action_panel["feature_complete_flag"].astype(bool) & action_panel["complete_h120_flag"].astype(bool)]
        .groupby("condition_group_id")
        .size()
        .astype(int)
        .to_dict()
    )
    manifest = {
        "phase": config["phase"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement_path": config["requirement_path"],
        "config_path": relpath(topic_path(config_path)),
        "config_hash": _hash_file(topic_path(config_path)),
        "output_root": relpath(output_root),
        "upstream_r02_manifest_path": relpath(upstream_manifest_path),
        "upstream_r02_manifest_hash": _hash_file(upstream_manifest_path),
        "upstream_parallel_result_hash": upstream_manifest.get("parallel_result_hash"),
        "frozen_condition_group_count": int(len(config["frozen_conditions"])),
        "eligible_stock_day_count": int(next(iter(base_counts.values())) if base_counts else 0),
        "signal_stock_day_count_by_condition": signal_counts,
        "episode_count_by_condition": episode_counts,
        "base_action_time_row_count_by_condition": base_counts,
        "feature_matched_background_row_count_by_condition": matched_counts,
        "split_policy": config["split_policy"],
        "price_anchor_policy": config["price_anchor_policy"],
        "horizons": [int(v) for v in config["horizons"]],
        "forward_label_horizon": int(config["forward_label_horizon"]),
        "decision_grain": config["decision"]["decision_grain"],
        "decision_min_lift_validation": float(config["decision"]["min_lift_validation"]),
        "decision_min_lift_robustness": float(config["decision"]["min_lift_robustness"]),
        "decision_min_positive_h120_count": int(config["decision"]["min_positive_h120_count"]),
        "decision_min_signal_count": int(config["decision"]["min_signal_count"]),
        "bootstrap_iterations": int(config["bootstrap"]["iterations"]),
        "bootstrap_random_seed": int(config["bootstrap"]["random_seed"]),
        "bootstrap_resample_unit": config["bootstrap"]["resample_unit"],
        "bootstrap_confidence_level": float(config["bootstrap"]["confidence_level"]),
        "bootstrap_sample_count_by_split_condition": bootstrap_sample_counts,
        **top4_manifest,
        "final_decision": decision,
    }
    write_report(
        reports_dir,
        precision_stock,
        returns_stock,
        precision_episode,
        redundancy_long,
        incremental,
        top4_audit,
        top4_combined,
        decision_audit,
        manifest,
        decision,
    )
    write_json(manifest, manifests_dir / "r02_family_precision_forward_return_stats_manifest.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EP4 R02 family precision and forward-return statistics.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    manifest = run(Path(args.config))
    print(json.dumps(manifest, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

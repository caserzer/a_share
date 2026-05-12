#!/usr/bin/env python3
from __future__ import annotations

import argparse
import multiprocessing as mp
import hashlib
import json
import math
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

import r01_high_recall_probe_fail_fast_common as r01  # noqa: E402
import ep2_common as base  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r02_evidence_family_discovery_v1.yaml"
SCHEMA_VERSION = "ep4_r02_evidence_family_discovery_v1"
ALLOWED_DECISIONS = {
    "go_to_r03_evidence_accumulation",
    "revise_family_search_space",
    "archive_family_discovery_no_r03",
}
SPLITS = ["train", "validation", "robustness"]
LABEL_IDS = [
    "continuation_h20",
    "continuation_h60",
    "big_winner_forward",
    "failed_seed_forward",
    "executable_entry_available",
]
REQUIRED_CACHE = [
    "r02_action_time_panel.parquet",
    "r02_primitive_event_panel.parquet",
    "r02_family_event_panel.parquet",
]
REQUIRED_REPORTS = [
    "r02_primitive_search_summary.csv",
    "r02_primitive_rejection_audit.csv",
    "r02_combo_search_summary.csv",
    "r02_family_cluster_matrix.csv",
    "r02_family_incremental_lift.csv",
    "r02_family_selection_summary.csv",
    "r02_family_validation_summary.csv",
    "r02_family_execution_diagnostics.csv",
    "r02_family_stability_by_year.csv",
    "r02_effective_window_audit.csv",
    "r02_label_confusion_matrix.csv",
    "r02_mandatory_v3_seed_baseline.csv",
    "r02_gate_audit.csv",
    "r02_final_report.md",
]
REQUIRED_MANIFESTS = ["r02_family_discovery_manifest.json"]
METRIC_COLUMNS = [
    "candidate_id",
    "candidate_type",
    "group_id",
    "raw_feature",
    "component_primitive_ids",
    "component_group_ids",
    "split",
    "trigger_count",
    "stock_day_density",
    "instrument_year_concentration",
    "primary_positive_count",
    "P_signal_given_winner",
    "P_signal_given_non_winner",
    "P_winner_given_signal",
    "LR",
    "primary_LR_ci90_lower",
    "primary_LR_ci90_upper",
    "log_lift",
    "EV_R",
    "avg_win_R",
    "avg_loss_R",
    "failed_seed_rate",
    "entry_buyability_rate",
    "risk_distance_ineligible_rate",
    "initial_risk_pct_p50",
    "delay_sensitivity",
]
COMBO_COLUMNS = METRIC_COLUMNS + [
    "combo_rank_score",
    "component_single_LR",
    "component_single_EV_R",
    "combo_incremental_LR_vs_best_component",
    "combo_incremental_EV_R_vs_best_component",
]
CLUSTER_COLUMNS = [
    "candidate_id_left",
    "candidate_id_right",
    "same_day_overlap",
    "same_day_jaccard",
    "within_5d_overlap",
    "binary_signal_correlation",
    "winner_conditional_overlap",
    "non_winner_conditional_overlap",
    "failed_episode_overlap",
    "shared_raw_feature_penalty",
    "incremental_status",
    "incremental_LR_after_selected_family",
    "incremental_EV_R_after_selected_family",
    "merge_status",
]
FAMILY_SELECTION_COLUMNS = COMBO_COLUMNS + [
    "status",
    "positive_LR_year_share",
    "non_negative_EV_R_year_share",
    "train_years_with_trigger_count_30",
    "stability_passed",
    "rank_score",
    "family_id",
    "r03_pool_status",
]
_WORKER_PANEL: pd.DataFrame | None = None
_WORKER_EVENTS: pd.DataFrame | None = None
_WORKER_CONFIG: dict[str, Any] | None = None


@dataclass(frozen=True)
class R02Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str, default_config: Path = DEFAULT_CONFIG) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(default_config))
    return parser.parse_args()


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def with_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty and len(df.columns) == 0:
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in df.columns:
            df[column] = np.nan
    return df


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(config_path: str | Path) -> tuple[dict[str, Any], R02Paths, dict[str, Any]]:
    cfg_path = topic_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    output_root = topic_path(config["output_root"])
    paths = R02Paths(
        config_path=cfg_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [paths.cache_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    with topic_path(config["upstream_ep2"]["config"]).open("r", encoding="utf-8") as file:
        ep2_config = yaml.safe_load(file) or {}
    return config, paths, ep2_config


def _date_str(value: Any) -> str:
    if pd.isna(value) or str(value) in {"", "NaT", "nan", "None"}:
        return ""
    return pd.Timestamp(value).date().isoformat()


def _safe_div(numer: float, denom: float, default: float = np.nan) -> float:
    return float(numer) / float(denom) if np.isfinite(numer) and np.isfinite(denom) and float(denom) != 0 else default


def _metric_bool(value: Any) -> bool:
    return bool(value) if pd.notna(value) else False


def _parallel_backend(config: dict[str, Any]) -> str:
    return str(config.get("runtime", {}).get("parallel_backend", "serial"))


def _effective_jobs(config: dict[str, Any], override: int | None = None) -> int:
    configured = int(config.get("runtime", {}).get("default_n_jobs", 1)) if override is None else int(override)
    max_jobs = int(config.get("runtime", {}).get("max_n_jobs", configured))
    return max(1, min(configured, max_jobs, os.cpu_count() or 1))


def _init_metric_worker(panel: pd.DataFrame, events: pd.DataFrame, config: dict[str, Any]) -> None:
    global _WORKER_PANEL, _WORKER_EVENTS, _WORKER_CONFIG
    _WORKER_PANEL = panel
    _WORKER_EVENTS = events
    _WORKER_CONFIG = config


def _metric_worker(task: tuple[dict[str, Any], str, bool]) -> dict[str, Any]:
    row, split, ci = task
    if _WORKER_PANEL is None or _WORKER_EVENTS is None or _WORKER_CONFIG is None:
        raise RuntimeError("metric worker was not initialized")
    return metric_for_candidate(_WORKER_PANEL, _WORKER_EVENTS, pd.Series(row), _WORKER_CONFIG, split=split, ci=ci)


def compute_candidate_metrics(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    meta: pd.DataFrame,
    config: dict[str, Any],
    *,
    split: str = "train",
    ci: bool = True,
    n_jobs: int = 1,
) -> pd.DataFrame:
    rows = [row._asdict() for row in meta.itertuples(index=False)]
    if not rows:
        return pd.DataFrame(columns=METRIC_COLUMNS)
    if n_jobs <= 1 or _parallel_backend(config) != "process_pool":
        return with_columns(
            pd.DataFrame([metric_for_candidate(panel, events, pd.Series(row), config, split=split, ci=ci) for row in rows]),
            METRIC_COLUMNS,
        )
    ctx = mp.get_context("fork")
    tasks = [(row, split, ci) for row in rows]
    with ctx.Pool(processes=min(n_jobs, len(tasks)), initializer=_init_metric_worker, initargs=(panel, events, config)) as pool:
        result = pool.map(_metric_worker, tasks)
    return with_columns(pd.DataFrame(result), METRIC_COLUMNS)


def assert_authority_inputs(config: dict[str, Any]) -> pd.DataFrame:
    canonical = {
        "ep4_discussion2": "ep4/discussion2.md",
        "ep4_requirement": config["requirement_path"],
        "ep2_manifest": config["upstream_ep2"]["manifest"],
        "ep2_config": config["upstream_ep2"]["config"],
        "qlib_provider_uri": config["data_sources"]["qlib_provider_uri"],
        "trading_calendar": config["data_sources"]["trading_calendar_path"],
        "pit_universe": config["data_sources"]["pit_universe_path"],
        "pit_qlib_instrument_universe": config["data_sources"]["pit_qlib_instrument_universe_path"],
        "pit_industry": config["data_sources"]["pit_industry_path"],
        "qlib_instrument_path": config["data_sources"]["qlib_instrument_path"],
    }
    rows = []
    for name, value in canonical.items():
        path = topic_path(value)
        rows.append(
            {
                "artifact_name": name,
                "path": relpath(path),
                "exists": path.exists(),
                "sha256": file_hash(path) if path.is_file() else "",
                "status": "passed" if path.exists() else "failed",
            }
        )
    authority = pd.DataFrame(rows)
    if not bool(authority["exists"].all()):
        missing = "; ".join(authority.loc[~authority["exists"], "path"].astype(str).tolist())
        raise RuntimeError(f"missing R02 authority inputs: {missing}")
    manifest = json.loads(topic_path(config["upstream_ep2"]["manifest"]).read_text(encoding="utf-8"))
    if manifest.get("validation_status") != "passed":
        raise RuntimeError("EP2 engineering baseline manifest is not passed")
    return authority


def split_bounds(config: dict[str, Any]) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    split = config["split"]
    return {
        "train": (pd.Timestamp(split["train_start"]), pd.Timestamp(split["train_end"])),
        "validation": (pd.Timestamp(split["validation_start"]), pd.Timestamp(split["validation_end"])),
        "robustness": (pd.Timestamp(split["robustness_start"]), pd.Timestamp(split["robustness_end"])),
    }


def build_stock_panel(config: dict[str, Any], ep2_config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    panel, calendar = r01.load_provider_spine(config, ep2_config)
    stock = r01.prepare_stock_day_panel(config, ep2_config, panel, calendar)
    group = stock.groupby("instrument", group_keys=False)
    stock["ret1d"] = group["close"].pct_change()
    stock["gap_open_pct"] = stock["open"] / group["close"].shift(1) - 1.0
    stock["rolling_close_high20_asof"] = group["close"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).max())
    stock["rolling_close_high60_asof"] = group["close"].transform(lambda s: s.shift(1).rolling(60, min_periods=60).max())
    stock["close_near_high5_pct"] = stock["close"] / stock["rolling_close_high5_asof"] - 1.0
    stock["close_near_high20_pct"] = stock["close"] / stock["rolling_close_high20_asof"] - 1.0
    stock["close_near_high60_pct"] = stock["close"] / stock["rolling_close_high60_asof"] - 1.0
    stock["ret20_asof"] = group["close"].transform(lambda s: s / s.shift(20) - 1.0)
    stock["rps20"] = np.nan
    stock["rps60"] = np.nan
    ranked = stock["split"].isin(SPLITS) & stock["pit_universe_member"].astype(bool) & stock["not_suspended_or_dirty_bar"].astype(bool)
    stock.loc[ranked & stock["ret20_asof"].notna(), "rps20"] = stock.loc[ranked & stock["ret20_asof"].notna()].groupby("date")["ret20_asof"].rank(pct=True)
    stock.loc[ranked & stock["ret60_asof"].notna(), "rps60"] = stock.loc[ranked & stock["ret60_asof"].notna()].groupby("date")["ret60_asof"].rank(pct=True)
    ema20 = group["close"].transform(lambda s: s.shift(1).ewm(span=20, adjust=False, min_periods=20).mean())
    stock["ema20_asof"] = ema20
    stock["ema20_hold_depth"] = np.where(stock["low"] >= ema20, 0.0, ema20 / stock["low"] - 1.0)
    stock["prior20_high_asof"] = group["high"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).max())
    stock["prior20_pullback_depth"] = stock["close"] / stock["prior20_high_asof"] - 1.0
    stock["prior20_pullback_depth"] = stock["prior20_pullback_depth"].abs()
    stock["prior10_low_excl_today"] = group["low"].transform(lambda s: s.shift(1).rolling(10, min_periods=10).min())
    stock["prior20_low_excl_today"] = group["low"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).min())
    stock["past_h10_no_close_below_prior10_low"] = group["close"].transform(lambda s: s.shift(1).rolling(10, min_periods=10).min()) > stock["prior10_low_excl_today"]
    stock["past_h20_no_close_below_prior20_low"] = group["close"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).min()) > stock["prior20_low_excl_today"]
    stock["atr20_pct"] = stock["atr20_pct_asof"]
    stock["atr20_pct_60d_median_asof"] = group["atr20_pct_asof"].transform(lambda s: s.shift(1).rolling(60, min_periods=40).median())
    stock["atr20_contraction_ratio"] = stock["atr20_pct_asof"] / stock["atr20_pct_60d_median_asof"]
    stock["down_day_high_volume"] = (stock["close"] < group["close"].shift(1)) & (stock["vol_ratio10"] > 1.5)
    stock["past_h20_no_high_volume_down_day"] = ~group["down_day_high_volume"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).max()).fillna(False).astype(bool)
    stock["failed_breakout_day"] = (stock["high"] >= stock["rolling_close_high20_asof"]) & (stock["close"] < stock["rolling_close_high20_asof"])
    stock["past_h10_no_failed_breakout"] = ~group["failed_breakout_day"].transform(lambda s: s.shift(1).rolling(10, min_periods=10).max()).fillna(False).astype(bool)
    stock["above_ma20"] = stock["close"] > group["close"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
    stock["market_breadth20"] = stock.groupby("date")["above_ma20"].transform("mean")
    industry_keys = stock["industry_name"].fillna("UNKNOWN").astype(str)
    stock["industry_breadth20"] = stock.assign(_industry=industry_keys).groupby(["date", "_industry"])["above_ma20"].transform("mean")
    return stock, calendar


def _forward_shift(group: pd.core.groupby.generic.DataFrameGroupBy, column: str, periods: int) -> pd.Series:
    return group[column].shift(-periods)


def build_action_time_panel(stock: pd.DataFrame, config: dict[str, Any], calendar: pd.DatetimeIndex, ep2_config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = config["labels"]["horizons"]
    max_horizon = max(int(v) for v in labels.values())
    group = stock.groupby("instrument", group_keys=False)
    df = stock.copy()
    for horizon in [1, 10, 20, 60, 120]:
        df[f"close_h{horizon}"] = _forward_shift(group, "close", horizon)
    for horizon in [10, 20, 60, 120]:
        shifted = pd.concat([group["close"].shift(-i).rename(str(i)) for i in range(1, horizon + 1)], axis=1)
        df[f"forward_close_peak_h{horizon}"] = shifted.max(axis=1)
        df[f"forward_close_min_h{horizon}"] = shifted.min(axis=1)
    df["signal_day_low"] = df["low"]
    df["prior_10d_low"] = df["prior10_low_excl_today"]
    df["prior_20d_low"] = df["prior20_low_excl_today"]
    min_risk = float(config["execution"]["min_initial_risk_pct"])
    max_risk = float(config["execution"]["max_initial_risk_pct"])
    entry = df["next_open"].astype(float)
    stops = df[["signal_day_low", "prior_10d_low", "prior_20d_low"]].astype(float)
    risk = (entry.values[:, None] - stops.values) / entry.values[:, None]
    below_entry = (stops.values < entry.values[:, None]) & np.isfinite(risk)
    stop_values = np.where(below_entry, stops.values, np.nan)
    df["initial_structural_stop"] = np.nanmax(stop_values, axis=1)
    df["initial_risk_pct"] = (entry - df["initial_structural_stop"]) / entry
    has_any_stop_below = below_entry.any(axis=1)
    df["risk_distance_status"] = np.select(
        [
            ~has_any_stop_below,
            df["initial_risk_pct"].isna() & has_any_stop_below,
            df["initial_risk_pct"] < min_risk,
            df["initial_risk_pct"] > max_risk,
        ],
        ["no_valid_stop_below_entry", "risk_distance_outside_bounds", "risk_distance_below_min", "risk_distance_above_max"],
        default="passed",
    )
    df["entry_execution_status"] = np.where(df["is_buy_executable_next_open"].astype(bool), "entry_execution_available", "entry_execution_unavailable")
    df["execution_eligible"] = df["entry_execution_status"].eq("entry_execution_available") & df["risk_distance_status"].eq("passed")
    calendar_pos = df["calendar_pos"].astype("Int64")
    data_max_pos = int(pd.Series(calendar_pos.dropna().astype(int)).max())
    bounds = split_bounds(config)
    for label_id, horizon in labels.items():
        horizon = int(horizon)
        df[f"{label_id}_complete_forward_window"] = False
        df[f"{label_id}_effective_label_end"] = ""
        for split, (_, split_end) in bounds.items():
            split_end_pos = int(calendar.searchsorted(split_end, side="right") - 1)
            pos_limit = min(split_end_pos, data_max_pos) - horizon
            split_mask = df["split"].eq(split) & calendar_pos.notna()
            df.loc[split_mask, f"{label_id}_complete_forward_window"] = calendar_pos.loc[split_mask].astype(int) <= pos_limit
            effective_end = pd.Timestamp(calendar[pos_limit]) if 0 <= pos_limit < len(calendar) else pd.NaT
            df.loc[split_mask, f"{label_id}_effective_label_end"] = _date_str(effective_end)
    df["continuation_h20"] = (
        (df["close_h20"] / df["next_open"] - 1.0 >= 0.10)
        & (df["forward_close_min_h20"] / df["next_open"] - 1.0 > -0.06)
    )
    df["continuation_h60"] = (
        (df["close_h60"] / df["next_open"] - 1.0 >= 0.20)
        & (df["forward_close_peak_h60"] / df["next_open"] - 1.0 >= 0.30)
    )
    df["big_winner_forward"] = df["forward_close_peak_h120"] / df["next_open"] - 1.0 >= 0.50
    df["failed_seed_forward"] = df["forward_close_min_h10"] / df["next_open"] - 1.0 <= -0.06
    df["executable_entry_available"] = df["execution_eligible"]
    rates = base.cost_rates(ep2_config)
    terminal = int(config["execution"]["terminal_horizon_trading_days"])
    ff_window = int(config["execution"]["fail_fast_window_trading_days"])
    ff_drawdown = float(config["execution"]["fail_fast_drawdown_pct"])
    ff_cols = pd.concat([group["close"].shift(-i).rename(str(i)) for i in range(1, ff_window + 1)], axis=1)
    ff_hit = ff_cols.le(df["next_open"] * (1.0 - ff_drawdown), axis=0)
    first_ff_offset = ff_hit.apply(lambda row: int(row.idxmax()) if row.any() else terminal, axis=1)
    exit_price = pd.Series(np.nan, index=df.index, dtype=float)
    for offset in sorted(first_ff_offset.dropna().unique()):
        offset_int = int(offset)
        exit_price.loc[first_ff_offset.eq(offset_int)] = group["close"].shift(-offset_int).loc[first_ff_offset.eq(offset_int)]
    after_cost = (exit_price * (1.0 - rates["sell_total"])) / (df["next_open"] * (1.0 + rates["buy_total"])) - 1.0
    df["diagnostic_exit_offset"] = first_ff_offset
    df["diagnostic_exit_price"] = exit_price
    df["after_cost_return_pct"] = after_cost
    df["unit_return_R"] = after_cost / df["initial_risk_pct"]
    base_history = [
        "rolling_close_high5_asof",
        "rolling_close_high20_asof",
        "rolling_close_high60_asof",
        "volume_10d_mean_asof",
        "volume_3d_mean_asof",
        "money_20d_mean_asof",
        "rps5",
        "rps20",
        "rps60",
        "atr20_pct_asof",
        "prior10_low_excl_today",
        "prior20_low_excl_today",
    ]
    df["has_r02_required_history"] = df[base_history].notna().all(axis=1)
    df["r02_action_time_eligible"] = (
        df["split"].isin(SPLITS)
        & df["pit_universe_member"].astype(bool)
        & df["has_r02_required_history"].astype(bool)
        & df["not_suspended_or_dirty_bar"].astype(bool)
        & ~df["st_or_delist_risk"].astype(bool)
    )
    window_rows = []
    for split in SPLITS:
        split_rows = df["split"].eq(split) & df["r02_action_time_eligible"]
        for label_id in LABEL_IDS:
            complete = split_rows & df[f"{label_id}_complete_forward_window"].astype(bool)
            label_den = complete if label_id == "executable_entry_available" else complete & df["entry_execution_status"].ne("entry_execution_unavailable")
            effective_end = df.loc[split_rows, f"{label_id}_effective_label_end"].dropna().astype(str)
            effective_end_text = effective_end.iloc[0] if not effective_end.empty else ""
            window_rows.append(
                {
                    "split": split,
                    "label_id": label_id,
                    "raw_action_time_rows": int(split_rows.sum()),
                    "complete_forward_rows": int(label_den.sum()),
                    "incomplete_forward_rows": int((split_rows & ~df[f"{label_id}_complete_forward_window"].astype(bool)).sum()),
                    "entry_execution_unavailable_rows": int((split_rows & df["entry_execution_status"].eq("entry_execution_unavailable")).sum()),
                    "effective_label_end": effective_end_text,
                    "complete_forward_rate": _safe_div(float(label_den.sum()), float(split_rows.sum()), 0.0),
                }
            )
    keep_cols = [
        "instrument",
        "date",
        "split",
        "calendar_pos",
        "industry_name",
        "pit_universe_member",
        "not_suspended_or_dirty_bar",
        "st_or_delist_risk",
        "r02_action_time_eligible",
        "entry_execution_status",
        "execution_eligible",
        "risk_distance_status",
        "next_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "next_open",
        "initial_structural_stop",
        "initial_risk_pct",
        "after_cost_return_pct",
        "unit_return_R",
        "diagnostic_exit_offset",
    ]
    feature_cols = sorted({item["feature"] for item in config["primitive_search"]["primitive_grid"] if item["feature"] in df.columns})
    label_cols = []
    for label_id in LABEL_IDS:
        label_cols.extend([label_id, f"{label_id}_complete_forward_window", f"{label_id}_effective_label_end"])
    out = df.loc[df["split"].isin(SPLITS), keep_cols + feature_cols + label_cols].copy()
    out["trade_date"] = out["date"].map(_date_str)
    out["next_trade_date"] = out["next_date"].map(_date_str)
    out = out.drop(columns=["date", "next_date"]).sort_values(["instrument", "trade_date"]).reset_index(drop=True)
    return out, pd.DataFrame(window_rows)


def primitive_id(group: str, feature: str, operator: str, threshold: Any) -> str:
    text = str(threshold).replace("-", "m").replace(".", "p")
    op = {"==": "eq", ">=": "ge", ">": "gt", "<=": "le", "<": "lt"}[operator]
    return f"{group}__{feature}__{op}_{text}"


def evaluate_condition(series: pd.Series, operator: str, threshold: Any) -> pd.Series:
    if operator == ">":
        return series > float(threshold)
    if operator == ">=":
        return series >= float(threshold)
    if operator == "<":
        return series < float(threshold)
    if operator == "<=":
        return series <= float(threshold)
    if operator == "==":
        return series.astype(float) == float(threshold)
    raise ValueError(f"unsupported operator: {operator}")


def build_single_primitive_events(panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    event_frames = []
    base_mask = panel["r02_action_time_eligible"].astype(bool)
    for item in config["primitive_search"]["primitive_grid"]:
        feature = item["feature"]
        if feature not in panel.columns:
            continue
        for threshold in item["thresholds"]:
            pid = primitive_id(item["group"], feature, item["operator"], threshold)
            mask = base_mask & evaluate_condition(panel[feature], item["operator"], threshold).fillna(False)
            triggered = panel.loc[mask, ["instrument", "trade_date", "split"]].copy()
            triggered["candidate_id"] = pid
            triggered["candidate_type"] = "single_primitive"
            triggered["group_id"] = item["group"]
            triggered["raw_feature"] = feature
            triggered["component_primitive_ids"] = pid
            event_frames.append(triggered)
            rows.append(
                {
                    "candidate_id": pid,
                    "candidate_type": "single_primitive",
                    "group_id": item["group"],
                    "raw_feature": feature,
                    "operator": item["operator"],
                    "threshold": threshold,
                    "component_primitive_ids": pid,
                    "component_group_ids": item["group"],
                }
            )
    meta = pd.DataFrame(rows)
    events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame(columns=["instrument", "trade_date", "split", "candidate_id", "candidate_type", "group_id", "raw_feature", "component_primitive_ids"])
    return meta, events


def mandatory_baseline_events(panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_mask = panel["r02_action_time_eligible"].astype(bool)
    mask = (
        base_mask
        & panel["close_near_high5_pct"].ge(0.0).fillna(False)
        & panel["vol_ratio10"].gt(1.2).fillna(False)
        & panel["vol_ratio3"].gt(1.2).fillna(False)
        & panel["rps5"].gt(0.60).fillna(False)
    )
    cid = config["primitive_search"]["mandatory_composite_baseline_id"]
    meta = pd.DataFrame(
        [
            {
                "candidate_id": cid,
                "candidate_type": "mandatory_composite_baseline",
                "group_id": "post30_profile_momentum_state",
                "raw_feature": "close_near_high5_pct+vol_ratio10+vol_ratio3+rps5",
                "operator": "frozen_v3_formula",
                "threshold": "",
                "component_primitive_ids": "close_near_high5_gt_0pct;vol_ratio10_gt_1_2;vol_ratio3_gt_1_2;rps5_gt_60",
                "component_group_ids": "price_momentum;volume_money;relative_strength",
            }
        ]
    )
    events = panel.loc[mask, ["instrument", "trade_date", "split"]].copy()
    events["candidate_id"] = cid
    events["candidate_type"] = "mandatory_composite_baseline"
    events["group_id"] = "post30_profile_momentum_state"
    events["raw_feature"] = "close_near_high5_pct+vol_ratio10+vol_ratio3+rps5"
    events["component_primitive_ids"] = meta["component_primitive_ids"].iloc[0]
    return meta, events


def _event_mask(panel: pd.DataFrame, events: pd.DataFrame, candidate_id: str) -> pd.Series:
    keys = set(zip(events.loc[events["candidate_id"].eq(candidate_id), "instrument"], events.loc[events["candidate_id"].eq(candidate_id), "trade_date"]))
    return pd.Series([key in keys for key in zip(panel["instrument"], panel["trade_date"])], index=panel.index)


def bootstrap_lr_ci(sub: pd.DataFrame, mask: pd.Series, label_col: str, rng_seed: int, replicates: int = 200) -> tuple[float, float]:
    eligible = sub[f"{label_col}_metric_eligible"].astype(bool)
    base_df = sub.loc[eligible, ["instrument", "year", label_col]].copy()
    base_df["signal"] = mask.loc[base_df.index].astype(bool).values
    if base_df.empty or base_df[label_col].nunique() < 2:
        return np.nan, np.nan
    base_df["instrument_year"] = base_df["instrument"].astype(str) + "_" + base_df["year"].astype(str)
    grouped = base_df.groupby("instrument_year", sort=True)
    counts = grouped.apply(
        lambda g: pd.Series(
            {
                "signal_winner": int((g["signal"] & g[label_col].astype(bool)).sum()),
                "signal_non_winner": int((g["signal"] & ~g[label_col].astype(bool)).sum()),
                "winner": int(g[label_col].astype(bool).sum()),
                "non_winner": int((~g[label_col].astype(bool)).sum()),
            }
        ),
        include_groups=False,
    )
    if counts.shape[0] < 2:
        return np.nan, np.nan
    arr = counts[["signal_winner", "signal_non_winner", "winner", "non_winner"]].to_numpy(dtype=float)
    rng = np.random.default_rng(rng_seed)
    values = []
    for _ in range(replicates):
        sample_idx = rng.integers(0, arr.shape[0], size=arr.shape[0])
        sample = arr[sample_idx].sum(axis=0)
        p_sig_w = _safe_div(sample[0], sample[2])
        p_sig_n = _safe_div(sample[1], sample[3])
        values.append(_safe_div(p_sig_w, p_sig_n))
    clean = np.array([v for v in values if np.isfinite(v)])
    if clean.size == 0:
        return np.nan, np.nan
    alpha = (1.0 - 0.90) / 2.0
    return float(np.quantile(clean, alpha)), float(np.quantile(clean, 1.0 - alpha))


def metric_for_candidate(panel: pd.DataFrame, events: pd.DataFrame, meta_row: pd.Series, config: dict[str, Any], split: str = "train", ci: bool = True) -> dict[str, Any]:
    label = config["labels"]["primary_selection_label_id"]
    sub = panel.loc[panel["split"].eq(split) & panel["r02_action_time_eligible"].astype(bool)].copy()
    signal = _event_mask(sub, events, str(meta_row["candidate_id"]))
    label_eligible = sub[f"{label}_metric_eligible"].astype(bool)
    winners = sub[label].astype(bool) & label_eligible
    non_winners = ~sub[label].astype(bool) & label_eligible
    trigger_count = int(signal.sum())
    primary_positive_count = int((signal & winners).sum())
    p_sig_winner = _safe_div(float((signal & winners).sum()), float(winners.sum()))
    p_sig_non = _safe_div(float((signal & non_winners).sum()), float(non_winners.sum()))
    lr = _safe_div(p_sig_winner, p_sig_non)
    p_winner_signal = _safe_div(float((signal & winners).sum()), float((signal & label_eligible).sum()))
    exec_signal = signal & sub["execution_eligible"].astype(bool)
    ev_r = float(sub.loc[exec_signal, "unit_return_R"].mean()) if exec_signal.any() else np.nan
    wins_r = sub.loc[exec_signal & sub["unit_return_R"].gt(0), "unit_return_R"]
    losses_r = sub.loc[exec_signal & sub["unit_return_R"].le(0), "unit_return_R"]
    buyability = _safe_div(float((signal & sub["entry_execution_status"].eq("entry_execution_available")).sum()), float(trigger_count), 0.0)
    risk_ineligible = _safe_div(float((signal & sub["entry_execution_status"].eq("entry_execution_available") & ~sub["execution_eligible"].astype(bool)).sum()), float(max(1, (signal & sub["entry_execution_status"].eq("entry_execution_available")).sum())), 0.0)
    ci_lower, ci_upper = bootstrap_lr_ci(sub, signal, label, int(config["primitive_search"]["bootstrap_random_seed"]), int(config["primitive_search"]["bootstrap_replicates"])) if ci else (np.nan, np.nan)
    years = sub.loc[signal, "trade_date"].str.slice(0, 4)
    concentration = float(years.value_counts(normalize=True).max()) if trigger_count > 0 else np.nan
    return {
        "candidate_id": meta_row["candidate_id"],
        "candidate_type": meta_row["candidate_type"],
        "group_id": meta_row["group_id"],
        "raw_feature": meta_row["raw_feature"],
        "component_primitive_ids": meta_row.get("component_primitive_ids", ""),
        "component_group_ids": meta_row.get("component_group_ids", ""),
        "split": split,
        "trigger_count": trigger_count,
        "stock_day_density": _safe_div(float(trigger_count), float(sub.shape[0]), 0.0),
        "instrument_year_concentration": concentration,
        "primary_positive_count": primary_positive_count,
        "P_signal_given_winner": p_sig_winner,
        "P_signal_given_non_winner": p_sig_non,
        "P_winner_given_signal": p_winner_signal,
        "LR": lr,
        "primary_LR_ci90_lower": ci_lower,
        "primary_LR_ci90_upper": ci_upper,
        "log_lift": math.log(lr) if np.isfinite(lr) and lr > 0 else np.nan,
        "EV_R": ev_r,
        "avg_win_R": float(wins_r.mean()) if not wins_r.empty else np.nan,
        "avg_loss_R": float(losses_r.mean()) if not losses_r.empty else np.nan,
        "failed_seed_rate": _safe_div(float((signal & sub["failed_seed_forward"].astype(bool)).sum()), float(trigger_count), np.nan),
        "entry_buyability_rate": buyability,
        "risk_distance_ineligible_rate": risk_ineligible,
        "initial_risk_pct_p50": float(sub.loc[exec_signal, "initial_risk_pct"].median()) if exec_signal.any() else np.nan,
        "delay_sensitivity": np.nan,
    }


def apply_metric_eligibility(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    for label in LABEL_IDS:
        complete = df[f"{label}_complete_forward_window"].astype(bool)
        if label == "executable_entry_available":
            df[f"{label}_metric_eligible"] = complete
        else:
            df[f"{label}_metric_eligible"] = complete & df["entry_execution_status"].ne("entry_execution_unavailable")
    df["year"] = df["trade_date"].str.slice(0, 4).astype(int)
    return df


def rejection_status(summary: pd.DataFrame, config: dict[str, Any], kind: str) -> pd.DataFrame:
    gates = config["early_rejection"]
    prefix = "single" if kind == "single_primitive" else "combo"
    rows = []
    for row in summary.itertuples(index=False):
        checks = {
            f"min_train_trigger_count_{prefix}": row.trigger_count >= gates[f"min_train_trigger_count_{prefix}"],
            f"min_train_primary_positive_count_{prefix}": row.primary_positive_count >= gates[f"min_train_primary_positive_count_{prefix}"],
            f"max_train_stock_day_density_{prefix}": row.stock_day_density <= gates[f"max_train_stock_day_density_{prefix}"],
            "min_train_primary_LR": np.isfinite(row.LR) and row.LR >= gates["min_train_primary_LR"],
            "min_train_primary_LR_ci90_lower": np.isfinite(row.primary_LR_ci90_lower) and row.primary_LR_ci90_lower >= gates["min_train_primary_LR_ci90_lower"],
            "min_train_EV_R": np.isfinite(row.EV_R) and row.EV_R >= gates["min_train_EV_R"],
            "min_train_entry_buyability_rate": row.entry_buyability_rate >= gates["min_train_entry_buyability_rate"],
            "max_train_risk_distance_ineligible_rate": row.risk_distance_ineligible_rate <= gates["max_train_risk_distance_ineligible_rate"],
        }
        failed = [name for name, ok in checks.items() if not ok]
        rows.append(
            {
                "candidate_id": row.candidate_id,
                "candidate_type": row.candidate_type,
                "status": "passed" if not failed else "rejected",
                "failed_rules": ";".join(failed),
                "concentration_warning": bool(np.isfinite(row.instrument_year_concentration) and row.instrument_year_concentration > 0.50),
            }
        )
    return pd.DataFrame(rows)


def build_combo_candidates(panel: pd.DataFrame, single_meta: pd.DataFrame, single_events: pd.DataFrame, single_summary: pd.DataFrame, rejection: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    passed_ids = rejection.loc[rejection["status"].eq("passed"), "candidate_id"].tolist()
    passed_meta = single_meta.loc[single_meta["candidate_id"].isin(passed_ids)].copy()
    masks = {cid: _event_mask(panel, single_events, cid) for cid in passed_meta["candidate_id"]}
    summary_by_id = single_summary.set_index("candidate_id")
    rows = []
    event_frames = []
    group_pair_counts: dict[str, int] = {}
    max_pair = int(config["primitive_search"]["group_pair_top_n"])
    max_total = int(config["primitive_search"]["max_total_approved_combos"])
    candidates = []
    for i, left in passed_meta.sort_values("candidate_id").iterrows():
        for _, right in passed_meta.sort_values("candidate_id").iterrows():
            if str(left["candidate_id"]) >= str(right["candidate_id"]):
                continue
            if left["group_id"] == right["group_id"] or left["raw_feature"] == right["raw_feature"]:
                continue
            combo_mask = masks[left["candidate_id"]] & masks[right["candidate_id"]]
            if not combo_mask.any():
                continue
            pair = "__".join(sorted([left["group_id"], right["group_id"]]))
            cid = f"combo2__{left['candidate_id']}__AND__{right['candidate_id']}"
            meta = pd.Series(
                {
                    "candidate_id": cid,
                    "candidate_type": "approved_2_primitive_and",
                    "group_id": pair,
                    "raw_feature": f"{left['raw_feature']}+{right['raw_feature']}",
                    "component_primitive_ids": f"{left['candidate_id']};{right['candidate_id']}",
                    "component_group_ids": f"{left['group_id']};{right['group_id']}",
                }
            )
            metrics = metric_for_candidate(panel, pd.DataFrame({"instrument": panel.loc[combo_mask, "instrument"], "trade_date": panel.loc[combo_mask, "trade_date"], "candidate_id": cid}), meta, config, ci=False)
            score = max(0.0, math.log(metrics["LR"])) * max(0.0, metrics["EV_R"] + 0.05) * math.sqrt(min(metrics["stock_day_density"], 0.02) / 0.02) if np.isfinite(metrics["LR"]) and metrics["LR"] > 0 and np.isfinite(metrics["EV_R"]) else 0.0
            candidates.append((score, metrics, meta, combo_mask, pair))
    candidates.sort(key=lambda item: (-item[0], -_nan_to_sort(item[1]["LR"]), -_nan_to_sort(item[1]["EV_R"]), -item[1]["stock_day_density"], item[1]["candidate_id"]))
    for score, metrics, meta, combo_mask, pair in candidates:
        if len(rows) >= max_total or group_pair_counts.get(pair, 0) >= max_pair:
            continue
        left_id, right_id = str(meta["component_primitive_ids"]).split(";")
        best_component = summary_by_id.loc[[left_id, right_id]]
        best_lr = float(best_component["LR"].max())
        best_ev = float(best_component["EV_R"].max())
        metrics["combo_rank_score"] = score
        metrics["component_single_LR"] = ";".join(best_component["LR"].map(lambda v: f"{v:.6g}").tolist())
        metrics["component_single_EV_R"] = ";".join(best_component["EV_R"].map(lambda v: f"{v:.6g}").tolist())
        metrics["combo_incremental_LR_vs_best_component"] = _safe_div(metrics["LR"], best_lr)
        metrics["combo_incremental_EV_R_vs_best_component"] = metrics["EV_R"] - best_ev if np.isfinite(metrics["EV_R"]) and np.isfinite(best_ev) else np.nan
        rows.append(metrics)
        group_pair_counts[pair] = group_pair_counts.get(pair, 0) + 1
        events = panel.loc[combo_mask & panel["r02_action_time_eligible"].astype(bool), ["instrument", "trade_date", "split"]].copy()
        events["candidate_id"] = meta["candidate_id"]
        events["candidate_type"] = "approved_2_primitive_and"
        events["group_id"] = meta["group_id"]
        events["raw_feature"] = meta["raw_feature"]
        events["component_primitive_ids"] = meta["component_primitive_ids"]
        event_frames.append(events)
    combo_summary = with_columns(pd.DataFrame(rows), COMBO_COLUMNS)
    if not combo_summary.empty:
        combo_summary = combo_summary.sort_values(["combo_rank_score", "LR", "EV_R", "stock_day_density", "candidate_id"], ascending=[False, False, False, False, True]).reset_index(drop=True)
    combo_events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame(columns=single_events.columns)
    return combo_summary, combo_events


def _nan_to_sort(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return -1e99
    return out if np.isfinite(out) else -1e99


def build_year_stability(panel: pd.DataFrame, events: pd.DataFrame, candidates: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    label = config["labels"]["primary_selection_label_id"]
    train = panel.loc[panel["split"].eq("train") & panel["r02_action_time_eligible"].astype(bool)].copy()
    for row in candidates.itertuples(index=False):
        signal = _event_mask(train, events, row.candidate_id)
        for year, sub in train.groupby("year"):
            sig = signal.loc[sub.index]
            eligible = sub[f"{label}_metric_eligible"].astype(bool)
            winners = sub[label].astype(bool) & eligible
            non = ~sub[label].astype(bool) & eligible
            p_w = _safe_div(float((sig & winners).sum()), float(winners.sum()))
            p_n = _safe_div(float((sig & non).sum()), float(non.sum()))
            lr = _safe_div(p_w, p_n)
            ev = float(sub.loc[sig & sub["execution_eligible"].astype(bool), "unit_return_R"].mean()) if sig.any() else np.nan
            rows.append(
                {
                    "candidate_id": row.candidate_id,
                    "candidate_type": row.candidate_type,
                    "year": int(year),
                    "trigger_count": int(sig.sum()),
                    "primary_LR": lr,
                    "EV_R": ev,
                    "positive_LR_year": bool(np.isfinite(lr) and lr > 1.0),
                    "non_negative_EV_R_year": bool(np.isfinite(ev) and ev >= 0.0),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    agg = out.groupby("candidate_id").agg(
        positive_LR_year_share=("positive_LR_year", "mean"),
        non_negative_EV_R_year_share=("non_negative_EV_R_year", "mean"),
        train_years_with_trigger_count_30=("trigger_count", lambda s: int((s >= 30).sum())),
    )
    out = out.merge(agg, on="candidate_id", how="left")
    return out


def pair_overlap(panel: pd.DataFrame, events: pd.DataFrame, a: str, b: str, config: dict[str, Any]) -> dict[str, Any]:
    sub = panel.loc[panel["r02_action_time_eligible"].astype(bool)].copy()
    ma = _event_mask(sub, events, a)
    mb = _event_mask(sub, events, b)
    union = ma | mb
    intersection = ma & mb
    label = config["labels"]["primary_selection_label_id"]
    eligible = sub[f"{label}_metric_eligible"].astype(bool)
    winners = sub[label].astype(bool) & eligible
    non_winners = ~sub[label].astype(bool) & eligible
    failed = sub["failed_seed_forward"].astype(bool) & sub["failed_seed_forward_metric_eligible"].astype(bool)
    same_day_j = _safe_div(float(intersection.sum()), float(union.sum()), 0.0)
    corr = float(np.corrcoef(ma.astype(int), mb.astype(int))[0, 1]) if ma.any() and mb.any() else np.nan
    # Conservative within-5d approximation: same instrument and candidate B within a five-day rolling window.
    b_dates = events.loc[events["candidate_id"].eq(b), ["instrument", "trade_date"]].copy()
    b_dates["trade_date"] = pd.to_datetime(b_dates["trade_date"])
    a_dates = events.loc[events["candidate_id"].eq(a), ["instrument", "trade_date"]].copy()
    a_dates["trade_date"] = pd.to_datetime(a_dates["trade_date"])
    within_hits = 0
    if not a_dates.empty and not b_dates.empty:
        b_by_inst = {inst: dates.sort_values().to_numpy() for inst, dates in b_dates.groupby("instrument")["trade_date"]}
        for inst, dt in zip(a_dates["instrument"], a_dates["trade_date"]):
            vals = b_by_inst.get(inst)
            if vals is None:
                continue
            deltas = np.abs((vals - np.datetime64(dt)).astype("timedelta64[D]").astype(int))
            within_hits += int((deltas <= 7).any())
    within = _safe_div(float(within_hits), float(max(1, len(a_dates))), 0.0)
    active = ma
    active_winners = winners & active
    active_non_winners = non_winners & active
    if int(active.sum()) < 100 or int(active_winners.sum()) == 0 or int(active_non_winners.sum()) == 0:
        incremental_status = "insufficient_conditional_sample"
        inc_lr = np.nan
        inc_ev = np.nan
    else:
        inc_lr = _safe_div(
            _safe_div(float((mb & active_winners).sum()), float(active_winners.sum())),
            _safe_div(float((mb & active_non_winners).sum()), float(active_non_winners.sum())),
        )
        inc_ev = sub.loc[active & mb & sub["execution_eligible"].astype(bool), "unit_return_R"].mean() - sub.loc[active & ~mb & sub["execution_eligible"].astype(bool), "unit_return_R"].mean()
        incremental_status = "computed"
    return {
        "candidate_id_left": a,
        "candidate_id_right": b,
        "same_day_overlap": int(intersection.sum()),
        "same_day_jaccard": same_day_j,
        "within_5d_overlap": within,
        "binary_signal_correlation": corr,
        "winner_conditional_overlap": _safe_div(float((intersection & winners).sum()), float((union & winners).sum()), np.nan),
        "non_winner_conditional_overlap": _safe_div(float((intersection & non_winners).sum()), float((union & non_winners).sum()), np.nan),
        "failed_episode_overlap": _safe_div(float((intersection & failed).sum()), float((union & failed).sum()), np.nan),
        "incremental_status": incremental_status,
        "incremental_LR_after_selected_family": inc_lr,
        "incremental_EV_R_after_selected_family": inc_ev,
    }


def select_families(panel: pd.DataFrame, events: pd.DataFrame, summary: pd.DataFrame, rejection: pd.DataFrame, stability: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    passed = summary.merge(rejection[["candidate_id", "status"]], on="candidate_id", how="left")
    passed = passed.loc[passed["status"].eq("passed") & passed["candidate_type"].ne("mandatory_composite_baseline")].copy()
    stability_agg = stability.groupby("candidate_id").agg(
        positive_LR_year_share=("positive_LR_year_share", "max"),
        non_negative_EV_R_year_share=("non_negative_EV_R_year_share", "max"),
        train_years_with_trigger_count_30=("train_years_with_trigger_count_30", "max"),
    )
    passed = passed.merge(stability_agg, on="candidate_id", how="left")
    st = config["stability"]
    passed["stability_passed"] = (
        (passed["positive_LR_year_share"] >= st["positive_LR_year_share_min"])
        & (passed["non_negative_EV_R_year_share"] >= st["non_negative_EV_R_year_share_min"])
        & (passed["train_years_with_trigger_count_30"] >= st["min_train_years_with_trigger_count_30"])
    )
    passed = passed.loc[passed["stability_passed"]].copy()
    passed["rank_score"] = (
        passed["LR"].map(lambda v: max(0.0, math.log(v)) if np.isfinite(v) and v > 0 else 0.0)
        * passed["EV_R"].map(lambda v: max(0.0, v + 0.05) if np.isfinite(v) else 0.0)
        * passed["stock_day_density"].map(lambda v: math.sqrt(min(v, 0.02) / 0.02) if np.isfinite(v) else 0.0)
    )
    passed = passed.sort_values(["rank_score", "LR", "EV_R", "stock_day_density", "candidate_id"], ascending=[False, False, False, False, True])
    selected = []
    cluster_rows = []
    incremental_rows = []
    cluster_id = 0
    for row in passed.itertuples(index=False):
        duplicate = False
        for chosen in selected:
            overlap = pair_overlap(panel, events, row.candidate_id, chosen["candidate_id"], config)
            shared_raw = str(row.raw_feature).split("+")[0] == str(chosen["raw_feature"]).split("+")[0]
            merge = (
                overlap["same_day_jaccard"] >= config["clustering"]["same_day_jaccard_merge"]
                or overlap["within_5d_overlap"] >= config["clustering"]["within_5d_overlap_merge"]
                or (
                    shared_raw
                    and (
                        overlap["incremental_status"] == "insufficient_conditional_sample"
                        or (
                            np.isfinite(overlap["incremental_LR_after_selected_family"])
                            and np.isfinite(overlap["incremental_EV_R_after_selected_family"])
                            and overlap["incremental_LR_after_selected_family"] < config["clustering"]["shared_raw_incremental_lr_min"]
                            and overlap["incremental_EV_R_after_selected_family"] <= config["clustering"]["shared_raw_incremental_ev_r_min"]
                        )
                    )
                )
            )
            cluster_rows.append(overlap | {"merge_status": "merged" if merge else "separate", "shared_raw_feature_penalty": shared_raw})
            if merge:
                duplicate = True
                break
        if duplicate:
            continue
        cluster_id += 1
        selected.append(row._asdict() | {"family_id": f"family_{cluster_id:02d}", "r03_pool_status": "candidate"})
        if len([s for s in selected if s["candidate_type"] != "mandatory_composite_baseline"]) >= int(config["clustering"]["target_family_count_max"]):
            break
    selected_df = pd.DataFrame(selected)
    if selected_df.empty:
        selected_df = pd.DataFrame(columns=FAMILY_SELECTION_COLUMNS)
    selected_ids = selected_df["candidate_id"].tolist() if "candidate_id" in selected_df else []
    for candidate_id in selected_ids:
        active = pd.Series(False, index=panel.index)
        for selected_id in selected_ids:
            if selected_id == candidate_id:
                break
            active |= _event_mask(panel, events, selected_id)
        cand = _event_mask(panel, events, candidate_id)
        label = config["labels"]["primary_selection_label_id"]
        sub = panel.loc[panel["split"].eq("train") & panel["r02_action_time_eligible"].astype(bool) & active].copy()
        if sub.shape[0] < 100:
            incremental_rows.append({"candidate_id": candidate_id, "incremental_status": "insufficient_conditional_sample", "incremental_LR_after_selected_family": np.nan, "incremental_EV_R_after_selected_family": np.nan})
            continue
        c = cand.loc[sub.index]
        eligible = sub[f"{label}_metric_eligible"].astype(bool)
        winners = sub[label].astype(bool) & eligible
        non = ~sub[label].astype(bool) & eligible
        lr = _safe_div(_safe_div(float((c & winners).sum()), float(winners.sum())), _safe_div(float((c & non).sum()), float(non.sum())))
        ev_yes = sub.loc[c & sub["execution_eligible"].astype(bool), "unit_return_R"].mean()
        ev_no = sub.loc[~c & sub["execution_eligible"].astype(bool), "unit_return_R"].mean()
        incremental_rows.append({"candidate_id": candidate_id, "incremental_status": "computed", "incremental_LR_after_selected_family": lr, "incremental_EV_R_after_selected_family": ev_yes - ev_no})
    cluster = with_columns(
        pd.DataFrame(cluster_rows),
        CLUSTER_COLUMNS,
    )
    incremental = with_columns(
        pd.DataFrame(incremental_rows),
        ["candidate_id", "incremental_status", "incremental_LR_after_selected_family", "incremental_EV_R_after_selected_family"],
    )
    return selected_df, cluster, incremental


def evaluate_families(panel: pd.DataFrame, events: pd.DataFrame, selected: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    validation_rows = []
    execution_rows = []
    family_event_frames = []
    if selected.empty:
        return (
            pd.DataFrame(columns=METRIC_COLUMNS + ["family_id", "r03_pool_status"]),
            pd.DataFrame(columns=["family_id", "candidate_id", "split", "trigger_count", "entry_buyability_rate", "execution_eligible_rate", "risk_distance_ineligible_rate", "initial_risk_pct_p25", "initial_risk_pct_p50", "initial_risk_pct_p75"]),
            pd.DataFrame(columns=["family_id", "candidate_id", "instrument", "trade_date", "split"]),
        )
    for row in selected.itertuples(index=False):
        cand_events = events.loc[events["candidate_id"].eq(row.candidate_id)].copy()
        cand_events["family_id"] = row.family_id
        family_event_frames.append(cand_events)
        for split in SPLITS:
            meta = pd.Series(row._asdict())
            metrics = metric_for_candidate(panel, events, meta, config, split=split, ci=False)
            for label in ["continuation_h20", "continuation_h60", "failed_seed_forward"]:
                sub = panel.loc[panel["split"].eq(split) & panel["r02_action_time_eligible"].astype(bool)].copy()
                sig = _event_mask(sub, events, row.candidate_id)
                eligible = sub[f"{label}_metric_eligible"].astype(bool)
                winners = sub[label].astype(bool) & eligible
                non = ~sub[label].astype(bool) & eligible
                metrics[f"{label}_LR"] = _safe_div(_safe_div(float((sig & winners).sum()), float(winners.sum())), _safe_div(float((sig & non).sum()), float(non.sum())))
            validation_rows.append(metrics | {"family_id": row.family_id, "r03_pool_status": row.r03_pool_status})
            sub = panel.loc[panel["split"].eq(split) & panel["r02_action_time_eligible"].astype(bool)].copy()
            sig = _event_mask(sub, events, row.candidate_id)
            execution_rows.append(
                {
                    "family_id": row.family_id,
                    "candidate_id": row.candidate_id,
                    "split": split,
                    "trigger_count": int(sig.sum()),
                    "entry_buyability_rate": _safe_div(float((sig & sub["entry_execution_status"].eq("entry_execution_available")).sum()), float(sig.sum()), 0.0),
                    "execution_eligible_rate": _safe_div(float((sig & sub["execution_eligible"].astype(bool)).sum()), float(sig.sum()), 0.0),
                    "risk_distance_ineligible_rate": _safe_div(float((sig & sub["entry_execution_status"].eq("entry_execution_available") & ~sub["execution_eligible"].astype(bool)).sum()), float(max(1, (sig & sub["entry_execution_status"].eq("entry_execution_available")).sum())), 0.0),
                    "initial_risk_pct_p25": float(sub.loc[sig & sub["execution_eligible"].astype(bool), "initial_risk_pct"].quantile(0.25)) if sig.any() else np.nan,
                    "initial_risk_pct_p50": float(sub.loc[sig & sub["execution_eligible"].astype(bool), "initial_risk_pct"].median()) if sig.any() else np.nan,
                    "initial_risk_pct_p75": float(sub.loc[sig & sub["execution_eligible"].astype(bool), "initial_risk_pct"].quantile(0.75)) if sig.any() else np.nan,
                }
            )
    family_events = pd.concat(family_event_frames, ignore_index=True) if family_event_frames else pd.DataFrame()
    return pd.DataFrame(validation_rows), pd.DataFrame(execution_rows), family_events


def build_label_confusion(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pairs = [
        ("continuation_h20", "continuation_h60"),
        ("continuation_h20", "failed_seed_forward"),
        ("continuation_h60", "failed_seed_forward"),
    ]
    for split in SPLITS:
        sub = panel.loc[panel["split"].eq(split) & panel["r02_action_time_eligible"].astype(bool)].copy()
        for left, right in pairs:
            eligible = sub[f"{left}_metric_eligible"].astype(bool) & sub[f"{right}_metric_eligible"].astype(bool)
            for lv in [False, True]:
                for rv in [False, True]:
                    rows.append(
                        {
                            "split": split,
                            "label_left": left,
                            "label_right": right,
                            "left_value": lv,
                            "right_value": rv,
                            "row_count": int((eligible & sub[left].astype(bool).eq(lv) & sub[right].astype(bool).eq(rv)).sum()),
                        }
                    )
    return pd.DataFrame(rows)


def build_decision(selection: pd.DataFrame, validation: pd.DataFrame, execution: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    rows = []
    pool = selection.loc[selection["candidate_type"].ne("mandatory_composite_baseline")].copy() if not selection.empty else pd.DataFrame()
    val = validation.loc[validation["split"].eq("validation")].copy() if not validation.empty else pd.DataFrame()
    rob = validation.loc[validation["split"].eq("robustness")].copy() if not validation.empty else pd.DataFrame()
    exec_val = execution.loc[execution["split"].eq("validation")].copy() if not execution.empty else pd.DataFrame()
    family_count = int(pool.shape[0])
    rows.append({"gate_id": "min_3_non_baseline_families", "actual": family_count, "expected": 3, "operator": ">=", "status": "passed" if family_count >= 3 else "failed", "failure_class": "research_gate"})
    val_ok = bool(not val.empty and val["LR"].gt(1.0).all())
    rows.append({"gate_id": "validation_primary_lr_gt_1", "actual": bool(val_ok), "expected": True, "operator": "==", "status": "passed" if val_ok else "failed", "failure_class": "research_gate"})
    val_ev_count = int(val["EV_R"].ge(0.0).sum()) if not val.empty else 0
    rows.append({"gate_id": "validation_at_least_2_ev_non_negative", "actual": val_ev_count, "expected": 2, "operator": ">=", "status": "passed" if val_ev_count >= 2 else "failed", "failure_class": "research_gate"})
    rob_lr_ok = bool(not rob.empty and rob["LR"].ge(1.0).all())
    rows.append({"gate_id": "robustness_lr_ge_1", "actual": bool(rob_lr_ok), "expected": True, "operator": "==", "status": "passed" if rob_lr_ok else "failed", "failure_class": "research_gate"})
    rob_ev_ok = bool(not rob.empty and rob["EV_R"].ge(-0.05).all())
    rows.append({"gate_id": "robustness_ev_ge_minus_005", "actual": bool(rob_ev_ok), "expected": True, "operator": "==", "status": "passed" if rob_ev_ok else "failed", "failure_class": "research_gate"})
    reverse = val["continuation_h20_LR"].gt(config["decision_gates"]["h20_positive_h60_reverse_h20_lr_min"]) & val["continuation_h60_LR"].lt(config["decision_gates"]["h20_positive_h60_reverse_h60_lr_max"]) if not val.empty else pd.Series(dtype=bool)
    reverse_ok = not bool(reverse.any())
    rows.append({"gate_id": "no_h20_positive_h60_reverse", "actual": bool(reverse_ok), "expected": True, "operator": "==", "status": "passed" if reverse_ok else "failed", "failure_class": "research_gate"})
    exec_ok = bool(not exec_val.empty and exec_val["entry_buyability_rate"].ge(0.30).all() and exec_val["risk_distance_ineligible_rate"].le(0.70).all())
    rows.append({"gate_id": "validation_execution_feasible", "actual": bool(exec_ok), "expected": True, "operator": "==", "status": "passed" if exec_ok else "failed", "failure_class": "research_gate"})
    gate = pd.DataFrame(rows)
    if gate["status"].eq("passed").all():
        decision = "go_to_r03_evidence_accumulation"
    elif family_count >= 1:
        decision = "revise_family_search_space"
    else:
        decision = "archive_family_discovery_no_r03"
    return gate, decision


def build_report(decision: str, primitive_summary: pd.DataFrame, combo_summary: pd.DataFrame, selection: pd.DataFrame, validation: pd.DataFrame, execution: pd.DataFrame, gate: pd.DataFrame, baseline: pd.DataFrame) -> str:
    lines = [
        "# EP4 R02 Evidence Family Discovery V1 Report",
        "",
        f"- Final decision: `{decision}`",
        "- Scope: action-time evidence family discovery only; no final entry/add/exit model and no portfolio simulation.",
        "- R02 generic `unit_return_R` uses the R02 lookback-low diagnostic stop and is not numerically comparable to R01 V3 `return_R`.",
        "",
        "## Search Summary",
        "",
        f"- Single primitives evaluated: {int(primitive_summary['candidate_type'].eq('single_primitive').sum()) if not primitive_summary.empty else 0}",
        f"- Approved combo rows reported: {int(combo_summary.shape[0]) if not combo_summary.empty else 0}",
        f"- Frozen non-baseline family count: {int(selection.shape[0]) if not selection.empty else 0}",
        "",
        "## Frozen Families",
        "",
        selection[[c for c in ["family_id", "candidate_id", "candidate_type", "group_id", "LR", "EV_R", "stock_day_density", "P_winner_given_signal", "r03_pool_status"] if c in selection.columns]].to_markdown(index=False) if not selection.empty else "_No frozen family passed selection._",
        "",
        "## Validation / Robustness",
        "",
        validation[[c for c in ["family_id", "candidate_id", "split", "LR", "EV_R", "continuation_h20_LR", "continuation_h60_LR", "failed_seed_rate", "entry_buyability_rate"] if c in validation.columns]].to_markdown(index=False) if not validation.empty else "_No validation rows._",
        "",
        "## Execution Feasibility",
        "",
        execution[[c for c in ["family_id", "candidate_id", "split", "trigger_count", "entry_buyability_rate", "execution_eligible_rate", "risk_distance_ineligible_rate", "initial_risk_pct_p50"] if c in execution.columns]].to_markdown(index=False) if not execution.empty else "_No execution diagnostics._",
        "",
        "## Mandatory V3 Seed Baseline",
        "",
        baseline.to_markdown(index=False) if not baseline.empty else "_Missing mandatory baseline._",
        "",
        "## Label Confusion / Overlap",
        "",
        "Detailed label confusion and family-overlap artifacts are written to `r02_label_confusion_matrix.csv` and `r02_family_cluster_matrix.csv`. The final decision does not use winner-anchored coverage as prior.",
        "",
        "## Interpretation Boundary",
        "",
        "Action-time prior is estimated from eligible stock-days. Posterior precision is `P_winner_given_signal`. Winner coverage diagnostics, EV_R, and execution feasibility are separate quantities and are not converted into a risk-budget mapping in R02 V1.",
        "",
        "## Gate Audit",
        "",
        gate.to_markdown(index=False),
    ]
    return "\n".join(lines) + "\n"


def run_discovery_from_panel(
    action_panel: pd.DataFrame,
    config: dict[str, Any],
    *,
    n_jobs: int,
) -> dict[str, pd.DataFrame | str]:
    single_meta, single_events = build_single_primitive_events(action_panel, config)
    baseline_meta, baseline_events = mandatory_baseline_events(action_panel, config)
    single_summary = compute_candidate_metrics(action_panel, single_events, single_meta, config, split="train", ci=True, n_jobs=n_jobs)
    single_rejection = rejection_status(single_summary, config, "single_primitive") if not single_summary.empty else pd.DataFrame()
    combo_summary, combo_events = build_combo_candidates(action_panel, single_meta, single_events, single_summary, single_rejection, config)
    if not combo_summary.empty:
        combo_meta = combo_summary[["candidate_id", "candidate_type", "group_id", "raw_feature", "component_primitive_ids", "component_group_ids"]].drop_duplicates("candidate_id")
        combo_summary = compute_candidate_metrics(action_panel, combo_events, combo_meta, config, split="train", ci=True, n_jobs=n_jobs).merge(
            combo_summary[["candidate_id", "combo_rank_score", "component_single_LR", "component_single_EV_R", "combo_incremental_LR_vs_best_component", "combo_incremental_EV_R_vs_best_component"]],
            on="candidate_id",
            how="left",
        )
        combo_summary = with_columns(combo_summary, COMBO_COLUMNS).sort_values(["combo_rank_score", "LR", "EV_R", "stock_day_density", "candidate_id"], ascending=[False, False, False, False, True]).reset_index(drop=True)
    combo_rejection = rejection_status(combo_summary, config, "approved_2_primitive_and") if not combo_summary.empty else pd.DataFrame(columns=["candidate_id", "candidate_type", "status", "failed_rules", "concentration_warning"])
    all_events = pd.concat([single_events, combo_events, baseline_events], ignore_index=True)
    baseline_train = compute_candidate_metrics(action_panel, baseline_events, baseline_meta, config, split="train", ci=True, n_jobs=1)
    baseline_by_split = with_columns(
        pd.concat(
            [compute_candidate_metrics(action_panel, baseline_events, baseline_meta, config, split=split, ci=(split == "train"), n_jobs=1) for split in SPLITS],
            ignore_index=True,
        ),
        METRIC_COLUMNS,
    )
    primitive_summary = with_columns(pd.concat([single_summary, combo_summary, baseline_train], ignore_index=True, sort=False), COMBO_COLUMNS)
    rejection = pd.concat([single_rejection, combo_rejection], ignore_index=True, sort=False)
    rejection = pd.concat(
        [
            rejection,
            pd.DataFrame(
                [
                    {
                        "candidate_id": baseline_train["candidate_id"].iloc[0],
                        "candidate_type": "mandatory_composite_baseline",
                        "status": "report_only",
                        "failed_rules": "",
                        "concentration_warning": False,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    family_candidate_summary = with_columns(pd.concat([single_summary, combo_summary], ignore_index=True, sort=False), COMBO_COLUMNS)
    stability = build_year_stability(action_panel, all_events, family_candidate_summary, config)
    selection, cluster_matrix, incremental = select_families(action_panel, all_events, family_candidate_summary, rejection, stability, config)
    selection = with_columns(selection, FAMILY_SELECTION_COLUMNS)
    validation, execution, family_events = evaluate_families(action_panel, all_events, selection, config)
    gate, decision = build_decision(selection, validation, execution, config)
    return {
        "single_meta": single_meta,
        "all_events": all_events,
        "primitive_summary": primitive_summary,
        "rejection": rejection,
        "combo_summary": combo_summary,
        "cluster_matrix": cluster_matrix,
        "incremental": incremental,
        "selection": selection,
        "validation": validation,
        "execution": execution,
        "family_events": family_events,
        "stability": stability,
        "baseline_report": baseline_by_split,
        "gate": gate,
        "decision": decision,
    }


def artifact_hashes(paths: R02Paths) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in REQUIRED_CACHE:
        out[name] = file_hash(paths.cache_dir / name)
    for name in REQUIRED_REPORTS:
        out[name] = file_hash(paths.reports_dir / name)
    return out


def run_r02(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths, ep2_config = load_config(config_path)
    authority = assert_authority_inputs(config)
    stock, calendar = build_stock_panel(config, ep2_config)
    action_panel, effective_window = build_action_time_panel(stock, config, calendar, ep2_config)
    action_panel = apply_metric_eligibility(action_panel)
    runtime = config["runtime"]
    configured_jobs = int(runtime["default_n_jobs"])
    effective_jobs = _effective_jobs(config)
    result = run_discovery_from_panel(action_panel, config, n_jobs=effective_jobs)
    smoke = run_discovery_from_panel(action_panel, config, n_jobs=1)
    single_meta = result["single_meta"]
    all_events = result["all_events"]
    primitive_summary = result["primitive_summary"]
    rejection = result["rejection"]
    combo_summary = result["combo_summary"]
    cluster_matrix = result["cluster_matrix"]
    incremental = result["incremental"]
    selection = result["selection"]
    validation = result["validation"]
    execution = result["execution"]
    family_events = result["family_events"]
    stability = result["stability"]
    baseline_report = result["baseline_report"]
    gate = result["gate"]
    decision = str(result["decision"])
    confusion = build_label_confusion(action_panel)
    report = build_report(decision, primitive_summary, combo_summary, selection, validation, execution, gate, baseline_report)
    deterministic_sort_keys = ["candidate_id", "LR desc", "EV_R desc", "stock_day_density desc"]
    smoke_selection_ids = selection["candidate_id"].tolist() if not selection.empty else []
    smoke_combo_top = combo_summary["candidate_id"].head(20).tolist() if not combo_summary.empty else []
    smoke_selection_ids_1 = smoke["selection"]["candidate_id"].tolist() if not smoke["selection"].empty else []
    smoke_combo_top_1 = smoke["combo_summary"]["candidate_id"].head(20).tolist() if not smoke["combo_summary"].empty else []

    write_parquet(action_panel, paths.cache_dir / "r02_action_time_panel.parquet")
    write_parquet(all_events.sort_values(["candidate_id", "instrument", "trade_date"]).reset_index(drop=True), paths.cache_dir / "r02_primitive_event_panel.parquet")
    write_parquet(family_events.sort_values(["family_id", "instrument", "trade_date"]).reset_index(drop=True) if not family_events.empty else family_events, paths.cache_dir / "r02_family_event_panel.parquet")
    write_csv(primitive_summary, paths.reports_dir / "r02_primitive_search_summary.csv")
    write_csv(rejection, paths.reports_dir / "r02_primitive_rejection_audit.csv")
    write_csv(combo_summary, paths.reports_dir / "r02_combo_search_summary.csv")
    write_csv(cluster_matrix, paths.reports_dir / "r02_family_cluster_matrix.csv")
    write_csv(incremental, paths.reports_dir / "r02_family_incremental_lift.csv")
    write_csv(selection, paths.reports_dir / "r02_family_selection_summary.csv")
    write_csv(validation, paths.reports_dir / "r02_family_validation_summary.csv")
    write_csv(execution, paths.reports_dir / "r02_family_execution_diagnostics.csv")
    write_csv(stability, paths.reports_dir / "r02_family_stability_by_year.csv")
    write_csv(effective_window, paths.reports_dir / "r02_effective_window_audit.csv")
    write_csv(confusion, paths.reports_dir / "r02_label_confusion_matrix.csv")
    write_csv(baseline_report, paths.reports_dir / "r02_mandatory_v3_seed_baseline.csv")
    write_csv(gate, paths.reports_dir / "r02_gate_audit.csv")
    (paths.reports_dir / "r02_final_report.md").write_text(report, encoding="utf-8")

    manifest = {
        "phase": config["phase"],
        "schema_version": SCHEMA_VERSION,
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "output_root": relpath(paths.output_root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_decision": decision,
        "primary_selection_label_id": config["labels"]["primary_selection_label_id"],
        "configured_n_jobs": configured_jobs,
        "effective_n_jobs": effective_jobs,
        "parallel_backend": runtime["parallel_backend"],
        "random_seed": int(runtime["random_seed"]),
        "deterministic_sort_keys": deterministic_sort_keys,
        "deterministic_smoke": {
            "effective_n_jobs_1_selected_family_ids": smoke_selection_ids_1,
            "configured_run_selected_family_ids": smoke_selection_ids,
            "effective_n_jobs_1_combo_top20": smoke_combo_top_1,
            "configured_run_combo_top20": smoke_combo_top,
            "final_decision": decision,
            "effective_n_jobs_1_final_decision": smoke["decision"],
            "configured_run_final_decision": decision,
            "status": "passed" if smoke_selection_ids_1 == smoke_selection_ids and smoke_combo_top_1 == smoke_combo_top and smoke["decision"] == decision else "failed",
        },
        "action_time_rows": int(action_panel.shape[0]),
        "eligible_action_time_rows": int(action_panel["r02_action_time_eligible"].sum()),
        "primitive_candidate_count": int(single_meta.shape[0]),
        "combo_candidate_count": int(combo_summary.shape[0]),
        "frozen_family_count": int(selection.shape[0]),
        "artifact_hashes": {},
    }
    write_json(manifest, paths.manifests_dir / "r02_family_discovery_manifest.json")
    manifest["artifact_hashes"] = artifact_hashes(paths)
    write_json(manifest, paths.manifests_dir / "r02_family_discovery_manifest.json")
    return {
        "output_root": relpath(paths.output_root),
        "final_decision": decision,
        "eligible_action_time_rows": int(action_panel["r02_action_time_eligible"].sum()),
        "primitive_candidate_count": int(single_meta.shape[0]),
        "combo_candidate_count": int(combo_summary.shape[0]),
        "frozen_family_count": int(selection.shape[0]),
        "failed_gate_count": int(gate["status"].eq("failed").sum()),
    }


def validate_r02(config_path: str | Path = DEFAULT_CONFIG, fail_on_research_gates: bool = False) -> dict[str, Any]:
    config, paths, ep2_config = load_config(config_path)
    failures: list[str] = []
    required = [paths.cache_dir / name for name in REQUIRED_CACHE] + [paths.reports_dir / name for name in REQUIRED_REPORTS] + [paths.manifests_dir / name for name in REQUIRED_MANIFESTS]
    missing = [relpath(path) for path in required if not path.exists()]
    if missing:
        failures.append("missing required artifacts: " + "; ".join(missing))
    if failures:
        raise RuntimeError("; ".join(failures))
    manifest = json.loads((paths.manifests_dir / "r02_family_discovery_manifest.json").read_text(encoding="utf-8"))
    action = pd.read_parquet(paths.cache_dir / "r02_action_time_panel.parquet")
    primitive_events = pd.read_parquet(paths.cache_dir / "r02_primitive_event_panel.parquet")
    selection = pd.read_csv(paths.reports_dir / "r02_family_selection_summary.csv")
    primitive_summary = pd.read_csv(paths.reports_dir / "r02_primitive_search_summary.csv")
    rejection = pd.read_csv(paths.reports_dir / "r02_primitive_rejection_audit.csv")
    combo = pd.read_csv(paths.reports_dir / "r02_combo_search_summary.csv")
    effective = pd.read_csv(paths.reports_dir / "r02_effective_window_audit.csv")
    confusion = pd.read_csv(paths.reports_dir / "r02_label_confusion_matrix.csv")
    baseline = pd.read_csv(paths.reports_dir / "r02_mandatory_v3_seed_baseline.csv")
    gate = pd.read_csv(paths.reports_dir / "r02_gate_audit.csv")
    if manifest.get("final_decision") not in ALLOWED_DECISIONS:
        failures.append("final decision is outside allowed enum")
    if manifest.get("primary_selection_label_id") != config["labels"]["primary_selection_label_id"]:
        failures.append("manifest primary label mismatch")
    if not bool(action["r02_action_time_eligible"].any()):
        failures.append("action-time denominator has no eligible rows")
    cost_model = ep2_config.get("cost_model", {})
    for key in ["commission_bps_buy", "commission_bps_sell", "stamp_tax_bps_sell", "slippage_bps_buy", "slippage_bps_sell"]:
        if key not in cost_model:
            failures.append(f"missing cost model field: {key}")
    for label in LABEL_IDS:
        if f"{label}_complete_forward_window" not in action.columns or f"{label}_metric_eligible" not in action.columns:
            failures.append(f"missing label eligibility columns for {label}")
        if f"{label}_effective_label_end" not in action.columns:
            failures.append(f"missing effective label boundary column for {label}")
    for _, row in effective.iterrows():
        split = str(row["split"])
        label = str(row["label_id"])
        sub = action.loc[action["split"].eq(split) & action["r02_action_time_eligible"].astype(bool)]
        if sub.empty or label not in LABEL_IDS:
            continue
        complete = sub[f"{label}_complete_forward_window"].astype(bool)
        metric_eligible = sub[f"{label}_metric_eligible"].astype(bool)
        expected_metric = complete if label == "executable_entry_available" else complete & sub["entry_execution_status"].ne("entry_execution_unavailable")
        if int(row["raw_action_time_rows"]) != int(sub.shape[0]):
            failures.append(f"effective window raw rows mismatch for {split}/{label}")
        if int(row["complete_forward_rows"]) != int(expected_metric.sum()):
            failures.append(f"effective window complete rows mismatch for {split}/{label}")
        if int(row["incomplete_forward_rows"]) != int((~complete).sum()):
            failures.append(f"effective window incomplete rows mismatch for {split}/{label}")
        effective_end = str(row["effective_label_end"])
        if effective_end and metric_eligible.any() and pd.to_datetime(sub.loc[metric_eligible, "trade_date"]).max() > pd.Timestamp(effective_end):
            failures.append(f"metric eligible rows exceed effective_label_end for {split}/{label}")
    exec_rows = action.loc[
        action["r02_action_time_eligible"].astype(bool)
        & action["entry_execution_status"].eq("entry_execution_unavailable")
        & action["executable_entry_available_complete_forward_window"].astype(bool)
    ]
    if not exec_rows.empty and not exec_rows["executable_entry_available_metric_eligible"].all():
        failures.append("entry-unavailable rows must remain in executable_entry_available denominator")
    if effective.empty or not set(LABEL_IDS).issubset(set(effective["label_id"])):
        failures.append("effective window audit missing label rows")
    mandatory_id = config["primitive_search"]["mandatory_composite_baseline_id"]
    if baseline.empty or mandatory_id not in set(baseline["candidate_id"].astype(str)):
        failures.append("mandatory V3 seed baseline missing")
    expected_components = "close_near_high5_gt_0pct;vol_ratio10_gt_1_2;vol_ratio3_gt_1_2;rps5_gt_60"
    if not baseline.empty and not baseline["component_primitive_ids"].astype(str).eq(expected_components).any():
        failures.append("mandatory V3 seed baseline formula was rewritten")
    allowed_types = {"single_primitive", "approved_2_primitive_and", "mandatory_composite_baseline"}
    if not set(primitive_events["candidate_type"].dropna().astype(str)).issubset(allowed_types):
        failures.append("primitive event panel contains unsupported candidate_type")
    if not selection.empty and selection["candidate_type"].astype(str).eq("mandatory_composite_baseline").any():
        failures.append("mandatory V3 seed baseline must not be selected as frozen family")
    normal_combo = combo.loc[combo.get("candidate_type", pd.Series(dtype=str)).eq("approved_2_primitive_and")] if not combo.empty else combo
    if not normal_combo.empty:
        if normal_combo["component_primitive_ids"].astype(str).map(lambda v: len(v.split(";"))).gt(2).any():
            failures.append("approved combo has more than 2 components")
        if normal_combo.shape[0] > int(config["primitive_search"]["max_total_approved_combos"]):
            failures.append("approved combo total exceeds config cap")
        rejection_passed = set(rejection.loc[rejection["status"].eq("passed"), "candidate_id"].astype(str))
        for row in normal_combo.itertuples(index=False):
            components = str(row.component_primitive_ids).split(";")
            groups = str(row.component_group_ids).split(";")
            if len(set(groups)) != len(groups):
                failures.append(f"approved combo has duplicate component groups: {row.candidate_id}")
            if any(component not in rejection_passed for component in components):
                failures.append(f"approved combo uses component that did not pass single rejection: {row.candidate_id}")
    if not primitive_summary.empty and primitive_summary.loc[primitive_summary["candidate_id"].isin(selection.get("candidate_id", [])), "primary_LR_ci90_lower"].lt(1.0).any():
        failures.append("selected representative has primary_LR_ci90_lower < 1")
    if confusion.empty or confusion["row_count"].sum() <= 0:
        failures.append("label confusion matrix missing or empty")
    smoke = manifest.get("deterministic_smoke", {})
    if smoke.get("effective_n_jobs_1_selected_family_ids") != smoke.get("configured_run_selected_family_ids"):
        failures.append("deterministic smoke selected family ids mismatch")
    if smoke.get("effective_n_jobs_1_combo_top20") != smoke.get("configured_run_combo_top20"):
        failures.append("deterministic smoke combo top-k mismatch")
    if smoke.get("effective_n_jobs_1_final_decision") != smoke.get("configured_run_final_decision") or smoke.get("status") != "passed":
        failures.append("deterministic smoke final decision mismatch")
    if manifest.get("configured_n_jobs") is None or manifest.get("effective_n_jobs") is None or not manifest.get("deterministic_sort_keys"):
        failures.append("manifest missing runtime determinism fields")
    report_text = (paths.reports_dir / "r02_final_report.md").read_text(encoding="utf-8").lower()
    for token in ["action-time prior", "posterior precision", "ev_r", "execution feasibility", "label confusion", "not numerically comparable"]:
        if token not in report_text:
            failures.append(f"final report missing required distinction: {token}")
    research_failures = gate.loc[gate["status"].eq("failed"), "gate_id"].astype(str).tolist() if not gate.empty else []
    if fail_on_research_gates and research_failures:
        failures.append("research gates failed: " + "; ".join(research_failures))
    if failures:
        raise RuntimeError("; ".join(failures))
    return {
        "output_root": relpath(paths.output_root),
        "final_decision": manifest.get("final_decision"),
        "contract_validation_status": "passed",
        "research_failed_gate_count": len(research_failures),
        "research_failed_gates": research_failures,
        "required_artifact_count": len(required),
    }

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
BASELINE_SCRIPT_DIR = TOPIC_DIR / "ep2" / "engineering_baseline" / "scripts"
if str(BASELINE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(BASELINE_SCRIPT_DIR))

import ep2_common as base  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r01_high_recall_probe_fail_fast.yaml"
SCHEMA_VERSION = "ep4_r01_high_recall_probe_fail_fast_v1"
CANDIDATE_SEED_ID = "ep4_wide_seed_v0"
EP2_SEED_ID = "ep2_launch_detector_v0_bridge"
ALLOWED_DECISIONS = {
    "go_to_r02",
    "go_to_r02_with_robustness_warning",
    "archive_cost_control_sleeve_no_r02",
    "stop_ep4_r01_path",
}

REQUIRED_CACHE = [
    "r01_big_winner_reference_panel.parquet",
    "r01_seed_event_panel.parquet",
    "r01_seed_episode_panel.parquet",
    "r01_probe_simulation_panel.parquet",
    "r01_baseline_simulation_panel.parquet",
]
REQUIRED_REPORTS = [
    "r01_upstream_authority.csv",
    "r01_big_winner_reference_audit.csv",
    "r01_seed_density_audit.csv",
    "r01_density_cap_tightness_audit.csv",
    "r01_seed_recall_audit.csv",
    "r01_label_bridge_audit.csv",
    "r01_fail_fast_path_audit.csv",
    "r01_fail_fast_error_audit.csv",
    "r01_matched_control_bucket_freeze.csv",
    "r01_random_baseline_health_audit.csv",
    "r01_r_unit_distribution_audit.csv",
    "r01_baseline_diff_audit.csv",
    "r01_matched_delay_ineligible_audit.csv",
    "r01_recall_cost_tradeoff.csv",
    "r01_counterfactual_failure_inheritance.csv",
    "r01_gate_audit.csv",
    "r01_final_report.md",
]
REQUIRED_MANIFESTS = ["r01_run_manifest.json"]

BIG_WINNER_REFERENCE_COLUMNS = [
    "reference_event_id",
    "instrument",
    "reference_date",
    "entry_price_next_open",
    "forward_horizon_trading_days",
    "forward_peak_close",
    "forward_peak_date",
    "forward_return",
    "dedupe_gap_trading_days",
    "split",
    "eligibility_status",
    "ineligibility_reason",
]
SEED_EVENT_COLUMNS = [
    "seed_event_id",
    "seed_family_id",
    "instrument",
    "signal_date",
    "split",
    "close",
    "money",
    "price_structure_component",
    "close_near_60d_high_triggered",
    "close_breaks_40d_high_triggered",
    "rolling_high_60_asof",
    "rolling_high_40_asof",
    "component_trigger_threshold",
    "breakout_reference",
    "money_activity_ratio",
    "money_20d_median_asof",
    "atr20_asof",
    "atr20_pct_asof",
    "rs_rank_pct_audit",
    "pit_universe_member",
    "next_open_buy_executable",
    "buy_block_reason",
    "hard_filter_status",
    "reject_reason",
]
SEED_EPISODE_COLUMNS = [
    "seed_episode_id",
    "seed_family_id",
    "instrument",
    "episode_start_signal_date",
    "episode_effective_entry_date",
    "episode_end_signal_date",
    "split",
    "first_seed_event_id",
    "seed_event_count",
    "suppressed_reentry_count",
    "entry_price",
    "price_structure_component",
    "seed_day_low",
    "breakout_reference",
    "pivot_low_10d",
    "initial_structural_stop",
    "initial_risk_pct",
    "risk_distance_status",
    "executable_status",
    "episode_reject_reason",
    "primary_metric_eligible_seed_episode",
    "captures_primary_big_winner",
    "captured_reference_event_id",
    "capture_window_id",
    "captures_ep2_bridge_big_winner",
]
PROBE_SIM_COLUMNS = [
    "simulation_id",
    "seed_episode_id",
    "seed_family_id",
    "instrument",
    "entry_date",
    "entry_price",
    "initial_probe_risk_budget_r",
    "initial_structural_stop",
    "initial_risk_pct",
    "exit_trigger_type",
    "exit_signal_date",
    "exit_execution_date",
    "exit_price",
    "sell_blocked_day_count",
    "terminal_blocked_exit",
    "gross_return_pct",
    "after_cost_return_pct",
    "return_r",
    "loss_r",
    "holding_days",
    "exposure_days",
    "primary_metric_eligible_seed_episode",
    "failed_seed_primary",
    "failed_seed_label_a_h10_u1_5",
    "failed_seed_label_a_h20_u2_0",
    "failed_seed_h20_negative",
    "failed_seed_fail_fast_triggered",
    "split",
]
BASELINE_SIM_COLUMNS = [
    "baseline_simulation_id",
    "baseline_id",
    "replicate_id",
    "matched_control_type",
    "fail_fast_policy",
    "structural_reference_policy",
    "carried_price_structure_component",
    "carried_seed_episode_id",
    "seed_episode_id",
    "random_event_id",
    "instrument",
    "signal_date",
    "random_signal_date",
    "entry_date",
    "entry_price",
    "seed_day_low",
    "breakout_reference",
    "pivot_low_10d",
    "initial_structural_stop",
    "initial_risk_pct",
    "delay_days",
    "delay_period_return_pct",
    "delay_period_return_bucket",
    "matched_delay_reliability_status",
    "random_excluded_candidate_seed_day",
    "random_capacity_shortfall",
    "random_sampling_replacement_policy",
    "random_baseline_reliability_status",
    "primary_metric_eligible_baseline_event",
    "captures_primary_big_winner",
    "captured_reference_event_id",
    "capture_window_id",
    "baseline_failed_seed_primary",
    "exit_date",
    "exit_price",
    "eligibility_status",
    "ineligibility_reason",
    "gross_return_pct",
    "after_cost_return_pct",
    "return_r",
    "loss_r",
    "holding_days",
    "exposure_days",
    "split",
    "match_year",
    "match_industry",
    "match_liquidity_bucket",
    "match_volatility_bucket",
]


@dataclass(frozen=True)
class R01Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str, require_config: bool = False) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=None if require_config else str(DEFAULT_CONFIG))
    args = parser.parse_args()
    if require_config and not args.config:
        parser.error("--config is required")
    return args


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


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(config_path: str | Path) -> tuple[dict[str, Any], R01Paths, dict[str, Any]]:
    cfg_path = topic_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    output_root = topic_path(config["output_root"])
    paths = R01Paths(
        config_path=cfg_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [paths.cache_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    ep2_config_path = topic_path(config["upstream_ep2"]["config"])
    with ep2_config_path.open("r", encoding="utf-8") as file:
        ep2_config = yaml.safe_load(file) or {}
    return config, paths, ep2_config


def _date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def _date_str(value: Any) -> str:
    if pd.isna(value) or str(value) in {"", "NaT", "nan", "None"}:
        return ""
    return pd.Timestamp(value).date().isoformat()


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes", "passed"}
    return bool(value)


def _safe_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if np.isfinite(out) else default


def _safe_div(numer: float, denom: float, default: float = np.nan) -> float:
    return float(numer) / float(denom) if np.isfinite(numer) and np.isfinite(denom) and float(denom) != 0 else default


def split_bounds(config: dict[str, Any]) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    split = config["split"]
    return {
        "train": (_date(split["train_start"]), _date(split["train_end"])),
        "validation": (_date(split["validation_start"]), _date(split["validation_end"])),
        "robustness": (_date(split["robustness_start"]), _date(split["robustness_end"])),
    }


def assign_split(date: Any, bounds: dict[str, tuple[pd.Timestamp, pd.Timestamp]]) -> str:
    if pd.isna(date):
        return "out_of_scope"
    dt = _date(date)
    for split, (start, end) in bounds.items():
        if start <= dt <= end:
            return split
    return "out_of_scope"


def split_effective_windows(
    config: dict[str, Any], calendar: pd.DatetimeIndex, data_max_date: pd.Timestamp
) -> tuple[dict[str, tuple[pd.Timestamp, pd.Timestamp]], pd.Timestamp]:
    horizon = int(config["big_winner_reference"]["forward_horizon_trading_days"])
    data_max_pos = int(calendar.searchsorted(data_max_date, side="right") - 1)
    effective_pos = data_max_pos - horizon
    if effective_pos < 0:
        data_max_minus = pd.NaT
    else:
        data_max_minus = pd.Timestamp(calendar[effective_pos])
    windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for split, (start, end) in split_bounds(config).items():
        effective_end = min(end, data_max_minus) if not pd.isna(data_max_minus) else pd.NaT
        windows[split] = (start, effective_end)
    return windows, data_max_minus


def assert_authority_inputs(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    canonical = {
        "ep4_discussion": "ep4/discussion.md",
        "ep4_requirement": "ep4/requirement_01_high_recall_probe_fail_fast.md",
        "ep2_manifest": config["upstream_ep2"]["manifest"],
        "ep2_config": config["upstream_ep2"]["config"],
        "ep2_launch_pool": config["upstream_ep2"]["launch_pool"],
        "ep2_episode_dictionary": config["upstream_ep2"]["episode_dictionary"],
        "ep2_label_freeze_candidate": config["upstream_ep2"]["label_freeze_candidate"],
        "ep2_baseline_freeze_audit": config["upstream_ep2"]["baseline_freeze_audit"],
        "qlib_provider_uri": config["data_sources"]["qlib_provider_uri"],
        "trading_calendar": config["data_sources"]["trading_calendar_path"],
        "pit_universe": config["data_sources"]["pit_universe_path"],
        "pit_qlib_instrument_universe": config["data_sources"]["pit_qlib_instrument_universe_path"],
        "pit_industry": config["data_sources"]["pit_industry_path"],
        "qlib_instrument_path": config["data_sources"]["qlib_instrument_path"],
    }
    for name, value in canonical.items():
        path = topic_path(value)
        exists = path.exists()
        rows.append(
            {
                "artifact_name": name,
                "path": relpath(path),
                "exists": bool(exists),
                "sha256": file_hash(path) if exists and path.is_file() else "",
                "status": "passed" if exists else "failed",
            }
        )
    authority = pd.DataFrame(rows)
    if not bool(authority["exists"].all()):
        missing = "; ".join(authority.loc[~authority["exists"], "path"].astype(str).tolist())
        raise RuntimeError(f"missing canonical R01 inputs: {missing}")
    manifest = read_json(topic_path(config["upstream_ep2"]["manifest"]))
    if manifest.get("validation_status") != "passed":
        raise RuntimeError("EP2 engineering baseline manifest is not passed")
    return authority


def load_provider_spine(config: dict[str, Any], ep2_config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    provider_config = {
        "data_sources": config["data_sources"],
        "input_contract": {
            "required_min_date": config["split"]["train_start"],
            "required_max_date": config["split"]["robustness_end"],
            "provider_load_end_date": ep2_config.get("input_contract", {}).get("provider_load_end_date", "2026-04-30"),
        },
    }
    calendar = base.load_calendar(provider_config)
    provider = base.load_provider_panel(provider_config)
    universe = pd.read_csv(topic_path(config["data_sources"]["pit_universe_path"]), parse_dates=["date"])
    universe["date"] = pd.to_datetime(universe["date"]).dt.normalize()
    universe["instrument"] = universe["instrument"].astype(str).str.upper()
    keep_universe = [c for c in ["date", "instrument", "name"] if c in universe.columns]
    panel = provider.merge(
        universe[keep_universe].drop_duplicates(["date", "instrument"]).rename(columns={"date": "datetime"}),
        on=["datetime", "instrument"],
        how="left",
    )
    panel["pit_universe_member"] = panel["name"].notna() if "name" in panel.columns else False
    if "name" not in panel.columns:
        panel["name"] = ""
    industry = pd.read_csv(topic_path(config["data_sources"]["pit_industry_path"]), parse_dates=["date"])
    industry["date"] = pd.to_datetime(industry["date"]).dt.normalize()
    industry["instrument"] = industry["instrument"].astype(str).str.upper()
    industry_cols = [c for c in ["date", "instrument", "industry_target_key", "industry_name"] if c in industry.columns]
    panel = panel.merge(
        industry[industry_cols].drop_duplicates(["date", "instrument"]).rename(columns={"date": "datetime"}),
        on=["datetime", "instrument"],
        how="left",
    )
    panel["industry_name"] = panel.get("industry_name", pd.Series(index=panel.index, dtype=object)).fillna("UNKNOWN")
    panel = panel.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    return panel, calendar


def prepare_stock_day_panel(
    config: dict[str, Any], ep2_config: dict[str, Any], panel: pd.DataFrame, calendar: pd.DatetimeIndex
) -> pd.DataFrame:
    bounds = split_bounds(config)
    calendar_list = list(pd.to_datetime(calendar).normalize())
    next_map = {calendar_list[i]: calendar_list[i + 1] for i in range(len(calendar_list) - 1)}
    position_map = {calendar_list[i]: i for i in range(len(calendar_list))}
    limit_pct = float(ep2_config["execution"]["limit_inference_pct"]["mainboard_default"])
    df = panel.copy()
    df["date"] = pd.to_datetime(df["datetime"]).dt.normalize()
    df["split"] = df["date"].map(lambda value: assign_split(value, bounds))
    df["calendar_pos"] = df["date"].map(position_map).astype("Int64")
    df["next_date"] = df["date"].map(next_map)
    group = df.groupby("instrument", group_keys=False)
    df["rolling_high_60_asof"] = group["high"].transform(lambda s: s.shift(1).rolling(60, min_periods=60).max())
    df["rolling_high_40_asof"] = group["high"].transform(lambda s: s.shift(1).rolling(40, min_periods=40).max())
    df["pivot_low_10d"] = group["low"].transform(lambda s: s.shift(1).rolling(10, min_periods=10).min())
    df["money_20d_median_asof"] = group["money"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).median())
    prev_close = group["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["true_range"] = tr
    df["atr20_asof"] = df.groupby("instrument")["true_range"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
    df["atr20_pct_asof"] = df["atr20_asof"] / df["close"]
    df["ret60_asof"] = group["close"].transform(lambda s: s / s.shift(60) - 1.0)
    df["rs_rank_pct_audit"] = df.groupby("date")["ret60_asof"].rank(pct=True)
    df["money_activity_ratio"] = df["money"] / df["money_20d_median_asof"]
    df["close_near_60d_high_triggered"] = df["close"] >= 0.97 * df["rolling_high_60_asof"]
    df["close_breaks_40d_high_triggered"] = df["close"] >= df["rolling_high_40_asof"]
    df["component_trigger_threshold_near60"] = 0.97 * df["rolling_high_60_asof"]
    df["component_trigger_threshold_break40"] = df["rolling_high_40_asof"]
    df["breakout_reference_near60"] = df["component_trigger_threshold_near60"]
    df["breakout_reference_break40"] = df["rolling_high_40_asof"]
    df["seed_day_low"] = df["low"]
    df["has_required_history_for_seed_formula"] = df[
        ["rolling_high_60_asof", "rolling_high_40_asof", "pivot_low_10d", "money_20d_median_asof", "atr20_asof"]
    ].notna().all(axis=1)
    price_ok = df[["open", "high", "low", "close"]].apply(np.isfinite).all(axis=1) & (df[["open", "high", "low", "close"]] > 0).all(axis=1)
    volume_ok = np.isfinite(df["volume"]) & (df["volume"] > 0)
    money_ok = np.isfinite(df["money"]) & (df["money"] > 0)
    df["not_suspended_or_dirty_bar"] = price_ok & volume_ok & money_ok
    df["st_or_delist_risk"] = df["name"].astype(str).str.upper().str.contains("ST", na=False)

    df["next_open"] = group["open"].shift(-1)
    df["next_volume"] = group["volume"].shift(-1)
    df["next_money"] = group["money"].shift(-1)
    df["next_universe_member"] = group["pit_universe_member"].shift(-1).fillna(False).astype(bool)
    buy_reason = np.select(
        [
            df["next_date"].isna(),
            ~np.isfinite(df["next_open"]),
            ~np.isfinite(df["next_volume"]) | (df["next_volume"] <= 0),
            ~np.isfinite(df["next_money"]) | (df["next_money"] <= 0),
            df["next_open"] >= df["close"] * (1.0 + limit_pct),
            ~df["next_universe_member"],
        ],
        [
            "missing_calendar_next_day",
            "missing_open",
            "zero_volume",
            "zero_money",
            "limit_up_inferred",
            "not_universe_member",
        ],
        default="",
    )
    sell_reason = np.select(
        [
            df["next_date"].isna(),
            ~np.isfinite(df["next_open"]),
            ~np.isfinite(df["next_volume"]) | (df["next_volume"] <= 0),
            ~np.isfinite(df["next_money"]) | (df["next_money"] <= 0),
            df["next_open"] <= df["close"] * (1.0 - limit_pct),
        ],
        [
            "missing_calendar_next_day",
            "missing_open",
            "zero_volume",
            "zero_money",
            "limit_down_inferred",
        ],
        default="",
    )
    df["execution_price_reference"] = df["next_open"]
    df["blocked_buy_reason"] = pd.Series(buy_reason, index=df.index)
    df["blocked_sell_reason"] = pd.Series(sell_reason, index=df.index)
    df["is_buy_executable_next_open"] = df["blocked_buy_reason"].eq("")
    df["is_sell_executable_next_open"] = df["blocked_sell_reason"].eq("")
    df["eligible_stock_day"] = (
        df["split"].isin(["train", "validation", "robustness"])
        & df["pit_universe_member"].astype(bool)
        & df["is_buy_executable_next_open"].astype(bool)
        & df["has_required_history_for_seed_formula"].astype(bool)
        & df["not_suspended_or_dirty_bar"].astype(bool)
        & ~df["st_or_delist_risk"].astype(bool)
    )
    df["year"] = df["date"].dt.year
    return df


def _component_for_row(row: pd.Series) -> tuple[str, float, float]:
    if bool(row.get("close_near_60d_high_triggered", False)):
        return "close_near_60d_high", _safe_float(row.get("component_trigger_threshold_near60")), _safe_float(row.get("breakout_reference_near60"))
    return "close_breaks_40d_high", _safe_float(row.get("component_trigger_threshold_break40")), _safe_float(row.get("breakout_reference_break40"))


def build_candidate_seed_events(stock: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    min_money = float(config["seed_rules"]["candidate_seed_components"]["money_activity"]["min_money_ratio_vs_window_median"])
    triggered = (
        stock["split"].isin(["train", "validation", "robustness"])
        & (stock["close_near_60d_high_triggered"].fillna(False) | stock["close_breaks_40d_high_triggered"].fillna(False))
        & (stock["money_activity_ratio"] >= min_money)
    )
    raw = stock.loc[triggered].copy()
    if raw.empty:
        return pd.DataFrame(columns=SEED_EVENT_COLUMNS)
    components = raw.apply(_component_for_row, axis=1, result_type="expand")
    raw["price_structure_component"] = components[0]
    raw["component_trigger_threshold"] = components[1]
    raw["breakout_reference"] = components[2]
    reasons: list[str] = []
    for row in raw.itertuples(index=False):
        reason = ""
        if not bool(row.pit_universe_member):
            reason = "not_pit_universe_member"
        elif not bool(row.has_required_history_for_seed_formula):
            reason = "missing_seed_formula_history"
        elif not bool(row.not_suspended_or_dirty_bar):
            reason = "suspended_or_dirty_bar"
        elif bool(row.st_or_delist_risk):
            reason = "st_or_delist_risk"
        elif not bool(row.is_buy_executable_next_open):
            reason = str(row.blocked_buy_reason) or "next_open_buy_blocked"
        reasons.append(reason)
    raw["reject_reason"] = reasons
    raw["hard_filter_status"] = np.where(raw["reject_reason"].eq(""), "passed", "rejected")
    raw["seed_event_id"] = [
        f"{CANDIDATE_SEED_ID}_{inst}_{_date_str(dt).replace('-', '')}_{idx:08d}"
        for idx, (inst, dt) in enumerate(zip(raw["instrument"], raw["date"]), start=1)
    ]
    out = pd.DataFrame(
        {
            "seed_event_id": raw["seed_event_id"],
            "seed_family_id": CANDIDATE_SEED_ID,
            "instrument": raw["instrument"],
            "signal_date": raw["date"].map(_date_str),
            "split": raw["split"],
            "close": raw["close"],
            "money": raw["money"],
            "price_structure_component": raw["price_structure_component"],
            "close_near_60d_high_triggered": raw["close_near_60d_high_triggered"].astype(bool),
            "close_breaks_40d_high_triggered": raw["close_breaks_40d_high_triggered"].astype(bool),
            "rolling_high_60_asof": raw["rolling_high_60_asof"],
            "rolling_high_40_asof": raw["rolling_high_40_asof"],
            "component_trigger_threshold": raw["component_trigger_threshold"],
            "breakout_reference": raw["breakout_reference"],
            "money_activity_ratio": raw["money_activity_ratio"],
            "money_20d_median_asof": raw["money_20d_median_asof"],
            "atr20_asof": raw["atr20_asof"],
            "atr20_pct_asof": raw["atr20_pct_asof"],
            "rs_rank_pct_audit": raw["rs_rank_pct_audit"],
            "pit_universe_member": raw["pit_universe_member"].astype(bool),
            "next_open_buy_executable": raw["is_buy_executable_next_open"].astype(bool),
            "buy_block_reason": raw["blocked_buy_reason"].fillna(""),
            "hard_filter_status": raw["hard_filter_status"],
            "reject_reason": raw["reject_reason"],
        }
    )
    return out[SEED_EVENT_COLUMNS].reset_index(drop=True)


def build_ep2_seed_events(stock: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    pool = pd.read_parquet(topic_path(config["upstream_ep2"]["launch_pool"]))
    first = pool.sort_values(["instrument", "signal_date", "launch_event_rank_within_episode"]).drop_duplicates("launch_episode_id")
    stock_key = stock.set_index(["instrument", "date"])
    rows: list[dict[str, Any]] = []
    for row in first.itertuples(index=False):
        sig = _date(row.signal_date)
        key = (str(row.instrument).upper(), sig)
        if key not in stock_key.index:
            continue
        s = stock_key.loc[key]
        component = "close_breaks_40d_high"
        threshold = _safe_float(s.get("component_trigger_threshold_break40"))
        breakout = _safe_float(s.get("breakout_reference_break40"))
        rows.append(
            {
                "seed_event_id": str(row.launch_episode_id),
                "seed_family_id": EP2_SEED_ID,
                "instrument": str(row.instrument).upper(),
                "signal_date": _date_str(sig),
                "split": assign_split(sig, split_bounds(config)),
                "close": s.get("close", np.nan),
                "money": s.get("money", np.nan),
                "price_structure_component": component,
                "close_near_60d_high_triggered": bool(s.get("close_near_60d_high_triggered", False)),
                "close_breaks_40d_high_triggered": bool(s.get("close_breaks_40d_high_triggered", False)),
                "rolling_high_60_asof": s.get("rolling_high_60_asof", np.nan),
                "rolling_high_40_asof": s.get("rolling_high_40_asof", np.nan),
                "component_trigger_threshold": threshold,
                "breakout_reference": breakout,
                "money_activity_ratio": s.get("money_activity_ratio", np.nan),
                "money_20d_median_asof": s.get("money_20d_median_asof", np.nan),
                "atr20_asof": s.get("atr20_asof", np.nan),
                "atr20_pct_asof": s.get("atr20_pct_asof", np.nan),
                "rs_rank_pct_audit": s.get("rs_rank_pct_audit", np.nan),
                "pit_universe_member": bool(s.get("pit_universe_member", False)),
                "next_open_buy_executable": bool(row.is_buy_executable_next_open),
                "buy_block_reason": str(row.blocked_buy_reason) if pd.notna(row.blocked_buy_reason) else "",
                "hard_filter_status": "passed" if bool(row.is_buy_executable_next_open) else "rejected",
                "reject_reason": "" if bool(row.is_buy_executable_next_open) else str(row.blocked_buy_reason),
            }
        )
    return pd.DataFrame(rows, columns=SEED_EVENT_COLUMNS)


def closest_stop_below(entry_price: float, stops: list[float], min_pct: float, max_pct: float) -> tuple[float, float, str]:
    valid = [float(v) for v in stops if np.isfinite(v) and np.isfinite(entry_price) and float(v) < float(entry_price)]
    if not valid:
        return np.nan, np.nan, "no_valid_stop_below_entry"
    stop = max(valid)
    risk_pct = (float(entry_price) - stop) / float(entry_price) if float(entry_price) > 0 else np.nan
    if not np.isfinite(risk_pct) or risk_pct < min_pct:
        return stop, risk_pct, "risk_distance_below_min"
    if risk_pct > max_pct:
        return stop, risk_pct, "risk_distance_above_max"
    return stop, risk_pct, "passed"


def build_seed_episodes(
    seed_events: pd.DataFrame,
    stock: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    reference: pd.DataFrame,
    bridge_reference: pd.DataFrame,
    effective_windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
) -> pd.DataFrame:
    if seed_events.empty:
        return pd.DataFrame(columns=SEED_EPISODE_COLUMNS)
    min_risk = float(config["risk_normalization"]["min_initial_risk_pct"])
    max_risk = float(config["risk_normalization"]["max_initial_risk_pct"])
    stock_key = stock.set_index(["instrument", "date"])
    pos = {pd.Timestamp(d): i for i, d in enumerate(calendar)}
    rows: list[dict[str, Any]] = []
    for family, fam_events in seed_events.sort_values(["seed_family_id", "instrument", "signal_date"]).groupby("seed_family_id"):
        for instrument, inst_events in fam_events.groupby("instrument"):
            active: list[pd.Series] = []
            active_end = pd.NaT
            for _, event in inst_events.iterrows():
                sig = _date(event["signal_date"])
                if event["hard_filter_status"] != "passed":
                    continue
                if not active or sig > active_end:
                    if active:
                        rows.append(
                            _episode_from_events(
                                active, stock_key, config, calendar, reference, bridge_reference, effective_windows, pos, min_risk, max_risk
                            )
                        )
                    active = [event]
                    active_end = base.add_trading_days(calendar, sig, 20)
                else:
                    active.append(event)
                    active_end = base.add_trading_days(calendar, sig, 20)
            if active:
                rows.append(
                    _episode_from_events(
                        active, stock_key, config, calendar, reference, bridge_reference, effective_windows, pos, min_risk, max_risk
                    )
                )
    return pd.DataFrame(rows, columns=SEED_EPISODE_COLUMNS).sort_values(["seed_family_id", "instrument", "episode_start_signal_date"]).reset_index(drop=True)


def _episode_from_events(
    events: list[pd.Series],
    stock_key: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    reference: pd.DataFrame,
    bridge_reference: pd.DataFrame,
    effective_windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
    pos: dict[pd.Timestamp, int],
    min_risk: float,
    max_risk: float,
) -> dict[str, Any]:
    first = events[0]
    family = str(first["seed_family_id"])
    instrument = str(first["instrument"]).upper()
    start = _date(first["signal_date"])
    end = _date(events[-1]["signal_date"])
    episode_id = str(first["seed_event_id"]) if family == EP2_SEED_ID else f"{family}_{instrument}_{_date_str(start).replace('-', '')}_{hashlib.sha1(str(first['seed_event_id']).encode()).hexdigest()[:10]}"
    key = (instrument, start)
    s = stock_key.loc[key] if key in stock_key.index else pd.Series(dtype=object)
    entry_date = s.get("next_date", pd.NaT)
    entry_price = _safe_float(s.get("next_open"))
    seed_day_low = _safe_float(s.get("seed_day_low"))
    breakout_reference = _safe_float(first.get("breakout_reference"))
    pivot_low = _safe_float(s.get("pivot_low_10d"))
    stop, risk_pct, risk_status = closest_stop_below(entry_price, [seed_day_low, breakout_reference, pivot_low], min_risk, max_risk)
    executable = "passed" if risk_status == "passed" and pd.notna(entry_date) and np.isfinite(entry_price) and bool(s.get("is_buy_executable_next_open", False)) else "rejected"
    reject_reason = "" if executable == "passed" else (risk_status if risk_status != "passed" else str(s.get("blocked_buy_reason", "entry_not_executable")))
    split = assign_split(start, split_bounds(config))
    eff_end = effective_windows.get(split, (pd.NaT, pd.NaT))[1]
    primary_eligible = split in {"train", "validation", "robustness"} and not pd.isna(eff_end) and start <= eff_end
    captured, captured_id, window_id = capture_reference(instrument, start, reference, calendar, 20, 0)
    bridge_captured, _, _ = capture_reference(instrument, start, bridge_reference, calendar, 20, 0)
    return {
        "seed_episode_id": episode_id,
        "seed_family_id": family,
        "instrument": instrument,
        "episode_start_signal_date": _date_str(start),
        "episode_effective_entry_date": _date_str(entry_date),
        "episode_end_signal_date": _date_str(base.add_trading_days(calendar, end, 20)),
        "split": split,
        "first_seed_event_id": str(first["seed_event_id"]),
        "seed_event_count": len(events),
        "suppressed_reentry_count": max(0, len(events) - 1),
        "entry_price": entry_price,
        "price_structure_component": first.get("price_structure_component", ""),
        "seed_day_low": seed_day_low,
        "breakout_reference": breakout_reference,
        "pivot_low_10d": pivot_low,
        "initial_structural_stop": stop,
        "initial_risk_pct": risk_pct,
        "risk_distance_status": risk_status,
        "executable_status": executable,
        "episode_reject_reason": reject_reason,
        "primary_metric_eligible_seed_episode": bool(primary_eligible),
        "captures_primary_big_winner": bool(captured) if primary_eligible else False,
        "captured_reference_event_id": captured_id if primary_eligible else "",
        "capture_window_id": window_id if primary_eligible and captured else "",
        "captures_ep2_bridge_big_winner": bool(bridge_captured),
    }


def capture_reference(
    instrument: str,
    signal_date: pd.Timestamp,
    reference: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    lookback_days: int,
    forward_days: int,
) -> tuple[bool, str, str]:
    if reference.empty:
        return False, "", ""
    refs = reference.loc[reference["instrument"].astype(str).eq(str(instrument).upper())].copy()
    if refs.empty:
        return False, "", ""
    start = base.add_trading_days(calendar, signal_date, -forward_days) if forward_days < 0 else signal_date
    end = base.add_trading_days(calendar, signal_date, lookback_days)
    if pd.isna(end):
        end = signal_date
    hits = refs.loc[(pd.to_datetime(refs["reference_date"]) >= signal_date) & (pd.to_datetime(refs["reference_date"]) <= end)]
    if hits.empty:
        return False, "", ""
    first = hits.sort_values("reference_date").iloc[0]
    return True, str(first["reference_event_id"]), "primary_-20_0"


def reference_index(reference: pd.DataFrame) -> dict[str, list[tuple[pd.Timestamp, str]]]:
    out: dict[str, list[tuple[pd.Timestamp, str]]] = {}
    if reference.empty:
        return out
    for instrument, group in reference.groupby("instrument"):
        out[str(instrument).upper()] = [
            (pd.Timestamp(row.reference_date), str(row.reference_event_id))
            for row in group.sort_values("reference_date").itertuples(index=False)
        ]
    return out


def capture_reference_fast(
    ref_idx: dict[str, list[tuple[pd.Timestamp, str]]],
    instrument: str,
    signal_date: pd.Timestamp,
    calendar: pd.DatetimeIndex,
    lookahead_days: int = 20,
) -> tuple[bool, str, str]:
    refs = ref_idx.get(str(instrument).upper(), [])
    if not refs:
        return False, "", ""
    end = base.add_trading_days(calendar, signal_date, lookahead_days)
    if pd.isna(end):
        end = signal_date
    for ref_date, ref_id in refs:
        if signal_date <= ref_date <= end:
            return True, ref_id, "primary_-20_0"
        if ref_date > end:
            break
    return False, "", ""


def build_big_winner_reference(
    stock: pd.DataFrame, config: dict[str, Any], calendar: pd.DatetimeIndex, effective_windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]]
) -> pd.DataFrame:
    horizon = int(config["big_winner_reference"]["forward_horizon_trading_days"])
    threshold = float(config["big_winner_reference"]["return_threshold"])
    dedupe = int(config["big_winner_reference"]["dedupe_gap_trading_days"])
    bounds = split_bounds(config)
    rows: list[dict[str, Any]] = []
    for instrument, inst_all in stock.sort_values(["instrument", "date"]).groupby("instrument"):
        inst = inst_all.reset_index(drop=True)
        eligible_mask = inst["eligible_stock_day"].astype(bool).to_numpy()
        closes = inst["close"].to_numpy(dtype=float)
        next_open = inst["next_open"].to_numpy(dtype=float)
        calendar_pos = inst["calendar_pos"].astype("Int64").to_numpy()
        suppress_until_pos = -1
        for i, row in inst.iterrows():
            if not eligible_mask[i]:
                continue
            date = pd.Timestamp(row["date"])
            pos_i = int(row["calendar_pos"]) if not pd.isna(row["calendar_pos"]) else -1
            if pos_i <= suppress_until_pos:
                continue
            if i + horizon >= len(inst):
                continue
            if int(calendar_pos[i + horizon]) - pos_i != horizon:
                continue
            window = closes[i + 1 : i + horizon + 1]
            if len(window) < horizon or not np.isfinite(window).any():
                continue
            rel_peak_idx = int(np.nanargmax(window)) + i + 1
            peak_close = _safe_float(closes[rel_peak_idx])
            fwd_ret = peak_close / float(next_open[i]) - 1.0 if np.isfinite(peak_close) and next_open[i] > 0 else np.nan
            if np.isfinite(fwd_ret) and fwd_ret >= threshold:
                split = assign_split(date, bounds)
                rows.append(
                    {
                        "reference_event_id": f"{config['big_winner_reference']['primary_id']}_{instrument}_{_date_str(date).replace('-', '')}_{len(rows)+1:06d}",
                        "instrument": instrument,
                        "reference_date": _date_str(date),
                        "entry_price_next_open": float(next_open[i]),
                        "forward_horizon_trading_days": horizon,
                        "forward_peak_close": peak_close,
                        "forward_peak_date": _date_str(inst.loc[rel_peak_idx, "date"]),
                        "forward_return": fwd_ret,
                        "dedupe_gap_trading_days": dedupe,
                        "split": split,
                        "eligibility_status": "passed",
                        "ineligibility_reason": "",
                    }
                )
                suppress_until_pos = pos_i + dedupe
    return pd.DataFrame(rows, columns=BIG_WINNER_REFERENCE_COLUMNS)


def build_ep2_bridge_reference(stock: pd.DataFrame, config: dict[str, Any], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    pool = pd.read_parquet(topic_path(config["upstream_ep2"]["launch_pool"]))
    first = pool.sort_values(["instrument", "signal_date"]).drop_duplicates("launch_episode_id")
    stock_groups: dict[str, pd.DataFrame] = {
        inst: group.sort_values("date").reset_index(drop=True)
        for inst, group in stock.groupby("instrument", sort=False)
    }
    stock_pos: dict[str, dict[pd.Timestamp, int]] = {
        inst: {pd.Timestamp(dt): i for i, dt in enumerate(group["date"])}
        for inst, group in stock_groups.items()
    }
    rows: list[dict[str, Any]] = []
    horizon = int(config["big_winner_reference"]["forward_horizon_trading_days"])
    threshold = float(config["big_winner_reference"]["return_threshold"])
    for row in first.itertuples(index=False):
        instrument = str(row.instrument).upper()
        sig = _date(row.signal_date)
        if instrument not in stock_groups or sig not in stock_pos[instrument]:
            continue
        group = stock_groups[instrument]
        i = stock_pos[instrument][sig]
        s = group.iloc[i]
        entry = _safe_float(s.get("next_open"))
        if not np.isfinite(entry) or i + horizon >= len(group):
            continue
        if int(group.iloc[i + horizon]["calendar_pos"]) - int(s["calendar_pos"]) != horizon:
            continue
        window = group["close"].iloc[i + 1 : i + horizon + 1].to_numpy(dtype=float)
        if len(window) < horizon or not np.isfinite(window).any():
            continue
        rel_peak_idx = int(np.nanargmax(window)) + i + 1
        peak = _safe_float(group.iloc[rel_peak_idx]["close"])
        ret = peak / entry - 1.0 if entry > 0 and np.isfinite(peak) else np.nan
        if np.isfinite(ret) and ret >= threshold:
            rows.append(
                {
                    "reference_event_id": f"ep2_launch_pool_big_winner_50h120_{instrument}_{_date_str(sig).replace('-', '')}_{len(rows)+1:06d}",
                    "instrument": instrument,
                    "reference_date": _date_str(sig),
                    "entry_price_next_open": entry,
                    "forward_horizon_trading_days": horizon,
                    "forward_peak_close": peak,
                    "forward_peak_date": _date_str(group.iloc[rel_peak_idx]["date"]),
                    "forward_return": ret,
                    "dedupe_gap_trading_days": horizon,
                    "split": assign_split(sig, split_bounds(config)),
                    "eligibility_status": "passed",
                    "ineligibility_reason": "",
                }
            )
    return pd.DataFrame(rows, columns=BIG_WINNER_REFERENCE_COLUMNS)


def simulate_episode_rows(
    rows: pd.DataFrame,
    config: dict[str, Any],
    ep2_config: dict[str, Any],
    stock: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    fail_fast: bool,
    id_prefix: str,
    baseline_id: str | None = None,
    simple_stop_pct: float | None = None,
    natural_h_override: int | None = None,
) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(columns=BASELINE_SIM_COLUMNS if baseline_id else PROBE_SIM_COLUMNS)
    stock_key = stock.set_index(["instrument", "date"])
    universe_set = set(
        zip(
            stock.loc[stock["pit_universe_member"].astype(bool), "instrument"].astype(str),
            pd.to_datetime(stock.loc[stock["pit_universe_member"].astype(bool), "date"]).dt.normalize(),
        )
    )
    lookup = base.price_lookup(stock.rename(columns={"date": "datetime"}))
    rates = base.cost_rates(ep2_config)
    limit_pct = float(ep2_config["execution"]["limit_inference_pct"]["mainboard_default"])
    natural_h = int(natural_h_override if natural_h_override is not None else config["fail_fast"]["natural_exit_horizon_trading_days"])
    ff_window = int(config["fail_fast"]["max_fail_fast_window_trading_days"])
    retry_max = int(config["execution"]["max_exit_retry_trading_days"])
    probe_r = float(config["probe"]["initial_probe_risk_budget_r"])
    records: list[dict[str, Any]] = []
    for idx, row in rows.reset_index(drop=True).iterrows():
        sim = _simulate_one(row, stock_key, lookup, universe_set, calendar, rates, limit_pct, natural_h, ff_window, retry_max, probe_r, fail_fast, simple_stop_pct)
        if baseline_id:
            records.append(_baseline_record(row, sim, idx, id_prefix, baseline_id))
        else:
            records.append(_probe_record(row, sim, idx, id_prefix))
    cols = BASELINE_SIM_COLUMNS if baseline_id else PROBE_SIM_COLUMNS
    return pd.DataFrame(records, columns=cols)


def simulate_random_baseline_fast(
    rows: pd.DataFrame,
    config: dict[str, Any],
    ep2_config: dict[str, Any],
    stock: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    baseline_id: str,
) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(columns=BASELINE_SIM_COLUMNS)
    rates = base.cost_rates(ep2_config)
    work = rows.reset_index(drop=True).copy()
    stock_pos = stock[["instrument", "date", "calendar_pos"]].rename(columns={"date": "random_signal_date_key"})
    work["random_signal_date_key"] = pd.to_datetime(work["random_signal_date"]).dt.normalize()
    work = work.merge(stock_pos, on=["instrument", "random_signal_date_key"], how="left")
    signal_pos = work["calendar_pos"].astype("float")
    natural_exit_pos = signal_pos + 1 + int(config["fail_fast"]["natural_exit_horizon_trading_days"]) + 1
    exit_trigger = pd.Series("natural_exit_h20", index=work.index, dtype=object)
    exit_signal_pos = signal_pos + 1 + int(config["fail_fast"]["natural_exit_horizon_trading_days"])
    if "same_fail_fast" in baseline_id:
        close_lookup = stock[["instrument", "calendar_pos", "date", "close"]]
        first_trigger_pos = pd.Series(np.nan, index=work.index, dtype=float)
        first_trigger_type = pd.Series("", index=work.index, dtype=object)
        for offset in range(int(config["fail_fast"]["max_fail_fast_window_trading_days"])):
            probe = pd.DataFrame(
                {
                    "row_id": work.index,
                    "instrument": work["instrument"].astype(str).to_numpy(),
                    "trigger_calendar_pos": signal_pos.to_numpy() + 1 + offset,
                }
            )
            day = probe.merge(
                close_lookup.rename(columns={"calendar_pos": "trigger_calendar_pos", "date": "trigger_date", "close": "trigger_close"}),
                on=["instrument", "trigger_calendar_pos"],
                how="left",
            ).set_index("row_id").reindex(work.index)
            close = day["trigger_close"].astype(float)
            trigger_type = pd.Series("", index=work.index, dtype=object)
            trigger_type = np.where(close < work["seed_day_low"].astype(float), "close_below_seed_day_low", trigger_type)
            trigger_type = np.where((trigger_type == "") & (close < work["breakout_reference"].astype(float)), "close_below_breakout_reference", trigger_type)
            trigger_type = np.where((trigger_type == "") & (close < work["pivot_low_10d"].astype(float)), "close_below_pivot_low_10d", trigger_type)
            hit = pd.Series(trigger_type, index=work.index).astype(str).ne("") & first_trigger_pos.isna()
            first_trigger_pos.loc[hit] = day.loc[hit, "trigger_calendar_pos"].astype(float)
            first_trigger_type.loc[hit] = pd.Series(trigger_type, index=work.index).loc[hit]
        has_trigger = first_trigger_pos.notna()
        exit_signal_pos = exit_signal_pos.where(~has_trigger, first_trigger_pos)
        exit_trigger = exit_trigger.where(~has_trigger, first_trigger_type)
    work["exit_calendar_pos"] = exit_signal_pos + 1
    exit_lookup = stock[["instrument", "calendar_pos", "date", "open"]].rename(
        columns={"calendar_pos": "exit_calendar_pos", "date": "exit_date_calc", "open": "exit_open"}
    )
    work = work.merge(exit_lookup, on=["instrument", "exit_calendar_pos"], how="left")
    entry = work["entry_price"].astype(float)
    exit_price = work["exit_open"].astype(float)
    risk = work["initial_risk_pct"].astype(float)
    gross = exit_price / entry - 1.0
    after = (exit_price * (1.0 - rates["sell_total"])) / (entry * (1.0 + rates["buy_total"])) - 1.0
    return_r = float(config["probe"]["initial_probe_risk_budget_r"]) * after / risk
    ok = (
        work["pre_sim_eligibility_status"].eq("passed")
        & np.isfinite(entry)
        & np.isfinite(exit_price)
        & np.isfinite(risk)
        & (risk > 0)
    )
    out = pd.DataFrame(
        {
            "baseline_simulation_id": [f"{baseline_id}_{i + 1:08d}" for i in range(len(work))],
            "baseline_id": baseline_id,
            "replicate_id": work["replicate_id"],
            "matched_control_type": "matched_random",
            "fail_fast_policy": "same_fail_fast" if "same_fail_fast" in baseline_id else "no_fail_fast",
            "structural_reference_policy": "pseudo_event_recomputed_references",
            "carried_price_structure_component": work["price_structure_component"],
            "carried_seed_episode_id": work["carried_seed_episode_id"],
            "seed_episode_id": "",
            "random_event_id": work["random_event_id"],
            "instrument": work["instrument"],
            "signal_date": work["signal_date"],
            "random_signal_date": work["random_signal_date"],
            "entry_date": work["entry_date"],
            "entry_price": work["entry_price"],
            "seed_day_low": work["seed_day_low"],
            "breakout_reference": work["breakout_reference"],
            "pivot_low_10d": work["pivot_low_10d"],
            "initial_structural_stop": work["initial_structural_stop"],
            "initial_risk_pct": work["initial_risk_pct"],
            "delay_days": 0,
            "delay_period_return_pct": np.nan,
            "delay_period_return_bucket": "",
            "matched_delay_reliability_status": "not_applicable",
            "random_excluded_candidate_seed_day": False,
            "random_capacity_shortfall": work["random_capacity_shortfall"],
            "random_sampling_replacement_policy": work["random_sampling_replacement_policy"],
            "random_baseline_reliability_status": work["random_baseline_reliability_status"],
            "primary_metric_eligible_baseline_event": work["primary_metric_eligible_baseline_event"].astype(bool),
            "captures_primary_big_winner": work["captures_primary_big_winner"].astype(bool),
            "captured_reference_event_id": work["captured_reference_event_id"],
            "capture_window_id": work["capture_window_id"],
            "baseline_failed_seed_primary": np.where(work["primary_metric_eligible_baseline_event"].astype(bool) & ok, ~work["captures_primary_big_winner"].astype(bool), np.nan),
            "exit_date": pd.to_datetime(work["exit_date_calc"]).dt.strftime("%Y-%m-%d"),
            "exit_price": np.where(ok, exit_price, np.nan),
            "eligibility_status": np.where(ok, "passed", "ineligible"),
            "ineligibility_reason": np.where(ok, "", np.where(work["pre_sim_ineligibility_reason"].astype(str).ne(""), work["pre_sim_ineligibility_reason"].astype(str), "missing_exit_or_risk")),
            "gross_return_pct": np.where(ok, gross, np.nan),
            "after_cost_return_pct": np.where(ok, after, np.nan),
            "return_r": np.where(ok, return_r, np.nan),
            "loss_r": np.where(ok, np.maximum(0.0, -return_r), np.nan),
            "holding_days": np.where(ok, np.maximum(0, work["exit_calendar_pos"].astype(float) - (signal_pos + 1) + 1), 0),
            "exposure_days": np.where(ok, np.maximum(0, work["exit_calendar_pos"].astype(float) - (signal_pos + 1) + 1), 0),
            "split": work["split"],
            "match_year": work["match_year"],
            "match_industry": work["match_industry"],
            "match_liquidity_bucket": work["match_liquidity_bucket"],
            "match_volatility_bucket": work["match_volatility_bucket"],
        }
    )
    return out[BASELINE_SIM_COLUMNS]


def _simulate_one(
    row: pd.Series,
    stock_key: pd.DataFrame,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    calendar: pd.DatetimeIndex,
    rates: dict[str, float],
    limit_pct: float,
    natural_h: int,
    ff_window: int,
    retry_max: int,
    probe_r: float,
    fail_fast: bool,
    simple_stop_pct: float | None = None,
) -> dict[str, Any]:
    instrument = str(row["instrument"]).upper()
    try:
        entry_date = _date(row.get("entry_date", row.get("episode_effective_entry_date", "")))
    except Exception:
        entry_date = pd.NaT
    entry_price = _safe_float(row.get("entry_price"))
    seed_day_low = _safe_float(row.get("seed_day_low"))
    breakout = _safe_float(row.get("breakout_reference"))
    pivot = _safe_float(row.get("pivot_low_10d"))
    risk_pct = _safe_float(row.get("initial_risk_pct"))
    if pd.isna(entry_date) or not np.isfinite(entry_price) or not np.isfinite(risk_pct) or risk_pct <= 0:
        return _empty_sim("ineligible_entry_or_risk")
    exit_trigger = f"natural_exit_h{natural_h}"
    exit_signal = base.add_trading_days(calendar, entry_date, natural_h)
    if fail_fast:
        for day in range(ff_window):
            signal = base.add_trading_days(calendar, entry_date, day)
            if pd.isna(signal):
                continue
            info = lookup.get((instrument, signal), {})
            close = _safe_float(info.get("close"))
            if not np.isfinite(close):
                continue
            if simple_stop_pct is not None:
                triggered = ["ep2_simple_stop_6pct"] if close <= entry_price * (1.0 - float(simple_stop_pct)) else []
            else:
                triggered = []
                if np.isfinite(seed_day_low) and close < seed_day_low:
                    triggered.append("close_below_seed_day_low")
                if np.isfinite(breakout) and close < breakout:
                    triggered.append("close_below_breakout_reference")
                if np.isfinite(pivot) and close < pivot:
                    triggered.append("close_below_pivot_low_10d")
            if triggered:
                exit_trigger = "|".join(triggered)
                exit_signal = signal
                break
    exit_exec = base.next_trading_day(calendar, exit_signal)
    blocked = 0
    terminal = False
    exit_price = np.nan
    if pd.isna(exit_exec):
        return _empty_sim("missing_exit_execution_date")
    current = exit_exec
    while True:
        signal_for_execution = base.prev_trading_day(calendar, current)
        status = base.execution_status(lookup, universe_set, instrument, signal_for_execution, current, limit_pct)
        if not status.get("blocked_sell_reason"):
            exit_price = _safe_float(status.get("execution_price_reference"))
            exit_exec = current
            break
        blocked += 1
        if blocked > retry_max:
            terminal = True
            info = lookup.get((instrument, current), {})
            exit_price = _safe_float(info.get("open"), _safe_float(info.get("close")))
            exit_exec = current
            break
        current = base.next_trading_day(calendar, current)
        if pd.isna(current):
            terminal = True
            break
    if not np.isfinite(exit_price) or not np.isfinite(entry_price) or entry_price <= 0:
        return _empty_sim("missing_exit_price")
    gross_return = exit_price / entry_price - 1.0
    after_cost = (exit_price * (1.0 - rates["sell_total"])) / (entry_price * (1.0 + rates["buy_total"])) - 1.0
    return_r = probe_r * after_cost / risk_pct
    pos_entry = calendar.searchsorted(entry_date, side="left")
    pos_exit = calendar.searchsorted(exit_exec, side="left")
    exposure_days = max(0, int(pos_exit - pos_entry + 1))
    return {
        "eligibility_status": "passed",
        "ineligibility_reason": "",
        "exit_trigger_type": exit_trigger,
        "exit_signal_date": _date_str(exit_signal),
        "exit_execution_date": _date_str(exit_exec),
        "exit_price": exit_price,
        "sell_blocked_day_count": blocked,
        "terminal_blocked_exit": terminal,
        "gross_return_pct": gross_return,
        "after_cost_return_pct": after_cost,
        "return_r": return_r,
        "loss_r": max(0.0, -return_r),
        "holding_days": exposure_days,
        "exposure_days": exposure_days,
        "failed_seed_h20_negative": after_cost < 0,
        "failed_seed_fail_fast_triggered": fail_fast and not exit_trigger.startswith("natural_exit_h"),
    }


def _empty_sim(reason: str) -> dict[str, Any]:
    return {
        "eligibility_status": "ineligible",
        "ineligibility_reason": reason,
        "exit_trigger_type": "",
        "exit_signal_date": "",
        "exit_execution_date": "",
        "exit_price": np.nan,
        "sell_blocked_day_count": 0,
        "terminal_blocked_exit": False,
        "gross_return_pct": np.nan,
        "after_cost_return_pct": np.nan,
        "return_r": np.nan,
        "loss_r": np.nan,
        "holding_days": 0,
        "exposure_days": 0,
        "failed_seed_h20_negative": False,
        "failed_seed_fail_fast_triggered": False,
    }


def _probe_record(row: pd.Series, sim: dict[str, Any], idx: int, id_prefix: str) -> dict[str, Any]:
    failed_primary = (
        not bool(row.get("captures_primary_big_winner", False))
        if bool(row.get("primary_metric_eligible_seed_episode", False)) and sim["eligibility_status"] == "passed"
        else np.nan
    )
    return {
        "simulation_id": f"{id_prefix}_{idx + 1:08d}",
        "seed_episode_id": row["seed_episode_id"],
        "seed_family_id": row["seed_family_id"],
        "instrument": row["instrument"],
        "entry_date": _date_str(row["entry_date"]),
        "entry_price": row["entry_price"],
        "initial_probe_risk_budget_r": 0.25,
        "initial_structural_stop": row["initial_structural_stop"],
        "initial_risk_pct": row["initial_risk_pct"],
        "exit_trigger_type": sim["exit_trigger_type"],
        "exit_signal_date": sim["exit_signal_date"],
        "exit_execution_date": sim["exit_execution_date"],
        "exit_price": sim["exit_price"],
        "sell_blocked_day_count": sim["sell_blocked_day_count"],
        "terminal_blocked_exit": sim["terminal_blocked_exit"],
        "gross_return_pct": sim["gross_return_pct"],
        "after_cost_return_pct": sim["after_cost_return_pct"],
        "return_r": sim["return_r"],
        "loss_r": sim["loss_r"],
        "holding_days": sim["holding_days"],
        "exposure_days": sim["exposure_days"],
        "primary_metric_eligible_seed_episode": bool(row.get("primary_metric_eligible_seed_episode", False)),
        "failed_seed_primary": failed_primary,
        "failed_seed_label_a_h10_u1_5": bool(row.get("label_a_h10_negative", False)),
        "failed_seed_label_a_h20_u2_0": bool(row.get("label_a_h20_negative", False)),
        "failed_seed_h20_negative": sim["failed_seed_h20_negative"],
        "failed_seed_fail_fast_triggered": sim["failed_seed_fail_fast_triggered"],
        "split": row["split"],
    }


def _baseline_record(row: pd.Series, sim: dict[str, Any], idx: int, id_prefix: str, baseline_id: str) -> dict[str, Any]:
    failed_primary = (
        not bool(row.get("captures_primary_big_winner", False))
        if bool(row.get("primary_metric_eligible_baseline_event", False)) and sim["eligibility_status"] == "passed"
        else np.nan
    )
    return {
        "baseline_simulation_id": f"{id_prefix}_{idx + 1:08d}",
        "baseline_id": baseline_id,
        "replicate_id": row.get("replicate_id", 0),
        "matched_control_type": row.get("matched_control_type", "same_seed"),
        "fail_fast_policy": row.get("fail_fast_policy", "same_fail_fast" if "same_fail_fast" in baseline_id else "no_fail_fast"),
        "structural_reference_policy": row.get("structural_reference_policy", "carried_original_seed_references"),
        "carried_price_structure_component": row.get("price_structure_component", row.get("carried_price_structure_component", "")),
        "carried_seed_episode_id": row.get("carried_seed_episode_id", row.get("seed_episode_id", "")),
        "seed_episode_id": row.get("seed_episode_id", ""),
        "random_event_id": row.get("random_event_id", ""),
        "instrument": row.get("instrument", ""),
        "signal_date": _date_str(row.get("signal_date", row.get("episode_start_signal_date", ""))),
        "random_signal_date": _date_str(row.get("random_signal_date", "")),
        "entry_date": _date_str(row.get("entry_date", "")),
        "entry_price": row.get("entry_price", np.nan),
        "seed_day_low": row.get("seed_day_low", np.nan),
        "breakout_reference": row.get("breakout_reference", np.nan),
        "pivot_low_10d": row.get("pivot_low_10d", np.nan),
        "initial_structural_stop": row.get("initial_structural_stop", np.nan),
        "initial_risk_pct": row.get("initial_risk_pct", np.nan),
        "delay_days": row.get("delay_days", 0),
        "delay_period_return_pct": row.get("delay_period_return_pct", np.nan),
        "delay_period_return_bucket": row.get("delay_period_return_bucket", ""),
        "matched_delay_reliability_status": row.get("matched_delay_reliability_status", "not_applicable"),
        "random_excluded_candidate_seed_day": row.get("random_excluded_candidate_seed_day", False),
        "random_capacity_shortfall": row.get("random_capacity_shortfall", False),
        "random_sampling_replacement_policy": row.get("random_sampling_replacement_policy", "not_random"),
        "random_baseline_reliability_status": row.get("random_baseline_reliability_status", "not_applicable"),
        "primary_metric_eligible_baseline_event": bool(row.get("primary_metric_eligible_baseline_event", row.get("primary_metric_eligible_seed_episode", False))),
        "captures_primary_big_winner": bool(row.get("captures_primary_big_winner", False)),
        "captured_reference_event_id": row.get("captured_reference_event_id", ""),
        "capture_window_id": row.get("capture_window_id", ""),
        "baseline_failed_seed_primary": failed_primary,
        "exit_date": sim["exit_execution_date"],
        "exit_price": sim["exit_price"],
        "eligibility_status": sim["eligibility_status"] if row.get("pre_sim_eligibility_status", "passed") == "passed" else row.get("pre_sim_eligibility_status"),
        "ineligibility_reason": sim["ineligibility_reason"] if row.get("pre_sim_ineligibility_reason", "") == "" else row.get("pre_sim_ineligibility_reason"),
        "gross_return_pct": sim["gross_return_pct"],
        "after_cost_return_pct": sim["after_cost_return_pct"],
        "return_r": sim["return_r"],
        "loss_r": sim["loss_r"],
        "holding_days": sim["holding_days"],
        "exposure_days": sim["exposure_days"],
        "split": row.get("split", ""),
        "match_year": row.get("match_year", ""),
        "match_industry": row.get("match_industry", "all"),
        "match_liquidity_bucket": row.get("match_liquidity_bucket", "all"),
        "match_volatility_bucket": row.get("match_volatility_bucket", "all"),
    }


def enrich_episode_for_sim(episodes: pd.DataFrame) -> pd.DataFrame:
    out = episodes.copy()
    out["entry_date"] = out["episode_effective_entry_date"]
    return out


def label_a_audit(episodes: pd.DataFrame, stock: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    stock_key = stock.set_index(["instrument", "date"])
    rows: list[dict[str, Any]] = []
    labels: dict[str, tuple[int, float, float]] = {
        "seed_quality_triple_barrier_atr_h10_u1_5_d1_0": (10, 1.5, 1.0),
        "seed_quality_triple_barrier_atr_h20_u2_0_d1_0": (20, 2.0, 1.0),
    }
    for _, ep in episodes.iterrows():
        if ep["seed_family_id"] != CANDIDATE_SEED_ID or ep["executable_status"] != "passed":
            continue
        instrument = ep["instrument"]
        sig = _date(ep["episode_start_signal_date"])
        if (instrument, sig) not in stock_key.index:
            continue
        s = stock_key.loc[(instrument, sig)]
        atr = _safe_float(s.get("atr20_asof"))
        entry = _safe_float(ep["entry_price"])
        for label_id, (horizon, up_mult, down_mult) in labels.items():
            value = np.nan
            first_target = ""
            first_drawdown = ""
            ambiguous = False
            if np.isfinite(entry) and np.isfinite(atr) and atr > 0:
                upper = entry + up_mult * atr
                lower = entry - down_mult * atr
                for day in range(horizon + 1):
                    dt = base.add_trading_days(calendar, _date(ep["episode_effective_entry_date"]), day)
                    if pd.isna(dt) or (instrument, dt) not in stock_key.index:
                        continue
                    px = stock_key.loc[(instrument, dt)]
                    hit_up = _safe_float(px.get("high")) >= upper
                    hit_down = _safe_float(px.get("low")) <= lower
                    if hit_up and hit_down:
                        value = 0.0
                        ambiguous = True
                        first_target = _date_str(dt)
                        first_drawdown = _date_str(dt)
                        break
                    if hit_down:
                        value = 0.0
                        first_drawdown = _date_str(dt)
                        break
                    if hit_up:
                        value = 1.0
                        first_target = _date_str(dt)
                        break
                if pd.isna(value):
                    value = 0.0
            rows.append(
                {
                    "split": ep["split"],
                    "seed_episode_id": ep["seed_episode_id"],
                    "instrument": instrument,
                    "label_id": label_id,
                    "atr20_asof": atr,
                    "entry_price": entry,
                    "label_value": value,
                    "first_target_date": first_target,
                    "first_drawdown_date": first_drawdown,
                    "same_day_ambiguous": ambiguous,
                    "audit_only_status": "report_only",
                }
            )
    audit = pd.DataFrame(rows)
    if audit.empty:
        return pd.DataFrame(columns=["split", "seed_episode_id", "instrument", "label_id", "atr20_asof", "entry_price", "label_value", "first_target_date", "first_drawdown_date", "same_day_ambiguous", "audit_only_status"])
    return audit


def build_bucket_freeze(stock: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    q = [float(x) for x in config["matched_controls"]["bucket_quantiles"]]
    train = stock.loc[stock["split"].eq("train") & stock["eligible_stock_day"].astype(bool)].copy()
    frames: list[pd.DataFrame] = []
    bucketed = stock.copy()
    for field in [config["matched_controls"]["liquidity_field"], config["matched_controls"]["volatility_field"]]:
        values = train[field].dropna().astype(float)
        edges = values.quantile(q).to_numpy() if not values.empty else np.array([np.nan] * len(q))
        if len(edges) >= 2:
            edges[0] = -np.inf
            edges[-1] = np.inf
        rows: list[dict[str, Any]] = []
        labels: list[str] = []
        for i in range(len(q) - 1):
            bucket_id = f"{field}_q{i + 1}"
            labels.append(bucket_id)
            lo, hi = edges[i], edges[i + 1]
            count = int(((train[field] >= lo) & (train[field] <= hi if i == len(q) - 2 else train[field] < hi)).sum()) if np.isfinite(hi) or np.isinf(hi) else 0
            rows.append(
                {
                    "bucket_field": field,
                    "bucket_id": bucket_id,
                    "quantile_low": q[i],
                    "quantile_high": q[i + 1],
                    "value_low": lo,
                    "value_high": hi,
                    "train_row_count": count,
                    "merged_bucket_id": bucket_id,
                    "missing_bucket": False,
                    "status": "passed" if count >= int(config["matched_controls"]["min_train_rows_per_bucket"]) else "failed",
                }
            )
        rows.append(
            {
                "bucket_field": field,
                "bucket_id": f"{field}_missing",
                "quantile_low": np.nan,
                "quantile_high": np.nan,
                "value_low": np.nan,
                "value_high": np.nan,
                "train_row_count": int(train[field].isna().sum()),
                "merged_bucket_id": f"{field}_missing",
                "missing_bucket": True,
                "status": "passed",
            }
        )
        frames.append(pd.DataFrame(rows))
        bucket_col = "liquidity_bucket" if field == config["matched_controls"]["liquidity_field"] else "volatility_bucket"
        bucketed[bucket_col] = f"{field}_missing"
        for i, label in enumerate(labels):
            lo, hi = edges[i], edges[i + 1]
            if i == len(labels) - 1:
                mask = bucketed[field].notna() & (bucketed[field] >= lo) & (bucketed[field] <= hi)
            else:
                mask = bucketed[field].notna() & (bucketed[field] >= lo) & (bucketed[field] < hi)
            bucketed.loc[mask, bucket_col] = label
    freeze = pd.concat(frames, ignore_index=True)
    return freeze, bucketed


def build_baseline_inputs(
    episodes: pd.DataFrame,
    stock: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    reference: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    candidate = episodes.loc[(episodes["seed_family_id"].eq(CANDIDATE_SEED_ID)) & (episodes["executable_status"].eq("passed"))].copy()
    ep2 = episodes.loc[(episodes["seed_family_id"].eq(EP2_SEED_ID)) & (episodes["executable_status"].eq("passed"))].copy()
    candidate = enrich_episode_for_sim(candidate)
    ep2 = enrich_episode_for_sim(ep2)
    stock_key = stock.set_index(["instrument", "date"])
    out: dict[str, pd.DataFrame] = {
        "same_seed_no_fail_fast_hold_h20": _same_seed_rows(candidate),
        "ep2_detector_probe_with_simple_stop_bridge": _ep2_bridge_rows(ep2),
    }
    for delay in [1, 3]:
        delay_rows = _matched_delay_rows(candidate, stock_key, config, calendar, reference, delay)
        out[f"same_seed_matched_delay_{delay}d_same_fail_fast_h20"] = delay_rows.copy()
        out[f"same_seed_matched_delay_{delay}d_no_fail_fast_h20"] = delay_rows.copy()
    random_rows = _matched_random_rows(candidate, stock, config, calendar, reference)
    out["matched_random_same_density_same_fail_fast_h20"] = random_rows.copy()
    out["matched_random_same_density_no_fail_fast_h20"] = random_rows.copy()
    return out


def _same_seed_rows(candidate: pd.DataFrame) -> pd.DataFrame:
    rows = candidate.copy()
    rows["signal_date"] = rows["episode_start_signal_date"]
    rows["primary_metric_eligible_baseline_event"] = rows["primary_metric_eligible_seed_episode"]
    rows["matched_control_type"] = "same_seed"
    rows["fail_fast_policy"] = "no_fail_fast"
    rows["structural_reference_policy"] = "same_seed_references"
    rows["replicate_id"] = 0
    rows["match_year"] = pd.to_datetime(rows["episode_start_signal_date"]).dt.year
    rows["match_industry"] = "all"
    rows["match_liquidity_bucket"] = "all"
    rows["match_volatility_bucket"] = "all"
    return rows


def _ep2_bridge_rows(ep2: pd.DataFrame) -> pd.DataFrame:
    rows = ep2.copy()
    rows["signal_date"] = rows["episode_start_signal_date"]
    rows["primary_metric_eligible_baseline_event"] = rows["primary_metric_eligible_seed_episode"]
    rows["matched_control_type"] = "ep2_bridge"
    rows["fail_fast_policy"] = "ep2_probe_with_simple_stop_bridge"
    rows["structural_reference_policy"] = "ep2_detector_reconstructed_references"
    rows["replicate_id"] = 0
    rows["match_year"] = pd.to_datetime(rows["episode_start_signal_date"]).dt.year
    rows["match_industry"] = "all"
    rows["match_liquidity_bucket"] = "all"
    rows["match_volatility_bucket"] = "all"
    return rows


def _matched_delay_rows(
    candidate: pd.DataFrame,
    stock_key: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    reference: pd.DataFrame,
    delay: int,
) -> pd.DataFrame:
    min_risk = float(config["risk_normalization"]["min_initial_risk_pct"])
    max_risk = float(config["risk_normalization"]["max_initial_risk_pct"])
    records: list[dict[str, Any]] = []
    for _, ep in candidate.iterrows():
        entry_date = _date(ep["episode_effective_entry_date"])
        delayed_entry_date = base.add_trading_days(calendar, entry_date, delay)
        rec = ep.to_dict()
        rec["signal_date"] = ep["episode_start_signal_date"]
        rec["entry_date"] = _date_str(delayed_entry_date)
        rec["delay_days"] = delay
        rec["matched_control_type"] = "matched_delay"
        rec["replicate_id"] = 0
        rec["primary_metric_eligible_baseline_event"] = bool(ep["primary_metric_eligible_seed_episode"])
        rec["fail_fast_policy"] = "same_fail_fast"
        rec["structural_reference_policy"] = "carried_original_seed_references"
        rec["match_year"] = _date(ep["episode_start_signal_date"]).year
        rec["match_industry"] = "all"
        rec["match_liquidity_bucket"] = "all"
        rec["match_volatility_bucket"] = "all"
        rec["pre_sim_eligibility_status"] = "passed"
        rec["pre_sim_ineligibility_reason"] = ""
        if pd.isna(delayed_entry_date) or (ep["instrument"], delayed_entry_date) not in stock_key.index:
            rec["entry_price"] = np.nan
            rec["initial_structural_stop"] = np.nan
            rec["initial_risk_pct"] = np.nan
            rec["delay_period_return_pct"] = np.nan
            rec["pre_sim_eligibility_status"] = "ineligible"
            rec["pre_sim_ineligibility_reason"] = "missing_delayed_entry"
        else:
            delayed = stock_key.loc[(ep["instrument"], delayed_entry_date)]
            entry_price = _safe_float(delayed.get("open"))
            stop, risk_pct, risk_status = closest_stop_below(
                entry_price,
                [_safe_float(ep["seed_day_low"]), _safe_float(ep["breakout_reference"]), _safe_float(ep["pivot_low_10d"])],
                min_risk,
                max_risk,
            )
            rec["entry_price"] = entry_price
            rec["initial_structural_stop"] = stop
            rec["initial_risk_pct"] = risk_pct
            rec["delay_period_return_pct"] = entry_price / _safe_float(ep["entry_price"]) - 1.0 if _safe_float(ep["entry_price"]) > 0 and np.isfinite(entry_price) else np.nan
            if risk_status != "passed":
                rec["pre_sim_eligibility_status"] = "ineligible"
                rec["pre_sim_ineligibility_reason"] = risk_status
        rec["delay_period_return_bucket"] = ""
        records.append(rec)
    rows = pd.DataFrame(records)
    if rows.empty:
        return rows
    rows["delay_period_return_bucket"] = _qbucket(rows["delay_period_return_pct"], 5, "delay_return")
    all_rate = float(rows["pre_sim_eligibility_status"].ne("passed").mean()) if len(rows) else 0.0
    top_mask = rows["delay_period_return_bucket"].eq("delay_return_q5")
    top_rate = float(rows.loc[top_mask, "pre_sim_eligibility_status"].ne("passed").mean()) if top_mask.any() else 0.0
    status = "failed" if top_rate >= 2.0 * all_rate and top_rate >= 0.20 else "passed"
    rows["matched_delay_reliability_status"] = status
    return rows


def _matched_random_rows(
    candidate: pd.DataFrame,
    stock: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    reference: pd.DataFrame,
) -> pd.DataFrame:
    if candidate.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(int(config["matched_controls"]["random_seed"]))
    reps = int(config["matched_controls"]["random_replicates_per_split"])
    min_risk = float(config["risk_normalization"]["min_initial_risk_pct"])
    max_risk = float(config["risk_normalization"]["max_initial_risk_pct"])
    seed_stock_days = set(zip(candidate["instrument"].astype(str), pd.to_datetime(candidate["episode_start_signal_date"]).dt.normalize()))
    stock_pool = stock.loc[stock["split"].isin(["train", "validation", "robustness"]) & stock["eligible_stock_day"].astype(bool)].copy()
    stock_pool["is_candidate_seed_stock_day"] = [item in seed_stock_days for item in zip(stock_pool["instrument"].astype(str), stock_pool["date"])]
    stock_pool = stock_pool.loc[~stock_pool["is_candidate_seed_stock_day"]].copy()

    stock_key = stock.set_index(["instrument", "date"])
    capture_map: dict[int, tuple[str, str]] = {}
    stock_pool_by_inst = {inst: group for inst, group in stock_pool.groupby("instrument", sort=False)}
    for ref in reference.itertuples(index=False):
        inst = str(ref.instrument).upper()
        if inst not in stock_pool_by_inst:
            continue
        ref_date = _date(ref.reference_date)
        start = base.add_trading_days(calendar, ref_date, -20)
        if pd.isna(start):
            start = ref_date
        group = stock_pool_by_inst[inst]
        hit_idx = group.loc[(group["date"] >= start) & (group["date"] <= ref_date)].index
        for idx in hit_idx:
            capture_map.setdefault(int(idx), (str(ref.reference_event_id), "primary_-20_0"))

    candidate = candidate.copy().reset_index(drop=True)
    candidate["match_year"] = pd.to_datetime(candidate["episode_start_signal_date"]).dt.year
    candidate["match_industry"] = "UNKNOWN"
    candidate["match_liquidity_bucket"] = "missing"
    candidate["match_volatility_bucket"] = "missing"
    for idx, ep in candidate.iterrows():
        sig = _date(ep["episode_start_signal_date"])
        key = (ep["instrument"], sig)
        if key in stock_key.index:
            s = stock_key.loc[key]
            candidate.loc[idx, "match_industry"] = s.get("industry_name", "UNKNOWN")
            candidate.loc[idx, "match_liquidity_bucket"] = s.get("liquidity_bucket", "missing")
            candidate.loc[idx, "match_volatility_bucket"] = s.get("volatility_bucket", "missing")

    records: list[pd.DataFrame] = []
    effective_end = {split: _effective_end_for_split(config, split, calendar, stock) for split in ["train", "validation", "robustness"]}
    key_cols = ["split", "match_year", "match_industry", "match_liquidity_bucket", "match_volatility_bucket"]
    pool_key_cols = ["split", "year", "industry_name", "liquidity_bucket", "volatility_bucket"]
    pool_by_key = {key: group for key, group in stock_pool.groupby(pool_key_cols, dropna=False, sort=False)}
    for key, key_candidates in candidate.groupby(key_cols, dropna=False, sort=False):
        split = key[0]
        pool_key = (key[0], key[1], key[2], key[3], key[4])
        pool = pool_by_key.get(pool_key, pd.DataFrame())
        n = len(key_candidates)
        if n == 0:
            continue
        carried_base = key_candidates.reset_index(drop=True).copy()
        shortfall = pool.empty or len(pool) < n
        pool_indices = pool.index.to_numpy()
        sampled_blocks: list[np.ndarray] = []
        for _rep in range(reps):
            if pool.empty:
                sampled_blocks.append(np.full(n, -1, dtype=int))
            elif len(pool) >= n:
                sampled_blocks.append(rng.choice(pool_indices, size=n, replace=False).astype(int))
            else:
                block = np.full(n, -1, dtype=int)
                block[: len(pool_indices)] = rng.permutation(pool_indices).astype(int)
                sampled_blocks.append(block)
        sampled_idx = np.concatenate(sampled_blocks)
        sampled = stock_pool.reindex(sampled_idx).reset_index(drop=False)
        sampled["index"] = sampled_idx
        carried = carried_base.iloc[np.tile(np.arange(n), reps)].reset_index(drop=True).copy()
        replicate_ids = np.repeat(np.arange(1, reps + 1), n)
        component = carried["price_structure_component"].astype(str).to_numpy()
        with np.errstate(invalid="ignore"):
            breakout = np.where(
                component == "close_near_60d_high",
                sampled["breakout_reference_near60"].astype(float).to_numpy(),
                sampled["breakout_reference_break40"].astype(float).to_numpy(),
            )
            entry_price = sampled["next_open"].astype(float).to_numpy()
            stop_candidates = np.vstack(
                [
                    sampled["seed_day_low"].astype(float).to_numpy(),
                    breakout.astype(float),
                    sampled["pivot_low_10d"].astype(float).to_numpy(),
                ]
            )
            valid_stops = np.where(np.isfinite(stop_candidates) & (stop_candidates < entry_price), stop_candidates, -np.inf)
            initial_stop = valid_stops.max(axis=0)
            initial_stop = np.where(np.isfinite(initial_stop), initial_stop, np.nan)
            risk_pct = (entry_price - initial_stop) / entry_price
        risk_status = np.where(
            ~np.isfinite(initial_stop),
            "no_valid_stop_below_entry",
            np.where(risk_pct < min_risk, "risk_distance_below_min", np.where(risk_pct > max_risk, "risk_distance_above_max", "passed")),
        )
        buy_ok = sampled["is_buy_executable_next_open"].fillna(False).astype(bool).to_numpy()
        pre_status = np.where((risk_status == "passed") & buy_ok, "passed", "ineligible")
        pre_reason = np.where(risk_status != "passed", risk_status, np.where(buy_ok, "", sampled["blocked_buy_reason"].astype(str).to_numpy()))
        random_dates = pd.to_datetime(sampled["date"]).dt.normalize()
        frame = carried.copy()
        frame["replicate_id"] = replicate_ids
        frame["matched_control_type"] = "matched_random"
        frame["fail_fast_policy"] = "same_fail_fast"
        frame["structural_reference_policy"] = "pseudo_event_recomputed_references"
        frame["carried_seed_episode_id"] = carried["seed_episode_id"]
        frame["seed_episode_id"] = ""
        sampled_indices = sampled["index"].fillna(-1).astype(float).astype(int).to_numpy()
        frame["random_event_id"] = [
            f"random_{split}_{rep}_{idx}" if idx >= 0 else f"random_shortfall_{split}_{rep}_{i}"
            for i, (rep, idx) in enumerate(zip(replicate_ids, sampled_indices), start=1)
        ]
        frame["instrument"] = sampled["instrument"].astype(str).replace("nan", "").to_numpy()
        frame["random_signal_date"] = random_dates.dt.strftime("%Y-%m-%d").fillna("").to_numpy()
        frame["signal_date"] = frame["random_signal_date"]
        frame["entry_date"] = pd.to_datetime(sampled["next_date"]).dt.strftime("%Y-%m-%d").fillna("").to_numpy()
        frame["entry_price"] = entry_price
        frame["seed_day_low"] = sampled["seed_day_low"].astype(float).to_numpy()
        frame["breakout_reference"] = breakout
        frame["pivot_low_10d"] = sampled["pivot_low_10d"].astype(float).to_numpy()
        frame["initial_structural_stop"] = initial_stop
        frame["initial_risk_pct"] = risk_pct
        captured_info = [capture_map.get(int(idx), ("", "")) for idx in sampled_indices]
        frame["primary_metric_eligible_baseline_event"] = random_dates.le(effective_end[split]).fillna(False).to_numpy()
        frame["captures_primary_big_winner"] = [bool(item[0]) for item in captured_info]
        frame["captured_reference_event_id"] = [item[0] for item in captured_info]
        frame["capture_window_id"] = [item[1] for item in captured_info]
        frame["random_sampling_replacement_policy"] = "without_replacement_within_replicate"
        frame["random_capacity_shortfall"] = bool(shortfall)
        frame["random_baseline_reliability_status"] = "pending"
        frame["pre_sim_eligibility_status"] = np.where(sampled_indices < 0, "ineligible", pre_status)
        frame["pre_sim_ineligibility_reason"] = np.where(sampled_indices < 0, "random_capacity_shortfall", pre_reason)
        records.append(frame)
    rows = pd.concat(records, ignore_index=True) if records else pd.DataFrame()
    if rows.empty:
        return rows
    split_health = rows.groupby("split")["pre_sim_eligibility_status"].apply(lambda s: float(s.eq("passed").mean())).to_dict()
    shortfall = rows.groupby("split")["random_capacity_shortfall"].any().to_dict()
    rows["random_baseline_reliability_status"] = rows["split"].map(
        lambda split: "passed" if split_health.get(split, 0.0) >= float(config["matched_controls"]["random_min_split_eligible_rate"]) and not shortfall.get(split, False) else "failed"
    )
    return rows


def _effective_end_for_split(config: dict[str, Any], split: str, calendar: pd.DatetimeIndex, stock: pd.DataFrame) -> pd.Timestamp:
    data_max = pd.to_datetime(stock["date"]).max()
    windows, _ = split_effective_windows(config, calendar, data_max)
    return windows.get(split, (pd.NaT, pd.NaT))[1]


def _qbucket(series: pd.Series, q: int, prefix: str) -> pd.Series:
    out = pd.Series(f"{prefix}_missing", index=series.index, dtype=object)
    valid = series.dropna()
    if valid.empty:
        return out
    try:
        buckets = pd.qcut(valid.rank(method="first"), q=q, labels=[f"{prefix}_q{i}" for i in range(1, q + 1)])
        out.loc[valid.index] = buckets.astype(str)
    except ValueError:
        out.loc[valid.index] = f"{prefix}_q1"
    return out


def apply_label_flags(episodes: pd.DataFrame, label_a: pd.DataFrame) -> pd.DataFrame:
    out = episodes.copy()
    out["label_a_h10_negative"] = False
    out["label_a_h20_negative"] = False
    if label_a.empty:
        return out
    h10 = label_a.loc[label_a["label_id"].eq("seed_quality_triple_barrier_atr_h10_u1_5_d1_0")].set_index("seed_episode_id")["label_value"]
    h20 = label_a.loc[label_a["label_id"].eq("seed_quality_triple_barrier_atr_h20_u2_0_d1_0")].set_index("seed_episode_id")["label_value"]
    out["label_a_h10_negative"] = out["seed_episode_id"].map(h10).fillna(1.0).astype(float).le(0)
    out["label_a_h20_negative"] = out["seed_episode_id"].map(h20).fillna(1.0).astype(float).le(0)
    return out


def build_density_audits(stock: pd.DataFrame, episodes: pd.DataFrame, seed_events: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    eligible = stock.loc[stock["eligible_stock_day"].astype(bool)]
    eligible_inst_year = (
        eligible.groupby(["split", "instrument", "year"]).size().reset_index(name="eligible_stock_days")
    )
    eligible_inst_year = eligible_inst_year.loc[eligible_inst_year["eligible_stock_days"] >= int(config["density_denominator"]["eligible_instrument_year_requires_min_stock_days"])]
    for split in ["train", "validation", "robustness"]:
        denom_days = int(eligible.loc[eligible["split"].eq(split)].shape[0])
        denom_iy = int(eligible_inst_year.loc[eligible_inst_year["split"].eq(split), ["instrument", "year"]].drop_duplicates().shape[0])
        for family in [CANDIDATE_SEED_ID, EP2_SEED_ID]:
            event_count = int(seed_events.loc[(seed_events["seed_family_id"].eq(family)) & (seed_events["split"].eq(split)) & (seed_events["hard_filter_status"].eq("passed"))].shape[0])
            ep = episodes.loc[(episodes["seed_family_id"].eq(family)) & (episodes["split"].eq(split))]
            episode_count = int(ep.shape[0])
            unique_iy = int(ep.assign(year=pd.to_datetime(ep["episode_start_signal_date"]).dt.year)[["instrument", "year"]].drop_duplicates().shape[0]) if not ep.empty else 0
            rows.append(
                {
                    "split": split,
                    "seed_family_id": family,
                    "eligible_stock_day_count": denom_days,
                    "eligible_instrument_year_count": denom_iy,
                    "executable_seed_stock_day_count": event_count,
                    "seed_episode_count": episode_count,
                    "seed_day_rate": _safe_div(event_count, denom_days, 0.0),
                    "seed_episode_rate": _safe_div(episode_count, denom_iy, 0.0),
                    "unique_instrument_count": int(ep["instrument"].nunique()) if not ep.empty else 0,
                    "unique_instrument_year_count": unique_iy,
                    "suppressed_reentry_count": int(ep["suppressed_reentry_count"].sum()) if not ep.empty else 0,
                    "next_open_buy_executable_rate": float(seed_events.loc[(seed_events["seed_family_id"].eq(family)) & (seed_events["split"].eq(split)), "next_open_buy_executable"].mean()) if not seed_events.loc[(seed_events["seed_family_id"].eq(family)) & (seed_events["split"].eq(split))].empty else np.nan,
                    "limit_up_unbuyable_reject_count": int(seed_events.loc[(seed_events["seed_family_id"].eq(family)) & (seed_events["split"].eq(split)) & (seed_events["buy_block_reason"].eq("limit_up_inferred"))].shape[0]),
                    "risk_distance_ineligible_count": int(ep.loc[ep["risk_distance_status"].ne("passed")].shape[0]) if not ep.empty else 0,
                }
            )
    density = pd.DataFrame(rows)
    ep2_by_split = density.loc[density["seed_family_id"].eq(EP2_SEED_ID)].set_index("split")
    for col in ["seed_day_rate", "seed_episode_rate", "executable_seed_stock_day_count", "seed_episode_count"]:
        density[f"{col}_vs_ep2"] = density.apply(lambda row: _safe_div(row[col], ep2_by_split.loc[row["split"], col], np.nan) if row["split"] in ep2_by_split.index else np.nan, axis=1)
    tight_rows: list[dict[str, Any]] = []
    candidate = density.loc[density["seed_family_id"].eq(CANDIDATE_SEED_ID)].set_index("split")
    ep2 = density.loc[density["seed_family_id"].eq(EP2_SEED_ID)].set_index("split")
    for split in ["train", "validation", "robustness"]:
        if split not in candidate.index or split not in ep2.index:
            continue
        day_cap = min(float(config["seed_density_caps"]["max_candidate_seed_day_rate"]), float(config["seed_density_caps"]["max_candidate_seed_day_rate_vs_ep2_multiple"]) * float(ep2.loc[split, "seed_day_rate"]))
        ep_cap = float(config["seed_density_caps"]["max_candidate_episode_rate_vs_ep2_multiple"]) * float(ep2.loc[split, "seed_episode_rate"])
        tight_rows.append(
            {
                "split": split,
                "year": "all",
                "industry": "all",
                "liquidity_bucket": "all",
                "volatility_bucket": "all",
                "candidate_seed_day_rate": candidate.loc[split, "seed_day_rate"],
                "candidate_seed_episode_rate": candidate.loc[split, "seed_episode_rate"],
                "seed_day_cap": day_cap,
                "seed_episode_cap": ep_cap,
                "seed_day_cap_utilization": _safe_div(candidate.loc[split, "seed_day_rate"], day_cap, np.nan),
                "seed_episode_cap_utilization": _safe_div(candidate.loc[split, "seed_episode_rate"], ep_cap, np.nan),
                "cap_violation_flag": bool(candidate.loc[split, "seed_day_rate"] > day_cap or candidate.loc[split, "seed_episode_rate"] > ep_cap),
                "forward_return_p50": np.nan,
                "failed_seed_average_loss_r": np.nan,
                "audit_only_status": "report_only",
            }
        )
    return density, pd.DataFrame(tight_rows)


def build_recall_audit(reference: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    executable = episodes.loc[episodes["executable_status"].eq("passed") & episodes["primary_metric_eligible_seed_episode"].astype(bool)].copy()
    for split in ["train", "validation", "robustness"]:
        ref_split = reference.loc[reference["split"].eq(split)]
        ref_count = int(ref_split.shape[0])
        for family in [CANDIDATE_SEED_ID, EP2_SEED_ID]:
            fam = executable.loc[(executable["seed_family_id"].eq(family)) & (executable["split"].eq(split))]
            captured = set(fam.loc[fam["captures_primary_big_winner"].astype(bool), "captured_reference_event_id"].astype(str))
            rows.append(
                {
                    "split": split,
                    "seed_family_id": family,
                    "reference_type": "primary_big_winner_50h120_close_confirmed",
                    "big_winner_reference_count": ref_count,
                    "captured_big_winner_count": len(captured),
                    "missed_big_winner_count": max(0, ref_count - len(captured)),
                    "primary_big_winner_seed_recall": _safe_div(len(captured), ref_count, 0.0),
                    "bridge_ep2_big_winner_seed_recall": np.nan,
                    "late_capture_0_to_10_count": 0,
                }
            )
    recall = pd.DataFrame(rows)
    ep2 = recall.loc[recall["seed_family_id"].eq(EP2_SEED_ID)].set_index("split")
    recall["seed_recall_diff_vs_ep2_detector"] = recall.apply(
        lambda row: float(row["primary_big_winner_seed_recall"]) - float(ep2.loc[row["split"], "primary_big_winner_seed_recall"]) if row["split"] in ep2.index else np.nan,
        axis=1,
    )
    return recall


def summarize_population(df: pd.DataFrame, failed_col: str, prefix: str = "") -> dict[str, float]:
    eligible = df.loc[df["eligibility_status"].eq("passed")] if "eligibility_status" in df else df.copy()
    failed = eligible.loc[eligible[failed_col].astype(str).isin(["True", "true", "1"])] if failed_col in eligible else eligible.iloc[0:0]
    returns = eligible["return_r"].dropna().astype(float) if "return_r" in eligible else pd.Series(dtype=float)
    losses = failed["loss_r"].dropna().astype(float) if "loss_r" in failed else pd.Series(dtype=float)
    return {
        f"{prefix}mean_return_r": float(returns.mean()) if len(returns) else np.nan,
        f"{prefix}median_return_r": float(returns.median()) if len(returns) else np.nan,
        f"{prefix}p05_return_r": float(returns.quantile(0.05)) if len(returns) else np.nan,
        f"{prefix}p95_return_r": float(returns.quantile(0.95)) if len(returns) else np.nan,
        f"{prefix}positive_return_rate": float((returns > 0).mean()) if len(returns) else np.nan,
        f"{prefix}payoff_skew": float(returns.skew()) if len(returns) > 2 else np.nan,
        f"{prefix}right_tail_contribution_share": _safe_div(float(returns.loc[returns > 0].sum()), float(returns.abs().sum()), np.nan) if len(returns) else np.nan,
        f"{prefix}failed_seed_average_loss_r": float(losses.mean()) if len(losses) else 0.0,
        f"{prefix}failed_seed_median_loss_r": float(losses.median()) if len(losses) else 0.0,
        f"{prefix}failed_seed_median_holding_days": float(failed["holding_days"].median()) if len(failed) else 0.0,
        f"{prefix}exposure_days_per_seed_episode": _safe_div(float(eligible["exposure_days"].sum()), float(len(eligible)), 0.0) if len(eligible) else 0.0,
    }


def build_recall_cost_tradeoff(episodes: pd.DataFrame, probe: pd.DataFrame, baseline: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    candidate_probe = probe.loc[probe["seed_family_id"].eq(CANDIDATE_SEED_ID)]
    ep2_bridge = baseline.loc[baseline["baseline_id"].eq("ep2_detector_probe_with_simple_stop_bridge")]
    for split in ["train", "validation", "robustness"]:
        cand = candidate_probe.loc[candidate_probe["split"].eq(split) & candidate_probe["primary_metric_eligible_seed_episode"].astype(bool)]
        ep2 = ep2_bridge.loc[ep2_bridge["split"].eq(split) & ep2_bridge["primary_metric_eligible_baseline_event"].astype(bool)]
        cand_failed = cand.loc[cand["failed_seed_primary"].astype(str).isin(["True", "true", "1"])]
        ep2_failed = ep2.loc[ep2["baseline_failed_seed_primary"].astype(str).isin(["True", "true", "1"])]
        cand_loss = float(cand_failed["loss_r"].fillna(0).sum())
        ep2_loss = float(ep2_failed["loss_r"].fillna(0).sum())
        inc_loss = max(0.0, cand_loss - ep2_loss)
        cand_refs = set(episodes.loc[(episodes["seed_family_id"].eq(CANDIDATE_SEED_ID)) & (episodes["split"].eq(split)) & episodes["primary_metric_eligible_seed_episode"].astype(bool) & episodes["captures_primary_big_winner"].astype(bool), "captured_reference_event_id"].astype(str))
        ep2_refs = set(episodes.loc[(episodes["seed_family_id"].eq(EP2_SEED_ID)) & (episodes["split"].eq(split)) & episodes["primary_metric_eligible_seed_episode"].astype(bool) & episodes["captures_primary_big_winner"].astype(bool), "captured_reference_event_id"].astype(str))
        overlap = cand_refs & ep2_refs
        added = cand_refs - ep2_refs
        lost = ep2_refs - cand_refs
        net = len(added) - len(lost)
        cand_exposure = float(cand_failed["exposure_days"].fillna(0).sum())
        ep2_exposure = float(ep2_failed["exposure_days"].fillna(0).sum())
        inc_exposure = max(0.0, cand_exposure - ep2_exposure)
        max_loss = float(config["recall_cost_gate"]["max_incremental_loss_r_per_added_big_winner_vs_ep2"]) if split != "robustness" else float(config["recall_cost_gate"]["robustness_max_incremental_loss_r_per_added_big_winner_vs_ep2"])
        max_exposure = float(config["recall_cost_gate"]["max_incremental_exposure_days_per_added_big_winner_vs_ep2"]) if split != "robustness" else float(config["recall_cost_gate"]["robustness_max_incremental_exposure_days_per_added_big_winner_vs_ep2"])
        rows.append(
            {
                "split": split,
                "candidate_total_failed_loss_r": cand_loss,
                "ep2_total_failed_loss_r": ep2_loss,
                "incremental_abs_failed_loss_r_vs_ep2": inc_loss,
                "candidate_captured_reference_count": len(cand_refs),
                "ep2_captured_reference_count": len(ep2_refs),
                "overlap_captured_reference_count": len(overlap),
                "added_capture_vs_ep2_count": len(added),
                "lost_capture_vs_ep2_count": len(lost),
                "net_added_capture_vs_ep2_count": net,
                "late_capture_0_to_10_count": 0,
                "recall_cost_score": _safe_div(net, max(1.0, inc_loss), 0.0),
                "incremental_loss_r_per_added_big_winner_vs_ep2": _safe_div(inc_loss, max(1, net), np.inf),
                "incremental_exposure_days_per_added_big_winner_vs_ep2": _safe_div(inc_exposure, max(1, net), np.inf),
                "max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2": max_loss,
                "max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2": max_exposure,
                "decision_support_status": "passed" if net > 0 and _safe_div(inc_loss, max(1, net), np.inf) <= max_loss and _safe_div(inc_exposure, max(1, net), np.inf) <= max_exposure else "failed",
            }
        )
    return pd.DataFrame(rows)


def build_baseline_diff_audit(probe: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    candidate = probe.loc[probe["seed_family_id"].eq(CANDIDATE_SEED_ID)]
    for split in ["train", "validation", "robustness"]:
        cand = candidate.loc[candidate["split"].eq(split)]
        cand_summary = summarize_population(cand, "failed_seed_primary")
        for baseline_id, base_df in baseline.loc[baseline["split"].eq(split)].groupby("baseline_id"):
            if baseline_id.startswith("matched_random"):
                base_groups = [("p50", base_df)]
            else:
                base_groups = [("not_random", base_df)]
            for stat, bdf in base_groups:
                base_summary = summarize_population(bdf, "baseline_failed_seed_primary")
                for metric in ["mean_return_r", "p05_return_r", "failed_seed_average_loss_r", "failed_seed_median_holding_days"]:
                    cand_value = cand_summary.get(metric, np.nan)
                    base_value = base_summary.get(metric, np.nan)
                    rows.append(
                        {
                            "split": split,
                            "baseline_id": baseline_id,
                            "baseline_role": "gate" if any(token in baseline_id for token in ["same_fail_fast", "no_fail_fast", "ep2_detector"]) else "audit",
                            "metric_name": f"{metric}_diff_vs_{baseline_id}",
                            "candidate_value": cand_value,
                            "baseline_value": base_value,
                            "diff_value": cand_value - base_value if np.isfinite(cand_value) and np.isfinite(base_value) else np.nan,
                            "random_replicate_stat": stat,
                            "comparison": "",
                            "threshold": np.nan,
                            "status": "report_only",
                        }
                    )
    return pd.DataFrame(rows)


def build_random_health_audit(baseline: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    random_df = baseline.loc[baseline["matched_control_type"].eq("matched_random")]
    for keys, group in random_df.groupby(["split", "baseline_id", "match_industry", "match_liquidity_bucket", "match_volatility_bucket"], dropna=False):
        split, baseline_id, industry, liq, vol = keys
        sampled = len(group)
        eligible = int(group["eligibility_status"].eq("passed").sum())
        rate = _safe_div(eligible, sampled, 0.0)
        rep_count = int(group["replicate_id"].nunique())
        shortfall = bool(group["random_capacity_shortfall"].astype(bool).any())
        status = "passed" if rate >= float(config["matched_controls"]["random_min_bucket_eligible_rate"]) and rep_count >= int(config["matched_controls"]["random_replicates_per_split"]) and not shortfall else "failed"
        returns = group.loc[group["eligibility_status"].eq("passed"), "return_r"].dropna().astype(float)
        losses = group.loc[group["baseline_failed_seed_primary"].astype(str).isin(["True", "true", "1"]), "loss_r"].dropna().astype(float)
        rows.append(
            {
                "split": split,
                "baseline_id": baseline_id,
                "replicate_stat": "p50",
                "industry": industry,
                "liquidity_bucket": liq,
                "volatility_bucket": vol,
                "sampled_random_event_count": sampled,
                "eligible_random_event_count": eligible,
                "bucket_random_eligible_rate": rate,
                "random_replicate_count": rep_count,
                "random_excluded_candidate_seed_day_count": 0,
                "random_capacity_shortfall": shortfall,
                "random_sampling_replacement_policy": "without_replacement_within_replicate",
                "random_baseline_reliability_status": status,
                "failed_seed_average_loss_r": float(losses.mean()) if len(losses) else 0.0,
                "p05_return_r": float(returns.quantile(0.05)) if len(returns) else np.nan,
                "p50_return_r": float(returns.quantile(0.50)) if len(returns) else np.nan,
                "p95_return_r": float(returns.quantile(0.95)) if len(returns) else np.nan,
                "audit_only_status": "report_only",
            }
        )
    if not rows:
        return pd.DataFrame(columns=["split", "baseline_id", "replicate_stat", "industry", "liquidity_bucket", "volatility_bucket", "sampled_random_event_count", "eligible_random_event_count", "bucket_random_eligible_rate", "random_replicate_count", "random_excluded_candidate_seed_day_count", "random_capacity_shortfall", "random_sampling_replacement_policy", "random_baseline_reliability_status", "failed_seed_average_loss_r", "p05_return_r", "p50_return_r", "p95_return_r", "audit_only_status"])
    return pd.DataFrame(rows)


def build_delay_ineligible_audit(baseline: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    delay_df = baseline.loc[baseline["matched_control_type"].eq("matched_delay")]
    for (split, delay), group in delay_df.groupby(["split", "delay_days"], dropna=False):
        all_rate = float(group["eligibility_status"].ne("passed").mean()) if len(group) else 0.0
        top = group.loc[group["delay_period_return_bucket"].eq("delay_return_q5")]
        top_rate = float(top["eligibility_status"].ne("passed").mean()) if len(top) else 0.0
        status = "failed" if top_rate >= 2.0 * all_rate and top_rate >= 0.20 else "passed"
        for bucket, bdf in group.groupby("delay_period_return_bucket", dropna=False):
            rows.append(
                {
                    "split": split,
                    "delay_days": delay,
                    "delay_period_return_bucket": bucket,
                    "candidate_row_count": len(bdf),
                    "matched_delay_ineligible_count": int(bdf["eligibility_status"].ne("passed").sum()),
                    "matched_delay_ineligible_rate": float(bdf["eligibility_status"].ne("passed").mean()) if len(bdf) else 0.0,
                    "all_delay_ineligible_rate": all_rate,
                    "top_quintile_ineligible_rate": top_rate,
                    "matched_delay_reliability_status": status,
                    "audit_only_status": "report_only",
                }
            )
    return pd.DataFrame(rows)


def build_r_unit_distribution_audit(probe: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    populations = [("candidate", probe.loc[probe["seed_family_id"].eq(CANDIDATE_SEED_ID)])]
    populations.append(("ep2_bridge", baseline.loc[baseline["baseline_id"].eq("ep2_detector_probe_with_simple_stop_bridge")]))
    populations.append(("matched_delay", baseline.loc[baseline["matched_control_type"].eq("matched_delay")]))
    populations.append(("matched_random", baseline.loc[baseline["matched_control_type"].eq("matched_random")]))
    for split in ["train", "validation", "robustness"]:
        for name, frame in populations:
            df = frame.loc[frame["split"].eq(split)].copy()
            if df.empty:
                continue
            for budget in [0.10, 0.25, 0.50]:
                scale = budget / 0.25
                returns = df["return_r"].dropna().astype(float) * scale
                risks = df["initial_risk_pct"].dropna().astype(float)
                losses = df["loss_r"].fillna(0).astype(float) * scale
                total_loss = float(losses.sum())
                row = {
                    "split": split,
                    "population": name,
                    "probe_r_budget": budget,
                    "initial_risk_pct_p01": float(risks.quantile(0.01)) if len(risks) else np.nan,
                    "initial_risk_pct_p05": float(risks.quantile(0.05)) if len(risks) else np.nan,
                    "initial_risk_pct_p25": float(risks.quantile(0.25)) if len(risks) else np.nan,
                    "initial_risk_pct_median": float(risks.median()) if len(risks) else np.nan,
                    "initial_risk_pct_p75": float(risks.quantile(0.75)) if len(risks) else np.nan,
                    "initial_risk_pct_p95": float(risks.quantile(0.95)) if len(risks) else np.nan,
                    "initial_risk_pct_p99": float(risks.quantile(0.99)) if len(risks) else np.nan,
                    "return_r_p01": float(returns.quantile(0.01)) if len(returns) else np.nan,
                    "return_r_p99": float(returns.quantile(0.99)) if len(returns) else np.nan,
                    "loss_r_top1_share": _safe_div(float(losses.nlargest(1).sum()), total_loss, 0.0),
                    "loss_r_top5_share": _safe_div(float(losses.nlargest(5).sum()), total_loss, 0.0),
                    "near_risk_floor_extreme_loss_share": _safe_div(float(losses.loc[df["initial_risk_pct"].fillna(1.0) <= 0.021].sum()), total_loss, 0.0),
                    "risk_distance_ineligible_count": int(df["eligibility_status"].ne("passed").sum()) if "eligibility_status" in df else 0,
                    "initial_risk_pct_quintile": "all",
                    "quintile_failed_seed_count": int(df.get("failed_seed_primary", df.get("baseline_failed_seed_primary", pd.Series(False, index=df.index))).astype(str).isin(["True", "true", "1"]).sum()),
                    "quintile_failed_seed_average_loss_r": float(losses.mean()) if len(losses) else 0.0,
                    "quintile_baseline_failed_seed_average_loss_r": np.nan,
                    "quintile_loss_r_diff_vs_same_seed_no_fail_fast": np.nan,
                    "risk_pct_quintile_cost_control_status": "report_only",
                    "audit_only_status": "report_only",
                }
                rows.append(row)
    return pd.DataFrame(rows)


def build_fail_fast_audits(probe: pd.DataFrame, no_ff: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    path_rows: list[dict[str, Any]] = []
    err_rows: list[dict[str, Any]] = []
    no_ff_by_id = no_ff.set_index("seed_episode_id") if not no_ff.empty else pd.DataFrame()
    for _, row in probe.iterrows():
        if row["seed_family_id"] != CANDIDATE_SEED_ID:
            continue
        path_rows.append(
            {
                "split": row["split"],
                "seed_episode_id": row["seed_episode_id"],
                "instrument": row["instrument"],
                "exit_trigger_type": row["exit_trigger_type"],
                "exit_signal_date": row["exit_signal_date"],
                "exit_execution_date": row["exit_execution_date"],
                "holding_days": row["holding_days"],
                "return_r": row["return_r"],
                "loss_r": row["loss_r"],
                "audit_only_status": "report_only",
            }
        )
        noff_ret = np.nan
        if not no_ff_by_id.empty and row["seed_episode_id"] in no_ff_by_id.index:
            noff_ret = no_ff_by_id.loc[row["seed_episode_id"], "after_cost_return_pct"]
        if bool(row["failed_seed_fail_fast_triggered"]) and not bool(row["failed_seed_primary"]) and bool(row["primary_metric_eligible_seed_episode"]):
            err_type = "false_reject_winner"
        elif (not bool(row["failed_seed_fail_fast_triggered"])) and bool(row["failed_seed_primary"]) and np.isfinite(noff_ret) and noff_ret < 0:
            err_type = "missed_failure"
        else:
            continue
        err_rows.append(
            {
                "split": row["split"],
                "error_type": err_type,
                "seed_episode_id": row["seed_episode_id"],
                "instrument": row["instrument"],
                "episode_start_signal_date": "",
                "exit_trigger_type": row["exit_trigger_type"],
                "exit_signal_date": row["exit_signal_date"],
                "h20_after_cost_return": noff_ret,
                "return_r": row["return_r"],
                "loss_r": row["loss_r"],
                "captured_reference_event_id": "",
                "price_structure_component": "",
                "initial_risk_pct": row["initial_risk_pct"],
                "audit_only_status": "report_only",
            }
        )
    path = pd.DataFrame(path_rows)
    error = pd.DataFrame(err_rows)
    if error.empty:
        error = pd.DataFrame(columns=["split", "error_type", "seed_episode_id", "instrument", "episode_start_signal_date", "exit_trigger_type", "exit_signal_date", "h20_after_cost_return", "return_r", "loss_r", "captured_reference_event_id", "price_structure_component", "initial_risk_pct", "audit_only_status"])
    return path, error


def build_counterfactual(decision: str, probe: pd.DataFrame, density_tightness: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ["train", "validation", "robustness"]:
        split_probe = probe.loc[probe["split"].eq(split)]
        rows.append(
            {
                "split": split,
                "counterfactual_family": "fail_fast_window",
                "counterfactual_variant": "trigger_day_le_8_vs_9_12_descriptive",
                "primary_decision": decision,
                "decision_change_allowed": False,
                "metric_name": "fail_fast_triggered_count",
                "primary_value": int(split_probe["failed_seed_fail_fast_triggered"].astype(bool).sum()) if not split_probe.empty else 0,
                "counterfactual_value": np.nan,
                "diff_value": np.nan,
                "affected_episode_count": int(split_probe.shape[0]),
                "affected_reference_count": 0,
                "dominant_year": "none",
                "dominant_industry": "none",
                "dominant_bucket": "none",
                "inheritance_note": "report-only timing sensitivity; frozen R01 rule unchanged",
                "audit_only_status": "report_only_not_decision_changing",
            }
        )
        cap = density_tightness.loc[density_tightness["split"].eq(split)]
        rows.append(
            {
                "split": split,
                "counterfactual_family": "density_cap",
                "counterfactual_variant": "cap_violation_source_descriptive",
                "primary_decision": decision,
                "decision_change_allowed": False,
                "metric_name": "cap_violation_flag",
                "primary_value": bool(cap["cap_violation_flag"].any()) if not cap.empty else False,
                "counterfactual_value": np.nan,
                "diff_value": np.nan,
                "affected_episode_count": 0,
                "affected_reference_count": 0,
                "dominant_year": "none",
                "dominant_industry": "none",
                "dominant_bucket": "none",
                "inheritance_note": "report-only density diagnostic; no threshold trimming applied",
                "audit_only_status": "report_only_not_decision_changing",
            }
        )
    return pd.DataFrame(rows)


def _metric_from_density(density: pd.DataFrame, split: str, family: str, metric: str) -> float:
    row = density.loc[(density["split"].eq(split)) & (density["seed_family_id"].eq(family))]
    return _safe_float(row.iloc[0][metric]) if not row.empty and metric in row.columns else np.nan


def _recall_diff(recall: pd.DataFrame, split: str) -> float:
    row = recall.loc[(recall["split"].eq(split)) & (recall["seed_family_id"].eq(CANDIDATE_SEED_ID))]
    return _safe_float(row.iloc[0]["seed_recall_diff_vs_ep2_detector"]) if not row.empty else np.nan


def _diff_metric(diff: pd.DataFrame, split: str, baseline_id: str, metric_contains: str) -> float:
    rows = diff.loc[
        diff["split"].eq(split)
        & diff["baseline_id"].eq(baseline_id)
        & diff["metric_name"].str.contains(metric_contains, regex=False)
    ]
    return _safe_float(rows.iloc[0]["diff_value"]) if not rows.empty else np.nan


def build_gate_audit(
    authority: pd.DataFrame,
    density: pd.DataFrame,
    recall: pd.DataFrame,
    baseline_diff: pd.DataFrame,
    delay_audit: pd.DataFrame,
    random_health: pd.DataFrame,
    recall_cost: pd.DataFrame,
    probe: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []

    def add(gate_id: str, split: str, metric_name: str, value: Any, threshold: Any, comparison: str, status: bool, hard: bool = True, reason: str = "") -> None:
        rows.append(
            {
                "gate_id": gate_id,
                "split": split,
                "metric_name": metric_name,
                "metric_value": value,
                "threshold": threshold,
                "comparison": comparison,
                "status": "passed" if status else "failed",
                "is_hard_gate": bool(hard),
                "failure_reason": "" if status else (reason or "gate_failed"),
            }
        )

    add("authority_inputs_status", "all", "authority_inputs_status", "passed" if authority["status"].eq("passed").all() else "failed", "passed", "==", bool(authority["status"].eq("passed").all()))
    add("validation_threshold_selection_status", "validation", "validation_threshold_selection_status", "no_selection_from_validation", "no_selection_from_validation", "==", True)

    for split in ["train", "validation", "robustness"]:
        cand_day = _metric_from_density(density, split, CANDIDATE_SEED_ID, "seed_day_rate")
        ep2_day = _metric_from_density(density, split, EP2_SEED_ID, "seed_day_rate")
        cand_ep = _metric_from_density(density, split, CANDIDATE_SEED_ID, "seed_episode_rate")
        ep2_ep = _metric_from_density(density, split, EP2_SEED_ID, "seed_episode_rate")
        day_cap = min(float(config["seed_density_caps"]["max_candidate_seed_day_rate"]), 3.0 * ep2_day)
        ep_cap = 3.0 * ep2_ep
        add("seed_density_day_cap", split, "candidate_seed_day_rate", cand_day, day_cap, "<=", bool(np.isfinite(cand_day) and cand_day <= day_cap))
        add("seed_density_episode_cap", split, "candidate_seed_episode_rate", cand_ep, ep_cap, "<=", bool(np.isfinite(cand_ep) and cand_ep <= ep_cap))
        denom = _metric_from_density(density, split, CANDIDATE_SEED_ID, "eligible_stock_day_count")
        add("density_denominator_nonzero", split, "eligible_stock_day_count", denom, 0, ">", bool(np.isfinite(denom) and denom > 0))

    val_unique_iy = _metric_from_density(density, "validation", CANDIDATE_SEED_ID, "unique_instrument_year_count")
    add("validation_unique_instrument_years", "validation", "unique_instrument_year_count", val_unique_iy, config["seed_density_caps"]["min_unique_instrument_years_validation"], ">=", bool(val_unique_iy >= int(config["seed_density_caps"]["min_unique_instrument_years_validation"])))

    for split in ["validation", "robustness"]:
        threshold = -0.05 if split == "validation" else -0.10
        diff = _recall_diff(recall, split)
        add("primary_recall_no_harm", split, "primary_big_winner_seed_recall_diff_vs_ep2_detector", diff, threshold, ">=", bool(np.isfinite(diff) and diff >= threshold))

    add("validation_cost_vs_no_fail_fast", "validation", "failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast", _diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r"), 0, "<", bool(_diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r") < 0))
    add("validation_holding_days_vs_no_fail_fast", "validation", "failed_seed_median_holding_days_diff_vs_same_seed_no_fail_fast", _diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_median_holding_days"), 0, "<", bool(_diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_median_holding_days") < 0))
    add("validation_p05_vs_no_fail_fast", "validation", "p05_return_r_diff_vs_same_seed_no_fail_fast", _diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "p05_return_r"), -0.02, ">=", bool(_diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "p05_return_r") >= -0.02))

    delay_status = "passed" if delay_audit.empty or delay_audit["matched_delay_reliability_status"].eq("passed").all() else "failed"
    add("matched_delay_reliability_status", "validation", "matched_delay_reliability_status", delay_status, "passed", "==", delay_status == "passed")
    random_val = random_health.loc[random_health["split"].eq("validation")]
    random_status = "passed" if not random_val.empty and random_val["random_baseline_reliability_status"].eq("passed").all() else "failed"
    add("random_baseline_reliability_status", "validation", "random_baseline_reliability_status", random_status, "passed", "==", random_status == "passed")
    add("matched_delay_1d_mean_no_harm", "validation", "mean_return_r_diff_vs_matched_delay_same_fail_fast_1d", _diff_metric(baseline_diff, "validation", "same_seed_matched_delay_1d_same_fail_fast_h20", "mean_return_r"), -0.005, ">=", bool(_diff_metric(baseline_diff, "validation", "same_seed_matched_delay_1d_same_fail_fast_h20", "mean_return_r") >= -0.005))
    add("matched_delay_3d_mean_no_harm", "validation", "mean_return_r_diff_vs_matched_delay_same_fail_fast_3d", _diff_metric(baseline_diff, "validation", "same_seed_matched_delay_3d_same_fail_fast_h20", "mean_return_r"), -0.005, ">=", bool(_diff_metric(baseline_diff, "validation", "same_seed_matched_delay_3d_same_fail_fast_h20", "mean_return_r") >= -0.005))

    val_trade = recall_cost.loc[recall_cost["split"].eq("validation")]
    if not val_trade.empty:
        tr = val_trade.iloc[0]
        add("validation_added_capture_vs_ep2", "validation", "added_capture_vs_ep2_count", tr["added_capture_vs_ep2_count"], 0, ">", bool(tr["added_capture_vs_ep2_count"] > 0))
        add("validation_net_capture_vs_ep2", "validation", "added_capture_vs_ep2_count_gt_lost_capture", tr["added_capture_vs_ep2_count"] - tr["lost_capture_vs_ep2_count"], 0, ">", bool(tr["added_capture_vs_ep2_count"] > tr["lost_capture_vs_ep2_count"]))
        add("validation_recall_cost_score", "validation", "recall_cost_score", tr["recall_cost_score"], 0, ">", bool(tr["recall_cost_score"] > 0))
        add("validation_incremental_loss_bound", "validation", "incremental_loss_r_per_added_big_winner_vs_ep2", tr["incremental_loss_r_per_added_big_winner_vs_ep2"], tr["max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2"], "<=", bool(tr["incremental_loss_r_per_added_big_winner_vs_ep2"] <= tr["max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2"]))
        add("validation_incremental_exposure_bound", "validation", "incremental_exposure_days_per_added_big_winner_vs_ep2", tr["incremental_exposure_days_per_added_big_winner_vs_ep2"], tr["max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2"], "<=", bool(tr["incremental_exposure_days_per_added_big_winner_vs_ep2"] <= tr["max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2"]))

    cand_day_ratio = _metric_from_density(density, "validation", CANDIDATE_SEED_ID, "executable_seed_stock_day_count_vs_ep2")
    cand_ep_ratio = _metric_from_density(density, "validation", CANDIDATE_SEED_ID, "seed_episode_count_vs_ep2")
    add("validation_seed_day_count_vs_ep2", "validation", "candidate_seed_day_count_vs_ep2_ratio", cand_day_ratio, 1.0, ">=", bool(cand_day_ratio >= 1.0))
    add("validation_seed_episode_count_vs_ep2", "validation", "candidate_seed_episode_count_vs_ep2_ratio", cand_ep_ratio, 1.0, ">=", bool(cand_ep_ratio >= 1.0))

    gate_df = pd.DataFrame(rows)
    hard_pass = bool(gate_df.loc[gate_df["is_hard_gate"].astype(bool), "status"].eq("passed").all())
    validation_high_recall = bool(
        hard_pass
        and not val_trade.empty
        and val_trade.iloc[0]["added_capture_vs_ep2_count"] > 0
        and val_trade.iloc[0]["added_capture_vs_ep2_count"] > val_trade.iloc[0]["lost_capture_vs_ep2_count"]
        and cand_day_ratio >= 1.0
        and cand_ep_ratio >= 1.0
    )
    robustness_core = bool(_recall_diff(recall, "robustness") >= -0.10)
    archive = bool(
        hard_pass
        and _recall_diff(recall, "validation") >= -0.02
        and _diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r") < 0
    )
    if validation_high_recall and robustness_core:
        decision = "go_to_r02"
    elif validation_high_recall:
        decision = "go_to_r02_with_robustness_warning"
    elif archive:
        decision = "archive_cost_control_sleeve_no_r02"
    else:
        decision = "stop_ep4_r01_path"
    return gate_df, decision


def build_big_winner_audit(reference: pd.DataFrame, effective_windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]], data_max: pd.Timestamp, data_max_minus: pd.Timestamp) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, (start, eff_end) in effective_windows.items():
        ref = reference.loc[reference["split"].eq(split)]
        rows.append(
            {
                "split": split,
                "configured_start": _date_str(start),
                "effective_reference_end": _date_str(eff_end),
                "data_max_date": _date_str(data_max),
                "data_max_date_minus_forward_horizon": _date_str(data_max_minus),
                "big_winner_reference_count": int(ref.shape[0]),
                "unique_instrument_count": int(ref["instrument"].nunique()) if not ref.empty else 0,
                "forward_return_p50": float(ref["forward_return"].median()) if not ref.empty else np.nan,
                "status": "passed" if not ref.empty else "failed",
            }
        )
    return pd.DataFrame(rows)


def build_final_report(
    decision: str,
    reference_audit: pd.DataFrame,
    density: pd.DataFrame,
    recall: pd.DataFrame,
    recall_cost: pd.DataFrame,
    gate: pd.DataFrame,
    random_health: pd.DataFrame,
) -> str:
    failed = gate.loc[gate["status"].eq("failed")]
    lines = [
        "# EP4 R01 High-Recall Probe Cost-Control Report",
        "",
        f"- Final decision: `{decision}`",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        "- Phase boundary: no model training, no add, no portfolio sizing, no dynamic exit optimization.",
        "",
        "## Reference Windows",
        reference_audit.to_markdown(index=False),
        "",
        "## Density Summary",
        density.loc[density["split"].isin(["validation", "robustness"]), ["split", "seed_family_id", "seed_day_rate", "seed_episode_rate", "executable_seed_stock_day_count", "seed_episode_count", "unique_instrument_year_count"]].to_markdown(index=False),
        "",
        "## Recall Summary",
        recall.loc[recall["split"].isin(["validation", "robustness"])].to_markdown(index=False),
        "",
        "## Recall-Cost Tradeoff",
        recall_cost.to_markdown(index=False),
        "",
        "## Matched-Random Reliability",
        random_health.groupby(["split", "baseline_id"], dropna=False).agg(bucket_random_eligible_rate=("bucket_random_eligible_rate", "min"), random_replicate_count=("random_replicate_count", "min"), random_capacity_shortfall=("random_capacity_shortfall", "max"), random_baseline_reliability_status=("random_baseline_reliability_status", lambda s: "passed" if (s == "passed").all() else "failed")).reset_index().to_markdown(index=False) if not random_health.empty else "No random baseline rows.",
        "",
        "## Gate Evidence",
        gate.to_markdown(index=False),
        "",
        "## Failed Gates",
        failed.to_markdown(index=False) if not failed.empty else "No failed gates.",
        "",
        "## R02 Handoff",
        "R02 may only use surviving R01 episodes if the decision is `go_to_r02` or `go_to_r02_with_robustness_warning`; otherwise R02 must not start without a new requirement.",
    ]
    return "\n".join(lines) + "\n"


def run_r01(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths, ep2_config = load_config(config_path)
    authority = assert_authority_inputs(config)
    panel, calendar = load_provider_spine(config, ep2_config)
    stock = prepare_stock_day_panel(config, ep2_config, panel, calendar)
    bucket_freeze, stock = build_bucket_freeze(stock, config)
    data_max = pd.to_datetime(stock["date"]).max()
    effective_windows, data_max_minus = split_effective_windows(config, calendar, data_max)
    reference = build_big_winner_reference(stock, config, calendar, effective_windows)
    bridge_reference = build_ep2_bridge_reference(stock, config, calendar)
    candidate_events = build_candidate_seed_events(stock, config)
    ep2_events = build_ep2_seed_events(stock, config)
    seed_events = pd.concat([candidate_events, ep2_events], ignore_index=True)
    episodes = build_seed_episodes(seed_events, stock, config, calendar, reference, bridge_reference, effective_windows)
    label_a = label_a_audit(episodes, stock, calendar)
    episodes_for_sim = apply_label_flags(enrich_episode_for_sim(episodes), label_a)
    candidate_sim_input = episodes_for_sim.loc[(episodes_for_sim["seed_family_id"].eq(CANDIDATE_SEED_ID)) & (episodes_for_sim["executable_status"].eq("passed"))].copy()
    probe = simulate_episode_rows(candidate_sim_input, config, ep2_config, stock, calendar, fail_fast=True, id_prefix="r01_candidate")
    baseline_inputs = build_baseline_inputs(episodes_for_sim, stock, config, calendar, reference)
    baseline_frames: list[pd.DataFrame] = []
    for baseline_id, rows in baseline_inputs.items():
        if baseline_id.startswith("matched_random"):
            baseline_frames.append(simulate_random_baseline_fast(rows, config, ep2_config, stock, calendar, baseline_id))
        elif baseline_id == "ep2_detector_probe_with_simple_stop_bridge":
            baseline_frames.append(
                simulate_episode_rows(
                    rows,
                    config,
                    ep2_config,
                    stock,
                    calendar,
                    fail_fast=True,
                    id_prefix=baseline_id,
                    baseline_id=baseline_id,
                    simple_stop_pct=float(ep2_config["schedule_defaults"]["canonical_fast_fail_drawdown"]),
                    natural_h_override=int(ep2_config["schedule_defaults"]["primary_H"]),
                )
            )
        else:
            fail_fast = "no_fail_fast" not in baseline_id
            baseline_frames.append(simulate_episode_rows(rows, config, ep2_config, stock, calendar, fail_fast=fail_fast, id_prefix=baseline_id, baseline_id=baseline_id))
    baseline = pd.concat(baseline_frames, ignore_index=True) if baseline_frames else pd.DataFrame(columns=BASELINE_SIM_COLUMNS)

    density, density_tightness = build_density_audits(stock, episodes, seed_events, config)
    recall = build_recall_audit(reference, episodes)
    recall_cost = build_recall_cost_tradeoff(episodes, probe, baseline, config)
    baseline_diff = build_baseline_diff_audit(probe, baseline)
    random_health = build_random_health_audit(baseline, config)
    delay_audit = build_delay_ineligible_audit(baseline)
    r_unit = build_r_unit_distribution_audit(probe, baseline)
    no_ff = baseline.loc[baseline["baseline_id"].eq("same_seed_no_fail_fast_hold_h20")]
    ff_path, ff_error = build_fail_fast_audits(probe, no_ff)
    gate, decision = build_gate_audit(authority, density, recall, baseline_diff, delay_audit, random_health, recall_cost, probe, config)
    counterfactual = build_counterfactual(decision, probe, density_tightness)
    reference_audit = build_big_winner_audit(reference, effective_windows, data_max, data_max_minus)
    report = build_final_report(decision, reference_audit, density, recall, recall_cost, gate, random_health)

    for col in ["failed_seed_primary", "primary_metric_eligible_seed_episode", "failed_seed_label_a_h10_u1_5", "failed_seed_label_a_h20_u2_0", "failed_seed_h20_negative", "failed_seed_fail_fast_triggered", "terminal_blocked_exit"]:
        if col in probe.columns:
            probe[col] = probe[col].map(lambda value: pd.NA if pd.isna(value) else bool(value)).astype("boolean")
    for col in ["baseline_failed_seed_primary", "primary_metric_eligible_baseline_event", "captures_primary_big_winner", "random_excluded_candidate_seed_day", "random_capacity_shortfall"]:
        if col in baseline.columns:
            baseline[col] = baseline[col].map(lambda value: pd.NA if pd.isna(value) else bool(value)).astype("boolean")
    for col in ["primary_metric_eligible_seed_episode", "captures_primary_big_winner", "captures_ep2_bridge_big_winner"]:
        if col in episodes.columns:
            episodes[col] = episodes[col].map(lambda value: pd.NA if pd.isna(value) else bool(value)).astype("boolean")

    write_parquet(reference, paths.cache_dir / "r01_big_winner_reference_panel.parquet")
    write_parquet(seed_events, paths.cache_dir / "r01_seed_event_panel.parquet")
    write_parquet(episodes[SEED_EPISODE_COLUMNS], paths.cache_dir / "r01_seed_episode_panel.parquet")
    write_parquet(probe[PROBE_SIM_COLUMNS], paths.cache_dir / "r01_probe_simulation_panel.parquet")
    write_parquet(baseline[BASELINE_SIM_COLUMNS], paths.cache_dir / "r01_baseline_simulation_panel.parquet")

    write_csv(authority, paths.reports_dir / "r01_upstream_authority.csv")
    write_csv(reference_audit, paths.reports_dir / "r01_big_winner_reference_audit.csv")
    write_csv(density, paths.reports_dir / "r01_seed_density_audit.csv")
    write_csv(density_tightness, paths.reports_dir / "r01_density_cap_tightness_audit.csv")
    write_csv(recall, paths.reports_dir / "r01_seed_recall_audit.csv")
    write_csv(label_a, paths.reports_dir / "r01_label_bridge_audit.csv")
    write_csv(ff_path, paths.reports_dir / "r01_fail_fast_path_audit.csv")
    write_csv(ff_error, paths.reports_dir / "r01_fail_fast_error_audit.csv")
    write_csv(bucket_freeze, paths.reports_dir / "r01_matched_control_bucket_freeze.csv")
    write_csv(random_health, paths.reports_dir / "r01_random_baseline_health_audit.csv")
    write_csv(r_unit, paths.reports_dir / "r01_r_unit_distribution_audit.csv")
    write_csv(baseline_diff, paths.reports_dir / "r01_baseline_diff_audit.csv")
    write_csv(delay_audit, paths.reports_dir / "r01_matched_delay_ineligible_audit.csv")
    write_csv(recall_cost, paths.reports_dir / "r01_recall_cost_tradeoff.csv")
    write_csv(counterfactual, paths.reports_dir / "r01_counterfactual_failure_inheritance.csv")
    write_csv(gate, paths.reports_dir / "r01_gate_audit.csv")
    (paths.reports_dir / "r01_final_report.md").write_text(report, encoding="utf-8")

    manifest = {
        "phase": config["phase"],
        "schema_version": SCHEMA_VERSION,
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "output_root": relpath(paths.output_root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_decision": decision,
        "configured_train_window": [config["split"]["train_start"], config["split"]["train_end"]],
        "configured_validation_window": [config["split"]["validation_start"], config["split"]["validation_end"]],
        "configured_robustness_window": [config["split"]["robustness_start"], config["split"]["robustness_end"]],
        "effective_train_reference_window": [_date_str(effective_windows["train"][0]), _date_str(effective_windows["train"][1])],
        "effective_validation_reference_window": [_date_str(effective_windows["validation"][0]), _date_str(effective_windows["validation"][1])],
        "effective_robustness_reference_window": [_date_str(effective_windows["robustness"][0]), _date_str(effective_windows["robustness"][1])],
        "data_max_date": _date_str(data_max),
        "data_max_date_minus_forward_horizon": _date_str(data_max_minus),
        "primary_big_winner_reference_count": int(reference.shape[0]),
        "candidate_seed_episode_count": int(episodes.loc[episodes["seed_family_id"].eq(CANDIDATE_SEED_ID)].shape[0]),
        "ep2_seed_episode_count": int(episodes.loc[episodes["seed_family_id"].eq(EP2_SEED_ID)].shape[0]),
        "gate_count": int(gate.shape[0]),
        "failed_gate_count": int(gate["status"].eq("failed").sum()),
        "artifact_hashes": {
            name: file_hash(paths.cache_dir / name) for name in REQUIRED_CACHE
        }
        | {name: file_hash(paths.reports_dir / name) for name in REQUIRED_REPORTS},
    }
    write_json(manifest, paths.manifests_dir / "r01_run_manifest.json")
    return {
        "output_root": relpath(paths.output_root),
        "final_decision": decision,
        "gate_count": int(gate.shape[0]),
        "failed_gate_count": int(gate["status"].eq("failed").sum()),
        "primary_big_winner_reference_count": int(reference.shape[0]),
        "candidate_seed_episode_count": int(episodes.loc[episodes["seed_family_id"].eq(CANDIDATE_SEED_ID)].shape[0]),
        "ep2_seed_episode_count": int(episodes.loc[episodes["seed_family_id"].eq(EP2_SEED_ID)].shape[0]),
    }


def validate_r01(config_path: str | Path = DEFAULT_CONFIG, fail_on_hard_gates: bool = True) -> dict[str, Any]:
    config, paths, _ = load_config(config_path)
    failures: list[str] = []
    required_paths = [paths.cache_dir / name for name in REQUIRED_CACHE]
    required_paths += [paths.reports_dir / name for name in REQUIRED_REPORTS]
    required_paths += [paths.manifests_dir / name for name in REQUIRED_MANIFESTS]
    missing = [relpath(path) for path in required_paths if not path.exists()]
    if missing:
        failures.append("missing required artifacts: " + "; ".join(missing))
    if failures:
        raise RuntimeError("; ".join(failures))

    manifest = read_json(paths.manifests_dir / "r01_run_manifest.json")
    if manifest.get("phase") != config["phase"]:
        failures.append("manifest phase mismatch")
    if manifest.get("final_decision") not in ALLOWED_DECISIONS:
        failures.append("manifest final decision is not in allowed set")
    for key in ["effective_train_reference_window", "effective_validation_reference_window", "effective_robustness_reference_window", "data_max_date", "data_max_date_minus_forward_horizon"]:
        if key not in manifest or manifest.get(key) in ("", None, []):
            failures.append(f"manifest missing {key}")

    required_columns = {
        "r01_big_winner_reference_panel.parquet": BIG_WINNER_REFERENCE_COLUMNS,
        "r01_seed_event_panel.parquet": SEED_EVENT_COLUMNS,
        "r01_seed_episode_panel.parquet": SEED_EPISODE_COLUMNS,
        "r01_probe_simulation_panel.parquet": PROBE_SIM_COLUMNS,
        "r01_baseline_simulation_panel.parquet": BASELINE_SIM_COLUMNS,
    }
    for name, columns in required_columns.items():
        df = pd.read_parquet(paths.cache_dir / name)
        miss = [col for col in columns if col not in df.columns]
        if miss:
            failures.append(f"{name} missing columns: {miss}")

    reference = pd.read_parquet(paths.cache_dir / "r01_big_winner_reference_panel.parquet")
    if reference.empty:
        failures.append("primary big-winner reference set is empty")
    seed_events = pd.read_parquet(paths.cache_dir / "r01_seed_event_panel.parquet")
    if seed_events.loc[seed_events["seed_family_id"].eq(CANDIDATE_SEED_ID), "rs_rank_pct_audit"].notna().any():
        hard_rejects = seed_events.loc[
            seed_events["seed_family_id"].eq(CANDIDATE_SEED_ID)
            & seed_events["reject_reason"].astype(str).str.contains("relative_strength|rs_rank|rs_filter", case=False, regex=True)
        ]
        if not hard_rejects.empty:
            failures.append("candidate seed appears to use relative strength as a hard filter")

    episodes = pd.read_parquet(paths.cache_dir / "r01_seed_episode_panel.parquet")
    robustness_end = pd.Timestamp(manifest["effective_robustness_reference_window"][1])
    invalid_primary = episodes.loc[
        episodes["primary_metric_eligible_seed_episode"].astype(bool)
        & (pd.to_datetime(episodes["episode_start_signal_date"]) > robustness_end)
    ]
    if not invalid_primary.empty:
        failures.append("primary metric eligible seed episodes extend beyond effective reference end")
    if episodes.loc[episodes["seed_family_id"].eq(CANDIDATE_SEED_ID) & episodes["executable_status"].eq("passed") & episodes["initial_risk_pct"].isna()].shape[0] > 0:
        failures.append("candidate executable episodes have missing initial_risk_pct")

    baseline = pd.read_parquet(paths.cache_dir / "r01_baseline_simulation_panel.parquet")
    required_baselines = set(config["baselines"])
    observed_baselines = set(baseline["baseline_id"].dropna().astype(str))
    missing_baselines = sorted(required_baselines - observed_baselines)
    if missing_baselines:
        failures.append(f"missing required baseline ids: {missing_baselines}")
    random_rows = baseline.loc[baseline["matched_control_type"].eq("matched_random")]
    if not random_rows.empty:
        if not random_rows["random_sampling_replacement_policy"].eq("without_replacement_within_replicate").all():
            failures.append("matched-random replacement policy is not frozen no-replacement")
        if random_rows["random_excluded_candidate_seed_day"].astype(bool).any():
            failures.append("matched-random contains candidate seed stock-day contamination")

    gate = pd.read_csv(paths.reports_dir / "r01_gate_audit.csv")
    gate_missing = [col for col in ["gate_id", "split", "metric_name", "metric_value", "threshold", "comparison", "status", "is_hard_gate", "failure_reason"] if col not in gate.columns]
    if gate_missing:
        failures.append(f"gate audit missing columns: {gate_missing}")
    if fail_on_hard_gates and not gate.empty:
        failed_hard = gate.loc[gate["is_hard_gate"].astype(bool) & gate["status"].eq("failed")]
        if not failed_hard.empty:
            failures.append("hard gates failed: " + "; ".join(failed_hard["gate_id"].astype(str).head(20).tolist()))

    report = (paths.reports_dir / "r01_final_report.md").read_text(encoding="utf-8")
    required_report_tokens = ["Final decision", "Recall-Cost Tradeoff", "Matched-Random Reliability", "R02 Handoff"]
    for token in required_report_tokens:
        if token not in report:
            failures.append(f"final report missing section token: {token}")

    if failures:
        raise RuntimeError("; ".join(failures))
    return {
        "validation_status": "passed",
        "output_root": relpath(paths.output_root),
        "final_decision": manifest.get("final_decision"),
        "gate_count": int(len(gate)),
        "failed_gate_count": int(gate["status"].eq("failed").sum()),
    }

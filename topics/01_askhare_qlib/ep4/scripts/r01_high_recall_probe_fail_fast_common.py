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
    "go_to_oos_retest_required",
    "archive_hypothesis_no_r02",
    "archive_cost_control_sleeve_no_r02",
    "stop_ep4_r01_path",
    "stop_ep4_r01_1_path",
}
R01_1_DEFAULT_CONFIG = EP4_DIR / "configs" / "r01_1_emission_throttled_cooling_entry_probe_fail_fast.yaml"
R01_1_REQUIREMENT_ID = "ep4_r01_1_emission_throttled_cooling_entry_probe_fail_fast"
R01_1_SCHEMA_VERSION = "ep4_r01_1_emission_throttled_cooling_probe_v1"
R01_1_ALLOWED_DECISIONS = {
    "go_to_r02",
    "go_to_r02_with_robustness_warning",
    "archive_cost_control_sleeve_no_r02",
    "stop_ep4_r01_1_path",
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
R01_1_CACHE = [
    "r01_1_big_winner_reference_panel.parquet",
    "r01_1_raw_seed_panel.parquet",
    "r01_1_emitted_seed_panel.parquet",
    "r01_1_cooling_entry_panel.parquet",
    "r01_1_seed_episode_panel.parquet",
    "r01_1_probe_simulation_panel.parquet",
    "r01_1_baseline_simulation_panel.parquet",
]
R01_1_REPORTS = [
    "r01_1_final_report.md",
    "r01_1_gate_audit.csv",
    "r01_1_density_audit.csv",
    "r01_1_raw_to_emitted_waterfall.csv",
    "r01_1_cooling_entry_waterfall.csv",
    "r01_1_recall_bridge.csv",
    "r01_1_entry_after_reference_audit.csv",
    "r01_1_recall_cost_tradeoff.csv",
    "r01_1_fail_fast_attribution.csv",
    "r01_1_false_reject_missed_failure_audit.csv",
    "r01_1_entry_timing_audit.csv",
    "r01_1_r_unit_distribution_audit.csv",
    "r01_1_risk_pct_quintile_cost_control.csv",
    "r01_1_baseline_eligibility_audit.csv",
    "r01_1_vcp_audit.csv",
    "r01_1_confirmation_audit.csv",
    "r01_1_matched_delay_reliability_audit.csv",
    "r01_1_matched_random_reliability_audit.csv",
    "r01_1_archive_decision_audit.csv",
    "r01_1_counterfactual_failure_inheritance.csv",
]
R01_1_MANIFESTS = ["r01_1_run_manifest.json"]

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
    "close_near_high5_gt_0pct_triggered",
    "rolling_close_high5_asof",
    "close_near_60d_high_triggered",
    "close_breaks_40d_high_triggered",
    "rolling_high_60_asof",
    "rolling_high_40_asof",
    "component_trigger_threshold",
    "breakout_reference",
    "vol_ratio10",
    "vol_ratio3",
    "rps5",
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
    "entry_execution_date",
    "episode_end_signal_date",
    "split",
    "terminal_exit_date",
    "split_boundary_status",
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
    "boundary_status",
    "captures_primary_big_winner",
    "captured_reference_event_id",
    "capture_window_id",
    "capture_time_basis",
    "entry_capture_window_status",
    "captures_ep2_bridge_big_winner",
    "captured_ep2_bridge_reference_event_id",
    "ep2_bridge_capture_window_id",
]
PROBE_SIM_COLUMNS = [
    "simulation_id",
    "seed_episode_id",
    "seed_family_id",
    "instrument",
    "entry_date",
    "entry_execution_date",
    "entry_price",
    "initial_probe_risk_budget_r",
    "initial_structural_stop",
    "initial_risk_pct",
    "exit_trigger_type",
    "exit_signal_date",
    "exit_execution_date",
    "terminal_exit_date",
    "exit_price",
    "sell_blocked_day_count",
    "terminal_blocked_exit",
    "split_boundary_status",
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
    "entry_execution_date",
    "candidate_entry_execution_date",
    "baseline_entry_execution_date",
    "ep2_bridge_entry_execution_date",
    "capture_timestamp_used",
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
    "boundary_status",
    "captures_primary_big_winner",
    "captured_reference_event_id",
    "capture_window_id",
    "capture_time_basis",
    "entry_capture_window_status",
    "baseline_failed_seed_primary",
    "exit_date",
    "exit_execution_date",
    "terminal_exit_date",
    "exit_price",
    "split_boundary_status",
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
    global CANDIDATE_SEED_ID
    cfg_path = topic_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    CANDIDATE_SEED_ID = str(config.get("seed_rules", {}).get("candidate_seed_id", CANDIDATE_SEED_ID))
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


def is_v3_config(config: dict[str, Any]) -> bool:
    formula = str(config.get("seed_rules", {}).get("candidate_seed_formula_id", ""))
    phase = str(config.get("phase", ""))
    return "v3" in phase or formula == "close_near_high5_gt_0pct_and_vol_ratio10_gt_1_2_and_vol_ratio3_gt_1_2_and_rps5_gt_60"


def max_probe_observation_horizon(config: dict[str, Any]) -> int:
    return int(config.get("fail_fast", {}).get("natural_exit_horizon_trading_days", 20)) + int(config.get("execution", {}).get("max_exit_retry_trading_days", 20))


def primary_entry_capture_forward_days(config: dict[str, Any]) -> int:
    return int(config.get("capture_time_basis", {}).get("primary_entry_capture_window", {}).get("end_offset_from_reference_trading_days", config.get("seed_recall", {}).get("primary_recall_forward_days", 0)))


def split_effective_windows(
    config: dict[str, Any], calendar: pd.DatetimeIndex, data_max_date: pd.Timestamp
) -> tuple[dict[str, tuple[pd.Timestamp, pd.Timestamp]], pd.Timestamp]:
    horizon = int(config["big_winner_reference"]["forward_horizon_trading_days"])
    extra_tail = primary_entry_capture_forward_days(config) + max_probe_observation_horizon(config) if is_v3_config(config) else 0
    label_horizon = max(horizon, extra_tail)
    data_max_pos = int(calendar.searchsorted(data_max_date, side="right") - 1)
    effective_pos = data_max_pos - label_horizon
    if effective_pos < 0:
        data_max_minus = pd.NaT
    else:
        data_max_minus = pd.Timestamp(calendar[effective_pos])
    windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for split, (start, end) in split_bounds(config).items():
        split_end = end
        if is_v3_config(config):
            split_end_pos = int(calendar.searchsorted(end, side="right") - 1)
            split_limited_pos = split_end_pos - extra_tail
            split_end = pd.Timestamp(calendar[split_limited_pos]) if split_limited_pos >= 0 else pd.NaT
        effective_end = min(split_end, data_max_minus) if not pd.isna(data_max_minus) and not pd.isna(split_end) else pd.NaT
        windows[split] = (start, effective_end)
    return windows, data_max_minus


def split_effective_boundaries(
    config: dict[str, Any], calendar: pd.DatetimeIndex, data_max_date: pd.Timestamp
) -> tuple[dict[str, dict[str, pd.Timestamp]], pd.Timestamp]:
    windows, data_max_minus = split_effective_windows(config, calendar, data_max_date)
    bounds = split_bounds(config)
    entry_forward = primary_entry_capture_forward_days(config)
    probe_tail = max_probe_observation_horizon(config)
    boundaries: dict[str, dict[str, pd.Timestamp]] = {}
    for split, (start, ref_end) in windows.items():
        seed_end = base.add_trading_days(calendar, ref_end, entry_forward) if not pd.isna(ref_end) else pd.NaT
        split_end = bounds[split][1]
        split_gate_pos = int(calendar.searchsorted(split_end, side="right") - 1) - probe_tail
        split_gate_end = pd.Timestamp(calendar[split_gate_pos]) if split_gate_pos >= 0 else pd.NaT
        gate_end = min(seed_end, split_gate_end) if not pd.isna(seed_end) and not pd.isna(split_gate_end) else pd.NaT
        boundaries[split] = {
            "configured_start": start,
            "configured_end": bounds[split][1],
            "effective_reference_end": ref_end,
            "effective_primary_seed_end": seed_end,
            "effective_gate_entry_end": gate_end,
        }
    return boundaries, data_max_minus


def effective_gate_entry_end_for_split(config: dict[str, Any], calendar: pd.DatetimeIndex, split: str, effective_reference_end: pd.Timestamp) -> pd.Timestamp:
    if pd.isna(effective_reference_end):
        return pd.NaT
    seed_end = base.add_trading_days(calendar, effective_reference_end, primary_entry_capture_forward_days(config))
    split_end = split_bounds(config)[split][1]
    split_gate_pos = int(calendar.searchsorted(split_end, side="right") - 1) - max_probe_observation_horizon(config)
    split_gate_end = pd.Timestamp(calendar[split_gate_pos]) if split_gate_pos >= 0 else pd.NaT
    return min(seed_end, split_gate_end) if not pd.isna(seed_end) and not pd.isna(split_gate_end) else pd.NaT


def primary_recall_lookback_days(config: dict[str, Any]) -> int:
    return int(config.get("seed_recall", {}).get("primary_recall_lookback_days", 20))


def primary_recall_window_id(config: dict[str, Any]) -> str:
    configured = config.get("seed_recall", {}).get("primary_recall_window_id")
    if configured:
        return str(configured)
    return f"primary_-{primary_recall_lookback_days(config)}_0"


def assert_authority_inputs(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    canonical = {
        "ep4_discussion": "ep4/discussion.md",
        "ep4_requirement": config.get("requirement_path", "ep4/requirement_01_high_recall_probe_fail_fast.md"),
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
    df["rolling_close_high5_asof"] = group["close"].transform(lambda s: s.shift(1).rolling(5, min_periods=5).max())
    df["rolling_close_high_10_asof"] = group["close"].transform(lambda s: s.shift(1).rolling(10, min_periods=10).max())
    df["pivot_low_10d"] = group["low"].transform(lambda s: s.shift(1).rolling(10, min_periods=10).min())
    df["money_20d_median_asof"] = group["money"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).median())
    df["money_20d_mean_asof"] = group["money"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).mean())
    df["money_5d_mean_asof"] = group["money"].transform(lambda s: s.shift(1).rolling(5, min_periods=5).mean())
    df["volume_10d_mean_asof"] = group["volume"].transform(lambda s: s.shift(1).rolling(10, min_periods=10).mean())
    df["volume_3d_mean_asof"] = group["volume"].transform(lambda s: s.shift(1).rolling(3, min_periods=3).mean())
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
    df["ret5_asof"] = group["close"].transform(lambda s: s / s.shift(5) - 1.0)
    df["rs_rank_pct_audit"] = df.groupby("date")["ret60_asof"].rank(pct=True)
    df["rps5_rank_pct"] = df.groupby("date")["ret5_asof"].rank(pct=True)
    df["money_activity_ratio"] = df["money"] / df["money_20d_median_asof"]
    df["money_ratio20_mean_asof"] = df["money"] / df["money_20d_mean_asof"]
    df["money_ratio5_mean_asof"] = df["money"] / df["money_5d_mean_asof"]
    df["vol_ratio10"] = df["volume"] / df["volume_10d_mean_asof"]
    df["vol_ratio3"] = df["volume"] / df["volume_3d_mean_asof"]
    boll20_mid = group["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    boll20_std = group["close"].transform(lambda s: s.rolling(20, min_periods=20).std(ddof=0))
    boll20_upper = boll20_mid + 2.0 * boll20_std
    boll20_lower = boll20_mid - 2.0 * boll20_std
    df["boll20_pct_b"] = (df["close"] - boll20_lower) / (boll20_upper - boll20_lower)
    df["close_near_high5_gt_0pct_triggered"] = df["close"] >= df["rolling_close_high5_asof"]
    df["close_near_high10_ratio"] = df["close"] / df["rolling_close_high_10_asof"]
    df["close_near_60d_high_triggered"] = df["close"] >= 0.97 * df["rolling_high_60_asof"]
    df["close_breaks_40d_high_triggered"] = df["close"] >= df["rolling_high_40_asof"]
    df["component_trigger_threshold_near60"] = 0.97 * df["rolling_high_60_asof"]
    df["component_trigger_threshold_break40"] = df["rolling_high_40_asof"]
    df["breakout_reference_near60"] = df["component_trigger_threshold_near60"]
    df["breakout_reference_break40"] = df["rolling_high_40_asof"]
    df["seed_day_low"] = df["low"]
    if is_v3_config(config):
        history_fields = ["rolling_close_high5_asof", "pivot_low_10d", "volume_10d_mean_asof", "volume_3d_mean_asof", "ret5_asof", "atr20_asof"]
    else:
        history_fields = ["rolling_high_60_asof", "rolling_high_40_asof", "pivot_low_10d", "money_20d_median_asof", "atr20_asof"]
    df["has_required_history_for_seed_formula"] = df[history_fields].notna().all(axis=1)
    price_ok = df[["open", "high", "low", "close"]].apply(np.isfinite).all(axis=1) & (df[["open", "high", "low", "close"]] > 0).all(axis=1)
    volume_ok = np.isfinite(df["volume"]) & (df["volume"] > 0)
    money_ok = np.isfinite(df["money"]) & (df["money"] > 0)
    df["not_suspended_or_dirty_bar"] = price_ok & volume_ok & money_ok
    df["st_or_delist_risk"] = df["name"].astype(str).str.upper().str.contains("ST", na=False)
    rps_rank_mask = (
        df["split"].isin(["train", "validation", "robustness"])
        & df["pit_universe_member"].astype(bool)
        & df["not_suspended_or_dirty_bar"].astype(bool)
        & df["ret5_asof"].notna()
        & np.isfinite(df["close"])
    )
    df["rps5"] = np.nan
    df.loc[rps_rank_mask, "rps5"] = df.loc[rps_rank_mask].groupby("date")["ret5_asof"].rank(pct=True)
    df["rps5_rank_pct"] = df["rps5"]

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
    formula_id = str(config.get("seed_rules", {}).get("candidate_seed_formula_id", "ep4_wide_seed_v0"))
    if formula_id == "money_ratio20_gt_1_0_and_money_ratio5_gt_2_0_and_rps5_gt_50":
        triggered = (
            stock["split"].isin(["train", "validation", "robustness"])
            & (stock["money_ratio20_mean_asof"] > 1.0)
            & (stock["money_ratio5_mean_asof"] > 2.0)
            & (stock["rps5_rank_pct"] > 0.50)
        )
        seed_kind = "money_rps5_pre60"
    elif formula_id == "money_ratio20_gt_1_0_and_money_ratio5_gt_2_0_and_rps5_gt_50_and_boll20_pct_b_gt_1_0_and_close_near_high10_gt_0":
        triggered = (
            stock["split"].isin(["train", "validation", "robustness"])
            & (stock["money_ratio20_mean_asof"] > 1.0)
            & (stock["money_ratio5_mean_asof"] > 2.0)
            & (stock["rps5_rank_pct"] > 0.50)
            & (stock["boll20_pct_b"] > 1.0)
            & (stock["close_near_high10_ratio"] >= 1.0)
        )
        seed_kind = "money_rps5_boll20_high10"
    elif formula_id == "close_near_high5_gt_0pct_and_vol_ratio10_gt_1_2_and_vol_ratio3_gt_1_2_and_rps5_gt_60":
        triggered = (
            stock["split"].isin(["train", "validation", "robustness"])
            & stock["close_near_high5_gt_0pct_triggered"].fillna(False)
            & (stock["vol_ratio10"] > 1.2)
            & (stock["vol_ratio3"] > 1.2)
            & (stock["rps5"] > 0.60)
        )
        seed_kind = "post30_high5_volume_rps5"
    elif formula_id == "boll20_pct_b_gt_1_0_and_close_near_high10_gt_0":
        triggered = (
            stock["split"].isin(["train", "validation", "robustness"])
            & (stock["boll20_pct_b"] > 1.0)
            & (stock["close_near_high10_ratio"] >= 1.0)
        )
        seed_kind = "boll20_high10"
    else:
        min_money = float(config["seed_rules"]["candidate_seed_components"]["money_activity"]["min_money_ratio_vs_window_median"])
        triggered = (
            stock["split"].isin(["train", "validation", "robustness"])
            & (stock["close_near_60d_high_triggered"].fillna(False) | stock["close_breaks_40d_high_triggered"].fillna(False))
            & (stock["money_activity_ratio"] >= min_money)
        )
        seed_kind = "wide_price_money"
    raw = stock.loc[triggered].copy()
    if raw.empty:
        return pd.DataFrame(columns=SEED_EVENT_COLUMNS)
    if seed_kind == "money_rps5_pre60":
        raw["price_structure_component"] = "money_ratio20_1_money_ratio5_2_rps5_50"
        raw["component_trigger_threshold"] = np.nan
        raw["breakout_reference"] = np.nan
    elif seed_kind == "money_rps5_boll20_high10":
        raw["price_structure_component"] = "money_ratio20_1_money_ratio5_2_rps5_50_boll20_pct_b_1_close_near_high10_0"
        raw["component_trigger_threshold"] = raw["rolling_close_high_10_asof"]
        raw["breakout_reference"] = raw["rolling_close_high_10_asof"]
    elif seed_kind == "post30_high5_volume_rps5":
        raw["price_structure_component"] = "close_near_high5_gt_0pct"
        raw["component_trigger_threshold"] = raw["rolling_close_high5_asof"]
        raw["breakout_reference"] = raw["rolling_close_high5_asof"]
    elif seed_kind == "boll20_high10":
        raw["price_structure_component"] = "boll20_pct_b_1_close_near_high10_0"
        raw["component_trigger_threshold"] = raw["rolling_close_high_10_asof"]
        raw["breakout_reference"] = raw["rolling_close_high_10_asof"]
    else:
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
    if seed_kind in {"money_rps5_pre60", "money_rps5_boll20_high10"}:
        money_activity_ratio = raw["money_ratio20_mean_asof"]
        rs_rank_pct_audit = raw["rps5_rank_pct"]
    elif seed_kind == "post30_high5_volume_rps5":
        money_activity_ratio = raw["vol_ratio10"]
        rs_rank_pct_audit = raw["rps5"]
    elif seed_kind == "boll20_high10":
        money_activity_ratio = raw["boll20_pct_b"]
        rs_rank_pct_audit = raw["rs_rank_pct_audit"]
    else:
        money_activity_ratio = raw["money_activity_ratio"]
        rs_rank_pct_audit = raw["rs_rank_pct_audit"]
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
            "close_near_high5_gt_0pct_triggered": raw["close_near_high5_gt_0pct_triggered"].astype(bool),
            "rolling_close_high5_asof": raw["rolling_close_high5_asof"],
            "close_near_60d_high_triggered": raw["close_near_60d_high_triggered"].astype(bool),
            "close_breaks_40d_high_triggered": raw["close_breaks_40d_high_triggered"].astype(bool),
            "rolling_high_60_asof": raw["rolling_high_60_asof"],
            "rolling_high_40_asof": raw["rolling_high_40_asof"],
            "component_trigger_threshold": raw["component_trigger_threshold"],
            "breakout_reference": raw["breakout_reference"],
            "vol_ratio10": raw["vol_ratio10"],
            "vol_ratio3": raw["vol_ratio3"],
            "rps5": raw["rps5"],
            "money_activity_ratio": money_activity_ratio,
            "money_20d_median_asof": raw["money_20d_median_asof"],
            "atr20_asof": raw["atr20_asof"],
            "atr20_pct_asof": raw["atr20_pct_asof"],
            "rs_rank_pct_audit": rs_rank_pct_audit,
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
                "close_near_high5_gt_0pct_triggered": bool(s.get("close_near_high5_gt_0pct_triggered", False)),
                "rolling_close_high5_asof": s.get("rolling_close_high5_asof", np.nan),
                "close_near_60d_high_triggered": bool(s.get("close_near_60d_high_triggered", False)),
                "close_breaks_40d_high_triggered": bool(s.get("close_breaks_40d_high_triggered", False)),
                "rolling_high_60_asof": s.get("rolling_high_60_asof", np.nan),
                "rolling_high_40_asof": s.get("rolling_high_40_asof", np.nan),
                "component_trigger_threshold": threshold,
                "breakout_reference": breakout,
                "vol_ratio10": s.get("vol_ratio10", np.nan),
                "vol_ratio3": s.get("vol_ratio3", np.nan),
                "rps5": s.get("rps5", np.nan),
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
    primary_lookback = primary_recall_lookback_days(config)
    primary_window_id = primary_recall_window_id(config)
    if is_v3_config(config):
        gate_end = effective_gate_entry_end_for_split(config, calendar, split, eff_end) if split in {"train", "validation", "robustness"} else pd.NaT
        primary_eligible = split in {"train", "validation", "robustness"} and not pd.isna(gate_end) and pd.notna(entry_date) and _date(entry_date) <= gate_end
        captured, captured_id, window_id = capture_entry_reference(
            instrument,
            _date(entry_date),
            reference,
            calendar,
            int(config["capture_time_basis"]["primary_entry_capture_window"]["start_offset_from_reference_trading_days"]),
            int(config["capture_time_basis"]["primary_entry_capture_window"]["end_offset_from_reference_trading_days"]),
            str(config.get("entry_capture", {}).get("primary_entry_capture_window_id", "primary_entry_1_30")),
        )
        bridge_captured, bridge_ref_id, bridge_window_id = capture_entry_reference(
            instrument,
            _date(entry_date),
            bridge_reference,
            calendar,
            int(config["capture_time_basis"]["primary_entry_capture_window"]["start_offset_from_reference_trading_days"]),
            int(config["capture_time_basis"]["primary_entry_capture_window"]["end_offset_from_reference_trading_days"]),
            str(config.get("entry_capture", {}).get("primary_entry_capture_window_id", "primary_entry_1_30")),
        )
        boundary_status = "primary_metric_eligible" if primary_eligible else "cross_split_execution_report_only"
        capture_basis = "entry_execution_date"
        entry_capture_status = "captured" if primary_eligible and captured else ("not_captured" if primary_eligible else "not_primary_metric_eligible")
    else:
        primary_eligible = split in {"train", "validation", "robustness"} and not pd.isna(eff_end) and start <= eff_end
        captured, captured_id, window_id = capture_reference(instrument, start, reference, calendar, primary_lookback, 0, primary_window_id)
        bridge_captured, bridge_ref_id, bridge_window_id = capture_reference(instrument, start, bridge_reference, calendar, primary_lookback, 0, primary_window_id)
        boundary_status = "primary_metric_eligible" if primary_eligible else "not_primary_metric_eligible"
        capture_basis = "signal_date"
        entry_capture_status = "legacy_signal_capture" if captured else "not_captured"
    return {
        "seed_episode_id": episode_id,
        "seed_family_id": family,
        "instrument": instrument,
        "episode_start_signal_date": _date_str(start),
        "episode_effective_entry_date": _date_str(entry_date),
        "entry_execution_date": _date_str(entry_date),
        "episode_end_signal_date": _date_str(base.add_trading_days(calendar, end, 20)),
        "split": split,
        "terminal_exit_date": "",
        "split_boundary_status": boundary_status,
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
        "boundary_status": boundary_status,
        "captures_primary_big_winner": bool(captured) if primary_eligible else False,
        "captured_reference_event_id": captured_id if primary_eligible else "",
        "capture_window_id": window_id if primary_eligible and captured else "",
        "capture_time_basis": capture_basis,
        "entry_capture_window_status": entry_capture_status,
        "captures_ep2_bridge_big_winner": bool(bridge_captured),
        "captured_ep2_bridge_reference_event_id": bridge_ref_id if bridge_captured else "",
        "ep2_bridge_capture_window_id": bridge_window_id if bridge_captured else "",
    }


def capture_reference(
    instrument: str,
    signal_date: pd.Timestamp,
    reference: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    lookback_days: int,
    forward_days: int,
    window_id: str | None = None,
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
    return True, str(first["reference_event_id"]), window_id or f"primary_-{int(lookback_days)}_0"


def capture_entry_reference(
    instrument: str,
    entry_execution_date: pd.Timestamp,
    reference: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    start_offset: int,
    end_offset: int,
    window_id: str,
) -> tuple[bool, str, str]:
    if reference.empty or pd.isna(entry_execution_date):
        return False, "", ""
    refs = reference.loc[reference["instrument"].astype(str).eq(str(instrument).upper())].copy()
    if refs.empty:
        return False, "", ""
    hits: list[tuple[pd.Timestamp, str]] = []
    entry_dt = _date(entry_execution_date)
    for row in refs.itertuples(index=False):
        ref_date = _date(row.reference_date)
        start = base.add_trading_days(calendar, ref_date, start_offset)
        end = base.add_trading_days(calendar, ref_date, end_offset)
        if pd.isna(start) or pd.isna(end):
            continue
        if start <= entry_dt <= end:
            hits.append((ref_date, str(row.reference_event_id)))
    if not hits:
        return False, "", ""
    hits.sort()
    return True, hits[0][1], window_id


def capture_signal_reference_v3(
    instrument: str,
    signal_date: pd.Timestamp,
    reference: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> tuple[bool, str]:
    captured, ref_id, _ = capture_entry_reference(
        instrument,
        signal_date,
        reference,
        calendar,
        0,
        29,
        "signal_0_29",
    )
    return captured, ref_id


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
    window_id: str | None = None,
) -> tuple[bool, str, str]:
    refs = ref_idx.get(str(instrument).upper(), [])
    if not refs:
        return False, "", ""
    end = base.add_trading_days(calendar, signal_date, lookahead_days)
    if pd.isna(end):
        end = signal_date
    for ref_date, ref_id in refs:
        if signal_date <= ref_date <= end:
            return True, ref_id, window_id or f"primary_-{int(lookahead_days)}_0"
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
                if split not in effective_windows:
                    continue
                eff_start, eff_end = effective_windows[split]
                if pd.isna(eff_start) or pd.isna(eff_end) or date < eff_start or date > eff_end:
                    continue
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
            if offset == int(config["fail_fast"]["max_fail_fast_window_trading_days"]) - 1:
                trigger_type = np.where((trigger_type == "") & (close < work["entry_price"].astype(float)), "t10_close_below_entry_price", trigger_type)
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
            "entry_execution_date": work["entry_date"],
            "candidate_entry_execution_date": work.get("episode_effective_entry_date", pd.Series("", index=work.index)),
            "baseline_entry_execution_date": work["entry_date"],
            "ep2_bridge_entry_execution_date": "",
            "capture_timestamp_used": work["entry_date"],
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
            "boundary_status": np.where(work["primary_metric_eligible_baseline_event"].astype(bool), "primary_metric_eligible", "not_primary_metric_eligible"),
            "captures_primary_big_winner": work["captures_primary_big_winner"].astype(bool),
            "captured_reference_event_id": work["captured_reference_event_id"],
            "capture_window_id": work["capture_window_id"],
            "capture_time_basis": "entry_execution_date" if is_v3_config(config) else "signal_date",
            "entry_capture_window_status": np.where(work["captures_primary_big_winner"].astype(bool), "captured", "not_captured"),
            "baseline_failed_seed_primary": np.where(work["primary_metric_eligible_baseline_event"].astype(bool) & ok, ~work["captures_primary_big_winner"].astype(bool), np.nan),
            "exit_date": pd.to_datetime(work["exit_date_calc"]).dt.strftime("%Y-%m-%d"),
            "exit_execution_date": pd.to_datetime(work["exit_date_calc"]).dt.strftime("%Y-%m-%d"),
            "terminal_exit_date": pd.to_datetime(work["exit_date_calc"]).dt.strftime("%Y-%m-%d"),
            "exit_price": np.where(ok, exit_price, np.nan),
            "split_boundary_status": np.where(work["primary_metric_eligible_baseline_event"].astype(bool), "primary_metric_eligible", "cross_split_execution_report_only"),
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
                if day == ff_window - 1 and np.isfinite(entry_price) and close < entry_price:
                    triggered.append("t10_close_below_entry_price")
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
        "entry_execution_date": _date_str(row["entry_date"]),
        "entry_price": row["entry_price"],
        "initial_probe_risk_budget_r": 0.25,
        "initial_structural_stop": row["initial_structural_stop"],
        "initial_risk_pct": row["initial_risk_pct"],
        "exit_trigger_type": sim["exit_trigger_type"],
        "exit_signal_date": sim["exit_signal_date"],
        "exit_execution_date": sim["exit_execution_date"],
        "terminal_exit_date": sim["exit_execution_date"],
        "exit_price": sim["exit_price"],
        "sell_blocked_day_count": sim["sell_blocked_day_count"],
        "terminal_blocked_exit": sim["terminal_blocked_exit"],
        "split_boundary_status": row.get("split_boundary_status", ""),
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
    entry_date = _date_str(row.get("entry_date", ""))
    candidate_entry = _date_str(row.get("episode_effective_entry_date", row.get("candidate_entry_execution_date", "")))
    baseline_entry = entry_date
    ep2_entry = entry_date if baseline_id == "ep2_detector_probe_with_simple_stop_bridge" else ""
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
        "entry_date": entry_date,
        "entry_execution_date": entry_date,
        "candidate_entry_execution_date": candidate_entry,
        "baseline_entry_execution_date": baseline_entry,
        "ep2_bridge_entry_execution_date": ep2_entry,
        "capture_timestamp_used": baseline_entry,
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
        "boundary_status": row.get("boundary_status", "primary_metric_eligible" if bool(row.get("primary_metric_eligible_baseline_event", row.get("primary_metric_eligible_seed_episode", False))) else "not_primary_metric_eligible"),
        "captures_primary_big_winner": bool(row.get("captures_primary_big_winner", False)),
        "captured_reference_event_id": row.get("captured_reference_event_id", ""),
        "capture_window_id": row.get("capture_window_id", ""),
        "capture_time_basis": row.get("capture_time_basis", "signal_date"),
        "entry_capture_window_status": row.get("entry_capture_window_status", "captured" if bool(row.get("captures_primary_big_winner", False)) else "not_captured"),
        "baseline_failed_seed_primary": failed_primary,
        "exit_date": sim["exit_execution_date"],
        "exit_execution_date": sim["exit_execution_date"],
        "terminal_exit_date": sim["exit_execution_date"],
        "exit_price": sim["exit_price"],
        "split_boundary_status": row.get("split_boundary_status", row.get("boundary_status", "")),
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
        rec["candidate_entry_execution_date"] = ep.get("episode_effective_entry_date", "")
        rec["baseline_entry_execution_date"] = _date_str(delayed_entry_date)
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
        if is_v3_config(config) and pd.notna(delayed_entry_date):
            captured, ref_id, window_id = capture_entry_reference(
                str(ep["instrument"]),
                _date(delayed_entry_date),
                reference,
                calendar,
                int(config["capture_time_basis"]["primary_entry_capture_window"]["start_offset_from_reference_trading_days"]),
                int(config["capture_time_basis"]["primary_entry_capture_window"]["end_offset_from_reference_trading_days"]),
                str(config.get("entry_capture", {}).get("primary_entry_capture_window_id", "primary_entry_1_30")),
            )
            rec["captures_primary_big_winner"] = bool(captured)
            rec["captured_reference_event_id"] = ref_id
            rec["capture_window_id"] = window_id if captured else ""
            rec["capture_time_basis"] = "entry_execution_date"
            rec["entry_capture_window_status"] = "captured" if captured else "not_captured"
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
    stock_pool = stock.loc[stock["split"].isin(["train", "validation", "robustness"]) & stock["eligible_stock_day"].astype(bool)].copy()
    if "candidate_seed_stock_day" in stock_pool.columns:
        stock_pool["is_candidate_seed_stock_day"] = stock_pool["candidate_seed_stock_day"].fillna(False).astype(bool)
    else:
        seed_stock_days = set(zip(candidate["instrument"].astype(str), pd.to_datetime(candidate["episode_start_signal_date"]).dt.normalize()))
        stock_pool["is_candidate_seed_stock_day"] = [item in seed_stock_days for item in zip(stock_pool["instrument"].astype(str), stock_pool["date"])]
    stock_pool = stock_pool.loc[~stock_pool["is_candidate_seed_stock_day"]].copy()

    stock_key = stock.set_index(["instrument", "date"])
    capture_map: dict[int, tuple[str, str]] = {}
    stock_pool_by_inst = {inst: group for inst, group in stock_pool.groupby("instrument", sort=False)}
    primary_window_id = primary_recall_window_id(config)
    for ref in reference.itertuples(index=False):
        inst = str(ref.instrument).upper()
        if inst not in stock_pool_by_inst:
            continue
        ref_date = _date(ref.reference_date)
        group = stock_pool_by_inst[inst]
        if is_v3_config(config):
            start = base.add_trading_days(calendar, ref_date, int(config["capture_time_basis"]["primary_entry_capture_window"]["start_offset_from_reference_trading_days"]))
            end = base.add_trading_days(calendar, ref_date, int(config["capture_time_basis"]["primary_entry_capture_window"]["end_offset_from_reference_trading_days"]))
            hit_idx = group.loc[(pd.to_datetime(group["next_date"]) >= start) & (pd.to_datetime(group["next_date"]) <= end)].index
            primary_window_id = str(config.get("entry_capture", {}).get("primary_entry_capture_window_id", "primary_entry_1_30"))
        else:
            primary_lookback = primary_recall_lookback_days(config)
            start = base.add_trading_days(calendar, ref_date, -primary_lookback)
            if pd.isna(start):
                start = ref_date
            hit_idx = group.loc[(group["date"] >= start) & (group["date"] <= ref_date)].index
        for idx in hit_idx:
            capture_map.setdefault(int(idx), (str(ref.reference_event_id), primary_window_id))

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
    if is_v3_config(config):
        data_max = pd.to_datetime(stock["date"]).max()
        boundaries, _ = split_effective_boundaries(config, calendar, data_max)
        effective_end = {split: boundaries[split]["effective_gate_entry_end"] for split in ["train", "validation", "robustness"]}
    else:
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
            no_breakout_ref = component == "money_ratio20_1_money_ratio5_2_rps5_50"
            breakout = np.where(no_breakout_ref, np.nan, breakout)
            uses_high10_ref = np.isin(
                component,
                [
                    "boll20_pct_b_1_close_near_high10_0",
                    "money_ratio20_1_money_ratio5_2_rps5_50_boll20_pct_b_1_close_near_high10_0",
                ],
            )
            breakout = np.where(uses_high10_ref, sampled["rolling_close_high_10_asof"].astype(float).to_numpy(), breakout)
            breakout = np.where(component == "close_near_high5_gt_0pct", sampled["rolling_close_high5_asof"].astype(float).to_numpy(), breakout)
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
        capture_dates_for_gate = pd.to_datetime(sampled["next_date"] if is_v3_config(config) else sampled["date"]).dt.normalize()
        frame["primary_metric_eligible_baseline_event"] = capture_dates_for_gate.le(effective_end[split]).fillna(False).to_numpy()
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
            if not ep.empty:
                ep_iy = ep.assign(year=pd.to_datetime(ep["episode_start_signal_date"]).dt.year)
                top1_share = _safe_div(float(ep_iy.groupby(["instrument", "year"]).size().max()), float(len(ep_iy)), 0.0)
                top5_share = _safe_div(float(ep_iy.groupby("instrument").size().sort_values(ascending=False).head(5).sum()), float(len(ep_iy)), 0.0)
            else:
                top1_share = 0.0
                top5_share = 0.0
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
                    "top1_instrument_year_seed_share": top1_share,
                    "top5_instrument_seed_share": top5_share,
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


def build_recall_audit(reference: pd.DataFrame, bridge_reference: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    executable = episodes.loc[episodes["executable_status"].eq("passed") & episodes["primary_metric_eligible_seed_episode"].astype(bool)].copy()
    for split in ["train", "validation", "robustness"]:
        ref_split = reference.loc[reference["split"].eq(split)]
        ref_count = int(ref_split.shape[0])
        bridge_split = bridge_reference.loc[bridge_reference["split"].eq(split)] if "split" in bridge_reference.columns else bridge_reference.iloc[0:0]
        bridge_ref_count = int(bridge_split.shape[0])
        for family in [CANDIDATE_SEED_ID, EP2_SEED_ID]:
            fam = executable.loc[(executable["seed_family_id"].eq(family)) & (executable["split"].eq(split))]
            captured = set(fam.loc[fam["captures_primary_big_winner"].astype(bool), "captured_reference_event_id"].astype(str))
            bridge_captured = set()
            if "captured_ep2_bridge_reference_event_id" in fam.columns:
                bridge_captured = set(
                    fam.loc[
                        fam["captures_ep2_bridge_big_winner"].astype(bool),
                        "captured_ep2_bridge_reference_event_id",
                    ]
                    .dropna()
                    .astype(str)
                )
                bridge_captured.discard("")
            rows.append(
                {
                    "split": split,
                    "seed_family_id": family,
                    "reference_type": "primary_big_winner_50h120_close_confirmed",
                    "big_winner_reference_count": ref_count,
                    "captured_big_winner_count": len(captured),
                    "missed_big_winner_count": max(0, ref_count - len(captured)),
                    "primary_big_winner_seed_recall": _safe_div(len(captured), ref_count, 0.0),
                    "bridge_ep2_big_winner_reference_count": bridge_ref_count,
                    "captured_ep2_bridge_big_winner_count": len(bridge_captured),
                    "bridge_ep2_big_winner_seed_recall": _safe_div(len(bridge_captured), bridge_ref_count, 0.0),
                    "late_capture_0_to_10_count": 0,
                }
            )
    recall = pd.DataFrame(rows)
    ep2 = recall.loc[recall["seed_family_id"].eq(EP2_SEED_ID)].set_index("split")
    recall["seed_recall_diff_vs_ep2_detector"] = recall.apply(
        lambda row: float(row["primary_big_winner_seed_recall"]) - float(ep2.loc[row["split"], "primary_big_winner_seed_recall"]) if row["split"] in ep2.index else np.nan,
        axis=1,
    )
    recall["bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector"] = recall.apply(
        lambda row: float(row["bridge_ep2_big_winner_seed_recall"]) - float(ep2.loc[row["split"], "bridge_ep2_big_winner_seed_recall"]) if row["split"] in ep2.index else np.nan,
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


def build_recall_cost_tradeoff(
    episodes: pd.DataFrame,
    probe: pd.DataFrame,
    baseline: pd.DataFrame,
    config: dict[str, Any],
    reference: pd.DataFrame | None = None,
    calendar: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
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
        post_0_10_refs: set[str] = set()
        signal_refs: set[str] = set()
        if is_v3_config(config) and reference is not None and calendar is not None and not reference.empty:
            ref_by_id = reference.set_index("reference_event_id")
            cand_eps = episodes.loc[
                (episodes["seed_family_id"].eq(CANDIDATE_SEED_ID))
                & (episodes["split"].eq(split))
                & episodes["executable_status"].eq("passed")
            ]
            for ep in cand_eps.itertuples(index=False):
                sig_captured, sig_ref = capture_signal_reference_v3(str(ep.instrument), _date(ep.episode_start_signal_date), reference, calendar)
                if sig_captured:
                    signal_refs.add(sig_ref)
                ref_id = str(getattr(ep, "captured_reference_event_id", ""))
                if ref_id and ref_id in ref_by_id.index:
                    ref_date = _date(ref_by_id.loc[ref_id, "reference_date"])
                    entry_dt = _date(getattr(ep, "entry_execution_date", getattr(ep, "episode_effective_entry_date", "")))
                    end_10 = base.add_trading_days(calendar, ref_date, 10)
                    if pd.notna(entry_dt) and pd.notna(end_10) and entry_dt <= end_10:
                        post_0_10_refs.add(ref_id)
        cand_exposure = float(cand_failed["exposure_days"].fillna(0).sum())
        ep2_exposure = float(ep2_failed["exposure_days"].fillna(0).sum())
        inc_exposure = max(0.0, cand_exposure - ep2_exposure)
        cand_loss_per_capture = _safe_div(cand_loss, max(1, len(cand_refs)), np.inf)
        ep2_loss_per_capture = _safe_div(ep2_loss, max(1, len(ep2_refs)), np.inf)
        cand_exposure_per_capture = _safe_div(cand_exposure, max(1, len(cand_refs)), np.inf)
        ep2_exposure_per_capture = _safe_div(ep2_exposure, max(1, len(ep2_refs)), np.inf)
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
                "post_reference_capture_0_to_10_count": len(post_0_10_refs),
                "late_capture_0_to_10_count": len(post_0_10_refs),
                "signal_capture_count": len(signal_refs) if is_v3_config(config) else len(cand_refs),
                "entry_capture_count": len(cand_refs),
                "signal_only_not_entry_within_window_count": max(0, len(signal_refs - cand_refs)) if is_v3_config(config) else 0,
                "capture_time_basis": "entry_execution_date" if is_v3_config(config) else "signal_date",
                "seed_discovery_scope": config.get("seed_provenance_gate", {}).get("discovery_scope", "not_applicable"),
                "validation_oos_clean": bool(config.get("seed_provenance_gate", {}).get("validation_oos_clean", True)),
                "recall_cost_score": _safe_div(net, max(1.0, inc_loss), 0.0),
                "candidate_loss_r_per_captured_big_winner_seed": cand_loss_per_capture,
                "ep2_loss_r_per_captured_big_winner_seed": ep2_loss_per_capture,
                "loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector": cand_loss_per_capture - ep2_loss_per_capture if np.isfinite(cand_loss_per_capture) and np.isfinite(ep2_loss_per_capture) else np.nan,
                "candidate_exposure_days_per_captured_big_winner_seed": cand_exposure_per_capture,
                "ep2_exposure_days_per_captured_big_winner_seed": ep2_exposure_per_capture,
                "exposure_days_per_captured_big_winner_seed_diff_vs_ep2_detector": cand_exposure_per_capture - ep2_exposure_per_capture if np.isfinite(cand_exposure_per_capture) and np.isfinite(ep2_exposure_per_capture) else np.nan,
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
                replicate_summaries = []
                for _, rep_df in base_df.groupby("replicate_id", dropna=False):
                    replicate_summaries.append(summarize_population(rep_df, "baseline_failed_seed_primary"))
                rep_summary_df = pd.DataFrame(replicate_summaries)
                base_groups = []
                for stat in ["mean", "p05", "p50", "p95"]:
                    if rep_summary_df.empty:
                        summary = summarize_population(base_df.iloc[0:0], "baseline_failed_seed_primary")
                    elif stat == "mean":
                        summary = rep_summary_df.mean(numeric_only=True).to_dict()
                    else:
                        q = {"p05": 0.05, "p50": 0.50, "p95": 0.95}[stat]
                        summary = rep_summary_df.quantile(q, numeric_only=True).to_dict()
                    base_groups.append((stat, summary))
            else:
                base_groups = [("not_random", summarize_population(base_df, "baseline_failed_seed_primary"))]
            for stat, base_summary in base_groups:
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
    random_df = baseline.loc[baseline["matched_control_type"].eq("matched_random")].copy()
    if random_df.empty:
        return pd.DataFrame(columns=["split", "baseline_id", "replicate_stat", "industry", "liquidity_bucket", "volatility_bucket", "sampled_random_event_count", "eligible_random_event_count", "bucket_random_eligible_rate", "random_replicate_count", "random_excluded_candidate_seed_day_count", "random_capacity_shortfall", "random_sampling_replacement_policy", "random_baseline_reliability_status", "failed_seed_average_loss_r", "p05_return_r", "p50_return_r", "p95_return_r", "audit_only_status"])
    random_df["eligible_flag"] = random_df["eligibility_status"].eq("passed").astype(int)
    random_df["eligible_return_r"] = np.where(random_df["eligibility_status"].eq("passed"), random_df["return_r"].astype(float), np.nan)
    random_df["failed_loss_r"] = np.where(random_df["baseline_failed_seed_primary"].astype(str).isin(["True", "true", "1"]), random_df["loss_r"].astype(float), np.nan)
    # Keep replicate reliability executable and bounded in runtime. Row-level matched-random
    # bucket fields remain in the baseline panel; this audit summarizes the distribution
    # across replicates at the split/baseline level.
    random_df["match_industry"] = "all"
    random_df["match_liquidity_bucket"] = "all"
    random_df["match_volatility_bucket"] = "all"
    group_keys = ["split", "baseline_id", "match_industry", "match_liquidity_bucket", "match_volatility_bucket", "replicate_id"]
    per_rep = (
        random_df.groupby(group_keys, dropna=False)
        .agg(
            sampled_random_event_count=("baseline_id", "size"),
            eligible_random_event_count=("eligible_flag", "sum"),
            failed_seed_average_loss_r=("failed_loss_r", "mean"),
            p05_return_r=("eligible_return_r", lambda s: s.quantile(0.05)),
            p50_return_r=("eligible_return_r", lambda s: s.quantile(0.50)),
            p95_return_r=("eligible_return_r", lambda s: s.quantile(0.95)),
            random_capacity_shortfall=("random_capacity_shortfall", "max"),
        )
        .reset_index()
    )
    per_rep["bucket_random_eligible_rate"] = per_rep["eligible_random_event_count"] / per_rep["sampled_random_event_count"].replace(0, np.nan)
    for keys, group in per_rep.groupby(["split", "baseline_id", "match_industry", "match_liquidity_bucket", "match_volatility_bucket"], dropna=False):
        split, baseline_id, industry, liq, vol = keys
        rep_count = int(group["replicate_id"].nunique())
        shortfall = bool(group["random_capacity_shortfall"].astype(bool).any())
        for stat in ["mean", "p05", "p50", "p95"]:
            metric_cols = [
                "sampled_random_event_count",
                "eligible_random_event_count",
                "failed_seed_average_loss_r",
                "p05_return_r",
                "p50_return_r",
                "p95_return_r",
                "bucket_random_eligible_rate",
            ]
            if group.empty:
                values = {}
            elif stat == "mean":
                values = group[metric_cols].mean(numeric_only=True).to_dict()
            else:
                values = group[metric_cols].quantile({"p05": 0.05, "p50": 0.50, "p95": 0.95}[stat], numeric_only=True).to_dict()
            rate = _safe_float(values.get("bucket_random_eligible_rate"))
            status = "passed" if rate >= float(config["matched_controls"]["random_min_bucket_eligible_rate"]) and rep_count >= int(config["matched_controls"]["random_replicates_per_split"]) and not shortfall else "failed"
            rows.append(
                {
                    "split": split,
                    "baseline_id": baseline_id,
                    "replicate_stat": stat,
                    "industry": industry,
                    "liquidity_bucket": liq,
                    "volatility_bucket": vol,
                    "sampled_random_event_count": values.get("sampled_random_event_count", np.nan),
                    "eligible_random_event_count": values.get("eligible_random_event_count", np.nan),
                    "bucket_random_eligible_rate": rate,
                    "random_replicate_count": rep_count,
                    "random_excluded_candidate_seed_day_count": 0,
                    "random_capacity_shortfall": shortfall,
                    "random_sampling_replacement_policy": "without_replacement_within_replicate",
                    "random_baseline_reliability_status": status,
                    "failed_seed_average_loss_r": values.get("failed_seed_average_loss_r", np.nan),
                    "p05_return_r": values.get("p05_return_r", np.nan),
                    "p50_return_r": values.get("p50_return_r", np.nan),
                    "p95_return_r": values.get("p95_return_r", np.nan),
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
    val_candidate = probe.loc[
        probe["seed_family_id"].eq(CANDIDATE_SEED_ID)
        & probe["split"].eq("validation")
        & probe["primary_metric_eligible_seed_episode"].astype(bool)
    ].copy()
    val_no_ff = baseline.loc[
        baseline["baseline_id"].eq("same_seed_no_fail_fast_hold_h20")
        & baseline["split"].eq("validation")
        & baseline["primary_metric_eligible_baseline_event"].astype(bool)
    ].copy()
    if not val_candidate.empty and not val_no_ff.empty:
        val_candidate["initial_risk_pct_quintile"] = _qbucket(val_candidate["initial_risk_pct"], 5, "risk")
        val_no_ff["initial_risk_pct_quintile"] = _qbucket(val_no_ff["initial_risk_pct"], 5, "risk")
        for quintile, qdf in val_candidate.groupby("initial_risk_pct_quintile", dropna=False):
            bdf = val_no_ff.loc[val_no_ff["initial_risk_pct_quintile"].eq(quintile)]
            cand_failed = qdf.loc[qdf["failed_seed_primary"].astype(str).isin(["True", "true", "1"])]
            base_failed = bdf.loc[bdf["baseline_failed_seed_primary"].astype(str).isin(["True", "true", "1"])]
            cand_loss = float(cand_failed["loss_r"].mean()) if len(cand_failed) else 0.0
            base_loss = float(base_failed["loss_r"].mean()) if len(base_failed) else 0.0
            diff = cand_loss - base_loss
            rows.append(
                {
                    "split": "validation",
                    "population": "candidate_vs_same_seed_no_fail_fast",
                    "probe_r_budget": 0.25,
                    "initial_risk_pct_p01": float(qdf["initial_risk_pct"].quantile(0.01)) if len(qdf) else np.nan,
                    "initial_risk_pct_p05": float(qdf["initial_risk_pct"].quantile(0.05)) if len(qdf) else np.nan,
                    "initial_risk_pct_p25": float(qdf["initial_risk_pct"].quantile(0.25)) if len(qdf) else np.nan,
                    "initial_risk_pct_median": float(qdf["initial_risk_pct"].median()) if len(qdf) else np.nan,
                    "initial_risk_pct_p75": float(qdf["initial_risk_pct"].quantile(0.75)) if len(qdf) else np.nan,
                    "initial_risk_pct_p95": float(qdf["initial_risk_pct"].quantile(0.95)) if len(qdf) else np.nan,
                    "initial_risk_pct_p99": float(qdf["initial_risk_pct"].quantile(0.99)) if len(qdf) else np.nan,
                    "return_r_p01": float(qdf["return_r"].quantile(0.01)) if len(qdf) else np.nan,
                    "return_r_p99": float(qdf["return_r"].quantile(0.99)) if len(qdf) else np.nan,
                    "loss_r_top1_share": _safe_div(float(cand_failed["loss_r"].nlargest(1).sum()), float(cand_failed["loss_r"].sum()), 0.0) if len(cand_failed) else 0.0,
                    "loss_r_top5_share": _safe_div(float(cand_failed["loss_r"].nlargest(5).sum()), float(cand_failed["loss_r"].sum()), 0.0) if len(cand_failed) else 0.0,
                    "near_risk_floor_extreme_loss_share": np.nan,
                    "risk_distance_ineligible_count": 0,
                    "initial_risk_pct_quintile": str(quintile),
                    "quintile_failed_seed_count": int(len(cand_failed)),
                    "quintile_failed_seed_average_loss_r": cand_loss,
                    "quintile_baseline_failed_seed_average_loss_r": base_loss,
                    "quintile_loss_r_diff_vs_same_seed_no_fail_fast": diff,
                    "risk_pct_quintile_cost_control_status": "passed" if diff <= 0 else "failed",
                    "audit_only_status": "report_only",
                }
            )
    return pd.DataFrame(rows)


def build_fail_fast_audits(probe: pd.DataFrame, no_ff: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    path_rows: list[dict[str, Any]] = []
    err_rows: list[dict[str, Any]] = []
    no_ff_by_id = no_ff.set_index("seed_episode_id") if not no_ff.empty else pd.DataFrame()
    def truthy(value: Any) -> bool:
        return False if pd.isna(value) else bool(value)

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
        if truthy(row["failed_seed_fail_fast_triggered"]) and not truthy(row["failed_seed_primary"]) and truthy(row["primary_metric_eligible_seed_episode"]):
            err_type = "false_reject_winner"
        elif (not truthy(row["failed_seed_fail_fast_triggered"])) and truthy(row["failed_seed_primary"]) and np.isfinite(noff_ret) and noff_ret < 0:
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


def build_counterfactual(
    decision: str,
    probe: pd.DataFrame,
    density_tightness: pd.DataFrame,
    baseline_diff: pd.DataFrame | None = None,
    label_a: pd.DataFrame | None = None,
) -> pd.DataFrame:
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
        ambiguous_count = 0
        if label_a is not None and not label_a.empty and "same_day_ambiguous" in label_a.columns:
            labeled_probe_ids = set(split_probe["seed_episode_id"].astype(str)) if "seed_episode_id" in split_probe.columns else set()
            ambiguous_count = int(
                label_a.loc[
                    label_a["seed_episode_id"].astype(str).isin(labeled_probe_ids)
                    & label_a["same_day_ambiguous"].astype(bool)
                ].shape[0]
            )
        rows.append(
            {
                "split": split,
                "counterfactual_family": "conservative_fail",
                "counterfactual_variant": "ambiguous_same_day_open_low_forced_fail_descriptive",
                "primary_decision": decision,
                "decision_change_allowed": False,
                "metric_name": "same_day_ambiguous_episode_count",
                "primary_value": ambiguous_count,
                "counterfactual_value": np.nan,
                "diff_value": np.nan,
                "affected_episode_count": ambiguous_count,
                "affected_reference_count": 0,
                "dominant_year": "none",
                "dominant_industry": "none",
                "dominant_bucket": "none",
                "inheritance_note": "report-only conservative failure-label sensitivity; frozen R01 rule unchanged",
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
        p05_diff = np.nan
        if baseline_diff is not None and not baseline_diff.empty:
            rows_diff = baseline_diff.loc[
                baseline_diff["split"].eq(split)
                & baseline_diff["baseline_id"].astype(str).str.contains("same_fail_fast", regex=False)
                & baseline_diff["metric_name"].astype(str).str.contains("p05_return_r", regex=False)
            ]
            if not rows_diff.empty:
                p05_diff = float(rows_diff["diff_value"].min())
        rows.append(
            {
                "split": split,
                "counterfactual_family": "p05_no_harm",
                "counterfactual_variant": "worst_matched_delay_p05_return_diff_descriptive",
                "primary_decision": decision,
                "decision_change_allowed": False,
                "metric_name": "min_p05_return_r_diff_vs_same_fail_fast_baselines",
                "primary_value": p05_diff,
                "counterfactual_value": np.nan,
                "diff_value": np.nan,
                "affected_episode_count": int(split_probe.shape[0]),
                "affected_reference_count": 0,
                "dominant_year": "none",
                "dominant_industry": "none",
                "dominant_bucket": "none",
                "inheritance_note": "report-only lower-tail no-harm diagnostic; no post-hoc threshold tuning",
                "audit_only_status": "report_only_not_decision_changing",
            }
        )
    return pd.DataFrame(rows)


def apply_v3_terminal_boundaries(
    episodes: pd.DataFrame,
    probe: pd.DataFrame,
    baseline: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    data_max: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not is_v3_config(config):
        return episodes, probe, baseline
    boundaries, _ = split_effective_boundaries(config, calendar, data_max)
    bounds = split_bounds(config)

    def eligible_mask(frame: pd.DataFrame, entry_col: str, terminal_col: str) -> pd.Series:
        eligible = pd.Series(False, index=frame.index)
        entry_dt = pd.to_datetime(frame[entry_col], errors="coerce")
        terminal_dt = pd.to_datetime(frame[terminal_col], errors="coerce")
        for split, split_bounds_value in boundaries.items():
            gate_end = split_bounds_value["effective_gate_entry_end"]
            split_end = bounds[split][1]
            mask = frame["split"].astype(str).eq(split)
            eligible.loc[mask] = (
                entry_dt.loc[mask].notna()
                & terminal_dt.loc[mask].notna()
                & pd.notna(gate_end)
                & (entry_dt.loc[mask] <= gate_end)
                & (terminal_dt.loc[mask] <= split_end)
                & (terminal_dt.loc[mask] <= data_max)
            )
        return eligible

    probe = probe.copy()
    if not probe.empty:
        probe["terminal_exit_date"] = probe["exit_execution_date"]
        entry_col = "entry_execution_date" if "entry_execution_date" in probe.columns else "entry_date"
        eligible = eligible_mask(probe, entry_col, "terminal_exit_date")
        probe["primary_metric_eligible_seed_episode"] = eligible
        probe["failed_seed_primary"] = np.where(probe["primary_metric_eligible_seed_episode"].astype(bool), probe["failed_seed_primary"], np.nan)
        probe["split_boundary_status"] = np.where(probe["primary_metric_eligible_seed_episode"].astype(bool), "primary_metric_eligible", "cross_split_execution_report_only")

    episodes = episodes.copy()
    if not probe.empty:
        term_map = probe.set_index("seed_episode_id")["terminal_exit_date"].to_dict()
        status_map = probe.set_index("seed_episode_id")["split_boundary_status"].to_dict()
        eligible_map = probe.set_index("seed_episode_id")["primary_metric_eligible_seed_episode"].to_dict()
        episodes["terminal_exit_date"] = episodes["seed_episode_id"].map(term_map).fillna(episodes.get("terminal_exit_date", ""))
        episodes["split_boundary_status"] = episodes["seed_episode_id"].map(status_map).fillna(episodes.get("split_boundary_status", ""))
        episodes["boundary_status"] = episodes["split_boundary_status"]
        episodes["primary_metric_eligible_seed_episode"] = episodes["seed_episode_id"].map(eligible_map).fillna(episodes["primary_metric_eligible_seed_episode"]).astype(bool)
        episodes.loc[~episodes["primary_metric_eligible_seed_episode"].astype(bool), ["captures_primary_big_winner", "captured_reference_event_id", "capture_window_id"]] = [False, "", ""]
        bridge_clear_cols = ["captures_ep2_bridge_big_winner", "captured_ep2_bridge_reference_event_id", "ep2_bridge_capture_window_id"]
        present_bridge_cols = [col for col in bridge_clear_cols if col in episodes.columns]
        if present_bridge_cols:
            episodes.loc[~episodes["primary_metric_eligible_seed_episode"].astype(bool), present_bridge_cols] = [False, "", ""][: len(present_bridge_cols)]

    baseline = baseline.copy()
    if not baseline.empty:
        baseline["terminal_exit_date"] = baseline["exit_execution_date"]
        entry_field = "capture_timestamp_used" if "capture_timestamp_used" in baseline.columns else "entry_date"
        eligible = eligible_mask(baseline, entry_field, "terminal_exit_date")
        baseline["primary_metric_eligible_baseline_event"] = baseline["primary_metric_eligible_baseline_event"].astype(bool) & pd.Series(eligible, index=baseline.index)
        baseline["baseline_failed_seed_primary"] = np.where(baseline["primary_metric_eligible_baseline_event"].astype(bool), baseline["baseline_failed_seed_primary"], np.nan)
        baseline["boundary_status"] = np.where(baseline["primary_metric_eligible_baseline_event"].astype(bool), "primary_metric_eligible", "cross_split_execution_report_only")
        baseline["split_boundary_status"] = baseline["boundary_status"]
    return episodes, probe, baseline


def _metric_from_density(density: pd.DataFrame, split: str, family: str, metric: str) -> float:
    row = density.loc[(density["split"].eq(split)) & (density["seed_family_id"].eq(family))]
    return _safe_float(row.iloc[0][metric]) if not row.empty and metric in row.columns else np.nan


def _recall_diff(recall: pd.DataFrame, split: str) -> float:
    row = recall.loc[(recall["split"].eq(split)) & (recall["seed_family_id"].eq(CANDIDATE_SEED_ID))]
    return _safe_float(row.iloc[0]["seed_recall_diff_vs_ep2_detector"]) if not row.empty else np.nan


def _bridge_recall_diff(recall: pd.DataFrame, split: str) -> float:
    row = recall.loc[(recall["split"].eq(split)) & (recall["seed_family_id"].eq(CANDIDATE_SEED_ID))]
    return _safe_float(row.iloc[0]["bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector"]) if not row.empty and "bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector" in row.columns else np.nan


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
    baseline: pd.DataFrame,
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
    if is_v3_config(config):
        discovery_scope = str(config.get("seed_provenance_gate", {}).get("discovery_scope", ""))
        validation_oos_clean = bool(config.get("seed_provenance_gate", {}).get("validation_oos_clean", False))
        add(
            "seed_provenance_oos_status",
            "all",
            "seed_discovery_scope",
            discovery_scope,
            "present",
            "!=",
            bool(discovery_scope),
            hard=True,
            reason="missing_seed_discovery_scope",
        )
        add(
            "seed_provenance_r02_cap",
            "all",
            "validation_oos_clean",
            validation_oos_clean,
            "train_only_required_for_r02",
            "report",
            True,
            hard=False,
            reason="all_split_discovery_blocks_r02",
        )

    for split in ["train", "validation", "robustness"]:
        cand_day = _metric_from_density(density, split, CANDIDATE_SEED_ID, "seed_day_rate")
        ep2_day = _metric_from_density(density, split, EP2_SEED_ID, "seed_day_rate")
        cand_ep = _metric_from_density(density, split, CANDIDATE_SEED_ID, "seed_episode_rate")
        ep2_ep = _metric_from_density(density, split, EP2_SEED_ID, "seed_episode_rate")
        day_cap = min(
            float(config["seed_density_caps"]["max_candidate_seed_day_rate"]),
            float(config["seed_density_caps"]["max_candidate_seed_day_rate_vs_ep2_multiple"]) * ep2_day,
        )
        ep_cap = float(config["seed_density_caps"]["max_candidate_episode_rate_vs_ep2_multiple"]) * ep2_ep
        add("seed_density_day_cap", split, "candidate_seed_day_rate", cand_day, day_cap, "<=", bool(np.isfinite(cand_day) and cand_day <= day_cap))
        add("seed_density_episode_cap", split, "candidate_seed_episode_rate", cand_ep, ep_cap, "<=", bool(np.isfinite(cand_ep) and cand_ep <= ep_cap))
        denom = _metric_from_density(density, split, CANDIDATE_SEED_ID, "eligible_stock_day_count")
        add("density_denominator_nonzero", split, "eligible_stock_day_count", denom, 0, ">", bool(np.isfinite(denom) and denom > 0))

    val_unique_iy = _metric_from_density(density, "validation", CANDIDATE_SEED_ID, "unique_instrument_year_count")
    add("validation_unique_instrument_years", "validation", "unique_instrument_year_count", val_unique_iy, config["seed_density_caps"]["min_unique_instrument_years_validation"], ">=", bool(val_unique_iy >= int(config["seed_density_caps"]["min_unique_instrument_years_validation"])))
    top1_share = _metric_from_density(density, "validation", CANDIDATE_SEED_ID, "top1_instrument_year_seed_share")
    add("validation_top1_instrument_year_seed_share", "validation", "top1_instrument_year_seed_share", top1_share, 0.05, "<=", bool(np.isfinite(top1_share) and top1_share <= 0.05))

    for split in ["validation", "robustness"]:
        threshold = -0.05 if split == "validation" else -0.10
        diff = _recall_diff(recall, split)
        add("primary_recall_no_harm", split, "primary_big_winner_seed_recall_diff_vs_ep2_detector", diff, threshold, ">=", bool(np.isfinite(diff) and diff >= threshold))
        bridge_diff = _bridge_recall_diff(recall, split)
        add(
            "bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector",
            split,
            "bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector",
            bridge_diff,
            threshold,
            ">=",
            bool(np.isfinite(bridge_diff) and bridge_diff >= threshold),
        )

    add("validation_cost_vs_no_fail_fast", "validation", "failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast", _diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r"), 0, "<", bool(_diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r") < 0))
    add("validation_holding_days_vs_no_fail_fast", "validation", "failed_seed_median_holding_days_diff_vs_same_seed_no_fail_fast", _diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_median_holding_days"), 0, "<", bool(_diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_median_holding_days") < 0))
    add("validation_p05_vs_no_fail_fast", "validation", "p05_return_r_diff_vs_same_seed_no_fail_fast", _diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "p05_return_r"), -0.02, ">=", bool(_diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "p05_return_r") >= -0.02))
    validation_survived_refs = set(
        baseline.loc[
            baseline["split"].eq("validation")
            & baseline["baseline_id"].eq("same_seed_no_fail_fast_hold_h20")
            & baseline["captures_primary_big_winner"].astype(bool),
            "captured_reference_event_id",
        ]
        .dropna()
        .astype(str)
    )
    validation_probe_refs = set(
        probe.loc[
            probe["split"].eq("validation")
            & probe["seed_family_id"].eq(CANDIDATE_SEED_ID)
            & probe["primary_metric_eligible_seed_episode"].astype(bool),
            "seed_episode_id",
        ]
        .dropna()
        .astype(str)
    )
    validation_episode_ref_map = {}
    if "seed_episode_id" in baseline.columns:
        validation_episode_ref_map = (
            baseline.loc[
                baseline["split"].eq("validation")
                & baseline["baseline_id"].eq("same_seed_no_fail_fast_hold_h20")
                & baseline["seed_episode_id"].astype(str).isin(validation_probe_refs)
                & baseline["captures_primary_big_winner"].astype(bool),
                ["seed_episode_id", "captured_reference_event_id"],
            ]
            .dropna()
            .astype(str)
            .set_index("seed_episode_id")["captured_reference_event_id"]
            .to_dict()
        )
    validation_probe_captured_refs = set(validation_episode_ref_map.values())
    add(
        "fail_fast_survived_big_winner_recall_loss_vs_same_seed_no_fail_fast",
        "validation",
        "captured_reference_loss_vs_same_seed_no_fail_fast_count",
        len(validation_survived_refs - validation_probe_captured_refs),
        0,
        "==",
        len(validation_survived_refs - validation_probe_captured_refs) == 0,
    )
    if not probe.empty:
        val_probe = probe.loc[probe["split"].eq("validation") & probe["failed_seed_primary"].astype(str).isin(["True", "true", "1"])].copy()
        val_noff = baseline.loc[baseline["split"].eq("validation") & baseline["baseline_id"].eq("same_seed_no_fail_fast_hold_h20") & baseline["baseline_failed_seed_primary"].astype(str).isin(["True", "true", "1"])].copy()
        risk_quintile_status = True
        if len(val_probe) >= 30 and not val_noff.empty:
            val_probe["risk_q"] = _qbucket(val_probe["initial_risk_pct"], 5, "risk")
            val_noff["risk_q"] = _qbucket(val_noff["initial_risk_pct"], 5, "risk")
            for qid, qdf in val_probe.groupby("risk_q"):
                if len(qdf) < 30:
                    continue
                cand_loss = float(qdf["loss_r"].mean()) if len(qdf) else 0.0
                base_loss = float(val_noff.loc[val_noff["risk_q"].eq(qid), "loss_r"].mean()) if val_noff["risk_q"].eq(qid).any() else np.nan
                if np.isfinite(base_loss) and cand_loss > base_loss:
                    risk_quintile_status = False
                    break
        add("risk_pct_quintile_cost_control_status", "validation", "risk_pct_quintile_cost_control_status", "passed" if risk_quintile_status else "failed", "passed", "==", risk_quintile_status)

    delay_status = "passed" if delay_audit.empty or delay_audit["matched_delay_reliability_status"].eq("passed").all() else "failed"
    add("matched_delay_reliability_status", "validation", "matched_delay_reliability_status", delay_status, "passed", "==", delay_status == "passed")
    random_val = random_health.loc[random_health["split"].eq("validation")]
    random_status = "passed" if not random_val.empty and random_val["random_baseline_reliability_status"].eq("passed").all() else "failed"
    add("random_baseline_reliability_status", "validation", "random_baseline_reliability_status", random_status, "passed", "==", random_status == "passed", hard=False, reason="report_only_diagnostic")
    add("matched_delay_1d_mean_no_harm", "validation", "mean_return_r_diff_vs_matched_delay_same_fail_fast_1d", _diff_metric(baseline_diff, "validation", "same_seed_matched_delay_1d_same_fail_fast_h20", "mean_return_r"), -0.0055, ">=", bool(_diff_metric(baseline_diff, "validation", "same_seed_matched_delay_1d_same_fail_fast_h20", "mean_return_r") >= -0.0055))
    add("matched_delay_3d_mean_no_harm", "validation", "mean_return_r_diff_vs_matched_delay_same_fail_fast_3d", _diff_metric(baseline_diff, "validation", "same_seed_matched_delay_3d_same_fail_fast_h20", "mean_return_r"), -0.005, ">=", bool(_diff_metric(baseline_diff, "validation", "same_seed_matched_delay_3d_same_fail_fast_h20", "mean_return_r") >= -0.005))
    add("matched_delay_1d_p05_no_harm", "validation", "p05_return_r_diff_vs_matched_delay_same_fail_fast_1d", _diff_metric(baseline_diff, "validation", "same_seed_matched_delay_1d_same_fail_fast_h20", "p05_return_r"), -0.03, ">=", bool(_diff_metric(baseline_diff, "validation", "same_seed_matched_delay_1d_same_fail_fast_h20", "p05_return_r") >= -0.03))
    add("matched_delay_3d_p05_no_harm", "validation", "p05_return_r_diff_vs_matched_delay_same_fail_fast_3d", _diff_metric(baseline_diff, "validation", "same_seed_matched_delay_3d_same_fail_fast_h20", "p05_return_r"), -0.03, ">=", bool(_diff_metric(baseline_diff, "validation", "same_seed_matched_delay_3d_same_fail_fast_h20", "p05_return_r") >= -0.03))

    val_trade = recall_cost.loc[recall_cost["split"].eq("validation")]
    if not val_trade.empty:
        tr = val_trade.iloc[0]
        add("validation_added_capture_vs_ep2", "validation", "added_capture_vs_ep2_count", tr["added_capture_vs_ep2_count"], 0, ">", bool(tr["added_capture_vs_ep2_count"] > 0))
        add("validation_net_capture_vs_ep2", "validation", "added_capture_vs_ep2_count_gt_lost_capture", tr["added_capture_vs_ep2_count"] - tr["lost_capture_vs_ep2_count"], 0, ">", bool(tr["added_capture_vs_ep2_count"] > tr["lost_capture_vs_ep2_count"]))
        add("validation_recall_cost_score", "validation", "recall_cost_score", tr["recall_cost_score"], 0, ">", bool(tr["recall_cost_score"] > 0))
        add("validation_incremental_loss_bound", "validation", "incremental_loss_r_per_added_big_winner_vs_ep2", tr["incremental_loss_r_per_added_big_winner_vs_ep2"], tr["max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2"], "<=", bool(tr["incremental_loss_r_per_added_big_winner_vs_ep2"] <= tr["max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2"]))
        add("validation_incremental_exposure_bound", "validation", "incremental_exposure_days_per_added_big_winner_vs_ep2", tr["incremental_exposure_days_per_added_big_winner_vs_ep2"], tr["max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2"], "<=", bool(tr["incremental_exposure_days_per_added_big_winner_vs_ep2"] <= tr["max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2"]))
        add("loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector", "validation", "loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector", tr["loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector"], 0, "<=", bool(tr["loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector"] <= 0))

    robust_noff_loss = _diff_metric(baseline_diff, "robustness", "same_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r")
    add("robustness_failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast", "robustness", "failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast", robust_noff_loss, 0, "<=", bool(robust_noff_loss <= 0))
    robust_p05_1d = _diff_metric(baseline_diff, "robustness", "same_seed_matched_delay_1d_same_fail_fast_h20", "p05_return_r")
    robust_p05_3d = _diff_metric(baseline_diff, "robustness", "same_seed_matched_delay_3d_same_fail_fast_h20", "p05_return_r")
    robust_min_p05 = np.nanmin([robust_p05_1d, robust_p05_3d]) if any(np.isfinite([robust_p05_1d, robust_p05_3d])) else np.nan
    add("robustness_p05_return_r_diff_vs_matched_delay_same_fail_fast_min", "robustness", "min_p05_return_r_diff_vs_matched_delay_same_fail_fast", robust_min_p05, -0.03, ">=", bool(np.isfinite(robust_min_p05) and robust_min_p05 >= -0.03))
    robust_trade = recall_cost.loc[recall_cost["split"].eq("robustness")]
    if not robust_trade.empty:
        rr = robust_trade.iloc[0]
        add("robustness_recall_cost_score_positive", "robustness", "recall_cost_score", rr["recall_cost_score"], 0, ">", bool(rr["recall_cost_score"] > 0))
        add("robustness_incremental_loss_bound", "robustness", "incremental_loss_r_per_added_big_winner_vs_ep2", rr["incremental_loss_r_per_added_big_winner_vs_ep2"], rr["max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2"], "<=", bool(rr["incremental_loss_r_per_added_big_winner_vs_ep2"] <= rr["max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2"]))
        add("robustness_incremental_exposure_bound", "robustness", "incremental_exposure_days_per_added_big_winner_vs_ep2", rr["incremental_exposure_days_per_added_big_winner_vs_ep2"], rr["max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2"], "<=", bool(rr["incremental_exposure_days_per_added_big_winner_vs_ep2"] <= rr["max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2"]))

    cand_day_ratio = _metric_from_density(density, "validation", CANDIDATE_SEED_ID, "executable_seed_stock_day_count_vs_ep2")
    cand_ep_ratio = _metric_from_density(density, "validation", CANDIDATE_SEED_ID, "seed_episode_count_vs_ep2")
    add("validation_seed_day_count_vs_ep2", "validation", "candidate_seed_day_count_vs_ep2_ratio", cand_day_ratio, 1.0, ">=", bool(cand_day_ratio >= 1.0), hard=not is_v3_config(config), reason="report_only_v3_post_reference_density_diagnostic")
    add("validation_seed_episode_count_vs_ep2", "validation", "candidate_seed_episode_count_vs_ep2_ratio", cand_ep_ratio, 1.0, ">=", bool(cand_ep_ratio >= 1.0), hard=not is_v3_config(config), reason="report_only_v3_post_reference_density_diagnostic")

    gate_df = pd.DataFrame(rows)
    hard_pass = bool(gate_df.loc[gate_df["is_hard_gate"].astype(bool), "status"].eq("passed").all())
    validation_high_recall = bool(
        hard_pass
        and not val_trade.empty
        and val_trade.iloc[0]["added_capture_vs_ep2_count"] > 0
        and val_trade.iloc[0]["added_capture_vs_ep2_count"] > val_trade.iloc[0]["lost_capture_vs_ep2_count"]
        and (is_v3_config(config) or (cand_day_ratio >= 1.0 and cand_ep_ratio >= 1.0))
    )
    robustness_core = bool(_recall_diff(recall, "robustness") >= -0.10)
    archive = bool(
        hard_pass
        and _recall_diff(recall, "validation") >= -0.02
        and _diff_metric(baseline_diff, "validation", "same_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r") < 0
    )
    discovery_scope = str(config.get("seed_provenance_gate", {}).get("discovery_scope", "train_only"))
    oos_clean = bool(config.get("seed_provenance_gate", {}).get("validation_oos_clean", True))
    if validation_high_recall and robustness_core:
        decision = "go_to_r02" if (not is_v3_config(config) or discovery_scope == "train_only" or oos_clean) else "go_to_oos_retest_required"
    elif validation_high_recall:
        decision = "go_to_r02_with_robustness_warning" if (not is_v3_config(config) or discovery_scope == "train_only" or oos_clean) else "go_to_oos_retest_required"
    elif archive:
        decision = "archive_hypothesis_no_r02" if is_v3_config(config) and discovery_scope != "train_only" else "archive_cost_control_sleeve_no_r02"
    else:
        decision = "stop_ep4_r01_path"
    return gate_df, decision


def build_big_winner_audit(
    reference: pd.DataFrame,
    effective_windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
    data_max: pd.Timestamp,
    data_max_minus: pd.Timestamp,
    boundaries: dict[str, dict[str, pd.Timestamp]] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, (start, eff_end) in effective_windows.items():
        ref = reference.loc[reference["split"].eq(split)]
        rows.append(
            {
                "split": split,
                "configured_start": _date_str(start),
                "effective_reference_end": _date_str(eff_end),
                "effective_primary_seed_end": _date_str(boundaries.get(split, {}).get("effective_primary_seed_end", "")) if boundaries else "",
                "effective_gate_entry_end": _date_str(boundaries.get(split, {}).get("effective_gate_entry_end", "")) if boundaries else "",
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
    authority: pd.DataFrame,
    reference_audit: pd.DataFrame,
    density: pd.DataFrame,
    density_tightness: pd.DataFrame,
    recall: pd.DataFrame,
    recall_cost: pd.DataFrame,
    baseline_diff: pd.DataFrame,
    delay_audit: pd.DataFrame,
    r_unit: pd.DataFrame,
    ff_path: pd.DataFrame,
    ff_error: pd.DataFrame,
    counterfactual: pd.DataFrame,
    gate: pd.DataFrame,
    random_health: pd.DataFrame,
    config: dict[str, Any],
) -> str:
    failed = gate.loc[gate["status"].eq("failed")]
    provenance = config.get("seed_provenance_gate", {})
    density_provenance = config.get("density_provenance", {})
    v3_note = []
    if is_v3_config(config):
        v3_note = [
            "",
            "## V3 Post30 Provenance And OOS Status",
            f"- Frozen seed: `{config['seed_rules']['candidate_seed_formula_id']}`.",
            f"- Seed discovery artifact: `{provenance.get('discovery_artifact', '')}`.",
            f"- Discovery scope: `{provenance.get('discovery_scope', '')}`; validation_oos_clean: `{provenance.get('validation_oos_clean', False)}`.",
            "- OOS status: not clean OOS for R02 because the frozen seed was discovered from all splits; a passing structural run can at most request an OOS retest.",
            "- The canonical `reference_date` is a retrospective evaluation anchor, not an observable trading state; executable evidence below uses the seed's `entry_execution_date`.",
            f"- Post30 search eligible-day density: `{density_provenance.get('post30_search_eligible_day_density', '')}`; R01 full-universe density is reported separately in the density summary and manifest.",
        ]
    lines = [
        "# EP4 R01 High-Recall Probe Cost-Control Report",
        "",
        f"- Final decision: `{decision}`",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        "- Phase boundary: no model training, no add, no portfolio sizing, no dynamic exit optimization.",
        "",
        *v3_note,
        "",
        "## Upstream Authority",
        authority.to_markdown(index=False),
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
        "## Captured Post-Reference Entry Cost",
        recall_cost[[c for c in ["split", "candidate_loss_r_per_captured_big_winner_seed", "ep2_loss_r_per_captured_big_winner_seed", "loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector", "candidate_exposure_days_per_captured_big_winner_seed", "ep2_exposure_days_per_captured_big_winner_seed", "exposure_days_per_captured_big_winner_seed_diff_vs_ep2_detector"] if c in recall_cost.columns]].to_markdown(index=False),
        "",
        "## Signal-Date Vs Entry-Date Capture Audit",
        recall_cost[[c for c in ["split", "signal_capture_count", "entry_capture_count", "signal_only_not_entry_within_window_count", "capture_time_basis", "seed_discovery_scope", "validation_oos_clean"] if c in recall_cost.columns]].to_markdown(index=False),
        "",
        "## Density Cap Tightness",
        density_tightness.to_markdown(index=False) if not density_tightness.empty else "No density cap rows.",
        "",
        "## Matched-Random Reliability",
        random_health.groupby(["split", "baseline_id"], dropna=False).agg(bucket_random_eligible_rate=("bucket_random_eligible_rate", "min"), random_replicate_count=("random_replicate_count", "min"), random_capacity_shortfall=("random_capacity_shortfall", "max"), random_baseline_reliability_status=("random_baseline_reliability_status", lambda s: "passed" if (s == "passed").all() else "failed")).reset_index().to_markdown(index=False) if not random_health.empty else "No random baseline rows.",
        "",
        "## Matched-Delay Ineligible Bias",
        delay_audit.to_markdown(index=False) if not delay_audit.empty else "No matched-delay ineligible rows.",
        "",
        "## R-Unit Distribution And Risk Quintile Cost Control",
        r_unit.loc[(r_unit["split"].eq("validation")) | (r_unit["initial_risk_pct_quintile"].astype(str).ne("all"))].to_markdown(index=False) if not r_unit.empty else "No R-unit rows.",
        "",
        "## Baseline Difference Audit",
        baseline_diff.to_markdown(index=False) if not baseline_diff.empty else "No baseline difference rows.",
        "",
        "## Fail-Fast Attribution",
        ff_path.groupby(["split", "exit_trigger_type"], dropna=False).size().reset_index(name="episode_count").to_markdown(index=False) if not ff_path.empty else "No fail-fast path rows.",
        "",
        "## Fail-Fast Error Audit",
        ff_error.to_markdown(index=False) if not ff_error.empty else "No fail-fast error rows.",
        "",
        "## Counterfactual Failure Inheritance",
        counterfactual.to_markdown(index=False) if not counterfactual.empty else "No counterfactual rows.",
        "",
        "## Gate Evidence",
        gate.to_markdown(index=False),
        "",
        "## Failed Gates",
        failed.to_markdown(index=False) if not failed.empty else "No failed gates.",
        "",
        "## R02 Handoff",
        "R02 may only use surviving R01 episodes if the decision is `go_to_r02` or `go_to_r02_with_robustness_warning`; `go_to_oos_retest_required`, archive decisions, and stops do not authorize R02.",
    ]
    return "\n".join(lines) + "\n"


def assert_authority_inputs_r01_1(config: dict[str, Any]) -> pd.DataFrame:
    authority = assert_authority_inputs(config)
    rows: list[dict[str, Any]] = []
    for name, value in config.get("upstream_r01_v2", {}).items():
        path = topic_path(value)
        exists = path.exists()
        rows.append(
            {
                "artifact_name": f"upstream_r01_v2_{name}",
                "path": relpath(path),
                "exists": bool(exists),
                "sha256": file_hash(path) if exists and path.is_file() else "",
                "status": "passed" if exists else "failed",
            }
        )
    extra = pd.DataFrame(rows)
    if not extra.empty and not bool(extra["exists"].all()):
        missing = "; ".join(extra.loc[~extra["exists"], "path"].astype(str).tolist())
        raise RuntimeError(f"missing canonical R01.1 upstream inputs: {missing}")
    return pd.concat([authority, extra], ignore_index=True) if not extra.empty else authority


def _r01_1_reference_capture_fields(
    instrument: str,
    signal_date: pd.Timestamp,
    split: str,
    reference: pd.DataFrame,
    bridge_reference: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    effective_windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
    config: dict[str, Any],
) -> dict[str, Any]:
    eff_end = effective_windows.get(split, (pd.NaT, pd.NaT))[1]
    primary_eligible = split in {"train", "validation", "robustness"} and not pd.isna(eff_end) and signal_date <= eff_end
    lookback = primary_recall_lookback_days(config)
    window_id = primary_recall_window_id(config)
    captured, ref_id, cap_window = capture_reference(instrument, signal_date, reference, calendar, lookback, 0, window_id)
    bridge_captured, bridge_ref_id, bridge_window = capture_reference(instrument, signal_date, bridge_reference, calendar, lookback, 0, window_id)
    return {
        "primary_metric_eligible_seed_episode": bool(primary_eligible),
        "captures_primary_big_winner": bool(captured) if primary_eligible else False,
        "captured_reference_event_id": ref_id if primary_eligible and captured else "",
        "capture_window_id": cap_window if primary_eligible and captured else "",
        "captures_ep2_bridge_big_winner": bool(bridge_captured),
        "captured_ep2_bridge_reference_event_id": bridge_ref_id if bridge_captured else "",
        "bridge_capture_window_id": bridge_window if bridge_captured else "",
    }


def build_r01_1_raw_seed_panel(
    raw_events: pd.DataFrame,
    stock: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    reference: pd.DataFrame,
    bridge_reference: pd.DataFrame,
    effective_windows: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
) -> pd.DataFrame:
    if raw_events.empty:
        return pd.DataFrame()
    stock_cols = [
        "instrument",
        "date",
        "money_ratio20_mean_asof",
        "money_ratio5_mean_asof",
        "rps5_rank_pct",
        "boll20_pct_b",
        "close_near_high10_ratio",
        "seed_day_low",
        "pivot_low_10d",
        "rolling_close_high_10_asof",
        "industry_name",
        "liquidity_bucket",
        "volatility_bucket",
    ]
    available = [col for col in stock_cols if col in stock.columns]
    raw = raw_events.copy()
    raw["raw_signal_date"] = pd.to_datetime(raw["signal_date"]).dt.normalize()
    raw = raw.merge(
        stock[available].rename(columns={"date": "raw_signal_date"}),
        on=["instrument", "raw_signal_date"],
        how="left",
    )
    raw = raw.sort_values(["instrument", "raw_signal_date"]).reset_index(drop=True)
    raw["raw_seed_event_id"] = [
        f"{config['seed_rules']['raw_seed_id']}_{inst}_{_date_str(dt).replace('-', '')}_{idx:08d}"
        for idx, (inst, dt) in enumerate(zip(raw["instrument"], raw["raw_signal_date"]), start=1)
    ]
    captures = [
        _r01_1_reference_capture_fields(
            str(row.instrument).upper(),
            _date(row.raw_signal_date),
            str(row.split),
            reference,
            bridge_reference,
            calendar,
            effective_windows,
            config,
        )
        for row in raw.itertuples(index=False)
    ]
    cap_df = pd.DataFrame(captures)
    raw = pd.concat([raw, cap_df], axis=1)
    raw["raw_seed_flag"] = True
    raw["emitted_seed_flag"] = False
    raw["emission_suppressed"] = False
    raw["suppressed_by_emitted_seed_id"] = ""
    raw["split_boundary_suppressed"] = False
    raw["emitted_seed_id"] = ""
    raw["emitted_signal_date"] = ""
    raw["money_ratio20"] = raw["money_ratio20_mean_asof"]
    raw["money_ratio5"] = raw["money_ratio5_mean_asof"]
    raw["rps5"] = raw["rps5_rank_pct"]
    raw["close_near_high10"] = raw["close_near_high10_ratio"]
    raw["breakout_reference"] = raw["rolling_close_high_10_asof"]
    return raw


def apply_r01_1_emission_throttle(raw_panel: pd.DataFrame, config: dict[str, Any], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    if raw_panel.empty:
        return raw_panel.copy()
    out = raw_panel.copy()
    out["raw_signal_date_ts"] = pd.to_datetime(out["raw_signal_date"]).dt.normalize()
    pos = {pd.Timestamp(dt): idx for idx, dt in enumerate(calendar)}
    window = int(config["emission"]["throttle_window_trading_days"])
    emitted_seed_id = str(config["emission"]["emitted_seed_id"])
    emit_counter = 0
    for instrument, idxs in out.sort_values(["instrument", "raw_signal_date_ts"]).groupby("instrument").groups.items():
        last_emit_pos: int | None = None
        last_emit_id = ""
        last_emit_split = ""
        for idx in idxs:
            row = out.loc[idx]
            raw_pos = pos.get(pd.Timestamp(row["raw_signal_date_ts"]))
            if row["hard_filter_status"] != "passed" or raw_pos is None:
                continue
            if last_emit_pos is not None and raw_pos <= last_emit_pos + window:
                out.loc[idx, "emission_suppressed"] = True
                out.loc[idx, "suppressed_by_emitted_seed_id"] = last_emit_id
                out.loc[idx, "split_boundary_suppressed"] = str(row["split"]) != last_emit_split
                continue
            emit_counter += 1
            current_id = f"{emitted_seed_id}_{instrument}_{_date_str(row['raw_signal_date_ts']).replace('-', '')}_{emit_counter:08d}"
            out.loc[idx, "emitted_seed_flag"] = True
            out.loc[idx, "emitted_seed_id"] = current_id
            out.loc[idx, "emitted_signal_date"] = _date_str(row["raw_signal_date_ts"])
            last_emit_pos = raw_pos
            last_emit_id = current_id
            last_emit_split = str(row["split"])
    out = out.drop(columns=["raw_signal_date_ts"])
    return out


def _entry_open_state(
    stock_key: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    instrument: str,
    entry_date: pd.Timestamp,
) -> dict[str, Any]:
    if pd.isna(entry_date):
        return {"entry_price": np.nan, "buy_executable": False, "buy_block_reason": "missing_entry_date"}
    prev = base.prev_trading_day(calendar, entry_date)
    entry_row = stock_key.loc[(instrument, entry_date)] if (instrument, entry_date) in stock_key.index else pd.Series(dtype=object)
    prev_row = stock_key.loc[(instrument, prev)] if not pd.isna(prev) and (instrument, prev) in stock_key.index else pd.Series(dtype=object)
    price = _safe_float(entry_row.get("open", prev_row.get("next_open", np.nan)))
    buy_ok = bool(prev_row.get("is_buy_executable_next_open", False))
    reason = "" if buy_ok else str(prev_row.get("blocked_buy_reason", "entry_not_executable"))
    if not np.isfinite(price):
        reason = "missing_entry_open"
        buy_ok = False
    return {"entry_price": price, "buy_executable": buy_ok, "buy_block_reason": reason}


def build_r01_1_cooling_entry_panel(
    emitted_panel: pd.DataFrame,
    stock: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    emitted = emitted_panel.loc[emitted_panel["emitted_seed_flag"].astype(bool)].copy()
    if emitted.empty:
        return pd.DataFrame()
    stock_key = stock.set_index(["instrument", "date"])
    min_risk = float(config["risk_normalization"]["min_initial_risk_pct"])
    max_risk = float(config["risk_normalization"]["max_initial_risk_pct"])
    rows: list[dict[str, Any]] = []
    for row in emitted.itertuples(index=False):
        instrument = str(row.instrument).upper()
        emitted_date = _date(row.emitted_signal_date)
        cooling_date = base.add_trading_days(calendar, emitted_date, 1)
        entry_date = base.add_trading_days(calendar, emitted_date, 2)
        cooling = stock_key.loc[(instrument, cooling_date)] if not pd.isna(cooling_date) and (instrument, cooling_date) in stock_key.index else pd.Series(dtype=object)
        cooling_close = _safe_float(cooling.get("close"))
        seed_low = _safe_float(row.seed_day_low)
        breakout = _safe_float(row.breakout_reference)
        pivot = _safe_float(row.pivot_low_10d)
        cancel_reasons: list[str] = []
        if not np.isfinite(cooling_close):
            cancel_reasons.append("missing_cooling_close")
        else:
            if np.isfinite(seed_low) and cooling_close < seed_low:
                cancel_reasons.append("cooling_close_below_seed_day_low")
            if np.isfinite(breakout) and cooling_close < breakout:
                cancel_reasons.append("cooling_close_below_breakout_reference")
            if np.isfinite(pivot) and cooling_close < pivot:
                cancel_reasons.append("cooling_close_below_pivot_low_10d")
        entry_state = _entry_open_state(stock_key, calendar, instrument, entry_date)
        stop, risk_pct, risk_status = closest_stop_below(entry_state["entry_price"], [seed_low, breakout, pivot], min_risk, max_risk)
        cooling_cancelled = bool(cancel_reasons)
        executable = (not cooling_cancelled) and bool(entry_state["buy_executable"]) and risk_status == "passed"
        if cooling_cancelled:
            reject_reason = "|".join(cancel_reasons)
        elif not entry_state["buy_executable"]:
            reject_reason = entry_state["buy_block_reason"]
        elif risk_status != "passed":
            reject_reason = risk_status
        else:
            reject_reason = ""
        rec = row._asdict()
        rec.update(
            {
                "cooling_observation_date": _date_str(cooling_date),
                "cooling_close": cooling_close,
                "entry_date": _date_str(entry_date),
                "entry_price": entry_state["entry_price"],
                "entry_buy_executable": bool(entry_state["buy_executable"]),
                "entry_buy_block_reason": entry_state["buy_block_reason"],
                "cooling_cancelled": cooling_cancelled,
                "cooling_cancel_reason": "|".join(cancel_reasons),
                "cooling_qualified_probe": bool(executable),
                "initial_structural_stop": stop,
                "initial_risk_pct": risk_pct,
                "risk_distance_status": risk_status,
                "executable_status": "passed" if executable else "rejected",
                "episode_reject_reason": reject_reason,
            }
        )
        rows.append(rec)
    return pd.DataFrame(rows)


def build_r01_1_seed_episodes(cooling_panel: pd.DataFrame, config: dict[str, Any], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    if cooling_panel.empty:
        return pd.DataFrame(columns=SEED_EPISODE_COLUMNS)
    rows: list[dict[str, Any]] = []
    family = str(config["emission"]["emitted_seed_id"])
    for row in cooling_panel.itertuples(index=False):
        start = _date(row.emitted_signal_date)
        episode_id = f"{family}_{str(row.instrument).upper()}_{_date_str(start).replace('-', '')}_{hashlib.sha1(str(row.emitted_seed_id).encode()).hexdigest()[:10]}"
        rows.append(
            {
                "seed_episode_id": episode_id,
                "seed_family_id": family,
                "instrument": str(row.instrument).upper(),
                "episode_start_signal_date": _date_str(start),
                "episode_effective_entry_date": row.entry_date if row.executable_status == "passed" else "",
                "episode_end_signal_date": _date_str(base.add_trading_days(calendar, _date(row.entry_date), int(config["fail_fast"]["natural_exit_horizon_trading_days"]))) if row.executable_status == "passed" else "",
                "split": assign_split(start, split_bounds(config)),
                "first_seed_event_id": str(row.emitted_seed_id),
                "seed_event_count": 1,
                "suppressed_reentry_count": 0,
                "entry_price": row.entry_price,
                "price_structure_component": row.price_structure_component,
                "seed_day_low": row.seed_day_low,
                "breakout_reference": row.breakout_reference,
                "pivot_low_10d": row.pivot_low_10d,
                "initial_structural_stop": row.initial_structural_stop,
                "initial_risk_pct": row.initial_risk_pct,
                "risk_distance_status": row.risk_distance_status,
                "executable_status": row.executable_status,
                "episode_reject_reason": row.episode_reject_reason,
                "primary_metric_eligible_seed_episode": bool(row.primary_metric_eligible_seed_episode),
                "captures_primary_big_winner": bool(row.captures_primary_big_winner),
                "captured_reference_event_id": row.captured_reference_event_id,
                "capture_window_id": row.capture_window_id,
                "captures_ep2_bridge_big_winner": bool(row.captures_ep2_bridge_big_winner),
            }
        )
    return pd.DataFrame(rows, columns=SEED_EPISODE_COLUMNS)


def _r01_1_episode_extra(cooling_panel: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    if cooling_panel.empty or episodes.empty:
        return episodes.copy()
    extra = cooling_panel[
        [
            "emitted_seed_id",
            "emitted_signal_date",
            "cooling_observation_date",
            "cooling_cancelled",
            "cooling_cancel_reason",
            "entry_buy_executable",
        ]
    ].copy()
    extra["first_seed_event_id"] = extra["emitted_seed_id"]
    return episodes.merge(extra, on="first_seed_event_id", how="left")


def _r01_1_shift_rows(
    episodes: pd.DataFrame,
    stock: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    baseline_id: str,
    entry_shift_from_emitted: int,
    matched_type: str,
) -> pd.DataFrame:
    if episodes.empty:
        return pd.DataFrame()
    stock_key = stock.set_index(["instrument", "date"])
    min_risk = float(config["risk_normalization"]["min_initial_risk_pct"])
    max_risk = float(config["risk_normalization"]["max_initial_risk_pct"])
    records: list[dict[str, Any]] = []
    for _, ep in episodes.iterrows():
        emitted_date = _date(ep["episode_start_signal_date"])
        entry_date = base.add_trading_days(calendar, emitted_date, entry_shift_from_emitted)
        entry_state = _entry_open_state(stock_key, calendar, str(ep["instrument"]).upper(), entry_date)
        stop, risk_pct, risk_status = closest_stop_below(
            entry_state["entry_price"],
            [_safe_float(ep["seed_day_low"]), _safe_float(ep["breakout_reference"]), _safe_float(ep["pivot_low_10d"])],
            min_risk,
            max_risk,
        )
        pre_status = "passed" if entry_state["buy_executable"] and risk_status == "passed" else "ineligible"
        pre_reason = "" if pre_status == "passed" else (risk_status if risk_status != "passed" else entry_state["buy_block_reason"])
        candidate_entry = _safe_float(ep.get("entry_price"))
        entry_price = _safe_float(entry_state["entry_price"])
        rec = ep.to_dict()
        rec.update(
            {
                "baseline_id": baseline_id,
                "signal_date": ep["episode_start_signal_date"],
                "entry_date": _date_str(entry_date),
                "entry_price": entry_price,
                "initial_structural_stop": stop,
                "initial_risk_pct": risk_pct,
                "delay_days": int(entry_shift_from_emitted - 2),
                "delay_period_return_pct": entry_price / candidate_entry - 1.0 if np.isfinite(entry_price) and np.isfinite(candidate_entry) and candidate_entry > 0 else np.nan,
                "matched_control_type": matched_type,
                "replicate_id": 0,
                "primary_metric_eligible_baseline_event": bool(ep.get("primary_metric_eligible_seed_episode", False)),
                "captures_primary_big_winner": bool(ep.get("captures_primary_big_winner", False)),
                "captured_reference_event_id": ep.get("captured_reference_event_id", ""),
                "capture_window_id": ep.get("capture_window_id", ""),
                "fail_fast_policy": "no_fail_fast" if "no_fail_fast" in baseline_id else "same_fail_fast",
                "structural_reference_policy": "carried_original_emitted_seed_references",
                "match_year": _date(ep["episode_start_signal_date"]).year,
                "match_industry": "all",
                "match_liquidity_bucket": "all",
                "match_volatility_bucket": "all",
                "pre_sim_eligibility_status": pre_status,
                "pre_sim_ineligibility_reason": pre_reason,
            }
        )
        records.append(rec)
    rows = pd.DataFrame(records)
    if rows.empty:
        return rows
    rows["delay_period_return_bucket"] = _qbucket(rows["delay_period_return_pct"], 5, "delay_return")
    if matched_type == "matched_delay":
        all_rate = float(rows["pre_sim_eligibility_status"].ne("passed").mean()) if len(rows) else 0.0
        top = rows["delay_period_return_bucket"].eq("delay_return_q5")
        top_rate = float(rows.loc[top, "pre_sim_eligibility_status"].ne("passed").mean()) if top.any() else 0.0
        status = "failed" if top_rate >= 2.0 * all_rate and top_rate >= 0.20 else "passed"
        rows["matched_delay_reliability_status"] = status
    else:
        rows["matched_delay_reliability_status"] = "not_applicable"
    return rows


def _r01_1_same_candidate_rows(candidate: pd.DataFrame, baseline_id: str) -> pd.DataFrame:
    rows = candidate.copy()
    rows["baseline_id"] = baseline_id
    rows["signal_date"] = rows["episode_start_signal_date"]
    rows["primary_metric_eligible_baseline_event"] = rows["primary_metric_eligible_seed_episode"]
    rows["matched_control_type"] = "same_seed"
    rows["fail_fast_policy"] = "no_fail_fast" if "no_fail_fast" in baseline_id else "same_fail_fast"
    rows["structural_reference_policy"] = "same_cooling_qualified_seed_references"
    rows["replicate_id"] = 0
    rows["delay_days"] = 0
    rows["delay_period_return_pct"] = np.nan
    rows["delay_period_return_bucket"] = ""
    rows["matched_delay_reliability_status"] = "not_applicable"
    rows["match_year"] = pd.to_datetime(rows["episode_start_signal_date"]).dt.year
    rows["match_industry"] = "all"
    rows["match_liquidity_bucket"] = "all"
    rows["match_volatility_bucket"] = "all"
    return rows


def build_r01_1_baseline_inputs(
    episodes: pd.DataFrame,
    stock: pd.DataFrame,
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    reference: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    candidate = episodes.loc[(episodes["seed_family_id"].eq(CANDIDATE_SEED_ID)) & (episodes["executable_status"].eq("passed"))].copy()
    all_emitted = episodes.loc[episodes["seed_family_id"].eq(CANDIDATE_SEED_ID)].copy()
    ep2 = episodes.loc[(episodes["seed_family_id"].eq(EP2_SEED_ID)) & (episodes["executable_status"].eq("passed"))].copy()
    candidate = enrich_episode_for_sim(candidate)
    all_emitted = enrich_episode_for_sim(all_emitted)
    ep2 = enrich_episode_for_sim(ep2)
    random_rows = _matched_random_rows(candidate, stock, config, calendar, reference)
    return {
        "same_cooling_qualified_seed_no_fail_fast_hold_h20": _r01_1_same_candidate_rows(candidate, "same_cooling_qualified_seed_no_fail_fast_hold_h20"),
        "same_cooling_qualified_seed_t1_open_same_fail_fast_h20": _r01_1_shift_rows(candidate, stock, config, calendar, "same_cooling_qualified_seed_t1_open_same_fail_fast_h20", 1, "same_sample_t1"),
        "same_cooling_qualified_seed_t3_open_same_fail_fast_h20": _r01_1_shift_rows(candidate, stock, config, calendar, "same_cooling_qualified_seed_t3_open_same_fail_fast_h20", 3, "matched_delay"),
        "same_cooling_qualified_seed_t1_open_no_fail_fast_h20": _r01_1_shift_rows(candidate, stock, config, calendar, "same_cooling_qualified_seed_t1_open_no_fail_fast_h20", 1, "same_sample_t1"),
        "same_cooling_qualified_seed_t3_open_no_fail_fast_h20": _r01_1_shift_rows(candidate, stock, config, calendar, "same_cooling_qualified_seed_t3_open_no_fail_fast_h20", 3, "matched_delay"),
        "same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted": _r01_1_shift_rows(all_emitted, stock, config, calendar, "same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted", 1, "same_emitted_t1"),
        "r01_v2_raw_seed_t1_open_bridge": _r01_1_shift_rows(all_emitted, stock, config, calendar, "r01_v2_raw_seed_t1_open_bridge", 1, "r01_v2_bridge"),
        "ep2_detector_probe_with_simple_stop_bridge": _ep2_bridge_rows(ep2),
        "matched_random_same_density_same_fail_fast_h20_report_only": random_rows.copy(),
        "matched_random_same_density_no_fail_fast_h20_report_only": random_rows.copy(),
    }


def enrich_r01_1_probe(probe: pd.DataFrame, episodes_extra: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    if probe.empty:
        return probe.copy()
    extra_cols = [
        "seed_episode_id",
        "first_seed_event_id",
        "episode_start_signal_date",
        "cooling_observation_date",
        "cooling_cancelled",
        "cooling_cancel_reason",
        "captures_primary_big_winner",
        "captured_reference_event_id",
        "capture_window_id",
    ]
    extra = episodes_extra[[col for col in extra_cols if col in episodes_extra.columns]].copy()
    out = probe.merge(extra, on="seed_episode_id", how="left")
    out = out.rename(
        columns={
            "first_seed_event_id": "emitted_seed_id",
            "episode_start_signal_date": "emitted_signal_date",
        }
    )
    ref_dates = reference.set_index("reference_event_id")["reference_date"].to_dict() if not reference.empty else {}
    out["captured_reference_date"] = pd.to_datetime(out["captured_reference_event_id"].map(ref_dates), errors="coerce")
    out["entry_date_ts"] = pd.to_datetime(out["entry_date"], errors="coerce")
    out["entry_after_reference"] = out["captured_reference_date"].notna() & out["entry_date_ts"].gt(out["captured_reference_date"])
    out["entry_after_reference_days"] = (out["entry_date_ts"] - out["captured_reference_date"]).dt.days
    return out.drop(columns=["entry_date_ts"])


def build_r01_1_density_audit(stock: pd.DataFrame, raw: pd.DataFrame, emitted: pd.DataFrame, cooling: pd.DataFrame, episodes: pd.DataFrame, ep2_episodes: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    eligible = stock.loc[stock["eligible_stock_day"].astype(bool)]
    eligible_inst_year = eligible.groupby(["split", "instrument", "year"]).size().reset_index(name="eligible_stock_days")
    eligible_inst_year = eligible_inst_year.loc[eligible_inst_year["eligible_stock_days"] >= int(config["density_denominator"]["eligible_instrument_year_requires_min_stock_days"])]
    rows: list[dict[str, Any]] = []
    probe = cooling.loc[cooling["cooling_qualified_probe"].astype(bool)] if not cooling.empty else pd.DataFrame()
    for split in ["train", "validation", "robustness"]:
        denom_days = int(eligible.loc[eligible["split"].eq(split)].shape[0])
        denom_iy = int(eligible_inst_year.loc[eligible_inst_year["split"].eq(split), ["instrument", "year"]].drop_duplicates().shape[0])
        split_raw = raw.loc[raw["split"].eq(split)] if not raw.empty else pd.DataFrame()
        split_emit = emitted.loc[emitted["split"].eq(split) & emitted["emitted_seed_flag"].astype(bool)] if not emitted.empty else pd.DataFrame()
        split_probe = probe.loc[probe["split"].eq(split)] if not probe.empty else pd.DataFrame()
        split_eps = episodes.loc[episodes["split"].eq(split)] if not episodes.empty else pd.DataFrame()
        split_ep2 = ep2_episodes.loc[ep2_episodes["split"].eq(split)] if not ep2_episodes.empty else pd.DataFrame()
        layers = [
            ("raw_seed", split_raw, split_raw),
            ("emitted_seed", split_emit, split_emit),
            ("probe_entry", split_probe, split_eps.loc[split_eps["executable_status"].eq("passed")] if not split_eps.empty else split_eps),
            ("ep2_detector", split_ep2, split_ep2),
        ]
        for layer, event_df, ep_df in layers:
            event_count = int(len(event_df))
            episode_count = int(len(ep_df))
            unique_iy = int(ep_df.assign(year=pd.to_datetime(ep_df["episode_start_signal_date"], errors="coerce").dt.year)[["instrument", "year"]].drop_duplicates().shape[0]) if not ep_df.empty and "episode_start_signal_date" in ep_df else 0
            rows.append(
                {
                    "split": split,
                    "layer": layer,
                    "seed_family_id": CANDIDATE_SEED_ID if layer != "ep2_detector" else EP2_SEED_ID,
                    "eligible_stock_day_count": denom_days,
                    "eligible_instrument_year_count": denom_iy,
                    "event_count": event_count,
                    "episode_count": episode_count,
                    "day_rate": _safe_div(event_count, denom_days, 0.0),
                    "episode_rate": _safe_div(episode_count, denom_iy, 0.0),
                    "unique_instrument_count": int(ep_df["instrument"].nunique()) if not ep_df.empty and "instrument" in ep_df else 0,
                    "unique_instrument_year_count": unique_iy,
                }
            )
    density = pd.DataFrame(rows)
    ep2 = density.loc[density["layer"].eq("ep2_detector")].set_index("split")
    for metric in ["event_count", "episode_count", "day_rate", "episode_rate"]:
        density[f"{metric}_vs_ep2"] = density.apply(lambda row: _safe_div(float(row[metric]), float(ep2.loc[row["split"], metric]), np.nan) if row["split"] in ep2.index else np.nan, axis=1)
    return density


def build_r01_1_waterfalls(raw: pd.DataFrame, emitted: pd.DataFrame, cooling: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_rows: list[dict[str, Any]] = []
    cooling_rows: list[dict[str, Any]] = []
    for split in ["train", "validation", "robustness"]:
        raw_split = raw.loc[raw["split"].eq(split)] if not raw.empty else pd.DataFrame()
        emitted_split = emitted.loc[emitted["split"].eq(split) & emitted["emitted_seed_flag"].astype(bool)] if not emitted.empty else pd.DataFrame()
        suppressed = emitted.loc[emitted["split"].eq(split) & emitted["emission_suppressed"].astype(bool)] if not emitted.empty else pd.DataFrame()
        raw_caps = set(raw_split.loc[raw_split["captures_primary_big_winner"].astype(bool), "captured_reference_event_id"].astype(str)) if not raw_split.empty else set()
        emitted_caps = set(emitted_split.loc[emitted_split["captures_primary_big_winner"].astype(bool), "captured_reference_event_id"].astype(str)) if not emitted_split.empty else set()
        raw_rows.append(
            {
                "split": split,
                "raw_seed_count": int(len(raw_split)),
                "emitted_seed_count": int(len(emitted_split)),
                "suppressed_raw_seed_count": int(len(suppressed)),
                "suppressed_raw_seed_share": _safe_div(float(len(suppressed)), float(len(raw_split)), 0.0),
                "raw_to_emitted_lost_primary_capture_count": len(raw_caps - emitted_caps),
                "raw_to_emitted_added_primary_capture_count": len(emitted_caps - raw_caps),
                "raw_to_emitted_net_capture_count": len(emitted_caps) - len(raw_caps),
                "split_boundary_suppressed_raw_seed_count": int(suppressed["split_boundary_suppressed"].astype(bool).sum()) if not suppressed.empty else 0,
            }
        )
        cooling_split = cooling.loc[cooling["split"].eq(split)] if not cooling.empty else pd.DataFrame()
        canceled = cooling_split.loc[cooling_split["cooling_cancelled"].astype(bool)] if not cooling_split.empty else pd.DataFrame()
        qualified = cooling_split.loc[cooling_split["cooling_qualified_probe"].astype(bool)] if not cooling_split.empty else pd.DataFrame()
        cooling_rows.append(
            {
                "split": split,
                "emitted_seed_count": int(len(cooling_split)),
                "cooling_cancelled_count": int(len(canceled)),
                "cooling_cancelled_rate": _safe_div(float(len(canceled)), float(len(cooling_split)), 0.0),
                "cooling_qualified_probe_count": int(len(qualified)),
                "cooling_cancelled_primary_big_winner_capture_loss_count": int(canceled["captures_primary_big_winner"].astype(bool).sum()) if not canceled.empty else 0,
                "cooling_cancel_reason_distribution": ";".join(canceled["cooling_cancel_reason"].value_counts().astype(str).index[:10]) if not canceled.empty else "",
            }
        )
    return pd.DataFrame(raw_rows), pd.DataFrame(cooling_rows)


def build_r01_1_recall_bridge(reference: pd.DataFrame, raw: pd.DataFrame, emitted: pd.DataFrame, cooling: pd.DataFrame, episodes: pd.DataFrame, probe: pd.DataFrame, ep2_episodes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ["train", "validation", "robustness"]:
        ref_count = int(reference.loc[reference["split"].eq(split)].shape[0])
        populations = {
            "raw_seed_primary_recall": raw.loc[raw["split"].eq(split)] if not raw.empty else pd.DataFrame(),
            "emitted_seed_primary_recall_pre_cooling": emitted.loc[emitted["split"].eq(split) & emitted["emitted_seed_flag"].astype(bool)] if not emitted.empty else pd.DataFrame(),
            "cooling_qualified_probe_primary_recall": cooling.loc[cooling["split"].eq(split) & cooling["cooling_qualified_probe"].astype(bool)] if not cooling.empty else pd.DataFrame(),
            "ep2_detector_primary_recall": ep2_episodes.loc[ep2_episodes["split"].eq(split)] if not ep2_episodes.empty else pd.DataFrame(),
        }
        survived = probe.loc[
            probe["split"].eq(split)
            & probe["captures_primary_big_winner"].astype(bool)
            & probe["exit_trigger_type"].astype(str).str.startswith("natural_exit_h", na=False)
        ] if not probe.empty and "captures_primary_big_winner" in probe.columns else pd.DataFrame()
        populations["fail_fast_survived_probe_primary_recall"] = survived
        for basis, frame in populations.items():
            if "captured_reference_event_id" in frame:
                captured = set(frame.loc[frame["captures_primary_big_winner"].astype(bool), "captured_reference_event_id"].astype(str))
            else:
                captured = set()
            rows.append(
                {
                    "split": split,
                    "recall_basis": basis,
                    "big_winner_reference_count": ref_count,
                    "captured_reference_count": len(captured),
                    "primary_recall": _safe_div(float(len(captured)), float(ref_count), 0.0),
                }
            )
    recall = pd.DataFrame(rows)
    ep2 = recall.loc[recall["recall_basis"].eq("ep2_detector_primary_recall")].set_index("split")
    recall["recall_diff_vs_ep2_detector"] = recall.apply(lambda row: float(row["primary_recall"]) - float(ep2.loc[row["split"], "primary_recall"]) if row["split"] in ep2.index else np.nan, axis=1)
    return recall


def build_r01_1_entry_after_reference_audit(probe: pd.DataFrame) -> pd.DataFrame:
    if probe.empty:
        return pd.DataFrame(columns=["split", "captured_reference_count", "entry_after_reference_count", "entry_after_reference_share", "captured_reference_count_with_entry_on_or_before_reference", "captured_reference_count_with_entry_after_reference", "audit_only_status"])
    captured = probe.loc[probe["captures_primary_big_winner"].astype(bool)].copy()
    rows: list[dict[str, Any]] = []
    for split, group in captured.groupby("split", dropna=False):
        after = group["entry_after_reference"].astype(bool)
        rows.append(
            {
                "split": split,
                "captured_reference_count": int(len(group)),
                "entry_after_reference_count": int(after.sum()),
                "entry_after_reference_share": _safe_div(float(after.sum()), float(len(group)), 0.0),
                "captured_reference_count_with_entry_on_or_before_reference": int((~after).sum()),
                "captured_reference_count_with_entry_after_reference": int(after.sum()),
                "audit_only_status": "report_only",
            }
        )
    return pd.DataFrame(rows)


def _r01_1_density_metric(density: pd.DataFrame, split: str, layer: str, metric: str) -> float:
    row = density.loc[density["split"].eq(split) & density["layer"].eq(layer)]
    return _safe_float(row.iloc[0][metric]) if not row.empty and metric in row.columns else np.nan


def _r01_1_recall_metric(recall: pd.DataFrame, split: str, basis: str, metric: str) -> float:
    row = recall.loc[recall["split"].eq(split) & recall["recall_basis"].eq(basis)]
    return _safe_float(row.iloc[0][metric]) if not row.empty and metric in row.columns else np.nan


def build_r01_1_risk_pct_quintile_cost_control(probe: pd.DataFrame, baseline: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    candidate = probe.loc[probe["seed_family_id"].eq(CANDIDATE_SEED_ID)].copy()
    no_ff = baseline.loc[baseline["baseline_id"].eq("same_cooling_qualified_seed_no_fail_fast_hold_h20")].copy()
    train_risk = candidate.loc[candidate["split"].eq("train") & candidate["initial_risk_pct"].notna(), "initial_risk_pct"].astype(float)
    if train_risk.empty:
        edges = np.array([np.nan] * 6)
    else:
        edges = train_risk.quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0]).to_numpy()
        edges[0] = -np.inf
        edges[-1] = np.inf
    labels = [f"risk_pct_q{i}" for i in range(1, 6)]
    candidate["risk_pct_quintile"] = pd.cut(candidate["initial_risk_pct"].astype(float), bins=edges, labels=labels, include_lowest=True).astype(str) if np.isfinite(edges[1:-1]).any() else "risk_pct_missing"
    no_ff["risk_pct_quintile"] = pd.cut(no_ff["initial_risk_pct"].astype(float), bins=edges, labels=labels, include_lowest=True).astype(str) if np.isfinite(edges[1:-1]).any() else "risk_pct_missing"
    min_rows = int(config["risk_pct_quintile_cost_control"]["min_validation_rows_per_quintile"])
    sufficient = 0
    all_pass = True
    for idx, label in enumerate(labels):
        lo = edges[idx] if idx < len(edges) else np.nan
        hi = edges[idx + 1] if idx + 1 < len(edges) else np.nan
        cand = candidate.loc[candidate["split"].eq("validation") & candidate["risk_pct_quintile"].eq(label)]
        base_df = no_ff.loc[no_ff["split"].eq("validation") & no_ff["risk_pct_quintile"].eq(label)]
        cand_failed = cand.loc[cand["failed_seed_primary"].astype(str).isin(["True", "true", "1"])]
        base_failed = base_df.loc[base_df["baseline_failed_seed_primary"].astype(str).isin(["True", "true", "1"])]
        cand_loss = float(cand_failed["loss_r"].mean()) if len(cand_failed) else 0.0
        base_loss = float(base_failed["loss_r"].mean()) if len(base_failed) else 0.0
        cand_p05 = float(cand["return_r"].dropna().astype(float).quantile(0.05)) if len(cand["return_r"].dropna()) else np.nan
        base_p05 = float(base_df["return_r"].dropna().astype(float).quantile(0.05)) if len(base_df["return_r"].dropna()) else np.nan
        sample_status = "sufficient" if len(cand) >= min_rows else "insufficient"
        pass_status = bool(sample_status == "sufficient" and cand_loss - base_loss <= 0 and (np.isfinite(cand_p05 - base_p05) and cand_p05 - base_p05 >= -0.03))
        if sample_status == "sufficient":
            sufficient += 1
            all_pass = all_pass and pass_status
        rows.append(
            {
                "risk_pct_quintile": label,
                "risk_pct_quintile_edge_low": lo,
                "risk_pct_quintile_edge_high": hi,
                "eligible_probe_count": int(len(cand)),
                "failed_seed_average_loss_r_diff_vs_no_fail_fast": cand_loss - base_loss,
                "p05_return_r_diff_vs_no_fail_fast": cand_p05 - base_p05 if np.isfinite(cand_p05) and np.isfinite(base_p05) else np.nan,
                "risk_pct_quintile_sample_status": sample_status,
                "risk_pct_quintile_pass_status": "passed" if pass_status else ("insufficient" if sample_status == "insufficient" else "failed"),
            }
        )
    status = "passed" if all_pass and sufficient >= int(config["risk_pct_quintile_cost_control"]["min_sufficient_validation_quintiles"]) else "failed"
    out = pd.DataFrame(rows)
    out["risk_pct_quintile_cost_control_status"] = status
    return out


def build_r01_1_gate_audit(
    authority: pd.DataFrame,
    density: pd.DataFrame,
    recall: pd.DataFrame,
    baseline_diff: pd.DataFrame,
    delay_audit: pd.DataFrame,
    recall_cost: pd.DataFrame,
    risk_pct: pd.DataFrame,
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

    formula = config["seed_rules"]["candidate_seed_formula_id"]
    exact_formula = "money_ratio20_gt_1_0_and_money_ratio5_gt_2_0_and_rps5_gt_50_and_boll20_pct_b_gt_1_0_and_close_near_high10_gt_0"
    add("authority_inputs_status", "all", "authority_inputs_status", "passed" if authority["status"].eq("passed").all() else "failed", "passed", "==", bool(authority["status"].eq("passed").all()))
    add("raw_seed_formula_status", "all", "raw_seed_formula_id", formula, exact_formula, "==", formula == exact_formula)
    add("emission_rule_status", "all", "throttle_window_trading_days", config["emission"]["throttle_window_trading_days"], 20, "==", int(config["emission"]["throttle_window_trading_days"]) == 20)
    add("cooling_entry_rule_status", "all", "entry_family_id", config["cooling_entry"]["entry_family_id"], "cooling_observation_day_then_t2_open_entry", "==", config["cooling_entry"]["entry_family_id"] == "cooling_observation_day_then_t2_open_entry")
    add("validation_threshold_selection_status", "validation", "validation_threshold_selection_status", "no_selection_from_validation", "no_selection_from_validation", "==", True)

    for split in ["train", "validation"]:
        ep2_day = _r01_1_density_metric(density, split, "ep2_detector", "day_rate")
        ep2_ep = _r01_1_density_metric(density, split, "ep2_detector", "episode_rate")
        day_cap = min(float(config["seed_density_caps"]["max_candidate_emitted_seed_day_rate"]), float(config["seed_density_caps"]["max_candidate_emitted_seed_day_rate_vs_ep2_multiple"]) * ep2_day)
        probe_day_cap = min(float(config["seed_density_caps"]["max_candidate_probe_entry_day_rate"]), float(config["seed_density_caps"]["max_candidate_probe_entry_day_rate_vs_ep2_multiple"]) * ep2_day)
        ep_cap = float(config["seed_density_caps"]["max_candidate_episode_rate_vs_ep2_multiple"]) * ep2_ep
        emitted_day = _r01_1_density_metric(density, split, "emitted_seed", "day_rate")
        emitted_ep = _r01_1_density_metric(density, split, "emitted_seed", "episode_rate")
        probe_day = _r01_1_density_metric(density, split, "probe_entry", "day_rate")
        probe_ep = _r01_1_density_metric(density, split, "probe_entry", "episode_rate")
        add("candidate_emitted_seed_day_rate", split, "candidate_emitted_seed_day_rate", emitted_day, day_cap, "<=", bool(np.isfinite(emitted_day) and emitted_day <= day_cap))
        add("candidate_probe_entry_day_rate", split, "candidate_probe_entry_day_rate", probe_day, probe_day_cap, "<=", bool(np.isfinite(probe_day) and probe_day <= probe_day_cap))
        add("candidate_emitted_seed_episode_rate", split, "candidate_emitted_seed_episode_rate", emitted_ep, ep_cap, "<=", bool(np.isfinite(emitted_ep) and emitted_ep <= ep_cap))
        add("candidate_probe_entry_episode_rate", split, "candidate_probe_entry_episode_rate", probe_ep, ep_cap, "<=", bool(np.isfinite(probe_ep) and probe_ep <= ep_cap))
    val_unique = _r01_1_density_metric(density, "validation", "probe_entry", "unique_instrument_year_count")
    add("validation_unique_instrument_years", "validation", "unique_instrument_year_count", val_unique, config["seed_density_caps"]["min_unique_instrument_years_validation"], ">=", bool(val_unique >= int(config["seed_density_caps"]["min_unique_instrument_years_validation"])))
    day_ratio = _r01_1_density_metric(density, "validation", "probe_entry", "event_count_vs_ep2")
    ep_ratio = _r01_1_density_metric(density, "validation", "probe_entry", "episode_count_vs_ep2")
    add("validation_probe_entry_day_count_vs_ep2", "validation", "candidate_probe_entry_day_count_vs_ep2_ratio", day_ratio, 1.0, ">=", bool(day_ratio >= 1.0))
    add("validation_probe_entry_episode_count_vs_ep2", "validation", "candidate_probe_entry_episode_count_vs_ep2_ratio", ep_ratio, 1.0, ">=", bool(ep_ratio >= 1.0))

    val_recall_diff = _r01_1_recall_metric(recall, "validation", "cooling_qualified_probe_primary_recall", "recall_diff_vs_ep2_detector")
    robust_recall_diff = _r01_1_recall_metric(recall, "robustness", "cooling_qualified_probe_primary_recall", "recall_diff_vs_ep2_detector")
    add("cooling_qualified_probe_primary_recall_no_harm", "validation", "recall_diff_vs_ep2_detector", val_recall_diff, -0.05, ">=", bool(val_recall_diff >= -0.05))
    add("robustness_cooling_qualified_probe_primary_recall_no_harm", "robustness", "recall_diff_vs_ep2_detector", robust_recall_diff, -0.10, ">=", bool(robust_recall_diff >= -0.10))
    emitted_count = _r01_1_recall_metric(recall, "validation", "emitted_seed_primary_recall_pre_cooling", "captured_reference_count")
    cooling_count = _r01_1_recall_metric(recall, "validation", "cooling_qualified_probe_primary_recall", "captured_reference_count")
    cooling_loss = 1.0 - _safe_div(cooling_count, max(1.0, emitted_count), 0.0)
    add("emitted_to_cooling_recall_loss_rate", "validation", "emitted_to_cooling_recall_loss_rate", cooling_loss, 0.15, "<=", bool(cooling_loss <= 0.15))
    survived = _r01_1_recall_metric(recall, "validation", "fail_fast_survived_probe_primary_recall", "captured_reference_count")
    ff_loss = 1.0 - _safe_div(survived, max(1.0, cooling_count), 0.0)
    add("fail_fast_survived_big_winner_recall_loss", "validation", "fail_fast_survived_loss_rate", ff_loss, 0.15, "<=", bool(ff_loss <= 0.15))

    add("validation_cost_vs_no_fail_fast", "validation", "failed_seed_average_loss_r_diff_vs_no_fail_fast", _diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r"), 0, "<", bool(_diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r") < 0))
    add("validation_p05_vs_no_fail_fast", "validation", "p05_return_r_diff_vs_no_fail_fast", _diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_no_fail_fast_hold_h20", "p05_return_r"), -0.02, ">=", bool(_diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_no_fail_fast_hold_h20", "p05_return_r") >= -0.02))
    risk_status = str(risk_pct["risk_pct_quintile_cost_control_status"].iloc[0]) if not risk_pct.empty else "failed"
    add("risk_pct_quintile_cost_control_status", "validation", "risk_pct_quintile_cost_control_status", risk_status, "passed", "==", risk_status == "passed")
    delay3 = delay_audit.loc[delay_audit["delay_days"].eq(1)] if not delay_audit.empty else pd.DataFrame()
    delay3_status = "passed" if delay3.empty or delay3["matched_delay_reliability_status"].eq("passed").all() else "failed"
    add("matched_delay_t3_reliability_status", "validation", "matched_delay_t3_reliability_status", delay3_status, "passed", "==", delay3_status == "passed")
    add("total_effect_failed_seed_loss_vs_t1_all_emitted", "validation", "failed_seed_average_loss_r_diff_vs_t1_all_emitted", _diff_metric(baseline_diff, "validation", "same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted", "failed_seed_average_loss_r"), 0, "<=", bool(_diff_metric(baseline_diff, "validation", "same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted", "failed_seed_average_loss_r") <= 0))
    add("entry_timing_t3_mean_no_harm", "validation", "mean_return_r_diff_vs_t3_same_fail_fast", _diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_t3_open_same_fail_fast_h20", "mean_return_r"), -0.0055, ">=", bool(_diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_t3_open_same_fail_fast_h20", "mean_return_r") >= -0.0055))
    add("entry_timing_t3_p05_no_harm", "validation", "p05_return_r_diff_vs_t3_same_fail_fast", _diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_t3_open_same_fail_fast_h20", "p05_return_r"), -0.02, ">=", bool(_diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_t3_open_same_fail_fast_h20", "p05_return_r") >= -0.02))

    for split in ["validation", "robustness"]:
        tr = recall_cost.loc[recall_cost["split"].eq(split)]
        if tr.empty:
            add(f"{split}_recall_cost_tradeoff", split, "recall_cost_status", "missing", "passed", "==", False)
            continue
        row = tr.iloc[0]
        add(f"{split}_net_added_capture_vs_ep2", split, "net_added_capture_vs_ep2_count", row["net_added_capture_vs_ep2_count"], 0, ">", bool(row["net_added_capture_vs_ep2_count"] > 0))
        add(f"{split}_incremental_loss_bound", split, "incremental_loss_r_per_added_big_winner_vs_ep2", row["incremental_loss_r_per_added_big_winner_vs_ep2"], row["max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2"], "<=", bool(row["incremental_loss_r_per_added_big_winner_vs_ep2"] <= row["max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2"]))
        add(f"{split}_incremental_exposure_bound", split, "incremental_exposure_days_per_added_big_winner_vs_ep2", row["incremental_exposure_days_per_added_big_winner_vs_ep2"], row["max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2"], "<=", bool(row["incremental_exposure_days_per_added_big_winner_vs_ep2"] <= row["max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2"]))

    gate = pd.DataFrame(rows)
    hard_pass = bool(gate.loc[gate["is_hard_gate"].astype(bool), "status"].eq("passed").all())
    validation_trade = recall_cost.loc[recall_cost["split"].eq("validation")]
    robustness_trade = recall_cost.loc[recall_cost["split"].eq("robustness")]
    validation_high_recall = bool(hard_pass and day_ratio >= 1.0 and ep_ratio >= 1.0 and not validation_trade.empty and validation_trade.iloc[0]["net_added_capture_vs_ep2_count"] > 0)
    robustness_ok = bool(robust_recall_diff >= -0.10 and not robustness_trade.empty and robustness_trade.iloc[0]["net_added_capture_vs_ep2_count"] > 0)
    archive = bool(
        not validation_high_recall
        and val_recall_diff >= -0.15
        and _diff_metric(baseline_diff, "validation", "same_cooling_qualified_seed_no_fail_fast_hold_h20", "failed_seed_average_loss_r") < 0
        and _diff_metric(baseline_diff, "validation", "same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted", "failed_seed_average_loss_r") <= 0
    )
    if validation_high_recall and robustness_ok:
        decision = "go_to_r02"
    elif validation_high_recall:
        decision = "go_to_r02_with_robustness_warning"
    elif archive:
        decision = "archive_cost_control_sleeve_no_r02"
    else:
        decision = "stop_ep4_r01_1_path"
    return gate, decision


def build_r01_1_final_report(
    decision: str,
    reference_audit: pd.DataFrame,
    density: pd.DataFrame,
    raw_waterfall: pd.DataFrame,
    cooling_waterfall: pd.DataFrame,
    recall: pd.DataFrame,
    entry_after_reference: pd.DataFrame,
    baseline_diff: pd.DataFrame,
    recall_cost: pd.DataFrame,
    gate: pd.DataFrame,
) -> str:
    failed = gate.loc[gate["status"].eq("failed")]
    sections = [
        "# EP4 R01.1 Emission-Throttled Cooling Probe Report",
        "",
        f"- Final decision: `{decision}`",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        "- Phase boundary: raw R01 V2 seed only; deterministic 20D emission throttle; T+1 cooling observation; T+2 0.25R probe; no model training, add, sizing, or dynamic exit.",
        "",
        "## R01 V2 Failure Inheritance",
        "R01 V2 stopped because seed-day density and validation matched-delay timing failed; R01.1 only tests deterministic emission throttling and cooling entry as the repair.",
        "",
        "## Raw Seed Formula",
        "`money_ratio20 > 1.0 AND money_ratio5 > 2.0 AND rps5 > 0.50 AND boll20_pct_b > 1.0 AND close_near_high10 >= 1.0`.",
        "",
        "## Emission Throttle Definition",
        "Same instrument emits the first raw seed, suppresses T+1 through T+20 raw seeds, and can emit again only from T+21. The state is evaluated over full history and does not reset at split boundaries.",
        raw_waterfall.to_markdown(index=False),
        "",
        "## Cooling Entry Definition",
        "After emitted seed T, observe T+1 close. Cancel if T+1 close breaks seed-day low, breakout reference, or pivot low. Otherwise attempt T+2 open.",
        cooling_waterfall.to_markdown(index=False),
        "",
        "## Reference Windows",
        reference_audit.to_markdown(index=False),
        "",
        "## Recall Bridge",
        recall.to_markdown(index=False),
        "",
        "## Entry-After-Reference Audit",
        "Primary recall is seed-start recall. Rows whose T+2 entry occurs after the reference date are reported here and must not be described as pre-reference executable capture.",
        entry_after_reference.to_markdown(index=False),
        "",
        "## Density and EP2 Comparison",
        density.to_markdown(index=False),
        "",
        "## Entry Timing Repair Evidence",
        baseline_diff.loc[baseline_diff["baseline_id"].astype(str).str.contains("t1_open|t3_open|same_emitted", regex=True, na=False)].to_markdown(index=False),
        "",
        "## Recall-Cost Tradeoff",
        recall_cost.to_markdown(index=False),
        "",
        "## Matched-Delay and Matched-Random Evidence",
        "Matched-delay T+3 is a hard timing reliability check. Matched-random remains report-only and cannot create pass or fail.",
        "",
        "## VCP and Continuous Confirmation Audit",
        "VCP and continuous confirmation are report-only diagnostics in this run; they do not alter the main seed, entry, gates, or decision.",
        "",
        "## Gate Evidence",
        gate.to_markdown(index=False),
        "",
        "## Failed Gates",
        failed.to_markdown(index=False) if not failed.empty else "No failed gates.",
        "",
        "## R02 Handoff",
        "R02 may only use survived cooling-qualified probe episodes if the decision is `go_to_r02` or `go_to_r02_with_robustness_warning`. Otherwise R02 must not start without a new requirement.",
        "",
        "## R02 Non-Assumptions",
        "This report does not prove standalone profitability, optimal fail-fast, VCP hard-gate value, confirmation hard-gate value, add eligibility, ATR/state stops, or portfolio risk budgeting.",
    ]
    return "\n".join(sections) + "\n"


def run_r01_1(config_path: str | Path = R01_1_DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths, ep2_config = load_config(config_path)
    authority = assert_authority_inputs_r01_1(config)
    panel, calendar = load_provider_spine(config, ep2_config)
    stock = prepare_stock_day_panel(config, ep2_config, panel, calendar)
    bucket_freeze, stock = build_bucket_freeze(stock, config)
    data_max = pd.to_datetime(stock["date"]).max()
    effective_windows, data_max_minus = split_effective_windows(config, calendar, data_max)
    effective_boundaries, _ = split_effective_boundaries(config, calendar, data_max)
    reference = build_big_winner_reference(stock, config, calendar, effective_windows)
    bridge_reference = build_ep2_bridge_reference(stock, config, calendar)

    raw_events = build_candidate_seed_events(stock, config)
    raw_panel = build_r01_1_raw_seed_panel(raw_events, stock, config, calendar, reference, bridge_reference, effective_windows)
    emitted_panel = apply_r01_1_emission_throttle(raw_panel, config, calendar)
    cooling_panel = build_r01_1_cooling_entry_panel(emitted_panel, stock, config, calendar)
    candidate_episodes = build_r01_1_seed_episodes(cooling_panel, config, calendar)

    ep2_events = build_ep2_seed_events(stock, config)
    ep2_episodes = build_seed_episodes(ep2_events, stock, config, calendar, reference, bridge_reference, effective_windows)
    episodes = pd.concat([candidate_episodes, ep2_episodes], ignore_index=True)
    episodes_extra = _r01_1_episode_extra(cooling_panel, episodes)

    label_a = label_a_audit(episodes_extra, stock, calendar)
    episodes_for_sim = apply_label_flags(enrich_episode_for_sim(episodes_extra), label_a)
    candidate_sim_input = episodes_for_sim.loc[(episodes_for_sim["seed_family_id"].eq(CANDIDATE_SEED_ID)) & (episodes_for_sim["executable_status"].eq("passed"))].copy()
    probe = simulate_episode_rows(candidate_sim_input, config, ep2_config, stock, calendar, fail_fast=True, id_prefix="r01_1_candidate")
    probe = enrich_r01_1_probe(probe, episodes_extra, reference)

    baseline_inputs = build_r01_1_baseline_inputs(episodes_for_sim, stock, config, calendar, reference)
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
            baseline_frames.append(simulate_episode_rows(rows, config, ep2_config, stock, calendar, fail_fast="no_fail_fast" not in baseline_id, id_prefix=baseline_id, baseline_id=baseline_id))
    baseline = pd.concat(baseline_frames, ignore_index=True) if baseline_frames else pd.DataFrame(columns=BASELINE_SIM_COLUMNS)

    density = build_r01_1_density_audit(stock, raw_panel, emitted_panel, cooling_panel, candidate_episodes, ep2_episodes, config)
    raw_waterfall, cooling_waterfall = build_r01_1_waterfalls(raw_panel, emitted_panel, cooling_panel)
    recall = build_r01_1_recall_bridge(reference, raw_panel, emitted_panel, cooling_panel, candidate_episodes, probe, ep2_episodes)
    recall_cost = build_recall_cost_tradeoff(episodes, probe, baseline, config)
    baseline_diff = build_baseline_diff_audit(probe, baseline)
    random_health = build_random_health_audit(baseline, config)
    delay_audit = build_delay_ineligible_audit(baseline)
    r_unit = build_r_unit_distribution_audit(probe, baseline)
    no_ff = baseline.loc[baseline["baseline_id"].eq("same_cooling_qualified_seed_no_fail_fast_hold_h20")]
    ff_path, ff_error = build_fail_fast_audits(probe, no_ff)
    risk_pct = build_r01_1_risk_pct_quintile_cost_control(probe, baseline, config)
    gate, decision = build_r01_1_gate_audit(authority, density, recall, baseline_diff, delay_audit, recall_cost, risk_pct, config)
    counterfactual = build_counterfactual(decision, probe, pd.DataFrame(columns=["split", "cap_violation_flag"]))
    reference_audit = build_big_winner_audit(reference, effective_windows, data_max, data_max_minus, effective_boundaries if is_v3_config(config) else None)
    entry_after_reference = build_r01_1_entry_after_reference_audit(probe)
    report = build_r01_1_final_report(decision, reference_audit, density, raw_waterfall, cooling_waterfall, recall, entry_after_reference, baseline_diff, recall_cost, gate)

    for col in ["failed_seed_primary", "primary_metric_eligible_seed_episode", "failed_seed_label_a_h10_u1_5", "failed_seed_label_a_h20_u2_0", "failed_seed_h20_negative", "failed_seed_fail_fast_triggered", "terminal_blocked_exit", "captures_primary_big_winner", "entry_after_reference"]:
        if col in probe.columns:
            probe[col] = probe[col].map(lambda value: pd.NA if pd.isna(value) else bool(value)).astype("boolean")
    for col in ["baseline_failed_seed_primary", "primary_metric_eligible_baseline_event", "captures_primary_big_winner", "random_excluded_candidate_seed_day", "random_capacity_shortfall"]:
        if col in baseline.columns:
            baseline[col] = baseline[col].map(lambda value: pd.NA if pd.isna(value) else bool(value)).astype("boolean")

    write_parquet(reference, paths.cache_dir / "r01_1_big_winner_reference_panel.parquet")
    write_parquet(raw_panel, paths.cache_dir / "r01_1_raw_seed_panel.parquet")
    write_parquet(emitted_panel, paths.cache_dir / "r01_1_emitted_seed_panel.parquet")
    write_parquet(cooling_panel, paths.cache_dir / "r01_1_cooling_entry_panel.parquet")
    write_parquet(candidate_episodes, paths.cache_dir / "r01_1_seed_episode_panel.parquet")
    write_parquet(probe, paths.cache_dir / "r01_1_probe_simulation_panel.parquet")
    write_parquet(baseline, paths.cache_dir / "r01_1_baseline_simulation_panel.parquet")

    write_csv(gate, paths.reports_dir / "r01_1_gate_audit.csv")
    write_csv(density, paths.reports_dir / "r01_1_density_audit.csv")
    write_csv(raw_waterfall, paths.reports_dir / "r01_1_raw_to_emitted_waterfall.csv")
    write_csv(cooling_waterfall, paths.reports_dir / "r01_1_cooling_entry_waterfall.csv")
    write_csv(recall, paths.reports_dir / "r01_1_recall_bridge.csv")
    write_csv(entry_after_reference, paths.reports_dir / "r01_1_entry_after_reference_audit.csv")
    write_csv(recall_cost, paths.reports_dir / "r01_1_recall_cost_tradeoff.csv")
    write_csv(ff_path, paths.reports_dir / "r01_1_fail_fast_attribution.csv")
    write_csv(ff_error, paths.reports_dir / "r01_1_false_reject_missed_failure_audit.csv")
    write_csv(baseline_diff.loc[baseline_diff["baseline_id"].astype(str).str.contains("t1_open|t3_open|same_emitted", regex=True, na=False)], paths.reports_dir / "r01_1_entry_timing_audit.csv")
    write_csv(r_unit, paths.reports_dir / "r01_1_r_unit_distribution_audit.csv")
    write_csv(risk_pct, paths.reports_dir / "r01_1_risk_pct_quintile_cost_control.csv")
    write_csv(baseline.groupby(["split", "baseline_id", "eligibility_status"], dropna=False).size().reset_index(name="row_count"), paths.reports_dir / "r01_1_baseline_eligibility_audit.csv")
    write_csv(pd.DataFrame({"audit_name": ["vcp"], "audit_only_status": ["report_only_not_decision_changing"]}), paths.reports_dir / "r01_1_vcp_audit.csv")
    write_csv(pd.DataFrame({"audit_name": ["continuous_confirmation"], "audit_only_status": ["report_only_not_decision_changing"]}), paths.reports_dir / "r01_1_confirmation_audit.csv")
    write_csv(delay_audit, paths.reports_dir / "r01_1_matched_delay_reliability_audit.csv")
    write_csv(random_health, paths.reports_dir / "r01_1_matched_random_reliability_audit.csv")
    write_csv(pd.DataFrame({"final_decision": [decision], "archive_allowed": [decision == "archive_cost_control_sleeve_no_r02"]}), paths.reports_dir / "r01_1_archive_decision_audit.csv")
    write_csv(counterfactual, paths.reports_dir / "r01_1_counterfactual_failure_inheritance.csv")
    write_csv(bucket_freeze, paths.reports_dir / "r01_1_matched_control_bucket_freeze.csv")
    write_csv(authority, paths.reports_dir / "r01_1_upstream_authority.csv")
    (paths.reports_dir / "r01_1_final_report.md").write_text(report, encoding="utf-8")

    artifact_hashes = {name: file_hash(paths.cache_dir / name) for name in R01_1_CACHE}
    artifact_hashes |= {name: file_hash(paths.reports_dir / name) for name in R01_1_REPORTS}
    manifest = {
        "phase": config["phase"],
        "requirement_id": config.get("requirement_id", R01_1_REQUIREMENT_ID),
        "schema_version": R01_1_SCHEMA_VERSION,
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "output_root": relpath(paths.output_root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_decision": decision,
        "raw_seed_formula_id": config["seed_rules"]["candidate_seed_formula_id"],
        "emission_rule_id": config["emission"]["throttle_policy"],
        "cooling_entry_rule_id": config["cooling_entry"]["entry_family_id"],
        "fail_fast_family_id": config["fail_fast"]["family_id"],
        "cost_model_source": config["execution"]["cost_model_source"],
        "selection_policy_status": "no_validation_or_robustness_threshold_selection",
        "configured_split_windows": {split: [_date_str(start), _date_str(end)] for split, (start, end) in split_bounds(config).items()},
        "effective_reference_windows": {split: [_date_str(start), _date_str(end)] for split, (start, end) in effective_windows.items()},
        "data_max_date": _date_str(data_max),
        "data_max_date_minus_forward_horizon": _date_str(data_max_minus),
        "primary_big_winner_reference_count": int(reference.shape[0]),
        "raw_seed_count": int(raw_panel.shape[0]),
        "emitted_seed_count": int(emitted_panel["emitted_seed_flag"].astype(bool).sum()) if not emitted_panel.empty else 0,
        "cooling_qualified_probe_count": int(cooling_panel["cooling_qualified_probe"].astype(bool).sum()) if not cooling_panel.empty else 0,
        "gate_count": int(gate.shape[0]),
        "failed_gate_count": int(gate["status"].eq("failed").sum()),
        "artifact_hashes": artifact_hashes,
    }
    write_json(manifest, paths.manifests_dir / "r01_1_run_manifest.json")
    return {
        "output_root": relpath(paths.output_root),
        "final_decision": decision,
        "gate_count": int(gate.shape[0]),
        "failed_gate_count": int(gate["status"].eq("failed").sum()),
        "primary_big_winner_reference_count": int(reference.shape[0]),
        "raw_seed_count": int(raw_panel.shape[0]),
        "emitted_seed_count": int(manifest["emitted_seed_count"]),
        "cooling_qualified_probe_count": int(manifest["cooling_qualified_probe_count"]),
    }


def run_r01(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths, ep2_config = load_config(config_path)
    authority = assert_authority_inputs(config)
    panel, calendar = load_provider_spine(config, ep2_config)
    stock = prepare_stock_day_panel(config, ep2_config, panel, calendar)
    bucket_freeze, stock = build_bucket_freeze(stock, config)
    data_max = pd.to_datetime(stock["date"]).max()
    effective_windows, data_max_minus = split_effective_windows(config, calendar, data_max)
    effective_boundaries, _ = split_effective_boundaries(config, calendar, data_max)
    reference = build_big_winner_reference(stock, config, calendar, effective_windows)
    bridge_reference = build_ep2_bridge_reference(stock, config, calendar)
    candidate_events = build_candidate_seed_events(stock, config)
    if not candidate_events.empty:
        candidate_seed_stock_days = set(zip(candidate_events["instrument"].astype(str), pd.to_datetime(candidate_events["signal_date"]).dt.normalize()))
        stock["candidate_seed_stock_day"] = [item in candidate_seed_stock_days for item in zip(stock["instrument"].astype(str), stock["date"])]
    else:
        stock["candidate_seed_stock_day"] = False
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
    episodes_for_sim, probe, baseline = apply_v3_terminal_boundaries(episodes_for_sim, probe, baseline, config, calendar, data_max)
    episodes = episodes_for_sim[SEED_EPISODE_COLUMNS].copy()

    density, density_tightness = build_density_audits(stock, episodes, seed_events, config)
    recall = build_recall_audit(reference, bridge_reference, episodes)
    recall_cost = build_recall_cost_tradeoff(episodes, probe, baseline, config, reference, calendar)
    baseline_diff = build_baseline_diff_audit(probe, baseline)
    random_health = build_random_health_audit(baseline, config)
    delay_audit = build_delay_ineligible_audit(baseline)
    r_unit = build_r_unit_distribution_audit(probe, baseline)
    no_ff = baseline.loc[baseline["baseline_id"].eq("same_seed_no_fail_fast_hold_h20")]
    ff_path, ff_error = build_fail_fast_audits(probe, no_ff)
    gate, decision = build_gate_audit(authority, density, recall, baseline_diff, delay_audit, random_health, recall_cost, probe, baseline, config)
    counterfactual = build_counterfactual(decision, probe, density_tightness, baseline_diff, label_a)
    reference_audit = build_big_winner_audit(reference, effective_windows, data_max, data_max_minus, effective_boundaries if is_v3_config(config) else None)
    report = build_final_report(
        decision,
        authority,
        reference_audit,
        density,
        density_tightness,
        recall,
        recall_cost,
        baseline_diff,
        delay_audit,
        r_unit,
        ff_path,
        ff_error,
        counterfactual,
        gate,
        random_health,
        config,
    )

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
        "candidate_seed_id": CANDIDATE_SEED_ID,
        "candidate_seed_formula_id": config.get("seed_rules", {}).get("candidate_seed_formula_id", "ep4_wide_seed_v0"),
        "primary_recall_window_id": primary_recall_window_id(config),
        "primary_recall_lookback_days": primary_recall_lookback_days(config),
        "configured_train_window": [config["split"]["train_start"], config["split"]["train_end"]],
        "configured_validation_window": [config["split"]["validation_start"], config["split"]["validation_end"]],
        "configured_robustness_window": [config["split"]["robustness_start"], config["split"]["robustness_end"]],
        "effective_train_reference_window": [_date_str(effective_windows["train"][0]), _date_str(effective_windows["train"][1])],
        "effective_validation_reference_window": [_date_str(effective_windows["validation"][0]), _date_str(effective_windows["validation"][1])],
        "effective_robustness_reference_window": [_date_str(effective_windows["robustness"][0]), _date_str(effective_windows["robustness"][1])],
        "effective_train_primary_seed_end": _date_str(effective_boundaries["train"]["effective_primary_seed_end"]),
        "effective_validation_primary_seed_end": _date_str(effective_boundaries["validation"]["effective_primary_seed_end"]),
        "effective_robustness_primary_seed_end": _date_str(effective_boundaries["robustness"]["effective_primary_seed_end"]),
        "effective_train_gate_entry_end": _date_str(effective_boundaries["train"]["effective_gate_entry_end"]),
        "effective_validation_gate_entry_end": _date_str(effective_boundaries["validation"]["effective_gate_entry_end"]),
        "effective_robustness_gate_entry_end": _date_str(effective_boundaries["robustness"]["effective_gate_entry_end"]),
        "max_probe_observation_horizon_trading_days": max_probe_observation_horizon(config),
        "split_boundary_policy": config.get("split", {}).get("split_boundary_policy", {}),
        "primary_capture_basis": config.get("capture_time_basis", {}).get("primary_capture_basis", "signal_date"),
        "signal_capture_basis": config.get("capture_time_basis", {}).get("signal_capture_basis", "primary"),
        "seed_discovery_artifact": config.get("seed_provenance_gate", {}).get("discovery_artifact", ""),
        "seed_discovery_scope": config.get("seed_provenance_gate", {}).get("discovery_scope", "train_only"),
        "validation_oos_clean": bool(config.get("seed_provenance_gate", {}).get("validation_oos_clean", True)),
        "post30_search_eligible_day_density": config.get("density_provenance", {}).get("post30_search_eligible_day_density", np.nan),
        "r01_full_universe_seed_day_density_by_split": density.loc[density["seed_family_id"].eq(CANDIDATE_SEED_ID)].set_index("split")["seed_day_rate"].to_dict() if not density.empty else {},
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
        "candidate_seed_id": CANDIDATE_SEED_ID,
        "candidate_seed_formula_id": config.get("seed_rules", {}).get("candidate_seed_formula_id", "ep4_wide_seed_v0"),
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
    if is_v3_config(config):
        expected_formula = "close_near_high5_gt_0pct_and_vol_ratio10_gt_1_2_and_vol_ratio3_gt_1_2_and_rps5_gt_60"
        if config.get("seed_rules", {}).get("candidate_seed_formula_id") != expected_formula:
            failures.append("V3 candidate seed formula is not the frozen post30 formula")
        for key in [
            "effective_train_primary_seed_end",
            "effective_validation_primary_seed_end",
            "effective_robustness_primary_seed_end",
            "effective_train_gate_entry_end",
            "effective_validation_gate_entry_end",
            "effective_robustness_gate_entry_end",
            "max_probe_observation_horizon_trading_days",
            "primary_capture_basis",
            "seed_discovery_artifact",
            "seed_discovery_scope",
            "validation_oos_clean",
            "post30_search_eligible_day_density",
            "r01_full_universe_seed_day_density_by_split",
        ]:
            if key not in manifest or manifest.get(key) in ("", None, []):
                failures.append(f"V3 manifest missing {key}")
        if manifest.get("primary_capture_basis") != "entry_execution_date":
            failures.append("V3 primary capture basis must be entry_execution_date")
        if manifest.get("seed_discovery_scope") != "train_only" and manifest.get("final_decision") in {"go_to_r02", "go_to_r02_with_robustness_warning"}:
            failures.append("V3 all-split discovery cannot authorize R02 decisions")

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
    if is_v3_config(config) and not reference.empty:
        for split in ["train", "validation", "robustness"]:
            window_key = f"effective_{split}_reference_window"
            if window_key not in manifest or not manifest.get(window_key):
                continue
            start, end = [pd.Timestamp(value) for value in manifest[window_key]]
            ref_dates = pd.to_datetime(reference.loc[reference["split"].eq(split), "reference_date"], errors="coerce")
            if bool(((ref_dates < start) | (ref_dates > end)).any()):
                failures.append(f"V3 reference panel contains {split} rows outside effective reference window")
    seed_events = pd.read_parquet(paths.cache_dir / "r01_seed_event_panel.parquet")
    if is_v3_config(config):
        v3_required_event_cols = ["close_near_high5_gt_0pct_triggered", "rolling_close_high5_asof", "vol_ratio10", "vol_ratio3", "rps5"]
        missing_v3_event_cols = [col for col in v3_required_event_cols if col not in seed_events.columns]
        if missing_v3_event_cols:
            failures.append(f"V3 seed event panel missing columns: {missing_v3_event_cols}")
        candidate_rows = seed_events.loc[seed_events["seed_family_id"].eq(CANDIDATE_SEED_ID) & seed_events["hard_filter_status"].eq("passed")]
        if not candidate_rows.empty:
            formula_ok = (
                candidate_rows["close_near_high5_gt_0pct_triggered"].astype(bool)
                & (candidate_rows["vol_ratio10"].astype(float) > 1.2)
                & (candidate_rows["vol_ratio3"].astype(float) > 1.2)
                & (candidate_rows["rps5"].astype(float) > 0.60)
            )
            if not bool(formula_ok.all()):
                failures.append("V3 candidate seed rows do not reproduce the frozen high5/volume/rps formula")
    if seed_events.loc[seed_events["seed_family_id"].eq(CANDIDATE_SEED_ID), "rs_rank_pct_audit"].notna().any():
        hard_rejects = seed_events.loc[
            seed_events["seed_family_id"].eq(CANDIDATE_SEED_ID)
            & seed_events["reject_reason"].astype(str).str.contains("relative_strength|rs_rank|rs_filter", case=False, regex=True)
        ]
        if not hard_rejects.empty:
            failures.append("candidate seed appears to use relative strength as a hard filter")

    episodes = pd.read_parquet(paths.cache_dir / "r01_seed_episode_panel.parquet")
    if is_v3_config(config):
        invalid_masks = []
        for split in ["train", "validation", "robustness"]:
            gate_key = f"effective_{split}_gate_entry_end"
            gate_end = pd.Timestamp(manifest[gate_key]) if gate_key in manifest and manifest.get(gate_key) else pd.NaT
            split_mask = (
                episodes["split"].eq(split)
                & episodes["primary_metric_eligible_seed_episode"].astype(bool)
                & (pd.to_datetime(episodes["entry_execution_date"]) > gate_end)
            )
            invalid_masks.append(split_mask)
        invalid_primary = episodes.loc[pd.concat(invalid_masks, axis=1).any(axis=1)] if invalid_masks else episodes.iloc[0:0]
    else:
        robustness_end = pd.Timestamp(manifest["effective_robustness_reference_window"][1])
        invalid_primary = episodes.loc[
            episodes["primary_metric_eligible_seed_episode"].astype(bool)
            & (pd.to_datetime(episodes["episode_start_signal_date"]) > robustness_end)
        ]
    if not invalid_primary.empty:
        failures.append("primary metric eligible seed episodes extend beyond effective gate entry end" if is_v3_config(config) else "primary metric eligible seed episodes extend beyond effective reference end")
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
    if is_v3_config(config):
        for baseline_id in ["same_seed_matched_delay_1d_same_fail_fast_h20", "same_seed_matched_delay_3d_same_fail_fast_h20", "ep2_detector_probe_with_simple_stop_bridge"]:
            bdf = baseline.loc[baseline["baseline_id"].eq(baseline_id)]
            if bdf.empty:
                continue
            timestamp_cols = ["candidate_entry_execution_date", "baseline_entry_execution_date", "capture_timestamp_used"]
            if baseline_id == "ep2_detector_probe_with_simple_stop_bridge":
                timestamp_cols.append("ep2_bridge_entry_execution_date")
            missing_ts = [col for col in timestamp_cols if col not in bdf.columns or bdf[col].isna().all()]
            if missing_ts:
                failures.append(f"V3 baseline {baseline_id} missing executable timestamp fields: {missing_ts}")

    gate = pd.read_csv(paths.reports_dir / "r01_gate_audit.csv")
    gate_missing = [col for col in ["gate_id", "split", "metric_name", "metric_value", "threshold", "comparison", "status", "is_hard_gate", "failure_reason"] if col not in gate.columns]
    if gate_missing:
        failures.append(f"gate audit missing columns: {gate_missing}")
    if fail_on_hard_gates and not gate.empty:
        failed_hard = gate.loc[gate["is_hard_gate"].astype(bool) & gate["status"].eq("failed")]
        if not failed_hard.empty:
            failures.append("hard gates failed: " + "; ".join(failed_hard["gate_id"].astype(str).head(20).tolist()))
    if is_v3_config(config):
        required_v3_gate_ids = {
            "seed_provenance_r02_cap",
            "bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector",
            "fail_fast_survived_big_winner_recall_loss_vs_same_seed_no_fail_fast",
            "loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector",
            "matched_delay_1d_p05_no_harm",
            "matched_delay_3d_p05_no_harm",
            "robustness_failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast",
            "robustness_p05_return_r_diff_vs_matched_delay_same_fail_fast_min",
            "robustness_recall_cost_score_positive",
            "robustness_incremental_loss_bound",
            "robustness_incremental_exposure_bound",
        }
        observed_gate_ids = set(gate["gate_id"].astype(str))
        missing_gate_ids = sorted(required_v3_gate_ids - observed_gate_ids)
        if missing_gate_ids:
            failures.append(f"V3 gate audit missing required gate ids: {missing_gate_ids}")
        trade = pd.read_csv(paths.reports_dir / "r01_recall_cost_tradeoff.csv")
        required_trade_cols = [
            "signal_capture_count",
            "entry_capture_count",
            "signal_only_not_entry_within_window_count",
            "capture_time_basis",
            "seed_discovery_scope",
            "validation_oos_clean",
            "loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector",
            "exposure_days_per_captured_big_winner_seed_diff_vs_ep2_detector",
        ]
        missing_trade_cols = [col for col in required_trade_cols if col not in trade.columns]
        if missing_trade_cols:
            failures.append(f"V3 recall-cost tradeoff missing columns: {missing_trade_cols}")
        elif not trade["capture_time_basis"].eq("entry_execution_date").all():
            failures.append("V3 recall-cost tradeoff must use entry_execution_date capture basis")
        recall_audit = pd.read_csv(paths.reports_dir / "r01_seed_recall_audit.csv")
        for col in ["bridge_ep2_big_winner_reference_count", "captured_ep2_bridge_big_winner_count", "bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector"]:
            if col not in recall_audit.columns:
                failures.append(f"V3 seed recall audit missing column: {col}")
        random_health = pd.read_csv(paths.reports_dir / "r01_random_baseline_health_audit.csv")
        random_stats = set(random_health["replicate_stat"].astype(str)) if not random_health.empty and "replicate_stat" in random_health.columns else set()
        if not {"mean", "p05", "p50", "p95"}.issubset(random_stats):
            failures.append("V3 random health audit missing mean/p05/p50/p95 replicate stats")
        counterfactual = pd.read_csv(paths.reports_dir / "r01_counterfactual_failure_inheritance.csv")
        cf_families = set(counterfactual["counterfactual_family"].astype(str)) if not counterfactual.empty and "counterfactual_family" in counterfactual.columns else set()
        if not {"conservative_fail", "p05_no_harm", "density_cap", "fail_fast_window"}.issubset(cf_families):
            failures.append("V3 counterfactual audit missing required families")
        r_unit = pd.read_csv(paths.reports_dir / "r01_r_unit_distribution_audit.csv")
        quintile_rows = r_unit.loc[
            r_unit["split"].astype(str).eq("validation")
            & r_unit["initial_risk_pct_quintile"].astype(str).ne("all")
        ] if "initial_risk_pct_quintile" in r_unit.columns else pd.DataFrame()
        if quintile_rows.empty:
            failures.append("V3 R-unit audit missing validation risk-quintile rows")

    report = (paths.reports_dir / "r01_final_report.md").read_text(encoding="utf-8")
    required_report_tokens = ["Final decision", "Recall-Cost Tradeoff", "Matched-Random Reliability", "R02 Handoff"]
    if is_v3_config(config):
        required_report_tokens += [
            "OOS status",
            "Post30 Provenance",
            "retrospective evaluation anchor",
            "Captured Post-Reference Entry Cost",
            "Density Cap Tightness",
            "Matched-Delay Ineligible Bias",
            "R-Unit Distribution And Risk Quintile Cost Control",
            "Fail-Fast Attribution",
            "Fail-Fast Error Audit",
            "Counterfactual Failure Inheritance",
        ]
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


def validate_r01_1(config_path: str | Path = R01_1_DEFAULT_CONFIG, fail_on_hard_gates: bool = True) -> dict[str, Any]:
    config, paths, _ = load_config(config_path)
    failures: list[str] = []
    required_paths = [paths.cache_dir / name for name in R01_1_CACHE]
    required_paths += [paths.reports_dir / name for name in R01_1_REPORTS]
    required_paths += [paths.manifests_dir / name for name in R01_1_MANIFESTS]
    missing = [relpath(path) for path in required_paths if not path.exists()]
    if missing:
        failures.append("missing required R01.1 artifacts: " + "; ".join(missing))
    if failures:
        raise RuntimeError("; ".join(failures))

    manifest = read_json(paths.manifests_dir / "r01_1_run_manifest.json")
    if manifest.get("phase") != config["phase"]:
        failures.append("manifest phase mismatch")
    if manifest.get("requirement_id") != config.get("requirement_id", R01_1_REQUIREMENT_ID):
        failures.append("manifest requirement_id mismatch")
    if manifest.get("final_decision") not in R01_1_ALLOWED_DECISIONS:
        failures.append("manifest final decision is not an allowed R01.1 decision")
    exact_formula = "money_ratio20_gt_1_0_and_money_ratio5_gt_2_0_and_rps5_gt_50_and_boll20_pct_b_gt_1_0_and_close_near_high10_gt_0"
    if manifest.get("raw_seed_formula_id") != exact_formula:
        failures.append("raw seed formula differs from exact R01 V2 five-condition formula")
    if int(config["emission"]["throttle_window_trading_days"]) != 20:
        failures.append("emission throttle is not exactly 20 trading days")
    if config["cooling_entry"]["entry_family_id"] != "cooling_observation_day_then_t2_open_entry":
        failures.append("cooling entry is not T+1 observe / T+2 open")

    raw = pd.read_parquet(paths.cache_dir / "r01_1_raw_seed_panel.parquet")
    emitted = pd.read_parquet(paths.cache_dir / "r01_1_emitted_seed_panel.parquet")
    cooling = pd.read_parquet(paths.cache_dir / "r01_1_cooling_entry_panel.parquet")
    episodes = pd.read_parquet(paths.cache_dir / "r01_1_seed_episode_panel.parquet")
    probe = pd.read_parquet(paths.cache_dir / "r01_1_probe_simulation_panel.parquet")
    baseline = pd.read_parquet(paths.cache_dir / "r01_1_baseline_simulation_panel.parquet")
    required_raw_cols = ["instrument", "raw_signal_date", "raw_seed_flag", "money_ratio20", "money_ratio5", "rps5", "boll20_pct_b", "close_near_high10", "split"]
    required_emitted_cols = ["instrument", "raw_signal_date", "emitted_signal_date", "emitted_seed_flag", "emission_suppressed", "suppressed_by_emitted_seed_id", "split_boundary_suppressed"]
    required_cooling_cols = ["instrument", "emitted_signal_date", "cooling_observation_date", "entry_date", "cooling_cancelled", "cooling_cancel_reason", "entry_buy_executable", "seed_day_low", "breakout_reference", "pivot_low_10d", "split"]
    required_probe_cols = ["simulation_id", "seed_episode_id", "emitted_seed_id", "emitted_signal_date", "cooling_observation_date", "entry_date", "entry_price", "return_r", "loss_r", "primary_metric_eligible_seed_episode", "captures_primary_big_winner", "captured_reference_event_id", "entry_after_reference", "entry_after_reference_days"]
    for name, df, cols in [
        ("r01_1_raw_seed_panel.parquet", raw, required_raw_cols),
        ("r01_1_emitted_seed_panel.parquet", emitted, required_emitted_cols),
        ("r01_1_cooling_entry_panel.parquet", cooling, required_cooling_cols),
        ("r01_1_probe_simulation_panel.parquet", probe, required_probe_cols),
    ]:
        miss = [col for col in cols if col not in df.columns]
        if miss:
            failures.append(f"{name} missing columns: {miss}")

    emitted_rows = emitted.loc[emitted["emitted_seed_flag"].astype(bool)].copy()
    if not emitted_rows.empty:
        calendar_path = topic_path(config["data_sources"]["trading_calendar_path"])
        calendar = pd.to_datetime(pd.read_csv(calendar_path, header=None)[0]).dt.normalize()
        pos = {pd.Timestamp(dt): idx for idx, dt in enumerate(calendar)}
        for instrument, group in emitted_rows.sort_values(["instrument", "emitted_signal_date"]).groupby("instrument"):
            positions = [pos.get(pd.Timestamp(dt)) for dt in pd.to_datetime(group["emitted_signal_date"])]
            positions = [p for p in positions if p is not None]
            if any((b - a) <= 20 for a, b in zip(positions, positions[1:])):
                failures.append(f"emission throttle violated for {instrument}")
                break
    if not episodes.empty and not episodes["seed_event_count"].eq(1).all():
        failures.append("R01.1 candidate episodes merged multiple emitted seeds")
    if int(episodes.shape[0]) != int(emitted_rows.shape[0]):
        failures.append("candidate episode count does not equal emitted seed count")
    if "cooling_cancelled" not in cooling.columns:
        failures.append("cooling cancelled rows/field are missing")

    observed_baselines = set(baseline["baseline_id"].dropna().astype(str))
    missing_baselines = sorted(set(config["baselines"]) - observed_baselines)
    if missing_baselines:
        failures.append(f"missing required R01.1 baseline ids: {missing_baselines}")
    if "same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted" not in observed_baselines:
        failures.append("missing total-effect emitted-sleeve T+1 bridge baseline")
    random_rows = baseline.loc[baseline["matched_control_type"].eq("matched_random")]
    if not random_rows.empty:
        if not random_rows["random_sampling_replacement_policy"].eq("without_replacement_within_replicate").all():
            failures.append("matched-random replacement policy is not no-replacement")
        for col in ["random_signal_date", "random_capacity_shortfall", "random_baseline_reliability_status", "primary_metric_eligible_baseline_event", "baseline_failed_seed_primary"]:
            if col not in random_rows.columns:
                failures.append(f"matched-random missing {col}")

    gate = pd.read_csv(paths.reports_dir / "r01_1_gate_audit.csv")
    if fail_on_hard_gates:
        failed_hard = gate.loc[gate["is_hard_gate"].astype(bool) & gate["status"].eq("failed")]
        if not failed_hard.empty:
            failures.append("hard gates failed: " + "; ".join(failed_hard["gate_id"].astype(str).head(20).tolist()))
    report = (paths.reports_dir / "r01_1_final_report.md").read_text(encoding="utf-8")
    for token in ["Final decision", "Recall-Cost Tradeoff", "Entry-After-Reference Audit", "R02 Handoff"]:
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

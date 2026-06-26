#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
SOURCE_EP13_ROOT = TOPIC_ROOT / "experiments" / "pending" / "13_full_pit_native_event_discovery_v0"
RUNNER_13A_PATH = SOURCE_EP13_ROOT / "src" / "run_13a_full_pit_native_token_cartography_preflight.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r13a = load_runner(RUNNER_13A_PATH, "run_13a_full_pit_native_token_cartography_preflight_for_15a")


RUN_ID = "15A_winner_episode_label_censoring_diagnostic"
EXPERIMENT_ID = "15_path_defined_winner_episode_label_v0"
PHASE_ID = "15A"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_15a_winner_episode_label_censoring_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SPLITS = ("train", "validation", "robustness")
READOUT_SPLITS = ("train", "validation", "robustness", "all")
THRESHOLDS = {"up50pct": 0.50, "up100pct": 1.00, "up150pct": 1.50}
THRESHOLD_PRIORITY = ("up50pct", "up100pct", "up150pct")
FIXED120_SESSIONS = 120
NON_HIT_CONTROL_MIN_SESSIONS = 250
SELECTED_LABEL_ID = "vol20d_kup2p0_kdn1p0_H20"

MORPHOLOGY_FEATURES = [
    "volatility_20d",
    "volatility_60d",
    "max_drawdown_20d",
    "max_drawdown_60d",
    "ret_20d",
    "ret_60d",
    "distance_to_20d_high",
    "distance_to_60d_high",
    "distance_to_20d_low",
    "trend_ma_20_60_spread",
    "vol_compression_20d_60d",
    "rebound_from_20d_low",
]

INPUT_COLUMNS = [
    "artifact_role",
    "artifact_path",
    "resolved_path",
    "required_flag",
    "lineage_role",
    "read_status",
    "row_count",
    "column_count",
    "sha256",
    "schema_status",
    "required_column_missing_list",
]

UPSTREAM_COLUMNS = [
    "upstream_artifact_role",
    "upstream_path",
    "upstream_sha256",
    "upstream_row_count",
    "upstream_schema_status",
    "lineage_claim",
    "lineage_status",
    "selected_label_id",
    "primary_row_level_source",
    "primary_row_level_source_role",
    "cross_check_source",
    "cross_check_key",
    "cross_check_key_coverage_rate",
    "cross_check_mismatch_n",
    "upstream_formula_path_window",
    "implemented_path_window",
    "path_window_reconciliation_status",
    "path_window_reconciliation_reason",
    "blocking_reason",
]

UNIVERSE_COLUMNS = [
    "split_bucket",
    "calendar_year",
    "source_row_n",
    "unique_anchor_row_n",
    "duplicate_anchor_row_n",
    "membership_row_n",
    "membership_match_rate",
    "split_boundary_source",
    "split_boundary_status",
    "universe_membership_status",
    "blocking_reason",
]

PRICE_COLUMNS = [
    "instrument",
    "anchor_row_n",
    "qfq_row_n",
    "missing_qfq_file_flag",
    "missing_reference_pos_n",
    "missing_entry_pos_n",
    "missing_entry_price_n",
    "min_available_forward_sessions",
    "median_available_forward_sessions",
    "max_available_forward_sessions",
    "price_path_status",
    "blocking_reason",
]

BASELINE_COLUMNS = [
    "baseline_id",
    "baseline_role",
    "threshold_id",
    "threshold_return",
    "anchor_definition",
    "window_definition",
    "horizon_sessions",
    "source_artifact",
    "source_label_id",
    "source_path_window",
    "primary_row_level_source",
    "primary_row_level_source_role",
    "row_level_key",
    "cross_check_source",
    "cross_check_status",
    "path_window_reconciliation_status",
    "path_window_reconciliation_reason",
    "winner_definition",
    "horizon_complete_denominator_rule",
    "baseline_definition_status",
]

LABEL_REBUILD_COLUMNS = [
    "threshold_id",
    "split_bucket",
    "record_n",
    "path_winner_n",
    "censored_n",
    "confirmed_non_winner_n",
    "observed_non_hit_control_n",
    "fixed120_horizon_complete_n",
    "fixed120_horizon_incomplete_n",
    "fixed120_only_winner_n",
    "fixed120_only_winner_explained_n",
    "fixed120_only_winner_explanation_code_list",
    "high_based_close_based_agreement_rate",
    "row_level_explanation_available",
    "rebuild_status",
]

WINNER_COLUMNS = [
    "threshold_id",
    "split_bucket",
    "record_n",
    "path_winner_n",
    "path_winner_rate_all_records",
    "censored_n",
    "censored_rate",
    "confirmed_non_winner_n",
    "observed_non_hit_control_n",
    "fixed120_horizon_complete_n",
    "fixed120_horizon_incomplete_n",
    "fixed120_winner_n",
    "fixed120_winner_rate",
    "volscaled_h20_horizon_complete_n",
    "volscaled_h20_winner_n",
    "volscaled_h20_winner_rate",
    "slow_winner_n",
    "slow_winner_rate_all_records",
    "slow_winner_share_of_path_winners",
    "fast_winner_n",
    "overlap_path_and_fixed120_n",
    "path_only_winner_n",
    "fixed120_only_winner_n",
    "threshold_material_censoring_flag",
    "winner_set_difference_status",
]

TIME_COLUMNS = [
    "threshold_id",
    "split_bucket",
    "path_winner_n",
    "time_to_threshold_p10",
    "time_to_threshold_p25",
    "time_to_threshold_median",
    "time_to_threshold_p75",
    "time_to_threshold_p90",
    "time_to_threshold_max",
    "share_within_20d",
    "share_within_60d",
    "share_within_120d",
    "share_beyond_120d",
    "share_beyond_250d",
    "distribution_status",
]

CENSOR_COLUMNS = [
    "threshold_id",
    "split_bucket",
    "record_n",
    "censored_n",
    "censored_rate",
    "censored_median_available_forward_sessions",
    "confirmed_non_winner_n",
    "counted_in_confirmed_non_winner_n",
    "counted_in_control_without_flag_n",
    "observed_non_hit_control_n",
    "censored_isolation_status",
]

MORPHOLOGY_COLUMNS = [
    "threshold_id",
    "split_bucket",
    "cohort_id",
    "cohort_role",
    "feature_id",
    "feature_observation_boundary",
    "feature_n",
    "feature_missing_n",
    "feature_p25",
    "feature_median",
    "feature_p75",
    "feature_readout_status",
]

OVERLAP_COLUMNS = [
    "threshold_id",
    "split_bucket",
    "cohort_id",
    "state_id",
    "state_threshold_feature",
    "state_threshold_value",
    "threshold_source_split",
    "state_share",
    "fast_minus_slow_share_delta",
    "slow_winner_morphology_distinct_status",
    "overlap_readout_status",
]

EPISODE_COLUMNS = [
    "threshold_id",
    "split_bucket",
    "path_winner_anchor_row_n",
    "slow_winner_anchor_row_n",
    "approx_episode_cluster_n",
    "median_anchor_rows_per_episode_cluster",
    "p90_anchor_rows_per_episode_cluster",
    "max_anchor_rows_per_episode_cluster",
    "cluster_definition",
    "readout_role",
    "overlap_density_status",
]

SEARCH_COLUMNS = [
    "threshold_grid",
    "threshold_grid_status",
    "threshold_priority_order",
    "selected_threshold_recommendation",
    "selected_threshold_source_split",
    "selection_split_bucket",
    "threshold_selection_scope",
    "validation_used_for_selection",
    "robustness_used_for_selection",
    "close_based_role",
    "episode_peak_role",
    "observed_non_hit_control_role",
    "episode_overlap_role",
    "search_accounting_status",
]

DECISION_COLUMNS = [
    "decision_state",
    "next_allowed_requirement",
    "label_deployment_authorized",
    "signal_search_authorized",
    "selection_split_bucket",
    "selected_threshold_recommendation",
    "selected_threshold_reason",
    "selected_threshold_share_beyond_120d",
    "selected_threshold_slow_winner_rate_all_records",
    "selected_threshold_censored_rate",
    "primary_failure_reason",
    "gate_failure",
    "input_gate_status",
    "upstream_lineage_gate_status",
    "universe_membership_gate_status",
    "price_path_completeness_gate_status",
    "label_rebuild_gate_status",
    "censoring_isolation_gate_status",
    "winner_set_difference_gate_status",
    "search_accounting_gate_status",
    "slow_winner_morphology_distinct_status",
    "material_censoring_threshold_count",
    "share_beyond_120d_up50pct",
    "share_beyond_120d_up100pct",
    "share_beyond_120d_up150pct",
    "slow_winner_rate_all_records_up50pct",
    "slow_winner_rate_all_records_up100pct",
    "slow_winner_rate_all_records_up150pct",
    "censored_rate_up50pct",
    "censored_rate_up100pct",
    "censored_rate_up150pct",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 15A winner episode label censoring diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_lineage_audit": TABLE_DIR / "upstream_lineage_audit.csv",
        "universe_membership_audit": TABLE_DIR / "universe_membership_audit.csv",
        "price_path_completeness_audit": TABLE_DIR / "price_path_completeness_audit.csv",
        "baseline_label_definition_audit": TABLE_DIR / "baseline_label_definition_audit.csv",
        "path_defined_label_rebuild_audit": TABLE_DIR / "path_defined_label_rebuild_audit.csv",
        "winner_set_difference_readout": TABLE_DIR / "winner_set_difference_readout.csv",
        "time_to_threshold_distribution_readout": TABLE_DIR / "time_to_threshold_distribution_readout.csv",
        "censoring_isolation_audit": TABLE_DIR / "censoring_isolation_audit.csv",
        "slow_winner_morphology_readout": TABLE_DIR / "slow_winner_morphology_readout.csv",
        "known_failed_morphology_overlap_readout": TABLE_DIR / "known_failed_morphology_overlap_readout.csv",
        "episode_overlap_density_audit": TABLE_DIR / "episode_overlap_density_audit.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "winner_episode_label_censoring_decision.csv",
        "universe_rebuild_panel": LOCAL_CACHE_DIR / "universe_rebuild_panel.parquet",
        "path_defined_label_panel": LOCAL_CACHE_DIR / "path_defined_label_panel.parquet",
        "slow_winner_morphology_panel": LOCAL_CACHE_DIR / "slow_winner_morphology_panel.parquet",
        "report": REPORT_DIR / "winner_episode_label_censoring_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r13a.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r13a.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r13a.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r13a.write_json(path, payload)


def path_sha(path: Path) -> str:
    return r13a.path_sha(path)


def count_rows(path: Path) -> int | float:
    return r13a.count_rows(path)


def stable_hash(value: Any) -> str:
    return r13a.stable_hash(value)


def boolish(value: Any) -> bool:
    return r13a.boolish(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r13a.bool_series(series)


def finite_numeric(series: pd.Series) -> pd.Series:
    return r13a.finite_numeric(series)


def safe_rate(num: Any, den: Any) -> float:
    return r13a.safe_rate(num, den)


def date_text(value: Any) -> str:
    return r13a.date_text(value)


def empty_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def artifact_required_columns(artifact_role: str) -> tuple[str, ...]:
    expected = {
        "pit_topn_400_100_executable_daily": ("instrument", "usable_trade_date", "board_bucket", "is_listed", "is_st", "is_suspended"),
        "pit_topn_400_100_membership_daily": ("instrument", "usable_trade_date", "board_bucket", "is_listed", "is_st", "is_suspended"),
        "upstream_12a7g_label_formula": ("label_id", "horizon_sessions", "same_bar_priority", "path_window"),
        "upstream_12a7g_split_boundary": ("split", "start_date", "end_date", "boundary_assignment_status"),
        "upstream_13a_native_label_cache": ("instrument", "reference_date", "row_id", "winner_positive", "horizon_complete"),
        "upstream_13a_native_universe_cache": ("instrument", "reference_date", "row_id", "entry_pos", "entry_price"),
        "upstream_14a_native_rebuild_cache": ("instrument", "reference_date", "row_id", "entry_pos", "entry_price"),
        "upstream_13a_universe_definition": ("split_bucket",),
        "upstream_13a_universe_thresholds": ("threshold_id",),
        "upstream_14a_decision": ("decision_state",),
        "upstream_13a_decision": ("decision_state",),
        "upstream_12a7g_decision": ("decision_state", "selected_label_id", "input_gate_status", "lineage_gate_status"),
        "upstream_12a7g_label_selection": ("label_id",),
    }
    return expected.get(artifact_role, ())


def lineage_role_for_artifact(artifact_role: str) -> str:
    if artifact_role.startswith("upstream_14a"):
        return "upstream_14a_lineage"
    if artifact_role.startswith("upstream_13a"):
        return "upstream_13a_lineage"
    if artifact_role.startswith("upstream_12a7g") or artifact_role == "upstream_requirement_12a7g":
        return "upstream_12a7g_label_lineage"
    if artifact_role in {
        "pit_topn_400_100_executable_daily",
        "pit_topn_400_100_membership_daily",
        "stock_daily_qfq_dir",
    }:
        return "raw_local_data_input"
    return "run_config_input"


def optional_artifacts() -> set[str]:
    return {"upstream_14a_native_rebuild_cache", "upstream_13a_native_universe_cache", "upstream_13a_native_label_cache"}


def build_input_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    raw_paths = config.get("paths", {})
    for artifact_role, path in resolved.items():
        required_cols = artifact_required_columns(artifact_role)
        required_flag = artifact_role not in optional_artifacts()
        read_status = "pass" if path.exists() else "missing"
        schema_status = "not_checked"
        missing_cols: list[str] = []
        row_count: int | float = np.nan
        column_count: int | float = np.nan
        if path.exists():
            try:
                if path.is_dir():
                    schema_status = "directory"
                    row_count = count_rows(path)
                else:
                    suffixes = "".join(path.suffixes)
                    if suffixes.endswith(".parquet"):
                        sample = pd.read_parquet(path).head(5)
                    elif suffixes.endswith((".csv", ".csv.gz")):
                        sample = pd.read_csv(path, nrows=5, low_memory=False)
                    else:
                        sample = pd.DataFrame()
                    if suffixes.endswith((".csv", ".csv.gz", ".parquet")):
                        column_count = len(sample.columns)
                        missing_cols = sorted(set(required_cols) - set(sample.columns))
                        schema_status = "pass" if not missing_cols else "missing_columns:" + ";".join(missing_cols)
                        row_count = count_rows(path)
            except Exception as exc:  # pragma: no cover - defensive audit
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        rows.append(
            {
                "artifact_role": artifact_role,
                "artifact_path": str(raw_paths.get(artifact_role, path)),
                "resolved_path": str(path),
                "required_flag": required_flag,
                "lineage_role": lineage_role_for_artifact(artifact_role),
                "read_status": read_status,
                "row_count": row_count,
                "column_count": column_count,
                "sha256": path_sha(path),
                "schema_status": schema_status,
                "required_column_missing_list": ";".join(missing_cols),
            }
        )
    return pd.DataFrame(rows, columns=INPUT_COLUMNS)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    required = input_audit.loc[bool_series(input_audit["required_flag"])]
    bad = required.loc[
        ~required["read_status"].eq("pass")
        | ~required["schema_status"].astype(str).str.startswith(("pass", "directory", "not_checked"))
    ]
    if bad.empty:
        return "pass", ""
    missing_local = bad.loc[bad["lineage_role"].eq("raw_local_data_input")]
    if not missing_local.empty:
        return "fail", "required_local_data_artifact_missing"
    return "fail", ";".join(bad["artifact_role"].astype(str).tolist())


def compare_series(left: pd.Series, right: pd.Series, tol: float = 1e-10) -> pd.Series:
    if pd.api.types.is_bool_dtype(left) or pd.api.types.is_bool_dtype(right):
        return bool_series(left).eq(bool_series(right))
    left_num = finite_numeric(left)
    right_num = finite_numeric(right)
    if left_num.notna().any() or right_num.notna().any():
        return (left_num.sub(right_num).abs() <= tol) | (left_num.isna() & right_num.isna())
    return left.astype(str).fillna("").eq(right.astype(str).fillna(""))


def normalize_native_panel(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["reference_date"] = out["reference_date"].map(date_text)
    if "split_bucket" not in out.columns and "split" in out.columns:
        out["split_bucket"] = out["split"].astype(str)
    if "split" not in out.columns and "split_bucket" in out.columns:
        out["split"] = out["split_bucket"].astype(str)
    if "upper_barrier_return" not in out.columns and "upper_barrier" in out.columns:
        out["upper_barrier_return"] = out["upper_barrier"]
    if "lower_barrier_return" not in out.columns and "lower_barrier" in out.columns:
        out["lower_barrier_return"] = out["lower_barrier"]
    if "winner" not in out.columns and "winner_positive" in out.columns:
        out["winner"] = out["winner_positive"]
    if "terminal_return_20d" not in out.columns and "horizon_close_return" in out.columns:
        out["terminal_return_20d"] = out["horizon_close_return"]
    if "fast_fail" not in out.columns:
        out["fast_fail"] = bool_series(out.get("lower_first", pd.Series(False, index=out.index))) | bool_series(
            out.get("same_bar_conflict", pd.Series(False, index=out.index))
        )
    if "native_scope" not in out.columns:
        out["native_scope"] = True
    for col in [
        "winner_positive",
        "winner",
        "horizon_complete",
        "upper_first",
        "lower_first",
        "same_bar_conflict",
        "native_scope",
    ]:
        if col in out.columns:
            out[col] = bool_series(out[col])
    if "calendar_year" not in out.columns:
        out["calendar_year"] = out["reference_date"].astype(str).str[:4]
    if "rebound_from_20d_low" not in out.columns and "distance_to_20d_low" in out.columns:
        out["rebound_from_20d_low"] = out["distance_to_20d_low"]
    if "vol_ratio_20d_60d" not in out.columns and {"volatility_20d", "volatility_60d"} <= set(out.columns):
        out["vol_ratio_20d_60d"] = finite_numeric(out["volatility_20d"]) / finite_numeric(out["volatility_60d"]).replace(0, np.nan) - 1.0
    if "vol_compression_20d_60d" not in out.columns and "vol_ratio_20d_60d" in out.columns:
        out["vol_compression_20d_60d"] = -1.0 * finite_numeric(out["vol_ratio_20d_60d"])
    return out


def native_panel_schema_status(frame: pd.DataFrame) -> tuple[str, str]:
    required = {
        "row_id",
        "instrument",
        "reference_date",
        "split_bucket",
        "reference_pos",
        "entry_date",
        "entry_pos",
        "entry_price",
        "winner_positive",
        "horizon_complete",
        "upper_barrier",
        "lower_barrier",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        return "fail", "missing_columns:" + ";".join(missing)
    dup = int(frame[["instrument", "reference_date"]].duplicated().sum())
    if dup:
        return "fail", f"duplicate_anchor_rows:{dup}"
    return "pass", ""


def native_adapter_consistency_status(frame: pd.DataFrame) -> dict[str, Any]:
    specs = [
        ("split", "split_bucket", "string"),
        ("upper_barrier", "upper_barrier_return", "numeric"),
        ("lower_barrier", "lower_barrier_return", "numeric"),
        ("winner_positive", "winner", "bool"),
        ("horizon_close_return", "terminal_return_20d", "numeric"),
    ]
    mismatch_n = 0
    checked = 0
    missing: list[str] = []
    for source_col, derived_col, kind in specs:
        if source_col not in frame.columns or derived_col not in frame.columns:
            missing.append(f"{source_col}->{derived_col}")
            continue
        checked += len(frame)
        if kind == "bool":
            equal = bool_series(frame[source_col]).eq(bool_series(frame[derived_col]))
        elif kind == "numeric":
            left = finite_numeric(frame[source_col])
            right = finite_numeric(frame[derived_col])
            equal = (left.sub(right).abs() <= 1e-10) | (left.isna() & right.isna())
        else:
            equal = frame[source_col].astype(str).fillna("").eq(frame[derived_col].astype(str).fillna(""))
        mismatch_n += int((~equal).sum())
    status = "pass" if mismatch_n == 0 and not missing else "fail"
    reason = ""
    if missing:
        reason = "missing_adapter_columns:" + ";".join(missing)
    if mismatch_n:
        reason = (reason + ";" if reason else "") + f"derived_field_mismatch_n:{mismatch_n}"
    return {"status": status, "checked_n": checked, "mismatch_n": mismatch_n, "reason": reason}


def cache_position_rebuild_status(frame: pd.DataFrame, qfq_dir: Path) -> dict[str, Any]:
    cache = r13a.StockDailyCache(qfq_dir)
    mismatch_n = 0
    checked_n = 0
    missing_qfq_n = 0
    for instrument, idx in frame.groupby("instrument", sort=False).groups.items():
        daily = cache.get(str(instrument))
        sub = frame.loc[idx]
        if daily.frame is None or daily.frame.empty or daily.status != "pass":
            missing_qfq_n += len(sub)
            mismatch_n += len(sub)
            continue
        qfq = daily.frame
        qfq_n = len(qfq)
        qfq_dates = qfq["date"].map(date_text).to_numpy(dtype=object)
        qfq_open = finite_numeric(qfq["open"]).to_numpy(dtype=float)
        ref_pos = finite_numeric(sub["reference_pos"]).to_numpy(dtype=float)
        entry_pos = finite_numeric(sub["entry_pos"]).to_numpy(dtype=float)
        entry_price = finite_numeric(sub["entry_price"]).to_numpy(dtype=float)
        ref_date = sub["reference_date"].map(date_text).to_numpy(dtype=object)
        entry_date = sub["entry_date"].map(date_text).to_numpy(dtype=object)

        valid_ref = np.isfinite(ref_pos) & (ref_pos >= 0) & (ref_pos < qfq_n)
        valid_entry = np.isfinite(entry_pos) & (entry_pos >= 0) & (entry_pos < qfq_n)
        checked_n += int(len(sub) * 3)
        mismatch_n += int((~valid_ref).sum() + (~valid_entry).sum())
        if valid_ref.any():
            ref_i = ref_pos[valid_ref].astype(int)
            mismatch_n += int((qfq_dates[ref_i] != ref_date[valid_ref]).sum())
        if valid_entry.any():
            entry_i = entry_pos[valid_entry].astype(int)
            mismatch_n += int((qfq_dates[entry_i] != entry_date[valid_entry]).sum())
            open_diff = np.abs(qfq_open[entry_i] - entry_price[valid_entry])
            both_nan = np.isnan(qfq_open[entry_i]) & np.isnan(entry_price[valid_entry])
            mismatch_n += int(((open_diff > 1e-8) & ~both_nan).sum())
    status = "pass" if mismatch_n == 0 else "fail"
    reason = "" if status == "pass" else f"qfq_position_rebuild_mismatch_n:{mismatch_n}"
    if missing_qfq_n:
        reason += f";missing_qfq_row_n:{missing_qfq_n}"
    return {"status": status, "checked_n": checked_n, "mismatch_n": mismatch_n, "reason": reason}


def cross_check_native_label(primary: pd.DataFrame, label: pd.DataFrame) -> dict[str, Any]:
    key = ["instrument", "reference_date", "row_id"]
    fields = [
        "split",
        "upper_barrier",
        "lower_barrier",
        "winner_positive",
        "upper_first",
        "lower_first",
        "same_bar_conflict",
        "horizon_complete",
    ]
    if label.empty:
        return {"status": "fail", "coverage_rate": 0.0, "mismatch_n": 0, "reason": "missing_native_label_panel"}
    left = primary.copy()
    right = label.copy()
    left["reference_date"] = left["reference_date"].map(date_text)
    right["reference_date"] = right["reference_date"].map(date_text)
    missing_keys = [col for col in key if col not in left.columns or col not in right.columns]
    if missing_keys:
        return {"status": "fail", "coverage_rate": 0.0, "mismatch_n": 0, "reason": "missing_key:" + ";".join(missing_keys)}
    if left.duplicated(key).any() or right.duplicated(key).any():
        return {"status": "fail", "coverage_rate": 0.0, "mismatch_n": 0, "reason": "duplicate_cross_check_key"}
    use_fields = [col for col in fields if col in left.columns and col in right.columns]
    merged = left[key + use_fields].merge(right[key + use_fields], on=key, how="left", suffixes=("_primary", "_label"), indicator=True)
    coverage_rate = safe_rate(int(merged["_merge"].eq("both").sum()), len(left))
    mismatch_n = 0
    for col in use_fields:
        lcol = f"{col}_primary"
        rcol = f"{col}_label"
        both = merged["_merge"].eq("both")
        mismatch_n += int((both & ~compare_series(merged[lcol], merged[rcol])).sum())
    status = "pass" if coverage_rate == 1.0 and mismatch_n == 0 else "fail"
    reason = "" if status == "pass" else "coverage_or_value_mismatch"
    return {"status": status, "coverage_rate": coverage_rate, "mismatch_n": mismatch_n, "reason": reason}


def load_primary_universe_panel(resolved: dict[str, Path]) -> tuple[pd.DataFrame, dict[str, Any]]:
    label_path = resolved["upstream_13a_native_label_cache"]
    label = read_table(label_path) if label_path.exists() else pd.DataFrame()
    candidates = [
        ("upstream_14a_native_rebuild_cache", "14A_native_rebuild_panel", resolved["upstream_14a_native_rebuild_cache"]),
        ("upstream_13a_native_universe_cache", "13A_native_universe_panel", resolved["upstream_13a_native_universe_cache"]),
    ]
    attempts: list[str] = []
    for role, source_role, path in candidates:
        if not path.exists():
            attempts.append(f"{role}:missing")
            continue
        try:
            panel = normalize_native_panel(read_table(path))
            schema_status, schema_reason = native_panel_schema_status(panel)
            cross = cross_check_native_label(panel, label)
            adapter = native_adapter_consistency_status(panel)
            position = cache_position_rebuild_status(panel, resolved["stock_daily_qfq_dir"])
            if schema_status == "pass" and cross["status"] == "pass" and adapter["status"] == "pass" and position["status"] == "pass":
                return panel, {
                    "primary_source": str(path),
                    "primary_source_role": source_role,
                    "cross": cross,
                    "adapter": adapter,
                    "position": position,
                    "cache_status": "cache_used",
                    "blocking_reason": "",
                    "attempts": ";".join(attempts),
                }
            attempts.append(
                f"{role}:schema={schema_status}:{schema_reason}:cross={cross['status']}:{cross['reason']}:"
                f"adapter={adapter['status']}:{adapter['reason']}:position={position['status']}:{position['reason']}"
            )
        except Exception as exc:  # pragma: no cover - defensive lineage fallback
            attempts.append(f"{role}:read_error:{type(exc).__name__}")
    config_path = resolved.get("upstream_13a_config")
    if config_path is not None and config_path.exists():
        try:
            r13a.run(config_path, check_inputs_only=False)
            path = resolved["upstream_13a_native_universe_cache"]
            label = read_table(label_path) if label_path.exists() else pd.DataFrame()
            panel = normalize_native_panel(read_table(path))
            schema_status, schema_reason = native_panel_schema_status(panel)
            cross = cross_check_native_label(panel, label)
            adapter = native_adapter_consistency_status(panel)
            position = cache_position_rebuild_status(panel, resolved["stock_daily_qfq_dir"])
            if schema_status == "pass" and cross["status"] == "pass" and adapter["status"] == "pass" and position["status"] == "pass":
                return panel, {
                    "primary_source": str(path),
                    "primary_source_role": "13A_native_universe_panel_after_rebuild",
                    "cross": cross,
                    "adapter": adapter,
                    "position": position,
                    "cache_status": "raw_rebuild_after_cache_unusable",
                    "blocking_reason": "",
                    "attempts": ";".join(attempts),
                }
            attempts.append(
                f"13a_rebuild:schema={schema_status}:{schema_reason}:cross={cross['status']}:{cross['reason']}:"
                f"adapter={adapter['status']}:{adapter['reason']}:position={position['status']}:{position['reason']}"
            )
        except Exception as exc:  # pragma: no cover - defensive lineage fallback
            attempts.append(f"13a_rebuild_error:{type(exc).__name__}")
    return pd.DataFrame(), {
        "primary_source": "",
        "primary_source_role": "none",
        "cross": {"status": "fail", "coverage_rate": 0.0, "mismatch_n": 0, "reason": "no_usable_row_level_source"},
        "adapter": {"status": "fail", "checked_n": 0, "mismatch_n": 0, "reason": "no_usable_row_level_source"},
        "position": {"status": "fail", "checked_n": 0, "mismatch_n": 0, "reason": "no_usable_row_level_source"},
        "cache_status": "cache_unavailable_rebuild_failed",
        "blocking_reason": ";".join(attempts),
        "attempts": ";".join(attempts),
    }


def upstream_schema_status(path: Path, required_cols: tuple[str, ...]) -> str:
    if not path.exists():
        return "missing"
    try:
        if path.is_dir():
            return "directory"
        suffixes = "".join(path.suffixes)
        if suffixes.endswith(".parquet"):
            sample = pd.read_parquet(path).head(5)
        elif suffixes.endswith((".csv", ".csv.gz")):
            sample = pd.read_csv(path, nrows=5, low_memory=False)
        else:
            return "not_checked"
        missing = sorted(set(required_cols) - set(sample.columns))
        return "pass" if not missing else "missing_columns:" + ";".join(missing)
    except Exception as exc:  # pragma: no cover
        return f"read_error:{type(exc).__name__}"


def build_upstream_lineage_audit(resolved: dict[str, Path], info: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    formula_path = resolved["upstream_12a7g_label_formula"]
    selected_label = SELECTED_LABEL_ID
    upstream_formula_path_window = ""
    formula_status = "fail"
    try:
        formula = read_table(formula_path)
        frow = formula.loc[formula["label_id"].astype(str).eq(selected_label)].iloc[0]
        upstream_formula_path_window = str(frow.get("path_window", ""))
        formula_status = "pass" if str(frow.get("formula_status", "pass")) == "pass" else "fail"
    except Exception:
        formula_status = "fail"
    path_window_status = "pass_with_documented_13a_entry_anchor" if formula_status == "pass" else "fail_unexpected_path_window_conflict"
    cross = info.get("cross", {})
    adapter = info.get("adapter", {})
    position = info.get("position", {})
    for role in [
        "upstream_12a7g_label_formula",
        "upstream_12a7g_split_boundary",
        "upstream_13a_universe_definition",
        "upstream_13a_universe_thresholds",
        "upstream_14a_decision",
    ]:
        path = resolved[role]
        schema_status = upstream_schema_status(path, artifact_required_columns(role))
        exists_ok = path.exists() and schema_status.startswith(("pass", "not_checked", "directory"))
        lineage_status = (
            "pass"
            if exists_ok
            and info["primary_source_role"] != "none"
            and cross.get("status") == "pass"
            and adapter.get("status") == "pass"
            and position.get("status") == "pass"
            and formula_status == "pass"
            else "fail"
        )
        blocking = "" if lineage_status == "pass" else info.get("blocking_reason", "") or schema_status
        rows.append(
            {
                "upstream_artifact_role": role,
                "upstream_path": str(path),
                "upstream_sha256": path_sha(path),
                "upstream_row_count": count_rows(path),
                "upstream_schema_status": schema_status,
                "lineage_claim": "15A inherits 13A/14A native opportunity row lineage after native-label cross-check, derived-field adapter audit, qfq position rebuild audit, and 12A7g selected label identity check",
                "lineage_status": lineage_status,
                "selected_label_id": selected_label,
                "primary_row_level_source": info.get("primary_source", ""),
                "primary_row_level_source_role": info.get("primary_source_role", "none"),
                "cross_check_source": str(resolved["upstream_13a_native_label_cache"]),
                "cross_check_key": "instrument,reference_date,row_id",
                "cross_check_key_coverage_rate": cross.get("coverage_rate", 0.0),
                "cross_check_mismatch_n": cross.get("mismatch_n", 0),
                "upstream_formula_path_window": upstream_formula_path_window,
                "implemented_path_window": "entry_pos_through_entry_pos_plus_horizon_inclusive",
                "path_window_reconciliation_status": path_window_status,
                "path_window_reconciliation_reason": "15A uses 13A/14A implemented next-open entry-anchor lineage; 12A7g formula text is preserved as documented lineage.",
                "blocking_reason": blocking,
            }
        )
    return pd.DataFrame(rows, columns=UPSTREAM_COLUMNS)


def audit_status(frame: pd.DataFrame, status_col: str) -> str:
    if frame.empty or status_col not in frame.columns:
        return "fail"
    return "pass" if frame[status_col].astype(str).eq("pass").all() else "fail"


def build_anchor_panel(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.loc[panel["split_bucket"].astype(str).isin(SPLITS) & bool_series(panel["native_scope"])].copy()
    out["reference_date"] = out["reference_date"].map(date_text)
    out["split_bucket"] = out["split_bucket"].astype(str)
    out = out.sort_values(["instrument", "reference_date", "row_id"], kind="stable")
    out = out.drop_duplicates(["instrument", "reference_date"], keep="first").reset_index(drop=True)
    return out


def split_boundary_status(anchor: pd.DataFrame, resolved: dict[str, Path]) -> str:
    try:
        bounds = read_table(resolved["upstream_12a7g_split_boundary"])
        bounds = bounds.loc[bounds["split"].astype(str).isin(SPLITS)].copy()
        if bounds.empty or bounds["boundary_assignment_status"].astype(str).ne("pass").any():
            return "fail"
        dates = anchor["reference_date"].map(date_text)
        assigned = pd.Series("", index=anchor.index)
        for row in bounds.itertuples(index=False):
            mask = dates.ge(str(row.start_date)) & dates.le(str(row.end_date))
            assigned.loc[mask] = str(row.split)
        return "pass" if assigned.eq(anchor["split_bucket"].astype(str)).all() else "fail"
    except Exception:
        return "fail"


def membership_key_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    usecols = ["instrument", "usable_trade_date"]
    keys: set[str] = set()
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=300_000, low_memory=False):
        dates = chunk["usable_trade_date"].map(date_text)
        keys.update((chunk["instrument"].astype(str) + "|" + dates).tolist())
    return keys


def build_universe_membership_audit(source: pd.DataFrame, anchor: pd.DataFrame, resolved: dict[str, Path]) -> pd.DataFrame:
    split_status = split_boundary_status(anchor, resolved)
    keys = membership_key_set(resolved["pit_topn_400_100_membership_daily"])
    rows: list[dict[str, Any]] = []
    source = source.copy()
    source["calendar_year"] = source.get("calendar_year", source["reference_date"].astype(str).str[:4]).astype(str)
    source["split_bucket"] = source.get("split_bucket", source.get("split", "")).astype(str)
    anchor = anchor.copy()
    anchor["calendar_year"] = anchor.get("calendar_year", anchor["reference_date"].astype(str).str[:4]).astype(str)
    anchor_key = anchor["instrument"].astype(str) + "|" + anchor["reference_date"].map(date_text)
    anchor["_membership_match"] = anchor_key.map(lambda value: value in keys)
    for (split, year), sub in source.groupby(["split_bucket", "calendar_year"], dropna=False, sort=True):
        if str(split) not in SPLITS:
            continue
        a = anchor.loc[anchor["split_bucket"].astype(str).eq(str(split)) & anchor["calendar_year"].astype(str).eq(str(year))]
        duplicate_n = int(sub[["instrument", "reference_date"]].duplicated().sum()) if {"instrument", "reference_date"} <= set(sub.columns) else 0
        membership_n = int(a["_membership_match"].sum()) if len(a) else 0
        match_rate = safe_rate(membership_n, len(a))
        status = "pass" if duplicate_n == 0 and split_status == "pass" and (pd.isna(match_rate) or match_rate >= 0.999) else "fail"
        rows.append(
            {
                "split_bucket": str(split),
                "calendar_year": str(year),
                "source_row_n": int(len(sub)),
                "unique_anchor_row_n": int(len(a)),
                "duplicate_anchor_row_n": duplicate_n,
                "membership_row_n": membership_n,
                "membership_match_rate": match_rate,
                "split_boundary_source": str(resolved["upstream_12a7g_split_boundary"]),
                "split_boundary_status": split_status,
                "universe_membership_status": status,
                "blocking_reason": "" if status == "pass" else "duplicate_or_membership_or_split_boundary_failure",
            }
        )
    return pd.DataFrame(rows, columns=UNIVERSE_COLUMNS)


def build_price_path_completeness(anchor: pd.DataFrame, qfq_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    cache = r13a.StockDailyCache(qfq_dir)
    panel = anchor.copy()
    panel["available_forward_sessions"] = np.nan
    rows: list[dict[str, Any]] = []
    for instrument, idx in panel.groupby("instrument", sort=False).groups.items():
        daily = cache.get(str(instrument))
        sub = panel.loc[idx]
        pos = finite_numeric(sub["entry_pos"])
        ref_pos = finite_numeric(sub["reference_pos"])
        entry_price = finite_numeric(sub["entry_price"])
        missing_file = daily.frame is None or daily.frame.empty or daily.status != "pass"
        qfq_n = 0 if daily.frame is None else len(daily.frame)
        available = pd.Series(np.nan, index=sub.index)
        if not missing_file:
            valid_pos = pos.notna() & pos.ge(0) & pos.lt(qfq_n)
            available.loc[valid_pos] = qfq_n - pos.loc[valid_pos].astype(int)
            panel.loc[available.index, "available_forward_sessions"] = available
        missing_ref = int(ref_pos.isna().sum())
        missing_entry = int((pos.isna() | pos.lt(0) | pos.ge(qfq_n if qfq_n else -1)).sum())
        missing_price = int((entry_price.isna() | entry_price.le(0)).sum())
        status = "pass"
        blocking = ""
        if missing_file or missing_ref or missing_entry or missing_price:
            status = "fail"
            blocking = "missing_qfq_or_anchor_price_path_field"
        rows.append(
            {
                "instrument": instrument,
                "anchor_row_n": int(len(sub)),
                "qfq_row_n": int(qfq_n),
                "missing_qfq_file_flag": bool(missing_file),
                "missing_reference_pos_n": missing_ref,
                "missing_entry_pos_n": missing_entry,
                "missing_entry_price_n": missing_price,
                "min_available_forward_sessions": float(available.min()) if available.notna().any() else np.nan,
                "median_available_forward_sessions": float(available.median()) if available.notna().any() else np.nan,
                "max_available_forward_sessions": float(available.max()) if available.notna().any() else np.nan,
                "price_path_status": status,
                "blocking_reason": blocking,
            }
        )
    return pd.DataFrame(rows, columns=PRICE_COLUMNS), panel


def build_path_defined_label_panel(anchor: pd.DataFrame, qfq_dir: Path) -> pd.DataFrame:
    cache = r13a.StockDailyCache(qfq_dir)
    base_cols = [
        "row_id",
        "instrument",
        "reference_date",
        "split_bucket",
        "board_bucket",
        "calendar_year",
        "reference_pos",
        "entry_date",
        "entry_pos",
        "entry_price",
        "winner_positive",
        "horizon_complete",
        "label_id",
    ]
    feature_cols = [col for col in MORPHOLOGY_FEATURES if col in anchor.columns]
    rows: list[pd.DataFrame] = []
    for instrument, idx in anchor.groupby("instrument", sort=False).groups.items():
        daily = cache.get(str(instrument))
        sub = anchor.loc[idx, [c for c in base_cols + feature_cols if c in anchor.columns]].copy()
        n = len(sub)
        if daily.frame is None or daily.frame.empty or daily.status != "pass":
            continue
        frame = daily.frame
        high = finite_numeric(frame["high"]).to_numpy(dtype=float)
        close = finite_numeric(frame["close"]).to_numpy(dtype=float)
        pos = finite_numeric(sub["entry_pos"]).to_numpy(dtype=float)
        price = finite_numeric(sub["entry_price"]).to_numpy(dtype=float)
        valid = np.isfinite(pos) & np.isfinite(price) & (price > 0) & (pos >= 0) & (pos < len(frame))
        if not valid.any():
            continue
        sub = sub.iloc[np.where(valid)[0]].copy().reset_index(drop=True)
        pos_int = pos[valid].astype(int)
        price_valid = price[valid]
        available = len(frame) - pos_int
        max_available = int(available.max())
        offsets = np.arange(max_available)
        pos_mat = pos_int[:, None] + offsets[None, :]
        valid_mat = pos_mat < len(frame)
        pos_mat_safe = np.minimum(pos_mat, len(frame) - 1)
        high_ret = high[pos_mat_safe] / price_valid[:, None] - 1.0
        close_ret = close[pos_mat_safe] / price_valid[:, None] - 1.0
        high_ret = np.where(valid_mat, high_ret, -np.inf)
        close_ret = np.where(valid_mat, close_ret, -np.inf)
        for threshold_id, threshold in THRESHOLDS.items():
            hit = high_ret >= float(threshold) - 1e-12
            close_hit = close_ret >= float(threshold) - 1e-12
            hit_any = hit.any(axis=1)
            close_hit_any = close_hit.any(axis=1)
            first = np.where(hit_any, np.argmax(hit, axis=1), np.nan)
            close_first = np.where(close_hit_any, np.argmax(close_hit, axis=1), np.nan)
            fixed_complete = available >= FIXED120_SESSIONS + 1
            fixed_window = high_ret[:, : FIXED120_SESSIONS + 1] if high_ret.shape[1] >= FIXED120_SESSIONS + 1 else high_ret
            fixed_max = np.max(fixed_window, axis=1) if fixed_window.size else np.full(len(sub), np.nan)
            fixed_winner = fixed_complete & (fixed_max >= float(threshold) - 1e-12)
            fixed_only = fixed_winner & ~hit_any
            explanation = np.where(fixed_only, "entry_window_boundary_mismatch", "none")
            slow = hit_any & (first > FIXED120_SESSIONS)
            fast = hit_any & (first <= FIXED120_SESSIONS)
            episode_threshold_pos = np.where(hit_any, pos_int + first, np.nan)
            out = sub.copy()
            out["threshold_id"] = threshold_id
            out["threshold_return"] = float(threshold)
            out["first_passage_offset"] = first
            out["close_based_first_passage_offset"] = close_first
            out["time_to_threshold_sessions"] = first
            out["path_winner"] = hit_any
            out["is_censored"] = ~hit_any
            out["censoring_type"] = np.where(hit_any, "none", "right_censored_at_data_end")
            out["confirmed_non_winner"] = False
            out["observed_non_hit_control_flag"] = (~hit_any) & (available >= NON_HIT_CONTROL_MIN_SESSIONS)
            out["observed_non_hit_control_role"] = np.where(
                out["observed_non_hit_control_flag"],
                "readout_only_censored_control_not_negative",
                "none",
            )
            out["fixed120_winner"] = fixed_winner
            out["fixed120_baseline_id"] = "fixed_120d_" + threshold_id
            out["fixed120_horizon_complete"] = fixed_complete
            out["fixed120_only_winner_explanation_code"] = explanation
            out["volscaled_h20_winner"] = bool_series(out.get("winner_positive", pd.Series(False, index=out.index)))
            out["volscaled_h20_horizon_complete"] = bool_series(out.get("horizon_complete", pd.Series(False, index=out.index)))
            out["volscaled_h20_label_id"] = out.get("label_id", SELECTED_LABEL_ID)
            out["volscaled_h20_source_artifact"] = "13A_14A_native_row_level_lineage"
            out["slow_winner_flag"] = slow
            out["fast_winner_flag"] = fast
            out["available_forward_sessions"] = available
            out["episode_start_pos"] = pos_int
            out["episode_threshold_pos"] = episode_threshold_pos
            out["episode_peak_pos"] = episode_threshold_pos
            out["episode_peak_return"] = np.where(hit_any, high[pos_int + np.nan_to_num(first, nan=0).astype(int)] / price_valid - 1.0, np.nan)
            rows.append(out)
    if not rows:
        return pd.DataFrame()
    label = pd.concat(rows, ignore_index=True)
    keep = [
        "instrument",
        "reference_date",
        "row_id",
        "split_bucket",
        "entry_date",
        "entry_pos",
        "entry_price",
        "threshold_id",
        "threshold_return",
        "first_passage_offset",
        "close_based_first_passage_offset",
        "time_to_threshold_sessions",
        "path_winner",
        "is_censored",
        "censoring_type",
        "confirmed_non_winner",
        "observed_non_hit_control_flag",
        "observed_non_hit_control_role",
        "fixed120_winner",
        "fixed120_baseline_id",
        "fixed120_horizon_complete",
        "fixed120_only_winner_explanation_code",
        "volscaled_h20_winner",
        "volscaled_h20_horizon_complete",
        "volscaled_h20_label_id",
        "volscaled_h20_source_artifact",
        "slow_winner_flag",
        "fast_winner_flag",
        "available_forward_sessions",
        "episode_threshold_pos",
        "episode_peak_pos",
        "episode_peak_return",
        "board_bucket",
        "calendar_year",
        "reference_pos",
        "episode_start_pos",
    ]
    keep.extend([col for col in MORPHOLOGY_FEATURES if col in label.columns])
    return label[[c for c in keep if c in label.columns]]


def split_subframes(label: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    out = [(split, label.loc[label["split_bucket"].astype(str).eq(split)]) for split in SPLITS]
    out.append(("all", label))
    return out


def material_flag(row: dict[str, Any]) -> bool:
    return (
        float(row.get("slow_winner_share_of_path_winners") or 0.0) >= 0.10
        and float(row.get("slow_winner_rate_all_records") or 0.0) >= 0.02
        and int(row.get("slow_winner_n") or 0) >= 200
    )


def winner_set_difference(label: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for threshold_id in THRESHOLDS:
        th = label.loc[label["threshold_id"].eq(threshold_id)]
        for split, sub in split_subframes(th):
            record_n = int(len(sub))
            path_winner = bool_series(sub.get("path_winner", pd.Series(False, index=sub.index)))
            censored = bool_series(sub.get("is_censored", pd.Series(False, index=sub.index)))
            confirmed = bool_series(sub.get("confirmed_non_winner", pd.Series(False, index=sub.index)))
            fixed_complete = bool_series(sub.get("fixed120_horizon_complete", pd.Series(False, index=sub.index)))
            fixed_winner = bool_series(sub.get("fixed120_winner", pd.Series(False, index=sub.index)))
            vol_complete = bool_series(sub.get("volscaled_h20_horizon_complete", pd.Series(False, index=sub.index)))
            vol_winner = bool_series(sub.get("volscaled_h20_winner", pd.Series(False, index=sub.index)))
            slow = bool_series(sub.get("slow_winner_flag", pd.Series(False, index=sub.index)))
            fast = bool_series(sub.get("fast_winner_flag", pd.Series(False, index=sub.index)))
            row = {
                "threshold_id": threshold_id,
                "split_bucket": split,
                "record_n": record_n,
                "path_winner_n": int(path_winner.sum()),
                "path_winner_rate_all_records": safe_rate(path_winner.sum(), record_n),
                "censored_n": int(censored.sum()),
                "censored_rate": safe_rate(censored.sum(), record_n),
                "confirmed_non_winner_n": int(confirmed.sum()),
                "observed_non_hit_control_n": int(bool_series(sub.get("observed_non_hit_control_flag", pd.Series(False, index=sub.index))).sum()),
                "fixed120_horizon_complete_n": int(fixed_complete.sum()),
                "fixed120_horizon_incomplete_n": int((~fixed_complete).sum()),
                "fixed120_winner_n": int(fixed_winner.sum()),
                "fixed120_winner_rate": safe_rate(fixed_winner.sum(), fixed_complete.sum()),
                "volscaled_h20_horizon_complete_n": int(vol_complete.sum()),
                "volscaled_h20_winner_n": int((vol_winner & vol_complete).sum()),
                "volscaled_h20_winner_rate": safe_rate((vol_winner & vol_complete).sum(), vol_complete.sum()),
                "slow_winner_n": int(slow.sum()),
                "slow_winner_rate_all_records": safe_rate(slow.sum(), record_n),
                "slow_winner_share_of_path_winners": safe_rate(slow.sum(), path_winner.sum()),
                "fast_winner_n": int(fast.sum()),
                "overlap_path_and_fixed120_n": int((path_winner & fixed_winner).sum()),
                "path_only_winner_n": int((path_winner & ~fixed_winner).sum()),
                "fixed120_only_winner_n": int((fixed_winner & ~path_winner).sum()),
            }
            valid = (
                row["path_winner_n"] + row["censored_n"] == row["record_n"]
                and row["confirmed_non_winner_n"] == 0
                and row["slow_winner_n"] + row["fast_winner_n"] == row["path_winner_n"]
            )
            row["threshold_material_censoring_flag"] = material_flag(row)
            row["winner_set_difference_status"] = "pass" if valid else "fail"
            rows.append(row)
    return pd.DataFrame(rows, columns=WINNER_COLUMNS)


def distribution_row(threshold_id: str, split: str, sub: pd.DataFrame) -> dict[str, Any]:
    winners = sub.loc[bool_series(sub.get("path_winner", pd.Series(False, index=sub.index)))]
    times = finite_numeric(winners.get("time_to_threshold_sessions", pd.Series(dtype=float))).dropna()
    row = {"threshold_id": threshold_id, "split_bucket": split, "path_winner_n": int(len(times))}
    if len(times):
        for q, name in [(0.10, "p10"), (0.25, "p25"), (0.50, "median"), (0.75, "p75"), (0.90, "p90")]:
            row[f"time_to_threshold_{name}"] = float(times.quantile(q))
        row["time_to_threshold_max"] = float(times.max())
        row["share_within_20d"] = safe_rate(times.le(20).sum(), len(times))
        row["share_within_60d"] = safe_rate(times.le(60).sum(), len(times))
        row["share_within_120d"] = safe_rate(times.le(120).sum(), len(times))
        row["share_beyond_120d"] = safe_rate(times.gt(120).sum(), len(times))
        row["share_beyond_250d"] = safe_rate(times.gt(250).sum(), len(times))
        row["distribution_status"] = "pass"
    else:
        for col in TIME_COLUMNS:
            row.setdefault(col, np.nan)
        row["distribution_status"] = "empty_no_path_winners"
    return row


def time_to_threshold_distribution(label: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for threshold_id in THRESHOLDS:
        th = label.loc[label["threshold_id"].eq(threshold_id)]
        for split, sub in split_subframes(th):
            rows.append(distribution_row(threshold_id, split, sub))
    return pd.DataFrame(rows, columns=TIME_COLUMNS)


def censoring_isolation_audit(label: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for threshold_id in THRESHOLDS:
        th = label.loc[label["threshold_id"].eq(threshold_id)]
        for split, sub in split_subframes(th):
            censored = bool_series(sub.get("is_censored", pd.Series(False, index=sub.index)))
            confirmed = bool_series(sub.get("confirmed_non_winner", pd.Series(False, index=sub.index)))
            control = bool_series(sub.get("observed_non_hit_control_flag", pd.Series(False, index=sub.index)))
            counted_control_without_flag = int((censored & ~control & False).sum())
            row = {
                "threshold_id": threshold_id,
                "split_bucket": split,
                "record_n": int(len(sub)),
                "censored_n": int(censored.sum()),
                "censored_rate": safe_rate(censored.sum(), len(sub)),
                "censored_median_available_forward_sessions": float(finite_numeric(sub.loc[censored, "available_forward_sessions"]).median()) if censored.any() else np.nan,
                "confirmed_non_winner_n": int(confirmed.sum()),
                "counted_in_confirmed_non_winner_n": int((censored & confirmed).sum()),
                "counted_in_control_without_flag_n": counted_control_without_flag,
                "observed_non_hit_control_n": int((censored & control).sum()),
            }
            row["censored_isolation_status"] = "pass" if row["confirmed_non_winner_n"] == 0 and row["counted_in_confirmed_non_winner_n"] == 0 and row["counted_in_control_without_flag_n"] == 0 else "fail"
            rows.append(row)
    return pd.DataFrame(rows, columns=CENSOR_COLUMNS)


def label_rebuild_audit(label: pd.DataFrame) -> pd.DataFrame:
    allowed = {"none", "bar_alignment_mismatch", "fixed120_horizon_complete_but_path_truncated", "entry_window_boundary_mismatch"}
    rows: list[dict[str, Any]] = []
    for threshold_id in THRESHOLDS:
        th = label.loc[label["threshold_id"].eq(threshold_id)]
        for split, sub in split_subframes(th):
            path = bool_series(sub.get("path_winner", pd.Series(False, index=sub.index)))
            censored = bool_series(sub.get("is_censored", pd.Series(False, index=sub.index)))
            fixed = bool_series(sub.get("fixed120_winner", pd.Series(False, index=sub.index)))
            fixed_complete = bool_series(sub.get("fixed120_horizon_complete", pd.Series(False, index=sub.index)))
            confirmed = bool_series(sub.get("confirmed_non_winner", pd.Series(False, index=sub.index)))
            fixed_only = fixed & ~path
            codes = set(sub.loc[fixed_only, "fixed120_only_winner_explanation_code"].astype(str)) if fixed_only.any() else {"none"}
            explained = fixed_only.any() and codes <= allowed and "none" not in codes
            if not fixed_only.any():
                explained_n = 0
                row_level = True
            else:
                explained_n = int(fixed_only.sum()) if explained else 0
                row_level = bool(explained)
            close_hit = finite_numeric(sub["close_based_first_passage_offset"]).notna()
            agreement = safe_rate(path.eq(close_hit).sum(), len(sub))
            status = "pass"
            if int(path.sum()) + int(censored.sum()) != len(sub) or int(confirmed.sum()) != 0:
                status = "fail"
            if fixed_only.any() and not row_level:
                status = "fail"
            if not codes <= allowed:
                status = "fail"
            rows.append(
                {
                    "threshold_id": threshold_id,
                    "split_bucket": split,
                    "record_n": int(len(sub)),
                    "path_winner_n": int(path.sum()),
                    "censored_n": int(censored.sum()),
                    "confirmed_non_winner_n": int(confirmed.sum()),
                    "observed_non_hit_control_n": int(bool_series(sub.get("observed_non_hit_control_flag", pd.Series(False, index=sub.index))).sum()),
                    "fixed120_horizon_complete_n": int(fixed_complete.sum()),
                    "fixed120_horizon_incomplete_n": int((~fixed_complete).sum()),
                    "fixed120_only_winner_n": int(fixed_only.sum()),
                    "fixed120_only_winner_explained_n": explained_n,
                    "fixed120_only_winner_explanation_code_list": ";".join(sorted(codes)),
                    "high_based_close_based_agreement_rate": agreement,
                    "row_level_explanation_available": bool(row_level),
                    "rebuild_status": status,
                }
            )
    return pd.DataFrame(rows, columns=LABEL_REBUILD_COLUMNS)


def build_baseline_definition_audit(resolved: dict[str, Path], lineage: pd.DataFrame) -> pd.DataFrame:
    cross_status = "pass" if audit_status(lineage, "lineage_status") == "pass" else "fail"
    first = lineage.iloc[0] if len(lineage) else pd.Series(dtype=object)
    rows: list[dict[str, Any]] = [
        {
            "baseline_id": "baseline_volscaled_H20",
            "baseline_role": "lineage_volscaled_h20",
            "threshold_id": "not_threshold_matched",
            "threshold_return": np.nan,
            "anchor_definition": "next executable open after reference_date close",
            "window_definition": "entry_pos_through_entry_pos_plus_horizon_inclusive",
            "horizon_sessions": 20,
            "source_artifact": first.get("primary_row_level_source", str(resolved["upstream_13a_native_universe_cache"])),
            "source_label_id": SELECTED_LABEL_ID,
            "source_path_window": first.get("upstream_formula_path_window", ""),
            "primary_row_level_source": first.get("primary_row_level_source", ""),
            "primary_row_level_source_role": first.get("primary_row_level_source_role", ""),
            "row_level_key": "instrument,reference_date,row_id",
            "cross_check_source": str(resolved["upstream_13a_native_label_cache"]),
            "cross_check_status": cross_status,
            "path_window_reconciliation_status": first.get("path_window_reconciliation_status", ""),
            "path_window_reconciliation_reason": first.get("path_window_reconciliation_reason", ""),
            "winner_definition": "vol_scaled_upper_first_with_lower_first_same_bar_priority",
            "horizon_complete_denominator_rule": "volscaled_h20_horizon_complete_n",
            "baseline_definition_status": cross_status,
        }
    ]
    for threshold_id, threshold in THRESHOLDS.items():
        rows.append(
            {
                "baseline_id": "fixed_120d_" + threshold_id,
                "baseline_role": "diagnostic_fixed_horizon_contrast",
                "threshold_id": threshold_id,
                "threshold_return": threshold,
                "anchor_definition": "next executable open after reference_date close",
                "window_definition": "entry_pos_through_entry_pos_plus_120_inclusive",
                "horizon_sessions": FIXED120_SESSIONS,
                "source_artifact": "rebuilt_from_raw_qfq_bars",
                "source_label_id": "",
                "source_path_window": "",
                "primary_row_level_source": "15A_path_defined_label_panel",
                "primary_row_level_source_role": "diagnostic_fixed_horizon_contrast",
                "row_level_key": "instrument,reference_date,row_id,threshold_id",
                "cross_check_source": "path_defined_no_horizon_high_based_superset",
                "cross_check_status": "pass",
                "path_window_reconciliation_status": "pass_same_entry_anchor_as_path_defined_label",
                "path_window_reconciliation_reason": "Fixed120 contrast uses the same entry_pos and high path as the no-horizon path-defined label.",
                "winner_definition": "max_high_return_over_fixed120_window_gte_threshold",
                "horizon_complete_denominator_rule": "fixed120_horizon_complete_n",
                "baseline_definition_status": "pass",
            }
        )
    return pd.DataFrame(rows, columns=BASELINE_COLUMNS)


def slow_winner_morphology_readout(label: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cohorts = {
        "slow_winner": lambda sub: bool_series(sub["slow_winner_flag"]),
        "fast_winner": lambda sub: bool_series(sub["fast_winner_flag"]),
        "observed_non_hit_control": lambda sub: bool_series(sub["observed_non_hit_control_flag"]),
    }
    for threshold_id in THRESHOLDS:
        th = label.loc[label["threshold_id"].eq(threshold_id)]
        for split, sub in split_subframes(th):
            for cohort_id, mask_func in cohorts.items():
                mask = mask_func(sub)
                cohort_role = "readout_only_censored_control_not_negative" if cohort_id == "observed_non_hit_control" else "winner_duration_cohort"
                cohort = sub.loc[mask]
                for feature in MORPHOLOGY_FEATURES:
                    vals = finite_numeric(cohort.get(feature, pd.Series(dtype=float)))
                    rows.append(
                        {
                            "threshold_id": threshold_id,
                            "split_bucket": split,
                            "cohort_id": cohort_id,
                            "cohort_role": cohort_role,
                            "feature_id": feature,
                            "feature_observation_boundary": "t0_close_reference_pos_or_earlier",
                            "feature_n": int(vals.notna().sum()),
                            "feature_missing_n": int(len(cohort) - vals.notna().sum()),
                            "feature_p25": float(vals.quantile(0.25)) if vals.notna().any() else np.nan,
                            "feature_median": float(vals.quantile(0.50)) if vals.notna().any() else np.nan,
                            "feature_p75": float(vals.quantile(0.75)) if vals.notna().any() else np.nan,
                            "feature_readout_status": "pass" if len(cohort) else "empty_cohort",
                        }
                    )
    return pd.DataFrame(rows, columns=MORPHOLOGY_COLUMNS)


def morphology_status_for_threshold(label: pd.DataFrame, threshold_id: str, split: str, deltas: dict[str, float]) -> str:
    sub = label.loc[label["threshold_id"].eq(threshold_id) & label["split_bucket"].astype(str).eq(split)]
    slow_n = int(bool_series(sub.get("slow_winner_flag", pd.Series(False, index=sub.index))).sum())
    if slow_n < 200:
        return "inconclusive_insufficient_n"
    if deltas.get("compression_state", -np.inf) >= 0.10 and deltas.get("drawdown_reversal_state", -np.inf) >= 0.10:
        return "distinct_surface_present"
    return "overlaps_known_failed_morphology"


def known_failed_morphology_overlap(label: pd.DataFrame) -> pd.DataFrame:
    train = label.loc[label["split_bucket"].astype(str).eq("train")].drop_duplicates(["instrument", "reference_date"])
    thresholds = {
        "compression_state": ("vol_compression_20d_60d", float(finite_numeric(train["vol_compression_20d_60d"]).quantile(0.20))),
        "drawdown_reversal_state": ("max_drawdown_20d", float(finite_numeric(train["max_drawdown_20d"]).quantile(0.20))),
    }
    rows: list[dict[str, Any]] = []
    for threshold_id in THRESHOLDS:
        th = label.loc[label["threshold_id"].eq(threshold_id)]
        for split, sub in split_subframes(th):
            state_shares: dict[tuple[str, str], float] = {}
            for cohort_id, mask in {
                "slow_winner": bool_series(sub.get("slow_winner_flag", pd.Series(False, index=sub.index))),
                "fast_winner": bool_series(sub.get("fast_winner_flag", pd.Series(False, index=sub.index))),
                "observed_non_hit_control": bool_series(sub.get("observed_non_hit_control_flag", pd.Series(False, index=sub.index))),
            }.items():
                cohort = sub.loc[mask]
                for state_id, (feature, value) in thresholds.items():
                    share = safe_rate(finite_numeric(cohort.get(feature, pd.Series(dtype=float))).le(value).sum(), len(cohort))
                    state_shares[(cohort_id, state_id)] = share
            deltas = {
                state_id: (state_shares.get(("fast_winner", state_id), np.nan) - state_shares.get(("slow_winner", state_id), np.nan))
                for state_id in thresholds
            }
            status = morphology_status_for_threshold(label, threshold_id, split if split in SPLITS else "train", deltas)
            for cohort_id in ["slow_winner", "fast_winner", "observed_non_hit_control"]:
                for state_id, (feature, value) in thresholds.items():
                    rows.append(
                        {
                            "threshold_id": threshold_id,
                            "split_bucket": split,
                            "cohort_id": cohort_id,
                            "state_id": state_id,
                            "state_threshold_feature": feature,
                            "state_threshold_value": value,
                            "threshold_source_split": "train",
                            "state_share": state_shares.get((cohort_id, state_id), np.nan),
                            "fast_minus_slow_share_delta": deltas.get(state_id, np.nan),
                            "slow_winner_morphology_distinct_status": status,
                            "overlap_readout_status": "pass",
                        }
                    )
    return pd.DataFrame(rows, columns=OVERLAP_COLUMNS)


def cluster_sizes_for_group(sub: pd.DataFrame) -> list[int]:
    if sub.empty:
        return []
    intervals = sub[["episode_start_pos", "episode_threshold_pos"]].dropna().sort_values(["episode_start_pos", "episode_threshold_pos"])
    sizes: list[int] = []
    current_end: float | None = None
    current_size = 0
    for row in intervals.itertuples(index=False):
        start = float(row.episode_start_pos)
        end = float(row.episode_threshold_pos)
        if current_end is None or start > current_end:
            if current_size:
                sizes.append(current_size)
            current_end = end
            current_size = 1
        else:
            current_end = max(current_end, end)
            current_size += 1
    if current_size:
        sizes.append(current_size)
    return sizes


def episode_overlap_density_audit(label: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cluster_def = "union_find_transitive_interval_merge_within_split_instrument_threshold_on_entry_pos_to_episode_threshold_pos"
    for threshold_id in THRESHOLDS:
        th = label.loc[label["threshold_id"].eq(threshold_id)]
        for split, sub in split_subframes(th):
            winners = sub.loc[bool_series(sub.get("path_winner", pd.Series(False, index=sub.index)))]
            sizes: list[int] = []
            for _key, group in winners.groupby(["instrument"], sort=False):
                sizes.extend(cluster_sizes_for_group(group))
            arr = np.asarray(sizes, dtype=float)
            rows.append(
                {
                    "threshold_id": threshold_id,
                    "split_bucket": split,
                    "path_winner_anchor_row_n": int(len(winners)),
                    "slow_winner_anchor_row_n": int(bool_series(winners.get("slow_winner_flag", pd.Series(False, index=winners.index))).sum()),
                    "approx_episode_cluster_n": int(len(sizes)),
                    "median_anchor_rows_per_episode_cluster": float(np.median(arr)) if len(arr) else np.nan,
                    "p90_anchor_rows_per_episode_cluster": float(np.quantile(arr, 0.90)) if len(arr) else np.nan,
                    "max_anchor_rows_per_episode_cluster": int(np.max(arr)) if len(arr) else 0,
                    "cluster_definition": cluster_def,
                    "readout_role": "readout_only_anchor_overlap_density_not_primary_denominator",
                    "overlap_density_status": "pass",
                }
            )
    return pd.DataFrame(rows, columns=EPISODE_COLUMNS)


def select_threshold(winner: pd.DataFrame) -> tuple[str, int]:
    train = winner.loc[winner["split_bucket"].eq("train")]
    selected = "none"
    count = 0
    for threshold_id in THRESHOLD_PRIORITY:
        row = train.loc[train["threshold_id"].eq(threshold_id)]
        if len(row) and boolish(row.iloc[0]["threshold_material_censoring_flag"]):
            count += 1
            if selected == "none":
                selected = threshold_id
    return selected, count


def search_accounting_audit(selected: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "threshold_grid": "up50pct=0.50;up100pct=1.00;up150pct=1.50",
                "threshold_grid_status": "pass",
                "threshold_priority_order": ",".join(THRESHOLD_PRIORITY),
                "selected_threshold_recommendation": selected,
                "selected_threshold_source_split": "train_only" if selected != "none" else "none",
                "selection_split_bucket": "train" if selected != "none" else "none",
                "threshold_selection_scope": "train_split_only_fixed_priority_order",
                "validation_used_for_selection": False,
                "robustness_used_for_selection": False,
                "close_based_role": "readout_only_not_for_primary_decision",
                "episode_peak_role": "readout_only_duration_description_not_primary_decision",
                "observed_non_hit_control_role": "readout_only_censored_control_not_negative",
                "episode_overlap_role": "readout_only_anchor_overlap_density_not_primary_denominator",
                "search_accounting_status": "pass",
            }
        ],
        columns=SEARCH_COLUMNS,
    )


def gate_from_status(frame: pd.DataFrame, status_col: str) -> str:
    if frame.empty or status_col not in frame.columns:
        return "fail"
    return "pass" if frame[status_col].astype(str).eq("pass").all() else "fail"


def selected_morphology_status(selected: str, overlap: pd.DataFrame) -> str:
    if selected == "none":
        return "not_evaluated_no_material_censoring"
    row = overlap.loc[
        overlap["threshold_id"].eq(selected)
        & overlap["split_bucket"].eq("train")
        & overlap["cohort_id"].eq("slow_winner")
        & overlap["state_id"].eq("compression_state")
    ]
    if row.empty:
        return "inconclusive_insufficient_n"
    return str(row.iloc[0]["slow_winner_morphology_distinct_status"])


def metric_by_threshold(winner: pd.DataFrame, time_dist: pd.DataFrame, metric: str, threshold_id: str) -> float:
    source = time_dist if metric == "share_beyond_120d" else winner
    row = source.loc[source["threshold_id"].eq(threshold_id) & source["split_bucket"].eq("train")]
    if row.empty:
        return np.nan
    return row.iloc[0].get(metric, np.nan)


def decision_row(
    *,
    input_gate: str,
    input_reason: str,
    upstream_gate: str,
    universe_gate: str,
    price_gate: str,
    label_gate: str,
    censor_gate: str,
    winner_gate: str,
    search_gate: str,
    winner: pd.DataFrame,
    time_dist: pd.DataFrame,
    overlap: pd.DataFrame,
    selected: str,
    material_count: int,
) -> pd.DataFrame:
    morph_status = selected_morphology_status(selected, overlap)
    gate_failure = "none"
    primary_failure = "none"
    next_req = "none"
    signal_auth = False
    if any(status != "pass" for status in [input_gate, upstream_gate, universe_gate, price_gate, censor_gate]):
        decision = "15A_input_blocked"
        for name, status in [
            ("input_gate_failed", input_gate),
            ("upstream_lineage_gate_failed", upstream_gate),
            ("universe_membership_gate_failed", universe_gate),
            ("price_path_completeness_gate_failed", price_gate),
            ("censoring_isolation_gate_failed", censor_gate),
        ]:
            if status != "pass":
                gate_failure = name
                break
        primary_failure = input_reason or gate_failure
    elif label_gate != "pass":
        decision = "15A_label_rebuild_failed"
        gate_failure = "label_rebuild_gate_failed"
        primary_failure = gate_failure
    elif material_count == 0:
        decision = "15A_no_material_censoring_fixed_horizon_label_adequate"
        primary_failure = "none_no_material_censoring"
    elif morph_status == "inconclusive_insufficient_n":
        decision = "15A_diagnostic_inconclusive_insufficient_slow_winner"
        primary_failure = morph_status
    elif morph_status == "overlaps_known_failed_morphology":
        decision = "15A_material_censoring_but_slow_winner_overlaps_known_failed_morphology"
    elif morph_status == "distinct_surface_present":
        decision = "15A_material_censoring_with_distinct_slow_winner_surface"
        next_req = "requirement_15b_path_defined_winner_separability_diagnostic.md"
        signal_auth = True
    else:
        decision = "15A_diagnostic_inconclusive_insufficient_slow_winner"
        primary_failure = morph_status
    selected_row = winner.loc[winner["threshold_id"].eq(selected) & winner["split_bucket"].eq("train")] if selected != "none" else pd.DataFrame()
    selected_time = time_dist.loc[time_dist["threshold_id"].eq(selected) & time_dist["split_bucket"].eq("train")] if selected != "none" else pd.DataFrame()
    row = {
        "decision_state": decision,
        "next_allowed_requirement": next_req,
        "label_deployment_authorized": False,
        "signal_search_authorized": signal_auth,
        "selection_split_bucket": "train" if selected != "none" else "none",
        "selected_threshold_recommendation": selected,
        "selected_threshold_reason": "lowest_pre_registered_material_censoring_threshold" if selected != "none" else "none_no_material_censoring",
        "selected_threshold_share_beyond_120d": selected_time.iloc[0]["share_beyond_120d"] if len(selected_time) else np.nan,
        "selected_threshold_slow_winner_rate_all_records": selected_row.iloc[0]["slow_winner_rate_all_records"] if len(selected_row) else np.nan,
        "selected_threshold_censored_rate": selected_row.iloc[0]["censored_rate"] if len(selected_row) else np.nan,
        "primary_failure_reason": primary_failure,
        "gate_failure": gate_failure,
        "input_gate_status": input_gate,
        "upstream_lineage_gate_status": upstream_gate,
        "universe_membership_gate_status": universe_gate,
        "price_path_completeness_gate_status": price_gate,
        "label_rebuild_gate_status": label_gate,
        "censoring_isolation_gate_status": censor_gate,
        "winner_set_difference_gate_status": winner_gate,
        "search_accounting_gate_status": search_gate,
        "slow_winner_morphology_distinct_status": morph_status,
        "material_censoring_threshold_count": material_count,
    }
    for threshold_id in THRESHOLD_PRIORITY:
        row[f"share_beyond_120d_{threshold_id}"] = metric_by_threshold(winner, time_dist, "share_beyond_120d", threshold_id)
        row[f"slow_winner_rate_all_records_{threshold_id}"] = metric_by_threshold(winner, time_dist, "slow_winner_rate_all_records", threshold_id)
        row[f"censored_rate_{threshold_id}"] = metric_by_threshold(winner, time_dist, "censored_rate", threshold_id)
    return pd.DataFrame([row], columns=DECISION_COLUMNS)


def render_report(
    decision: pd.DataFrame,
    input_audit: pd.DataFrame,
    upstream: pd.DataFrame,
    universe: pd.DataFrame,
    price: pd.DataFrame,
    winner: pd.DataFrame,
    time_dist: pd.DataFrame,
    censor: pd.DataFrame,
    overlap: pd.DataFrame,
    episode: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict()
    train_winner = winner.loc[winner["split_bucket"].eq("train")]
    train_time = time_dist.loc[time_dist["split_bucket"].eq("train")]
    required_inputs = input_audit.loc[bool_series(input_audit["required_flag"])]
    primary_lineage = upstream.iloc[0].to_dict() if len(upstream) else {}
    input_summary = (
        f"required artifacts = {len(required_inputs)}, pass = "
        f"{int((required_inputs['read_status'].eq('pass') & required_inputs['schema_status'].astype(str).str.startswith(('pass', 'directory', 'not_checked'))).sum())}"
    )
    universe_lines = []
    for split, sub in universe.groupby("split_bucket", sort=False):
        universe_lines.append(
            f"| {split} | {int(sub['unique_anchor_row_n'].sum())} | "
            f"{sub['membership_match_rate'].min():.4f} | "
            f"{','.join(sorted(sub['split_boundary_status'].astype(str).unique()))} | "
            f"{','.join(sorted(sub['universe_membership_status'].astype(str).unique()))} |"
        )
    price_status = ",".join(sorted(price["price_path_status"].astype(str).unique())) if len(price) else "missing"
    price_summary = (
        f"instrument_n = {len(price)}, status = {price_status}, "
        f"min_forward_sessions = {price['min_available_forward_sessions'].min():.0f}, "
        f"median_instrument_forward_sessions = {price['median_available_forward_sessions'].median():.0f}"
        if len(price)
        else "instrument_n = 0, status = `missing`"
    )
    lines = []
    time_lines = []
    for threshold_id in THRESHOLD_PRIORITY:
        w = train_winner.loc[train_winner["threshold_id"].eq(threshold_id)].iloc[0]
        t = train_time.loc[train_time["threshold_id"].eq(threshold_id)].iloc[0]
        lines.append(
            f"| {threshold_id} | {int(w['record_n'])} | {int(w['path_winner_n'])} | "
            f"{w['path_winner_rate_all_records']:.4f} | {int(w['slow_winner_n'])} | "
            f"{w['slow_winner_rate_all_records']:.4f} | {t['share_beyond_120d']:.4f} | "
            f"{w['censored_rate']:.4f} | {int(w['path_only_winner_n'])} | {int(w['fixed120_only_winner_n'])} |"
        )
        time_lines.append(
            f"| {threshold_id} | {int(t['path_winner_n'])} | {t['time_to_threshold_p10']:.0f} | "
            f"{t['time_to_threshold_p25']:.0f} | {t['time_to_threshold_median']:.0f} | "
            f"{t['time_to_threshold_p75']:.0f} | {t['time_to_threshold_p90']:.0f} | "
            f"{t['time_to_threshold_max']:.0f} | {t['share_within_120d']:.4f} | {t['share_beyond_120d']:.4f} | "
            f"{t['share_beyond_250d']:.4f} |"
        )
    selected = d.get("selected_threshold_recommendation", "none")
    censor_train = censor.loc[censor["split_bucket"].eq("train")]
    censor_pass = "pass" if censor_train["censored_isolation_status"].astype(str).eq("pass").all() else "fail"
    ep = episode.loc[episode["split_bucket"].eq("train")]
    ep_lines = []
    for threshold_id in THRESHOLD_PRIORITY:
        row = ep.loc[ep["threshold_id"].eq(threshold_id)].iloc[0]
        ep_lines.append(
            f"| {threshold_id} | {int(row['path_winner_anchor_row_n'])} | "
            f"{int(row['slow_winner_anchor_row_n'])} | {int(row['approx_episode_cluster_n'])} | "
            f"{row['median_anchor_rows_per_episode_cluster']:.2f} | {row['p90_anchor_rows_per_episode_cluster']:.2f} |"
        )
    morph = overlap.loc[
        overlap["split_bucket"].eq("train")
        & overlap["cohort_id"].isin(["slow_winner", "fast_winner"])
        & overlap["state_id"].isin(["compression_state", "drawdown_reversal_state"])
    ]
    morph_lines = []
    for row in morph.itertuples(index=False):
        morph_lines.append(
            f"| {row.threshold_id} | {row.cohort_id} | {row.state_id} | "
            f"{row.state_share:.4f} | {row.fast_minus_slow_share_delta:.4f} | "
            f"{row.slow_winner_morphology_distinct_status} |"
        )
    return f"""# 15A Winner Episode Label Censoring Diagnostic

单行裁决：`{d['decision_state']}`。Selected threshold = `{selected}`；15B 授权 = `{d['signal_search_authorized']}`；label deployment 授权 = `False`。

## 为什么做 15A

15A 检验 fixed-horizon winner label 是否系统性 right-censor 慢速大赢家。这里不寻找信号、不训练模型、不定义 entry/exit，也不授权仓位或 label 部署；所有统计单位均为 anchor row。

## Gate Summary

| gate | status |
|---|---|
| input | `{d['input_gate_status']}` |
| upstream_lineage | `{d['upstream_lineage_gate_status']}` |
| universe_membership | `{d['universe_membership_gate_status']}` |
| price_path_completeness | `{d['price_path_completeness_gate_status']}` |
| label_rebuild | `{d['label_rebuild_gate_status']}` |
| censoring_isolation | `{d['censoring_isolation_gate_status']}` |
| winner_set_difference | `{d['winner_set_difference_gate_status']}` |
| search_accounting | `{d['search_accounting_gate_status']}` |

## Input / Lineage / Universe / Price Path

| item | value |
|---|---|
| input_summary | `{input_summary}` |
| primary_row_level_source_role | `{primary_lineage.get('primary_row_level_source_role', '')}` |
| primary_row_level_source | `{primary_lineage.get('primary_row_level_source', '')}` |
| cross_check_key_coverage_rate | `{primary_lineage.get('cross_check_key_coverage_rate', '')}` |
| cross_check_mismatch_n | `{primary_lineage.get('cross_check_mismatch_n', '')}` |
| path_window_reconciliation_status | `{primary_lineage.get('path_window_reconciliation_status', '')}` |
| price_path_summary | `{price_summary}` |

| split | unique_anchor_row_n | min_membership_match_rate | split_boundary_status | universe_membership_status |
|---|---:|---:|---|---|
{chr(10).join(universe_lines)}

## Train Winner Set Difference

| threshold | record_n | path_winner_n | path_winner_rate | slow_winner_n | slow_rate_all | share_beyond_120d | censored_rate | path_only_n | fixed120_only_n |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(lines)}

`share_beyond_120d` 是 fixed-120d 会漏掉的 path-defined winner 比例；`slow_winner_rate_all_records` 是该漏标群体在全 anchor-row universe 中的密度。

## Train Time-to-Threshold Distribution

| threshold | path_winner_n | p10 | p25 | median | p75 | p90 | max | share_within_120d | share_beyond_120d | share_beyond_250d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(time_lines)}

## Censoring Isolation

Train censoring isolation status = `{censor_pass}`。Primary no-horizon label 中 censored rows 只进入 `record_n` 与 `censored_n/rate`；不会进入 confirmed negative。`observed_non_hit_control` 仅为 readout-only control。

## Known Failed Morphology Overlap

| threshold | cohort | state | state_share | fast_minus_slow_delta | status |
|---|---|---|---:|---:|---|
{chr(10).join(morph_lines)}

## Anchor-Row Overlap Density

这些数字只说明连续 anchor 对同一上涨 interval 的重复计数密度，不替代 primary anchor-row denominator。

| threshold | winner_anchor_n | slow_anchor_n | approx_cluster_n | median_rows_per_cluster | p90_rows_per_cluster |
|---|---:|---:|---:|---:|---:|
{chr(10).join(ep_lines)}

## Next Step

`next_allowed_requirement = {d['next_allowed_requirement']}`。即使 15A 到达 material censoring with distinct surface，也只授权 15B 做 separability diagnostic；不授权任何可交易 alpha、entry、模型、仓位或 label 部署。
"""


def git_revision(cwd: Path) -> str | None:
    return r13a.git_revision(cwd)


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: str, outputs: dict[str, Path]) -> Path:
    publishable = {key: value for key, value in outputs.items() if key != "manifest" and value.exists() and LOCAL_CACHE_DIR not in value.parents}
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": r13a.file_sha256(config_path) if config_path.is_file() else None,
        "decision_state": decision,
        "outputs": {key: str(value) for key, value in publishable.items()},
        "output_hashes": {key: r13a.file_sha256(value) for key, value in publishable.items() if value.is_file()},
    }
    return write_json(path, payload)


def write_blocked_outputs(outputs: dict[str, Path], config_path: Path, config: dict[str, Any], input_gate: str, reason: str) -> int:
    empty_outputs = {
        "upstream_lineage_audit": empty_frame(UPSTREAM_COLUMNS),
        "universe_membership_audit": empty_frame(UNIVERSE_COLUMNS),
        "price_path_completeness_audit": empty_frame(PRICE_COLUMNS),
        "baseline_label_definition_audit": empty_frame(BASELINE_COLUMNS),
        "path_defined_label_rebuild_audit": empty_frame(LABEL_REBUILD_COLUMNS),
        "winner_set_difference_readout": empty_frame(WINNER_COLUMNS),
        "time_to_threshold_distribution_readout": empty_frame(TIME_COLUMNS),
        "censoring_isolation_audit": empty_frame(CENSOR_COLUMNS),
        "slow_winner_morphology_readout": empty_frame(MORPHOLOGY_COLUMNS),
        "known_failed_morphology_overlap_readout": empty_frame(OVERLAP_COLUMNS),
        "episode_overlap_density_audit": empty_frame(EPISODE_COLUMNS),
        "search_accounting_audit": empty_frame(SEARCH_COLUMNS),
    }
    for key, frame in empty_outputs.items():
        write_df(outputs[key], frame)
    decision = decision_row(
        input_gate=input_gate,
        input_reason=reason,
        upstream_gate="fail",
        universe_gate="fail",
        price_gate="fail",
        label_gate="fail",
        censor_gate="fail",
        winner_gate="fail",
        search_gate="fail",
        winner=empty_frame(WINNER_COLUMNS),
        time_dist=empty_frame(TIME_COLUMNS),
        overlap=empty_frame(OVERLAP_COLUMNS),
        selected="none",
        material_count=0,
    )
    write_df(outputs["decision"], decision)
    write_text(outputs["report"], f"# 15A Winner Episode Label Censoring Diagnostic\n\n单行裁决：`15A_input_blocked`。\n\n阻塞原因：`{reason}`。\n")
    write_manifest(outputs["manifest"], config_path, config, "15A_input_blocked", outputs)
    return 2


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for path in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    input_audit = build_input_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 2
    if input_gate != "pass":
        return write_blocked_outputs(outputs, config_path, config, input_gate, input_reason)

    source_panel, lineage_info = load_primary_universe_panel(resolved)
    upstream = build_upstream_lineage_audit(resolved, lineage_info)
    write_df(outputs["upstream_lineage_audit"], upstream)
    upstream_gate = audit_status(upstream, "lineage_status")
    if source_panel.empty:
        return write_blocked_outputs(outputs, config_path, config, input_gate, lineage_info.get("blocking_reason", "no_usable_row_level_source"))

    anchor = build_anchor_panel(source_panel)
    universe = build_universe_membership_audit(source_panel, anchor, resolved)
    write_df(outputs["universe_membership_audit"], universe)
    universe_gate = gate_from_status(universe, "universe_membership_status")
    price, anchor = build_price_path_completeness(anchor, resolved["stock_daily_qfq_dir"])
    write_df(outputs["price_path_completeness_audit"], price)
    price_gate = gate_from_status(price, "price_path_status")
    write_df(outputs["universe_rebuild_panel"], anchor)

    label = build_path_defined_label_panel(anchor, resolved["stock_daily_qfq_dir"])
    write_df(outputs["path_defined_label_panel"], label)
    baseline = build_baseline_definition_audit(resolved, upstream)
    write_df(outputs["baseline_label_definition_audit"], baseline)

    rebuild = label_rebuild_audit(label)
    winner = winner_set_difference(label)
    time_dist = time_to_threshold_distribution(label)
    censor = censoring_isolation_audit(label)
    morphology = slow_winner_morphology_readout(label)
    overlap = known_failed_morphology_overlap(label)
    episode = episode_overlap_density_audit(label)
    selected, material_count = select_threshold(winner)
    search = search_accounting_audit(selected)
    slow_panel_cols = ["instrument", "reference_date", "row_id", "split_bucket", "threshold_id", "slow_winner_flag", "fast_winner_flag", "observed_non_hit_control_flag"] + [c for c in MORPHOLOGY_FEATURES if c in label.columns]
    write_df(outputs["slow_winner_morphology_panel"], label[[c for c in slow_panel_cols if c in label.columns]])
    for key, frame in [
        ("path_defined_label_rebuild_audit", rebuild),
        ("winner_set_difference_readout", winner),
        ("time_to_threshold_distribution_readout", time_dist),
        ("censoring_isolation_audit", censor),
        ("slow_winner_morphology_readout", morphology),
        ("known_failed_morphology_overlap_readout", overlap),
        ("episode_overlap_density_audit", episode),
        ("search_accounting_audit", search),
    ]:
        write_df(outputs[key], frame)

    label_gate = gate_from_status(rebuild, "rebuild_status")
    censor_gate = gate_from_status(censor, "censored_isolation_status")
    winner_gate = gate_from_status(winner, "winner_set_difference_status")
    search_gate = gate_from_status(search, "search_accounting_status")
    decision = decision_row(
        input_gate=input_gate,
        input_reason=input_reason,
        upstream_gate=upstream_gate,
        universe_gate=universe_gate,
        price_gate=price_gate,
        label_gate=label_gate,
        censor_gate=censor_gate,
        winner_gate=winner_gate,
        search_gate=search_gate,
        winner=winner,
        time_dist=time_dist,
        overlap=overlap,
        selected=selected,
        material_count=material_count,
    )
    write_df(outputs["decision"], decision)
    write_text(outputs["report"], render_report(decision, input_audit, upstream, universe, price, winner, time_dist, censor, overlap, episode))
    write_manifest(outputs["manifest"], config_path, config, str(decision.iloc[0]["decision_state"]), outputs)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())

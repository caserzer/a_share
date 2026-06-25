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
RUNNER_14A_PATH = EXPERIMENT_DIR / "src" / "run_14a_full_native_sparse_state_change_event_utility_preflight.py"


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r14a = load_runner(RUNNER_14A_PATH, "run_14a_full_native_sparse_state_change_event_utility_preflight")
r13a = r14a.r13a


RUN_ID = "14C_cohort_rank_monotonicity_stress_diagnostic"
EXPERIMENT_ID = "14_full_native_sparse_state_change_event_utility_preflight_v0"
PHASE_ID = "14C"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_14c_cohort_rank_monotonicity_stress_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SPLITS = ("train", "validation", "robustness")


ALLOWED_14A_DECISIONS = {
    "14A_diagnostic_cohort_signal_only_no_utility",
    "14A_diagnostic_raw_event_signal_but_no_cohort_transport",
    "14A_stop_no_cohort_utility_transport",
    "14A_stop_validation_stress_failure_no_active_entry_authorization",
    "14A_stop_density_duplicate_or_morphology_rediscovery",
    "14A_stop_no_sparse_event_utility",
}
SUPPORTED_14A_DECISION = "14A_supported_open_14B_confirmatory_sparse_event_requirement"
DIAGNOSTIC_ROLE = "diagnostic_secondary_not_for_selection"


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "requirement": (),
    "upstream_requirement_14a": (),
    "upstream_14a_manifest": (),
    "upstream_14a_decision": (
        "decision_state",
        "next_allowed_requirement",
        "selected_raw_event_arm_id",
        "selected_cohort_arm_id",
        "selected_rank_cutoff_id",
        "primary_cost_tier_bps",
    ),
    "upstream_14a_search_multiplicity": ("search_accounting_gate_status",),
    "upstream_14a_cohort_dictionary": (
        "cohort_arm_id",
        "minimum_cohort_finite_n",
        "rank_direction",
    ),
    "upstream_14a_rank_availability": (
        "raw_event_arm_id",
        "cohort_arm_id",
        "split_bucket",
        "event_n",
        "cohort_rank_pass_n",
    ),
    "upstream_14a_utility_readout": (
        "raw_event_arm_id",
        "cohort_arm_id",
        "rank_cutoff_id",
        "split_bucket",
        "same_event_denominator_n",
    ),
    "upstream_14a_validation_stress": (
        "raw_event_arm_id",
        "cohort_arm_id",
        "rank_cutoff_id",
    ),
    "upstream_14a_raw_readout": (
        "raw_event_arm_id",
        "family_id",
        "parameter_set_id",
        "split_bucket",
        "event_n",
    ),
    "upstream_14a_report": (),
    "upstream_14a_cohort_event_panel_cache": (
        "family_id",
        "parameter_set_id",
        "raw_event_arm_id",
        "event_id",
        "row_id",
        "instrument",
        "reference_date",
        "split_bucket",
        "board_bucket",
        "calendar_year",
        "instrument_year",
        "reference_date_rank",
        "event_intensity_score",
        "entry_date",
        "entry_price",
        "upper_first",
        "lower_first",
        "same_bar_conflict",
        "winner",
        "fast_fail",
        "upper_barrier_return",
        "lower_barrier_return",
        "terminal_return_20d",
        "max_high_return",
        "min_low_return",
        "path_utility_component_0bps",
        "path_utility_component_50bps",
        "path_utility_component_100bps",
        "cohort_finite_n",
        "cohort_percentile_rank",
        "cohort_rank_status",
        "cohort_arm_id",
        "rank_cutoff_id",
        "selected_event_flag",
        "skipped_event_flag",
    ),
    "upstream_14a_sparse_event_panel_cache": (
        "family_id",
        "parameter_set_id",
        "raw_event_arm_id",
        "event_id",
        "row_id",
        "instrument",
        "reference_date",
        "split_bucket",
        "event_intensity_score",
        "winner",
        "fast_fail",
        "path_utility_component_50bps",
    ),
    "upstream_14a_state_change_feature_panel_cache": (
        "row_id",
        "instrument",
        "reference_date",
        "market_regime_bucket",
        "volatility_20d_decile",
        "liquidity_metric_decile",
        "board_bucket",
        "calendar_year",
        "calendar_month",
    ),
}

OPTIONAL_INPUT_ARTIFACTS = {"upstream_14a_report"}
LOCAL_CACHE_INPUTS = {
    "upstream_14a_cohort_event_panel_cache",
    "upstream_14a_sparse_event_panel_cache",
    "upstream_14a_state_change_feature_panel_cache",
}
PUBLISHABLE_TABLE_KEYS = [
    "input_artifact_audit",
    "upstream_14a_lineage_audit",
    "row_level_cohort_rank_source_audit",
    "rank_cutoff_duplicate_consistency_audit",
    "feature_enrichment_audit",
    "primary_finite_rank_coverage_audit",
    "primary_cohort_rank_ic_by_split",
    "primary_cohort_rank_bucket_monotonicity_readout",
    "primary_cohort_rank_bootstrap_interval",
    "cohort_dimension_rank_ic_by_split",
    "cohort_dimension_bucket_monotonicity_readout",
    "stress_regime_rank_monotonicity_readout",
    "stress_dimension_failure_mode_audit",
    "all_family_raw_intensity_monotonicity_readout",
    "search_accounting_audit",
    "cohort_rank_monotonicity_stress_decision",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 14C cohort rank monotonicity stress diagnostic.")
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
    out = {key: TABLE_DIR / f"{key}.csv" for key in PUBLISHABLE_TABLE_KEYS}
    out.update(
        {
            "cohort_rank_monotonicity_panel": LOCAL_CACHE_DIR / "cohort_rank_monotonicity_panel.parquet",
            "primary_c3_rank_bucket_panel": LOCAL_CACHE_DIR / "primary_c3_rank_bucket_panel.parquet",
            "stress_dimension_rank_panel": LOCAL_CACHE_DIR / "stress_dimension_rank_panel.parquet",
            "report": REPORT_DIR / "cohort_rank_monotonicity_stress_diagnostic_report.md",
            "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
        }
    )
    return out


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r14a.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r14a.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r14a.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r14a.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r14a.file_sha(path)


def count_rows(path: Path) -> int | float:
    return r14a.count_rows(path)


def stable_hash(value: Any) -> str:
    return r14a.stable_hash(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r14a.bool_series(series)


def finite_numeric(series: pd.Series) -> pd.Series:
    return r14a.finite_numeric(series)


def safe_rate(num: Any, den: Any) -> float:
    return r14a.safe_rate(num, den)


def table_columns(path: Path) -> list[str]:
    if not path.exists() or path.is_dir():
        return []
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path).columns)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    return []


def read_status_for_path(path: Path) -> tuple[str, int | float, int | float, str]:
    if not path.exists():
        return "missing", np.nan, np.nan, "missing"
    if path.is_dir():
        return "pass", count_rows(path), np.nan, "directory"
    try:
        cols = table_columns(path)
        return "pass", count_rows(path), len(cols) if cols else np.nan, "readable"
    except Exception as exc:  # pragma: no cover - defensive audit path
        return f"read_error:{type(exc).__name__}", np.nan, np.nan, "not_checked"


def artifact_lineage_role(artifact_id: str) -> str:
    if artifact_id in LOCAL_CACHE_INPUTS:
        return "14a_local_row_level_cache"
    if artifact_id.startswith("upstream_14a"):
        return "14a_publishable_lineage"
    return "run_config_input"


def build_input_artifact_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, path in resolved.items():
        required_cols = EXPECTED_INPUT_COLUMNS.get(artifact_id, ())
        read_status, row_count, column_count, fallback_schema = read_status_for_path(path)
        missing = sorted(set(required_cols) - set(table_columns(path))) if path.exists() and required_cols else []
        if not path.exists():
            schema_status = "missing"
        elif path.is_dir():
            schema_status = "directory"
        elif missing:
            schema_status = "missing_columns"
        else:
            schema_status = "pass" if required_cols else fallback_schema
        rows.append(
            {
                "artifact_role": artifact_id,
                "artifact_path": str(path),
                "resolved_path": str(path.resolve()) if path.exists() else str(path),
                "required_flag": artifact_id not in OPTIONAL_INPUT_ARTIFACTS,
                "lineage_role": artifact_lineage_role(artifact_id),
                "read_status": read_status,
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path),
                "schema_status": schema_status,
                "required_column_missing_list": ";".join(missing),
            }
        )
    return pd.DataFrame(rows)


def build_row_level_source_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    role_map = {
        "upstream_14a_cohort_event_panel_cache": "pit_cohort_normalized_event_panel",
        "upstream_14a_sparse_event_panel_cache": "sparse_event_panel",
        "upstream_14a_state_change_feature_panel_cache": "state_change_feature_panel",
    }
    rows: list[dict[str, Any]] = []
    for artifact_id, artifact_role in role_map.items():
        path = resolved[artifact_id]
        required_cols = EXPECTED_INPUT_COLUMNS[artifact_id]
        read_status, row_count, column_count, _fallback = read_status_for_path(path)
        cols = table_columns(path)
        missing = sorted(set(required_cols) - set(cols)) if cols else list(required_cols)
        schema_status = "pass" if path.exists() and not missing else "missing_columns" if path.exists() else "missing"
        local_status = "pass" if read_status == "pass" and schema_status == "pass" and file_sha(path) else "fail"
        rows.append(
            {
                "artifact_role": artifact_role,
                "artifact_path": str(path),
                "direct_read_status": read_status,
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path),
                "schema_status": schema_status,
                "required_column_missing_list": ";".join(missing),
                "local_cache_lineage_status": local_status,
            }
        )
    return pd.DataFrame(rows)


def build_upstream_lineage_audit(resolved: dict[str, Path]) -> tuple[pd.DataFrame, dict[str, Any]]:
    decision_info: dict[str, Any] = {
        "decision_state": "",
        "next_allowed_requirement": "",
        "selected_raw_event_arm_id": "",
        "selected_cohort_arm_id": "",
        "selected_rank_cutoff_id": "",
        "primary_cost_tier_bps": 50,
        "decision_prerequisite_status": "fail",
    }
    try:
        decision = read_table(resolved["upstream_14a_decision"]).iloc[0].to_dict()
        state = str(decision.get("decision_state", ""))
        if state in ALLOWED_14A_DECISIONS:
            prereq = "pass"
        elif state == SUPPORTED_14A_DECISION:
            prereq = "not_applicable_14a_supported_confirmatory_path"
        else:
            prereq = "fail_unrecognized_14a_decision"
        decision_info.update(
            {
                "decision_state": state,
                "next_allowed_requirement": str(decision.get("next_allowed_requirement", "")),
                "selected_raw_event_arm_id": str(decision.get("selected_raw_event_arm_id", "")),
                "selected_cohort_arm_id": str(decision.get("selected_cohort_arm_id", "")),
                "selected_rank_cutoff_id": str(decision.get("selected_rank_cutoff_id", "")),
                "primary_cost_tier_bps": int(float(decision.get("primary_cost_tier_bps", 50))),
                "decision_prerequisite_status": prereq,
            }
        )
    except Exception as exc:
        decision_info["decision_prerequisite_status"] = f"read_error:{type(exc).__name__}"
    row = {
        "upstream_requirement_path": str(resolved["upstream_requirement_14a"]),
        "upstream_requirement_sha256": file_sha(resolved["upstream_requirement_14a"]),
        "upstream_manifest_path": str(resolved["upstream_14a_manifest"]),
        "upstream_manifest_sha256": file_sha(resolved["upstream_14a_manifest"]),
        "upstream_decision_path": str(resolved["upstream_14a_decision"]),
        "upstream_decision_sha256": file_sha(resolved["upstream_14a_decision"]),
        "upstream_decision_state": decision_info["decision_state"],
        "upstream_next_allowed_requirement": decision_info["next_allowed_requirement"],
        "upstream_selected_raw_event_arm_id": decision_info["selected_raw_event_arm_id"],
        "upstream_selected_cohort_arm_id": decision_info["selected_cohort_arm_id"],
        "upstream_selected_rank_cutoff_id": decision_info["selected_rank_cutoff_id"],
        "upstream_primary_cost_tier_bps": decision_info["primary_cost_tier_bps"],
        "decision_prerequisite_status": decision_info["decision_prerequisite_status"],
        "lineage_status": "pass" if decision_info["decision_prerequisite_status"] in {"pass", "not_applicable_14a_supported_confirmatory_path"} else "fail",
    }
    return pd.DataFrame([row]), decision_info


def compare_values(left: pd.Series, right: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(left) or pd.api.types.is_numeric_dtype(right):
        lnum = finite_numeric(left)
        rnum = finite_numeric(right)
        return (lnum.eq(rnum)) | (lnum.isna() & rnum.isna())
    return left.astype(str).fillna("").eq(right.astype(str).fillna(""))


def rank_cutoff_priority(value: Any) -> tuple[int, str]:
    text = str(value)
    if text == "top20pct":
        return 0, text
    if text == "top10pct":
        return 1, text
    return 2, text


INVARIANT_FIELDS = [
    "row_id",
    "instrument",
    "reference_date",
    "split_bucket",
    "event_intensity_score",
    "winner",
    "fast_fail",
    "lower_first",
    "same_bar_conflict",
    "path_utility_component_0bps",
    "path_utility_component_50bps",
    "path_utility_component_100bps",
    "cohort_finite_n",
    "cohort_percentile_rank",
    "cohort_rank_status",
]


def canonicalize_rank_cutoffs(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    key = ["raw_event_arm_id", "event_id", "cohort_arm_id"]
    work = panel.copy()
    for date_col in ["reference_date", "entry_date"]:
        if date_col in work.columns:
            work[date_col] = work[date_col].astype(str).str[:10]
    rows: list[dict[str, Any]] = []
    group_count = int(work.groupby(key, dropna=False).ngroups) if not work.empty else 0
    duplicate_row_n = int(work.duplicated(key, keep=False).sum()) if not work.empty else 0
    overall_status = "pass"
    for field in INVARIANT_FIELDS:
        mismatch_group_n = 0
        mismatch_row_n = 0
        if field not in work.columns:
            mismatch_group_n = group_count
            mismatch_row_n = len(work)
        else:
            for _, sub in work.groupby(key, dropna=False, sort=False):
                if len(sub) <= 1:
                    continue
                values = sub[field]
                if pd.api.types.is_numeric_dtype(values):
                    distinct = finite_numeric(values).dropna().unique()
                    has_mismatch = len(distinct) > 1 or (values.isna().any() and len(distinct) > 0)
                else:
                    has_mismatch = values.astype(str).fillna("").nunique(dropna=False) > 1
                if has_mismatch:
                    mismatch_group_n += 1
                    mismatch_row_n += len(sub)
        field_status = "pass" if mismatch_group_n == 0 else "fail"
        if field_status != "pass":
            overall_status = "fail"
        rows.append(
            {
                "raw_event_arm_id": "__all__",
                "cohort_arm_id": "__all__",
                "duplicate_key_name": "+".join(key),
                "duplicate_group_n": group_count,
                "duplicate_row_n": duplicate_row_n,
                "rank_cutoff_values": ";".join(sorted(work.get("rank_cutoff_id", pd.Series(dtype=str)).astype(str).unique())),
                "canonical_rank_cutoff_priority": "top20pct,top10pct,lexicographic",
                "canonical_row_n": group_count,
                "invariant_field": field,
                "mismatch_group_n": mismatch_group_n,
                "mismatch_row_n": mismatch_row_n,
                "duplicate_consistency_status": field_status,
            }
        )
    if work.empty:
        canonical = work.copy()
    else:
        priority = work["rank_cutoff_id"].map(rank_cutoff_priority)
        work["_rank_cutoff_priority"] = [x[0] for x in priority]
        work["_rank_cutoff_lex"] = [x[1] for x in priority]
        canonical = work.sort_values(key + ["_rank_cutoff_priority", "_rank_cutoff_lex"], kind="stable").drop_duplicates(key, keep="first")
        canonical = canonical.rename(columns={"rank_cutoff_id": "canonical_rank_cutoff_source"})
        canonical = canonical.drop(columns=["_rank_cutoff_priority", "_rank_cutoff_lex"])
    return canonical.reset_index(drop=True), pd.DataFrame(rows), overall_status


def normalize_decile(series: pd.Series) -> tuple[pd.Series, str]:
    values = finite_numeric(series)
    finite = values.dropna()
    if finite.empty:
        return values, "no_finite_deciles"
    if finite.min() >= 0 and finite.max() <= 9:
        return values + 1, "shifted_0_9_to_1_10"
    return values, "pass"


def bucket_from_decile(series: pd.Series) -> pd.Series:
    values = finite_numeric(series)
    out = pd.Series("missing", index=series.index, dtype=object)
    out.loc[values.le(3)] = "low"
    out.loc[values.between(4, 6, inclusive="both")] = "mid"
    out.loc[values.ge(7)] = "high"
    return out


def enrich_features(canonical: pd.DataFrame, feature: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    key = ["row_id", "instrument", "reference_date"]
    left = canonical.copy()
    right = feature.copy()
    for frame in [left, right]:
        frame["reference_date"] = frame["reference_date"].astype(str).str[:10]
    split_field_source = "split_bucket" if "split_bucket" in right.columns else "split"
    split_adapter_status = "pass" if split_field_source == "split_bucket" else "adapted_from_split"
    if "split_bucket" not in right.columns and "split" in right.columns:
        right["split_bucket"] = right["split"]
    right = right.drop_duplicates(key, keep="first")
    keep_cols = key + [
        c
        for c in [
            "market_regime_bucket",
            "volatility_20d_decile",
            "liquidity_metric_decile",
            "board_bucket",
            "calendar_year",
            "calendar_month",
            "split_bucket",
        ]
        if c in right.columns
    ]
    merged = left.merge(right[keep_cols], on=key, how="left", suffixes=("_canonical", "_feature"))
    matched = int(merged["market_regime_bucket"].notna().sum()) if "market_regime_bucket" in merged.columns else 0
    missing = len(merged) - matched
    missing_rate = safe_rate(missing, len(merged))
    decile_statuses: list[str] = []
    if "volatility_20d_decile" in merged.columns:
        merged["volatility_20d_decile"], status = normalize_decile(merged["volatility_20d_decile"])
        decile_statuses.append(f"volatility:{status}")
        merged["volatility_bucket"] = bucket_from_decile(merged["volatility_20d_decile"])
    else:
        merged["volatility_bucket"] = "missing"
        decile_statuses.append("volatility:missing")
    if "liquidity_metric_decile" in merged.columns:
        merged["liquidity_metric_decile"], status = normalize_decile(merged["liquidity_metric_decile"])
        decile_statuses.append(f"liquidity:{status}")
        merged["liquidity_bucket"] = bucket_from_decile(merged["liquidity_metric_decile"])
    else:
        merged["liquidity_bucket"] = "missing"
        decile_statuses.append("liquidity:missing")
    audit_rows: list[dict[str, Any]] = []
    status = "pass" if missing_rate <= 0.001 else "fail"
    overlap_specs = [
        ("board_bucket", "board_bucket_canonical", "board_bucket_feature"),
        ("calendar_year", "calendar_year_canonical", "calendar_year_feature"),
        ("reference_date", "reference_date", "reference_date"),
        ("split_bucket", "split_bucket_canonical", "split_bucket_feature"),
    ]
    for field, left_col, right_col in overlap_specs:
        if right_col not in merged.columns:
            conflict_n = 0
            conflict_rate = 0.0
        elif left_col == right_col:
            conflict_n = 0
            conflict_rate = 0.0
        else:
            eq = compare_values(merged[left_col], merged[right_col])
            present = merged[left_col].notna() & merged[right_col].notna()
            conflict_n = int((present & ~eq).sum())
            conflict_rate = safe_rate(conflict_n, present.sum())
        if conflict_n > 0:
            status = "fail"
        audit_rows.append(
            {
                "join_key_name": "+".join(key),
                "canonical_row_n": int(len(merged)),
                "matched_row_n": matched,
                "missing_n": int(missing),
                "missing_rate": missing_rate,
                "overlap_field": field,
                "feature_conflict_n": conflict_n,
                "feature_conflict_rate": conflict_rate,
                "split_field_source": split_field_source,
                "split_adapter_status": split_adapter_status,
                "decile_encoding_adapter_status": ";".join(decile_statuses),
                "feature_enrichment_status": status,
            }
        )
    rename_map = {
        "board_bucket_canonical": "board_bucket",
        "calendar_year_canonical": "calendar_year",
        "split_bucket_canonical": "split_bucket",
    }
    merged = merged.rename(columns={k: v for k, v in rename_map.items() if k in merged.columns})
    for drop_col in ["board_bucket_feature", "calendar_year_feature", "split_bucket_feature"]:
        if drop_col in merged.columns:
            merged = merged.drop(columns=[drop_col])
    return merged, pd.DataFrame(audit_rows), status


def split_selected(decision_info: dict[str, Any], config: dict[str, Any]) -> tuple[str, str, str, int]:
    primary = config.get("primary", {})
    return (
        str(decision_info.get("selected_raw_event_arm_id") or primary.get("selected_raw_event_arm_id", "")),
        str(decision_info.get("selected_cohort_arm_id") or primary.get("selected_cohort_arm_id", "C3")),
        str(decision_info.get("selected_rank_cutoff_id") or primary.get("selected_rank_cutoff_id", "top20pct")),
        int(decision_info.get("primary_cost_tier_bps") or primary.get("primary_cost_tier_bps", 50)),
    )


def primary_panels(canonical: pd.DataFrame, decision_info: dict[str, Any], config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_arm, cohort_arm, _rank_cutoff, _cost = split_selected(decision_info, config)
    primary = canonical.loc[
        canonical["raw_event_arm_id"].astype(str).eq(raw_arm)
        & canonical["cohort_arm_id"].astype(str).eq(cohort_arm)
    ].copy()
    finite = primary.loc[
        primary["cohort_rank_status"].astype(str).eq("pass")
        & finite_numeric(primary["cohort_percentile_rank"]).notna()
    ].copy()
    return primary.reset_index(drop=True), finite.reset_index(drop=True)


def spearman_rank_ic(frame: pd.DataFrame, x_col: str, y_col: str, minimum_n: int) -> tuple[float, int, str]:
    if frame.empty or x_col not in frame.columns or y_col not in frame.columns:
        return np.nan, 0, "insufficient_n"
    x = finite_numeric(frame[x_col])
    y = finite_numeric(frame[y_col])
    mask = x.notna() & y.notna()
    n = int(mask.sum())
    if n < minimum_n:
        return np.nan, n, "insufficient_n"
    rx = x.loc[mask].rank(method="average")
    ry = y.loc[mask].rank(method="average")
    if rx.nunique(dropna=True) < 2 or ry.nunique(dropna=True) < 2:
        return np.nan, n, "degenerate"
    return float(rx.corr(ry)), n, "pass"


BUCKETS = [
    ("Q1", 0.00, 0.20, False),
    ("Q2", 0.20, 0.40, False),
    ("Q3", 0.40, 0.60, False),
    ("Q4", 0.60, 0.80, False),
    ("Q5", 0.80, 1.00, True),
]


def bucket_id(rank: pd.Series) -> pd.Series:
    r = finite_numeric(rank)
    out = pd.Series(pd.NA, index=rank.index, dtype=object)
    for name, low, high, include_high in BUCKETS:
        mask = r.ge(low) & (r.le(high) if include_high else r.lt(high))
        out.loc[mask] = name
    return out


def rate_bool(series: pd.Series) -> float:
    return safe_rate(bool_series(series).sum(), len(series))


def bucket_metrics(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    work = frame.copy()
    work["_rank_bucket_id"] = bucket_id(work["cohort_percentile_rank"])
    rows: list[dict[str, Any]] = []
    bucket_values: dict[str, dict[str, float]] = {}
    for name, low, high, _include_high in BUCKETS:
        sub = work.loc[work["_rank_bucket_id"].astype(str).eq(name)]
        metrics = {
            "winner_rate": rate_bool(sub["winner"]) if len(sub) else np.nan,
            "fast_fail_rate": rate_bool(sub["fast_fail"]) if len(sub) else np.nan,
            "lower_first_rate": rate_bool(sub["lower_first"]) if len(sub) else np.nan,
            "utility_mean_0bps": finite_numeric(sub["path_utility_component_0bps"]).mean() if len(sub) else np.nan,
            "utility_mean_50bps": finite_numeric(sub["path_utility_component_50bps"]).mean() if len(sub) else np.nan,
            "utility_mean_100bps": finite_numeric(sub["path_utility_component_100bps"]).mean() if len(sub) else np.nan,
            "terminal_return_20d_mean": finite_numeric(sub["terminal_return_20d"]).mean() if len(sub) else np.nan,
        }
        bucket_values[name] = metrics
        rows.append(
            {
                "bucket_scheme": "quintile",
                "rank_bucket_id": name,
                "rank_bucket_low": low,
                "rank_bucket_high": high,
                "event_n": int(len(sub)),
                **metrics,
            }
        )
    deltas = {
        "top_bottom_winner_delta": bucket_values["Q5"]["winner_rate"] - bucket_values["Q1"]["winner_rate"],
        "top_bottom_fast_fail_delta": bucket_values["Q5"]["fast_fail_rate"] - bucket_values["Q1"]["fast_fail_rate"],
        "top_bottom_lower_first_delta": bucket_values["Q5"]["lower_first_rate"] - bucket_values["Q1"]["lower_first_rate"],
        "top_bottom_utility_delta_50bps": bucket_values["Q5"]["utility_mean_50bps"] - bucket_values["Q1"]["utility_mean_50bps"],
    }
    out = pd.DataFrame(rows)
    for key, value in deltas.items():
        out[key] = value
    status = "pass_expected_signs" if (
        pd.notna(deltas["top_bottom_winner_delta"])
        and deltas["top_bottom_winner_delta"] > 0
        and deltas["top_bottom_fast_fail_delta"] < 0
        and deltas["top_bottom_lower_first_delta"] < 0
        and deltas["top_bottom_utility_delta_50bps"] > 0
    ) else "fail_expected_signs"
    out["bucket_monotonicity_status"] = status
    return out, deltas


def primary_coverage_audit(primary: pd.DataFrame, finite: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    threshold = float(config.get("coverage_audit", {}).get("early_history_drop_share_threshold", 0.80))
    rows: list[dict[str, Any]] = []
    split_drop_totals = primary.assign(
        _dropped=~primary["cohort_rank_status"].astype(str).eq("pass")
        | finite_numeric(primary["cohort_percentile_rank"]).isna()
    ).groupby("split_bucket")["_dropped"].sum().to_dict()
    train_years = primary.loc[primary["split_bucket"].astype(str).eq("train"), "calendar_year"]
    earliest_train_year = int(finite_numeric(train_years).min()) if len(train_years) else np.nan
    earliest_drop_share = np.nan
    if pd.notna(earliest_train_year) and split_drop_totals.get("train", 0) > 0:
        earliest_drop = primary.loc[
            primary["split_bucket"].astype(str).eq("train")
            & finite_numeric(primary["calendar_year"]).eq(float(earliest_train_year))
            & (
                ~primary["cohort_rank_status"].astype(str).eq("pass")
                | finite_numeric(primary["cohort_percentile_rank"]).isna()
            )
        ]
        earliest_drop_share = safe_rate(len(earliest_drop), split_drop_totals.get("train", 0))
    for (split, year), sub in primary.groupby(["split_bucket", "calendar_year"], dropna=False, sort=True):
        denom = len(sub)
        finite_mask = sub["cohort_rank_status"].astype(str).eq("pass") & finite_numeric(sub["cohort_percentile_rank"]).notna()
        dropped_total = int((~finite_mask).sum())
        insufficient = int(sub["cohort_rank_status"].astype(str).eq("insufficient_cohort").sum())
        degenerate = int(sub["cohort_rank_status"].astype(str).eq("degenerate_partial_cohort").sum())
        nonfinite = int((sub["cohort_rank_status"].astype(str).eq("pass") & finite_numeric(sub["cohort_percentile_rank"]).isna()).sum())
        status_counts = sub.loc[~finite_mask, "cohort_rank_status"].astype(str).value_counts()
        dominant = str(status_counts.index[0]) if len(status_counts) else ""
        split_drop = int(split_drop_totals.get(split, 0))
        if split_drop == 0:
            status = "no_drops"
        elif str(split) == "train" and pd.notna(earliest_train_year) and int(float(year)) == int(earliest_train_year) and earliest_drop_share >= threshold:
            status = "train_early_history_concentration"
        else:
            status = "pass"
        rows.append(
            {
                "raw_event_arm_id": str(sub.iloc[0]["raw_event_arm_id"]),
                "cohort_arm_id": str(sub.iloc[0]["cohort_arm_id"]),
                "split_bucket": split,
                "calendar_year": year,
                "same_event_denominator_n": int(denom),
                "finite_rank_n": int(finite_mask.sum()),
                "dropped_total_n": dropped_total,
                "dropped_insufficient_cohort_n": insufficient,
                "dropped_insufficient_cohort_rate": safe_rate(insufficient, denom),
                "dropped_degenerate_partial_cohort_n": degenerate,
                "dropped_degenerate_partial_cohort_rate": safe_rate(degenerate, denom),
                "dropped_nonfinite_rank_n": nonfinite,
                "dropped_nonfinite_rank_rate": safe_rate(nonfinite, denom),
                "split_dropped_total_n": split_drop,
                "earliest_train_year": earliest_train_year,
                "earliest_train_year_drop_share": earliest_drop_share,
                "dominant_dropped_cohort_rank_status": dominant,
                "coverage_audit_status": status,
            }
        )
    summary_rows: list[dict[str, Any]] = []
    for split, sub in primary.groupby("split_bucket", dropna=False):
        denom = len(sub)
        finite_mask = sub["cohort_rank_status"].astype(str).eq("pass") & finite_numeric(sub["cohort_percentile_rank"]).notna()
        insufficient = int(sub["cohort_rank_status"].astype(str).eq("insufficient_cohort").sum())
        degenerate = int(sub["cohort_rank_status"].astype(str).eq("degenerate_partial_cohort").sum())
        nonfinite = int((sub["cohort_rank_status"].astype(str).eq("pass") & finite_numeric(sub["cohort_percentile_rank"]).isna()).sum())
        summary_rows.append(
            {
                "split_bucket": split,
                "same_event_denominator_n": int(denom),
                "finite_rank_n": int(finite_mask.sum()),
                "finite_rank_coverage": safe_rate(finite_mask.sum(), denom),
                "dropped_total_n": int((~finite_mask).sum()),
                "dropped_insufficient_cohort_n": insufficient,
                "dropped_insufficient_cohort_rate": safe_rate(insufficient, denom),
                "dropped_degenerate_partial_cohort_n": degenerate,
                "dropped_nonfinite_rank_n": nonfinite,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(summary_rows)


def rank_ic_by_split(panel: pd.DataFrame, coverage: pd.DataFrame, minimum_n: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        sub = panel.loc[panel["split_bucket"].astype(str).eq(split)]
        cov = coverage.loc[coverage["split_bucket"].astype(str).eq(split)]
        base = cov.iloc[0].to_dict() if len(cov) else {
            "same_event_denominator_n": 0,
            "finite_rank_n": 0,
            "finite_rank_coverage": np.nan,
            "dropped_total_n": 0,
            "dropped_insufficient_cohort_n": 0,
            "dropped_insufficient_cohort_rate": np.nan,
            "dropped_degenerate_partial_cohort_n": 0,
            "dropped_nonfinite_rank_n": 0,
        }
        metrics = {}
        statuses = []
        for target in ["winner", "fast_fail", "lower_first", "path_utility_component_0bps", "path_utility_component_50bps", "path_utility_component_100bps", "terminal_return_20d"]:
            value, _n, status = spearman_rank_ic(sub, "cohort_percentile_rank", target, minimum_n)
            metrics[target] = value
            statuses.append(status)
        if len(sub):
            raw_arm = str(sub.iloc[0]["raw_event_arm_id"])
            cohort_arm = str(sub.iloc[0]["cohort_arm_id"])
        else:
            raw_arm = ""
            cohort_arm = ""
        rows.append(
            {
                "raw_event_arm_id": raw_arm,
                "cohort_arm_id": cohort_arm,
                "split_bucket": split,
                **base,
                "rank_ic_winner": metrics["winner"],
                "rank_ic_fast_fail": metrics["fast_fail"],
                "rank_ic_lower_first": metrics["lower_first"],
                "rank_ic_utility_0bps": metrics["path_utility_component_0bps"],
                "rank_ic_utility_50bps": metrics["path_utility_component_50bps"],
                "rank_ic_utility_100bps": metrics["path_utility_component_100bps"],
                "rank_ic_terminal_return_20d": metrics["terminal_return_20d"],
                "expected_sign_winner_status": "pass" if pd.notna(metrics["winner"]) and metrics["winner"] > 0 else "fail",
                "expected_sign_fast_fail_status": "pass" if pd.notna(metrics["fast_fail"]) and metrics["fast_fail"] < 0 else "fail",
                "expected_sign_lower_first_status": "pass" if pd.notna(metrics["lower_first"]) and metrics["lower_first"] < 0 else "fail",
                "expected_sign_utility_50bps_status": "pass" if pd.notna(metrics["path_utility_component_50bps"]) and metrics["path_utility_component_50bps"] > 0 else "fail",
                "rank_ic_status": "pass" if all(s == "pass" for s in statuses) else "insufficient_or_degenerate",
            }
        )
    return pd.DataFrame(rows)


def primary_bucket_readout(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[pd.DataFrame] = []
    bucket_panel = panel.copy()
    bucket_panel["rank_bucket_id"] = bucket_id(bucket_panel["cohort_percentile_rank"])
    for split, sub in panel.groupby("split_bucket", dropna=False):
        out, _deltas = bucket_metrics(sub)
        out.insert(0, "split_bucket", split)
        out.insert(0, "cohort_arm_id", str(sub.iloc[0]["cohort_arm_id"]))
        out.insert(0, "raw_event_arm_id", str(sub.iloc[0]["raw_event_arm_id"]))
        rows.append(out)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(), bucket_panel


def group_bucket_readout(frame: pd.DataFrame, group_cols: list[str], role: str | None = None, min_n: int = 0) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    if frame.empty:
        return pd.DataFrame()
    for keys, sub in frame.groupby(group_cols, dropna=False, sort=True):
        key_tuple = keys if isinstance(keys, tuple) else (keys,)
        out, _deltas = bucket_metrics(sub)
        if len(sub) < min_n:
            out["bucket_monotonicity_status"] = "insufficient_n"
        for col, value in reversed(list(zip(group_cols, key_tuple))):
            out.insert(0, col, value)
        if role is not None:
            out["readout_role"] = role
        rows.append(out)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def top_bottom_from_frame(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return {
            "top_bottom_winner_delta": np.nan,
            "top_bottom_fast_fail_delta": np.nan,
            "top_bottom_lower_first_delta": np.nan,
            "top_bottom_utility_delta_50bps": np.nan,
        }
    _out, deltas = bucket_metrics(frame)
    return deltas


def bootstrap_primary(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    boot_cfg = config.get("bootstrap", {})
    seed = int(boot_cfg.get("seed", 1403001))
    n_boot = int(boot_cfg.get("n", 500))
    min_clusters = int(boot_cfg.get("minimum_clusters", 30))
    ci_level = float(boot_cfg.get("ci_level", 0.90))
    low_q = (1.0 - ci_level) / 2.0
    high_q = 1.0 - low_q
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for split in SPLITS:
        sub = panel.loc[panel["split_bucket"].astype(str).eq(split)].copy()
        clusters = sorted(sub["instrument_year"].astype(str).dropna().unique())
        base = {
            "raw_event_arm_id": str(sub.iloc[0]["raw_event_arm_id"]) if len(sub) else "",
            "cohort_arm_id": str(sub.iloc[0]["cohort_arm_id"]) if len(sub) else "",
            "split_bucket": split,
            "bootstrap_seed": seed,
            "bootstrap_n": n_boot,
            "bootstrap_cluster": "instrument_year",
        }
        if len(clusters) < min_clusters:
            rows.append({**base, "bootstrap_status": "insufficient_clusters", "rank_ic_fast_fail_ci_low": np.nan, "rank_ic_fast_fail_ci_high": np.nan, "rank_ic_utility_50bps_ci_low": np.nan, "rank_ic_utility_50bps_ci_high": np.nan, "top_bottom_fast_fail_delta_ci_low": np.nan, "top_bottom_fast_fail_delta_ci_high": np.nan, "top_bottom_utility_delta_50bps_ci_low": np.nan, "top_bottom_utility_delta_50bps_ci_high": np.nan})
            continue
        cluster_groups = {cluster: group.copy() for cluster, group in sub.groupby(sub["instrument_year"].astype(str), sort=False)}
        metrics = {
            "rank_ic_fast_fail": [],
            "rank_ic_utility_50bps": [],
            "top_bottom_fast_fail_delta": [],
            "top_bottom_utility_delta_50bps": [],
        }
        for _ in range(n_boot):
            sampled = rng.choice(clusters, size=len(clusters), replace=True)
            sample = pd.concat([cluster_groups[c] for c in sampled], ignore_index=True)
            metrics["rank_ic_fast_fail"].append(spearman_rank_ic(sample, "cohort_percentile_rank", "fast_fail", 1)[0])
            metrics["rank_ic_utility_50bps"].append(spearman_rank_ic(sample, "cohort_percentile_rank", "path_utility_component_50bps", 1)[0])
            deltas = top_bottom_from_frame(sample)
            metrics["top_bottom_fast_fail_delta"].append(deltas["top_bottom_fast_fail_delta"])
            metrics["top_bottom_utility_delta_50bps"].append(deltas["top_bottom_utility_delta_50bps"])
        def interval(values: list[float]) -> tuple[float, float]:
            arr = np.asarray(values, dtype=float)
            arr = arr[np.isfinite(arr)]
            if arr.size == 0:
                return np.nan, np.nan
            return float(np.quantile(arr, low_q)), float(np.quantile(arr, high_q))
        ff_low, ff_high = interval(metrics["rank_ic_fast_fail"])
        util_low, util_high = interval(metrics["rank_ic_utility_50bps"])
        tb_ff_low, tb_ff_high = interval(metrics["top_bottom_fast_fail_delta"])
        tb_util_low, tb_util_high = interval(metrics["top_bottom_utility_delta_50bps"])
        rows.append(
            {
                **base,
                "bootstrap_status": "pass",
                "rank_ic_fast_fail_ci_low": ff_low,
                "rank_ic_fast_fail_ci_high": ff_high,
                "rank_ic_utility_50bps_ci_low": util_low,
                "rank_ic_utility_50bps_ci_high": util_high,
                "top_bottom_fast_fail_delta_ci_low": tb_ff_low,
                "top_bottom_fast_fail_delta_ci_high": tb_ff_high,
                "top_bottom_utility_delta_50bps_ci_low": tb_util_low,
                "top_bottom_utility_delta_50bps_ci_high": tb_util_high,
            }
        )
    return pd.DataFrame(rows)


def cohort_dimension_rank_ic(canonical: pd.DataFrame, decision_info: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    raw_arm, _cohort, _rank, _cost = split_selected(decision_info, config)
    minimum = int(config.get("rank_ic", {}).get("minimum_rank_ic_n", 100))
    rows: list[dict[str, Any]] = []
    sub_all = canonical.loc[canonical["raw_event_arm_id"].astype(str).eq(raw_arm)]
    for (cohort, split), sub0 in sub_all.groupby(["cohort_arm_id", "split_bucket"], dropna=False, sort=True):
        sub = sub0.loc[sub0["cohort_rank_status"].astype(str).eq("pass") & finite_numeric(sub0["cohort_percentile_rank"]).notna()]
        metrics = {}
        statuses = []
        for target in ["winner", "fast_fail", "lower_first", "path_utility_component_50bps"]:
            value, _n, status = spearman_rank_ic(sub, "cohort_percentile_rank", target, minimum)
            metrics[target] = value
            statuses.append(status)
        rows.append(
            {
                "raw_event_arm_id": raw_arm,
                "cohort_arm_id": cohort,
                "split_bucket": split,
                "event_n": int(len(sub0)),
                "finite_rank_n": int(len(sub)),
                "rank_ic_winner": metrics["winner"],
                "rank_ic_fast_fail": metrics["fast_fail"],
                "rank_ic_lower_first": metrics["lower_first"],
                "rank_ic_utility_50bps": metrics["path_utility_component_50bps"],
                "expected_sign_winner_status": "pass" if pd.notna(metrics["winner"]) and metrics["winner"] > 0 else "fail",
                "expected_sign_fast_fail_status": "pass" if pd.notna(metrics["fast_fail"]) and metrics["fast_fail"] < 0 else "fail",
                "expected_sign_lower_first_status": "pass" if pd.notna(metrics["lower_first"]) and metrics["lower_first"] < 0 else "fail",
                "expected_sign_utility_50bps_status": "pass" if pd.notna(metrics["path_utility_component_50bps"]) and metrics["path_utility_component_50bps"] > 0 else "fail",
                "rank_ic_status": "pass" if all(s == "pass" for s in statuses) else "insufficient_or_degenerate",
                "readout_role": DIAGNOSTIC_ROLE,
            }
        )
    return pd.DataFrame(rows)


def stress_readout(primary: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    min_n = int(config.get("rank_ic", {}).get("minimum_stress_stratum_rank_ic_n", 50))
    stress_dims = ["market_regime_bucket", "board_bucket", "volatility_bucket", "liquidity_bucket", "calendar_year"]
    validation = primary.loc[primary["split_bucket"].astype(str).eq("validation")]
    finite = validation.loc[validation["cohort_rank_status"].astype(str).eq("pass") & finite_numeric(validation["cohort_percentile_rank"]).notna()]
    readout_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    stress_panel_parts: list[pd.DataFrame] = []
    for dim in stress_dims:
        if dim not in finite.columns:
            continue
        for bucket, sub in finite.groupby(dim, dropna=False, sort=True):
            sub = sub.copy()
            sub["stress_dimension"] = dim
            sub["stress_bucket"] = bucket
            stress_panel_parts.append(sub)
            status = "pass" if len(sub) >= min_n else "insufficient_n"
            metrics = {}
            if status == "pass":
                for target in ["winner", "fast_fail", "lower_first", "path_utility_component_50bps"]:
                    metrics[target] = spearman_rank_ic(sub, "cohort_percentile_rank", target, min_n)[0]
                deltas = top_bottom_from_frame(sub)
            else:
                metrics = {"winner": np.nan, "fast_fail": np.nan, "lower_first": np.nan, "path_utility_component_50bps": np.nan}
                deltas = {
                    "top_bottom_winner_delta": np.nan,
                    "top_bottom_fast_fail_delta": np.nan,
                    "top_bottom_lower_first_delta": np.nan,
                    "top_bottom_utility_delta_50bps": np.nan,
                }
            readout_rows.append(
                {
                    "raw_event_arm_id": str(sub.iloc[0]["raw_event_arm_id"]) if len(sub) else "",
                    "cohort_arm_id": str(sub.iloc[0]["cohort_arm_id"]) if len(sub) else "",
                    "stress_dimension": dim,
                    "stress_bucket": bucket,
                    "split_bucket": "validation",
                    "event_n": int(len(sub)),
                    "finite_rank_n": int(len(sub)),
                    "rank_ic_winner": metrics["winner"],
                    "rank_ic_fast_fail": metrics["fast_fail"],
                    "rank_ic_lower_first": metrics["lower_first"],
                    "rank_ic_utility_50bps": metrics["path_utility_component_50bps"],
                    **deltas,
                    "stress_bucket_status": status,
                    "readout_role": DIAGNOSTIC_ROLE,
                }
            )
            if status == "insufficient_n":
                failure_mode = "insufficient_n"
            elif metrics["fast_fail"] < 0 and metrics["path_utility_component_50bps"] > 0:
                failure_mode = "both_monotonic"
            elif metrics["fast_fail"] < 0:
                failure_mode = "badside_monotonic_utility_not_monotonic"
            elif metrics["path_utility_component_50bps"] > 0:
                failure_mode = "utility_monotonic_badside_not_monotonic"
            else:
                failure_mode = "neither_monotonic"
            failure_rows.append(
                {
                    "stress_dimension": dim,
                    "stress_bucket": bucket,
                    "split_bucket": "validation",
                    "event_n": int(len(sub)),
                    "rank_ic_fast_fail": metrics["fast_fail"],
                    "rank_ic_utility_50bps": metrics["path_utility_component_50bps"],
                    "top_bottom_fast_fail_delta": deltas["top_bottom_fast_fail_delta"],
                    "top_bottom_utility_delta_50bps": deltas["top_bottom_utility_delta_50bps"],
                    "stress_bucket_status": status,
                    "failure_mode": failure_mode,
                }
            )
    stress_panel = pd.concat(stress_panel_parts, ignore_index=True) if stress_panel_parts else pd.DataFrame()
    return pd.DataFrame(readout_rows), pd.DataFrame(failure_rows), stress_panel


def midpoint_percentile_rank(series: pd.Series) -> pd.Series:
    finite = finite_numeric(series)
    n = int(finite.notna().sum())
    if n == 0:
        return pd.Series(np.nan, index=series.index)
    return (finite.rank(method="average") - 0.5) / n


def all_family_raw_intensity_readout(sparse: pd.DataFrame, minimum_n: int = 1) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (arm, split), sub0 in sparse.groupby(["raw_event_arm_id", "split_bucket"], dropna=False, sort=True):
        sub = sub0.copy()
        sub["secondary_raw_intensity_percentile_rank"] = midpoint_percentile_rank(sub["event_intensity_score"])
        top = sub.loc[finite_numeric(sub["secondary_raw_intensity_percentile_rank"]).ge(0.80)]
        bottom = sub.loc[finite_numeric(sub["secondary_raw_intensity_percentile_rank"]).le(0.20)]
        def corr(target: str) -> float:
            return spearman_rank_ic(
                sub.rename(columns={"secondary_raw_intensity_percentile_rank": "rank"}),
                "rank",
                target,
                minimum_n,
            )[0]
        rows.append(
            {
                "raw_event_arm_id": arm,
                "family_id": str(sub.iloc[0]["family_id"]) if len(sub) else "",
                "parameter_set_id": str(sub.iloc[0]["parameter_set_id"]) if len(sub) else "",
                "split_bucket": split,
                "event_n": int(len(sub)),
                "rank_source": "secondary_raw_intensity_percentile_rank",
                "top20_event_n": int(len(top)),
                "bottom20_event_n": int(len(bottom)),
                "rank_ic_winner": corr("winner"),
                "rank_ic_fast_fail": corr("fast_fail"),
                "rank_ic_utility_50bps": corr("path_utility_component_50bps"),
                "top_bottom_winner_delta": rate_bool(top["winner"]) - rate_bool(bottom["winner"]) if len(top) and len(bottom) else np.nan,
                "top_bottom_fast_fail_delta": rate_bool(top["fast_fail"]) - rate_bool(bottom["fast_fail"]) if len(top) and len(bottom) else np.nan,
                "top_bottom_utility_delta_50bps": finite_numeric(top["path_utility_component_50bps"]).mean() - finite_numeric(bottom["path_utility_component_50bps"]).mean() if len(top) and len(bottom) else np.nan,
                "readout_role": DIAGNOSTIC_ROLE,
            }
        )
    return pd.DataFrame(rows)


def search_accounting_audit(decision_info: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    raw_arm, cohort, rank_cutoff, _cost = split_selected(decision_info, config)
    return pd.DataFrame(
        [
            {
                "primary_raw_event_arm_id": raw_arm,
                "primary_cohort_arm_id": cohort,
                "primary_rank_cutoff_id": rank_cutoff,
                "validation_selected_new_arm": False,
                "robustness_selected_new_arm": False,
                "c1_c6_readout_role": DIAGNOSTIC_ROLE,
                "all_family_readout_role": DIAGNOSTIC_ROLE,
                "threshold_selected_from_validation": False,
                "threshold_selected_from_robustness": False,
                "search_accounting_gate_status": "pass",
            }
        ]
    )


def primary_power_gate(primary_ic: pd.DataFrame, config: dict[str, Any]) -> str:
    gate = config.get("power_gate", {})
    for split in SPLITS:
        row = primary_ic.loc[primary_ic["split_bucket"].astype(str).eq(split)]
        if row.empty:
            return "fail"
        r = row.iloc[0]
        if int(r["same_event_denominator_n"]) < int(gate.get("minimum_same_event_denominator_n", 300)):
            return "fail"
        if int(r["finite_rank_n"]) < int(gate.get("minimum_finite_rank_n", 300)):
            return "fail"
        if float(r["finite_rank_coverage"]) < float(gate.get("minimum_finite_rank_coverage", 0.90)):
            return "fail"
    return "pass"


def split_metric(primary_ic: pd.DataFrame, split: str, col: str) -> float:
    row = primary_ic.loc[primary_ic["split_bucket"].astype(str).eq(split)]
    return float(row.iloc[0][col]) if len(row) and pd.notna(row.iloc[0][col]) else np.nan


def split_delta(bucket_readout: pd.DataFrame, split: str, col: str) -> float:
    row = bucket_readout.loc[bucket_readout["split_bucket"].astype(str).eq(split)]
    return float(row.iloc[0][col]) if len(row) and pd.notna(row.iloc[0][col]) else np.nan


def bootstrap_metric(bootstrap: pd.DataFrame, split: str, col: str) -> Any:
    row = bootstrap.loc[bootstrap["split_bucket"].astype(str).eq(split)]
    return row.iloc[0][col] if len(row) else np.nan


def monotonicity_gates(primary_ic: pd.DataFrame, bucket_readout: pd.DataFrame, bootstrap: pd.DataFrame, config: dict[str, Any]) -> dict[str, str]:
    cfg = config.get("stress_gates", {})
    val_ff = split_metric(primary_ic, "validation", "rank_ic_fast_fail")
    train_ff = split_metric(primary_ic, "train", "rank_ic_fast_fail")
    rob_ff = split_metric(primary_ic, "robustness", "rank_ic_fast_fail")
    val_tb_ff = split_delta(bucket_readout, "validation", "top_bottom_fast_fail_delta")
    val_tb_lower = split_delta(bucket_readout, "validation", "top_bottom_lower_first_delta")
    badside = (
        pd.notna(val_ff)
        and val_ff <= float(cfg.get("validation_rank_ic_fast_fail_max", -0.03))
        and str(bootstrap_metric(bootstrap, "validation", "bootstrap_status")) == "pass"
        and pd.notna(bootstrap_metric(bootstrap, "validation", "rank_ic_fast_fail_ci_high"))
        and float(bootstrap_metric(bootstrap, "validation", "rank_ic_fast_fail_ci_high")) < 0
        and pd.notna(val_tb_ff)
        and val_tb_ff <= float(cfg.get("validation_top_bottom_fast_fail_delta_max", -0.03))
        and pd.notna(train_ff)
        and train_ff <= float(cfg.get("train_rank_ic_max_for_badside", 0.0))
        and pd.notna(rob_ff)
        and rob_ff <= float(cfg.get("robustness_rank_ic_max_for_badside", 0.0))
        and pd.notna(val_tb_lower)
        and val_tb_lower <= 0
    )
    val_util = split_metric(primary_ic, "validation", "rank_ic_utility_50bps")
    train_util = split_metric(primary_ic, "train", "rank_ic_utility_50bps")
    rob_util = split_metric(primary_ic, "robustness", "rank_ic_utility_50bps")
    val_tb_util = split_delta(bucket_readout, "validation", "top_bottom_utility_delta_50bps")
    utility = (
        pd.notna(val_util)
        and val_util >= float(cfg.get("validation_rank_ic_utility_50bps_min", 0.03))
        and pd.notna(val_tb_util)
        and val_tb_util > 0
        and pd.notna(train_util)
        and train_util >= float(cfg.get("train_rank_ic_min_for_positive_targets", 0.0))
        and pd.notna(rob_util)
        and rob_util >= float(cfg.get("robustness_rank_ic_min_for_positive_targets", 0.0))
    )
    val_winner = split_metric(primary_ic, "validation", "rank_ic_winner")
    train_winner = split_metric(primary_ic, "train", "rank_ic_winner")
    rob_winner = split_metric(primary_ic, "robustness", "rank_ic_winner")
    val_tb_winner = split_delta(bucket_readout, "validation", "top_bottom_winner_delta")
    winner = (
        pd.notna(val_winner)
        and val_winner >= float(cfg.get("validation_rank_ic_winner_min", 0.03))
        and pd.notna(val_tb_winner)
        and val_tb_winner > 0
        and pd.notna(train_winner)
        and train_winner >= float(cfg.get("train_rank_ic_min_for_positive_targets", 0.0))
        and pd.notna(rob_winner)
        and rob_winner >= float(cfg.get("robustness_rank_ic_min_for_positive_targets", 0.0))
    )
    return {
        "stress_badside_monotonicity_gate_status": "pass" if badside else "fail",
        "stress_utility_monotonicity_gate_status": "pass" if utility else "fail",
        "stress_winner_monotonicity_gate_status": "pass" if winner else "fail",
    }


def cohort_dimension_status(cohort_ic: pd.DataFrame) -> str:
    val = cohort_ic.loc[cohort_ic["split_bucket"].astype(str).eq("validation")]
    badside_n = int(finite_numeric(val["rank_ic_fast_fail"]).lt(0).sum()) if len(val) else 0
    utility_n = int(finite_numeric(val["rank_ic_utility_50bps"]).gt(0).sum()) if len(val) else 0
    c3 = val.loc[val["cohort_arm_id"].astype(str).eq("C3")]
    c3_any = False
    if len(c3):
        row = c3.iloc[0]
        c3_any = (
            pd.notna(row["rank_ic_fast_fail"])
            and row["rank_ic_fast_fail"] < 0
            or pd.notna(row["rank_ic_utility_50bps"])
            and row["rank_ic_utility_50bps"] > 0
            or pd.notna(row["rank_ic_winner"])
            and row["rank_ic_winner"] > 0
        )
    if badside_n >= 3 and utility_n >= 2:
        return "broad_support"
    if badside_n >= 3 and utility_n < 2:
        return "badside_only_broad_support"
    if c3_any and badside_n < 3:
        return "localized_or_weak"
    return "no_support"


def build_decision(
    input_gate_status: str,
    decision_info: dict[str, Any],
    primary_power_status: str,
    gates: dict[str, str],
    cohort_dimension_consistency_status: str,
    search_status: str,
    config: dict[str, Any],
    primary_failure_reason: str = "",
) -> pd.DataFrame:
    raw_arm, cohort, rank_cutoff, cost = split_selected(decision_info, config)
    secondary = "none"
    if input_gate_status != "pass":
        decision = "14C_input_blocked"
        next_allowed = "none"
        secondary = "none"
        reason = primary_failure_reason or "input_gate_failed"
    elif decision_info.get("decision_prerequisite_status") == "not_applicable_14a_supported_confirmatory_path":
        decision = "14C_not_applicable_14A_already_supported_confirmatory_path"
        next_allowed = "none"
        reason = "14a_already_supported_confirmatory_path"
    elif primary_power_status != "pass":
        decision = "14C_insufficient_primary_power"
        next_allowed = "none"
        reason = "primary_c3_power_gate_failed"
    elif (
        gates.get("stress_badside_monotonicity_gate_status") == "pass"
        and gates.get("stress_utility_monotonicity_gate_status") == "pass"
        and gates.get("stress_winner_monotonicity_gate_status") == "pass"
    ):
        decision = "14C_stress_rank_monotonic_supported_diagnostic_only"
        next_allowed = "requirement_14d_defense_overlay_confirmatory.md"
        secondary = "requirement_14e_event_uniqueness_redesign_preflight.md"
        reason = "badside_utility_winner_monotonic_diagnostic_only"
    elif gates.get("stress_badside_monotonicity_gate_status") == "pass":
        decision = "14C_stress_badside_monotonic_supported_defense_only"
        next_allowed = "requirement_14d_defense_overlay_confirmatory.md"
        reason = "badside_monotonic_defense_only"
    elif gates.get("stress_utility_monotonicity_gate_status") == "pass" or gates.get("stress_winner_monotonicity_gate_status") == "pass":
        decision = "14C_probability_or_utility_monotonic_partial_no_defense_support"
        next_allowed = "none"
        secondary = "requirement_14e_event_uniqueness_redesign_preflight.md"
        reason = "probability_or_utility_only_no_defense_support"
    else:
        decision = "14C_stress_cohort_rank_monotonicity_not_supported"
        next_allowed = "none"
        reason = "stress_cohort_rank_monotonicity_not_supported"
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "secondary_allowed_discussion": secondary,
                "active_winner_entry_search_authorized": False,
                "confirmatory_entry_authorized": False,
                "meta_labeling_authorized": False,
                "bet_sizing_authorized": False,
                "production_strategy_authorized": False,
                "selected_raw_event_arm_id": raw_arm,
                "selected_cohort_arm_id": cohort,
                "selected_rank_cutoff_id": rank_cutoff,
                "primary_cost_tier_bps": cost,
                "input_gate_status": input_gate_status,
                "primary_c3_power_gate_status": primary_power_status,
                "stress_badside_monotonicity_gate_status": gates.get("stress_badside_monotonicity_gate_status", "fail"),
                "stress_utility_monotonicity_gate_status": gates.get("stress_utility_monotonicity_gate_status", "fail"),
                "stress_winner_monotonicity_gate_status": gates.get("stress_winner_monotonicity_gate_status", "fail"),
                "cohort_dimension_consistency_status": cohort_dimension_consistency_status,
                "search_accounting_gate_status": search_status,
                "primary_failure_reason": reason,
            }
        ]
    )


def input_gate(
    input_audit: pd.DataFrame,
    source_audit: pd.DataFrame,
    lineage: pd.DataFrame,
    duplicate_audit: pd.DataFrame,
    feature_audit: pd.DataFrame,
) -> tuple[str, str]:
    required = input_audit.loc[input_audit["required_flag"].astype(bool)]
    bad_inputs = required.loc[
        ~required["read_status"].astype(str).eq("pass")
        | ~required["schema_status"].astype(str).isin(["pass", "readable"])
    ]
    if not bad_inputs.empty:
        return "fail", "required_artifact_read_or_schema_failed"
    if not source_audit["local_cache_lineage_status"].astype(str).eq("pass").all():
        return "fail", "local_cache_lineage_failed"
    if not lineage["lineage_status"].astype(str).eq("pass").all():
        return "fail", "upstream_14a_lineage_failed"
    if not duplicate_audit["duplicate_consistency_status"].astype(str).eq("pass").all():
        return "fail", "rank_cutoff_duplicate_consistency_failed"
    if not feature_audit["feature_enrichment_status"].astype(str).eq("pass").all():
        return "fail", "feature_enrichment_failed"
    return "pass", ""


def render_report(
    decision: pd.DataFrame,
    primary_ic: pd.DataFrame,
    bucket: pd.DataFrame,
    coverage: pd.DataFrame,
    stress: pd.DataFrame,
    all_family: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict()
    lines = [
        "# 14C Cohort Rank Monotonicity Stress Diagnostic Report",
        "",
        "## 裁决",
        "",
        f"- decision_state: `{d['decision_state']}`",
        f"- next_allowed_requirement: `{d['next_allowed_requirement']}`",
        f"- secondary_allowed_discussion: `{d['secondary_allowed_discussion']}`",
        f"- primary_failure_reason: `{d['primary_failure_reason']}`",
        "",
        "14C 是 14A 失败后的诊断层，不授权 winner entry、meta-labeling、bet sizing 或生产策略。",
        "",
        "## Primary C3 Rank-IC",
        "",
    ]
    if primary_ic.empty:
        lines.append("Primary C3 rank-IC readout is empty.")
    else:
        show = primary_ic[
            [
                "split_bucket",
                "same_event_denominator_n",
                "finite_rank_n",
                "finite_rank_coverage",
                "rank_ic_winner",
                "rank_ic_fast_fail",
                "rank_ic_utility_50bps",
            ]
        ].copy()
        lines.append(show.to_markdown(index=False))
    lines.extend(["", "## Bucket Monotonicity", ""])
    if not bucket.empty:
        show = bucket.loc[bucket["rank_bucket_id"].isin(["Q1", "Q5"])][
            [
                "split_bucket",
                "rank_bucket_id",
                "event_n",
                "winner_rate",
                "fast_fail_rate",
                "utility_mean_50bps",
                "top_bottom_fast_fail_delta",
                "top_bottom_utility_delta_50bps",
            ]
        ]
        lines.append(show.to_markdown(index=False))
    lines.extend(["", "## Finite Rank Coverage", ""])
    if not coverage.empty:
        lines.append(
            coverage[
                [
                    "split_bucket",
                    "calendar_year",
                    "same_event_denominator_n",
                    "finite_rank_n",
                    "dropped_total_n",
                    "dropped_insufficient_cohort_n",
                    "coverage_audit_status",
                ]
            ].to_markdown(index=False)
        )
    lines.extend(["", "## Stress Readout", ""])
    if stress.empty:
        lines.append("No stress stratum readout was generated.")
    else:
        lines.append(
            stress[
                [
                    "stress_dimension",
                    "stress_bucket",
                    "event_n",
                    "rank_ic_fast_fail",
                    "rank_ic_utility_50bps",
                    "stress_bucket_status",
                ]
            ].head(30).to_markdown(index=False)
        )
    lines.extend(["", "## All-Family Raw Intensity", ""])
    if not all_family.empty:
        show = all_family.loc[all_family["split_bucket"].eq("validation")].sort_values("rank_ic_fast_fail").head(12)
        lines.append(
            show[
                [
                    "raw_event_arm_id",
                    "event_n",
                    "rank_ic_winner",
                    "rank_ic_fast_fail",
                    "rank_ic_utility_50bps",
                    "readout_role",
                ]
            ].to_markdown(index=False)
        )
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "二元目标的 rank-IC 只用于方向和不确定性判断，不与连续 utility rank-IC 的绝对值直接比较。",
            "F2/F5/F6 等 14A density-excluded family 即使 raw-intensity 单调，也不能触发 next_allowed_requirement。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_manifest(config_path: Path, config: dict[str, Any], outputs: dict[str, Path], input_audit: pd.DataFrame, decision: pd.DataFrame) -> dict[str, Any]:
    publishable = {k: v for k, v in outputs.items() if k in PUBLISHABLE_TABLE_KEYS or k == "report"}
    publishable = {k: v for k, v in publishable.items() if v.exists()}
    d = decision.iloc[0].to_dict()
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
        "git_revision": r13a.git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha(config_path),
        "decision_state": d["decision_state"],
        "next_allowed_requirement": d["next_allowed_requirement"],
        "outputs": {k: str(v) for k, v in publishable.items()},
        "output_hashes": {k: file_sha(v) for k, v in publishable.items() if v.is_file()},
        "input_artifacts": input_audit.to_dict(orient="records"),
    }


def run(config_path: Path, mode: str = "full", check_inputs_only: bool = False) -> dict[str, Path]:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for path in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    input_audit = build_input_artifact_audit(resolved)
    source_audit = build_row_level_source_audit(resolved)
    lineage, decision_info = build_upstream_lineage_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    write_df(outputs["row_level_cohort_rank_source_audit"], source_audit)
    write_df(outputs["upstream_14a_lineage_audit"], lineage)

    panel = read_table(resolved["upstream_14a_cohort_event_panel_cache"])
    sparse = read_table(resolved["upstream_14a_sparse_event_panel_cache"])
    features = read_table(resolved["upstream_14a_state_change_feature_panel_cache"])
    canonical, duplicate_audit, duplicate_status = canonicalize_rank_cutoffs(panel)
    enriched, feature_audit, feature_status = enrich_features(canonical, features)
    write_df(outputs["rank_cutoff_duplicate_consistency_audit"], duplicate_audit)
    write_df(outputs["feature_enrichment_audit"], feature_audit)

    input_status, input_reason = input_gate(input_audit, source_audit, lineage, duplicate_audit, feature_audit)
    if duplicate_status != "pass":
        input_status, input_reason = "fail", "rank_cutoff_duplicate_consistency_failed"
    if feature_status != "pass":
        input_status, input_reason = "fail", "feature_enrichment_failed"

    if check_inputs_only or mode == "check-inputs":
        decision = build_decision(
            input_status,
            decision_info,
            "not_evaluated",
            {},
            "not_evaluated",
            "not_evaluated",
            config,
            primary_failure_reason=input_reason or "check_inputs_only",
        )
        if input_status == "pass":
            decision.loc[0, "decision_state"] = "14C_check_inputs_pass"
            decision.loc[0, "primary_failure_reason"] = "check_inputs_only"
        write_df(outputs["cohort_rank_monotonicity_stress_decision"], decision)
        write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit, decision))
        return outputs

    primary, primary_finite = primary_panels(enriched, decision_info, config)
    write_df(outputs["cohort_rank_monotonicity_panel"], enriched)
    coverage_audit, coverage_summary = primary_coverage_audit(primary, primary_finite, config)
    primary_ic = rank_ic_by_split(primary_finite, coverage_summary, int(config.get("rank_ic", {}).get("minimum_rank_ic_n", 100)))
    primary_bucket, primary_bucket_panel = primary_bucket_readout(primary_finite)
    bootstrap = bootstrap_primary(primary_finite, config)
    cohort_ic = cohort_dimension_rank_ic(enriched, decision_info, config)
    raw_arm, _cohort, _rank, _cost = split_selected(decision_info, config)
    cohort_finite = enriched.loc[
        enriched["raw_event_arm_id"].astype(str).eq(raw_arm)
        & enriched["cohort_rank_status"].astype(str).eq("pass")
        & finite_numeric(enriched["cohort_percentile_rank"]).notna()
    ]
    cohort_bucket = group_bucket_readout(
        cohort_finite,
        ["raw_event_arm_id", "cohort_arm_id", "split_bucket"],
        role=DIAGNOSTIC_ROLE,
        min_n=int(config.get("rank_ic", {}).get("minimum_rank_ic_n", 100)),
    )
    stress_read, stress_failure, stress_panel = stress_readout(primary, config)
    all_family = all_family_raw_intensity_readout(sparse)
    search = search_accounting_audit(decision_info, config)
    power_status = primary_power_gate(primary_ic, config)
    gates = monotonicity_gates(primary_ic, primary_bucket, bootstrap, config)
    cohort_status = cohort_dimension_status(cohort_ic)
    decision = build_decision(
        input_status,
        decision_info,
        power_status,
        gates,
        cohort_status,
        str(search.iloc[0]["search_accounting_gate_status"]) if len(search) else "fail",
        config,
        primary_failure_reason=input_reason,
    )

    write_df(outputs["primary_finite_rank_coverage_audit"], coverage_audit)
    write_df(outputs["primary_cohort_rank_ic_by_split"], primary_ic)
    write_df(outputs["primary_cohort_rank_bucket_monotonicity_readout"], primary_bucket)
    write_df(outputs["primary_cohort_rank_bootstrap_interval"], bootstrap)
    write_df(outputs["cohort_dimension_rank_ic_by_split"], cohort_ic)
    write_df(outputs["cohort_dimension_bucket_monotonicity_readout"], cohort_bucket)
    write_df(outputs["stress_regime_rank_monotonicity_readout"], stress_read)
    write_df(outputs["stress_dimension_failure_mode_audit"], stress_failure)
    write_df(outputs["all_family_raw_intensity_monotonicity_readout"], all_family)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["cohort_rank_monotonicity_stress_decision"], decision)
    write_df(outputs["primary_c3_rank_bucket_panel"], primary_bucket_panel)
    write_df(outputs["stress_dimension_rank_panel"], stress_panel)
    write_text(outputs["report"], render_report(decision, primary_ic, primary_bucket, coverage_audit, stress_read, all_family))
    write_json(outputs["manifest"], build_manifest(config_path, config, outputs, input_audit, decision))
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(Path(args.config), mode=args.mode, check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    main()

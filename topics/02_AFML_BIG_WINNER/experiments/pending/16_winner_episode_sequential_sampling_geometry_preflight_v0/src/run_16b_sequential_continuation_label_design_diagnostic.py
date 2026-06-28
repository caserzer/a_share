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
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
SOURCE_EP15_ROOT = TOPIC_ROOT / "experiments" / "pending" / "15_path_defined_winner_episode_label_v0"
SOURCE_EP14_ROOT = TOPIC_ROOT / "experiments" / "pending" / "14_full_native_sparse_state_change_event_utility_preflight_v0"
SOURCE_EP13_ROOT = TOPIC_ROOT / "experiments" / "pending" / "13_full_pit_native_event_discovery_v0"
RUNNER_16A_PATH = EXPERIMENT_DIR / "src" / "run_16a_sequential_sampling_geometry_preflight.py"
SOURCE_ROOTS = {
    "SOURCE_EP16_ROOT": EXPERIMENT_DIR,
    "SOURCE_EP15_ROOT": SOURCE_EP15_ROOT,
    "SOURCE_EP14_ROOT": SOURCE_EP14_ROOT,
    "SOURCE_EP13_ROOT": SOURCE_EP13_ROOT,
}


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r16a = load_runner(RUNNER_16A_PATH, "run_16a_for_16b")
r15a = r16a.r15a
r15b = r16a.r15b

RUN_ID = "16B_sequential_continuation_label_design_diagnostic"
EXPERIMENT_ID = "16_winner_episode_sequential_sampling_geometry_preflight_v0"
PHASE_ID = "16B"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_16b_sequential_continuation_label_design_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

DECISION_READY = "16B_continuation_label_ready_for_separability_diagnostic"
DECISION_BLOCKED = "16B_continuation_label_blocked_by_input_or_lineage_failure"
NEXT_16C = "requirement_16c_sequential_continuation_separability_diagnostic.md"
UPSTREAM_READY = "16A_sampling_geometry_ready_for_sequential_label_design"
UPSTREAM_NEXT = "requirement_16b_sequential_continuation_label_design_diagnostic.md"
PRIMARY_LABEL_ID = "continuation_survival_h20_no_deep_drawdown"
SECONDARY_LABEL_ID = "continuation_progress_h20_positive_path"
STRESS_LABEL_ID = "continuation_survival_h20_no_episode_break"
KNOWN_FAILED_FAMILIES = (
    "choppy_reversal_winner",
    "late_rescue_winner",
    "jump_repricing_winner",
    "unclassified_mixed_path",
)
SPLITS = ("train", "validation", "robustness")
LABEL_PANEL_COLUMNS = [
    "step_id",
    "label_id",
    "threshold_id",
    "cluster_split_bucket",
    "instrument",
    "episode_cluster_id",
    "horizon_sessions",
    "step_index",
    "step_start_pos",
    "step_end_pos",
    "step_start_date",
    "step_end_date",
    "step_start_qfq_close",
    "step_end_qfq_close",
    "max_drawdown_from_step_start",
    "step_end_price_ratio_minus_one_for_label_rule",
    "continuation_positive",
    "continuation_negative",
    "continuation_neutral",
    "continuation_progress_positive",
    "continuation_survival_positive",
    "label_rule_status",
]
BASE_RATE_COLUMNS = [
    "label_id",
    "threshold_id",
    "cluster_split_bucket",
    "horizon_sessions",
    "labelable_step_n",
    "positive_step_n",
    "negative_step_n",
    "neutral_step_n",
    "positive_rate",
    "negative_rate",
    "neutral_rate",
    "effective_sample_size_nonoverlap",
    "positive_effective_sample_size",
    "negative_effective_sample_size",
    "episode_cluster_n",
    "anchor_n_reference_only",
    "base_rate_status",
]
OVERLAP_COLUMNS = [
    "label_id",
    "threshold_id",
    "known_failed_family",
    "overlap_source",
    "cluster_split_bucket",
    "horizon_sessions",
    "positive_step_n",
    "failed_family_positive_step_n",
    "failed_family_positive_share",
    "all_step_failed_family_share",
    "share_delta",
    "hard_projection_coverage",
    "soft_overlap_coverage",
    "soft_overlap_status",
    "overlap_status",
    "blocking_reason",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 16B sequential continuation label design diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    for alias, root in SOURCE_ROOTS.items():
        prefix = f"{alias}/"
        if text.startswith(prefix):
            return root / text[len(prefix) :]
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
        "upstream_16a_authorization_audit": TABLE_DIR / "upstream_16a_authorization_audit.csv",
        "step_lineage_adapter_audit": TABLE_DIR / "step_lineage_adapter_audit.csv",
        "step_materialization_audit": TABLE_DIR / "step_materialization_audit.csv",
        "qfq_price_source_audit": TABLE_DIR / "qfq_price_source_audit.csv",
        "price_path_completeness_audit": TABLE_DIR / "price_path_completeness_audit.csv",
        "label_rule_definition_audit": TABLE_DIR / "label_rule_definition_audit.csv",
        "continuation_label_panel_readout": TABLE_DIR / "continuation_label_panel_readout.csv",
        "continuation_label_base_rate_readout": TABLE_DIR / "continuation_label_base_rate_readout.csv",
        "continuation_label_by_split_readout": TABLE_DIR / "continuation_label_by_split_readout.csv",
        "continuation_label_by_horizon_sensitivity_readout": TABLE_DIR / "continuation_label_by_horizon_sensitivity_readout.csv",
        "continuation_label_by_threshold_sensitivity_readout": TABLE_DIR / "continuation_label_by_threshold_sensitivity_readout.csv",
        "known_failed_overlap_readout": TABLE_DIR / "known_failed_overlap_readout.csv",
        "validation_stress_readout": TABLE_DIR / "validation_stress_readout.csv",
        "effective_sample_label_support_readout": TABLE_DIR / "effective_sample_label_support_readout.csv",
        "sequential_continuation_label_decision": TABLE_DIR / "sequential_continuation_label_decision.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "continuation_label_step_panel": LOCAL_CACHE_DIR / "continuation_label_step_panel.parquet",
        "materialized_step_panel": LOCAL_CACHE_DIR / "materialized_step_panel.parquet",
        "known_failed_overlap_panel": LOCAL_CACHE_DIR / "known_failed_overlap_panel.parquet",
        "report": REPORT_DIR / "sequential_continuation_label_design_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r15a.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r15a.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r15a.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r15a.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r15b.file_sha(path)


def count_rows(path: Path) -> int | float:
    return r15a.count_rows(path)


def stable_hash(value: Any) -> str:
    return r15a.stable_hash(value)


def finite(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def bool_series(series: pd.Series) -> pd.Series:
    return r15a.bool_series(series)


def safe_rate(num: Any, den: Any) -> float:
    try:
        den_f = float(den)
        if den_f == 0 or not np.isfinite(den_f):
            return 0.0
        value = float(num) / den_f
        return float(value) if np.isfinite(value) else 0.0
    except Exception:
        return 0.0


def artifact_required_columns(role: str) -> tuple[str, ...]:
    expected = {
        "upstream_16a_sampling_geometry_decision": (
            "decision_state",
            "next_allowed_requirement",
            "selected_threshold_id",
            "primary_horizon_sessions",
            "effective_to_anchor_ratio_abs_range",
        ),
        "upstream_16a_horizon_grid_step_readout": (
            "threshold_id",
            "cluster_split_bucket",
            "horizon_sessions",
            "labelable_step_n_for_future_16B",
        ),
        "upstream_16a_episode_interval_panel": (
            "threshold_id",
            "cluster_split_bucket",
            "instrument",
            "episode_cluster_id",
            "cluster_start_pos",
            "cluster_end_pos",
            "eligible_episode_cluster",
        ),
        "upstream_16a_step_geometry_panel": (
            "threshold_id",
            "cluster_split_bucket",
            "instrument",
            "episode_cluster_id",
            "horizon_sessions",
            "labelable_step_n_for_future_16B",
        ),
        "upstream_15b_membership_audit": (
            "source_row_key",
            "threshold_id",
            "instrument",
            "episode_cluster_id",
            "cluster_split_bucket",
        ),
        "upstream_15b_taxonomy_assignment_panel": (
            "source_row_key",
            "threshold_id",
            "episode_cluster_id",
            "path_type",
            "assignment_unit",
        ),
        "upstream_15c2_anchor_soft_membership_panel": (
            "source_row_key",
            "threshold_id",
            "hard_path_type_15b",
        ),
        "upstream_15a_price_path_completeness_audit": ("instrument", "qfq_row_n", "price_path_status"),
        "upstream_15b_price_path_completeness_audit": ("instrument", "qfq_row_n", "price_path_status"),
    }
    return expected.get(role, ())


def artifact_required_flag(role: str) -> str:
    if role.startswith("upstream_14a"):
        return "optional_appendix"
    if role == "upstream_15c2_anchor_soft_membership_panel":
        return "optional_soft_overlap_context"
    return "required"


def lineage_role_for_artifact(role: str) -> str:
    if role.startswith("upstream_16a"):
        return "upstream_16a_authorization_and_step_lineage"
    if role.startswith("upstream_15b"):
        return "upstream_15b_hard_taxonomy_projection"
    if role.startswith("upstream_15c2"):
        return "upstream_15c2_soft_overlap_context"
    if role.startswith("upstream_14a"):
        return "upstream_14a_appendix_context"
    if role == "stock_daily_qfq_dir":
        return "qfq_close_label_construction_source"
    return "run_config_input"


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    raw_paths = config.get("paths", {})
    for role, path in resolved.items():
        required_cols = artifact_required_columns(role)
        required_flag = artifact_required_flag(role)
        is_required = required_flag == "required"
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
                elif path.suffix in {".md", ".yaml", ".yml", ".json"}:
                    schema_status = "not_checked"
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
            except Exception as exc:  # pragma: no cover
                read_status = f"read_error:{type(exc).__name__}"
        gate_status = "pass"
        if is_required and read_status != "pass":
            gate_status = "fail"
        if is_required and schema_status.startswith("missing_columns"):
            gate_status = "fail"
        rows.append(
            {
                "artifact_role": role,
                "artifact_path": str(raw_paths.get(role, path)),
                "resolved_path": str(path),
                "required_flag": required_flag,
                "lineage_role": lineage_role_for_artifact(role),
                "read_status": read_status,
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path),
                "schema_status": schema_status,
                "required_column_missing_list": ";".join(missing_cols),
                "input_gate_status": gate_status,
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(audit: pd.DataFrame) -> tuple[str, str]:
    if audit.empty or "input_gate_status" not in audit.columns:
        return "fail", "empty_or_malformed_input_artifact_audit"
    bad = audit.loc[audit["input_gate_status"].astype(str).ne("pass")]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_role"].astype(str).tolist())


def status_all(frame: pd.DataFrame, status_col: str, allowlist: set[str]) -> str:
    if frame.empty or status_col not in frame.columns:
        return "fail"
    statuses = set(frame[status_col].astype(str).fillna(""))
    return "pass" if statuses.issubset(allowlist) else "fail"


def build_upstream_16a_authorization_audit(decision_16a: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    ld = config["label_design"]
    row = decision_16a.iloc[0].to_dict() if not decision_16a.empty else {}
    gate_cols = [
        "input_artifact_gate",
        "upstream_lineage_gate",
        "price_path_completeness_gate",
        "cluster_interval_adapter_gate",
        "cluster_interval_rebuild_gate",
        "episode_cluster_non_overlap_gate",
        "geometry_consistency_gate",
        "search_accounting_gate",
    ]
    all_gates = all(str(row.get(col)) == "pass" for col in gate_cols)
    checks = {
        "upstream_decision_state": row.get("decision_state") == UPSTREAM_READY,
        "upstream_next_allowed_requirement": row.get("next_allowed_requirement") == UPSTREAM_NEXT,
        "selected_threshold_id": row.get("selected_threshold_id") == ld["selected_threshold_id"],
        "primary_horizon_sessions": int(row.get("primary_horizon_sessions", -1)) == int(ld["primary_horizon_sessions"]),
        "sampling_unit": row.get("recommended_sampling_unit") == "non_overlapping_time_blocked_sampling_geometry_step",
        "stability_gate_split_buckets": row.get("stability_gate_split_buckets") == "train;robustness",
        "stress_test_split_buckets": row.get("stress_test_split_buckets") == "validation",
        "all_16a_hard_gates_passed": all_gates,
    }
    expected_numbers = {
        "anchor_n_train": 57524,
        "episode_cluster_n_train": 667,
        "episode_cluster_n_validation": 45,
        "episode_cluster_n_robustness": 218,
        "nonoverlap_step_n_train_primary_horizon": 20871,
        "full_horizon_nonoverlap_step_n_train_primary_horizon": 20245,
        "partial_tail_step_n_train_primary_horizon": 626,
        "effective_sample_size_train_primary_horizon": 20245,
    }
    for key, expected in expected_numbers.items():
        checks[key] = abs(float(row.get(key, np.nan)) - expected) < 1e-9
    checks["anchor_overcount_ratio_train_primary_horizon"] = abs(float(row.get("anchor_overcount_ratio_train_primary_horizon", np.nan)) - 2.756169) < 1e-3
    checks["effective_to_anchor_ratio_abs_range"] = abs(float(row.get("effective_to_anchor_ratio_abs_range", np.nan)) - 0.131094) < 1e-3
    status = "pass" if all(checks.values()) else "fail"
    out = {
        "upstream_decision_state": row.get("decision_state", ""),
        "upstream_next_allowed_requirement": row.get("next_allowed_requirement", ""),
        "selected_threshold_id": row.get("selected_threshold_id", ""),
        "primary_horizon_sessions": row.get("primary_horizon_sessions", np.nan),
        "sampling_unit": row.get("recommended_sampling_unit", ""),
        "stability_gate_split_buckets": row.get("stability_gate_split_buckets", ""),
        "stress_test_split_buckets": row.get("stress_test_split_buckets", ""),
        "nonoverlap_step_n_train_primary_horizon": row.get("nonoverlap_step_n_train_primary_horizon", np.nan),
        "full_horizon_nonoverlap_step_n_train_primary_horizon": row.get("full_horizon_nonoverlap_step_n_train_primary_horizon", np.nan),
        "partial_tail_step_n_train_primary_horizon": row.get("partial_tail_step_n_train_primary_horizon", np.nan),
        "anchor_overcount_ratio_train_primary_horizon": row.get("anchor_overcount_ratio_train_primary_horizon", np.nan),
        "effective_sample_size_train_primary_horizon": row.get("effective_sample_size_train_primary_horizon", np.nan),
        "effective_to_anchor_ratio_abs_range": row.get("effective_to_anchor_ratio_abs_range", np.nan),
        "geometry_stable_across_splits": row.get("geometry_stable_across_splits", False),
        "all_16a_hard_gates_passed": all_gates,
        "authorization_status": status,
        "blocking_reason": "" if status == "pass" else ";".join(k for k, ok in checks.items() if not ok),
    }
    return pd.DataFrame([out])


def build_label_rule_definition_audit(config: dict[str, Any]) -> pd.DataFrame:
    ld = config["label_design"]
    rows = [
        {
            "label_id": PRIMARY_LABEL_ID,
            "label_role": "primary",
            "horizon_sessions": ld["primary_horizon_sessions"],
            "step_price_field": "qfq_close",
            "drawdown_threshold": ld["drawdown_threshold"],
            "step_end_price_ratio_threshold": ld["step_end_price_ratio_threshold"],
            "positive_predicate": "max_drawdown_from_step_start > -0.10 and step_end_price_ratio_minus_one_for_label_rule >= 0",
            "negative_predicate": "max_drawdown_from_step_start <= -0.10",
            "neutral_predicate": "not continuation_positive and not continuation_negative",
            "tail_step_usage": "excluded_from_labelable_population",
            "rule_status": "pass",
        },
        {
            "label_id": SECONDARY_LABEL_ID,
            "label_role": "secondary_readout_only",
            "horizon_sessions": ld["primary_horizon_sessions"],
            "step_price_field": "qfq_close",
            "drawdown_threshold": ld["drawdown_threshold"],
            "step_end_price_ratio_threshold": 0.0,
            "positive_predicate": "step_end_price_ratio_minus_one_for_label_rule > 0 and max_drawdown_from_step_start > -0.10",
            "negative_predicate": "readout_only_primary_negative",
            "neutral_predicate": "readout_only_not_positive_not_primary_negative",
            "tail_step_usage": "excluded_from_labelable_population",
            "rule_status": "pass",
        },
        {
            "label_id": STRESS_LABEL_ID,
            "label_role": "stress_sanity_readout_only",
            "horizon_sessions": ld["primary_horizon_sessions"],
            "step_price_field": "qfq_session_pos",
            "drawdown_threshold": np.nan,
            "step_end_price_ratio_threshold": np.nan,
            "positive_predicate": "step_end_pos <= cluster_end_pos and full_horizon_nonoverlap_step",
            "negative_predicate": "false",
            "neutral_predicate": "not continuation_survival_positive",
            "tail_step_usage": "excluded_from_labelable_population",
            "rule_status": "pass",
        },
    ]
    return pd.DataFrame(rows)


def materialize_steps(intervals: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    ld = config["label_design"]
    thresholds = set(ld["threshold_sensitivity_grid"])
    splits = set(ld["eligible_split_buckets"])
    horizons = [int(x) for x in ld["horizon_grid_sessions"]]
    eligible = intervals.loc[
        bool_series(intervals["eligible_episode_cluster"])
        & intervals["threshold_id"].astype(str).isin(thresholds)
        & intervals["cluster_split_bucket"].astype(str).isin(splits)
    ].copy()
    rows: list[dict[str, Any]] = []
    for row in eligible.itertuples(index=False):
        start = int(row.cluster_start_pos)
        end = int(row.cluster_end_pos)
        length = end - start + 1
        for horizon in horizons:
            full = int(length // horizon)
            for step_index in range(full):
                step_start = start + step_index * horizon
                step_end = step_start + horizon - 1
                rows.append(
                    {
                        "step_id": f"{row.threshold_id}|{row.instrument}|{row.episode_cluster_id}|h{horizon}|{step_index}",
                        "threshold_id": row.threshold_id,
                        "cluster_split_bucket": row.cluster_split_bucket,
                        "instrument": row.instrument,
                        "episode_cluster_id": row.episode_cluster_id,
                        "horizon_sessions": horizon,
                        "step_index": step_index,
                        "step_start_pos": step_start,
                        "step_end_pos": step_end,
                        "cluster_start_pos": start,
                        "cluster_end_pos": end,
                        "episode_length_sessions": length,
                        "anchor_n": int(row.anchor_n),
                        "full_horizon_nonoverlap_step": True,
                        "partial_tail_step": False,
                    }
                )
    return pd.DataFrame(rows)


def build_step_materialization_audit(steps: pd.DataFrame, horizon_readout: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    expected = horizon_readout.copy()
    group_cols = ["threshold_id", "cluster_split_bucket", "horizon_sessions"]
    if not steps.empty:
        checked = steps.copy()
        step_len = finite(checked["step_end_pos"]) - finite(checked["step_start_pos"]) + 1
        checked["bad_step_bounds_flag"] = (
            (finite(checked["step_start_pos"]) < finite(checked["cluster_start_pos"]))
            | (finite(checked["step_end_pos"]) > finite(checked["cluster_end_pos"]))
            | (step_len != finite(checked["horizon_sessions"]))
            | (finite(checked["step_start_pos"]) < 0)
        )
        cluster_cols = ["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id", "horizon_sessions"]
        cluster_counts = (
            checked.groupby(cluster_cols, dropna=False)
            .agg(
                materialized_cluster_step_n=("step_id", "size"),
                cluster_start_pos=("cluster_start_pos", "first"),
                cluster_end_pos=("cluster_end_pos", "first"),
            )
            .reset_index()
        )
        cluster_length = finite(cluster_counts["cluster_end_pos"]) - finite(cluster_counts["cluster_start_pos"]) + 1
        cluster_counts["expected_cluster_step_n"] = (cluster_length // finite(cluster_counts["horizon_sessions"])).astype(int)
        cluster_counts["cluster_count_mismatch_flag"] = cluster_counts["materialized_cluster_step_n"] != cluster_counts["expected_cluster_step_n"]
        cluster_mismatch = (
            cluster_counts.groupby(group_cols, dropna=False)
            .agg(cluster_count_mismatch_n=("cluster_count_mismatch_flag", lambda s: int(bool_series(s).sum())))
            .reset_index()
        )
        actual = (
            checked.groupby(group_cols, dropna=False)
            .agg(
                materialized_step_n=("step_id", "size"),
                source_episode_cluster_n=("episode_cluster_id", "nunique"),
                duplicate_step_id_n=("step_id", lambda s: int(s.duplicated().sum())),
                bad_step_bounds_n=("bad_step_bounds_flag", lambda s: int(bool_series(s).sum())),
                partial_tail_materialized_n=("partial_tail_step", lambda s: int(bool_series(s).sum())),
            )
            .reset_index()
            .merge(cluster_mismatch, on=group_cols, how="left")
        )
    else:
        actual = pd.DataFrame(
            columns=group_cols
            + [
                "materialized_step_n",
                "source_episode_cluster_n",
                "duplicate_step_id_n",
                "bad_step_bounds_n",
                "partial_tail_materialized_n",
                "cluster_count_mismatch_n",
            ]
        )
    merged = expected[group_cols + ["labelable_step_n_for_future_16B"]].merge(actual, on=group_cols, how="left")
    for row in merged.itertuples(index=False):
        materialized = int(0 if pd.isna(row.materialized_step_n) else row.materialized_step_n)
        expected_n = int(row.labelable_step_n_for_future_16B)
        delta = materialized - expected_n
        duplicate_step_id_n = int(0 if pd.isna(row.duplicate_step_id_n) else row.duplicate_step_id_n)
        bad_step_bounds_n = int(0 if pd.isna(row.bad_step_bounds_n) else row.bad_step_bounds_n)
        partial_tail_materialized_n = int(0 if pd.isna(row.partial_tail_materialized_n) else row.partial_tail_materialized_n)
        cluster_count_mismatch_n = int(0 if pd.isna(row.cluster_count_mismatch_n) else row.cluster_count_mismatch_n)
        status = (
            "pass"
            if delta == 0
            and duplicate_step_id_n == 0
            and bad_step_bounds_n == 0
            and partial_tail_materialized_n == 0
            and cluster_count_mismatch_n == 0
            else "fail"
        )
        rows.append(
            {
                "threshold_id": row.threshold_id,
                "cluster_split_bucket": row.cluster_split_bucket,
                "horizon_sessions": int(row.horizon_sessions),
                "source_episode_cluster_n": int(0 if pd.isna(row.source_episode_cluster_n) else row.source_episode_cluster_n),
                "materialized_step_n": materialized,
                "expected_labelable_step_n_from_16a": expected_n,
                "step_count_delta_vs_16a": delta,
                "duplicate_step_id_n": duplicate_step_id_n,
                "bad_step_bounds_n": bad_step_bounds_n,
                "partial_tail_materialized_n": partial_tail_materialized_n,
                "cluster_count_mismatch_n": cluster_count_mismatch_n,
                "adapter_status": status,
                "materialization_status": status,
                "blocking_reason": "" if status == "pass" else "step_materialization_count_or_identity_mismatch",
            }
        )
    return pd.DataFrame(rows)


def read_qfq(instrument: str, qfq_dir: Path) -> pd.DataFrame | None:
    path = qfq_dir / f"{instrument}.csv"
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, usecols=["date", "close"])
    except Exception:
        return None


def build_qfq_price_source_audit(
    steps: pd.DataFrame,
    qfq_dir: Path,
    price_15a: pd.DataFrame,
    price_15b: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    qfq_cache: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, Any]] = []
    qfq_n_15a = dict(zip(price_15a["instrument"].astype(str), finite(price_15a["qfq_row_n"]))) if not price_15a.empty else {}
    qfq_n_15b = dict(zip(price_15b["instrument"].astype(str), finite(price_15b["qfq_row_n"]))) if not price_15b.empty else {}
    for instrument, sub in steps.groupby("instrument", sort=False):
        path = qfq_dir / f"{instrument}.csv"
        qfq = read_qfq(str(instrument), qfq_dir)
        missing_file = qfq is None
        missing_cols = ""
        nonfinite = np.nan
        nonpositive = np.nan
        qfq_row_n = 0 if qfq is None else len(qfq)
        if qfq is not None:
            qfq_cache[str(instrument)] = qfq
            close = finite(qfq["close"])
            nonfinite = int(close.isna().sum())
            nonpositive = int((close <= 0).sum())
            missing_cols = "" if {"date", "close"}.issubset(qfq.columns) else "date_or_close"
        max_step_end = int(finite(sub["step_end_pos"]).max())
        bounds_bad = int(max_step_end >= qfq_row_n or finite(sub["step_start_pos"]).min() < 0)
        n15a = qfq_n_15a.get(str(instrument), np.nan)
        n15b = qfq_n_15b.get(str(instrument), np.nan)
        row_order_bad = int(pd.isna(n15a) or pd.isna(n15b) or int(n15a) != qfq_row_n or int(n15b) != qfq_row_n)
        status = "pass"
        reasons = []
        if missing_file:
            status = "fail"
            reasons.append("missing_qfq_file")
        if missing_cols:
            status = "fail"
            reasons.append("missing_required_columns")
        if not missing_file and (nonfinite or nonpositive):
            status = "fail"
            reasons.append("bad_close_values")
        if bounds_bad:
            status = "fail"
            reasons.append("step_bounds_out_of_qfq")
        if row_order_bad:
            status = "fail"
            reasons.append("qfq_row_n_mismatch_vs_upstream_audit")
        rows.append(
            {
                "instrument": instrument,
                "qfq_path": str(path),
                "qfq_row_n": qfq_row_n,
                "required_by_labelable_step_n": len(sub),
                "missing_qfq_file_flag": missing_file,
                "missing_required_columns": missing_cols,
                "nonfinite_close_n": nonfinite,
                "nonpositive_close_n": nonpositive,
                "step_bounds_out_of_qfq_n": bounds_bad,
                "qfq_row_n_15a": n15a,
                "qfq_row_n_15b": n15b,
                "qfq_price_source_status": status,
                "blocking_reason": ";".join(reasons),
            }
        )
    return pd.DataFrame(rows), qfq_cache


def build_price_path_completeness_audit(
    qfq_audit: pd.DataFrame,
    steps: pd.DataFrame,
    price_15a: pd.DataFrame,
    price_15b: pd.DataFrame,
) -> pd.DataFrame:
    status_15a = dict(zip(price_15a["instrument"].astype(str), price_15a["price_path_status"].astype(str))) if not price_15a.empty else {}
    status_15b = dict(zip(price_15b["instrument"].astype(str), price_15b["price_path_status"].astype(str))) if not price_15b.empty else {}
    max_end = steps.groupby("instrument")["step_end_pos"].max().to_dict() if not steps.empty else {}
    rows = []
    for row in qfq_audit.itertuples(index=False):
        s15a = status_15a.get(str(row.instrument), "missing")
        s15b = status_15b.get(str(row.instrument), "missing")
        status = "pass" if s15a == "pass" and s15b == "pass" and row.qfq_price_source_status == "pass" else "fail"
        rows.append(
            {
                "instrument": row.instrument,
                "qfq_row_n": row.qfq_row_n,
                "upstream_15a_price_path_status": s15a,
                "upstream_15b_price_path_status": s15b,
                "qfq_price_source_status": row.qfq_price_source_status,
                "required_labelable_step_n": row.required_by_labelable_step_n,
                "max_step_end_pos": max_end.get(row.instrument, np.nan),
                "step_bounds_out_of_qfq_n": row.step_bounds_out_of_qfq_n,
                "price_path_status": status,
                "blocking_reason": "" if status == "pass" else "upstream_or_qfq_price_path_status_failed",
            }
        )
    return pd.DataFrame(rows)


def compute_continuation_labels(steps: pd.DataFrame, qfq_cache: dict[str, pd.DataFrame], config: dict[str, Any]) -> pd.DataFrame:
    ld = config["label_design"]
    drawdown_threshold = float(ld["drawdown_threshold"])
    end_threshold = float(ld["step_end_price_ratio_threshold"])
    boundary_eps = 1e-12
    rows: list[dict[str, Any]] = []
    for instrument, sub in steps.groupby("instrument", sort=False):
        qfq = qfq_cache.get(str(instrument))
        if qfq is None:
            continue
        close = finite(qfq["close"]).to_numpy(dtype=float)
        dates = qfq["date"].astype(str).to_numpy()
        for step in sub.itertuples(index=False):
            start = int(step.step_start_pos)
            end = int(step.step_end_pos)
            if start < 0 or end >= len(close) or end < start:
                status = "fail_bad_step_bounds"
                start_price = end_price = max_dd = ratio = np.nan
                primary_pos = primary_neg = primary_neutral = False
            else:
                window = close[start : end + 1]
                start_price = float(close[start])
                end_price = float(close[end])
                ratio = end_price / start_price - 1.0 if start_price > 0 else np.nan
                max_dd = float(np.nanmin(window / start_price - 1.0)) if start_price > 0 else np.nan
                primary_pos = bool(max_dd > drawdown_threshold + boundary_eps and ratio >= end_threshold)
                primary_neg = bool(max_dd <= drawdown_threshold + boundary_eps)
                primary_neutral = bool(not primary_pos and not primary_neg)
                status = "pass" if np.isfinite([start_price, end_price, max_dd, ratio]).all() else "fail_bad_price_values"
            secondary_pos = bool(ratio > 0 and max_dd > drawdown_threshold + boundary_eps) if np.isfinite(ratio) and np.isfinite(max_dd) else False
            stress_pos = bool(end <= int(step.cluster_end_pos))
            rows.append(
                {
                    "step_id": step.step_id,
                    "label_id": PRIMARY_LABEL_ID,
                    "threshold_id": step.threshold_id,
                    "cluster_split_bucket": step.cluster_split_bucket,
                    "instrument": step.instrument,
                    "episode_cluster_id": step.episode_cluster_id,
                    "horizon_sessions": int(step.horizon_sessions),
                    "step_index": int(step.step_index),
                    "step_start_pos": start,
                    "step_end_pos": end,
                    "step_start_date": dates[start] if 0 <= start < len(dates) else "",
                    "step_end_date": dates[end] if 0 <= end < len(dates) else "",
                    "step_start_qfq_close": start_price,
                    "step_end_qfq_close": end_price,
                    "max_drawdown_from_step_start": max_dd,
                    "step_end_price_ratio_minus_one_for_label_rule": ratio,
                    "continuation_positive": primary_pos,
                    "continuation_negative": primary_neg,
                    "continuation_neutral": primary_neutral,
                    "continuation_progress_positive": secondary_pos,
                    "continuation_survival_positive": stress_pos,
                    "label_rule_status": status,
                }
            )
    return pd.DataFrame(rows, columns=LABEL_PANEL_COLUMNS)


def _label_counts(frame: pd.DataFrame, label_id: str) -> tuple[int, int, int]:
    if label_id == PRIMARY_LABEL_ID:
        pos = int(bool_series(frame["continuation_positive"]).sum())
        neg = int(bool_series(frame["continuation_negative"]).sum())
        neutral = int(bool_series(frame["continuation_neutral"]).sum())
    elif label_id == SECONDARY_LABEL_ID:
        pos = int(bool_series(frame["continuation_progress_positive"]).sum())
        neg = int(bool_series(frame["continuation_negative"]).sum())
        neutral = int(len(frame) - pos - neg)
    else:
        pos = int(bool_series(frame["continuation_survival_positive"]).sum())
        neg = 0
        neutral = int(len(frame) - pos)
    return pos, neg, neutral


def build_continuation_label_base_rate_readout(labels: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = ["threshold_id", "cluster_split_bucket", "horizon_sessions"]
    for keys, sub in labels.groupby(group_cols, dropna=False, sort=False):
        threshold, split, horizon = keys
        for label_id in [PRIMARY_LABEL_ID, SECONDARY_LABEL_ID, STRESS_LABEL_ID]:
            pos, neg, neutral = _label_counts(sub, label_id)
            total = len(sub)
            rows.append(
                {
                    "label_id": label_id,
                    "threshold_id": threshold,
                    "cluster_split_bucket": split,
                    "horizon_sessions": int(horizon),
                    "labelable_step_n": total,
                    "positive_step_n": pos,
                    "negative_step_n": neg,
                    "neutral_step_n": neutral,
                    "positive_rate": safe_rate(pos, total),
                    "negative_rate": safe_rate(neg, total),
                    "neutral_rate": safe_rate(neutral, total),
                    "effective_sample_size_nonoverlap": total,
                    "positive_effective_sample_size": pos,
                    "negative_effective_sample_size": neg,
                    "episode_cluster_n": int(sub["episode_cluster_id"].nunique()),
                    "anchor_n_reference_only": int(finite(sub.get("anchor_n", pd.Series(dtype=float))).sum()) if "anchor_n" in sub.columns else np.nan,
                    "base_rate_status": "pass",
                }
            )
    return pd.DataFrame(rows, columns=BASE_RATE_COLUMNS)


def build_known_failed_cluster_projection(
    membership: pd.DataFrame,
    taxonomy: pd.DataFrame,
    soft: pd.DataFrame | None,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str, str]:
    required_families = set(KNOWN_FAILED_FAMILIES)
    if "path_type" not in taxonomy.columns or not required_families.issubset(set(taxonomy["path_type"].dropna().astype(str))):
        return pd.DataFrame(), "fail_unknown_known_failed_family_enum", "required_15b_known_failed_path_types_missing"
    required_cols = {"source_row_key", "threshold_id", "episode_cluster_id", "path_type", "assignment_unit"}
    if not required_cols.issubset(taxonomy.columns):
        return pd.DataFrame(), "fail_missing_known_failed_projection_column", "15b_taxonomy_required_columns_missing"
    tax = taxonomy.loc[taxonomy["assignment_unit"].astype(str).eq("anchor_path"), ["source_row_key", "threshold_id", "path_type"]].copy()
    mem_cols = ["source_row_key", "threshold_id", "instrument", "episode_cluster_id", "cluster_split_bucket"]
    joined = membership[mem_cols].merge(tax, on=["source_row_key", "threshold_id"], how="left")
    soft_joined = pd.DataFrame()
    soft_schema_caveat = False
    soft_cols: list[str] = []
    if soft is not None:
        soft_required_cols = {"source_row_key", "threshold_id", "hard_path_type_15b"}
        soft_schema_caveat = not soft_required_cols.issubset(soft.columns)
        soft_cols = [f"membership_{family}" for family in KNOWN_FAILED_FAMILIES if f"membership_{family}" in set(soft.columns)]
        if not soft_cols:
            soft_schema_caveat = True
    if soft is not None and not soft_schema_caveat:
        keep_cols = ["source_row_key", "threshold_id"] + soft_cols
        soft_joined = membership[mem_cols].merge(soft[keep_cols], on=["source_row_key", "threshold_id"], how="left")
    rows: list[dict[str, Any]] = []
    for keys, sub in joined.groupby(["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"], sort=False):
        threshold, split, instrument, cluster_id = keys
        anchor_n = len(sub)
        hard_coverage = safe_rate(sub["path_type"].notna().sum(), anchor_n)
        soft_sub = pd.DataFrame()
        soft_coverage = 0.0
        if not soft_joined.empty:
            mask = (
                soft_joined["threshold_id"].astype(str).eq(str(threshold))
                & soft_joined["instrument"].astype(str).eq(str(instrument))
                & soft_joined["episode_cluster_id"].astype(str).eq(str(cluster_id))
            )
            soft_sub = soft_joined.loc[mask]
            if soft_cols:
                soft_coverage = safe_rate(soft_sub[soft_cols].notna().any(axis=1).sum(), len(soft_sub))
        for family in KNOWN_FAILED_FAMILIES:
            hard_share = safe_rate((sub["path_type"].astype(str) == family).sum(), sub["path_type"].notna().sum())
            soft_col = f"membership_{family}"
            soft_share = np.nan
            if not soft_sub.empty and soft_col in soft_sub.columns:
                soft_share = safe_rate((finite(soft_sub[soft_col]) >= float(config["label_design"]["soft_membership_high_threshold"])).sum(), soft_sub[soft_col].notna().sum())
            rows.append(
                {
                    "threshold_id": threshold,
                    "cluster_split_bucket": split,
                    "instrument": instrument,
                    "episode_cluster_id": cluster_id,
                    "known_failed_family": family,
                    "cluster_anchor_n": anchor_n,
                    "cluster_failed_anchor_share": hard_share,
                    "known_failed_step_flag": hard_share >= 0.50,
                    "hard_projection_coverage": hard_coverage,
                    "cluster_soft_failed_anchor_share": soft_share,
                    "soft_overlap_coverage": soft_coverage if soft is not None else np.nan,
                    "soft_overlap_status": (
                        "soft_overlap_schema_caveat"
                        if soft_schema_caveat
                        else "soft_overlap_partial_coverage_caveat"
                        if soft is None or soft_coverage < float(config["label_design"]["soft_overlap_coverage_caveat_min"])
                        else "pass"
                    ),
                }
            )
    projection = pd.DataFrame(rows)
    if projection.empty:
        return projection, "fail_not_evaluable", "empty_projection"
    low_hard = projection.loc[finite(projection["hard_projection_coverage"]) < float(config["label_design"]["hard_projection_anchor_coverage_min"])]
    if not low_hard.empty:
        return projection, "fail_insufficient_15b_hard_projection_coverage", "15b_hard_projection_coverage_below_min"
    return projection, "pass", ""


def build_known_failed_overlap_readout(labels: pd.DataFrame, projection: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if projection.empty or labels.empty:
        return pd.DataFrame(columns=OVERLAP_COLUMNS), pd.DataFrame()
    cluster_counts = (
        labels.groupby(["threshold_id", "cluster_split_bucket", "horizon_sessions", "instrument", "episode_cluster_id"], sort=False)
        .agg(
            all_step_n=("step_id", "size"),
            positive_step_n=("continuation_positive", lambda s: int(bool_series(s).sum())),
        )
        .reset_index()
    )
    panel = cluster_counts.merge(
        projection,
        on=["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"],
        how="left",
    )
    rows: list[dict[str, Any]] = []
    for keys, sub in panel.groupby(["threshold_id", "cluster_split_bucket", "horizon_sessions", "known_failed_family"], dropna=False, sort=False):
        threshold, split, horizon, family = keys
        pos_total = int(finite(sub["positive_step_n"]).sum())
        all_total = int(finite(sub["all_step_n"]).sum())
        flag = bool_series(sub["known_failed_step_flag"])
        failed_pos = int(finite(sub.loc[flag, "positive_step_n"]).sum())
        failed_all = int(finite(sub.loc[flag, "all_step_n"]).sum())
        failed_share = safe_rate(failed_pos, pos_total)
        all_share = safe_rate(failed_all, all_total)
        share_delta = failed_share - all_share
        rows.append(
            {
                "label_id": PRIMARY_LABEL_ID,
                "threshold_id": threshold,
                "known_failed_family": family,
                "overlap_source": "hard_15b_taxonomy",
                "cluster_split_bucket": split,
                "horizon_sessions": int(horizon),
                "positive_step_n": pos_total,
                "failed_family_positive_step_n": failed_pos,
                "failed_family_positive_share": failed_share,
                "all_step_failed_family_share": all_share,
                "share_delta": share_delta,
                "hard_projection_coverage": float(finite(sub["hard_projection_coverage"]).min()),
                "soft_overlap_coverage": float(finite(sub["soft_overlap_coverage"]).min()) if finite(sub["soft_overlap_coverage"]).notna().any() else np.nan,
                "soft_overlap_status": "soft_overlap_partial_coverage_caveat"
                if set(sub["soft_overlap_status"].astype(str)) - {"pass"}
                else "pass",
                "overlap_status": "pass",
                "blocking_reason": "",
            }
        )
    out = pd.DataFrame(rows, columns=OVERLAP_COLUMNS)
    return out, panel


def build_search_accounting_audit(config: dict[str, Any]) -> pd.DataFrame:
    ld = config["label_design"]
    row = {
        "startup_authorization_basis": ld["startup_authorization_basis"],
        "selected_threshold_id": ld["selected_threshold_id"],
        "primary_label_id": ld["primary_label_id"],
        "primary_horizon_sessions": int(ld["primary_horizon_sessions"]),
        "horizon_sensitivity_grid": ";".join(str(x) for x in ld["horizon_sensitivity_grid"]),
        "sampling_unit": "non_overlapping_time_blocked_sampling_geometry_step",
        "validation_usage": ld["validation_usage"],
        "geometry_fit_split": "none_label_design_only",
        "forward_return_computed_for_trading": False,
        "step_materialization_source": "16A_episode_interval_panel_formula",
        "qfq_price_source": "data/raw/akshare/day/qfq",
        "entry_search_authorized": False,
        "signal_search_authorized": False,
        "model_training_authorized": False,
        "separability_search_authorized": False,
        "label_deployment_authorized": False,
    }
    status = (
        row["startup_authorization_basis"] == UPSTREAM_READY
        and row["selected_threshold_id"] == "up50pct"
        and row["primary_label_id"] == PRIMARY_LABEL_ID
        and row["primary_horizon_sessions"] == 20
        and row["horizon_sensitivity_grid"] == "5;8;13;15"
        and row["validation_usage"] == "stress_test_readout_only"
        and row["geometry_fit_split"] == "none_label_design_only"
        and not any(
            [
                row["forward_return_computed_for_trading"],
                row["entry_search_authorized"],
                row["signal_search_authorized"],
                row["model_training_authorized"],
                row["separability_search_authorized"],
                row["label_deployment_authorized"],
            ]
        )
    )
    row["search_accounting_status"] = "pass" if status else "fail"
    return pd.DataFrame([row])


def _base_row(base: pd.DataFrame, split: str, threshold: str, horizon: int) -> pd.Series | None:
    sub = base.loc[
        base["label_id"].astype(str).eq(PRIMARY_LABEL_ID)
        & base["threshold_id"].astype(str).eq(threshold)
        & base["cluster_split_bucket"].astype(str).eq(split)
        & finite(base["horizon_sessions"]).eq(horizon)
    ]
    if sub.empty:
        return None
    return sub.iloc[0]


def build_effective_sample_label_support_readout(base: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    ld = config["label_design"]
    threshold = ld["selected_threshold_id"]
    horizon = int(ld["primary_horizon_sessions"])
    rows = []
    for split in ["train", "robustness", "validation"]:
        row = _base_row(base, split, threshold, horizon)
        if row is None:
            rows.append({"cluster_split_bucket": split, "support_status": "missing"})
            continue
        rows.append(
            {
                "label_id": PRIMARY_LABEL_ID,
                "threshold_id": threshold,
                "cluster_split_bucket": split,
                "horizon_sessions": horizon,
                "labelable_step_n": row["labelable_step_n"],
                "positive_effective_sample_size": row["positive_effective_sample_size"],
                "negative_effective_sample_size": row["negative_effective_sample_size"],
                "positive_rate": row["positive_rate"],
                "negative_rate": row["negative_rate"],
                "support_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def build_sequential_continuation_label_decision(
    config: dict[str, Any],
    hard_gates: dict[str, str],
    base: pd.DataFrame,
    overlap: pd.DataFrame,
    validation_stress: pd.DataFrame,
) -> pd.DataFrame:
    ld = config["label_design"]
    threshold = ld["selected_threshold_id"]
    horizon = int(ld["primary_horizon_sessions"])
    train = _base_row(base, "train", threshold, horizon)
    robust = _base_row(base, "robustness", threshold, horizon)
    validation = _base_row(base, "validation", threshold, horizon)
    train = pd.Series(dtype=object) if train is None else train
    robust = pd.Series(dtype=object) if robust is None else robust
    validation = pd.Series(dtype=object) if validation is None else validation
    pos_train = float(train.get("positive_rate", 0.0))
    neg_train = float(train.get("negative_rate", 0.0))
    pos_robust = float(robust.get("positive_rate", 0.0))
    neg_robust = float(robust.get("negative_rate", 0.0))
    base_rate_nontrivial = (
        float(ld["positive_rate_train_min"]) <= pos_train <= float(ld["positive_rate_train_max"])
        and float(ld["negative_rate_train_min"]) <= neg_train <= float(ld["negative_rate_train_max"])
    )
    effective_sample_sufficient = (
        float(train.get("positive_effective_sample_size", 0.0)) >= float(ld["positive_effective_sample_size_train_min"])
        and float(train.get("negative_effective_sample_size", 0.0)) >= float(ld["negative_effective_sample_size_train_min"])
        and float(train.get("labelable_step_n", 0.0)) >= float(ld["labelable_step_n_train_min"])
        and float(robust.get("negative_effective_sample_size", 0.0)) >= float(ld["negative_effective_sample_size_robustness_min"])
    )
    stable = (
        abs(pos_train - pos_robust) <= float(ld["base_rate_abs_delta_max"])
        and abs(neg_train - neg_robust) <= float(ld["base_rate_abs_delta_max"])
    )
    validation_evaluable = float(validation.get("labelable_step_n", 0.0)) >= float(ld["validation_labelable_step_n_caveat_min"])
    stress_rate = 0.0
    if not validation_stress.empty and "continuation_survival_positive_rate" in validation_stress.columns:
        stress_rate = float(finite(validation_stress["continuation_survival_positive_rate"]).min())
    step_generation_lineage_sane = stress_rate >= float(ld["step_generation_lineage_sane_min"])
    hard_gates = dict(hard_gates)
    if not step_generation_lineage_sane:
        hard_gates["step_materialization"] = "fail"
    soft_caveat = bool(
        not overlap.empty
        and "soft_overlap_status" in overlap.columns
        and (overlap["soft_overlap_status"].astype(str) != "pass").any()
    )
    required_overlap_cols = {"label_id", "threshold_id", "cluster_split_bucket", "horizon_sessions", "overlap_source"}
    if overlap.empty or not required_overlap_cols.issubset(overlap.columns):
        primary_overlap = pd.DataFrame()
    else:
        primary_overlap = overlap.loc[
            overlap["label_id"].astype(str).eq(PRIMARY_LABEL_ID)
            & overlap["threshold_id"].astype(str).eq(threshold)
            & overlap["cluster_split_bucket"].astype(str).eq("train")
            & finite(overlap["horizon_sessions"]).eq(horizon)
            & overlap["overlap_source"].astype(str).eq("hard_15b_taxonomy")
        ]
    known_failed_context_exposure_caveat = False
    if primary_overlap.empty:
        known_failed_overlap_gate = "fail_not_evaluable"
    else:
        known_failed_overlap_gate = "pass"
        known_failed_context_exposure_caveat = bool(
            finite(primary_overlap["failed_family_positive_share"]).max() > float(ld["known_failed_positive_share_max"])
            or finite(primary_overlap["share_delta"]).max() > float(ld["known_failed_share_delta_max"])
        )
    any_hard_fail = any(status != "pass" for status in hard_gates.values()) or known_failed_overlap_gate != "pass"
    if any_hard_fail:
        decision = DECISION_BLOCKED
        next_allowed = "none"
    elif not base_rate_nontrivial:
        decision = "16B_continuation_label_base_rate_degenerate"
        next_allowed = "none"
    elif not effective_sample_sufficient:
        decision = "16B_continuation_label_effective_sample_too_small"
        next_allowed = "none"
    elif not stable:
        decision = "16B_continuation_label_unstable_train_robustness"
        next_allowed = "none"
    else:
        decision = DECISION_READY
        next_allowed = NEXT_16C
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "primary_label_id": PRIMARY_LABEL_ID,
                "selected_threshold_id": threshold,
                "primary_horizon_sessions": horizon,
                "labelable_step_n_train": float(train.get("labelable_step_n", 0.0)),
                "positive_rate_train": pos_train,
                "negative_rate_train": neg_train,
                "positive_effective_sample_size_train": float(train.get("positive_effective_sample_size", 0.0)),
                "negative_effective_sample_size_train": float(train.get("negative_effective_sample_size", 0.0)),
                "labelable_step_n_robustness": float(robust.get("labelable_step_n", 0.0)),
                "positive_rate_robustness": pos_robust,
                "negative_rate_robustness": neg_robust,
                "negative_effective_sample_size_robustness": float(robust.get("negative_effective_sample_size", 0.0)),
                "base_rate_nontrivial": bool(base_rate_nontrivial),
                "effective_sample_sufficient": bool(effective_sample_sufficient),
                "base_rate_stable_train_robustness": bool(stable),
                "validation_stress_evaluable": bool(validation_evaluable),
                "step_generation_lineage_sane": bool(step_generation_lineage_sane),
                "soft_overlap_partial_coverage_caveat": bool(soft_caveat),
                "known_failed_context_exposure_caveat": bool(known_failed_context_exposure_caveat),
                "step_materialization_gate": hard_gates.get("step_materialization", "fail"),
                "qfq_price_source_gate": hard_gates.get("qfq_price_source", "fail"),
                "known_failed_overlap_gate": known_failed_overlap_gate,
                "known_failed_overlap_evaluability_gate": hard_gates.get("known_failed_overlap_evaluability", "fail"),
                "label_deployment_authorized": False,
                "signal_search_authorized": False,
                "model_training_authorized": False,
                "entry_policy_authorized": False,
                "separability_search_authorized": False,
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows._"
    sub = frame.loc[:, [col for col in columns if col in frame.columns]].head(max_rows).copy()
    headers = list(sub.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in sub.itertuples(index=False):
        cells = []
        for value in row:
            if isinstance(value, float):
                cells.append("" if pd.isna(value) else f"{value:.4f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_report(decision: pd.DataFrame, base: pd.DataFrame, overlap: pd.DataFrame, support: pd.DataFrame) -> str:
    d = decision.iloc[0].to_dict()
    primary = base.loc[
        base["label_id"].astype(str).eq(PRIMARY_LABEL_ID)
        & base["threshold_id"].astype(str).eq(str(d["selected_threshold_id"]))
        & finite(base["horizon_sessions"]).eq(int(d["primary_horizon_sessions"]))
    ]
    hard_overlap_all = (
        overlap.loc[overlap["overlap_source"].astype(str).eq("hard_15b_taxonomy")]
        if "overlap_source" in overlap.columns
        else pd.DataFrame(columns=OVERLAP_COLUMNS)
    )
    hard_overlap = hard_overlap_all.loc[
        hard_overlap_all["threshold_id"].astype(str).eq(str(d["selected_threshold_id"]))
        & finite(hard_overlap_all["horizon_sessions"]).eq(int(d["primary_horizon_sessions"]))
    ] if not hard_overlap_all.empty else hard_overlap_all
    return f"""# 16B Sequential Continuation Label Design Diagnostic Report

## 1. 单行裁决

`decision_state = {d['decision_state']}`；`next_allowed_requirement = {d['next_allowed_requirement']}`。

16B 只审计 continuation label 形态，不授权 entry、exit、holding、收益、cost、模型、separability search 或 deployment。

## 2. Primary Label Base Rate

{markdown_table(primary, ['label_id', 'cluster_split_bucket', 'labelable_step_n', 'positive_step_n', 'negative_step_n', 'neutral_step_n', 'positive_rate', 'negative_rate'])}

## 3. Effective Sample Support

{markdown_table(support, ['cluster_split_bucket', 'labelable_step_n', 'positive_effective_sample_size', 'negative_effective_sample_size', 'positive_rate', 'negative_rate', 'support_status'])}

## 4. Known-failed Episode-context Exposure

{markdown_table(hard_overlap, ['known_failed_family', 'cluster_split_bucket', 'horizon_sessions', 'positive_step_n', 'failed_family_positive_share', 'all_step_failed_family_share', 'share_delta', 'hard_projection_coverage', 'overlap_status'], max_rows=16)}

15B hard taxonomy 是 episode/cluster full-path descriptor，投影到 h20 step 后只表示 known-failed episode context exposure，不是 step-local morphology rediscovery。高 exposure 只设置 caveat，不阻断 primary decision。known_failed_context_exposure_caveat = `{d['known_failed_context_exposure_caveat']}`。

15C2 soft membership 只作为 appendix / caveat，不会因为 soft coverage 不足阻断 primary decision。soft_overlap_partial_coverage_caveat = `{d['soft_overlap_partial_coverage_caveat']}`。

## 5. Authorization Boundary

label_deployment_authorized = `{d['label_deployment_authorized']}`；signal_search_authorized = `{d['signal_search_authorized']}`；model_training_authorized = `{d['model_training_authorized']}`；entry_policy_authorized = `{d['entry_policy_authorized']}`；separability_search_authorized = `{d['separability_search_authorized']}`。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: str, outputs: dict[str, Path]) -> Path:
    publishable = {
        key: value
        for key, value in outputs.items()
        if key != "manifest" and value.exists() and LOCAL_CACHE_DIR not in value.parents
    }
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": r15a.git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha(config_path),
        "decision_state": decision,
        "outputs": {key: str(value) for key, value in publishable.items()},
        "output_hashes": {key: file_sha(value) for key, value in publishable.items() if value.is_file()},
    }
    return write_json(path, payload)


def hard_gate_status(
    input_gate: str,
    upstream: pd.DataFrame,
    step_audit: pd.DataFrame,
    label_rules: pd.DataFrame,
    qfq_audit: pd.DataFrame,
    price_audit: pd.DataFrame,
    projection_status: str,
    search: pd.DataFrame,
) -> dict[str, str]:
    return {
        "input_artifact": input_gate,
        "upstream_16a_authorization": status_all(upstream, "authorization_status", {"pass"}),
        "step_lineage_adapter": status_all(step_audit, "adapter_status", {"pass"}),
        "label_rule_definition": status_all(label_rules, "rule_status", {"pass"}),
        "step_materialization": status_all(step_audit, "materialization_status", {"pass"}),
        "qfq_price_source": status_all(qfq_audit, "qfq_price_source_status", {"pass"}),
        "price_path_completeness": status_all(price_audit, "price_path_status", {"pass"}),
        "known_failed_overlap_evaluability": "pass" if projection_status == "pass" else projection_status,
        "search_accounting": status_all(search, "search_accounting_status", {"pass"}),
    }


def blocked_decision(config: dict[str, Any], reason: str) -> pd.DataFrame:
    ld = config.get("label_design", {})
    return pd.DataFrame(
        [
            {
                "decision_state": DECISION_BLOCKED,
                "next_allowed_requirement": "none",
                "primary_label_id": ld.get("primary_label_id", PRIMARY_LABEL_ID),
                "selected_threshold_id": ld.get("selected_threshold_id", "up50pct"),
                "primary_horizon_sessions": ld.get("primary_horizon_sessions", 20),
                "blocking_reason": reason,
                "label_deployment_authorized": False,
                "signal_search_authorized": False,
                "model_training_authorized": False,
                "entry_policy_authorized": False,
                "separability_search_authorized": False,
            }
        ]
    )


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for directory in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    input_audit = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 2
    if input_gate != "pass":
        decision = blocked_decision(config, input_reason)
        write_df(outputs["sequential_continuation_label_decision"], decision)
        write_manifest(outputs["manifest"], config_path, config, DECISION_BLOCKED, outputs)
        return 2

    decision_16a = read_table(resolved["upstream_16a_sampling_geometry_decision"])
    horizon_16a = read_table(resolved["upstream_16a_horizon_grid_step_readout"])
    intervals = read_table(resolved["upstream_16a_episode_interval_panel"])
    price_15a = read_table(resolved["upstream_15a_price_path_completeness_audit"])
    price_15b = read_table(resolved["upstream_15b_price_path_completeness_audit"])
    membership = read_table(resolved["upstream_15b_membership_audit"])
    taxonomy = read_table(resolved["upstream_15b_taxonomy_assignment_panel"])
    soft = read_table(resolved["upstream_15c2_anchor_soft_membership_panel"]) if resolved["upstream_15c2_anchor_soft_membership_panel"].exists() else None

    upstream = build_upstream_16a_authorization_audit(decision_16a, config)
    label_rules = build_label_rule_definition_audit(config)
    steps = materialize_steps(intervals, config)
    step_audit = build_step_materialization_audit(steps, horizon_16a)
    qfq_audit, qfq_cache = build_qfq_price_source_audit(steps, resolved["stock_daily_qfq_dir"], price_15a, price_15b)
    price_audit = build_price_path_completeness_audit(qfq_audit, steps, price_15a, price_15b)
    labels = compute_continuation_labels(steps, qfq_cache, config)
    if not labels.empty:
        labels = labels.merge(
            steps[["step_id", "anchor_n"]],
            on="step_id",
            how="left",
        )
    base = build_continuation_label_base_rate_readout(labels)
    validation_stress = base.loc[
        base["label_id"].astype(str).eq(STRESS_LABEL_ID)
        & base["cluster_split_bucket"].astype(str).eq("validation")
    ].rename(columns={"positive_rate": "continuation_survival_positive_rate"})
    projection, projection_status, projection_reason = build_known_failed_cluster_projection(membership, taxonomy, soft, config)
    overlap, overlap_panel = build_known_failed_overlap_readout(labels, projection)
    if not overlap.empty:
        max_share = float(config["label_design"]["known_failed_positive_share_max"])
        max_delta = float(config["label_design"]["known_failed_share_delta_max"])
        bad = (finite(overlap["failed_family_positive_share"]) > max_share) | (finite(overlap["share_delta"]) > max_delta)
        overlap.loc[bad, "overlap_status"] = "episode_context_exposure_caveat"
        overlap.loc[bad, "blocking_reason"] = "nonblocking_episode_context_exposure_caveat"
    search = build_search_accounting_audit(config)
    support = build_effective_sample_label_support_readout(base, config)
    gates = hard_gate_status(input_gate, upstream, step_audit, label_rules, qfq_audit, price_audit, projection_status, search)
    decision = build_sequential_continuation_label_decision(config, gates, base, overlap, validation_stress)
    if projection_status != "pass":
        decision["blocking_reason"] = projection_reason

    write_df(outputs["upstream_16a_authorization_audit"], upstream)
    write_df(outputs["step_lineage_adapter_audit"], step_audit)
    write_df(outputs["step_materialization_audit"], step_audit)
    write_df(outputs["qfq_price_source_audit"], qfq_audit)
    write_df(outputs["price_path_completeness_audit"], price_audit)
    write_df(outputs["label_rule_definition_audit"], label_rules)
    write_df(outputs["materialized_step_panel"], steps)
    write_df(outputs["continuation_label_step_panel"], labels)
    write_df(outputs["continuation_label_panel_readout"], labels[
        [
            "step_id",
            "label_id",
            "threshold_id",
            "cluster_split_bucket",
            "instrument",
            "episode_cluster_id",
            "horizon_sessions",
            "step_index",
            "step_start_pos",
            "step_end_pos",
            "step_start_date",
            "step_end_date",
            "step_start_qfq_close",
            "step_end_qfq_close",
            "max_drawdown_from_step_start",
            "step_end_price_ratio_minus_one_for_label_rule",
            "continuation_positive",
            "continuation_negative",
            "continuation_neutral",
            "label_rule_status",
        ]
    ])
    write_df(outputs["continuation_label_base_rate_readout"], base)
    write_df(outputs["continuation_label_by_split_readout"], base.loc[base["horizon_sessions"].eq(config["label_design"]["primary_horizon_sessions"])])
    write_df(outputs["continuation_label_by_horizon_sensitivity_readout"], base.loc[base["threshold_id"].eq(config["label_design"]["selected_threshold_id"])])
    write_df(outputs["continuation_label_by_threshold_sensitivity_readout"], base.loc[base["horizon_sessions"].eq(config["label_design"]["primary_horizon_sessions"])])
    write_df(outputs["validation_stress_readout"], validation_stress)
    write_df(outputs["effective_sample_label_support_readout"], support)
    write_df(outputs["known_failed_overlap_readout"], overlap)
    write_df(outputs["known_failed_overlap_panel"], overlap_panel)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["sequential_continuation_label_decision"], decision)
    write_text(outputs["report"], render_report(decision, base, overlap, support))
    write_manifest(outputs["manifest"], config_path, config, str(decision.iloc[0]["decision_state"]), outputs)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())

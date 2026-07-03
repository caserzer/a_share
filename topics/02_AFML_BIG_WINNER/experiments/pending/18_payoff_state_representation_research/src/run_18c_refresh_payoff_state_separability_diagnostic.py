#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "18C_refresh_payoff_state_separability_diagnostic"
EXPERIMENT_ID = "18_payoff_state_representation_research"
PHASE_ID = "18C"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_18c_refresh_payoff_state_separability_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
FIGURE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "figures" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID

AUTH_FALSE_COLUMNS = (
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
)
HARD_GATES = (
    "upstream_18e_contract_gate",
    "input_artifact_gate",
    "matrix_contract_replay_gate",
    "model_registry_gate",
    "train_only_fit_gate",
    "oos_no_tuning_gate",
    "rank_ic_support_gate",
    "monotonicity_support_gate",
    "bucket_lift_gate",
    "bootstrap_ci_gate",
    "baseline_improvement_gate",
    "risk_only_gate",
    "binary_sanity_boundary_gate",
    "search_accounting_gate",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run refreshed EP18C payoff-state separability diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    parser.add_argument("--check-inputs-only", action="store_true")
    return parser.parse_args(argv)


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


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
        "score_panel": LOCAL_CACHE_DIR / "refreshed_payoff_state_score_panel.parquet",
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_18e_handoff_audit": TABLE_DIR / "upstream_18e_handoff_audit.csv",
        "matrix_contract_replay_audit": TABLE_DIR / "refreshed_matrix_contract_replay_audit.csv",
        "model_registry": TABLE_DIR / "payoff_state_model_registry.csv",
        "model_cv_readout": TABLE_DIR / "payoff_state_model_cv_readout.csv",
        "model_coefficients": TABLE_DIR / "payoff_state_model_coefficients.csv",
        "oos_rank_readout": TABLE_DIR / "payoff_state_oos_rank_readout.csv",
        "decile_monotonicity": TABLE_DIR / "payoff_state_decile_monotonicity.csv",
        "bucket_lift": TABLE_DIR / "payoff_state_bucket_lift.csv",
        "bootstrap_ci": TABLE_DIR / "payoff_state_bootstrap_ci.csv",
        "topk_removal_sensitivity": TABLE_DIR / "topk_removal_sensitivity.csv",
        "family_removal_sensitivity": TABLE_DIR / "family_removal_sensitivity.csv",
        "baseline_comparison": TABLE_DIR / "baseline_comparison_readout.csv",
        "binary_sanity": TABLE_DIR / "binary_sanity_readout.csv",
        "search_accounting": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "payoff_state_separability_decision.csv",
        "decile_curve": FIGURE_DIR / "payoff_state_decile_curve.png",
        "score_surface": FIGURE_DIR / "score_vs_payoff_rank_surface.png",
        "report": REPORT_DIR / "payoff_state_separability_refresh_report.md",
        "manifest": MANIFEST_DIR / "18C_refresh_payoff_state_separability_diagnostic_manifest.json",
        "input_manifest": MANIFEST_DIR / "input_artifact_manifest_18c_refresh.json",
        "score_panel_manifest": MANIFEST_DIR / "refreshed_payoff_state_score_panel_manifest.json",
    }


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_df(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_placeholder_figure(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.axis("off")
    ax.text(0.5, 0.58, title, ha="center", va="center", fontsize=12)
    ax.text(0.5, 0.40, "Not scored: refreshed 18E matrix local cache is missing.", ha="center", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def count_rows(path: Path) -> int | None:
    if not path.exists() or path.is_dir():
        return None
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith((".csv", ".csv.gz")):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".json"):
        return 1
    if suffixes.endswith(".md"):
        return len(path.read_text(encoding="utf-8").splitlines())
    return None


def header_columns(path: Path) -> list[str]:
    if not path.exists() or path.is_dir():
        return []
    suffixes = "".join(path.suffixes)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path, engine="pyarrow").columns)
    return []


def read_table(path: Path) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def bool_like(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def false_like(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no", ""}
    if pd.isna(value):
        return False
    return not bool(value)


def required_columns_for_key(config: dict[str, Any], key: str) -> set[str]:
    identity = set(config["identity_key_columns"])
    split = {config["split_column"]}
    mapping: dict[str, set[str]] = {
        "eighteen_e_refreshed_matrix": identity | split,
        "eighteen_e_decision": {"decision_state", "next_allowed_requirement", "next_allowed_requirement_scope", "all_hard_gates_pass", *AUTH_FALSE_COLUMNS},
        "eighteen_e_schema": {"column_name", "column_role", "primary_model_feature", "target_column"},
        "eighteen_e_family_coverage": {"feature_family_id", "observed_model_ready_feature_n", "family_coverage_status"},
        "eighteen_e_lineage_audit": {"feature_name", "feature_lineage_gate"},
        "eighteen_e_target_binding_audit": {"bound_matrix_row_n", "target_binding_gate"},
        "eighteen_e_missingness_audit": {"feature_name", "finite_rate"},
        "eighteen_e_pit_availability_audit": {"feature_name", "pit_t0_availability_gate"},
        "eighteen_e_preprocessing_audit": {"feature_name", "model_ready_feature_name", "fit_split", "fit_row_n"},
        "eighteen_e_forbidden_feature_audit": {"column_name", "forbidden_feature_gate"},
        "eighteen_e_search_accounting": {"phase_id", "search_accounting_gate"},
        "eighteen_a_target_definition_registry": {"target_id", "lineage_hash"},
        "eighteen_a_target_denominator_reconciliation": {"split_bucket", "labelable_step_n", "neutral_step_n"},
        "eighteen_a_payoff_cutoff_freeze": {"threshold_id", "train_absolute_payoff_cutoff", "split_local_recompute_used"},
        "eighteen_a_neutral_preservation_audit": {"split_bucket", "neutral_preservation_gate"},
    }
    if key.endswith("_manifest") or key.endswith("_report") or key.startswith("requirement") or key in {"research_plan", "umbrella_requirement", "eighteen_a_target_contract_doc"}:
        return set()
    return mapping.get(key, set())


def expected_manifest_hashes(resolved: dict[str, Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    manifest_path = resolved.get("eighteen_e_manifest")
    if manifest_path and manifest_path.exists():
        manifest = read_json(manifest_path)
        table_hashes = manifest.get("publishable_table_sha256_by_name", {})
        table_key_map = {
            "eighteen_e_decision": "refreshed_feature_matrix_decision",
            "eighteen_e_schema": "refreshed_feature_matrix_schema",
            "eighteen_e_family_coverage": "refreshed_feature_family_coverage",
            "eighteen_e_lineage_audit": "refreshed_feature_lineage_audit",
            "eighteen_e_target_binding_audit": "refreshed_feature_target_binding_audit",
            "eighteen_e_missingness_audit": "refreshed_feature_missingness_audit",
            "eighteen_e_pit_availability_audit": "refreshed_feature_pit_availability_audit",
            "eighteen_e_preprocessing_audit": "train_only_preprocessing_audit",
            "eighteen_e_forbidden_feature_audit": "forbidden_feature_audit",
            "eighteen_e_search_accounting": "search_accounting_audit",
        }
        for artifact_key, table_key in table_key_map.items():
            value = table_hashes.get(table_key)
            if value:
                hashes[artifact_key] = str(value)
        if manifest.get("report_sha256"):
            hashes["eighteen_e_report"] = str(manifest["report_sha256"])

    matrix_manifest_path = resolved.get("refreshed_matrix_manifest")
    if matrix_manifest_path and matrix_manifest_path.exists():
        matrix_manifest = read_json(matrix_manifest_path)
        if matrix_manifest.get("matrix_sha256"):
            hashes["eighteen_e_refreshed_matrix"] = str(matrix_manifest["matrix_sha256"])
        if matrix_manifest.get("schema_sha256"):
            hashes["eighteen_e_schema"] = str(matrix_manifest["schema_sha256"])
    return hashes


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    rows = []
    manifest_hashes = expected_manifest_hashes(resolved)
    for key, meta in config["required_artifacts"].items():
        path = resolved[key]
        exists = path.exists()
        required = required_columns_for_key(config, key)
        cols = set(header_columns(path)) if exists else set()
        missing_cols = sorted(required - cols) if exists else []
        sha = file_sha(path) if exists and path.is_file() else ""
        expected_sha = manifest_hashes.get(key)
        hash_status = "missing" if not exists else "not_manifested" if not expected_sha else "exact_match" if sha == expected_sha else "mismatch"
        blockers = []
        if not exists:
            blockers.append("missing")
            if key == "eighteen_e_refreshed_matrix":
                blockers.append("missing_local_cache_refreshed_matrix")
                blockers.append("rerun_18e_full_to_regenerate")
        if missing_cols:
            blockers.append("schema_missing:" + ",".join(missing_cols))
        if hash_status == "mismatch":
            blockers.append("manifest_hash_mismatch")
        schema_status = "pass" if exists and not missing_cols else "fail"
        rows.append(
            {
                "artifact_key": key,
                "artifact_role": meta["role"],
                "required_flag": "required",
                "resolver_alias": key,
                "resolved_path": str(path),
                "relative_path": relative_to_topic(path),
                "source_experiment_id": meta["source_experiment_id"],
                "source_phase_id": meta["source_phase_id"],
                "row_count": count_rows(path) if exists else "",
                "sha256": sha,
                "source_kind": "publishable_or_local_cache",
                "schema_status": schema_status,
                "read_status": "pass" if exists else "missing",
                "expected_row_n": "",
                "observed_row_n": count_rows(path) if exists else "",
                "cache_hash_validated": hash_status,
                "cache_schema_validated": schema_status == "pass",
                "cache_key_reconciliation_gate": "pass" if hash_status in {"exact_match", "not_manifested"} and schema_status == "pass" else "fail",
                "absolute_path_mismatch_ignored": False,
                "blocking_reason": ";".join(blockers),
            }
        )
    audit = pd.DataFrame(rows)
    gate = "pass" if audit["read_status"].eq("pass").all() and audit["schema_status"].eq("pass").all() and ~audit["cache_hash_validated"].eq("mismatch").any() else "fail"
    return audit, gate


def build_upstream_18e_handoff_audit(config: dict[str, Any], resolved: dict[str, Path], input_audit: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    expected = config["expected"]
    rows: list[dict[str, Any]] = []
    decision_path = resolved["eighteen_e_decision"]
    if decision_path.exists():
        decision = read_table(decision_path).iloc[0]
        checks: list[tuple[str, Any]] = [
            ("decision_state", expected["upstream_18e_decision_state"]),
            ("next_allowed_requirement", expected["upstream_18e_next_allowed_requirement"]),
            ("next_allowed_requirement_scope", expected["upstream_18e_next_allowed_requirement_scope"]),
            ("all_hard_gates_pass", True),
            ("upstream_18d_contract_gate", "pass"),
            ("input_artifact_gate", "pass"),
            ("feature_family_recommendation_replay_gate", "pass"),
            ("refreshed_feature_source_gate", "pass"),
            ("refreshed_feature_formula_gate", "pass"),
            ("refreshed_feature_lineage_gate", "pass"),
            ("pit_t0_availability_gate", "pass"),
            ("target_binding_gate", "pass"),
            ("feature_matrix_schema_gate", "pass"),
            ("feature_complete_rate_gate", "pass"),
            ("feature_family_coverage_gate", "pass"),
            ("train_only_preprocessing_gate", "pass"),
            ("forbidden_feature_gate", "pass"),
            ("search_accounting_gate", "pass"),
        ]
        checks.extend((col, False) for col in AUTH_FALSE_COLUMNS)
        for field, exp in checks:
            observed = decision.get(field, "")
            ok = bool_like(observed) if exp is True else false_like(observed) if exp is False else str(observed) == str(exp)
            rows.append({"contract_check_id": field, "observed_value": observed, "expected_value": exp, "upstream_18e_contract_gate": "pass" if ok else "fail", "blocking_reason": "" if ok else f"{field}_mismatch"})
    else:
        rows.append({"contract_check_id": "decision_artifact_exists", "observed_value": "missing", "expected_value": "present", "upstream_18e_contract_gate": "fail", "blocking_reason": "eighteen_e_decision_missing"})

    missing_18e = input_audit.loc[input_audit["source_phase_id"].eq("18E") & ~input_audit["read_status"].eq("pass")]
    rows.append(
        {
            "contract_check_id": "all_required_18e_artifacts_present",
            "observed_value": int(len(missing_18e)),
            "expected_value": 0,
            "upstream_18e_contract_gate": "pass" if missing_18e.empty else "fail",
            "blocking_reason": "" if missing_18e.empty else "missing_required_18e_artifact",
        }
    )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["upstream_18e_contract_gate"].eq("pass").all() else "fail"


def build_matrix_contract_replay_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    expected = config["expected"]
    matrix_path = resolved["eighteen_e_refreshed_matrix"]
    schema_path = resolved["eighteen_e_schema"]
    manifest_path = resolved["refreshed_matrix_manifest"]
    rows = []
    if not matrix_path.exists():
        rows.append({"check_id": "matrix_file_exists", "expected_value": "present", "observed_value": "missing", "matrix_contract_replay_gate": "fail", "blocking_reason": "missing_local_cache_refreshed_matrix;rerun_18e_full_to_regenerate"})
    else:
        rows.append({"check_id": "matrix_file_exists", "expected_value": "present", "observed_value": "present", "matrix_contract_replay_gate": "pass", "blocking_reason": ""})
        rows.append({"check_id": "matrix_sha256", "expected_value": expected["matrix_sha256"], "observed_value": file_sha(matrix_path), "matrix_contract_replay_gate": "pass" if file_sha(matrix_path) == expected["matrix_sha256"] else "fail", "blocking_reason": "" if file_sha(matrix_path) == expected["matrix_sha256"] else "matrix_hash_mismatch"})
    if schema_path.exists():
        schema = read_table(schema_path)
        feature_n = int(schema["primary_model_feature"].astype(str).str.lower().eq("true").sum())
        target_n = int(schema["target_column"].astype(str).str.lower().eq("true").sum())
        rows.append({"check_id": "primary_model_ready_feature_n", "expected_value": expected["primary_model_ready_feature_n"], "observed_value": feature_n, "matrix_contract_replay_gate": "pass" if feature_n == expected["primary_model_ready_feature_n"] else "fail", "blocking_reason": "" if feature_n == expected["primary_model_ready_feature_n"] else "feature_count_mismatch"})
        rows.append({"check_id": "target_column_n", "expected_value": expected["target_column_n"], "observed_value": target_n, "matrix_contract_replay_gate": "pass" if target_n == expected["target_column_n"] else "fail", "blocking_reason": "" if target_n == expected["target_column_n"] else "target_count_mismatch"})
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        rows.append({"check_id": "manifest_matrix_row_n", "expected_value": expected["matrix_row_n"], "observed_value": manifest.get("matrix_row_n"), "matrix_contract_replay_gate": "pass" if int(manifest.get("matrix_row_n", -1)) == expected["matrix_row_n"] else "fail", "blocking_reason": ""})
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["matrix_contract_replay_gate"].eq("pass").all() else "fail"


def empty_table(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def placeholder_tables() -> dict[str, pd.DataFrame]:
    return {
        "model_registry": pd.DataFrame(
            [
                {
                    "model_id": "ridge_payoff_rank_h20_v1",
                    "model_family": "ridge_regression",
                    "model_role": "primary_support_model",
                    "target_column": "y_payoff_h20",
                    "feature_column_n": 49,
                    "fit_split": "train",
                    "hyperparameters": "alpha=10.0; fit_intercept=true; solver=auto",
                    "used_for_primary_decision": True,
                    "binary_metric_used_as_primary_gate": False,
                    "training_uses_robustness_rows": False,
                    "training_uses_validation_rows": False,
                    "model_registry_gate": "pass",
                    "blocking_reason": "",
                }
            ]
        ),
        "model_cv_readout": empty_table(["cv_scheme", "model_id", "fold_id", "train_row_n", "test_row_n", "train_episode_cluster_n", "test_episode_cluster_n", "payoff_rank_ic", "decile_payoff_monotonicity_spearman", "top3_minus_bottom3_payoff_gap", "fold_status"]),
        "model_coefficients": empty_table(["model_id", "feature_name", "feature_family_id", "coefficient", "feature_train_std", "standardized_coefficient", "abs_coefficient_rank", "standardized_abs_coefficient_rank", "train_fit_row_n", "coefficient_source"]),
        "oos_rank_readout": empty_table(["split_bucket", "model_id", "target_id", "row_n", "episode_cluster_n", "rank_ic_spearman", "continue_advantage_rank_ic_spearman", "continue_advantage_replay_abs_diff", "coarse_rank_ic_vs_16x_external_delta", "rank_ic_status"]),
        "decile_monotonicity": empty_table(["split_bucket", "model_id", "decile_index", "row_n", "mean_payoff", "mean_continue_advantage", "mean_score", "score_cutoff_source", "decile_payoff_monotonicity_spearman", "top3_minus_bottom3_payoff_gap", "split_local_score_cutoff_recompute_used", "monotonicity_status"]),
        "bucket_lift": empty_table(["split_bucket", "model_id", "bucket_id", "score_cutoff_source", "score_cutoff_value", "row_n", "split_unconditional_event_rate", "bucket_event_rate", "bucket_lift", "target_column", "split_local_score_cutoff_recompute_used", "bucket_lift_status"]),
        "bootstrap_ci": empty_table(["split_bucket", "model_id", "metric_id", "point_estimate", "cluster_bootstrap_rank_ic_ci_low", "cluster_bootstrap_rank_ic_ci_high", "bootstrap_ci_level", "ci_excludes_zero_flag", "bootstrap_resample_n", "valid_bootstrap_resample_n", "invalid_bootstrap_resample_n", "bootstrap_cluster_key", "bootstrap_random_seed", "bootstrap_status"]),
        "topk_removal_sensitivity": empty_table(["sensitivity_id", "split_bucket", "model_id", "removal_type", "removed_feature_n", "removed_feature_names", "removed_feature_family_id", "base_rank_ic_spearman", "sensitivity_rank_ic_spearman", "rank_ic_retention_rate", "sensitivity_status"]),
        "family_removal_sensitivity": empty_table(["sensitivity_id", "split_bucket", "model_id", "removal_type", "removed_feature_family_id", "removed_feature_n", "removed_feature_names", "base_rank_ic_spearman", "sensitivity_rank_ic_spearman", "rank_ic_retention_rate", "family_role", "refresh_family_flag", "risk_only_focus_flag", "sensitivity_status", "blocking_reason"]),
        "baseline_comparison": empty_table(["comparison_id", "split_bucket", "model_id", "baseline_id", "metric_id", "model_denominator_type", "baseline_denominator_type", "baseline_role", "model_value", "baseline_value", "delta_vs_baseline", "required_delta", "hard_gate_used", "comparison_status"]),
        "binary_sanity": empty_table(["split_bucket", "model_id", "target_column", "denominator_type", "row_n", "positive_n", "negative_n", "neutral_n", "roc_auc", "average_precision", "split_unconditional_positive_rate", "precision_lift", "binary_metric_used_as_primary_gate", "binary_sanity_status"]),
        "search_accounting": pd.DataFrame(
            [
                {
                    "search_family": "18C_refresh_contract_fail_closed",
                    "phase_id": "18C",
                    "model_family_registry_predeclared": True,
                    "primary_model_predeclared": True,
                    "no_feature_selection_from_target_correlation": True,
                    "no_feature_selection_from_robustness": True,
                    "no_feature_selection_from_validation": True,
                    "no_model_family_selection_from_robustness": True,
                    "no_model_family_selection_from_validation": True,
                    "no_threshold_tuning_on_robustness": True,
                    "no_threshold_tuning_on_validation": True,
                    "no_split_local_payoff_cutoff_recompute": True,
                    "no_split_local_score_threshold_recompute_for_gate": True,
                    "binary_metric_not_primary_gate": True,
                    "validation_stress_readout_only": True,
                    "no_entry_policy_authorized": True,
                    "no_exit_policy_authorized": True,
                    "no_holding_policy_authorized": True,
                    "no_portfolio_backtest_authorized": True,
                    "no_model_deployment_authorized": True,
                    "no_production_signal_authorized": True,
                    "no_live_trading_authorized": True,
                    "search_accounting_gate": "pass",
                    "blocking_reason": "",
                }
            ]
        ),
    }


def build_decision(config: dict[str, Any], upstream_gate: str, input_gate: str, matrix_gate: str) -> pd.DataFrame:
    gates = {
        "upstream_18e_contract_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "matrix_contract_replay_gate": matrix_gate,
        "model_registry_gate": "pass",
        "train_only_fit_gate": "fail",
        "oos_no_tuning_gate": "pass",
        "rank_ic_support_gate": "fail",
        "monotonicity_support_gate": "fail",
        "bucket_lift_gate": "fail",
        "bootstrap_ci_gate": "fail",
        "baseline_improvement_gate": "fail",
        "risk_only_gate": "fail",
        "binary_sanity_boundary_gate": "pass",
        "search_accounting_gate": "pass",
    }
    if upstream_gate != "pass":
        decision = "18C_refresh_upstream_18e_contract_blocked"
    elif input_gate != "pass":
        decision = "18C_refresh_input_artifact_blocked"
    elif matrix_gate != "pass":
        decision = "18C_refresh_matrix_contract_replay_blocked"
    else:
        decision = "18C_refresh_separability_contract_blocked"
    row = {
        "decision_state": decision,
        "next_allowed_requirement": "none",
        "next_allowed_requirement_scope": "none",
        "all_hard_gates_pass": False,
        **gates,
        "validation_stress_evaluable": False,
        "validation_stress_caveat": "not_evaluable_until_full_refresh_runner_scores_matrix",
        **{col: False for col in AUTH_FALSE_COLUMNS},
        "blocking_reason": decision,
    }
    return pd.DataFrame([row])


def build_report(decision: pd.DataFrame, input_audit: pd.DataFrame, upstream: pd.DataFrame, matrix_contract: pd.DataFrame) -> str:
    d = decision.iloc[0]
    missing = input_audit.loc[~input_audit["read_status"].eq("pass"), ["artifact_key", "blocking_reason"]]
    return f"""# Refreshed 18C Payoff-state Separability Diagnostic Report

## Decision

decision_state = {d["decision_state"]}
next_allowed_requirement = {d["next_allowed_requirement"]}
next_allowed_requirement_scope = {d["next_allowed_requirement_scope"]}

This refreshed 18C runner is fail-closed. It does not authorize policy,
backtest, deployment, production signal, or live trading.

## Missing Inputs

{missing.to_markdown(index=False) if not missing.empty else "No missing inputs."}

## 18E Handoff

{upstream.to_markdown(index=False)}

## Matrix Contract Replay

{matrix_contract.to_markdown(index=False)}
"""


def write_all_outputs(config: dict[str, Any], resolved: dict[str, Path], outputs: dict[str, Path], input_audit: pd.DataFrame, upstream: pd.DataFrame, matrix_contract: pd.DataFrame, decision: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tables = placeholder_tables()
    write_df(outputs["input_artifact_audit"], input_audit)
    write_df(outputs["upstream_18e_handoff_audit"], upstream)
    write_df(outputs["matrix_contract_replay_audit"], matrix_contract)
    for key, frame in tables.items():
        write_df(outputs[key], frame)
    write_df(outputs["decision"], decision)
    write_text(outputs["report"], build_report(decision, input_audit, upstream, matrix_contract))
    # Placeholders keep manifest references deterministic while making it clear no scoring occurred.
    outputs["score_panel"].parent.mkdir(parents=True, exist_ok=True)
    empty_table(["score_panel_status", "blocking_reason"]).to_parquet(outputs["score_panel"], index=False)
    write_placeholder_figure(outputs["decile_curve"], "Refreshed 18C Decile Curve")
    write_placeholder_figure(outputs["score_surface"], "Refreshed 18C Score Surface")
    write_manifests(config, resolved, outputs, input_audit, decision)
    return tables


def write_manifests(config: dict[str, Any], resolved: dict[str, Path], outputs: dict[str, Path], input_audit: pd.DataFrame, decision: pd.DataFrame) -> None:
    write_json(
        outputs["input_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_artifacts": input_audit.to_dict(orient="records"),
        },
    )
    write_json(
        outputs["score_panel_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "score_panel_file": relative_to_topic(outputs["score_panel"]),
            "score_panel_sha256": file_sha(outputs["score_panel"]),
            "source_18e_matrix_sha256": file_sha(resolved["eighteen_e_refreshed_matrix"]) if resolved["eighteen_e_refreshed_matrix"].exists() else "",
            "row_count": count_rows(outputs["score_panel"]),
            "score_panel_status": "not_scored_fail_closed",
        },
    )
    d = decision.iloc[0]
    publishable_tables = {
        key: file_sha(path)
        for key, path in outputs.items()
        if path.suffix == ".csv" and path.exists()
    }
    write_json(
        outputs["manifest"],
        {
            "run_id": RUN_ID,
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "requirement_file_sha256": file_sha(EXPERIMENT_DIR / "requirement_18c_refresh_payoff_state_separability_diagnostic.md"),
            "base_requirement_file_sha256": file_sha(EXPERIMENT_DIR / "requirement_18c_payoff_state_separability_diagnostic.md"),
            "config_file_sha256": file_sha(CONFIG_PATH),
            "runner_file_sha256": file_sha(Path(__file__)),
            "input_artifact_manifest_sha256": file_sha(outputs["input_manifest"]),
            "source_18e_matrix_sha256": file_sha(resolved["eighteen_e_refreshed_matrix"]) if resolved["eighteen_e_refreshed_matrix"].exists() else "",
            "source_18e_schema_sha256": file_sha(resolved["eighteen_e_schema"]) if resolved["eighteen_e_schema"].exists() else "",
            "score_panel_sha256": file_sha(outputs["score_panel"]),
            "publishable_table_sha256_by_name": publishable_tables,
            "report_sha256": file_sha(outputs["report"]),
            "decision_state": d["decision_state"],
            "next_allowed_requirement": d["next_allowed_requirement"],
            "next_allowed_requirement_scope": d["next_allowed_requirement_scope"],
            "all_hard_gates_pass": bool(d["all_hard_gates_pass"]),
            "primary_model_id": "ridge_payoff_rank_h20_v1",
            "primary_feature_n": int(config["expected"]["primary_model_ready_feature_n"]),
            "validation_role": "stress_readout_only",
            **{col: bool(d[col]) for col in AUTH_FALSE_COLUMNS},
        },
    )


def run(config_path: str | Path = CONFIG_PATH, mode: str = "full") -> dict[str, Any]:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit, input_gate = build_input_artifact_audit(config, resolved)
    upstream, upstream_gate = build_upstream_18e_handoff_audit(config, resolved, input_audit)
    matrix_contract, matrix_gate = build_matrix_contract_replay_audit(config, resolved)
    decision = build_decision(config, upstream_gate, input_gate, matrix_gate)

    write_df(outputs["input_artifact_audit"], input_audit)
    write_json(
        outputs["input_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_artifacts": input_audit.to_dict(orient="records"),
        },
    )
    if mode == "check-inputs":
        return {"input_artifact_gate": input_gate, "input_artifact_audit": input_audit, "upstream": upstream, "decision": decision}

    tables = write_all_outputs(config, resolved, outputs, input_audit, upstream, matrix_contract, decision)
    return {
        "input_artifact_gate": input_gate,
        "input_artifact_audit": input_audit,
        "upstream": upstream,
        "matrix_contract": matrix_contract,
        "decision": decision,
        **tables,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "check-inputs" if args.check_inputs_only else args.mode
    run(args.config, mode=mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
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
BASE_18C_RUNNER_PATH = EXPERIMENT_DIR / "src" / "run_18c_payoff_state_separability_diagnostic.py"

SPLITS = ("train", "robustness", "validation")
PRIMARY_MODEL_ID = "ridge_payoff_rank_h20_v1"
VOL_BASELINE_ID = "volatility20d_defense_baseline"
TARGET_COLUMNS = (
    "label_class",
    "continuation_positive",
    "continuation_negative",
    "continuation_neutral",
    "y_payoff_h20",
    "y_signed_max_drawdown_h20",
    "continue_value",
    "defend_value",
    "continue_advantage",
    "defend_advantage",
    "o5_incremental",
    "payoff_ordinal_state",
    "risk_state_dd08",
    "risk_state_dd10",
    "risk_state_dd12",
    "binary_positive_negative",
    "top30_yes_no",
    "top20_yes_no",
    "drawdown_dd10_yes_no",
)
SCORE_MODEL_IDS = (
    "ridge_payoff_rank_h20_v1",
    "elastic_net_payoff_rank_h20_v1",
    "ridge_ordinal_payoff_state_v1",
    "ridge_logistic_top30_sanity_v1",
    "ridge_logistic_top20_sanity_v1",
    "shallow_tree_payoff_depth2_v1",
)
SCORE_PANEL_COLUMNS = [
    "step_id",
    "label_id",
    "threshold_id",
    "horizon_sessions",
    "instrument",
    "episode_cluster_id",
    "step_index",
    "step_start_date",
    "step_end_date",
    "cluster_split_bucket",
    "y_payoff_h20",
    "continue_advantage",
    "payoff_ordinal_state",
    "top30_yes_no",
    "top20_yes_no",
    "binary_positive_negative",
    "ridge_payoff_rank_h20_v1_score",
    "elastic_net_payoff_rank_h20_v1_score",
    "ridge_ordinal_payoff_state_v1_score",
    "ridge_logistic_top30_sanity_v1_score",
    "ridge_logistic_top20_sanity_v1_score",
    "shallow_tree_payoff_depth2_v1_score",
    "ridge_payoff_rank_h20_v1_train_score_decile",
    "ridge_payoff_rank_h20_v1_train_score_top30_bucket",
    "ridge_payoff_rank_h20_v1_train_score_top20_bucket",
    "score_cutoff_source",
    "split_local_score_cutoff_recompute_used",
    "source_18e_matrix_sha256",
    "score_panel_status",
    "blocking_reason",
]
ORDINAL_MAPPING = {
    "state_0_below_top30_payoff": 0,
    "state_1_top30_to_top20_payoff": 1,
    "state_2_top20_to_top10_payoff": 2,
    "state_3_top10_extreme_payoff": 3,
}
DEFAULT_MODELS = {
    "ridge_payoff_rank_h20_v1": {"family": "ridge_regression", "target_column": "y_payoff_h20", "alpha": 10.0, "fit_intercept": True, "used_for_primary_decision": True},
    "elastic_net_payoff_rank_h20_v1": {"family": "elastic_net_regression", "target_column": "y_payoff_h20", "alpha": 0.0005, "l1_ratio": 0.10, "fit_intercept": True, "max_iter": 10000, "random_state": 1818, "used_for_primary_decision": False},
    "ridge_ordinal_payoff_state_v1": {"family": "ridge_regression_on_ordinal_state", "target_column": "payoff_ordinal_state_int", "alpha": 10.0, "fit_intercept": True, "used_for_primary_decision": False},
    "shallow_tree_payoff_depth2_v1": {"family": "decision_tree_regressor", "target_column": "y_payoff_h20", "max_depth": 2, "min_samples_leaf_floor": 50, "min_samples_leaf_train_fraction": 0.02, "random_state": 1818, "used_for_primary_decision": False},
    "ridge_logistic_top30_sanity_v1": {"family": "logistic_regression_l2", "target_column": "top30_yes_no", "penalty": "l2", "C": 1.0, "class_weight": "balanced", "solver": "liblinear", "max_iter": 1000, "random_state": 1818, "used_for_primary_decision": False},
    "ridge_logistic_top20_sanity_v1": {"family": "logistic_regression_l2", "target_column": "top20_yes_no", "penalty": "l2", "C": 1.0, "class_weight": "balanced", "solver": "liblinear", "max_iter": 1000, "random_state": 1818, "used_for_primary_decision": False},
}
DEFAULT_CV = {"scheme": "episode_cluster_grouped_cv", "fold_n": 5, "fold_seed": 1818}
SIXTEEN_X_CONTEXT = {
    "payoff_probe_id": "payoff_rank_probe_v1",
    "robustness_payoff_rank_ic": 0.05187674283077765,
    "robustness_decile_monotonicity_spearman": 0.16363636363636364,
    "robustness_cluster_bootstrap_rank_ic_ci_low": 0.007705547248002782,
}
TARGET_LINEAGE_HASH = "602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3"

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


def load_base_18c_runner():
    spec = importlib.util.spec_from_file_location("run_18c_base_for_refresh", BASE_18C_RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BASE_18C = load_base_18c_runner()


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
    primary_key = set(config.get("primary_identity_key_columns", ["step_id", "label_id"]))
    full_key = set(config.get("full_lineage_key_columns", config.get("identity_key_columns", [])))
    split = {config["split_column"]}
    mapping: dict[str, set[str]] = {
        "eighteen_e_refreshed_matrix": primary_key | full_key | split | set(TARGET_COLUMNS),
        "eighteen_e_decision": {"decision_state", "next_allowed_requirement", "next_allowed_requirement_scope", "all_hard_gates_pass", *AUTH_FALSE_COLUMNS},
        "eighteen_e_schema": {"column_name", "column_role", "feature_family_id", "raw_feature_name", "model_ready_feature_name", "primary_model_feature", "target_column"},
        "eighteen_e_family_coverage": {"feature_family_id", "observed_model_ready_feature_n", "family_coverage_status"},
        "eighteen_e_lineage_audit": {"candidate_family_id", "feature_id", "candidate_feature_id", "lineage_scope", "pit_valid_status", "t0_available_status", "lineage_before_correlation_gate"},
        "eighteen_e_target_binding_audit": {"refreshed_matrix_row_n", "refreshed_identity_key_n", "refreshed_duplicate_key_n", "neutral_row_n", "target_binding_gate"},
        "eighteen_e_missingness_audit": {"feature_name", "finite_rate"},
        "eighteen_e_pit_availability_audit": {"candidate_family_id", "feature_id", "candidate_feature_id", "pit_valid_status", "t0_available_status"},
        "eighteen_e_preprocessing_audit": {"feature_name", "model_ready_feature_name", "fit_split", "fit_row_n", "status"},
        "eighteen_e_forbidden_feature_audit": {"column_name", "forbidden_feature_gate"},
        "eighteen_e_search_accounting": {"phase_id", "no_model_training", "no_scoring", "no_entry_policy_authorized", "no_live_trading_authorized", "search_accounting_gate"},
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

    invalid_18e = input_audit.loc[
        input_audit["source_phase_id"].eq("18E")
        & ~input_audit["cache_key_reconciliation_gate"].eq("pass")
    ]
    rows.append(
        {
            "contract_check_id": "all_required_18e_artifacts_present_and_valid",
            "observed_value": int(len(invalid_18e)),
            "expected_value": 0,
            "upstream_18e_contract_gate": "pass" if invalid_18e.empty else "fail",
            "blocking_reason": "" if invalid_18e.empty else "invalid_required_18e_artifact",
        }
    )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["upstream_18e_contract_gate"].eq("pass").all() else "fail"


def build_matrix_contract_replay_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    expected = config["expected"]
    matrix_path = resolved["eighteen_e_refreshed_matrix"]
    schema_path = resolved["eighteen_e_schema"]
    manifest_path = resolved["refreshed_matrix_manifest"]
    rows: list[dict[str, Any]] = []

    def add(check_id: str, expected_value: Any, observed_value: Any, ok: bool, reason: str | None = None) -> None:
        rows.append(
            {
                "check_id": check_id,
                "expected_value": expected_value,
                "observed_value": observed_value,
                "matrix_contract_replay_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else reason or f"{check_id}_mismatch",
            }
        )

    if not matrix_path.exists():
        add("matrix_file_exists", "present", "missing", False, "missing_local_cache_refreshed_matrix;rerun_18e_full_to_regenerate")
    else:
        matrix = read_table(matrix_path)
        matrix_sha = file_sha(matrix_path)
        split_col = config["split_column"]
        primary_key = config.get("primary_identity_key_columns", ["step_id", "label_id"])
        full_key = config.get("full_lineage_key_columns", config.get("identity_key_columns", []))
        split_counts = matrix[split_col].value_counts().to_dict() if split_col in matrix.columns else {}
        add("matrix_file_exists", "present", "present", True)
        add("actual_matrix_sha256", expected["matrix_sha256"], matrix_sha, matrix_sha == expected["matrix_sha256"], "matrix_hash_mismatch")
        add("matrix_row_n", expected["matrix_row_n"], len(matrix), len(matrix) == expected["matrix_row_n"])
        add("train_row_n", expected["train_row_n"], int(split_counts.get("train", 0)), int(split_counts.get("train", 0)) == expected["train_row_n"])
        add("robustness_row_n", expected["robustness_row_n"], int(split_counts.get("robustness", 0)), int(split_counts.get("robustness", 0)) == expected["robustness_row_n"])
        add("validation_row_n", expected["validation_row_n"], int(split_counts.get("validation", 0)), int(split_counts.get("validation", 0)) == expected["validation_row_n"])
        add("primary_identity_key_columns", "step_id|label_id", "|".join(primary_key), primary_key == ["step_id", "label_id"])
        if set(primary_key).issubset(matrix.columns):
            primary_dup_n = int(matrix.duplicated(primary_key).sum())
            add("primary_identity_key_duplicate_n", 0, primary_dup_n, primary_dup_n == 0)
        else:
            add("primary_identity_key_duplicate_n", 0, "missing_key_columns", False, "primary_identity_key_columns_missing")
        if set(full_key).issubset(matrix.columns):
            full_dup_n = int(matrix.duplicated(full_key).sum())
            add("full_lineage_key_columns", "|".join(full_key), "|".join(full_key), True)
            add("full_lineage_key_duplicate_n", 0, full_dup_n, full_dup_n == 0)
        else:
            add("full_lineage_key_columns", "|".join(full_key), "missing_key_columns", False, "full_lineage_key_columns_missing")
            add("full_lineage_key_duplicate_n", 0, "missing_key_columns", False, "full_lineage_key_columns_missing")
        target_n = sum(col in matrix.columns for col in TARGET_COLUMNS)
        add("target_column_n", expected["target_column_n"], target_n, target_n == expected["target_column_n"])
    if schema_path.exists():
        schema = read_table(schema_path)
        primary_model_feature = schema["primary_model_feature"].map(bool_like)
        feature_n = int(primary_model_feature.sum())
        target_n = int(schema["target_column"].astype(str).str.lower().eq("true").sum())
        existing_feature_n = int(schema.loc[primary_model_feature & schema["feature_family_id"].astype(str).isin(["F1", "F2", "F3", "F4", "F5"])].shape[0])
        refresh_feature_n = int(schema.loc[primary_model_feature & schema["feature_family_id"].astype(str).str.startswith("M")].shape[0])
        schema_sha = file_sha(schema_path)
        add("primary_model_ready_feature_n", expected["primary_model_ready_feature_n"], feature_n, feature_n == expected["primary_model_ready_feature_n"], "feature_count_mismatch")
        add("existing_18B_model_ready_feature_n", expected["existing_18b_model_ready_feature_n"], existing_feature_n, existing_feature_n == expected["existing_18b_model_ready_feature_n"], "existing_feature_count_mismatch")
        add("refresh_model_ready_feature_n", expected["refresh_model_ready_feature_n"], refresh_feature_n, refresh_feature_n == expected["refresh_model_ready_feature_n"], "refresh_feature_count_mismatch")
        add("schema_target_column_n", expected["target_column_n"], target_n, target_n == expected["target_column_n"], "target_count_mismatch")
        add("schema_sha256", expected["schema_sha256"], schema_sha, schema_sha == expected["schema_sha256"], "schema_hash_mismatch")
    else:
        add("schema_file_exists", "present", "missing", False, "schema_missing")
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        add("matrix_source_run_id", "18E_payoff_state_feature_matrix_refresh", manifest.get("run_id"), manifest.get("run_id") == "18E_payoff_state_feature_matrix_refresh")
        add("manifest_matrix_row_n", expected["matrix_row_n"], manifest.get("matrix_row_n"), int(manifest.get("matrix_row_n", -1)) == expected["matrix_row_n"])
        add("source_18e_manifest_matrix_sha256", expected["matrix_sha256"], manifest.get("matrix_sha256"), manifest.get("matrix_sha256") == expected["matrix_sha256"], "manifest_matrix_hash_mismatch")
        add("source_18e_manifest_schema_sha256", expected["schema_sha256"], manifest.get("schema_sha256"), manifest.get("schema_sha256") == expected["schema_sha256"], "manifest_schema_hash_mismatch")
    else:
        add("refreshed_matrix_manifest_exists", "present", "missing", False, "refreshed_matrix_manifest_missing")

    target_registry = resolved.get("eighteen_a_target_definition_registry")
    if target_registry and target_registry.exists():
        registry = read_table(target_registry)
        lineage = dict(zip(registry["target_id"].astype(str), registry["lineage_hash"].astype(str), strict=False))
        add("target_lineage_hash_y_payoff_h20", TARGET_LINEAGE_HASH, lineage.get("y_payoff_h20", ""), lineage.get("y_payoff_h20") == TARGET_LINEAGE_HASH)
        add("target_lineage_hash_continue_advantage", TARGET_LINEAGE_HASH, lineage.get("continue_advantage", ""), lineage.get("continue_advantage") == TARGET_LINEAGE_HASH)

    neutral_path = resolved.get("eighteen_a_neutral_preservation_audit")
    if neutral_path and neutral_path.exists():
        neutral = read_table(neutral_path)
        gate_col = "neutral_preservation_gate"
        add(gate_col, "pass", "|".join(neutral[gate_col].astype(str).tolist()), neutral[gate_col].eq("pass").all())

    cutoff_path = resolved.get("eighteen_a_payoff_cutoff_freeze")
    if cutoff_path and cutoff_path.exists():
        cutoffs = read_table(cutoff_path)
        expected_cutoffs = {
            "high_upside_top30_stress": expected["top30_cutoff"],
            "high_upside_top20_stress": expected["top20_cutoff"],
            "high_upside_top10_stress": expected["top10_cutoff"],
        }
        observed = {
            row["threshold_id"]: float(row["train_absolute_payoff_cutoff"])
            for _, row in cutoffs.iterrows()
            if row["threshold_id"] in expected_cutoffs
        }
        cutoff_ok = set(observed) == set(expected_cutoffs) and all(abs(observed[key] - expected_cutoffs[key]) <= 1e-12 for key in expected_cutoffs)
        recompute_used = bool_like(cutoffs["split_local_recompute_used"].any())
        add("train_frozen_payoff_cutoff_value_replay", expected_cutoffs, observed, cutoff_ok)
        add("split_local_payoff_cutoff_recompute_used", False, recompute_used, not recompute_used)

    preprocessing_path = resolved.get("eighteen_e_preprocessing_audit")
    if preprocessing_path and preprocessing_path.exists():
        preprocessing = read_table(preprocessing_path)
        observed = "|".join(sorted(preprocessing["status"].astype(str).unique()))
        add("train_only_preprocessing_gate", "pass", observed, set(preprocessing["status"].astype(str)) == {"pass"})

    forbidden_path = resolved.get("eighteen_e_forbidden_feature_audit")
    if forbidden_path and forbidden_path.exists():
        forbidden = read_table(forbidden_path)
        add("forbidden_feature_gate", "pass", "|".join(forbidden["forbidden_feature_gate"].astype(str).unique()), forbidden["forbidden_feature_gate"].eq("pass").all())
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["matrix_contract_replay_gate"].eq("pass").all() else "fail"


def empty_table(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def prepared_model_config(config: dict[str, Any], resolved: dict[str, Path]) -> dict[str, Any]:
    out = deepcopy(config)
    schema = read_table(resolved["eighteen_e_schema"])
    feature_rows = schema.loc[schema["primary_model_feature"].map(bool_like)].copy()
    out["model_ready_features"] = feature_rows["model_ready_feature_name"].astype(str).tolist()
    family_map: dict[str, list[str]] = {}
    for family_id, rows in feature_rows.groupby("feature_family_id", sort=True):
        family_map[str(family_id)] = rows["model_ready_feature_name"].astype(str).tolist()
    out["feature_family_map"] = family_map
    out["ordinal_mapping"] = ORDINAL_MAPPING
    out["models"] = DEFAULT_MODELS
    out["cv"] = DEFAULT_CV
    out["primary_identity_key_columns"] = out.get("primary_identity_key_columns", ["step_id", "label_id"])
    out["full_lineage_key_columns"] = out.get("full_lineage_key_columns", out.get("identity_key_columns", []))

    expected = out["expected"]
    expected.setdefault("total_labelable_step_n", expected["matrix_row_n"])
    expected.setdefault(
        "denominators",
        {
            "train": {"labelable_step_n": expected["train_row_n"], "neutral_step_n": 5283},
            "robustness": {"labelable_step_n": expected["robustness_row_n"], "neutral_step_n": 624, "episode_cluster_n_min": 30},
            "validation": {"labelable_step_n": expected["validation_row_n"], "neutral_step_n": 159, "episode_cluster_n_min": 30},
        },
    )
    expected.setdefault("binary_blocked_classification_min_roc_auc", 0.55)
    expected.setdefault("binary_blocked_classification_min_precision_lift", 0.02)
    expected.setdefault("bootstrap_ci_level", 0.95)
    expected.setdefault("sixteen_x", SIXTEEN_X_CONTEXT)
    return out


def build_binary_sanity(config: dict[str, Any], score: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("ridge_logistic_top30_sanity_v1", "top30_yes_no"),
        ("ridge_logistic_top20_sanity_v1", "top20_yes_no"),
        (PRIMARY_MODEL_ID, "binary_positive_negative"),
    ]
    for model_id, target in specs:
        col = BASE_18C.model_score_column(model_id)
        for split in SPLITS:
            sub = score.loc[score["cluster_split_bucket"].eq(split)]
            y = sub[target].astype(bool)
            ap = BASE_18C.safe_ap(y, sub[col])
            base_rate = float(y.mean())
            rows.append(
                {
                    "split_bucket": split,
                    "model_id": model_id,
                    "target_column": target,
                    "denominator_type": "labelable_full",
                    "row_n": len(sub),
                    "positive_n": int(y.sum()),
                    "negative_n": int((~y).sum()),
                    "neutral_n": int(sub["label_class"].eq("neutral").sum()),
                    "roc_auc": BASE_18C.safe_auc(y, sub[col]),
                    "average_precision": ap,
                    "split_unconditional_positive_rate": base_rate,
                    "precision_lift": ap - base_rate if np.isfinite(ap) else np.nan,
                    "binary_metric_used_as_primary_gate": False,
                    "binary_sanity_status": "appendix_sanity_only",
                }
            )
    return pd.DataFrame(rows)


def build_family_removal_sensitivity(topk_and_family: pd.DataFrame, family_coverage: pd.DataFrame) -> pd.DataFrame:
    family = topk_and_family.loc[topk_and_family["removal_type"].eq("family")].copy()
    role_map = dict(zip(family_coverage["feature_family_id"].astype(str), family_coverage["family_role"].astype(str), strict=False))
    family["family_role"] = family["removed_feature_family_id"].astype(str).map(role_map).fillna("unknown")
    family["refresh_family_flag"] = family["removed_feature_family_id"].astype(str).str.startswith("M")
    family["risk_only_focus_flag"] = family["removed_feature_family_id"].astype(str).eq("F4")
    invalid = ~np.isfinite(family["base_rank_ic_spearman"].astype(float)) | (family["base_rank_ic_spearman"].astype(float) <= 0)
    family.loc[invalid, "sensitivity_status"] = "invalid_base_rank_ic"
    family["blocking_reason"] = np.where(invalid, "invalid_base_rank_ic", "")
    columns = [
        "sensitivity_id",
        "split_bucket",
        "model_id",
        "removal_type",
        "removed_feature_family_id",
        "removed_feature_n",
        "removed_feature_names",
        "base_rank_ic_spearman",
        "sensitivity_rank_ic_spearman",
        "rank_ic_retention_rate",
        "family_role",
        "refresh_family_flag",
        "risk_only_focus_flag",
        "sensitivity_status",
        "blocking_reason",
    ]
    return family.loc[:, columns]


def build_score_panel(config: dict[str, Any], score: pd.DataFrame, source_matrix_sha: str) -> pd.DataFrame:
    out = score.copy()
    primary_col = BASE_18C.model_score_column(PRIMARY_MODEL_ID)
    train_score = out.loc[out["cluster_split_bucket"].eq("train"), primary_col]
    out["ridge_payoff_rank_h20_v1_train_score_decile"], _ = BASE_18C.score_deciles(out[primary_col], train_score)
    out["ridge_payoff_rank_h20_v1_train_score_top30_bucket"] = out[primary_col] >= float(train_score.quantile(0.70))
    out["ridge_payoff_rank_h20_v1_train_score_top20_bucket"] = out[primary_col] >= float(train_score.quantile(0.80))
    for model_id in SCORE_MODEL_IDS:
        out[f"{model_id}_score"] = out[BASE_18C.model_score_column(model_id)]
    out["score_cutoff_source"] = "train_frozen_score_cutoff"
    out["split_local_score_cutoff_recompute_used"] = False
    out["source_18e_matrix_sha256"] = source_matrix_sha
    out["score_panel_status"] = "scored"
    out["blocking_reason"] = ""
    return out.loc[:, SCORE_PANEL_COLUMNS]


def empty_score_panel(blocking_reason: str) -> pd.DataFrame:
    frame = empty_table(SCORE_PANEL_COLUMNS)
    frame["score_panel_status"] = frame["score_panel_status"].astype("object")
    frame["blocking_reason"] = frame["blocking_reason"].astype("object")
    return frame


def build_full_report(
    input_audit: pd.DataFrame,
    upstream: pd.DataFrame,
    matrix_contract: pd.DataFrame,
    registry: pd.DataFrame,
    cv: pd.DataFrame,
    oos: pd.DataFrame,
    deciles: pd.DataFrame,
    bucket: pd.DataFrame,
    bootstrap: pd.DataFrame,
    family: pd.DataFrame,
    baseline: pd.DataFrame,
    binary: pd.DataFrame,
    search: pd.DataFrame,
    decision: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    gates = pd.DataFrame({"gate": list(HARD_GATES), "status": [d[gate] for gate in HARD_GATES]})
    primary_oos = oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID)].copy()
    primary_deciles = deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID)].copy()
    robust_family = family.loc[family["split_bucket"].eq("robustness")].copy()
    input_summary = input_audit.groupby(["read_status", "schema_status", "cache_key_reconciliation_gate"], dropna=False).size().reset_index(name="artifact_n")
    return f"""# Refreshed 18C Payoff-state Separability Diagnostic Report

## Decision

decision_state = {d["decision_state"]}
next_allowed_requirement = {d["next_allowed_requirement"]}
next_allowed_requirement_scope = {d["next_allowed_requirement_scope"]}

This refreshed 18C rerun scores the 18E 49-feature matrix with train-only low-capacity models.
It does not authorize policy, backtest, deployment, production signal, or live trading.

## Gate Summary

{gates.to_markdown(index=False)}

## Input Artifact Audit

{input_summary.to_markdown(index=False)}

## 18E Handoff

{upstream.to_markdown(index=False)}

## Refreshed Matrix Contract Replay

{matrix_contract.to_markdown(index=False)}

## Model Registry And Train-only CV

{registry.to_markdown(index=False)}

{cv.groupby("model_id", as_index=False).agg(fold_n=("fold_id", "nunique"), mean_payoff_rank_ic=("payoff_rank_ic", "mean"), mean_decile_monotonicity=("decile_payoff_monotonicity_spearman", "mean")).to_markdown(index=False)}

## Primary OOS Rank Readout

{primary_oos.to_markdown(index=False)}

## Decile Monotonicity

{primary_deciles.to_markdown(index=False)}

## Bucket Lift

{bucket.to_markdown(index=False)}

## Bootstrap CI

{bootstrap.to_markdown(index=False)}

## Family Removal Sensitivity

{robust_family.to_markdown(index=False)}

## Baseline Boundary

{baseline.to_markdown(index=False)}

## Binary Sanity Appendix

{binary.to_markdown(index=False)}

## Search Accounting

{search.to_markdown(index=False)}
"""


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
                    "run_id": RUN_ID,
                    "phase_id": "18C",
                    "scope_id": "refreshed_matrix_rerun",
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


def gate_from_bool(value: bool) -> str:
    return "pass" if bool(value) else "fail"


def build_search_accounting_audit(config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    row = {
        "search_family": "18C_refresh_payoff_state_separability_diagnostic",
        "run_id": RUN_ID,
        "phase_id": PHASE_ID,
        "scope_id": config.get("scope_id", "refreshed_matrix_rerun"),
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
    return pd.DataFrame([row]), "pass"


def build_refreshed_decision(
    config: dict[str, Any],
    gates: dict[str, str],
    oos: pd.DataFrame,
    deciles: pd.DataFrame,
    bucket: pd.DataFrame,
    bootstrap: pd.DataFrame,
    baseline: pd.DataFrame,
    family: pd.DataFrame,
    binary: pd.DataFrame,
    score_panel_status: str,
) -> pd.DataFrame:
    primary = oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness")].iloc[0]
    primary_rank = float(primary["rank_ic_spearman"])
    primary_mono = float(
        deciles.loc[
            deciles["model_id"].eq(PRIMARY_MODEL_ID) & deciles["split_bucket"].eq("robustness"),
            "decile_payoff_monotonicity_spearman",
        ].iloc[0]
    )
    ci_low = float(bootstrap["cluster_bootstrap_rank_ic_ci_low"].iloc[0])
    vol_rows = baseline.loc[baseline["comparison_id"].eq("payoff_rank_ic_vs_volatility20d")]
    vol_delta = float(vol_rows["delta_vs_baseline"].iloc[0]) if not vol_rows.empty else np.nan
    validation = oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("validation")].iloc[0]
    all_pass = score_panel_status == "scored" and all(gates[gate] == "pass" for gate in HARD_GATES)

    binary_positive = bool(
        binary.loc[
            binary["split_bucket"].eq("robustness")
            & (
                (binary["roc_auc"] >= float(config["expected"]["binary_blocked_classification_min_roc_auc"]))
                | (binary["precision_lift"] > float(config["expected"]["binary_blocked_classification_min_precision_lift"]))
            )
        ].shape[0]
    )
    primary_rank_or_mono_weak = gates["rank_ic_support_gate"] != "pass" or gates["monotonicity_support_gate"] != "pass"

    decision = "18C_payoff_state_separability_supported"
    next_req = config["expected"]["positive_next_allowed_requirement"]
    next_scope = config["expected"]["positive_next_allowed_requirement_scope"]
    blocking = ""
    if not all_pass:
        next_req = "none"
        next_scope = "none"
        if gates["upstream_18e_contract_gate"] != "pass":
            decision = "18C_refresh_upstream_18e_contract_blocked"
        elif gates["input_artifact_gate"] != "pass":
            decision = "18C_refresh_input_artifact_blocked"
        elif gates["matrix_contract_replay_gate"] != "pass":
            decision = "18C_refresh_matrix_contract_replay_blocked"
        elif gates["model_registry_gate"] != "pass":
            decision = "18C_model_registry_blocked"
        elif gates["train_only_fit_gate"] != "pass":
            decision = "18C_train_only_fit_blocked"
        elif gates["oos_no_tuning_gate"] != "pass":
            decision = "18C_oos_tuning_blocked"
        elif gates["search_accounting_gate"] != "pass":
            decision = "18C_search_accounting_blocked"
        elif (
            gates["rank_ic_support_gate"] != "pass"
            and gates["monotonicity_support_gate"] != "pass"
            and gates["bucket_lift_gate"] != "pass"
            and gates["bootstrap_ci_gate"] != "pass"
            and gates["baseline_improvement_gate"] != "pass"
            and not binary_positive
        ):
            decision = "18C_current_features_reconfirmed_insufficient"
        elif gates["bucket_lift_gate"] == "pass" and primary_rank_or_mono_weak:
            decision = "18C_over_narrow_winner_target_blocked"
        elif binary_positive and primary_rank_or_mono_weak:
            decision = "18C_binary_only_not_supported"
        elif any(gates[gate] != "pass" for gate in ["rank_ic_support_gate", "monotonicity_support_gate", "bootstrap_ci_gate", "baseline_improvement_gate"]):
            decision = "18C_payoff_state_signal_weak_or_nonmonotone"
        elif gates["risk_only_gate"] == "fail":
            decision = "18C_risk_only_no_payoff_state"
        else:
            decision = "18C_refresh_separability_contract_blocked"
        blocking = decision

    row = {
        "decision_state": decision,
        "next_allowed_requirement": next_req,
        "next_allowed_requirement_scope": next_scope,
        "all_hard_gates_pass": all_pass,
        **gates,
        "validation_stress_evaluable": bool(int(validation["row_n"]) == int(config["expected"]["validation_row_n"]) and int(validation["episode_cluster_n"]) >= 30),
        "validation_stress_caveat": "stress_readout_only",
        **{col: False for col in AUTH_FALSE_COLUMNS},
        "blocking_reason": blocking,
        "primary_model_id": PRIMARY_MODEL_ID,
        "robustness_payoff_rank_ic": primary_rank,
        "robustness_decile_payoff_monotonicity_spearman": primary_mono,
        "robustness_cluster_bootstrap_rank_ic_ci_low": ci_low,
        "rank_ic_vs_volatility20d_delta": vol_delta,
        "rank_ic_materiality_floor": config["expected"]["rank_ic_materiality_floor"],
    }
    return pd.DataFrame([row])


def build_full_outputs(
    config: dict[str, Any],
    resolved: dict[str, Path],
    input_gate: str,
    upstream_gate: str,
    matrix_gate: str,
) -> dict[str, Any]:
    model_config = prepared_model_config(config, resolved)
    matrix = BASE_18C.add_ordinal_int(model_config, read_table(resolved["eighteen_e_refreshed_matrix"]))
    registry, registry_gate = BASE_18C.build_model_registry(model_config)
    score, coefficients, _ = BASE_18C.build_scores_and_coefficients(model_config, matrix)
    cv = BASE_18C.build_cv_readout(model_config, matrix)
    oos = BASE_18C.build_oos_rank_readout(model_config, score)
    deciles = BASE_18C.build_decile_monotonicity(model_config, score)
    bucket = BASE_18C.build_bucket_lift(score)
    bootstrap = BASE_18C.build_bootstrap_ci(model_config, score)
    topk = BASE_18C.build_topk_removal_sensitivity(model_config, score, coefficients)
    family = build_family_removal_sensitivity(topk, read_table(resolved["eighteen_e_family_coverage"]))
    baseline = BASE_18C.build_baseline_comparison(model_config, oos, deciles, bootstrap)
    binary = build_binary_sanity(model_config, score)
    search, search_gate = build_search_accounting_audit(model_config)

    primary_row = oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness")].iloc[0]
    rank_gate = gate_from_bool(
        float(primary_row["rank_ic_spearman"]) >= float(model_config["expected"]["rank_ic_materiality_floor"])
        and float(primary_row["continue_advantage_replay_abs_diff"]) <= 1e-12
    )
    primary_mono = deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID) & deciles["split_bucket"].eq("robustness")]
    mono_gate = gate_from_bool(
        float(primary_mono["decile_payoff_monotonicity_spearman"].iloc[0]) >= float(model_config["expected"]["monotonicity_floor"])
        and float(primary_mono["top3_minus_bottom3_payoff_gap"].iloc[0]) > 0
        and not bool(primary_mono["split_local_score_cutoff_recompute_used"].any())
    )
    robust_bucket = bucket.loc[bucket["split_bucket"].eq("robustness")]
    bucket_gate = gate_from_bool(float(robust_bucket["bucket_lift"].min()) > 1.0 and not bool(robust_bucket["split_local_score_cutoff_recompute_used"].any()))
    boot_gate = gate_from_bool(
        float(bootstrap["cluster_bootstrap_rank_ic_ci_low"].iloc[0]) > 0
        and int(bootstrap["valid_bootstrap_resample_n"].iloc[0]) == int(model_config["expected"]["bootstrap_resample_n"])
    )
    baseline_hard = baseline.loc[baseline["comparison_id"].eq("payoff_rank_ic_vs_volatility20d")]
    baseline_gate = gate_from_bool(not baseline_hard.empty and baseline_hard["comparison_status"].eq("pass").all())
    risk_precondition = all(gate == "pass" for gate in [rank_gate, mono_gate, boot_gate, baseline_gate])
    f4 = family.loc[family["split_bucket"].eq("robustness") & family["sensitivity_id"].eq("family_F4_removed")]
    if not risk_precondition:
        risk_gate = "not_evaluable_primary_signal_weak"
    else:
        f4_retention = float(f4["rank_ic_retention_rate"].iloc[0]) if not f4.empty else np.nan
        f4_rank = float(f4["sensitivity_rank_ic_spearman"].iloc[0]) if not f4.empty else np.nan
        risk_gate = gate_from_bool(
            np.isfinite(f4_retention)
            and f4_retention >= float(model_config["expected"]["f4_removal_retention_floor"])
            and np.isfinite(f4_rank)
            and f4_rank > 0
        )
    binary_gate = gate_from_bool((~binary["binary_metric_used_as_primary_gate"].astype(bool)).all())
    gates = {
        "upstream_18e_contract_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "matrix_contract_replay_gate": matrix_gate,
        "model_registry_gate": registry_gate,
        "train_only_fit_gate": "pass",
        "oos_no_tuning_gate": "pass",
        "rank_ic_support_gate": rank_gate,
        "monotonicity_support_gate": mono_gate,
        "bucket_lift_gate": bucket_gate,
        "bootstrap_ci_gate": boot_gate,
        "baseline_improvement_gate": baseline_gate,
        "risk_only_gate": risk_gate,
        "binary_sanity_boundary_gate": binary_gate,
        "search_accounting_gate": search_gate,
    }
    decision = build_refreshed_decision(model_config, gates, oos, deciles, bucket, bootstrap, baseline, family, binary, "scored")
    score_panel = build_score_panel(model_config, score, file_sha(resolved["eighteen_e_refreshed_matrix"]))
    return {
        "model_config": model_config,
        "matrix": matrix,
        "score": score,
        "score_panel": score_panel,
        "model_registry": registry,
        "model_cv_readout": cv,
        "model_coefficients": coefficients,
        "oos_rank_readout": oos,
        "decile_monotonicity": deciles,
        "bucket_lift": bucket,
        "bootstrap_ci": bootstrap,
        "topk_removal_sensitivity": topk,
        "family_removal_sensitivity": family,
        "baseline_comparison": baseline,
        "binary_sanity": binary,
        "search_accounting": search,
        "decision": decision,
        "gates": gates,
    }


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
    empty_score_panel(str(decision.iloc[0]["decision_state"])).to_parquet(outputs["score_panel"], index=False)
    write_placeholder_figure(outputs["decile_curve"], "Refreshed 18C Decile Curve")
    write_placeholder_figure(outputs["score_surface"], "Refreshed 18C Score Surface")
    write_manifests(config, resolved, outputs, input_audit, decision)
    return tables


def write_full_outputs(
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
    upstream: pd.DataFrame,
    matrix_contract: pd.DataFrame,
    artifacts: dict[str, Any],
) -> None:
    outputs["score_panel"].parent.mkdir(parents=True, exist_ok=True)
    artifacts["score_panel"].to_parquet(outputs["score_panel"], index=False)
    write_df(outputs["input_artifact_audit"], input_audit)
    write_df(outputs["upstream_18e_handoff_audit"], upstream)
    write_df(outputs["matrix_contract_replay_audit"], matrix_contract)
    for key in [
        "model_registry",
        "model_cv_readout",
        "model_coefficients",
        "oos_rank_readout",
        "decile_monotonicity",
        "bucket_lift",
        "bootstrap_ci",
        "topk_removal_sensitivity",
        "family_removal_sensitivity",
        "baseline_comparison",
        "binary_sanity",
        "search_accounting",
        "decision",
    ]:
        write_df(outputs[key], artifacts[key])
    BASE_18C.build_figures(artifacts["score"], artifacts["decile_monotonicity"], outputs)
    write_text(
        outputs["report"],
        build_full_report(
            input_audit,
            upstream,
            matrix_contract,
            artifacts["model_registry"],
            artifacts["model_cv_readout"],
            artifacts["oos_rank_readout"],
            artifacts["decile_monotonicity"],
            artifacts["bucket_lift"],
            artifacts["bootstrap_ci"],
            artifacts["family_removal_sensitivity"],
            artifacts["baseline_comparison"],
            artifacts["binary_sanity"],
            artifacts["search_accounting"],
            artifacts["decision"],
        ),
    )
    write_manifests(config, resolved, outputs, input_audit, artifacts["decision"], artifacts)


def write_manifests(
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
    decision: pd.DataFrame,
    artifacts: dict[str, Any] | None = None,
) -> None:
    score_panel_status = "scored" if artifacts is not None else "not_scored_fail_closed"
    if artifacts is not None:
        score_panel = artifacts["score_panel"]
        split_counts = score_panel["cluster_split_bucket"].value_counts().sort_index().to_dict()
        feature_names = artifacts["model_config"]["model_ready_features"]
        score_columns = [col for col in SCORE_PANEL_COLUMNS if col.endswith("_score")]
        model_ids = artifacts["model_registry"]["model_id"].tolist()
        target_columns = [col for col in TARGET_COLUMNS if col in score_panel.columns]
    else:
        split_counts = {}
        feature_names = []
        score_columns = [col for col in SCORE_PANEL_COLUMNS if col.endswith("_score")]
        model_ids = list(SCORE_MODEL_IDS)
        target_columns = [col for col in TARGET_COLUMNS if col in SCORE_PANEL_COLUMNS]
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
            "split_counts": split_counts,
            "identity_key_columns": config.get("primary_identity_key_columns", ["step_id", "label_id"]),
            "full_lineage_key_columns": config.get("full_lineage_key_columns", config.get("identity_key_columns", [])),
            "target_columns": target_columns,
            "score_columns": score_columns,
            "model_ids": model_ids,
            "feature_names": feature_names,
            "score_panel_status": score_panel_status,
        },
    )
    d = decision.iloc[0]
    output_keys = [
        "score_panel",
        "input_artifact_audit",
        "upstream_18e_handoff_audit",
        "matrix_contract_replay_audit",
        "model_registry",
        "model_cv_readout",
        "model_coefficients",
        "oos_rank_readout",
        "decile_monotonicity",
        "bucket_lift",
        "bootstrap_ci",
        "topk_removal_sensitivity",
        "family_removal_sensitivity",
        "baseline_comparison",
        "binary_sanity",
        "search_accounting",
        "decision",
        "decile_curve",
        "score_surface",
        "report",
    ]
    publishable_tables = {
        key: file_sha(path)
        for key, path in outputs.items()
        if path.suffix == ".csv" and path.exists()
    }
    publishable_figures = {key: file_sha(outputs[key]) for key in ["decile_curve", "score_surface"] if outputs[key].exists()}
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
            "publishable_figure_sha256_by_name": publishable_figures,
            "report_sha256": file_sha(outputs["report"]),
            "output_hashes": {key: file_sha(outputs[key]) for key in [*output_keys, "input_manifest", "score_panel_manifest"] if outputs[key].exists()},
            "row_counts": {key: count_rows(outputs[key]) for key in [*output_keys, "input_manifest", "score_panel_manifest"] if outputs[key].exists()},
            "decision_state": d["decision_state"],
            "next_allowed_requirement": d["next_allowed_requirement"],
            "next_allowed_requirement_scope": d["next_allowed_requirement_scope"],
            "all_hard_gates_pass": bool(d["all_hard_gates_pass"]),
            "primary_model_id": "ridge_payoff_rank_h20_v1",
            "primary_feature_n": int(config["expected"]["primary_model_ready_feature_n"]),
            "primary_split": "robustness",
            "primary_target_id": "y_payoff_h20",
            "robustness_payoff_rank_ic": d.get("robustness_payoff_rank_ic"),
            "robustness_decile_payoff_monotonicity_spearman": d.get("robustness_decile_payoff_monotonicity_spearman"),
            "robustness_cluster_bootstrap_rank_ic_ci_low": d.get("robustness_cluster_bootstrap_rank_ic_ci_low"),
            "rank_ic_vs_volatility20d_delta": d.get("rank_ic_vs_volatility20d_delta"),
            "validation_role": "stress_readout_only",
            "authorization_flags": {col: bool(d[col]) for col in AUTH_FALSE_COLUMNS},
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
        decision = build_decision(config, upstream_gate, input_gate, matrix_gate)
        return {"input_artifact_gate": input_gate, "input_artifact_audit": input_audit, "upstream": upstream, "decision": decision}

    if input_gate == "pass" and upstream_gate == "pass" and matrix_gate == "pass":
        artifacts = build_full_outputs(config, resolved, input_gate, upstream_gate, matrix_gate)
        write_full_outputs(config, resolved, outputs, input_audit, upstream, matrix_contract, artifacts)
        return {
            "input_artifact_gate": input_gate,
            "input_artifact_audit": input_audit,
            "upstream": upstream,
            "matrix_contract": matrix_contract,
            **artifacts,
        }

    decision = build_decision(config, upstream_gate, input_gate, matrix_gate)
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

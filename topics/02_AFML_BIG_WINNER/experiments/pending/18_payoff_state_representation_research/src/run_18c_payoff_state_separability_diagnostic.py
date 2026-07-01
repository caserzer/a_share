#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.tree import DecisionTreeRegressor


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "18C_payoff_state_separability_diagnostic"
EXPERIMENT_ID = "18_payoff_state_representation_research"
PHASE_ID = "18C"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_18c_payoff_state_separability_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
FIGURE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "figures" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID

SPLITS = ("train", "robustness", "validation")
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
    "upstream_18b_contract_gate",
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
PRIMARY_MODEL_ID = "ridge_payoff_rank_h20_v1"
VOL_BASELINE_ID = "volatility20d_defense_baseline"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP18C payoff-state separability diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    parser.add_argument("--check-inputs-only", action="store_true")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
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
        "score_panel": LOCAL_CACHE_DIR / "payoff_state_score_panel.parquet",
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_18b_handoff_audit": TABLE_DIR / "upstream_18b_handoff_audit.csv",
        "matrix_contract_replay_audit": TABLE_DIR / "matrix_contract_replay_audit.csv",
        "model_registry": TABLE_DIR / "payoff_state_model_registry.csv",
        "model_cv_readout": TABLE_DIR / "payoff_state_model_cv_readout.csv",
        "model_coefficients": TABLE_DIR / "payoff_state_model_coefficients.csv",
        "oos_rank_readout": TABLE_DIR / "payoff_state_oos_rank_readout.csv",
        "decile_monotonicity": TABLE_DIR / "payoff_state_decile_monotonicity.csv",
        "bucket_lift": TABLE_DIR / "payoff_state_bucket_lift.csv",
        "bootstrap_ci": TABLE_DIR / "payoff_state_bootstrap_ci.csv",
        "topk_removal_sensitivity": TABLE_DIR / "topk_removal_sensitivity.csv",
        "baseline_comparison": TABLE_DIR / "baseline_comparison_readout.csv",
        "binary_sanity": TABLE_DIR / "binary_sanity_readout.csv",
        "search_accounting": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "payoff_state_separability_decision.csv",
        "decile_curve": FIGURE_DIR / "payoff_state_decile_curve.png",
        "score_surface": FIGURE_DIR / "score_vs_payoff_rank_surface.png",
        "report": REPORT_DIR / "payoff_state_separability_diagnostic_report.md",
        "manifest": MANIFEST_DIR / "18C_payoff_state_separability_diagnostic_manifest.json",
        "input_manifest": MANIFEST_DIR / "input_artifact_manifest_18c.json",
        "score_panel_manifest": MANIFEST_DIR / "payoff_state_score_panel_manifest.json",
    }


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if not isinstance(value, (str, bytes, dict, list, tuple)):
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
    return value


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return len(pd.read_parquet(path))
    if suffixes.endswith((".csv", ".csv.gz")):
        with path.open("r", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    if suffixes.endswith(".md"):
        return len(path.read_text(encoding="utf-8").splitlines())
    if suffixes.endswith(".json"):
        return 1
    return None


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path, **kwargs)
    raise ValueError(f"Unsupported table path: {path}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def header_columns(path: Path) -> list[str]:
    if not path.exists() or path.is_dir():
        return []
    suffixes = "".join(path.suffixes)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path, engine="pyarrow").columns)
    return []


def str_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value)


def bool_like(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass"}
    if pd.isna(value):
        return False
    return bool(value)


def false_like(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return not bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no", ""}
    if pd.isna(value):
        return False
    return not bool(value)


def metric_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return float(out) if np.isfinite(out) else default


def required_columns_for_key(config: dict[str, Any], key: str) -> set[str]:
    model_features = set(config["model_ready_features"])
    primary_key = set(config["primary_identity_key_columns"])
    lineage_key = set(config["full_lineage_key_columns"])
    split = {config["split_column"]}
    mapping: dict[str, set[str]] = {
        "eighteen_b_matrix": primary_key | lineage_key | split | model_features | set(TARGET_COLUMNS),
        "eighteen_b_decision": {"decision_state", "next_allowed_requirement", "all_hard_gates_pass", *AUTH_FALSE_COLUMNS},
        "eighteen_b_schema": {"column_name", "column_role", "model_ready_feature", "target_column"},
        "eighteen_b_feature_target_binding_audit": {"bound_matrix_row_n", "split_mismatch_n", "feature_target_binding_gate"},
        "eighteen_b_feature_missingness_audit": {"feature_name", "split_bucket", "finite_rate", "feature_complete_rate_gate"},
        "eighteen_b_matrix_row_completeness_audit": {"split_bucket", "row_n", "matrix_row_complete_rate"},
        "eighteen_b_feature_lineage_audit": {"feature_name", "feature_lineage_gate"},
        "eighteen_b_feature_family_coverage": {"feature_family_id", "observed_model_ready_feature_n", "feature_family_coverage_gate"},
        "eighteen_b_train_only_preprocessing_audit": {"feature_name", "model_ready_feature_name", "fit_split", "fit_row_n"},
        "eighteen_b_forbidden_feature_audit": {"column_name", "marked_model_ready_feature", "forbidden_feature_gate"},
        "eighteen_b_search_accounting_audit": {"phase_id", "search_accounting_gate"},
        "eighteen_a_decision": {"decision_state", "next_allowed_requirement", "all_hard_gates_pass"},
        "eighteen_a_target_definition_registry": {"target_id", "target_family", "lineage_hash"},
        "eighteen_a_target_denominator_reconciliation": {"split_bucket", "labelable_step_n", "neutral_step_n"},
        "eighteen_a_payoff_cutoff_freeze": {"threshold_id", "train_absolute_payoff_cutoff", "split_local_recompute_used"},
        "eighteen_a_neutral_preservation_audit": {"split_bucket", "neutral_preservation_gate"},
        "sixteen_x_survival_vs_payoff_rank_ic": {"split_bucket", "probe_id", "rank_ic_spearman"},
        "sixteen_x_payoff_decile_monotonicity": {"split_bucket", "decile_index", "payoff_decile_monotonicity_spearman"},
        "sixteen_x_cluster_bootstrap_rank_ic": {"split_bucket", "probe_id", "cluster_bootstrap_rank_ic_ci_low"},
        "sixteen_x_decision": {"decision_state", "robustness_payoff_probe_rank_ic_spearman"},
        "sixteen_c_oos_separability": {"split_bucket", "model_id", "roc_auc", "average_precision"},
    }
    if key.endswith("_manifest") or key.endswith("_report") or key.startswith("requirement") or key in {"research_plan", "umbrella_requirement", "eighteen_a_target_contract_doc"}:
        return set()
    return mapping.get(key, set())


def expected_manifest_hashes(resolved: dict[str, Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    key_map = {
        "eighteen_b_matrix": "matrix",
        "eighteen_b_decision": "decision",
        "eighteen_b_schema": "schema",
        "eighteen_b_feature_target_binding_audit": "feature_target_binding_audit",
        "eighteen_b_feature_missingness_audit": "feature_missingness_audit",
        "eighteen_b_matrix_row_completeness_audit": "matrix_row_completeness_audit",
        "eighteen_b_feature_lineage_audit": "feature_lineage_audit",
        "eighteen_b_feature_family_coverage": "feature_family_coverage",
        "eighteen_b_train_only_preprocessing_audit": "train_only_preprocessing_audit",
        "eighteen_b_forbidden_feature_audit": "forbidden_feature_audit",
        "eighteen_b_search_accounting_audit": "search_accounting_audit",
        "eighteen_b_report": "report",
        "eighteen_b_matrix_manifest": "matrix_manifest",
        "eighteen_b_input_artifact_manifest": "input_artifact_manifest",
    }
    manifest_path = resolved.get("eighteen_b_manifest")
    if manifest_path is not None and manifest_path.exists():
        output_hashes = read_json(manifest_path).get("output_hashes", {})
        for artifact_key, manifest_key in key_map.items():
            value = output_hashes.get(manifest_key)
            if value:
                hashes[artifact_key] = str(value)

    matrix_manifest_path = resolved.get("eighteen_b_matrix_manifest")
    if matrix_manifest_path is not None and matrix_manifest_path.exists():
        matrix_manifest = read_json(matrix_manifest_path)
        if matrix_manifest.get("matrix_sha256"):
            hashes["eighteen_b_matrix"] = str(matrix_manifest["matrix_sha256"])
        if matrix_manifest.get("schema_sha256"):
            hashes["eighteen_b_schema"] = str(matrix_manifest["schema_sha256"])
    return hashes


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    rows = []
    manifest_hashes = expected_manifest_hashes(resolved)
    for key, meta in config["required_artifacts"].items():
        path = resolved[key]
        exists = path.exists()
        cols = set(header_columns(path)) if exists else set()
        required = required_columns_for_key(config, key)
        missing = sorted(required - cols)
        observed_sha = file_sha(path) if exists and path.is_file() else ""
        expected_sha = manifest_hashes.get(key)
        hash_status = (
            "missing"
            if not exists
            else "not_manifested"
            if not expected_sha
            else "exact_match"
            if observed_sha == expected_sha
            else "mismatch"
        )
        blockers = []
        if not exists:
            blockers.append("missing")
        if missing:
            blockers.append("schema_missing:" + ",".join(missing))
        if hash_status == "mismatch":
            blockers.append("manifest_hash_mismatch")
        schema_status = "pass" if exists and not missing else "fail"
        read_status = "pass" if exists else "missing"
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
                "row_count": count_rows(path) if exists else np.nan,
                "sha256": file_sha(path) if exists and path.is_file() else "",
                "source_kind": "publishable_or_local_cache",
                "schema_status": schema_status,
                "read_status": read_status,
                "expected_row_n": np.nan,
                "observed_row_n": count_rows(path) if exists else np.nan,
                "expected_identity_key_n": np.nan,
                "observed_identity_key_n": np.nan,
                "cache_hash_validated": hash_status,
                "cache_schema_validated": schema_status == "pass",
                "cache_key_reconciliation_gate": "pass" if hash_status in {"exact_match", "not_manifested"} and schema_status == "pass" else "fail",
                "absolute_path_mismatch_ignored": False,
                "blocking_reason": ";".join(blockers),
            }
        )
    audit = pd.DataFrame(rows)
    gate = (
        "pass"
        if audit["read_status"].eq("pass").all()
        and audit["schema_status"].eq("pass").all()
        and not audit["cache_hash_validated"].eq("mismatch").any()
        else "fail"
    )
    return audit, gate


def append_sixteen_x_reference_audit(
    input_audit: pd.DataFrame,
    observed: dict[str, float],
    expected: dict[str, float],
    reference_gate: str,
) -> pd.DataFrame:
    payload = {"observed": observed, "expected": expected}
    payload_sha = hashlib.sha256(json.dumps(clean_json(payload), sort_keys=True).encode("utf-8")).hexdigest()
    row = {
        "artifact_key": "sixteen_x_reference_values",
        "artifact_role": "sixteen_x_external_context_integrity",
        "required_flag": "required",
        "resolver_alias": "sixteen_x_reference_values",
        "resolved_path": "sixteen_x_external_context_reference_values",
        "relative_path": "sixteen_x_external_context_reference_values",
        "source_experiment_id": "16_winner_episode_sequential_sampling_geometry_preflight_v0",
        "source_phase_id": "16X",
        "row_count": len(observed),
        "sha256": payload_sha,
        "source_kind": "source_value_reference_check",
        "schema_status": reference_gate,
        "read_status": "pass",
        "expected_row_n": len(expected),
        "observed_row_n": len(observed),
        "expected_identity_key_n": np.nan,
        "observed_identity_key_n": np.nan,
        "cache_hash_validated": "exact_match" if reference_gate == "pass" else "source_value_mismatch",
        "cache_schema_validated": reference_gate == "pass",
        "cache_key_reconciliation_gate": reference_gate,
        "absolute_path_mismatch_ignored": False,
        "blocking_reason": "" if reference_gate == "pass" else "sixteen_x_reference_value_mismatch",
    }
    return pd.concat([input_audit, pd.DataFrame([row])], ignore_index=True)


def load_inputs(resolved: dict[str, Path]) -> dict[str, pd.DataFrame]:
    keys = [
        "eighteen_b_decision",
        "eighteen_b_schema",
        "eighteen_b_feature_target_binding_audit",
        "eighteen_b_feature_missingness_audit",
        "eighteen_b_matrix_row_completeness_audit",
        "eighteen_b_feature_lineage_audit",
        "eighteen_b_feature_family_coverage",
        "eighteen_b_train_only_preprocessing_audit",
        "eighteen_b_forbidden_feature_audit",
        "eighteen_b_search_accounting_audit",
        "eighteen_a_decision",
        "eighteen_a_target_definition_registry",
        "eighteen_a_target_denominator_reconciliation",
        "eighteen_a_payoff_cutoff_freeze",
        "eighteen_a_neutral_preservation_audit",
        "sixteen_x_survival_vs_payoff_rank_ic",
        "sixteen_x_payoff_decile_monotonicity",
        "sixteen_x_cluster_bootstrap_rank_ic",
        "sixteen_x_decision",
        "sixteen_c_oos_separability",
    ]
    return {key: read_table(resolved[key]) for key in keys}


def build_upstream_18b_handoff_audit(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    decision = tables["eighteen_b_decision"].iloc[0]
    checks: list[tuple[str, Any]] = [
        ("decision_state", config["expected"]["upstream_18b_decision_state"]),
        ("next_allowed_requirement", config["expected"]["upstream_18b_next_allowed_requirement"]),
        ("all_hard_gates_pass", True),
        ("input_artifact_gate", "pass"),
        ("feature_target_binding_gate", "pass"),
        ("feature_matrix_schema_gate", "pass"),
        ("feature_complete_rate_gate", "pass"),
        ("feature_lineage_gate", "pass"),
        ("feature_family_coverage_gate", "pass"),
        ("train_only_preprocessing_gate", "pass"),
        ("forbidden_feature_gate", "pass"),
        ("split_binding_gate", "pass"),
        ("split_drift_readout_gate", "pass"),
        ("search_accounting_gate", "pass"),
    ]
    checks.extend((col, False) for col in AUTH_FALSE_COLUMNS)
    rows = []
    for field, expected in checks:
        observed = decision[field]
        ok = bool_like(observed) if expected is True else false_like(observed) if expected is False else str_value(observed) == str(expected)
        rows.append(
            {
                "contract_check_id": field,
                "observed_value": observed,
                "expected_value": expected,
                "upstream_18b_contract_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else f"{field}_mismatch",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["upstream_18b_contract_gate"].eq("pass").all() else "fail"


def add_ordinal_int(config: dict[str, Any], matrix: pd.DataFrame) -> pd.DataFrame:
    out = matrix.copy()
    mapping = config["ordinal_mapping"]
    out["payoff_ordinal_state_int"] = out["payoff_ordinal_state"].map(mapping)
    return out


def target_lineage_hash(tables: dict[str, pd.DataFrame], target_id: str) -> str:
    registry = tables["eighteen_a_target_definition_registry"]
    rows = registry.loc[registry["target_id"].astype(str).eq(target_id)]
    return "" if rows.empty else str(rows["lineage_hash"].iloc[0])


def target_registry_gate(tables: dict[str, pd.DataFrame], target_id: str) -> str:
    registry = tables["eighteen_a_target_definition_registry"]
    rows = registry.loc[registry["target_id"].astype(str).eq(target_id)]
    return "missing" if rows.empty else str(rows["target_lineage_gate"].iloc[0])


def build_matrix_contract_replay_audit(config: dict[str, Any], matrix: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, str]:
    split_col = config["split_column"]
    primary_key = config["primary_identity_key_columns"]
    full_key = config["full_lineage_key_columns"]
    expected = config["expected"]
    cont_diff = (pd.to_numeric(matrix["continue_advantage"]) - (pd.to_numeric(matrix["y_payoff_h20"]) + 0.005)).abs().max()
    denominator = tables["eighteen_a_target_denominator_reconciliation"]
    neutral = tables["eighteen_a_neutral_preservation_audit"]
    cutoffs = tables["eighteen_a_payoff_cutoff_freeze"]

    matrix_split_counts = matrix.groupby(split_col).size().to_dict()
    matrix_neutral_counts = matrix.loc[matrix["label_class"].eq("neutral")].groupby(split_col).size().to_dict()
    expected_cutoffs = {
        "high_upside_top30_stress": expected["top30_cutoff"],
        "high_upside_top20_stress": expected["top20_cutoff"],
        "high_upside_top10_stress": expected["top10_cutoff"],
    }
    split_count_replay_ok = True
    neutral_count_replay_ok = True
    for split in SPLITS:
        denom_row = denominator.loc[denominator["split_bucket"].eq(split)].iloc[0]
        exp_labelable = expected["denominators"][split]["labelable_step_n"]
        exp_neutral = expected["denominators"][split]["neutral_step_n"]
        split_count_replay_ok &= int(denom_row["labelable_step_n"]) == exp_labelable == int(matrix_split_counts.get(split, 0))
        neutral_count_replay_ok &= int(denom_row["neutral_step_n"]) == exp_neutral == int(matrix_neutral_counts.get(split, 0))

    observed_cutoff_values = {
        row["threshold_id"]: float(row["train_absolute_payoff_cutoff"])
        for _, row in cutoffs.iterrows()
        if row["threshold_id"] in expected_cutoffs
    }
    cutoff_value_replay_ok = (
        set(observed_cutoff_values) == set(expected_cutoffs)
        and all(abs(observed_cutoff_values[key] - float(expected_cutoffs[key])) <= 1e-12 for key in expected_cutoffs)
    )
    cutoff_recompute_used = bool_like(cutoffs["split_local_recompute_used"].any())
    cutoff_hashes = set(cutoffs["y_payoff_lineage_hash"].astype(str))
    registry_hashes = {
        target_id: target_lineage_hash(tables, target_id)
        for target_id in ["y_payoff_h20", "continue_advantage", "payoff_ordinal_h20_train_frozen"]
    }
    checks = [
        ("matrix_row_n", expected["total_labelable_step_n"], len(matrix), len(matrix) == expected["total_labelable_step_n"]),
        (
            "train_row_n",
            expected["denominators"]["train"]["labelable_step_n"],
            int(matrix[split_col].eq("train").sum()),
            int(matrix[split_col].eq("train").sum()) == expected["denominators"]["train"]["labelable_step_n"],
        ),
        (
            "robustness_row_n",
            expected["denominators"]["robustness"]["labelable_step_n"],
            int(matrix[split_col].eq("robustness").sum()),
            int(matrix[split_col].eq("robustness").sum()) == expected["denominators"]["robustness"]["labelable_step_n"],
        ),
        (
            "validation_row_n",
            expected["denominators"]["validation"]["labelable_step_n"],
            int(matrix[split_col].eq("validation").sum()),
            int(matrix[split_col].eq("validation").sum()) == expected["denominators"]["validation"]["labelable_step_n"],
        ),
        ("model_ready_feature_n", 23, len(config["model_ready_features"]), len(config["model_ready_features"]) == 23),
        ("target_column_n", 19, sum(col in matrix.columns for col in TARGET_COLUMNS), sum(col in matrix.columns for col in TARGET_COLUMNS) == 19),
        ("identity_key_columns", "step_id|label_id", "|".join(primary_key), primary_key == ["step_id", "label_id"]),
        ("identity_key_duplicate_n", 0, int(matrix.duplicated(primary_key).sum()), int(matrix.duplicated(primary_key).sum()) == 0),
        ("full_lineage_key_columns", "|".join(full_key), "|".join(full_key), full_key == config["full_lineage_key_columns"]),
        ("full_lineage_key_duplicate_n", 0, int(matrix.duplicated(full_key).sum()), int(matrix.duplicated(full_key).sum()) == 0),
        ("target_lineage_hash_y_payoff_h20", expected["target_lineage_hash"], registry_hashes["y_payoff_h20"], registry_hashes["y_payoff_h20"] == expected["target_lineage_hash"]),
        ("target_lineage_hash_continue_advantage", expected["target_lineage_hash"], registry_hashes["continue_advantage"], registry_hashes["continue_advantage"] == expected["target_lineage_hash"]),
        (
            "target_lineage_hash_payoff_ordinal_state",
            expected["target_lineage_hash"],
            registry_hashes["payoff_ordinal_h20_train_frozen"],
            registry_hashes["payoff_ordinal_h20_train_frozen"] == expected["target_lineage_hash"],
        ),
        ("target_lineage_gate_y_payoff_h20", "pass", target_registry_gate(tables, "y_payoff_h20"), target_registry_gate(tables, "y_payoff_h20") == "pass"),
        ("target_denominator_reconciliation_gate", "pass", "|".join(denominator["denominator_reconciliation_gate"].astype(str).tolist()), denominator["denominator_reconciliation_gate"].eq("pass").all()),
        ("target_denominator_labelable_replay", "18A_equals_18B_matrix", "|".join(f"{split}:{int(matrix_split_counts.get(split, 0))}" for split in SPLITS), split_count_replay_ok),
        ("target_denominator_neutral_replay", "18A_equals_18B_matrix", "|".join(f"{split}:{int(matrix_neutral_counts.get(split, 0))}" for split in SPLITS), neutral_count_replay_ok),
        ("neutral_preservation_gate", "pass", "|".join(neutral["neutral_preservation_gate"].astype(str).tolist()), neutral["neutral_preservation_gate"].eq("pass").all()),
        (
            "neutral_reclassified_as_positive_or_negative",
            False,
            bool_like(neutral["neutral_reclassified_as_positive_or_negative"].any()),
            not bool_like(neutral["neutral_reclassified_as_positive_or_negative"].any()),
        ),
        ("neutral_rows_preserved", True, bool(matrix["label_class"].eq("neutral").any()) and neutral_count_replay_ok, bool(matrix["label_class"].eq("neutral").any()) and neutral_count_replay_ok),
        ("payoff_ordinal_state_string_mapping_complete", True, bool(matrix["payoff_ordinal_state_int"].notna().all()), bool(matrix["payoff_ordinal_state_int"].notna().all())),
        ("continue_advantage_affine_replay_max_abs_diff", "<=1e-12", cont_diff, float(cont_diff) <= 1e-12),
        ("train_frozen_payoff_cutoff_value_replay", expected_cutoffs, observed_cutoff_values, cutoff_value_replay_ok),
        ("train_frozen_payoff_cutoff_lineage_hash", expected["target_lineage_hash"], "|".join(sorted(cutoff_hashes)), cutoff_hashes == {expected["target_lineage_hash"]}),
        ("split_local_payoff_cutoff_recompute_used", False, cutoff_recompute_used, not cutoff_recompute_used),
        ("train_frozen_payoff_cutoff_gate", "pass", "|".join(cutoffs["train_frozen_cutoff_gate"].astype(str).tolist()), cutoffs["train_frozen_cutoff_gate"].eq("pass").all()),
    ]
    rows = []
    for check_id, expected_value, observed_value, ok in checks:
        rows.append(
            {
                "check_id": check_id,
                "expected_value": expected_value,
                "observed_value": observed_value,
                "matrix_contract_replay_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else f"{check_id}_mismatch",
            }
        )
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["matrix_contract_replay_gate"].eq("pass").all() else "fail"


def rank_ic(score: pd.Series | np.ndarray, target: pd.Series | np.ndarray) -> float:
    s = pd.Series(score, dtype="float64")
    t = pd.Series(target, dtype="float64")
    valid = np.isfinite(s) & np.isfinite(t)
    if int(valid.sum()) < 3:
        return np.nan
    sr = s.loc[valid].rank(method="average")
    tr = t.loc[valid].rank(method="average")
    if sr.nunique() <= 1 or tr.nunique() <= 1:
        return np.nan
    return float(sr.corr(tr))


def score_deciles(score: pd.Series, train_score: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    cutoffs = np.quantile(train_score.to_numpy(dtype=float), np.arange(0.1, 1.0, 0.1))
    deciles = np.searchsorted(cutoffs, score.to_numpy(dtype=float), side="right") + 1
    return np.clip(deciles, 1, 10), cutoffs


def decile_metrics(frame: pd.DataFrame, score_col: str, train_score: pd.Series, split: str) -> tuple[pd.DataFrame, float, float]:
    sub = frame.loc[frame["cluster_split_bucket"].eq(split)].copy()
    sub["decile_index"], _ = score_deciles(sub[score_col], train_score)
    rows = []
    for decile in range(1, 11):
        d = sub.loc[sub["decile_index"].eq(decile)]
        rows.append(
            {
                "split_bucket": split,
                "decile_index": decile,
                "row_n": len(d),
                "mean_payoff": float(d["y_payoff_h20"].mean()) if len(d) else np.nan,
                "mean_continue_advantage": float(d["continue_advantage"].mean()) if len(d) else np.nan,
                "mean_score": float(d[score_col].mean()) if len(d) else np.nan,
            }
        )
    out = pd.DataFrame(rows)
    mono = rank_ic(out["decile_index"], out["mean_payoff"])
    top = sub.loc[sub["decile_index"].isin([8, 9, 10]), "y_payoff_h20"].mean()
    bottom = sub.loc[sub["decile_index"].isin([1, 2, 3]), "y_payoff_h20"].mean()
    gap = float(top - bottom)
    return out, mono, gap


def model_score_column(model_id: str) -> str:
    return f"score_{model_id}"


def feature_family_lookup(config: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for family, features in config["feature_family_map"].items():
        for feature in features:
            out[feature] = family
    return out


def fit_model(config: dict[str, Any], model_id: str, train: pd.DataFrame):
    spec = config["models"][model_id]
    features = config["model_ready_features"]
    x = train[features].to_numpy(dtype=float)
    y = train[spec["target_column"]].to_numpy(dtype=float)
    family = spec["family"]
    if family in {"ridge_regression", "ridge_regression_on_ordinal_state"}:
        model = Ridge(alpha=float(spec["alpha"]), fit_intercept=bool(spec.get("fit_intercept", True)))
    elif family == "elastic_net_regression":
        model = ElasticNet(
            alpha=float(spec["alpha"]),
            l1_ratio=float(spec["l1_ratio"]),
            fit_intercept=bool(spec.get("fit_intercept", True)),
            max_iter=int(spec.get("max_iter", 10000)),
            random_state=int(spec["random_state"]),
        )
    elif family == "decision_tree_regressor":
        leaf = max(int(spec.get("min_samples_leaf_floor", 50)), int(math.ceil(float(spec.get("min_samples_leaf_train_fraction", 0.02)) * len(train))))
        model = DecisionTreeRegressor(max_depth=int(spec["max_depth"]), min_samples_leaf=leaf, random_state=int(spec["random_state"]))
    elif family == "logistic_regression_l2":
        y = train[spec["target_column"]].astype(int).to_numpy()
        model = LogisticRegression(
            penalty=str(spec.get("penalty", "l2")),
            C=float(spec["C"]),
            class_weight=spec.get("class_weight", "balanced"),
            solver=str(spec.get("solver", "liblinear")),
            max_iter=int(spec.get("max_iter", 1000)),
            random_state=int(spec["random_state"]),
        )
    else:
        raise ValueError(f"Unknown model family: {family}")
    return model.fit(x, y)


def score_model(model: Any, config: dict[str, Any], model_id: str, frame: pd.DataFrame) -> np.ndarray:
    x = frame[config["model_ready_features"]].to_numpy(dtype=float)
    if config["models"][model_id]["family"] == "logistic_regression_l2":
        return model.predict_proba(x)[:, 1]
    return model.predict(x)


def build_model_registry(config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    rows = []
    for model_id, spec in config["models"].items():
        rows.append(
            {
                "model_id": model_id,
                "model_family": spec["family"],
                "model_role": "primary_support" if model_id == PRIMARY_MODEL_ID else "diagnostic_or_sanity",
                "target_column": spec["target_column"],
                "feature_column_n": len(config["model_ready_features"]),
                "fit_split": "train",
                "hyperparameters": ";".join(f"{k}={v}" for k, v in spec.items() if k not in {"family", "target_column", "used_for_primary_decision"}),
                "used_for_primary_decision": bool(spec.get("used_for_primary_decision", False)),
                "binary_metric_used_as_primary_gate": False,
                "training_uses_robustness_rows": False,
                "training_uses_validation_rows": False,
                "model_registry_gate": "pass",
                "blocking_reason": "",
            }
        )
    for baseline_id, family, role in [
        ("intercept_unconditional_payoff_baseline", "constant_intercept", "baseline_only"),
        (VOL_BASELINE_ID, "volatility_score", "same_denominator_risk_baseline"),
        ("16x_payoff_rank_probe_v1", "external_16x_context", "external_coarse_context_only"),
        ("16c_ridge_logistic_bar_state_v1", "external_16c_binary", "appendix_only"),
    ]:
        rows.append(
            {
                "model_id": baseline_id,
                "model_family": family,
                "model_role": role,
                "target_column": "readout_only",
                "feature_column_n": 0 if baseline_id.startswith("16") else len(config["model_ready_features"]),
                "fit_split": "train" if not baseline_id.startswith("16") else "external",
                "hyperparameters": "predeclared",
                "used_for_primary_decision": False,
                "binary_metric_used_as_primary_gate": False,
                "training_uses_robustness_rows": False,
                "training_uses_validation_rows": False,
                "model_registry_gate": "pass",
                "blocking_reason": "",
            }
        )
    frame = pd.DataFrame(rows)
    primary_n = int(frame["used_for_primary_decision"].sum())
    gate = "pass" if primary_n == 1 and frame["model_registry_gate"].eq("pass").all() else "fail"
    return frame, gate


def build_scores_and_coefficients(config: dict[str, Any], matrix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    train = matrix.loc[matrix["cluster_split_bucket"].eq("train")].copy()
    score = matrix.copy()
    fitted: dict[str, Any] = {}
    coefficient_rows = []
    feature_to_family = feature_family_lookup(config)
    train_std = train[config["model_ready_features"]].std(ddof=0).replace(0, 1.0)
    for model_id in [
        "ridge_payoff_rank_h20_v1",
        "elastic_net_payoff_rank_h20_v1",
        "ridge_ordinal_payoff_state_v1",
        "shallow_tree_payoff_depth2_v1",
        "ridge_logistic_top30_sanity_v1",
        "ridge_logistic_top20_sanity_v1",
    ]:
        model = fit_model(config, model_id, train)
        fitted[model_id] = model
        score[model_score_column(model_id)] = score_model(model, config, model_id, score)
        if hasattr(model, "coef_"):
            coefs = np.asarray(model.coef_).reshape(-1)
            source = "linear_coefficient"
        else:
            coefs = np.asarray(model.feature_importances_).reshape(-1)
            source = "tree_importance"
        abs_order = pd.Series(np.abs(coefs), index=config["model_ready_features"]).rank(method="first", ascending=False).astype(int)
        std_coef = coefs * train_std.loc[config["model_ready_features"]].to_numpy(dtype=float)
        std_order = pd.Series(np.abs(std_coef), index=config["model_ready_features"]).rank(method="first", ascending=False).astype(int)
        for feature, coef, stdc in zip(config["model_ready_features"], coefs, std_coef, strict=False):
            coefficient_rows.append(
                {
                    "model_id": model_id,
                    "feature_name": feature,
                    "feature_family_id": feature_to_family[feature],
                    "coefficient": float(coef),
                    "feature_train_std": float(train_std[feature]),
                    "standardized_coefficient": float(stdc),
                    "abs_coefficient_rank": int(abs_order[feature]),
                    "standardized_abs_coefficient_rank": int(std_order[feature]),
                    "train_fit_row_n": len(train),
                    "coefficient_source": source,
                }
            )
    score["score_intercept_unconditional_payoff_baseline"] = float(train["y_payoff_h20"].mean())
    score[f"score_{VOL_BASELINE_ID}"] = -1.0 * score["mr_volatility_20d"].astype(float)
    return score, pd.DataFrame(coefficient_rows), fitted


def build_cv_readout(config: dict[str, Any], matrix: pd.DataFrame) -> pd.DataFrame:
    train = matrix.loc[matrix["cluster_split_bucket"].eq("train")].copy()
    rng = np.random.default_rng(int(config["cv"]["fold_seed"]))
    clusters = np.array(sorted(train["episode_cluster_id"].astype(str).unique()))
    rng.shuffle(clusters)
    fold_map = {cluster: i % int(config["cv"]["fold_n"]) for i, cluster in enumerate(clusters)}
    train["fold_id"] = train["episode_cluster_id"].astype(str).map(fold_map)
    rows = []
    for model_id in ["ridge_payoff_rank_h20_v1", "elastic_net_payoff_rank_h20_v1", "ridge_ordinal_payoff_state_v1", "shallow_tree_payoff_depth2_v1"]:
        for fold in range(int(config["cv"]["fold_n"])):
            fit = train.loc[~train["fold_id"].eq(fold)].copy()
            test = train.loc[train["fold_id"].eq(fold)].copy()
            model = fit_model(config, model_id, fit)
            test_score = score_model(model, config, model_id, test)
            test = test.assign(_score=test_score)
            deciles, mono, gap = decile_metrics(test, "_score", pd.Series(score_model(model, config, model_id, fit)), "train")
            rows.append(
                {
                    "cv_scheme": config["cv"]["scheme"],
                    "model_id": model_id,
                    "fold_id": fold,
                    "train_row_n": len(fit),
                    "test_row_n": len(test),
                    "train_episode_cluster_n": fit["episode_cluster_id"].nunique(),
                    "test_episode_cluster_n": test["episode_cluster_id"].nunique(),
                    "payoff_rank_ic": rank_ic(test_score, test["y_payoff_h20"]),
                    "decile_payoff_monotonicity_spearman": mono,
                    "top3_minus_bottom3_payoff_gap": gap,
                    "fold_status": "pass" if len(test) > 0 and len(deciles) == 10 else "fail",
                }
            )
    return pd.DataFrame(rows)


def build_oos_rank_readout(config: dict[str, Any], score: pd.DataFrame) -> pd.DataFrame:
    rows = []
    model_ids = [
        "ridge_payoff_rank_h20_v1",
        "elastic_net_payoff_rank_h20_v1",
        "ridge_ordinal_payoff_state_v1",
        "shallow_tree_payoff_depth2_v1",
        "intercept_unconditional_payoff_baseline",
        VOL_BASELINE_ID,
    ]
    x_ref = config["expected"]["sixteen_x"]["robustness_payoff_rank_ic"]
    for model_id in model_ids:
        col = model_score_column(model_id)
        for split in SPLITS:
            sub = score.loc[score["cluster_split_bucket"].eq(split)]
            pay_ic = rank_ic(sub[col], sub["y_payoff_h20"])
            adv_ic = rank_ic(sub[col], sub["continue_advantage"])
            diff = abs(pay_ic - adv_ic) if np.isfinite(pay_ic) and np.isfinite(adv_ic) else np.nan
            if split == "train":
                status = "train_in_sample"
            elif model_id == PRIMARY_MODEL_ID and split == "robustness":
                status = (
                    "pass"
                    if np.isfinite(pay_ic)
                    and pay_ic >= float(config["expected"]["rank_ic_materiality_floor"])
                    and np.isfinite(diff)
                    and diff <= 1e-12
                    else "fail"
                )
            elif model_id == PRIMARY_MODEL_ID and split == "validation":
                status = "stress_readout_only"
            else:
                status = "diagnostic_readout"
            rows.append(
                {
                    "split_bucket": split,
                    "model_id": model_id,
                    "target_id": "y_payoff_h20",
                    "row_n": len(sub),
                    "episode_cluster_n": sub["episode_cluster_id"].nunique(),
                    "rank_ic_spearman": pay_ic,
                    "continue_advantage_rank_ic_spearman": adv_ic,
                    "continue_advantage_replay_abs_diff": diff,
                    "coarse_rank_ic_vs_16x_external_delta": pay_ic - x_ref if model_id == PRIMARY_MODEL_ID and split == "robustness" else np.nan,
                    "rank_ic_status": status,
                }
            )
    return pd.DataFrame(rows)


def build_decile_monotonicity(config: dict[str, Any], score: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model_id in ["ridge_payoff_rank_h20_v1", VOL_BASELINE_ID]:
        col = model_score_column(model_id)
        train_score = score.loc[score["cluster_split_bucket"].eq("train"), col]
        for split in SPLITS:
            deciles, mono, gap = decile_metrics(score, col, train_score, split)
            deciles["model_id"] = model_id
            deciles["score_cutoff_source"] = "train_frozen_score_deciles"
            deciles["decile_payoff_monotonicity_spearman"] = mono
            deciles["top3_minus_bottom3_payoff_gap"] = gap
            deciles["split_local_score_cutoff_recompute_used"] = False
            deciles["monotonicity_status"] = "pass" if split != "robustness" or (mono >= config["expected"]["monotonicity_floor"] and gap > 0) else "fail"
            rows.extend(deciles.to_dict("records"))
    return pd.DataFrame(rows)


def build_bucket_lift(score: pd.DataFrame) -> pd.DataFrame:
    rows = []
    model_id = PRIMARY_MODEL_ID
    col = model_score_column(model_id)
    train_score = score.loc[score["cluster_split_bucket"].eq("train"), col]
    cutoffs = {"score_top30_bucket": float(train_score.quantile(0.70)), "score_top20_bucket": float(train_score.quantile(0.80))}
    targets = {"score_top30_bucket": "top30_yes_no", "score_top20_bucket": "top20_yes_no"}
    for split in SPLITS:
        sub = score.loc[score["cluster_split_bucket"].eq(split)].copy()
        for bucket_id, cutoff in cutoffs.items():
            target = targets[bucket_id]
            in_bucket = sub[col] >= cutoff
            base_rate = float(sub[target].astype(bool).mean())
            bucket_rate = float(sub.loc[in_bucket, target].astype(bool).mean()) if int(in_bucket.sum()) else np.nan
            lift = bucket_rate / base_rate if base_rate > 0 and np.isfinite(bucket_rate) else np.nan
            rows.append(
                {
                    "split_bucket": split,
                    "model_id": model_id,
                    "bucket_id": bucket_id,
                    "score_cutoff_source": "train_frozen_score_cutoff",
                    "score_cutoff_value": cutoff,
                    "row_n": int(in_bucket.sum()),
                    "split_unconditional_event_rate": base_rate,
                    "bucket_event_rate": bucket_rate,
                    "bucket_lift": lift,
                    "target_column": target,
                    "split_local_score_cutoff_recompute_used": False,
                    "bucket_lift_status": "pass" if split != "robustness" or (np.isfinite(lift) and lift > 1.0) else "fail",
                }
            )
    return pd.DataFrame(rows)


def build_bootstrap_ci(config: dict[str, Any], score: pd.DataFrame) -> pd.DataFrame:
    sub = score.loc[score["cluster_split_bucket"].eq("robustness")].copy()
    clusters = np.array(sorted(sub["episode_cluster_id"].astype(str).unique()))
    by_cluster = {cluster: rows for cluster, rows in sub.groupby(sub["episode_cluster_id"].astype(str))}
    rng = np.random.default_rng(int(config["expected"]["bootstrap_random_seed"]))
    values = []
    for _ in range(int(config["expected"]["bootstrap_resample_n"])):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        frame = pd.concat([by_cluster[c] for c in sampled], ignore_index=True)
        values.append(rank_ic(frame[model_score_column(PRIMARY_MODEL_ID)], frame["y_payoff_h20"]))
    valid = np.array([v for v in values if np.isfinite(v)], dtype=float)
    ci_low = float(np.quantile(valid, 0.025)) if len(valid) else np.nan
    ci_high = float(np.quantile(valid, 0.975)) if len(valid) else np.nan
    point = rank_ic(sub[model_score_column(PRIMARY_MODEL_ID)], sub["y_payoff_h20"])
    row = {
        "split_bucket": "robustness",
        "model_id": PRIMARY_MODEL_ID,
        "metric_id": "payoff_rank_ic",
        "point_estimate": point,
        "cluster_bootstrap_rank_ic_ci_low": ci_low,
        "cluster_bootstrap_rank_ic_ci_high": ci_high,
        "bootstrap_ci_level": config["expected"]["bootstrap_ci_level"],
        "ci_excludes_zero_flag": bool(np.isfinite(ci_low) and ci_low > 0),
        "bootstrap_resample_n": int(config["expected"]["bootstrap_resample_n"]),
        "valid_bootstrap_resample_n": int(len(valid)),
        "invalid_bootstrap_resample_n": int(len(values) - len(valid)),
        "bootstrap_cluster_key": "episode_cluster_id",
        "bootstrap_random_seed": int(config["expected"]["bootstrap_random_seed"]),
        "bootstrap_status": "pass" if len(valid) == len(values) and ci_low > 0 else "fail",
    }
    return pd.DataFrame([row])


def score_after_zeroing(score: pd.DataFrame, coefficients: pd.DataFrame, removed: list[str]) -> pd.Series:
    coef = coefficients.loc[
        coefficients["model_id"].eq(PRIMARY_MODEL_ID) & coefficients["feature_name"].isin(removed),
        ["feature_name", "coefficient"],
    ]
    adjustment = np.zeros(len(score), dtype=float)
    for _, row in coef.iterrows():
        adjustment += score[row["feature_name"]].to_numpy(dtype=float) * float(row["coefficient"])
    return score[model_score_column(PRIMARY_MODEL_ID)] - adjustment


def build_topk_removal_sensitivity(config: dict[str, Any], score: pd.DataFrame, coefficients: pd.DataFrame) -> pd.DataFrame:
    primary_coef = coefficients.loc[coefficients["model_id"].eq(PRIMARY_MODEL_ID)].copy()
    ordered = primary_coef.sort_values("standardized_abs_coefficient_rank")["feature_name"].tolist()
    rows = []
    specs: list[tuple[str, str, list[str], str]] = []
    for k in (1, 3, 5):
        specs.append((f"top{k}_abs_coefficient_removed", "topk", ordered[:k], "mixed"))
    for family, features in config["feature_family_map"].items():
        specs.append((f"family_{family}_removed", "family", features, family))
    for split in ("robustness", "validation"):
        sub = score.loc[score["cluster_split_bucket"].eq(split)]
        base_ic = rank_ic(sub[model_score_column(PRIMARY_MODEL_ID)], sub["y_payoff_h20"])
        for sid, typ, removed, family in specs:
            sens_score = score_after_zeroing(score, primary_coef, removed)
            sens = sens_score.loc[sub.index]
            sens_ic = rank_ic(sens, sub["y_payoff_h20"])
            retention = sens_ic / base_ic if np.isfinite(sens_ic) and np.isfinite(base_ic) and abs(base_ic) > 1e-15 else np.nan
            rows.append(
                {
                    "sensitivity_id": sid,
                    "split_bucket": split,
                    "model_id": PRIMARY_MODEL_ID,
                    "removal_type": typ,
                    "removed_feature_n": len(removed),
                    "removed_feature_names": "|".join(removed),
                    "removed_feature_family_id": family,
                    "base_rank_ic_spearman": base_ic,
                    "sensitivity_rank_ic_spearman": sens_ic,
                    "rank_ic_retention_rate": retention,
                    "sensitivity_status": "pass" if np.isfinite(sens_ic) else "fail",
                }
            )
    return pd.DataFrame(rows)


def build_baseline_comparison(config: dict[str, Any], oos: pd.DataFrame, deciles: pd.DataFrame, bootstrap: pd.DataFrame) -> pd.DataFrame:
    primary_rank = float(oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness"), "rank_ic_spearman"].iloc[0])
    vol_rank = float(oos.loc[oos["model_id"].eq(VOL_BASELINE_ID) & oos["split_bucket"].eq("robustness"), "rank_ic_spearman"].iloc[0])
    primary_mono = float(deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID) & deciles["split_bucket"].eq("robustness"), "decile_payoff_monotonicity_spearman"].iloc[0])
    vol_mono = float(deciles.loc[deciles["model_id"].eq(VOL_BASELINE_ID) & deciles["split_bucket"].eq("robustness"), "decile_payoff_monotonicity_spearman"].iloc[0])
    rows = []
    def add(comp: str, baseline: str, metric: str, model_val: float, base_val: float, req: float, hard: bool, role: str, base_den: str) -> None:
        delta = model_val - base_val if np.isfinite(model_val) and np.isfinite(base_val) else np.nan
        rows.append(
            {
                "comparison_id": comp,
                "split_bucket": "robustness",
                "model_id": PRIMARY_MODEL_ID,
                "baseline_id": baseline,
                "metric_id": metric,
                "model_denominator_type": "labelable_full",
                "baseline_denominator_type": base_den,
                "baseline_role": role,
                "model_value": model_val,
                "baseline_value": base_val,
                "delta_vs_baseline": delta,
                "required_delta": req,
                "hard_gate_used": hard,
                "comparison_status": "pass" if hard and np.isfinite(delta) and delta > req else "external_context_only" if not hard and role == "external_coarse_context_only" else "diagnostic_only",
            }
        )
    add("payoff_rank_ic_vs_volatility20d", VOL_BASELINE_ID, "payoff_rank_ic", primary_rank, vol_rank, config["expected"]["volatility_rank_ic_margin_floor"], True, "same_denominator_risk_baseline", "labelable_full")
    add("monotonicity_vs_volatility20d", VOL_BASELINE_ID, "decile_monotonicity", primary_mono, vol_mono, 0.0, False, "same_denominator_risk_baseline", "labelable_full")
    add("payoff_rank_ic_vs_intercept", "intercept_unconditional_payoff_baseline", "payoff_rank_ic", primary_rank, np.nan, 0.0, False, "baseline_only", "labelable_full")
    x = config["expected"]["sixteen_x"]
    add("payoff_rank_ic_vs_16x_external", "16x_payoff_rank_probe_v1", "payoff_rank_ic", primary_rank, x["robustness_payoff_rank_ic"], 0.0, False, "external_coarse_context_only", "winner_episode_probe_rows_only")
    add("monotonicity_vs_16x_external", "16x_payoff_rank_probe_v1", "decile_monotonicity", primary_mono, x["robustness_decile_monotonicity_spearman"], 0.0, False, "external_coarse_context_only", "winner_episode_probe_rows_only")
    add("bootstrap_ci_low_vs_16x_external", "16x_payoff_rank_probe_v1", "bootstrap_ci_low", float(bootstrap["cluster_bootstrap_rank_ic_ci_low"].iloc[0]), x["robustness_cluster_bootstrap_rank_ic_ci_low"], 0.0, False, "external_coarse_context_only", "winner_episode_probe_rows_only")
    return pd.DataFrame(rows)


def safe_auc(y: pd.Series, score: pd.Series) -> float:
    y = y.astype(int)
    if y.nunique() < 2:
        return np.nan
    return float(roc_auc_score(y, score))


def safe_ap(y: pd.Series, score: pd.Series) -> float:
    y = y.astype(int)
    if y.nunique() < 2:
        return np.nan
    return float(average_precision_score(y, score))


def build_binary_sanity(config: dict[str, Any], score: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    specs = [
        ("ridge_logistic_top30_sanity_v1", "top30_yes_no"),
        ("ridge_logistic_top20_sanity_v1", "top20_yes_no"),
        (PRIMARY_MODEL_ID, "binary_positive_negative"),
    ]
    for model_id, target in specs:
        col = model_score_column(model_id)
        for split in SPLITS:
            sub = score.loc[score["cluster_split_bucket"].eq(split)]
            y = sub[target].astype(bool)
            ap = safe_ap(y, sub[col])
            base = float(y.mean())
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
                    "roc_auc": safe_auc(y, sub[col]),
                    "average_precision": ap,
                    "split_unconditional_positive_rate": base,
                    "precision_lift": ap - base if np.isfinite(ap) else np.nan,
                    "binary_metric_used_as_primary_gate": False,
                    "binary_sanity_status": "appendix_sanity_only",
                }
            )
    c16 = tables["sixteen_c_oos_separability"]
    c16_rows = c16.loc[c16["model_id"].astype(str).eq("ridge_logistic_bar_state_v1")]
    for _, row in c16_rows.iterrows():
        rows.append(
            {
                "split_bucket": row["split_bucket"],
                "model_id": "16c_ridge_logistic_bar_state_v1",
                "target_column": "binary_positive_negative",
                "denominator_type": "binary_primary",
                "row_n": int(row["binary_step_n"]),
                "positive_n": int(row["positive_n"]),
                "negative_n": int(row["negative_n"]),
                "neutral_n": 0,
                "roc_auc": row["roc_auc"],
                "average_precision": row["average_precision"],
                "split_unconditional_positive_rate": row["binary_positive_rate"],
                "precision_lift": row["pr_auc_lift_vs_binary_base"],
                "binary_metric_used_as_primary_gate": False,
                "binary_sanity_status": "external_16c_appendix_only",
            }
        )
    return pd.DataFrame(rows)


def build_search_accounting_audit() -> tuple[pd.DataFrame, str]:
    row = {
        "search_family": "payoff_state_separability_diagnostic",
        "phase_id": PHASE_ID,
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


def build_figures(score: pd.DataFrame, deciles: pd.DataFrame, outputs: dict[str, Path]) -> None:
    outputs["decile_curve"].parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    plot = deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID)]
    label_map = {
        "train": "train",
        "robustness": "robustness (primary support)",
        "validation": "validation (stress readout only)",
    }
    for split in SPLITS:
        sub = plot.loc[plot["split_bucket"].eq(split)].sort_values("decile_index")
        ax.plot(sub["decile_index"], sub["mean_payoff"], marker="o", label=label_map[split])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Train-frozen score decile")
    ax.set_ylabel("Mean h20 payoff")
    ax.set_title("Payoff-state decile curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(outputs["decile_curve"], dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    robust = score.loc[score["cluster_split_bucket"].eq("robustness")]
    x = robust[model_score_column(PRIMARY_MODEL_ID)].rank(pct=True)
    y = robust["y_payoff_h20"].rank(pct=True)
    ax.hexbin(x, y, gridsize=25, mincnt=1, cmap="viridis")
    ax.set_xlabel("Score rank pct")
    ax.set_ylabel("Payoff rank pct")
    ax.set_title("Score vs payoff rank surface")
    fig.tight_layout()
    fig.savefig(outputs["score_surface"], dpi=160)
    plt.close(fig)


def build_decision_row(
    config: dict[str, Any],
    gates: dict[str, str],
    oos: pd.DataFrame,
    deciles: pd.DataFrame,
    bucket: pd.DataFrame,
    bootstrap: pd.DataFrame,
    baseline: pd.DataFrame,
    sensitivity: pd.DataFrame,
    binary: pd.DataFrame,
) -> pd.DataFrame:
    primary_rank = float(oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness"), "rank_ic_spearman"].iloc[0])
    primary_mono = float(deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID) & deciles["split_bucket"].eq("robustness"), "decile_payoff_monotonicity_spearman"].iloc[0])
    ci_low = float(bootstrap["cluster_bootstrap_rank_ic_ci_low"].iloc[0])
    x_delta = float(oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness"), "coarse_rank_ic_vs_16x_external_delta"].iloc[0])
    validation = oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("validation")].iloc[0]
    all_pass = all(gates[gate] == "pass" for gate in HARD_GATES)
    binary_positive = bool(
        binary.loc[
            binary["split_bucket"].eq("robustness")
            & ~binary["model_id"].astype(str).str.startswith("16c")
            & (
                (binary["roc_auc"] >= float(config["expected"]["binary_blocked_classification_min_roc_auc"]))
                | (binary["precision_lift"] > float(config["expected"]["binary_blocked_classification_min_precision_lift"]))
            )
        ].shape[0]
    )
    bucket_weak = gates["bucket_lift_gate"] != "pass"
    primary_weak = gates["rank_ic_support_gate"] != "pass" and gates["monotonicity_support_gate"] != "pass"

    decision = "18C_payoff_state_separability_supported"
    next_req = "requirement_18d_payoff_state_oracle_gap_bridge.md"
    blocking = ""
    if not all_pass:
        next_req = "none"
        if gates["upstream_18b_contract_gate"] != "pass":
            decision = "18C_upstream_18b_contract_blocked"
        elif gates["input_artifact_gate"] != "pass":
            decision = "18C_input_artifact_blocked"
        elif gates["matrix_contract_replay_gate"] != "pass":
            decision = "18C_matrix_contract_replay_blocked"
        elif gates["model_registry_gate"] != "pass":
            decision = "18C_model_registry_blocked"
        elif gates["train_only_fit_gate"] != "pass":
            decision = "18C_train_only_fit_blocked"
        elif gates["oos_no_tuning_gate"] != "pass":
            decision = "18C_oos_tuning_blocked"
        elif gates["search_accounting_gate"] != "pass":
            decision = "18C_search_accounting_blocked"
        elif gates["risk_only_gate"] != "pass":
            decision = "18C_risk_only_no_payoff_state"
        elif primary_weak and bucket_weak and not binary_positive:
            decision = "18C_current_features_reconfirmed_insufficient"
        elif gates["bucket_lift_gate"] == "pass" and primary_weak:
            decision = "18C_over_narrow_winner_target_blocked"
        elif binary_positive and primary_weak:
            decision = "18C_binary_only_not_supported"
        elif any(gates[g] != "pass" for g in ["rank_ic_support_gate", "monotonicity_support_gate", "bootstrap_ci_gate", "baseline_improvement_gate"]):
            decision = "18C_payoff_state_signal_weak_or_nonmonotone"
        else:
            decision = "18C_separability_contract_blocked"
        blocking = decision
    row = {
        "decision_state": decision,
        "next_allowed_requirement": next_req,
        "all_hard_gates_pass": all_pass,
        **gates,
        "validation_stress_evaluable": bool(int(validation["row_n"]) == config["expected"]["denominators"]["validation"]["labelable_step_n"] and int(validation["episode_cluster_n"]) >= config["expected"]["denominators"]["validation"]["episode_cluster_n_min"]),
        "validation_stress_caveat": "stress_readout_only",
        "entry_policy_authorized": False,
        "exit_policy_authorized": False,
        "holding_policy_authorized": False,
        "portfolio_backtest_authorized": False,
        "model_deployment_authorized": False,
        "production_signal_authorized": False,
        "live_trading_authorized": False,
        "blocking_reason": blocking,
        "primary_model_id": PRIMARY_MODEL_ID,
        "robustness_payoff_rank_ic": primary_rank,
        "robustness_decile_payoff_monotonicity_spearman": primary_mono,
        "robustness_cluster_bootstrap_rank_ic_ci_low": ci_low,
        "coarse_rank_ic_vs_16x_external_delta": x_delta,
        "rank_ic_materiality_floor": config["expected"]["rank_ic_materiality_floor"],
    }
    return pd.DataFrame([row])


def markdown_table(frame: pd.DataFrame) -> str:
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda value: "" if pd.isna(value) else str(value).replace("|", r"\|"))
    return out.to_markdown(index=False)


def build_report(
    input_audit: pd.DataFrame,
    upstream: pd.DataFrame,
    matrix_contract: pd.DataFrame,
    registry: pd.DataFrame,
    cv: pd.DataFrame,
    coefficients: pd.DataFrame,
    oos: pd.DataFrame,
    deciles: pd.DataFrame,
    bucket: pd.DataFrame,
    bootstrap: pd.DataFrame,
    sensitivity: pd.DataFrame,
    baseline: pd.DataFrame,
    binary: pd.DataFrame,
    search: pd.DataFrame,
    decision: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    primary = oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness")].iloc[0]
    mono = deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID) & deciles["split_bucket"].eq("robustness"), "decile_payoff_monotonicity_spearman"].iloc[0]
    top_gap = deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID) & deciles["split_bucket"].eq("robustness"), "top3_minus_bottom3_payoff_gap"].iloc[0]
    gate_rows = pd.DataFrame({"gate": list(HARD_GATES), "status": [d[gate] for gate in HARD_GATES]})
    input_summary = (
        input_audit.groupby(["read_status", "schema_status", "cache_key_reconciliation_gate"], dropna=False)
        .size()
        .reset_index(name="artifact_n")
    )
    cv_summary = (
        cv.groupby("model_id", as_index=False)
        .agg(
            fold_n=("fold_id", "nunique"),
            mean_payoff_rank_ic=("payoff_rank_ic", "mean"),
            mean_decile_monotonicity=("decile_payoff_monotonicity_spearman", "mean"),
        )
        .sort_values("model_id")
    )
    coefficient_top = coefficients.loc[coefficients["model_id"].eq(PRIMARY_MODEL_ID)].sort_values("standardized_abs_coefficient_rank").head(10)
    primary_oos = oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID)].copy()
    primary_deciles = deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID)].copy()
    sensitivity_readout = sensitivity.loc[sensitivity["split_bucket"].eq("robustness")].copy()
    return f"""# Payoff-state Separability Diagnostic Report

## Decision

decision_state = {d["decision_state"]}
next_allowed_requirement = {d["next_allowed_requirement"]}

18C evaluates low-capacity payoff-state separability only.
18C does not authorize policy, portfolio backtest, deployment, production signal, or live trading.
Only 18C_payoff_state_separability_supported may authorize 18D.

## Gate Summary

    {markdown_table(gate_rows)}

## Input Artifact Audit

    {markdown_table(input_summary)}

## 18B Handoff Replay

    {markdown_table(upstream)}

## Matrix Contract Replay

continue_advantage is an affine replay of y_payoff_h20 and is not independent evidence.

    {markdown_table(matrix_contract)}

## Model Registry And Train-only Fitting

    {markdown_table(registry)}

Train-only grouped CV is diagnostic-only and does not select model family, features, score threshold, payoff cutoff, or any OOS gate.

    {markdown_table(cv_summary)}

## Primary Robustness Readout

| metric | value |
|:--|--:|
| robustness_payoff_rank_ic | {float(primary["rank_ic_spearman"]):.6f} |
| rank_ic_materiality_floor | {float(d["rank_ic_materiality_floor"]):.6f} |
| robustness_decile_monotonicity | {float(mono):.6f} |
| top3_minus_bottom3_payoff_gap | {float(top_gap):.6f} |
| bootstrap_ci_low | {float(bootstrap["cluster_bootstrap_rank_ic_ci_low"].iloc[0]):.6f} |

## OOS Rank Readout

Robustness is the primary support split. Validation is stress readout only.

    {markdown_table(primary_oos)}

## Decile Monotonicity

    {markdown_table(primary_deciles)}

## Baseline Boundary

16X is reported as external coarse context only because its denominator and target construction differ from 18C.
The hard same-denominator baseline gate uses `volatility20d_defense_baseline`.

    {markdown_table(baseline)}

## Bucket Lift

    {markdown_table(bucket)}

## Cluster Bootstrap CI

    {markdown_table(bootstrap)}

## Coefficients And Sensitivity

Top-k removal uses standardized_abs_coefficient_rank, computed from coefficient * feature_train_std.

    {markdown_table(coefficient_top)}

    {markdown_table(sensitivity_readout)}

## Binary Sanity Appendix

16C binary continuation results are appendix-only and are not primary payoff-state gates.

    {markdown_table(binary)}

## Search Accounting

No feature selection from target correlation, no robustness/validation feature selection, no OOS model-family selection, no threshold tuning, no split-local payoff cutoff recomputation, and no binary metric primary gate were used.

    {markdown_table(search)}
"""


def gate_from_bool(value: bool) -> str:
    return "pass" if bool(value) else "fail"


def build_all_outputs(config: dict[str, Any], resolved: dict[str, Path], input_gate: str) -> dict[str, Any]:
    tables = load_inputs(resolved)
    matrix = add_ordinal_int(config, read_table(resolved["eighteen_b_matrix"]))
    upstream, upstream_gate = build_upstream_18b_handoff_audit(config, tables)
    contract, contract_gate = build_matrix_contract_replay_audit(config, matrix, tables)
    registry, registry_gate = build_model_registry(config)
    score, coefficients, _ = build_scores_and_coefficients(config, matrix)
    cv = build_cv_readout(config, matrix)
    oos = build_oos_rank_readout(config, score)
    deciles = build_decile_monotonicity(config, score)
    bucket = build_bucket_lift(score)
    bootstrap = build_bootstrap_ci(config, score)
    sensitivity = build_topk_removal_sensitivity(config, score, coefficients)
    baseline = build_baseline_comparison(config, oos, deciles, bootstrap)
    binary = build_binary_sanity(config, score, tables)
    search, search_gate = build_search_accounting_audit()

    primary_row = oos.loc[oos["model_id"].eq(PRIMARY_MODEL_ID) & oos["split_bucket"].eq("robustness")].iloc[0]
    rank_gate = gate_from_bool(
        float(primary_row["rank_ic_spearman"]) >= float(config["expected"]["rank_ic_materiality_floor"])
        and float(primary_row["continue_advantage_replay_abs_diff"]) <= 1e-12
    )
    primary_mono_rows = deciles.loc[deciles["model_id"].eq(PRIMARY_MODEL_ID) & deciles["split_bucket"].eq("robustness")]
    mono_gate = gate_from_bool(
        float(primary_mono_rows["decile_payoff_monotonicity_spearman"].iloc[0]) >= float(config["expected"]["monotonicity_floor"])
        and float(primary_mono_rows["top3_minus_bottom3_payoff_gap"].iloc[0]) > 0
        and not bool(primary_mono_rows["split_local_score_cutoff_recompute_used"].any())
    )
    robust_bucket = bucket.loc[bucket["split_bucket"].eq("robustness")]
    bucket_gate = gate_from_bool(robust_bucket["bucket_lift"].min() > 1.0 and not robust_bucket["split_local_score_cutoff_recompute_used"].any())
    boot_gate = gate_from_bool(
        float(bootstrap["cluster_bootstrap_rank_ic_ci_low"].iloc[0]) > 0
        and int(bootstrap["valid_bootstrap_resample_n"].iloc[0]) == int(config["expected"]["bootstrap_resample_n"])
    )
    baseline_hard = baseline.loc[baseline["hard_gate_used"].astype(bool)]
    baseline_gate = gate_from_bool(not baseline_hard.empty and baseline_hard["comparison_status"].eq("pass").all())
    f4_retention = float(
        sensitivity.loc[
            sensitivity["split_bucket"].eq("robustness") & sensitivity["sensitivity_id"].eq("family_F4_removed"),
            "rank_ic_retention_rate",
        ].iloc[0]
    )
    vol_delta = float(baseline_hard["delta_vs_baseline"].iloc[0]) if not baseline_hard.empty else np.nan
    risk_gate = gate_from_bool(
        (np.isfinite(vol_delta) and vol_delta > float(config["expected"]["volatility_rank_ic_margin_floor"]))
        or (np.isfinite(f4_retention) and f4_retention >= float(config["expected"]["f4_removal_retention_floor"]))
    )
    binary_gate = gate_from_bool((~binary["binary_metric_used_as_primary_gate"].astype(bool)).all())
    gates = {
        "upstream_18b_contract_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "matrix_contract_replay_gate": contract_gate,
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
    decision = build_decision_row(config, gates, oos, deciles, bucket, bootstrap, baseline, sensitivity, binary)
    return {
        "tables": tables,
        "matrix": matrix,
        "score": score,
        "upstream": upstream,
        "matrix_contract": contract,
        "registry": registry,
        "cv": cv,
        "coefficients": coefficients,
        "oos": oos,
        "deciles": deciles,
        "bucket": bucket,
        "bootstrap": bootstrap,
        "sensitivity": sensitivity,
        "baseline": baseline,
        "binary": binary,
        "search": search,
        "gates": gates,
        "decision": decision,
    }


def write_outputs(config: dict[str, Any], resolved: dict[str, Path], outputs: dict[str, Path], input_audit: pd.DataFrame, artifacts: dict[str, Any]) -> None:
    outputs["score_panel"].parent.mkdir(parents=True, exist_ok=True)
    score_columns = [
        *config["full_lineage_key_columns"],
        config["split_column"],
        *TARGET_COLUMNS,
        "payoff_ordinal_state_int",
        *config["model_ready_features"],
        *[col for col in artifacts["score"].columns if col.startswith("score_")],
    ]
    artifacts["score"].loc[:, score_columns].to_parquet(outputs["score_panel"], index=False)
    write_df(outputs["upstream_18b_handoff_audit"], artifacts["upstream"])
    write_df(outputs["matrix_contract_replay_audit"], artifacts["matrix_contract"])
    write_df(outputs["model_registry"], artifacts["registry"])
    write_df(outputs["model_cv_readout"], artifacts["cv"])
    write_df(outputs["model_coefficients"], artifacts["coefficients"])
    write_df(outputs["oos_rank_readout"], artifacts["oos"])
    write_df(outputs["decile_monotonicity"], artifacts["deciles"])
    write_df(outputs["bucket_lift"], artifacts["bucket"])
    write_df(outputs["bootstrap_ci"], artifacts["bootstrap"])
    write_df(outputs["topk_removal_sensitivity"], artifacts["sensitivity"])
    write_df(outputs["baseline_comparison"], artifacts["baseline"])
    write_df(outputs["binary_sanity"], artifacts["binary"])
    write_df(outputs["search_accounting"], artifacts["search"])
    write_df(outputs["decision"], artifacts["decision"])
    build_figures(artifacts["score"], artifacts["deciles"], outputs)
    write_text(
        outputs["report"],
        build_report(
            input_audit,
            artifacts["upstream"],
            artifacts["matrix_contract"],
            artifacts["registry"],
            artifacts["cv"],
            artifacts["coefficients"],
            artifacts["oos"],
            artifacts["deciles"],
            artifacts["bucket"],
            artifacts["bootstrap"],
            artifacts["sensitivity"],
            artifacts["baseline"],
            artifacts["binary"],
            artifacts["search"],
            artifacts["decision"],
        ),
    )
    write_manifests(config, resolved, outputs, input_audit, artifacts)


def write_manifests(config: dict[str, Any], resolved: dict[str, Path], outputs: dict[str, Path], input_audit: pd.DataFrame, artifacts: dict[str, Any]) -> None:
    output_keys = [
        "score_panel",
        "input_artifact_audit",
        "upstream_18b_handoff_audit",
        "matrix_contract_replay_audit",
        "model_registry",
        "model_cv_readout",
        "model_coefficients",
        "oos_rank_readout",
        "decile_monotonicity",
        "bucket_lift",
        "bootstrap_ci",
        "topk_removal_sensitivity",
        "baseline_comparison",
        "binary_sanity",
        "search_accounting",
        "decision",
        "decile_curve",
        "score_surface",
        "report",
    ]
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
            "source_18b_matrix_sha256": file_sha(resolved["eighteen_b_matrix"]),
            "row_count": count_rows(outputs["score_panel"]),
            "split_counts": artifacts["score"]["cluster_split_bucket"].value_counts().sort_index().to_dict(),
            "identity_key_columns": config["primary_identity_key_columns"],
            "score_columns": [col for col in artifacts["score"].columns if col.startswith("score_")],
            "target_columns": list(TARGET_COLUMNS) + ["payoff_ordinal_state_int"],
            "model_ids": artifacts["registry"]["model_id"].tolist(),
        },
    )
    decision = artifacts["decision"].iloc[0]
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "requirement_file_sha256": file_sha(EXPERIMENT_DIR / "requirement_18c_payoff_state_separability_diagnostic.md"),
        "config_file_sha256": file_sha(CONFIG_PATH),
        "runner_file_sha256": file_sha(Path(__file__)),
        "input_artifact_manifest_sha256": file_sha(outputs["input_manifest"]),
        "score_panel_sha256": file_sha(outputs["score_panel"]),
        "publishable_table_sha256_by_name": {key: file_sha(outputs[key]) for key in output_keys if outputs[key].suffix == ".csv"},
        "publishable_figure_sha256_by_name": {key: file_sha(outputs[key]) for key in ("decile_curve", "score_surface")},
        "report_sha256": file_sha(outputs["report"]),
        "output_hashes": {key: file_sha(outputs[key]) for key in [*output_keys, "input_manifest", "score_panel_manifest"]},
        "row_counts": {key: count_rows(outputs[key]) for key in [*output_keys, "input_manifest", "score_panel_manifest"]},
        "input_artifact_hashes": dict(zip(input_audit["artifact_key"], input_audit["sha256"], strict=False)),
        "decision_state": decision["decision_state"],
        "next_allowed_requirement": decision["next_allowed_requirement"],
        "all_hard_gates_pass": bool(decision["all_hard_gates_pass"]),
        "primary_model_id": PRIMARY_MODEL_ID,
        "primary_split": "robustness",
        "primary_target_id": "y_payoff_h20",
        "robustness_payoff_rank_ic": decision["robustness_payoff_rank_ic"],
        "robustness_decile_payoff_monotonicity_spearman": decision["robustness_decile_payoff_monotonicity_spearman"],
        "robustness_cluster_bootstrap_rank_ic_ci_low": decision["robustness_cluster_bootstrap_rank_ic_ci_low"],
        "coarse_rank_ic_vs_16x_external_delta": decision["coarse_rank_ic_vs_16x_external_delta"],
        "validation_role": "stress_readout_only",
        "authorization_flags": {col: bool(decision[col]) for col in AUTH_FALSE_COLUMNS},
        **{col: bool(decision[col]) for col in AUTH_FALSE_COLUMNS},
    }
    write_json(outputs["manifest"], manifest)


def run(config_path: Path, mode: str = "full") -> dict[str, Any]:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit, input_gate = build_input_artifact_audit(config, resolved)
    tables = load_inputs(resolved)
    xref = config["expected"]["sixteen_x"]
    x_rank = tables["sixteen_x_survival_vs_payoff_rank_ic"].loc[
        tables["sixteen_x_survival_vs_payoff_rank_ic"]["split_bucket"].eq("robustness")
        & tables["sixteen_x_survival_vs_payoff_rank_ic"]["probe_id"].eq(xref["payoff_probe_id"]),
        "rank_ic_spearman",
    ].iloc[0]
    x_boot = tables["sixteen_x_cluster_bootstrap_rank_ic"]["cluster_bootstrap_rank_ic_ci_low"].iloc[0]
    x_mono = tables["sixteen_x_payoff_decile_monotonicity"].loc[
        tables["sixteen_x_payoff_decile_monotonicity"]["split_bucket"].eq("robustness"),
        "payoff_decile_monotonicity_spearman",
    ].iloc[0]
    observed_xref = {
        "robustness_payoff_rank_ic": float(x_rank),
        "robustness_cluster_bootstrap_rank_ic_ci_low": float(x_boot),
        "robustness_decile_monotonicity_spearman": float(x_mono),
    }
    expected_xref = {
        "robustness_payoff_rank_ic": float(xref["robustness_payoff_rank_ic"]),
        "robustness_cluster_bootstrap_rank_ic_ci_low": float(xref["robustness_cluster_bootstrap_rank_ic_ci_low"]),
        "robustness_decile_monotonicity_spearman": float(xref["robustness_decile_monotonicity_spearman"]),
    }
    x_ok = all(abs(observed_xref[key] - expected_xref[key]) <= 1e-12 for key in expected_xref)
    input_audit = append_sixteen_x_reference_audit(input_audit, observed_xref, expected_xref, "pass" if x_ok else "fail")
    if not x_ok:
        input_gate = "fail"
    write_df(outputs["input_artifact_audit"], input_audit)
    write_json(
        outputs["input_manifest"],
        {
            "experiment_id": EXPERIMENT_ID,
            "phase_id": PHASE_ID,
            "run_id": RUN_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_artifacts": input_audit.to_dict(orient="records"),
            "sixteen_x_reference_gate": "pass" if x_ok else "fail",
        },
    )
    if mode == "check-inputs":
        return {"input_artifact_gate": input_gate, "input_artifact_audit": input_audit, "sixteen_x_reference_gate": "pass" if x_ok else "fail"}
    artifacts = build_all_outputs(config, resolved, input_gate)
    write_outputs(config, resolved, outputs, input_audit, artifacts)
    return {
        "input_artifact_gate": input_gate,
        "input_artifact_audit": input_audit,
        **artifacts,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "check-inputs" if args.check_inputs_only else args.mode
    run(Path(args.config), mode=mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

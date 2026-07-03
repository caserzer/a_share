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
import numpy as np
import pandas as pd
import yaml


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "18F_payoff_state_oracle_gap_bridge"
EXPERIMENT_ID = "18_payoff_state_representation_research"
PHASE_ID = "18F"
PRIMARY_MODEL_ID = "ridge_payoff_rank_h20_v1"
PRIMARY_SCORE_COLUMN = "ridge_payoff_rank_h20_v1_score"
PRIMARY_OPERATING_POINT_ID = "defend_bottom30_continue_rest"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_18f_payoff_state_oracle_gap_bridge.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
FIGURE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "figures" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

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
    "upstream_18c_refresh_contract_gate",
    "input_artifact_gate",
    "score_matrix_join_gate",
    "oracle_denominator_contract_gate",
    "o5_identity_replay_gate",
    "o5_upper_bound_contract_gate",
    "operating_point_freeze_gate",
    "learned_utility_support_gate",
    "oracle_gap_reduction_gate",
    "positive_sacrifice_gate",
    "payoff_retention_gate",
    "neutral_reconciliation_gate",
    "cluster_bootstrap_utility_gate",
    "topk_sensitivity_gate",
    "validation_stress_gate",
    "binary_boundary_gate",
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
    "top30_yes_no",
    "top20_yes_no",
    "binary_positive_negative",
)
SCORE_PANEL_COLUMNS = (
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
    PRIMARY_SCORE_COLUMN,
    "ridge_payoff_rank_h20_v1_train_score_decile",
    "ridge_payoff_rank_h20_v1_train_score_top30_bucket",
    "ridge_payoff_rank_h20_v1_train_score_top20_bucket",
    "score_cutoff_source",
    "split_local_score_cutoff_recompute_used",
    "source_18e_matrix_sha256",
    "score_panel_status",
    "blocking_reason",
)
UTILITY_COLUMNS = [
    "split_bucket",
    "denominator_type",
    "operating_point_id",
    "decision_role",
    "row_n",
    "episode_cluster_n",
    "defended_n",
    "continued_n",
    "defended_rate",
    "learned_mean_incremental_return",
    "learned_sum_incremental_return",
    "mean_continue_value",
    "mean_defend_value_on_defended_rows",
    "mean_defend_advantage_on_defended_rows",
    "defended_positive_incremental_return",
    "defended_negative_incremental_return",
    "defended_neutral_incremental_return",
    "residual_reconciliation_term",
    "positive_sacrifice_to_avoidance_ratio",
    "top30_payoff_retention_rate",
    "top20_payoff_retention_rate",
    "neutral_row_n",
    "neutral_contribution_mean",
    "utility_bridge_status",
    "blocking_reason",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP18F payoff-state oracle gap bridge.")
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
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_18c_refresh_handoff_audit": TABLE_DIR / "upstream_18c_refresh_handoff_audit.csv",
        "score_matrix_join_audit": TABLE_DIR / "score_matrix_join_audit.csv",
        "oracle_reference_replay_audit": TABLE_DIR / "oracle_reference_replay_audit.csv",
        "score_operating_point_freeze": TABLE_DIR / "score_operating_point_freeze.csv",
        "learned_payoff_state_utility_bridge": TABLE_DIR / "learned_payoff_state_utility_bridge.csv",
        "oracle_gap_bridge": TABLE_DIR / "oracle_gap_bridge.csv",
        "payoff_state_six_cell_decomposition": TABLE_DIR / "payoff_state_six_cell_decomposition.csv",
        "binary_denominator_bridge": TABLE_DIR / "binary_denominator_bridge.csv",
        "cluster_bootstrap_utility_bridge": TABLE_DIR / "cluster_bootstrap_utility_bridge.csv",
        "topk_bootstrap_utility_bridge": TABLE_DIR / "topk_bootstrap_utility_bridge.csv",
        "validation_stress_utility_bridge": TABLE_DIR / "validation_stress_utility_bridge.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "payoff_state_oracle_gap_bridge_decision.csv",
        "oracle_gap_bridge_curve": FIGURE_DIR / "oracle_gap_bridge_curve.png",
        "positive_sacrifice_vs_payoff_preservation": FIGURE_DIR / "positive_sacrifice_vs_payoff_preservation.png",
        "report": REPORT_DIR / "payoff_state_oracle_gap_bridge_report.md",
        "manifest": MANIFEST_DIR / "18F_payoff_state_oracle_gap_bridge_manifest.json",
        "input_manifest": MANIFEST_DIR / "input_artifact_manifest_18f.json",
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
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_json(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_df(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_table(path: Path) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path)
    if suffixes.endswith((".csv", ".csv.gz")):
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table path: {path}")


def count_rows(path: Path) -> int | str:
    if not path.exists() or path.is_dir():
        return ""
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
    return ""


def header_columns(path: Path) -> list[str]:
    if not path.exists() or path.is_dir():
        return []
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return list(pd.read_parquet(path, engine="pyarrow").columns)
    if suffixes.endswith((".csv", ".csv.gz")):
        return list(pd.read_csv(path, nrows=0).columns)
    return []


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


def relative_to_topic(path: Path) -> str:
    try:
        return str(path.relative_to(TOPIC_ROOT))
    except ValueError:
        return str(path)


def gate_from_bool(value: bool) -> str:
    return "pass" if bool(value) else "fail"


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def required_columns_for_key(key: str, config: dict[str, Any]) -> set[str]:
    full_key = set(config["full_lineage_key_columns"])
    score_required = set(SCORE_PANEL_COLUMNS)
    matrix_required = full_key | set(TARGET_COLUMNS)
    mapping: dict[str, set[str]] = {
        "eighteen_c_refresh_score_panel": score_required,
        "eighteen_c_refresh_decision": {
            "decision_state",
            "next_allowed_requirement",
            "next_allowed_requirement_scope",
            "all_hard_gates_pass",
            *AUTH_FALSE_COLUMNS,
            "primary_model_id",
            "robustness_payoff_rank_ic",
            "robustness_decile_payoff_monotonicity_spearman",
            "robustness_cluster_bootstrap_rank_ic_ci_low",
            "rank_ic_vs_volatility20d_delta",
        },
        "eighteen_c_refresh_oos_rank_readout": {"split_bucket", "model_id", "rank_ic_spearman"},
        "eighteen_c_refresh_decile_monotonicity": {"split_bucket", "model_id", "decile_payoff_monotonicity_spearman"},
        "eighteen_c_refresh_bucket_lift": {"split_bucket", "model_id", "bucket_lift"},
        "eighteen_c_refresh_bootstrap_ci": {"split_bucket", "model_id", "cluster_bootstrap_rank_ic_ci_low"},
        "eighteen_c_refresh_model_registry": {"model_id", "model_family", "target_column", "fit_split", "model_registry_gate"},
        "eighteen_c_refresh_model_coefficients": {
            "model_id",
            "feature_name",
            "feature_family_id",
            "coefficient",
            "standardized_abs_coefficient_rank",
        },
        "eighteen_c_refresh_topk_sensitivity": {
            "sensitivity_id",
            "split_bucket",
            "removed_feature_names",
            "removal_type",
            "rank_ic_retention_rate",
        },
        "eighteen_c_refresh_family_sensitivity": {
            "sensitivity_id",
            "split_bucket",
            "removed_feature_family_id",
            "removed_feature_names",
            "rank_ic_retention_rate",
        },
        "eighteen_c_refresh_baseline_comparison": {"comparison_id", "split_bucket", "delta_vs_baseline"},
        "eighteen_c_refresh_search_accounting": {"run_id", "scope_id", "search_accounting_gate"},
        "eighteen_e_refreshed_matrix": matrix_required,
        "eighteen_e_schema": {"column_name", "model_ready_feature_name", "primary_model_feature", "target_column"},
        "eighteen_a_decision": {"decision_state", "next_allowed_requirement", "all_hard_gates_pass"},
        "eighteen_a_target_definition_registry": {"target_id", "denominator_type", "lineage_hash"},
        "eighteen_a_target_denominator_reconciliation": {"split_bucket", "labelable_step_n", "neutral_step_n"},
        "eighteen_a_oracle_reference_denominator_map": {
            "oracle_reference_id",
            "source_denominator_type",
            "split_bucket",
            "observed_step_n",
            "mean_incremental_return",
            "allowed_bridge_denominator",
            "direct_comparison_allowed",
            "oracle_reference_denominator_gate",
        },
        "eighteen_a_o5_incremental_definition_replay": {
            "split_bucket",
            "source_mean_incremental_return",
            "max_abs_diff",
            "formula_mismatch_n",
            "o5_incremental_definition_replay_gate",
        },
        "eighteen_a_payoff_cutoff_freeze": {"threshold_id", "train_absolute_payoff_cutoff", "split_local_recompute_used"},
        "eighteen_a_neutral_preservation_audit": {"split_bucket", "neutral_preservation_gate"},
        "seventeen_d_oracle_value_source_attribution": {
            "oracle_variant_id",
            "oracle_family",
            "split_bucket",
            "observed_step_n",
            "mean_incremental_return",
        },
        "seventeen_d_decision": {"final_decision_state", "recommended_next_requirement"},
        "seventeen_d_oracle_learned_model_gap_bridge": {"source_phase_id", "artifact_key", "evidence_metric", "gate_status"},
        "seventeen_d_search_accounting": {"search_accounting_gate"},
        "seventeen_b_oracle_ladder_summary": {"oracle_variant_id", "split_bucket", "mean_incremental_return"},
        "seventeen_b_o5_action_selection_proof": {"split_bucket"},
        "seventeen_b_o2_drawdown_threshold_replay": {"split_bucket"},
        "seventeen_b_high_upside_threshold_freeze": {"threshold_id"},
    }
    if key.endswith("_manifest") or key.endswith("_report") or key.startswith("requirement") or key in {"research_plan", "umbrella_requirement", "eighteen_a_target_contract_doc"}:
        return set()
    return mapping.get(key, set())


def expected_hashes(config: dict[str, Any], resolved: dict[str, Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    expected = config["expected"]
    hashes["eighteen_c_refresh_score_panel"] = str(expected["score_panel_sha256"])
    hashes["eighteen_e_refreshed_matrix"] = str(expected["source_18e_matrix_sha256"])
    hashes["eighteen_e_schema"] = str(expected["source_18e_schema_sha256"])
    c_manifest = resolved.get("eighteen_c_refresh_manifest")
    if c_manifest and c_manifest.exists():
        manifest = read_json(c_manifest)
        table_hashes = manifest.get("publishable_table_sha256_by_name", {})
        table_map = {
            "eighteen_c_refresh_decision": "decision",
            "eighteen_c_refresh_oos_rank_readout": "oos_rank_readout",
            "eighteen_c_refresh_decile_monotonicity": "decile_monotonicity",
            "eighteen_c_refresh_bucket_lift": "bucket_lift",
            "eighteen_c_refresh_bootstrap_ci": "bootstrap_ci",
            "eighteen_c_refresh_model_registry": "model_registry",
            "eighteen_c_refresh_model_coefficients": "model_coefficients",
            "eighteen_c_refresh_topk_sensitivity": "topk_removal_sensitivity",
            "eighteen_c_refresh_family_sensitivity": "family_removal_sensitivity",
            "eighteen_c_refresh_baseline_comparison": "baseline_comparison",
            "eighteen_c_refresh_search_accounting": "search_accounting",
        }
        for artifact_key, table_key in table_map.items():
            value = table_hashes.get(table_key)
            if value:
                hashes[artifact_key] = str(value)
        if manifest.get("report_sha256"):
            hashes["eighteen_c_refresh_report"] = str(manifest["report_sha256"])
    return hashes


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    rows = []
    hashes = expected_hashes(config, resolved)
    for key, meta in config["required_artifacts"].items():
        path = resolved[key]
        exists = path.exists()
        required = required_columns_for_key(key, config)
        observed_cols = set(header_columns(path)) if exists else set()
        missing_cols = sorted(required - observed_cols) if exists else []
        sha = file_sha(path) if exists and path.is_file() else ""
        expected_sha = hashes.get(key, "")
        if not exists:
            hash_status = "missing"
        elif not expected_sha:
            hash_status = "not_manifested"
        elif sha == expected_sha:
            hash_status = "exact_match"
        else:
            hash_status = "mismatch"
        blockers = []
        if not exists:
            blockers.append("missing")
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
                "expected_sha256": expected_sha,
                "source_kind": "publishable_or_local_cache",
                "schema_status": schema_status,
                "read_status": "pass" if exists else "missing",
                "observed_row_n": count_rows(path) if exists else "",
                "cache_hash_validated": hash_status,
                "cache_schema_validated": schema_status == "pass",
                "cache_key_reconciliation_gate": "pass" if schema_status == "pass" and hash_status in {"exact_match", "not_manifested"} else "fail",
                "absolute_path_mismatch_ignored": False,
                "blocking_reason": ";".join(blockers),
            }
        )
    audit = pd.DataFrame(rows)
    gate = "pass" if audit["read_status"].eq("pass").all() and audit["schema_status"].eq("pass").all() and ~audit["cache_hash_validated"].eq("mismatch").any() else "fail"
    return audit, gate


def build_upstream_18c_refresh_handoff_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    expected = config["expected"]

    def add(check_id: str, observed: Any, exp: Any, ok: bool, reason: str | None = None) -> None:
        rows.append(
            {
                "contract_check_id": check_id,
                "observed_value": observed,
                "expected_value": exp,
                "upstream_18c_refresh_contract_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else reason or f"{check_id}_mismatch",
            }
        )

    decision_path = resolved["eighteen_c_refresh_decision"]
    manifest_path = resolved["eighteen_c_refresh_manifest"]
    if decision_path.exists():
        decision = read_table(decision_path).iloc[0]
        checks: list[tuple[str, Any]] = [
            ("decision_state", expected["upstream_18c_decision_state"]),
            ("next_allowed_requirement", expected["upstream_18c_next_allowed_requirement"]),
            ("next_allowed_requirement_scope", expected["upstream_18c_next_allowed_requirement_scope"]),
            ("all_hard_gates_pass", True),
            ("upstream_18e_contract_gate", "pass"),
            ("input_artifact_gate", "pass"),
            ("matrix_contract_replay_gate", "pass"),
            ("model_registry_gate", "pass"),
            ("train_only_fit_gate", "pass"),
            ("oos_no_tuning_gate", "pass"),
            ("rank_ic_support_gate", "pass"),
            ("monotonicity_support_gate", "pass"),
            ("bucket_lift_gate", "pass"),
            ("bootstrap_ci_gate", "pass"),
            ("baseline_improvement_gate", "pass"),
            ("risk_only_gate", "pass"),
            ("binary_sanity_boundary_gate", "pass"),
            ("search_accounting_gate", "pass"),
            ("primary_model_id", expected["primary_model_id"]),
        ]
        checks.extend((col, False) for col in AUTH_FALSE_COLUMNS)
        for field, exp in checks:
            observed = decision.get(field, "")
            ok = bool_like(observed) if exp is True else false_like(observed) if exp is False else str(observed) == str(exp)
            add(field, observed, exp, ok)
        metric_checks = {
            "robustness_payoff_rank_ic": expected["robustness_payoff_rank_ic"],
            "robustness_decile_payoff_monotonicity_spearman": expected["robustness_decile_payoff_monotonicity_spearman"],
            "robustness_cluster_bootstrap_rank_ic_ci_low": expected["robustness_cluster_bootstrap_rank_ic_ci_low"],
            "rank_ic_vs_volatility20d_delta": expected["rank_ic_vs_volatility20d_delta"],
        }
        for field, exp in metric_checks.items():
            observed = safe_float(decision.get(field))
            add(field, observed, exp, abs(observed - float(exp)) <= 1e-12)
    else:
        add("decision_artifact_exists", "missing", "present", False, "eighteen_c_refresh_decision_missing")

    if manifest_path.exists():
        manifest = read_json(manifest_path)
        add("manifest_decision_state", manifest.get("decision_state"), expected["upstream_18c_decision_state"], manifest.get("decision_state") == expected["upstream_18c_decision_state"])
        add("manifest_score_panel_sha256", manifest.get("score_panel_sha256"), expected["score_panel_sha256"], manifest.get("score_panel_sha256") == expected["score_panel_sha256"])
        add("manifest_source_18e_matrix_sha256", manifest.get("source_18e_matrix_sha256"), expected["source_18e_matrix_sha256"], manifest.get("source_18e_matrix_sha256") == expected["source_18e_matrix_sha256"])
    else:
        add("manifest_exists", "missing", "present", False, "eighteen_c_refresh_manifest_missing")

    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["upstream_18c_refresh_contract_gate"].eq("pass").all() else "fail"


def compare_columns(left: pd.Series, right: pd.Series) -> int:
    if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
        return int((~np.isclose(left.astype(float), right.astype(float), atol=1e-12, rtol=0, equal_nan=True)).sum())
    return int((left.astype(str).fillna("") != right.astype(str).fillna("")).sum())


def build_score_matrix_join_audit(
    config: dict[str, Any],
    resolved: dict[str, Path],
) -> tuple[pd.DataFrame, str, str, pd.DataFrame]:
    expected = config["expected"]
    rows: list[dict[str, Any]] = []
    score_path = resolved["eighteen_c_refresh_score_panel"]
    matrix_path = resolved["eighteen_e_refreshed_matrix"]
    coeff_path = resolved["eighteen_c_refresh_model_coefficients"]
    if not score_path.exists() or not matrix_path.exists() or not coeff_path.exists():
        rows.append(
            {
                "check_id": "required_join_inputs_exist",
                "expected_value": "present",
                "observed_value": "missing",
                "score_matrix_join_gate": "fail",
                "o5_identity_replay_gate": "fail",
                "blocking_reason": "required_join_inputs_missing",
            }
        )
        return pd.DataFrame(rows), "fail", "fail", pd.DataFrame()

    score = read_table(score_path)
    matrix = read_table(matrix_path)
    coeff = read_table(coeff_path)
    full_key = config["full_lineage_key_columns"]
    primary_key = config["primary_identity_key_columns"]
    feature_names = coeff.loc[coeff["model_id"].eq(PRIMARY_MODEL_ID), "feature_name"].astype(str).tolist()
    missing_features = sorted(set(feature_names) - set(matrix.columns))
    score_dup = int(score.duplicated(primary_key).sum())
    matrix_dup = int(matrix.duplicated(primary_key).sum())
    join_cols = list(dict.fromkeys([*full_key, *TARGET_COLUMNS, *feature_names]))
    joined = score.merge(matrix[join_cols], on=full_key, how="outer", indicator=True, suffixes=("_score", ""))
    both = joined["_merge"].eq("both")
    unmatched_score = int(joined["_merge"].eq("left_only").sum())
    unmatched_matrix = int(joined["_merge"].eq("right_only").sum())
    target_mismatch = 0
    for col in ["y_payoff_h20", "continue_advantage", "payoff_ordinal_state", "top30_yes_no", "top20_yes_no", "binary_positive_negative"]:
        left_col = f"{col}_score"
        if left_col in joined.columns and col in joined.columns:
            target_mismatch += compare_columns(joined.loc[both, left_col], joined.loc[both, col])
    o5_formula = np.maximum(joined.loc[both, "defend_advantage"].astype(float), 0.0)
    o5_diff = (joined.loc[both, "o5_incremental"].astype(float) - o5_formula).abs()
    max_o5_diff = float(o5_diff.max()) if len(o5_diff) else np.nan
    o5_mismatch_n = int((o5_diff > float(expected["o5_identity_tolerance"])).sum())

    checks = [
        ("primary_identity_key_columns", "|".join(primary_key), "|".join(primary_key), True, "score_matrix_join_gate"),
        ("full_lineage_key_columns", "|".join(full_key), "|".join(full_key), True, "score_matrix_join_gate"),
        (
            "score_panel_to_18e_matrix_join_type",
            "one_to_one",
            "one_to_one" if score_dup == 0 and matrix_dup == 0 and unmatched_score == 0 and unmatched_matrix == 0 else "not_one_to_one",
            score_dup == 0 and matrix_dup == 0 and unmatched_score == 0 and unmatched_matrix == 0,
            "score_matrix_join_gate",
        ),
        ("primary_identity_score_duplicate_n", 0, score_dup, score_dup == 0, "score_matrix_join_gate"),
        ("primary_identity_matrix_duplicate_n", 0, matrix_dup, matrix_dup == 0, "score_matrix_join_gate"),
        ("joined_row_n", expected["matrix_row_n"], int(both.sum()), int(both.sum()) == int(expected["matrix_row_n"]), "score_matrix_join_gate"),
        ("unmatched_score_panel_row_n", 0, unmatched_score, unmatched_score == 0, "score_matrix_join_gate"),
        ("unmatched_matrix_row_n", 0, unmatched_matrix, unmatched_matrix == 0, "score_matrix_join_gate"),
        ("target_value_mismatch_n", 0, target_mismatch, target_mismatch == 0, "score_matrix_join_gate"),
        ("model_ready_feature_mismatch_n", 0, len(missing_features), len(missing_features) == 0, "score_matrix_join_gate"),
        ("joined_o5_incremental_max_abs_diff", expected["o5_identity_tolerance"], max_o5_diff, max_o5_diff <= float(expected["o5_identity_tolerance"]), "o5_identity_replay_gate"),
        ("joined_o5_incremental_formula_mismatch_n", 0, o5_mismatch_n, o5_mismatch_n == 0, "o5_identity_replay_gate"),
    ]
    for check_id, exp, obs, ok, gate_col in checks:
        rows.append(
            {
                "check_id": check_id,
                "expected_value": exp,
                "observed_value": obs,
                "score_matrix_join_gate": "pass" if ok or gate_col != "score_matrix_join_gate" else "fail",
                "o5_identity_replay_gate": "pass" if ok or gate_col != "o5_identity_replay_gate" else "fail",
                "blocking_reason": "" if ok else f"{check_id}_failed",
            }
        )
    frame = pd.DataFrame(rows)
    join_gate = "pass" if frame.loc[frame["score_matrix_join_gate"].eq("fail")].empty else "fail"
    o5_gate = "pass" if frame.loc[frame["o5_identity_replay_gate"].eq("fail")].empty else "fail"
    clean = joined.loc[both].drop(columns=["_merge"]).copy()
    return frame, join_gate, o5_gate, clean


def build_oracle_reference_replay_audit(config: dict[str, Any], resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    expected = config["expected"]
    path = resolved["eighteen_a_oracle_reference_denominator_map"]
    rows: list[dict[str, Any]] = []

    def add(check_id: str, observed: Any, exp: Any, ok: bool, reason: str | None = None) -> None:
        rows.append(
            {
                "check_id": check_id,
                "observed_value": observed,
                "expected_value": exp,
                "oracle_denominator_contract_gate": "pass" if ok else "fail",
                "blocking_reason": "" if ok else reason or f"{check_id}_failed",
            }
        )

    if not path.exists():
        add("oracle_reference_denominator_map_exists", "missing", "present", False)
        return pd.DataFrame(rows), "fail"
    oracle = read_table(path)
    specs = {
        "O5_perfect_utility_primary": ("labelable_full", "robustness", 2496, expected["o5_mean_incremental_return"], "labelable_full", True),
        "O2_dd_10pct_primary": ("labelable_full", "robustness", 2496, expected["o2_mean_incremental_return"], "labelable_full", True),
        "O4_label_positive_primary": ("binary_primary", "robustness", 1872, expected["o4_binary_primary_mean_incremental_return"], "binary_primary", False),
        "17D_mixed_o5_vs_best_label_path_gap": ("mixed_diagnostic_only", "robustness", np.nan, np.nan, "none", False),
    }
    for oracle_id, (denom, split, row_n, mean_value, allowed, direct) in specs.items():
        found = oracle.loc[oracle["oracle_reference_id"].astype(str).eq(oracle_id)]
        add(f"{oracle_id}_exists", int(len(found)), 1, len(found) == 1)
        if found.empty:
            continue
        row = found.iloc[0]
        add(f"{oracle_id}_denominator_type", row["source_denominator_type"], denom, str(row["source_denominator_type"]) == denom)
        add(f"{oracle_id}_split_bucket", row["split_bucket"], split, str(row["split_bucket"]) == split)
        if np.isfinite(row_n):
            add(f"{oracle_id}_observed_step_n", safe_float(row["observed_step_n"]), row_n, abs(safe_float(row["observed_step_n"]) - float(row_n)) <= 1e-12)
        if np.isfinite(mean_value):
            add(f"{oracle_id}_mean_incremental_return", safe_float(row["mean_incremental_return"]), mean_value, abs(safe_float(row["mean_incremental_return"]) - float(mean_value)) <= 1e-12)
        add(f"{oracle_id}_allowed_bridge_denominator", row["allowed_bridge_denominator"], allowed, str(row["allowed_bridge_denominator"]) == allowed)
        add(f"{oracle_id}_direct_comparison_allowed", bool_like(row["direct_comparison_allowed"]), direct, bool_like(row["direct_comparison_allowed"]) is bool(direct))
        add(f"{oracle_id}_gate", row["oracle_reference_denominator_gate"], "pass", str(row["oracle_reference_denominator_gate"]) == "pass")
    frame = pd.DataFrame(rows)
    return frame, "pass" if frame["oracle_denominator_contract_gate"].eq("pass").all() else "fail"


def action_mask(frame: pd.DataFrame, score_col: str, cutoff: float, action_rule: str) -> pd.Series:
    if action_rule == "defend_bottom":
        return frame[score_col] <= cutoff
    if action_rule == "continue_top":
        return ~(frame[score_col] >= cutoff)
    raise ValueError(f"Unknown action rule: {action_rule}")


def operating_point_actions(config: dict[str, Any], frame: pd.DataFrame, score_col: str = PRIMARY_SCORE_COLUMN) -> dict[str, dict[str, Any]]:
    train = frame.loc[frame["cluster_split_bucket"].eq("train")]
    actions: dict[str, dict[str, Any]] = {}
    for spec in config["operating_points"]:
        cutoff = float(train[score_col].quantile(float(spec["cutoff_quantile"])))
        defend = action_mask(frame, score_col, cutoff, str(spec["action_rule"]))
        actions[str(spec["operating_point_id"])] = {
            **spec,
            "score_col": score_col,
            "cutoff": cutoff,
            "learned_defend_flag": defend.astype(bool),
            "learned_continue_flag": (~defend).astype(bool),
        }
    return actions


def build_score_operating_point_freeze(config: dict[str, Any], frame: pd.DataFrame, actions: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, str]:
    rows = []
    for op_id, spec in actions.items():
        defend = spec["learned_defend_flag"]
        row = {
            "operating_point_id": op_id,
            "score_source_column": spec["score_col"],
            "cutoff_source_split": "train",
            "cutoff_quantile": spec["cutoff_quantile"],
            "train_score_cutoff_value": spec["cutoff"],
            "learned_defend_rule": f"{spec['score_col']} <= train_score_q{int(float(spec['cutoff_quantile']) * 100)}_cutoff"
            if spec["action_rule"] == "defend_bottom"
            else f"{spec['score_col']} < train_score_q{int(float(spec['cutoff_quantile']) * 100)}_cutoff",
            "learned_continue_rule": "not learned_defend_flag",
            "decision_role": spec["decision_role"],
            "split_local_threshold_recompute_used": False,
            "operating_point_freeze_gate": "pass",
            "blocking_reason": "",
        }
        for split in SPLITS:
            split_mask = frame["cluster_split_bucket"].eq(split)
            defended_n = int(defend.loc[split_mask].sum())
            row[f"{split}_defended_n"] = defended_n
            row[f"{split}_defended_rate"] = defended_n / int(split_mask.sum())
        rows.append(row)
    cols = [
        "operating_point_id",
        "score_source_column",
        "cutoff_source_split",
        "cutoff_quantile",
        "train_score_cutoff_value",
        "learned_defend_rule",
        "learned_continue_rule",
        "decision_role",
        "train_defended_n",
        "train_defended_rate",
        "robustness_defended_n",
        "robustness_defended_rate",
        "validation_defended_n",
        "validation_defended_rate",
        "split_local_threshold_recompute_used",
        "operating_point_freeze_gate",
        "blocking_reason",
    ]
    out = pd.DataFrame(rows).loc[:, cols]
    gate = "pass" if out["operating_point_freeze_gate"].eq("pass").all() and (~out["split_local_threshold_recompute_used"].astype(bool)).all() else "fail"
    return out, gate


def denominator_mask(frame: pd.DataFrame, denominator_type: str) -> pd.Series:
    if denominator_type == "labelable_full":
        return pd.Series(True, index=frame.index)
    if denominator_type == "binary_primary":
        return frame["label_class"].isin(["positive", "negative"])
    raise ValueError(f"Unknown denominator_type: {denominator_type}")


def utility_row(
    frame: pd.DataFrame,
    defend_flag: pd.Series,
    split: str,
    denominator_type: str,
    operating_point_id: str,
    decision_role: str,
) -> dict[str, Any]:
    split_frame = frame.loc[frame["cluster_split_bucket"].eq(split)].copy()
    denom = denominator_mask(split_frame, denominator_type)
    sub = split_frame.loc[denom].copy()
    defend = defend_flag.loc[sub.index].astype(bool)
    continue_flag = ~defend
    defend_adv = sub["defend_advantage"].astype(float)
    continue_adv = sub["continue_advantage"].astype(float)
    inc = np.where(defend, defend_adv, 0.0)
    row_n = len(sub)
    positive = sub["label_class"].eq("positive").to_numpy()
    negative = sub["label_class"].eq("negative").to_numpy()
    neutral = sub["label_class"].eq("neutral").to_numpy()
    defended_positive = np.where(defend & positive, defend_adv, 0.0).mean() if row_n else np.nan
    defended_negative = np.where(defend & negative, defend_adv, 0.0).mean() if row_n else np.nan
    defended_neutral = np.where(defend & neutral, defend_adv, 0.0).mean() if row_n else np.nan
    learned_mean = float(np.mean(inc)) if row_n else np.nan
    residual = learned_mean - float(defended_positive + defended_negative + defended_neutral)
    positive_cost = float(np.where(defend & positive, np.maximum(continue_adv, 0.0), 0.0).mean()) if row_n else np.nan
    negative_gain = float(np.where(defend & negative, np.maximum(defend_adv, 0.0), 0.0).mean()) if row_n else np.nan
    neutral_contribution = float(defended_neutral)
    denominator = max(negative_gain + max(neutral_contribution, 0.0), 1e-12)
    top30 = sub["top30_yes_no"].astype(bool)
    top20 = sub["top20_yes_no"].astype(bool)
    top30_count = int(top30.sum())
    top20_count = int(top20.sum())
    defended_n = int(defend.sum())
    row = {
        "split_bucket": split,
        "denominator_type": denominator_type,
        "operating_point_id": operating_point_id,
        "decision_role": decision_role,
        "row_n": row_n,
        "episode_cluster_n": int(sub["episode_cluster_id"].nunique()),
        "defended_n": defended_n,
        "continued_n": int(row_n - defended_n),
        "defended_rate": defended_n / row_n if row_n else np.nan,
        "learned_mean_incremental_return": learned_mean,
        "learned_sum_incremental_return": float(np.sum(inc)),
        "mean_continue_value": float(sub["continue_value"].mean()) if row_n else np.nan,
        "mean_defend_value_on_defended_rows": float(sub.loc[defend, "defend_value"].mean()) if defended_n else np.nan,
        "mean_defend_advantage_on_defended_rows": float(sub.loc[defend, "defend_advantage"].mean()) if defended_n else np.nan,
        "defended_positive_incremental_return": float(defended_positive),
        "defended_negative_incremental_return": float(defended_negative),
        "defended_neutral_incremental_return": float(defended_neutral),
        "residual_reconciliation_term": float(residual),
        "positive_sacrifice_to_avoidance_ratio": positive_cost / denominator if np.isfinite(positive_cost) else np.nan,
        "top30_payoff_retention_rate": float((top30 & continue_flag).sum() / top30_count) if top30_count else np.nan,
        "top20_payoff_retention_rate": float((top20 & continue_flag).sum() / top20_count) if top20_count else np.nan,
        "neutral_row_n": int(neutral.sum()),
        "neutral_contribution_mean": neutral_contribution,
        "utility_bridge_status": "pass" if abs(residual) <= 1e-12 else "fail",
        "blocking_reason": "" if abs(residual) <= 1e-12 else "residual_reconciliation_failed",
        "_positive_opportunity_cost": positive_cost,
        "_negative_avoidance_gain": negative_gain,
        "_continued_negative_leakage": float(np.where(continue_flag & negative, np.maximum(defend_adv, 0.0), 0.0).mean()) if row_n else np.nan,
        "_continued_positive_retained": float(np.where(continue_flag & positive, np.maximum(continue_adv, 0.0), 0.0).mean()) if row_n else np.nan,
    }
    return row


def build_utility_bridge(config: dict[str, Any], frame: pd.DataFrame, actions: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for op_id, spec in actions.items():
        for split in SPLITS:
            rows.append(
                utility_row(
                    frame,
                    spec["learned_defend_flag"],
                    split,
                    "labelable_full",
                    op_id,
                    str(spec["decision_role"]),
                )
            )
    return pd.DataFrame(rows)


def build_six_cell_decomposition(
    frame: pd.DataFrame,
    actions: dict[str, dict[str, Any]],
    utility: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for op_id, spec in actions.items():
        defend_all = spec["learned_defend_flag"].astype(bool)
        for split in SPLITS:
            split_frame = frame.loc[frame["cluster_split_bucket"].eq(split)].copy()
            denom_n = len(split_frame)
            defend = defend_all.loc[split_frame.index]
            for action_name, action_values in {"defended": defend, "continued": ~defend}.items():
                for label in ["positive", "negative", "neutral"]:
                    sub = split_frame.loc[action_values & split_frame["label_class"].eq(label)]
                    inc = sub["defend_advantage"].astype(float) if action_name == "defended" else pd.Series(0.0, index=sub.index)
                    rows.append(
                        {
                            "split_bucket": split,
                            "denominator_type": "labelable_full",
                            "operating_point_id": op_id,
                            "score_action_bucket": action_name,
                            "label_class": label,
                            "row_n": len(sub),
                            "row_share": len(sub) / denom_n if denom_n else np.nan,
                            "mean_y_payoff_h20": float(sub["y_payoff_h20"].mean()) if len(sub) else np.nan,
                            "mean_continue_value": float(sub["continue_value"].mean()) if len(sub) else np.nan,
                            "mean_defend_value": float(sub["defend_value"].mean()) if len(sub) else np.nan,
                            "mean_defend_advantage": float(sub["defend_advantage"].mean()) if len(sub) else np.nan,
                            "sum_incremental_return": float(inc.sum()) if len(sub) else 0.0,
                            "mean_incremental_return_on_full_denominator": float(inc.sum() / denom_n) if denom_n else np.nan,
                            "positive_opportunity_cost": float(np.maximum(sub["continue_advantage"], 0.0).sum() / denom_n) if action_name == "defended" and label == "positive" and denom_n else 0.0,
                            "negative_avoidance_gain": float(np.maximum(sub["defend_advantage"], 0.0).sum() / denom_n) if action_name == "defended" and label == "negative" and denom_n else 0.0,
                            "neutral_contribution": float(sub["defend_advantage"].sum() / denom_n) if action_name == "defended" and label == "neutral" and denom_n else 0.0,
                            "continued_positive_retained": float(np.maximum(sub["continue_advantage"], 0.0).sum() / denom_n) if action_name == "continued" and label == "positive" and denom_n else 0.0,
                            "continued_negative_leakage": float(np.maximum(sub["defend_advantage"], 0.0).sum() / denom_n) if action_name == "continued" and label == "negative" and denom_n else 0.0,
                            "decomposition_status": "pass",
                            "blocking_reason": "",
                        }
                    )
    max_residual = float(utility["residual_reconciliation_term"].abs().max()) if not utility.empty else np.nan
    if np.isfinite(max_residual) and max_residual > 1e-12:
        for row in rows:
            row["decomposition_status"] = "fail"
            row["blocking_reason"] = "utility_residual_reconciliation_failed"
    return pd.DataFrame(rows)


def build_oracle_gap_bridge(config: dict[str, Any], utility: pd.DataFrame) -> pd.DataFrame:
    expected = config["expected"]
    rows = []
    robust = utility.loc[utility["split_bucket"].eq("robustness") & utility["denominator_type"].eq("labelable_full")]
    references = [
        ("O5_perfect_utility_primary", "labelable_full", float(expected["o5_mean_incremental_return"]), True),
        ("O2_dd_10pct_primary", "labelable_full", float(expected["o2_mean_incremental_return"]), True),
    ]
    for _, util in robust.iterrows():
        for oracle_id, oracle_denom, oracle_mean, direct in references:
            learned = float(util["learned_mean_incremental_return"])
            upper = bool(oracle_id.startswith("O5") and learned > oracle_mean + float(expected["o5_tolerance"]))
            rows.append(
                {
                    "split_bucket": "robustness",
                    "denominator_type": "labelable_full",
                    "operating_point_id": util["operating_point_id"],
                    "oracle_reference_id": oracle_id,
                    "oracle_reference_denominator_type": oracle_denom,
                    "oracle_mean_incremental_return": oracle_mean,
                    "learned_mean_incremental_return": learned,
                    "oracle_gap_remaining": oracle_mean - learned,
                    "oracle_approximation_ratio": learned / oracle_mean if abs(oracle_mean) > 1e-15 else np.nan,
                    "oracle_upper_bound_violation": upper,
                    "direct_comparison_allowed": direct,
                    "hard_gate_used": util["operating_point_id"] == PRIMARY_OPERATING_POINT_ID,
                    "oracle_gap_bridge_status": "fail" if upper else "pass",
                    "blocking_reason": "o5_upper_bound_violation" if upper else "",
                }
            )
    return pd.DataFrame(rows)


def build_binary_denominator_bridge(config: dict[str, Any], frame: pd.DataFrame, actions: dict[str, dict[str, Any]]) -> pd.DataFrame:
    expected = config["expected"]
    rows = []
    robust = frame.loc[frame["cluster_split_bucket"].eq("robustness")]
    binary_mask = robust["label_class"].isin(["positive", "negative"])
    binary = robust.loc[binary_mask]
    o4 = float(expected["o4_binary_primary_mean_incremental_return"])
    for op_id, spec in actions.items():
        defend = spec["learned_defend_flag"].loc[binary.index].astype(bool)
        learned = float(np.where(defend, binary["defend_advantage"].astype(float), 0.0).mean()) if len(binary) else np.nan
        rows.append(
            {
                "split_bucket": "robustness",
                "operating_point_id": op_id,
                "binary_denominator_row_n": len(binary),
                "learned_binary_primary_mean_incremental_return": learned,
                "o4_binary_primary_mean_incremental_return": o4,
                "o4_binary_gap_remaining": o4 - learned,
                "o4_binary_approximation_ratio": learned / o4 if abs(o4) > 1e-15 else np.nan,
                "binary_bridge_used_as_primary_gate": False,
                "binary_bridge_role": "appendix_sanity_only",
                "binary_bridge_status": "appendix_sanity_only",
                "blocking_reason": "",
            }
        )
    return pd.DataFrame(rows)


def cluster_bootstrap_ci(
    frame: pd.DataFrame,
    values: pd.Series,
    cluster_col: str,
    resample_n: int,
    seed: int,
    ci_level: float,
) -> tuple[float, float, int]:
    rng = np.random.default_rng(seed)
    clusters = frame[cluster_col].dropna().unique()
    grouped = {
        cluster: values.loc[frame[cluster_col].eq(cluster)].to_numpy(dtype=float)
        for cluster in clusters
    }
    samples = []
    for _ in range(resample_n):
        chosen = rng.choice(clusters, size=len(clusters), replace=True)
        total = 0.0
        count = 0
        for cluster in chosen:
            vals = grouped[cluster]
            total += float(vals.sum())
            count += len(vals)
        if count:
            samples.append(total / count)
    valid = np.array([v for v in samples if np.isfinite(v)], dtype=float)
    if len(valid) == 0:
        return np.nan, np.nan, 0
    alpha = (1.0 - ci_level) / 2.0
    return float(np.quantile(valid, alpha)), float(np.quantile(valid, 1.0 - alpha)), int(len(valid))


def build_cluster_bootstrap_utility_bridge(
    config: dict[str, Any],
    robust: pd.DataFrame,
    primary_inc: pd.Series,
    ci_low: float,
    ci_high: float,
    valid_n: int,
) -> pd.DataFrame:
    expected = config["expected"]
    resample_n = int(expected["bootstrap_resample_n"])
    ok = valid_n == resample_n and np.isfinite(ci_low) and ci_low > 0
    return pd.DataFrame(
        [
            {
                "split_bucket": "robustness",
                "denominator_type": "labelable_full",
                "operating_point_id": PRIMARY_OPERATING_POINT_ID,
                "cluster_key": "episode_cluster_id",
                "metric_id": "learned_mean_incremental_return",
                "row_n": int(len(robust)),
                "episode_cluster_n": int(robust["episode_cluster_id"].nunique()) if not robust.empty else 0,
                "learned_mean_incremental_return": float(primary_inc.mean()) if len(primary_inc) else np.nan,
                "cluster_bootstrap_utility_ci_low": ci_low,
                "cluster_bootstrap_utility_ci_high": ci_high,
                "bootstrap_resample_n": resample_n,
                "valid_bootstrap_resample_n": int(valid_n),
                "bootstrap_random_seed": int(expected["bootstrap_random_seed"]),
                "ci_level": float(expected["bootstrap_ci_level"]),
                "cluster_bootstrap_utility_status": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "cluster_bootstrap_utility_ci_low_not_positive",
            }
        ]
    )


def sensitivity_score(frame: pd.DataFrame, coeff: pd.DataFrame, removed_features: list[str]) -> pd.Series:
    out = frame[PRIMARY_SCORE_COLUMN].astype(float).copy()
    primary = coeff.loc[coeff["model_id"].eq(PRIMARY_MODEL_ID)].set_index("feature_name")
    for feature in removed_features:
        out = out - frame[feature].astype(float) * float(primary.loc[feature, "coefficient"])
    return out


def build_topk_bootstrap_utility_bridge(
    config: dict[str, Any],
    frame: pd.DataFrame,
    coeff: pd.DataFrame,
    topk_source: pd.DataFrame,
    family_source: pd.DataFrame,
    base_utility: pd.DataFrame,
) -> pd.DataFrame:
    expected = config["expected"]
    required_topk = config["sensitivity_required_ids"]["topk"]
    required_family = config["sensitivity_required_ids"]["family"]
    base = base_utility.loc[
        base_utility["split_bucket"].eq("robustness")
        & base_utility["denominator_type"].eq("labelable_full")
        & base_utility["operating_point_id"].eq(PRIMARY_OPERATING_POINT_ID)
    ].iloc[0]
    base_mean = float(base["learned_mean_incremental_return"])
    rows = []
    source_rows = []
    source_rows.extend(topk_source.loc[topk_source["split_bucket"].eq("robustness") & topk_source["sensitivity_id"].isin(required_topk)].to_dict(orient="records"))
    source_rows.extend(family_source.loc[family_source["split_bucket"].eq("robustness") & family_source["sensitivity_id"].isin(required_family)].to_dict(orient="records"))
    for src in source_rows:
        removed = [name for name in str(src["removed_feature_names"]).split("|") if name]
        sens_col = "_sensitivity_score"
        temp = frame.copy()
        temp[sens_col] = sensitivity_score(temp, coeff, removed)
        actions = operating_point_actions(
            {**config, "operating_points": [op for op in config["operating_points"] if op["operating_point_id"] == PRIMARY_OPERATING_POINT_ID]},
            temp,
            sens_col,
        )
        defend = actions[PRIMARY_OPERATING_POINT_ID]["learned_defend_flag"]
        util = utility_row(temp, defend, "robustness", "labelable_full", PRIMARY_OPERATING_POINT_ID, "primary")
        robust = temp.loc[temp["cluster_split_bucket"].eq("robustness")]
        inc = pd.Series(np.where(defend.loc[robust.index], robust["defend_advantage"].astype(float), 0.0), index=robust.index)
        ci_low, ci_high, valid_n = cluster_bootstrap_ci(
            robust,
            inc,
            "episode_cluster_id",
            int(expected["bootstrap_resample_n"]),
            int(expected["bootstrap_random_seed"]),
            float(expected["bootstrap_ci_level"]),
        )
        sens_mean = float(util["learned_mean_incremental_return"])
        retention = sens_mean / base_mean if np.isfinite(base_mean) and base_mean > 0 else np.nan
        status_ok = (
            np.isfinite(sens_mean)
            and valid_n == int(expected["bootstrap_resample_n"])
            and np.isfinite(retention)
        )
        blocking_reason = ""
        if not np.isfinite(retention):
            blocking_reason = "base_learned_utility_nonpositive"
        elif not status_ok:
            blocking_reason = "sensitivity_utility_not_evaluable"
        rows.append(
            {
                "sensitivity_id": src["sensitivity_id"],
                "split_bucket": "robustness",
                "denominator_type": "labelable_full",
                "operating_point_id": PRIMARY_OPERATING_POINT_ID,
                "removed_feature_n": int(src["removed_feature_n"]),
                "removed_feature_names": src["removed_feature_names"],
                "removed_feature_family_id": src.get("removed_feature_family_id", "mixed"),
                "base_learned_mean_incremental_return": base_mean,
                "sensitivity_learned_mean_incremental_return": sens_mean,
                "learned_utility_retention_rate": retention,
                "cluster_bootstrap_utility_ci_low": ci_low,
                "cluster_bootstrap_utility_ci_high": ci_high,
                "bootstrap_resample_n": int(expected["bootstrap_resample_n"]),
                "valid_bootstrap_resample_n": valid_n,
                "topk_bootstrap_status": "pass" if status_ok else "not_evaluable",
                "blocking_reason": blocking_reason,
            }
        )
    return pd.DataFrame(rows)


def build_validation_stress_utility_bridge(config: dict[str, Any], utility: pd.DataFrame) -> pd.DataFrame:
    expected = config["expected"]
    primary = utility.loc[
        utility["operating_point_id"].eq(PRIMARY_OPERATING_POINT_ID)
        & utility["split_bucket"].eq("robustness")
        & utility["denominator_type"].eq("labelable_full")
    ].iloc[0]
    validation = utility.loc[
        utility["operating_point_id"].eq(PRIMARY_OPERATING_POINT_ID)
        & utility["split_bucket"].eq("validation")
        & utility["denominator_type"].eq("labelable_full")
    ].iloc[0]
    val_mean = float(validation["learned_mean_incremental_return"])
    o5 = float(expected["o5_mean_incremental_return"])
    sign_reversal = bool(float(primary["learned_mean_incremental_return"]) > 0 and val_mean < 0)
    ok = (
        val_mean >= 0
        and float(validation["top30_payoff_retention_rate"]) >= float(expected["validation_top30_payoff_retention_floor"])
        and float(validation["top20_payoff_retention_rate"]) >= float(expected["validation_top20_payoff_retention_floor"])
        and not sign_reversal
    )
    return pd.DataFrame(
        [
            {
                "operating_point_id": PRIMARY_OPERATING_POINT_ID,
                "validation_row_n": int(validation["row_n"]),
                "validation_episode_cluster_n": int(validation["episode_cluster_n"]),
                "validation_learned_mean_incremental_return": val_mean,
                "validation_o5_approximation_ratio": val_mean / o5,
                "validation_top30_payoff_retention_rate": float(validation["top30_payoff_retention_rate"]),
                "validation_top20_payoff_retention_rate": float(validation["top20_payoff_retention_rate"]),
                "validation_utility_sign_reversal": sign_reversal,
                "validation_stress_role": "stress_readout_only",
                "validation_stress_status": "pass" if ok else "fail",
                "blocking_reason": "" if ok else "validation_stress_gate_failed",
            }
        ]
    )


def build_search_accounting_audit(config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    row = {
        "search_family": "18F_payoff_state_oracle_gap_bridge",
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "scope_id": config.get("scope_id", "refreshed_matrix_oracle_gap_bridge"),
        "primary_operating_point_predeclared": True,
        "no_model_training": True,
        "no_model_refit": True,
        "no_feature_selection_from_utility": True,
        "no_feature_selection_from_robustness": True,
        "no_feature_selection_from_validation": True,
        "no_threshold_tuning_on_robustness": True,
        "no_threshold_tuning_on_validation": True,
        "no_oracle_reference_selection_from_results": True,
        "no_binary_metric_primary_gate": True,
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


def primary_metrics(
    config: dict[str, Any],
    utility: pd.DataFrame,
    oracle_gap: pd.DataFrame,
    topk: pd.DataFrame,
    validation: pd.DataFrame,
    bootstrap_ci_low: float,
) -> dict[str, Any]:
    expected = config["expected"]
    primary = utility.loc[
        utility["split_bucket"].eq("robustness")
        & utility["denominator_type"].eq("labelable_full")
        & utility["operating_point_id"].eq(PRIMARY_OPERATING_POINT_ID)
    ].iloc[0]
    o5_row = oracle_gap.loc[
        oracle_gap["operating_point_id"].eq(PRIMARY_OPERATING_POINT_ID)
        & oracle_gap["oracle_reference_id"].eq("O5_perfect_utility_primary")
    ].iloc[0]
    o2_row = oracle_gap.loc[
        oracle_gap["operating_point_id"].eq(PRIMARY_OPERATING_POINT_ID)
        & oracle_gap["oracle_reference_id"].eq("O2_dd_10pct_primary")
    ].iloc[0]
    top5 = topk.loc[topk["sensitivity_id"].eq("top5_abs_coefficient_removed")]
    f4 = topk.loc[topk["sensitivity_id"].eq("family_F4_removed")]
    return {
        "learned_mean": float(primary["learned_mean_incremental_return"]),
        "o5_approximation_ratio": float(o5_row["oracle_approximation_ratio"]),
        "o2_approximation_ratio": float(o2_row["oracle_approximation_ratio"]),
        "o5_gap_remaining": float(o5_row["oracle_gap_remaining"]),
        "o5_upper_bound_violation": bool(o5_row["oracle_upper_bound_violation"]),
        "positive_sacrifice_to_avoidance_ratio": float(primary["positive_sacrifice_to_avoidance_ratio"]),
        "positive_opportunity_cost": float(primary["_positive_opportunity_cost"]),
        "negative_avoidance_gain": float(primary["_negative_avoidance_gain"]),
        "neutral_contribution": float(primary["neutral_contribution_mean"]),
        "top30_payoff_retention_rate": float(primary["top30_payoff_retention_rate"]),
        "top20_payoff_retention_rate": float(primary["top20_payoff_retention_rate"]),
        "top5_retention": float(top5["learned_utility_retention_rate"].iloc[0]) if not top5.empty else np.nan,
        "f4_retention": float(f4["learned_utility_retention_rate"].iloc[0]) if not f4.empty else np.nan,
        "bootstrap_ci_low": bootstrap_ci_low,
        "validation_status": str(validation["validation_stress_status"].iloc[0]),
        "neutral_counts_ok": {
            "train": int(utility.loc[utility["split_bucket"].eq("train") & utility["operating_point_id"].eq(PRIMARY_OPERATING_POINT_ID), "neutral_row_n"].iloc[0]) == int(expected["train_neutral_row_n"]),
            "robustness": int(primary["neutral_row_n"]) == int(expected["robustness_neutral_row_n"]),
            "validation": int(utility.loc[utility["split_bucket"].eq("validation") & utility["operating_point_id"].eq(PRIMARY_OPERATING_POINT_ID), "neutral_row_n"].iloc[0]) == int(expected["validation_neutral_row_n"]),
        },
        "max_residual_abs": float(utility["residual_reconciliation_term"].abs().max()),
    }


def build_decision(config: dict[str, Any], gates: dict[str, str], metrics: dict[str, Any]) -> pd.DataFrame:
    all_pass = all(gates.get(gate) == "pass" for gate in HARD_GATES)
    decision = "18F_payoff_state_policy_preflight_allowed"
    next_req = config["expected"]["positive_next_allowed_requirement"]
    next_scope = config["expected"]["positive_next_allowed_requirement_scope"]
    if not all_pass:
        next_req = "none"
        next_scope = "none"
        if gates.get("upstream_18c_refresh_contract_gate") != "pass":
            decision = "18F_upstream_18c_refresh_contract_blocked"
        elif gates.get("input_artifact_gate") != "pass":
            decision = "18F_input_artifact_blocked"
        elif gates.get("score_matrix_join_gate") != "pass":
            decision = "18F_score_matrix_join_blocked"
        elif (
            gates.get("oracle_denominator_contract_gate") != "pass"
            or gates.get("o5_identity_replay_gate") != "pass"
            or gates.get("o5_upper_bound_contract_gate") != "pass"
            or gates.get("binary_boundary_gate") != "pass"
        ):
            decision = "18F_oracle_gap_contract_blocked"
        elif gates.get("operating_point_freeze_gate") != "pass":
            decision = "18F_oracle_gap_contract_blocked"
        elif gates.get("search_accounting_gate") != "pass":
            decision = "18F_search_accounting_blocked"
        elif gates.get("learned_utility_support_gate") != "pass":
            decision = "18F_utility_bridge_not_supported"
        elif gates.get("oracle_gap_reduction_gate") != "pass":
            decision = "18F_oracle_gap_not_reduced"
        elif gates.get("positive_sacrifice_gate") != "pass" or gates.get("payoff_retention_gate") != "pass":
            decision = "18F_over_narrow_winner_bridge_blocked"
        elif (
            gates.get("cluster_bootstrap_utility_gate") != "pass"
            or gates.get("topk_sensitivity_gate") != "pass"
            or gates.get("validation_stress_gate") != "pass"
        ):
            decision = "18F_payoff_state_representation_diagnostic_only"
        else:
            decision = "18F_unclassified_oracle_gap_bridge_blocked"
    row = {
        "decision_state": decision,
        "next_allowed_requirement": next_req,
        "next_allowed_requirement_scope": next_scope,
        "all_hard_gates_pass": all_pass,
        **{gate: gates.get(gate, "fail") for gate in HARD_GATES},
        "primary_operating_point_id": PRIMARY_OPERATING_POINT_ID,
        "primary_labelable_full_learned_mean_incremental_return": metrics.get("learned_mean", np.nan),
        "primary_o5_approximation_ratio": metrics.get("o5_approximation_ratio", np.nan),
        "primary_o2_approximation_ratio": metrics.get("o2_approximation_ratio", np.nan),
        "primary_o5_gap_remaining": metrics.get("o5_gap_remaining", np.nan),
        "primary_o5_upper_bound_violation": bool(metrics.get("o5_upper_bound_violation", False)),
        "primary_positive_sacrifice_to_avoidance_ratio": metrics.get("positive_sacrifice_to_avoidance_ratio", np.nan),
        "primary_top30_payoff_retention_rate": metrics.get("top30_payoff_retention_rate", np.nan),
        "primary_top20_payoff_retention_rate": metrics.get("top20_payoff_retention_rate", np.nan),
        "primary_cluster_bootstrap_utility_ci_low": metrics.get("bootstrap_ci_low", np.nan),
        "primary_cluster_bootstrap_utility_ci_high": metrics.get("bootstrap_ci_high", np.nan),
        "primary_cluster_bootstrap_valid_resample_n": metrics.get("bootstrap_valid_resample_n", np.nan),
        "validation_stress_evaluable": True,
        "validation_stress_caveat": "stress_readout_only",
        **{col: False for col in AUTH_FALSE_COLUMNS},
        "blocking_reason": "" if all_pass else decision,
    }
    return pd.DataFrame([row])


def build_gates(
    config: dict[str, Any],
    upstream_gate: str,
    input_gate: str,
    join_gate: str,
    oracle_gate: str,
    o5_identity_gate: str,
    operating_gate: str,
    search_gate: str,
    metrics: dict[str, Any],
    topk: pd.DataFrame,
    validation: pd.DataFrame,
    binary: pd.DataFrame,
) -> dict[str, str]:
    expected = config["expected"]
    learned = float(metrics["learned_mean"])
    ratio_floor = float(expected["approximation_ratio_floor"])
    o5_ratio = float(metrics["o5_approximation_ratio"])
    o2_ratio = float(metrics["o2_approximation_ratio"])
    positive_sacrifice_ok = (
        float(metrics["positive_sacrifice_to_avoidance_ratio"]) < float(expected["positive_sacrifice_ratio_ceiling"])
        and float(metrics["positive_opportunity_cost"])
        < float(metrics["negative_avoidance_gain"]) + max(float(metrics["neutral_contribution"]), 0.0)
    )
    payoff_retention_ok = (
        float(metrics["top30_payoff_retention_rate"]) >= float(expected["top30_payoff_retention_floor"])
        and float(metrics["top20_payoff_retention_rate"]) >= float(expected["top20_payoff_retention_floor"])
    )
    top5_ok = np.isfinite(metrics["top5_retention"]) and float(metrics["top5_retention"]) >= float(expected["sensitivity_retention_floor"])
    f4_ok = np.isfinite(metrics["f4_retention"]) and float(metrics["f4_retention"]) >= float(expected["sensitivity_retention_floor"])
    return {
        "upstream_18c_refresh_contract_gate": upstream_gate,
        "input_artifact_gate": input_gate,
        "score_matrix_join_gate": join_gate,
        "oracle_denominator_contract_gate": oracle_gate,
        "o5_identity_replay_gate": o5_identity_gate,
        "o5_upper_bound_contract_gate": gate_from_bool(not bool(metrics["o5_upper_bound_violation"])),
        "operating_point_freeze_gate": operating_gate,
        "learned_utility_support_gate": gate_from_bool(learned > 0),
        "oracle_gap_reduction_gate": gate_from_bool(learned > 0 and o5_ratio >= ratio_floor and o2_ratio >= ratio_floor),
        "positive_sacrifice_gate": gate_from_bool(positive_sacrifice_ok),
        "payoff_retention_gate": gate_from_bool(payoff_retention_ok),
        "neutral_reconciliation_gate": gate_from_bool(all(metrics["neutral_counts_ok"].values()) and float(metrics["max_residual_abs"]) <= float(expected["utility_decomposition_tolerance"])),
        "cluster_bootstrap_utility_gate": gate_from_bool(
            np.isfinite(metrics["bootstrap_ci_low"])
            and float(metrics["bootstrap_ci_low"]) > 0
        ),
        "topk_sensitivity_gate": gate_from_bool(top5_ok and f4_ok and topk["topk_bootstrap_status"].eq("pass").all()),
        "validation_stress_gate": gate_from_bool(validation["validation_stress_status"].eq("pass").all()),
        "binary_boundary_gate": gate_from_bool((~binary["binary_bridge_used_as_primary_gate"].astype(bool)).all()),
        "search_accounting_gate": search_gate,
    }


def build_all_artifacts(
    config: dict[str, Any],
    resolved: dict[str, Path],
    joined: pd.DataFrame,
    upstream_gate: str,
    input_gate: str,
    join_gate: str,
    oracle_gate: str,
    o5_identity_gate: str,
) -> dict[str, Any]:
    coeff = read_table(resolved["eighteen_c_refresh_model_coefficients"])
    topk_source = read_table(resolved["eighteen_c_refresh_topk_sensitivity"])
    family_source = read_table(resolved["eighteen_c_refresh_family_sensitivity"])
    actions = operating_point_actions(config, joined)
    freeze, operating_gate = build_score_operating_point_freeze(config, joined, actions)
    utility = build_utility_bridge(config, joined, actions)
    decomposition = build_six_cell_decomposition(joined, actions, utility)
    oracle_gap = build_oracle_gap_bridge(config, utility)
    binary = build_binary_denominator_bridge(config, joined, actions)
    search, search_gate = build_search_accounting_audit(config)
    primary_action = actions[PRIMARY_OPERATING_POINT_ID]["learned_defend_flag"]
    robust = joined.loc[joined["cluster_split_bucket"].eq("robustness")]
    primary_inc = pd.Series(np.where(primary_action.loc[robust.index], robust["defend_advantage"].astype(float), 0.0), index=robust.index)
    ci_low, ci_high, valid_n = cluster_bootstrap_ci(
        robust,
        primary_inc,
        "episode_cluster_id",
        int(config["expected"]["bootstrap_resample_n"]),
        int(config["expected"]["bootstrap_random_seed"]),
        float(config["expected"]["bootstrap_ci_level"]),
    )
    cluster_bootstrap = build_cluster_bootstrap_utility_bridge(config, robust, primary_inc, ci_low, ci_high, valid_n)
    topk = build_topk_bootstrap_utility_bridge(config, joined, coeff, topk_source, family_source, utility)
    validation = build_validation_stress_utility_bridge(config, utility)
    metrics = primary_metrics(config, utility, oracle_gap, topk, validation, ci_low)
    metrics["bootstrap_ci_high"] = ci_high
    metrics["bootstrap_valid_resample_n"] = valid_n
    gates = build_gates(
        config,
        upstream_gate,
        input_gate,
        join_gate,
        oracle_gate,
        o5_identity_gate,
        operating_gate,
        search_gate,
        metrics,
        topk,
        validation,
        binary,
    )
    decision = build_decision(config, gates, metrics)
    return {
        "score_operating_point_freeze": freeze,
        "learned_payoff_state_utility_bridge": utility.loc[:, UTILITY_COLUMNS],
        "oracle_gap_bridge": oracle_gap,
        "payoff_state_six_cell_decomposition": decomposition,
        "binary_denominator_bridge": binary,
        "cluster_bootstrap_utility_bridge": cluster_bootstrap,
        "topk_bootstrap_utility_bridge": topk,
        "validation_stress_utility_bridge": validation,
        "search_accounting_audit": search,
        "decision": decision,
        "gates": gates,
        "metrics": metrics,
        "joined": joined,
    }


def empty_outputs(decision: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "score_operating_point_freeze": pd.DataFrame(
            columns=[
                "operating_point_id",
                "score_source_column",
                "cutoff_source_split",
                "cutoff_quantile",
                "train_score_cutoff_value",
                "learned_defend_rule",
                "learned_continue_rule",
                "decision_role",
                "train_defended_n",
                "train_defended_rate",
                "robustness_defended_n",
                "robustness_defended_rate",
                "validation_defended_n",
                "validation_defended_rate",
                "split_local_threshold_recompute_used",
                "operating_point_freeze_gate",
                "blocking_reason",
            ]
        ),
        "learned_payoff_state_utility_bridge": pd.DataFrame(columns=UTILITY_COLUMNS),
        "oracle_gap_bridge": pd.DataFrame(
            columns=[
                "split_bucket",
                "denominator_type",
                "operating_point_id",
                "oracle_reference_id",
                "oracle_reference_denominator_type",
                "oracle_mean_incremental_return",
                "learned_mean_incremental_return",
                "oracle_gap_remaining",
                "oracle_approximation_ratio",
                "oracle_upper_bound_violation",
                "direct_comparison_allowed",
                "hard_gate_used",
                "oracle_gap_bridge_status",
                "blocking_reason",
            ]
        ),
        "payoff_state_six_cell_decomposition": pd.DataFrame(),
        "binary_denominator_bridge": pd.DataFrame(),
        "cluster_bootstrap_utility_bridge": pd.DataFrame(
            columns=[
                "split_bucket",
                "denominator_type",
                "operating_point_id",
                "cluster_key",
                "metric_id",
                "row_n",
                "episode_cluster_n",
                "learned_mean_incremental_return",
                "cluster_bootstrap_utility_ci_low",
                "cluster_bootstrap_utility_ci_high",
                "bootstrap_resample_n",
                "valid_bootstrap_resample_n",
                "bootstrap_random_seed",
                "ci_level",
                "cluster_bootstrap_utility_status",
                "blocking_reason",
            ]
        ),
        "topk_bootstrap_utility_bridge": pd.DataFrame(),
        "validation_stress_utility_bridge": pd.DataFrame(),
        "search_accounting_audit": pd.DataFrame(),
        "decision": decision,
    }


def build_fail_closed_decision(config: dict[str, Any], gates: dict[str, str]) -> pd.DataFrame:
    metrics = {
        "learned_mean": np.nan,
        "o5_approximation_ratio": np.nan,
        "o2_approximation_ratio": np.nan,
        "o5_gap_remaining": np.nan,
        "o5_upper_bound_violation": False,
        "positive_sacrifice_to_avoidance_ratio": np.nan,
        "top30_payoff_retention_rate": np.nan,
        "top20_payoff_retention_rate": np.nan,
    }
    return build_decision(config, gates, metrics)


def to_markdown_or_message(frame: pd.DataFrame, message: str, columns: list[str] | None = None) -> str:
    if frame.empty:
        return message
    out = frame.copy()
    if columns is not None:
        out = out.loc[:, [col for col in columns if col in out.columns]]
    return out.to_markdown(index=False)


def build_report(
    decision: pd.DataFrame,
    input_audit: pd.DataFrame,
    upstream: pd.DataFrame,
    join_audit: pd.DataFrame,
    oracle_audit: pd.DataFrame,
    artifacts: dict[str, Any],
) -> str:
    d = decision.iloc[0]
    gates = pd.DataFrame({"gate": list(HARD_GATES), "status": [d[gate] for gate in HARD_GATES]})
    auth = pd.DataFrame(
        {
            "authorization_flag": list(AUTH_FALSE_COLUMNS),
            "authorized": [bool(d[col]) for col in AUTH_FALSE_COLUMNS],
        }
    )
    utility = artifacts.get("learned_payoff_state_utility_bridge", pd.DataFrame())
    primary = (
        utility.loc[
            utility.get("operating_point_id", pd.Series(dtype=str)).eq(PRIMARY_OPERATING_POINT_ID)
            & utility.get("denominator_type", pd.Series(dtype=str)).eq("labelable_full")
        ]
        if not utility.empty
        else pd.DataFrame()
    )
    freeze = artifacts.get("score_operating_point_freeze", pd.DataFrame())
    oracle_gap = artifacts.get("oracle_gap_bridge", pd.DataFrame())
    primary_oracle_gap = (
        oracle_gap.loc[oracle_gap.get("operating_point_id", pd.Series(dtype=str)).eq(PRIMARY_OPERATING_POINT_ID)]
        if not oracle_gap.empty
        else pd.DataFrame()
    )
    decomposition = artifacts.get("payoff_state_six_cell_decomposition", pd.DataFrame())
    primary_decomposition = (
        decomposition.loc[
            decomposition.get("operating_point_id", pd.Series(dtype=str)).eq(PRIMARY_OPERATING_POINT_ID)
            & decomposition.get("denominator_type", pd.Series(dtype=str)).eq("labelable_full")
        ]
        if not decomposition.empty
        else pd.DataFrame()
    )
    cluster_bootstrap = artifacts.get("cluster_bootstrap_utility_bridge", pd.DataFrame())
    topk = artifacts.get("topk_bootstrap_utility_bridge", pd.DataFrame())
    validation = artifacts.get("validation_stress_utility_bridge", pd.DataFrame())
    binary = artifacts.get("binary_denominator_bridge", pd.DataFrame())
    return f"""# 18F Payoff-state Oracle Gap Bridge Report

## Decision

decision_state = {d["decision_state"]}
next_allowed_requirement = {d["next_allowed_requirement"]}
next_allowed_requirement_scope = {d["next_allowed_requirement_scope"]}

18F is not a policy, not a backtest, and not a production signal.

## Policy Authorization Flags

{auth.to_markdown(index=False)}

## Gate Summary

{gates.to_markdown(index=False)}

## Input Artifact Audit

{input_audit.groupby(["read_status", "schema_status", "cache_key_reconciliation_gate"], dropna=False).size().reset_index(name="artifact_n").to_markdown(index=False)}

## 18C Refresh Handoff

{upstream.to_markdown(index=False)}

## Score Matrix Join And Oracle Replay

{join_audit.to_markdown(index=False)}

{oracle_audit.to_markdown(index=False)}

## Train-Frozen Operating Points

{to_markdown_or_message(freeze, "Operating points not evaluated.")}

## Learned Labelable Full Utility

{to_markdown_or_message(primary, "Primary utility not evaluated.")}

## O5 And O2 Oracle Gap

{to_markdown_or_message(primary_oracle_gap, "Oracle gap bridge not evaluated.", ["split_bucket", "denominator_type", "operating_point_id", "oracle_reference_id", "oracle_mean_incremental_return", "learned_mean_incremental_return", "oracle_gap_remaining", "oracle_approximation_ratio", "oracle_upper_bound_violation", "hard_gate_used", "oracle_gap_bridge_status", "blocking_reason"])}

## Direct Incremental-Return Decomposition

{to_markdown_or_message(primary_decomposition, "Six-cell decomposition not evaluated.", ["split_bucket", "denominator_type", "operating_point_id", "score_action_bucket", "label_class", "row_n", "row_share", "sum_incremental_return", "mean_incremental_return_on_full_denominator", "positive_opportunity_cost", "negative_avoidance_gain", "neutral_contribution", "continued_positive_retained", "continued_negative_leakage", "decomposition_status", "blocking_reason"])}

## Cluster Bootstrap Utility CI

{to_markdown_or_message(cluster_bootstrap, "Cluster bootstrap utility not evaluated.")}

## Sensitivity Utility

{to_markdown_or_message(topk, "Sensitivity utility not evaluated.")}

## Validation Stress

{to_markdown_or_message(validation, "Validation stress not evaluated.")}

## Binary Appendix

{to_markdown_or_message(binary, "Binary bridge not evaluated.")}

## AFML Interpretation

The refreshed 18C score is evaluated here as an action-value utility mask rather
than as a ranking-only representation. A positive decision would only authorize
a later policy preflight. In this run, the primary train-frozen operating point
must clear labelable_full utility before any policy work can proceed.
"""


def build_figures(artifacts: dict[str, Any], outputs: dict[str, Path]) -> None:
    oracle = artifacts.get("oracle_gap_bridge", pd.DataFrame())
    utility = artifacts.get("learned_payoff_state_utility_bridge", pd.DataFrame())
    outputs["oracle_gap_bridge_curve"].parent.mkdir(parents=True, exist_ok=True)
    if oracle.empty:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.text(0.5, 0.5, "Oracle gap bridge not evaluated", ha="center", va="center")
        ax.axis("off")
    else:
        o5 = oracle.loc[oracle["oracle_reference_id"].eq("O5_perfect_utility_primary")].copy()
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(o5["operating_point_id"], o5["learned_mean_incremental_return"], marker="o", label="learned")
        ax.axhline(o5["oracle_mean_incremental_return"].iloc[0], color="tab:green", linestyle="--", label="O5")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_ylabel("mean incremental return")
        ax.set_title("18F labelable_full oracle gap bridge")
        ax.tick_params(axis="x", rotation=35)
        ax.legend()
    fig.tight_layout()
    fig.savefig(outputs["oracle_gap_bridge_curve"], dpi=140)
    plt.close(fig)

    if utility.empty:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.text(0.5, 0.5, "Positive sacrifice not evaluated", ha="center", va="center")
        ax.axis("off")
    else:
        robust = utility.loc[utility["split_bucket"].eq("robustness")].copy()
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.scatter(robust["positive_sacrifice_to_avoidance_ratio"], robust["top30_payoff_retention_rate"])
        for _, row in robust.iterrows():
            ax.annotate(str(row["operating_point_id"]).replace("_continue_rest", ""), (row["positive_sacrifice_to_avoidance_ratio"], row["top30_payoff_retention_rate"]), fontsize=7)
        ax.axvline(1.0, color="tab:red", linestyle="--")
        ax.axhline(0.70, color="tab:green", linestyle="--")
        ax.set_xlabel("positive sacrifice / avoidance")
        ax.set_ylabel("top30 payoff retention")
        ax.set_title("18F sacrifice vs payoff preservation")
    fig.tight_layout()
    fig.savefig(outputs["positive_sacrifice_vs_payoff_preservation"], dpi=140)
    plt.close(fig)


def write_all_outputs(
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
    upstream: pd.DataFrame,
    join_audit: pd.DataFrame,
    oracle_audit: pd.DataFrame,
    artifacts: dict[str, Any],
) -> None:
    write_df(outputs["input_artifact_audit"], input_audit)
    write_df(outputs["upstream_18c_refresh_handoff_audit"], upstream)
    write_df(outputs["score_matrix_join_audit"], join_audit)
    write_df(outputs["oracle_reference_replay_audit"], oracle_audit)
    for key in [
        "score_operating_point_freeze",
        "learned_payoff_state_utility_bridge",
        "oracle_gap_bridge",
        "payoff_state_six_cell_decomposition",
        "binary_denominator_bridge",
        "cluster_bootstrap_utility_bridge",
        "topk_bootstrap_utility_bridge",
        "validation_stress_utility_bridge",
        "search_accounting_audit",
        "decision",
    ]:
        write_df(outputs[key], artifacts[key])
    build_figures(artifacts, outputs)
    write_text(outputs["report"], build_report(artifacts["decision"], input_audit, upstream, join_audit, oracle_audit, artifacts))
    write_manifests(config, resolved, outputs, input_audit, artifacts["decision"])


def write_manifests(
    config: dict[str, Any],
    resolved: dict[str, Path],
    outputs: dict[str, Path],
    input_audit: pd.DataFrame,
    decision: pd.DataFrame,
) -> None:
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
    d = decision.iloc[0]
    table_keys = [
        "input_artifact_audit",
        "upstream_18c_refresh_handoff_audit",
        "score_matrix_join_audit",
        "oracle_reference_replay_audit",
        "score_operating_point_freeze",
        "learned_payoff_state_utility_bridge",
        "oracle_gap_bridge",
        "payoff_state_six_cell_decomposition",
        "binary_denominator_bridge",
        "cluster_bootstrap_utility_bridge",
        "topk_bootstrap_utility_bridge",
        "validation_stress_utility_bridge",
        "search_accounting_audit",
        "decision",
    ]
    figure_keys = ["oracle_gap_bridge_curve", "positive_sacrifice_vs_payoff_preservation"]
    write_json(
        outputs["manifest"],
        {
            "run_id": RUN_ID,
            "phase_id": PHASE_ID,
            "experiment_id": EXPERIMENT_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "requirement_file_sha256": file_sha(EXPERIMENT_DIR / "requirement_18f_payoff_state_oracle_gap_bridge.md"),
            "config_file_sha256": file_sha(CONFIG_PATH),
            "runner_file_sha256": file_sha(Path(__file__)),
            "input_artifact_manifest_sha256": file_sha(outputs["input_manifest"]),
            "source_18c_refresh_manifest_sha256": file_sha(resolved["eighteen_c_refresh_manifest"]) if resolved["eighteen_c_refresh_manifest"].exists() else "",
            "source_18c_score_panel_sha256": file_sha(resolved["eighteen_c_refresh_score_panel"]) if resolved["eighteen_c_refresh_score_panel"].exists() else "",
            "source_18e_matrix_sha256": file_sha(resolved["eighteen_e_refreshed_matrix"]) if resolved["eighteen_e_refreshed_matrix"].exists() else "",
            "source_18a_target_contract_manifest_sha256": file_sha(resolved["eighteen_a_target_contract_manifest"]) if resolved["eighteen_a_target_contract_manifest"].exists() else "",
            "publishable_table_sha256_by_name": {key: file_sha(outputs[key]) for key in table_keys if outputs[key].exists()},
            "publishable_figure_sha256_by_name": {key: file_sha(outputs[key]) for key in figure_keys if outputs[key].exists()},
            "report_sha256": file_sha(outputs["report"]) if outputs["report"].exists() else "",
            "output_hashes": {key: file_sha(outputs[key]) for key in [*table_keys, *figure_keys, "report", "input_manifest"] if outputs[key].exists()},
            "row_counts": {key: count_rows(outputs[key]) for key in [*table_keys, "report", "input_manifest"] if outputs[key].exists()},
            "decision_state": d["decision_state"],
            "next_allowed_requirement": d["next_allowed_requirement"],
            "next_allowed_requirement_scope": d["next_allowed_requirement_scope"],
            "all_hard_gates_pass": bool(d["all_hard_gates_pass"]),
            "o5_upper_bound_contract_gate": d["o5_upper_bound_contract_gate"],
            "primary_operating_point_id": d["primary_operating_point_id"],
            "primary_labelable_full_learned_mean_incremental_return": d["primary_labelable_full_learned_mean_incremental_return"],
            "primary_o5_approximation_ratio": d["primary_o5_approximation_ratio"],
            "primary_o2_approximation_ratio": d["primary_o2_approximation_ratio"],
            "primary_o5_gap_remaining": d["primary_o5_gap_remaining"],
            "primary_o5_upper_bound_violation": bool(d["primary_o5_upper_bound_violation"]),
            "primary_positive_sacrifice_to_avoidance_ratio": d["primary_positive_sacrifice_to_avoidance_ratio"],
            "primary_top30_payoff_retention_rate": d["primary_top30_payoff_retention_rate"],
            "primary_top20_payoff_retention_rate": d["primary_top20_payoff_retention_rate"],
            "primary_cluster_bootstrap_utility_ci_low": d.get("primary_cluster_bootstrap_utility_ci_low", None),
            "primary_cluster_bootstrap_utility_ci_high": d.get("primary_cluster_bootstrap_utility_ci_high", None),
            "primary_cluster_bootstrap_valid_resample_n": d.get("primary_cluster_bootstrap_valid_resample_n", None),
            "validation_role": "stress_readout_only",
            **{col: bool(d[col]) for col in AUTH_FALSE_COLUMNS},
            "authorization_flags": {col: bool(d[col]) for col in AUTH_FALSE_COLUMNS},
        },
    )


def run(config_path: str | Path = CONFIG_PATH, mode: str = "full") -> dict[str, Any]:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit, input_gate = build_input_artifact_audit(config, resolved)
    upstream, upstream_gate = build_upstream_18c_refresh_handoff_audit(config, resolved)
    join_audit, join_gate, o5_identity_gate, joined = build_score_matrix_join_audit(config, resolved)
    oracle_audit, oracle_gate = build_oracle_reference_replay_audit(config, resolved)
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
        gates = {gate: "pass" for gate in HARD_GATES}
        gates.update(
            {
                "input_artifact_gate": input_gate,
                "upstream_18c_refresh_contract_gate": upstream_gate,
                "score_matrix_join_gate": join_gate,
                "oracle_denominator_contract_gate": oracle_gate,
                "o5_identity_replay_gate": o5_identity_gate,
            }
        )
        decision = build_fail_closed_decision(config, gates)
        return {
            "input_artifact_gate": input_gate,
            "input_artifact_audit": input_audit,
            "upstream": upstream,
            "score_matrix_join_audit": join_audit,
            "oracle_reference_replay_audit": oracle_audit,
            "decision": decision,
        }

    early_gates_ok = all(gate == "pass" for gate in [input_gate, upstream_gate, join_gate, oracle_gate, o5_identity_gate])
    if early_gates_ok:
        artifacts = build_all_artifacts(config, resolved, joined, upstream_gate, input_gate, join_gate, oracle_gate, o5_identity_gate)
    else:
        gates = {gate: "fail" for gate in HARD_GATES}
        gates.update(
            {
                "input_artifact_gate": input_gate,
                "upstream_18c_refresh_contract_gate": upstream_gate,
                "score_matrix_join_gate": join_gate,
                "oracle_denominator_contract_gate": oracle_gate,
                "o5_identity_replay_gate": o5_identity_gate,
                "o5_upper_bound_contract_gate": "pass",
                "binary_boundary_gate": "pass",
                "search_accounting_gate": "pass",
            }
        )
        decision = build_fail_closed_decision(config, gates)
        artifacts = empty_outputs(decision)
    write_all_outputs(config, resolved, outputs, input_audit, upstream, join_audit, oracle_audit, artifacts)
    return {
        "input_artifact_gate": input_gate,
        "input_artifact_audit": input_audit,
        "upstream": upstream,
        "score_matrix_join_audit": join_audit,
        "oracle_reference_replay_audit": oracle_audit,
        **artifacts,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "check-inputs" if args.check_inputs_only else args.mode
    run(args.config, mode=mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

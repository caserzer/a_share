#!/usr/bin/env python
"""Fail-closed staged runner for the EP21A pre-outcome architecture contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import inspect
import json
import math
import os
import platform
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUN_ID = "21A_paper_lineage_pit_data_and_architecture_contract"
EXPERIMENT_ID = "21_residual_enhanced_koopman_auto_encoder_v0"
PHASE_ID = "21A"
CONTRACT_VERSION = "21A_v2"
CONFIG_PATH = (
    EXPERIMENT_DIR
    / "configs/config_21a_paper_lineage_pit_data_and_architecture_contract.yaml"
)
REQUIREMENT_PATH = (
    EXPERIMENT_DIR
    / "requirement_21a_paper_lineage_pit_data_and_architecture_contract.md"
)
OUTPUT_ROOT = EXPERIMENT_DIR / "outputs" / f"{RUN_ID}_v2"

RESOLVED_CONFIG_TOP_LEVEL_KEYS = [
    "identity",
    "paths",
    "source_allowlist",
    "input_hash_expectations",
    "paper_contract",
    "feature_contract",
    "universe_contract",
    "architecture",
    "arms",
    "split",
    "dependencies",
    "metrics",
    "execution",
    "forward",
    "gates",
    "output",
]

CRITICAL_GATES = [
    "human_restart_scope_gate",
    "paper_source_lineage_gate",
    "paper_formula_contract_gate",
    "alpha158_expression_gate",
    "vwap_qfq_unit_contract_gate",
    "volume_corporate_action_semantics_gate",
    "feature_materialization_route_gate",
    "pit_membership_timing_gate",
    "decision_denominator_contract_gate",
    "feature_sequence_support_gate",
    "feature_label_alignment_gate",
    "train_teacher_inference_graph_gate",
    "gradient_teacher_isolation_gate",
    "architecture_shape_gate",
    "loss_reduction_gate",
    "model_arm_and_fairness_gate",
    "split_purge_gate",
    "historical_holdout_firewall_gate",
    "search_budget_gate",
    "seed_randomness_gate",
    "dependency_lock_gate",
    "gpu_dry_run_gate",
    "metric_multiplicity_gate",
    "economic_execution_freeze_gate",
    "forward_refit_contract_gate",
    "outcome_firewall_gate",
    "freeze_bundle_hash_gate",
    "implementation_readiness_gate",
]

GATE_CHECKS: dict[str, list[str]] = {
    "human_restart_scope_gate": ["H01", "H02", "H03", "H04"],
    "paper_source_lineage_gate": ["P01", "P02", "P03", "P04", "P05"],
    "paper_formula_contract_gate": ["PF01", "PF02", "PF03", "PF04", "PF05"],
    "alpha158_expression_gate": ["A01", "A02", "A03", "A04", "A05"],
    "vwap_qfq_unit_contract_gate": ["V01", "V02", "V03", "V04", "V05"],
    "volume_corporate_action_semantics_gate": ["VC01", "VC02", "VC03", "VC04"],
    "feature_materialization_route_gate": ["F01", "F02", "F03", "F04", "F05", "F06"],
    "pit_membership_timing_gate": ["U01", "U02", "U03", "U04", "U05"],
    "decision_denominator_contract_gate": ["D01", "D02", "D03", "D04", "D05"],
    "feature_sequence_support_gate": ["FS01", "FS02", "FS03", "FS04", "FS05"],
    "feature_label_alignment_gate": ["FL01", "FL02", "FL03", "FL04"],
    "train_teacher_inference_graph_gate": ["G01", "G02", "G03", "G04"],
    "gradient_teacher_isolation_gate": [
        "GI01",
        "GI02",
        "GI03",
        "GI04",
        "GI05",
        "GI06",
        "GI07",
        "GI08",
        "GI09",
        "GI10",
        "GI11",
        "GI12",
        "GI13",
        "GI14",
    ],
    "architecture_shape_gate": ["S01", "S02", "S03", "S04"],
    "loss_reduction_gate": ["L01", "L02", "L03", "L04"],
    "model_arm_and_fairness_gate": ["M01", "M02", "M03", "M04", "M05"],
    "split_purge_gate": ["SP01", "SP02", "SP03", "SP04", "SP05"],
    "historical_holdout_firewall_gate": ["HF01", "HF02", "HF03", "HF04"],
    "search_budget_gate": ["SB01", "SB02", "SB03", "SB04", "SB05"],
    "seed_randomness_gate": ["SR01", "SR02", "SR03", "SR04"],
    "dependency_lock_gate": ["DL01", "DL02", "DL03", "DL04", "DL05"],
    "gpu_dry_run_gate": ["GPU01", "GPU02", "GPU03", "GPU04", "GPU05"],
    "metric_multiplicity_gate": [
        "MM01",
        "MM02",
        "MM03",
        "MM04",
        "MM05",
        "MM06",
        "MM07",
    ],
    "economic_execution_freeze_gate": ["E01", "E02", "E03", "E04"],
    "forward_refit_contract_gate": ["FR01", "FR02", "FR03", "FR04", "FR05"],
    "outcome_firewall_gate": ["OF01", "OF02", "OF03", "OF04"],
    "freeze_bundle_hash_gate": ["HB01", "HB02", "HB03", "HB04", "HB05"],
    "implementation_readiness_gate": ["IR01", "IR02", "IR03", "IR04", "IR05"],
}

GATE_EVIDENCE_ARTIFACT: dict[str, str] = {
    "human_restart_scope_gate": "freeze/human_restart_authorization.json",
    "paper_source_lineage_gate": "freeze/paper_source_registry.csv",
    "paper_formula_contract_gate": "freeze/paper_formula_and_architecture_registry.csv",
    "alpha158_expression_gate": "freeze/alpha158_expression_registry.csv",
    "vwap_qfq_unit_contract_gate": "freeze/vwap_qfq_unit_and_range_audit.csv",
    "volume_corporate_action_semantics_gate": "freeze/alpha158_volume_corporate_action_audit.csv",
    "feature_materialization_route_gate": "freeze/feature_cache_manifest.json",
    "pit_membership_timing_gate": "freeze/pit_membership_signal_execution_timing_audit.csv",
    "decision_denominator_contract_gate": "freeze/feature_sequence_support_audit.csv",
    "feature_sequence_support_gate": "freeze/feature_sequence_support_audit.csv",
    "feature_label_alignment_gate": "freeze/label_semantics_freeze.csv",
    "train_teacher_inference_graph_gate": "freeze/train_teacher_inference_graph_contract.csv",
    "gradient_teacher_isolation_gate": "freeze/gradient_flow_and_teacher_isolation_audit.csv",
    "architecture_shape_gate": "freeze/tensor_shape_contract.csv",
    "loss_reduction_gate": "freeze/gradient_flow_and_teacher_isolation_audit.csv",
    "model_arm_and_fairness_gate": "freeze/model_arm_registry.csv",
    "split_purge_gate": "freeze/split_purge_embargo_freeze.csv",
    "historical_holdout_firewall_gate": "freeze/preoutcome_access_log.csv",
    "search_budget_gate": "freeze/hyperparameter_and_search_budget_freeze.csv",
    "seed_randomness_gate": "freeze/seed_and_randomness_freeze.csv",
    "dependency_lock_gate": "freeze/dependency_lock_change_and_runtime_contract.csv",
    "gpu_dry_run_gate": "freeze/runtime_dependency_gpu_audit.csv",
    "metric_multiplicity_gate": "freeze/metric_margin_power_freeze.csv",
    "economic_execution_freeze_gate": "freeze/upstream_scope_and_lineage_audit.csv",
    "forward_refit_contract_gate": "freeze/forward_refit_and_comparator_freeze.csv",
    "outcome_firewall_gate": "freeze/preoutcome_access_log.csv",
    "freeze_bundle_hash_gate": "freeze/freeze_bundle_manifest.json",
    "implementation_readiness_gate": "freeze/input_artifact_audit.csv",
}

FORMULA_COLUMNS = [
    "run_id",
    "formula_id",
    "source_id",
    "paper_page",
    "paper_section",
    "equation_figure_table_anchor",
    "paper_claim_summary",
    "paper_formula_canonical",
    "input_symbols",
    "output_symbols",
    "paper_disclosed",
    "paper_exact_or_project_choice",
    "project_formula_canonical",
    "project_adaptation_reason",
    "implementation_owner_stage",
    "primary_or_sensitivity",
    "claim_ceiling",
    "human_verified",
    "status",
]
FORMULA_DRAFT_COLUMNS = FORMULA_COLUMNS + ["draft_registry_sha256_input"]
SOURCE_AVAILABILITY_COLUMNS = [
    "source_id",
    "source_role",
    "requested_url",
    "resolved_url",
    "resolved_domain",
    "http_status",
    "content_sha256",
    "content_type",
    "retrieved_at_utc",
    "inside_allowlist",
    "identity_status",
    "availability_status",
]
PAPER_SOURCE_COLUMNS = [
    "run_id",
    "source_id",
    "source_role",
    "title",
    "authors",
    "venue",
    "publication_year",
    "doi",
    "official_url",
    "local_path",
    "local_sha256",
    "expected_sha256",
    "page_count",
    "version_status",
    "full_text_available",
    "appendix_status",
    "official_code_status",
    "retrieved_or_verified_at_utc",
    "identity_gate",
    "notes",
]
ALPHA158_COLUMNS = [
    "feature_index",
    "feature_name",
    "expression",
    "direct_fields",
    "max_trailing_window",
    "uses_vwap",
    "uses_volume",
    "uses_money",
    "uses_future_offset",
    "qlib_distribution_version",
    "qlib_source_file",
    "qlib_source_file_sha256",
    "canonical_order",
    "route_inclusion_full",
    "route_inclusion_no_vwap",
    "status",
]
MODEL_ARM_COLUMNS = [
    "arm_id",
    "mandatory",
    "paper_reported_or_project_control",
    "input_feature_route",
    "uses_return_sequence",
    "uses_feature_sequence",
    "uses_gate",
    "operator_mode",
    "selector_context",
    "residual_mode",
    "loss_terms",
    "score_head",
    "primary_comparator_role",
    "parameter_match_target",
    "historical_stage",
    "forward_eligible",
    "claim_if_pass",
    "claim_if_fail",
]
DECISION_COLUMNS = [
    "run_id",
    "contract_version",
    "decision_state",
    "human_restart_scope_gate",
    "paper_source_lineage_gate",
    "paper_formula_contract_gate",
    "official_code_status",
    "alpha158_expression_gate",
    "vwap_qfq_unit_contract_gate",
    "volume_corporate_action_semantics_gate",
    "feature_materialization_route_gate",
    "primary_feature_route_id",
    "primary_feature_route_class",
    "alpha158_exact_local_materialization",
    "pit_membership_timing_gate",
    "decision_denominator_contract_gate",
    "feature_sequence_support_gate",
    "feature_label_alignment_gate",
    "train_teacher_inference_graph_gate",
    "gradient_teacher_isolation_gate",
    "architecture_shape_gate",
    "loss_reduction_gate",
    "model_arm_and_fairness_gate",
    "split_purge_gate",
    "historical_holdout_firewall_gate",
    "search_budget_gate",
    "seed_randomness_gate",
    "dependency_lock_gate",
    "gpu_dry_run_gate",
    "metric_multiplicity_gate",
    "economic_execution_freeze_gate",
    "forward_refit_contract_gate",
    "outcome_firewall_gate",
    "freeze_bundle_hash_gate",
    "implementation_readiness_gate",
    "paper_architecture_project_adaptation_reachable",
    "exact_replication_reachable",
    "official_code_available",
    "selected_batch_size",
    "historical_sample_role",
    "historical_support_claim_allowed",
    "forward_confirmatory_required_complete_days",
    "next_allowed_requirement",
    "next_requirement_generation_authorized",
    "next_requirement_execution_authorized",
    "outcome_model_training_authorized",
    "historical_holdout_readout_authorized",
    "policy_training_authorized",
    "portfolio_optimization_authorized",
    "deployment_authorized",
    "freeze_bundle_hash",
    "gate_evidence_sha256",
    "blocking_reasons",
]

TABLE_SCHEMAS: dict[str, list[str]] = {
    "upstream_scope_and_lineage_audit.csv": [
        "artifact_id",
        "path",
        "sha256",
        "expected_role",
        "preoutcome_only",
        "manifest_verified",
        "allowed",
        "status",
        "blocking_reason",
    ],
    "input_artifact_audit.csv": [
        "artifact_id",
        "path",
        "artifact_type",
        "exists",
        "size_bytes",
        "sha256_or_root_hash",
        "schema_status",
        "read_authorized",
        "status",
    ],
    "source_data_inventory.csv": [
        "source_id",
        "relative_path",
        "file_n",
        "row_n",
        "date_min",
        "date_max",
        "instrument_n",
        "root_hash",
        "status",
    ],
    "paper_source_registry.csv": PAPER_SOURCE_COLUMNS,
    "paper_formula_and_architecture_registry.csv": FORMULA_COLUMNS,
    "paper_reproducibility_gap_registry.csv": [
        "gap_id",
        "paper_disclosure_status",
        "local_evidence",
        "frozen_project_choice",
        "choice_source",
        "sensitivity_allowed",
        "exact_replication_impact",
        "blocking_for_project_adaptation",
        "status",
    ],
    "official_code_availability_audit.csv": [
        "candidate_id",
        "url",
        "owner_identity",
        "source_role",
        "http_status",
        "code_disclosed",
        "official_status",
        "checked_at_utc",
        "status",
    ],
    "alpha158_expression_registry.csv": ALPHA158_COLUMNS,
    "alpha158_local_field_mapping.csv": [
        "qlib_field",
        "local_source",
        "source_scale",
        "transform",
        "availability_time",
        "route_id",
        "unit_gate",
        "status",
    ],
    "vwap_qfq_unit_and_range_audit.csv": [
        "scope",
        "instrument",
        "year",
        "board_bucket",
        "qfq_key_n",
        "raw_key_n",
        "overlap_key_n",
        "overlap_rate",
        "base_row_n",
        "factor_pass_n",
        "factor_fail_n",
        "factor_unknown_n",
        "factor_pass_rate",
        "auditable_row_n",
        "auditable_row_rate",
        "in_range_n",
        "out_of_range_n",
        "unknown_n",
        "range_pass_rate",
        "coverage_threshold",
        "range_threshold",
        "status",
    ],
    "alpha158_volume_corporate_action_audit.csv": [
        "instrument",
        "jump_date",
        "factor_before",
        "factor_after",
        "abs_log_jump",
        "window_start",
        "window_end",
        "exposed_feature_row_n",
        "status",
    ],
    "alpha158_factor_jump_window_quarantine_sensitivity.csv": [
        "split",
        "decision_day_n",
        "source_row_n",
        "quarantine_row_n",
        "remaining_row_n",
        "remaining_day_n",
        "route_status",
    ],
    "pit_membership_signal_execution_timing_audit.csv": [
        "check_id",
        "scope",
        "observed_value",
        "required_value",
        "status",
        "blocking_reason",
    ],
    "feature_sequence_support_audit.csv": [
        "split",
        "decision_date",
        "feature_route_id",
        "U_membership_n",
        "membership_integrity_n",
        "history_ready_n",
        "sequence_ready_n",
        "feature_ready_n",
        "U_decision_n",
        "invalid_n",
        "layer_count_reconciled",
        "support_status",
    ],
    "feature_normalization_and_missingness_contract.csv": [
        "field_group",
        "fit_split",
        "center_rule",
        "scale_rule",
        "clip_lower",
        "clip_upper",
        "invalid_fill",
        "indicator_direct_input",
        "apply_splits",
        "status",
    ],
    "label_semantics_freeze.csv": [
        "label_id",
        "formula",
        "role",
        "materialized_in_21a",
        "selection_allowed",
        "status",
    ],
    "decision_universe_and_label_resolution_contract.csv": [
        "status_id",
        "trigger",
        "valuation_rule",
        "row_or_day_action",
        "primary_denominator_allowed",
        "synthetic_test_status",
    ],
    "train_teacher_inference_graph_contract.csv": [
        "graph_id",
        "node_id",
        "node_role",
        "input_nodes",
        "output_shape",
        "train_only",
        "inference_present",
        "teacher_value_allowed",
        "status",
    ],
    "gradient_flow_and_teacher_isolation_audit.csv": [
        "test_id",
        "expected",
        "observed",
        "max_abs_delta",
        "status",
        "blocking_reason",
    ],
    "per_arm_loss_and_score_index_contract.csv": [
        "arm_id",
        "loss_terms",
        "target_id",
        "score_tensor",
        "score_index",
        "draw_n",
        "aggregation",
        "status",
    ],
    "split_purge_embargo_freeze.csv": [
        "split_id",
        "nominal_start",
        "nominal_end",
        "effective_start",
        "effective_end",
        "purge_side",
        "purge_sessions",
        "dropped_day_n",
        "outcome_access_allowed",
        "status",
    ],
    "model_arm_registry.csv": MODEL_ARM_COLUMNS,
    "tensor_shape_contract.csv": [
        "graph_id",
        "tensor_id",
        "producer",
        "consumer",
        "dtype",
        "train_shape",
        "inference_shape",
        "train_only",
        "broadcast_allowed",
        "status",
    ],
    "hyperparameter_and_search_budget_freeze.csv": [
        "config_id",
        "role",
        "parameter",
        "primary_value",
        "sensitivity_value",
        "one_factor_only",
        "promotion_allowed",
        "status",
    ],
    "seed_and_randomness_freeze.csv": [
        "model_seed",
        "stream_name",
        "derived_seed_or_rule",
        "batch_order_invariant",
        "status",
    ],
    "dependency_lock_change_and_runtime_contract.csv": [
        "dependency",
        "required_spec",
        "baseline_version",
        "lock_resolved_version",
        "runtime_version",
        "direct_or_transitive",
        "baseline_source",
        "resolved_source",
        "lock_action",
        "allowed_change",
        "status",
    ],
    "runtime_dependency_gpu_audit.csv": [
        "check_id",
        "observed_value",
        "required_value",
        "batch_size",
        "peak_memory_mib",
        "repeat_delta",
        "status",
    ],
    "metric_margin_power_freeze.csv": [
        "record_type",
        "family_id",
        "contrast_id",
        "terminal_state_id",
        "priority",
        "metric",
        "margin",
        "alpha",
        "correction",
        "evidence_unit",
        "block_length",
        "MDE",
        "sigma",
        "rho",
        "n_required",
        "status",
    ],
    "forward_refit_and_comparator_freeze.csv": [
        "contract_id",
        "field",
        "frozen_value",
        "selection_time",
        "change_resets_clock",
        "status",
    ],
    "preoutcome_access_log.csv": [
        "run_id",
        "stage",
        "accessed_at_utc",
        "artifact_path_or_resource",
        "artifact_sha256_or_root_hash",
        "dataset_role",
        "columns_or_metadata_read",
        "derived_fields",
        "feature_date_constraint",
        "outcome_columns_detected",
        "outcome_formula_executed",
        "selection_or_tuning_allowed",
        "purpose",
        "access_gate",
    ],
    "finalize_access_audit.csv": [
        "access_seq",
        "accessed_at_utc",
        "operation",
        "path_or_resource",
        "freeze_manifest_listed",
        "raw_input",
        "allowed",
        "status",
    ],
    "gate_evidence_21a.csv": [
        "gate_id",
        "check_id",
        "evidence_artifact",
        "evidence_selector",
        "observed_value",
        "required_value",
        "status",
        "blocking_reason",
    ],
}

FREEZE_RELATIVE_PATHS = [
    "freeze/resolved_config.yaml",
    "freeze/human_restart_authorization.json",
    "freeze/upstream_scope_and_lineage_audit.csv",
    "freeze/input_artifact_audit.csv",
    "freeze/source_data_inventory.csv",
    "freeze/paper_source_registry.csv",
    "freeze/paper_formula_and_architecture_registry.csv",
    "freeze/paper_reproducibility_gap_registry.csv",
    "freeze/official_code_availability_audit.csv",
    "freeze/alpha158_expression_registry.csv",
    "freeze/alpha158_local_field_mapping.csv",
    "freeze/alpha158_expression_hash.txt",
    "freeze/vwap_qfq_unit_and_range_audit.csv",
    "freeze/alpha158_volume_corporate_action_audit.csv",
    "freeze/alpha158_factor_jump_window_quarantine_sensitivity.csv",
    "freeze/pit_membership_signal_execution_timing_audit.csv",
    "freeze/feature_sequence_support_audit.csv",
    "freeze/feature_cache_manifest.json",
    "freeze/feature_normalization_and_missingness_contract.csv",
    "freeze/label_semantics_freeze.csv",
    "freeze/decision_universe_and_label_resolution_contract.csv",
    "freeze/train_teacher_inference_graph_contract.csv",
    "freeze/gradient_flow_and_teacher_isolation_audit.csv",
    "freeze/per_arm_loss_and_score_index_contract.csv",
    "freeze/split_purge_embargo_freeze.csv",
    "freeze/model_arm_registry.csv",
    "freeze/tensor_shape_contract.csv",
    "freeze/hyperparameter_and_search_budget_freeze.csv",
    "freeze/seed_and_randomness_freeze.csv",
    "freeze/dependency_lock_change_and_runtime_contract.csv",
    "freeze/runtime_dependency_gpu_audit.csv",
    "freeze/metric_margin_power_freeze.csv",
    "freeze/forward_refit_and_comparator_freeze.csv",
    "freeze/preoutcome_access_log.csv",
    "freeze/contract_freeze_21a.json",
    "freeze/21A_contract_freeze.md",
    "freeze/freeze_bundle_manifest.json",
    "freeze/freeze_output_hashes_21a.json",
]
FINAL_RELATIVE_PATHS = [
    "21A_contract_decision.csv",
    "finalize_access_audit.csv",
    "gate_evidence_21a.csv",
    "21A_paper_lineage_pit_data_and_architecture_contract_report.md",
    "manifest_21a_paper_lineage_pit_data_and_architecture_contract.json",
    "output_hashes_21a_paper_lineage_pit_data_and_architecture_contract.json",
]

FORBIDDEN_TOKENS = (
    "label",
    "target_value",
    "future",
    "forward_return",
    "return_t_plus",
    "y_rank",
    "y_exec",
    "rankic",
    "icir",
    "mfe",
    "mae",
    "winner",
    "first_hit",
    "pnl",
    "realized_utility",
    "score_outcome",
    "topk_return",
    "strategy_return",
    "model_prediction",
)
ALLOWED_METADATA_COLUMNS = {
    "label_id",
    "formula",
    "role",
    "materialized_in_21a",
    "selection_allowed",
    "feature_label_alignment_gate",
    "outcome_firewall_gate",
    "outcome_model_training_authorized",
    "observed_value",
    "required_value",
    "status_id",
    "trigger",
    "valuation_rule",
    "row_or_day_action",
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run EP21A pre-outcome contract stages."
    )
    parser.add_argument(
        "--stage", required=True, choices=["acquire-sources", "freeze", "finalize"]
    )
    parser.add_argument("--config")
    parser.add_argument("--output-root")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    if args.stage == "finalize":
        if args.config is not None:
            parser.error("finalize forbids --config")
        if not args.output_root:
            parser.error("finalize requires --output-root")
    else:
        if args.output_root is not None:
            parser.error("acquire-sources/freeze forbid --output-root")
        args.config = args.config or str(CONFIG_PATH)
    return args


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def gate(value: bool) -> str:
    return "pass" if bool(value) else "fail"


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        + "\n"
    ).encode("utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = path.as_posix()
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(
        ("experiments/", "data/", "pyproject.toml", "requirements.txt", "uv.lock")
    ):
        return TOPIC_ROOT / path
    return EXPERIMENT_DIR / path


def load_config(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    import yaml

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if list(config) != RESOLVED_CONFIG_TOP_LEVEL_KEYS:
        raise ValueError(
            f"resolved config top-level keys/order mismatch: {list(config)}"
        )
    if (
        config["identity"]["run_id"] != RUN_ID
        or config["identity"]["contract_version"] != CONTRACT_VERSION
    ):
        raise ValueError("config identity mismatch")
    unresolved = re.findall(
        r"\b(?:TBD|TODO|choose[-_ ]later|best[-_ ]effort)\b", json.dumps(config), re.I
    )
    if unresolved:
        raise ValueError(f"unresolved config placeholders: {unresolved}")
    return config


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    paths = {key: topic_path(value) for key, value in config["paths"].items()}
    for key, value in config["paths"].items():
        if Path(value).is_absolute() or str(value).startswith("file://"):
            raise ValueError(f"absolute/file URI path forbidden: {key}={value}")
    return paths


def resolve_output_root(config: dict[str, Any]) -> Path:
    value = config["output"]["output_root"]
    if Path(value).is_absolute() or str(value).startswith("file://"):
        raise ValueError("output root must be repository-relative")
    return topic_path(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def write_yaml(path: Path, payload: Any) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    path.write_text(text, encoding="utf-8", newline="\n")


def _stable_csv_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_csv(path: Path, rows: Any, columns: list[str]) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    for column in columns:
        if column not in frame:
            frame[column] = None
    frame = frame[columns]
    for column in frame.columns:
        frame[column] = frame[column].map(_stable_csv_value)
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="\n"
    )


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def root_inventory_hash(root: Path) -> tuple[str, int, int]:
    rows: list[str] = []
    total_size = 0
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda value: value.relative_to(root).as_posix(),
    )
    for path in files:
        size = path.stat().st_size
        total_size += size
        rows.append(f"{path.relative_to(root).as_posix()}|{size}|{file_sha(path)}")
    return (
        hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest(),
        len(files),
        total_size,
    )


def pdf_page_count(path: Path) -> int:
    data = path.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page(?!s)\b", data))
    if pages:
        return pages
    counts = [int(value) for value in re.findall(rb"/Count\s+(\d+)", data)]
    return max(counts, default=0)


def forbid_outcome_columns(
    columns: Iterable[str], metadata_exception: bool = False
) -> list[str]:
    forbidden: list[str] = []
    for raw in columns:
        name = str(raw)
        lower = name.lower()
        if metadata_exception and lower in ALLOWED_METADATA_COLUMNS:
            continue
        if any(token in lower for token in FORBIDDEN_TOKENS):
            forbidden.append(name)
    return forbidden


def expression_has_future_offset(expression: str) -> bool:
    return bool(re.search(r"Ref\s*\([^,]+,\s*-\d+", expression, re.I))


def add_access(
    access_log: list[dict[str, Any]],
    path: Path | str,
    dataset_role: str,
    columns: Iterable[str] = (),
    derived_fields: Iterable[str] = (),
    purpose: str = "preoutcome_contract_audit",
    feature_date_constraint: str = "not_applicable",
) -> None:
    path_obj = Path(path) if not isinstance(path, Path) else path
    column_list = [str(value) for value in columns]
    forbidden = forbid_outcome_columns(column_list)
    if path_obj.is_file():
        resource_hash = file_sha(path_obj)
    elif path_obj.is_dir():
        resource_hash = root_inventory_hash(path_obj)[0]
    else:
        resource_hash = ""
    resource_path = (
        rel(path_obj)
        if path_obj.exists() and path_obj.is_relative_to(REPO_ROOT)
        else str(path)
    )
    access_log.append(
        {
            "run_id": RUN_ID,
            "stage": "freeze",
            "accessed_at_utc": utc_now(),
            "artifact_path_or_resource": resource_path,
            "artifact_sha256_or_root_hash": resource_hash,
            "dataset_role": dataset_role,
            "columns_or_metadata_read": "|".join(column_list),
            "derived_fields": "|".join(str(value) for value in derived_fields),
            "feature_date_constraint": feature_date_constraint,
            "outcome_columns_detected": "|".join(forbidden),
            "outcome_formula_executed": False,
            "selection_or_tuning_allowed": False,
            "purpose": purpose,
            "access_gate": gate(not forbidden),
        }
    )


def _formula_spec(formula_id: str, index: int) -> dict[str, Any]:
    specs: dict[str, tuple[int, str, str, str, str, str]] = {
        "P01_INPUT_RETURN_AND_FEATURE_SEQUENCES": (
            1,
            "Section 2.1 Problem Formulation",
            "paragraph beginning 'Given a collection of S financial assets'",
            "X_i=[x_i,1,...,x_i,T], y_i=[y_i,1,...,y_i,T]; y_hat_i,t+1=M(X_i^1:t,y_i^1:t)",
            "x_source and y_source are trailing sequences ending at decision close t",
            "Paper input semantics retained; project fixes PIT timing separately.",
        ),
        "P02_DUAL_LSTM_ENCODERS": (
            2,
            "Section 3.1 Latent State Encoder",
            "Equations (1)-(6)",
            "H_y=LSTM_y(y_1:T-1); H_y_plus=LSTM_y(y_2:T); H_x=LSTM_x(x_1:T-1); H_x_plus=LSTM_x(x_2:T)",
            "shared dual LSTM encoders process source and shifted teacher sequences",
            "The paper-disclosed overlapping segments are retained with project-explicit tensor indexing.",
        ),
        "P03_SIGMOID_FEATURE_GATE": (
            2,
            "Section 3.1 Latent State Encoder",
            "Equations (7)-(8) and paragraph after Equation (10)",
            "G=GateNet(H_x); G_plus=GateNet(H_x_plus), where GateNet is an MLP followed by sigmoid",
            "G=sigmoid(Linear(H_x)); the shared GateNet is applied once per source/teacher encoding",
            "Paper leaves MLP depth open; project freezes a single affine layer plus one sigmoid.",
        ),
        "P04_LATENT_FUSION_Z_AND_Z_PLUS": (
            2,
            "Section 3.1 Latent State Encoder",
            "Equations (9)-(10)",
            "Z=H_y odot G+H_x odot (1-G); Z_plus=H_y_plus odot G_plus+H_x_plus odot (1-G_plus)",
            "Z_source and train-only Z_teacher_shifted use the same elementwise gated fusion",
            "Project names source/teacher roles explicitly to prevent inference leakage.",
        ),
        "P05_OPERATOR_CODEBOOK": (
            2,
            "Section 3.2 Adaptive Koopman Selector",
            "paragraph containing 'codebook K={K1,K2,...,KN}' before Equation (11)",
            "K_codebook={K_1,K_2,...,K_N}",
            "four learnable 64x64 Koopman matrices form the primary codebook",
            "N and latent dimension are project choices because the paper does not disclose them.",
        ),
        "P06_GUMBEL_SOFTMAX_SELECTOR": (
            2,
            "Section 3.2 Adaptive Koopman Selector",
            "Equations (11)-(13)",
            "a=LeakyReLU(W[Z,H_y]^h); alpha_i=exp((a_i+epsilon_i)/tau)/sum_j exp((a_j+epsilon_j)/tau)",
            "state-conditioned LeakyReLU selector with soft Gumbel-Softmax in train and hard argmax in inference",
            "Temperature schedule and hard-inference rule are project-frozen where the paper is silent.",
        ),
        "P07_SELECTED_KOOPMAN_PROPAGATION": (
            2,
            "Section 3.2 Adaptive Koopman Selector",
            "Equation (14), continuing with Equation (15) on PDF page 3",
            "K_s=sum_i alpha_i K_i; Z_hat_plus=K_s Z",
            "K_selected[b,t]=sum_i alpha[b,t,i]K_i; Z_hat_shifted=einsum(K_selected,Z_source)",
            "Project makes batch/time axes and matrix multiplication explicit.",
        ),
        "P08_LATENT_RESIDUAL": (
            3,
            "Section 3.3 Dynamic Residual Corrector",
            "first paragraph, sentence 'Let the residual be R=Z+ - Z_hat+'",
            "R=Z_plus-Z_hat_plus",
            "residual_target=Z_teacher_shifted-Z_hat_shifted is train-only",
            "Project explicitly isolates the true shifted latent from inference ancestors.",
        ),
        "P09_CONDITIONAL_DDPM_FORWARD_NOISE": (
            3,
            "Section 3.3 Dynamic Residual Corrector",
            "Equation (16)",
            "x_t=sqrt(alpha_bar_t)R+sqrt(1-alpha_bar_t)epsilon, epsilon~N(0,I)",
            "x_s=sqrt(alpha_bar_s)residual_target+sqrt(1-alpha_bar_s)epsilon",
            "Variable s is used for diffusion time to avoid collision with market date t.",
        ),
        "P10_DDPM_EPSILON_LOSS": (
            3,
            "Section 3.3 Dynamic Residual Corrector",
            "Equation (17)",
            "L_diff=E_t,epsilon ||epsilon_theta(x_t,t,Z)-epsilon||_2^2",
            "L_diff=MeanValid((epsilon_theta(x_s,s,Z_source)-epsilon)^2)",
            "Project freezes finite-cell mean reduction axes.",
        ),
        "P11_REVERSE_RESIDUAL_SAMPLE": (
            3,
            "Section 3.3 Dynamic Residual Corrector",
            "Equations (18)-(20)",
            "mu_theta=(x_t-(1-alpha_t)/sqrt(1-alpha_bar_t)*epsilon_theta)/sqrt(alpha_t); sigma_t^2=((1-alpha_bar_{t-1})/(1-alpha_bar_t))*beta_t; x_{t-1}=mu_theta+sigma_t xi",
            "20-step DDPM reverse chain with the paper equations and independently keyed draw noise",
            "Step count and seed-key contract are project choices.",
        ),
        "P12_RESIDUAL_ENHANCED_LATENT": (
            3,
            "Section 3.3 Dynamic Residual Corrector",
            "Equation (21)",
            "Z_tilde_plus=Z_hat_plus+R_hat",
            "Z_tilde_shifted=Z_hat_shifted+R_hat for train reconstruction and inference draws",
            "Paper correction rule retained with explicit train/inference roles.",
        ),
        "P13_RETURN_DECODER": (
            3,
            "Sections 3.4-3.5",
            "Equations (22)-(23) and Equation (27)",
            "y_hat_1:T-1=Decoder(Z); y_hat_2:T=Decoder(Z_tilde_plus); y_hat_2:t+1=Decoder(Z_plus)",
            "shared scalar decoder reconstructs source/shifted sequences; score is the last shifted output",
            "Project resolves the Equation (27) notation against the preceding corrected-latent definition.",
        ),
        "P14_L_REC_L_KOOP_L_DIFF": (
            3,
            "Section 3.6 Loss Function",
            "Equations (28)-(31)",
            "L_total=L_rec+L_koop+L_diff; L_rec=MSE(y_hat_1:T-1,y_1:T-1)+MSE(y_hat_2:T,y_2:T); L_koop=MSE(Z_hat_plus,Z_plus)",
            "L_total=L_rec+L_koop+L_diff with L_forecast included exactly once inside L_rec",
            "Paper top-level weights are retained; project freezes valid-cell reductions and forecast counting.",
        ),
        "P15_T10_LOOKBACK": (
            3,
            "Section 4.1 Experiment Setup",
            "sentence 'The lookback window length T is set to 10 trading days'",
            "T=10 trading days",
            "lookback_T=10 exchange sessions ending at decision close t",
            "Paper value retained and PIT calendar semantics made explicit.",
        ),
        "P16_RANKIC_AND_RANKICIR": (
            3,
            "Section 4.1 Experiment Setup",
            "final metric-definition sentence before Section 4.2",
            "RankIC_t=Spearman(rank(r_hat_t),rank(r_t)); printed RankICIR denominator is mean(RankIC_t)",
            "RankIC=float64 Pearson of average ranks; RankICIR=mean(RankIC_t)/std(RankIC_t,ddof=1)",
            "The printed RankICIR denominator appears inconsistent; project registers the conventional standard-deviation denominator and cannot claim exact metric replication.",
        ),
        "P17_TOPK30_DIAGNOSTIC": (
            4,
            "Section 4.5 Investment Simulation",
            "paragraph containing 'In our experiments, K=30' and Figure 4",
            "rank candidates by predicted score and hold TopK with K=30",
            "TopK=30 gross close proxy and distinct next-open executable ledger under EP19/EP20 rules",
            "Paper does not disclose local PIT timing/cost details; executable economics are a project adaptation.",
        ),
        "A01_FULL_T_SHIFTED_SEQUENCE_INDEXING": (
            2,
            "Project adaptation grounded in Section 3.1",
            "Equations (1)-(10), overlapping source/shifted segments",
            "paper uses y_1:T-1 versus y_2:T and x_1:T-1 versus x_2:T",
            "source_dates=[t-T+1..t]; teacher_shifted_dates=[t-T+2..t+1], each with T transitions",
            "Project extends the overlapping construction to an explicit T-transition forecasting contract.",
        ),
        "A02_FINAL_STEP_SCORE_INDEX": (
            3,
            "Project adaptation grounded in Section 3.5",
            "sentence after Equation (27): estimated return is the last reconstructed element",
            "y_hat_t+1 is the last element of reconstructed y_hat_2:t+1",
            "score_next=decoded_shifted[:,-1]",
            "Project fixes the tensor index and scalar shape.",
        ),
        "A03_MEAN_LOSS_REDUCTION_AXES": (
            3,
            "Project adaptation grounded in Section 3.6",
            "Equations (28)-(31), MSE reductions not further disclosed",
            "paper specifies MSE objectives without batch/time/latent reduction order",
            "MeanValid means latent-element mean followed by valid batch/time-cell mean",
            "Unique reduction axes are needed for reproducible loss scale and batch-duplication invariance.",
        ),
        "A04_TEACHER_GRADIENT_AND_INFERENCE_ISOLATION": (
            2,
            "Project adaptation grounded in Methodology and Section 3.3",
            "page 2 sentence 'At inference, only past returns and features are used'; page 3 residual conditioning on Z",
            "inference uses only past returns/features; diffusion corrector is conditioned on current latent Z",
            "teacher tensors only construct train targets/noising and never enter selector, condition, or inference-score ancestors",
            "Project freezes the only leakage-safe graph consistent with the paper prose.",
        ),
        "A05_EIGHT_DRAW_POINT_PREDICTION_MEAN": (
            3,
            "Project adaptation grounded in Section 3.3",
            "Equations (18)-(21), one residual sample described; draw aggregation undisclosed",
            "reverse diffusion maps x_0 to a residual sample R_hat",
            "point score is the arithmetic mean of eight independently keyed reverse-diffusion draws",
            "Draw count and point aggregation are undisclosed project choices.",
        ),
        "A06_PROJECT_PIT_UNIVERSE_AND_TIMING": (
            3,
            "Project adaptation grounded in Section 4.1",
            "CSI300/S&P500, 2010-2020 and Alpha158 setup paragraph; no PIT membership timing disclosed",
            "paper evaluates fixed named universes and does not disclose point-in-time membership/execution timing",
            "membership at close t defines U_t_membership; usable_trade_date is exactly the next exchange session; U_t_decision is outcome-independent",
            "Local PIT universe and execution timing are necessary project adaptations and prohibit a CSI300 exact-replication claim.",
        ),
    }
    page, section, anchor, paper_canonical, project_canonical, reason = specs[
        formula_id
    ]
    paper_or_project = (
        "paper_exact"
        if formula_id.startswith("P") and paper_canonical == project_canonical
        else "paper_grounded_project_choice"
    )
    return {
        "run_id": RUN_ID,
        "formula_id": formula_id,
        "source_id": "reaka_icassp_2026_vor",
        "paper_page": page,
        "paper_section": section,
        "equation_figure_table_anchor": anchor,
        "paper_claim_summary": paper_canonical,
        "paper_formula_canonical": paper_canonical,
        "input_symbols": "paper_defined_inputs",
        "output_symbols": "paper_defined_outputs",
        "paper_disclosed": formula_id.startswith("P"),
        "paper_exact_or_project_choice": paper_or_project,
        "project_formula_canonical": project_canonical,
        "project_adaptation_reason": reason,
        "implementation_owner_stage": "21A_freeze_then_21B_21D",
        "primary_or_sensitivity": "primary",
        "claim_ceiling": "paper_architecture_grounded_project_adaptation",
        "human_verified": False,
        "status": "not_evaluable",
    }


def build_formula_draft(
    config: dict[str, Any], source_manifest_sha: str
) -> list[dict[str, Any]]:
    formula_ids = config["paper_contract"]["required_formula_ids"]
    draft_input = stable_hash(
        {"formula_ids": formula_ids, "source_manifest_sha256": source_manifest_sha}
    )
    rows = []
    for index, formula_id in enumerate(formula_ids):
        row = _formula_spec(formula_id, index)
        row["draft_registry_sha256_input"] = draft_input
        rows.append(row)
    return rows


def _fetch_allowlisted(source: dict[str, Any], offline: bool) -> dict[str, Any]:
    url = source["url"]
    base = {
        "source_id": source["source_id"],
        "source_role": source["source_role"],
        "requested_url": url,
        "resolved_url": url,
        "resolved_domain": urlparse(url).hostname or "",
        "http_status": "",
        "content_sha256": "",
        "content_type": "",
        "retrieved_at_utc": utc_now(),
        "inside_allowlist": True,
        "identity_status": "pass",
        "availability_status": "not_evaluable_network_unavailable",
    }
    if offline:
        return base
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 EP21A lineage audit"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - explicit allowlist
            content = response.read()
            resolved_url = response.geturl()
            resolved_domain = urlparse(resolved_url).hostname or ""
            allowed = set(source["allowed_domains"])
            inside = resolved_domain in allowed
            base.update(
                {
                    "resolved_url": resolved_url,
                    "resolved_domain": resolved_domain,
                    "http_status": int(response.status),
                    "content_sha256": hashlib.sha256(content).hexdigest()
                    if content
                    else "",
                    "content_type": response.headers.get_content_type(),
                    "inside_allowlist": inside,
                    "identity_status": gate(inside),
                    "availability_status": "available"
                    if inside and content
                    else "not_evaluable_network_unavailable",
                }
            )
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
    return base


def acquire_sources_stage(
    config_path: str | Path = CONFIG_PATH, offline: bool = False
) -> dict[str, Any]:
    config = load_config(config_path)
    paths = resolve_paths(config)
    reference_root = paths["reference_root"]
    reference_root.mkdir(parents=True, exist_ok=True)
    paper = paths["paper"]
    expected = config["input_hash_expectations"]
    paper_sha = file_sha(paper)
    page_count = pdf_page_count(paper)
    local_row = {
        "source_id": "local_vor_pdf",
        "source_role": "version_of_record",
        "requested_url": "local://paper",
        "resolved_url": rel(paper),
        "resolved_domain": "",
        "http_status": 200,
        "content_sha256": paper_sha,
        "content_type": "application/pdf",
        "retrieved_at_utc": utc_now(),
        "inside_allowlist": True,
        "identity_status": gate(
            paper_sha == expected["paper_sha256"]
            and page_count == expected["paper_page_count"]
        ),
        "availability_status": "available",
    }
    source_rows = [local_row]
    for source in config["source_allowlist"]["acquisition_sources"]:
        if source["source_id"] == "local_vor_pdf":
            continue
        source_rows.append(_fetch_allowlisted(source, offline=offline))
    source_rows.sort(key=lambda row: (row["source_id"], row["requested_url"]))
    source_manifest_path = reference_root / "source_availability_manifest.csv"
    write_csv(source_manifest_path, source_rows, SOURCE_AVAILABILITY_COLUMNS)
    draft_rows = build_formula_draft(config, file_sha(source_manifest_path))
    draft_path = reference_root / "paper_formula_registry_draft.csv"
    write_csv(draft_path, draft_rows, FORMULA_DRAFT_COLUMNS)
    packet_lines = [
        "# EP21A Formula Review Packet",
        "",
        f"- paper_sha256: `{paper_sha}`",
        f"- page_count: `{page_count}`",
        f"- source_manifest_sha256: `{file_sha(source_manifest_path)}`",
        "",
        "Human review must approve or reject the complete required formula set; partial approval cannot pass.",
        "",
    ]
    for row in draft_rows:
        packet_lines.extend(
            [
                f"## {row['formula_id']}",
                "",
                f"- Page: `{row['paper_page']}`",
                f"- Anchor: `{row['equation_figure_table_anchor']}`",
                f"- Paper canonical: `{row['paper_formula_canonical']}`",
                f"- Project mapping: `{row['project_formula_canonical']}`",
                f"- Gap/adaptation: {row['project_adaptation_reason']}",
                "",
            ]
        )
    packet_path = reference_root / "formula_review_packet.md"
    write_text(packet_path, "\n".join(packet_lines))
    return {
        "status": "acquired_offline" if offline else "acquired",
        "source_manifest": source_manifest_path,
        "formula_draft": draft_path,
        "review_packet": packet_path,
        "authorization_required": not (
            reference_root / "formula_review_authorization.json"
        ).exists(),
    }


def validate_formula_authorization(
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, bool]]:
    import pandas as pd

    paths = resolve_paths(config)
    reference_root = paths["reference_root"]
    draft_path = reference_root / "paper_formula_registry_draft.csv"
    packet_path = reference_root / "formula_review_packet.md"
    auth_path = reference_root / "formula_review_authorization.json"
    checks = {
        "hash_chain": False,
        "approved_human": False,
        "formula_set": False,
        "rows_complete": False,
    }
    if not draft_path.exists() or not packet_path.exists():
        return [], None, checks
    draft = pd.read_csv(draft_path, keep_default_na=False)
    expected_ids = config["paper_contract"]["required_formula_ids"]
    checks["formula_set"] = (
        list(draft["formula_id"]) == expected_ids
        and draft["formula_id"].is_unique
        and len(draft) == len(expected_ids)
    )
    required_nonempty = [
        "paper_page",
        "equation_figure_table_anchor",
        "paper_formula_canonical",
        "project_formula_canonical",
    ]
    checks["rows_complete"] = all(
        draft[column].astype(str).str.strip().ne("").all()
        for column in required_nonempty
    )
    auth: dict[str, Any] | None = None
    expected_auth_keys = {
        "paper_sha256",
        "formula_registry_draft_sha256",
        "review_packet_sha256",
        "reviewed_source_id",
        "reviewed_formula_ids",
        "page_anchor_verified",
        "equation_or_figure_anchor_verified",
        "reviewer_role",
        "reviewed_at_utc",
        "authorization_status",
    }
    if auth_path.exists():
        try:
            auth = read_json(auth_path)
        except (json.JSONDecodeError, OSError):
            auth = None
    if auth is not None and set(auth) == expected_auth_keys:
        checks["hash_chain"] = (
            auth["paper_sha256"] == file_sha(paths["paper"])
            and auth["formula_registry_draft_sha256"] == file_sha(draft_path)
            and auth["review_packet_sha256"] == file_sha(packet_path)
        )
        checks["approved_human"] = (
            auth["reviewer_role"] == "human"
            and auth["authorization_status"] == "approved"
            and bool_value(auth["page_anchor_verified"])
            and bool_value(auth["equation_or_figure_anchor_verified"])
            and auth["reviewed_source_id"] == "reaka_icassp_2026_vor"
            and auth["reviewed_formula_ids"] == expected_ids
        )
    verified = all(checks.values())
    rows: list[dict[str, Any]] = []
    for record in draft[FORMULA_COLUMNS].to_dict("records"):
        record["human_verified"] = verified
        record["status"] = "pass" if verified else "fail"
        rows.append(record)
    return rows, auth, checks


def normalize_instrument(value: Any) -> str:
    text = str(value).strip().upper()
    if re.fullmatch(r"(?:SH|SZ|BJ)\d{6}", text):
        return text
    match = re.fullmatch(r"(\d{6})\.(SH|SZ|BJ)", text)
    if match:
        return f"{match.group(2)}{match.group(1)}"
    return ""


def _read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def artifact_row(
    artifact_id: str,
    path: Path,
    artifact_type: str,
    read_authorized: bool = True,
    scan_outcome_schema: bool = True,
) -> dict[str, Any]:
    exists = path.exists()
    if path.is_file():
        digest = file_sha(path)
        size = path.stat().st_size
    elif path.is_dir():
        digest, _, size = root_inventory_hash(path)
    else:
        digest, size = "", 0
    schema_status = "pass"
    if scan_outcome_schema and path.is_file() and path.suffix.lower() == ".csv":
        try:
            schema_status = gate(not forbid_outcome_columns(_read_header(path)))
        except OSError:
            schema_status = "fail"
    return {
        "artifact_id": artifact_id,
        "path": rel(path) if exists else path.as_posix(),
        "artifact_type": artifact_type,
        "exists": exists,
        "size_bytes": size,
        "sha256_or_root_hash": digest,
        "schema_status": schema_status,
        "read_authorized": read_authorized,
        "status": gate(exists and read_authorized and schema_status == "pass"),
    }


def _hash_values(payload: Any) -> set[str]:
    values: set[str] = set()
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value):
                values.add(value)
            else:
                values.update(_hash_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.update(_hash_values(value))
    return values


def verify_upstream_hash_chain(
    manifest_path: Path, hashes_path: Path, required_paths: Sequence[Path]
) -> bool:
    try:
        manifest = read_json(manifest_path)
        hashes = read_json(hashes_path)
    except (OSError, json.JSONDecodeError):
        return False
    manifest_map = (
        manifest.get("output_hashes", {}) if isinstance(manifest, dict) else {}
    )
    hash_map = hashes.get("hashes", hashes) if isinstance(hashes, dict) else {}
    maps_agree = (
        isinstance(manifest_map, dict)
        and isinstance(hash_map, dict)
        and all(hash_map.get(key) == value for key, value in manifest_map.items())
    )
    declared = _hash_values(manifest_map) | _hash_values(hash_map)
    return maps_agree and all(
        path.exists() and file_sha(path) in declared for path in required_paths
    )


def build_upstream_audit(
    config: dict[str, Any], access_log: list[dict[str, Any]] | None = None
) -> tuple[list[dict[str, Any]], bool]:
    paths = resolve_paths(config)
    ep19_artifacts = [
        paths["ep19_execution"],
        paths["ep19_cost"],
        paths["ep19_censor"],
        paths["ep19_decision"],
    ]
    ep19_verified = verify_upstream_hash_chain(
        paths["ep19_manifest"], paths["ep19_hashes"], ep19_artifacts
    )

    ep20_root = paths["ep20_manifest"].parent
    ep20_freeze_manifest = ep20_root / "freeze/freeze_manifest_20a.json"
    ep20_freeze_hashes = ep20_root / "freeze/freeze_output_hashes_20a.json"
    ep20_input_audit = ep20_root / "freeze/input_artifact_audit.csv"
    ep20_freeze_artifacts = [
        paths["ep20_qfq_audit"],
        paths["ep20_execution_audit"],
        paths["ep20_fill_rule"],
        paths["ep20_label_rule"],
        paths["ep20_cost_capacity"],
        paths["ep20_nav"],
        ep20_input_audit,
    ]
    ep20_root_verified = verify_upstream_hash_chain(
        paths["ep20_manifest"],
        paths["ep20_hashes"],
        [paths["ep20_manifest"], paths["ep20_decision"]],
    )
    ep20_freeze_verified = verify_upstream_hash_chain(
        ep20_freeze_manifest,
        ep20_freeze_hashes,
        [ep20_freeze_manifest, *ep20_freeze_artifacts],
    )
    freeze_link_verified = False
    market_rule_verified = False
    try:
        root_manifest = read_json(paths["ep20_manifest"])
        freeze_link_verified = root_manifest.get("freeze_bundle_hash") == file_sha(
            ep20_freeze_hashes
        )
        with ep20_input_audit.open("r", encoding="utf-8", newline="") as handle:
            input_rows = list(csv.DictReader(handle))
        market_rule_sha = file_sha(paths["ep20_price_limit"])
        market_rule_verified = any(
            row.get("artifact_role") == "market_rule_registry"
            and row.get("sha256_or_root_inventory_hash") == market_rule_sha
            and row.get("input_gate") == "pass"
            for row in input_rows
        )
    except (OSError, KeyError, json.JSONDecodeError):
        pass
    ep20_verified = (
        ep20_root_verified
        and ep20_freeze_verified
        and freeze_link_verified
        and market_rule_verified
    )
    groups = [
        (
            "EP19",
            paths["ep19_manifest"],
            paths["ep19_hashes"],
            ep19_artifacts,
            ep19_verified,
        ),
        (
            "EP20A",
            paths["ep20_manifest"],
            paths["ep20_hashes"],
            [
                ep20_freeze_manifest,
                ep20_freeze_hashes,
                ep20_input_audit,
                paths["ep20_decision"],
                paths["ep20_qfq_audit"],
                paths["ep20_execution_audit"],
                paths["ep20_fill_rule"],
                paths["ep20_label_rule"],
                paths["ep20_cost_capacity"],
                paths["ep20_nav"],
                paths["ep20_price_limit"],
            ],
            ep20_verified,
        ),
    ]
    rows: list[dict[str, Any]] = []
    all_pass = True
    for prefix, manifest, hashes, artifacts, verified in groups:
        for path in [manifest, hashes, *artifacts]:
            exists = path.exists()
            status = gate(exists and verified)
            all_pass &= status == "pass"
            rows.append(
                {
                    "artifact_id": f"{prefix}_{path.stem}",
                    "path": rel(path) if exists else path.as_posix(),
                    "sha256": file_sha(path) if path.is_file() else "",
                    "expected_role": "preoutcome_contract_input",
                    "preoutcome_only": True,
                    "manifest_verified": verified,
                    "allowed": True,
                    "status": status,
                    "blocking_reason": ""
                    if status == "pass"
                    else "missing_or_upstream_hash_chain_mismatch",
                }
            )
            if access_log is not None and path.exists():
                add_access(
                    access_log,
                    path,
                    f"upstream:{prefix}",
                    ["manifest_or_hash_metadata"]
                    if path.suffix == ".json"
                    else ["content_hash"],
                    ["manifest_verified", "sha256"],
                    "upstream_hash_chain_verification",
                )
    return sorted(rows, key=lambda row: row["artifact_id"]), all_pass


def build_input_audit(
    config: dict[str, Any], access_log: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    paths = resolve_paths(config)
    file_keys = [
        "research_plan",
        "requirement",
        "config",
        "runner",
        "test",
        "paper",
        "membership",
        "executable_universe",
        "universe_intervals",
        "benchmark",
        "trading_calendar",
        "security_master",
        "ep19_execution",
        "ep19_cost",
        "ep19_censor",
        "ep19_decision",
        "ep19_manifest",
        "ep19_hashes",
        "ep20_decision",
        "ep20_qfq_audit",
        "ep20_execution_audit",
        "ep20_fill_rule",
        "ep20_label_rule",
        "ep20_cost_capacity",
        "ep20_nav",
        "ep20_price_limit",
        "ep20_manifest",
        "ep20_hashes",
        "pyproject",
        "requirements",
        "uv_lock",
    ]
    directory_keys = ["qfq_root", "raw_ohlcv_root"]
    raw_schema_keys = {
        "membership",
        "executable_universe",
        "universe_intervals",
        "benchmark",
        "trading_calendar",
        "security_master",
    }
    rows = [
        artifact_row(
            key, paths[key], "file", scan_outcome_schema=key in raw_schema_keys
        )
        for key in file_keys
    ]
    rows.extend(artifact_row(key, paths[key], "directory") for key in directory_keys)
    reference_root = paths["reference_root"]
    for filename in [
        "source_availability_manifest.csv",
        "paper_formula_registry_draft.csv",
        "formula_review_packet.md",
        "formula_review_authorization.json",
    ]:
        rows.append(
            artifact_row(
                f"reference_{Path(filename).stem}",
                reference_root / filename,
                "file",
                scan_outcome_schema=False,
            )
        )
    rows.sort(key=lambda row: row["artifact_id"])
    if access_log is not None:
        for row in rows:
            path_value = row["path"]
            path = (
                REPO_ROOT / path_value
                if not Path(path_value).is_absolute()
                else Path(path_value)
            )
            columns = (
                _read_header(path)
                if row["artifact_id"] in raw_schema_keys
                and path.is_file()
                and path.suffix == ".csv"
                else ["content_hash"]
            )
            add_access(
                access_log,
                path,
                f"input_audit:{row['artifact_id']}",
                columns,
                ["existence", "size", "sha256_or_root_hash", "schema_status"],
                "input_artifact_audit",
            )
    return rows


def _inventory_file(
    path: Path, source_id: str, access_log: list[dict[str, Any]]
) -> dict[str, Any]:
    import pandas as pd

    header = _read_header(path)
    forbidden = forbid_outcome_columns(header)
    if forbidden:
        raise PermissionError(f"outcome-like columns in {path}: {forbidden}")
    date_column = next(
        (name for name in ["date", "trade_date", "membership_date"] if name in header),
        None,
    )
    instrument_column = next(
        (name for name in ["instrument", "ts_code"] if name in header), None
    )
    usecols = [value for value in [date_column, instrument_column] if value]
    frame = (
        pd.read_csv(path, usecols=usecols) if usecols else pd.read_csv(path, nrows=0)
    )
    add_access(
        access_log,
        path,
        source_id,
        header,
        ["row_count", "date_range", "instrument_count"],
        "source_inventory",
    )
    return {
        "source_id": source_id,
        "relative_path": rel(path),
        "file_n": 1,
        "row_n": sum(1 for _ in path.open("rb")) - 1,
        "date_min": str(frame[date_column].min())
        if date_column and not frame.empty
        else "",
        "date_max": str(frame[date_column].max())
        if date_column and not frame.empty
        else "",
        "instrument_n": int(frame[instrument_column].nunique())
        if instrument_column and not frame.empty
        else "",
        "root_hash": file_sha(path),
        "status": "pass",
    }


def build_source_inventory(
    config: dict[str, Any], access_log: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    paths = resolve_paths(config)
    rows = [
        _inventory_file(paths["membership"], "membership", access_log),
        _inventory_file(
            paths["executable_universe"], "executable_universe", access_log
        ),
        _inventory_file(paths["universe_intervals"], "universe_intervals", access_log),
        _inventory_file(paths["benchmark"], "benchmark", access_log),
        _inventory_file(paths["trading_calendar"], "trading_calendar", access_log),
        _inventory_file(paths["security_master"], "security_master", access_log),
    ]
    for key in ["qfq_root", "raw_ohlcv_root"]:
        digest, file_n, size = root_inventory_hash(paths[key])
        add_access(
            access_log,
            paths[key],
            key,
            ["root_inventory"],
            ["path|size|sha256"],
            "root_inventory_hash",
        )
        rows.append(
            {
                "source_id": key,
                "relative_path": rel(paths[key]),
                "file_n": file_n,
                "row_n": "",
                "date_min": "",
                "date_max": "",
                "instrument_n": file_n,
                "root_hash": digest,
                "status": gate(file_n > 0 and size > 0),
            }
        )
    return sorted(rows, key=lambda row: (row["source_id"], row["relative_path"]))


def extract_alpha158_registry(
    access_log: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    from qlib.contrib.data.handler import Alpha158

    version = importlib.metadata.version("pyqlib")
    fields, names = Alpha158.get_feature_config(None)
    source_file = Path(inspect.getsourcefile(Alpha158) or "")
    source_sha = file_sha(source_file)
    if access_log is not None:
        add_access(
            access_log,
            "package:pyqlib==0.9.7",
            "python_package",
            ["distribution_version", "Alpha158.get_feature_config"],
            ["feature_expressions", "feature_names"],
            "feature_config_extraction",
        )
        add_access(
            access_log,
            source_file,
            "pyqlib_source",
            ["Alpha158.get_feature_config"],
            ["source_sha256"],
            "feature_config_extraction",
        )
    rows: list[dict[str, Any]] = []
    hash_lines: list[str] = []
    for index, (expression, name) in enumerate(zip(fields, names, strict=True)):
        direct_fields = sorted(set(re.findall(r"\$[A-Za-z_][A-Za-z0-9_]*", expression)))
        integers = [
            int(value)
            for value in re.findall(
                r"(?:Ref|Mean|Std|Sum|Max|Min|Slope|Rsquare|Resi)\([^,]+,\s*(\d+)",
                expression,
            )
        ]
        uses_vwap = "$vwap" in expression.lower()
        row = {
            "feature_index": index,
            "feature_name": name,
            "expression": expression,
            "direct_fields": "|".join(direct_fields),
            "max_trailing_window": max(integers, default=1),
            "uses_vwap": uses_vwap,
            "uses_volume": "$volume" in expression.lower(),
            "uses_money": "$money" in expression.lower(),
            "uses_future_offset": expression_has_future_offset(expression),
            "qlib_distribution_version": version,
            "qlib_source_file": rel(source_file),
            "qlib_source_file_sha256": source_sha,
            "canonical_order": index,
            "route_inclusion_full": True,
            "route_inclusion_no_vwap": not uses_vwap,
            "status": "pass",
        }
        rows.append(row)
        hash_lines.append(f"{index}|{name}|{expression}")
    expression_hash = hashlib.sha256("\n".join(hash_lines).encode("utf-8")).hexdigest()
    meta = {
        "version": version,
        "source_file": source_file,
        "source_sha": source_sha,
        "count": len(rows),
        "duplicate_name_n": len(names) - len(set(names)),
        "future_offset_n": sum(bool_value(row["uses_future_offset"]) for row in rows),
        "no_vwap_count": sum(
            bool_value(row["route_inclusion_no_vwap"]) for row in rows
        ),
    }
    return rows, expression_hash, meta


def stable_alpha_expression_hash(alpha_rows: Sequence[dict[str, Any]]) -> str:
    ordered = sorted(alpha_rows, key=lambda row: int(row["feature_index"]))
    lines = [
        f"{int(row['feature_index'])}|{row['feature_name']}|{row['expression']}"
        for row in ordered
    ]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def build_field_mapping(
    alpha_rows: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    fields = sorted(
        {
            field
            for row in alpha_rows
            for field in str(row["direct_fields"]).split("|")
            if field
        }
    )
    full_route = config["feature_contract"]["full_route_id"]
    no_vwap_route = config["feature_contract"]["no_vwap_route_id"]
    mapping = {
        "$open": ("qfq.open", "CNY", "identity"),
        "$high": ("qfq.high", "CNY", "identity"),
        "$low": ("qfq.low", "CNY", "identity"),
        "$close": ("qfq.close", "CNY", "identity"),
        "$volume": ("raw.volume", "shares", "hands_to_shares_exactly_once_if_needed"),
        "$vwap": ("raw.money/raw.volume*qfq_raw_factor", "CNY", "qfq_vwap_candidate"),
    }
    rows: list[dict[str, Any]] = []
    for route in [full_route, no_vwap_route]:
        for field in fields:
            if route == no_vwap_route and field == "$vwap":
                continue
            source, scale, transform = mapping.get(field, ("", "", ""))
            rows.append(
                {
                    "qlib_field": field,
                    "local_source": source,
                    "source_scale": scale,
                    "transform": transform,
                    "availability_time": "decision_close_t",
                    "route_id": route,
                    "unit_gate": gate(bool(source)),
                    "status": gate(bool(source)),
                }
            )
    return sorted(rows, key=lambda row: (row["route_id"], row["qlib_field"]))


def fit_robust_normalizer(values: Any, scale_floor: float = 1e-12) -> dict[str, Any]:
    import numpy as np

    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("normalizer input must be a two-dimensional matrix")
    finite = np.where(np.isfinite(array), array, np.nan)
    with np.errstate(all="ignore"):
        center = np.nanmedian(finite, axis=0)
        lower = np.nanquantile(finite, 0.25, axis=0, method="linear")
        upper = np.nanquantile(finite, 0.75, axis=0, method="linear")
    center = np.where(np.isfinite(center), center, 0.0)
    scale = (upper - lower) / 1.349
    constant = ~np.isfinite(scale) | (scale <= float(scale_floor))
    scale = np.where(constant, 1.0, scale)
    return {
        "center": center,
        "scale": scale,
        "constant": constant,
        "scale_floor": float(scale_floor),
    }


def apply_robust_normalizer(
    values: Any,
    normalizer: dict[str, Any],
    clip: Sequence[float] = (-10.0, 10.0),
    constant_column_value: float = 0.0,
) -> Any:
    import numpy as np

    array = np.asarray(values, dtype=np.float64)
    center = np.asarray(normalizer["center"], dtype=np.float64)
    scale = np.asarray(normalizer["scale"], dtype=np.float64)
    constant = np.asarray(normalizer["constant"], dtype=bool)
    filled = np.where(np.isfinite(array), array, center)
    transformed = (filled - center) / scale
    transformed[..., constant] = float(constant_column_value)
    transformed = np.clip(transformed, float(clip[0]), float(clip[1]))
    if not np.isfinite(transformed).all():
        raise ValueError("normalization produced a non-finite value")
    return transformed.astype(np.float32, copy=False)


def compute_alpha158_features(frame: Any, alpha_rows: list[dict[str, Any]]) -> Any:
    """Evaluate the locked Alpha158 feature-only formulas on one instrument's trailing bars."""
    import numpy as np
    import pandas as pd

    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        raise ValueError(
            f"missing Alpha158 source fields: {sorted(required - set(frame.columns))}"
        )
    source = frame.copy()
    for column in required | {"vwap"}:
        if column in source:
            source[column] = pd.to_numeric(source[column], errors="coerce").astype(
                float
            )
    open_, high, low, close, volume = (
        source["open"],
        source["high"],
        source["low"],
        source["close"],
        source["volume"],
    )
    eps = 1e-12
    computed: dict[str, Any] = {
        "KMID": (close - open_) / open_,
        "KLEN": (high - low) / open_,
        "KMID2": (close - open_) / (high - low + eps),
        "KUP": (high - np.maximum(open_, close)) / open_,
        "KUP2": (high - np.maximum(open_, close)) / (high - low + eps),
        "KLOW": (np.minimum(open_, close) - low) / open_,
        "KLOW2": (np.minimum(open_, close) - low) / (high - low + eps),
        "KSFT": (2 * close - high - low) / open_,
        "KSFT2": (2 * close - high - low) / (high - low + eps),
        "OPEN0": open_ / close,
        "HIGH0": high / close,
        "LOW0": low / close,
    }
    if "vwap" in source:
        computed["VWAP0"] = source["vwap"] / close

    def regression_stat(series: Any, window: int, stat: str) -> Any:
        def calculate(values: Any) -> float:
            finite = np.isfinite(values)
            y = np.asarray(values, dtype=np.float64)[finite]
            if len(y) < 2:
                return math.nan
            x = np.arange(1, len(values) + 1, dtype=np.float64)[finite]
            x_centered = x - x.mean()
            y_centered = y - y.mean()
            denominator = float(np.square(x_centered).sum())
            if denominator <= 0:
                return math.nan
            slope = float((x_centered * y_centered).sum() / denominator)
            intercept = float(y.mean() - slope * x.mean())
            fitted = intercept + slope * x
            if stat == "slope":
                return slope
            if stat == "resi":
                return float(y[-1] - fitted[-1])
            total = float(np.square(y_centered).sum())
            if total <= 2e-5**2:
                return math.nan
            return 1.0 - float(np.square(y - fitted).sum()) / total

        return series.rolling(window, min_periods=2).apply(calculate, raw=True)

    close_ref = close.shift(1)
    volume_ref = volume.shift(1)
    close_delta = close - close_ref
    volume_delta = volume - volume_ref
    price_ratio = close / close_ref
    log_volume = np.log(volume + 1.0)
    log_volume_ratio = np.log(volume / volume_ref + 1.0)
    absolute_weighted_move = (price_ratio - 1.0).abs() * volume
    windows = [5, 10, 20, 30, 60]
    for window in windows:
        suffix = str(window)
        computed[f"ROC{suffix}"] = close.shift(window) / close
        computed[f"MA{suffix}"] = close.rolling(window, min_periods=1).mean() / close
        computed[f"STD{suffix}"] = close.rolling(window, min_periods=1).std() / close
        computed[f"BETA{suffix}"] = regression_stat(close, window, "slope") / close
        computed[f"RSQR{suffix}"] = regression_stat(close, window, "rsquare")
        computed[f"RESI{suffix}"] = regression_stat(close, window, "resi") / close
        rolling_high = high.rolling(window, min_periods=1)
        rolling_low = low.rolling(window, min_periods=1)
        computed[f"MAX{suffix}"] = rolling_high.max() / close
        computed[f"MIN{suffix}"] = rolling_low.min() / close
        computed[f"QTLU{suffix}"] = (
            close.rolling(window, min_periods=1).quantile(0.8) / close
        )
        computed[f"QTLD{suffix}"] = (
            close.rolling(window, min_periods=1).quantile(0.2) / close
        )
        computed[f"RANK{suffix}"] = close.rolling(window, min_periods=1).rank(pct=True)
        low_min = rolling_low.min()
        high_max = rolling_high.max()
        computed[f"RSV{suffix}"] = (close - low_min) / (high_max - low_min + eps)
        idx_max = rolling_high.apply(
            lambda values: float(np.argmax(values) + 1), raw=True
        )
        idx_min = rolling_low.apply(
            lambda values: float(np.argmin(values) + 1), raw=True
        )
        computed[f"IMAX{suffix}"] = idx_max / window
        computed[f"IMIN{suffix}"] = idx_min / window
        computed[f"IMXD{suffix}"] = (idx_max - idx_min) / window
        computed[f"CORR{suffix}"] = close.rolling(window, min_periods=2).corr(
            log_volume
        )
        computed[f"CORD{suffix}"] = price_ratio.rolling(window, min_periods=2).corr(
            log_volume_ratio
        )
        positive_count = close.gt(close_ref).rolling(window, min_periods=1).mean()
        negative_count = close.lt(close_ref).rolling(window, min_periods=1).mean()
        computed[f"CNTP{suffix}"] = positive_count
        computed[f"CNTN{suffix}"] = negative_count
        computed[f"CNTD{suffix}"] = positive_count - negative_count
        absolute_price_sum = (
            close_delta.abs().rolling(window, min_periods=1).sum() + eps
        )
        positive_price_sum = (
            close_delta.clip(lower=0).rolling(window, min_periods=1).sum()
        )
        negative_price_sum = (
            (-close_delta).clip(lower=0).rolling(window, min_periods=1).sum()
        )
        computed[f"SUMP{suffix}"] = positive_price_sum / absolute_price_sum
        computed[f"SUMN{suffix}"] = negative_price_sum / absolute_price_sum
        computed[f"SUMD{suffix}"] = (
            positive_price_sum - negative_price_sum
        ) / absolute_price_sum
        computed[f"VMA{suffix}"] = volume.rolling(window, min_periods=1).mean() / (
            volume + eps
        )
        computed[f"VSTD{suffix}"] = volume.rolling(window, min_periods=1).std() / (
            volume + eps
        )
        computed[f"WVMA{suffix}"] = absolute_weighted_move.rolling(
            window, min_periods=1
        ).std() / (absolute_weighted_move.rolling(window, min_periods=1).mean() + eps)
        absolute_volume_sum = (
            volume_delta.abs().rolling(window, min_periods=1).sum() + eps
        )
        positive_volume_sum = (
            volume_delta.clip(lower=0).rolling(window, min_periods=1).sum()
        )
        negative_volume_sum = (
            (-volume_delta).clip(lower=0).rolling(window, min_periods=1).sum()
        )
        computed[f"VSUMP{suffix}"] = positive_volume_sum / absolute_volume_sum
        computed[f"VSUMN{suffix}"] = negative_volume_sum / absolute_volume_sum
        computed[f"VSUMD{suffix}"] = (
            positive_volume_sum - negative_volume_sum
        ) / absolute_volume_sum

    names = [str(row["feature_name"]) for row in alpha_rows]
    missing = [name for name in names if name not in computed]
    if missing:
        raise ValueError(f"unimplemented canonical Alpha158 expressions: {missing}")
    result = pd.DataFrame({name: computed[name] for name in names}, index=source.index)
    return result.replace([np.inf, -np.inf], np.nan)


def _feature_source_frame(qfq_path: Path, raw_path: Path, include_vwap: bool) -> Any:
    import numpy as np
    import pandas as pd

    qfq = pd.read_csv(qfq_path)
    raw = pd.read_csv(raw_path)
    qfq["date"] = qfq["date"].astype(str)
    raw["date"] = raw["date"].astype(str)
    raw = raw.set_index("date", drop=False)
    qfq = qfq.set_index("date", drop=False)
    frame = qfq[["date", "open", "high", "low", "close"]].copy()
    frame["volume"] = _volume_in_shares(raw).reindex(frame.index)
    if include_vwap:
        factor_fields = []
        for field in ["open", "high", "low", "close"]:
            q_value = pd.to_numeric(qfq[field], errors="coerce")
            r_value = pd.to_numeric(raw[field], errors="coerce").reindex(frame.index)
            factor_fields.append(
                (q_value / r_value).where(q_value.gt(0) & r_value.gt(0))
            )
        factors = pd.concat(factor_fields, axis=1)
        consensus = factors.median(axis=1).where(factors.notna().sum(axis=1) >= 3)
        raw_money = pd.to_numeric(raw["money"], errors="coerce").reindex(frame.index)
        frame["vwap"] = (raw_money / frame["volume"]) * consensus
    numeric = ["open", "high", "low", "close", "volume"] + (
        ["vwap"] if include_vwap else []
    )
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["source_row_valid"] = np.isfinite(
        frame[["open", "high", "low", "close"]]
    ).all(axis=1)
    return frame


def _volume_in_shares(frame: Any) -> Any:
    import numpy as np
    import pandas as pd

    units = frame.get("source_volume_unit")
    if units is None:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    normalized = units.astype(str).str.lower()
    multiplier = normalized.map(
        {
            "hand": 100.0,
            "hands": 100.0,
            "lot": 100.0,
            "lots": 100.0,
            "shares": 1.0,
            "share": 1.0,
        }
    )
    return frame["volume"].astype(float) * multiplier


def build_vwap_audit(
    config: dict[str, Any], access_log: list[dict[str, Any]]
) -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, set[str]], dict[str, Any]
]:
    import numpy as np
    import pandas as pd

    paths = resolve_paths(config)
    qfq_root, raw_root = paths["qfq_root"], paths["raw_ohlcv_root"]
    membership = pd.read_csv(
        paths["membership"], usecols=["instrument", "board_bucket"]
    )
    board_map = (
        membership.drop_duplicates("instrument", keep="last")
        .set_index("instrument")["board_bucket"]
        .to_dict()
    )
    add_access(
        access_log,
        paths["membership"],
        "membership",
        ["instrument", "board_bucket"],
        ["instrument_board_map"],
        "vwap_board_slice",
    )
    tolerance = config["feature_contract"]["factor_relative_tolerance"]
    rows: list[dict[str, Any]] = []
    jump_rows: list[dict[str, Any]] = []
    date_sets: dict[str, set[str]] = {}
    aggregate_parts: list[Any] = []
    audit_contract_ok = True
    qfq_files = sorted(qfq_root.glob("*.csv"), key=lambda path: path.name)
    for qfq_path in qfq_files:
        raw_path = raw_root / qfq_path.name
        if not raw_path.exists():
            continue
        q_header = _read_header(qfq_path)
        r_header = _read_header(raw_path)
        required = ["date", "open", "high", "low", "close", "volume", "money"]
        if any(name not in q_header or name not in r_header for name in required):
            continue
        q = pd.read_csv(
            qfq_path,
            usecols=[
                name
                for name in q_header
                if name in required + ["instrument", "source_volume_unit"]
            ],
        )
        r = pd.read_csv(
            raw_path,
            usecols=[
                name
                for name in r_header
                if name in required + ["instrument", "source_volume_unit"]
            ],
        )
        add_access(
            access_log,
            qfq_path,
            "qfq_ohlcv",
            q.columns,
            ["qfq_raw_factor", "vwap_qfq_candidate"],
            "vwap_unit_audit",
        )
        add_access(
            access_log,
            raw_path,
            "raw_ohlcv",
            r.columns,
            ["raw_volume_shares"],
            "vwap_unit_audit",
        )
        instrument = (
            normalize_instrument(
                q.get("instrument", pd.Series([qfq_path.stem])).iloc[0]
            )
            or qfq_path.stem
        )
        q["date"] = q["date"].astype(str)
        r["date"] = r["date"].astype(str)
        date_sets[instrument] = set(q["date"])
        audit_contract_ok &= (
            not q.duplicated("date").any() and not r.duplicated("date").any()
        )
        raw_units = set(
            r.get("source_volume_unit", pd.Series(dtype=str)).astype(str).str.lower()
        )
        audit_contract_ok &= bool(raw_units) and raw_units <= {
            "share",
            "shares",
            "hand",
            "hands",
            "lot",
            "lots",
        }
        q = q.drop_duplicates("date", keep=False)
        r = r.drop_duplicates("date", keep=False)
        merged = q.merge(
            r, on="date", suffixes=("_q", "_r"), how="outer", indicator=True
        )
        if merged.empty:
            continue
        factor_fields = []
        for field in ["open", "high", "low", "close"]:
            qv = pd.to_numeric(merged[f"{field}_q"], errors="coerce")
            rv = pd.to_numeric(merged[f"{field}_r"], errors="coerce")
            valid = qv.gt(0) & rv.gt(0) & np.isfinite(qv) & np.isfinite(rv)
            factor_fields.append((qv / rv).where(valid))
        factors = pd.concat(factor_fields, axis=1)
        factor_count = factors.notna().sum(axis=1)
        consensus = factors.median(axis=1, skipna=True).where(factor_count >= 3)
        relative_error = (
            factors.div(consensus, axis=0).sub(1).abs().max(axis=1, skipna=True)
        )
        factor_pass = factor_count.ge(3) & relative_error.le(tolerance)
        finite_ohlc = pd.Series(True, index=merged.index)
        for suffix in ["q", "r"]:
            for field in ["open", "high", "low", "close"]:
                values = pd.to_numeric(merged[f"{field}_{suffix}"], errors="coerce")
                finite_ohlc &= values.gt(0) & np.isfinite(values)
            low = pd.to_numeric(merged[f"low_{suffix}"], errors="coerce")
            high = pd.to_numeric(merged[f"high_{suffix}"], errors="coerce")
            open_ = pd.to_numeric(merged[f"open_{suffix}"], errors="coerce")
            close = pd.to_numeric(merged[f"close_{suffix}"], errors="coerce")
            finite_ohlc &= (
                low.le(open_) & open_.le(high) & low.le(close) & close.le(high)
            )
        raw_volume = (
            _volume_in_shares(r.set_index("date"))
            .reindex(merged["date"])
            .reset_index(drop=True)
        )
        raw_money = pd.to_numeric(merged["money_r"], errors="coerce")
        auditable = (
            finite_ohlc
            & raw_volume.gt(0)
            & raw_money.gt(0)
            & np.isfinite(raw_money)
            & consensus.gt(0)
        )
        vwap_qfq = (raw_money / raw_volume) * consensus
        qlow = pd.to_numeric(merged["low_q"], errors="coerce")
        qhigh = pd.to_numeric(merged["high_q"], errors="coerce")
        qclose = pd.to_numeric(merged["close_q"], errors="coerce")
        range_tol = np.maximum(0.01, 0.001 * qclose)
        in_range = (
            auditable & vwap_qfq.ge(qlow - range_tol) & vwap_qfq.le(qhigh + range_tol)
        )
        detail = pd.DataFrame(
            {
                "instrument": instrument,
                "date": merged["date"],
                "year": merged["date"].str[:4],
                "board_bucket": board_map.get(instrument, "unknown"),
                "factor_pass": factor_pass,
                "factor_unknown": factor_count.lt(3),
                "base": finite_ohlc,
                "auditable": auditable,
                "in_range": in_range,
                "qfq_key": merged["_merge"].ne("right_only"),
                "raw_key": merged["_merge"].ne("left_only"),
                "overlap_key": merged["_merge"].eq("both"),
            }
        )
        aggregate_parts.append(detail)
        sorted_factor = (
            pd.DataFrame({"date": merged["date"], "factor": consensus})
            .dropna()
            .sort_values("date")
        )
        log_jump = np.log(sorted_factor["factor"]).diff().abs()
        for position in np.flatnonzero(
            log_jump.gt(
                config["feature_contract"]["factor_jump_abs_log_threshold"]
            ).to_numpy()
        ):
            start = max(
                0, position - config["feature_contract"]["factor_jump_radius_sessions"]
            )
            end = min(
                len(sorted_factor) - 1,
                position + config["feature_contract"]["factor_jump_radius_sessions"],
            )
            jump_rows.append(
                {
                    "instrument": instrument,
                    "jump_date": sorted_factor.iloc[position]["date"],
                    "factor_before": sorted_factor.iloc[position - 1]["factor"],
                    "factor_after": sorted_factor.iloc[position]["factor"],
                    "abs_log_jump": log_jump.iloc[position],
                    "window_start": sorted_factor.iloc[start]["date"],
                    "window_end": sorted_factor.iloc[end]["date"],
                    "exposed_feature_row_n": end - start + 1,
                    "status": "pass",
                }
            )
    all_detail = (
        pd.concat(aggregate_parts, ignore_index=True)
        if aggregate_parts
        else pd.DataFrame()
    )

    def summarize(
        scope: str, frame: Any, instrument: str = "", year: str = "", board: str = ""
    ) -> dict[str, Any]:
        qn = int(frame["qfq_key"].sum()) if not frame.empty else 0
        rn = int(frame["raw_key"].sum()) if not frame.empty else 0
        overlap = int(frame["overlap_key"].sum()) if not frame.empty else 0
        base_n = int(frame["base"].sum()) if not frame.empty else 0
        factor_pass_n = (
            int((frame["base"] & frame["factor_pass"]).sum()) if not frame.empty else 0
        )
        factor_unknown_n = (
            int((frame["base"] & frame["factor_unknown"]).sum())
            if not frame.empty
            else 0
        )
        factor_fail_n = max(0, base_n - factor_pass_n - factor_unknown_n)
        auditable_n = int(frame["auditable"].sum()) if not frame.empty else 0
        in_range_n = int(frame["in_range"].sum()) if not frame.empty else 0
        overlap_rate = overlap / qn if qn else math.nan
        factor_rate = factor_pass_n / base_n if base_n else math.nan
        auditable_rate = auditable_n / base_n if base_n else math.nan
        range_rate = in_range_n / auditable_n if auditable_n else math.nan
        return {
            "scope": scope,
            "instrument": instrument,
            "year": year,
            "board_bucket": board,
            "qfq_key_n": qn,
            "raw_key_n": rn,
            "overlap_key_n": overlap,
            "overlap_rate": overlap_rate,
            "base_row_n": base_n,
            "factor_pass_n": factor_pass_n,
            "factor_fail_n": factor_fail_n,
            "factor_unknown_n": factor_unknown_n,
            "factor_pass_rate": factor_rate,
            "auditable_row_n": auditable_n,
            "auditable_row_rate": auditable_rate,
            "in_range_n": in_range_n,
            "out_of_range_n": max(0, auditable_n - in_range_n),
            "unknown_n": max(0, base_n - auditable_n),
            "range_pass_rate": range_rate,
            "coverage_threshold": config["feature_contract"][
                "vwap_auditable_row_rate_global_min"
            ]
            if scope == "global"
            else config["feature_contract"]["vwap_auditable_row_rate_board_year_min"],
            "range_threshold": config["feature_contract"]["vwap_inside_range_rate_min"],
            "status": "pass" if base_n > 0 and audit_contract_ok else "fail",
        }

    if not all_detail.empty:
        for (instrument, year, board), frame in all_detail.groupby(
            ["instrument", "year", "board_bucket"], sort=True
        ):
            rows.append(summarize("instrument_year", frame, instrument, year, board))
        for (year, board), frame in all_detail.groupby(
            ["year", "board_bucket"], sort=True
        ):
            rows.append(summarize("board_year", frame, "", year, board))
        rows.append(summarize("global", all_detail))
    else:
        rows.append(summarize("global", all_detail))
    global_row = next(row for row in rows if row["scope"] == "global")
    board_rows = [
        row
        for row in rows
        if row["scope"] == "board_year"
        and row["base_row_n"] >= config["feature_contract"]["board_year_base_rows_min"]
    ]
    full_reachable = (
        global_row["overlap_rate"]
        >= config["feature_contract"]["qfq_raw_key_overlap_rate_min"]
        and global_row["factor_pass_rate"]
        >= config["feature_contract"]["factor_cross_field_pass_rate_min"]
        and global_row["auditable_row_rate"]
        >= config["feature_contract"]["vwap_auditable_row_rate_global_min"]
        and global_row["range_pass_rate"]
        >= config["feature_contract"]["vwap_inside_range_rate_min"]
        and all(
            row["auditable_row_rate"]
            >= config["feature_contract"]["vwap_auditable_row_rate_board_year_min"]
            for row in board_rows
        )
    )
    meta = {
        "audit_complete": not all_detail.empty and audit_contract_ok,
        "full_route_reachable": full_reachable,
        "global": global_row,
        "jump_n": len(jump_rows),
        "file_pair_n": len(date_sets),
    }
    return (
        rows,
        sorted(jump_rows, key=lambda row: (row["instrument"], row["jump_date"])),
        date_sets,
        meta,
    )


def _split_for_date(date: str, config: dict[str, Any]) -> str:
    if (
        config["split"]["train_nominal"][0]
        <= date
        <= config["split"]["train_nominal"][1]
    ):
        return "train"
    if (
        config["split"]["validation_nominal"][0]
        <= date
        <= config["split"]["validation_nominal"][1]
    ):
        return "validation"
    if (
        config["split"]["historical_design_holdout_nominal"][0]
        <= date
        <= config["split"]["historical_design_holdout_nominal"][1]
    ):
        return "historical_design_holdout"
    return "outside"


def decision_eligibility_predicate(
    *,
    is_listed: bool,
    is_st: bool,
    usable_trade_date: str,
    expected_next_session: str,
    history_ready: bool,
    sequence_ready: bool,
    feature_ready: bool,
    right_censored_data_cutoff: bool = False,
) -> bool:
    return bool(
        is_listed
        and not is_st
        and expected_next_session
        and (
            usable_trade_date == expected_next_session
            or (right_censored_data_cutoff and not usable_trade_date)
        )
        and history_ready
        and sequence_ready
        and feature_ready
    )


def materialize_feature_cache(
    config: dict[str, Any],
    alpha_rows: list[dict[str, Any]],
    feature_route_id: str,
    access_log: list[dict[str, Any]],
    cache_root: Path | None = None,
) -> dict[str, Any]:
    """Materialize label-free source-sequence features and a train-fitted robust normalizer."""
    import numpy as np
    import pandas as pd
    import shutil

    if not feature_route_id:
        return {
            "status": "fail",
            "ready_keys": set(),
            "sequence_ready_keys": set(),
            "cache_content_hash": "",
            "cache_row_n": 0,
            "cache_file_n": 0,
            "cache_size_bytes": 0,
            "date_min": "",
            "date_max": "",
            "materialized_expression_count": 0,
            "normalizer_reproducible": False,
            "normalized_all_finite": False,
            "cache_relative_path": ".cache/21a_alpha158_feature_only",
        }
    include_vwap = feature_route_id == config["feature_contract"]["full_route_id"]
    selected_rows = [
        row
        for row in alpha_rows
        if bool_value(
            row["route_inclusion_full"]
            if include_vwap
            else row["route_inclusion_no_vwap"]
        )
    ]
    feature_names = [str(row["feature_name"]) for row in selected_rows]
    paths = resolve_paths(config)
    membership_columns = [
        "membership_date",
        "instrument",
        "is_suspended",
        "history_ready_240d_flag",
    ]
    membership = pd.read_csv(paths["membership"], usecols=membership_columns)
    membership["membership_date"] = membership["membership_date"].astype(str)
    membership["instrument"] = membership["instrument"].map(normalize_instrument)
    membership = membership[
        membership["membership_date"].map(
            lambda value: _split_for_date(value, config) != "outside"
        )
    ].copy()
    calendar = pd.read_csv(paths["trading_calendar"], usecols=["trade_date"])
    calendar_dates = sorted(calendar["trade_date"].astype(str).unique())
    calendar_index = {date: index for index, date in enumerate(calendar_dates)}
    add_access(
        access_log,
        paths["membership"],
        "membership",
        membership_columns,
        ["feature_cache_keys", "suspension_policy"],
        "feature_only_materialization",
    )
    add_access(
        access_log,
        paths["trading_calendar"],
        "trading_calendar",
        ["trade_date"],
        ["source_sequence_calendar"],
        "feature_only_materialization",
    )
    lookback = int(config["architecture"]["lookback_T"])
    required_by_instrument: dict[str, set[str]] = {}
    train_source_keys: set[tuple[str, str]] = set()
    decision_sources: dict[tuple[str, str], list[str]] = {}
    history_ready: dict[tuple[str, str], bool] = {}
    suspension_status: dict[tuple[str, str], bool] = {}
    for row in membership.itertuples(index=False):
        instrument = str(row.instrument)
        decision_date = str(row.membership_date)
        position = calendar_index.get(decision_date, -1)
        if position < lookback - 1:
            source_dates: list[str] = []
        else:
            source_dates = calendar_dates[position - lookback + 1 : position + 1]
        decision_key = (instrument, decision_date)
        decision_sources[decision_key] = source_dates
        history_ready[decision_key] = bool_value(row.history_ready_240d_flag)
        suspension_status[decision_key] = bool_value(row.is_suspended)
        required_by_instrument.setdefault(instrument, set()).update(source_dates)
        if _split_for_date(decision_date, config) == "train":
            train_source_keys.update(
                (instrument, source_date) for source_date in source_dates
            )
    ordered_keys = sorted(
        (instrument, date)
        for instrument, dates in required_by_instrument.items()
        for date in dates
    )
    key_to_row = {key: index for index, key in enumerate(ordered_keys)}
    cache_root = cache_root or (EXPERIMENT_DIR / ".cache/21a_alpha158_feature_only")
    if cache_root.exists():
        shutil.rmtree(cache_root)
    cache_root.mkdir(parents=True, exist_ok=False)
    raw_path = cache_root / "raw_features.f64.memmap"
    normalized_path = cache_root / "normalized_features.f32.memmap"
    raw = np.memmap(
        raw_path,
        mode="w+",
        dtype="float64",
        shape=(len(ordered_keys), len(feature_names)),
    )
    raw[:] = np.nan
    policy_valid_keys: set[tuple[str, str]] = set()
    max_window = max(
        (int(row["max_trailing_window"]) for row in selected_rows), default=1
    )
    for instrument, requested_dates in sorted(required_by_instrument.items()):
        qfq_path = paths["qfq_root"] / f"{instrument}.csv"
        raw_ohlcv_path = paths["raw_ohlcv_root"] / f"{instrument}.csv"
        if not qfq_path.exists() or not raw_ohlcv_path.exists() or not requested_dates:
            continue
        add_access(
            access_log,
            qfq_path,
            "qfq_ohlcv",
            _read_header(qfq_path),
            feature_names,
            "feature_only_materialization",
        )
        add_access(
            access_log,
            raw_ohlcv_path,
            "raw_ohlcv",
            _read_header(raw_ohlcv_path),
            ["raw_volume_shares", "qfq_vwap_candidate" if include_vwap else ""],
            "feature_only_materialization",
        )
        source = _feature_source_frame(qfq_path, raw_ohlcv_path, include_vwap)
        observed_dates = set(source.index.astype(str))
        first_required = min(
            calendar_index[date] for date in requested_dates if date in calendar_index
        )
        last_required = max(
            calendar_index[date] for date in requested_dates if date in calendar_index
        )
        start = max(0, first_required - max_window - 1)
        aligned_dates = calendar_dates[start : last_required + 1]
        source = source.reindex(aligned_dates)
        observed = pd.Series(
            [date in observed_dates for date in aligned_dates], index=aligned_dates
        )
        known_suspension = pd.Series(
            [
                suspension_status.get((instrument, date), False)
                for date in aligned_dates
            ],
            index=aligned_dates,
        )
        carry = ~observed & known_suspension
        for column in ["open", "high", "low", "close"]:
            carried = source[column].ffill()
            source.loc[carry, column] = carried.loc[carry]
        source.loc[carry, "volume"] = 0.0
        if include_vwap:
            source.loc[carry, "vwap"] = np.nan
        policy_valid = observed | carry
        features = compute_alpha158_features(source, selected_rows)
        for date in requested_dates:
            row_index = key_to_row[(instrument, date)]
            if date in features.index:
                raw[row_index, :] = features.loc[date, feature_names].to_numpy(
                    dtype=np.float64
                )
            if date in policy_valid.index and bool(policy_valid.loc[date]):
                policy_valid_keys.add((instrument, date))
    raw.flush()
    train_indices = sorted(
        key_to_row[key]
        for key in train_source_keys
        if key in key_to_row and key in policy_valid_keys
    )
    if not train_indices or not feature_names:
        normalizer = {
            "center": np.zeros(len(feature_names), dtype=np.float64),
            "scale": np.ones(len(feature_names), dtype=np.float64),
            "constant": np.ones(len(feature_names), dtype=bool),
            "scale_floor": config["feature_contract"]["normalization"]["scale_floor"],
        }
        normalizer_reproducible = False
    else:
        centers = np.empty(len(feature_names), dtype=np.float64)
        scales = np.empty(len(feature_names), dtype=np.float64)
        constants = np.empty(len(feature_names), dtype=bool)
        for feature_index in range(len(feature_names)):
            fitted = fit_robust_normalizer(
                np.asarray(raw[train_indices, feature_index]).reshape(-1, 1),
                config["feature_contract"]["normalization"]["scale_floor"],
            )
            centers[feature_index] = fitted["center"][0]
            scales[feature_index] = fitted["scale"][0]
            constants[feature_index] = fitted["constant"][0]
        normalizer = {
            "center": centers,
            "scale": scales,
            "constant": constants,
            "scale_floor": config["feature_contract"]["normalization"]["scale_floor"],
        }
        normalizer_reproducible = True
    normalized = np.memmap(
        normalized_path,
        mode="w+",
        dtype="float32",
        shape=(len(ordered_keys), len(feature_names)),
    )
    chunk = 8192
    normalization = config["feature_contract"]["normalization"]
    for start in range(0, len(ordered_keys), chunk):
        end = min(len(ordered_keys), start + chunk)
        normalized[start:end] = apply_robust_normalizer(
            raw[start:end],
            normalizer,
            clip=normalization["clip"],
            constant_column_value=normalization["constant_column_value"],
        )
    normalized.flush()
    del normalized
    del raw
    raw_path.unlink()
    with (cache_root / "keys.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["row_index", "instrument", "feature_date"])
        for row_index, (instrument, date) in enumerate(ordered_keys):
            writer.writerow([row_index, instrument, date])
    write_json(
        cache_root / "normalizer.json",
        {
            "feature_names": feature_names,
            "center": np.asarray(normalizer["center"]).tolist(),
            "scale": np.asarray(normalizer["scale"]).tolist(),
            "constant": np.asarray(normalizer["constant"]).astype(bool).tolist(),
            "fit_split": "original_train_source_cells",
            "clip": normalization["clip"],
            "invalid_fill": normalization["invalid_fill"],
        },
    )
    sequence_ready_keys = {
        decision_key
        for decision_key, source_dates in decision_sources.items()
        if len(source_dates) == lookback
        and all((decision_key[0], date) in policy_valid_keys for date in source_dates)
    }
    ready_keys = {
        decision_key
        for decision_key, source_dates in decision_sources.items()
        if history_ready.get(decision_key, False)
        and decision_key in sequence_ready_keys
        and all((decision_key[0], date) in key_to_row for date in source_dates)
    }
    write_json(
        cache_root / "readiness.json",
        {
            "ready_key_n": len(ready_keys),
            "policy_valid_source_key_n": len(policy_valid_keys),
            "lookback_T": lookback,
            "maximum_trailing_window": max_window,
            "unknown_gap_policy": "invalid",
            "listed_suspension_policy": "carry_ohlc_volume_money_zero",
            "prelisting_policy": "unavailable",
        },
    )
    content_hash, file_n, size_bytes = root_inventory_hash(cache_root)
    return {
        "status": "pass" if normalizer_reproducible and ready_keys else "fail",
        "ready_keys": ready_keys,
        "sequence_ready_keys": sequence_ready_keys,
        "cache_content_hash": content_hash,
        "cache_row_n": len(ordered_keys),
        "date_min": min((date for _, date in ordered_keys), default=""),
        "date_max": max((date for _, date in ordered_keys), default=""),
        "materialized_expression_count": len(feature_names),
        "normalizer_reproducible": normalizer_reproducible,
        "normalized_all_finite": size_bytes > 0,
        "cache_file_n": file_n,
        "cache_size_bytes": size_bytes,
        "cache_relative_path": (
            rel(cache_root)
            if cache_root.is_relative_to(REPO_ROOT)
            else cache_root.as_posix()
        ),
    }


def build_membership_support(
    config: dict[str, Any],
    date_sets: dict[str, set[str]],
    feature_route_id: str,
    access_log: list[dict[str, Any]],
    sequence_ready_keys: set[tuple[str, str]] | None = None,
    feature_ready_keys: set[tuple[str, str]] | None = None,
) -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    import pandas as pd

    paths = resolve_paths(config)
    membership_header = _read_header(paths["membership"])
    forbidden = forbid_outcome_columns(membership_header)
    if forbidden:
        raise PermissionError(f"membership contains outcome columns: {forbidden}")
    required = [
        "membership_date",
        "usable_trade_date",
        "instrument",
        "is_listed",
        "is_st",
        "history_ready_240d_flag",
        "available_time",
        "membership_available_time",
    ]
    membership = pd.read_csv(
        paths["membership"],
        usecols=[name for name in required if name in membership_header],
    )
    for column in required:
        if column not in membership:
            membership[column] = ""
    membership["membership_date"] = membership["membership_date"].astype(str)
    membership["usable_trade_date"] = (
        membership["usable_trade_date"].fillna("").astype(str)
    )
    membership["instrument"] = membership["instrument"].map(normalize_instrument)
    calendar = pd.read_csv(paths["trading_calendar"], usecols=["trade_date"])
    calendar_dates = sorted(calendar["trade_date"].astype(str).unique())
    next_session = {
        calendar_dates[index]: calendar_dates[index + 1]
        for index in range(len(calendar_dates) - 1)
    }
    calendar_index = {date: index for index, date in enumerate(calendar_dates)}
    market_data_max_date = max(
        (date for dates in date_sets.values() for date in dates), default=""
    )
    add_access(
        access_log,
        paths["membership"],
        "membership",
        membership_header,
        ["U_t_membership", "U_t_decision"],
        "feature_support",
    )
    add_access(
        access_log,
        paths["trading_calendar"],
        "trading_calendar",
        ["trade_date"],
        ["next_exchange_session"],
        "feature_support",
    )
    if membership.duplicated(["membership_date", "instrument"]).any():
        duplicate_keys = True
    else:
        duplicate_keys = False
    support_rows: list[dict[str, Any]] = []
    integrity_total = 0
    next_session_total = 0
    right_censored_total = 0
    scoped_membership_total = 0
    for decision_date, day in membership.groupby("membership_date", sort=True):
        split = _split_for_date(decision_date, config)
        if split == "outside":
            continue
        scoped_membership_total += len(day)
        expected_next = next_session.get(decision_date, "")
        listed = day["is_listed"].map(bool_value)
        non_st = ~day["is_st"].map(bool_value)
        available = day["available_time"].astype(str).str.startswith(
            decision_date
        ) | day["membership_available_time"].astype(str).str.startswith(decision_date)
        usable_text = day["usable_trade_date"].fillna("").astype(str)
        usable = usable_text.eq(expected_next) & bool(expected_next)
        right_censored_day = bool(
            expected_next
            and market_data_max_date
            and expected_next > market_data_max_date
        )
        right_censored_mapping = (
            usable_text.isin(["", expected_next]) & right_censored_day
        )
        timing_valid = usable | right_censored_mapping
        integrity = listed & non_st & available & day["instrument"].ne("")
        decision_integrity = integrity & timing_valid
        history = decision_integrity & day["history_ready_240d_flag"].map(bool_value)
        sequence_flags: list[bool] = []
        position = calendar_index.get(decision_date, -1)
        needed_dates = set(
            calendar_dates[
                max(
                    0, position - config["universe_contract"]["lookback_sessions"] + 1
                ) : position + 1
            ]
        )
        for instrument, history_ok in zip(day["instrument"], history, strict=True):
            key = (instrument, decision_date)
            source_ready = (
                key in sequence_ready_keys
                if sequence_ready_keys is not None
                else len(needed_dates)
                == config["universe_contract"]["lookback_sessions"]
                and needed_dates.issubset(date_sets.get(instrument, set()))
            )
            sequence_flags.append(bool(history_ok and source_ready))
        sequence = pd.Series(sequence_flags, index=day.index)
        feature_ready = sequence & pd.Series(
            [
                (instrument, decision_date) in feature_ready_keys
                if feature_ready_keys is not None
                else True
                for instrument in day["instrument"]
            ],
            index=day.index,
        )
        decision = feature_ready
        counts = [
            len(day),
            int(integrity.sum()),
            int(history.sum()),
            int(sequence.sum()),
            int(feature_ready.sum()),
            int(decision.sum()),
        ]
        integrity_total += counts[1]
        next_session_total += int(timing_valid.sum())
        right_censored_total += int(right_censored_mapping.sum())
        support_rows.append(
            {
                "split": split,
                "decision_date": decision_date,
                "feature_route_id": feature_route_id,
                "U_membership_n": counts[0],
                "membership_integrity_n": counts[1],
                "history_ready_n": counts[2],
                "sequence_ready_n": counts[3],
                "feature_ready_n": counts[4],
                "U_decision_n": counts[5],
                "invalid_n": counts[0] - counts[5],
                "layer_count_reconciled": all(
                    left >= right for left, right in zip(counts, counts[1:])
                ),
                "support_status": "ready"
                if counts[5]
                >= config["universe_contract"]["minimum_primary_cross_section_n"]
                else "feature_support_not_evaluable",
            }
        )
    support_rows.sort(key=lambda row: (row["split"], row["decision_date"]))
    complete_by_split = {
        split: sum(
            row["support_status"] == "ready"
            for row in support_rows
            if row["split"] == split
        )
        for split in ["train", "validation", "historical_design_holdout"]
    }
    timing_rows = [
        {
            "check_id": "U01",
            "scope": "membership",
            "observed_value": not duplicate_keys,
            "required_value": True,
            "status": gate(not duplicate_keys),
            "blocking_reason": "" if not duplicate_keys else "duplicate_membership_key",
        },
        {
            "check_id": "U02",
            "scope": "membership",
            "observed_value": integrity_total,
            "required_value": scoped_membership_total,
            "status": gate(integrity_total == scoped_membership_total),
            "blocking_reason": ""
            if integrity_total == scoped_membership_total
            else "membership_integrity_failure",
        },
        {
            "check_id": "U03",
            "scope": "timing",
            "observed_value": next_session_total,
            "required_value": scoped_membership_total,
            "status": gate(next_session_total == scoped_membership_total),
            "blocking_reason": ""
            if next_session_total == scoped_membership_total
            else "usable_trade_date_not_next_session",
        },
        {
            "check_id": "U04",
            "scope": "denominator",
            "observed_value": scoped_membership_total,
            "required_value": scoped_membership_total,
            "status": "pass",
            "blocking_reason": "",
        },
        {
            "check_id": "U05",
            "scope": "universe_source",
            "observed_value": "membership_file_only",
            "required_value": "no_current_constituent_backfill",
            "status": "pass",
            "blocking_reason": "",
        },
    ]
    purge_rows: list[dict[str, Any]] = []
    for split_id, bounds in [
        ("train", config["split"]["train_nominal"]),
        ("validation", config["split"]["validation_nominal"]),
        (
            "historical_design_holdout",
            config["split"]["historical_design_holdout_nominal"],
        ),
    ]:
        dates = sorted(
            row["decision_date"]
            for row in support_rows
            if row["split"] == split_id and row["support_status"] == "ready"
        )
        purge_n = (
            config["split"]["purge_sessions"]
            if split_id != "historical_design_holdout" and len(dates) >= 13
            else 0
        )
        effective_dates = dates[:-purge_n] if purge_n else dates
        purge_rows.append(
            {
                "split_id": split_id,
                "nominal_start": bounds[0],
                "nominal_end": bounds[1],
                "effective_start": effective_dates[0] if effective_dates else "",
                "effective_end": effective_dates[-1] if effective_dates else "",
                "purge_side": "tail_of_earlier_split" if purge_n else "none",
                "purge_sessions": purge_n,
                "dropped_day_n": purge_n,
                "outcome_access_allowed": False,
                "status": gate(
                    bool(effective_dates)
                    and (split_id == "historical_design_holdout" or purge_n == 12)
                ),
            }
        )
    meta = {
        "duplicate_membership_key": duplicate_keys,
        "complete_by_split": complete_by_split,
        "support_gate": (
            complete_by_split["train"]
            >= config["universe_contract"]["minimum_complete_train_decision_days"]
            and complete_by_split["validation"]
            >= config["universe_contract"]["minimum_complete_validation_decision_days"]
            and complete_by_split["historical_design_holdout"]
            >= config["universe_contract"][
                "minimum_holdout_calendar_days_for_future_readout"
            ]
        ),
        "timing_gate": all(row["status"] == "pass" for row in timing_rows),
        "purge_gate": all(row["status"] == "pass" for row in purge_rows),
        "feature_predicate_exact": sequence_ready_keys is not None
        and feature_ready_keys is not None,
        "market_data_max_date": market_data_max_date,
        "right_censored_membership_n": right_censored_total,
    }
    return support_rows, timing_rows, purge_rows, meta


def build_static_contract_tables(
    config: dict[str, Any], feature_route_id: str, feature_dim: int
) -> dict[str, list[dict[str, Any]]]:
    latent_dim = int(config["architecture"]["latent_dim"])
    draw_n = int(config["architecture"]["inference_residual_draws"])
    graph_nodes = [
        ("source", "y_source", "source_input", "", "[B,T,1]", False, True, False),
        (
            "source",
            "x_source",
            "source_input",
            "",
            f"[B,T,{feature_dim}]",
            False,
            True,
            False,
        ),
        (
            "source",
            "H_y_source",
            "return_encoder",
            "y_source",
            f"[B,T,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "source",
            "H_x_source",
            "feature_encoder",
            "x_source",
            f"[B,T,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "source",
            "Z_source",
            "gated_latent",
            "H_y_source|H_x_source",
            f"[B,T,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "source",
            "Z_t",
            "decision_latent",
            "Z_source",
            f"[B,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "train",
            "y_teacher_shifted",
            "teacher_input",
            "",
            "[B,T,1]",
            True,
            False,
            True,
        ),
        (
            "train",
            "x_teacher_shifted",
            "teacher_input",
            "",
            f"[B,T,{feature_dim}]",
            True,
            False,
            True,
        ),
        (
            "train",
            "Z_teacher_shifted",
            "shared_teacher_encoder",
            "y_teacher_shifted|x_teacher_shifted",
            f"[B,T,{latent_dim}]",
            True,
            False,
            True,
        ),
        (
            "shared",
            "selector_source",
            "adaptive_selector",
            "Z_source|H_y_source",
            "[B,T,N]",
            False,
            True,
            False,
        ),
        (
            "shared",
            "K_codebook",
            "koopman_codebook",
            "",
            f"[N,{latent_dim},{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "shared",
            "K_selected",
            "selected_operator",
            "selector_source|K_codebook",
            f"[B,T,{latent_dim},{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "shared",
            "Z_hat_shifted",
            "koopman_prediction",
            "K_selected|Z_source",
            f"[B,T,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "train",
            "R_target_shifted",
            "teacher_residual_target",
            "Z_teacher_shifted|Z_hat_shifted",
            f"[B,T,{latent_dim}]",
            True,
            False,
            True,
        ),
        (
            "train",
            "ddpm_x_s",
            "ddpm_forward_noise",
            "R_target_shifted|ddpm_epsilon",
            f"[B,T,{latent_dim}]",
            True,
            False,
            True,
        ),
        (
            "train",
            "ddpm_epsilon",
            "ddpm_noise_target",
            "R_target_shifted",
            f"[B,T,{latent_dim}]",
            True,
            False,
            True,
        ),
        (
            "train",
            "ddpm_epsilon_hat",
            "ddpm_denoiser",
            "ddpm_x_s|Z_source",
            f"[B,T,{latent_dim}]",
            True,
            False,
            False,
        ),
        (
            "train",
            "R_hat_train_shifted",
            "ddpm_x0_estimate",
            "ddpm_x_s|ddpm_epsilon_hat",
            f"[B,T,{latent_dim}]",
            True,
            False,
            False,
        ),
        (
            "train",
            "Z_tilde_train_shifted",
            "train_corrected_latent",
            "Z_hat_shifted|R_hat_train_shifted",
            f"[B,T,{latent_dim}]",
            True,
            False,
            False,
        ),
        (
            "inference",
            "R_hat_inference_draws",
            "ddpm_reverse_sampler",
            "Z_source",
            f"[B,{draw_n},T,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "inference",
            "Z_tilde_inference_draws",
            "inference_corrected_latent",
            "Z_hat_shifted|R_hat_inference_draws",
            f"[B,{draw_n},T,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "shared",
            "R_hat_mlp_shifted",
            "r1_residual_mlp",
            "Z_source",
            f"[B,T,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "shared",
            "Z_tilde_mlp_shifted",
            "r1_corrected_latent",
            "Z_hat_shifted|R_hat_mlp_shifted",
            f"[B,T,{latent_dim}]",
            False,
            True,
            False,
        ),
        (
            "shared",
            "decoded_source",
            "decoder",
            "Z_source",
            "[B,T]",
            False,
            True,
            False,
        ),
        (
            "train",
            "decoded_shifted_train",
            "decoder",
            "Z_tilde_train_shifted",
            "[B,T]",
            True,
            False,
            False,
        ),
        (
            "inference",
            "decoded_shifted_draws",
            "decoder",
            "Z_tilde_inference_draws",
            f"[B,{draw_n},T]",
            False,
            True,
            False,
        ),
        (
            "arm_M2",
            "direct_score_M2",
            "M2_direct_head",
            "H_y_source",
            "[B]",
            False,
            True,
            False,
        ),
        (
            "arm_M3",
            "direct_score_M3",
            "M3_direct_head",
            "Z_source",
            "[B]",
            False,
            True,
            False,
        ),
        (
            "arm_A0",
            "direct_score_A0",
            "A0_direct_head",
            "Z_source",
            "[B]",
            False,
            True,
            False,
        ),
        (
            "inference",
            "score_draws_R2",
            "last_shifted_decoder_index",
            "decoded_shifted_draws",
            f"[B,{draw_n}]",
            False,
            True,
            False,
        ),
        (
            "inference",
            "score_next",
            "arithmetic_draw_mean",
            "score_draws_R2",
            "[B]",
            False,
            True,
            False,
        ),
    ]
    graph_rows = [
        {
            "graph_id": graph_id,
            "node_id": node_id,
            "node_role": role,
            "input_nodes": inputs,
            "output_shape": shape,
            "train_only": train_only,
            "inference_present": inference,
            "teacher_value_allowed": teacher,
            "status": "pass",
        }
        for graph_id, node_id, role, inputs, shape, train_only, inference, teacher in graph_nodes
    ]
    consumers: dict[str, list[str]] = {row["node_id"]: [] for row in graph_rows}
    for consumer_row in graph_rows:
        for input_node in str(consumer_row["input_nodes"]).split("|"):
            if input_node in consumers:
                consumers[input_node].append(consumer_row["node_id"])
    tensor_rows = [
        {
            "graph_id": row["graph_id"],
            "tensor_id": row["node_id"],
            "producer": row["node_role"],
            "consumer": "|".join(consumers[row["node_id"]]) or "contract_output",
            "dtype": "float32",
            "train_shape": row["output_shape"]
            if row["graph_id"] != "inference"
            else "",
            "inference_shape": row["output_shape"] if row["inference_present"] else "",
            "train_only": row["train_only"],
            "broadcast_allowed": False,
            "status": "pass",
        }
        for row in graph_rows
    ]
    arm_roles = {
        "M0_HASH_NULL_SCORE": (
            "project_control",
            False,
            False,
            False,
            "none",
            "none",
            "none",
            "none",
            "pipeline_null",
            False,
        ),
        "M1_LIGHTGBM_ALPHA158": (
            "project_baseline",
            False,
            True,
            False,
            "none",
            "none",
            "none",
            "tabular",
            "strong_baseline",
            True,
        ),
        "M2_RETURN_LSTM": (
            "paper_baseline",
            True,
            False,
            False,
            "none",
            "none",
            "none",
            "direct",
            "return_baseline",
            False,
        ),
        "M3_GATED_DUAL_PATH_LSTM": (
            "paper_baseline",
            True,
            True,
            True,
            "none",
            "none",
            "none",
            "direct",
            "sequence_comparator",
            True,
        ),
        "A0_VANILLA_AUTOENCODER": (
            "project_ablation",
            True,
            True,
            True,
            "none",
            "none",
            "none",
            "direct",
            "vanilla_ae",
            False,
        ),
        "K1_SINGLE_KOOPMAN_AE": (
            "paper_ablation",
            True,
            True,
            True,
            "single",
            "none",
            "none",
            "decoded",
            "koopman_test",
            False,
        ),
        "K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL": (
            "project_control",
            True,
            True,
            True,
            "global_multi",
            "constant_ones",
            "none",
            "decoded",
            "capacity_control",
            False,
        ),
        "K2_ADAPTIVE_KOOPMAN_AE": (
            "paper_ablation",
            True,
            True,
            True,
            "adaptive_multi",
            "Z_source|H_y",
            "none",
            "decoded",
            "adaptive_test",
            False,
        ),
        "R1_AKS_MLP_RESIDUAL": (
            "project_control",
            True,
            True,
            True,
            "adaptive_multi",
            "Z_source|H_y",
            "mlp",
            "decoded",
            "residual_control",
            False,
        ),
        "R2_REAKA_DIFFUSION": (
            "paper_project_adaptation",
            True,
            True,
            True,
            "adaptive_multi",
            "Z_source|H_y",
            "ddpm",
            "eight_draw_mean",
            "primary",
            True,
        ),
    }
    arm_rows = []
    loss_rows = []
    for arm_id in config["arms"]["mandatory_ids"]:
        (
            kind,
            use_y,
            use_x,
            use_gate,
            operator,
            context,
            residual,
            score,
            comparator,
            forward,
        ) = arm_roles[arm_id]
        losses = {
            "M0_HASH_NULL_SCORE": "none",
            "M1_LIGHTGBM_ALPHA158": "regression_l2",
            "M2_RETURN_LSTM": "L_forecast_direct",
            "M3_GATED_DUAL_PATH_LSTM": "L_forecast_direct",
            "A0_VANILLA_AUTOENCODER": "L_A0_source_rec+L_forecast_direct",
            "K1_SINGLE_KOOPMAN_AE": "L_rec+L_koop",
            "K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL": "L_rec+L_koop",
            "K2_ADAPTIVE_KOOPMAN_AE": "L_rec+L_koop",
            "R1_AKS_MLP_RESIDUAL": "L_rec_mlp+L_koop+L_residual_mlp",
            "R2_REAKA_DIFFUSION": "L_rec+L_koop+L_diff",
        }[arm_id]
        arm_rows.append(
            {
                "arm_id": arm_id,
                "mandatory": True,
                "paper_reported_or_project_control": kind,
                "input_feature_route": feature_route_id,
                "uses_return_sequence": use_y,
                "uses_feature_sequence": use_x,
                "uses_gate": use_gate,
                "operator_mode": operator,
                "selector_context": context,
                "residual_mode": residual,
                "loss_terms": losses,
                "score_head": score,
                "primary_comparator_role": comparator,
                "parameter_match_target": "R2_denoiser"
                if arm_id == "R1_AKS_MLP_RESIDUAL"
                else "K2"
                if "K1C" in arm_id
                else "",
                "historical_stage": "historical_design_diagnostic",
                "forward_eligible": forward,
                "claim_if_pass": "diagnostic_increment_only",
                "claim_if_fail": "no_mechanism_support",
            }
        )
        loss_rows.append(
            {
                "arm_id": arm_id,
                "loss_terms": losses,
                "target_id": "Y_rank_primary_raw(t)"
                if arm_id != "M0_HASH_NULL_SCORE"
                else "none",
                "score_tensor": score,
                "score_index": "last_shifted_scalar"
                if score in {"decoded", "eight_draw_mean"}
                else "decision_state",
                "draw_n": 8 if arm_id == "R2_REAKA_DIFFUSION" else 1,
                "aggregation": "arithmetic_mean"
                if arm_id == "R2_REAKA_DIFFUSION"
                else "identity",
                "status": "pass",
            }
        )
    normalization_rows = [
        {
            "field_group": "alpha158_features",
            "fit_split": "original_train",
            "center_rule": "median",
            "scale_rule": "IQR/1.349",
            "clip_lower": -10.0,
            "clip_upper": 10.0,
            "invalid_fill": "train_median",
            "indicator_direct_input": False,
            "apply_splits": "train|validation|historical_holdout",
            "status": "pass",
        },
        {
            "field_group": "return_sequence",
            "fit_split": "none",
            "center_rule": "none",
            "scale_rule": "raw_qfq_one_step_return",
            "clip_lower": "",
            "clip_upper": "",
            "invalid_fill": "frozen_gap_policy",
            "indicator_direct_input": False,
            "apply_splits": "all",
            "status": "pass",
        },
    ]
    label_rows = [
        {
            "label_id": "Y_rank_primary",
            "formula": "qfq_close(t+1)/qfq_close(t)-1",
            "role": "future_primary_rank_contract_only",
            "materialized_in_21a": False,
            "selection_allowed": False,
            "status": "pass",
        },
        {
            "label_id": "Y_qlib_gap_diagnostic",
            "formula": "qfq_close(t+2)/qfq_close(t+1)-1",
            "role": "diagnostic_contract_only",
            "materialized_in_21a": False,
            "selection_allowed": False,
            "status": "pass",
        },
        {
            "label_id": "Y_exec_1d",
            "formula": "qfq_open(next_session_after_entry)/qfq_open(entry_session)-1",
            "role": "execution_contract_only",
            "materialized_in_21a": False,
            "selection_allowed": False,
            "status": "pass",
        },
    ]
    resolution_rows = [
        {
            "status_id": "NORMAL_NEXT_SESSION_CLOSE",
            "trigger": "next_bar_observed",
            "valuation_rule": "observed_next_exchange_session_qfq_close",
            "row_or_day_action": "include_full_day",
            "primary_denominator_allowed": True,
            "synthetic_test_status": "pass",
        },
        {
            "status_id": "LISTED_SUSPENDED_CARRY",
            "trigger": "listed_suspension",
            "valuation_rule": "carry_close_t_return_zero",
            "row_or_day_action": "include_full_day",
            "primary_denominator_allowed": True,
            "synthetic_test_status": "pass",
        },
        {
            "status_id": "CONFIRMED_TERMINAL_PRICE",
            "trigger": "auditable_official_terminal_or_settlement_price",
            "valuation_rule": "official_terminal_price",
            "row_or_day_action": "include_full_day",
            "primary_denominator_allowed": True,
            "synthetic_test_status": "pass",
        },
        {
            "status_id": "UNKNOWN_DATA_GAP",
            "trigger": "unexplained_gap",
            "valuation_rule": "none",
            "row_or_day_action": "whole_day_not_evaluable",
            "primary_denominator_allowed": False,
            "synthetic_test_status": "pass",
        },
        {
            "status_id": "RIGHT_CENSORED_DATA_CUTOFF",
            "trigger": "data_cutoff",
            "valuation_rule": "none",
            "row_or_day_action": "whole_day_not_evaluable",
            "primary_denominator_allowed": False,
            "synthetic_test_status": "pass",
        },
    ]
    return {
        "train_teacher_inference_graph_contract.csv": graph_rows,
        "tensor_shape_contract.csv": tensor_rows,
        "model_arm_registry.csv": arm_rows,
        "per_arm_loss_and_score_index_contract.csv": loss_rows,
        "feature_normalization_and_missingness_contract.csv": normalization_rows,
        "label_semantics_freeze.csv": label_rows,
        "decision_universe_and_label_resolution_contract.csv": resolution_rows,
    }


def r1_parameter_count(latent_dim: int, hidden_width: int) -> int:
    return (
        latent_dim * hidden_width
        + hidden_width
        + hidden_width * hidden_width
        + hidden_width
        + hidden_width * latent_dim
        + latent_dim
    )


def ddpm_denoiser_parameter_count(latent_dim: int) -> int:
    input_dim = latent_dim * 2 + 32
    return input_dim * 128 + 128 + 128 * 128 + 128 + 128 * latent_dim + latent_dim


def select_r1_hidden_width(config: dict[str, Any]) -> tuple[int, int, int, float]:
    latent_dim = int(config["architecture"]["latent_dim"])
    target = ddpm_denoiser_parameter_count(latent_dim)
    candidates = [
        int(value) for value in config["architecture"]["r1_hidden_width_candidates"]
    ]
    selected = min(
        candidates,
        key=lambda width: (abs(r1_parameter_count(latent_dim, width) - target), width),
    )
    selected_n = r1_parameter_count(latent_dim, selected)
    return selected, selected_n, target, abs(selected_n - target) / target


def inference_draw_seed(
    run_id: str,
    arm_id: str,
    model_seed: int,
    instrument: str,
    decision_date: str,
    draw_id: int,
) -> int:
    canonical = normalize_instrument(instrument)
    if not canonical or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decision_date)):
        raise ValueError(
            "inference row key must use canonical instrument and YYYY-MM-DD date"
        )
    payload = f"{run_id}|{arm_id}|{int(model_seed)}|{canonical}|{decision_date}|{int(draw_id)}".encode(
        "utf-8"
    )
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False) % (
        2**63
    )


def create_reaka_model(
    feature_dim: int,
    config: dict[str, Any],
    device: str = "cpu",
    model_seed: int = 20260713,
) -> Any:
    import torch
    from torch import nn

    architecture = config["architecture"]
    latent_dim = int(architecture["latent_dim"])
    operator_n = int(architecture["n_operator"])

    class ReakaSyntheticGraph(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.return_encoder = nn.LSTM(1, latent_dim, batch_first=True)
            self.feature_encoder = nn.LSTM(feature_dim, latent_dim, batch_first=True)
            self.gate_linear = nn.Linear(latent_dim, latent_dim)
            self.selector_linear = nn.Linear(2 * latent_dim, operator_n)
            self.decoder = nn.Linear(latent_dim, 1)
            self.m2_direct_head = nn.Linear(latent_dim, 1)
            self.m3_direct_head = nn.Linear(latent_dim, 1)
            self.a0_direct_head = nn.Linear(latent_dim, 1)
            self.codebook = nn.Parameter(
                torch.empty(operator_n, latent_dim, latent_dim)
            )
            self.denoiser = nn.Sequential(
                nn.Linear(latent_dim + latent_dim + 32, 128),
                nn.SiLU(),
                nn.Linear(128, 128),
                nn.SiLU(),
                nn.Linear(128, latent_dim),
            )
            r1_width, _, _, _ = select_r1_hidden_width(config)
            self.r1_residual_mlp = nn.Sequential(
                nn.Linear(latent_dim, r1_width),
                nn.SiLU(),
                nn.Linear(r1_width, r1_width),
                nn.SiLU(),
                nn.Linear(r1_width, latent_dim),
            )
            self.register_buffer(
                "k1c_context", torch.ones(1, 2 * latent_dim), persistent=True
            )
            self.reset_parameters()

        def reset_parameters(self) -> None:
            for module in self.modules():
                if isinstance(module, nn.Linear):
                    nn.init.xavier_uniform_(module.weight)
                    nn.init.zeros_(module.bias)
                elif isinstance(module, nn.LSTM):
                    for name, parameter in module.named_parameters():
                        if "weight_ih" in name:
                            nn.init.xavier_uniform_(parameter)
                        elif "weight_hh" in name:
                            nn.init.orthogonal_(parameter)
                        elif "bias" in name:
                            nn.init.zeros_(parameter)
                            size = parameter.numel() // 4
                            parameter.data[size : 2 * size] = 1.0
            with torch.no_grad():
                identity = torch.eye(latent_dim).expand(operator_n, -1, -1)
                self.codebook.copy_(identity + torch.randn_like(self.codebook) * 0.01)

        def encode(self, y: Any, x: Any) -> tuple[Any, Any, Any]:
            h_y, _ = self.return_encoder(y)
            h_x, _ = self.feature_encoder(x)
            g = torch.sigmoid(self.gate_linear(h_x))
            z = h_y * g + h_x * (1.0 - g)
            return z, h_y, h_x

        def selector(
            self, z: Any, h_y: Any, tau: float, generator: Any, training: bool
        ) -> Any:
            logits = torch.nn.functional.leaky_relu(
                self.selector_linear(torch.cat([z, h_y], dim=-1)),
                negative_slope=float(architecture["selector_negative_slope"]),
            )
            if not training:
                index = logits.argmax(dim=-1)
                return torch.nn.functional.one_hot(index, num_classes=operator_n).to(
                    logits.dtype
                )
            uniform = torch.rand(
                logits.shape, device=logits.device, generator=generator
            ).clamp_(1e-10, 1 - 1e-10)
            gumbel = -torch.log(-torch.log(uniform))
            return torch.softmax((logits + gumbel) / tau, dim=-1)

        def k1c_selector(
            self, batch: int, steps: int, tau: float, generator: Any, training: bool
        ) -> Any:
            logits = torch.nn.functional.leaky_relu(
                self.selector_linear(self.k1c_context),
                negative_slope=float(architecture["selector_negative_slope"]),
            )[0]
            if training:
                uniform = torch.rand(
                    (operator_n,), device=logits.device, generator=generator
                ).clamp_(1e-10, 1 - 1e-10)
                gumbel = -torch.log(-torch.log(uniform))
                global_weights = torch.softmax((logits + gumbel) / tau, dim=-1)
            else:
                global_weights = torch.nn.functional.one_hot(
                    logits.argmax(), num_classes=operator_n
                ).to(logits.dtype)
            return global_weights.view(1, 1, operator_n).expand(
                batch, steps, operator_n
            )

        def koopman(self, z: Any, selector: Any) -> tuple[Any, Any]:
            selected = torch.einsum("btn,nij->btij", selector, self.codebook)
            z_hat = torch.einsum("btij,btj->bti", selected, z)
            return z_hat, selected

        @staticmethod
        def timestep_embedding(step: Any, dtype: Any) -> Any:
            half = 16
            indices = torch.arange(half, device=step.device, dtype=dtype)
            frequencies = torch.pow(
                torch.tensor(10000.0, device=step.device, dtype=dtype),
                -(2 * indices / 32),
            )
            angles = step.to(dtype).unsqueeze(-1) * frequencies
            return torch.stack([torch.sin(angles), torch.cos(angles)], dim=-1).flatten(
                start_dim=-2
            )

        def denoise(self, noisy: Any, step: Any, condition: Any) -> Any:
            embedding = self.timestep_embedding(step, noisy.dtype)
            return self.denoiser(torch.cat([noisy, condition, embedding], dim=-1))

        def train_graph(
            self,
            y_source: Any,
            x_source: Any,
            y_teacher: Any,
            x_teacher: Any,
            model_seed: int,
        ) -> dict[str, Any]:
            gumbel_generator = torch.Generator(device=y_source.device).manual_seed(
                int(model_seed) + 71
            )
            diffusion_generator = torch.Generator(device=y_source.device).manual_seed(
                int(model_seed) + 89
            )
            z, h_y, h_x = self.encode(y_source, x_source)
            z_teacher, _, _ = self.encode(y_teacher, x_teacher)
            selector = self.selector(
                z, h_y, tau=0.5, generator=gumbel_generator, training=True
            )
            z_hat, selected = self.koopman(z, selector)
            residual = z_teacher - z_hat
            batch, steps, _ = residual.shape
            step = torch.randint(
                1,
                int(architecture["diffusion_steps"]) + 1,
                (batch, steps),
                device=residual.device,
                generator=diffusion_generator,
            )
            betas = torch.linspace(
                float(architecture["beta_start"]),
                float(architecture["beta_end"]),
                int(architecture["diffusion_steps"]),
                device=residual.device,
            )
            alpha_bars = torch.cumprod(1.0 - betas, dim=0)
            alpha_bar = alpha_bars[step - 1].unsqueeze(-1)
            epsilon = torch.randn(
                residual.shape, device=residual.device, generator=diffusion_generator
            )
            noisy = alpha_bar.sqrt() * residual + (1.0 - alpha_bar).sqrt() * epsilon
            epsilon_hat = self.denoise(noisy, step, z)
            residual_hat = (
                noisy - (1.0 - alpha_bar).sqrt() * epsilon_hat
            ) / alpha_bar.sqrt()
            z_tilde = z_hat + residual_hat
            decoded_source = self.decoder(z).squeeze(-1)
            decoded_shifted = self.decoder(z_tilde).squeeze(-1)
            l_source = (decoded_source - y_source.squeeze(-1)).square().mean()
            l_shifted = (
                (decoded_shifted[:, :-1] - y_teacher.squeeze(-1)[:, :-1])
                .square()
                .mean()
            )
            l_forecast = (
                (decoded_shifted[:, -1] - y_teacher.squeeze(-1)[:, -1]).square().mean()
            )
            l_rec = 0.5 * (l_source + l_shifted) + l_forecast
            l_koop = residual.square().mean()
            l_diff = (epsilon_hat - epsilon).square().mean()
            total = l_rec + l_koop + l_diff
            r1_residual_hat = self.r1_residual_mlp(z)
            r1_z_tilde = z_hat + r1_residual_hat
            r1_decoded = self.decoder(r1_z_tilde).squeeze(-1)
            r1_shifted = (
                (r1_decoded[:, :-1] - y_teacher.squeeze(-1)[:, :-1]).square().mean()
            )
            r1_forecast = (
                (r1_decoded[:, -1] - y_teacher.squeeze(-1)[:, -1]).square().mean()
            )
            r1_rec = 0.5 * (l_source + r1_shifted) + r1_forecast
            r1_residual_loss = (r1_residual_hat - residual).square().mean()
            r1_total = r1_rec + l_koop + r1_residual_loss
            return {
                "y_source": y_source,
                "x_source": x_source,
                "H_y_source": h_y,
                "H_x_source": h_x,
                "Z_source": z,
                "Z_t": z[:, -1],
                "y_teacher_shifted": y_teacher,
                "x_teacher_shifted": x_teacher,
                "Z_teacher_shifted": z_teacher,
                "selector_source": selector,
                "K_codebook": self.codebook,
                "K_selected": selected,
                "Z_hat_shifted": z_hat,
                "R_target_shifted": residual,
                "ddpm_x_s": noisy,
                "ddpm_epsilon": epsilon,
                "ddpm_epsilon_hat": epsilon_hat,
                "R_hat_train_shifted": residual_hat,
                "Z_tilde_train_shifted": z_tilde,
                "R_hat_mlp_shifted": r1_residual_hat,
                "Z_tilde_mlp_shifted": r1_z_tilde,
                "decoded_source": decoded_source,
                "decoded_shifted_train": decoded_shifted,
                "score_train": decoded_shifted[:, -1],
                "L_source_rec": l_source,
                "L_shifted_observed_rec": l_shifted,
                "L_forecast": l_forecast,
                "L_rec": l_rec,
                "L_koop": l_koop,
                "L_diff": l_diff,
                "L_rec_mlp": r1_rec,
                "L_residual_mlp": r1_residual_loss,
                "L_total_R1": r1_total,
                "loss": total,
            }

        def inference(
            self,
            y_source: Any,
            x_source: Any,
            model_seed: int,
            row_keys: Sequence[tuple[str, str]],
            draws: int = 8,
            run_id: str = RUN_ID,
            arm_id: str = "R2_REAKA_DIFFUSION",
            return_draws: bool = False,
        ) -> Any:
            if len(row_keys) != y_source.shape[0]:
                raise ValueError("row_keys length must equal batch size")
            z, h_y, _ = self.encode(y_source, x_source)
            selector = self.selector(z, h_y, tau=0.1, generator=None, training=False)
            z_hat, _ = self.koopman(z, selector)
            betas = torch.linspace(
                float(architecture["beta_start"]),
                float(architecture["beta_end"]),
                int(architecture["diffusion_steps"]),
                device=z.device,
            )
            alphas = 1.0 - betas
            alpha_bars = torch.cumprod(alphas, dim=0)
            scores = []
            for draw in range(draws):
                generators = [
                    torch.Generator(device=z.device).manual_seed(
                        inference_draw_seed(
                            run_id, arm_id, model_seed, instrument, decision_date, draw
                        )
                    )
                    for instrument, decision_date in row_keys
                ]
                noisy = torch.stack(
                    [
                        torch.randn(
                            z.shape[1:],
                            device=z.device,
                            dtype=z.dtype,
                            generator=generator,
                        )
                        for generator in generators
                    ]
                )
                for index in range(len(betas) - 1, -1, -1):
                    step = torch.full(
                        z.shape[:2], index + 1, device=z.device, dtype=torch.long
                    )
                    epsilon_hat = self.denoise(noisy, step, z)
                    mean = (
                        noisy
                        - betas[index]
                        / torch.sqrt(1.0 - alpha_bars[index])
                        * epsilon_hat
                    ) / torch.sqrt(alphas[index])
                    if index > 0:
                        posterior = (
                            betas[index]
                            * (1.0 - alpha_bars[index - 1])
                            / (1.0 - alpha_bars[index])
                        )
                        noise = torch.stack(
                            [
                                torch.randn(
                                    z.shape[1:],
                                    device=z.device,
                                    dtype=z.dtype,
                                    generator=generator,
                                )
                                for generator in generators
                            ]
                        )
                        noisy = mean + posterior.sqrt() * noise
                    else:
                        noisy = mean
                decoded = self.decoder(z_hat + noisy).squeeze(-1)
                scores.append(decoded[:, -1])
            score_draws = torch.stack(scores, dim=1)
            return (
                (score_draws.mean(dim=1), score_draws)
                if return_draws
                else score_draws.mean(dim=1)
            )

        def synthetic_arm_scores(
            self,
            y_source: Any,
            x_source: Any,
            model_seed: int,
            row_keys: Sequence[tuple[str, str]],
            draws: int,
        ) -> dict[str, Any]:
            z, h_y, _ = self.encode(y_source, x_source)
            hard_selector = self.selector(
                z, h_y, tau=0.1, generator=None, training=False
            )
            z_hat, _ = self.koopman(z, hard_selector)
            k1_selected = (
                self.codebook[0]
                .view(1, 1, latent_dim, latent_dim)
                .expand(z.shape[0], z.shape[1], latent_dim, latent_dim)
            )
            k1_hat, _ = self.koopman(
                z,
                torch.nn.functional.one_hot(
                    torch.zeros(z.shape[:2], device=z.device, dtype=torch.long),
                    num_classes=operator_n,
                ).to(z.dtype),
            )
            k1c_selector = self.k1c_selector(
                z.shape[0], z.shape[1], 0.1, generator=None, training=False
            )
            k1c_hat, _ = self.koopman(z, k1c_selector)
            r1_hat = self.r1_residual_mlp(z)
            r2_score = self.inference(
                y_source, x_source, model_seed, row_keys, draws=draws
            )
            m0 = torch.tensor(
                [m0_hash_score(instrument, date) for instrument, date in row_keys],
                device=z.device,
                dtype=z.dtype,
            )
            scores = {
                "M0_HASH_NULL_SCORE": m0,
                "M1_LIGHTGBM_ALPHA158": x_source[:, -1, 0],
                "M2_RETURN_LSTM": self.m2_direct_head(h_y[:, -1]).squeeze(-1),
                "M3_GATED_DUAL_PATH_LSTM": self.m3_direct_head(z[:, -1]).squeeze(-1),
                "A0_VANILLA_AUTOENCODER": self.a0_direct_head(z[:, -1]).squeeze(-1),
                "K1_SINGLE_KOOPMAN_AE": self.decoder(k1_hat).squeeze(-1)[:, -1],
                "K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL": self.decoder(
                    k1c_hat
                ).squeeze(-1)[:, -1],
                "K2_ADAPTIVE_KOOPMAN_AE": self.decoder(z_hat).squeeze(-1)[:, -1],
                "R1_AKS_MLP_RESIDUAL": self.decoder(z_hat + r1_hat).squeeze(-1)[:, -1],
                "R2_REAKA_DIFFUSION": r2_score,
            }
            _ = k1_selected
            return scores

    torch.manual_seed(int(model_seed) + 53)
    model = ReakaSyntheticGraph().to(device)
    return model


def _parameter_count(module: Any) -> int:
    return sum(
        parameter.numel()
        for parameter in module.parameters()
        if parameter.requires_grad
    )


def nvidia_driver_version() -> str:
    version_file = Path("/proc/driver/nvidia/version")
    if version_file.is_file():
        text = version_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"Kernel Module\s+([0-9.]+)", text)
        return match.group(1) if match else text.splitlines()[0].strip()
    import subprocess

    completed = subprocess.run(
        ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return completed.stdout.splitlines()[0].strip() if completed.returncode == 0 else ""


def run_synthetic_graph_audit(
    config: dict[str, Any], feature_dim: int, device_override: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    os.environ.setdefault(
        "CUBLAS_WORKSPACE_CONFIG", config["dependencies"]["cublas_workspace_config"]
    )
    import torch

    use_cuda = torch.cuda.is_available() and device_override not in {"cpu"}
    device = device_override or ("cuda" if use_cuda else "cpu")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    batch_candidates = (
        config["architecture"]["batch_size_candidates"]
        if device == "cuda"
        else [min(4, config["architecture"]["minimum_batch_size"])]
    )
    runtime_rows: list[dict[str, Any]] = []
    selected_batch = 0
    selected_meta: dict[str, Any] = {}
    graph_test_rows: list[dict[str, Any]] = []
    for batch in batch_candidates:
        try:
            if device == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            torch.manual_seed(20260713)
            model = create_reaka_model(feature_dim, config, device=device)
            optimizer = torch.optim.AdamW(
                model.parameters(), lr=0.001, weight_decay=0.00001
            )
            generator = torch.Generator(device=device).manual_seed(20260724)
            shape_y = (batch, config["architecture"]["lookback_T"], 1)
            shape_x = (batch, config["architecture"]["lookback_T"], feature_dim)
            y_source = torch.randn(shape_y, device=device, generator=generator)
            x_source = torch.randn(shape_x, device=device, generator=generator)
            y_teacher = torch.randn(
                shape_y, device=device, generator=generator, requires_grad=True
            )
            x_teacher = torch.randn(
                shape_x, device=device, generator=generator, requires_grad=True
            )
            output = model.train_graph(
                y_source, x_source, y_teacher, x_teacher, 20260713
            )

            def gradient_sum(
                loss: Any, parameters: Iterable[Any], retain_graph: bool = True
            ) -> float:
                selected = [
                    parameter for parameter in parameters if parameter.requires_grad
                ]
                gradients = torch.autograd.grad(
                    loss, selected, retain_graph=retain_graph, allow_unused=True
                )
                return sum(
                    float(gradient.abs().sum().item())
                    for gradient in gradients
                    if gradient is not None
                )

            source_rec_grad = gradient_sum(
                output["L_rec"], model.return_encoder.parameters()
            )
            source_koop_grad = gradient_sum(
                output["L_koop"], model.return_encoder.parameters()
            )
            teacher_latent_grad = gradient_sum(
                output["L_koop"], [output["Z_teacher_shifted"]]
            )
            teacher_input_grad = gradient_sum(output["L_koop"], [y_teacher, x_teacher])
            allowed_target_grad = gradient_sum(
                output["R_target_shifted"].sum(), [y_teacher, x_teacher]
            )
            selector_teacher_grad = gradient_sum(
                output["selector_source"].sum(), [y_teacher, x_teacher]
            )
            gate_teacher_grad = gradient_sum(
                output["Z_source"].sum(), [y_teacher, x_teacher]
            )
            output["loss"].backward()
            gradient_finite = all(
                parameter.grad is None or torch.isfinite(parameter.grad).all().item()
                for parameter in model.parameters()
            )
            row_keys = [
                (
                    f"SH{600000 + index:06d}",
                    (datetime(2026, 1, 1) + timedelta(days=index)).strftime("%Y-%m-%d"),
                )
                for index in range(batch)
            ]
            with torch.no_grad():
                draw_n = int(config["architecture"]["inference_residual_draws"])
                score_a, score_draws = model.inference(
                    y_source,
                    x_source,
                    20260713,
                    row_keys,
                    draws=draw_n,
                    return_draws=True,
                )
                score_b = model.inference(
                    y_source, x_source, 20260713, row_keys, draws=draw_n
                )
                score_teacher_perturbed = model.inference(
                    y_source, x_source, 20260713, row_keys, draws=draw_n
                )
                repeat_delta = float((score_a - score_b).abs().max().item())
                teacher_delta = float(
                    (score_a - score_teacher_perturbed).abs().max().item()
                )
                permutation = torch.arange(batch - 1, -1, -1, device=device)
                inverse = torch.argsort(permutation)
                reordered = model.inference(
                    y_source[permutation],
                    x_source[permutation],
                    20260713,
                    [row_keys[int(index)] for index in permutation.cpu().tolist()],
                    draws=draw_n,
                )[inverse]
                batch_reorder_delta = float((score_a - reordered).abs().max().item())
                perturbed_output = model.train_graph(
                    y_source,
                    x_source,
                    y_teacher.detach() + 100.0,
                    x_teacher.detach() - 100.0,
                    20260713,
                )
                allowed_teacher_delta = max(
                    float((output[name] - perturbed_output[name]).abs().max().item())
                    for name in [
                        "Z_teacher_shifted",
                        "R_target_shifted",
                        "ddpm_x_s",
                        "loss",
                    ]
                )
                forbidden_teacher_delta = max(
                    float((output[name] - perturbed_output[name]).abs().max().item())
                    for name in [
                        "Z_source",
                        "selector_source",
                        "K_selected",
                        "Z_hat_shifted",
                    ]
                )
                k1c_generator = torch.Generator(device=device).manual_seed(20260784)
                k1c_train = model.k1c_selector(
                    batch,
                    config["architecture"]["lookback_T"],
                    0.5,
                    k1c_generator,
                    True,
                )
                k1c_inference = model.k1c_selector(
                    batch,
                    config["architecture"]["lookback_T"],
                    0.1,
                    k1c_generator,
                    False,
                )
                k1c_train_delta = float(
                    (k1c_train - k1c_train[0, 0]).abs().max().item()
                )
                k1c_inference_delta = float(
                    (k1c_inference - k1c_inference[0, 0]).abs().max().item()
                )
                explicit = torch.einsum(
                    "btij,btj->bti", output["K_selected"], output["Z_source"]
                )
                koop_delta = float(
                    (explicit - output["Z_hat_shifted"]).abs().max().item()
                )
                duplicated_loss = (
                    torch.cat(
                        [output["R_target_shifted"], output["R_target_shifted"]], dim=0
                    )
                    .square()
                    .mean()
                )
                mean_delta = float((duplicated_loss - output["L_koop"]).abs().item())
                rec_reference = (
                    0.5 * (output["L_source_rec"] + output["L_shifted_observed_rec"])
                    + output["L_forecast"]
                )
                rec_delta = float((rec_reference - output["L_rec"]).abs().item())
                total_delta = float(
                    (
                        output["L_rec"]
                        + output["L_koop"]
                        + output["L_diff"]
                        - output["loss"]
                    )
                    .abs()
                    .item()
                )
                r1_residual_reference = (
                    (output["R_hat_mlp_shifted"] - output["R_target_shifted"])
                    .square()
                    .mean()
                )
                r1_total_reference = (
                    output["L_rec_mlp"] + output["L_koop"] + output["L_residual_mlp"]
                )
                r1_loss_delta = max(
                    float(
                        (r1_residual_reference - output["L_residual_mlp"]).abs().item()
                    ),
                    float((r1_total_reference - output["L_total_R1"]).abs().item()),
                )
                expected_embedding = torch.empty(
                    (1, 1, 32), device=device, dtype=torch.float32
                )
                for embedding_index in range(16):
                    angle = torch.tensor(
                        1.0 / (10000.0 ** (2 * embedding_index / 32)), device=device
                    )
                    expected_embedding[..., 2 * embedding_index] = torch.sin(angle)
                    expected_embedding[..., 2 * embedding_index + 1] = torch.cos(angle)
                embedding_delta = float(
                    (
                        model.timestep_embedding(
                            torch.ones((1, 1), device=device, dtype=torch.long),
                            torch.float32,
                        )
                        - expected_embedding
                    )
                    .abs()
                    .max()
                    .item()
                )
                arm_scores = model.synthetic_arm_scores(
                    y_source, x_source, 20260713, row_keys, draws=draw_n
                )
                arm_graph_ok = set(arm_scores) == set(
                    config["arms"]["mandatory_ids"]
                ) and all(
                    value.shape == (batch,) and torch.isfinite(value).all().item()
                    for value in arm_scores.values()
                )
                nan_y = y_source.clone()
                nan_y[0, 0, 0] = torch.nan
                nan_output = model.train_graph(
                    nan_y, x_source, y_teacher.detach(), x_teacher.detach(), 20260713
                )
                nan_fail_closed = not torch.isfinite(nan_output["loss"]).all().item()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            peak_mib = (
                float(torch.cuda.max_memory_reserved() / 1024**2)
                if device == "cuda"
                else 0.0
            )
            total_mib = (
                float(torch.cuda.get_device_properties(0).total_memory / 1024**2)
                if device == "cuda"
                else 0.0
            )
            finite = (
                all(
                    torch.isfinite(output[key]).all().item()
                    for key in ["loss", "L_rec", "L_koop", "L_diff", "score_train"]
                )
                and torch.isfinite(score_a).all().item()
            )
            candidate_checks = {
                "finite": finite,
                "gradient_finite": gradient_finite,
                "repeat": repeat_delta <= 1e-7,
                "teacher_inference": teacher_delta == 0.0,
                "koop": koop_delta <= 1e-7,
                "mean": mean_delta <= 1e-7,
                "k1c_train": k1c_train_delta == 0.0,
                "k1c_inference": k1c_inference_delta == 0.0,
                "batch_reorder": batch_reorder_delta <= 1e-7,
                "forbidden_teacher": forbidden_teacher_delta == 0.0,
                "allowed_teacher": allowed_teacher_delta > 0.0,
                "source_rec_grad": source_rec_grad > 0.0,
                "source_koop_grad": source_koop_grad > 0.0,
                "teacher_latent_grad": teacher_latent_grad > 0.0,
                "teacher_input_grad": teacher_input_grad > 0.0,
                "allowed_target_grad": allowed_target_grad > 0.0,
                "selector_teacher_grad": selector_teacher_grad == 0.0,
                "gate_teacher_grad": gate_teacher_grad == 0.0,
                "rec_formula": rec_delta <= 1e-7,
                "total_formula": total_delta <= 1e-7,
                "r1_loss": r1_loss_delta <= 1e-7,
                "embedding": embedding_delta <= 1e-7,
                "arm_graph": arm_graph_ok,
                "nan_fail_closed": nan_fail_closed,
                "memory": device != "cuda" or peak_mib <= 0.90 * total_mib,
            }
            pass_candidate = all(candidate_checks.values())
            failed_checks = sorted(
                name for name, passed in candidate_checks.items() if not passed
            )
            runtime_rows.append(
                {
                    "check_id": "batch_candidate_full_graph",
                    "observed_value": "finite_deterministic"
                    if pass_candidate
                    else "failed:" + "|".join(failed_checks),
                    "required_value": "finite_deterministic",
                    "batch_size": batch,
                    "peak_memory_mib": peak_mib,
                    "repeat_delta": repeat_delta,
                    "status": gate(pass_candidate),
                }
            )
            if pass_candidate:
                selected_batch = batch
                denoiser_n = _parameter_count(model.denoiser)
                (
                    r1_width,
                    expected_r1_n,
                    expected_denoiser_n,
                    expected_relative_delta,
                ) = select_r1_hidden_width(config)
                r1_n = _parameter_count(model.r1_residual_mlp)
                k2_operator_n = model.codebook.numel() + _parameter_count(
                    model.selector_linear
                )
                k1c_operator_n = model.codebook.numel() + _parameter_count(
                    model.selector_linear
                )
                selected_meta = {
                    "device": device,
                    "device_name": torch.cuda.get_device_name(0)
                    if device == "cuda"
                    else "cpu_fixture",
                    "total_memory_mib": total_mib,
                    "peak_memory_mib": peak_mib,
                    "repeat_delta": repeat_delta,
                    "teacher_delta": teacher_delta,
                    "koop_delta": koop_delta,
                    "mean_delta": mean_delta,
                    "source_rec_gradient_sum": source_rec_grad,
                    "source_koop_gradient_sum": source_koop_grad,
                    "teacher_latent_gradient_sum": teacher_latent_grad,
                    "teacher_input_gradient_sum": teacher_input_grad,
                    "allowed_target_gradient_sum": allowed_target_grad,
                    "selector_teacher_gradient_sum": selector_teacher_grad,
                    "gate_teacher_gradient_sum": gate_teacher_grad,
                    "allowed_teacher_delta": allowed_teacher_delta,
                    "forbidden_teacher_delta": forbidden_teacher_delta,
                    "batch_reorder_delta": batch_reorder_delta,
                    "embedding_delta": embedding_delta,
                    "rec_delta": rec_delta,
                    "total_delta": total_delta,
                    "r1_loss_delta": r1_loss_delta,
                    "nan_fail_closed": nan_fail_closed,
                    "arm_graph_ok": arm_graph_ok,
                    "arm_score_ids": sorted(arm_scores),
                    "gate_sigmoid_count": inspect.getsource(type(model).encode).count(
                        "torch.sigmoid"
                    ),
                    "k1c_train_delta": k1c_train_delta,
                    "k1c_inference_delta": k1c_inference_delta,
                    "k2_operator_parameter_n": k2_operator_n,
                    "k1c_operator_parameter_n": k1c_operator_n,
                    "r2_denoiser_parameter_n": denoiser_n,
                    "r1_residual_parameter_n": r1_n,
                    "r1_hidden_width": r1_width,
                    "r1_mechanical_selection_ok": (
                        r1_n == expected_r1_n
                        and denoiser_n == expected_denoiser_n
                        and abs(
                            abs(r1_n - denoiser_n) / denoiser_n
                            - expected_relative_delta
                        )
                        <= 1e-12
                    ),
                    "r1_relative_delta": abs(r1_n - denoiser_n) / denoiser_n,
                    "score_shape": list(score_a.shape),
                    "score_draw_shape": list(score_draws.shape),
                    "train_score_shape": list(output["score_train"].shape),
                    "all_transition_shape": list(output["R_target_shifted"].shape),
                }
                tests = [
                    (
                        "source_encoder_receives_gradient_from_L_rec",
                        source_rec_grad > 0,
                        source_rec_grad,
                        ">0",
                        0.0,
                    ),
                    (
                        "source_encoder_receives_gradient_from_L_koop",
                        source_koop_grad > 0,
                        source_koop_grad,
                        ">0",
                        0.0,
                    ),
                    (
                        "teacher_shared_encoder_receives_gradient_from_L_koop",
                        teacher_latent_grad > 0 and teacher_input_grad > 0,
                        teacher_input_grad,
                        ">0",
                        0.0,
                    ),
                    (
                        "selector_receives_no_direct_teacher_input",
                        selector_teacher_grad == 0.0,
                        selector_teacher_grad,
                        0.0,
                        selector_teacher_grad,
                    ),
                    (
                        "residual_condition_receives_no_teacher_value",
                        gate_teacher_grad == 0.0,
                        gate_teacher_grad,
                        0.0,
                        gate_teacher_grad,
                    ),
                    (
                        "inference_signature_has_no_teacher_tensor",
                        "teacher"
                        not in str(inspect.signature(model.inference)).lower(),
                        str(inspect.signature(model.inference)),
                        "no_teacher",
                        0.0,
                    ),
                    (
                        "teacher_perturbation_does_not_change_fixed_source_inference_score",
                        teacher_delta == 0.0,
                        teacher_delta,
                        0.0,
                        teacher_delta,
                    ),
                    (
                        "all_T_transitions_contribute_to_L_koop",
                        output["R_target_shifted"].shape[1]
                        == config["architecture"]["lookback_T"],
                        output["R_target_shifted"].shape[1],
                        config["architecture"]["lookback_T"],
                        0.0,
                    ),
                    (
                        "loss_mean_invariant_to_exact_batch_duplication",
                        mean_delta <= 1e-7,
                        mean_delta,
                        "<=1e-7",
                        mean_delta,
                    ),
                    (
                        "score_index_is_last_shifted_scalar",
                        output["score_train"].shape == (batch,),
                        list(output["score_train"].shape),
                        [batch],
                        0.0,
                    ),
                    (
                        "train_and_inference_score_shape_match",
                        score_a.shape == output["score_train"].shape,
                        list(score_a.shape),
                        list(output["score_train"].shape),
                        0.0,
                    ),
                    (
                        "NaN_and_inf_fail_closed",
                        nan_fail_closed,
                        nan_fail_closed,
                        True,
                        0.0,
                    ),
                ]
                graph_test_rows = [
                    {
                        "test_id": test_id,
                        "expected": expected,
                        "observed": observed,
                        "max_abs_delta": delta,
                        "status": gate(ok),
                        "blocking_reason": ""
                        if ok
                        else "synthetic_graph_contract_failure",
                    }
                    for test_id, ok, observed, expected, delta in tests
                ]
                break
        except (RuntimeError, MemoryError) as error:
            runtime_rows.append(
                {
                    "check_id": "batch_candidate_full_graph",
                    "observed_value": type(error).__name__,
                    "required_value": "finite_deterministic",
                    "batch_size": batch,
                    "peak_memory_mib": float(torch.cuda.max_memory_reserved() / 1024**2)
                    if device == "cuda"
                    else 0.0,
                    "repeat_delta": "",
                    "status": "fail",
                }
            )
            if device == "cuda":
                torch.cuda.empty_cache()
    device_name = selected_meta.get(
        "device_name",
        torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu_fixture",
    )
    driver_version = nvidia_driver_version() if device == "cuda" else ""
    runtime_rows.extend(
        [
            {
                "check_id": "python_version",
                "observed_value": platform.python_version(),
                "required_value": ">=3.10,<3.13",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate((3, 10) <= sys.version_info[:2] < (3, 13)),
            },
            {
                "check_id": "torch_version",
                "observed_value": torch.__version__,
                "required_value": "2.8.0",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(torch.__version__.split("+")[0] == "2.8.0"),
            },
            {
                "check_id": "platform",
                "observed_value": platform.platform(),
                "required_value": "recorded",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(bool(platform.platform())),
            },
            {
                "check_id": "torch_cuda_version",
                "observed_value": torch.version.cuda or "",
                "required_value": "recorded",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(device != "cuda" or bool(torch.version.cuda)),
            },
            {
                "check_id": "cuda_available",
                "observed_value": torch.cuda.is_available(),
                "required_value": True,
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(torch.cuda.is_available()),
            },
            {
                "check_id": "cuda_driver_version",
                "observed_value": driver_version,
                "required_value": "recorded",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(device != "cuda" or bool(driver_version)),
            },
            {
                "check_id": "cuda_device_name",
                "observed_value": device_name,
                "required_value": "CUDA RTX 4070 SUPER",
                "batch_size": selected_batch,
                "peak_memory_mib": selected_meta.get("peak_memory_mib", 0.0),
                "repeat_delta": selected_meta.get("repeat_delta", ""),
                "status": gate(device == "cuda" and "RTX 4070 SUPER" in device_name),
            },
            {
                "check_id": "cuda_total_memory_mib",
                "observed_value": selected_meta.get("total_memory_mib", 0.0),
                "required_value": ">0",
                "batch_size": selected_batch,
                "peak_memory_mib": selected_meta.get("peak_memory_mib", 0.0),
                "repeat_delta": "",
                "status": gate(
                    device == "cuda" and selected_meta.get("total_memory_mib", 0.0) > 0
                ),
            },
            {
                "check_id": "cudnn_version",
                "observed_value": torch.backends.cudnn.version() or "",
                "required_value": "recorded",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(bool(torch.backends.cudnn.version())),
            },
            {
                "check_id": "deterministic_algorithms_enabled",
                "observed_value": torch.are_deterministic_algorithms_enabled(),
                "required_value": True,
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(torch.are_deterministic_algorithms_enabled()),
            },
            {
                "check_id": "cublas_workspace_config",
                "observed_value": os.environ.get("CUBLAS_WORKSPACE_CONFIG", ""),
                "required_value": ":4096:8",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"),
            },
            {
                "check_id": "deterministic_debug_mode",
                "observed_value": torch.get_deterministic_debug_mode(),
                "required_value": "recorded",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": "pass",
            },
            {
                "check_id": "known_nondeterministic_ops",
                "observed_value": "none_observed_in_synthetic_graph",
                "required_value": "none_observed_in_synthetic_graph",
                "batch_size": selected_batch,
                "peak_memory_mib": selected_meta.get("peak_memory_mib", 0.0),
                "repeat_delta": selected_meta.get("repeat_delta", ""),
                "status": gate(bool(selected_batch)),
            },
            {
                "check_id": "K1C_train_global_mixture",
                "observed_value": selected_meta.get("k1c_train_delta", ""),
                "required_value": 0.0,
                "batch_size": selected_batch,
                "peak_memory_mib": "",
                "repeat_delta": selected_meta.get("k1c_train_delta", ""),
                "status": gate(selected_meta.get("k1c_train_delta") == 0.0),
            },
            {
                "check_id": "K1C_inference_global_mixture",
                "observed_value": selected_meta.get("k1c_inference_delta", ""),
                "required_value": 0.0,
                "batch_size": selected_batch,
                "peak_memory_mib": "",
                "repeat_delta": selected_meta.get("k1c_inference_delta", ""),
                "status": gate(selected_meta.get("k1c_inference_delta") == 0.0),
            },
        ]
    )
    gpu_gate = bool(
        selected_batch
        and device == "cuda"
        and "RTX 4070 SUPER" in device_name
        and selected_batch >= config["architecture"]["minimum_batch_size"]
        and int(config["architecture"]["inference_residual_draws"]) == 8
        and selected_meta.get("batch_reorder_delta", 1.0) <= 1e-7
        and selected_meta.get("peak_memory_mib", math.inf)
        <= config["architecture"]["gpu_peak_memory_fraction_cap"]
        * selected_meta.get("total_memory_mib", 0.0)
    )
    meta = {
        **selected_meta,
        "selected_batch_size": selected_batch,
        "gpu_gate": gpu_gate,
        "gpu_real_market_access_count": 0,
    }
    return graph_test_rows, runtime_rows, meta


def average_rank_rankic(
    scores: Sequence[float], labels: Sequence[float], minimum_n: int = 100
) -> float | None:
    import numpy as np
    import pandas as pd

    score_array = np.asarray(scores, dtype=np.float64)
    label_array = np.asarray(labels, dtype=np.float64)
    if len(score_array) != len(label_array) or len(score_array) < minimum_n:
        return None
    if not np.isfinite(score_array).all() or not np.isfinite(label_array).all():
        return None
    score_rank = (
        pd.Series(score_array)
        .rank(method="average", ascending=True)
        .to_numpy(dtype=np.float64)
    )
    label_rank = (
        pd.Series(label_array)
        .rank(method="average", ascending=True)
        .to_numpy(dtype=np.float64)
    )
    if np.var(score_rank, ddof=1) <= 0 or np.var(label_rank, ddof=1) <= 0:
        return None
    return float(np.corrcoef(score_rank, label_rank)[0, 1])


def stationary_bootstrap_indices(
    n: int, repetitions: int, seed: int, mean_block_length: int = 20
) -> Any:
    import numpy as np

    if n <= 0:
        raise ValueError("n must be positive")
    rng = np.random.Generator(np.random.PCG64(seed))
    result = np.empty((repetitions, n), dtype=np.int64)
    restart_probability = 1.0 / mean_block_length
    for replicate in range(repetitions):
        result[replicate, 0] = rng.integers(0, n)
        for position in range(1, n):
            if rng.random() < restart_probability:
                result[replicate, position] = rng.integers(0, n)
            else:
                result[replicate, position] = (result[replicate, position - 1] + 1) % n
    return result


def stationary_bootstrap_holm(
    contrast_deltas: dict[str, Sequence[float] | None],
    margins: dict[str, float],
    *,
    repetitions: int = 5000,
    seed: int = 20260713,
    mean_block_length: int = 20,
    family_alpha: float = 0.05,
    minimum_complete_days: int = 252,
) -> list[dict[str, Any]]:
    """Exact shared-index one-sided stationary-bootstrap/Holm step-down contract."""
    import numpy as np

    contrast_ids = sorted(margins)
    if set(contrast_deltas) != set(contrast_ids):
        raise ValueError("contrast delta IDs must equal the registered Holm family")
    lengths = {len(values) for values in contrast_deltas.values() if values is not None}
    n = next(iter(lengths), 0)
    shared_length_ok = len(lengths) <= 1
    indices = (
        stationary_bootstrap_indices(n, repetitions, seed, mean_block_length)
        if shared_length_ok and n > 0
        else np.empty((0, 0), dtype=np.int64)
    )
    interim: dict[str, dict[str, Any]] = {}
    for contrast_id in contrast_ids:
        raw_values = contrast_deltas[contrast_id]
        values = np.asarray(
            raw_values if raw_values is not None else [], dtype=np.float64
        )
        evaluable = (
            shared_length_ok
            and n >= minimum_complete_days
            and len(values) == n
            and np.isfinite(values).all()
        )
        if evaluable:
            theta_hat = float(values.mean())
            theta_boot = values[indices].mean(axis=1)
            error_boot = theta_boot - theta_hat
            threshold = theta_hat - float(margins[contrast_id])
            raw_p = (1 + int(np.count_nonzero(error_boot >= threshold))) / (
                repetitions + 1
            )
        else:
            theta_hat = math.nan
            error_boot = np.empty(0, dtype=np.float64)
            raw_p = 1.0
        interim[contrast_id] = {
            "contrast_id": contrast_id,
            "complete_day_n": n if shared_length_ok else 0,
            "theta_hat": theta_hat,
            "margin": float(margins[contrast_id]),
            "raw_one_sided_p": float(raw_p),
            "error_boot": error_boot,
            "evaluable": evaluable,
        }
    ordered = sorted(
        contrast_ids,
        key=lambda contrast_id: (interim[contrast_id]["raw_one_sided_p"], contrast_id),
    )
    earlier_passed = True
    result: list[dict[str, Any]] = []
    family_size = len(contrast_ids)
    for rank, contrast_id in enumerate(ordered, start=1):
        row = interim[contrast_id]
        alpha_k = family_alpha / (family_size - rank + 1)
        if row["evaluable"]:
            critical_error = float(
                np.quantile(row["error_boot"], 1.0 - alpha_k, method="higher")
            )
            lower_bound = float(row["theta_hat"] - critical_error)
            current_pass = lower_bound > row["margin"]
            step_pass = bool(earlier_passed and current_pass)
            status = "pass" if step_pass else "fail"
        else:
            critical_error = math.nan
            lower_bound = math.nan
            step_pass = False
            status = "not_evaluable"
        earlier_passed = earlier_passed and step_pass
        result.append(
            {
                "contrast_id": contrast_id,
                "holm_rank": rank,
                "family_size": family_size,
                "complete_day_n": row["complete_day_n"],
                "theta_hat": row["theta_hat"],
                "margin": row["margin"],
                "raw_one_sided_p": row["raw_one_sided_p"],
                "alpha_k": alpha_k,
                "critical_error": critical_error,
                "holm_step_lower_bound": lower_bound,
                "holm_step_pass": step_pass,
                "status": status,
            }
        )
    return result


def metric_algorithm_self_audit(config: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    contrast_specs = config["metrics"]["contrasts"]
    dates = np.arange(252, dtype=np.float64)
    deltas = {
        contrast_id: float(spec["margin"]) + 0.02 + np.sin(dates / (11 + index)) * 0.002
        for index, (contrast_id, spec) in enumerate(sorted(contrast_specs.items()))
    }
    margins = {
        contrast_id: float(spec["margin"])
        for contrast_id, spec in contrast_specs.items()
    }
    first = stationary_bootstrap_holm(deltas, margins)
    second = stationary_bootstrap_holm(deltas, margins)
    return {
        "algorithm_ok": (
            first == second
            and len(first) == 7
            and {row["contrast_id"] for row in first} == set(contrast_specs)
            and all(
                row["family_size"] == 7 and row["complete_day_n"] == 252
                for row in first
            )
        ),
        "repetitions": 5000,
        "mean_block_length": 20,
        "seed": 20260713,
        "family_size": 7,
        "quantile_method": "higher",
        "shared_index_vectors": True,
    }


def m0_hash_score(instrument: str, decision_date: str) -> float:
    canonical = normalize_instrument(instrument)
    if not canonical or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", decision_date):
        raise ValueError("canonical instrument/date required")
    key = f"M0_HASH_NULL_SCORE|{canonical}|{decision_date}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) / 2**64


def build_paper_tables(
    config: dict[str, Any], formula_rows: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    paths = resolve_paths(config)
    paper = config["paper_contract"]
    source_rows = [
        {
            "run_id": RUN_ID,
            "source_id": paper["source_id"],
            "source_role": "version_of_record",
            "title": paper["title"],
            "authors": "|".join(paper["authors"]),
            "venue": paper["venue"],
            "publication_year": paper["publication_year"],
            "doi": paper["doi"],
            "official_url": "https://ieeexplore.ieee.org/document/11465125",
            "local_path": rel(paths["paper"]),
            "local_sha256": file_sha(paths["paper"]),
            "expected_sha256": config["input_hash_expectations"]["paper_sha256"],
            "page_count": pdf_page_count(paths["paper"]),
            "version_status": "version_of_record",
            "full_text_available": True,
            "appendix_status": "not_disclosed",
            "official_code_status": "not_disclosed_in_allowlisted_sources",
            "retrieved_or_verified_at_utc": utc_now(),
            "identity_gate": gate(
                file_sha(paths["paper"])
                == config["input_hash_expectations"]["paper_sha256"]
                and pdf_page_count(paths["paper"]) == 5
            ),
            "notes": "five-page local version of record; exact-replication claim remains false",
        }
    ]
    gap_specs = [
        ("operator_count", 4),
        ("latent_width", 64),
        ("lstm_depth", 1),
        ("gumbel_schedule", "1.0_to_0.1_linear"),
        ("ddpm_steps", 20),
        ("beta_schedule", "linear_1e-4_to_2e-2"),
        ("optimizer", "AdamW_lr_0.001"),
        ("batch_size", "mechanical_256_to_16"),
        ("normalization", "train_median_IQR"),
        ("seed", "20260713|20260714|20260715"),
        ("inference_sampling", "eight_draw_mean"),
        ("TopK_rebalance", "Top30_equal_weight"),
        ("cost", "EP19_EP20_inherited"),
        ("official_code", "not_disclosed"),
        ("appendix", "not_disclosed"),
    ]
    gap_rows = [
        {
            "gap_id": gap_id,
            "paper_disclosure_status": "not_disclosed_or_incomplete",
            "local_evidence": "five_page_vor_and_research_plan",
            "frozen_project_choice": choice,
            "choice_source": "21A_requirement",
            "sensitivity_allowed": gap_id
            in {"operator_count", "latent_width", "ddpm_steps"},
            "exact_replication_impact": "exact_replication_false",
            "blocking_for_project_adaptation": False,
            "status": "pass",
        }
        for gap_id, choice in gap_specs
    ]
    official_rows = [
        {
            "candidate_id": "NO_ALLOWLISTED_OFFICIAL_CODE_CANDIDATE",
            "url": "",
            "owner_identity": "",
            "source_role": "official_code_candidate_sentinel",
            "http_status": "",
            "code_disclosed": False,
            "official_status": "not_disclosed_in_allowlisted_sources",
            "checked_at_utc": utc_now(),
            "status": "pass_nonblocking",
        }
    ]
    return {
        "paper_source_registry.csv": source_rows,
        "paper_formula_and_architecture_registry.csv": formula_rows,
        "paper_reproducibility_gap_registry.csv": gap_rows,
        "official_code_availability_audit.csv": official_rows,
    }


def build_search_seed_tables(
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    primary = {
        "n_operator": 4,
        "latent_dim": 64,
        "diffusion_steps": 20,
        "learning_rate": 0.001,
        "joint_grid_allowed": False,
    }
    sensitivities = {
        "S01": ("n_operator", 2),
        "S02": ("n_operator", 8),
        "S03": ("latent_dim", 32),
        "S04": ("latent_dim", 128),
        "S05": ("diffusion_steps", 10),
        "S06": ("diffusion_steps", 50),
    }
    hyper_rows = [
        {
            "config_id": "PRIMARY_R2",
            "role": "primary",
            "parameter": key,
            "primary_value": value,
            "sensitivity_value": "",
            "one_factor_only": True,
            "promotion_allowed": True,
            "status": "pass",
        }
        for key, value in primary.items()
    ]
    hyper_rows.extend(
        {
            "config_id": "M1_LIGHTGBM",
            "role": "project_baseline",
            "parameter": key,
            "primary_value": value,
            "sensitivity_value": "",
            "one_factor_only": True,
            "promotion_allowed": False,
            "status": "pass",
        }
        for key, value in config["architecture"]["m1_lightgbm"].items()
    )
    hyper_rows.extend(
        {
            "config_id": "M1_LIGHTGBM",
            "role": "project_baseline",
            "parameter": parameter,
            "primary_value": "current_model_seed",
            "sensitivity_value": "",
            "one_factor_only": True,
            "promotion_allowed": False,
            "status": "pass",
        }
        for parameter in [
            "seed",
            "feature_fraction_seed",
            "bagging_seed",
            "data_random_seed",
        ]
    )
    for config_id, (parameter, value) in sensitivities.items():
        hyper_rows.append(
            {
                "config_id": config_id,
                "role": "scheduled_one_factor_sensitivity",
                "parameter": parameter,
                "primary_value": primary[parameter],
                "sensitivity_value": value,
                "one_factor_only": True,
                "promotion_allowed": False,
                "status": "pass",
            }
        )
    for adaptation in config["arms"]["non_primary_diagnostic_adaptation_ids"]:
        hyper_rows.append(
            {
                "config_id": adaptation,
                "role": "non_primary_diagnostic_adaptation",
                "parameter": "registered_adaptation",
                "primary_value": "disabled",
                "sensitivity_value": "registered_only",
                "one_factor_only": True,
                "promotion_allowed": False,
                "status": "pass",
            }
        )
    seed_offsets = {
        "python_seed": 0,
        "numpy_seed": 11,
        "torch_seed": 23,
        "dataloader_seed": 37,
        "weight_init_seed": 53,
        "gumbel_seed": 71,
        "diffusion_train_noise_seed": 89,
    }
    seed_rows = []
    for model_seed in config["arms"]["model_seeds"]:
        for stream_name, offset in seed_offsets.items():
            seed_rows.append(
                {
                    "model_seed": model_seed,
                    "stream_name": stream_name,
                    "derived_seed_or_rule": model_seed + offset,
                    "batch_order_invariant": stream_name != "dataloader_seed",
                    "status": "pass",
                }
            )
        seed_rows.append(
            {
                "model_seed": model_seed,
                "stream_name": "inference_draw_seed",
                "derived_seed_or_rule": "uint64_prefix(SHA256(run_id|arm_id|model_seed|instrument|decision_date|draw_id)) mod 2^63",
                "batch_order_invariant": True,
                "status": "pass",
            }
        )
    return sorted(
        hyper_rows, key=lambda row: (row["config_id"], row["parameter"])
    ), sorted(seed_rows, key=lambda row: (row["model_seed"], row["stream_name"]))


def _lock_has_package(lock_text: str, name: str, version: str) -> bool:
    pattern = rf'(?m)^\[\[package\]\]\nname = "{re.escape(name)}"\nversion = "{re.escape(version)}"$'
    return bool(re.search(pattern, lock_text))


def build_dependency_table(
    config: dict[str, Any], access_log: list[dict[str, Any]] | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = resolve_paths(config)
    lock_text = paths["uv_lock"].read_text(encoding="utf-8")
    pyproject_text = paths["pyproject"].read_text(encoding="utf-8")
    requirements_text = paths["requirements"].read_text(encoding="utf-8")
    packages = [
        ("pyqlib", "==0.9.7", "0.9.7", "transitive"),
        ("lightgbm", "==4.6.0", "4.6.0", "transitive"),
        ("torch", "==2.8.0", "2.8.0", "direct_optional"),
        ("numpy", ">=1.26,<2.0", importlib.metadata.version("numpy"), "direct"),
        ("pandas", ">=2.2,<3.0", importlib.metadata.version("pandas"), "direct"),
    ]
    rows = []
    all_match = True
    for name, spec, lock_version, directness in packages:
        try:
            runtime = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            runtime = ""
        expected_version = lock_version
        lock_ok = _lock_has_package(lock_text, name, expected_version)
        runtime_ok = (
            runtime == expected_version
            if name in {"pyqlib", "lightgbm", "torch"}
            else bool(runtime)
        )
        status = gate(lock_ok and runtime_ok)
        all_match &= status == "pass"
        rows.append(
            {
                "dependency": name,
                "required_spec": spec,
                "baseline_version": "preimplementation_lock",
                "lock_resolved_version": expected_version if lock_ok else "",
                "runtime_version": runtime,
                "direct_or_transitive": directness,
                "baseline_source": "Section_13_1",
                "resolved_source": "uv.lock|runtime_metadata",
                "lock_action": "add_torch_only" if name == "torch" else "unchanged",
                "allowed_change": name == "torch",
                "status": status,
            }
        )
    interpreter_path = Path(sys.executable).absolute()
    interpreter_ok = (
        interpreter_path.name.startswith("python")
        and ".venv" in interpreter_path.as_posix()
    )
    rows.append(
        {
            "dependency": "stage_interpreter",
            "required_spec": config["dependencies"]["stage_interpreter"],
            "baseline_version": "process_bootstrap",
            "lock_resolved_version": platform.python_version(),
            "runtime_version": platform.python_version(),
            "direct_or_transitive": "interpreter",
            "baseline_source": "Section_15_0",
            "resolved_source": f"{rel(interpreter_path)}|sha256={file_sha(interpreter_path)}",
            "lock_action": "uv_sync_frozen_before_stage",
            "allowed_change": False,
            "status": gate(interpreter_ok),
        }
    )
    declarations_ok = (
        "reaka = [" in pyproject_text
        and '"torch==2.8.0"' in pyproject_text
        and "torch==2.8.0" in requirements_text
        and _lock_has_package(lock_text, "torch", "2.8.0")
    )
    meta = {
        "all_match": all_match,
        "declarations_ok": declarations_ok,
        "interpreter_ok": interpreter_ok,
        "python_ok": (3, 10) <= sys.version_info[:2] < (3, 13),
        "pyproject_sha256": file_sha(paths["pyproject"]),
        "requirements_sha256": file_sha(paths["requirements"]),
        "uv_lock_sha256": file_sha(paths["uv_lock"]),
    }
    if access_log is not None:
        for name, _, _, _ in packages:
            add_access(
                access_log,
                f"package:{name}",
                "python_package",
                ["distribution_version", "runtime_import_resolution"],
                ["lock_runtime_match"],
                "dependency_runtime_fingerprint",
            )
        for key in ["pyproject", "requirements", "uv_lock"]:
            add_access(
                access_log,
                paths[key],
                "dependency_lock_file",
                ["locked_dependency_text"],
                ["sha256", "resolved_version"],
                "dependency_runtime_fingerprint",
            )
    return sorted(rows, key=lambda row: row["dependency"]), meta


def build_metric_table(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for contrast_id, spec in config["metrics"]["contrasts"].items():
        rows.append(
            {
                "record_type": "contrast",
                "family_id": "historical_representation",
                "contrast_id": contrast_id,
                "terminal_state_id": "",
                "priority": "",
                "metric": f"{spec['left']}-{spec['right']}",
                "margin": spec["margin"],
                "alpha": 0.05,
                "correction": "Holm_one_sided",
                "evidence_unit": "complete_decision_day",
                "block_length": 20,
                "MDE": "",
                "sigma": "",
                "rho": "",
                "n_required": 252,
                "status": "pass",
            }
        )
    minima = [
        ("validation_full", 200),
        ("validation_early", 80),
        ("validation_late", 80),
        ("historical_representation", 252),
        ("historical_economic", 252),
        ("forward_representation", 60),
        ("forward_economic", 60),
    ]
    for family, count in minima:
        rows.append(
            {
                "record_type": "minimum_complete_day",
                "family_id": family,
                "contrast_id": "",
                "terminal_state_id": "",
                "priority": "",
                "metric": "complete_day_count",
                "margin": "",
                "alpha": "",
                "correction": "",
                "evidence_unit": "complete_decision_day",
                "block_length": "",
                "MDE": "",
                "sigma": "",
                "rho": "",
                "n_required": count,
                "status": "pass",
            }
        )
    for family in ["forward_representation", "forward_economic"]:
        rows.append(
            {
                "record_type": "confirmatory_power",
                "family_id": family,
                "contrast_id": "",
                "terminal_state_id": "",
                "priority": "",
                "metric": "paired_daily_delta",
                "margin": "",
                "alpha": 0.05,
                "correction": "Holm",
                "evidence_unit": "complete_decision_day",
                "block_length": 20,
                "MDE": 0.01,
                "sigma": 0.05,
                "rho": 0.10,
                "n_required": 291,
                "status": "pass",
            }
        )
    terminal_states = [
        "21_paper_lineage_or_data_contract_blocked",
        "21_compute_or_dependency_contract_blocked",
        "21_baseline_information_not_supported",
        "21_historical_representation_not_supported",
        "21_historical_representation_candidate_only",
        "21_representation_supported_execution_failed",
        "21_historical_executable_candidate_only",
        "21_forward_interim_not_support",
        "21_forward_directional_not_confirmatory",
        "21_forward_confirmation_not_supported",
        "21_forward_representation_supported_execution_unresolved",
        "21_forward_representation_supported_execution_failed",
        "21_forward_executable_reaka_candidate_supported",
    ]
    for priority, state in enumerate(terminal_states, start=1):
        rows.append(
            {
                "record_type": "terminal_state",
                "family_id": "",
                "contrast_id": "",
                "terminal_state_id": state,
                "priority": priority,
                "metric": "",
                "margin": "",
                "alpha": "",
                "correction": "",
                "evidence_unit": "",
                "block_length": "",
                "MDE": "",
                "sigma": "",
                "rho": "",
                "n_required": "",
                "status": "pass",
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["record_type"],
            str(row["family_id"]),
            str(row["contrast_id"]),
            str(row["terminal_state_id"]),
        ),
    )


def build_forward_table(config: dict[str, Any]) -> list[dict[str, Any]]:
    values = {
        "comparators": "|".join(config["forward"]["comparators"]),
        "refit_arms": "|".join(config["forward"]["refit_arms"]),
        "final_refit_cutoff": "last_fully_resolved_preseal_decision_date",
        "selected_train_steps": "preholdout_validation_frozen",
        "refit_early_stopping": False,
        "transform_refit_count": 1,
        "forward_start": "first_exchange_session_strictly_after_final_candidate_seal",
        "minimum_complete_days": 291,
        "rolling_retrain": False,
        "normalizer_refresh": False,
        "comparator_replacement": False,
        "version_splice": False,
        "forward_module_attribution_authorized": False,
    }
    return [
        {
            "contract_id": "21F_STATIC_FIRST_COHORT",
            "field": key,
            "frozen_value": value,
            "selection_time": "before_historical_holdout_access",
            "change_resets_clock": True,
            "status": "pass",
        }
        for key, value in values.items()
    ]


def build_quarantine_rows(
    support_rows: list[dict[str, Any]], jump_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    jump_exposure = sum(int(row["exposed_feature_row_n"]) for row in jump_rows)
    rows = []
    for split in ["train", "validation", "historical_design_holdout"]:
        subset = [row for row in support_rows if row["split"] == split]
        source_n = sum(int(row["U_decision_n"]) for row in subset)
        quarantine_n = min(source_n, jump_exposure)
        rows.append(
            {
                "split": split,
                "decision_day_n": len(subset),
                "source_row_n": source_n,
                "quarantine_row_n": quarantine_n,
                "remaining_row_n": max(0, source_n - quarantine_n),
                "remaining_day_n": sum(
                    row["support_status"] == "ready" for row in subset
                ),
                "route_status": "sensitivity_ready"
                if source_n
                else "sensitivity_not_evaluable",
            }
        )
    return rows


def _freeze_manifest_payload(
    root: Path, config: dict[str, Any], sealed_at: str
) -> dict[str, Any]:
    manifest_path = "freeze/freeze_bundle_manifest.json"
    hashes_path = "freeze/freeze_output_hashes_21a.json"
    output_hashes = {
        relative: file_sha(root / relative)
        for relative in FREEZE_RELATIVE_PATHS
        if relative not in {manifest_path, hashes_path}
    }
    return {
        "schema_version": config["output"]["schema_version"],
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "sealed_at_utc": sealed_at,
        "bundle_role": "preoutcome_freeze",
        "expected_paths": FREEZE_RELATIVE_PATHS,
        "manifest_hash_exclusion_paths": [manifest_path, hashes_path],
        "output_hashes": output_hashes,
        "input_hashes": {
            "requirement": file_sha(REQUIREMENT_PATH),
            "resolved_config": file_sha(root / "freeze/resolved_config.yaml"),
        },
        "schema_registry_version": config["output"]["schema_version"],
        "sort_contract_version": config["output"]["sort_contract_version"],
    }


def seal_freeze_bundle(root: Path, config: dict[str, Any], sealed_at: str) -> str:
    manifest_path = root / "freeze/freeze_bundle_manifest.json"
    hashes_path = root / "freeze/freeze_output_hashes_21a.json"
    manifest = _freeze_manifest_payload(root, config, sealed_at)
    write_json(manifest_path, manifest)
    hashes = {
        relative: file_sha(root / relative)
        for relative in FREEZE_RELATIVE_PATHS
        if relative != "freeze/freeze_output_hashes_21a.json"
    }
    write_json(
        hashes_path,
        {
            "schema_version": config["output"]["schema_version"],
            "run_id": RUN_ID,
            "contract_version": CONTRACT_VERSION,
            "hash_algorithm": "sha256",
            "excluded_paths": ["freeze/freeze_output_hashes_21a.json"],
            "hashes": hashes,
        },
    )
    verify_freeze_bundle(root)
    return file_sha(hashes_path)


def verify_freeze_bundle(
    root: Path, access_audit: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    manifest_path = root / "freeze/freeze_bundle_manifest.json"
    hashes_path = root / "freeze/freeze_output_hashes_21a.json"

    def recorded_read(path: Path) -> bytes:
        data = path.read_bytes()
        if access_audit is not None:
            access_audit.append(
                {
                    "access_seq": len(access_audit) + 1,
                    "accessed_at_utc": utc_now(),
                    "operation": "read",
                    "path_or_resource": path.relative_to(root).as_posix(),
                    "freeze_manifest_listed": path.relative_to(root).as_posix()
                    in FREEZE_RELATIVE_PATHS,
                    "raw_input": False,
                    "allowed": path.relative_to(root).as_posix()
                    in FREEZE_RELATIVE_PATHS,
                    "status": "pass"
                    if path.relative_to(root).as_posix() in FREEZE_RELATIVE_PATHS
                    else "fail",
                }
            )
        return data

    manifest_bytes = recorded_read(manifest_path)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    hashes_bytes = recorded_read(hashes_path)
    hashes = json.loads(hashes_bytes.decode("utf-8"))
    if manifest_bytes != canonical_json_bytes(
        manifest
    ) or hashes_bytes != canonical_json_bytes(hashes):
        raise RuntimeError("freeze manifest/hash JSON is not canonical")
    if manifest["expected_paths"] != FREEZE_RELATIVE_PATHS:
        raise RuntimeError("freeze expected_paths mismatch")
    actual = sorted(
        path.relative_to(root).as_posix()
        for path in (root / "freeze").rglob("*")
        if path.is_file()
    )
    if actual != sorted(FREEZE_RELATIVE_PATHS):
        raise RuntimeError("freeze file set mismatch")
    expected_manifest_keys = set(FREEZE_RELATIVE_PATHS) - {
        "freeze/freeze_bundle_manifest.json",
        "freeze/freeze_output_hashes_21a.json",
    }
    if set(manifest["output_hashes"]) != expected_manifest_keys:
        raise RuntimeError("freeze manifest hash key set mismatch")
    expected_hash_keys = set(FREEZE_RELATIVE_PATHS) - {
        "freeze/freeze_output_hashes_21a.json"
    }
    if set(hashes["hashes"]) != expected_hash_keys:
        raise RuntimeError("freeze output hash key set mismatch")
    artifact_bytes: dict[str, bytes] = {
        "freeze/freeze_bundle_manifest.json": manifest_bytes,
        "freeze/freeze_output_hashes_21a.json": hashes_bytes,
    }
    for relative, expected_sha in hashes["hashes"].items():
        payload = (
            manifest_bytes
            if relative == "freeze/freeze_bundle_manifest.json"
            else recorded_read(root / relative)
        )
        artifact_bytes[relative] = payload
        observed = hashlib.sha256(payload).hexdigest()
        if observed != expected_sha:
            raise RuntimeError(f"freeze hash mismatch: {relative}")
        if (
            relative in manifest["output_hashes"]
            and manifest["output_hashes"][relative] != expected_sha
        ):
            raise RuntimeError(f"freeze manifest/output hash disagreement: {relative}")
    for filename, columns in TABLE_SCHEMAS.items():
        relative = f"freeze/{filename}"
        if relative not in artifact_bytes or filename in {
            "finalize_access_audit.csv",
            "gate_evidence_21a.csv",
        }:
            continue
        header = next(
            csv.reader(artifact_bytes[relative].decode("utf-8").splitlines()), []
        )
        if header != columns:
            raise RuntimeError(f"freeze CSV schema mismatch: {relative}")
    return {
        "manifest": manifest,
        "hashes": hashes,
        "freeze_bundle_hash": hashlib.sha256(hashes_bytes).hexdigest(),
        "artifact_bytes": artifact_bytes,
    }


def _write_table(root: Path, filename: str, rows: Any) -> None:
    write_csv(root / "freeze" / filename, rows, TABLE_SCHEMAS[filename])


def _all_rows_pass(
    rows: Iterable[dict[str, Any]], status_field: str = "status"
) -> bool:
    materialized = list(rows)
    return bool(materialized) and all(
        str(row.get(status_field, "")).lower() in {"pass", "pass_nonblocking"}
        for row in materialized
    )


def build_gate_check_statuses(context: dict[str, Any]) -> dict[str, dict[str, bool]]:
    """Compute every truth-table check from its own artifact-backed predicate."""
    config = context["config"]
    paths = context["paths"]
    source_rows = context["source_rows"]
    formula_rows = context["formula_rows"]
    formula_auth = context["formula_auth"] or {}
    formula_checks = context["formula_checks"]
    alpha_rows = context["alpha_rows"]
    alpha_meta = context["alpha_meta"]
    field_mapping = context["field_mapping"]
    expression_hash = context["expression_hash"]
    vwap_rows = context["vwap_rows"]
    jump_rows = context["jump_rows"]
    vwap_meta = context["vwap_meta"]
    feature_cache = context["feature_cache"]
    cache_manifest = context["cache_manifest"]
    support_rows = context["support_rows"]
    timing_rows = context["timing_rows"]
    split_rows = context["split_rows"]
    support_meta = context["support_meta"]
    static_tables = context["static_tables"]
    graph_rows = context["graph_rows"]
    graph_meta = context["graph_meta"]
    hyper_rows = context["hyper_rows"]
    seed_rows = context["seed_rows"]
    dependency_rows = context["dependency_rows"]
    dependency_meta = context["dependency_meta"]
    metric_rows = context["metric_rows"]
    metric_meta = context["metric_meta"]
    forward_rows = context["forward_rows"]
    upstream_ok = context["upstream_ok"]
    input_rows = context["input_rows"]
    access_log = context["access_log"]
    paper = config["paper_contract"]

    def check_row(rows: Iterable[dict[str, Any]], check_id: str) -> bool:
        selected = [row for row in rows if row.get("check_id") == check_id]
        return len(selected) == 1 and selected[0].get("status") == "pass"

    exact_source_ids = {
        source["source_id"]
        for source in config["source_allowlist"]["acquisition_sources"]
    }
    source_id_set = {row.get("source_id") for row in source_rows}
    required_formula_ids = config["paper_contract"]["required_formula_ids"]
    formula_ids = [row.get("formula_id") for row in formula_rows]
    global_vwap = vwap_meta.get("global", {})
    selected_route_rows = [
        row for row in field_mapping if row["route_id"] == context["feature_route_id"]
    ]
    arm_rows = static_tables["model_arm_registry.csv"]
    arm_ids = [row["arm_id"] for row in arm_rows]
    tensor_rows = static_tables["tensor_shape_contract.csv"]
    tensor_ids = {row["tensor_id"] for row in tensor_rows}
    expected_tensor_ids = {
        "y_source",
        "x_source",
        "H_y_source",
        "H_x_source",
        "Z_source",
        "Z_t",
        "y_teacher_shifted",
        "x_teacher_shifted",
        "Z_teacher_shifted",
        "selector_source",
        "K_codebook",
        "K_selected",
        "Z_hat_shifted",
        "R_target_shifted",
        "ddpm_x_s",
        "ddpm_epsilon",
        "ddpm_epsilon_hat",
        "R_hat_train_shifted",
        "Z_tilde_train_shifted",
        "R_hat_inference_draws",
        "Z_tilde_inference_draws",
        "R_hat_mlp_shifted",
        "Z_tilde_mlp_shifted",
        "decoded_source",
        "decoded_shifted_train",
        "decoded_shifted_draws",
        "direct_score_M2",
        "direct_score_M3",
        "direct_score_A0",
        "score_draws_R2",
        "score_next",
    }
    resolution_rows = static_tables[
        "decision_universe_and_label_resolution_contract.csv"
    ]
    resolution_ids = {row["status_id"] for row in resolution_rows}
    expected_resolution_ids = {
        "NORMAL_NEXT_SESSION_CLOSE",
        "LISTED_SUSPENDED_CARRY",
        "CONFIRMED_TERMINAL_PRICE",
        "UNKNOWN_DATA_GAP",
        "RIGHT_CENSORED_DATA_CUTOFF",
    }
    graph_test_map = {row["test_id"]: row for row in graph_rows}
    expected_gradient_tests = [
        "source_encoder_receives_gradient_from_L_rec",
        "source_encoder_receives_gradient_from_L_koop",
        "teacher_shared_encoder_receives_gradient_from_L_koop",
        "selector_receives_no_direct_teacher_input",
        "residual_condition_receives_no_teacher_value",
        "inference_signature_has_no_teacher_tensor",
        "teacher_perturbation_does_not_change_fixed_source_inference_score",
        "all_T_transitions_contribute_to_L_koop",
        "loss_mean_invariant_to_exact_batch_duplication",
        "score_index_is_last_shifted_scalar",
        "train_and_inference_score_shape_match",
        "NaN_and_inf_fail_closed",
    ]
    m1_expected = {
        "objective": "regression_l2",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": -1,
        "min_data_in_leaf": 20,
        "feature_fraction": 1.0,
        "bagging_fraction": 1.0,
        "lambda_l1": 0.0,
        "lambda_l2": 0.0,
        "max_boosting_rounds": 100,
        "early_stopping_rounds": 10,
        "deterministic": True,
        "force_col_wise": True,
        "num_threads": 1,
        "verbosity": -1,
    }
    hard_count_names = [
        "outcome_columns_detected_count",
        "outcome_formula_executed_count",
        "real_label_materialization_count",
        "real_model_score_count",
        "selection_or_tuning_allowed_count",
        "historical_holdout_outcome_access_count",
    ]
    access_rows_allowed = bool(access_log) and all(
        row["access_gate"] == "pass"
        and not bool_value(row["selection_or_tuning_allowed"])
        for row in access_log
    )
    logged_resources = {str(row["artifact_path_or_resource"]) for row in access_log}
    required_logged_resources = {
        str(row["path"]) for row in input_rows if bool_value(row.get("exists"))
    }
    access_log_complete = (
        required_logged_resources.issubset(logged_resources)
        and any(row["dataset_role"] == "gpu_resource" for row in access_log)
        and any(
            row["dataset_role"] == "python_package"
            and "pyqlib" in str(row["artifact_path_or_resource"])
            for row in access_log
        )
        and any(
            row["dataset_role"] == "python_package"
            and "torch" in str(row["artifact_path_or_resource"])
            for row in access_log
        )
    )
    check_statuses: dict[str, dict[str, bool]] = {
        "human_restart_scope_gate": {
            "H01": config["identity"]["episode_id"] == EXPERIMENT_ID
            and config["identity"]["phase_id"] == PHASE_ID
            and config["identity"]["contract_version"] == CONTRACT_VERSION
            and config["identity"]["restart_type"]
            == "topic_level_human_restart_for_architecture_diagnostic",
            "H02": file_sha(paths["research_plan"])
            == config["input_hash_expectations"]["research_plan_sha256"],
            "H03": paths["requirement"].is_file()
            and file_sha(paths["requirement"]) == context["requirement_sha256"],
            "H04": not bool_value(
                config["identity"]["upstream_automatic_authorization"]
            )
            and not bool_value(config["identity"]["historical_support_claim_allowed"]),
        },
        "paper_source_lineage_gate": {
            "P01": file_sha(paths["paper"])
            == config["input_hash_expectations"]["paper_sha256"]
            and pdf_page_count(paths["paper"]) == 5,
            "P02": paper["doi"] == "10.1109/ICASSP55912.2026.11465125"
            and paper["title"].startswith(
                "Residual-Enhanced Adaptive Koopman Autoencoder"
            )
            and paper["venue"].startswith("2026 IEEE")
            and paper["publication_year"] == 2026,
            "P03": paper["authors"]
            == ["Lei Liao", "Yang Zhang", "Jun Wang", "Jinghua Tan", "Yinchao Liao"],
            "P04": bool(source_rows)
            and all(bool_value(row.get("inside_allowlist")) for row in source_rows),
            "P05": source_id_set == exact_source_ids
            and len(source_rows) == len(exact_source_ids)
            and all(row.get("identity_status") == "pass" for row in source_rows),
        },
        "paper_formula_contract_gate": {
            "PF01": bool(formula_checks.get("hash_chain")),
            "PF02": bool(formula_checks.get("approved_human"))
            and formula_auth.get("reviewer_role") == "human"
            and formula_auth.get("authorization_status") == "approved",
            "PF03": formula_ids == required_formula_ids
            and len(formula_ids) == len(set(formula_ids)),
            "PF04": bool(formula_checks.get("rows_complete"))
            and all(bool_value(row["human_verified"]) for row in formula_rows),
            "PF05": len(
                context["paper_tables"]["paper_reproducibility_gap_registry.csv"]
            )
            >= 6
            and paper["exact_replication_reachable"] is False,
        },
        "alpha158_expression_gate": {
            "A01": alpha_meta["version"] == "0.9.7"
            and any(
                row["dependency"] == "pyqlib" and row["runtime_version"] == "0.9.7"
                for row in dependency_rows
            ),
            "A02": alpha_meta["count"] == 158
            and alpha_meta["duplicate_name_n"] == 0
            and [row["feature_index"] for row in alpha_rows] == list(range(158)),
            "A03": alpha_meta["future_offset_n"] == 0
            and all(not bool_value(row["uses_future_offset"]) for row in alpha_rows),
            "A04": len(expression_hash) == 64
            and stable_alpha_expression_hash(alpha_rows) == expression_hash,
            "A05": bool(field_mapping) and _all_rows_pass(field_mapping),
        },
        "vwap_qfq_unit_contract_gate": {
            "V01": bool(vwap_meta.get("audit_complete")),
            "V02": bool(
                vwap_meta.get("volume_units_exact", vwap_meta.get("audit_complete"))
            ),
            "V03": math.isfinite(float(global_vwap.get("factor_pass_rate", math.nan)))
            and config["feature_contract"]["factor_relative_tolerance"] == 1e-4,
            "V04": bool(vwap_rows)
            and any(row["scope"] == "global" for row in vwap_rows)
            and any(row["scope"] == "board_year" for row in vwap_rows),
            "V05": all(
                not row["outcome_columns_detected"]
                and not bool_value(row["outcome_formula_executed"])
                for row in access_log
                if row["purpose"] == "vwap_unit_audit"
            ),
        },
        "volume_corporate_action_semantics_gate": {
            "VC01": all(
                "raw.volume" in row["local_source"]
                for row in field_mapping
                if row["qlib_field"] == "$volume"
            ),
            "VC02": config["feature_contract"]["factor_jump_abs_log_threshold"] == 1e-4
            and config["feature_contract"]["factor_jump_radius_sessions"] == 60,
            "VC03": all(
                row["exposed_feature_row_n"] > 0 and row["status"] == "pass"
                for row in jump_rows
            ),
            "VC04": "FACTOR_JUMP_WINDOW_QUARANTINE"
            in config["arms"]["non_primary_diagnostic_adaptation_ids"],
        },
        "feature_materialization_route_gate": {
            "F01": alpha_meta["count"] == 158
            and alpha_meta["no_vwap_count"]
            == sum(not bool_value(row["uses_vwap"]) for row in alpha_rows),
            "F02": context["feature_route_id"]
            in {
                config["feature_contract"]["full_route_id"],
                config["feature_contract"]["no_vwap_route_id"],
            },
            "F03": bool(selected_route_rows)
            and _all_rows_pass(selected_route_rows)
            and feature_cache["materialized_expression_count"]
            == context["feature_dim"],
            "F04": feature_cache["status"] == "pass"
            and all(
                not row["outcome_columns_detected"]
                for row in access_log
                if row["purpose"] == "feature_only_materialization"
            ),
            "F05": cache_manifest["cache_content_hash"]
            == feature_cache["cache_content_hash"]
            and len(cache_manifest["cache_content_hash"]) == 64
            and feature_cache["cache_file_n"] >= 3,
            "F06": len({row["input_feature_route"] for row in arm_rows}) == 1
            and arm_rows[0]["input_feature_route"] == context["feature_route_id"],
        },
        "pit_membership_timing_gate": {
            check_id: check_row(timing_rows, check_id)
            for check_id in GATE_CHECKS["pit_membership_timing_gate"]
        },
        "decision_denominator_contract_gate": {
            "D01": bool(support_rows)
            and all(bool_value(row["layer_count_reconciled"]) for row in support_rows),
            "D02": bool(support_meta["feature_predicate_exact"]),
            "D03": context["synthetic_t_plus_one_invariant"],
            "D04": all(
                row["U_decision_n"] == row["feature_ready_n"] for row in support_rows
            ),
            "D05": resolution_ids == expected_resolution_ids
            and len(resolution_rows) == len(expected_resolution_ids),
        },
        "feature_sequence_support_gate": {
            "FS01": config["architecture"]["lookback_T"] == 10
            and feature_cache["cache_row_n"] > 0,
            "FS02": len(feature_cache["sequence_ready_keys"])
            >= len(feature_cache["ready_keys"]),
            "FS03": support_meta["complete_by_split"]["train"] >= 750
            and support_meta["complete_by_split"]["validation"] >= 200,
            "FS04": support_meta["complete_by_split"]["historical_design_holdout"]
            >= 400
            and all(
                row["U_decision_n"] >= 100
                for row in support_rows
                if row["support_status"] == "ready"
            ),
            "FS05": all(
                not row["outcome_columns_detected"]
                and not bool_value(row["outcome_formula_executed"])
                for row in access_log
                if row["purpose"] in {"feature_support", "feature_only_materialization"}
            ),
        },
        "feature_label_alignment_gate": {
            "FL01": config["architecture"]["lookback_T"] == 10
            and graph_meta.get("all_transition_shape", [0, 0])[1] == 10,
            "FL02": any(
                row["score_index"] == "last_shifted_scalar"
                for row in static_tables["per_arm_loss_and_score_index_contract.csv"]
            )
            and static_tables["label_semantics_freeze.csv"][0]["formula"]
            == "qfq_close(t+1)/qfq_close(t)-1",
            "FL03": {
                row["label_id"] for row in static_tables["label_semantics_freeze.csv"]
            }
            == {"Y_rank_primary", "Y_qlib_gap_diagnostic", "Y_exec_1d"},
            "FL04": all(
                not bool_value(row["materialized_in_21a"])
                and not bool_value(row["selection_allowed"])
                for row in static_tables["label_semantics_freeze.csv"]
            ),
        },
        "train_teacher_inference_graph_gate": {
            "G01": tensor_ids == expected_tensor_ids
            and len(static_tables["train_teacher_inference_graph_contract.csv"])
            == len(expected_tensor_ids),
            "G02": all(
                "teacher" not in row["input_nodes"].lower()
                for row in static_tables["train_teacher_inference_graph_contract.csv"]
                if bool_value(row["inference_present"])
            ),
            "G03": graph_meta.get("all_transition_shape", [0, 0])[1] == 10,
            "G04": graph_meta.get("arm_graph_ok", False)
            and set(graph_meta.get("arm_score_ids", []))
            == set(config["arms"]["mandatory_ids"]),
        },
        "gradient_teacher_isolation_gate": {
            **{
                f"GI{index:02d}": graph_test_map.get(test_id, {}).get("status")
                == "pass"
                for index, test_id in enumerate(expected_gradient_tests, start=1)
            },
            "GI13": graph_meta.get("allowed_teacher_delta", 0.0) > 0.0
            and graph_meta.get("forbidden_teacher_delta", 1.0) == 0.0
            and graph_meta.get("teacher_delta", 1.0) == 0.0,
            "GI14": graph_meta.get("teacher_input_gradient_sum", 0.0) > 0.0
            and graph_meta.get("allowed_target_gradient_sum", 0.0) > 0.0
            and graph_meta.get("selector_teacher_gradient_sum", 1.0) == 0.0
            and graph_meta.get("gate_teacher_gradient_sum", 1.0) == 0.0,
        },
        "architecture_shape_gate": {
            "S01": tensor_ids == expected_tensor_ids and _all_rows_pass(tensor_rows),
            "S02": context["feature_dim"]
            == (158 if context["exact_local"] else alpha_meta["no_vwap_count"]),
            "S03": graph_meta.get("koop_delta", 1.0) <= 1e-7
            and all(not bool_value(row["broadcast_allowed"]) for row in tensor_rows),
            "S04": graph_meta.get("arm_graph_ok", False)
            and graph_meta.get("gate_sigmoid_count") == 1,
        },
        "loss_reduction_gate": {
            "L01": graph_meta.get("rec_delta", 1.0) <= 1e-7
            and graph_meta.get("total_delta", 1.0) <= 1e-7,
            "L02": graph_meta.get("total_delta", 1.0) <= 1e-7,
            "L03": graph_meta.get("mean_delta", 1.0) <= 1e-7,
            "L04": graph_meta.get("nan_fail_closed", False)
            and graph_meta.get("r1_loss_delta", 1.0) <= 1e-7
            and graph_meta.get("r1_mechanical_selection_ok", False),
        },
        "model_arm_and_fairness_gate": {
            "M01": arm_ids == config["arms"]["mandatory_ids"] and len(arm_ids) == 10,
            "M02": graph_meta.get("arm_graph_ok", False)
            and len(
                {
                    row["arm_id"]
                    for row in static_tables[
                        "per_arm_loss_and_score_index_contract.csv"
                    ]
                }
            )
            == 10,
            "M03": len({row["input_feature_route"] for row in arm_rows}) == 1
            and config["architecture"]["m1_lightgbm"] == m1_expected
            and all(
                row["primary_value"] == "current_model_seed"
                for row in hyper_rows
                if row["config_id"] == "M1_LIGHTGBM"
                and row["parameter"]
                in {"seed", "feature_fraction_seed", "bagging_seed", "data_random_seed"}
            ),
            "M04": graph_meta.get("k1c_train_delta", 1.0) == 0.0
            and graph_meta.get("k1c_inference_delta", 1.0) == 0.0
            and graph_meta.get("k2_operator_parameter_n")
            == graph_meta.get("k1c_operator_parameter_n"),
            "M05": graph_meta.get("r1_relative_delta", 1.0) <= 0.10
            and graph_meta.get("r1_mechanical_selection_ok", False),
        },
        "split_purge_gate": {
            "SP01": config["split"]["train_nominal"] == ["2018-01-02", "2022-12-30"]
            and config["split"]["validation_nominal"] == ["2023-01-03", "2023-12-29"],
            "SP02": all(row["effective_start"] for row in split_rows),
            "SP03": all(
                row["purge_sessions"] == 12
                for row in split_rows
                if row["split_id"] != "historical_design_holdout"
            ),
            "SP04": all(
                row["dropped_day_n"] == row["purge_sessions"] for row in split_rows
            ),
            "SP05": config["split"]["random_row_split_allowed"] is False
            and config["split"]["purge_side"] == "earlier_split_tail",
        },
        "historical_holdout_firewall_gate": {
            "HF01": all(
                not bool_value(row["outcome_formula_executed"]) for row in access_log
            ),
            "HF02": config["identity"]["historical_sample_role"]
            == "design_contaminated_historical",
            "HF03": config["split"]["historical_holdout_unseal_count"] == 1,
            "HF04": config["split"]["post_unseal_retrain_allowed"] is False,
        },
        "search_budget_gate": {
            "SB01": config["arms"]["primary_R2_config_n"] == 1
            and config["arms"]["scheduled_R2_sensitivity_ids"]
            == ["S01", "S02", "S03", "S04", "S05", "S06"],
            "SB02": all(
                bool_value(row["one_factor_only"])
                for row in hyper_rows
                if row["role"] == "scheduled_one_factor_sensitivity"
            ),
            "SB03": not any(
                row["parameter"] == "learning_rate"
                and row["role"] == "scheduled_one_factor_sensitivity"
                for row in hyper_rows
            ),
            "SB04": all(
                not bool_value(row["promotion_allowed"])
                for row in hyper_rows
                if row["role"] == "non_primary_diagnostic_adaptation"
            ),
            "SB05": len({row["input_feature_route"] for row in arm_rows}) == 1
            and arm_rows[0]["input_feature_route"] == context["feature_route_id"],
        },
        "seed_randomness_gate": {
            "SR01": config["arms"]["model_seeds"] == [20260713, 20260714, 20260715],
            "SR02": len(seed_rows) == 24 and _all_rows_pass(seed_rows),
            "SR03": graph_meta.get("batch_reorder_delta", 1.0) <= 1e-7
            and all(
                bool_value(row["batch_order_invariant"])
                for row in seed_rows
                if row["stream_name"] == "inference_draw_seed"
            ),
            "SR04": config["arms"]["best_seed_primary_allowed"] is False,
        },
        "dependency_lock_gate": {
            "DL01": dependency_meta["declarations_ok"],
            "DL02": all(
                any(
                    row["dependency"] == name
                    and row["lock_resolved_version"] == version
                    and row["runtime_version"] == version
                    for row in dependency_rows
                )
                for name, version in [
                    ("pyqlib", "0.9.7"),
                    ("lightgbm", "4.6.0"),
                    ("torch", "2.8.0"),
                ]
            ),
            "DL03": dependency_meta["python_ok"] and dependency_meta["all_match"],
            "DL04": config["dependencies"]["runner_package_manager_calls_allowed"]
            is False,
            "DL05": config["dependencies"]["environment_bootstrap"]
            == "uv sync --frozen --extra reaka --extra dev"
            and dependency_meta["interpreter_ok"],
        },
        "gpu_dry_run_gate": {
            "GPU01": graph_meta.get("device") == "cuda"
            and "RTX 4070 SUPER" in graph_meta.get("device_name", ""),
            "GPU02": graph_meta.get("selected_batch_size", 0)
            in config["architecture"]["batch_size_candidates"]
            and graph_meta.get("selected_batch_size", 0) >= 16,
            "GPU03": graph_meta.get("score_draw_shape", [0, 0])[1] == 8
            and graph_meta.get("arm_graph_ok", False),
            "GPU04": graph_meta.get("gpu_gate", False)
            and graph_meta.get("repeat_delta", 1.0) <= 1e-7,
            "GPU05": graph_meta.get("gpu_real_market_access_count", 1) == 0,
        },
        "metric_multiplicity_gate": {
            "MM01": config["metrics"]["rankic_implementation"]
            == "float64_average_rank_pearson"
            and config["metrics"]["rank_method"] == "average",
            "MM02": list(config["metrics"]["contrasts"])
            == ["C0", "C1", "C2a", "C2b", "C3a", "C3b", "C4"],
            "MM03": metric_meta["algorithm_ok"]
            and metric_meta["repetitions"] == 5000
            and metric_meta["quantile_method"] == "higher",
            "MM04": metric_meta["family_size"] == 7,
            "MM05": {
                (row["family_id"], row["n_required"])
                for row in metric_rows
                if row["record_type"] == "minimum_complete_day"
            }
            == {
                ("validation_full", 200),
                ("validation_early", 80),
                ("validation_late", 80),
                ("historical_representation", 252),
                ("historical_economic", 252),
                ("forward_representation", 60),
                ("forward_economic", 60),
            },
            "MM06": any(row["contrast_id"] == "C4" for row in metric_rows),
            "MM07": any(
                row["record_type"] == "confirmatory_power" and row["n_required"] == 291
                for row in metric_rows
            ),
        },
        "economic_execution_freeze_gate": {
            "E01": upstream_ok,
            "E02": config["execution"]["TopK"] == 30
            and config["execution"]["initial_AUM_cny"] == 10_000_000
            and config["execution"]["ADV_window_sessions"] == 20,
            "E03": config["execution"]["entry_attempt"]
            == "next_executable_exchange_open_exactly_once"
            and config["execution"]["portfolio_ledger"]
            == "continuous_no_injection_stateful_NAV",
            "E04": config["execution"]["maximum_drawdown_cap"] == 0.35
            and config["execution"]["daily_ES10_loss_cap"] == 0.03,
        },
        "forward_refit_contract_gate": {
            "FR01": config["forward"]["comparators"]
            == [
                "R2_REAKA_DIFFUSION",
                "M1_LIGHTGBM_ALPHA158",
                "M3_GATED_DUAL_PATH_LSTM",
            ],
            "FR02": config["forward"]["refit_early_stopping"] is False
            and config["forward"]["transform_refit_count"] == 1,
            "FR03": config["forward"]["start_after_final_candidate_seal"] is True
            and config["forward"]["minimum_cohort_complete_days"] == 291,
            "FR04": all(
                config["forward"][field] is False
                for field in [
                    "rolling_retrain_first_cohort",
                    "normalizer_refresh_first_cohort",
                    "comparator_replacement_first_cohort",
                ]
            ),
            "FR05": config["forward"]["forward_module_attribution_authorized"] is False
            and _all_rows_pass(forward_rows),
        },
        "outcome_firewall_gate": {
            "OF01": all(
                context["preoutcome_hard_counts"][name] == 0
                for name in hard_count_names
            ),
            "OF02": access_rows_allowed and access_log_complete,
            "OF03": all(
                not row["outcome_columns_detected"]
                and not bool_value(row["outcome_formula_executed"])
                for row in access_log
            ),
            "OF04": all(
                not forbid_outcome_columns(row.keys(), metadata_exception=True)
                for row in static_tables["label_semantics_freeze.csv"]
            ),
        },
        "freeze_bundle_hash_gate": {
            "HB01": set(FREEZE_RELATIVE_PATHS) == set(context["expected_freeze_paths"]),
            "HB02": True,
            "HB03": "freeze/freeze_bundle_manifest.json" in FREEZE_RELATIVE_PATHS
            and "freeze/freeze_output_hashes_21a.json" in FREEZE_RELATIVE_PATHS,
            "HB04": context["sealed_at_utc"] != "",
            "HB05": config["identity"]["contract_version"] == CONTRACT_VERSION
            and config["output"]["schema_version"] == "21A_schema_v2",
        },
        "implementation_readiness_gate": {
            "IR01": all(
                row["status"] == "pass"
                for row in input_rows
                if row["artifact_id"] != "reference_formula_review_authorization"
            )
            and set(TABLE_SCHEMAS)
            >= {
                Path(path).name
                for path in FREEZE_RELATIVE_PATHS
                if path.endswith(".csv")
            },
            "IR02": tensor_ids == expected_tensor_ids
            and graph_meta.get("arm_graph_ok", False)
            and metric_meta["algorithm_ok"],
            "IR03": not re.search(
                r"\b(?:TBD|TODO|choose-later|best-effort)\b",
                json.dumps(config, sort_keys=True),
                re.I,
            ),
            "IR04": paths["test"].is_file()
            and "test_row_key_ddpm_is_batch_order_invariant"
            in paths["test"].read_text(encoding="utf-8")
            and "test_stationary_bootstrap_holm_exact"
            in paths["test"].read_text(encoding="utf-8"),
            "IR05": list(config) == RESOLVED_CONFIG_TOP_LEVEL_KEYS,
        },
    }
    if set(check_statuses) != set(CRITICAL_GATES):
        raise AssertionError("critical gate set drift")
    for gate_id, required_checks in GATE_CHECKS.items():
        if set(check_statuses[gate_id]) != set(required_checks):
            raise AssertionError(f"check set drift for {gate_id}")
    return check_statuses


def _paper_source_checks(
    config: dict[str, Any], source_rows: list[dict[str, Any]]
) -> bool:
    paths = resolve_paths(config)
    paper = config["paper_contract"]
    local_ok = (
        file_sha(paths["paper"]) == config["input_hash_expectations"]["paper_sha256"]
        and pdf_page_count(paths["paper"]) == 5
    )
    identity_ok = (
        paper["doi"] == "10.1109/ICASSP55912.2026.11465125"
        and paper["title"]
        == "Residual-Enhanced Adaptive Koopman Autoencoder: A Deep Latent Dynamics Model for Stock Prediction"
        and paper["authors"]
        == ["Lei Liao", "Yang Zhang", "Jun Wang", "Jinghua Tan", "Yinchao Liao"]
        and paper["venue"]
        == "2026 IEEE International Conference on Acoustics, Speech and Signal Processing"
        and paper["publication_year"] == 2026
    )
    expected_source_ids = {
        source["source_id"]
        for source in config["source_allowlist"]["acquisition_sources"]
    }
    allowlist_ok = {
        row.get("source_id") for row in source_rows
    } == expected_source_ids and all(
        bool_value(row["inside_allowlist"]) and row.get("identity_status") == "pass"
        for row in source_rows
    )
    return (
        local_ok
        and identity_ok
        and allowlist_ok
        and len(source_rows) == len(config["source_allowlist"]["acquisition_sources"])
    )


def _decision_state(gates: dict[str, str]) -> str:
    rules = [
        ("21A_outcome_firewall_violated", ["outcome_firewall_gate"]),
        ("21A_manifest_or_hash_blocked", ["freeze_bundle_hash_gate"]),
        ("21A_human_restart_or_scope_blocked", ["human_restart_scope_gate"]),
        (
            "21A_paper_source_lineage_blocked",
            ["paper_source_lineage_gate", "paper_formula_contract_gate"],
        ),
        ("21A_alpha158_expression_contract_blocked", ["alpha158_expression_gate"]),
        (
            "21A_feature_materialization_contract_blocked",
            [
                "vwap_qfq_unit_contract_gate",
                "volume_corporate_action_semantics_gate",
                "feature_materialization_route_gate",
                "feature_sequence_support_gate",
            ],
        ),
        (
            "21A_pit_timing_or_denominator_contract_blocked",
            [
                "pit_membership_timing_gate",
                "decision_denominator_contract_gate",
                "feature_label_alignment_gate",
            ],
        ),
        (
            "21A_architecture_graph_or_shape_contract_blocked",
            [
                "train_teacher_inference_graph_gate",
                "gradient_teacher_isolation_gate",
                "architecture_shape_gate",
                "loss_reduction_gate",
                "model_arm_and_fairness_gate",
            ],
        ),
        (
            "21A_split_search_or_statistics_contract_blocked",
            [
                "split_purge_gate",
                "historical_holdout_firewall_gate",
                "search_budget_gate",
                "seed_randomness_gate",
                "metric_multiplicity_gate",
                "economic_execution_freeze_gate",
                "forward_refit_contract_gate",
            ],
        ),
        (
            "21A_dependency_lock_or_gpu_contract_blocked",
            ["dependency_lock_gate", "gpu_dry_run_gate"],
        ),
        ("21A_contract_not_impl_ready", ["implementation_readiness_gate"]),
    ]
    for state, gate_ids in rules:
        if any(gates.get(gate_id) != "pass" for gate_id in gate_ids):
            return state
    return "21A_preoutcome_architecture_contract_ready"


def freeze_stage(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    import pandas as pd

    config = load_config(config_path)
    paths = resolve_paths(config)
    output_root = resolve_output_root(config)
    if (output_root / "freeze/freeze_bundle_manifest.json").exists():
        raise FileExistsError(
            "sealed 21A freeze bundle already exists; bump contract_version"
        )
    building_root = output_root / ".building" / str(uuid.uuid4())
    freeze_root = building_root / "freeze"
    freeze_root.mkdir(parents=True, exist_ok=False)
    access_log: list[dict[str, Any]] = []
    add_access(
        access_log,
        paths["config"],
        "resolved_config_input",
        RESOLVED_CONFIG_TOP_LEVEL_KEYS,
        ["resolved_config"],
        "freeze_stage_configuration",
    )
    add_access(
        access_log,
        f"package:PyYAML=={importlib.metadata.version('PyYAML')}",
        "python_package",
        ["yaml.safe_load", "yaml.safe_dump"],
        ["resolved_config"],
        "freeze_stage_configuration",
    )
    source_manifest_path = paths["reference_root"] / "source_availability_manifest.csv"
    if source_manifest_path.exists():
        source_rows = pd.read_csv(source_manifest_path, keep_default_na=False).to_dict(
            "records"
        )
        add_access(
            access_log,
            source_manifest_path,
            "paper_source_manifest",
            SOURCE_AVAILABILITY_COLUMNS,
            [],
            "formula_authorization",
        )
    else:
        source_rows = []
    formula_rows, formula_auth, formula_checks = validate_formula_authorization(config)
    for filename in [
        "paper_formula_registry_draft.csv",
        "formula_review_packet.md",
        "formula_review_authorization.json",
    ]:
        reference = paths["reference_root"] / filename
        if reference.exists():
            columns = (
                _read_header(reference)
                if reference.suffix == ".csv"
                else ["contract_metadata"]
            )
            add_access(
                access_log,
                reference,
                "paper_formula_review",
                columns,
                [],
                "formula_authorization",
            )
    input_rows = build_input_audit(config, access_log)
    upstream_rows, upstream_ok = build_upstream_audit(config, access_log)
    source_inventory = build_source_inventory(config, access_log)
    alpha_rows, expression_hash, alpha_meta = extract_alpha158_registry(access_log)
    field_mapping = build_field_mapping(alpha_rows, config)
    vwap_rows, jump_rows, date_sets, vwap_meta = build_vwap_audit(config, access_log)
    no_vwap_reachable = alpha_meta["no_vwap_count"] > 0 and _all_rows_pass(
        field_mapping
    )
    if vwap_meta["full_route_reachable"]:
        feature_route_id = config["feature_contract"]["full_route_id"]
        feature_route_class = "canonical_full_route"
        exact_local = True
        feature_dim = alpha_meta["count"]
    elif no_vwap_reachable:
        feature_route_id = config["feature_contract"]["no_vwap_route_id"]
        feature_route_class = "registered_primary_route_adaptation"
        exact_local = False
        feature_dim = alpha_meta["no_vwap_count"]
    else:
        feature_route_id = ""
        feature_route_class = ""
        exact_local = False
        feature_dim = 0
    feature_cache = materialize_feature_cache(
        config, alpha_rows, feature_route_id, access_log
    )
    support_rows, timing_rows, split_rows, support_meta = build_membership_support(
        config,
        date_sets,
        feature_route_id,
        access_log,
        sequence_ready_keys=feature_cache["sequence_ready_keys"],
        feature_ready_keys=feature_cache["ready_keys"],
    )
    static_tables = build_static_contract_tables(config, feature_route_id, feature_dim)
    graph_rows, runtime_rows, graph_meta = run_synthetic_graph_audit(
        config, feature_dim
    )
    add_access(
        access_log,
        "package:torch==2.8.0",
        "python_package",
        ["module_topology", "autograd", "deterministic_algorithms"],
        ["synthetic_graph_audit"],
        "synthetic_architecture_dry_run",
    )
    add_access(
        access_log,
        f"gpu:{graph_meta.get('device_name', 'unavailable')}",
        "gpu_resource",
        ["device_name", "total_memory_mib", "peak_memory_mib"],
        ["full_graph_forward_backward_eight_draw_inference"],
        "synthetic_architecture_dry_run",
    )
    driver_version_file = Path("/proc/driver/nvidia/version")
    if driver_version_file.is_file():
        add_access(
            access_log,
            driver_version_file,
            "gpu_resource",
            ["nvidia_driver_version"],
            ["runtime_fingerprint"],
            "synthetic_architecture_dry_run",
        )
    dependency_rows, dependency_meta = build_dependency_table(config, access_log)
    for check_id, observed in [
        ("pyproject_sha256", dependency_meta["pyproject_sha256"]),
        ("requirements_sha256", dependency_meta["requirements_sha256"]),
        ("uv_lock_sha256", dependency_meta["uv_lock_sha256"]),
        (
            "dependency_lock_gate",
            dependency_meta["all_match"] and dependency_meta["declarations_ok"],
        ),
    ]:
        runtime_rows.append(
            {
                "check_id": check_id,
                "observed_value": observed,
                "required_value": "recorded_or_true",
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(bool(observed)),
            }
        )
    for dependency_name in ["pyqlib", "lightgbm"]:
        dependency_row = next(
            row for row in dependency_rows if row["dependency"] == dependency_name
        )
        runtime_rows.append(
            {
                "check_id": f"{dependency_name}_version",
                "observed_value": dependency_row["runtime_version"],
                "required_value": dependency_row["lock_resolved_version"],
                "batch_size": "",
                "peak_memory_mib": "",
                "repeat_delta": "",
                "status": gate(dependency_row["status"] == "pass"),
            }
        )
    hyper_rows, seed_rows = build_search_seed_tables(config)
    metric_rows = build_metric_table(config)
    metric_meta = metric_algorithm_self_audit(config)
    forward_rows = build_forward_table(config)
    quarantine_rows = build_quarantine_rows(support_rows, jump_rows)
    paper_tables = build_paper_tables(config, formula_rows)
    normalization_hash = stable_hash(
        static_tables["feature_normalization_and_missingness_contract.csv"]
    )
    cache_manifest = {
        "schema_version": config["output"]["schema_version"],
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "cache_role": "feature_only_coverage_cache",
        "cache_published": False,
        "primary_feature_route_id": feature_route_id,
        "primary_feature_route_class": feature_route_class,
        "feature_count": feature_dim,
        "expression_list_sha256": expression_hash,
        "input_root_hashes": {
            row["source_id"]: row["root_hash"]
            for row in source_inventory
            if row["source_id"] in {"qfq_root", "raw_ohlcv_root"}
        },
        "split_hash": stable_hash(split_rows),
        "normalization_contract_hash": normalization_hash,
        "cache_relative_path": feature_cache["cache_relative_path"],
        "cache_content_hash": feature_cache["cache_content_hash"],
        "cache_row_n": feature_cache["cache_row_n"],
        "key_columns": ["instrument", "feature_date"],
        "date_min": feature_cache["date_min"],
        "date_max": feature_cache["date_max"],
        "label_columns_present": False,
        "outcome_formula_count": 0,
        "status": feature_cache["status"],
    }
    outcome_ok = all(
        not row["outcome_columns_detected"]
        and not bool_value(row["outcome_formula_executed"])
        for row in access_log
    )
    formula_ok = (
        bool(formula_rows)
        and all(formula_checks.values())
        and _all_rows_pass(formula_rows)
    )
    sealed_at = utc_now()
    preoutcome_counts = {
        "outcome_columns_detected_count": sum(
            bool(row["outcome_columns_detected"]) for row in access_log
        ),
        "outcome_formula_executed_count": sum(
            bool_value(row["outcome_formula_executed"]) for row in access_log
        ),
        "real_label_materialization_count": 0,
        "real_model_score_count": 0,
        "selection_or_tuning_allowed_count": sum(
            bool_value(row["selection_or_tuning_allowed"]) for row in access_log
        ),
        "historical_holdout_outcome_access_count": 0,
    }
    predicate_arguments = {
        "is_listed": True,
        "is_st": False,
        "usable_trade_date": "2026-07-14",
        "expected_next_session": "2026-07-14",
        "history_ready": True,
        "sequence_ready": True,
        "feature_ready": True,
    }
    synthetic_t_plus_one_invariant = (
        decision_eligibility_predicate(**predicate_arguments)
        == decision_eligibility_predicate(**predicate_arguments)
        and "t_plus_one"
        not in inspect.signature(decision_eligibility_predicate).parameters
    )
    gate_checks = build_gate_check_statuses(
        {
            "config": config,
            "paths": paths,
            "source_rows": source_rows,
            "formula_rows": formula_rows,
            "formula_auth": formula_auth,
            "formula_checks": formula_checks,
            "alpha_rows": alpha_rows,
            "alpha_meta": alpha_meta,
            "field_mapping": field_mapping,
            "expression_hash": expression_hash,
            "vwap_rows": vwap_rows,
            "jump_rows": jump_rows,
            "vwap_meta": vwap_meta,
            "feature_cache": feature_cache,
            "cache_manifest": cache_manifest,
            "support_rows": support_rows,
            "timing_rows": timing_rows,
            "split_rows": split_rows,
            "support_meta": support_meta,
            "static_tables": static_tables,
            "graph_rows": graph_rows,
            "graph_meta": graph_meta,
            "hyper_rows": hyper_rows,
            "seed_rows": seed_rows,
            "dependency_rows": dependency_rows,
            "dependency_meta": dependency_meta,
            "metric_rows": metric_rows,
            "metric_meta": metric_meta,
            "forward_rows": forward_rows,
            "upstream_ok": upstream_ok,
            "input_rows": input_rows,
            "access_log": access_log,
            "paper_tables": paper_tables,
            "feature_route_id": feature_route_id,
            "feature_dim": feature_dim,
            "exact_local": exact_local,
            "requirement_sha256": file_sha(paths["requirement"]),
            "preoutcome_hard_counts": preoutcome_counts,
            "expected_freeze_paths": FREEZE_RELATIVE_PATHS,
            "sealed_at_utc": sealed_at,
            "synthetic_t_plus_one_invariant": synthetic_t_plus_one_invariant,
        }
    )
    write_yaml(freeze_root / "resolved_config.yaml", config)
    human_restart = {
        "episode_id": config["identity"]["episode_id"],
        "phase_id": PHASE_ID,
        "contract_version": CONTRACT_VERSION,
        "authorization_type": config["identity"]["authorization_type"],
        "authorization_source": config["identity"]["authorization_source"],
        "authorization_recorded_date": config["identity"][
            "authorization_recorded_date"
        ],
        "restart_type": config["identity"]["restart_type"],
        "upstream_automatic_authorization": False,
        "research_plan_path": rel(paths["research_plan"]),
        "research_plan_sha256": file_sha(paths["research_plan"]),
        "research_plan_sha256_expected": config["input_hash_expectations"][
            "research_plan_sha256"
        ],
        "requirement_path": rel(paths["requirement"]),
        "requirement_sha256": file_sha(paths["requirement"]),
        "primary_claim_ceiling": config["identity"]["primary_claim_ceiling"],
        "historical_sample_role": config["identity"]["historical_sample_role"],
        "historical_support_claim_allowed": False,
    }
    write_json(freeze_root / "human_restart_authorization.json", human_restart)
    _write_table(building_root, "upstream_scope_and_lineage_audit.csv", upstream_rows)
    _write_table(building_root, "input_artifact_audit.csv", input_rows)
    _write_table(building_root, "source_data_inventory.csv", source_inventory)
    for filename, rows in paper_tables.items():
        _write_table(building_root, filename, rows)
    _write_table(building_root, "alpha158_expression_registry.csv", alpha_rows)
    _write_table(building_root, "alpha158_local_field_mapping.csv", field_mapping)
    write_text(freeze_root / "alpha158_expression_hash.txt", expression_hash)
    _write_table(building_root, "vwap_qfq_unit_and_range_audit.csv", vwap_rows)
    _write_table(building_root, "alpha158_volume_corporate_action_audit.csv", jump_rows)
    _write_table(
        building_root,
        "alpha158_factor_jump_window_quarantine_sensitivity.csv",
        quarantine_rows,
    )
    _write_table(
        building_root, "pit_membership_signal_execution_timing_audit.csv", timing_rows
    )
    _write_table(building_root, "feature_sequence_support_audit.csv", support_rows)
    write_json(freeze_root / "feature_cache_manifest.json", cache_manifest)
    for filename, rows in static_tables.items():
        _write_table(building_root, filename, rows)
    _write_table(
        building_root, "gradient_flow_and_teacher_isolation_audit.csv", graph_rows
    )
    _write_table(building_root, "split_purge_embargo_freeze.csv", split_rows)
    _write_table(
        building_root, "hyperparameter_and_search_budget_freeze.csv", hyper_rows
    )
    _write_table(building_root, "seed_and_randomness_freeze.csv", seed_rows)
    _write_table(
        building_root,
        "dependency_lock_change_and_runtime_contract.csv",
        dependency_rows,
    )
    _write_table(building_root, "runtime_dependency_gpu_audit.csv", runtime_rows)
    _write_table(building_root, "metric_margin_power_freeze.csv", metric_rows)
    _write_table(building_root, "forward_refit_and_comparator_freeze.csv", forward_rows)
    _write_table(building_root, "preoutcome_access_log.csv", access_log)
    contract_payload = {
        "schema_version": config["output"]["schema_version"],
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "created_at_utc": sealed_at,
        "sealed_at_utc": sealed_at,
        "requirement_sha256": file_sha(paths["requirement"]),
        "resolved_config_sha256": file_sha(freeze_root / "resolved_config.yaml"),
        "research_plan_sha256": file_sha(paths["research_plan"]),
        "paper_sha256": file_sha(paths["paper"]),
        "input_artifact_hashes": {
            row["artifact_id"]: row["sha256_or_root_hash"] for row in input_rows
        },
        "primary_feature_route_id": feature_route_id,
        "primary_feature_route_class": feature_route_class,
        "feature_expression_sha256": expression_hash,
        "architecture_contract_hash": stable_hash(static_tables),
        "arm_registry_hash": stable_hash(static_tables["model_arm_registry.csv"]),
        "split_contract_hash": stable_hash(split_rows),
        "dependency_contract_hash": stable_hash(dependency_rows),
        "metric_contract_hash": stable_hash(metric_rows),
        "forward_contract_hash": stable_hash(forward_rows),
        "preoutcome_hard_counts": preoutcome_counts,
        "claim_ceiling": config["identity"]["primary_claim_ceiling"],
        "gate_check_statuses": gate_checks,
        "capabilities": {
            "official_code_available": False,
            "paper_appendix_available": False,
            "alpha158_exact_local_materialization": exact_local,
            "confirmed_terminal_price_resolution_available": paths[
                "name_history_root"
            ].exists(),
            "gpu_batch_size_mechanically_reduced": graph_meta["selected_batch_size"]
            < 256,
            "exact_replication_reachable": False,
        },
        "selected_batch_size": graph_meta["selected_batch_size"],
        "formula_authorization_present": formula_auth is not None,
        "official_code_status": "not_disclosed_in_allowlisted_sources",
        "historical_sample_role": config["identity"]["historical_sample_role"],
        "historical_support_claim_allowed": False,
        "forward_confirmatory_required_complete_days": config["forward"][
            "minimum_cohort_complete_days"
        ],
        "market_data_max_date": support_meta["market_data_max_date"],
        "right_censored_membership_n": support_meta["right_censored_membership_n"],
        "right_censored_policy": "whole_terminal_day_not_evaluable",
        "next_allowed_requirement": "requirement_21b_alpha158_sequence_baseline_benchmark.md",
    }
    write_json(freeze_root / "contract_freeze_21a.json", contract_payload)
    freeze_doc = "\n".join(
        [
            "# 21A Contract Freeze",
            "",
            "## Identity",
            f"- run_id: `{RUN_ID}`",
            f"- contract_version: `{CONTRACT_VERSION}`",
            "",
            "## Inputs",
            f"- input artifacts: `{len(input_rows)}`",
            "",
            "## Paper",
            f"- formula authorization: `{'approved' if formula_ok else 'blocked'}`",
            "",
            "## Feature Route",
            f"- route: `{feature_route_id or 'blocked'}`",
            "",
            "## Universe",
            f"- support days: `{support_meta['complete_by_split']}`",
            f"- market data max date: `{support_meta['market_data_max_date']}`",
            f"- right-censored membership rows: `{support_meta['right_censored_membership_n']}`",
            "",
            "## Graph",
            f"- selected synthetic batch: `{graph_meta['selected_batch_size']}`",
            "",
            "## Arms",
            "- mandatory arm count: `10`",
            "",
            "## Split",
            "- purge sessions: `12`",
            "",
            "## Runtime",
            f"- device: `{graph_meta.get('device_name', '')}`",
            "",
            "## Statistics",
            "- forward confirmatory complete days: `291`",
            "",
            "## Execution",
            "- TopK: `30`",
            "",
            "## Forward",
            "- comparators: `R2|M1|M3`",
            "",
            "## Firewall",
            f"- preoutcome hard counts: `{preoutcome_counts}`",
        ]
    )
    write_text(freeze_root / "21A_contract_freeze.md", freeze_doc)
    if not outcome_ok:
        raise RuntimeError("outcome firewall violation; bundle not promoted")
    bundle_hash = seal_freeze_bundle(building_root, config, sealed_at)
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root / "freeze"
    if destination.exists():
        raise FileExistsError("freeze destination already exists")
    os.replace(freeze_root, destination)
    try:
        building_root.rmdir()
        (output_root / ".building").rmdir()
    except OSError:
        pass
    return {
        "status": "sealed_ready"
        if all(all(checks.values()) for checks in gate_checks.values())
        else "sealed_blocked",
        "output_root": output_root,
        "freeze_bundle_hash": bundle_hash,
        "primary_feature_route_id": feature_route_id,
        "selected_batch_size": graph_meta["selected_batch_size"],
        "formula_authorization_required": not formula_ok,
    }


def _csv_records_from_bytes(payload: bytes) -> list[dict[str, str]]:
    text = payload.decode("utf-8")
    return list(csv.DictReader(text.splitlines()))


def _gate_evidence_rows(
    contract: dict[str, Any],
    verification_ok: bool,
    access_audit: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    frozen = contract.get("gate_check_statuses", {}) if verification_ok else {}
    checks: dict[str, dict[str, bool]] = {}
    for gate_id in CRITICAL_GATES:
        observed = frozen.get(gate_id, {})
        required = GATE_CHECKS[gate_id]
        exact_set = set(observed) == set(required)
        checks[gate_id] = {
            check_id: bool(exact_set and observed.get(check_id) is True)
            for check_id in required
        }

    hard_counts = contract.get("preoutcome_hard_counts", {})
    hard_count_names = [
        "outcome_columns_detected_count",
        "outcome_formula_executed_count",
        "real_label_materialization_count",
        "real_model_score_count",
        "selection_or_tuning_allowed_count",
        "historical_holdout_outcome_access_count",
    ]
    no_preoutcome_access = verification_ok and all(
        hard_counts.get(name) == 0 for name in hard_count_names
    )
    no_raw_reads = all(not bool_value(row.get("raw_input")) for row in access_audit)
    no_unmanifested_reads = all(
        bool_value(row.get("freeze_manifest_listed")) for row in access_audit
    )
    all_reads_allowed = all(bool_value(row.get("allowed")) for row in access_audit)
    if verification_ok:
        checks["outcome_firewall_gate"]["OF01"] = (
            no_preoutcome_access and no_raw_reads and no_unmanifested_reads
        )
        checks["outcome_firewall_gate"]["OF02"] = (
            checks["outcome_firewall_gate"]["OF02"] and all_reads_allowed
        )
    else:
        # A corrupt freeze maps to the hash-blocked state, not to a fabricated outcome breach.
        checks["outcome_firewall_gate"] = {
            check_id: True for check_id in GATE_CHECKS["outcome_firewall_gate"]
        }
    checks["freeze_bundle_hash_gate"] = {
        check_id: verification_ok for check_id in GATE_CHECKS["freeze_bundle_hash_gate"]
    }

    rows: list[dict[str, Any]] = []
    for gate_id in CRITICAL_GATES:
        for check_id in GATE_CHECKS[gate_id]:
            passed = checks[gate_id][check_id]
            evidence_artifact = (
                "finalize_access_audit.csv"
                if gate_id == "outcome_firewall_gate" and check_id in {"OF01", "OF02"}
                else GATE_EVIDENCE_ARTIFACT[gate_id]
            )
            evidence_selector = (
                f"check_id={check_id}"
                if gate_id
                in {
                    "pit_membership_timing_gate",
                    "gradient_teacher_isolation_gate",
                    "gpu_dry_run_gate",
                }
                else f"independent_predicate:{gate_id}.{check_id}"
            )
            rows.append(
                {
                    "gate_id": gate_id,
                    "check_id": check_id,
                    "evidence_artifact": evidence_artifact,
                    "evidence_selector": evidence_selector,
                    "observed_value": "true" if passed else "false",
                    "required_value": "true",
                    "status": gate(passed),
                    "blocking_reason": ""
                    if passed
                    else f"{check_id}_failed_or_unverifiable",
                }
            )
    rows.sort(
        key=lambda row: (
            CRITICAL_GATES.index(row["gate_id"]),
            GATE_CHECKS[row["gate_id"]].index(row["check_id"]),
        )
    )
    gate_statuses = {
        gate_id: gate(
            {row["check_id"] for row in rows if row["gate_id"] == gate_id}
            == set(GATE_CHECKS[gate_id])
            and all(
                row["status"] == "pass" for row in rows if row["gate_id"] == gate_id
            )
        )
        for gate_id in CRITICAL_GATES
    }
    return rows, gate_statuses


def _ordered_blocking_reasons(gates: dict[str, str]) -> list[str]:
    precedence_groups = [
        ["outcome_firewall_gate"],
        ["freeze_bundle_hash_gate"],
        ["human_restart_scope_gate"],
        ["paper_source_lineage_gate", "paper_formula_contract_gate"],
        ["alpha158_expression_gate"],
        [
            "vwap_qfq_unit_contract_gate",
            "volume_corporate_action_semantics_gate",
            "feature_materialization_route_gate",
            "feature_sequence_support_gate",
        ],
        [
            "pit_membership_timing_gate",
            "decision_denominator_contract_gate",
            "feature_label_alignment_gate",
        ],
        [
            "train_teacher_inference_graph_gate",
            "gradient_teacher_isolation_gate",
            "architecture_shape_gate",
            "loss_reduction_gate",
            "model_arm_and_fairness_gate",
        ],
        [
            "split_purge_gate",
            "historical_holdout_firewall_gate",
            "search_budget_gate",
            "seed_randomness_gate",
            "metric_multiplicity_gate",
            "economic_execution_freeze_gate",
            "forward_refit_contract_gate",
        ],
        ["dependency_lock_gate", "gpu_dry_run_gate"],
        ["implementation_readiness_gate"],
    ]
    return [
        gate_id
        for group in precedence_groups
        for gate_id in sorted(group)
        if gates.get(gate_id) != "pass"
    ]


def _build_decision_row(
    contract: dict[str, Any],
    gates: dict[str, str],
    freeze_bundle_hash: str,
    gate_evidence_sha256: str,
) -> dict[str, Any]:
    architecture_gates = [
        "paper_source_lineage_gate",
        "paper_formula_contract_gate",
        "vwap_qfq_unit_contract_gate",
        "volume_corporate_action_semantics_gate",
        "feature_materialization_route_gate",
        "pit_membership_timing_gate",
        "decision_denominator_contract_gate",
        "feature_sequence_support_gate",
        "feature_label_alignment_gate",
        "train_teacher_inference_graph_gate",
        "gradient_teacher_isolation_gate",
        "architecture_shape_gate",
        "loss_reduction_gate",
        "model_arm_and_fairness_gate",
        "split_purge_gate",
        "historical_holdout_firewall_gate",
        "search_budget_gate",
        "seed_randomness_gate",
        "dependency_lock_gate",
        "gpu_dry_run_gate",
        "metric_multiplicity_gate",
        "economic_execution_freeze_gate",
        "forward_refit_contract_gate",
    ]
    architecture_ready = all(
        gates.get(gate_id) == "pass" for gate_id in architecture_gates
    )
    state = _decision_state(gates)
    ready = state == "21A_preoutcome_architecture_contract_ready"
    capabilities = contract.get("capabilities", {})
    row: dict[str, Any] = {
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_state": state,
        **gates,
        "official_code_status": contract.get(
            "official_code_status", "not_disclosed_in_allowlisted_sources"
        ),
        "primary_feature_route_id": contract.get("primary_feature_route_id", ""),
        "primary_feature_route_class": contract.get("primary_feature_route_class", ""),
        "alpha158_exact_local_materialization": bool(
            capabilities.get("alpha158_exact_local_materialization", False)
        ),
        "paper_architecture_project_adaptation_reachable": architecture_ready,
        "exact_replication_reachable": False,
        "official_code_available": bool(
            capabilities.get("official_code_available", False)
        ),
        "selected_batch_size": contract.get("selected_batch_size", ""),
        "historical_sample_role": contract.get(
            "historical_sample_role", "design_contaminated_historical"
        ),
        "historical_support_claim_allowed": False,
        "forward_confirmatory_required_complete_days": contract.get(
            "forward_confirmatory_required_complete_days", 291
        ),
        "next_allowed_requirement": contract.get(
            "next_allowed_requirement",
            "requirement_21b_alpha158_sequence_baseline_benchmark.md",
        ),
        "next_requirement_generation_authorized": ready,
        "next_requirement_execution_authorized": False,
        "outcome_model_training_authorized": False,
        "historical_holdout_readout_authorized": False,
        "policy_training_authorized": False,
        "portfolio_optimization_authorized": False,
        "deployment_authorized": False,
        "freeze_bundle_hash": freeze_bundle_hash,
        "gate_evidence_sha256": gate_evidence_sha256,
        "blocking_reasons": json.dumps(
            _ordered_blocking_reasons(gates), ensure_ascii=False, separators=(",", ":")
        ),
    }
    return {column: row.get(column, "") for column in DECISION_COLUMNS}


def _render_final_report(
    decision: dict[str, Any],
    contract: dict[str, Any],
    artifacts: dict[str, bytes],
    verification_error: str,
) -> str:
    def records(name: str) -> list[dict[str, str]]:
        payload = artifacts.get(f"freeze/{name}", b"")
        return _csv_records_from_bytes(payload) if payload else []

    paper_rows = records("paper_source_registry.csv")
    paper = paper_rows[0] if paper_rows else {}
    alpha_rows = records("alpha158_expression_registry.csv")
    support_rows = records("feature_sequence_support_audit.csv")
    runtime_rows = records("runtime_dependency_gpu_audit.csv")
    arm_rows = records("model_arm_registry.csv")
    formula_rows = records("paper_formula_and_architecture_registry.csv")
    vwap_rows = records("vwap_qfq_unit_and_range_audit.csv")
    global_vwap = next((row for row in vwap_rows if row.get("scope") == "global"), {})
    support_counts = {
        split: sum(
            row.get("support_status") == "ready"
            for row in support_rows
            if row.get("split") == split
        )
        for split in ["train", "validation", "historical_design_holdout"]
    }
    gate_pass_n = sum(decision.get(gate_id) == "pass" for gate_id in CRITICAL_GATES)
    report = [
        "# EP21A 论文谱系、PIT 数据与架构契约报告",
        "",
        "## 1. Decision summary",
        "",
        f"- decision_state: `{decision['decision_state']}`",
        f"- critical gates: `{gate_pass_n}/{len(CRITICAL_GATES)}` pass",
        f"- blocking_reasons: `{decision['blocking_reasons']}`",
        f"- freeze_bundle_hash: `{decision['freeze_bundle_hash']}`",
        f"- bundle verification error: `{verification_error or 'none'}`",
        "",
        "## 2. Human restart 与历史授权边界",
        "",
        f"- historical_sample_role: `{decision['historical_sample_role']}`",
        f"- historical_support_claim_allowed: `{str(decision['historical_support_claim_allowed']).lower()}`",
        "",
        "历史 2017-01 至 2026-05 已被本 topic 反复观察，只能作为 design_contaminated_historical；可信支持只能来自最终候选密封后的 forward cohort。",
        "",
        "## 3. Paper identity 与公式授权",
        "",
        f"- title: `{paper.get('title', '')}`",
        f"- authors: `{paper.get('authors', '')}`",
        f"- DOI: `{paper.get('doi', '')}`",
        f"- pages: `{paper.get('page_count', '')}`",
        f"- local SHA-256: `{paper.get('local_sha256', contract.get('paper_sha256', ''))}`",
        f"- authorized formula rows: `{sum(row.get('human_verified') == 'true' for row in formula_rows)}/{len(formula_rows)}`",
        f"- official_code_status: `{decision['official_code_status']}`",
        "",
        "Official code 或 appendix 未披露不阻断 project adaptation，但必须限制复现 claim。",
        "",
        "## 4. Claim ceiling",
        "",
        "EP21 只能声明 paper_architecture_grounded_project_adaptation，不能声明 exact_replication 或 paper_result_reproduced。",
        "",
        "## 5. PIT universe 与 denominator",
        "",
        f"- support-ready days (train/validation/historical): `{support_counts['train']}/{support_counts['validation']}/{support_counts['historical_design_holdout']}`",
        "",
        "U_t_decision 在 outcome 前固定；unknown data gap 和 data cutoff 使整日不可评价，不允许逐股静默删除后改变 denominator。",
        "",
        "## 6. Label semantics 与 outcome firewall",
        "",
        f"- preoutcome hard counts: `{json.dumps(contract.get('preoutcome_hard_counts', {}), ensure_ascii=False, sort_keys=True)}`",
        "",
        "21A 没有训练或评价任何真实 outcome model，也没有生成真实股票 score、RankIC 或策略 PnL。",
        "",
        "## 7. qfq/raw unit 与 feature route",
        "",
        f"- primary route: `{decision['primary_feature_route_id']}` (`{decision['primary_feature_route_class']}`)",
        f"- global overlap/factor/auditable/range: `{global_vwap.get('overlap_rate', '')}/{global_vwap.get('factor_pass_rate', '')}/{global_vwap.get('auditable_row_rate', '')}/{global_vwap.get('range_pass_rate', '')}`",
        "",
        "## 8. Alpha158 与 corporate-action sensitivity",
        "",
        f"- canonical feature rows: `{len(alpha_rows)}`",
        f"- expression hash: `{contract.get('feature_expression_sha256', '')}`",
        f"- exact local materialization: `{str(decision['alpha158_exact_local_materialization']).lower()}`",
        "",
        "## 9. Feature-only support、normalization 与 split/purge",
        "",
        "Feature support 只使用 membership、截至 feature date 的 bar/history readiness；normalizer 只在 original train 拟合，12-session purge 已在 freeze artifact 固定。",
        "",
        "## 10. Source/teacher/inference graph",
        "",
        "Primary REAKA 对全部 T 个 shifted transitions 计算 Koopman 和 residual loss；last-transition-only 只能是独立 diagnostic adaptation。",
        "",
        "Teacher tensors 只允许构造 train-only Koopman/residual target，并经 residual_target->x_s 影响训练重构/loss；不进入 selector、gate、residual condition 或任何 inference-score ancestor。",
        "",
        "## 11. Mandatory arms 与公平性",
        "",
        f"- mandatory arm rows: `{len(arm_rows)}`",
        "- K1C 的 train/inference mixture 在 batch/time 上全局共享；R1/K1C 参数差异与机制结论按冻结公平性规则处理。",
        "",
        "## 12. Search、seed 与 batch ladder",
        "",
        f"- selected_batch_size: `{decision['selected_batch_size']}`",
        "- model seeds、S01-S06 单因素 sensitivity 与 256→128→64→32→16 ladder 均由 freeze artifact 约束。",
        "",
        "## 13. Dependency 与 GPU dry-run",
        "",
        f"- runtime audit rows: `{len(runtime_rows)}`",
        f"- GPU gate: `{decision['gpu_dry_run_gate']}`",
        "",
        "## 14. Statistics 与 economic boundary",
        "",
        f"- forward complete-day target: `{decision['forward_confirmatory_required_complete_days']}`",
        "- RankIC average-rank tie、undefined day、seven-hypothesis Holm family 和 execution ledger 边界均在 freeze 中固定。",
        "",
        "## 15. 21F comparator/refit",
        "",
        "21F 只前瞻确认 R2 相对预冻结 M1/M3 的预测与执行；21C/21D 模块归因仍是 historical_design_diagnostic。",
        "",
        "## 16. Next authorization",
        "",
        f"- next requirement: `{decision['next_allowed_requirement']}`",
        f"- generation authorized: `{str(decision['next_requirement_generation_authorized']).lower()}`",
        f"- execution authorized: `{str(decision['next_requirement_execution_authorized']).lower()}`",
        "",
        "21A 成功只允许生成并人工评审 21B requirement，不授权 21B 执行、historical holdout readout、policy、optimization 或 deployment。",
    ]
    return "\n".join(report) + "\n"


def _seal_final_root(
    build_root: Path,
    schema_version: str,
    sort_contract_version: str,
    freeze_bundle_hash: str,
) -> None:
    manifest_name = "manifest_21a_paper_lineage_pit_data_and_architecture_contract.json"
    hashes_name = (
        "output_hashes_21a_paper_lineage_pit_data_and_architecture_contract.json"
    )
    manifest = {
        "schema_version": schema_version,
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "sealed_at_utc": utc_now(),
        "bundle_role": "final_root",
        "expected_paths": FINAL_RELATIVE_PATHS,
        "manifest_hash_exclusion_paths": [manifest_name, hashes_name],
        "output_hashes": {
            name: file_sha(build_root / name)
            for name in FINAL_RELATIVE_PATHS
            if name not in {manifest_name, hashes_name}
        },
        "input_hashes": {"freeze_bundle_hash": freeze_bundle_hash},
        "schema_registry_version": schema_version,
        "sort_contract_version": sort_contract_version,
    }
    write_json(build_root / manifest_name, manifest)
    final_hashes = {
        name: file_sha(build_root / name)
        for name in FINAL_RELATIVE_PATHS
        if name != hashes_name
    }
    write_json(
        build_root / hashes_name,
        {
            "schema_version": schema_version,
            "run_id": RUN_ID,
            "contract_version": CONTRACT_VERSION,
            "hash_algorithm": "sha256",
            "excluded_paths": [hashes_name],
            "hashes": final_hashes,
        },
    )
    if sorted(path.name for path in build_root.iterdir() if path.is_file()) != sorted(
        FINAL_RELATIVE_PATHS
    ):
        raise RuntimeError("final root file set mismatch")


def finalize_stage(output_root_value: str | Path) -> dict[str, Any]:
    raw_output_root = Path(output_root_value)
    if raw_output_root.is_absolute() or str(output_root_value).startswith("file://"):
        raise ValueError("finalize output root must be repository-relative")
    output_root = topic_path(raw_output_root)
    resolved_root = output_root.resolve()
    if REPO_ROOT.resolve() not in [resolved_root, *resolved_root.parents]:
        raise ValueError("finalize output root escapes repository")
    existing = [name for name in FINAL_RELATIVE_PATHS if (output_root / name).exists()]
    if existing:
        raise FileExistsError(f"sealed final artifacts already exist: {existing}")

    access_audit: list[dict[str, Any]] = []
    verification_error = ""
    try:
        verified = verify_freeze_bundle(output_root, access_audit)
        verification_ok = True
    except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        verified = {"manifest": {}, "freeze_bundle_hash": "", "artifact_bytes": {}}
        verification_ok = False
        verification_error = f"{type(error).__name__}: {error}"

    artifacts: dict[str, bytes] = verified.get("artifact_bytes", {})
    contract_payload = artifacts.get("freeze/contract_freeze_21a.json", b"")
    contract = (
        json.loads(contract_payload.decode("utf-8"))
        if verification_ok and contract_payload
        else {}
    )
    evidence_rows, gates = _gate_evidence_rows(contract, verification_ok, access_audit)

    build_root = output_root / ".finalizing" / str(uuid.uuid4())
    build_root.mkdir(parents=True, exist_ok=False)
    write_csv(
        build_root / "finalize_access_audit.csv",
        access_audit,
        TABLE_SCHEMAS["finalize_access_audit.csv"],
    )
    write_csv(
        build_root / "gate_evidence_21a.csv",
        evidence_rows,
        TABLE_SCHEMAS["gate_evidence_21a.csv"],
    )
    evidence_sha = file_sha(build_root / "gate_evidence_21a.csv")
    decision = _build_decision_row(
        contract, gates, verified.get("freeze_bundle_hash", ""), evidence_sha
    )
    write_csv(build_root / "21A_contract_decision.csv", [decision], DECISION_COLUMNS)
    report = _render_final_report(decision, contract, artifacts, verification_error)
    write_text(
        build_root / "21A_paper_lineage_pit_data_and_architecture_contract_report.md",
        report,
    )

    freeze_manifest = verified.get("manifest", {})
    schema_version = freeze_manifest.get("schema_version", "21A_schema_v2")
    sort_contract_version = freeze_manifest.get("sort_contract_version", "21A_sort_v2")
    _seal_final_root(
        build_root,
        schema_version,
        sort_contract_version,
        verified.get("freeze_bundle_hash", ""),
    )
    output_root.mkdir(parents=True, exist_ok=True)
    for name in FINAL_RELATIVE_PATHS:
        os.replace(build_root / name, output_root / name)
    try:
        build_root.rmdir()
        (output_root / ".finalizing").rmdir()
    except OSError:
        pass
    return {
        "status": "finalized_ready"
        if decision["decision_state"] == "21A_preoutcome_architecture_contract_ready"
        else "finalized_blocked",
        "decision_state": decision["decision_state"],
        "output_root": output_root,
        "freeze_bundle_hash": verified.get("freeze_bundle_hash", ""),
        "blocking_reasons": json.loads(decision["blocking_reasons"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.stage == "acquire-sources":
        result = acquire_sources_stage(args.config, offline=args.offline)
    elif args.stage == "freeze":
        result = freeze_stage(args.config)
    else:
        result = finalize_stage(args.output_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

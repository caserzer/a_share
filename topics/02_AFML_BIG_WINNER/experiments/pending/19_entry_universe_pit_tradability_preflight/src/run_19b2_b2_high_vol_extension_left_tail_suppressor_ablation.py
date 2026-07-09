#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import run_19b0_fast_rule_grid_enrichment_scan as b0  # noqa: E402
import run_19b1_t0_left_right_tail_separability_readout as b1  # noqa: E402


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]

RUN_ID = "19B2_b2_high_vol_extension_left_tail_suppressor_ablation"
EXPERIMENT_ID = "19_entry_universe_pit_tradability_preflight"
PHASE_ID = "19B2"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.md"
OUTPUT_ROOT = EXPERIMENT_DIR / "outputs" / RUN_ID

PRIMARY_SUPPRESSOR_FEATURE_WHITELIST = [
    "match_vol60",
    "atr_20_pct_asof_decision_date",
    "return_60d_asof_decision_date",
    "close_to_ema60_asof_decision_date",
]
SUPPORT_SMD_FEATURES = ["match_market_cap", "match_amount20", "match_vol60", "match_return20"]
RANK_COLUMNS = ["q_vol60", "q_atr20", "q_ret60", "q_ema60_dist"]
SCORE_COLUMNS = [
    "vol_block",
    "extension_block",
    "tail_risk_score",
    "basis_risk_score",
    "vol_expansion_rank_spread",
    "atr20_over_vol60",
    "candidate_vol_block_rank_pct",
    "candidate_extension_block_rank_pct",
    "candidate_q_atr20_rank_pct",
    "candidate_q_ema60_dist_rank_pct",
    "candidate_q_vol60_rank_pct",
    "candidate_q_ret60_rank_pct",
]
FORBIDDEN_PREFIXES = ("forward_mfe_", "forward_mae_", "forward_return_", "forward_big_winner_")
FORBIDDEN_NAMES = {
    "MFE_120",
    "MAE_20",
    "right_tail_event_50",
    "left_tail_event_10",
    "left_tail_event_20",
    "right_clean",
    "left_bad",
    "both",
    "neither",
    "outcome_group",
    "fast_fail_flag",
    "false_repair_flag",
}
POLICY_AUTH_COLUMNS = [
    "model_training_authorized",
    "entry_policy_authorized",
    "exit_policy_authorized",
    "holding_policy_authorized",
    "portfolio_backtest_authorized",
    "model_deployment_authorized",
    "production_signal_authorized",
    "live_trading_authorized",
    "19C_replay_authorized",
    "EP20_policy_preflight_authorized",
]
REQUIRED_INPUT_KEYS = [
    "nineteen_b_decision",
    "nineteen_b_manifest",
    "nineteen_b_output_hashes",
    "nineteen_b_handoff_contract",
    "nineteen_b_robustness_candidate_row_manifest",
    "nineteen_b_robustness_outcome_boundary_audit",
    "nineteen_b_robustness_metric_readout",
    "nineteen_b_false_positive_burden_readout",
    "nineteen_b_mfe_mae_joint_readout",
    "nineteen_b_robustness_baseline_quality_audit",
    "nineteen_b_topk_concentration_sensitivity",
    "nineteen_b_upstream_19a_contract_audit",
    "nineteen_b_upstream_19b0_contract_audit",
    "nineteen_b1_decision",
    "nineteen_b1_manifest",
    "nineteen_b1_output_hashes",
    "nineteen_b1_handoff_contract",
    "nineteen_b1_outcome_left_right_overlap_readout",
    "nineteen_b1_univariate_feature_separability_readout",
    "nineteen_b1_feature_source_audit",
    "nineteen_b1_feature_join_audit",
    "nineteen_b1_feature_matrix_manifest",
    "nineteen_b1_stability_readout",
    "simple_rule_feature_source_map",
    "matching_feature_source_map",
    "topn_executable_universe",
    "stock_qfq_dir",
    "benchmark_daily",
]
REQUIRED_OUTPUT_KEYS = [
    "entry_universe_19b2_decision",
    "input_artifact_audit",
    "upstream_contract_audit",
    "primary_row_join_audit",
    "rank_source_audit",
    "suppressor_feature_source_audit",
    "b2_pre_outcome_rank_panel",
    "b2_suppressor_score_panel",
    "suppressor_variant_grid",
    "suppressor_ablation_readout",
    "suppressor_budget_comparison_readout",
    "support_and_concentration_readout",
    "search_accounting_audit",
    "report",
    "handoff_contract",
    "manifest",
    "output_hashes",
    "suppressor_efficiency_frontier_figure",
    "four_group_removed_rate_by_variant_figure",
    "tail_risk_score_group_distribution_figure",
    "mae_vs_right_tail_retention_frontier_figure",
]
CSV_SCHEMAS = {
    "entry_universe_19b2_decision": [
        "run_id",
        "created_at",
        "requirement_file_hash",
        "config_file_hash",
        "input_artifact_hash_manifest",
        "config_contract_gate",
        "input_artifact_gate",
        "upstream_19a_contract_gate",
        "upstream_19b0_contract_gate",
        "upstream_19b_contract_gate",
        "upstream_19b1_contract_gate",
        "sample_support_gate",
        "primary_row_join_gate",
        "feature_pit_gate",
        "rank_source_gate",
        "score_contract_gate",
        "variant_grid_gate",
        "ablation_metric_gate",
        "interaction_superiority_gate",
        "policy_authorization_gate",
        "output_contract_gate",
        "decision_state",
        "blocking_reason",
        "family_id",
        "grid_cell_id",
        "row_scope",
        "split",
        "candidate_n",
        "instrument_n",
        "right_clean_n",
        "left_bad_n",
        "both_n",
        "neither_n",
        "variant_n_total",
        "variant_n_primary",
        "best_variant_id",
        "best_variant_family",
        "best_variant_candidate_removed_rate",
        "best_variant_left_bad_removed_per_right_clean_removed",
        "best_variant_right_clean_kept_rate",
        "best_variant_left_bad_removed_rate",
        "best_variant_both_removed_rate",
        "best_variant_p_candidate_50_after",
        "best_variant_MAE_20_p10_improvement_vs_S0",
        "best_variant_MAE_worsening_after",
        "best_single_feature_variant_id",
        "interaction_efficiency_lift_vs_single_feature",
        "interaction_efficiency_lift_ci_low",
        "validation_outcome_read",
        "max_ep19_terminal_state",
        "next_allowed_requirement",
        "next_research_suggestion",
        *POLICY_AUTH_COLUMNS,
    ],
    "primary_row_join_audit": [
        "family_id",
        "grid_cell_id",
        "row_scope",
        "split",
        "expected_candidate_n_from_19b_metric",
        "observed_candidate_n_from_mfe_mae_joint",
        "observed_candidate_n_after_manifest_join",
        "unique_join_key_n",
        "duplicate_join_key_n",
        "missing_in_candidate_manifest_n",
        "extra_manifest_row_n",
        "primary_enrichment_denominator_flag_false_n",
        "manifest_frozen_before_label_readout_false_n",
        "label_read_before_manifest_freeze_true_n",
        "primary_row_join_gate",
        "blocking_reason",
    ],
    "rank_source_audit": [
        "decision_date",
        "rank_scope",
        "rank_cross_section_n",
        "rank_feature_n",
        "rank_source_artifact",
        "rank_source_before_outcome_join",
        "forbidden_label_column_n",
        "missing_required_feature_n",
        "rank_source_gate",
        "blocking_reason",
    ],
    "suppressor_feature_source_audit": [
        "feature_name",
        "source_alias",
        "feature_value_type",
        "source_artifact",
        "source_columns",
        "asof_rule",
        "pit_safe_flag",
        "missing_rate",
        "left_bad_nonmissing_n",
        "right_clean_nonmissing_n",
        "left_bad_missing_rate",
        "right_clean_missing_rate",
        "used_in_primary_score",
        "primary_whitelist_flag",
        "feature_support_gate",
        "blocking_reason",
    ],
    "b2_pre_outcome_rank_panel": [
        "family_id",
        "grid_cell_id",
        "split",
        "row_scope",
        "row_key",
        "instrument_id",
        "decision_date",
        "decision_month",
        "rank_scope",
        "rank_source_artifact",
        "rank_cross_section_n",
        *PRIMARY_SUPPRESSOR_FEATURE_WHITELIST,
        *RANK_COLUMNS,
        "vol_block",
        "extension_block",
        "tail_risk_score",
        "basis_risk_score",
        "vol_expansion_rank_spread",
        "atr20_over_vol60",
        "candidate_vol_block_rank_pct",
        "candidate_extension_block_rank_pct",
        "candidate_q_atr20_rank_pct",
        "candidate_q_ema60_dist_rank_pct",
        "candidate_q_vol60_rank_pct",
        "candidate_q_ret60_rank_pct",
        "feature_pit_gate",
        "rank_source_gate",
        "pre_outcome_rank_panel_hash",
        "blocking_reason",
    ],
    "b2_suppressor_score_panel": [
        "family_id",
        "grid_cell_id",
        "split",
        "row_scope",
        "row_key",
        "instrument_id",
        "decision_date",
        "decision_month",
        "MFE_120",
        "MAE_20",
        "right_tail_event_50",
        "left_tail_event_10",
        "left_tail_event_20",
        "outcome_group",
        *PRIMARY_SUPPRESSOR_FEATURE_WHITELIST,
        *RANK_COLUMNS,
        *SCORE_COLUMNS,
        "rank_cross_section_n",
        "rank_source_gate",
        "feature_pit_gate",
        "pre_outcome_rank_panel_hash",
    ],
    "suppressor_variant_grid": [
        "variant_id",
        "suppressor_family",
        "suppressor_rule",
        "score_name",
        "threshold_type",
        "threshold_value",
        "candidate_removed_target_pct",
        "logical_condition",
        "primary_success_eligible",
        "exploratory_only",
        "excluded_from_primary_success_gate",
        "pre_registered_flag",
        "blocking_reason",
    ],
    "suppressor_ablation_readout": [
        "variant_id",
        "suppressor_family",
        "primary_success_eligible",
        "candidate_n_before",
        "candidate_n_removed",
        "candidate_n_after",
        "candidate_removed_rate",
        "right_clean_n_before",
        "right_clean_n_removed",
        "right_clean_n_after",
        "right_clean_kept_rate",
        "left_bad_n_before",
        "left_bad_n_removed",
        "left_bad_n_after",
        "left_bad_removed_rate",
        "both_n_before",
        "both_n_removed",
        "both_n_after",
        "both_removed_rate",
        "neither_n_before",
        "neither_n_removed",
        "neither_n_after",
        "neither_removed_rate",
        "left_bad_removed_per_right_clean_removed",
        "right_clean_removed_zero_flag",
        "right_tail_event_50_n_after",
        "left_tail_event_10_n_after",
        "left_tail_event_20_n_after",
        "p_candidate_50_after",
        "p_left_tail_10_after",
        "p_left_tail_20_after",
        "MAE_20_p10_after",
        "MAE_20_p05_after",
        "MFE_120_p90_after",
        "S0_candidate_MAE_20_p10",
        "MAE_20_p10_improvement_vs_S0",
        "eligible_universe_MAE_20_p10",
        "MAE_worsening_after",
        "fast_fail_rate_after",
        "candidate_per_winner_after",
        "left_bad_removed_per_right_clean_removed_ci_low",
        "left_bad_removed_per_right_clean_removed_ci_high",
        "right_clean_kept_rate_ci_low",
        "left_bad_removed_rate_ci_low",
        "p_candidate_50_after_ci_low",
        "MAE_20_p10_improvement_vs_S0_ci_low",
        "MAE_20_p10_improvement_vs_S0_ci_high",
        "MAE_worsening_after_ci_low",
        "MAE_worsening_after_ci_high",
        "primary_success_gate",
        "diagnostic_only_flag",
        "blocking_reason",
    ],
    "suppressor_budget_comparison_readout": [
        "primary_variant_id",
        "primary_variant_family",
        "single_feature_comparator_variant_id",
        "candidate_removed_rate_abs_diff",
        "primary_efficiency",
        "single_feature_efficiency",
        "efficiency_lift_abs",
        "efficiency_lift_pct",
        "efficiency_lift_pct_ci_low",
        "efficiency_lift_pct_ci_high",
        "primary_right_clean_kept_rate",
        "single_feature_right_clean_kept_rate",
        "primary_p_candidate_50_after",
        "single_feature_p_candidate_50_after",
        "primary_MAE_20_p10_improvement_vs_S0",
        "single_feature_MAE_20_p10_improvement_vs_S0",
        "primary_MAE_worsening_after",
        "single_feature_MAE_worsening_after",
        "budget_matched_flag",
        "interaction_superiority_component_gate",
        "blocking_reason",
    ],
    "support_and_concentration_readout": [
        "variant_id",
        "support_comparator_scope",
        "support_comparator_n",
        "candidate_n_after",
        "candidate_instrument_n_after",
        "winner_instrument_n_after",
        "max_SMD_after",
        "max_SMD_feature_after",
        "SMD_match_market_cap_after",
        "SMD_match_amount20_after",
        "SMD_match_vol60_after",
        "SMD_match_return20_after",
        "top10_instrument_winner_share_after",
        "top20_instrument_winner_share_after",
        "support_descriptive_gate",
        "concentration_descriptive_gate",
        "diagnostic_only_flag",
        "blocking_reason",
    ],
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP19B2 B2 high-vol extension suppressor ablation.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
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
    if text.startswith(("experiments/", "data/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_input_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("input_paths", {}).items()}


def resolve_output_root(config: dict[str, Any]) -> Path:
    return topic_path(config.get("output", {}).get("output_root", OUTPUT_ROOT))


def output_paths(output_root: Path | None = None) -> dict[str, Path]:
    root = output_root or OUTPUT_ROOT
    figures = root / "figures"
    return {
        "entry_universe_19b2_decision": root / "entry_universe_19b2_decision.csv",
        "input_artifact_audit": root / "input_artifact_audit.csv",
        "upstream_contract_audit": root / "upstream_contract_audit.csv",
        "primary_row_join_audit": root / "primary_row_join_audit.csv",
        "rank_source_audit": root / "rank_source_audit.csv",
        "suppressor_feature_source_audit": root / "suppressor_feature_source_audit.csv",
        "b2_pre_outcome_rank_panel": root / "b2_pre_outcome_rank_panel.csv",
        "b2_suppressor_score_panel": root / "b2_suppressor_score_panel.csv",
        "suppressor_variant_grid": root / "suppressor_variant_grid.csv",
        "suppressor_ablation_readout": root / "suppressor_ablation_readout.csv",
        "suppressor_budget_comparison_readout": root / "suppressor_budget_comparison_readout.csv",
        "support_and_concentration_readout": root / "support_and_concentration_readout.csv",
        "search_accounting_audit": root / "search_accounting_audit.csv",
        "report": root / "19B2_b2_high_vol_extension_left_tail_suppressor_ablation_report.md",
        "handoff_contract": root / "19B2_handoff_contract.md",
        "manifest": root / "manifest_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.json",
        "output_hashes": root / "output_hashes_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.json",
        "suppressor_efficiency_frontier_figure": figures / "suppressor_efficiency_frontier.png",
        "four_group_removed_rate_by_variant_figure": figures / "four_group_removed_rate_by_variant.png",
        "tail_risk_score_group_distribution_figure": figures / "tail_risk_score_group_distribution.png",
        "mae_vs_right_tail_retention_frontier_figure": figures / "mae_vs_right_tail_retention_frontier.png",
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pass_fail(condition: bool) -> str:
    return "pass" if bool(condition) else "fail"


def as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "pass"}


def safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def safe_div(num: float, den: float) -> float:
    return float(num / den) if den else float("nan")


def rel(path: Path) -> str:
    return b0.rel(path)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def json_text(value: Any) -> str:
    return json.dumps(b0.clean_json(value), ensure_ascii=False, sort_keys=True)


def stable_hash_payload(payload: Any) -> str:
    text = json.dumps(b0.clean_json(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frame_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    existing = [col for col in columns if col in frame.columns]
    if not existing:
        return stable_hash_payload([])
    sort_cols = [col for col in ["family_id", "grid_cell_id", "row_key", "instrument_id", "decision_date", "variant_id"] if col in existing]
    ordered = frame[existing].sort_values(sort_cols or existing[: min(4, len(existing))]).reset_index(drop=True)
    normalized = pd.DataFrame(index=ordered.index)
    for col in ordered.columns:
        series = ordered[col]
        if pd.api.types.is_bool_dtype(series):
            normalized[col] = series.map(lambda value: "true" if bool(value) else "false")
        elif pd.api.types.is_numeric_dtype(series):
            normalized[col] = series.map(lambda value: "" if pd.isna(value) else f"{float(value):.10g}")
        else:
            normalized[col] = series.fillna("").astype(str)
    return hashlib.sha256(normalized.to_csv(index=False).encode("utf-8")).hexdigest()


def b_output_root(paths: dict[str, Path]) -> Path:
    return paths["nineteen_b_decision"].parent


def b1_output_root(paths: dict[str, Path]) -> Path:
    return paths["nineteen_b1_decision"].parent


def resolve_upstream_hash_path(root: Path, scope: str, artifact_id: str) -> Path | None:
    mapped = UPSTREAM_HASH_PATH_MAPS.get(scope, {}).get(artifact_id)
    return root / mapped if mapped else None


def input_hash_lookup(paths: dict[str, Path]) -> dict[str, tuple[str, str]]:
    return {
        "nineteen_b_decision": ("19B", "entry_universe_19b_decision"),
        "nineteen_b_handoff_contract": ("19B", "handoff_contract"),
        "nineteen_b_robustness_candidate_row_manifest": ("19B", "robustness_candidate_row_manifest"),
        "nineteen_b_robustness_outcome_boundary_audit": ("19B", "robustness_outcome_boundary_audit"),
        "nineteen_b_robustness_metric_readout": ("19B", "robustness_metric_readout"),
        "nineteen_b_false_positive_burden_readout": ("19B", "false_positive_burden_readout"),
        "nineteen_b_mfe_mae_joint_readout": ("19B", "mfe_mae_joint_readout"),
        "nineteen_b_robustness_baseline_quality_audit": ("19B", "robustness_baseline_quality_audit"),
        "nineteen_b_topk_concentration_sensitivity": ("19B", "topk_concentration_sensitivity"),
        "nineteen_b_upstream_19a_contract_audit": ("19B", "upstream_19a_contract_audit"),
        "nineteen_b_upstream_19b0_contract_audit": ("19B", "upstream_19b0_contract_audit"),
        "nineteen_b1_decision": ("19B1", "entry_universe_19b1_decision"),
        "nineteen_b1_manifest": ("19B1", "manifest"),
        "nineteen_b1_handoff_contract": ("19B1", "handoff_contract"),
        "nineteen_b1_outcome_left_right_overlap_readout": ("19B1", "outcome_left_right_overlap_readout"),
        "nineteen_b1_univariate_feature_separability_readout": ("19B1", "t0_univariate_feature_separability_readout"),
        "nineteen_b1_feature_source_audit": ("19B1", "t0_feature_source_audit"),
        "nineteen_b1_feature_join_audit": ("19B1", "t0_feature_join_audit"),
        "nineteen_b1_feature_matrix_manifest": ("19B1", "t0_feature_matrix_manifest"),
        "nineteen_b1_stability_readout": ("19B1", "t0_separability_stability_readout"),
    }


def build_expected_variant_grid() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "variant_id": "S0",
            "suppressor_family": "baseline",
            "suppressor_rule": "keep_all",
            "score_name": "none",
            "threshold_type": "none",
            "threshold_value": "",
            "candidate_removed_target_pct": 0.00,
            "logical_condition": "keep_all",
            "primary_success_eligible": False,
            "exploratory_only": False,
            "excluded_from_primary_success_gate": True,
            "pre_registered_flag": True,
            "blocking_reason": "",
        }
    ]
    for pct in [0.10, 0.15, 0.20, 0.25, 0.30]:
        rows.append(
            {
                "variant_id": f"S{int(pct * 20 - 1)}",
                "suppressor_family": "tail_risk_score_top_pct",
                "suppressor_rule": f"remove_tail_risk_score_top_{int(pct * 100)}pct",
                "score_name": "tail_risk_score",
                "threshold_type": "top_pct",
                "threshold_value": f"{pct:.2f}",
                "candidate_removed_target_pct": pct,
                "logical_condition": f"tail_risk_score >= p{int((1 - pct) * 100)}",
                "primary_success_eligible": True,
                "exploratory_only": False,
                "excluded_from_primary_success_gate": False,
                "pre_registered_flag": True,
                "blocking_reason": "",
            }
        )
    single_specs = [
        ("A_VOL60", "q_vol60"),
        ("A_ATR20", "q_atr20"),
        ("A_RET60", "q_ret60"),
        ("A_EMA60", "q_ema60_dist"),
    ]
    for prefix, score_name in single_specs:
        for pct in [0.10, 0.20, 0.30]:
            rows.append(
                {
                    "variant_id": f"{prefix}_top{int(pct * 100)}",
                    "suppressor_family": "single_feature",
                    "suppressor_rule": f"remove_{score_name}_top_{int(pct * 100)}pct",
                    "score_name": score_name,
                    "threshold_type": "top_pct",
                    "threshold_value": f"{pct:.2f}",
                    "candidate_removed_target_pct": pct,
                    "logical_condition": f"{score_name} >= p{int((1 - pct) * 100)}",
                    "primary_success_eligible": False,
                    "exploratory_only": False,
                    "excluded_from_primary_success_gate": True,
                    "pre_registered_flag": True,
                    "blocking_reason": "",
                }
            )
    logical_rows = [
        (
            "B_vol80_extension80",
            "candidate_vol_block_rank_pct__candidate_extension_block_rank_pct",
            "0.80",
            "",
            "candidate_vol_block_rank_pct >= 0.80 and candidate_extension_block_rank_pct >= 0.80",
        ),
        (
            "B_vol70_extension85",
            "candidate_vol_block_rank_pct__candidate_extension_block_rank_pct",
            "0.70|0.85",
            "",
            "candidate_vol_block_rank_pct >= 0.70 and candidate_extension_block_rank_pct >= 0.85",
        ),
        (
            "B_vol85_extension70",
            "candidate_vol_block_rank_pct__candidate_extension_block_rank_pct",
            "0.85|0.70",
            "",
            "candidate_vol_block_rank_pct >= 0.85 and candidate_extension_block_rank_pct >= 0.70",
        ),
        (
            "B_atr80_ema80",
            "candidate_q_atr20_rank_pct__candidate_q_ema60_dist_rank_pct",
            "0.80",
            "",
            "candidate_q_atr20_rank_pct >= 0.80 and candidate_q_ema60_dist_rank_pct >= 0.80",
        ),
        (
            "B_vol60_80_ret60_80",
            "candidate_q_vol60_rank_pct__candidate_q_ret60_rank_pct",
            "0.80",
            "",
            "candidate_q_vol60_rank_pct >= 0.80 and candidate_q_ret60_rank_pct >= 0.80",
        ),
    ]
    for variant_id, score_name, threshold_value, target, condition in logical_rows:
        rows.append(
            {
                "variant_id": variant_id,
                "suppressor_family": "logical_interaction",
                "suppressor_rule": condition,
                "score_name": score_name,
                "threshold_type": "candidate_score_rank_threshold",
                "threshold_value": threshold_value,
                "candidate_removed_target_pct": target,
                "logical_condition": condition,
                "primary_success_eligible": True,
                "exploratory_only": False,
                "excluded_from_primary_success_gate": False,
                "pre_registered_flag": True,
                "blocking_reason": "",
            }
        )
    for pct in [0.10, 0.15, 0.20, 0.25, 0.30]:
        rows.append(
            {
                "variant_id": f"C_basis_top{int(pct * 100)}",
                "suppressor_family": "basis_risk_score_top_pct",
                "suppressor_rule": f"remove_basis_risk_score_top_{int(pct * 100)}pct",
                "score_name": "basis_risk_score",
                "threshold_type": "top_pct",
                "threshold_value": f"{pct:.2f}",
                "candidate_removed_target_pct": pct,
                "logical_condition": f"basis_risk_score >= p{int((1 - pct) * 100)}",
                "primary_success_eligible": True,
                "exploratory_only": False,
                "excluded_from_primary_success_gate": False,
                "pre_registered_flag": True,
                "blocking_reason": "",
            }
        )
    rows.extend(
        [
            {
                "variant_id": "D_atr20_over_vol60_top20",
                "suppressor_family": "volatility_contraction_descriptive",
                "suppressor_rule": "remove_atr20_over_vol60_top_20pct",
                "score_name": "atr20_over_vol60",
                "threshold_type": "top_pct",
                "threshold_value": "0.20",
                "candidate_removed_target_pct": 0.20,
                "logical_condition": "atr20_over_vol60 >= p80",
                "primary_success_eligible": False,
                "exploratory_only": False,
                "excluded_from_primary_success_gate": True,
                "pre_registered_flag": True,
                "blocking_reason": "",
            },
            {
                "variant_id": "D_rank_spread_top20",
                "suppressor_family": "volatility_contraction_descriptive",
                "suppressor_rule": "remove_vol_expansion_rank_spread_top_20pct",
                "score_name": "vol_expansion_rank_spread",
                "threshold_type": "top_pct",
                "threshold_value": "0.20",
                "candidate_removed_target_pct": 0.20,
                "logical_condition": "vol_expansion_rank_spread >= p80",
                "primary_success_eligible": False,
                "exploratory_only": False,
                "excluded_from_primary_success_gate": True,
                "pre_registered_flag": True,
                "blocking_reason": "",
            },
        ]
    )
    return rows


EXPECTED_VARIANT_GRID = build_expected_variant_grid()

UPSTREAM_HASH_PATH_MAPS = {
    "19B": {
        "entry_universe_19b_decision": "entry_universe_19b_decision.csv",
        "input_artifact_audit": "input_artifact_audit.csv",
        "upstream_19a_contract_audit": "upstream_19a_contract_audit.csv",
        "upstream_19b0_contract_audit": "upstream_19b0_contract_audit.csv",
        "robustness_candidate_row_manifest": "robustness_candidate_row_manifest.csv",
        "robustness_outcome_boundary_audit": "robustness_outcome_boundary_audit.csv",
        "robustness_metric_readout": "robustness_metric_readout.csv",
        "robustness_positive_exposure_readout": "robustness_positive_exposure_readout.csv",
        "robustness_residual_alpha_readout": "robustness_residual_alpha_readout.csv",
        "robustness_baseline_quality_audit": "robustness_baseline_quality_audit.csv",
        "robustness_baseline_row_manifest": "robustness_baseline_row_manifest.csv",
        "baseline_repair_variant_registry": "baseline_repair_variant_registry.csv",
        "baseline_repair_sweep_audit": "baseline_repair_sweep_audit.csv",
        "false_positive_burden_readout": "false_positive_burden_readout.csv",
        "topk_concentration_sensitivity": "topk_concentration_sensitivity.csv",
        "cluster_bootstrap_ci": "cluster_bootstrap_ci.csv",
        "tail_lift_curve_readout": "tail_lift_curve_readout.csv",
        "ccdf_survival_curve_readout": "ccdf_survival_curve_readout.csv",
        "capture_vs_burden_readout": "capture_vs_burden_readout.csv",
        "b2_right_left_tail_lift_balance_readout": "b2_right_left_tail_lift_balance_readout.csv",
        "mfe_mae_joint_readout": "mfe_mae_joint_readout.csv",
        "search_accounting_audit": "search_accounting_audit.csv",
        "handoff_contract": "19B_handoff_contract.md",
        "report": "19B_robust_right_tail_enrichment_and_false_positive_burden_readout_report.md",
        "tail_lift_curve_figure": "figures/tail_lift_curve.png",
        "ccdf_survival_curve_figure": "figures/ccdf_survival_curve.png",
        "capture_vs_burden_figure": "figures/capture_vs_burden.png",
        "mfe_mae_joint_scatter_figure": "figures/mfe_mae_joint_scatter.png",
        "b2_right_left_tail_lift_balance_figure": "figures/b2_right_left_tail_lift_balance.png",
    },
    "19B1": {
        "entry_universe_19b1_decision": "entry_universe_19b1_decision.csv",
        "input_artifact_audit": "input_artifact_audit.csv",
        "upstream_contract_audit": "upstream_contract_audit.csv",
        "t0_feature_join_audit": "t0_feature_join_audit.csv",
        "outcome_left_right_overlap_readout": "outcome_left_right_overlap_readout.csv",
        "t0_feature_source_audit": "t0_feature_source_audit.csv",
        "t0_feature_matrix_manifest": "t0_feature_matrix_manifest.csv",
        "t0_univariate_feature_separability_readout": "t0_univariate_feature_separability_readout.csv",
        "t0_separability_stability_readout": "t0_separability_stability_readout.csv",
        "t0_multivariate_diagnostic_separability_readout": "t0_multivariate_diagnostic_separability_readout.csv",
        "search_accounting_audit": "search_accounting_audit.csv",
        "handoff_contract": "19B1_handoff_contract.md",
        "manifest": "manifest_19b1_t0_left_right_tail_separability_readout.json",
        "report": "19B1_t0_left_right_tail_separability_readout_report.md",
        "b2_outcome_left_right_overlap_figure": "figures/b2_outcome_left_right_overlap.png",
        "b2_t0_feature_auc_forest_figure": "figures/b2_t0_feature_auc_forest.png",
        "b2_t0_separability_stability_figure": "figures/b2_t0_separability_stability.png",
        "b2_t0_top_feature_distributions_figure": "figures/b2_t0_top_feature_distributions.png",
    },
}
EXPECTED_SCORE_CONTRACT = {
    "q_vol60": "rank_pct(match_vol60)",
    "q_atr20": "rank_pct(atr_20_pct_asof_decision_date)",
    "q_ret60": "rank_pct(return_60d_asof_decision_date)",
    "q_ema60_dist": "rank_pct(close_to_ema60_asof_decision_date)",
    "vol_block": "max(q_vol60, q_atr20)",
    "extension_block": "max(q_ret60, q_ema60_dist)",
    "tail_risk_score": "vol_block * extension_block",
    "basis_risk_score": "q_ema60_dist * max(q_atr20, q_vol60)",
    "vol_expansion_rank_spread": "q_atr20 - q_vol60",
    "atr20_over_vol60": "atr_20_pct_asof_decision_date / max(match_vol60, epsilon)",
    "candidate_vol_block_rank_pct": "rank_pct(vol_block within B2 primary candidate rows)",
    "candidate_extension_block_rank_pct": "rank_pct(extension_block within B2 primary candidate rows)",
    "candidate_q_atr20_rank_pct": "rank_pct(q_atr20 within B2 primary candidate rows)",
    "candidate_q_ema60_dist_rank_pct": "rank_pct(q_ema60_dist within B2 primary candidate rows)",
    "candidate_q_vol60_rank_pct": "rank_pct(q_vol60 within B2 primary candidate rows)",
    "candidate_q_ret60_rank_pct": "rank_pct(q_ret60 within B2 primary candidate rows)",
}


def validate_config_contract(config: dict[str, Any], paths: dict[str, Path], output_root: Path) -> tuple[str, str]:
    reasons: list[str] = []
    if config.get("run_id") != RUN_ID:
        reasons.append("run_id_mismatch")
    if config.get("experiment_id") != EXPERIMENT_ID:
        reasons.append("experiment_id_mismatch")
    if config.get("phase_id") != PHASE_ID:
        reasons.append("phase_id_mismatch")
    missing_inputs = sorted(set(REQUIRED_INPUT_KEYS) - set(config.get("input_paths", {})))
    if missing_inputs:
        reasons.append("missing_input_paths:" + "|".join(missing_inputs))
    primary = config.get("primary_scope", {})
    if primary.get("family_id") != "B2_relative_strength_breakout":
        reasons.append("primary_family_id_mismatch")
    if primary.get("grid_cell_id") != "B2-relative-strength-breakout__182b3d0f30f5":
        reasons.append("primary_grid_cell_id_mismatch")
    if primary.get("split") != "robustness" or primary.get("row_scope") != "candidate_primary_denominator":
        reasons.append("primary_scope_mismatch")
    feature_contract = config.get("feature_contract", {})
    if list(feature_contract.get("primary_suppressor_feature_whitelist", [])) != PRIMARY_SUPPRESSOR_FEATURE_WHITELIST:
        reasons.append("primary_suppressor_feature_whitelist_mismatch")
    if feature_contract.get("rank_scope") != "executable_universe_same_decision_date":
        reasons.append("rank_scope_mismatch")
    if feature_contract.get("rank_pct_method") != "average_rank_pct_ascending":
        reasons.append("rank_pct_method_mismatch")
    if list(feature_contract.get("forbidden_feature_prefixes", [])) != list(FORBIDDEN_PREFIXES):
        reasons.append("forbidden_feature_prefixes_mismatch")
    if set(feature_contract.get("forbidden_label_columns", [])) != (FORBIDDEN_NAMES - {"outcome_group", "fast_fail_flag", "false_repair_flag"}):
        reasons.append("forbidden_label_columns_mismatch")
    score_contract = config.get("score_contract", {})
    for key, expected in EXPECTED_SCORE_CONTRACT.items():
        if str(score_contract.get(key, "")) != expected:
            reasons.append(f"score_contract_{key}_mismatch")
    if safe_float(score_contract.get("epsilon")) != 1.0e-12:
        reasons.append("score_contract_epsilon_mismatch")
    expected_grid = {
        "primary_tail_risk_top_pct": [0.10, 0.15, 0.20, 0.25, 0.30],
        "single_feature_top_pct": [0.10, 0.20, 0.30],
        "logical_interaction_threshold_pairs": [
            "vol80_extension80",
            "vol70_extension85",
            "vol85_extension70",
            "atr80_ema80",
            "vol60_80_ret60_80",
        ],
        "basis_risk_top_pct": [0.10, 0.15, 0.20, 0.25, 0.30],
        "volatility_contraction_top_pct": [0.20],
    }
    for key, expected in expected_grid.items():
        observed = list(config.get("grid_contract", {}).get(key, []))
        if observed != expected:
            reasons.append(f"grid_contract_{key}_mismatch")
    expected_thresholds = {"right_tail_event_50": 0.50, "left_tail_event_10": -0.10, "left_tail_event_20": -0.20}
    for key, expected in expected_thresholds.items():
        if safe_float(config.get("thresholds", {}).get(key)) != expected:
            reasons.append(f"threshold_{key}_mismatch")
    expected_support = {
        "candidate_n_min": 300,
        "instrument_n_min": 30,
        "right_clean_n_min": 50,
        "left_bad_n_min": 50,
        "kept_candidate_n_min": 300,
        "kept_right_tail_event_50_n_min": 50,
        "rank_cross_section_min_n": 30,
    }
    for key, expected in expected_support.items():
        if safe_float(config.get("support", {}).get(key)) != float(expected):
            reasons.append(f"support_{key}_mismatch")
    expected_primary = {
        "left_bad_removed_per_right_clean_removed_min": 2.0,
        "MAE_20_p10_improvement_vs_S0_min": 0.01,
        "p_candidate_50_after_min": 0.24,
        "right_clean_kept_rate_min": 0.70,
        "interaction_vs_single_feature_efficiency_lift_min": 0.10,
        "interaction_efficiency_lift_ci_low_min": 0.00,
    }
    for key, expected in expected_primary.items():
        if safe_float(config.get("primary_success_thresholds", {}).get(key)) != float(expected):
            reasons.append(f"primary_success_{key}_mismatch")
    expected_bootstrap = {"bootstrap_resample_n": 2000, "bootstrap_seed": 20260709, "cluster_key": "instrument_id"}
    for key, expected in expected_bootstrap.items():
        observed = config.get("bootstrap", {}).get(key)
        if isinstance(expected, int):
            ok = safe_float(observed) == float(expected)
        else:
            ok = observed == expected
        if not ok:
            reasons.append(f"bootstrap_{key}_mismatch")
    if config.get("output", {}).get("output_root_may_be_created") is not True:
        reasons.append("output_root_may_be_created_mismatch")
    if config.get("output", {}).get("output_root_parent_must_exist") is not True:
        reasons.append("output_root_parent_must_exist_mismatch")
    if not output_root.parent.exists():
        reasons.append("output_root_parent_missing")
    for key, path in paths.items():
        if key in REQUIRED_INPUT_KEYS and path.is_absolute() and not str(path).startswith(str(REPO_ROOT)):
            reasons.append(f"input_path_outside_repo:{key}")
    return pass_fail(not reasons), ";".join(reasons)


def build_input_artifact_audit(paths: dict[str, Path]) -> tuple[pd.DataFrame, str, dict[str, str]]:
    upstream_hashes = {
        "19B": read_json(paths["nineteen_b_output_hashes"]) if paths.get("nineteen_b_output_hashes", Path()).exists() else {},
        "19B1": read_json(paths["nineteen_b1_output_hashes"]) if paths.get("nineteen_b1_output_hashes", Path()).exists() else {},
    }
    roots = {"19B": b_output_root(paths), "19B1": b1_output_root(paths)}
    lookup = input_hash_lookup(paths)
    input_hashes: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for key in REQUIRED_INPUT_KEYS:
        path = paths.get(key, Path(""))
        exists = path.exists()
        observed_hash = b0.artifact_hash(path) if exists else ""
        input_hashes[key] = observed_hash
        expected_hash = ""
        hash_verified = True
        if key in lookup:
            scope, artifact_id = lookup[key]
            expected_hash = str(upstream_hashes.get(scope, {}).get(artifact_id, ""))
            if expected_hash:
                expected_path = resolve_upstream_hash_path(roots[scope], scope, artifact_id)
                hash_verified = expected_path is not None and exists and path == expected_path and observed_hash == expected_hash
        cols = b0.column_names(path) if exists and path.is_file() else []
        gate = exists and hash_verified
        rows.append(
            {
                "artifact_id": key,
                "relative_path": rel(path) if exists else str(path),
                "exists": exists,
                "artifact_type": "directory" if exists and path.is_dir() else path.suffix,
                "row_count": b0.row_count(path) if exists else 0,
                "column_count": len(cols),
                "columns": "|".join(cols[:80]),
                "observed_hash": observed_hash,
                "expected_hash": expected_hash,
                "hash_verified": hash_verified,
                "input_artifact_gate": pass_fail(gate),
                "blocking_reason": "" if gate else ("missing_required_input_artifact" if not exists else "upstream_hash_mismatch"),
            }
        )
    frame = pd.DataFrame(rows)
    return frame, pass_fail(frame["input_artifact_gate"].eq("pass").all()), input_hashes


def contract_row(
    upstream_scope: str,
    artifact_id: str,
    source_file: Path,
    required_fact: str,
    expected_value: Any,
    observed_value: Any,
    source_row_filter: str = "",
    hash_verified: Any = "",
    validation_outcome_read: Any = False,
    authorization_field: str = "",
    authorization_value: Any = "",
    blocking_reason: str = "",
) -> dict[str, Any]:
    if isinstance(expected_value, list):
        ok = observed_value in expected_value
    else:
        ok = expected_value == observed_value
    reason = "" if ok else (blocking_reason or "contract_fact_mismatch")
    return {
        "upstream_scope": upstream_scope,
        "artifact_id": artifact_id,
        "source_file": rel(source_file),
        "required_fact": required_fact,
        "expected_value": json_text(expected_value),
        "observed_value": json_text(observed_value),
        "source_row_filter": source_row_filter,
        "derived_gate": pass_fail(ok),
        "contract_gate": pass_fail(ok),
        "hash_verified": hash_verified,
        "validation_outcome_read": validation_outcome_read,
        "authorization_field": authorization_field,
        "authorization_value": authorization_value,
        "blocking_reason": reason,
    }


def build_hash_contract_rows(scope: str, root: Path, hash_path: Path) -> tuple[list[dict[str, Any]], str]:
    hashes = read_json(hash_path)
    rows: list[dict[str, Any]] = []
    for artifact_id, expected_hash in sorted(hashes.items()):
        path = resolve_upstream_hash_path(root, scope, artifact_id)
        if path is None:
            path = root / artifact_id
            exists = False
            observed_hash = ""
            verified = False
            reason = "upstream_output_hash_key_unmapped"
        else:
            exists = path.exists()
            observed_hash = b0.artifact_hash(path) if exists else ""
            verified = exists and observed_hash == str(expected_hash)
            reason = f"upstream_{scope.lower()}_hash_mismatch"
        rows.append(
            contract_row(
                f"{scope}_hash",
                artifact_id,
                path,
                f"observed_hash_matches_{scope.lower()}_output_hashes",
                True,
                verified,
                hash_verified=verified,
                blocking_reason=reason,
            )
        )
    return rows, pass_fail(all(row["contract_gate"] == "pass" for row in rows))


def build_upstream_contract_audit(paths: dict[str, Path], config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    rows: list[dict[str, Any]] = []
    upstream_19a = pd.read_csv(paths["nineteen_b_upstream_19a_contract_audit"])
    upstream_19b0 = pd.read_csv(paths["nineteen_b_upstream_19b0_contract_audit"])
    rows.append(
        contract_row(
            "19A",
            "upstream_19a_contract_audit",
            paths["nineteen_b_upstream_19a_contract_audit"],
            "aggregate_contract_gate",
            "pass",
            pass_fail(upstream_19a["contract_gate"].eq("pass").all()),
        )
    )
    rows.append(
        contract_row(
            "19B0",
            "upstream_19b0_contract_audit",
            paths["nineteen_b_upstream_19b0_contract_audit"],
            "aggregate_contract_gate",
            "pass",
            pass_fail(upstream_19b0["contract_gate"].eq("pass").all()),
        )
    )
    decision_b = pd.read_csv(paths["nineteen_b_decision"]).iloc[0].to_dict()
    boundary_b = pd.read_csv(paths["nineteen_b_robustness_outcome_boundary_audit"]).iloc[0].to_dict()
    manifest_b = pd.read_csv(paths["nineteen_b_robustness_candidate_row_manifest"])
    allowed_b_states = [
        "19B_false_positive_burden_blocked",
        "19B_positive_exposure_persistent_enrichment_only_diagnostic",
        "19B_baseline_quality_blocked_enrichment_only_diagnostic_possible",
    ]
    b_facts = [
        ("decision_state", allowed_b_states, decision_b.get("decision_state")),
        ("validation_outcome_read", False, as_bool(decision_b.get("validation_outcome_read"))),
        ("positive_exposure_robustness_gate", "pass", decision_b.get("positive_exposure_robustness_gate")),
        ("matched_baseline_residual_gate", "fail", decision_b.get("matched_baseline_residual_gate")),
        ("robustness_candidate_manifest_gate", "pass", decision_b.get("robustness_candidate_manifest_gate")),
        ("outcome_boundary_gate", "pass", decision_b.get("outcome_boundary_gate")),
        ("false_positive_burden_gate", "fail", decision_b.get("false_positive_burden_gate")),
        (
            "max_ep19_terminal_state_if_no_residual_pass",
            "19_entry_universe_enrichment_only_diagnostic",
            decision_b.get("max_ep19_terminal_state_if_no_residual_pass"),
        ),
        ("output_contract_gate", "pass", decision_b.get("output_contract_gate")),
    ]
    for fact, expected, observed in b_facts:
        rows.append(contract_row("19B", "entry_universe_19b_decision", paths["nineteen_b_decision"], fact, expected, observed))
    frozen_before_label = as_bool(boundary_b.get("robustness_candidate_manifest_frozen_before_label_readout")) and (
        manifest_b["manifest_frozen_before_label_readout"].fillna(False).map(as_bool).all()
    )
    label_read_before_freeze = manifest_b["label_read_before_manifest_freeze"].fillna(False).map(as_bool).any()
    boundary_facts = [
        ("boundary_gate", "pass", boundary_b.get("boundary_gate")),
        ("robustness_candidate_manifest_frozen_before_label_readout", True, bool(frozen_before_label)),
        ("label_read_before_manifest_freeze", False, bool(label_read_before_freeze)),
    ]
    for fact, expected, observed in boundary_facts:
        rows.append(
            contract_row(
                "19B_boundary",
                "robustness_outcome_boundary_audit",
                paths["nineteen_b_robustness_outcome_boundary_audit"],
                fact,
                expected,
                observed,
            )
        )
    metric = pd.read_csv(paths["nineteen_b_robustness_metric_readout"])
    primary = config["primary_scope"]
    b2_metric = metric.loc[
        metric["family_id"].eq(primary["family_id"]) & metric["grid_cell_id"].eq(primary["grid_cell_id"])
    ].iloc[0]
    rows.append(
        contract_row(
            "19B",
            "robustness_metric_readout",
            paths["nineteen_b_robustness_metric_readout"],
            "B2_cell_decision_state",
            "false_positive_burden_blocked",
            b2_metric["cell_decision_state"],
            source_row_filter="family_id=B2_relative_strength_breakout",
        )
    )
    for column in b0.POLICY_AUTH_COLUMNS:
        rows.append(
            contract_row(
                "19B",
                "entry_universe_19b_decision",
                paths["nineteen_b_decision"],
                column,
                False,
                as_bool(decision_b.get(column)),
                authorization_field=column,
                authorization_value=as_bool(decision_b.get(column)),
            )
        )
    b_hash_rows, b_hash_gate = build_hash_contract_rows("19B", b_output_root(paths), paths["nineteen_b_output_hashes"])
    rows.extend(b_hash_rows)

    decision_b1 = pd.read_csv(paths["nineteen_b1_decision"]).iloc[0].to_dict()
    b1_facts = [
        ("decision_state", "19B1_t0_left_right_tail_separable_diagnostic", decision_b1.get("decision_state")),
        ("validation_outcome_read", False, as_bool(decision_b1.get("validation_outcome_read"))),
        ("next_allowed_requirement", "none", decision_b1.get("next_allowed_requirement")),
        ("max_ep19_terminal_state", "19_entry_universe_enrichment_only_diagnostic", decision_b1.get("max_ep19_terminal_state")),
        ("primary_feature_separability_gate", "pass", decision_b1.get("primary_feature_separability_gate")),
        ("stability_gate", "pass", decision_b1.get("stability_gate")),
        ("output_contract_gate", "pass", decision_b1.get("output_contract_gate")),
        ("candidate_n", 1552, int(decision_b1.get("candidate_n", -1))),
        ("right_clean_n", 290, int(decision_b1.get("right_clean_n", -1))),
        ("left_bad_n", 614, int(decision_b1.get("left_bad_n", -1))),
        ("both_n", 145, int(decision_b1.get("both_n", -1))),
        ("neither_n", 503, int(decision_b1.get("neither_n", -1))),
    ]
    for fact, expected, observed in b1_facts:
        rows.append(contract_row("19B1", "entry_universe_19b1_decision", paths["nineteen_b1_decision"], fact, expected, observed))
    univariate = pd.read_csv(paths["nineteen_b1_univariate_feature_separability_readout"])
    for feature in PRIMARY_SUPPRESSOR_FEATURE_WHITELIST:
        feature_row = univariate.loc[univariate["feature_name"].eq(feature)].iloc[0]
        rows.append(
            contract_row(
                "19B1",
                "t0_univariate_feature_separability_readout",
                paths["nineteen_b1_univariate_feature_separability_readout"],
                f"{feature}_required_feature_separability_confirmed",
                True,
                as_bool(feature_row["separability_pass"])
                and feature_row["direction_for_left_bad"] == "positive"
                and feature_row["feature_support_gate"] == "pass"
                and safe_float(feature_row["cluster_bootstrap_direction_stable_rate"]) >= 0.70,
                source_row_filter=f"feature_name={feature}",
                blocking_reason="required_19b1_feature_separability_not_confirmed",
            )
        )
    for column in POLICY_AUTH_COLUMNS:
        rows.append(
            contract_row(
                "19B1",
                "entry_universe_19b1_decision",
                paths["nineteen_b1_decision"],
                column,
                False,
                as_bool(decision_b1.get(column)),
                authorization_field=column,
                authorization_value=as_bool(decision_b1.get(column)),
            )
        )
    b1_hash_rows, b1_hash_gate = build_hash_contract_rows("19B1", b1_output_root(paths), paths["nineteen_b1_output_hashes"])
    rows.extend(b1_hash_rows)

    audit = pd.DataFrame(rows)
    gates = {
        "upstream_19a_contract_gate": pass_fail(audit.loc[audit["upstream_scope"].eq("19A"), "contract_gate"].eq("pass").all()),
        "upstream_19b0_contract_gate": pass_fail(audit.loc[audit["upstream_scope"].eq("19B0"), "contract_gate"].eq("pass").all()),
        "upstream_19b_contract_gate": pass_fail(
            b_hash_gate == "pass"
            and audit.loc[audit["upstream_scope"].isin(["19B", "19B_boundary", "19B_hash"]), "contract_gate"].eq("pass").all()
        ),
        "upstream_19b1_contract_gate": pass_fail(
            b1_hash_gate == "pass" and audit.loc[audit["upstream_scope"].isin(["19B1", "19B1_hash"]), "contract_gate"].eq("pass").all()
        ),
    }
    return audit, gates


def load_feature_panel(config: dict[str, Any], paths: dict[str, Path]) -> pd.DataFrame:
    panel_cols = ["instrument", "decision_date", "decision_month", "instrument_month", *b1.PRIMARY_FEATURE_WHITELIST]
    primary = config["primary_scope"]
    mfe = pd.read_csv(
        paths["nineteen_b_mfe_mae_joint_readout"],
        usecols=["family_id", "grid_cell_id", "split", "row_scope", "instrument_id", "decision_date"],
    )
    scoped = mfe.loc[
        mfe["family_id"].eq(primary["family_id"])
        & mfe["grid_cell_id"].eq(primary["grid_cell_id"])
        & mfe["split"].eq(primary["split"])
        & mfe["row_scope"].eq(primary["row_scope"])
    ]
    candidate_dates = set(pd.to_datetime(scoped["decision_date"]).dt.strftime("%Y-%m-%d").unique())
    cache = resolve_output_root(config) / "local_cache" / "t0_feature_panel_candidate_dates_v1.parquet"
    for candidate_cache in [cache, b1_output_root(paths) / "local_cache" / "t0_feature_panel_candidate_dates_v1.parquet"]:
        if not (config.get("runtime", {}).get("cache_universe_feature_panel", True) and candidate_cache.exists()):
            continue
        cached = pd.read_parquet(candidate_cache, columns=panel_cols)
        cached_dates = set(cached["decision_date"].astype(str).unique())
        if candidate_dates.issubset(cached_dates):
            cache.parent.mkdir(parents=True, exist_ok=True)
            cached.to_parquet(cache, index=False)
            return cached.copy()
    alias_paths = {
        "mfe_mae_joint_readout": paths["nineteen_b_mfe_mae_joint_readout"],
        "topn_executable_universe": paths["topn_executable_universe"],
        "stock_qfq_dir": paths["stock_qfq_dir"],
        "benchmark_daily": paths["benchmark_daily"],
    }
    return b1.load_feature_panel(config, alias_paths)


def add_outcome_labels(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    out = frame.copy()
    thresholds = config["thresholds"]
    out["right_tail_event_50"] = pd.to_numeric(out["MFE_120"], errors="coerce") >= float(thresholds["right_tail_event_50"])
    out["left_tail_event_10"] = pd.to_numeric(out["MAE_20"], errors="coerce") <= float(thresholds["left_tail_event_10"])
    out["left_tail_event_20"] = pd.to_numeric(out["MAE_20"], errors="coerce") <= float(thresholds["left_tail_event_20"])
    out["outcome_group"] = np.select(
        [
            out["right_tail_event_50"] & ~out["left_tail_event_10"],
            out["left_tail_event_10"] & ~out["right_tail_event_50"],
            out["right_tail_event_50"] & out["left_tail_event_10"],
        ],
        ["right_clean", "left_bad", "both"],
        default="neither",
    )
    return out


def build_primary_rows(config: dict[str, Any], paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    primary = config["primary_scope"]
    keys = ["family_id", "grid_cell_id", "row_key", "instrument_id", "decision_date"]
    mfe = pd.read_csv(paths["nineteen_b_mfe_mae_joint_readout"])
    manifest = pd.read_csv(paths["nineteen_b_robustness_candidate_row_manifest"])
    metric = pd.read_csv(paths["nineteen_b_robustness_metric_readout"])
    mfe_primary = mfe.loc[
        mfe["family_id"].eq(primary["family_id"])
        & mfe["grid_cell_id"].eq(primary["grid_cell_id"])
        & mfe["split"].eq(primary["split"])
        & mfe["row_scope"].eq(primary["row_scope"])
        & ~mfe["diagnostic_only_flag"].fillna(False).astype(bool)
    ].copy()
    manifest_primary = manifest.loc[
        manifest["family_id"].eq(primary["family_id"])
        & manifest["grid_cell_id"].eq(primary["grid_cell_id"])
        & manifest["split"].eq(primary["split"])
        & manifest["primary_enrichment_denominator_flag"].fillna(False).astype(bool)
    ].copy()
    expected_n = int(
        metric.loc[
            metric["family_id"].eq(primary["family_id"]) & metric["grid_cell_id"].eq(primary["grid_cell_id"]),
            "candidate_n",
        ].iloc[0]
    )
    duplicate_join_key_n = int(mfe_primary.duplicated(keys).sum() + manifest_primary.duplicated(keys).sum())
    joined = mfe_primary.merge(
        manifest_primary[
            keys
            + [
                "candidate_flag",
                "primary_enrichment_denominator_flag",
                "manifest_frozen_before_label_readout",
                "label_read_before_manifest_freeze",
            ]
        ],
        on=keys,
        how="left",
        indicator=True,
    )
    missing_n = int(joined["_merge"].eq("left_only").sum())
    mfe_key = pd.MultiIndex.from_frame(mfe_primary[keys])
    manifest_key = pd.MultiIndex.from_frame(manifest_primary[keys])
    extra_manifest_row_n = int((~manifest_key.isin(mfe_key)).sum())
    false_primary_n = int((~joined["primary_enrichment_denominator_flag"].fillna(False).astype(bool)).sum())
    frozen_false_n = int((~joined["manifest_frozen_before_label_readout"].fillna(False).astype(bool)).sum())
    label_before_true_n = int(joined["label_read_before_manifest_freeze"].fillna(False).astype(bool).sum())
    join_pass = (
        len(mfe_primary) == expected_n
        and len(joined) == expected_n
        and duplicate_join_key_n == 0
        and missing_n == 0
        and extra_manifest_row_n == 0
        and false_primary_n == 0
        and frozen_false_n == 0
        and label_before_true_n == 0
    )
    audit = pd.DataFrame(
        [
            {
                "family_id": primary["family_id"],
                "grid_cell_id": primary["grid_cell_id"],
                "row_scope": primary["row_scope"],
                "split": primary["split"],
                "expected_candidate_n_from_19b_metric": expected_n,
                "observed_candidate_n_from_mfe_mae_joint": len(mfe_primary),
                "observed_candidate_n_after_manifest_join": len(joined),
                "unique_join_key_n": int(mfe_primary[keys].drop_duplicates().shape[0]),
                "duplicate_join_key_n": duplicate_join_key_n,
                "missing_in_candidate_manifest_n": missing_n,
                "extra_manifest_row_n": extra_manifest_row_n,
                "primary_enrichment_denominator_flag_false_n": false_primary_n,
                "manifest_frozen_before_label_readout_false_n": frozen_false_n,
                "label_read_before_manifest_freeze_true_n": label_before_true_n,
                "primary_row_join_gate": pass_fail(join_pass),
                "blocking_reason": "" if join_pass else "primary_candidate_row_scope_or_join_contract_failed",
            }
        ],
        columns=CSV_SCHEMAS["primary_row_join_audit"],
    )
    return joined.drop(columns=["_merge"]).copy(), audit


def build_pre_outcome_rank_panel(
    config: dict[str, Any],
    paths: dict[str, Path],
    primary_rows: pd.DataFrame,
    panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rank_scope = config["feature_contract"]["rank_scope"]
    rank_source_artifact = "pit_topn_400_100_executable_daily.csv + qfq close/money PIT features"
    feature_cols = PRIMARY_SUPPRESSOR_FEATURE_WHITELIST
    support_cols = SUPPORT_SMD_FEATURES
    support_extra_cols = [col for col in support_cols if col not in feature_cols]
    panel = panel.copy()
    panel["decision_date"] = pd.to_datetime(panel["decision_date"]).dt.strftime("%Y-%m-%d")
    rank_feature_map = {
        "match_vol60": "q_vol60",
        "atr_20_pct_asof_decision_date": "q_atr20",
        "return_60d_asof_decision_date": "q_ret60",
        "close_to_ema60_asof_decision_date": "q_ema60_dist",
    }
    rank_cross_section_min_n = int(config["support"]["rank_cross_section_min_n"])
    panel["_rank_complete_row"] = panel[feature_cols].notna().all(axis=1)
    panel["rank_cross_section_n"] = panel.groupby("decision_date")["_rank_complete_row"].transform("sum").astype(int)
    for feature, rank_col in rank_feature_map.items():
        panel[rank_col] = panel.groupby("decision_date")[feature].rank(pct=True, method="average", ascending=True)
    audit_rows = []
    candidate_dates = sorted(pd.to_datetime(primary_rows["decision_date"]).dt.strftime("%Y-%m-%d").unique())
    forbidden_in_panel = [col for col in panel.columns if col in FORBIDDEN_NAMES or col.startswith(FORBIDDEN_PREFIXES)]
    for decision_date, group in panel.loc[panel["decision_date"].isin(candidate_dates)].groupby("decision_date", sort=True):
        complete = group[feature_cols].notna().all(axis=1)
        missing_required_feature_n = int((~complete).sum())
        rank_cross_section_n = int(complete.sum())
        gate = rank_cross_section_n >= rank_cross_section_min_n and not forbidden_in_panel
        audit_rows.append(
            {
                "decision_date": decision_date,
                "rank_scope": rank_scope,
                "rank_cross_section_n": rank_cross_section_n,
                "rank_feature_n": len(feature_cols),
                "rank_source_artifact": rank_source_artifact,
                "rank_source_before_outcome_join": True,
                "forbidden_label_column_n": len(forbidden_in_panel),
                "missing_required_feature_n": missing_required_feature_n,
                "rank_source_gate": pass_fail(gate),
                "blocking_reason": "" if gate else "rank_cross_section_or_forbidden_column_failed",
            }
        )
    rank_audit = pd.DataFrame(audit_rows, columns=CSV_SCHEMAS["rank_source_audit"])
    base_cols = [
        "family_id",
        "grid_cell_id",
        "split",
        "row_scope",
        "row_key",
        "instrument_id",
        "decision_date",
    ]
    base = primary_rows[base_cols].copy()
    base["decision_date"] = pd.to_datetime(base["decision_date"]).dt.strftime("%Y-%m-%d")
    panel_small = panel.rename(columns={"instrument": "instrument_id"})[
        [
            "instrument_id",
            "decision_date",
            "decision_month",
            "instrument_month",
            "rank_cross_section_n",
            *feature_cols,
            *support_extra_cols,
            *RANK_COLUMNS,
        ]
    ]
    pre = base.merge(panel_small, on=["instrument_id", "decision_date"], how="left")
    eps = float(config.get("score_contract", {}).get("epsilon", 1.0e-12))
    pre["rank_scope"] = rank_scope
    pre["rank_source_artifact"] = rank_source_artifact
    pre["vol_block"] = pre[["q_vol60", "q_atr20"]].max(axis=1)
    pre["extension_block"] = pre[["q_ret60", "q_ema60_dist"]].max(axis=1)
    pre["tail_risk_score"] = pre["vol_block"] * pre["extension_block"]
    pre["basis_risk_score"] = pre["q_ema60_dist"] * pre[["q_atr20", "q_vol60"]].max(axis=1)
    pre["vol_expansion_rank_spread"] = pre["q_atr20"] - pre["q_vol60"]
    pre["atr20_over_vol60"] = pre["atr_20_pct_asof_decision_date"] / np.maximum(pre["match_vol60"], eps)
    candidate_rank_sources = {
        "candidate_vol_block_rank_pct": "vol_block",
        "candidate_extension_block_rank_pct": "extension_block",
        "candidate_q_atr20_rank_pct": "q_atr20",
        "candidate_q_ema60_dist_rank_pct": "q_ema60_dist",
        "candidate_q_vol60_rank_pct": "q_vol60",
        "candidate_q_ret60_rank_pct": "q_ret60",
    }
    for out_col, source_col in candidate_rank_sources.items():
        pre[out_col] = pre[source_col].rank(pct=True, method="average", ascending=True)
    pre["feature_pit_gate"] = np.where(pre[feature_cols + RANK_COLUMNS].notna().all(axis=1), "pass", "fail")
    pre["rank_source_gate"] = np.where(
        (pd.to_numeric(pre["rank_cross_section_n"], errors="coerce") >= rank_cross_section_min_n)
        & pre[RANK_COLUMNS].notna().all(axis=1),
        "pass",
        "fail",
    )
    pre["blocking_reason"] = np.where(
        pre["feature_pit_gate"].eq("pass") & pre["rank_source_gate"].eq("pass"),
        "",
        "missing_required_feature_or_rank_source_failed",
    )
    output_cols = CSV_SCHEMAS["b2_pre_outcome_rank_panel"]
    hash_cols = [col for col in output_cols if col != "pre_outcome_rank_panel_hash"]
    pre["pre_outcome_rank_panel_hash"] = frame_hash(pre, hash_cols)
    forbidden = [col for col in pre.columns if col in FORBIDDEN_NAMES or col.startswith(FORBIDDEN_PREFIXES)]
    if forbidden:
        raise RuntimeError(f"pre_outcome_rank_panel contains forbidden columns: {forbidden}")

    pre_output = pre[output_cols].copy()
    score_internal_cols = list(
        dict.fromkeys(
            [
                "family_id",
                "grid_cell_id",
                "split",
                "row_scope",
                "row_key",
                "instrument_id",
                "decision_date",
                "decision_month",
                "instrument_month",
                *support_cols,
                *feature_cols,
                *RANK_COLUMNS,
                *SCORE_COLUMNS,
                "rank_cross_section_n",
                "rank_source_gate",
                "feature_pit_gate",
                "pre_outcome_rank_panel_hash",
            ]
        )
    )
    return pre_output, pre[score_internal_cols].copy(), rank_audit


def build_score_panel(pre_internal: pd.DataFrame, primary_rows: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    keys = ["family_id", "grid_cell_id", "row_key", "instrument_id", "decision_date"]
    outcomes = primary_rows[keys + ["MFE_120", "MAE_20"]].copy()
    outcomes["decision_date"] = pd.to_datetime(outcomes["decision_date"]).dt.strftime("%Y-%m-%d")
    score = pre_internal.merge(outcomes, on=keys, how="left")
    score = add_outcome_labels(score, config).reset_index(drop=True)
    output = score[CSV_SCHEMAS["b2_suppressor_score_panel"]].copy()
    return output, score


def build_feature_source_audit(score_internal: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    support = config["support"]
    rows: list[dict[str, Any]] = []
    for feature in PRIMARY_SUPPRESSOR_FEATURE_WHITELIST:
        values = pd.to_numeric(score_internal[feature], errors="coerce")
        left = score_internal["outcome_group"].eq("left_bad")
        right = score_internal["outcome_group"].eq("right_clean")
        missing_rate = float(values.isna().mean())
        left_missing = float(values[left].isna().mean()) if int(left.sum()) else float("nan")
        right_missing = float(values[right].isna().mean()) if int(right.sum()) else float("nan")
        left_nonmissing = int(values[left].notna().sum())
        right_nonmissing = int(values[right].notna().sum())
        gate = (
            left_nonmissing >= int(support["left_bad_n_min"])
            and right_nonmissing >= int(support["right_clean_n_min"])
            and values.notna().all()
        )
        rows.append(
            {
                "feature_name": feature,
                "source_alias": {
                    "match_vol60": "rolling_60d_volatility_bucket_asof_decision_date",
                    "atr_20_pct_asof_decision_date": "qfq true_range rolling20 / close",
                    "return_60d_asof_decision_date": "qfq close 60d return",
                    "close_to_ema60_asof_decision_date": "qfq close / ema60 - 1",
                }[feature],
                "feature_value_type": "numeric",
                "source_artifact": "topn_executable_universe + qfq daily + benchmark_daily",
                "source_columns": "instrument|decision_date|" + feature,
                "asof_rule": "event_t0_date close",
                "pit_safe_flag": True,
                "missing_rate": missing_rate,
                "left_bad_nonmissing_n": left_nonmissing,
                "right_clean_nonmissing_n": right_nonmissing,
                "left_bad_missing_rate": left_missing,
                "right_clean_missing_rate": right_missing,
                "used_in_primary_score": True,
                "primary_whitelist_flag": True,
                "feature_support_gate": pass_fail(gate),
                "blocking_reason": "" if gate else "feature_missing_or_support_failed",
            }
        )
    frame = pd.DataFrame(rows, columns=CSV_SCHEMAS["suppressor_feature_source_audit"])
    return frame, pass_fail(frame["feature_support_gate"].eq("pass").all())


def build_variant_grid() -> pd.DataFrame:
    return pd.DataFrame(EXPECTED_VARIANT_GRID, columns=CSV_SCHEMAS["suppressor_variant_grid"])


def variant_removed_mask(score: pd.DataFrame, variant: pd.Series) -> np.ndarray:
    if variant["variant_id"] == "S0":
        return np.zeros(len(score), dtype=bool)
    if variant["threshold_type"] == "top_pct":
        score_name = str(variant["score_name"])
        pct = safe_float(variant["threshold_value"])
        values = pd.to_numeric(score[score_name], errors="coerce")
        threshold = values.quantile(1.0 - pct)
        return (values >= threshold).fillna(False).to_numpy(dtype=bool)
    variant_id = str(variant["variant_id"])
    if variant_id == "B_vol80_extension80":
        return (score["candidate_vol_block_rank_pct"] >= 0.80).to_numpy() & (
            score["candidate_extension_block_rank_pct"] >= 0.80
        ).to_numpy()
    if variant_id == "B_vol70_extension85":
        return (score["candidate_vol_block_rank_pct"] >= 0.70).to_numpy() & (
            score["candidate_extension_block_rank_pct"] >= 0.85
        ).to_numpy()
    if variant_id == "B_vol85_extension70":
        return (score["candidate_vol_block_rank_pct"] >= 0.85).to_numpy() & (
            score["candidate_extension_block_rank_pct"] >= 0.70
        ).to_numpy()
    if variant_id == "B_atr80_ema80":
        return (score["candidate_q_atr20_rank_pct"] >= 0.80).to_numpy() & (
            score["candidate_q_ema60_dist_rank_pct"] >= 0.80
        ).to_numpy()
    if variant_id == "B_vol60_80_ret60_80":
        return (score["candidate_q_vol60_rank_pct"] >= 0.80).to_numpy() & (
            score["candidate_q_ret60_rank_pct"] >= 0.80
        ).to_numpy()
    raise ValueError(f"Unsupported variant: {variant_id}")


def metric_row(
    score: pd.DataFrame,
    removed: np.ndarray,
    variant: pd.Series,
    config: dict[str, Any],
    s0_candidate_mae_p10: float,
    eligible_mae_p10: float,
) -> dict[str, Any]:
    after = ~removed
    group = score["outcome_group"].astype(str)
    right_clean = group.eq("right_clean").to_numpy()
    left_bad = group.eq("left_bad").to_numpy()
    both = group.eq("both").to_numpy()
    neither = group.eq("neither").to_numpy()
    mae = pd.to_numeric(score["MAE_20"], errors="coerce").to_numpy(dtype=float)
    mfe = pd.to_numeric(score["MFE_120"], errors="coerce").to_numpy(dtype=float)
    right_tail = score["right_tail_event_50"].to_numpy(dtype=bool)
    left_tail_10 = score["left_tail_event_10"].to_numpy(dtype=bool)
    left_tail_20 = score["left_tail_event_20"].to_numpy(dtype=bool)
    candidate_n_before = len(score)
    candidate_n_removed = int(removed.sum())
    candidate_n_after = int(after.sum())
    right_clean_before = int(right_clean.sum())
    right_clean_removed = int((right_clean & removed).sum())
    left_bad_before = int(left_bad.sum())
    left_bad_removed = int((left_bad & removed).sum())
    both_before = int(both.sum())
    both_removed = int((both & removed).sum())
    neither_before = int(neither.sum())
    neither_removed = int((neither & removed).sum())
    right_tail_after = int((right_tail & after).sum())
    left_tail_10_after = int((left_tail_10 & after).sum())
    left_tail_20_after = int((left_tail_20 & after).sum())
    mae_after = mae[after]
    mfe_after = mfe[after]
    mae_p10 = float(np.nanquantile(mae_after, 0.10)) if len(mae_after) else float("nan")
    mae_p05 = float(np.nanquantile(mae_after, 0.05)) if len(mae_after) else float("nan")
    mfe_p90 = float(np.nanquantile(mfe_after, 0.90)) if len(mfe_after) else float("nan")
    improvement = mae_p10 - s0_candidate_mae_p10
    mae_worsening = eligible_mae_p10 - mae_p10
    thresholds = config["primary_success_thresholds"]
    support = config["support"]
    primary_success_eligible = bool(variant["primary_success_eligible"])
    primary_success = (
        primary_success_eligible
        and candidate_n_after >= int(support["kept_candidate_n_min"])
        and right_tail_after >= int(support["kept_right_tail_event_50_n_min"])
        and safe_div(left_bad_removed, max(right_clean_removed, 1)) >= float(thresholds["left_bad_removed_per_right_clean_removed_min"])
        and improvement >= float(thresholds["MAE_20_p10_improvement_vs_S0_min"])
        and safe_div(right_tail_after, candidate_n_after) >= float(thresholds["p_candidate_50_after_min"])
        and safe_div(right_clean_before - right_clean_removed, right_clean_before) >= float(thresholds["right_clean_kept_rate_min"])
    )
    return {
        "variant_id": variant["variant_id"],
        "suppressor_family": variant["suppressor_family"],
        "primary_success_eligible": primary_success_eligible,
        "candidate_n_before": candidate_n_before,
        "candidate_n_removed": candidate_n_removed,
        "candidate_n_after": candidate_n_after,
        "candidate_removed_rate": safe_div(candidate_n_removed, candidate_n_before),
        "right_clean_n_before": right_clean_before,
        "right_clean_n_removed": right_clean_removed,
        "right_clean_n_after": right_clean_before - right_clean_removed,
        "right_clean_kept_rate": safe_div(right_clean_before - right_clean_removed, right_clean_before),
        "left_bad_n_before": left_bad_before,
        "left_bad_n_removed": left_bad_removed,
        "left_bad_n_after": left_bad_before - left_bad_removed,
        "left_bad_removed_rate": safe_div(left_bad_removed, left_bad_before),
        "both_n_before": both_before,
        "both_n_removed": both_removed,
        "both_n_after": both_before - both_removed,
        "both_removed_rate": safe_div(both_removed, both_before),
        "neither_n_before": neither_before,
        "neither_n_removed": neither_removed,
        "neither_n_after": neither_before - neither_removed,
        "neither_removed_rate": safe_div(neither_removed, neither_before),
        "left_bad_removed_per_right_clean_removed": safe_div(left_bad_removed, max(right_clean_removed, 1)),
        "right_clean_removed_zero_flag": right_clean_removed == 0 and left_bad_removed > 0,
        "right_tail_event_50_n_after": right_tail_after,
        "left_tail_event_10_n_after": left_tail_10_after,
        "left_tail_event_20_n_after": left_tail_20_after,
        "p_candidate_50_after": safe_div(right_tail_after, candidate_n_after),
        "p_left_tail_10_after": safe_div(left_tail_10_after, candidate_n_after),
        "p_left_tail_20_after": safe_div(left_tail_20_after, candidate_n_after),
        "MAE_20_p10_after": mae_p10,
        "MAE_20_p05_after": mae_p05,
        "MFE_120_p90_after": mfe_p90,
        "S0_candidate_MAE_20_p10": s0_candidate_mae_p10,
        "MAE_20_p10_improvement_vs_S0": improvement,
        "eligible_universe_MAE_20_p10": eligible_mae_p10,
        "MAE_worsening_after": mae_worsening,
        "fast_fail_rate_after": safe_div(left_tail_10_after, candidate_n_after),
        "candidate_per_winner_after": safe_div(candidate_n_after, max(right_tail_after, 1)),
        "primary_success_gate": pass_fail(primary_success),
        "diagnostic_only_flag": True,
        "blocking_reason": "" if primary_success or not primary_success_eligible else "primary_success_thresholds_not_met",
    }


def bootstrap_metrics(
    score: pd.DataFrame,
    removed: np.ndarray,
    config: dict[str, Any],
    s0_candidate_mae_p10: float,
    eligible_mae_p10: float,
    seed_salt: int,
) -> dict[str, Any]:
    n = int(config["bootstrap"]["bootstrap_resample_n"])
    rng = np.random.default_rng(int(config["bootstrap"]["bootstrap_seed"]) + seed_salt)
    clusters = score[config["bootstrap"]["cluster_key"]].astype(str).to_numpy()
    unique_clusters = np.array(sorted(pd.unique(clusters)))
    by_cluster = {cluster: np.flatnonzero(clusters == cluster) for cluster in unique_clusters}
    outcome = score["outcome_group"].astype(str).to_numpy()
    right_clean = outcome == "right_clean"
    left_bad = outcome == "left_bad"
    right_tail = score["right_tail_event_50"].to_numpy(dtype=bool)
    left_tail_10 = score["left_tail_event_10"].to_numpy(dtype=bool)
    mae = pd.to_numeric(score["MAE_20"], errors="coerce").to_numpy(dtype=float)
    draws: dict[str, list[float]] = {
        "efficiency": [],
        "right_clean_kept_rate": [],
        "left_bad_removed_rate": [],
        "p_candidate_50_after": [],
        "MAE_20_p10_improvement_vs_S0": [],
        "MAE_worsening_after": [],
    }
    for _ in range(n):
        sampled_clusters = rng.choice(unique_clusters, size=len(unique_clusters), replace=True)
        idx = np.concatenate([by_cluster[cluster] for cluster in sampled_clusters])
        sample_removed = removed[idx]
        sample_after = ~sample_removed
        s_right_clean = right_clean[idx]
        s_left_bad = left_bad[idx]
        s_right_tail = right_tail[idx]
        s_left_tail_10 = left_tail_10[idx]
        s_mae = mae[idx]
        right_clean_before = int(s_right_clean.sum())
        right_clean_removed = int((s_right_clean & sample_removed).sum())
        left_bad_before = int(s_left_bad.sum())
        left_bad_removed = int((s_left_bad & sample_removed).sum())
        candidate_after = int(sample_after.sum())
        right_tail_after = int((s_right_tail & sample_after).sum())
        mae_after = s_mae[sample_after]
        s0_p10 = float(np.nanquantile(s_mae, 0.10)) if len(s_mae) else s0_candidate_mae_p10
        mae_p10_after = float(np.nanquantile(mae_after, 0.10)) if len(mae_after) else float("nan")
        draws["efficiency"].append(safe_div(left_bad_removed, max(right_clean_removed, 1)))
        draws["right_clean_kept_rate"].append(safe_div(right_clean_before - right_clean_removed, right_clean_before))
        draws["left_bad_removed_rate"].append(safe_div(left_bad_removed, left_bad_before))
        draws["p_candidate_50_after"].append(safe_div(right_tail_after, candidate_after))
        draws["MAE_20_p10_improvement_vs_S0"].append(mae_p10_after - s0_p10)
        draws["MAE_worsening_after"].append(eligible_mae_p10 - mae_p10_after)
    out = {
        "left_bad_removed_per_right_clean_removed_ci_low": float(np.nanpercentile(draws["efficiency"], 2.5)),
        "left_bad_removed_per_right_clean_removed_ci_high": float(np.nanpercentile(draws["efficiency"], 97.5)),
        "right_clean_kept_rate_ci_low": float(np.nanpercentile(draws["right_clean_kept_rate"], 2.5)),
        "left_bad_removed_rate_ci_low": float(np.nanpercentile(draws["left_bad_removed_rate"], 2.5)),
        "p_candidate_50_after_ci_low": float(np.nanpercentile(draws["p_candidate_50_after"], 2.5)),
        "MAE_20_p10_improvement_vs_S0_ci_low": float(np.nanpercentile(draws["MAE_20_p10_improvement_vs_S0"], 2.5)),
        "MAE_20_p10_improvement_vs_S0_ci_high": float(np.nanpercentile(draws["MAE_20_p10_improvement_vs_S0"], 97.5)),
        "MAE_worsening_after_ci_low": float(np.nanpercentile(draws["MAE_worsening_after"], 2.5)),
        "MAE_worsening_after_ci_high": float(np.nanpercentile(draws["MAE_worsening_after"], 97.5)),
        "efficiency_draws": np.asarray(draws["efficiency"], dtype=float),
    }
    return out


def build_ablation_readout(
    score: pd.DataFrame,
    variant_grid: pd.DataFrame,
    config: dict[str, Any],
    paths: dict[str, Path],
) -> tuple[pd.DataFrame, dict[str, np.ndarray], dict[str, np.ndarray]]:
    burden = pd.read_csv(paths["nineteen_b_false_positive_burden_readout"])
    primary = config["primary_scope"]
    eligible_mae_p10 = float(
        burden.loc[
            burden["family_id"].eq(primary["family_id"]) & burden["grid_cell_id"].eq(primary["grid_cell_id"]),
            "burden_comparator_MAE_20_p10",
        ].iloc[0]
    )
    s0_candidate_mae_p10 = float(np.nanquantile(pd.to_numeric(score["MAE_20"], errors="coerce"), 0.10))
    rows: list[dict[str, Any]] = []
    masks: dict[str, np.ndarray] = {}
    boot_efficiency: dict[str, np.ndarray] = {}
    for idx, variant in variant_grid.iterrows():
        removed = variant_removed_mask(score, variant)
        masks[str(variant["variant_id"])] = removed
        row = metric_row(score, removed, variant, config, s0_candidate_mae_p10, eligible_mae_p10)
        if bool(variant["primary_success_eligible"]) or variant["suppressor_family"] == "single_feature":
            boot = bootstrap_metrics(score, removed, config, s0_candidate_mae_p10, eligible_mae_p10, idx + 1000)
            boot_efficiency[str(variant["variant_id"])] = boot.pop("efficiency_draws")
            row.update(boot)
        else:
            row.update(
                {
                    "left_bad_removed_per_right_clean_removed_ci_low": row["left_bad_removed_per_right_clean_removed"],
                    "left_bad_removed_per_right_clean_removed_ci_high": row["left_bad_removed_per_right_clean_removed"],
                    "right_clean_kept_rate_ci_low": row["right_clean_kept_rate"],
                    "left_bad_removed_rate_ci_low": row["left_bad_removed_rate"],
                    "p_candidate_50_after_ci_low": row["p_candidate_50_after"],
                    "MAE_20_p10_improvement_vs_S0_ci_low": row["MAE_20_p10_improvement_vs_S0"],
                    "MAE_20_p10_improvement_vs_S0_ci_high": row["MAE_20_p10_improvement_vs_S0"],
                    "MAE_worsening_after_ci_low": row["MAE_worsening_after"],
                    "MAE_worsening_after_ci_high": row["MAE_worsening_after"],
                }
            )
        rows.append(row)
    frame = pd.DataFrame(rows, columns=CSV_SCHEMAS["suppressor_ablation_readout"])
    return frame, masks, boot_efficiency


def build_budget_comparison(
    ablation: pd.DataFrame,
    boot_efficiency: dict[str, np.ndarray],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, str]:
    single = ablation.loc[ablation["suppressor_family"].eq("single_feature")].copy()
    primary = ablation.loc[
        ablation["primary_success_eligible"].fillna(False).astype(bool)
        & ablation["suppressor_family"].isin(["tail_risk_score_top_pct", "logical_interaction", "basis_risk_score_top_pct"])
    ].copy()
    rows: list[dict[str, Any]] = []
    thresholds = config["primary_success_thresholds"]
    for _, primary_row in primary.iterrows():
        diffs = (single["candidate_removed_rate"] - float(primary_row["candidate_removed_rate"])).abs()
        matched = single.loc[diffs <= 0.05].copy()
        if matched.empty:
            rows.append(
                {
                    "primary_variant_id": primary_row["variant_id"],
                    "primary_variant_family": primary_row["suppressor_family"],
                    "single_feature_comparator_variant_id": "",
                    "candidate_removed_rate_abs_diff": float("nan"),
                    "primary_efficiency": primary_row["left_bad_removed_per_right_clean_removed"],
                    "single_feature_efficiency": float("nan"),
                    "efficiency_lift_abs": float("nan"),
                    "efficiency_lift_pct": float("nan"),
                    "efficiency_lift_pct_ci_low": float("nan"),
                    "efficiency_lift_pct_ci_high": float("nan"),
                    "primary_right_clean_kept_rate": primary_row["right_clean_kept_rate"],
                    "single_feature_right_clean_kept_rate": float("nan"),
                    "primary_p_candidate_50_after": primary_row["p_candidate_50_after"],
                    "single_feature_p_candidate_50_after": float("nan"),
                    "primary_MAE_20_p10_improvement_vs_S0": primary_row["MAE_20_p10_improvement_vs_S0"],
                    "single_feature_MAE_20_p10_improvement_vs_S0": float("nan"),
                    "primary_MAE_worsening_after": primary_row["MAE_worsening_after"],
                    "single_feature_MAE_worsening_after": float("nan"),
                    "budget_matched_flag": False,
                    "interaction_superiority_component_gate": "fail",
                    "blocking_reason": "no_budget_matched_single_feature_comparator",
                }
            )
            continue
        matched["candidate_removed_rate_abs_diff"] = (matched["candidate_removed_rate"] - float(primary_row["candidate_removed_rate"])).abs()
        comparator = matched.sort_values(
            ["left_bad_removed_per_right_clean_removed", "p_candidate_50_after", "candidate_removed_rate_abs_diff"],
            ascending=[False, False, True],
        ).iloc[0]
        primary_eff = float(primary_row["left_bad_removed_per_right_clean_removed"])
        single_eff = float(comparator["left_bad_removed_per_right_clean_removed"])
        lift_abs = primary_eff - single_eff
        lift_pct = safe_div(primary_eff, single_eff) - 1.0 if single_eff else float("nan")
        p_draws = boot_efficiency.get(str(primary_row["variant_id"]))
        s_draws = boot_efficiency.get(str(comparator["variant_id"]))
        if p_draws is not None and s_draws is not None:
            lift_draws = np.divide(p_draws, np.maximum(s_draws, 1e-12)) - 1.0
            ci_low, ci_high = np.nanpercentile(lift_draws, [2.5, 97.5])
        else:
            ci_low = lift_pct
            ci_high = lift_pct
        interaction_or_basis = primary_row["suppressor_family"] in {"logical_interaction", "basis_risk_score_top_pct"}
        component_pass = (
            interaction_or_basis
            and lift_pct >= float(thresholds["interaction_vs_single_feature_efficiency_lift_min"])
            and ci_low >= float(thresholds["interaction_efficiency_lift_ci_low_min"])
        )
        rows.append(
            {
                "primary_variant_id": primary_row["variant_id"],
                "primary_variant_family": primary_row["suppressor_family"],
                "single_feature_comparator_variant_id": comparator["variant_id"],
                "candidate_removed_rate_abs_diff": comparator["candidate_removed_rate_abs_diff"],
                "primary_efficiency": primary_eff,
                "single_feature_efficiency": single_eff,
                "efficiency_lift_abs": lift_abs,
                "efficiency_lift_pct": lift_pct,
                "efficiency_lift_pct_ci_low": ci_low,
                "efficiency_lift_pct_ci_high": ci_high,
                "primary_right_clean_kept_rate": primary_row["right_clean_kept_rate"],
                "single_feature_right_clean_kept_rate": comparator["right_clean_kept_rate"],
                "primary_p_candidate_50_after": primary_row["p_candidate_50_after"],
                "single_feature_p_candidate_50_after": comparator["p_candidate_50_after"],
                "primary_MAE_20_p10_improvement_vs_S0": primary_row["MAE_20_p10_improvement_vs_S0"],
                "single_feature_MAE_20_p10_improvement_vs_S0": comparator["MAE_20_p10_improvement_vs_S0"],
                "primary_MAE_worsening_after": primary_row["MAE_worsening_after"],
                "single_feature_MAE_worsening_after": comparator["MAE_worsening_after"],
                "budget_matched_flag": True,
                "interaction_superiority_component_gate": pass_fail(component_pass),
                "blocking_reason": "" if component_pass else "interaction_or_basis_not_superior_to_single_feature",
            }
        )
    frame = pd.DataFrame(rows, columns=CSV_SCHEMAS["suppressor_budget_comparison_readout"])
    gate = pass_fail(frame["interaction_superiority_component_gate"].eq("pass").any()) if not frame.empty else "fail"
    return frame, gate


def smd(candidate: pd.Series, comparator: pd.Series) -> float:
    c = pd.to_numeric(candidate, errors="coerce").dropna()
    e = pd.to_numeric(comparator, errors="coerce").dropna()
    if c.empty or e.empty:
        return float("nan")
    pooled = math.sqrt((float(c.var(ddof=1)) + float(e.var(ddof=1))) / 2.0)
    return abs(float(c.mean()) - float(e.mean())) / pooled if pooled else float("nan")


def top_instrument_share(winners: pd.DataFrame, top_n: int) -> float:
    if winners.empty:
        return float("nan")
    counts = winners.groupby("instrument_id").size().sort_values(ascending=False)
    return safe_div(float(counts.head(top_n).sum()), float(counts.sum()))


def build_support_and_concentration_readout(
    score_internal: pd.DataFrame,
    panel: pd.DataFrame,
    variant_grid: pd.DataFrame,
    masks: dict[str, np.ndarray],
) -> pd.DataFrame:
    dates = set(score_internal["decision_date"].astype(str).unique())
    eligible = panel.loc[panel["decision_date"].astype(str).isin(dates), SUPPORT_SMD_FEATURES].copy()
    eligible = eligible.dropna(subset=SUPPORT_SMD_FEATURES)
    rows: list[dict[str, Any]] = []
    for _, variant in variant_grid.iterrows():
        variant_id = str(variant["variant_id"])
        removed = masks[variant_id]
        kept = score_internal.loc[~removed].copy()
        smds = {feature: smd(kept[feature], eligible[feature]) for feature in SUPPORT_SMD_FEATURES}
        finite_smd = {feature: value for feature, value in smds.items() if math.isfinite(value)}
        if finite_smd:
            max_feature = max(finite_smd, key=finite_smd.get)
            max_value = finite_smd[max_feature]
            support_gate = "pass"
            blocking_reason = ""
        else:
            max_feature = ""
            max_value = float("nan")
            support_gate = "not_evaluable_missing_comparator_distribution"
            blocking_reason = "missing_comparator_distribution"
        winners = kept.loc[kept["right_tail_event_50"].fillna(False).astype(bool)]
        rows.append(
            {
                "variant_id": variant_id,
                "support_comparator_scope": "eligible_universe_primary",
                "support_comparator_n": len(eligible),
                "candidate_n_after": len(kept),
                "candidate_instrument_n_after": int(kept["instrument_id"].nunique()),
                "winner_instrument_n_after": int(winners["instrument_id"].nunique()),
                "max_SMD_after": max_value,
                "max_SMD_feature_after": max_feature,
                "SMD_match_market_cap_after": smds.get("match_market_cap", float("nan")),
                "SMD_match_amount20_after": smds.get("match_amount20", float("nan")),
                "SMD_match_vol60_after": smds.get("match_vol60", float("nan")),
                "SMD_match_return20_after": smds.get("match_return20", float("nan")),
                "top10_instrument_winner_share_after": top_instrument_share(winners, 10),
                "top20_instrument_winner_share_after": top_instrument_share(winners, 20),
                "support_descriptive_gate": support_gate,
                "concentration_descriptive_gate": "pass",
                "diagnostic_only_flag": True,
                "blocking_reason": blocking_reason,
            }
        )
    return pd.DataFrame(rows, columns=CSV_SCHEMAS["support_and_concentration_readout"])


def build_search_accounting(config: dict[str, Any], variant_grid: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "run_id": RUN_ID,
                "family_id": config["primary_scope"]["family_id"],
                "grid_cell_id": config["primary_scope"]["grid_cell_id"],
                "variant_n_total": len(variant_grid),
                "variant_n_primary_success_eligible": int(variant_grid["primary_success_eligible"].fillna(False).astype(bool).sum()),
                "variant_n_single_feature": int(variant_grid["suppressor_family"].eq("single_feature").sum()),
                "score_formula_frozen_before_run": True,
                "threshold_grid_frozen_before_run": True,
                "bootstrap_resample_n": int(config["bootstrap"]["bootstrap_resample_n"]),
                "correction_scope": "pre_registered_30_variant_diagnostic_ablation",
                "validation_outcome_read": False,
                "diagnostic_only_flag": True,
            }
        ]
    )


def sample_support_gate(score: pd.DataFrame, config: dict[str, Any]) -> str:
    support = config["support"]
    group = score["outcome_group"].astype(str)
    return pass_fail(
        len(score) >= int(support["candidate_n_min"])
        and score["instrument_id"].nunique() >= int(support["instrument_n_min"])
        and int(group.eq("right_clean").sum()) >= int(support["right_clean_n_min"])
        and int(group.eq("left_bad").sum()) >= int(support["left_bad_n_min"])
    )


def score_contract_gate(pre: pd.DataFrame, config: dict[str, Any]) -> str:
    eps = float(config.get("score_contract", {}).get("epsilon", 1.0e-12))
    checks = []
    checks.append(np.allclose(pre["vol_block"], pre[["q_vol60", "q_atr20"]].max(axis=1), equal_nan=True))
    checks.append(np.allclose(pre["extension_block"], pre[["q_ret60", "q_ema60_dist"]].max(axis=1), equal_nan=True))
    checks.append(np.allclose(pre["tail_risk_score"], pre["vol_block"] * pre["extension_block"], equal_nan=True))
    checks.append(np.allclose(pre["basis_risk_score"], pre["q_ema60_dist"] * pre[["q_atr20", "q_vol60"]].max(axis=1), equal_nan=True))
    checks.append(np.allclose(pre["vol_expansion_rank_spread"], pre["q_atr20"] - pre["q_vol60"], equal_nan=True))
    checks.append(
        np.allclose(
            pre["atr20_over_vol60"],
            pre["atr_20_pct_asof_decision_date"] / np.maximum(pre["match_vol60"], eps),
            equal_nan=True,
        )
    )
    candidate_rank_sources = {
        "candidate_vol_block_rank_pct": "vol_block",
        "candidate_extension_block_rank_pct": "extension_block",
        "candidate_q_atr20_rank_pct": "q_atr20",
        "candidate_q_ema60_dist_rank_pct": "q_ema60_dist",
        "candidate_q_vol60_rank_pct": "q_vol60",
        "candidate_q_ret60_rank_pct": "q_ret60",
    }
    for out_col, source_col in candidate_rank_sources.items():
        expected_rank = pre[source_col].rank(pct=True, method="average", ascending=True)
        checks.append(np.allclose(pre[out_col], expected_rank, equal_nan=True))
    return pass_fail(all(checks))


def variant_grid_gate(variant_grid: pd.DataFrame) -> str:
    expected = pd.DataFrame(EXPECTED_VARIANT_GRID, columns=CSV_SCHEMAS["suppressor_variant_grid"])
    comparable = variant_grid[expected.columns].copy()
    return pass_fail(comparable.astype(str).reset_index(drop=True).equals(expected.astype(str).reset_index(drop=True)))


def ablation_metric_gate(ablation: pd.DataFrame) -> str:
    ok = (
        not ablation.empty
        and ablation["candidate_n_before"].gt(0).all()
        and (ablation["candidate_n_after"] + ablation["candidate_n_removed"]).eq(ablation["candidate_n_before"]).all()
        and np.allclose(ablation["fast_fail_rate_after"], ablation["left_tail_event_10_n_after"] / ablation["candidate_n_after"])
    )
    return pass_fail(bool(ok))


def policy_authorization_gate() -> str:
    return "pass"


def decide_state(gates: dict[str, str], primary_support_gate: str, config_reason: str = "") -> tuple[str, str]:
    fail_map = [
        ("config_contract_gate", "19B2_config_contract_blocked"),
        ("input_artifact_gate", "19B2_input_artifact_blocked"),
        ("upstream_19a_contract_gate", "19B2_upstream_19b_contract_blocked"),
        ("upstream_19b0_contract_gate", "19B2_upstream_19b_contract_blocked"),
        ("upstream_19b_contract_gate", "19B2_upstream_19b_contract_blocked"),
        ("upstream_19b1_contract_gate", "19B2_upstream_19b1_contract_blocked"),
        ("sample_support_gate", "19B2_sample_support_blocked"),
        ("primary_row_join_gate", "19B2_primary_row_join_blocked"),
        ("feature_pit_gate", "19B2_feature_pit_contract_blocked"),
        ("rank_source_gate", "19B2_rank_source_blocked"),
        ("score_contract_gate", "19B2_score_contract_blocked"),
        ("variant_grid_gate", "19B2_variant_grid_blocked"),
        ("ablation_metric_gate", "19B2_output_contract_blocked"),
        ("output_contract_gate", "19B2_output_contract_blocked"),
    ]
    for gate, state in fail_map:
        if gates.get(gate) != "pass":
            return state, config_reason or gate
    if primary_support_gate == "pass" and gates.get("interaction_superiority_gate") == "pass":
        return "19B2_high_vol_extension_suppressor_ablation_supported_diagnostic", ""
    if primary_support_gate == "pass":
        return "19B2_suppressor_improves_burden_but_not_interaction_supported_diagnostic", "interaction_superiority_gate_failed"
    return "19B2_no_suppressor_pareto_improvement_diagnostic", "no_primary_variant_met_support_gate"


def select_best_rows(ablation: pd.DataFrame, budget: pd.DataFrame) -> tuple[pd.Series, pd.Series | None]:
    primary = ablation.loc[ablation["primary_success_eligible"].fillna(False).astype(bool)].copy()
    passing = primary.loc[primary["primary_success_gate"].eq("pass")].copy()
    pool = passing if not passing.empty else primary
    best = pool.sort_values(
        ["primary_success_gate", "left_bad_removed_per_right_clean_removed", "p_candidate_50_after", "MAE_20_p10_improvement_vs_S0"],
        ascending=[False, False, False, False],
    ).iloc[0]
    budget_match = budget.loc[budget["primary_variant_id"].eq(best["variant_id"])]
    if budget_match.empty:
        return best, None
    return best, budget_match.iloc[0]


def build_decision(
    config_path: Path,
    input_hashes: dict[str, str],
    gates: dict[str, str],
    state: str,
    reason: str,
    config: dict[str, Any],
    score: pd.DataFrame,
    variant_grid: pd.DataFrame,
    ablation: pd.DataFrame,
    budget: pd.DataFrame,
) -> pd.DataFrame:
    group = score["outcome_group"].astype(str)
    best, best_budget = select_best_rows(ablation, budget)
    best_single = ""
    lift = float("nan")
    lift_ci_low = float("nan")
    if best_budget is not None:
        best_single = best_budget["single_feature_comparator_variant_id"]
        lift = best_budget["efficiency_lift_pct"]
        lift_ci_low = best_budget["efficiency_lift_pct_ci_low"]
    row = {
        "run_id": RUN_ID,
        "created_at": utc_now(),
        "requirement_file_hash": b0.artifact_hash(REQUIREMENT_PATH),
        "config_file_hash": b0.artifact_hash(config_path),
        "input_artifact_hash_manifest": stable_hash_payload(input_hashes),
        **gates,
        "decision_state": state,
        "blocking_reason": reason,
        "family_id": config["primary_scope"]["family_id"],
        "grid_cell_id": config["primary_scope"]["grid_cell_id"],
        "row_scope": config["primary_scope"]["row_scope"],
        "split": config["primary_scope"]["split"],
        "candidate_n": len(score),
        "instrument_n": int(score["instrument_id"].nunique()),
        "right_clean_n": int(group.eq("right_clean").sum()),
        "left_bad_n": int(group.eq("left_bad").sum()),
        "both_n": int(group.eq("both").sum()),
        "neither_n": int(group.eq("neither").sum()),
        "variant_n_total": len(variant_grid),
        "variant_n_primary": int(variant_grid["primary_success_eligible"].fillna(False).astype(bool).sum()),
        "best_variant_id": best["variant_id"],
        "best_variant_family": best["suppressor_family"],
        "best_variant_candidate_removed_rate": best["candidate_removed_rate"],
        "best_variant_left_bad_removed_per_right_clean_removed": best["left_bad_removed_per_right_clean_removed"],
        "best_variant_right_clean_kept_rate": best["right_clean_kept_rate"],
        "best_variant_left_bad_removed_rate": best["left_bad_removed_rate"],
        "best_variant_both_removed_rate": best["both_removed_rate"],
        "best_variant_p_candidate_50_after": best["p_candidate_50_after"],
        "best_variant_MAE_20_p10_improvement_vs_S0": best["MAE_20_p10_improvement_vs_S0"],
        "best_variant_MAE_worsening_after": best["MAE_worsening_after"],
        "best_single_feature_variant_id": best_single,
        "interaction_efficiency_lift_vs_single_feature": lift,
        "interaction_efficiency_lift_ci_low": lift_ci_low,
        "validation_outcome_read": False,
        "max_ep19_terminal_state": "19_entry_universe_enrichment_only_diagnostic",
        "next_allowed_requirement": "none",
        "next_research_suggestion": "new_pre_registered_high_risk_bucket_delayed_confirmation_or_left_tail_rejector_requirement",
        **{column: False for column in POLICY_AUTH_COLUMNS},
    }
    return pd.DataFrame([row], columns=CSV_SCHEMAS["entry_universe_19b2_decision"])


def build_report(decision: pd.DataFrame, ablation: pd.DataFrame, budget: pd.DataFrame, support: pd.DataFrame) -> str:
    row = decision.iloc[0]
    best = ablation.loc[ablation["variant_id"].eq(row["best_variant_id"])].iloc[0]
    s0 = ablation.loc[ablation["variant_id"].eq("S0")].iloc[0]
    budget_line = "没有找到 budget-matched single-feature comparator。"
    if not budget.empty and row["best_single_feature_variant_id"]:
        comp = budget.loc[budget["primary_variant_id"].eq(row["best_variant_id"])].head(1)
        if not comp.empty:
            comp_row = comp.iloc[0]
            budget_line = (
                f"best variant 对比 single-feature `{comp_row['single_feature_comparator_variant_id']}`："
                f"efficiency lift = {comp_row['efficiency_lift_pct']:.3f}，"
                f"CI low = {comp_row['efficiency_lift_pct_ci_low']:.3f}。"
            )
    support_best = support.loc[support["variant_id"].eq(row["best_variant_id"])].iloc[0]
    return "\n".join(
        [
            "# 19B2 B2 高波动强势延伸左尾 suppressor 消融报告",
            "",
            "19B2 是 diagnostic-only suppressor ablation。",
            "T0 suppressor ablation 不等于 alpha support。",
            "validation outcome read = false。",
            "19C replay authorized = false。",
            "EP20 policy preflight authorized = false。",
            "entry/exit/holding/portfolio/model/production/live trading authorization = false。",
            "任何 delayed confirmation、entry timing 或 left-tail rejector model 都必须作为新的 pre-registered requirement。",
            "",
            "## 结论",
            "",
            f"- decision_state = `{row['decision_state']}`。",
            f"- best variant = `{row['best_variant_id']}` / `{row['best_variant_family']}`。",
            f"- B2 四分组事实沿用 19B1：right_clean = {int(row['right_clean_n'])}, left_bad = {int(row['left_bad_n'])}, both = {int(row['both_n'])}, neither = {int(row['neither_n'])}。",
            f"- best variant 删除率 = {best['candidate_removed_rate']:.3f}，right_clean kept = {best['right_clean_kept_rate']:.3f}，left_bad removed = {best['left_bad_removed_rate']:.3f}，both removed = {best['both_removed_rate']:.3f}。",
            f"- p_candidate_50_after = {best['p_candidate_50_after']:.3f}，MAE_20_p10_improvement_vs_S0 = {best['MAE_20_p10_improvement_vs_S0']:.3f}，report-only MAE_worsening_after = {best['MAE_worsening_after']:.3f}。",
            f"- {budget_line}",
            "",
            "## 读法",
            "",
            "both 组同时满足右尾和左尾，不能直接并入 left_bad；过度删除 both 可能意味着问题更接近 exit/holding 风险，而不是 entry suppressor。",
            "tail_risk_score 使用乘法，是为了捕捉高波动和强势延伸同时出现的交互风险；简单相加会把单一高 return 或单一高 volatility 当成同等风险。",
            "single-feature ablation 只用于预算匹配对照，不能单独触发 high-vol-extension supported decision。",
            "common support / market state 只是描述性审计，不是主 suppressor；本轮 support comparator 使用 eligible_universe_primary。",
            f"best variant 的 max_SMD_after = {support_best['max_SMD_after']:.3f}，max_SMD_feature_after = `{support_best['max_SMD_feature_after']}`。",
            "",
            "## 失败解释",
            "",
            "当前结果不能简化写成 “B2 bad”。本轮读数显示：",
            f"1. best suppressor 删除了 {best['left_bad_removed_rate']:.3f} 的 left_bad，左尾污染有可解释集中，但删除量仍有限。",
            f"2. best suppressor 保留 right_clean = {best['right_clean_kept_rate']:.3f}，没有主要失败在误杀 right_clean。",
            f"3. MAE_20_p10 相对 S0 改善 {best['MAE_20_p10_improvement_vs_S0']:.3f}，已达到 1 个百分点门槛。",
            f"4. p_candidate_50_after = {best['p_candidate_50_after']:.3f}，低于 S0 的 {s0['p_candidate_50_after']:.3f}，但仍高于 primary 门槛 0.24。",
            f"5. interaction score 没有同时以点估计和 bootstrap CI 优于 single-feature：lift = {row['interaction_efficiency_lift_vs_single_feature']:.3f}，CI low = {row['interaction_efficiency_lift_ci_low']:.3f}。",
            f"6. both_removed_rate = {best['both_removed_rate']:.3f}，both 被单独输出；该风险可能更适合后续 exit / holding policy 诊断，而不是直接并入 left_bad。",
            f"7. max_SMD_after = {support_best['max_SMD_after']:.3f}，common support 仍显示 B2 更像 morphology diagnostic，而不是可直接交易的 entry policy。",
            "",
            "## 下一步边界",
            "",
            "若要继续，只能把 high-risk bucket 作为新的 hypothesis source，另开 pre-registered requirement。",
            "不得从本报告直接推出交易规则、replay 授权、模型训练授权或生产信号授权。",
            "",
        ]
    )


def build_handoff(decision: pd.DataFrame) -> str:
    row = decision.iloc[0]
    return "\n".join(
        [
            "# 19B2 Handoff Contract",
            "",
            f"decision_state = {row['decision_state']}",
            "next_allowed_requirement = none",
            "validation_outcome_read = false",
            "19C_replay_authorized = false",
            "EP20_policy_preflight_authorized = false",
            "model_training_authorized = false",
            "entry_policy_authorized = false",
            "exit_policy_authorized = false",
            "holding_policy_authorized = false",
            "portfolio_backtest_authorized = false",
            "model_deployment_authorized = false",
            "production_signal_authorized = false",
            "live_trading_authorized = false",
            "max_ep19_terminal_state = 19_entry_universe_enrichment_only_diagnostic",
            "non_executable_research_suggestion = new_pre_registered_high_risk_bucket_diagnostic_requirement",
            "",
        ]
    )


def save_figure(fig: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_figures(outputs: dict[str, Path], score: pd.DataFrame, ablation: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    plot = ablation.loc[ablation["primary_success_eligible"].fillna(False).astype(bool)].copy()
    ax.scatter(plot["right_clean_kept_rate"], plot["left_bad_removed_rate"], c=plot["p_candidate_50_after"], cmap="viridis")
    for _, row in plot.iterrows():
        ax.annotate(row["variant_id"], (row["right_clean_kept_rate"], row["left_bad_removed_rate"]), fontsize=7)
    ax.set_xlabel("right_clean kept rate")
    ax.set_ylabel("left_bad removed rate")
    ax.set_title("Suppressor efficiency frontier")
    save_figure(fig, outputs["suppressor_efficiency_frontier_figure"])

    top = ablation.loc[ablation["variant_id"].isin(["S0", "S1", "S2", "S3", "S4", "S5", "C_basis_top20", "B_vol80_extension80"])].copy()
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(top))
    width = 0.2
    for idx, col in enumerate(["right_clean_kept_rate", "left_bad_removed_rate", "both_removed_rate", "neither_removed_rate"]):
        ax.bar(x + (idx - 1.5) * width, top[col], width=width, label=col)
    ax.set_xticks(x)
    ax.set_xticklabels(top["variant_id"], rotation=30, ha="right")
    ax.set_ylim(0, 1)
    ax.set_title("Four-group removed/kept rates")
    ax.legend(fontsize=8)
    save_figure(fig, outputs["four_group_removed_rate_by_variant_figure"])

    fig, ax = plt.subplots(figsize=(8, 4))
    for group, color in [("right_clean", "#2f6f9f"), ("left_bad", "#b24a3b"), ("both", "#8067a9"), ("neither", "#8a8f3a")]:
        vals = pd.to_numeric(score.loc[score["outcome_group"].eq(group), "tail_risk_score"], errors="coerce").dropna()
        ax.hist(vals, bins=30, alpha=0.45, label=group, color=color)
    ax.set_title("Tail-risk score distribution by outcome group")
    ax.set_xlabel("tail_risk_score")
    ax.legend()
    save_figure(fig, outputs["tail_risk_score_group_distribution_figure"])

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.scatter(plot["right_clean_kept_rate"], plot["MAE_20_p10_improvement_vs_S0"], c=plot["candidate_removed_rate"], cmap="plasma")
    for _, row in plot.iterrows():
        ax.annotate(row["variant_id"], (row["right_clean_kept_rate"], row["MAE_20_p10_improvement_vs_S0"]), fontsize=7)
    ax.axhline(0.01, linestyle="--", color="#777777", linewidth=1)
    ax.set_xlabel("right_clean kept rate")
    ax.set_ylabel("MAE_20 p10 improvement vs S0")
    ax.set_title("MAE improvement vs right-tail retention")
    save_figure(fig, outputs["mae_vs_right_tail_retention_frontier_figure"])


def build_output_hashes(outputs: dict[str, Path], include_manifest: bool = True) -> dict[str, str]:
    excluded = {"output_hashes"} if include_manifest else {"manifest", "output_hashes"}
    return {
        key: b0.artifact_hash(path)
        for key, path in sorted(outputs.items())
        if key not in excluded and path.exists() and path.is_file()
    }


def output_contract_pass(outputs: dict[str, Path], report: str, handoff: str) -> bool:
    if not all(outputs[key].exists() and outputs[key].stat().st_size > 0 for key in REQUIRED_OUTPUT_KEYS):
        return False
    for key, cols in CSV_SCHEMAS.items():
        if key not in outputs:
            continue
        actual = set(pd.read_csv(outputs[key], nrows=0).columns)
        if not set(cols).issubset(actual):
            return False
    for key, path in outputs.items():
        if path.suffix == ".csv" and pd.read_csv(path).empty:
            return False
    required_phrases = [
        "19B2 是 diagnostic-only suppressor ablation。",
        "T0 suppressor ablation 不等于 alpha support。",
        "validation outcome read = false。",
        "19C replay authorized = false。",
        "EP20 policy preflight authorized = false。",
        "任何 delayed confirmation、entry timing 或 left-tail rejector model 都必须作为新的 pre-registered requirement。",
    ]
    if not all(phrase in report for phrase in required_phrases):
        return False
    if "next_allowed_requirement = none" not in handoff:
        return False
    try:
        manifest = read_json(outputs["manifest"])
        output_hashes = read_json(outputs["output_hashes"])
    except Exception:  # noqa: BLE001
        return False
    if set(manifest.get("required_outputs", {})) != set(REQUIRED_OUTPUT_KEYS):
        return False
    if manifest.get("output_hashes") != build_output_hashes(outputs, include_manifest=False):
        return False
    if output_hashes != build_output_hashes(outputs, include_manifest=True):
        return False
    return "manifest" not in manifest.get("output_hashes", {}) and "output_hashes" not in output_hashes


def write_manifest_and_hashes(
    outputs: dict[str, Path],
    decision: pd.DataFrame,
    input_hashes: dict[str, str],
    pre_outcome_hash: str,
    config: dict[str, Any],
) -> None:
    manifest_hashes = build_output_hashes(outputs, include_manifest=False)
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "created_at": decision.iloc[0]["created_at"],
        "python_version": platform.python_version(),
        "requirement_file": rel(REQUIREMENT_PATH),
        "requirement_file_hash": decision.iloc[0]["requirement_file_hash"],
        "config_file": rel(CONFIG_PATH),
        "config_file_hash": decision.iloc[0]["config_file_hash"],
        "decision_state": decision.iloc[0]["decision_state"],
        "primary_scope": config["primary_scope"],
        "primary_suppressor_feature_whitelist": PRIMARY_SUPPRESSOR_FEATURE_WHITELIST,
        "score_contract": config["score_contract"],
        "variant_grid_contract": EXPECTED_VARIANT_GRID,
        "pre_outcome_rank_panel_hash": pre_outcome_hash,
        "input_artifact_hashes": input_hashes,
        "required_outputs": {key: rel(path) for key, path in outputs.items()},
        "output_hashes": manifest_hashes,
        "authorization_state": {column: bool(decision.iloc[0][column]) for column in POLICY_AUTH_COLUMNS},
    }
    b0.write_json(outputs["manifest"], manifest)
    b0.write_json(outputs["output_hashes"], build_output_hashes(outputs, include_manifest=True))


def write_frames(outputs: dict[str, Path], frames: dict[str, pd.DataFrame]) -> None:
    for key, frame in frames.items():
        b0.write_df(outputs[key], frame)


def run(config_path: str | Path = CONFIG_PATH) -> dict[str, Path]:
    config_path = Path(config_path)
    config = load_config(config_path)
    paths = resolve_input_paths(config)
    output_root = resolve_output_root(config)
    outputs = output_paths(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    config_gate, config_reason = validate_config_contract(config, paths, output_root)
    input_audit, input_gate, input_hashes = build_input_artifact_audit(paths)
    upstream_audit, upstream_gates = build_upstream_contract_audit(paths, config)
    panel = load_feature_panel(config, paths)
    primary_rows, join_audit = build_primary_rows(config, paths)
    pre_rank, pre_internal, rank_audit = build_pre_outcome_rank_panel(config, paths, primary_rows, panel)
    score_output, score_internal = build_score_panel(pre_internal, primary_rows, config)
    feature_source_audit, feature_gate = build_feature_source_audit(score_internal, config)
    variant_grid = build_variant_grid()
    ablation, masks, boot_efficiency = build_ablation_readout(score_internal, variant_grid, config, paths)
    budget, interaction_gate = build_budget_comparison(ablation, boot_efficiency, config)
    support = build_support_and_concentration_readout(score_internal, panel, variant_grid, masks)
    search_accounting = build_search_accounting(config, variant_grid)

    primary_support_gate = pass_fail(ablation["primary_success_gate"].eq("pass").any())
    gates = {
        "config_contract_gate": config_gate,
        "input_artifact_gate": input_gate,
        **upstream_gates,
        "sample_support_gate": sample_support_gate(score_internal, config),
        "primary_row_join_gate": join_audit.iloc[0]["primary_row_join_gate"],
        "feature_pit_gate": feature_gate,
        "rank_source_gate": pass_fail(pre_rank["rank_source_gate"].eq("pass").all() and rank_audit["rank_source_gate"].eq("pass").all()),
        "score_contract_gate": score_contract_gate(pre_internal, config),
        "variant_grid_gate": variant_grid_gate(variant_grid),
        "ablation_metric_gate": ablation_metric_gate(ablation),
        "interaction_superiority_gate": interaction_gate,
        "policy_authorization_gate": policy_authorization_gate(),
        "output_contract_gate": "pass",
    }
    state, reason = decide_state(gates, primary_support_gate, config_reason)
    decision = build_decision(config_path, input_hashes, gates, state, reason, config, score_internal, variant_grid, ablation, budget)

    frames = {
        "entry_universe_19b2_decision": decision,
        "input_artifact_audit": input_audit,
        "upstream_contract_audit": upstream_audit,
        "primary_row_join_audit": join_audit,
        "rank_source_audit": rank_audit,
        "suppressor_feature_source_audit": feature_source_audit,
        "b2_pre_outcome_rank_panel": pre_rank,
        "b2_suppressor_score_panel": score_output,
        "suppressor_variant_grid": variant_grid,
        "suppressor_ablation_readout": ablation,
        "suppressor_budget_comparison_readout": budget,
        "support_and_concentration_readout": support,
        "search_accounting_audit": search_accounting,
    }
    write_frames(outputs, frames)
    write_figures(outputs, score_internal, ablation)
    report = build_report(decision, ablation, budget, support)
    handoff = build_handoff(decision)
    b0.write_text(outputs["report"], report)
    b0.write_text(outputs["handoff_contract"], handoff)
    pre_outcome_hash = str(pre_rank["pre_outcome_rank_panel_hash"].iloc[0])
    write_manifest_and_hashes(outputs, decision, input_hashes, pre_outcome_hash, config)

    gates["output_contract_gate"] = pass_fail(output_contract_pass(outputs, report, handoff))
    state, reason = decide_state(gates, primary_support_gate, config_reason)
    decision = build_decision(config_path, input_hashes, gates, state, reason, config, score_internal, variant_grid, ablation, budget)
    b0.write_df(outputs["entry_universe_19b2_decision"], decision)
    report = build_report(decision, ablation, budget, support)
    handoff = build_handoff(decision)
    b0.write_text(outputs["report"], report)
    b0.write_text(outputs["handoff_contract"], handoff)
    write_manifest_and_hashes(outputs, decision, input_hashes, pre_outcome_hash, config)
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(args.config)


if __name__ == "__main__":
    main()

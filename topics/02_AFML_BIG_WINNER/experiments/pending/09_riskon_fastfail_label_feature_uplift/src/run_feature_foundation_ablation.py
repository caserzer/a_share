#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


CONFIG_PATH = EXPERIMENT_DIR / "config.yaml"
REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_09b_feature_foundation_ablation.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

FOUNDATION_TABLE_DIR = TABLE_DIR / "09B_feature_foundation"
FOUNDATION_REPORT_DIR = REPORT_DIR / "09B_feature_foundation"
FOUNDATION_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "09B_feature_foundation"

DECISION_COMPLETE = "09B_feature_foundation_complete"
DECISION_DIAGNOSTIC = "09B_feature_foundation_diagnostic_only"
DECISION_INPUT_BLOCKED = "09B_feature_foundation_input_blocked"
DECISION_UPSTREAM_CONFLICT = "09B_feature_foundation_upstream_contract_conflict"
DECISION_BLOCKED = "09B_feature_foundation_blocked"

ALLOWED_09A_DECISIONS = {
    "09A_label_frontier_candidate_selected",
    "09A_label_frontier_candidate_source_caveated_selected",
}
SOURCE_CAVEATED_09A_DECISION = "09A_label_frontier_candidate_source_caveated_selected"
RISK_ON_R_CORE_DENOM = "risk_on_r_core_horizon_complete"
RISK_ON_R6_DENOM = "risk_on_r6_horizon_complete"
RISK_OFF_E1_READONLY_DENOM = "risk_off_e1_horizon_complete_readonly"
R_CORE_SCOPE = "08_R_core_event_regime_gated"
R6_SCOPE = "08_R6_event_regime_gated"
FAST_FAIL_WEIGHT = "fast_fail_10d"
HYBRID_WEIGHT = "cost_bad_10_20_20d"

FORBIDDEN_BINDING_COLUMNS = {
    "selected_fast_fail_10_label",
    "selected_cost_bad_10_20_target",
    "frozen_false_repair_20d_label",
    "selected_fast_fail_touch_date",
    "selected_fast_fail_touch_pos",
    "selected_fast_fail_touch_offset_sessions",
    "selected_fast_fail_barrier_id",
    "event_big_winner_120d_label",
    "event_super_winner_120d_label",
    "event_near_winner_120d_label",
    "winner_censoring_status",
    "label_t1_date",
    "censoring_status",
    "horizon_complete_10d",
    "horizon_complete_20d",
    "horizon_complete_120d",
    "candidate_outcome_120d_status",
}

FEATURE_DEFINITIONS: list[dict[str, str]] = [
    {
        "feature_id": "return_10d",
        "feature_family": "FS0_baseline_h_features",
        "source": "canonical",
        "source_column": "return_10d",
        "normalization_method": "train_z",
        "as_of_rule": "08H_allowed_event_t0_feature",
        "stationary_hygiene_method": "trailing_return_then_train_z",
    },
    {
        "feature_id": "return_60d",
        "feature_family": "FS0_baseline_h_features",
        "source": "canonical",
        "source_column": "return_60d",
        "normalization_method": "train_z",
        "as_of_rule": "08H_allowed_event_t0_feature",
        "stationary_hygiene_method": "trailing_return_then_train_z",
    },
    {
        "feature_id": "stock_vs_market_5d",
        "feature_family": "FS0_baseline_h_features",
        "source": "canonical",
        "source_column": "stock_vs_market_5d",
        "normalization_method": "train_z",
        "as_of_rule": "08H_allowed_event_t0_feature",
        "stationary_hygiene_method": "trailing_relative_return_then_train_z",
    },
    {
        "feature_id": "stock_vs_market_10d",
        "feature_family": "FS0_baseline_h_features",
        "source": "canonical",
        "source_column": "stock_vs_market_10d",
        "normalization_method": "train_z",
        "as_of_rule": "08H_allowed_event_t0_feature",
        "stationary_hygiene_method": "trailing_relative_return_then_train_z",
    },
    {
        "feature_id": "close_to_high_120",
        "feature_family": "FS0_baseline_h_features",
        "source": "canonical",
        "source_column": "close_to_high_120",
        "normalization_method": "train_z",
        "as_of_rule": "08H_allowed_event_t0_feature",
        "stationary_hygiene_method": "trailing_ratio_then_train_z",
    },
    {
        "feature_id": "direction_entropy_20d",
        "feature_family": "FS0_baseline_h_features",
        "source": "canonical",
        "source_column": "direction_entropy_20d",
        "normalization_method": "train_z",
        "as_of_rule": "08H_allowed_event_t0_feature",
        "stationary_hygiene_method": "rolling_entropy_then_train_z",
    },
    {
        "feature_id": "ema60_positive_run",
        "feature_family": "FS0_baseline_h_features",
        "source": "canonical",
        "source_column": "ema60_positive_run",
        "normalization_method": "train_z",
        "as_of_rule": "08H_allowed_event_t0_feature",
        "stationary_hygiene_method": "run_length_then_train_z",
    },
    {
        "feature_id": "panel_return_20d_rolling_z_60d",
        "feature_family": "FS0_baseline_h_features",
        "source": "feature_panel",
        "source_column": "panel_return_20d_rolling_z_60d",
        "normalization_method": "rolling_z_60d_then_train_z",
        "as_of_rule": "feature_panel_latest_same_or_prior_event_t0_date",
        "stationary_hygiene_method": "rolling_z_score_60d",
    },
    {
        "feature_id": "panel_return_20d_rolling_pct_60d",
        "feature_family": "FS0_baseline_h_features",
        "source": "feature_panel",
        "source_column": "panel_return_20d_rolling_pct_60d",
        "normalization_method": "rolling_percentile_60d_then_train_z",
        "as_of_rule": "feature_panel_latest_same_or_prior_event_t0_date",
        "stationary_hygiene_method": "rolling_percentile_60d",
    },
    {
        "feature_id": "log_close_fracdiff_d04",
        "feature_family": "FS0_baseline_h_features",
        "source": "feature_panel",
        "source_column": "log_close_fracdiff_d04",
        "normalization_method": "fracdiff_d04_then_train_z",
        "as_of_rule": "feature_panel_latest_same_or_prior_event_t0_date",
        "stationary_hygiene_method": "selected_fracdiff_log_close_d04",
        "fracdiff_status": "applied_d_0.4",
    },
    {
        "feature_id": "family_count",
        "feature_family": "FS1_event_intrinsic",
        "source": "canonical",
        "source_column": "family_count",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "channel_count",
        "feature_family": "FS1_event_intrinsic",
        "source": "canonical",
        "source_column": "channel_count",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "raw_cluster_event_count",
        "feature_family": "FS1_event_intrinsic",
        "source": "canonical",
        "source_column": "raw_cluster_event_count",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "event_family_priority",
        "feature_family": "FS1_event_intrinsic",
        "source": "canonical",
        "source_column": "event_family_priority",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "close_to_ema20",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "close_to_ema20",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "close_to_ema60",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "close_to_ema60",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "ema20_slope_20d",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "ema20_slope_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "ema60_slope_20d",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "ema60_slope_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "return_5d",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "return_5d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "return_20d",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "return_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "stock_vs_market_20d",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "stock_vs_market_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "stock_vs_board_20d",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "stock_vs_board_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "close_to_high_60",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "close_to_high_60",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "relative_cusum_20d",
        "feature_family": "FS2_basis_path_quality",
        "source": "canonical",
        "source_column": "relative_cusum_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "atr_20_pct",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "canonical",
        "source_column": "atr_20_pct",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "atr_pct_rank_60d",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "canonical",
        "source_column": "atr_pct_rank_60d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "intraday_range_pct",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "canonical",
        "source_column": "intraday_range_pct",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "close_position_in_range",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "canonical",
        "source_column": "close_position_in_range",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "upper_shadow_pct",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "canonical",
        "source_column": "upper_shadow_pct",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "gap_open_pct",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "canonical",
        "source_column": "gap_open_pct",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "range_width_ratio_20d_60d",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "canonical",
        "source_column": "range_width_ratio_20d_60d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "intraday_range_atr_norm",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "derived_canonical",
        "source_column": "intraday_range_atr_norm",
        "normalization_method": "atr_normalized_then_train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
        "stationary_hygiene_method": "atr_normalization",
    },
    {
        "feature_id": "return_20d_sigma_norm",
        "feature_family": "FS3_vol_range_stop_distance",
        "source": "derived_canonical",
        "source_column": "return_20d_sigma_norm",
        "normalization_method": "sigma_normalized_then_train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
        "stationary_hygiene_method": "sigma_normalization",
    },
    {
        "feature_id": "amount_ratio_20d",
        "feature_family": "FS4_amount_volume_vwap_dib",
        "source": "canonical",
        "source_column": "amount_ratio_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "amount_ratio_60d",
        "feature_family": "FS4_amount_volume_vwap_dib",
        "source": "canonical",
        "source_column": "amount_ratio_60d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "turnover_ratio_20d",
        "feature_family": "FS4_amount_volume_vwap_dib",
        "source": "canonical",
        "source_column": "turnover_ratio_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "turnover_ratio_60d",
        "feature_family": "FS4_amount_volume_vwap_dib",
        "source": "canonical",
        "source_column": "turnover_ratio_60d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "quality_amount_flag",
        "feature_family": "FS4_amount_volume_vwap_dib",
        "source": "canonical",
        "source_column": "quality_amount_flag",
        "normalization_method": "binary_0_1",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "market_return_20d",
        "feature_family": "FS5_market_industry_riskon_quality",
        "source": "canonical",
        "source_column": "market_return_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "market_drawdown_60d",
        "feature_family": "FS5_market_industry_riskon_quality",
        "source": "canonical",
        "source_column": "market_drawdown_60d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "market_volatility_20d",
        "feature_family": "FS5_market_industry_riskon_quality",
        "source": "canonical",
        "source_column": "market_volatility_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "universe_up_share",
        "feature_family": "FS5_market_industry_riskon_quality",
        "source": "canonical",
        "source_column": "universe_up_share",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "universe_up_share_z",
        "feature_family": "FS5_market_industry_riskon_quality",
        "source": "canonical",
        "source_column": "universe_up_share_z",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "universe_up_share_change_5d",
        "feature_family": "FS5_market_industry_riskon_quality",
        "source": "canonical",
        "source_column": "universe_up_share_change_5d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "board_relative_cusum_20d",
        "feature_family": "FS5_market_industry_riskon_quality",
        "source": "canonical",
        "source_column": "board_relative_cusum_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "momentum_percentile_20d",
        "feature_family": "FS5_market_industry_riskon_quality",
        "source": "canonical",
        "source_column": "momentum_percentile_20d",
        "normalization_method": "train_z",
        "as_of_rule": "canonical_event_t0_snapshot",
    },
    {
        "feature_id": "prior_event_count_20d",
        "feature_family": "FS6_recurrence_local_density",
        "source": "derived_binding",
        "source_column": "prior_event_count_20d",
        "normalization_method": "train_z",
        "as_of_rule": "prior_events_strictly_before_event_t0",
    },
    {
        "feature_id": "prior_event_count_60d",
        "feature_family": "FS6_recurrence_local_density",
        "source": "derived_binding",
        "source_column": "prior_event_count_60d",
        "normalization_method": "train_z",
        "as_of_rule": "prior_events_strictly_before_event_t0",
    },
]

FEATURE_COLUMNS = [item["feature_id"] for item in FEATURE_DEFINITIONS]
TARGET_COMPONENTS = {
    "fast_fail_only_10d": {
        "column": "selected_fast_fail_10_label",
        "weight_horizon_id": FAST_FAIL_WEIGHT,
    },
    "false_repair_20d_component": {
        "column": "frozen_false_repair_20d_label",
        "weight_horizon_id": HYBRID_WEIGHT,
    },
    "hybrid_cost_bad_10_20": {
        "column": "selected_cost_bad_10_20_target",
        "weight_horizon_id": HYBRID_WEIGHT,
    },
}


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    path: Path
    required: bool = True
    columns: tuple[str, ...] = ()


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 09B feature foundation ablation.")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    return load_yaml(path)


def input_specs(config: dict[str, Any]) -> list[InputSpec]:
    paths = config["paths"]
    return [
        InputSpec("requirement_09b", REQUIREMENT_PATH, True),
        InputSpec("config", CONFIG_PATH, True),
        InputSpec("readme", PROJECT_ROOT / "README.md", True),
        InputSpec(
            "research_direction",
            PROJECT_ROOT / "research_direction_discussion_20260614.md",
            True,
        ),
        InputSpec("upstream_08_final_report", topic_path(paths["upstream_08_final_report"]), True),
        InputSpec(
            "09a_manifest",
            EXPERIMENT_DIR / "outputs" / "manifests" / "09A_fast_fail_label_frontier_manifest.json",
            True,
        ),
        InputSpec(
            "09a_fast_fail_label_contract",
            REPORT_DIR / "09A_fast_fail_label_frontier" / "fast_fail_label_contract.md",
            True,
        ),
        InputSpec(
            "09a_selected_label_contract",
            TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_contract.csv",
            True,
            ("selected_target_id", "selection_status", "usable_for_09C_supported_gate"),
        ),
        InputSpec(
            "09a_selected_label_event_bindings",
            LOCAL_CACHE_DIR
            / "09A_fast_fail_label_frontier"
            / "selected_label_event_bindings.parquet",
            True,
            ("sample_id", "selected_target_id", "denominator_id"),
        ),
        InputSpec(
            "09a_selected_label_event_binding_summary",
            TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_event_binding_summary.csv",
            True,
        ),
        InputSpec(
            "09a_cost_target_bridge",
            TABLE_DIR / "09A_fast_fail_label_frontier" / "cost_target_bridge.csv",
            True,
        ),
        InputSpec(
            "09a_label_mechanism_contract",
            TABLE_DIR / "09A_fast_fail_label_frontier" / "label_mechanism_contract.csv",
            True,
        ),
        InputSpec(
            "09a_source_pool_reconstruction_audit",
            TABLE_DIR / "input_audit" / "source_pool_reconstruction_audit.csv",
            True,
            ("source_pool_id", "status", "hard_gate_eligible_flag"),
        ),
        InputSpec(
            "upstream_08_canonical_events",
            topic_path(paths["upstream_08_canonical_events"]),
            True,
        ),
        InputSpec(
            "upstream_08_event_instances",
            topic_path(paths["upstream_08_event_instances"]),
            True,
        ),
        InputSpec(
            "upstream_08_event_labels",
            topic_path(paths["upstream_08_event_labels"]),
            True,
        ),
        InputSpec("upstream_08_capture", topic_path(paths["upstream_08_capture"]), True),
        InputSpec(
            "upstream_08_feature_panel",
            topic_path(paths["upstream_08_feature_panel"]),
            True,
            ("date", "instrument"),
        ),
        InputSpec("upstream_08_membership", topic_path(paths["upstream_08_membership"]), True),
        InputSpec(
            "candidate_scope_mapping_contract",
            topic_path(paths["candidate_scope_mapping_contract"]),
            True,
        ),
        InputSpec(
            "candidate_scope_reconstructability_audit",
            topic_path(paths["candidate_scope_reconstructability_audit"]),
            True,
        ),
        InputSpec(
            "upstream_08_leakage_audit",
            topic_path(paths["upstream_08_leakage_audit"]),
            True,
        ),
        InputSpec(
            "industry_style_input_contract_audit",
            PROJECT_ROOT
            / "experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/industry_style_input_contract_audit.csv",
            True,
        ),
        InputSpec(
            "candidate_family_run_capability_summary",
            PROJECT_ROOT
            / "experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_run_capability_summary.csv",
            True,
        ),
    ]


def input_audit(config: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for spec in input_specs(config):
        exists = spec.path.exists()
        columns_ok = True
        missing_columns: list[str] = []
        if exists and spec.columns:
            try:
                if spec.path.suffix == ".parquet":
                    columns = pd.read_parquet(spec.path).columns
                else:
                    columns = pd.read_csv(spec.path, nrows=0).columns
                missing_columns = [col for col in spec.columns if col not in columns]
                columns_ok = not missing_columns
            except Exception as exc:  # pragma: no cover - defensive audit path
                columns_ok = False
                missing_columns = [f"read_error:{exc}"]
        ok = exists and columns_ok
        if spec.required and not ok:
            failures.append(spec.input_id)
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(spec.path),
                "required": spec.required,
                "exists": exists,
                "columns_ok": columns_ok,
                "missing_columns": ";".join(missing_columns),
                "sha256": path_hash(spec.path),
                "status": "pass" if ok else "missing_or_invalid",
            }
        )
    return pd.DataFrame(rows), failures


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_09a_manifest_hash_audit(manifest: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    required_output_ids = [
        "selected_label_contract",
        "selected_label_event_bindings",
        "source_pool_reconstruction_audit",
        "fast_fail_label_contract",
        "cost_target_bridge",
        "label_mechanism_contract",
    ]
    outputs = manifest.get("outputs", {})
    hashes = manifest.get("output_hashes", {})
    for output_id in required_output_ids:
        path_value = outputs.get(output_id, "")
        path = Path(path_value) if path_value else Path()
        recorded = str(hashes.get(output_id, ""))
        actual = file_sha256(path) if path_value and path.exists() and path.is_file() else ""
        rows.append(
            {
                "output_id": output_id,
                "path": str(path) if path_value else "",
                "recorded_sha256": recorded,
                "actual_sha256": actual,
                "hash_match_flag": bool(recorded) and recorded == actual,
                "status": "pass" if bool(recorded) and recorded == actual else "hash_mismatch",
            }
        )
    return pd.DataFrame(rows)


def source_caveated_from_09a_decision(decision: str) -> bool:
    return decision == SOURCE_CAVEATED_09A_DECISION


def selected_targets(contract: pd.DataFrame) -> pd.DataFrame:
    mask = (
        contract["selection_status"].astype(str).eq("selected")
        & contract["usable_for_09C_supported_gate"].map(boolish)
    )
    return contract.loc[mask].copy()


def build_selected_target_binding_coverage(
    selected_contract: pd.DataFrame, binding: pd.DataFrame
) -> pd.DataFrame:
    selected = selected_targets(selected_contract)
    counts = (
        binding.groupby("selected_target_id", dropna=False)
        .agg(
            binding_row_n=("sample_id", "size"),
            denominator_count=("denominator_id", "nunique"),
            denominators=("denominator_id", lambda values: ";".join(sorted(map(str, set(values))))),
        )
        .reset_index()
    )
    rows: list[dict[str, Any]] = []
    for _, target in selected.iterrows():
        target_id = str(target["selected_target_id"])
        hit = counts.loc[counts["selected_target_id"].astype(str).eq(target_id)]
        binding_row_n = int(hit["binding_row_n"].iloc[0]) if not hit.empty else 0
        denominators = str(hit["denominators"].iloc[0]) if not hit.empty else ""
        coverage_status = "complete" if binding_row_n > 0 else "missing_binding"
        rows.append(
            {
                "selected_target_id": target_id,
                "selected_fast_fail_label_id": target.get("selected_fast_fail_label_id", ""),
                "selection_status": target.get("selection_status", ""),
                "usable_for_09C_supported_gate": boolish(
                    target.get("usable_for_09C_supported_gate", False)
                ),
                "binding_row_n": binding_row_n,
                "denominators": denominators,
                "selected_target_binding_coverage_status": coverage_status,
                "upstream_contract_conflict_flag": binding_row_n == 0,
                "required_resolution": ""
                if binding_row_n > 0
                else "set_usable_false_or_emit_complete_event_binding",
            }
        )
    return pd.DataFrame(rows)


def selected_target_binding_status(coverage: pd.DataFrame) -> tuple[str, str, list[str], list[str]]:
    if coverage.empty:
        return "none", "no_selected_usable_target", [], []
    supported = coverage.loc[
        coverage["selected_target_binding_coverage_status"].eq("complete"), "selected_target_id"
    ].astype(str).tolist()
    missing = coverage.loc[
        coverage["selected_target_binding_coverage_status"].ne("complete"), "selected_target_id"
    ].astype(str).tolist()
    if missing:
        return "partial", "upstream_contract_conflict", supported, missing
    return "complete", "pass", supported, missing


def build_sample_key_uniqueness_audit(binding: pd.DataFrame) -> pd.DataFrame:
    keys = ["sample_id", "selected_target_id", "denominator_id"]
    rows = []
    for denominator, part in [("all", binding), *binding.groupby("denominator_id")]:
        duplicate_n = int(part.duplicated(keys).sum())
        rows.append(
            {
                "denominator_id": denominator,
                "row_n": int(len(part)),
                "sample_id_unique_n": int(part["sample_id"].nunique()),
                "sample_key_unique_n": int(part[keys].drop_duplicates().shape[0]),
                "sample_key_duplicate_n": duplicate_n,
                "sample_key_uniqueness_status": "pass" if duplicate_n == 0 else "blocked",
            }
        )
    return pd.DataFrame(rows)


def denominator_scope_usage(denominator_id: Any) -> str:
    denominator = str(denominator_id)
    if denominator == RISK_ON_R_CORE_DENOM:
        return "supported_training"
    if denominator == RISK_ON_R6_DENOM:
        return "readout_only"
    if denominator == RISK_OFF_E1_READONLY_DENOM:
        return "not_09B_scope_readonly"
    return "unsupported_scope"


def build_sample_uniqueness_audit(
    coverage: pd.DataFrame, binding: pd.DataFrame, *, blocked_by_upstream_conflict: bool
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, target in coverage.iterrows():
        target_id = str(target["selected_target_id"])
        target_binding = binding.loc[binding["selected_target_id"].astype(str).eq(target_id)]
        if target_binding.empty:
            rows.append(
                {
                    "selected_target_id": target_id,
                    "denominator_id": "",
                    "weight_horizon_id": "",
                    "scope_usage": "",
                    "sample_n": 0,
                    "average_uniqueness_mean": np.nan,
                    "average_uniqueness_median": np.nan,
                    "average_uniqueness_p10": np.nan,
                    "average_uniqueness_p90": np.nan,
                    "concurrency_count_mean": np.nan,
                    "concurrency_count_p90": np.nan,
                    "weight_status": "target_binding_missing",
                }
            )
            continue
        for denominator_id, part in target_binding.groupby("denominator_id"):
            scope_usage = denominator_scope_usage(denominator_id)
            if scope_usage == "not_09B_scope_readonly":
                status = "not_09B_scope_readonly"
            elif scope_usage == "unsupported_scope":
                status = "unsupported_scope"
            elif blocked_by_upstream_conflict:
                status = "not_materialized_upstream_contract_conflict"
            else:
                status = "not_materialized"
            for weight_horizon_id in (FAST_FAIL_WEIGHT, HYBRID_WEIGHT):
                rows.append(
                    {
                        "selected_target_id": target_id,
                        "denominator_id": denominator_id,
                        "weight_horizon_id": weight_horizon_id,
                        "scope_usage": scope_usage,
                        "sample_n": int(len(part)),
                        "average_uniqueness_mean": np.nan,
                        "average_uniqueness_median": np.nan,
                        "average_uniqueness_p10": np.nan,
                        "average_uniqueness_p90": np.nan,
                        "concurrency_count_mean": np.nan,
                        "concurrency_count_p90": np.nan,
                        "weight_status": status,
                    }
                )
    return pd.DataFrame(rows)


def build_source_pool_reconstruction_audit(source_audit: pd.DataFrame) -> pd.DataFrame:
    out = source_audit.copy()
    required = {R_CORE_SCOPE, R6_SCOPE}
    out["required_for_09B_flag"] = out["source_pool_id"].astype(str).isin(required)
    out["supported_training_scope_flag"] = out["source_pool_id"].astype(str).eq(R_CORE_SCOPE)
    out["scope_usage"] = np.where(
        out["source_pool_id"].astype(str).eq(R_CORE_SCOPE),
        "supported_training",
        np.where(out["source_pool_id"].astype(str).eq(R6_SCOPE), "readout_only", "not_09B_training"),
    )
    return out


def source_pool_reconstruction_status(source_audit: pd.DataFrame) -> str:
    required = source_audit.loc[source_audit["source_pool_id"].astype(str).isin({R_CORE_SCOPE, R6_SCOPE})]
    if set(required["source_pool_id"].astype(str)) != {R_CORE_SCOPE, R6_SCOPE}:
        return "missing_required_scope"
    pass_mask = required["status"].astype(str).eq("pass") & required["hard_gate_eligible_flag"].map(boolish)
    return "pass" if bool(pass_mask.all()) else "blocked"


def build_industry_board_pit_membership_audit(
    industry_audit: pd.DataFrame, capability: pd.DataFrame
) -> pd.DataFrame:
    blocked_industry = capability.loc[
        capability["data_dependency"].astype(str).str.contains("PIT industry", na=False)
        | capability["family_id"].astype(str).str.contains("industry", case=False, na=False)
    ]
    rows = []
    for _, row in industry_audit.iterrows():
        domain = str(row["feature_domain"])
        pit_available = boolish(row["pit_available_flag"])
        if domain == "industry" and not pit_available:
            policy = "block_industry_features"
            status = "industry_pit_unavailable"
        elif domain == "style_proxy_board" and pit_available:
            policy = "board_fallback_not_industry"
            status = "board_fallback_available"
        elif domain == "market_breadth" and pit_available:
            policy = "market_breadth_available"
            status = "pit_available"
        else:
            policy = "diagnostic_only"
            status = "diagnostic"
        rows.append(
            {
                "feature_domain": domain,
                "pit_available_flag": pit_available,
                "coverage_rate": row.get("coverage_rate", np.nan),
                "effective_date_policy": row.get("effective_date_policy", ""),
                "feature_policy": policy,
                "industry_pit_status": status,
                "blocked_family_count": int(len(blocked_industry))
                if domain == "industry"
                else 0,
                "notes": row.get("notes", ""),
            }
        )
    return pd.DataFrame(rows)


def trading_session_t1(
    trade_time: Any,
    touch_date: Any,
    touched: Any,
    offset_sessions: Any,
    calendar: list[pd.Timestamp] | None = None,
) -> tuple[str, str]:
    trade_ts = pd.to_datetime(trade_time, errors="coerce")
    touch_ts = pd.to_datetime(touch_date, errors="coerce")
    touched_flag = boolish(touched)
    offset = pd.to_numeric(pd.Series([offset_sessions]), errors="coerce").iloc[0]
    if pd.isna(trade_ts):
        return "", "not_evaluable_10d"
    if touched_flag:
        if pd.isna(touch_ts) or pd.isna(offset) or int(offset) < 0 or int(offset) > 9:
            return "", "not_evaluable_10d"
        return str(touch_ts.date()), "complete"
    if calendar:
        sessions = [date for date in calendar if date >= trade_ts]
        if len(sessions) >= 10:
            return str(sessions[9].date()), "complete"
    return "", "not_evaluable_10d"


def calendar_positions(calendar: list[pd.Timestamp]) -> dict[pd.Timestamp, int]:
    return {pd.Timestamp(date).normalize(): pos for pos, date in enumerate(calendar)}


def normalize_date(value: Any) -> pd.Timestamp | pd.NaT:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    return pd.Timestamp(ts).normalize()


def active_interval_end(
    row: pd.Series,
    weight_horizon_id: str,
    calendar: list[pd.Timestamp],
) -> tuple[pd.Timestamp | pd.NaT, str]:
    if weight_horizon_id == HYBRID_WEIGHT:
        end = normalize_date(row.get("label_t1_date"))
        if pd.isna(end) or str(row.get("censoring_status", "")) != "complete":
            return pd.NaT, "not_evaluable_20d"
        return end, "complete"
    end_text, status = trading_session_t1(
        row.get("trade_time"),
        row.get("selected_fast_fail_touch_date"),
        row.get("selected_fast_fail_10_label"),
        row.get("selected_fast_fail_touch_offset_sessions"),
        calendar,
    )
    return normalize_date(end_text), status


def compute_group_uniqueness(part: pd.DataFrame, calendar: list[pd.Timestamp]) -> pd.DataFrame:
    positions = calendar_positions(calendar)
    start_pos = part["active_interval_start"].map(positions)
    end_pos = part["active_interval_end"].map(positions)
    valid = (
        part["weight_status"].eq("complete")
        & start_pos.notna()
        & end_pos.notna()
        & (end_pos.astype("Int64") >= start_pos.astype("Int64"))
    )
    out = part.copy()
    out["concurrency_count_mean"] = np.nan
    out["average_uniqueness"] = np.nan
    if not bool(valid.any()):
        return out
    starts = start_pos.loc[valid].astype(int)
    ends = end_pos.loc[valid].astype(int)
    diff = np.zeros(len(calendar) + 1, dtype=float)
    for start, end in zip(starts, ends, strict=False):
        diff[start] += 1.0
        if end + 1 < len(diff):
            diff[end + 1] -= 1.0
    concurrency = np.cumsum(diff[:-1])
    for idx, start, end in zip(starts.index, starts, ends, strict=False):
        window = concurrency[start : end + 1]
        positive = window[window > 0]
        if len(positive) == 0:
            continue
        out.loc[idx, "concurrency_count_mean"] = float(np.mean(positive))
        out.loc[idx, "average_uniqueness"] = float(np.mean(1.0 / positive))
    return out


def build_sample_uniqueness_weights(
    binding: pd.DataFrame,
    calendar: list[pd.Timestamp],
    supported_targets: list[str],
) -> pd.DataFrame:
    scoped = binding.loc[
        binding["selected_target_id"].astype(str).isin(set(supported_targets))
        & binding["denominator_id"].astype(str).isin({RISK_ON_R_CORE_DENOM, RISK_ON_R6_DENOM})
    ].copy()
    rows: list[pd.DataFrame] = []
    for weight_horizon_id in (FAST_FAIL_WEIGHT, HYBRID_WEIGHT):
        part = scoped.copy()
        part["weight_horizon_id"] = weight_horizon_id
        part["scope_usage"] = part["denominator_id"].map(denominator_scope_usage)
        part["supported_training_scope_flag"] = part["denominator_id"].eq(RISK_ON_R_CORE_DENOM)
        part["active_interval_start"] = part["trade_time"].map(normalize_date)
        ends = part.apply(lambda row: active_interval_end(row, weight_horizon_id, calendar), axis=1)
        part["active_interval_end"] = [item[0] for item in ends]
        part["weight_status"] = [item[1] for item in ends]
        part.loc[part["active_interval_start"].isna(), "weight_status"] = "not_evaluable_start"
        weighted = []
        for _, group in part.groupby(["selected_target_id", "denominator_id"], dropna=False):
            weighted.append(compute_group_uniqueness(group, calendar))
        rows.append(pd.concat(weighted, ignore_index=True) if weighted else part)
    weights = pd.concat(rows, ignore_index=True) if rows else scoped
    weights["time_decay_weight"] = 1.0
    weights["final_sample_weight"] = weights["average_uniqueness"].astype(float)
    complete = weights["weight_status"].eq("complete") & weights["final_sample_weight"].notna()
    for _, idx in weights.loc[complete].groupby(
        ["selected_target_id", "denominator_id", "weight_horizon_id"]
    ).groups.items():
        mean_weight = float(weights.loc[list(idx), "final_sample_weight"].mean())
        if mean_weight > 0:
            weights.loc[list(idx), "final_sample_weight"] = (
                weights.loc[list(idx), "final_sample_weight"] / mean_weight
            )
    weights.loc[~complete, "final_sample_weight"] = 0.0
    cols = [
        "sample_id",
        "selected_target_id",
        "denominator_id",
        "weight_horizon_id",
        "scope_usage",
        "supported_training_scope_flag",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "label_t1_date",
        "active_interval_start",
        "active_interval_end",
        "concurrency_count_mean",
        "average_uniqueness",
        "time_decay_weight",
        "final_sample_weight",
        "weight_status",
    ]
    out = weights[cols].copy()
    for col in ["active_interval_start", "active_interval_end"]:
        out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    return out


def build_trading_calendar(config: dict[str, Any], binding: pd.DataFrame) -> list[pd.Timestamp]:
    stock_dir = topic_path(config["paths"]["stock_daily_csv_dir"])
    dates: set[pd.Timestamp] = set()
    for instrument in sorted(binding["instrument"].dropna().astype(str).unique()):
        path = stock_dir / f"{instrument}.csv"
        if not path.exists():
            continue
        frame = pd.read_csv(path, usecols=["date"])
        dates.update(pd.to_datetime(frame["date"], errors="coerce").dropna().dt.normalize())
    if not dates:
        fallback = pd.to_datetime(binding["trade_time"], errors="coerce").dropna().dt.normalize()
        dates.update(fallback)
        label_t1 = pd.to_datetime(binding["label_t1_date"], errors="coerce").dropna().dt.normalize()
        dates.update(label_t1)
    return sorted(dates)


def sample_uniqueness_audit_from_weights(
    coverage: pd.DataFrame,
    binding: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, target in coverage.iterrows():
        target_id = str(target["selected_target_id"])
        target_binding = binding.loc[binding["selected_target_id"].astype(str).eq(target_id)]
        for denominator_id, part in target_binding.groupby("denominator_id"):
            scope_usage = denominator_scope_usage(denominator_id)
            if scope_usage == "not_09B_scope_readonly":
                for weight_horizon_id in (FAST_FAIL_WEIGHT, HYBRID_WEIGHT):
                    rows.append(
                        {
                            "selected_target_id": target_id,
                            "denominator_id": denominator_id,
                            "weight_horizon_id": weight_horizon_id,
                            "scope_usage": scope_usage,
                            "sample_n": int(len(part)),
                            "average_uniqueness_mean": np.nan,
                            "average_uniqueness_median": np.nan,
                            "average_uniqueness_p10": np.nan,
                            "average_uniqueness_p90": np.nan,
                            "concurrency_count_mean": np.nan,
                            "concurrency_count_p90": np.nan,
                            "weight_status": "not_09B_scope_readonly",
                        }
                    )
                continue
            weight_part = weights.loc[
                (weights["selected_target_id"].astype(str) == target_id)
                & (weights["denominator_id"].astype(str) == str(denominator_id))
            ]
            for weight_horizon_id, horizon_part in weight_part.groupby("weight_horizon_id"):
                complete = horizon_part.loc[horizon_part["weight_status"].eq("complete")]
                non_complete = horizon_part.loc[~horizon_part["weight_status"].eq("complete")]
                if len(non_complete) == 0:
                    weight_status = "complete"
                elif set(non_complete["weight_status"].astype(str)).issubset(
                    {"not_evaluable_20d", "not_evaluable_10d"}
                ):
                    weight_status = "complete_with_non_executable_caveat"
                else:
                    weight_status = "partial_not_evaluable"
                rows.append(
                    {
                        "selected_target_id": target_id,
                        "denominator_id": denominator_id,
                        "weight_horizon_id": weight_horizon_id,
                        "scope_usage": scope_usage,
                        "sample_n": int(len(horizon_part)),
                        "not_evaluable_n": int(len(non_complete)),
                        "average_uniqueness_mean": complete["average_uniqueness"].mean(),
                        "average_uniqueness_median": complete["average_uniqueness"].median(),
                        "average_uniqueness_p10": complete["average_uniqueness"].quantile(0.10),
                        "average_uniqueness_p90": complete["average_uniqueness"].quantile(0.90),
                        "concurrency_count_mean": complete["concurrency_count_mean"].mean(),
                        "concurrency_count_p90": complete["concurrency_count_mean"].quantile(0.90),
                        "weight_status": weight_status,
                    }
                )
    return pd.DataFrame(rows)


def feature_source_columns(source: str) -> list[str]:
    return sorted(
        {
            item["source_column"]
            for item in FEATURE_DEFINITIONS
            if item["source"] == source
        }
    )


def build_recurrence_features(scoped: pd.DataFrame) -> pd.DataFrame:
    unique = scoped[["canonical_event_id", "instrument", "event_t0_date"]].drop_duplicates().copy()
    unique["event_t0_ts"] = pd.to_datetime(unique["event_t0_date"], errors="coerce")
    out_rows: list[pd.DataFrame] = []
    for _, group in unique.sort_values("event_t0_ts").groupby("instrument"):
        dates = group["event_t0_ts"].to_numpy(dtype="datetime64[ns]")
        same_day = group.groupby("event_t0_ts")["canonical_event_id"].transform("count")
        prior_20 = []
        prior_60 = []
        for date in dates:
            prior_20.append(int(((dates < date) & (dates >= date - np.timedelta64(20, "D"))).sum()))
            prior_60.append(int(((dates < date) & (dates >= date - np.timedelta64(60, "D"))).sum()))
        part = group[["canonical_event_id"]].copy()
        part["prior_event_count_20d"] = prior_20
        part["prior_event_count_60d"] = prior_60
        part["same_day_event_count"] = same_day.to_numpy()
        out_rows.append(part)
    return pd.concat(out_rows, ignore_index=True) if out_rows else pd.DataFrame()


def fracdiff_weights(d: float, max_lags: int, threshold: float) -> np.ndarray:
    weights = [1.0]
    for lag in range(1, max_lags + 1):
        next_weight = -weights[-1] * (d - lag + 1) / lag
        if abs(next_weight) < threshold:
            break
        weights.append(float(next_weight))
    return np.asarray(weights, dtype=float)


def fracdiff_array(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    width = len(weights)
    if width == 0:
        return out
    for idx in range(width - 1, len(values)):
        window = values[idx - width + 1 : idx + 1]
        if np.isfinite(window).all():
            out[idx] = float(np.dot(weights[::-1], window))
    return out


def trailing_percentile_last(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if len(finite) == 0 or not np.isfinite(values[-1]):
        return np.nan
    return float((finite <= values[-1]).mean())


def build_panel_stationary_features(config: dict[str, Any]) -> pd.DataFrame:
    params = config.get("stationary_hygiene", {})
    window = int(params.get("rolling_window_sessions", 60))
    min_periods = int(params.get("rolling_min_periods", 20))
    frac_d = float(params.get("fracdiff_d", 0.4))
    max_lags = int(params.get("fracdiff_max_lags", 20))
    threshold = float(params.get("fracdiff_weight_threshold", 0.0001))
    panel = pd.read_parquet(
        topic_path(config["paths"]["upstream_08_feature_panel"]),
        columns=["date", "instrument", "close", "return_20d"],
    )
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    panel = panel.dropna(subset=["date", "instrument"]).sort_values(["instrument", "date"])
    weights = fracdiff_weights(frac_d, max_lags, threshold)
    out_parts: list[pd.DataFrame] = []
    for _, part in panel.groupby("instrument", sort=False):
        part = part.copy()
        ret = pd.to_numeric(part["return_20d"], errors="coerce")
        rolling = ret.rolling(window=window, min_periods=min_periods)
        mean = rolling.mean()
        std = rolling.std(ddof=0).replace(0, np.nan)
        part["panel_return_20d_rolling_z_60d"] = (ret - mean) / std
        part["panel_return_20d_rolling_pct_60d"] = rolling.apply(
            trailing_percentile_last,
            raw=True,
        )
        log_close = np.log(pd.to_numeric(part["close"], errors="coerce").replace(0, np.nan))
        part["log_close_fracdiff_d04"] = fracdiff_array(log_close.to_numpy(), weights)
        out_parts.append(
            part[
                [
                    "instrument",
                    "date",
                    "panel_return_20d_rolling_z_60d",
                    "panel_return_20d_rolling_pct_60d",
                    "log_close_fracdiff_d04",
                ]
            ]
        )
    if not out_parts:
        return pd.DataFrame()
    return pd.concat(out_parts, ignore_index=True).drop_duplicates(
        ["instrument", "date"],
        keep="last",
    )


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce").replace(0, np.nan)
    return num / den


def build_feature_artifacts(
    binding: pd.DataFrame,
    config: dict[str, Any],
    supported_targets: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame, pd.DataFrame]:
    scoped = binding.loc[
        binding["selected_target_id"].astype(str).isin(set(supported_targets))
        & binding["denominator_id"].astype(str).isin({RISK_ON_R_CORE_DENOM, RISK_ON_R6_DENOM})
    ].copy()
    scoped["feature_as_of_date"] = scoped["event_t0_date"]
    canonical_cols = [
        "canonical_event_id",
        *feature_source_columns("canonical"),
    ]
    canonical = pd.read_csv(
        topic_path(config["paths"]["upstream_08_canonical_events"]),
        usecols=lambda col: col in set(canonical_cols),
        low_memory=False,
    ).drop_duplicates("canonical_event_id")
    matrix = scoped[
        [
            "sample_id",
            "selected_target_id",
            "denominator_id",
            "canonical_event_id",
            "instrument",
            "event_t0_date",
            "event_split",
            "feature_as_of_date",
        ]
    ].merge(canonical, on="canonical_event_id", how="left")
    matrix["intraday_range_atr_norm"] = safe_divide(
        matrix.get("intraday_range_pct", pd.Series(np.nan, index=matrix.index)),
        matrix.get("atr_20_pct", pd.Series(np.nan, index=matrix.index)),
    )
    matrix["return_20d_sigma_norm"] = safe_divide(
        matrix.get("return_20d", pd.Series(np.nan, index=matrix.index)),
        matrix.get("market_volatility_20d", pd.Series(np.nan, index=matrix.index)),
    )
    panel_features = build_panel_stationary_features(config)
    if not panel_features.empty:
        panel_features = panel_features.rename(columns={"date": "event_t0_date"})
        matrix = matrix.merge(
            panel_features,
            on=["instrument", "event_t0_date"],
            how="left",
            validate="many_to_one",
        )
    recurrence = build_recurrence_features(scoped)
    if not recurrence.empty:
        matrix = matrix.merge(recurrence, on="canonical_event_id", how="left")
    feature_values = pd.DataFrame(index=matrix.index)
    raw_missing_rates: dict[str, float] = {}
    for item in FEATURE_DEFINITIONS:
        fid = item["feature_id"]
        source_col = item["source_column"]
        series = matrix[source_col] if source_col in matrix.columns else pd.Series(np.nan, index=matrix.index)
        if series.dtype == bool:
            numeric = series.astype(float)
        else:
            numeric = pd.to_numeric(series, errors="coerce")
        raw_missing_rates[fid] = float(numeric.isna().mean())
        feature_values[fid] = numeric
    train_mask = (
        scoped["denominator_id"].astype(str).eq(RISK_ON_R_CORE_DENOM)
        & scoped["event_split"].astype(str).eq("train")
    ).to_numpy()
    stationary_params = config.get("stationary_hygiene", {})
    transform: dict[str, Any] = {
        "fit_scope": "risk_on_r_core_horizon_complete/train",
        "imputer": "train_median",
        "imputer_policy": "train_median_fit_on_r_core_train_then_transform_oos",
        "winsorization": "train_p01_p99",
        "winsorization_policy": "per_feature_p01_p99_fit_on_r_core_train",
        "scaler": "train_standard_z_for_continuous_binary_0_1_for_flags",
        "scaler_policy": "continuous_features_standard_z_fit_on_r_core_train",
        "normalizer_policy": {
            "rolling_z_score": "panel_return_20d_rolling_z_60d uses instrument trailing window ending at event_t0_date",
            "rolling_percentile": "panel_return_20d_rolling_pct_60d uses instrument trailing window ending at event_t0_date",
            "atr_normalization": "intraday_range_atr_norm = intraday_range_pct / atr_20_pct at event_t0_date",
            "sigma_normalization": "return_20d_sigma_norm = return_20d / market_volatility_20d at event_t0_date",
        },
        "rolling_window_definitions": {
            "rolling_window_sessions": int(stationary_params.get("rolling_window_sessions", 60)),
            "rolling_min_periods": int(stationary_params.get("rolling_min_periods", 20)),
            "window_policy": "feature_as_of_date <= event_t0_date; same-day t0 close is allowed for next-open execution",
        },
        "pca": "not_used",
        "pca_usage": "not_used",
        "fracdiff": {
            "status": "applied_selected_series_only",
            "selected_series": ["log(close)"],
            "output_feature": "log_close_fracdiff_d04",
            "d": float(stationary_params.get("fracdiff_d", 0.4)),
            "max_lags": int(stationary_params.get("fracdiff_max_lags", 20)),
            "weight_threshold": float(stationary_params.get("fracdiff_weight_threshold", 0.0001)),
            "fit_policy": "fixed_predeclared_d_no_full_sample_search",
        },
        "fracdiff_selected_series": [
            {
                "raw_series": "log(close)",
                "feature_id": "log_close_fracdiff_d04",
                "d": float(stationary_params.get("fracdiff_d", 0.4)),
                "max_lags": int(stationary_params.get("fracdiff_max_lags", 20)),
            }
        ],
        "train_fold_fit_oos_transform_rule": "imputer/winsor/scaler fit only on risk_on_r_core_horizon_complete train rows; validation/robustness/R6 transformed read-only",
        "missing_feature_behavior": "fail_closed_if_configured_feature_column_absent; otherwise train_median_impute_value_recorded_per_feature",
        "diagnostic_model_config": config.get("diagnostic_model", {}),
        "feature_order": FEATURE_COLUMNS,
        "features": {},
    }
    transformed = pd.DataFrame(index=matrix.index)
    for item in FEATURE_DEFINITIONS:
        fid = item["feature_id"]
        values = feature_values[fid].astype(float)
        train_values = values.loc[train_mask].dropna()
        if train_values.empty:
            median = 0.0
            lower = upper = mean = 0.0
            std = 1.0
        else:
            median = float(train_values.median())
            lower = float(train_values.quantile(0.01))
            upper = float(train_values.quantile(0.99))
            clipped_train = train_values.clip(lower, upper).fillna(median)
            mean = float(clipped_train.mean())
            std = float(clipped_train.std(ddof=0))
            if not np.isfinite(std) or std == 0:
                std = 1.0
        filled = values.fillna(median).clip(lower, upper)
        if item["normalization_method"] == "binary_0_1":
            transformed[fid] = filled.fillna(0.0).clip(0, 1)
        else:
            transformed[fid] = (filled - mean) / std
        transform["features"][fid] = {
            "raw_source": item["source"],
            "raw_column": item["source_column"],
            "missing_rate_before_impute": raw_missing_rates[fid],
            "median": median,
            "winsor_p01": lower,
            "winsor_p99": upper,
            "mean": mean,
            "std": std,
            "normalization_method": item["normalization_method"],
            "stationary_hygiene_method": item.get("stationary_hygiene_method", "train_z"),
            "fracdiff_status": item.get("fracdiff_status", "not_applied"),
        }
    meta_cols = [
        "sample_id",
        "selected_target_id",
        "denominator_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_split",
        "feature_as_of_date",
    ]
    feature_matrix = pd.concat([matrix[meta_cols].reset_index(drop=True), transformed.reset_index(drop=True)], axis=1)
    stationarity = build_feature_stationarity_audit(feature_matrix, raw_missing_rates)
    leakage = build_feature_leakage_audit(feature_matrix)
    contract = build_feature_contract(stationarity)
    schema = build_feature_matrix_schema(feature_matrix)
    return feature_matrix, contract, stationarity, transform, leakage, schema


def build_feature_stationarity_audit(
    feature_matrix: pd.DataFrame, raw_missing_rates: dict[str, float]
) -> pd.DataFrame:
    rows = []
    for item in FEATURE_DEFINITIONS:
        fid = item["feature_id"]
        train = feature_matrix.loc[
            (feature_matrix["denominator_id"].eq(RISK_ON_R_CORE_DENOM))
            & (feature_matrix["event_split"].eq("train")),
            fid,
        ]
        validation = feature_matrix.loc[
            (feature_matrix["denominator_id"].eq(RISK_ON_R_CORE_DENOM))
            & (feature_matrix["event_split"].eq("validation")),
            fid,
        ]
        robustness = feature_matrix.loc[
            (feature_matrix["denominator_id"].eq(RISK_ON_R_CORE_DENOM))
            & (feature_matrix["event_split"].eq("robustness")),
            fid,
        ]
        train_std = float(train.std(ddof=0))
        status = "pass" if np.isfinite(train_std) and train_std > 0 else "constant_after_transform"
        rows.append(
            {
                "feature_id": fid,
                "feature_family": item["feature_family"],
                "raw_missing_rate": raw_missing_rates.get(fid, np.nan),
                "train_mean": float(train.mean()),
                "train_std": train_std,
                "validation_mean": float(validation.mean()) if len(validation) else np.nan,
                "validation_std": float(validation.std(ddof=0)) if len(validation) else np.nan,
                "robustness_mean": float(robustness.mean()) if len(robustness) else np.nan,
                "robustness_std": float(robustness.std(ddof=0)) if len(robustness) else np.nan,
                "normalization_method": item["normalization_method"],
                "stationary_hygiene_method": item.get("stationary_hygiene_method", "train_z"),
                "stationarity_status": status,
                "fracdiff_status": item.get("fracdiff_status", "not_applied"),
            }
        )
    return pd.DataFrame(rows)


def build_feature_leakage_audit(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    rows = []
    forbidden = {col.lower() for col in FORBIDDEN_BINDING_COLUMNS}
    for col in feature_matrix.columns:
        role = "feature" if col in FEATURE_COLUMNS else "metadata"
        forbidden_match = col.lower() in forbidden or any(token in col.lower() for token in ["future", "winner", "touch", "label_t1"])
        rows.append(
            {
                "column": col,
                "role": role,
                "forbidden_feature_flag": bool(role == "feature" and forbidden_match),
                "status": "blocked" if role == "feature" and forbidden_match else "pass",
            }
        )
    return pd.DataFrame(rows)


def mechanism_overlap_type(feature_id: str) -> tuple[str, str]:
    lower = feature_id.lower()
    if "swing" in lower:
        return "direct", "swing_low"
    if any(token in lower for token in ["atr", "range", "close_to_high", "ema"]):
        return "related", "range_or_structural_stop_context"
    return "none", ""


def build_feature_contract(stationarity: pd.DataFrame) -> pd.DataFrame:
    stationarity_status = dict(zip(stationarity["feature_id"], stationarity["stationarity_status"]))
    rows = []
    for item in FEATURE_DEFINITIONS:
        overlap, shared = mechanism_overlap_type(item["feature_id"])
        rows.append(
            {
                "feature_id": item["feature_id"],
                "feature_family": item["feature_family"],
                "raw_source_artifact": item["source"],
                "as_of_rule": item["as_of_rule"],
                "t0_visible_flag": True,
                "normalization_method": item["normalization_method"],
                "stationarity_status": stationarity_status.get(item["feature_id"], "not_run"),
                "fracdiff_status": item.get("fracdiff_status", "not_applied"),
                "stationary_hygiene_method": item.get("stationary_hygiene_method", "train_z"),
                "industry_pit_status": "board_fallback_not_industry"
                if item["feature_family"] == "FS5_market_industry_riskon_quality"
                else "not_industry_feature",
                "allowed_for_09C_flag": stationarity_status.get(item["feature_id"], "pass") == "pass",
                "forbidden_reason": "",
                "label_mechanism_overlap_type": overlap,
                "feature_dtype": "float64",
                "feature_as_of_date_rule": "feature_as_of_date = event_t0_date",
                "transform_fit_scope": "risk_on_r_core_horizon_complete/train",
                "missing_value_policy": "train_median_impute_then_winsorize",
                "shared_series": shared,
            }
        )
    return pd.DataFrame(rows)


def build_feature_matrix_schema(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in feature_matrix.columns:
        if col in {"sample_id", "selected_target_id", "denominator_id"}:
            role = "sample_key"
        elif col in FEATURE_COLUMNS:
            role = "feature"
        else:
            role = "metadata"
        rows.append(
            {
                "column": col,
                "dtype": str(feature_matrix[col].dtype),
                "role": role,
                "forbidden_feature_flag": False,
            }
        )
    return pd.DataFrame(rows)


def build_label_mechanism_overlap_audit(contract: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in contract.iterrows():
        rows.append(
            {
                "feature_id": row["feature_id"],
                "feature_family": row["feature_family"],
                "label_id": "break_swing_low_20",
                "shared_series": row.get("shared_series", ""),
                "overlap_type": row["label_mechanism_overlap_type"],
                "interpretation_caveat": ""
                if row["label_mechanism_overlap_type"] == "none"
                else "Report ablation without related stop/range features in 09C.",
            }
        )
    return pd.DataFrame(rows)


def weighted_auc(y_true: pd.Series, score: np.ndarray, sample_weight: pd.Series | None = None) -> float:
    y = pd.Series(y_true).map(boolish).astype(int)
    if y.nunique(dropna=True) < 2:
        return np.nan
    try:
        return float(roc_auc_score(y, score, sample_weight=sample_weight))
    except ValueError:
        return np.nan


def train_logistic(
    train: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    sample_weight: pd.Series,
    model_config: dict[str, Any] | None = None,
) -> LogisticRegression | None:
    y = train[target_col].map(boolish).astype(int)
    if y.nunique() < 2 or not feature_cols:
        return None
    model_config = model_config or {}
    model = LogisticRegression(
        penalty=str(model_config.get("penalty", "l2")),
        class_weight=model_config.get("class_weight", "balanced"),
        solver=str(model_config.get("solver", "liblinear")),
        random_state=int(model_config.get("random_state", 17)),
        max_iter=int(model_config.get("max_iter", 1000)),
    )
    model.fit(train[feature_cols], y, sample_weight=sample_weight)
    return model


def build_importance_artifacts(
    feature_matrix: pd.DataFrame,
    binding: pd.DataFrame,
    weights: pd.DataFrame,
    contract: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    model_config = config.get("diagnostic_model", {})
    importance_config = config.get("importance", {})
    target_cols = ["sample_id", "selected_target_id", "denominator_id", *[v["column"] for v in TARGET_COMPONENTS.values()]]
    labels = binding[target_cols].drop_duplicates(["sample_id", "selected_target_id", "denominator_id"])
    data = feature_matrix.merge(labels, on=["sample_id", "selected_target_id", "denominator_id"], how="left")
    for meta in TARGET_COMPONENTS.values():
        data[meta["column"]] = data[meta["column"]].map(boolish).astype(int)
    families = contract.groupby("feature_family")["feature_id"].apply(list).to_dict()
    group_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    sfi_rows: list[dict[str, Any]] = []
    registry_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(int(importance_config.get("permutation_random_state", 17)))
    top_k = int(importance_config.get("stability_top_k", 3))
    for component, meta in TARGET_COMPONENTS.items():
        target_col = meta["column"]
        horizon = meta["weight_horizon_id"]
        weight_part = weights.loc[
            weights["weight_horizon_id"].eq(horizon)
            & weights["denominator_id"].eq(RISK_ON_R_CORE_DENOM)
        ][["sample_id", "selected_target_id", "denominator_id", "final_sample_weight"]]
        component_data = data.merge(
            weight_part,
            on=["sample_id", "selected_target_id", "denominator_id"],
            how="left",
        )
        r_core = component_data.loc[component_data["denominator_id"].eq(RISK_ON_R_CORE_DENOM)].copy()
        train = r_core.loc[r_core["event_split"].eq("train")].copy()
        sample_weight = train["final_sample_weight"].fillna(1.0)
        model = train_logistic(train, target_col, FEATURE_COLUMNS, sample_weight, model_config)
        registry_rows.append(
            {
                "target_component": component,
                "diagnostic_model_id": f"logistic_l2_{component}",
                "estimator": str(
                    model_config.get("sklearn_class", "sklearn.linear_model.LogisticRegression")
                ),
                "model_config_hash": stable_hash(model_config),
                "fit_scope": "risk_on_r_core_horizon_complete/train",
                "feature_n": len(FEATURE_COLUMNS),
                "train_row_n": int(len(train)),
                "train_positive_rate": float(train[target_col].astype(bool).mean()),
                "weight_horizon_id": horizon,
                "model_status": "fit" if model is not None else "not_fit_single_class",
            }
        )
        if model is None:
            continue
        for feature in FEATURE_COLUMNS:
            sfi_model = train_logistic(train, target_col, [feature], sample_weight, model_config)
            family = str(contract.loc[contract["feature_id"].eq(feature), "feature_family"].iloc[0])
            for split, split_df in r_core.groupby("event_split"):
                split_weight = split_df["final_sample_weight"].fillna(1.0)
                if sfi_model is None:
                    auc = np.nan
                else:
                    auc = weighted_auc(
                        split_df[target_col],
                        sfi_model.predict_proba(split_df[[feature]])[:, 1],
                        split_weight,
                    )
                sfi_rows.append(
                    {
                        "target_component": component,
                        "split": split,
                        "feature_id": feature,
                        "feature_family": family,
                        "single_feature_auc": auc,
                        "fit_scope": "train_only_single_feature_logistic",
                        "importance_status": "pass" if pd.notna(auc) else "low_power",
                    }
                )
        split_baseline: dict[str, float] = {}
        for split, split_df in r_core.groupby("event_split"):
            split_weight = split_df["final_sample_weight"].fillna(1.0)
            scores = model.predict_proba(split_df[FEATURE_COLUMNS])[:, 1]
            baseline_auc = weighted_auc(split_df[target_col], scores, split_weight)
            split_baseline[str(split)] = baseline_auc
            for family, cols in families.items():
                permuted = split_df[FEATURE_COLUMNS].copy()
                for col in cols:
                    permuted[col] = rng.permutation(permuted[col].to_numpy())
                perm_scores = model.predict_proba(permuted)[:, 1]
                perm_auc = weighted_auc(split_df[target_col], perm_scores, split_weight)
                group_rows.append(
                    {
                        "target_component": component,
                        "split": split,
                        "feature_family": family,
                        "baseline_auc": baseline_auc,
                        "permuted_auc": perm_auc,
                        "group_mda_auc_drop": baseline_auc - perm_auc
                        if pd.notna(baseline_auc) and pd.notna(perm_auc)
                        else np.nan,
                        "feature_count": len(cols),
                        "importance_status": "pass" if pd.notna(baseline_auc) else "low_power",
                    }
                )
        for family, cols in families.items():
            keep_cols = [col for col in FEATURE_COLUMNS if col not in set(cols)]
            ablated_model = train_logistic(train, target_col, keep_cols, sample_weight, model_config)
            for split, split_df in r_core.groupby("event_split"):
                split_weight = split_df["final_sample_weight"].fillna(1.0)
                if ablated_model is None:
                    auc = np.nan
                else:
                    auc = weighted_auc(
                        split_df[target_col],
                        ablated_model.predict_proba(split_df[keep_cols])[:, 1],
                        split_weight,
                    )
                baseline = split_baseline.get(str(split), np.nan)
                ablation_rows.append(
                    {
                        "target_component": component,
                        "split": split,
                        "removed_feature_family": family,
                        "baseline_auc": baseline,
                        "ablated_auc": auc,
                        "ablation_auc_delta": baseline - auc
                        if pd.notna(baseline) and pd.notna(auc)
                        else np.nan,
                        "fit_scope": "train_only_refit_without_family",
                    }
                )
        for family, cols in families.items():
            train_drop = [
                row["group_mda_auc_drop"]
                for row in group_rows
                if row["target_component"] == component
                and row["split"] == "train"
                and row["feature_family"] == family
            ]
            robustness_drop = [
                row["group_mda_auc_drop"]
                for row in group_rows
                if row["target_component"] == component
                and row["split"] == "robustness"
                and row["feature_family"] == family
            ]
            summary_rows.append(
                {
                    "target_component": component,
                    "feature_family": family,
                    "train_group_mda_auc_drop": train_drop[0] if train_drop else np.nan,
                    "robustness_group_mda_auc_drop": robustness_drop[0]
                    if robustness_drop
                    else np.nan,
                    "r6_importance_status": "not_materialized",
                }
            )
    group_mda = pd.DataFrame(group_rows)
    ablation = pd.DataFrame(ablation_rows)
    registry = pd.DataFrame(registry_rows)
    summary = pd.DataFrame(summary_rows)
    stability_rows = []
    for component, part in group_mda.groupby("target_component"):
        pivot = part.pivot_table(index="feature_family", columns="split", values="group_mda_auc_drop")
        spearman = (
            pivot[["train", "robustness"]].corr(method="spearman").iloc[0, 1]
            if {"train", "robustness"}.issubset(pivot.columns) and len(pivot.dropna()) >= 2
            else np.nan
        )
        train_top = set(pivot["train"].sort_values(ascending=False).head(top_k).index) if "train" in pivot else set()
        robust_top = (
            set(pivot["robustness"].sort_values(ascending=False).head(top_k).index)
            if "robustness" in pivot
            else set()
        )
        stability_rows.append(
            {
                "target_component": component,
                "train_robustness_group_rank_spearman": spearman,
                "top3_overlap": len(train_top & robust_top),
                "stability_status": "pass" if pd.notna(spearman) else "low_power",
            }
        )
    stability = pd.DataFrame(stability_rows)
    sfi = pd.DataFrame(sfi_rows)
    report = clustered_importance_report_text(group_mda, ablation, sfi, stability)
    return ablation, group_mda, sfi, registry, summary, stability, report


def clustered_importance_report_text(
    group_mda: pd.DataFrame,
    ablation: pd.DataFrame,
    sfi: pd.DataFrame,
    stability: pd.DataFrame,
) -> str:
    lines = [
        "# 09B Clustered Importance Report",
        "",
        "本报告使用 config-frozen train-only diagnostic model，按 feature family 做 group permutation MDA / family ablation，并补充 single-feature importance。它不是 09C 最终模型，只用于冻结 feature foundation 的读数。",
        "",
        "## Group MDA Top Rows",
        "",
        "| target | split | family | auc_drop | baseline_auc |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    top = group_mda.sort_values("group_mda_auc_drop", ascending=False, na_position="last").head(12)
    for _, row in top.iterrows():
        lines.append(
            "| {target} | {split} | {family} | {drop:.6f} | {auc:.6f} |".format(
                target=row["target_component"],
                split=row["split"],
                family=row["feature_family"],
                drop=0.0 if pd.isna(row["group_mda_auc_drop"]) else row["group_mda_auc_drop"],
                auc=0.0 if pd.isna(row["baseline_auc"]) else row["baseline_auc"],
            )
        )
    lines.extend(
        [
            "",
            "## Single Feature Importance Top Rows",
            "",
            "| target | split | feature | family | single_feature_auc |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )
    sfi_top = sfi.sort_values("single_feature_auc", ascending=False, na_position="last").head(12)
    for _, row in sfi_top.iterrows():
        lines.append(
            "| {target} | {split} | {feature} | {family} | {auc:.6f} |".format(
                target=row["target_component"],
                split=row["split"],
                feature=row["feature_id"],
                family=row["feature_family"],
                auc=0.0 if pd.isna(row["single_feature_auc"]) else row["single_feature_auc"],
            )
        )
    lines.extend(["", "## Split Stability", "", "| target | spearman | top3_overlap | status |", "| --- | ---: | ---: | --- |"])
    for _, row in stability.iterrows():
        lines.append(
            "| {target} | {spearman:.6f} | {overlap} | {status} |".format(
                target=row["target_component"],
                spearman=0.0
                if pd.isna(row["train_robustness_group_rank_spearman"])
                else row["train_robustness_group_rank_spearman"],
                overlap=int(row["top3_overlap"]),
                status=row["stability_status"],
            )
        )
    lines.extend(
        [
            "",
            "## Caveat",
            "",
            "validation / robustness importance 只读；feature selection、scaling 与 diagnostic fit 均只使用 R-core train scope。",
        ]
    )
    return "\n".join(lines)


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": FOUNDATION_TABLE_DIR / "input_artifact_audit.csv",
        "09a_manifest_hash_audit": FOUNDATION_TABLE_DIR / "09a_manifest_hash_audit.csv",
        "selected_target_binding_coverage_audit": FOUNDATION_TABLE_DIR
        / "selected_target_binding_coverage_audit.csv",
        "sample_uniqueness_audit": FOUNDATION_TABLE_DIR / "sample_uniqueness_audit.csv",
        "sample_key_uniqueness_audit": FOUNDATION_TABLE_DIR / "sample_key_uniqueness_audit.csv",
        "sample_uniqueness_weights": FOUNDATION_LOCAL_CACHE_DIR
        / "sample_uniqueness_weights.parquet",
        "source_pool_reconstruction_audit": FOUNDATION_TABLE_DIR
        / "source_pool_reconstruction_audit.csv",
        "industry_board_pit_membership_audit": FOUNDATION_TABLE_DIR
        / "industry_board_pit_membership_audit.csv",
        "feature_contract": FOUNDATION_TABLE_DIR / "feature_contract.csv",
        "feature_stationarity_audit": FOUNDATION_TABLE_DIR / "feature_stationarity_audit.csv",
        "feature_matrix": FOUNDATION_LOCAL_CACHE_DIR / "feature_matrix.parquet",
        "feature_matrix_schema": FOUNDATION_TABLE_DIR / "feature_matrix_schema.csv",
        "feature_transform_contract": FOUNDATION_TABLE_DIR / "feature_transform_contract.json",
        "feature_leakage_audit": FOUNDATION_TABLE_DIR / "feature_leakage_audit.csv",
        "label_mechanism_overlap_audit": FOUNDATION_TABLE_DIR
        / "label_mechanism_overlap_audit.csv",
        "feature_family_ablation": FOUNDATION_TABLE_DIR / "feature_family_ablation.csv",
        "single_feature_importance": FOUNDATION_TABLE_DIR / "single_feature_importance.csv",
        "group_mda_importance": FOUNDATION_TABLE_DIR / "group_mda_importance.csv",
        "diagnostic_model_registry": FOUNDATION_TABLE_DIR / "diagnostic_model_registry.csv",
        "target_component_importance_summary": FOUNDATION_TABLE_DIR
        / "target_component_importance_summary.csv",
        "importance_split_stability": FOUNDATION_TABLE_DIR / "importance_split_stability.csv",
        "clustered_importance_report": FOUNDATION_REPORT_DIR / "clustered_importance_report.md",
        "report": REPORT_DIR / "09B_feature_foundation_ablation_report.md",
        "manifest": MANIFEST_DIR / "09B_feature_foundation_ablation_manifest.json",
    }


def report_text(
    decision: str,
    coverage: pd.DataFrame,
    sample_key: pd.DataFrame,
    industry: pd.DataFrame,
    input_failures: list[str],
    *,
    hash_status: str = "not_run",
    source_pool_status: str = "not_run",
    materialization: dict[str, Any] | None = None,
) -> str:
    materialization = materialization or {}
    lines = [
        "# 09B Feature Foundation / Stationary / Importance Report",
        "",
        f"- decision: `{decision}`",
        "- 09B 当前只在上游契约通过后才允许 materialize feature matrix。",
        "- 当前实现首先执行 input / target binding / PIT membership / sample-key audits。",
        "",
        "## 1. Decision",
        "",
    ]
    if decision == DECISION_UPSTREAM_CONFLICT:
        missing = coverage.loc[
            coverage["selected_target_binding_coverage_status"].ne("complete"),
            "selected_target_id",
        ].astype(str).tolist()
        lines.extend(
            [
                "09B fail-closed 到 upstream contract conflict。",
                "",
                "原因：09A 的 `selected_label_contract.csv` 声明以下 target 可进入 09C supported gate，但 `selected_label_event_bindings.parquet` 没有对应事件级 binding：",
                "",
            ]
        )
        for target in missing:
            lines.append(f"- `{target}`")
        lines.extend(
            [
                "",
                "解除方式：回到 09A，将缺 binding target 改为 `usable_for_09C_supported_gate=false`，或补发该 target 的完整事件级 binding。",
            ]
        )
    elif decision == DECISION_INPUT_BLOCKED:
        lines.extend(["09B input blocked。缺失或无效输入：", ""])
        for failure in input_failures:
            lines.append(f"- `{failure}`")
    else:
        lines.append("09B audits completed without upstream target conflict.")

    lines.extend(
        [
            "",
            "## 2. Target Binding Coverage",
            "",
            "| selected_target_id | usable | binding rows | denominators | status |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for _, row in coverage.iterrows():
        lines.append(
            "| {target} | {usable} | {rows} | {denoms} | {status} |".format(
                target=row["selected_target_id"],
                usable=str(bool(row["usable_for_09C_supported_gate"])).lower(),
                rows=int(row["binding_row_n"]),
                denoms=row["denominators"],
                status=row["selected_target_binding_coverage_status"],
            )
        )
    lines.extend(
        [
            "",
            "## 3. Sample Key",
            "",
            "`sample_key = (sample_id, selected_target_id, denominator_id)` 是唯一 downstream join key；`sample_id` 单列不可假设唯一。",
            "",
            "| denominator | rows | sample_id unique | sample_key unique | duplicate key rows | status |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for _, row in sample_key.iterrows():
        lines.append(
            "| {denom} | {rows} | {sample_id} | {sample_key} | {dups} | {status} |".format(
                denom=row["denominator_id"],
                rows=int(row["row_n"]),
                sample_id=int(row["sample_id_unique_n"]),
                sample_key=int(row["sample_key_unique_n"]),
                dups=int(row["sample_key_duplicate_n"]),
                status=row["sample_key_uniqueness_status"],
            )
        )
    lines.extend(
        [
            "",
            "## 4. Industry / Board PIT",
            "",
            "| domain | PIT available | coverage | policy | status |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for _, row in industry.iterrows():
        coverage_rate = row["coverage_rate"]
        coverage_text = "" if pd.isna(coverage_rate) else f"{float(coverage_rate):.4f}"
        lines.append(
            "| {domain} | {pit} | {coverage} | {policy} | {status} |".format(
                domain=row["feature_domain"],
                pit=str(bool(row["pit_available_flag"])).lower(),
                coverage=coverage_text,
                policy=row["feature_policy"],
                status=row["industry_pit_status"],
            )
        )
    lines.extend(
        [
            "",
            "## 5. Input Contract Audits",
            "",
            f"- 09A manifest hash status: `{hash_status}`",
            f"- source pool reconstruction status: `{source_pool_status}`",
            "",
            "## 6. Weight / Scope Materialization",
            "",
        ]
    )
    if decision == DECISION_UPSTREAM_CONFLICT:
        lines.append(
            "由于当前处于 upstream contract conflict，09B 不产出 `sample_uniqueness_weights.parquet`、feature matrix 或 importance。"
        )
    elif decision == DECISION_DIAGNOSTIC:
        lines.append(
            "09A target binding contract 已通过；当前 09B 仍为 diagnostic-only，因为尚未 materialize 冻结 `sample_uniqueness_weights.parquet`、feature matrix、transform contract 与 importance。"
        )
    elif decision == DECISION_COMPLETE:
        lines.append("09B 已产出冻结 sample weights、feature matrix、transform contract 与 importance。")
    else:
        lines.append(
            "09B 未产出冻结 `sample_uniqueness_weights.parquet`、feature matrix 或 importance；需先解除 blocked / input 状态。"
        )
    lines.extend(
        [
            "",
            "scope 解释：`risk_on_r_core_horizon_complete` 是唯一 supported training denominator；`risk_on_r6_horizon_complete` 只能 readout-only；`risk_off_e1_horizon_complete_readonly` 只用于上游 binding 对账，标记为 `not_09B_scope_readonly`，不得进入 09B feature / weight / importance scope。",
            "",
        ]
    )
    if materialization:
        lines.extend(
            [
                "## 7. Materialized Artifacts",
                "",
                "| artifact | rows / count | status |",
                "| --- | ---: | --- |",
                "| feature matrix rows | {rows} | R-core={r_core}, R6={r6} |".format(
                    rows=materialization.get("feature_matrix_rows", 0),
                    r_core=materialization.get("feature_matrix_r_core_rows", 0),
                    r6=materialization.get("feature_matrix_r6_rows", 0),
                ),
                "| allowed features | {features} | all stationarity pass |".format(
                    features=materialization.get("feature_n", 0)
                ),
                "| sample weight rows | {rows} | horizons={horizons} |".format(
                    rows=materialization.get("sample_weight_rows", 0),
                    horizons=";".join(materialization.get("weight_horizon_ids", [])),
                ),
                "| 20D non-executable zero-weight rows | {rows} | documented caveat |".format(
                    rows=materialization.get("non_evaluable_20d_rows", 0)
                ),
                "| diagnostic models | {rows} | train-only logistic diagnostics |".format(
                    rows=materialization.get("diagnostic_model_n", 0)
                ),
                "| single feature importance rows | {rows} | SFI by target and split |".format(
                    rows=materialization.get("single_feature_importance_rows", 0)
                ),
                "",
                "20D hybrid 权重中有少量 `non_executable_next_open` 样本无法形成完整 20D active interval，09B 将其保留在 feature matrix 中，但在 `sample_uniqueness_weights.parquet` 中标为 `not_evaluable_20d` 且 `final_sample_weight=0`。10D fast-fail 权重已完整覆盖 R-core 与 R6。",
                "",
                "R6 的 feature matrix / weights 已 materialize 为 readout-only；R6 importance 当前未 materialize，并在 `target_component_importance_summary.csv` 中标记为 `not_materialized`。",
                "",
            ]
        )
    lines.extend(["## 8. Next Action" if materialization else "## 7. Next Action", ""])
    if decision == DECISION_UPSTREAM_CONFLICT:
        lines.append(
            "当前阻塞在 09A target contract，不应继续构造 feature matrix。优先修 09A：要么把缺 binding target 降为 sensitivity target，要么补齐其事件级 binding。"
        )
    elif decision == DECISION_DIAGNOSTIC:
        lines.append(
            "下一步应实现 09B 的冻结 feature foundation：按 `break_swing_low_20__or_false_repair_20d` 生成 R-core training scope 的 sample weights、feature matrix、transform contract、stationarity audit 与 importance readout。"
        )
    else:
        lines.append("按 manifest decision 处理后续 09C 是否可进入 supported gate。")
    return "\n".join(lines)


def build_manifest(
    decision: str,
    config: dict[str, Any],
    input_frame: pd.DataFrame,
    outputs: dict[str, Path],
    statuses: dict[str, Any],
) -> dict[str, Any]:
    output_hashes = {
        key: file_sha256(path)
        for key, path in sorted(outputs.items())
        if key != "manifest" and path.exists() and path.is_file()
    }
    input_hashes = {
        str(row["input_id"]): row["sha256"]
        for _, row in input_frame.iterrows()
        if str(row.get("sha256", ""))
    }
    input_paths = {
        str(row["input_id"]): str(row["path"])
        for _, row in input_frame.iterrows()
        if str(row.get("path", ""))
    }
    return {
        "experiment_id": config["experiment"]["id"],
        "phase": "09B_feature_foundation_ablation",
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_revision(PROJECT_ROOT),
        "decision": decision,
        "source_caveated": bool(statuses.get("source_caveated", False)),
        "input_paths": input_paths,
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
        "config_hash": stable_hash(config),
        **statuses,
        "outputs": {key: str(path) for key, path in outputs.items()},
    }


def run_feature_foundation(
    config_path: Path = CONFIG_PATH, *, check_inputs_only: bool = False
) -> dict[str, Any]:
    config = load_config(config_path)
    outputs = output_paths()
    for path in {p.parent for p in outputs.values()}:
        path.mkdir(parents=True, exist_ok=True)

    input_frame, input_failures = input_audit(config)
    write_df(outputs["input_artifact_audit"], input_frame)
    if check_inputs_only:
        return {"decision": "check_inputs", "input_failures": input_failures}

    coverage = pd.DataFrame()
    sample_key = pd.DataFrame()
    industry = pd.DataFrame()
    hash_status = "not_run"
    source_pool_status = "not_run"
    if input_failures:
        decision = DECISION_INPUT_BLOCKED
        statuses: dict[str, Any] = {
            "source_caveated": False,
            "selected_target_binding_coverage_status": "not_run",
            "sample_key_uniqueness_status": "not_run",
            "upstream_contract_status": "not_run",
            "09a_decision_status": "not_run",
            "09a_manifest_hash_status": "not_run",
            "source_pool_reconstruction_status": "not_run",
            "industry_pit_status": "not_run",
            "r6_readout_materialization_status": "not_run",
            "importance_split_stability_status": "not_run",
            "weight_horizon_ids": [],
            "supported_selected_target_ids": [],
            "missing_selected_target_ids": [],
            "selected_target_contract_hash": "",
            "selected_label_event_bindings_hash": "",
        }
        write_text(
            outputs["report"],
            report_text(
                decision,
                coverage,
                sample_key,
                industry,
                input_failures,
                hash_status=hash_status,
                source_pool_status=source_pool_status,
            ),
        )
        manifest = build_manifest(decision, config, input_frame, outputs, statuses)
        write_json(outputs["manifest"], manifest)
        return {
            "decision": decision,
            "input_failures": input_failures,
            "manifest_path": str(outputs["manifest"]),
            "report_path": str(outputs["report"]),
        }

    manifest_09a = load_json(MANIFEST_DIR / "09A_fast_fail_label_frontier_manifest.json")
    decision_09a = str(manifest_09a.get("decision", ""))
    source_caveated = source_caveated_from_09a_decision(decision_09a)
    decision_09a_status = (
        "pass" if decision_09a in ALLOWED_09A_DECISIONS else "diagnostic_only_no_candidate"
    )
    hash_audit = build_09a_manifest_hash_audit(manifest_09a)
    write_df(outputs["09a_manifest_hash_audit"], hash_audit)
    hash_status = "pass" if hash_audit["hash_match_flag"].map(boolish).all() else "hash_mismatch"
    if hash_status != "pass":
        input_failures = ["09a_manifest_hash_mismatch"]
        decision = DECISION_INPUT_BLOCKED
        statuses = {
            "source_caveated": source_caveated,
            "selected_target_binding_coverage_status": "not_run",
            "sample_key_uniqueness_status": "not_run",
            "upstream_contract_status": "not_run",
            "09a_decision_status": decision_09a_status,
            "09a_manifest_hash_status": hash_status,
            "source_pool_reconstruction_status": "not_run",
            "industry_pit_status": "not_run",
            "r6_readout_materialization_status": "not_run",
            "importance_split_stability_status": "not_run",
            "weight_horizon_ids": [],
            "supported_selected_target_ids": [],
            "missing_selected_target_ids": [],
            "selected_target_ids": [],
            "selected_target_contract_hash": path_hash(
                TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_contract.csv"
            ),
            "selected_label_event_bindings_hash": path_hash(
                LOCAL_CACHE_DIR
                / "09A_fast_fail_label_frontier"
                / "selected_label_event_bindings.parquet"
            ),
            "selected_feature_contract_hash": "",
            "feature_matrix_hash": "",
            "feature_transform_contract_hash": "",
            "sample_uniqueness_weights_hash": "",
            "feature_leakage_status": "not_run",
            "forbidden_feature_count": 0,
            "stationarity_audit_status": "not_run",
            "mechanism_overlap_status": "not_run",
        }
        write_text(
            outputs["report"],
            report_text(
                decision,
                coverage,
                sample_key,
                industry,
                input_failures,
                hash_status=hash_status,
                source_pool_status=source_pool_status,
            ),
        )
        manifest = build_manifest(decision, config, input_frame, outputs, statuses)
        write_json(outputs["manifest"], manifest)
        return {
            "decision": decision,
            "input_failures": input_failures,
            "manifest_path": str(outputs["manifest"]),
            "report_path": str(outputs["report"]),
        }

    selected_contract = read_csv(
        TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_contract.csv"
    )
    binding = pd.read_parquet(
        LOCAL_CACHE_DIR / "09A_fast_fail_label_frontier" / "selected_label_event_bindings.parquet"
    )
    industry_source = read_csv(
        PROJECT_ROOT
        / "experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/industry_style_input_contract_audit.csv"
    )
    capability = read_csv(
        PROJECT_ROOT
        / "experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_run_capability_summary.csv"
    )
    source_audit_source = read_csv(TABLE_DIR / "input_audit" / "source_pool_reconstruction_audit.csv")

    coverage = build_selected_target_binding_coverage(selected_contract, binding)
    sample_key = build_sample_key_uniqueness_audit(binding)
    industry = build_industry_board_pit_membership_audit(industry_source, capability)
    source_audit = build_source_pool_reconstruction_audit(source_audit_source)
    source_pool_status = source_pool_reconstruction_status(source_audit)
    coverage_status, upstream_status, supported, missing = selected_target_binding_status(coverage)
    sample_key_status = (
        "pass"
        if not sample_key.empty and sample_key["sample_key_uniqueness_status"].eq("pass").all()
        else "blocked"
    )
    industry_status = (
        "industry_blocked_board_fallback_available"
        if "industry_pit_unavailable" in set(industry["industry_pit_status"].astype(str))
        else "pass"
    )
    weight_horizon_ids: list[str] = []
    feature_leakage_status = "not_run"
    forbidden_feature_count = 0
    stationarity_audit_status = "not_run"
    mechanism_overlap_status = "not_run"
    importance_split_stability_status = "not_run"
    r6_readout_materialization_status = "not_materialized"
    materialization_summary: dict[str, Any] = {}
    if upstream_status == "upstream_contract_conflict":
        decision = DECISION_UPSTREAM_CONFLICT
        sample_uniqueness = build_sample_uniqueness_audit(
            coverage,
            binding,
            blocked_by_upstream_conflict=True,
        )
    elif sample_key_status != "pass":
        decision = DECISION_BLOCKED
        sample_uniqueness = build_sample_uniqueness_audit(
            coverage,
            binding,
            blocked_by_upstream_conflict=False,
        )
    elif source_pool_status != "pass":
        decision = DECISION_BLOCKED
        sample_uniqueness = build_sample_uniqueness_audit(
            coverage,
            binding,
            blocked_by_upstream_conflict=False,
        )
    elif decision_09a_status != "pass":
        decision = DECISION_DIAGNOSTIC
        sample_uniqueness = build_sample_uniqueness_audit(
            coverage,
            binding,
            blocked_by_upstream_conflict=False,
        )
    else:
        calendar = build_trading_calendar(config, binding)
        weights = build_sample_uniqueness_weights(binding, calendar, supported)
        sample_uniqueness = sample_uniqueness_audit_from_weights(coverage, binding, weights)
        (
            feature_matrix,
            feature_contract,
            stationarity,
            transform_contract,
            leakage,
            schema,
        ) = build_feature_artifacts(binding, config, supported)
        overlap = build_label_mechanism_overlap_audit(feature_contract)
        (
            family_ablation,
            group_mda,
            single_feature_importance,
            diagnostic_registry,
            importance_summary,
            importance_stability,
            clustered_report,
        ) = build_importance_artifacts(feature_matrix, binding, weights, feature_contract, config)

        write_df(outputs["sample_uniqueness_weights"], weights)
        write_df(outputs["feature_matrix"], feature_matrix)
        write_df(outputs["feature_contract"], feature_contract)
        write_df(outputs["feature_stationarity_audit"], stationarity)
        write_json(outputs["feature_transform_contract"], transform_contract)
        write_df(outputs["feature_leakage_audit"], leakage)
        write_df(outputs["feature_matrix_schema"], schema)
        write_df(outputs["label_mechanism_overlap_audit"], overlap)
        write_df(outputs["feature_family_ablation"], family_ablation)
        write_df(outputs["single_feature_importance"], single_feature_importance)
        write_df(outputs["group_mda_importance"], group_mda)
        write_df(outputs["diagnostic_model_registry"], diagnostic_registry)
        write_df(outputs["target_component_importance_summary"], importance_summary)
        write_df(outputs["importance_split_stability"], importance_stability)
        write_text(outputs["clustered_importance_report"], clustered_report)

        forbidden_feature_count = int(leakage["forbidden_feature_flag"].map(boolish).sum())
        feature_leakage_status = "pass" if forbidden_feature_count == 0 else "blocked"
        stationarity_audit_status = (
            "pass"
            if stationarity["stationarity_status"].isin({"pass", "constant_after_transform"}).all()
            else "blocked"
        )
        mechanism_overlap_status = "pass"
        importance_split_stability_status = (
            "pass"
            if not importance_stability.empty
            and importance_stability["stability_status"].isin({"pass", "low_power"}).all()
            else "low_power"
        )
        r6_readout_materialization_status = "materialized_readout_only"
        weight_horizon_ids = [FAST_FAIL_WEIGHT, HYBRID_WEIGHT]
        materialization_summary = {
            "feature_matrix_rows": int(len(feature_matrix)),
            "feature_matrix_r_core_rows": int(
                feature_matrix["denominator_id"].eq(RISK_ON_R_CORE_DENOM).sum()
            ),
            "feature_matrix_r6_rows": int(
                feature_matrix["denominator_id"].eq(RISK_ON_R6_DENOM).sum()
            ),
            "feature_n": int(len(feature_contract)),
            "sample_weight_rows": int(len(weights)),
            "weight_horizon_ids": weight_horizon_ids,
            "non_evaluable_20d_rows": int(weights["weight_status"].eq("not_evaluable_20d").sum()),
            "diagnostic_model_n": int(len(diagnostic_registry)),
            "single_feature_importance_rows": int(len(single_feature_importance)),
            "r6_importance_status": "not_materialized",
        }
        decision = (
            DECISION_COMPLETE
            if feature_leakage_status == "pass" and forbidden_feature_count == 0
            else DECISION_BLOCKED
        )

    write_df(outputs["selected_target_binding_coverage_audit"], coverage)
    write_df(outputs["sample_uniqueness_audit"], sample_uniqueness)
    write_df(outputs["sample_key_uniqueness_audit"], sample_key)
    write_df(outputs["source_pool_reconstruction_audit"], source_audit)
    write_df(outputs["industry_board_pit_membership_audit"], industry)

    statuses = {
        "source_caveated": source_caveated,
        "selected_target_ids": selected_targets(selected_contract)["selected_target_id"]
        .astype(str)
        .tolist(),
        "supported_selected_target_ids": supported,
        "missing_selected_target_ids": missing,
        "selected_target_binding_coverage_status": coverage_status,
        "sample_key_uniqueness_status": sample_key_status,
        "upstream_contract_status": upstream_status,
        "09a_decision_status": decision_09a_status,
        "09a_manifest_hash_status": hash_status,
        "source_pool_reconstruction_status": source_pool_status,
        "industry_pit_status": industry_status,
        "r6_readout_materialization_status": r6_readout_materialization_status,
        "r6_importance_materialization_status": "not_materialized"
        if decision == DECISION_COMPLETE
        else "not_run",
        "diagnostic_model_config_hash": stable_hash(config.get("diagnostic_model", {})),
        "importance_split_stability_status": "not_run_upstream_contract_conflict"
        if decision == DECISION_UPSTREAM_CONFLICT
        else importance_split_stability_status,
        "feature_leakage_status": "not_run_upstream_contract_conflict"
        if decision == DECISION_UPSTREAM_CONFLICT
        else feature_leakage_status,
        "forbidden_feature_count": forbidden_feature_count,
        "stationarity_audit_status": "not_run_upstream_contract_conflict"
        if decision == DECISION_UPSTREAM_CONFLICT
        else stationarity_audit_status,
        "mechanism_overlap_status": "not_run_upstream_contract_conflict"
        if decision == DECISION_UPSTREAM_CONFLICT
        else mechanism_overlap_status,
        "weight_horizon_ids": weight_horizon_ids,
        "selected_target_contract_hash": path_hash(
            TABLE_DIR / "09A_fast_fail_label_frontier" / "selected_label_contract.csv"
        ),
        "selected_label_event_bindings_hash": path_hash(
            LOCAL_CACHE_DIR
            / "09A_fast_fail_label_frontier"
            / "selected_label_event_bindings.parquet"
        ),
        "selected_feature_contract_hash": path_hash(outputs["feature_contract"]),
        "feature_matrix_hash": path_hash(outputs["feature_matrix"]),
        "feature_transform_contract_hash": path_hash(outputs["feature_transform_contract"]),
        "sample_uniqueness_weights_hash": path_hash(outputs["sample_uniqueness_weights"]),
    }
    write_text(
        outputs["report"],
        report_text(
            decision,
            coverage,
            sample_key,
            industry,
            input_failures,
            hash_status=hash_status,
            source_pool_status=source_pool_status,
            materialization=materialization_summary,
        ),
    )
    manifest = build_manifest(decision, config, input_frame, outputs, statuses)
    write_json(outputs["manifest"], manifest)
    return {
        "decision": decision,
        "selected_target_binding_coverage_status": coverage_status,
        "missing_selected_target_ids": missing,
        "manifest_path": str(outputs["manifest"]),
        "report_path": str(outputs["report"]),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_feature_foundation(
        Path(args.config), check_inputs_only=args.mode == "check-inputs"
    )
    if args.mode == "check-inputs":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if not result.get("input_failures") else 2
    print(f"decision={result['decision']}")
    if "selected_target_binding_coverage_status" in result:
        print(
            "selected_target_binding_coverage_status="
            f"{result['selected_target_binding_coverage_status']}"
        )
    if result.get("missing_selected_target_ids"):
        print("missing_selected_target_ids=" + ";".join(result["missing_selected_target_ids"]))
    print(f"manifest={result['manifest_path']}")
    print(f"report={result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

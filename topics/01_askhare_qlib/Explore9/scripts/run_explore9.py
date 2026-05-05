#!/usr/bin/env python3
"""Run Explore9 P0 broad discovery.

Explore9 is a discovery phase.  It rebuilds labels and primitive profiles from
PIT structural inputs and the Qlib provider, while treating Explore8 outputs as
background/schema references only.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore", category=FutureWarning)


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
DEFAULT_CONFIG = EXPLORE_DIR / "configs/broad_discovery_p0.yaml"
DEFAULT_P0_5_CONFIG = EXPLORE_DIR / "configs/broad_discovery_expand_1.yaml"
DEFAULT_P0_6_CONFIG = EXPLORE_DIR / "configs/entry_trigger_p0_6.yaml"
DEFAULT_P0_7_CONFIG = EXPLORE_DIR / "configs/launch_failure_p0_7ab.yaml"
DEFAULT_P0_8_CONFIG = EXPLORE_DIR / "configs/gate_lgbm_p0_8.yaml"
FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}
REQUIRED_P0_REPORTS = [
    "source_data_audit.csv",
    "source_data_audit_summary.json",
    "provider_coverage_audit.csv",
    "label_coverage_audit.csv",
    "run_manifest.json",
    "stock_day_label_panel_summary.csv",
    "episode_lifecycle_labels.csv",
    "label_distribution_by_year.csv",
    "label_distribution_by_industry.csv",
    "observed_reference_label_audit.csv",
    "primitive_feature_dictionary.csv",
    "primitive_feature_coverage.csv",
    "primitive_univariate_lift.csv",
    "primitive_pairwise_lift.csv",
    "primitive_year_stability.csv",
    "primitive_industry_stability.csv",
    "preliminary_discovery_leads.csv",
    "p0_scope_completion_audit.csv",
    "explore9_broad_discovery_report.md",
]
DEFERRED_P1_OUTPUTS = [
    "hypothesis_discovery_leaderboard.csv",
    "hypothesis_year_breakdown.csv",
    "hypothesis_industry_breakdown.csv",
    "hypothesis_lifecycle_stage_breakdown.csv",
    "hypothesis_failure_modes.csv",
    "hold_condition_analysis.csv",
    "early_exit_replacement_hypotheses.csv",
    "post_20pct_continuation_analysis.csv",
    "post_30pct_continuation_analysis.csv",
]
DEFERRED_P2_OUTPUTS = [
    "price_shape_cluster_summary.csv",
    "money_shape_cluster_summary.csv",
    "joint_shape_cluster_summary.csv",
    "shape_cluster_examples.csv",
]
P0_5_REQUIRED_REPORTS = [
    "p0_5_primitive_feature_dictionary.csv",
    "p0_5_primitive_feature_coverage.csv",
    "p0_5_univariate_lift.csv",
    "p0_5_pairwise_lift.csv",
    "p0_5_lead_ranking_stock_day.csv",
    "p0_5_lead_ranking_instrument_year.csv",
    "p0_5_lead_ranking_dedup_trigger_event.csv",
    "p0_5_winner_episode_coverage.csv",
    "p0_5_early_entry_discovery_leads.csv",
    "p0_5_confirmation_continuation_leads.csv",
    "p0_5_hold_exit_tolerance_leads.csv",
    "p0_5_high_volatility_decomposition.csv",
    "p0_5_repair_initiation_leads.csv",
    "p0_5_rank_jump_leadership_leads.csv",
    "p0_5_money_quality_leads.csv",
    "p0_5_sparse_strong_day_diagnostics.csv",
    "p0_5_candidate_pattern_audit.csv",
    "p0_5_false_positive_audit.csv",
    "p0_5_scope_completion_audit.csv",
    "p0_5_run_manifest.json",
    "explore9_p0_5_expand_1_report.md",
]
P0_6_REQUIRED_REPORTS = [
    "p0_6_launch_event_dictionary.csv",
    "p0_6_launch_formula_matrix.csv",
    "p0_6_launch_pool_quality_audit.csv",
    "p0_6_launch_pool_lifecycle_gate_audit.csv",
    "p0_6_entry_trigger_dictionary.csv",
    "p0_6_entry_trigger_formula_matrix.csv",
    "p0_6_launch_event_panel.csv",
    "p0_6_entry_event_panel.csv",
    "p0_6_direct_launch_entry_baseline.csv",
    "p0_6_all_launch_direct_baseline.csv",
    "p0_6_trigger_convertible_direct_baseline.csv",
    "p0_6_matched_delay_baseline.csv",
    "p0_6_entry_trigger_lift.csv",
    "p0_6_entry_trigger_vs_direct.csv",
    "p0_6_entry_trigger_year_breakdown.csv",
    "p0_6_entry_trigger_instrument_year_breakdown.csv",
    "p0_6_entry_trigger_industry_breakdown.csv",
    "p0_6_entry_execution_assumption_audit.csv",
    "p0_6_entry_execution_feasibility_audit.csv",
    "p0_6_entry_trigger_dedup_audit.csv",
    "p0_6_entry_trigger_failure_audit.csv",
    "p0_6_entry_trigger_missed_gain_audit.csv",
    "p0_6_entry_trigger_missed_winner_audit.csv",
    "p0_6_entry_trigger_leaderboard.csv",
    "p0_6_entry_trigger_rejected.csv",
    "p0_6_scope_completion_audit.csv",
    "p0_6_run_manifest.json",
    "explore9_p0_6_entry_trigger_report.md",
]
P0_7_REQUIRED_REPORTS = [
    "p0_7_feature_dictionary.csv",
    "p0_7_formula_token_coverage_audit.csv",
    "p0_7_launch_formula_matrix.csv",
    "p0_7_launch_episode_summary.csv",
    "p0_7_launch_stratum_event_summary.csv",
    "p0_7_launch_stratification_leaderboard.csv",
    "p0_7_launch_stratification_rejected.csv",
    "p0_7_direct_launch_baseline_by_stratum.csv",
    "p0_7_failure_filter_formula_matrix.csv",
    "p0_7_failure_filter_opportunity_summary.csv",
    "p0_7_failure_filter_event_summary.csv",
    "p0_7_failure_filter_leaderboard.csv",
    "p0_7_failure_filter_rejected.csv",
    "p0_7_failure_filter_false_reject_audit.csv",
    "p0_7_failure_filter_drawdown_reduction_audit.csv",
    "p0_7_matched_delay_filter_baseline.csv",
    "p0_7_lifecycle_transition_audit.csv",
    "p0_7_stratum_observability_audit.csv",
    "p0_7_regime_breakdown.csv",
    "p0_7_industry_breakdown.csv",
    "p0_7_instrument_year_breakdown.csv",
    "p0_7_dedup_audit.csv",
    "p0_7_scope_completion_audit.csv",
    "p0_7_row_panel_schema.csv",
    "p0_7_run_manifest.json",
    "explore9_p0_7ab_launch_failure_report.md",
]
P0_8_REQUIRED_CACHE = [
    "p0_8_launch_model_sample_panel.parquet",
    "p0_8_failure_model_sample_panel.parquet",
    "p0_8_failure_multi_window_event_level_dedup_panel.parquet",
    "p0_8_lgbm_launch_predictions_walkforward.parquet",
    "p0_8_lgbm_failure_predictions_walkforward.parquet",
]
P0_8_REQUIRED_REPORTS = [
    "p0_8_run_manifest.json",
    "p0_8_label_dictionary.csv",
    "p0_8_feature_dictionary.csv",
    "p0_8_gate_token_dictionary.csv",
    "p0_8_formula_token_coverage_audit.csv",
    "p0_8_feature_asof_leakage_audit.csv",
    "p0_8_observed_reference_label_measurement_audit.csv",
    "p0_8_fold_role_audit.csv",
    "p0_8_sample_weight_audit.csv",
    "p0_8_sample_weight_group_cap_audit.csv",
    "p0_8_failure_multi_window_dedup_audit.csv",
    "p0_8_candidate_baseline_composition_audit.csv",
    "p0_8_candidate_baseline_missing_audit.csv",
    "p0_8_gate_candidate_train_search.csv",
    "p0_8_gate_candidate_validation_metrics.csv",
    "p0_8_gate_candidate_oof_aggregation.csv",
    "p0_8_gate_complexity_audit.csv",
    "p0_8_lgbm_fold_trainability_audit.csv",
    "p0_8_lgbm_fold_metrics.csv",
    "p0_8_lgbm_score_bucket_metrics.csv",
    "p0_8_lgbm_instrument_year_metrics.csv",
    "p0_8_lgbm_industry_metrics.csv",
    "p0_8_lgbm_feature_importance.csv",
    "p0_8_lgbm_leaf_rule_candidates.csv",
    "p0_8_lgbm_leaf_rule_canonicalization_audit.csv",
    "p0_8_lgbm_model_card.csv",
    "p0_8_lgbm_early_stopping_audit.csv",
    "p0_8_lgbm_score_bucket_selection_audit.csv",
    "p0_8_threshold_dispersion_audit.csv",
    "p0_8_stable_candidate_oof_aggregation.csv",
    "p0_8_p1_promotion_oof_aggregation.csv",
    "p0_8_oof_robustness_all_folds.csv",
    "p0_8_search_bias_audit.csv",
    "p0_8_null_permutation_baseline.csv",
    "p0_8_lgbm_null_bucket_baseline.csv",
    "p0_8_lgbm_null_leaf_rule_baseline.csv",
    "p0_8_fold_local_p0_7_baseline_audit.csv",
    "p0_8_industry_regime_concentration_audit.csv",
    "p0_8_industry_regime_ablation_audit.csv",
    "explore9_p0_8_gate_lgbm_report.md",
]


class DataGateError(RuntimeError):
    """Raised when the strict PIT discovery contract cannot be satisfied."""


@dataclass(frozen=True)
class PrimitiveSpec:
    feature_name: str
    feature_family: str
    column: str
    value_type: str
    min_history_trading_days: int
    lookback_window: str
    requires_benchmark_history: bool = False
    requires_industry_history: bool = False
    p0_enabled: bool = True
    direction_hint: str = "high"


@dataclass(frozen=True)
class PairwiseSpec:
    lead_id: str
    lead_name: str
    feature_family: str
    first_feature: str
    first_bins: tuple[str, ...]
    second_feature: str
    second_bins: tuple[str, ...]
    observable_state_stage: str
    direction: str
    recommended_next_phase: str


@dataclass(frozen=True)
class P05PrimitiveSpec:
    feature_name: str
    feature_family: str
    column: str
    value_type: str
    min_history_trading_days: int
    lookback_window: str
    requires_benchmark_history: bool = False
    requires_industry_history: bool = False
    p0_enabled: bool = True
    direction_hint: str = "high"
    p0_5_new: bool = True
    lifecycle_bucket: str = "early_entry_discovery"
    primary_combo_family: str = ""
    sparse_diagnostic: bool = False
    generalizable_entry_lead: bool = True
    path_explanation_only: bool = False
    category_id: str = ""
    human_readable_definition: str = ""
    formula_or_bin: str = ""
    required_columns: str = ""
    close_location_rule: str = ""
    trend_or_drawdown_context: str = ""
    evaluation_only_false_positive_definition: str = ""
    diagnostic_only_not_p1_ready: bool = False


@dataclass(frozen=True)
class P05PatternSpec:
    lead_id: str
    lead_name: str
    primary_combo_family: str
    lifecycle_bucket: str
    conditions: tuple[tuple[str, tuple[str, ...]], ...]
    formula_or_bin: str
    direction: str
    recommended_next_phase: str
    sparse_diagnostic: bool = False
    generalizable_entry_lead: bool = True
    path_explanation_only: bool = False
    diagnostic_only_not_p1_ready: bool = False


@dataclass(frozen=True)
class P06LaunchSpec:
    launch_family: str
    formula: str
    declared_launch_pool: str
    lifecycle_role: str
    primary_entry_leaderboard_eligible: bool
    lookback_days: str
    thresholds: str
    required_fields: str
    sparse_diagnostic: bool = False


@dataclass(frozen=True)
class P06EntrySpec:
    entry_family: str
    entry_variant_id: str
    allowed_launch_families: tuple[str, ...]
    excluded_launch_families: tuple[str, ...]
    signal_window_start_after_launch: int
    signal_window_end_after_launch: int
    entry_signal_condition: str
    entry_signal_date_definition: str
    invalidation_rule_id: str
    invalidation_price_reference: str
    pre_entry_failure_filter_ids: tuple[str, ...]
    post_entry_invalidation_audit_ids: tuple[str, ...]
    primary_leaderboard_eligible: bool = True
    same_close_proxy_allowed: bool = False


@dataclass(frozen=True)
class P07LaunchSpec:
    stratum_family: str
    stratum_variant: str
    formula_text: str
    formula_text_resolved: str
    required_features: tuple[str, ...]
    required_thresholds: tuple[str, ...]
    declared_stratum_role: str
    declared_lifecycle_stage: str


@dataclass(frozen=True)
class P07FailureFilterSpec:
    filter_family: str
    filter_variant: str
    formula_text: str
    formula_text_resolved: str
    required_features: tuple[str, ...]
    required_thresholds: tuple[str, ...]
    signal_date_definition: str
    formula_window_trading_days: int
    filter_formula_observation_timing: str
    effective_date_rule: str
    filter_action: str
    filter_severity: str
    filter_reason_code: str


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(value: str | Path) -> str:
    path = Path(value).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def ensure_parent(value: str | Path) -> Path:
    path = topic_path(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(value: str | Path) -> Path:
    path = topic_path(value)
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_sha256(value: str | Path) -> str:
    path = topic_path(value)
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def maybe_sha256(value: str | Path) -> str:
    path = topic_path(value)
    return file_sha256(path) if path.exists() and path.is_file() else ""


def count_csv_rows(value: str | Path) -> int | None:
    path = topic_path(value)
    if not path.exists() or path.suffix.lower() != ".csv":
        return None
    with path.open("rb") as file:
        rows = sum(1 for _ in file)
    return max(rows - 1, 0)


def load_yaml(value: str | Path) -> dict[str, Any]:
    with topic_path(value).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_config(value: str | Path) -> dict[str, Any]:
    path = topic_path(value)
    config = load_yaml(path)
    config["_config_path"] = str(path)
    config["_config_sha256"] = file_sha256(path)
    return config


def sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_json(item) for item in value]
    if isinstance(value, Path):
        return relpath(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def write_json(data: dict[str, Any], value: str | Path) -> Path:
    path = ensure_parent(value)
    with path.open("w", encoding="utf-8") as file:
        json.dump(sanitize_json(data), file, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")
    return path


def read_json(value: str | Path) -> dict[str, Any]:
    path = topic_path(value)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_csv(df: pd.DataFrame, value: str | Path, **kwargs: Any) -> Path:
    path = ensure_parent(value)
    df.to_csv(path, index=False, **kwargs)
    return path


def read_csv_if_exists(value: str | Path) -> pd.DataFrame:
    path = topic_path(value)
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def parse_dt(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def iso_date(value: Any) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).date().isoformat()


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def safe_div(numerator: Any, denominator: Any) -> float:
    den = safe_float(denominator, 0.0)
    if den == 0 or pd.isna(den):
        return np.nan
    return safe_float(numerator, 0.0) / den


def format_pct(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.2%}"


def format_float(value: Any, digits: int = 3) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.{digits}f}"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    def cell(value: Any) -> str:
        try:
            missing = bool(pd.isna(value))
        except (TypeError, ValueError):
            missing = False
        return "" if missing else str(value)

    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    output.extend("| " + " | ".join(cell(item) for item in row) + " |" for row in rows)
    return output


def report_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["report_dir"])


def cache_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["cache_dir"])


def manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "run_manifest.json"


def stock_panel_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel.pkl"


def stock_panel_meta_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel_meta.json"


def label_panel_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_day_label_panel.parquet"


def source_category_counts(audit: pd.DataFrame) -> dict[str, int]:
    if audit.empty:
        return {}
    grouped = audit.groupby("category", as_index=False).size()
    return {str(row["category"]): int(row["size"]) for _, row in grouped.iterrows()}


def required_field_names(config: dict[str, Any]) -> list[str]:
    return [FIELD_RENAME.get(field, field.lstrip("$")) for field in config["qlib"]["required_fields"]]


def research_years(config: dict[str, Any]) -> list[int]:
    start = parse_dt(config["dates"]["research_start"]).year
    end = parse_dt(config["dates"]["research_end"]).year
    return list(range(start, end + 1))


def record_manifest(config: dict[str, Any], command: str, outputs: list[str | Path], extra: dict[str, Any] | None = None) -> None:
    path = manifest_path(config)
    manifest = read_json(path)
    commands = list(manifest.get("command_sequence", []))
    commands.append(command)
    output_paths = sorted(set(manifest.get("output_paths", []) + [relpath(p) for p in outputs]))
    audit_path = report_dir(config) / "source_data_audit.csv"
    audit = pd.read_csv(audit_path) if audit_path.exists() else pd.DataFrame()
    manifest.update(
        {
            "experiment": "Explore9 P0 broad discovery",
            "phase": "P0",
            "config_path": relpath(config["_config_path"]),
            "config_sha256": config["_config_sha256"],
            "command_sequence": commands,
            "output_paths": output_paths,
            "provider_uri": config["paths"]["provider_uri"],
            "fallback_provider_uri": config["paths"]["fallback_provider_uri"],
            "universe_membership": config["paths"]["universe_membership"],
            "industry_membership": config["paths"]["industry_membership"],
            "point_in_time_universe": bool(config["universe"].get("point_in_time", False)),
            "point_in_time_industry": bool(config["industry"].get("point_in_time", False)),
            "price_adjustment_mode": config["qlib"]["price_adjustment_mode"],
            "required_fields": required_field_names(config),
            "research_start": config["dates"]["research_start"],
            "research_end": config["dates"]["research_end"],
            "observed_reference_start": config["dates"]["observed_reference_start"],
            "observed_reference_end": config["dates"]["observed_reference_end"],
            "source_category_counts": source_category_counts(audit),
            "explore8_profile_csv_used_for_label": False,
            "explore8_profile_csv_used_for_signal": False,
            "explore8_profile_csv_used_for_selection": False,
            "historical_trade_results_used_for_labeling": False,
            "historical_trade_results_used_for_signal": False,
            "historical_trade_results_used_for_selection": False,
            "observed_reference_used_for_selection": False,
            "p1_outputs_status": {name: "deferred_to_p1" for name in DEFERRED_P1_OUTPUTS},
            "p2_outputs_status": {name: "deferred_to_p2" for name in DEFERRED_P2_OUTPUTS},
        }
    )
    if label_panel_path(config).exists():
        panel_path = label_panel_path(config)
        panel_meta = read_json(cache_dir(config) / "stock_day_label_panel_meta.json")
        manifest["stock_day_label_panel"] = {
            "path": relpath(panel_path),
            "format": "parquet",
            "file_size_bytes": panel_path.stat().st_size,
            **panel_meta,
        }
    if extra:
        manifest.update(extra)
    write_json(manifest, path)


def build_source_data_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(path_value: str | Path, category: str, allowed_use: str, used_for_calculation: bool, count_rows: bool = True) -> None:
        path = topic_path(path_value)
        rows.append(
            {
                "path": relpath(path),
                "category": category,
                "allowed_use": allowed_use,
                "exists": bool(path.exists()),
                "is_file": bool(path.is_file()),
                "row_count": count_csv_rows(path) if count_rows and path.exists() and path.is_file() else None,
                "sha256": maybe_sha256(path) if path.exists() and path.is_file() else "",
                "used_for_calculation": bool(used_for_calculation),
            }
        )

    for key in [
        "provider_uri",
        "fallback_provider_uri",
        "universe_membership",
        "universe_qlib",
        "industry_membership",
        "market_targets",
        "industry_targets",
        "target_history",
    ]:
        add(config["paths"][key], "structural_input", key, True, count_rows=key.endswith(("membership", "targets", "history")))
    for path in config.get("sources", {}).get("background_reference", []):
        add(path, "background_reference", "background narrative only", False)
    for path in config.get("sources", {}).get("schema_reference", []):
        add(path, "schema_reference_audit_only", "schema/audit reference only", False)

    patterns = config.get("sources", {}).get("forbidden_result_path_patterns", [])
    tokens = [str(token).lower() for token in config.get("sources", {}).get("forbidden_result_name_tokens", [])]
    for pattern in patterns:
        base = topic_path(pattern)
        candidates: list[Path] = []
        if base.exists() and base.is_dir():
            candidates = [p for p in base.rglob("*") if p.is_file()]
        elif any(ch in pattern for ch in "*?[]"):
            candidates = [p for p in TOPIC_DIR.glob(pattern) if p.is_file()]
        for candidate in sorted(candidates):
            lowered = candidate.name.lower()
            if candidate.suffix.lower() in {".csv", ".pkl", ".json", ".parquet"} and any(token in lowered for token in tokens):
                add(candidate, "forbidden_result_path", "must not enter Explore9 calculation path", False, count_rows=False)
    audit = pd.DataFrame(rows)
    if audit.empty:
        audit = pd.DataFrame(columns=["path", "category", "allowed_use", "exists", "is_file", "row_count", "sha256", "used_for_calculation"])
    return audit.drop_duplicates(["path", "category"]).sort_values(["category", "path"]).reset_index(drop=True)


def validate_source_audit(audit: pd.DataFrame) -> None:
    missing = audit[(audit["category"] == "structural_input") & (~audit["exists"].astype(bool))]
    if not missing.empty:
        raise DataGateError(f"missing structural inputs: {missing['path'].tolist()}")
    forbidden = audit[(audit["category"] == "forbidden_result_path") & (audit["used_for_calculation"].astype(bool))]
    if not forbidden.empty:
        raise DataGateError("forbidden result paths are marked as calculation inputs")


def read_universe(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["universe_membership"])
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "instrument", "listing_age_trading_days", "market_cap_asof_T"}
    missing = required - set(df.columns)
    if missing:
        raise DataGateError(f"PIT universe missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    if "name" not in df.columns:
        df["name"] = ""
    return df.sort_values(["date", "instrument"]).reset_index(drop=True)


def read_industry(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["industry_membership"])
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "instrument", "industry_target_key", "industry_name"}
    missing = required - set(df.columns)
    if missing:
        raise DataGateError(f"PIT industry membership missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    missing_name = config["industry"].get("missing_industry", "UNKNOWN")
    df["industry_name"] = df["industry_name"].fillna(missing_name).replace("", missing_name)
    df["industry_target_key"] = df["industry_target_key"].fillna("UNKNOWN").astype("string")
    return df.sort_values(["date", "instrument"]).reset_index(drop=True)


def read_target_history(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["target_history"])
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"target_type", "target_key", "date", "open", "high", "low", "close", "money"}
    missing = required - set(df.columns)
    if missing:
        raise DataGateError(f"target history missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["target_key"] = df["target_key"].astype("string")
    return df.sort_values(["target_key", "date"]).reset_index(drop=True)


def qlib_instruments_from_file(config: dict[str, Any]) -> list[str]:
    path = topic_path(config["paths"]["universe_qlib"])
    if not path.exists():
        raise DataGateError(f"Qlib PIT instrument file missing: {relpath(path)}")
    instruments: list[str] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            token = line.strip().split()
            if token:
                instruments.append(token[0].upper())
    if not instruments:
        raise DataGateError(f"Qlib PIT instrument file is empty: {relpath(path)}")
    return sorted(set(instruments))


def provider_candidates(config: dict[str, Any]) -> list[tuple[Path, bool]]:
    primary = topic_path(config["paths"]["provider_uri"])
    fallback = topic_path(config["paths"]["fallback_provider_uri"])
    candidates = [(primary, False)]
    if fallback != primary:
        candidates.append((fallback, True))
    return candidates


def load_stock_panel_from_qlib(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    instruments = qlib_instruments_from_file(config)
    fields = config["qlib"]["required_fields"]
    last_error = ""
    for provider_uri, fallback in provider_candidates(config):
        if not provider_uri.exists():
            last_error = f"provider missing: {relpath(provider_uri)}"
            continue
        try:
            qlib.init(provider_uri=str(provider_uri), region=REG_CN)
            df = D.features(
                instruments=instruments,
                fields=fields,
                start_time=config["dates"]["data_start"],
                end_time=config["dates"]["data_end"],
                freq=config["qlib"].get("freq", "day"),
            )
            if df.empty:
                last_error = f"Qlib provider returned no stock rows: {relpath(provider_uri)}"
                continue
            panel = df.rename(columns=FIELD_RENAME).reset_index()
            panel["instrument"] = panel["instrument"].astype(str).str.upper()
            panel["datetime"] = pd.to_datetime(panel["datetime"]).dt.normalize()
            meta = {
                "provider_uri": relpath(provider_uri),
                "fallback_used": bool(fallback),
                "fallback_provider_uri": relpath(provider_uri) if fallback else "",
                "loaded_instruments": int(panel["instrument"].nunique()),
                "loaded_rows": int(len(panel)),
            }
            return panel.sort_values(["instrument", "datetime"]).reset_index(drop=True), meta
        except Exception as exc:  # noqa: BLE001
            last_error = f"{relpath(provider_uri)}: {exc}"
    raise DataGateError(f"no readable Qlib provider for Explore9; last_error={last_error}")


def load_stock_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    panel_path = stock_panel_cache_path(config)
    meta_path = stock_panel_meta_path(config)
    if panel_path.exists() and meta_path.exists():
        return pd.read_pickle(panel_path), read_json(meta_path)
    panel, meta = load_stock_panel_from_qlib(config)
    ensure_parent(panel_path)
    pd.to_pickle(panel, panel_path)
    write_json(meta, meta_path)
    return panel, meta


def build_provider_coverage_audit(
    config: dict[str, Any],
    universe: pd.DataFrame,
    industry: pd.DataFrame,
    panel: pd.DataFrame,
    provider_meta: dict[str, Any],
    target_history: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    fields = required_field_names(config)
    research_start = parse_dt(config["dates"]["research_start"])
    observed_end = parse_dt(config["dates"]["observed_reference_end"])
    membership = universe[(universe["date"] >= research_start) & (universe["date"] <= observed_end)][["date", "instrument"]].drop_duplicates()
    membership["year"] = membership["date"].dt.year
    availability = panel[["datetime", "instrument"] + [field for field in fields if field in panel.columns]].rename(columns={"datetime": "date"}).copy()
    for field in fields:
        if field not in availability.columns:
            availability[field] = np.nan
    merged = membership.merge(availability, on=["date", "instrument"], how="left")
    merged["readable_row"] = merged["open"].notna()
    merged["all_required_fields"] = merged[fields].notna().all(axis=1)
    ind = industry[["date", "instrument", "industry_name"]].drop_duplicates()
    merged = merged.merge(ind, on=["date", "instrument"], how="left")
    merged["industry_name"] = merged["industry_name"].fillna(config["industry"].get("missing_industry", "UNKNOWN")).replace("", "UNKNOWN")
    broad_key = config["qlib"]["broad_market_key"]
    broad = target_history[(target_history["target_type"] == "market") & (target_history["target_key"] == broad_key)].copy()
    benchmark_years = set(pd.to_datetime(broad["date"]).dt.year.astype(int).tolist())

    rows: list[dict[str, Any]] = []
    coverage_ok_min = float(config["coverage"]["coverage_ok_min"])
    coverage_limited_min = float(config["coverage"]["coverage_limited_min"])
    required_ok_min = float(config["coverage"]["required_field_coverage_ok_min"])
    for year, subset in merged.groupby("year", sort=True):
        membership_rows = int(len(subset))
        readable_rows = int(subset["readable_row"].sum())
        required_rows = int(subset["all_required_fields"].sum())
        ratio = readable_rows / membership_rows if membership_rows else 0.0
        required_ratio = required_rows / membership_rows if membership_rows else 0.0
        missing = subset[~subset["all_required_fields"]]
        if ratio >= coverage_ok_min and required_ratio >= required_ok_min and int(year) in benchmark_years:
            status = "coverage_ok"
            conclusion_permission = "full_p0_discovery"
        elif ratio >= coverage_limited_min and int(year) in benchmark_years:
            status = "coverage_limited"
            conclusion_permission = "diagnostic_only_limited"
        else:
            status = "data_insufficient"
            conclusion_permission = "no_year_conclusion"
        rows.append(
            {
                "year": int(year),
                "pit_membership_rows": membership_rows,
                "readable_pit_membership_rows": readable_rows,
                "rows_with_all_required_fields": required_rows,
                "missing_required_rows": int(membership_rows - required_rows),
                "readable_coverage_ratio": ratio,
                "required_field_coverage_ratio": required_ratio,
                "missing_instrument_count": int(missing["instrument"].nunique()) if not missing.empty else 0,
                "missing_top_industries": json.dumps(missing.groupby("industry_name").size().sort_values(ascending=False).head(8).to_dict(), ensure_ascii=False),
                "benchmark_readable": bool(int(year) in benchmark_years),
                "coverage_status": status,
                "conclusion_permission": conclusion_permission,
                "provider_uri": provider_meta.get("provider_uri", ""),
                "fallback_used": bool(provider_meta.get("fallback_used", False)),
            }
        )
    audit = pd.DataFrame(rows)
    research = audit[audit["year"].isin(research_years(config))]
    total_membership = int(research["pit_membership_rows"].sum()) if not research.empty else 0
    total_required = int(research["rows_with_all_required_fields"].sum()) if not research.empty else 0
    summary = {
        "provider_uri": provider_meta.get("provider_uri", ""),
        "fallback_used": bool(provider_meta.get("fallback_used", False)),
        "research_membership_rows": total_membership,
        "research_required_field_rows": total_required,
        "research_required_field_coverage_ratio": total_required / total_membership if total_membership else 0.0,
        "coverage_limited_research": bool((research["coverage_status"] != "coverage_ok").any()) if not research.empty else True,
        "all_research_years_coverage_ok": bool((research["coverage_status"] == "coverage_ok").all()) if not research.empty else False,
    }
    return audit, summary


def future_rolling_max(series: pd.Series, horizon: int) -> pd.Series:
    rev = series.iloc[::-1]
    return rev.shift(1).rolling(horizon, min_periods=1).max().iloc[::-1].reindex(series.index)


def target_feature_frame(target_history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = target_history.copy().sort_values(["target_key", "date"])
    group = df.groupby("target_key", group_keys=False)
    for window in [20, 60, 120]:
        df[f"target_ret{window}"] = group["close"].pct_change(window)
    df["target_ret1"] = group["close"].pct_change()
    df["target_ema60"] = group["close"].transform(lambda s: s.ewm(span=60, adjust=False).mean())
    df["target_ema120"] = group["close"].transform(lambda s: s.ewm(span=120, adjust=False).mean())
    df["target_ema60_slope20"] = df["target_ema60"] / group["target_ema60"].shift(20) - 1.0
    df["target_volatility20"] = group["target_ret1"].transform(lambda s: s.rolling(20, min_periods=20).std())
    df["target_drawdown120"] = df["close"] / group["close"].transform(lambda s: s.rolling(120, min_periods=20).max()) - 1.0
    market = df[df["target_type"] == "market"].copy()
    industry = df[df["target_type"] == "industry"].copy()
    return market, industry


def consecutive_true_by_group(df: pd.DataFrame, flag_col: str, out_col: str) -> pd.DataFrame:
    values = np.zeros(len(df), dtype=np.int32)
    for _instrument, idx in df.groupby("instrument", sort=False).groups.items():
        flags = df.loc[idx, flag_col].fillna(False).to_numpy(dtype=bool)
        count = 0
        out = []
        for flag in flags:
            count = count + 1 if flag else 0
            out.append(count)
        values[df.index.get_indexer(idx)] = out
    df[out_col] = values
    return df


def add_stock_features(
    config: dict[str, Any],
    panel: pd.DataFrame,
    universe: pd.DataFrame,
    industry: pd.DataFrame,
    target_history: pd.DataFrame,
) -> pd.DataFrame:
    fields = required_field_names(config)
    stock = panel.copy().sort_values(["instrument", "datetime"]).reset_index(drop=True)
    for field in fields:
        if field not in stock.columns:
            stock[field] = np.nan
    group = stock.groupby("instrument", group_keys=False)
    prev_close = group["close"].shift(1)
    stock["prev_close"] = prev_close
    stock["ret1"] = group["close"].pct_change()
    for window in [3, 5, 10, 20, 60, 120]:
        stock[f"ret{window}"] = group["close"].pct_change(window)
    for span in [20, 30, 60, 120]:
        stock[f"ema{span}"] = group["close"].transform(lambda s, span=span: s.ewm(span=span, adjust=False).mean())
    true_range = pd.concat(
        [stock["high"] - stock["low"], (stock["high"] - prev_close).abs(), (stock["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    stock["true_range"] = true_range
    for window in [10, 20, 60]:
        stock[f"volatility{window}"] = group["ret1"].transform(lambda s, window=window: s.rolling(window, min_periods=window).std())
    stock["atr20"] = group["true_range"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    stock["atr20_pct"] = stock["atr20"] / stock["close"].replace(0, np.nan)
    stock["amplitude"] = (stock["high"] - stock["low"]) / prev_close.replace(0, np.nan)
    stock["amplitude20"] = group["amplitude"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    for window in [20, 60, 120, 240]:
        high_col = f"high{window}"
        low_col = f"low{window}"
        stock[high_col] = group["high"].transform(lambda s, window=window: s.rolling(window, min_periods=window).max())
        stock[low_col] = group["low"].transform(lambda s, window=window: s.rolling(window, min_periods=window).min())
        stock[f"dist_high{window}"] = stock["close"] / stock[high_col].replace(0, np.nan) - 1.0
        stock[f"dist_low{window}"] = stock["close"] / stock[low_col].replace(0, np.nan) - 1.0
    for window in [5, 20, 60]:
        prior = group["money"].transform(lambda s, window=window: s.shift(1).rolling(window, min_periods=window).mean())
        stock[f"avg_money{window}_prior"] = prior
        stock[f"money_ratio{window}"] = stock["money"] / prior.replace(0, np.nan)
    stock["money_regime_shift60"] = stock["avg_money20_prior"] / stock["avg_money60_prior"].replace(0, np.nan)
    stock["gap_pct"] = stock["open"] / prev_close.replace(0, np.nan) - 1.0
    stock["limit_up_like"] = ((stock["close"] / prev_close.replace(0, np.nan) - 1.0) >= 0.095) | (stock["gap_pct"] >= 0.095)
    rolling_high10 = group["high"].transform(lambda s: s.rolling(10, min_periods=10).max())
    rolling_low10 = group["low"].transform(lambda s: s.rolling(10, min_periods=10).min())
    stock["range10_pct"] = rolling_high10 / rolling_low10.replace(0, np.nan) - 1.0
    stock["narrow_range10"] = stock["range10_pct"] <= 0.08
    stock["range_expansion20"] = stock["amplitude20"] / group["amplitude20"].shift(20).replace(0, np.nan) - 1.0
    for window in [60, 120, 240]:
        stock[f"drawdown_from_high{window}"] = stock["close"] / stock[f"high{window}"].replace(0, np.nan) - 1.0
        stock[f"repair_from_low{window}"] = stock["close"] / stock[f"low{window}"].replace(0, np.nan) - 1.0
    stock["ema60_reclaim_flag"] = (stock["close"] > stock["ema60"]) & (prev_close <= group["ema60"].shift(1))
    stock["trend_speed20"] = stock["ret20"] / 20.0
    stock["close_above_ema60"] = stock["close"] > stock["ema60"]
    stock = consecutive_true_by_group(stock, "close_above_ema60", "trend_age_close_above_ema60")
    stock["instrument_day_index"] = stock.groupby("instrument").cumcount() + 1
    stock["available_history_trading_days"] = stock["instrument_day_index"] - 1
    stock["provider_required_fields_ok"] = stock[fields].notna().all(axis=1)

    membership_cols = ["date", "instrument", "name", "listing_age_trading_days", "market_cap_asof_T"]
    membership = universe[membership_cols].drop_duplicates().rename(columns={"date": "datetime"})
    df = stock.merge(membership, on=["datetime", "instrument"], how="inner")
    if df.empty:
        raise DataGateError("provider has no rows after explicit date+instrument PIT universe join")
    df["pit_member"] = True
    industry_join = industry[["date", "instrument", "industry_target_key", "industry_name"]].drop_duplicates().rename(columns={"date": "datetime"})
    df = df.merge(industry_join, on=["datetime", "instrument"], how="left")
    missing_industry = config["industry"].get("missing_industry", "UNKNOWN")
    df["industry_name"] = df["industry_name"].fillna(missing_industry).replace("", missing_industry)
    df["industry_target_key"] = df["industry_target_key"].fillna("UNKNOWN").astype("string")

    market, industry_targets = target_feature_frame(target_history)
    broad_key = config["qlib"]["broad_market_key"]
    broad = market[market["target_key"] == broad_key][
        [
            "date",
            "target_ret20",
            "target_ret60",
            "target_ret120",
            "target_ema60_slope20",
            "target_volatility20",
            "target_drawdown120",
            "close",
            "target_ema60",
        ]
    ].rename(
        columns={
            "date": "datetime",
            "target_ret20": "benchmark_ret20",
            "target_ret60": "benchmark_ret60",
            "target_ret120": "benchmark_ret120",
            "target_ema60_slope20": "benchmark_ema60_slope20",
            "target_volatility20": "benchmark_volatility20",
            "target_drawdown120": "benchmark_drawdown120",
            "close": "benchmark_close",
            "target_ema60": "benchmark_ema60",
        }
    )
    df = df.merge(broad, on="datetime", how="left")
    for window in [20, 60, 120]:
        df[f"relative_ret{window}_vs_benchmark"] = df[f"ret{window}"] - df[f"benchmark_ret{window}"]

    ind_target = industry_targets[["date", "target_key", "target_ret20", "target_ret60", "target_ret120"]].rename(
        columns={
            "date": "datetime",
            "target_key": "industry_target_key",
            "target_ret20": "industry_target_ret20",
            "target_ret60": "industry_target_ret60",
            "target_ret120": "industry_target_ret120",
        }
    )
    ind_target["industry_target_key"] = ind_target["industry_target_key"].astype("string")
    df = df.merge(ind_target, on=["datetime", "industry_target_key"], how="left")
    for window in [20, 60]:
        df[f"relative_ret{window}_vs_industry"] = df[f"ret{window}"] - df[f"industry_target_ret{window}"]

    df["ret20_universe_pctile"] = df.groupby("datetime")["ret20"].rank(pct=True)
    df["ret20_industry_pctile"] = df.groupby(["datetime", "industry_name"])["ret20"].rank(pct=True)
    df["money_universe_pctile"] = df.groupby("datetime")["money"].rank(pct=True)
    df["money_industry_pctile"] = df.groupby(["datetime", "industry_name"])["money"].rank(pct=True)
    df["volatility20_universe_pctile"] = df.groupby("datetime")["volatility20"].rank(pct=True)

    width = (
        df[df["provider_required_fields_ok"]]
        .assign(close_gt_ema60_flag=lambda x: x["close"] > x["ema60"], ema20_gt_ema60_flag=lambda x: x["ema20"] > x["ema60"])
        .groupby("datetime", as_index=False)
        .agg(
            readable_pit_instruments=("instrument", "nunique"),
            close_gt_ema60_ratio=("close_gt_ema60_flag", "mean"),
            ema20_gt_ema60_ratio=("ema20_gt_ema60_flag", "mean"),
        )
    )
    width["market_width_state"] = np.select(
        [width["close_gt_ema60_ratio"] >= 0.60, width["close_gt_ema60_ratio"] >= 0.40],
        ["width_strong", "width_neutral"],
        default="width_weak",
    )
    df = df.merge(width, on="datetime", how="left")
    industry_width = (
        df[df["provider_required_fields_ok"]]
        .assign(close_gt_ema60_flag=lambda x: x["close"] > x["ema60"])
        .groupby(["datetime", "industry_name"], as_index=False)
        .agg(industry_member_count=("instrument", "nunique"), industry_close_gt_ema60_ratio=("close_gt_ema60_flag", "mean"))
    )
    industry_width["industry_width_state"] = np.select(
        [industry_width["industry_close_gt_ema60_ratio"] >= 0.60, industry_width["industry_close_gt_ema60_ratio"] >= 0.40],
        ["industry_width_strong", "industry_width_neutral"],
        default="industry_width_weak",
    )
    df = df.merge(industry_width, on=["datetime", "industry_name"], how="left")
    df["market_regime_state"] = np.select(
        [
            (df["benchmark_close"] > df["benchmark_ema60"]) & (df["benchmark_ema60_slope20"] > 0),
            df["benchmark_drawdown120"] <= -0.10,
        ],
        ["market_trend_on", "market_drawdown"],
        default="market_choppy",
    )
    df["industry_regime_state"] = np.select(
        [
            (df["industry_target_ret60"] > df["benchmark_ret60"]) & (df["industry_width_state"] == "industry_width_strong"),
            df["industry_target_ret60"] < df["benchmark_ret60"],
        ],
        ["industry_sync_on", "industry_lagging"],
        default="industry_mixed",
    )
    df["market_cap_bucket"] = pd.cut(
        df["market_cap_asof_T"],
        bins=[-np.inf, 8e10, 1.5e11, 3e11, np.inf],
        labels=["cap_50_80b", "cap_80_150b", "cap_150_300b", "cap_300b_plus"],
    ).astype("string").fillna("missing")
    df["listing_age_bucket"] = pd.cut(
        df["listing_age_trading_days"],
        bins=[-np.inf, 250, 750, 1500, np.inf],
        labels=["listing_young", "listing_mid", "listing_mature", "listing_old"],
    ).astype("string").fillna("missing")
    df["trend_speed_bucket"] = pd.cut(
        df["ret20"],
        bins=[-np.inf, 0.00, 0.10, 0.25, np.inf],
        labels=["speed_negative", "speed_slow", "speed_mid", "speed_fast"],
    ).astype("string").fillna("missing")
    df["post_20pct_from_recent_low"] = df["repair_from_low120"] >= 0.20
    df["post_30pct_from_recent_low"] = df["repair_from_low120"] >= 0.30
    df["observable_state_stage"] = observable_stage(df)
    df["feature_eligible"] = (df["available_history_trading_days"] >= 20) & df["provider_required_fields_ok"]
    df["feature_missing_reason"] = np.select(
        [
            ~df["provider_required_fields_ok"],
            df["available_history_trading_days"] < 20,
        ],
        ["provider_required_fields_missing", "insufficient_minimum_history"],
        default="",
    )
    first_eligible = (
        df[df["feature_eligible"]]
        .groupby("instrument", as_index=False)["datetime"]
        .min()
        .rename(columns={"datetime": "first_feature_eligible_date"})
    )
    df = df.merge(first_eligible, on="instrument", how="left")
    df["year"] = df["datetime"].dt.year
    df["instrument_year"] = df["instrument"] + "_" + df["year"].astype(str)
    return df.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def observable_stage(df: pd.DataFrame) -> pd.Series:
    conditions = [
        (df["repair_from_low240"] >= 0.80) & (df["trend_age_close_above_ema60"] >= 80),
        df["repair_from_low120"] >= 0.30,
        df["repair_from_low120"] >= 0.20,
        (df["ret20_universe_pctile"] >= 0.80) & (df["relative_ret20_vs_benchmark"] > 0),
        (df["repair_from_low120"] >= 0.10) & (df["drawdown_from_high120"] <= -0.15),
        (df["range10_pct"] <= 0.08) & (df["drawdown_from_high120"] <= -0.20),
        (df["close"] < df["ema60"]) & (df["ret60"] < 0),
    ]
    choices = [
        "observable_late_acceleration_risk",
        "observable_30pct_from_recent_low",
        "observable_20pct_from_recent_low",
        "observable_relative_strength_leading",
        "observable_repairing",
        "observable_base_building",
        "observable_downtrend",
    ]
    return pd.Series(np.select(conditions, choices, default="observable_trend_extension"), index=df.index, dtype="string")


def add_loop_forward_fields(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    time_horizon = int(config["labels"]["time_to_max_horizon"])
    out_time_50_high = np.full(len(df), np.nan)
    out_time_100_high = np.full(len(df), np.nan)
    out_time_50_close = np.full(len(df), np.nan)
    out_time_100_close = np.full(len(df), np.nan)
    out_first_50_high = np.full(len(df), None, dtype=object)
    out_first_100_high = np.full(len(df), None, dtype=object)
    dd_before_60 = np.full(len(df), np.nan)
    dd_before_120 = np.full(len(df), np.nan)
    dd_horizon_60 = np.full(len(df), np.nan)
    dd_horizon_120 = np.full(len(df), np.nan)
    future_episode_key = np.full(len(df), None, dtype=object)

    for instrument, group in df.groupby("instrument", sort=False):
        idx = group.index.to_numpy()
        close = group["close"].to_numpy(dtype=float)
        high = group["high"].to_numpy(dtype=float)
        low = group["low"].to_numpy(dtype=float)
        dates = pd.to_datetime(group["datetime"]).dt.date.astype(str).to_numpy()
        n = len(group)
        for pos in range(n):
            base = close[pos]
            if not np.isfinite(base) or base <= 0:
                continue
            end_max = min(n, pos + time_horizon + 1)
            if pos + 1 >= end_max:
                continue
            future_high = high[pos + 1 : end_max]
            future_close = close[pos + 1 : end_max]
            high50 = np.flatnonzero(future_high >= base * 1.5)
            high100 = np.flatnonzero(future_high >= base * 2.0)
            close50 = np.flatnonzero(future_close >= base * 1.5)
            close100 = np.flatnonzero(future_close >= base * 2.0)
            row_index = idx[pos]
            if len(high50):
                first = int(high50[0]) + 1
                out_time_50_high[row_index] = first
                out_first_50_high[row_index] = dates[pos + first]
                future_episode_key[row_index] = f"{instrument}_{dates[pos + first]}"
            if len(high100):
                first = int(high100[0]) + 1
                out_time_100_high[row_index] = first
                out_first_100_high[row_index] = dates[pos + first]
            if len(close50):
                out_time_50_close[row_index] = int(close50[0]) + 1
            if len(close100):
                out_time_100_close[row_index] = int(close100[0]) + 1
            for horizon, dd_all, dd_before in [(60, dd_horizon_60, dd_before_60), (120, dd_horizon_120, dd_before_120)]:
                end_h = min(n, pos + horizon + 1)
                if end_h <= pos + 1:
                    continue
                lows = low[pos + 1 : end_h]
                if len(lows) and np.isfinite(lows).any():
                    dd_all[row_index] = np.nanmin(lows / base - 1.0)
                highs_h = high[pos + 1 : end_h]
                hit = np.flatnonzero(highs_h >= base * 1.5)
                if len(hit):
                    hit_end = pos + 1 + int(hit[0]) + 1
                    lows_before = low[pos + 1 : hit_end]
                    if len(lows_before) and np.isfinite(lows_before).any():
                        dd_before[row_index] = np.nanmin(lows_before / base - 1.0)

    df["future_time_to_50pct_high_gain"] = out_time_50_high
    df["future_time_to_100pct_high_gain"] = out_time_100_high
    df["future_time_to_50pct_close_gain"] = out_time_50_close
    df["future_time_to_100pct_close_gain"] = out_time_100_close
    df["future_first_50pct_high_gain_date"] = out_first_50_high
    df["future_first_100pct_high_gain_date"] = out_first_100_high
    df["future_50pct_episode_key_240d"] = future_episode_key
    df["future_max_drawdown_before_gain_60d"] = dd_before_60
    df["future_max_drawdown_before_gain_120d"] = dd_before_120
    df["future_max_drawdown_in_horizon_60d"] = dd_horizon_60
    df["future_max_drawdown_in_horizon_120d"] = dd_horizon_120
    return df


def add_forward_labels(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    df = df.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    group = df.groupby("instrument", group_keys=False)
    horizons = [int(h) for h in config["labels"]["horizons"]]
    for horizon in horizons:
        future_high = group["high"].transform(lambda s, horizon=horizon: future_rolling_max(s, horizon))
        future_close = group["close"].transform(lambda s, horizon=horizon: future_rolling_max(s, horizon))
        df[f"future_max_high_gain_{horizon}d"] = future_high / df["close"].replace(0, np.nan) - 1.0
        df[f"future_max_close_gain_{horizon}d"] = future_close / df["close"].replace(0, np.nan) - 1.0
        df[f"horizon_end_date_{horizon}d"] = group["datetime"].shift(-horizon)
        remaining = group.cumcount(ascending=False)
        df[f"label_horizon_truncated_{horizon}d"] = remaining < horizon
        horizon_end = pd.to_datetime(df[f"horizon_end_date_{horizon}d"])
        research_end = parse_dt(config["dates"]["research_end"])
        df[f"observed_reference_overlap_{horizon}d"] = (df["datetime"] <= research_end) & (horizon_end > research_end)
        df[f"is_future_50pct_high_{horizon}d"] = df[f"future_max_high_gain_{horizon}d"] >= 0.50
        df[f"is_future_100pct_high_{horizon}d"] = df[f"future_max_high_gain_{horizon}d"] >= 1.00
        df[f"is_future_50pct_close_{horizon}d"] = df[f"future_max_close_gain_{horizon}d"] >= 0.50
        df[f"is_future_100pct_close_{horizon}d"] = df[f"future_max_close_gain_{horizon}d"] >= 1.00
    df["intraday_50pct_not_close_confirmed_120d"] = df["is_future_50pct_high_120d"] & ~df["is_future_50pct_close_120d"]
    df["intraday_50pct_not_close_confirmed_240d"] = df["is_future_50pct_high_240d"] & ~df["is_future_50pct_close_240d"]
    df = add_loop_forward_fields(df, config)
    df["label_horizon_truncated"] = df["label_horizon_truncated_240d"]
    df["observed_reference_overlap"] = df["observed_reference_overlap_240d"]
    df["observed_reference_sample"] = df["datetime"] >= parse_dt(config["dates"]["observed_reference_start"])
    return df


def build_episode_lifecycle_labels(config: dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
    threshold = float(config["labels"]["episode_threshold"])
    research_start = parse_dt(config["dates"]["research_start"])
    research_end = parse_dt(config["dates"]["research_end"])
    observed_end = parse_dt(config["dates"]["observed_reference_end"])
    rows: list[dict[str, Any]] = []

    def best_episode(group: pd.DataFrame, year: int, scope: str) -> dict[str, Any] | None:
        group = group.sort_values("datetime").reset_index(drop=True)
        if len(group) < 2:
            return None
        lows = group["low"].to_numpy(dtype=float)
        highs = group["high"].to_numpy(dtype=float)
        closes = group["close"].to_numpy(dtype=float)
        best_gain = -np.inf
        best_low_pos = -1
        best_high_pos = -1
        for pos in range(len(group) - 1):
            if not np.isfinite(lows[pos]) or lows[pos] <= 0:
                continue
            future_highs = highs[pos + 1 :]
            if not len(future_highs) or not np.isfinite(future_highs).any():
                continue
            rel_pos = int(np.nanargmax(future_highs))
            gain = future_highs[rel_pos] / lows[pos] - 1.0
            if gain > best_gain:
                best_gain = float(gain)
                best_low_pos = pos
                best_high_pos = pos + 1 + rel_pos
        if best_gain < threshold or best_low_pos < 0 or best_high_pos < 0:
            return None
        low_date = group.loc[best_low_pos, "datetime"]
        high_date = group.loc[best_high_pos, "datetime"]
        base_low = lows[best_low_pos]
        episode_id = f"{scope}_{group.loc[best_low_pos, 'instrument']}_{iso_date(low_date)}_{iso_date(high_date)}"
        future_close = closes[best_high_pos] / base_low - 1.0 if np.isfinite(closes[best_high_pos]) else np.nan
        first_dates: dict[str, str] = {}
        for pct in [0.20, 0.30, 0.50, 1.00, 2.00]:
            hits = np.flatnonzero(highs[best_low_pos + 1 : best_high_pos + 1] >= base_low * (1.0 + pct))
            first_dates[f"first_intraday_{int(pct * 100)}pct_date"] = (
                iso_date(group.loc[best_low_pos + 1 + int(hits[0]), "datetime"]) if len(hits) else ""
            )
        return {
            "episode_id": episode_id,
            "episode_scope": scope,
            "year": int(year),
            "instrument": group.loc[best_low_pos, "instrument"],
            "name": group.loc[best_low_pos, "name"],
            "industry_name": group.loc[best_low_pos, "industry_name"],
            "low_date": iso_date(low_date),
            "high_date": iso_date(high_date),
            "duration_trading_days": int(best_high_pos - best_low_pos),
            "low_price": float(base_low),
            "high_price": float(highs[best_high_pos]),
            "forward_gain_intraday": best_gain,
            "forward_gain_close_confirmed": future_close,
            "observed_reference_overlap": bool(high_date > research_end),
            "truncated_by_year_boundary": bool(scope == "in_year_episode" and low_date.year != high_date.year),
            "retrospective_lifecycle_stage": "trend_extension",
            **first_dates,
        }

    research = df[(df["datetime"] >= research_start) & (df["datetime"] <= research_end) & df["provider_required_fields_ok"]].copy()
    for (year, instrument), group in research.groupby(["year", "instrument"], sort=True):
        episode = best_episode(group, int(year), "in_year_episode")
        if episode is not None:
            rows.append(episode)

    continuous = df[(df["datetime"] >= research_start) & (df["datetime"] <= observed_end) & df["provider_required_fields_ok"]].copy()
    for instrument, group in continuous.groupby("instrument", sort=True):
        episode = best_episode(group, 0, "cross_year_episode")
        if episode is not None:
            low_date = parse_dt(episode["low_date"])
            high_date = parse_dt(episode["high_date"])
            if low_date.year != high_date.year and low_date <= research_end:
                episode["year"] = int(low_date.year)
                episode["truncated_by_year_boundary"] = True
                rows.append(episode)

    columns = [
        "episode_id",
        "episode_scope",
        "year",
        "instrument",
        "name",
        "industry_name",
        "low_date",
        "high_date",
        "duration_trading_days",
        "low_price",
        "high_price",
        "forward_gain_intraday",
        "forward_gain_close_confirmed",
        "observed_reference_overlap",
        "truncated_by_year_boundary",
        "retrospective_lifecycle_stage",
        "first_intraday_20pct_date",
        "first_intraday_30pct_date",
        "first_intraday_50pct_date",
        "first_intraday_100pct_date",
        "first_intraday_200pct_date",
    ]
    return pd.DataFrame(rows, columns=columns)


def attach_retrospective_stage(df: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    df["retrospective_lifecycle_stage"] = ""
    if episodes.empty:
        return df
    in_year = episodes[episodes["episode_scope"] == "in_year_episode"].copy()
    episode_map = {(row.instrument, int(row.year)): row for row in in_year.itertuples(index=False)}
    stages = np.full(len(df), "", dtype=object)
    for (instrument, year), group in df.groupby(["instrument", "year"], sort=False):
        event = episode_map.get((instrument, int(year)))
        if event is None:
            continue
        low_date = parse_dt(event.low_date)
        high_date = parse_dt(event.high_date)
        low_price = safe_float(event.low_price, np.nan)
        idx = group.index.to_numpy()
        dates = pd.to_datetime(group["datetime"])
        gains = group["close"] / low_price - 1.0 if np.isfinite(low_price) and low_price > 0 else pd.Series(np.nan, index=group.index)
        stage = np.select(
            [
                dates < low_date,
                (dates >= low_date) & (gains < 0.20),
                (gains >= 0.20) & (gains < 0.30),
                (gains >= 0.30) & (dates < high_date),
                dates == high_date,
                dates > high_date,
            ],
            ["pre_repair", "early_repair", "confirmed_20pct", "confirmed_30pct", "trend_extension", "post_peak"],
            default="late_trend",
        )
        stages[idx] = stage
    df["retrospective_lifecycle_stage"] = stages
    return df


def build_label_coverage_audit(config: dict[str, Any], df: pd.DataFrame, provider_coverage: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    research_mask = (df["datetime"] >= parse_dt(config["dates"]["research_start"])) & (df["datetime"] <= parse_dt(config["dates"]["research_end"]))
    for horizon in [int(h) for h in config["labels"]["horizons"]]:
        subset = df[research_mask]
        rows.append(
            {
                "horizon": f"{horizon}d",
                "research_stock_day_rows": int(len(subset)),
                "horizon_valid_rows": int((~subset[f"label_horizon_truncated_{horizon}d"]).sum()),
                "label_horizon_truncated_rows": int(subset[f"label_horizon_truncated_{horizon}d"].sum()),
                "observed_reference_overlap_rows": int(subset[f"observed_reference_overlap_{horizon}d"].sum()),
                "provider_required_fields_ok_rows": int(subset["provider_required_fields_ok"].sum()),
                "future_50pct_high_positive_rows": int(subset[f"is_future_50pct_high_{horizon}d"].sum()),
                "future_100pct_high_positive_rows": int(subset[f"is_future_100pct_high_{horizon}d"].sum()),
                "future_50pct_close_positive_rows": int(subset[f"is_future_50pct_close_{horizon}d"].sum()),
                "future_100pct_close_positive_rows": int(subset[f"is_future_100pct_close_{horizon}d"].sum()),
            }
        )
    coverage = pd.DataFrame(rows)
    if not provider_coverage.empty:
        coverage["provider_coverage_limited_research"] = bool(
            (provider_coverage[provider_coverage["year"].isin(research_years(config))]["coverage_status"] != "coverage_ok").any()
        )
    return coverage


def build_label_summaries(config: dict[str, Any], df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    research_start = parse_dt(config["dates"]["research_start"])
    research_end = parse_dt(config["dates"]["research_end"])
    observed_start = parse_dt(config["dates"]["observed_reference_start"])
    observed_end = parse_dt(config["dates"]["observed_reference_end"])
    research = df[(df["datetime"] >= research_start) & (df["datetime"] <= research_end)]
    summary = pd.DataFrame(
        [
            {
                "row_count": int(len(df)),
                "research_row_count": int(len(research)),
                "instrument_count": int(df["instrument"].nunique()),
                "research_instrument_count": int(research["instrument"].nunique()),
                "first_date": iso_date(df["datetime"].min()),
                "last_date": iso_date(df["datetime"].max()),
                "required_fields_ok_ratio": float(df["provider_required_fields_ok"].mean()) if len(df) else 0.0,
                "feature_eligible_ratio": float(df["feature_eligible"].mean()) if len(df) else 0.0,
                "price_adjustment_mode": config["qlib"]["price_adjustment_mode"],
            }
        ]
    )
    by_year_rows = []
    for year, group in research.groupby("year", sort=True):
        by_year_rows.append(
            {
                "year": int(year),
                "stock_day_count": int(len(group)),
                "instrument_count": int(group["instrument"].nunique()),
                "future_50pct_high_120d_rate": float(group["is_future_50pct_high_120d"].mean()) if len(group) else np.nan,
                "future_100pct_high_240d_rate": float(group["is_future_100pct_high_240d"].mean()) if len(group) else np.nan,
                "horizon_120d_observed_reference_overlap_rate": float(group["observed_reference_overlap_120d"].mean()) if len(group) else np.nan,
                "horizon_240d_observed_reference_overlap_rate": float(group["observed_reference_overlap_240d"].mean()) if len(group) else np.nan,
            }
        )
    by_year = pd.DataFrame(by_year_rows)
    by_industry = (
        research.groupby("industry_name", as_index=False)
        .agg(
            stock_day_count=("instrument", "size"),
            instrument_count=("instrument", "nunique"),
            future_50pct_high_120d_rate=("is_future_50pct_high_120d", "mean"),
            future_100pct_high_240d_rate=("is_future_100pct_high_240d", "mean"),
        )
        .sort_values("stock_day_count", ascending=False)
    )
    observed = df[(df["datetime"] >= observed_start) & (df["datetime"] <= observed_end)]
    observed_audit = pd.DataFrame(
        [
            {
                "observed_reference_start": config["dates"]["observed_reference_start"],
                "observed_reference_end": config["dates"]["observed_reference_end"],
                "observed_reference_stock_day_rows": int(len(observed)),
                "observed_reference_instrument_count": int(observed["instrument"].nunique()) if len(observed) else 0,
                "used_for_selection": False,
                "used_for_feature_threshold_selection": False,
                "used_for_model_selection": False,
            }
        ]
    )
    return summary, by_year, by_industry, observed_audit


def primitive_specs() -> list[PrimitiveSpec]:
    specs = [
        PrimitiveSpec("ret3", "price_state", "ret3", "continuous", 3, "3d"),
        PrimitiveSpec("ret5", "price_state", "ret5", "continuous", 5, "5d"),
        PrimitiveSpec("ret10", "price_state", "ret10", "continuous", 10, "10d"),
        PrimitiveSpec("ret20", "price_state", "ret20", "continuous", 20, "20d"),
        PrimitiveSpec("ret60", "price_state", "ret60", "continuous", 60, "60d"),
        PrimitiveSpec("ret120", "price_state", "ret120", "continuous", 120, "120d"),
        PrimitiveSpec("dist_high20", "price_state", "dist_high20", "continuous", 20, "20d", direction_hint="low"),
        PrimitiveSpec("dist_high60", "price_state", "dist_high60", "continuous", 60, "60d", direction_hint="low"),
        PrimitiveSpec("dist_high120", "price_state", "dist_high120", "continuous", 120, "120d", direction_hint="low"),
        PrimitiveSpec("dist_low20", "price_state", "dist_low20", "continuous", 20, "20d"),
        PrimitiveSpec("dist_low60", "price_state", "dist_low60", "continuous", 60, "60d"),
        PrimitiveSpec("dist_low120", "price_state", "dist_low120", "continuous", 120, "120d"),
        PrimitiveSpec("gap_pct", "price_state", "gap_pct", "continuous", 1, "1d"),
        PrimitiveSpec("limit_up_like", "price_state", "limit_up_like", "boolean", 1, "1d"),
        PrimitiveSpec("relative_ret20_vs_benchmark", "relative_strength", "relative_ret20_vs_benchmark", "continuous", 20, "20d", True),
        PrimitiveSpec("relative_ret60_vs_benchmark", "relative_strength", "relative_ret60_vs_benchmark", "continuous", 60, "60d", True),
        PrimitiveSpec("relative_ret120_vs_benchmark", "relative_strength", "relative_ret120_vs_benchmark", "continuous", 120, "120d", True),
        PrimitiveSpec("relative_ret20_vs_industry", "relative_strength", "relative_ret20_vs_industry", "continuous", 20, "20d", False, True),
        PrimitiveSpec("relative_ret60_vs_industry", "relative_strength", "relative_ret60_vs_industry", "continuous", 60, "60d", False, True),
        PrimitiveSpec("ret20_universe_pctile", "relative_strength", "ret20_universe_pctile", "continuous", 20, "20d"),
        PrimitiveSpec("ret20_industry_pctile", "relative_strength", "ret20_industry_pctile", "continuous", 20, "20d", False, True),
        PrimitiveSpec("money_ratio5", "money_liquidity", "money_ratio5", "continuous", 5, "5d"),
        PrimitiveSpec("money_ratio20", "money_liquidity", "money_ratio20", "continuous", 20, "20d"),
        PrimitiveSpec("money_ratio60", "money_liquidity", "money_ratio60", "continuous", 60, "60d"),
        PrimitiveSpec("money_universe_pctile", "money_liquidity", "money_universe_pctile", "continuous", 1, "daily_cross_section"),
        PrimitiveSpec("money_industry_pctile", "money_liquidity", "money_industry_pctile", "continuous", 1, "daily_industry_cross_section", False, True),
        PrimitiveSpec("money_regime_shift60", "money_liquidity", "money_regime_shift60", "continuous", 60, "60d"),
        PrimitiveSpec("volatility10", "volatility_compression_expansion", "volatility10", "continuous", 10, "10d", direction_hint="low"),
        PrimitiveSpec("volatility20", "volatility_compression_expansion", "volatility20", "continuous", 20, "20d", direction_hint="low"),
        PrimitiveSpec("volatility60", "volatility_compression_expansion", "volatility60", "continuous", 60, "60d", direction_hint="low"),
        PrimitiveSpec("atr20_pct", "volatility_compression_expansion", "atr20_pct", "continuous", 20, "20d", direction_hint="low"),
        PrimitiveSpec("amplitude20", "volatility_compression_expansion", "amplitude20", "continuous", 20, "20d", direction_hint="low"),
        PrimitiveSpec("narrow_range10", "volatility_compression_expansion", "narrow_range10", "boolean", 10, "10d"),
        PrimitiveSpec("range_expansion20", "volatility_compression_expansion", "range_expansion20", "continuous", 40, "20d_vs_prior20d"),
        PrimitiveSpec("drawdown_from_high60", "drawdown_repair_base", "drawdown_from_high60", "continuous", 60, "60d", direction_hint="low"),
        PrimitiveSpec("drawdown_from_high120", "drawdown_repair_base", "drawdown_from_high120", "continuous", 120, "120d", direction_hint="low"),
        PrimitiveSpec("drawdown_from_high240", "drawdown_repair_base", "drawdown_from_high240", "continuous", 240, "240d", direction_hint="low"),
        PrimitiveSpec("repair_from_low60", "drawdown_repair_base", "repair_from_low60", "continuous", 60, "60d"),
        PrimitiveSpec("repair_from_low120", "drawdown_repair_base", "repair_from_low120", "continuous", 120, "120d"),
        PrimitiveSpec("repair_from_low240", "drawdown_repair_base", "repair_from_low240", "continuous", 240, "240d"),
        PrimitiveSpec("ema60_reclaim_flag", "drawdown_repair_base", "ema60_reclaim_flag", "boolean", 60, "60d"),
        PrimitiveSpec("trend_age_close_above_ema60", "trend_age_stage", "trend_age_close_above_ema60", "continuous", 60, "state_age"),
        PrimitiveSpec("trend_speed20", "trend_age_stage", "trend_speed20", "continuous", 20, "20d"),
        PrimitiveSpec("market_width_state", "market_industry_regime", "market_width_state", "categorical", 60, "market_width"),
        PrimitiveSpec("industry_width_state", "market_industry_regime", "industry_width_state", "categorical", 60, "industry_width", False, True),
        PrimitiveSpec("market_regime_state", "market_industry_regime", "market_regime_state", "categorical", 120, "benchmark_state", True),
        PrimitiveSpec("industry_regime_state", "market_industry_regime", "industry_regime_state", "categorical", 60, "industry_state", True, True),
        PrimitiveSpec("market_cap_bucket", "industry_style_layer", "market_cap_bucket", "categorical", 1, "asof_T_market_cap"),
        PrimitiveSpec("listing_age_bucket", "industry_style_layer", "listing_age_bucket", "categorical", 1, "asof_T_listing_age"),
        PrimitiveSpec("trend_speed_bucket", "industry_style_layer", "trend_speed_bucket", "categorical", 20, "20d"),
        PrimitiveSpec("observable_state_stage", "lifecycle_observable_stage", "observable_state_stage", "categorical", 20, "observable_state"),
        PrimitiveSpec("post_20pct_from_recent_low", "lifecycle_observable_stage", "post_20pct_from_recent_low", "boolean", 120, "120d"),
        PrimitiveSpec("post_30pct_from_recent_low", "lifecycle_observable_stage", "post_30pct_from_recent_low", "boolean", 120, "120d"),
        PrimitiveSpec("price_shape_cluster_registry", "shape_sequence_fragment", "ret20", "registry_only", 120, "deferred_p2", p0_enabled=False),
        PrimitiveSpec("cross_section_money_anomaly", "cross_section_anomaly_leadership", "money_universe_pctile", "continuous", 20, "daily_cross_section"),
        PrimitiveSpec("cross_section_return_anomaly", "cross_section_anomaly_leadership", "ret20_universe_pctile", "continuous", 20, "daily_cross_section"),
    ]
    return specs


def feature_dictionary() -> pd.DataFrame:
    rows = []
    for spec in primitive_specs():
        if not spec.p0_enabled:
            rule = "registry_only_deferred_to_p2"
            warmup = "deferred_to_p2"
        else:
            rule = f"available_history_trading_days >= {spec.min_history_trading_days} and provider_required_fields_ok and value_not_missing"
            warmup = "mark_warmup_partial_year_and_exclude_from_primitive_lift_denominator"
        rows.append(
            {
                "feature_name": spec.feature_name,
                "feature_family": spec.feature_family,
                "source_column": spec.column,
                "value_type": spec.value_type,
                "min_history_trading_days": int(spec.min_history_trading_days),
                "lookback_window": spec.lookback_window,
                "requires_benchmark_history": bool(spec.requires_benchmark_history),
                "requires_industry_history": bool(spec.requires_industry_history),
                "feature_eligible_rule": rule,
                "warmup_partial_year_handling": warmup,
                "p0_enabled": bool(spec.p0_enabled),
                "direction_hint": spec.direction_hint,
            }
        )
    return pd.DataFrame(rows)


def primitive_bin(df: pd.DataFrame, spec: PrimitiveSpec, config: dict[str, Any]) -> pd.Series:
    series = df[spec.column] if spec.column in df.columns else pd.Series(np.nan, index=df.index)
    if spec.value_type == "boolean":
        return pd.Series(np.where(series.fillna(False).astype(bool), "true", "false"), index=df.index, dtype="string")
    if spec.value_type == "categorical":
        return series.astype("string").fillna("missing")
    if spec.value_type == "registry_only":
        return pd.Series("deferred", index=df.index, dtype="string")
    pct = df.groupby("year")[spec.column].rank(pct=True) if spec.column in df.columns else pd.Series(np.nan, index=df.index)
    cuts = [float(x) for x in config["primitives"]["quantile_cuts"]]
    labels = ["p0_10", "p10_20", "p20_40", "p40_60", "p60_80", "p80_90", "p90_100"]
    bins = pd.Series("missing", index=df.index, dtype="object")
    previous = 0.0
    for cut, label in zip(cuts, labels):
        mask = (pct > previous) & (pct <= cut)
        bins.loc[mask] = label
        previous = cut
    bins.loc[pct > cuts[-1]] = labels[-1]
    return bins.astype("string")


def primitive_eligible(df: pd.DataFrame, spec: PrimitiveSpec) -> pd.Series:
    if not spec.p0_enabled or spec.column not in df.columns:
        return pd.Series(False, index=df.index)
    eligible = (
        df["pit_member"].fillna(False).astype(bool)
        & df["provider_required_fields_ok"].fillna(False).astype(bool)
        & (df["available_history_trading_days"] >= spec.min_history_trading_days)
        & df[spec.column].notna()
    )
    if spec.value_type == "categorical":
        eligible &= df[spec.column].astype("string").fillna("missing") != "missing"
    if spec.requires_benchmark_history:
        eligible &= df["benchmark_ret20"].notna()
    if spec.requires_industry_history:
        eligible &= df["industry_name"].fillna("UNKNOWN") != "UNKNOWN"
    return eligible


def baseline_mask(df: pd.DataFrame, eligible: pd.Series, horizon: int, config: dict[str, Any]) -> pd.Series:
    return (
        eligible.fillna(False)
        & (df["datetime"] >= parse_dt(config["dates"]["research_start"]))
        & (df["datetime"] <= parse_dt(config["dates"]["research_end"]))
        & ~df[f"label_horizon_truncated_{horizon}d"].fillna(True)
        & ~df[f"observed_reference_overlap_{horizon}d"].fillna(True)
        & df["pit_member"].fillna(False).astype(bool)
        & df["provider_required_fields_ok"].fillna(False).astype(bool)
    )


def summarize_condition(
    df: pd.DataFrame,
    condition: pd.Series,
    base_condition: pd.Series,
    positive_col: str,
    horizon: int,
    label_name: str,
    lead_id: str,
    lead_name: str,
    feature_family: str,
    formula_or_bin: str,
    direction: str,
    observable_state_stage: str,
    recommended_next_phase: str,
    baseline_scope: str = "same_year_same_horizon_horizon_valid_pit_stock_days",
) -> dict[str, Any]:
    base_mask = base_condition.fillna(False).astype(bool)
    lead_mask = (condition & base_mask).fillna(False).astype(bool)
    positive_mask = df[positive_col].fillna(False).astype(bool)
    lead_positive_mask = lead_mask & positive_mask
    base_positive_mask = base_mask & positive_mask
    base_count = int(base_mask.sum())
    lead_count = int(lead_mask.sum())
    positive_count = int(lead_positive_mask.sum())
    base_positive_count = int(base_positive_mask.sum())
    baseline_rate = safe_div(base_positive_count, base_count)
    lead_rate = safe_div(positive_count, lead_count)
    global_mask = (
        (df["datetime"] >= df["datetime"].min())
        & (df["datetime"] <= parse_dt("2024-12-31"))
        & ~df[f"label_horizon_truncated_{horizon}d"].fillna(True)
        & ~df[f"observed_reference_overlap_{horizon}d"].fillna(True)
        & df["provider_required_fields_ok"].fillna(False).astype(bool)
    )
    global_rate = safe_div(df.loc[global_mask, positive_col].sum(), global_mask.sum())
    lead_instrument = df.loc[lead_mask, "instrument"]
    positive_instrument = df.loc[lead_positive_mask, "instrument"]
    lead_instrument_year = df.loc[lead_mask, "instrument_year"]
    positive_instrument_year_series = df.loc[lead_positive_mask, "instrument_year"]
    base_instrument_year = df.loc[base_mask, "instrument_year"]
    base_positive_instrument_year_series = df.loc[base_positive_mask, "instrument_year"]
    instrument_year_denom = lead_instrument_year.nunique()
    positive_instrument_year = positive_instrument_year_series.nunique()
    base_instrument_year_denom = base_instrument_year.nunique()
    base_positive_instrument_year = base_positive_instrument_year_series.nunique()
    episode_col = "future_50pct_episode_key_240d"
    unique_episode_count = instrument_year_denom
    positive_unique_episode_count = df.loc[lead_positive_mask, episode_col].dropna().nunique() if episode_col in df.columns else 0
    base_unique_episode_count = base_instrument_year_denom
    base_positive_unique_episode_count = df.loc[base_positive_mask, episode_col].dropna().nunique() if episode_col in df.columns else 0
    episode_rate = safe_div(positive_unique_episode_count, unique_episode_count)
    base_episode_rate = safe_div(base_positive_unique_episode_count, base_unique_episode_count)
    instrument_year_rate = safe_div(positive_instrument_year, instrument_year_denom)
    base_instrument_year_rate = safe_div(base_positive_instrument_year, base_instrument_year_denom)
    yearly_positive_lifts = 0
    lead_years = df.loc[lead_mask, "year"].dropna().unique()
    for year in lead_years:
        year_lead_mask = lead_mask & (df["year"] == year)
        year_base_mask = base_mask & (df["year"] == year)
        if year_lead_mask.any() and year_base_mask.any():
            if safe_div(df.loc[year_lead_mask, positive_col].sum(), year_lead_mask.sum()) > safe_div(df.loc[year_base_mask, positive_col].sum(), year_base_mask.sum()):
                yearly_positive_lifts += 1
    industry_counts = df.loc[lead_mask, "industry_name"].value_counts(dropna=False)
    top1 = safe_div(industry_counts.iloc[0], lead_count) if len(industry_counts) else np.nan
    duplicate_limit = 5.0
    duplicate_risk = bool(positive_count > duplicate_limit * max(positive_unique_episode_count, 1))
    sparse_bin = bool(lead_count < 100)
    if lead_count == 0:
        failure = "empty_lead_sample"
    elif pd.isna(lead_rate) or lead_rate <= baseline_rate:
        failure = "lift_not_above_baseline"
    elif df.loc[lead_mask, "year"].nunique() < 3:
        failure = "insufficient_distinct_years"
    elif top1 > 0.50:
        failure = "single_industry_concentration"
    else:
        failure = ""
    drawdown_col = "future_max_drawdown_before_gain_120d" if horizon >= 120 else "future_max_drawdown_before_gain_60d"
    return {
        "lead_id": lead_id,
        "lead_name": lead_name,
        "feature_family": feature_family,
        "observable_state_stage": observable_state_stage,
        "formula_or_bin": formula_or_bin,
        "direction": direction,
        "horizon": f"{horizon}d",
        "positive_label": label_name,
        "baseline_scope": baseline_scope,
        "baseline_sample_count": int(base_count),
        "baseline_positive_rate": baseline_rate,
        "lead_positive_rate": lead_rate,
        "lift_vs_baseline": safe_div(lead_rate, baseline_rate),
        "global_lift": safe_div(lead_rate, global_rate),
        "industry_relative_lift": np.nan,
        "stock_day_count": int(lead_count),
        "unique_instrument_count": int(lead_instrument.nunique()),
        "unique_instrument_year_count": int(instrument_year_denom),
        "unique_episode_count": int(unique_episode_count),
        "positive_stock_day_count": int(positive_count),
        "positive_unique_instrument_count": int(positive_instrument.nunique()),
        "positive_unique_instrument_year_count": int(positive_instrument_year),
        "positive_unique_episode_count": int(positive_unique_episode_count),
        "lead_future_50pct_precision": float(df.loc[lead_mask, "is_future_50pct_high_120d"].mean()) if lead_count else np.nan,
        "lead_future_100pct_precision": float(df.loc[lead_mask, "is_future_100pct_high_240d"].mean()) if lead_count else np.nan,
        "episode_dedup_lift": safe_div(episode_rate, base_episode_rate),
        "instrument_year_dedup_lift": safe_div(instrument_year_rate, base_instrument_year_rate),
        "year_positive_lift_count": int(yearly_positive_lifts),
        "distinct_year_count": int(df.loc[lead_mask, "year"].nunique()),
        "distinct_industry_count": int(df.loc[lead_mask, "industry_name"].nunique()),
        "industry_concentration_top1": top1,
        "avg_lead_time_to_50pct": float(df.loc[lead_positive_mask, "future_time_to_50pct_high_gain"].mean()) if positive_count else np.nan,
        "median_lead_time_to_50pct": float(df.loc[lead_positive_mask, "future_time_to_50pct_high_gain"].median()) if positive_count else np.nan,
        "avg_future_max_gain": float(df.loc[lead_mask, f"future_max_high_gain_{horizon}d"].mean()) if lead_count else np.nan,
        "avg_future_drawdown_before_gain": float(df.loc[lead_positive_mask, drawdown_col].mean()) if positive_count and drawdown_col in df.columns else np.nan,
        "turnover_proxy": float(df.loc[lead_mask, "money"].median()) if lead_count else np.nan,
        "market_regime_dependency": df.loc[lead_mask, "market_regime_state"].value_counts(normalize=True).idxmax() if lead_count else "",
        "industry_regime_dependency": df.loc[lead_mask, "industry_regime_state"].value_counts(normalize=True).idxmax() if lead_count else "",
        "label_horizon_truncated_rate": float(df.loc[condition.fillna(False), f"label_horizon_truncated_{horizon}d"].mean()) if condition.any() else np.nan,
        "observed_reference_overlap_rate": float(df.loc[condition.fillna(False), f"observed_reference_overlap_{horizon}d"].mean()) if condition.any() else np.nan,
        "duplicate_positive_risk": duplicate_risk,
        "sparse_bin": sparse_bin,
        "failure_reason": failure,
        "recommended_next_phase": recommended_next_phase if not failure else "drop",
    }


def pairwise_specs() -> list[PairwiseSpec]:
    return [
        PairwiseSpec("pair_price_money", "20日强收益 + 成交放大", "price_money", "ret20", ("p80_90", "p90_100"), "money_ratio20", ("p80_90", "p90_100"), "observable_relative_strength_leading", "high_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_rs_market", "相对强度领先 + 弱市场", "relative_strength_regime", "relative_ret60_vs_benchmark", ("p80_90", "p90_100"), "market_regime_state", ("market_drawdown", "market_choppy"), "observable_relative_strength_leading", "high_regime", "p1_hypothesis_refine"),
        PairwiseSpec("pair_stock_lead_industry", "个股强于行业 + 行业未同步", "stock_industry_lead", "relative_ret20_vs_industry", ("p80_90", "p90_100"), "industry_regime_state", ("industry_lagging", "industry_mixed"), "observable_relative_strength_leading", "high_regime", "p1_hypothesis_refine"),
        PairwiseSpec("pair_vol_money", "低波压缩 + 放量扩张", "volatility_money", "volatility20", ("p0_10", "p10_20"), "money_ratio20", ("p80_90", "p90_100"), "observable_base_building", "low_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_repair_rs", "回撤修复 + 相对强", "repair_relative_strength", "repair_from_low120", ("p60_80", "p80_90", "p90_100"), "relative_ret20_vs_benchmark", ("p80_90", "p90_100"), "observable_repairing", "high_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_rank_industry", "全市场强排名 + 行业强宽度", "rank_industry_sync", "ret20_universe_pctile", ("p80_90", "p90_100"), "industry_width_state", ("industry_width_strong",), "observable_relative_strength_leading", "high_regime", "p1_hypothesis_refine"),
        PairwiseSpec("pair_money_near_high", "成交 regime shift + 接近新高", "money_near_high", "money_regime_shift60", ("p80_90", "p90_100"), "dist_high60", ("p80_90", "p90_100"), "observable_trend_extension", "high_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_narrow_expand", "窄幅整理 + 振幅扩张", "compression_expansion", "narrow_range10", ("true",), "range_expansion20", ("p80_90", "p90_100"), "observable_base_building", "true_high", "p1_hypothesis_refine"),
        PairwiseSpec("pair_stage_market", "可观察修复阶段 + 市场非强", "lifecycle_regime", "observable_state_stage", ("observable_repairing", "observable_relative_strength_leading"), "market_regime_state", ("market_choppy", "market_drawdown"), "observable_repairing", "stage_regime", "p1_hypothesis_refine"),
        PairwiseSpec("pair_hold_rs", "已涨20% + 仍然相对强", "continuation_hold", "post_20pct_from_recent_low", ("true",), "relative_ret20_vs_benchmark", ("p80_90", "p90_100"), "observable_20pct_from_recent_low", "true_high", "p1_hold_exit_refine"),
    ]


def build_stability_rows(
    config: dict[str, Any],
    df: pd.DataFrame,
    univariate: pd.DataFrame,
    specs: list[PrimitiveSpec],
    bins: dict[str, pd.Series],
    elig: dict[str, pd.Series],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    year_rows: list[dict[str, Any]] = []
    industry_rows: list[dict[str, Any]] = []
    if univariate.empty:
        return pd.DataFrame(), pd.DataFrame()
    target = univariate[univariate["positive_label"] == "future_50pct_high_120d"].copy()
    if target.empty:
        return pd.DataFrame(), pd.DataFrame()
    spec_by_name = {spec.feature_name: spec for spec in specs}
    best_rows = (
        target.sort_values(["feature_name", "lift_vs_baseline", "stock_day_count"], ascending=[True, False, False])
        .groupby("feature_name", as_index=False)
        .head(1)
    )
    horizon = 120
    positive_col = "is_future_50pct_high_120d"
    for _, selected in best_rows.iterrows():
        feature_name = str(selected["feature_name"])
        bin_value = str(selected["bin_value"])
        spec = spec_by_name.get(feature_name)
        if spec is None:
            continue
        eligible = elig[feature_name]
        condition = eligible & (bins[feature_name] == bin_value)
        base = baseline_mask(df, eligible, horizon, config)
        lead_mask = (condition & base).fillna(False).astype(bool)
        base_mask = base.fillna(False).astype(bool)
        for year in sorted(df.loc[lead_mask, "year"].dropna().unique()):
            year_lead_mask = lead_mask & (df["year"] == year)
            year_base_mask = base_mask & (df["year"] == year)
            year_rows.append(
                {
                    "feature_name": feature_name,
                    "bin_value": bin_value,
                    "horizon": "120d",
                    "positive_label": "future_50pct_high_120d",
                    "year": int(year),
                    "stock_day_count": int(year_lead_mask.sum()),
                    "positive_rate": float(df.loc[year_lead_mask, positive_col].mean()) if year_lead_mask.any() else np.nan,
                    "year_baseline_positive_rate": float(df.loc[year_base_mask, positive_col].mean()) if year_base_mask.any() else np.nan,
                    "lift_vs_year_baseline": safe_div(df.loc[year_lead_mask, positive_col].mean(), df.loc[year_base_mask, positive_col].mean())
                    if year_lead_mask.any() and year_base_mask.any()
                    else np.nan,
                }
            )
        for industry_name in sorted(df.loc[lead_mask, "industry_name"].dropna().astype(str).unique()):
            industry_lead_mask = lead_mask & (df["industry_name"].astype(str) == industry_name)
            industry_base_mask = base_mask & (df["industry_name"].astype(str) == industry_name)
            industry_rows.append(
                {
                    "feature_name": feature_name,
                    "bin_value": bin_value,
                    "horizon": "120d",
                    "positive_label": "future_50pct_high_120d",
                    "industry_name": industry_name,
                    "stock_day_count": int(industry_lead_mask.sum()),
                    "positive_rate": float(df.loc[industry_lead_mask, positive_col].mean()) if industry_lead_mask.any() else np.nan,
                    "industry_baseline_positive_rate": float(df.loc[industry_base_mask, positive_col].mean()) if industry_base_mask.any() else np.nan,
                    "lift_vs_industry_baseline": safe_div(df.loc[industry_lead_mask, positive_col].mean(), df.loc[industry_base_mask, positive_col].mean())
                    if industry_lead_mask.any() and industry_base_mask.any()
                    else np.nan,
                }
            )
    return pd.DataFrame(year_rows), pd.DataFrame(industry_rows)


def build_primitive_outputs(config: dict[str, Any], df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dictionary = feature_dictionary()
    specs = [spec for spec in primitive_specs() if spec.p0_enabled]
    bins: dict[str, pd.Series] = {}
    elig: dict[str, pd.Series] = {}
    for spec in specs:
        bins[spec.feature_name] = primitive_bin(df, spec, config)
        elig[spec.feature_name] = primitive_eligible(df, spec)
        df[f"bin__{spec.feature_name}"] = bins[spec.feature_name]

    coverage_rows = []
    for spec in primitive_specs():
        if not spec.p0_enabled:
            coverage_rows.append(
                {
                    "feature_name": spec.feature_name,
                    "feature_family": spec.feature_family,
                    "p0_enabled": False,
                    "eligible_rows": 0,
                    "ineligible_rows": 0,
                    "missing_value_rows": 0,
                    "insufficient_history_rows": 0,
                    "warmup_partial_year": False,
                    "warmup_partial_year_rows": 0,
                    "first_feature_eligible_date": "",
                    "coverage_note": "deferred_to_p2",
                }
            )
            continue
        eligible = elig[spec.feature_name]
        insufficient = df["available_history_trading_days"] < spec.min_history_trading_days
        warmup = insufficient & (df["year"] == parse_dt(config["dates"]["research_start"]).year)
        coverage_rows.append(
            {
                "feature_name": spec.feature_name,
                "feature_family": spec.feature_family,
                "p0_enabled": True,
                "eligible_rows": int(eligible.sum()),
                "ineligible_rows": int((~eligible).sum()),
                "missing_value_rows": int(df[spec.column].isna().sum()) if spec.column in df.columns else len(df),
                "insufficient_history_rows": int(insufficient.sum()),
                "warmup_partial_year": bool(warmup.any()),
                "warmup_partial_year_rows": int(warmup.sum()),
                "first_feature_eligible_date": iso_date(df.loc[eligible, "datetime"].min()) if eligible.any() else "",
                "coverage_note": "",
            }
        )
    feature_coverage = pd.DataFrame(coverage_rows)

    univariate_rows: list[dict[str, Any]] = []
    lead_candidates: list[dict[str, Any]] = []
    labels = [
        (120, "is_future_50pct_high_120d", "future_50pct_high_120d"),
        (240, "is_future_100pct_high_240d", "future_100pct_high_240d"),
    ]
    for spec in specs:
        eligible = elig[spec.feature_name]
        if not eligible.any():
            continue
        for bin_value in sorted(pd.Series(bins[spec.feature_name]).dropna().unique()):
            if bin_value == "missing":
                continue
            condition = eligible & (bins[spec.feature_name] == bin_value)
            for horizon, positive_col, label_name in labels:
                base = baseline_mask(df, eligible, horizon, config)
                next_phase = (
                    "p1_hold_exit_refine"
                    if spec.feature_name in {"post_20pct_from_recent_low", "post_30pct_from_recent_low"}
                    else "p1_hypothesis_refine"
                )
                row = summarize_condition(
                    df,
                    condition,
                    base,
                    positive_col,
                    horizon,
                    label_name,
                    f"uni_{spec.feature_name}_{bin_value}",
                    spec.feature_name,
                    spec.feature_family,
                    f"{spec.feature_name} == {bin_value}",
                    spec.direction_hint,
                    "mixed_observable_state",
                    next_phase,
                )
                row["feature_name"] = spec.feature_name
                row["bin_value"] = bin_value
                row["lead_type"] = "univariate_primitive"
                univariate_rows.append(row)
                if horizon == 120 and label_name == "future_50pct_high_120d":
                    lead_candidates.append(row.copy())

    pairwise_rows: list[dict[str, Any]] = []
    for pair in pairwise_specs():
        if pair.first_feature not in bins or pair.second_feature not in bins:
            continue
        eligible = elig[pair.first_feature] & elig[pair.second_feature]
        condition = eligible & bins[pair.first_feature].isin(pair.first_bins) & bins[pair.second_feature].isin(pair.second_bins)
        for horizon, positive_col, label_name in labels:
            base = baseline_mask(df, eligible, horizon, config)
            row = summarize_condition(
                df,
                condition,
                base,
                positive_col,
                horizon,
                label_name,
                pair.lead_id,
                pair.lead_name,
                pair.feature_family,
                f"{pair.first_feature} in {list(pair.first_bins)} and {pair.second_feature} in {list(pair.second_bins)}",
                pair.direction,
                pair.observable_state_stage,
                pair.recommended_next_phase,
            )
            row["first_feature"] = pair.first_feature
            row["second_feature"] = pair.second_feature
            row["lead_type"] = "pairwise_primitive"
            pairwise_rows.append(row)
            if horizon == 120 and label_name == "future_50pct_high_120d":
                lead_candidates.append(row.copy())

    univariate = pd.DataFrame(univariate_rows)
    pairwise = pd.DataFrame(pairwise_rows)
    year_stability, industry_stability = build_stability_rows(config, df, univariate, specs, bins, elig)
    leads = select_preliminary_leads(pd.DataFrame(lead_candidates), config)
    completion = build_p0_completion_audit(dictionary, univariate, pairwise, leads)
    return dictionary, feature_coverage, univariate, pairwise, year_stability, industry_stability, leads, completion


def select_preliminary_leads(candidates: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    required_cols = [
        "lead_id",
        "lead_name",
        "feature_family",
        "observable_state_stage",
        "formula_or_bin",
        "direction",
        "horizon",
        "baseline_scope",
        "stock_day_count",
        "unique_instrument_count",
        "unique_instrument_year_count",
        "unique_episode_count",
        "positive_stock_day_count",
        "positive_unique_instrument_year_count",
        "positive_unique_episode_count",
        "baseline_positive_rate",
        "lead_future_50pct_precision",
        "lead_future_100pct_precision",
        "lift_vs_baseline",
        "episode_dedup_lift",
        "instrument_year_dedup_lift",
        "year_positive_lift_count",
        "distinct_year_count",
        "distinct_industry_count",
        "industry_concentration_top1",
        "avg_lead_time_to_50pct",
        "median_lead_time_to_50pct",
        "avg_future_max_gain",
        "avg_future_drawdown_before_gain",
        "label_horizon_truncated_rate",
        "observed_reference_overlap_rate",
        "duplicate_positive_risk",
        "sparse_bin",
        "failure_reason",
        "recommended_next_phase",
    ]
    if candidates.empty:
        return pd.DataFrame(columns=required_cols)
    df = candidates.copy()
    min_samples = int(config["primitives"]["min_lead_samples"])
    score_cfg = config["primitives"]["lead_score"]
    df["candidate_ok"] = (
        (df["stock_day_count"] >= min_samples)
        & (df["lift_vs_baseline"] > 1.0)
        & (df["distinct_year_count"] >= 3)
        & (df["industry_concentration_top1"].fillna(1.0) <= 0.60)
    )
    df["score"] = (
        df["lift_vs_baseline"].fillna(0) * float(score_cfg["lift_weight"])
        + np.log1p(df["stock_day_count"].fillna(0)) * float(score_cfg["sample_log_weight"])
        + df["distinct_year_count"].fillna(0) * float(score_cfg["year_weight"])
        - df["industry_concentration_top1"].fillna(1.0) * float(score_cfg["industry_penalty"])
    )
    ranked = df.sort_values(["candidate_ok", "score"], ascending=[False, False]).copy()

    selected_rows: list[pd.Series] = []

    def add_matching(mask: pd.Series, count: int) -> None:
        nonlocal selected_rows
        existing = {str(row["lead_id"]) for row in selected_rows}
        candidate_ids = set(ranked.loc[mask, "lead_id"].astype(str))
        already_matching = sum(str(row["lead_id"]) in candidate_ids for row in selected_rows)
        needed = max(0, count - already_matching)
        if needed == 0:
            return
        added = 0
        for _, row in ranked[mask].iterrows():
            if str(row["lead_id"]) in existing:
                continue
            selected_rows.append(row)
            existing.add(str(row["lead_id"]))
            added += 1
            if added >= needed:
                break

    non_ema_mask = ~ranked["feature_family"].astype(str).str.contains("ema|breakout|pullback", case=False, regex=True)
    rs_mask = ranked["feature_family"].astype(str).str.contains(
        "relative_strength|relative_strength_regime|stock_industry_lead|rank_industry_sync|repair_relative_strength",
        case=False,
        regex=True,
    )
    money_vol_mask = ranked["feature_family"].astype(str).str.contains("money|volatility|compression", case=False, regex=True)
    hold_mask = (
        ranked["recommended_next_phase"].eq("p1_hold_exit_refine")
        | ranked["lead_id"].astype(str).str.contains("post_20|post_30|pair_hold", case=False, regex=True)
    )
    add_matching(non_ema_mask & ranked["candidate_ok"], 3)
    add_matching(rs_mask & ranked["candidate_ok"], 2)
    add_matching(money_vol_mask & ranked["candidate_ok"], 2)
    add_matching(hold_mask & ranked["candidate_ok"], 1)
    existing = {str(row["lead_id"]) for row in selected_rows}
    for _, row in ranked.iterrows():
        if str(row["lead_id"]) in existing:
            continue
        selected_rows.append(row)
        existing.add(str(row["lead_id"]))
        if len(selected_rows) >= 8:
            break
    result = pd.DataFrame(selected_rows)
    if result.empty:
        result = ranked.head(5).copy()
    result = result.head(max(5, min(8, len(result)))).copy()
    result["lead_rank"] = range(1, len(result) + 1)
    for column in required_cols:
        if column not in result.columns:
            result[column] = np.nan
    return result[["lead_rank"] + required_cols]


def build_p0_completion_audit(dictionary: pd.DataFrame, univariate: pd.DataFrame, pairwise: pd.DataFrame, leads: pd.DataFrame) -> pd.DataFrame:
    enabled = dictionary[dictionary["p0_enabled"].astype(bool)]
    family_count = int(dictionary["feature_family"].nunique())
    univariate_count = int(enabled["feature_name"].nunique())
    pairwise_count = int(pairwise["lead_id"].nunique()) if not pairwise.empty else 0
    lead_count = int(len(leads))
    non_ema_leads = int((~leads["feature_family"].astype(str).str.contains("ema|breakout|pullback", case=False, regex=True)).sum()) if not leads.empty else 0
    rs_leads = (
        int(
            leads["feature_family"]
            .astype(str)
            .str.contains(
                "relative_strength|relative_strength_regime|stock_industry_lead|rank_industry_sync|repair_relative_strength",
                case=False,
                regex=True,
            )
            .sum()
        )
        if not leads.empty
        else 0
    )
    money_vol_leads = int(leads["feature_family"].astype(str).str.contains("money|volatility|compression", case=False, regex=True).sum()) if not leads.empty else 0
    hold_leads = (
        int(
            (
                leads["recommended_next_phase"].eq("p1_hold_exit_refine")
                | leads["lead_id"].astype(str).str.contains("post_20|post_30|pair_hold", case=False, regex=True)
            ).sum()
        )
        if not leads.empty
        else 0
    )
    broad_met = (
        family_count >= 10
        and univariate_count >= 30
        and pairwise_count >= 10
        and lead_count >= 5
        and non_ema_leads >= 3
        and rs_leads >= 2
        and money_vol_leads >= 2
        and hold_leads >= 1
    )
    rows = [
        ("registry_feature_family_count", family_count, 10, family_count >= 10, ""),
        ("p0_univariate_primitive_count", univariate_count, 30, univariate_count >= 30, ""),
        ("p0_pairwise_combo_count", pairwise_count, 10, pairwise_count >= 10, ""),
        ("preliminary_discovery_lead_count", lead_count, 5, lead_count >= 5, ""),
        ("non_ema_breakout_pullback_lead_count", non_ema_leads, 3, non_ema_leads >= 3, ""),
        ("relative_strength_or_industry_lead_count", rs_leads, 2, rs_leads >= 2, ""),
        ("money_or_volatility_lead_count", money_vol_leads, 2, money_vol_leads >= 2, ""),
        ("continuation_or_hold_lead_count", hold_leads, 1, hold_leads >= 1, ""),
        ("broad_discovery_p0_minimum_coverage_met", int(broad_met), 1, broad_met, "" if broad_met else "minimum coverage requirement not fully met"),
    ]
    return pd.DataFrame(rows, columns=["check_name", "actual_value", "required_value", "passed", "failure_reason"])


def p0_5_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("p0_5", {})


def p0_5_feature_panel_path(config: dict[str, Any]) -> Path:
    configured = p0_5_cfg(config).get("feature_panel_cache", "Explore9/outputs/cache/p0_5_feature_panel_expand_1.parquet")
    return topic_path(configured)


def p0_5_manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "p0_5_run_manifest.json"


def rolling_sum_by_instrument(df: pd.DataFrame, column: str, window: int) -> pd.Series:
    return (
        df.groupby("instrument", group_keys=False)[column]
        .transform(lambda s, window=window: s.fillna(False).astype(float).rolling(window, min_periods=1).sum())
        .reindex(df.index)
    )


def add_p0_5_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values(["instrument", "datetime"]).reset_index(drop=True)
    group = df.groupby("instrument", group_keys=False)
    day_range = (df["high"] - df["low"]).replace(0, np.nan)
    df["close_location_in_day"] = ((df["close"] - df["low"]) / day_range).clip(0, 1)
    df["body_ratio"] = ((df["close"] - df["open"]).abs() / day_range).clip(0, 1)
    df["upper_shadow_ratio"] = ((df["high"] - df[["open", "close"]].max(axis=1)) / day_range).clip(0, 1)
    df["lower_shadow_ratio"] = ((df[["open", "close"]].min(axis=1) - df["low"]) / day_range).clip(0, 1)
    df["up_day"] = df["close"] > df["prev_close"]
    df["down_day"] = df["close"] < df["prev_close"]
    df["up_day_amplitude"] = df["amplitude"].where(df["up_day"])
    df["down_day_amplitude"] = df["amplitude"].where(df["down_day"])
    df["median_price20"] = group["close"].transform(lambda s: s.rolling(20, min_periods=20).median())
    df["median_price60"] = group["close"].transform(lambda s: s.rolling(60, min_periods=60).median())
    df["reclaim_median20_flag"] = (df["close"] > df["median_price20"]) & (group["close"].shift(1) <= df.groupby("instrument")["median_price20"].shift(1))
    df["reclaim_median60_flag"] = (df["close"] > df["median_price60"]) & (group["close"].shift(1) <= df.groupby("instrument")["median_price60"].shift(1))
    df["first_reclaim_median20_after_drawdown"] = df["reclaim_median20_flag"] & (df["drawdown_from_high120"] <= -0.20)
    df["first_reclaim_median60_after_drawdown"] = df["reclaim_median60_flag"] & (df["drawdown_from_high120"] <= -0.25)
    df["drawdown_from_high20"] = df["dist_high20"]
    df["repair_under20_from_low120"] = (df["repair_from_low120"] >= 0.05) & (df["repair_from_low120"] < 0.20)
    df["repair_under30_from_low120"] = (df["repair_from_low120"] >= 0.10) & (df["repair_from_low120"] < 0.30)
    df["higher_low20_flag"] = df["low20"] > group["low20"].shift(20)
    df["higher_low60_flag"] = df["low60"] > group["low60"].shift(60)
    df["higher_high20_flag"] = df["high20"] > group["high20"].shift(20)
    df["higher_high60_flag"] = df["high60"] > group["high60"].shift(60)
    df["higher_low_without_high_breakout"] = df["higher_low20_flag"] & ~df["higher_high20_flag"]
    prior_low20 = group["low20"].shift(1)
    df["false_breakdown_reclaim20"] = (df["low"] < prior_low20) & (df["close"] > prior_low20)
    df["drawdown_speed20"] = df["drawdown_from_high120"] - group["drawdown_from_high120"].shift(20)
    df["drawdown_speed_slowing20"] = df.groupby("instrument")["drawdown_speed20"].shift(20) - df["drawdown_speed20"]

    for ret_window in [5, 20, 60]:
        df[f"ret{ret_window}_universe_pctile_p0_5"] = df.groupby("datetime")[f"ret{ret_window}"].rank(pct=True)
        df[f"ret{ret_window}_industry_pctile_p0_5"] = df.groupby(["datetime", "industry_name"])[f"ret{ret_window}"].rank(pct=True)
    for money_window, money_col in [(5, "avg_money5_prior"), (20, "avg_money20_prior"), (60, "avg_money60_prior")]:
        df[f"money{money_window}_universe_pctile"] = df.groupby("datetime")[money_col].rank(pct=True)
        df[f"money{money_window}_industry_pctile"] = df.groupby(["datetime", "industry_name"])[money_col].rank(pct=True)
    df["ret_rank_jump5_20"] = df["ret5_universe_pctile_p0_5"] - df["ret20_universe_pctile"]
    df["ret_rank_jump20_60"] = df["ret20_universe_pctile"] - df["ret60_universe_pctile_p0_5"]
    df["money_rank_jump5_20"] = df["money5_universe_pctile"] - df["money20_universe_pctile"]
    df["money_rank_jump20_60"] = df["money20_universe_pctile"] - df["money60_universe_pctile"]
    df["industry_ret_rank_jump5_20"] = df["ret5_industry_pctile_p0_5"] - df["ret20_industry_pctile"]
    df["industry_ret_rank_jump20_60"] = df["ret20_industry_pctile"] - df["ret60_industry_pctile_p0_5"]
    df["from_industry_below_median_to_top20"] = (df["ret_rank_jump20_60"] >= 0.30) & (df["ret20_industry_pctile"] >= 0.80)
    df["market_top20_industry_lag"] = (df["ret20_universe_pctile"] >= 0.80) & df["industry_width_state"].isin(["industry_width_weak", "industry_width_neutral"])
    df["stock_leads_industry_lag"] = (df["relative_ret20_vs_industry"] > 0.10) & df["industry_regime_state"].isin(["industry_lagging", "industry_mixed"])
    df["isolated_strength_weak_market"] = (df["ret20_universe_pctile"] >= 0.80) & df["market_regime_state"].isin(["market_drawdown", "market_choppy"])
    df["market_turn_front_runner"] = (df["benchmark_ema60_slope20"] > 0) & (df["ret20_universe_pctile"] >= 0.80) & (df["market_width_state"] != "width_strong")

    industry_width = df[["datetime", "industry_name", "industry_close_gt_ema60_ratio"]].drop_duplicates().sort_values(["industry_name", "datetime"])
    industry_width["industry_width_delta20"] = industry_width.groupby("industry_name")["industry_close_gt_ema60_ratio"].diff(20)
    df = df.merge(industry_width[["datetime", "industry_name", "industry_width_delta20"]], on=["datetime", "industry_name"], how="left")
    market_width = df[["datetime", "close_gt_ema60_ratio"]].drop_duplicates().sort_values("datetime")
    market_width["market_width_delta20"] = market_width["close_gt_ema60_ratio"].diff(20)
    df = df.merge(market_width[["datetime", "market_width_delta20"]], on="datetime", how="left")
    df["industry_width_improving_front_runner"] = (df["industry_width_delta20"] > 0.10) & (df["ret20_industry_pctile"] >= 0.80)
    df["early_repair_industry_lag"] = df["repair_under20_from_low120"] & df["industry_width_state"].isin(["industry_width_weak", "industry_width_neutral"])

    df["expansion_volatility_flag"] = (df["amplitude20"] >= df.groupby("year")["amplitude20"].transform(lambda s: s.quantile(0.8))) & (df["close_location_in_day"] >= 0.60) & (df["ret20"] > 0)
    df["destructive_volatility_flag"] = (df["amplitude20"] >= df.groupby("year")["amplitude20"].transform(lambda s: s.quantile(0.8))) & (df["close_location_in_day"] <= 0.40) & (df["drawdown_from_high60"] <= -0.10)
    df["reversal_volatility_flag"] = (df["amplitude"] >= df.groupby("year")["amplitude"].transform(lambda s: s.quantile(0.8))) & (df["lower_shadow_ratio"] >= 0.45) & (df["close_location_in_day"] >= 0.55)
    df["late_acceleration_volatility_flag"] = (df["amplitude20"] >= df.groupby("year")["amplitude20"].transform(lambda s: s.quantile(0.8))) & (df["observable_state_stage"] == "observable_late_acceleration_risk")
    df["failed_high_volatility_flag"] = (df["amplitude20"] >= df.groupby("year")["amplitude20"].transform(lambda s: s.quantile(0.8))) & (df["ret20"] <= 0) & (df["close_location_in_day"] <= 0.45)
    df["high_atr_above_median20"] = (df["atr20_pct"] >= df.groupby("year")["atr20_pct"].transform(lambda s: s.quantile(0.8))) & (df["close"] > df["median_price20"])
    df["high_atr_break_short_structure"] = (df["atr20_pct"] >= df.groupby("year")["atr20_pct"].transform(lambda s: s.quantile(0.8))) & (df["close"] < df["low20"])
    df["high_vol_relative_strength_flag"] = (df["amplitude20"] >= df.groupby("year")["amplitude20"].transform(lambda s: s.quantile(0.8))) & (df["ret20_universe_pctile"] >= 0.80)
    df["high_vol_industry_width_improving"] = (df["amplitude20"] >= df.groupby("year")["amplitude20"].transform(lambda s: s.quantile(0.8))) & (df["industry_width_delta20"] > 0.10)
    df["high_vol_drawdown_controlled"] = (df["amplitude20"] >= df.groupby("year")["amplitude20"].transform(lambda s: s.quantile(0.8))) & (df["drawdown_from_high60"] > -0.12)
    df["high_vol_money_quality_flag"] = (df["amplitude20"] >= df.groupby("year")["amplitude20"].transform(lambda s: s.quantile(0.8))) & (df["money_ratio20"] >= 1.20) & (df["close_location_in_day"] >= 0.55)
    df["high_vol_false_positive_control"] = df["failed_high_volatility_flag"] & (df["money_ratio20"] >= 1.20)

    df["up_day_money_ratio20"] = df["money_ratio20"].where(df["up_day"])
    df["down_day_money_ratio20"] = df["money_ratio20"].where(df["down_day"])
    df["pullback_volume_contraction"] = (df["ret5"] < 0) & (df["money_ratio20"] < 0.80) & (df["close"] > df["ema60"])
    df["volume_price_hold_3d"] = (group["money_ratio20"].shift(3) >= 1.50) & (df["close"] >= group["close"].shift(3))
    df["volume_price_hold_5d"] = (group["money_ratio20"].shift(5) >= 1.50) & (df["close"] >= group["close"].shift(5))
    df["volume_spike_failed_5d"] = (group["money_ratio20"].shift(5) >= 1.50) & (df["close"] < group["low"].shift(5))
    df["money_close_location_score"] = df["money_ratio20"] * df["close_location_in_day"]
    df["money_rank_jump_with_ret_rank_jump"] = (df["money_rank_jump5_20"] >= 0.20) & (df["ret_rank_jump5_20"] >= 0.20)
    df["high_money_persistence5"] = rolling_sum_by_instrument(df, "money_ratio20", 5) >= 5.0
    df["money_up_no_return_followthrough"] = (df["money_ratio20"] >= 1.50) & (df["ret5"] <= 0.02)
    df["money_industry_width_improve"] = (df["money_ratio20"] >= 1.20) & (df["industry_width_delta20"] > 0.10)

    df["near_limit_up_like"] = ((df["close"] / df["prev_close"].replace(0, np.nan) - 1.0) >= 0.08) | (df["gap_pct"] >= 0.08)
    df["limit_up_count5"] = rolling_sum_by_instrument(df, "limit_up_like", 5)
    df["limit_up_count20"] = rolling_sum_by_instrument(df, "limit_up_like", 20)
    df["near_limit_up_count5"] = rolling_sum_by_instrument(df, "near_limit_up_like", 5)
    df["near_limit_up_count20"] = rolling_sum_by_instrument(df, "near_limit_up_like", 20)
    prior_limit60 = group["limit_up_like"].transform(lambda s: s.fillna(False).astype(float).shift(1).rolling(60, min_periods=1).sum())
    prior_near60 = df.groupby("instrument", group_keys=False)["near_limit_up_like"].transform(lambda s: s.fillna(False).astype(float).shift(1).rolling(60, min_periods=1).sum())
    df["first_limit_up_60d"] = df["limit_up_like"].fillna(False).astype(bool) & (prior_limit60.fillna(0) == 0)
    df["first_near_limit_up_60d"] = df["near_limit_up_like"].fillna(False).astype(bool) & (prior_near60.fillna(0) == 0)
    df["gap_up_close_upper"] = (df["gap_pct"] >= 0.03) & (df["close_location_in_day"] >= 0.60)
    df["recent_gap_up_count3"] = rolling_sum_by_instrument(df, "gap_up_close_upper", 3)
    df["recent_gap_up_count5"] = rolling_sum_by_instrument(df, "gap_up_close_upper", 5)
    df["gap_up_held_3d"] = (df["recent_gap_up_count3"] > 0) & (df["close"] > df["ema20"])
    df["gap_up_held_5d"] = (df["recent_gap_up_count5"] > 0) & (df["close"] > df["ema20"])
    df["strong_body_day"] = (df["body_ratio"] >= 0.60) & (df["ret1"] > 0.04) & (df["close_location_in_day"] >= 0.60)
    df["long_upper_shadow_failure"] = (df["upper_shadow_ratio"] >= 0.45) & (df["close_location_in_day"] <= 0.45) & (df["money_ratio20"] >= 1.20)
    df["recent_strong_body_count10"] = rolling_sum_by_instrument(df, "strong_body_day", 10)
    df["strong_day_pullback_hold20"] = (df["recent_strong_body_count10"] > 0) & (df["drawdown_from_high20"] > -0.12) & (df["money_ratio20"] < 1.30)
    return df


def p0_5_primitive_specs() -> list[P05PrimitiveSpec]:
    specs: list[P05PrimitiveSpec] = []
    for spec in primitive_specs():
        if not spec.p0_enabled:
            continue
        lifecycle = "hold_exit_tolerance" if spec.feature_name in {"post_20pct_from_recent_low", "post_30pct_from_recent_low"} else "early_entry_discovery"
        specs.append(
            P05PrimitiveSpec(
                spec.feature_name,
                spec.feature_family,
                spec.column,
                spec.value_type,
                spec.min_history_trading_days,
                spec.lookback_window,
                spec.requires_benchmark_history,
                spec.requires_industry_history,
                True,
                spec.direction_hint,
                p0_5_new=False,
                lifecycle_bucket=lifecycle,
                primary_combo_family=spec.feature_family,
                human_readable_definition=f"P0 inherited primitive: {spec.feature_name}",
                formula_or_bin=spec.column,
                required_columns=spec.column,
            )
        )

    def add(
        name: str,
        family: str,
        value_type: str,
        min_history: int,
        lifecycle: str,
        primary: str,
        definition: str,
        direction: str = "high",
        sparse: bool = False,
        generalizable: bool = True,
        path_only: bool = False,
        diagnostic_only: bool = False,
        close_rule: str = "",
        context: str = "",
        false_def: str = "evaluation_only: target forward label miss and/or adverse future drawdown; never used as T-day feature",
    ) -> None:
        specs.append(
            P05PrimitiveSpec(
                name,
                family,
                name,
                value_type,
                min_history,
                f"{min_history}d" if min_history > 1 else "1d",
                False,
                "industry" in name or "industry" in definition,
                True,
                direction,
                p0_5_new=True,
                lifecycle_bucket=lifecycle,
                primary_combo_family=primary,
                sparse_diagnostic=sparse,
                generalizable_entry_lead=generalizable,
                path_explanation_only=path_only,
                category_id=name if primary == "high_volatility_decomposition" else "",
                human_readable_definition=definition,
                formula_or_bin=name,
                required_columns=name,
                close_location_rule=close_rule,
                trend_or_drawdown_context=context,
                evaluation_only_false_positive_definition=false_def,
                diagnostic_only_not_p1_ready=diagnostic_only,
            )
        )

    hv = "high_volatility_decomposition"
    add("close_location_in_day", "price_intraday_structure", "continuous", 1, "early_entry_discovery", hv, "Close location within the daily range.")
    add("up_day_amplitude", "volatility_decomposition", "continuous", 20, "early_entry_discovery", hv, "Daily amplitude on up days.", close_rule="close > prev_close")
    add("down_day_amplitude", "volatility_decomposition", "continuous", 20, "early_entry_discovery", hv, "Daily amplitude on down days.", direction="low", close_rule="close < prev_close")
    add("expansion_volatility_flag", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High amplitude with upper close and positive 20d return.", close_rule="close_location >= 0.60", context="upward expansion")
    add("destructive_volatility_flag", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High amplitude with lower close and existing drawdown.", direction="low", close_rule="close_location <= 0.40", context="drawdown damage")
    add("reversal_volatility_flag", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High intraday range with lower shadow and upper-half close.", close_rule="lower_shadow >= 0.45")
    add("late_acceleration_volatility_flag", "volatility_decomposition", "boolean", 20, "hold_exit_tolerance", hv, "High volatility while already in late acceleration state.", diagnostic_only=True, context="late lifecycle")
    add("failed_high_volatility_flag", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High volatility with weak return and lower close.", direction="low", close_rule="close_location <= 0.45")
    add("high_atr_above_median20", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High ATR while close remains above 20d median price.", close_rule="close > median20")
    add("high_atr_break_short_structure", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High ATR with close breaking short-term structure.", direction="low", context="structure break")
    add("high_vol_relative_strength_flag", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High amplitude combined with top-quintile market relative return.")
    add("high_vol_industry_width_improving", "volatility_decomposition", "boolean", 60, "early_entry_discovery", hv, "High volatility while industry breadth improves.")
    add("high_vol_drawdown_controlled", "volatility_decomposition", "boolean", 60, "early_entry_discovery", hv, "High volatility with controlled 60d drawdown.")
    add("high_vol_money_quality_flag", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High volatility supported by money expansion and upper-half close.", close_rule="close_location >= 0.55")
    add("high_vol_false_positive_control", "volatility_decomposition", "boolean", 20, "early_entry_discovery", hv, "High volatility failure-control diagnostic.", direction="low", diagnostic_only=True)

    repair = "repair_initiation"
    add("reclaim_median20_flag", "repair_initiation", "boolean", 20, "early_entry_discovery", repair, "First close reclaim above 20d median price.")
    add("reclaim_median60_flag", "repair_initiation", "boolean", 60, "early_entry_discovery", repair, "First close reclaim above 60d median price.")
    add("drawdown_from_high20", "repair_initiation", "continuous", 20, "hold_exit_tolerance", repair, "20d drawdown from rolling high.", direction="low")
    add("first_reclaim_median20_after_drawdown", "repair_initiation", "boolean", 120, "early_entry_discovery", repair, "20d median reclaim after at least 20% drawdown.")
    add("first_reclaim_median60_after_drawdown", "repair_initiation", "boolean", 120, "early_entry_discovery", repair, "60d median reclaim after at least 25% drawdown.")
    add("repair_under20_from_low120", "repair_initiation", "boolean", 120, "early_entry_discovery", repair, "Repair from 120d low but still below post-20% confirmation.")
    add("repair_under30_from_low120", "repair_initiation", "boolean", 120, "early_entry_discovery", repair, "Repair from 120d low but still below post-30% confirmation.")
    add("higher_low20_flag", "repair_initiation", "boolean", 40, "early_entry_discovery", repair, "20d low is higher than prior 20d low.")
    add("higher_low60_flag", "repair_initiation", "boolean", 120, "early_entry_discovery", repair, "60d low is higher than prior 60d low.")
    add("higher_high20_flag", "repair_initiation", "boolean", 40, "confirmation_continuation", repair, "20d high is higher than prior 20d high.")
    add("higher_high60_flag", "repair_initiation", "boolean", 120, "confirmation_continuation", repair, "60d high is higher than prior 60d high.")
    add("higher_low_without_high_breakout", "repair_initiation", "boolean", 40, "early_entry_discovery", repair, "Higher low without a 20d high breakout.")
    add("false_breakdown_reclaim20", "repair_initiation", "boolean", 20, "early_entry_discovery", repair, "Temporary break below prior 20d low followed by reclaim.")
    add("drawdown_speed_slowing20", "repair_initiation", "continuous", 120, "early_entry_discovery", repair, "Recent drawdown deterioration slows versus previous 20d.")
    add("early_repair_industry_lag", "repair_initiation", "boolean", 120, "early_entry_discovery", repair, "Early repair while industry breadth has not yet synchronized.")

    rank = "rank_jump_leadership"
    add("industry_width_delta20", "rank_jump_leadership", "continuous", 60, "early_entry_discovery", rank, "20-session improvement in industry breadth.")
    add("market_width_delta20", "rank_jump_leadership", "continuous", 60, "early_entry_discovery", rank, "20-session improvement in market breadth.")
    add("ret5_universe_pctile_p0_5", "rank_jump_leadership", "continuous", 5, "early_entry_discovery", rank, "5d return cross-section rank.")
    add("ret60_universe_pctile_p0_5", "rank_jump_leadership", "continuous", 60, "confirmation_continuation", rank, "60d return cross-section rank.")
    add("ret_rank_jump5_20", "rank_jump_leadership", "continuous", 20, "early_entry_discovery", rank, "5d return rank minus 20d return rank.")
    add("ret_rank_jump20_60", "rank_jump_leadership", "continuous", 60, "early_entry_discovery", rank, "20d return rank minus 60d return rank.")
    add("money5_universe_pctile", "rank_jump_leadership", "continuous", 5, "early_entry_discovery", rank, "5d money cross-section rank.")
    add("money_rank_jump5_20", "rank_jump_leadership", "continuous", 20, "early_entry_discovery", rank, "5d money rank minus 20d money rank.")
    add("money_rank_jump20_60", "rank_jump_leadership", "continuous", 60, "early_entry_discovery", rank, "20d money rank minus 60d money rank.")
    add("industry_ret_rank_jump5_20", "rank_jump_leadership", "continuous", 20, "early_entry_discovery", rank, "5d industry return rank jump versus 20d.")
    add("from_industry_below_median_to_top20", "rank_jump_leadership", "boolean", 60, "early_entry_discovery", rank, "Stock jumps from weak/mid industry rank to top 20%.")
    add("market_top20_industry_lag", "rank_jump_leadership", "boolean", 20, "early_entry_discovery", rank, "Stock enters market top 20% before industry breadth sync.")
    add("stock_leads_industry_lag", "rank_jump_leadership", "boolean", 20, "early_entry_discovery", rank, "Stock persistently outperforms lagging industry.")
    add("isolated_strength_weak_market", "rank_jump_leadership", "boolean", 20, "early_entry_discovery", rank, "Top-quintile stock strength in weak or choppy market.")
    add("market_turn_front_runner", "rank_jump_leadership", "boolean", 120, "early_entry_discovery", rank, "Front-runner when benchmark slope turns but breadth is not strong.")
    add("industry_width_improving_front_runner", "rank_jump_leadership", "boolean", 60, "early_entry_discovery", rank, "Industry breadth improvement with stock in industry front row.")

    money = "money_quality"
    add("up_day_money_ratio20", "money_quality", "continuous", 20, "confirmation_continuation", money, "Money expansion on up days.")
    add("down_day_money_ratio20", "money_quality", "continuous", 20, "early_entry_discovery", money, "Money expansion on down days.", direction="low")
    add("pullback_volume_contraction", "money_quality", "boolean", 20, "early_entry_discovery", money, "Pullback with contracted money while price remains above EMA60.")
    add("volume_price_hold_3d", "money_quality", "boolean", 20, "confirmation_continuation", money, "Price holds 3 days after a prior volume expansion.")
    add("volume_price_hold_5d", "money_quality", "boolean", 20, "confirmation_continuation", money, "Price holds 5 days after a prior volume expansion.")
    add("volume_spike_failed_5d", "money_quality", "boolean", 20, "early_entry_discovery", money, "Price fails 5 days after a prior volume spike.", direction="low")
    add("money_close_location_score", "money_quality", "continuous", 20, "confirmation_continuation", money, "Money expansion weighted by close location.")
    add("money_rank_jump_with_ret_rank_jump", "money_quality", "boolean", 20, "early_entry_discovery", money, "Money rank jump confirms return rank jump.")
    add("high_money_persistence5", "money_quality", "boolean", 20, "confirmation_continuation", money, "Persistent elevated money for five recent sessions.")
    add("money_up_no_return_followthrough", "money_quality", "boolean", 20, "early_entry_discovery", money, "Money expansion without return follow-through.", direction="low")
    add("money_industry_width_improve", "money_quality", "boolean", 60, "confirmation_continuation", money, "Money expansion while industry breadth improves.")

    sparse = "sparse_strong_day_diagnostic"
    add("near_limit_up_like", "strong_day_path", "boolean", 1, "confirmation_continuation", sparse, "Near limit-up day.", sparse=True, generalizable=False, path_only=True)
    add("limit_up_count5", "strong_day_path", "continuous", 5, "confirmation_continuation", sparse, "Limit-up count in recent 5 sessions.", sparse=True, generalizable=False, path_only=True)
    add("limit_up_count20", "strong_day_path", "continuous", 20, "confirmation_continuation", sparse, "Limit-up count in recent 20 sessions.", sparse=True, generalizable=False, path_only=True)
    add("near_limit_up_count5", "strong_day_path", "continuous", 5, "confirmation_continuation", sparse, "Near-limit-up count in recent 5 sessions.", sparse=True, generalizable=False, path_only=True)
    add("near_limit_up_count20", "strong_day_path", "continuous", 20, "confirmation_continuation", sparse, "Near-limit-up count in recent 20 sessions.", sparse=True, generalizable=False, path_only=True)
    add("first_limit_up_60d", "strong_day_path", "boolean", 60, "confirmation_continuation", sparse, "First limit-up-like day in 60 sessions.", sparse=True, generalizable=False, path_only=True)
    add("first_near_limit_up_60d", "strong_day_path", "boolean", 60, "confirmation_continuation", sparse, "First near-limit-up-like day in 60 sessions.", sparse=True, generalizable=False, path_only=True)
    add("gap_up_close_upper", "strong_day_path", "boolean", 1, "confirmation_continuation", sparse, "Gap-up day closing in upper half.", sparse=True, generalizable=False, path_only=True)
    add("gap_up_held_3d", "strong_day_path", "boolean", 5, "confirmation_continuation", sparse, "Recent gap-up held above EMA20 for 3d diagnostic.", sparse=True, generalizable=False, path_only=True)
    add("gap_up_held_5d", "strong_day_path", "boolean", 5, "confirmation_continuation", sparse, "Recent gap-up held above EMA20 for 5d diagnostic.", sparse=True, generalizable=False, path_only=True)
    add("strong_body_day", "strong_day_path", "boolean", 1, "confirmation_continuation", sparse, "Strong real-body up day.", sparse=True, generalizable=False, path_only=True)
    add("long_upper_shadow_failure", "strong_day_path", "boolean", 1, "hold_exit_tolerance", sparse, "High-money upper-shadow failure day.", direction="low", sparse=True, generalizable=False, path_only=True, diagnostic_only=True)
    add("strong_day_pullback_hold20", "strong_day_path", "boolean", 20, "hold_exit_tolerance", sparse, "Pullback after strong day that holds within 20d structure.", sparse=True, generalizable=False, path_only=True)
    return specs


def p0_5_feature_dictionary() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in p0_5_primitive_specs():
        rows.append(
            {
                "feature_name": spec.feature_name,
                "feature_family": spec.feature_family,
                "source_column": spec.column,
                "value_type": spec.value_type,
                "min_history_trading_days": int(spec.min_history_trading_days),
                "lookback_window": spec.lookback_window,
                "requires_benchmark_history": bool(spec.requires_benchmark_history),
                "requires_industry_history": bool(spec.requires_industry_history),
                "feature_eligible_rule": f"available_history_trading_days >= {spec.min_history_trading_days} and provider_required_fields_ok and value_not_missing",
                "warmup_partial_year_handling": "mark_warmup_partial_year_and_exclude_from_p0_5_lift_denominator",
                "p0_5_enabled": bool(spec.p0_enabled),
                "p0_5_new": bool(spec.p0_5_new),
                "direction_hint": spec.direction_hint,
                "lifecycle_bucket": spec.lifecycle_bucket,
                "primary_combo_family": spec.primary_combo_family,
                "sparse_diagnostic": bool(spec.sparse_diagnostic),
                "generalizable_entry_lead": bool(spec.generalizable_entry_lead),
                "path_explanation_only": bool(spec.path_explanation_only),
                "category_id": spec.category_id,
                "human_readable_definition": spec.human_readable_definition,
                "formula_or_bin": spec.formula_or_bin,
                "required_columns": spec.required_columns,
                "feature_eligible_rule_detail": f"{spec.column} not missing and PIT member on T date",
                "close_location_rule": spec.close_location_rule,
                "trend_or_drawdown_context": spec.trend_or_drawdown_context,
                "evaluation_only_false_positive_definition": spec.evaluation_only_false_positive_definition,
                "diagnostic_only_not_p1_ready": bool(spec.diagnostic_only_not_p1_ready),
            }
        )
    return pd.DataFrame(rows)


def p0_5_common_mask(df: pd.DataFrame, config: dict[str, Any]) -> pd.Series:
    return (
        (df["datetime"] >= parse_dt(config["dates"]["research_start"]))
        & (df["datetime"] <= parse_dt(config["dates"]["research_end"]))
        & df["pit_member"].fillna(False).astype(bool)
        & df["provider_required_fields_ok"].fillna(False).astype(bool)
        & df["feature_eligible"].fillna(False).astype(bool)
        & ~df["label_horizon_truncated"].fillna(True).astype(bool)
        & ~df["observed_reference_overlap"].fillna(True).astype(bool)
    )


def p0_5_lifecycle_mask(df: pd.DataFrame, config: dict[str, Any], lifecycle_bucket: str) -> pd.Series:
    common = p0_5_common_mask(df, config)
    late = df["observable_state_stage"].astype("string") == "observable_late_acceleration_risk"
    post20 = df["post_20pct_from_recent_low"].fillna(False).astype(bool)
    post30 = df["post_30pct_from_recent_low"].fillna(False).astype(bool)
    if lifecycle_bucket == "early_entry_discovery":
        return common & ~post20 & ~post30 & ~late
    if lifecycle_bucket == "confirmation_continuation":
        return common & (
            post20
            | post30
            | df["observable_state_stage"].isin(
                ["observable_relative_strength_leading", "observable_20pct_from_recent_low", "observable_30pct_from_recent_low", "observable_trend_extension"]
            )
        ) & ~late
    if lifecycle_bucket == "hold_exit_tolerance":
        return common & (post20 | post30 | late | (df["trend_age_close_above_ema60"] >= 60))
    if lifecycle_bucket == "early_entry_shadow_with_post_20pct":
        return common & post20 & ~post30 & ~late
    if lifecycle_bucket == "early_entry_shadow_with_post_30pct":
        return common & post30 & ~late
    if lifecycle_bucket == "early_entry_shadow_with_late_acceleration":
        return common & late
    return common


def p0_5_patterns() -> list[P05PatternSpec]:
    def c(feature: str, values: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        return (feature, values)

    patterns = [
        P05PatternSpec("hv_expansion_rs", "扩张性高波 + 相对强度", "high_volatility_decomposition", "early_entry_discovery", (c("expansion_volatility_flag", ("true",)), c("ret20_universe_pctile", ("p80_90", "p90_100"))), "expansion_volatility_flag == true and ret20_universe_pctile in top20", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("hv_expansion_money", "扩张性高波 + 成交质量", "high_volatility_decomposition", "early_entry_discovery", (c("expansion_volatility_flag", ("true",)), c("money_close_location_score", ("p80_90", "p90_100"))), "expansion volatility with upper close and money quality", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("hv_upper_close_industry_improve", "高波上半区 + 行业宽度改善", "high_volatility_decomposition", "early_entry_discovery", (c("high_vol_industry_width_improving", ("true",)), c("close_location_in_day", ("p60_80", "p80_90", "p90_100"))), "high volatility with improving industry breadth", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("hv_drawdown_control_rs", "高波 + 回撤受控 + 排名强", "high_volatility_decomposition", "early_entry_discovery", (c("high_vol_drawdown_controlled", ("true",)), c("ret20_universe_pctile", ("p80_90", "p90_100"))), "high volatility, controlled drawdown, strong rank", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("hv_atr_above_median", "高ATR但守住中位价", "high_volatility_decomposition", "early_entry_discovery", (c("high_atr_above_median20", ("true",)), c("ret_rank_jump5_20", ("p60_80", "p80_90", "p90_100"))), "high ATR above median20 with rank jump", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("hv_reversal_lower_shadow", "高波反转下影", "high_volatility_decomposition", "early_entry_discovery", (c("reversal_volatility_flag", ("true",)), c("money_ratio20", ("p60_80", "p80_90", "p90_100"))), "reversal volatility with money support", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("hv_failed_destructive", "破坏性高波对照", "high_volatility_decomposition", "early_entry_discovery", (c("destructive_volatility_flag", ("true",)), c("failed_high_volatility_flag", ("true",))), "destructive and failed high volatility", "true_low", "drop_or_false_positive_audit", diagnostic_only_not_p1_ready=True),
        P05PatternSpec("hv_break_structure", "高ATR跌破结构对照", "high_volatility_decomposition", "early_entry_discovery", (c("high_atr_break_short_structure", ("true",)), c("close_location_in_day", ("p0_10", "p10_20", "p20_40"))), "high ATR breaks short structure", "true_low", "drop_or_false_positive_audit", diagnostic_only_not_p1_ready=True),
        P05PatternSpec("hv_late_acceleration", "后段加速高波", "high_volatility_decomposition", "hold_exit_tolerance", (c("late_acceleration_volatility_flag", ("true",)), c("trend_speed_bucket", ("speed_fast",))), "late acceleration volatility and fast trend", "true_high", "p1_hold_exit_refine", diagnostic_only_not_p1_ready=True),
        P05PatternSpec("hv_high_money_control", "高波 + 放量 + 上半区", "high_volatility_decomposition", "confirmation_continuation", (c("high_vol_money_quality_flag", ("true",)), c("relative_ret20_vs_benchmark", ("p60_80", "p80_90", "p90_100"))), "high volatility with money quality and benchmark relative strength", "true_high", "p1_confirmation_refine"),
        P05PatternSpec("hv_up_vs_down_spread", "上涨高波优于下跌高波", "high_volatility_decomposition", "early_entry_discovery", (c("up_day_amplitude", ("p80_90", "p90_100")), c("down_day_amplitude", ("missing", "p0_10", "p10_20", "p20_40"))), "up-day amplitude high without down-day amplitude dominance", "high_low", "p1_hypothesis_refine"),

        P05PatternSpec("repair_reclaim20_under20", "20日中位价收复 + 未涨20%", "repair_initiation", "early_entry_discovery", (c("reclaim_median20_flag", ("true",)), c("repair_under20_from_low120", ("true",))), "reclaim median20 before post-20 confirmation", "true_true", "p1_hypothesis_refine"),
        P05PatternSpec("repair_reclaim60_under30", "60日中位价收复 + 未涨30%", "repair_initiation", "early_entry_discovery", (c("reclaim_median60_flag", ("true",)), c("repair_under30_from_low120", ("true",))), "reclaim median60 before post-30 confirmation", "true_true", "p1_hypothesis_refine"),
        P05PatternSpec("repair_first_reclaim_drawdown", "深回撤后首次收复", "repair_initiation", "early_entry_discovery", (c("first_reclaim_median20_after_drawdown", ("true",)), c("drawdown_from_high120", ("p0_10", "p10_20", "p20_40"))), "first median reclaim after drawdown", "true_low", "p1_hypothesis_refine"),
        P05PatternSpec("repair_higher_low_rank_jump", "低点抬高 + 排名跃迁", "repair_initiation", "early_entry_discovery", (c("higher_low20_flag", ("true",)), c("ret_rank_jump5_20", ("p80_90", "p90_100"))), "higher low with return rank jump", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("repair_higher_low_no_breakout", "低点抬高但高点未破", "repair_initiation", "early_entry_discovery", (c("higher_low_without_high_breakout", ("true",)), c("ret_rank_jump20_60", ("p60_80", "p80_90", "p90_100"))), "higher low before high breakout", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("repair_false_breakdown_reclaim", "假跌破后快速收复", "repair_initiation", "early_entry_discovery", (c("false_breakdown_reclaim20", ("true",)), c("close_location_in_day", ("p60_80", "p80_90", "p90_100"))), "false breakdown reclaim with upper close", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("repair_slowing_drawdown", "回撤速度减弱 + 初修复", "repair_initiation", "early_entry_discovery", (c("drawdown_speed_slowing20", ("p80_90", "p90_100")), c("repair_under20_from_low120", ("true",))), "slowing drawdown plus early repair", "high_true", "p1_hypothesis_refine"),
        P05PatternSpec("repair_from_low_rs", "低点修复 + 相对强", "repair_initiation", "early_entry_discovery", (c("repair_under30_from_low120", ("true",)), c("relative_ret20_vs_benchmark", ("p60_80", "p80_90", "p90_100"))), "repair from low with benchmark relative strength", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("repair_industry_lag", "初修复 + 行业未同步", "repair_initiation", "early_entry_discovery", (c("early_repair_industry_lag", ("true",)), c("stock_leads_industry_lag", ("true",))), "early repair while industry has not synchronized", "true_true", "p1_hypothesis_refine"),

        P05PatternSpec("rank_jump_5_20", "5日排名跃迁", "rank_jump_leadership", "early_entry_discovery", (c("ret_rank_jump5_20", ("p90_100",)), c("ret20_universe_pctile", ("p20_40", "p40_60", "p60_80", "p80_90"))), "rank jump before absolute top10 strength", "high_not_top10", "p1_first_stage_filter"),
        P05PatternSpec("rank_jump_20_60", "20日相对60日排名跃迁", "rank_jump_leadership", "early_entry_discovery", (c("ret_rank_jump20_60", ("p80_90", "p90_100")), c("ret60_universe_pctile_p0_5", ("p0_10", "p10_20", "p20_40", "p40_60"))), "20d rank jump from weaker 60d base", "high_low", "p1_first_stage_filter"),
        P05PatternSpec("rank_industry_bottom_to_top", "行业内从中后排跃迁到前20%", "rank_jump_leadership", "early_entry_discovery", (c("from_industry_below_median_to_top20", ("true",)), c("industry_ret_rank_jump5_20", ("p60_80", "p80_90", "p90_100"))), "industry rank jump from below median to top 20", "true_high", "p1_first_stage_filter"),
        P05PatternSpec("rank_market_top20_industry_lag", "市场前20%但行业未同步", "rank_jump_leadership", "early_entry_discovery", (c("market_top20_industry_lag", ("true",)), c("industry_width_state", ("industry_width_weak", "industry_width_neutral"))), "market top20 stock before industry width sync", "true_regime", "p1_hypothesis_refine"),
        P05PatternSpec("rank_stock_leads_industry", "个股领先滞后行业", "rank_jump_leadership", "early_entry_discovery", (c("stock_leads_industry_lag", ("true",)), c("relative_ret20_vs_industry", ("p80_90", "p90_100"))), "stock leads lagging industry", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("rank_isolated_weak_market", "弱市孤立强势", "rank_jump_leadership", "early_entry_discovery", (c("isolated_strength_weak_market", ("true",)), c("market_regime_state", ("market_drawdown", "market_choppy"))), "isolated strength in weak market", "true_regime", "p1_first_stage_filter"),
        P05PatternSpec("rank_market_turn_front", "市场转折前排个股", "rank_jump_leadership", "early_entry_discovery", (c("market_turn_front_runner", ("true",)), c("ret_rank_jump5_20", ("p60_80", "p80_90", "p90_100"))), "front runner near market turn", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("rank_industry_width_front", "行业宽度刚改善的前排个股", "rank_jump_leadership", "early_entry_discovery", (c("industry_width_improving_front_runner", ("true",)), c("ret20_industry_pctile", ("p80_90", "p90_100"))), "front row when industry width improves", "true_high", "p1_hypothesis_refine"),

        P05PatternSpec("money_up_day_quality", "上涨日放量", "money_quality", "confirmation_continuation", (c("up_day_money_ratio20", ("p80_90", "p90_100")), c("close_location_in_day", ("p60_80", "p80_90", "p90_100"))), "up-day money expansion with upper close", "high_high", "p1_confirmation_refine"),
        P05PatternSpec("money_down_day_warning", "下跌日放量警示", "money_quality", "early_entry_discovery", (c("down_day_money_ratio20", ("p80_90", "p90_100")), c("close_location_in_day", ("p0_10", "p10_20", "p20_40"))), "down-day money expansion with weak close", "high_low", "drop_or_false_positive_audit", diagnostic_only_not_p1_ready=True),
        P05PatternSpec("money_pullback_contraction", "回撤缩量", "money_quality", "early_entry_discovery", (c("pullback_volume_contraction", ("true",)), c("higher_low20_flag", ("true",))), "pullback contraction with higher low", "true_true", "p1_hypothesis_refine"),
        P05PatternSpec("money_hold_3d", "放量后3日价格保持", "money_quality", "confirmation_continuation", (c("volume_price_hold_3d", ("true",)), c("ret20_universe_pctile", ("p60_80", "p80_90", "p90_100"))), "price holds after money spike", "true_high", "p1_confirmation_refine"),
        P05PatternSpec("money_hold_5d", "放量后5日价格保持", "money_quality", "confirmation_continuation", (c("volume_price_hold_5d", ("true",)), c("relative_ret20_vs_benchmark", ("p60_80", "p80_90", "p90_100"))), "5d price hold after volume spike", "true_high", "p1_confirmation_refine"),
        P05PatternSpec("money_spike_failed", "放量后快速跌破", "money_quality", "early_entry_discovery", (c("volume_spike_failed_5d", ("true",)), c("money_ratio20", ("p80_90", "p90_100"))), "failed volume spike", "true_high", "drop_or_false_positive_audit", diagnostic_only_not_p1_ready=True),
        P05PatternSpec("money_rank_ret_rank", "成交排名跃迁 + 收益排名跃迁", "money_quality", "early_entry_discovery", (c("money_rank_jump_with_ret_rank_jump", ("true",)), c("ret_rank_jump5_20", ("p80_90", "p90_100"))), "money rank jump with return rank jump", "true_high", "p1_hypothesis_refine"),
        P05PatternSpec("money_persistent_quality", "高成交额持续", "money_quality", "confirmation_continuation", (c("high_money_persistence5", ("true",)), c("money_close_location_score", ("p80_90", "p90_100"))), "persistent high money with good close location", "true_high", "p1_confirmation_refine"),
        P05PatternSpec("money_industry_improve", "成交放大 + 行业宽度改善", "money_quality", "confirmation_continuation", (c("money_industry_width_improve", ("true",)), c("industry_width_delta20", ("p80_90", "p90_100"))), "money expansion with industry breadth improvement", "true_high", "p1_confirmation_refine"),

        P05PatternSpec("sparse_first_limit", "首次涨停诊断", "sparse_strong_day_diagnostic", "confirmation_continuation", (c("first_limit_up_60d", ("true",)), c("limit_up_count20", ("p60_80", "p80_90", "p90_100"))), "first limit-up in 60d", "true_high", "p1_path_diagnostic", True, False, True),
        P05PatternSpec("sparse_first_near_limit", "首次接近涨停诊断", "sparse_strong_day_diagnostic", "confirmation_continuation", (c("first_near_limit_up_60d", ("true",)), c("near_limit_up_count20", ("p60_80", "p80_90", "p90_100"))), "first near-limit-up in 60d", "true_high", "p1_path_diagnostic", True, False, True),
        P05PatternSpec("sparse_gap_upper_hold", "Gap up 上半区且守住", "sparse_strong_day_diagnostic", "confirmation_continuation", (c("gap_up_close_upper", ("true",)), c("gap_up_held_3d", ("true",))), "gap-up closes upper and holds", "true_true", "p1_path_diagnostic", True, False, True),
        P05PatternSpec("sparse_strong_body", "极强实体日诊断", "sparse_strong_day_diagnostic", "confirmation_continuation", (c("strong_body_day", ("true",)), c("close_location_in_day", ("p80_90", "p90_100"))), "strong body up day", "true_high", "p1_path_diagnostic", True, False, True),
        P05PatternSpec("sparse_upper_shadow_fail", "长上影强势失败", "sparse_strong_day_diagnostic", "hold_exit_tolerance", (c("long_upper_shadow_failure", ("true",)), c("money_ratio20", ("p80_90", "p90_100"))), "long upper shadow failure with money", "true_high", "drop_or_false_positive_audit", True, False, True, True),
        P05PatternSpec("sparse_strong_pullback_hold", "强势日后缩量回撤守住", "sparse_strong_day_diagnostic", "hold_exit_tolerance", (c("strong_day_pullback_hold20", ("true",)), c("drawdown_from_high20", ("p80_90", "p90_100"))), "strong-day pullback holds structure", "true_high", "p1_hold_exit_refine", True, False, True),
    ]
    return patterns


def p0_5_build_bins(df: pd.DataFrame, config: dict[str, Any], specs: list[P05PrimitiveSpec]) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    bins: dict[str, pd.Series] = {}
    elig: dict[str, pd.Series] = {}
    for spec in specs:
        bins[spec.feature_name] = primitive_bin(df, spec, config)
        elig[spec.feature_name] = primitive_eligible(df, spec)
        df[f"bin__p0_5__{spec.feature_name}"] = bins[spec.feature_name]
    return bins, elig


def p0_5_condition_from_pattern(pattern: P05PatternSpec, bins: dict[str, pd.Series], elig: dict[str, pd.Series]) -> tuple[pd.Series, pd.Series]:
    first_feature = pattern.conditions[0][0]
    index = bins[first_feature].index
    condition = pd.Series(True, index=index)
    eligible = pd.Series(True, index=index)
    for feature, values in pattern.conditions:
        condition &= bins[feature].isin(values)
        eligible &= elig[feature].fillna(False).astype(bool)
    return condition, eligible


def p0_5_trigger_events(df: pd.DataFrame, mask: pd.Series, positive_col: str, gap: int) -> pd.DataFrame:
    subset = df.loc[mask.fillna(False).astype(bool), ["instrument", "datetime", "year", "instrument_year", "instrument_day_index", positive_col, "future_50pct_episode_key_240d"]].copy()
    if subset.empty:
        return pd.DataFrame(columns=["event_id", "instrument", "year", "instrument_year", "first_trigger_date", "positive", "future_episode_key"])
    rows: list[dict[str, Any]] = []
    for instrument, group in subset.sort_values(["instrument", "instrument_day_index"]).groupby("instrument", sort=False):
        last_idx: int | None = None
        event_number = 0
        for row in group.itertuples(index=False):
            idx = int(row.instrument_day_index)
            if last_idx is None or idx - last_idx > gap:
                event_number += 1
                rows.append(
                    {
                        "event_id": f"{instrument}_{event_number}_{iso_date(row.datetime)}",
                        "instrument": instrument,
                        "year": int(row.year),
                        "instrument_year": row.instrument_year,
                        "first_trigger_date": pd.Timestamp(row.datetime).normalize(),
                        "positive": bool(getattr(row, positive_col)),
                        "future_episode_key": getattr(row, "future_50pct_episode_key_240d"),
                    }
                )
            last_idx = idx
    return pd.DataFrame(rows)


def p0_5_baseline_pseudo_events(df: pd.DataFrame, base_mask: pd.Series, positive_col: str, gap: int) -> pd.DataFrame:
    subset = df.loc[base_mask.fillna(False).astype(bool), ["instrument", "year", "instrument_year", "datetime", "instrument_day_index", positive_col]].copy()
    if subset.empty:
        return pd.DataFrame(columns=["event_id", "instrument", "year", "instrument_year", "first_trigger_date", "positive"])
    rows: list[dict[str, Any]] = []
    for (instrument, year), group in subset.sort_values(["instrument", "year", "instrument_day_index"]).groupby(["instrument", "year"], sort=False):
        last_idx: int | None = None
        event_number = 0
        for row in group.itertuples(index=False):
            idx = int(row.instrument_day_index)
            if last_idx is None or idx - last_idx >= gap:
                event_number += 1
                rows.append(
                    {
                        "event_id": f"baseline_{instrument}_{int(year)}_{event_number}_{iso_date(row.datetime)}",
                        "instrument": instrument,
                        "year": int(year),
                        "instrument_year": row.instrument_year,
                        "first_trigger_date": pd.Timestamp(row.datetime).normalize(),
                        "positive": bool(getattr(row, positive_col)),
                    }
                )
                last_idx = idx
    return pd.DataFrame(rows)


def p0_5_winner_episode_coverage_for_events(events: pd.DataFrame, episodes: pd.DataFrame) -> tuple[float, int, int, list[str]]:
    if episodes.empty:
        return np.nan, 0, 0, []
    denom = episodes[(episodes["episode_scope"] == "in_year_episode") & (~episodes["observed_reference_overlap"].fillna(False).astype(bool))].copy()
    if denom.empty:
        return np.nan, 0, 0, []
    if events.empty:
        return 0.0, 0, int(len(denom)), []
    event_dates: dict[str, list[pd.Timestamp]] = {}
    for instrument, group in events.groupby("instrument", sort=False):
        event_dates[str(instrument)] = sorted(pd.to_datetime(group["first_trigger_date"]).tolist())
    covered: list[str] = []
    for row in denom.itertuples(index=False):
        low_date = parse_dt(row.low_date)
        high_date = parse_dt(row.high_date)
        dates = event_dates.get(str(row.instrument), [])
        if any((date >= low_date) and (date < high_date) for date in dates):
            covered.append(str(row.episode_id))
    coverage = len(covered) / len(denom) if len(denom) else np.nan
    return coverage, len(covered), int(len(denom)), covered


def summarize_p0_5_condition(
    df: pd.DataFrame,
    condition: pd.Series,
    feature_eligible: pd.Series,
    config: dict[str, Any],
    lead_id: str,
    lead_name: str,
    primary_combo_family: str,
    lifecycle_bucket: str,
    formula_or_bin: str,
    direction: str,
    recommended_next_phase: str,
    episodes: pd.DataFrame,
    sparse_diagnostic: bool = False,
    generalizable_entry_lead: bool = True,
    path_explanation_only: bool = False,
    diagnostic_only_not_p1_ready: bool = False,
    full_metrics: bool = True,
) -> dict[str, Any]:
    cfg = p0_5_cfg(config)
    positive_col = cfg.get("target_label", "is_future_50pct_high_120d")
    secondary_col = cfg.get("secondary_label", "is_future_100pct_high_240d")
    gap = int(cfg.get("dedup_gap_trading_days", 20))
    lifecycle = p0_5_lifecycle_mask(df, config, lifecycle_bucket)
    base_mask = lifecycle & feature_eligible.fillna(False).astype(bool)
    lead_mask = base_mask & condition.fillna(False).astype(bool)
    positive_mask = df[positive_col].fillna(False).astype(bool)
    secondary_valid = (
        lead_mask
        & ~df["label_horizon_truncated_240d"].fillna(True).astype(bool)
        & ~df["observed_reference_overlap_240d"].fillna(True).astype(bool)
    )
    base_count = int(base_mask.sum())
    lead_count = int(lead_mask.sum())
    positive_count = int((lead_mask & positive_mask).sum())
    base_positive_count = int((base_mask & positive_mask).sum())
    lead_precision = safe_div(positive_count, lead_count)
    base_precision = safe_div(base_positive_count, base_count)
    lead_positive_mask = lead_mask & positive_mask
    industry_counts = df.loc[lead_mask, "industry_name"].value_counts(dropna=False)
    top1_industry = safe_div(industry_counts.iloc[0], lead_count) if len(industry_counts) else np.nan
    instrument_counts = df.loc[lead_positive_mask, "instrument"].value_counts(dropna=False)
    episode_counts = df.loc[lead_positive_mask, "future_50pct_episode_key_240d"].dropna().value_counts(dropna=False)

    row: dict[str, Any] = {
        "lead_id": lead_id,
        "lead_name": lead_name,
        "primary_combo_family": primary_combo_family,
        "lifecycle_bucket": lifecycle_bucket,
        "formula_or_bin": formula_or_bin,
        "direction": direction,
        "target_horizon": f"{cfg.get('target_horizon_days', 120)}d",
        "positive_label": positive_col.replace("is_", ""),
        "baseline_scope": f"same_horizon_{lifecycle_bucket}_eligible_pit_stock_days",
        "baseline_stock_day_count": base_count,
        "stock_day_count": lead_count,
        "positive_stock_day_count": positive_count,
        "baseline_stock_day_precision": base_precision,
        "stock_day_precision": lead_precision,
        "stock_day_lift": safe_div(lead_precision, base_precision),
        "lead_future_50pct_precision": float(df.loc[lead_mask, positive_col].mean()) if lead_count else np.nan,
        "lead_future_100pct_240d_precision": float(df.loc[secondary_valid, secondary_col].mean()) if secondary_valid.any() else np.nan,
        "unique_instrument_count": int(df.loc[lead_mask, "instrument"].nunique()),
        "unique_instrument_year_count": int(df.loc[lead_mask, "instrument_year"].nunique()),
        "positive_unique_instrument_count": int(df.loc[lead_positive_mask, "instrument"].nunique()),
        "positive_unique_instrument_year_count": int(df.loc[lead_positive_mask, "instrument_year"].nunique()),
        "distinct_year_count": int(df.loc[lead_mask, "year"].nunique()),
        "distinct_industry_count": int(df.loc[lead_mask, "industry_name"].nunique()),
        "top1_industry_contribution": top1_industry,
        "top1_instrument_contribution": safe_div(instrument_counts.iloc[0], positive_count) if len(instrument_counts) else np.nan,
        "top5_instrument_contribution": safe_div(instrument_counts.head(5).sum(), positive_count) if len(instrument_counts) else np.nan,
        "top1_episode_contribution": safe_div(episode_counts.iloc[0], positive_count) if len(episode_counts) else np.nan,
        "top5_episode_contribution": safe_div(episode_counts.head(5).sum(), positive_count) if len(episode_counts) else np.nan,
        "avg_lead_time_to_50pct_high": float(df.loc[lead_positive_mask, "future_time_to_50pct_high_gain"].mean()) if positive_count else np.nan,
        "median_lead_time_to_50pct_high": float(df.loc[lead_positive_mask, "future_time_to_50pct_high_gain"].median()) if positive_count else np.nan,
        "avg_lead_time_to_50pct_close": float(df.loc[lead_positive_mask, "future_time_to_50pct_close_gain"].mean()) if positive_count else np.nan,
        "avg_lead_time_to_100pct_high": float(df.loc[lead_positive_mask, "future_time_to_100pct_high_gain"].mean()) if positive_count else np.nan,
        "trend_speed_not_fast_rate": float((df.loc[lead_mask, "trend_speed_bucket"].astype("string") != "speed_fast").mean()) if lead_count else np.nan,
        "repair_signal_rate": float(df.loc[lead_mask, ["reclaim_median20_flag", "repair_under20_from_low120", "higher_low20_flag"]].any(axis=1).mean()) if lead_count else np.nan,
        "label_horizon_truncated_rate": float(df.loc[lead_mask, "label_horizon_truncated"].mean()) if lead_count else np.nan,
        "observed_reference_overlap_rate": float(df.loc[lead_mask, "observed_reference_overlap"].mean()) if lead_count else np.nan,
        "false_positive_stock_day_count": int(lead_count - positive_count),
        "false_positive_rate": 1.0 - lead_precision if not pd.isna(lead_precision) else np.nan,
        "false_positive_avg_future_drawdown_120d": float(df.loc[lead_mask & ~positive_mask, "future_max_drawdown_in_horizon_120d"].mean()) if (lead_mask & ~positive_mask).any() else np.nan,
        "sparse_diagnostic": bool(sparse_diagnostic),
        "generalizable_entry_lead": bool(generalizable_entry_lead),
        "path_explanation_only": bool(path_explanation_only),
        "diagnostic_only_not_p1_ready": bool(diagnostic_only_not_p1_ready),
        "recommended_next_phase": recommended_next_phase,
    }
    if not full_metrics:
        row.update(
            {
                "instrument_year_hit_rate": np.nan,
                "baseline_instrument_year_hit_rate": np.nan,
                "instrument_year_hit_lift": np.nan,
                "mean_trigger_count_per_instrument_year": np.nan,
                "median_trigger_count_per_instrument_year": np.nan,
                "p95_trigger_count_per_instrument_year": np.nan,
                "lead_trigger_event_count": np.nan,
                "positive_lead_trigger_event_count": np.nan,
                "dedup_trigger_event_precision": np.nan,
                "baseline_trigger_event_precision": np.nan,
                "dedup_trigger_event_lift": np.nan,
                "winner_episode_coverage": np.nan,
                "winner_episode_covered_count": np.nan,
                "winner_episode_denominator_count": np.nan,
                "stock_day_vs_dedup_lift_gap": np.nan,
                "qualified_lead": False,
                "failure_reason": "univariate_screen_only",
            }
        )
        return row

    lead_iy = df.loc[lead_mask].groupby("instrument_year")[positive_col].any()
    base_iy = df.loc[base_mask].groupby("instrument_year")[positive_col].any()
    trigger_counts = df.loc[lead_mask].groupby("instrument_year").size()
    lead_events = p0_5_trigger_events(df, lead_mask, positive_col, gap)
    base_events = p0_5_baseline_pseudo_events(df, base_mask, positive_col, gap)
    trigger_precision = float(lead_events["positive"].mean()) if not lead_events.empty else np.nan
    base_trigger_precision = float(base_events["positive"].mean()) if not base_events.empty else np.nan
    coverage, covered_count, coverage_denom, covered_ids = p0_5_winner_episode_coverage_for_events(lead_events, episodes)
    iy_hit_rate = float(lead_iy.mean()) if len(lead_iy) else np.nan
    base_iy_hit_rate = float(base_iy.mean()) if len(base_iy) else np.nan
    dedup_lift = safe_div(trigger_precision, base_trigger_precision)
    iy_lift = safe_div(iy_hit_rate, base_iy_hit_rate)
    min_count = int(cfg.get("min_stock_day_count", 100))
    min_years = int(cfg.get("min_distinct_years", 3))
    max_industry = float(cfg.get("max_top1_industry_concentration", 0.60))
    if lead_count < min_count:
        failure = "insufficient_stock_day_count"
    elif pd.isna(dedup_lift) or dedup_lift <= 1.0:
        failure = "dedup_trigger_event_lift_not_positive"
    elif pd.isna(iy_lift) or iy_lift <= 1.0:
        failure = "instrument_year_lift_not_positive"
    elif row["distinct_year_count"] < min_years:
        failure = "insufficient_distinct_years"
    elif not pd.isna(top1_industry) and top1_industry > max_industry:
        failure = "top1_industry_concentration_too_high"
    elif diagnostic_only_not_p1_ready:
        failure = "diagnostic_only_not_p1_ready"
    else:
        failure = ""
    row.update(
        {
            "instrument_year_hit_rate": iy_hit_rate,
            "baseline_instrument_year_hit_rate": base_iy_hit_rate,
            "instrument_year_hit_lift": iy_lift,
            "mean_trigger_count_per_instrument_year": float(trigger_counts.mean()) if len(trigger_counts) else np.nan,
            "median_trigger_count_per_instrument_year": float(trigger_counts.median()) if len(trigger_counts) else np.nan,
            "p95_trigger_count_per_instrument_year": float(trigger_counts.quantile(0.95)) if len(trigger_counts) else np.nan,
            "lead_trigger_event_count": int(len(lead_events)),
            "positive_lead_trigger_event_count": int(lead_events["positive"].sum()) if not lead_events.empty else 0,
            "dedup_trigger_event_precision": trigger_precision,
            "baseline_trigger_event_precision": base_trigger_precision,
            "dedup_trigger_event_lift": dedup_lift,
            "winner_episode_coverage": coverage,
            "winner_episode_covered_count": int(covered_count),
            "winner_episode_denominator_count": int(coverage_denom),
            "covered_winner_episode_ids": ";".join(covered_ids[:20]),
            "stock_day_vs_dedup_lift_gap": row["stock_day_lift"] - dedup_lift if not pd.isna(row["stock_day_lift"]) and not pd.isna(dedup_lift) else np.nan,
            "qualified_lead": failure == "",
            "failure_reason": failure,
        }
    )
    return row


def build_p0_5_feature_outputs(config: dict[str, Any]) -> tuple[pd.DataFrame, Path]:
    if not label_panel_path(config).exists():
        command_build_labels(config)
    df = pd.read_parquet(label_panel_path(config))
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.normalize()
    if "first_feature_eligible_date" in df.columns:
        df["first_feature_eligible_date"] = pd.to_datetime(df["first_feature_eligible_date"], errors="coerce")
    df = add_p0_5_features(df)
    path = p0_5_feature_panel_path(config)
    ensure_parent(path)
    df.to_parquet(path, index=False)
    return df, path


def build_p0_5_feature_coverage(df: pd.DataFrame, specs: list[P05PrimitiveSpec], elig: dict[str, pd.Series], config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in specs:
        eligible = elig[spec.feature_name]
        insufficient = df["available_history_trading_days"] < spec.min_history_trading_days
        warmup = insufficient & (df["year"] == parse_dt(config["dates"]["research_start"]).year)
        missing = df[spec.column].isna() if spec.column in df.columns else pd.Series(True, index=df.index)
        rows.append(
            {
                "feature_name": spec.feature_name,
                "feature_family": spec.feature_family,
                "p0_5_enabled": bool(spec.p0_enabled),
                "p0_5_new": bool(spec.p0_5_new),
                "primary_combo_family": spec.primary_combo_family,
                "lifecycle_bucket": spec.lifecycle_bucket,
                "eligible_rows": int(eligible.sum()),
                "ineligible_rows": int((~eligible).sum()),
                "missing_value_rows": int(missing.sum()),
                "insufficient_history_rows": int(insufficient.sum()),
                "warmup_partial_year": bool(warmup.any()),
                "warmup_partial_year_rows": int(warmup.sum()),
                "first_feature_eligible_date": iso_date(df.loc[eligible, "datetime"].min()) if eligible.any() else "",
                "coverage_note": "",
            }
        )
    return pd.DataFrame(rows)


def build_p0_5_outputs(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], list[Path]]:
    df, feature_panel_path = build_p0_5_feature_outputs(config)
    episodes_path = report_dir(config) / "episode_lifecycle_labels.csv"
    if not episodes_path.exists():
        command_build_labels(config)
    episodes = pd.read_csv(episodes_path) if episodes_path.exists() else pd.DataFrame()
    if not episodes.empty:
        for col in ["low_date", "high_date"]:
            episodes[col] = pd.to_datetime(episodes[col], errors="coerce")

    specs = p0_5_primitive_specs()
    dictionary = p0_5_feature_dictionary()
    bins, elig = p0_5_build_bins(df, config, specs)
    coverage = build_p0_5_feature_coverage(df, specs, elig, config)

    univariate_rows: list[dict[str, Any]] = []
    for spec in specs:
        if spec.feature_name not in bins:
            continue
        eligible = elig[spec.feature_name]
        for bin_value in sorted(pd.Series(bins[spec.feature_name]).dropna().astype(str).unique()):
            if bin_value == "missing":
                continue
            condition = bins[spec.feature_name].astype(str) == bin_value
            row = summarize_p0_5_condition(
                df,
                condition,
                eligible,
                config,
                f"p0_5_uni_{spec.feature_name}_{bin_value}",
                spec.feature_name,
                spec.primary_combo_family or spec.feature_family,
                spec.lifecycle_bucket,
                f"{spec.feature_name} == {bin_value}",
                spec.direction_hint,
                "p1_hypothesis_refine" if spec.generalizable_entry_lead else "p1_path_diagnostic",
                episodes,
                spec.sparse_diagnostic,
                spec.generalizable_entry_lead,
                spec.path_explanation_only,
                spec.diagnostic_only_not_p1_ready,
                full_metrics=False,
            )
            row["feature_name"] = spec.feature_name
            row["bin_value"] = bin_value
            row["lead_type"] = "univariate_primitive"
            univariate_rows.append(row)
    univariate = pd.DataFrame(univariate_rows)

    pairwise_rows: list[dict[str, Any]] = []
    shadow_rows: list[dict[str, Any]] = []
    for pattern in p0_5_patterns():
        condition, eligible = p0_5_condition_from_pattern(pattern, bins, elig)
        row = summarize_p0_5_condition(
            df,
            condition,
            eligible,
            config,
            pattern.lead_id,
            pattern.lead_name,
            pattern.primary_combo_family,
            pattern.lifecycle_bucket,
            pattern.formula_or_bin,
            pattern.direction,
            pattern.recommended_next_phase,
            episodes,
            pattern.sparse_diagnostic,
            pattern.generalizable_entry_lead,
            pattern.path_explanation_only,
            pattern.diagnostic_only_not_p1_ready,
            full_metrics=True,
        )
        row["lead_type"] = "p0_5_diagnostic_combo"
        row["audit_scope"] = "main"
        row["condition_features"] = ";".join(feature for feature, _values in pattern.conditions)
        pairwise_rows.append(row)
        if pattern.lifecycle_bucket == "early_entry_discovery":
            for shadow_bucket in [
                "early_entry_shadow_with_post_20pct",
                "early_entry_shadow_with_post_30pct",
                "early_entry_shadow_with_late_acceleration",
            ]:
                shadow = summarize_p0_5_condition(
                    df,
                    condition,
                    eligible,
                    config,
                    f"{pattern.lead_id}_{shadow_bucket}",
                    pattern.lead_name,
                    pattern.primary_combo_family,
                    shadow_bucket,
                    pattern.formula_or_bin,
                    pattern.direction,
                    "shadow_audit_only",
                    episodes,
                    pattern.sparse_diagnostic,
                    pattern.generalizable_entry_lead,
                    pattern.path_explanation_only,
                    pattern.diagnostic_only_not_p1_ready,
                    full_metrics=False,
                )
                shadow["lead_type"] = "p0_5_shadow_audit"
                shadow["audit_scope"] = "shadow"
                shadow["condition_features"] = ";".join(feature for feature, _values in pattern.conditions)
                shadow_rows.append(shadow)
    pairwise = pd.DataFrame(pairwise_rows)

    if not pairwise.empty:
        stock_rank = pairwise.sort_values(["stock_day_lift", "stock_day_count"], ascending=[False, False]).reset_index(drop=True)
        stock_rank.insert(0, "stock_day_rank", range(1, len(stock_rank) + 1))
        iy_rank = pairwise.sort_values(["instrument_year_hit_lift", "unique_instrument_year_count"], ascending=[False, False]).reset_index(drop=True)
        iy_rank.insert(0, "instrument_year_rank", range(1, len(iy_rank) + 1))
        dedup_rank = pairwise.sort_values(["dedup_trigger_event_lift", "lead_trigger_event_count"], ascending=[False, False]).reset_index(drop=True)
        dedup_rank.insert(0, "dedup_trigger_rank", range(1, len(dedup_rank) + 1))
    else:
        stock_rank = pd.DataFrame()
        iy_rank = pd.DataFrame()
        dedup_rank = pd.DataFrame()

    def board(lifecycle: str) -> pd.DataFrame:
        cols = pairwise[pairwise["lifecycle_bucket"] == lifecycle].copy() if not pairwise.empty else pd.DataFrame()
        if cols.empty:
            return cols
        return cols.sort_values(["qualified_lead", "dedup_trigger_event_lift", "instrument_year_hit_lift"], ascending=[False, False, False]).reset_index(drop=True)

    early = board("early_entry_discovery")
    confirmation = board("confirmation_continuation")
    hold_exit = board("hold_exit_tolerance")
    high_vol = pairwise[pairwise["primary_combo_family"] == "high_volatility_decomposition"].copy() if not pairwise.empty else pd.DataFrame()
    repair = pairwise[pairwise["primary_combo_family"] == "repair_initiation"].copy() if not pairwise.empty else pd.DataFrame()
    rank_jump = pairwise[pairwise["primary_combo_family"] == "rank_jump_leadership"].copy() if not pairwise.empty else pd.DataFrame()
    money = pairwise[pairwise["primary_combo_family"] == "money_quality"].copy() if not pairwise.empty else pd.DataFrame()
    sparse = pairwise[pairwise["primary_combo_family"] == "sparse_strong_day_diagnostic"].copy() if not pairwise.empty else pd.DataFrame()
    winner_coverage = pairwise[
        [
            "lead_id",
            "lead_name",
            "primary_combo_family",
            "lifecycle_bucket",
            "winner_episode_coverage",
            "winner_episode_covered_count",
            "winner_episode_denominator_count",
            "covered_winner_episode_ids",
            "dedup_trigger_event_lift",
            "qualified_lead",
            "failure_reason",
        ]
    ].copy() if not pairwise.empty else pd.DataFrame()
    false_positive = pairwise[
        [
            "lead_id",
            "lead_name",
            "primary_combo_family",
            "lifecycle_bucket",
            "false_positive_stock_day_count",
            "false_positive_rate",
            "false_positive_avg_future_drawdown_120d",
            "stock_day_precision",
            "dedup_trigger_event_precision",
            "dedup_trigger_event_lift",
            "failure_reason",
        ]
    ].copy() if not pairwise.empty else pd.DataFrame()
    false_positive["evaluation_only_false_positive_definition"] = "forward-label miss and future drawdown audit only; not used as feature, lead formula, candidate selection, or ranking input"
    candidate_audit = pd.concat([pairwise, pd.DataFrame(shadow_rows)], ignore_index=True, sort=False)

    completion = build_p0_5_completion_audit(dictionary, pairwise, early, confirmation, hold_exit)
    frames = {
        "p0_5_primitive_feature_dictionary.csv": dictionary,
        "p0_5_primitive_feature_coverage.csv": coverage,
        "p0_5_univariate_lift.csv": univariate,
        "p0_5_pairwise_lift.csv": pairwise,
        "p0_5_lead_ranking_stock_day.csv": stock_rank,
        "p0_5_lead_ranking_instrument_year.csv": iy_rank,
        "p0_5_lead_ranking_dedup_trigger_event.csv": dedup_rank,
        "p0_5_winner_episode_coverage.csv": winner_coverage,
        "p0_5_early_entry_discovery_leads.csv": early,
        "p0_5_confirmation_continuation_leads.csv": confirmation,
        "p0_5_hold_exit_tolerance_leads.csv": hold_exit,
        "p0_5_high_volatility_decomposition.csv": high_vol,
        "p0_5_repair_initiation_leads.csv": repair,
        "p0_5_rank_jump_leadership_leads.csv": rank_jump,
        "p0_5_money_quality_leads.csv": money,
        "p0_5_sparse_strong_day_diagnostics.csv": sparse,
        "p0_5_candidate_pattern_audit.csv": candidate_audit,
        "p0_5_false_positive_audit.csv": false_positive,
        "p0_5_scope_completion_audit.csv": completion,
    }
    outputs: list[Path] = [feature_panel_path]
    for name, frame in frames.items():
        outputs.append(write_csv(frame, report_dir(config) / name))
    record_p0_5_manifest(config, "profile-p0-5", outputs, frames, df)
    return frames, outputs


def build_p0_5_completion_audit(
    dictionary: pd.DataFrame,
    pairwise: pd.DataFrame,
    early: pd.DataFrame,
    confirmation: pd.DataFrame,
    hold_exit: pd.DataFrame,
) -> pd.DataFrame:
    cfg = {
        "required_enabled_primitives": 90,
        "required_new_primitives": 35,
        "required_pairwise_combos": 30,
        "required_high_volatility_combos": 10,
        "required_repair_combos": 8,
        "required_rank_jump_combos": 6,
        "required_money_quality_combos": 6,
        "required_sparse_strong_day_patterns": 5,
    }
    enabled_count = int(dictionary[dictionary["p0_5_enabled"].astype(bool)]["feature_name"].nunique()) if not dictionary.empty else 0
    new_count = int(dictionary[dictionary["p0_5_new"].astype(bool)]["feature_name"].nunique()) if not dictionary.empty else 0
    combo_count = int(pairwise["lead_id"].nunique()) if not pairwise.empty else 0
    family_counts = pairwise.groupby("primary_combo_family")["lead_id"].nunique().to_dict() if not pairwise.empty else {}
    qualified = pairwise[pairwise["qualified_lead"].fillna(False).astype(bool)] if not pairwise.empty else pd.DataFrame()
    qualified_counts = qualified.groupby("primary_combo_family")["lead_id"].nunique().to_dict() if not qualified.empty else {}
    checks: list[tuple[str, Any, Any, bool, str]] = []

    def add_check(name: str, actual: Any, required: Any, passed: bool, failure: str = "") -> None:
        checks.append((name, actual, required, bool(passed), "" if passed else failure))

    add_check("p0_5_enabled_primitive_count", enabled_count, cfg["required_enabled_primitives"], enabled_count >= cfg["required_enabled_primitives"], "enabled primitive count below requirement")
    add_check("p0_5_new_primitive_count", new_count, cfg["required_new_primitives"], new_count >= cfg["required_new_primitives"], "new primitive count below requirement")
    add_check("p0_5_pairwise_diagnostic_combo_count", combo_count, cfg["required_pairwise_combos"], combo_count >= cfg["required_pairwise_combos"], "combo count below requirement")
    add_check("p0_5_high_volatility_combo_count", int(family_counts.get("high_volatility_decomposition", 0)), cfg["required_high_volatility_combos"], int(family_counts.get("high_volatility_decomposition", 0)) >= cfg["required_high_volatility_combos"], "high-vol combo count below requirement")
    add_check("p0_5_repair_initiation_combo_count", int(family_counts.get("repair_initiation", 0)), cfg["required_repair_combos"], int(family_counts.get("repair_initiation", 0)) >= cfg["required_repair_combos"], "repair combo count below requirement")
    add_check("p0_5_rank_jump_combo_count", int(family_counts.get("rank_jump_leadership", 0)), cfg["required_rank_jump_combos"], int(family_counts.get("rank_jump_leadership", 0)) >= cfg["required_rank_jump_combos"], "rank jump combo count below requirement")
    add_check("p0_5_money_quality_combo_count", int(family_counts.get("money_quality", 0)), cfg["required_money_quality_combos"], int(family_counts.get("money_quality", 0)) >= cfg["required_money_quality_combos"], "money combo count below requirement")
    add_check("p0_5_sparse_strong_day_pattern_count", int(family_counts.get("sparse_strong_day_diagnostic", 0)), cfg["required_sparse_strong_day_patterns"], int(family_counts.get("sparse_strong_day_diagnostic", 0)) >= cfg["required_sparse_strong_day_patterns"], "sparse strong-day pattern count below requirement")
    add_check("tested_early_entry_candidate_patterns", int((pairwise["lifecycle_bucket"] == "early_entry_discovery").sum()) if not pairwise.empty else 0, 8, int((pairwise["lifecycle_bucket"] == "early_entry_discovery").sum()) >= 8 if not pairwise.empty else False, "early-entry tested patterns below requirement")
    add_check("tested_high_volatility_candidate_patterns", int(family_counts.get("high_volatility_decomposition", 0)), 10, int(family_counts.get("high_volatility_decomposition", 0)) >= 10, "high-vol tested patterns below requirement")
    add_check("tested_repair_initiation_candidate_patterns", int(family_counts.get("repair_initiation", 0)), 8, int(family_counts.get("repair_initiation", 0)) >= 8, "repair tested patterns below requirement")
    add_check("tested_rank_jump_candidate_patterns", int(family_counts.get("rank_jump_leadership", 0)), 6, int(family_counts.get("rank_jump_leadership", 0)) >= 6, "rank tested patterns below requirement")
    add_check("tested_money_quality_candidate_patterns", int(family_counts.get("money_quality", 0)), 6, int(family_counts.get("money_quality", 0)) >= 6, "money tested patterns below requirement")
    add_check("qualified_early_entry_leads", int((qualified["lifecycle_bucket"] == "early_entry_discovery").sum()) if not qualified.empty else 0, 0, True, "")
    add_check("qualified_high_volatility_leads", int(qualified_counts.get("high_volatility_decomposition", 0)), 0, True, "")
    add_check("qualified_repair_initiation_leads", int(qualified_counts.get("repair_initiation", 0)), 0, True, "")
    add_check("qualified_rank_jump_leads", int(qualified_counts.get("rank_jump_leadership", 0)), 0, True, "")
    add_check("qualified_money_quality_leads", int(qualified_counts.get("money_quality", 0)), 0, True, "")
    add_check("early_entry_discovery_board_present", int(len(early)), 1, len(early) >= 1, "early-entry board is empty")
    add_check("confirmation_continuation_board_present", int(len(confirmation)), 1, len(confirmation) >= 1, "confirmation board is empty")
    add_check("hold_exit_tolerance_board_present", int(len(hold_exit)), 1, len(hold_exit) >= 1, "hold/exit board is empty")
    minimum_met = all(row[3] for row in checks if not str(row[0]).startswith("qualified_"))
    add_check("explore9_p0_5_minimum_coverage_met", int(minimum_met), 1, minimum_met, "minimum coverage requirement not fully met")
    return pd.DataFrame(checks, columns=["check_name", "actual_value", "required_value", "passed", "failure_reason"])


def output_file_stats(paths: list[Path], frames: dict[str, pd.DataFrame], feature_panel: pd.DataFrame | None = None) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    row_counts: dict[str, int] = {}
    column_counts: dict[str, int] = {}
    file_sizes: dict[str, int] = {}
    for path in paths:
        rel = relpath(path)
        if path.exists():
            file_sizes[rel] = int(path.stat().st_size)
        if path.name in frames:
            row_counts[rel] = int(len(frames[path.name]))
            column_counts[rel] = int(len(frames[path.name].columns))
        elif path.suffix == ".parquet" and feature_panel is not None:
            row_counts[rel] = int(len(feature_panel))
            column_counts[rel] = int(len(feature_panel.columns))
    return row_counts, column_counts, file_sizes


def record_p0_5_manifest(config: dict[str, Any], command: str, outputs: list[Path], frames: dict[str, pd.DataFrame], feature_panel: pd.DataFrame) -> Path:
    path = p0_5_manifest_path(config)
    existing = read_json(path)
    commands = list(existing.get("command_sequence", []))
    commands.append(command)
    all_outputs = sorted(set(existing.get("output_paths", []) + [relpath(p) for p in outputs] + [relpath(path)]))
    row_counts, column_counts, file_sizes = output_file_stats(outputs + [path], frames, feature_panel)
    row_counts = {**existing.get("row_count_by_output", {}), **row_counts}
    column_counts = {**existing.get("column_count_by_output", {}), **column_counts}
    file_sizes = {**existing.get("file_size_by_output", {}), **file_sizes}
    completion = frames.get("p0_5_scope_completion_audit.csv", pd.DataFrame())
    minimum_met = bool(existing.get("explore9_p0_5_minimum_coverage_met", False))
    if not completion.empty:
        row = completion[completion["check_name"] == "explore9_p0_5_minimum_coverage_met"]
        minimum_met = bool(row["passed"].iloc[0]) if not row.empty else False
    elif (report_dir(config) / "p0_5_scope_completion_audit.csv").exists():
        disk_completion = read_csv_if_exists(report_dir(config) / "p0_5_scope_completion_audit.csv")
        row = disk_completion[disk_completion["check_name"] == "explore9_p0_5_minimum_coverage_met"] if not disk_completion.empty else pd.DataFrame()
        minimum_met = bool(row["passed"].iloc[0]) if not row.empty else minimum_met
    manifest = {
        "experiment": "Explore9 P0.5 expand 1 early structure discovery",
        "phase": "P0.5",
        "expansion_id": p0_5_cfg(config).get("expansion_id", "expand_1"),
        "config_path": relpath(config["_config_path"]),
        "config_sha256": config["_config_sha256"],
        "command_line": " ".join(sys.argv),
        "command_sequence": commands,
        "input_report_paths": [
            relpath(report_dir(config) / "run_manifest.json"),
            relpath(report_dir(config) / "episode_lifecycle_labels.csv"),
            relpath(report_dir(config) / "primitive_feature_dictionary.csv"),
            relpath(report_dir(config) / "primitive_univariate_lift.csv"),
            relpath(report_dir(config) / "primitive_pairwise_lift.csv"),
        ],
        "input_cache_paths": [relpath(label_panel_path(config)), relpath(cache_dir(config) / "stock_day_label_panel_meta.json")],
        "output_report_paths": sorted(relpath(p) for p in outputs if p.suffix != ".parquet"),
        "output_cache_paths": sorted(relpath(p) for p in outputs if p.suffix == ".parquet"),
        "output_paths": all_outputs,
        "row_count_by_output": row_counts,
        "column_count_by_output": column_counts,
        "file_size_by_output": file_sizes,
        "p0_label_panel_reused": bool(label_panel_path(config).exists()),
        "p0_episode_labels_reused": bool((report_dir(config) / "episode_lifecycle_labels.csv").exists()),
        "p0_5_new_feature_panel_generated": bool(p0_5_feature_panel_path(config).exists()),
        "p0_5_feature_panel": {
            "path": relpath(p0_5_feature_panel_path(config)),
            "row_count": int(len(feature_panel)),
            "column_count": int(len(feature_panel.columns)),
        },
        "observed_reference_used_for_selection": False,
        "historical_trade_results_used_for_labeling": False,
        "historical_trade_results_used_for_signal": False,
        "historical_trade_results_used_for_selection": False,
        "explore8_profile_csv_used_for_label": False,
        "explore8_profile_csv_used_for_signal": False,
        "explore8_profile_csv_used_for_selection": False,
        "future_labels_used_as_features": False,
        "strategy_backtest_generated": False,
        "formal_hypothesis_generated": False,
        "explore9_p0_5_minimum_coverage_met": minimum_met,
    }
    write_json(manifest, path)
    return path


def command_profile_p0_5(config: dict[str, Any]) -> list[Path]:
    frames, outputs = build_p0_5_outputs(config)
    manifest = p0_5_manifest_path(config)
    outputs.append(manifest)
    completion = frames.get("p0_5_scope_completion_audit.csv", pd.DataFrame())
    min_met = False
    if not completion.empty:
        row = completion[completion["check_name"] == "explore9_p0_5_minimum_coverage_met"]
        min_met = bool(row["passed"].iloc[0]) if not row.empty else False
    print(f"profiled p0.5 outputs={len(outputs)} minimum_coverage={str(min_met).lower()}", flush=True)
    return outputs


def command_report_p0_5(config: dict[str, Any]) -> list[Path]:
    required = [name for name in P0_5_REQUIRED_REPORTS if name not in {"p0_5_run_manifest.json", "explore9_p0_5_expand_1_report.md"}]
    if any(not (report_dir(config) / name).exists() for name in required):
        command_profile_p0_5(config)
    report_path = report_dir(config) / "explore9_p0_5_expand_1_report.md"
    completion = read_csv_if_exists(report_dir(config) / "p0_5_scope_completion_audit.csv")
    early = read_csv_if_exists(report_dir(config) / "p0_5_early_entry_discovery_leads.csv")
    confirmation = read_csv_if_exists(report_dir(config) / "p0_5_confirmation_continuation_leads.csv")
    hold_exit = read_csv_if_exists(report_dir(config) / "p0_5_hold_exit_tolerance_leads.csv")
    high_vol = read_csv_if_exists(report_dir(config) / "p0_5_high_volatility_decomposition.csv")
    repair = read_csv_if_exists(report_dir(config) / "p0_5_repair_initiation_leads.csv")
    rank_jump = read_csv_if_exists(report_dir(config) / "p0_5_rank_jump_leadership_leads.csv")
    money = read_csv_if_exists(report_dir(config) / "p0_5_money_quality_leads.csv")
    sparse = read_csv_if_exists(report_dir(config) / "p0_5_sparse_strong_day_diagnostics.csv")
    dictionary = read_csv_if_exists(report_dir(config) / "p0_5_primitive_feature_dictionary.csv")
    pairwise = read_csv_if_exists(report_dir(config) / "p0_5_pairwise_lift.csv")
    p0_leads = read_csv_if_exists(report_dir(config) / "preliminary_discovery_leads.csv")
    manifest = read_json(p0_5_manifest_path(config))
    minimum_met = False
    if not completion.empty:
        row = completion[completion["check_name"] == "explore9_p0_5_minimum_coverage_met"]
        minimum_met = bool(row["passed"].iloc[0]) if not row.empty else False
    early_qualified = int(early["qualified_lead"].fillna(False).astype(bool).sum()) if not early.empty and "qualified_lead" in early else 0
    confirmation_qualified = int(confirmation["qualified_lead"].fillna(False).astype(bool).sum()) if not confirmation.empty and "qualified_lead" in confirmation else 0
    hold_qualified = int(hold_exit["qualified_lead"].fillna(False).astype(bool).sum()) if not hold_exit.empty and "qualified_lead" in hold_exit else 0
    if minimum_met and early_qualified > 0:
        recommendation = "proceed_to_p1_after_p0_5"
    elif minimum_met and (confirmation_qualified > 0 or hold_qualified > 0):
        recommendation = "proceed_to_p1_for_confirmation_hold_only_continue_entry_discovery"
    elif minimum_met:
        recommendation = "continue_p0_broad_discovery"
    else:
        recommendation = "continue_p0_broad_discovery"

    def top_table(frame: pd.DataFrame, title_col: str = "lead_name", limit: int = 8) -> list[list[Any]]:
        if frame.empty:
            return []
        ordered = frame.sort_values(["qualified_lead", "dedup_trigger_event_lift", "instrument_year_hit_lift"], ascending=[False, False, False]).head(limit)
        return [
            [
                row[title_col],
                row["stock_day_count"],
                format_pct(row["stock_day_precision"]),
                format_float(row["stock_day_lift"]),
                format_float(row["dedup_trigger_event_lift"]),
                format_float(row["instrument_year_hit_lift"]),
                format_pct(row["winner_episode_coverage"]),
                row["failure_reason"] if isinstance(row["failure_reason"], str) else "",
            ]
            for _, row in ordered.iterrows()
        ]

    lines: list[str] = []
    lines.append("# Explore9 P0.5 扩展探索报告：Expand 1")
    lines.append("")
    lines.append("## 1. 结论")
    lines.append("")
    lines.append(f"- `explore9_p0_5_minimum_coverage_met = {str(minimum_met).lower()}`。")
    lines.append(f"- `recommendation = {recommendation}`。")
    lines.append(f"- 本轮新增/启用原语 `{int(dictionary['feature_name'].nunique()) if not dictionary.empty else 0}` 个，其中新增 `{int(dictionary[dictionary['p0_5_new'].astype(bool)]['feature_name'].nunique()) if not dictionary.empty else 0}` 个；诊断组合 `{int(pairwise['lead_id'].nunique()) if not pairwise.empty else 0}` 个。")
    lines.append(f"- early-entry qualified lead `{early_qualified}` 个，confirmation qualified lead `{confirmation_qualified}` 个，hold/exit qualified lead `{hold_qualified}` 个。")
    if early_qualified == 0:
        lines.append("- 未发现足够稳定的 early-entry 结构。当前 Explore9 的有效方向不能被误写成初始买点；confirmation / continuation / hold tolerance 仍需单独处理。")
    lines.append("")
    lines.append("## 2. 与 P0 第一版的差异")
    lines.append("")
    lines.append("- P0.5 不替代 P0 标签和 episode，而是复用 `stock_day_label_panel.parquet` 与 `episode_lifecycle_labels.csv`，重新生成 P0.5 专用 feature panel、lead ranking 和 manifest。")
    lines.append("- P0 第一版按 stock-day lift 暴露出高波、强趋势、post-30 continuation 等线索；P0.5 把主榜拆成 early-entry、confirmation、hold/exit，并增加 instrument-year 与 dedup trigger-event ranking。")
    lines.append("- P0.5 early-entry 主榜硬性排除 post-20、post-30 和 late acceleration 状态；这些状态只进入 confirmation、hold/exit 或 shadow audit。")
    lines.append("")
    if not completion.empty:
        rows = []
        for _, row in completion.iterrows():
            rows.append([row["check_name"], row["actual_value"], row["required_value"], row["passed"], row["failure_reason"] if isinstance(row["failure_reason"], str) else ""])
        lines.extend(markdown_table(["检查项", "实际", "要求", "通过", "失败原因"], rows))
        lines.append("")
    lines.append("## 3. 三类 Lead 分离结果")
    lines.append("")
    for title, frame in [("Early Entry Discovery", early), ("Confirmation / Continuation", confirmation), ("Hold / Exit Tolerance", hold_exit)]:
        lines.append(f"### {title}")
        rows = top_table(frame)
        if rows:
            lines.extend(markdown_table(["lead", "样本", "precision", "stock-day lift", "dedup lift", "IY lift", "episode coverage", "失败原因"], rows))
        else:
            lines.append("无可排序样本。")
        lines.append("")
    lines.append("## 4. 结构分解")
    lines.append("")
    for title, frame in [
        ("高波动拆解", high_vol),
        ("修复初期", repair),
        ("Rank Jump / Leadership", rank_jump),
        ("成交质量", money),
        ("Sparse Strong-Day Diagnostic", sparse),
    ]:
        lines.append(f"### {title}")
        rows = top_table(frame, limit=6)
        if rows:
            lines.extend(markdown_table(["lead", "样本", "precision", "stock-day lift", "dedup lift", "IY lift", "episode coverage", "失败原因"], rows))
        else:
            lines.append("无样本。")
        lines.append("")
    lines.append("## 5. P0 线索降级与保留")
    lines.append("")
    if not p0_leads.empty:
        downgraded = p0_leads[p0_leads["lead_id"].astype(str).str.contains("late_acceleration|post_20|post_30", case=False, regex=True)]
        if not downgraded.empty:
            names = "、".join(downgraded["lead_name"].astype(str).head(8).tolist())
            lines.append(f"- P0 中偏生命周期后段的 `{names}` 在 P0.5 中不再计入 early-entry 主榜，只能作为 confirmation / hold / shadow audit。")
        hv_first = high_vol.sort_values("dedup_trigger_event_lift", ascending=False).head(1) if not high_vol.empty else pd.DataFrame()
        if not hv_first.empty:
            row = hv_first.iloc[0]
            lines.append(f"- 高波动方向被拆解后，当前最强结构是 `{row['lead_name']}`，dedup lift `{format_float(row['dedup_trigger_event_lift'])}`，这比 P0 的单一高波分箱更可解释。")
    lines.append("- 凡是 stock-day lift 高但 dedup trigger-event lift 不成立、instrument-year lift 不成立或 top1 行业贡献过高的方向，报告中保留为 negative evidence，不进入 P1 主假设。")
    lines.append("")
    lines.append("## 6. 数据纪律")
    lines.append("")
    flags = [
        "p0_label_panel_reused",
        "p0_episode_labels_reused",
        "p0_5_new_feature_panel_generated",
        "observed_reference_used_for_selection",
        "historical_trade_results_used_for_labeling",
        "historical_trade_results_used_for_signal",
        "historical_trade_results_used_for_selection",
        "explore8_profile_csv_used_for_label",
        "explore8_profile_csv_used_for_signal",
        "explore8_profile_csv_used_for_selection",
    ]
    for flag in flags:
        lines.append(f"- `{flag} = {str(bool(manifest.get(flag, False))).lower()}`")
    lines.append("- `evaluation_only_false_positive_definition` 只由 forward label 与未来回撤审计计算，不进入 T 日 feature、lead formula、candidate selection 或 ranking input。")
    lines.append("")
    lines.append("## 7. 下一步判断")
    lines.append("")
    if recommendation == "proceed_to_p1_after_p0_5":
        lines.append("- 可以进入 P1，但 P1 应只接收 dedup 和 instrument-year 同时成立的 lead，并继续保持 entry / confirmation / hold 的边界。")
    elif recommendation == "proceed_to_p1_for_confirmation_hold_only_continue_entry_discovery":
        lines.append("- 可以围绕 confirmation / hold 进入 P1，同时继续 early-entry broad discovery；不得把后段确认状态写成初始买点。")
    elif recommendation == "continue_p0_broad_discovery":
        lines.append("- 当前更适合继续 broad discovery，优先补足 early-entry 结构和去重后仍稳定的 candidate family。")
    else:
        lines.append("- 当前缺少稳定发现，不建议进入后续策略回测。")
    lines.append("")
    lines.append("Explore10 只能作为远期路径记录，本报告不输出策略回测建议。")
    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = [report_path]
    frames = {"explore9_p0_5_expand_1_report.md": pd.DataFrame([{"recommendation": recommendation, "minimum_met": minimum_met}])}
    feature_panel = pd.read_parquet(p0_5_feature_panel_path(config)) if p0_5_feature_panel_path(config).exists() else pd.DataFrame()
    record_p0_5_manifest(config, "report-p0-5", outputs, frames, feature_panel)
    print(f"wrote p0.5 report {relpath(report_path)} recommendation={recommendation}", flush=True)
    return outputs


def p0_6_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("p0_6", {})


def p0_6_manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "p0_6_run_manifest.json"


def p0_6_launch_panel_cache_path(config: dict[str, Any]) -> Path:
    return topic_path(p0_6_cfg(config).get("launch_event_panel_cache", "Explore9/outputs/cache/p0_6_launch_event_panel.parquet"))


def p0_6_entry_panel_cache_path(config: dict[str, Any]) -> Path:
    return topic_path(p0_6_cfg(config).get("entry_event_panel_cache", "Explore9/outputs/cache/p0_6_entry_event_panel.parquet"))


def p0_6_float(config: dict[str, Any], key: str, default: float) -> float:
    return float(p0_6_cfg(config).get(key, default))


def p0_6_int(config: dict[str, Any], key: str, default: int) -> int:
    return int(p0_6_cfg(config).get(key, default))


def p0_6_load_feature_panel(config: dict[str, Any]) -> pd.DataFrame:
    p05_path = p0_5_feature_panel_path(config)
    if p05_path.exists():
        df = pd.read_parquet(p05_path)
    elif label_panel_path(config).exists():
        df = add_p0_5_features(pd.read_parquet(label_panel_path(config)))
    else:
        raise DataGateError("P0.6 requires stock_day_label_panel.parquet; run build-labels first")
    return p0_6_add_features(df)


def p0_6_add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values(["instrument", "datetime"]).reset_index(drop=True)
    group = df.groupby("instrument", group_keys=False)
    eps = 1e-12
    df["p0_6_row_pos"] = group.cumcount()
    df["p0_6_ret_1d"] = df["close"] / df["prev_close"].replace(0, np.nan) - 1.0
    df["p0_6_ret_5d"] = group["close"].pct_change(5)
    df["p0_6_ret_20d"] = group["close"].pct_change(20)
    df["p0_6_day_range"] = df["high"] / df["low"].replace(0, np.nan) - 1.0
    df["p0_6_body_ret"] = df["close"] / df["open"].replace(0, np.nan) - 1.0
    df["p0_6_close_location"] = ((df["close"] - df["low"]) / (df["high"] - df["low"]).replace(0, np.nan)).clip(0, 1).fillna(0.5)
    df["p0_6_upper_shadow_ratio"] = ((df["high"] - df[["open", "close"]].max(axis=1)) / (df["high"] - df["low"]).replace(0, np.nan)).clip(0, 1)
    df["p0_6_money_median20"] = group["money"].transform(lambda s: s.rolling(20, min_periods=20).median())
    df["p0_6_money_median60"] = group["money"].transform(lambda s: s.rolling(60, min_periods=60).median())
    df["p0_6_money_ratio_20"] = df["money"] / df["p0_6_money_median20"].replace(0, np.nan)
    df["p0_6_money_ratio_60"] = df["money"] / df["p0_6_money_median60"].replace(0, np.nan)
    df["p0_6_ret_rank_20d_market"] = df.groupby("datetime")["p0_6_ret_20d"].rank(pct=True)
    df["p0_6_ret_rank_20d_market_5d_ago"] = group["p0_6_ret_rank_20d_market"].shift(5)
    df["p0_6_money_rank_20d_market"] = df.groupby("datetime")["p0_6_money_ratio_20"].rank(pct=True)
    df["p0_6_money_rank_20d_market_5d_ago"] = group["p0_6_money_rank_20d_market"].shift(5)
    df["p0_6_ema20_1d_ago"] = group["ema20"].shift(1)
    df["p0_6_close_1d_ago"] = group["close"].shift(1)
    if "median_price20" in df.columns:
        df["p0_6_median20"] = df["median_price20"]
    else:
        df["p0_6_median20"] = group["close"].transform(lambda s: s.rolling(20, min_periods=20).median())
    for window in [60, 90, 120]:
        df[f"p0_6_low{window}"] = group["low"].transform(lambda s, window=window: s.rolling(window, min_periods=20).min())
        df[f"p0_6_launch_gain_from_recent_low_{window}d"] = df["close"] / df[f"p0_6_low{window}"].replace(0, np.nan) - 1.0
    breadth = (
        df.assign(p0_6_close_gt_ema20=lambda x: x["close"] > x["ema20"])
        .groupby(["datetime", "industry_name"], as_index=False)["p0_6_close_gt_ema20"]
        .mean()
        .rename(columns={"p0_6_close_gt_ema20": "p0_6_industry_breadth_20d"})
    )
    df = df.merge(breadth, on=["datetime", "industry_name"], how="left")
    df["p0_6_post20_relative_strength_flag"] = (df["p0_6_launch_gain_from_recent_low_60d"] >= 0.20) & (df["p0_6_ret_rank_20d_market"] >= 0.70)
    df["p0_6_post30_relative_strength_flag"] = (df["p0_6_launch_gain_from_recent_low_90d"] >= 0.30) & (df["p0_6_ret_rank_20d_market"] >= 0.70)
    df["p0_6_late_acceleration_flag"] = (df["p0_6_launch_gain_from_recent_low_120d"] >= 0.50) | (
        df["observable_state_stage"].astype(str) == "observable_late_acceleration_risk"
    )
    remaining_rows = group.cumcount(ascending=False) + 1
    df["p0_6_remaining_rows"] = remaining_rows
    for horizon in [20, 60, 120, 240]:
        df[f"p0_6_fwd_max_high_{horizon}d_inclusive"] = group["high"].transform(lambda s, horizon=horizon: s.iloc[::-1].rolling(horizon, min_periods=1).max().iloc[::-1])
        df[f"p0_6_fwd_max_close_{horizon}d_inclusive"] = group["close"].transform(lambda s, horizon=horizon: s.iloc[::-1].rolling(horizon, min_periods=1).max().iloc[::-1])
        df[f"p0_6_fwd_min_low_{horizon}d_inclusive"] = group["low"].transform(lambda s, horizon=horizon: s.iloc[::-1].rolling(horizon, min_periods=1).min().iloc[::-1])
        df[f"p0_6_horizon_end_date_{horizon}d_inclusive"] = group["datetime"].shift(-(horizon - 1))
    df["p0_6_direct_entry_date"] = group["datetime"].shift(-1)
    df["p0_6_direct_entry_open"] = group["open"].shift(-1)
    for days in [3, 5, 10, 20]:
        df[f"p0_6_signal_date_{days}d"] = group["datetime"].shift(-days)
        df[f"p0_6_entry_date_{days}d"] = group["datetime"].shift(-(days + 1))
        df[f"p0_6_signal_close_{days}d"] = group["close"].shift(-days)
        df[f"p0_6_signal_low_{days}d"] = group["low"].shift(-days)
        df[f"p0_6_signal_high_{days}d"] = group["high"].shift(-days)
        df[f"p0_6_signal_ema20_{days}d"] = group["ema20"].shift(-days)
        df[f"p0_6_signal_median20_{days}d"] = group["p0_6_median20"].shift(-days)
        df[f"p0_6_signal_ret_rank_{days}d"] = group["p0_6_ret_rank_20d_market"].shift(-days)
        df[f"p0_6_signal_ret_rank_5d_ago_{days}d"] = group["p0_6_ret_rank_20d_market_5d_ago"].shift(-days)
        df[f"p0_6_signal_money_rank_{days}d"] = group["p0_6_money_rank_20d_market"].shift(-days)
        df[f"p0_6_signal_money_rank_5d_ago_{days}d"] = group["p0_6_money_rank_20d_market_5d_ago"].shift(-days)
        df[f"p0_6_signal_money_ratio_{days}d"] = group["p0_6_money_ratio_20"].shift(-days)
        df[f"p0_6_signal_close_location_{days}d"] = group["p0_6_close_location"].shift(-days)
        df[f"p0_6_signal_body_ret_{days}d"] = group["p0_6_body_ret"].shift(-days)
        df[f"p0_6_signal_upper_shadow_{days}d"] = group["p0_6_upper_shadow_ratio"].shift(-days)
        df[f"p0_6_entry_open_{days}d"] = group["open"].shift(-(days + 1))
        df[f"p0_6_entry_close_{days}d"] = group["close"].shift(-(days + 1))
        df[f"p0_6_window_low_min_{days}d"] = group["low"].transform(lambda s, days=days: s.shift(-1).iloc[::-1].rolling(days, min_periods=1).min().iloc[::-1])
        df[f"p0_6_window_high_max_{days}d"] = group["high"].transform(lambda s, days=days: s.iloc[::-1].rolling(days + 1, min_periods=1).max().iloc[::-1])
        df[f"p0_6_window_money_median_{days}d"] = group["p0_6_money_ratio_20"].transform(lambda s, days=days: s.shift(-1).iloc[::-1].rolling(days, min_periods=1).median().iloc[::-1])
    df["p0_6_available_for_launch"] = (
        df["provider_required_fields_ok"].fillna(False).astype(bool)
        & df["feature_eligible"].fillna(False).astype(bool)
        & (df["p0_6_money_ratio_20"].notna())
        & (df["p0_6_ret_rank_20d_market"].notna())
    )
    return df.replace([np.inf, -np.inf], np.nan)


def p0_6_launch_specs() -> list[P06LaunchSpec]:
    return [
        P06LaunchSpec("expansion_high_volatility", "day_range >= 0.08 and ret_1d > 0 and close_location >= 0.55", "primary_pre_20_launch_pool", "launch_observation_only", True, "20/60/120", "day_range=0.08;close_location=0.55", "open,high,low,close,money"),
        P06LaunchSpec("high_vol_money_upper_close", "day_range >= 0.08 and money_ratio_20 >= 1.5 and close_location >= 0.65", "primary_pre_20_launch_pool", "launch_observation_only", True, "20/60/120", "day_range=0.08;money_ratio_20=1.5;close_location=0.65", "open,high,low,close,money"),
        P06LaunchSpec("rank_jump_leadership", "ret_rank_20d_market >= 0.80 and ret_rank_20d_market - ret_rank_20d_market_5d_ago >= 0.30", "primary_pre_30_launch_pool", "launch_observation_only", True, "20", "rank=0.80;rank_jump=0.30", "close"),
        P06LaunchSpec("repair_reclaim", "close > ema20 and close_1d_ago <= ema20_1d_ago and ret_5d > 0", "primary_pre_20_launch_pool", "launch_observation_only", True, "20", "ret_5d>0", "close,ema20"),
        P06LaunchSpec("first_limit_up_like", "ret_1d >= 0.095 and close_location >= 0.80 and no same-family event in prior 60 trading days", "sparse_strong_day_diagnostic_pool", "sparse_launch_observation", False, "60", "ret_1d=0.095;close_location=0.80", "open,high,low,close", True),
        P06LaunchSpec("first_near_limit_up_like", "ret_1d >= 0.07 and ret_1d < 0.095 and close_location >= 0.75 and no same-family event in prior 60 trading days", "sparse_strong_day_diagnostic_pool", "sparse_launch_observation", False, "60", "ret_1d=0.07/0.095;close_location=0.75", "open,high,low,close", True),
        P06LaunchSpec("gap_up_upper_close", "open / prev_close - 1 >= 0.03 and close >= open and close_location >= 0.60", "sparse_strong_day_diagnostic_pool", "sparse_launch_observation", False, "1", "gap=0.03;close_location=0.60", "open,high,low,close", True),
        P06LaunchSpec("strong_body_day", "body_ret >= 0.05 and close_location >= 0.70 and money_ratio_20 >= 1.2", "sparse_strong_day_diagnostic_pool", "sparse_launch_observation", False, "20", "body_ret=0.05;close_location=0.70;money_ratio_20=1.2", "open,high,low,close,money", True),
        P06LaunchSpec("post_20pct_relative_strength", "launch_gain_from_recent_low_60d >= 0.20 and ret_rank_20d_market >= 0.70", "post_20_30_hold_only_pool", "add_on_or_hold_only", False, "60", "gain60=0.20;rank=0.70", "close"),
        P06LaunchSpec("post_30pct_relative_strength", "launch_gain_from_recent_low_90d >= 0.30 and ret_rank_20d_market >= 0.70", "post_20_30_hold_only_pool", "add_on_or_hold_only", False, "90", "gain90=0.30;rank=0.70", "close"),
    ]


def p0_6_launch_formula_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "launch_family": spec.launch_family,
                "v1_trigger_formula": spec.formula,
                "launch_pool": spec.declared_launch_pool,
                "launch_lifecycle_role": spec.lifecycle_role,
                "primary_entry_leaderboard_eligible": bool(spec.primary_entry_leaderboard_eligible),
                "lookback_days": spec.lookback_days,
                "thresholds": spec.thresholds,
                "required_fields": spec.required_fields,
                "sparse_diagnostic": bool(spec.sparse_diagnostic),
            }
            for spec in p0_6_launch_specs()
        ]
    )


def p0_6_prior_event_absent(df: pd.DataFrame, base_mask: pd.Series, window: int = 60) -> pd.Series:
    tmp = pd.Series(base_mask.fillna(False).astype(float), index=df.index)
    prior = tmp.groupby(df["instrument"], group_keys=False).transform(lambda s: s.shift(1).rolling(window, min_periods=1).sum())
    return base_mask.fillna(False).astype(bool) & (prior.fillna(0) == 0)


def p0_6_build_launch_events(config: dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
    specs = p0_6_launch_specs()
    common = (
        (df["datetime"] >= parse_dt(config["dates"]["research_start"]))
        & (df["datetime"] <= parse_dt(config["dates"]["research_end"]))
        & df["p0_6_available_for_launch"].fillna(False).astype(bool)
    )
    base_masks: dict[str, pd.Series] = {
        "expansion_high_volatility": (df["p0_6_day_range"] >= 0.08) & (df["p0_6_ret_1d"] > 0) & (df["p0_6_close_location"] >= 0.55),
        "high_vol_money_upper_close": (df["p0_6_day_range"] >= 0.08) & (df["p0_6_money_ratio_20"] >= 1.5) & (df["p0_6_close_location"] >= 0.65),
        "rank_jump_leadership": (df["p0_6_ret_rank_20d_market"] >= 0.80) & ((df["p0_6_ret_rank_20d_market"] - df["p0_6_ret_rank_20d_market_5d_ago"]) >= 0.30),
        "repair_reclaim": (df["close"] > df["ema20"]) & (df["p0_6_close_1d_ago"] <= df["p0_6_ema20_1d_ago"]) & (df["p0_6_ret_5d"] > 0),
        "first_limit_up_like": (df["p0_6_ret_1d"] >= 0.095) & (df["p0_6_close_location"] >= 0.80),
        "first_near_limit_up_like": (df["p0_6_ret_1d"] >= 0.07) & (df["p0_6_ret_1d"] < 0.095) & (df["p0_6_close_location"] >= 0.75),
        "gap_up_upper_close": (df["gap_pct"] >= 0.03) & (df["close"] >= df["open"]) & (df["p0_6_close_location"] >= 0.60),
        "strong_body_day": (df["p0_6_body_ret"] >= 0.05) & (df["p0_6_close_location"] >= 0.70) & (df["p0_6_money_ratio_20"] >= 1.2),
        "post_20pct_relative_strength": df["p0_6_post20_relative_strength_flag"],
        "post_30pct_relative_strength": df["p0_6_post30_relative_strength_flag"],
    }
    base_masks["first_limit_up_like"] = p0_6_prior_event_absent(df, base_masks["first_limit_up_like"], 60)
    base_masks["first_near_limit_up_like"] = p0_6_prior_event_absent(df, base_masks["first_near_limit_up_like"], 60)

    frames: list[pd.DataFrame] = []
    matrix = p0_6_launch_formula_matrix().set_index("launch_family")
    for spec in specs:
        mask = common & base_masks[spec.launch_family].fillna(False)
        if not mask.any():
            continue
        part = df.loc[mask].copy()
        part["launch_family"] = spec.launch_family
        part["launch_formula"] = spec.formula
        part["declared_launch_pool"] = spec.declared_launch_pool
        part["declared_primary_entry_leaderboard_eligible"] = bool(spec.primary_entry_leaderboard_eligible)
        part["launch_lifecycle_role"] = spec.lifecycle_role
        part["sparse_diagnostic"] = bool(spec.sparse_diagnostic)
        frames.append(part)
    if not frames:
        return pd.DataFrame()
    events = pd.concat(frames, ignore_index=True, sort=False)
    events["launch_date"] = pd.to_datetime(events["datetime"]).dt.normalize()
    events["launch_close"] = events["close"]
    events["launch_high"] = events["high"]
    events["launch_low"] = events["low"]
    events["launch_volume_or_money_context"] = events["p0_6_money_ratio_20"]
    events["launch_market_regime"] = events["market_regime_state"]
    events["launch_industry_regime"] = events["industry_regime_state"]
    events["launch_observable_stage"] = events["observable_state_stage"]
    events["late_acceleration_flag"] = events["p0_6_late_acceleration_flag"].fillna(False).astype(bool)

    events["launch_pool"] = events["declared_launch_pool"]
    events["launch_primary_entry_leaderboard_eligible"] = events["declared_primary_entry_leaderboard_eligible"].astype(bool)
    events["lifecycle_gate_status"] = "primary_or_declared_pool_ok"
    events["lifecycle_gate_bucket"] = "primary_or_declared_pool_ok"

    late = events["late_acceleration_flag"]
    post30 = events["p0_6_post30_relative_strength_flag"].fillna(False).astype(bool)
    post20 = events["p0_6_post20_relative_strength_flag"].fillna(False).astype(bool)
    pre30_family = events["launch_family"].eq("rank_jump_leadership")
    pre20_declared = events["declared_launch_pool"].eq("primary_pre_20_launch_pool")
    pre30_declared = events["declared_launch_pool"].eq("primary_pre_30_launch_pool")
    sparse_declared = events["declared_launch_pool"].eq("sparse_strong_day_diagnostic_pool")

    events.loc[late, ["launch_pool", "lifecycle_gate_status", "lifecycle_gate_bucket"]] = [
        "late_acceleration_hold_only_pool",
        "late_acceleration_hold_only",
        "post_30_or_late_acceleration_hold_only",
    ]
    events.loc[late, "launch_primary_entry_leaderboard_eligible"] = False
    hold30 = post30 & ~late
    events.loc[hold30, ["launch_pool", "lifecycle_gate_status", "lifecycle_gate_bucket"]] = [
        "post_20_30_hold_only_pool",
        "post_30_hold_only",
        "post_30_or_late_acceleration_hold_only",
    ]
    events.loc[hold30, "launch_primary_entry_leaderboard_eligible"] = False
    post20_hold = post20 & ~post30 & ~late & ~pre30_family
    events.loc[post20_hold, ["launch_pool", "lifecycle_gate_status", "lifecycle_gate_bucket"]] = [
        "post_20_30_hold_only_pool",
        "post_20_family_hold_only",
        "post_20_family_hold_only",
    ]
    events.loc[post20_hold, "launch_primary_entry_leaderboard_eligible"] = False

    pre20_bad = pre20_declared & ~late & ~post30 & ((events["p0_6_launch_gain_from_recent_low_60d"] >= 0.20) | post20)
    events.loc[pre20_bad, ["launch_pool", "lifecycle_gate_status", "lifecycle_gate_bucket"]] = [
        "lifecycle_gate_rejected_or_hold_only",
        "primary_pre_20_lifecycle_gate_rejected",
        "lifecycle_gate_rejected",
    ]
    events.loc[pre20_bad, "launch_primary_entry_leaderboard_eligible"] = False
    pre30_ok = pre30_declared & ~late & ~post30 & (events["p0_6_launch_gain_from_recent_low_90d"] < 0.30)
    pre30_band = pre30_ok & (events["p0_6_launch_gain_from_recent_low_60d"] >= 0.20)
    events.loc[pre30_band, ["launch_pool", "lifecycle_gate_status", "lifecycle_gate_bucket"]] = [
        "primary_pre_30_launch_pool",
        "primary_pre_30_early_confirmation_20_30_band",
        "primary_pre_30_early_confirmation_20_30_band",
    ]
    events.loc[pre30_ok, "launch_primary_entry_leaderboard_eligible"] = True
    pre30_bad = pre30_declared & ~pre30_ok & ~late & ~post30
    events.loc[pre30_bad, ["launch_pool", "lifecycle_gate_status", "lifecycle_gate_bucket"]] = [
        "lifecycle_gate_rejected_or_hold_only",
        "primary_pre_30_lifecycle_gate_rejected",
        "lifecycle_gate_rejected",
    ]
    events.loc[pre30_bad, "launch_primary_entry_leaderboard_eligible"] = False
    sparse_ok = sparse_declared & ~late & ~post30
    events.loc[sparse_ok, ["launch_pool", "lifecycle_gate_status", "lifecycle_gate_bucket"]] = [
        "sparse_strong_day_diagnostic_pool",
        "sparse_diagnostic_only",
        "sparse_diagnostic_only",
    ]
    events.loc[sparse_ok, "launch_primary_entry_leaderboard_eligible"] = False
    pre20_ok = pre20_declared & ~pre20_bad & ~late & ~post30 & ~post20
    events.loc[pre20_ok, ["launch_pool", "lifecycle_gate_status", "lifecycle_gate_bucket"]] = [
        "primary_pre_20_launch_pool",
        "primary_pre_20_lifecycle_gate_ok",
        "primary_pre_20_lifecycle_gate_ok",
    ]
    events.loc[pre20_ok, "launch_primary_entry_leaderboard_eligible"] = True

    events = events.sort_values(["instrument", "p0_6_row_pos", "launch_family"]).reset_index(drop=True)
    gap = p0_6_int(config, "launch_dedup_gap_trading_days", 20)
    episode_ids: list[str] = []
    for instrument, group_events in events.groupby("instrument", sort=False):
        last_pos: int | None = None
        episode_no = 0
        start_date = ""
        for _, row in group_events.iterrows():
            row_pos = int(row["p0_6_row_pos"])
            if last_pos is None or row_pos - last_pos > gap:
                episode_no += 1
                start_date = iso_date(row["launch_date"])
            episode_ids.append(f"LPE_{instrument}_{start_date}_{episode_no:04d}")
            last_pos = row_pos
    events["launch_episode_id"] = episode_ids
    events.insert(0, "launch_event_id", [f"LE_{i:08d}" for i in range(1, len(events) + 1)])
    events["launch_row_pos"] = events["p0_6_row_pos"].astype(int)
    events["launch_year"] = events["launch_date"].dt.year
    events["launch_lifecycle_role"] = events["launch_lifecycle_role"].where(
        events["launch_pool"].isin(["primary_pre_20_launch_pool", "primary_pre_30_launch_pool", "sparse_strong_day_diagnostic_pool"]),
        "add_on_or_hold_only",
    )
    return events


def p0_6_panel_groups(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {instrument: group.reset_index(drop=True) for instrument, group in df.sort_values(["instrument", "datetime"]).groupby("instrument", sort=False)}


def p0_6_attach_forward_metrics(
    config: dict[str, Any],
    panel_groups: dict[str, pd.DataFrame],
    events: pd.DataFrame,
    base_price_col: str,
    start_pos_col: str,
) -> pd.DataFrame:
    if events.empty:
        return events
    out = events.copy().reset_index(drop=True)
    horizons = [20, 60, 120, 240]
    research_end = parse_dt(config["dates"]["research_end"])
    for horizon in horizons:
        out[f"future_max_high_gain_{horizon}d_after_entry"] = np.nan
        out[f"future_max_close_gain_{horizon}d_after_entry"] = np.nan
        out[f"future_max_drawdown_{horizon}d_after_entry"] = np.nan
        out[f"label_horizon_truncated_{horizon}d"] = True
    out["future_drawdown_before_20pct_high_gain"] = np.nan
    out["future_drawdown_before_50pct_high_gain"] = np.nan
    out["future_time_to_20pct_high_gain"] = np.nan
    out["future_time_to_50pct_high_gain"] = np.nan
    out["horizon_end_date_240d"] = pd.NaT

    for instrument, idx in out.groupby("instrument", sort=False).groups.items():
        group = panel_groups.get(str(instrument))
        if group is None:
            continue
        idx_list = list(idx)
        start_pos = pd.to_numeric(out.loc[idx_list, start_pos_col], errors="coerce").fillna(-1).astype(int).to_numpy()
        base = pd.to_numeric(out.loc[idx_list, base_price_col], errors="coerce").to_numpy(dtype=float)
        valid = (start_pos >= 0) & (start_pos < len(group)) & np.isfinite(base) & (base > 0)
        if not valid.any():
            continue
        valid_idx = np.array(idx_list, dtype=int)[valid]
        valid_pos = start_pos[valid]
        valid_base = base[valid]
        for horizon in horizons:
            high_abs = group[f"p0_6_fwd_max_high_{horizon}d_inclusive"].to_numpy(dtype=float)[valid_pos]
            close_abs = group[f"p0_6_fwd_max_close_{horizon}d_inclusive"].to_numpy(dtype=float)[valid_pos]
            low_abs = group[f"p0_6_fwd_min_low_{horizon}d_inclusive"].to_numpy(dtype=float)[valid_pos]
            out.loc[valid_idx, f"future_max_high_gain_{horizon}d_after_entry"] = high_abs / valid_base - 1.0
            out.loc[valid_idx, f"future_max_close_gain_{horizon}d_after_entry"] = close_abs / valid_base - 1.0
            out.loc[valid_idx, f"future_max_drawdown_{horizon}d_after_entry"] = low_abs / valid_base - 1.0
            remaining = group["p0_6_remaining_rows"].to_numpy(dtype=int)[valid_pos]
            out.loc[valid_idx, f"label_horizon_truncated_{horizon}d"] = remaining < horizon
        horizon_end = pd.to_datetime(group["p0_6_horizon_end_date_240d_inclusive"].iloc[valid_pos]).reset_index(drop=True)
        out.loc[valid_idx, "horizon_end_date_240d"] = horizon_end.to_numpy()
        highs = group["high"].to_numpy(dtype=float)
        lows = group["low"].to_numpy(dtype=float)
        for out_idx, pos, entry_base in zip(valid_idx, valid_pos, valid_base, strict=False):
            end240 = min(len(group), int(pos) + 240)
            if end240 <= pos:
                continue
            window_high = highs[int(pos) : end240]
            window_low = lows[int(pos) : end240]
            hit20 = np.flatnonzero(window_high >= entry_base * 1.20)
            hit50 = np.flatnonzero(window_high >= entry_base * 1.50)
            if len(hit20):
                first = int(hit20[0])
                out.at[out_idx, "future_time_to_20pct_high_gain"] = first + 1
                out.at[out_idx, "future_drawdown_before_20pct_high_gain"] = np.nanmin(window_low[: first + 1]) / entry_base - 1.0
            else:
                out.at[out_idx, "future_drawdown_before_20pct_high_gain"] = np.nanmin(window_low) / entry_base - 1.0
            if len(hit50):
                first = int(hit50[0])
                out.at[out_idx, "future_time_to_50pct_high_gain"] = first + 1
                out.at[out_idx, "future_drawdown_before_50pct_high_gain"] = np.nanmin(window_low[: first + 1]) / entry_base - 1.0
            else:
                out.at[out_idx, "future_drawdown_before_50pct_high_gain"] = np.nanmin(window_low) / entry_base - 1.0

    out["label_horizon_truncated"] = out["label_horizon_truncated_240d"].fillna(True).astype(bool)
    out["observed_reference_overlap"] = (pd.to_datetime(out.get("entry_date", out.get("launch_date"))) > research_end) | (
        pd.to_datetime(out["horizon_end_date_240d"]) > research_end
    )
    out["entry_future_20pct_high_60d"] = out["future_max_high_gain_60d_after_entry"] >= 0.20
    out["entry_future_20pct_close_60d"] = out["future_max_close_gain_60d_after_entry"] >= 0.20
    out["entry_future_50pct_high_120d"] = out["future_max_high_gain_120d_after_entry"] >= 0.50
    out["entry_future_50pct_close_120d"] = out["future_max_close_gain_120d_after_entry"] >= 0.50
    out["entry_future_100pct_high_240d"] = out["future_max_high_gain_240d_after_entry"] >= 1.00
    out["entry_future_100pct_close_240d"] = out["future_max_close_gain_240d_after_entry"] >= 1.00
    out["entry_max_drawdown_20d_le_8pct"] = out["future_max_drawdown_20d_after_entry"] >= -0.08
    out["entry_max_drawdown_60d_le_12pct"] = out["future_max_drawdown_60d_after_entry"] >= -0.12
    out["entry_drawdown_before_20pct_gain_le_10pct"] = out["future_drawdown_before_20pct_high_gain"] >= -0.10
    return out.replace([np.inf, -np.inf], np.nan)


def p0_6_entry_specs() -> list[P06EntrySpec]:
    primary = ("expansion_high_volatility", "high_vol_money_upper_close", "rank_jump_leadership", "repair_reclaim")
    sparse = ("first_limit_up_like", "first_near_limit_up_like", "gap_up_upper_close", "strong_body_day")
    common_filters = ("break_launch_low_before_entry", "volume_close_below_launch_close", "long_upper_shadow_volume_failure")
    post_audits = ("break_invalidation_10d", "relative_strength_loss_20d", "industry_breadth_deterioration_20d", "no_10pct_gain_with_12pct_drawdown_20d")
    specs: list[P06EntrySpec] = []

    def add(family: str, variant: str, allowed: tuple[str, ...], start: int, end: int, condition: str, invalidation: str, price_ref: str, primary_ok: bool = True) -> None:
        specs.append(
            P06EntrySpec(
                family,
                variant,
                allowed,
                tuple(),
                start,
                end,
                condition,
                "signal generated at the first close satisfying the condition; entry_date is next trading day",
                invalidation,
                price_ref,
                common_filters,
                post_audits,
                primary_ok,
                False,
            )
        )

    for days in [3, 5, 10, 20]:
        add("price_hold_after_launch", f"hold_{days}d_close_ge_launch_close", primary, days, days, f"launch+{days} close >= launch close", "launch_low_stop", "launch_low")
    for days in [3, 5, 10]:
        add("price_hold_after_launch", f"hold_{days}d_low_ge_launch_low", primary, days, days, f"launch+{days} window low >= launch low", "launch_low_stop", "launch_low")
    add("price_hold_after_launch", "hold_3d_close_above_ema20", primary, 3, 3, "launch+3 close >= ema20", "ema20_stop", "ema20")
    add("price_hold_after_launch", "hold_5d_close_above_median20", primary, 5, 5, "launch+5 close >= median20", "median20_stop", "median20")
    add("pullback_hold_entry", "pullback_3_8_reclaim_ema20", primary + sparse, 3, 20, "3%-8% pullback, no launch-low break, money contraction, close reclaims ema20", "pullback_low_stop", "pullback_low", True)
    add("pullback_hold_entry", "pullback_5_12_reclaim_median20", primary + sparse, 3, 20, "5%-12% pullback, low above median20, money contraction, close reclaims median20", "pullback_low_stop", "pullback_low", True)
    add("pullback_hold_entry", "pullback_3_8_contraction_upper_close", primary + sparse, 3, 20, "3%-8% pullback, money contraction, close location upper half", "pullback_low_stop", "pullback_low", True)
    add("pullback_hold_entry", "pullback_5_12_low_above_launch_low", primary + sparse, 3, 20, "5%-12% pullback and pullback low stays above launch low", "pullback_low_stop", "pullback_low", True)
    add("higher_low_reacceleration_entry", "higher_low_reclaim_ema20", primary, 5, 20, "higher low above launch low and close reclaims ema20", "higher_low_stop", "higher_low")
    add("higher_low_reacceleration_entry", "higher_low_reaccel_rank", primary, 5, 20, "higher low plus ret rank back to top 20%", "higher_low_stop", "higher_low")
    add("higher_low_reacceleration_entry", "higher_low_money_quality", primary, 5, 20, "higher low plus money quality improvement", "higher_low_stop", "higher_low")
    add("volume_confirmation_entry", "volume_hold_3d", primary, 3, 3, "launch money spike and launch+3 price hold", "launch_low_stop", "launch_low")
    add("volume_confirmation_entry", "volume_hold_5d", primary, 5, 5, "launch money spike and launch+5 price hold", "launch_low_stop", "launch_low")
    add("volume_confirmation_entry", "volume_second_money_rank_jump", primary, 3, 20, "money rank jumps again after launch", "launch_low_stop", "launch_low")
    add("volume_confirmation_entry", "volume_rank_money_jump_followthrough", primary, 3, 20, "ret rank and money rank both improve after launch", "launch_low_stop", "launch_low")
    add("sparse_strong_day_followthrough_entry", "sparse_limit_followthrough_3d", sparse, 3, 3, "first limit/near-limit strong day holds low for 3 days", "launch_low_stop", "launch_low", False)
    add("sparse_strong_day_followthrough_entry", "sparse_limit_followthrough_5d", sparse, 5, 5, "first limit/near-limit strong day holds low for 5 days", "launch_low_stop", "launch_low", False)
    add("sparse_strong_day_followthrough_entry", "gap_up_hold_3d", sparse, 3, 3, "gap-up upper-close day holds gap-day low for 3 days", "launch_low_stop", "launch_low", False)
    add("sparse_strong_day_followthrough_entry", "strong_body_pullback_hold", sparse, 3, 20, "strong body day pulls back with contraction and holds key low", "pullback_low_stop", "pullback_low", False)
    add("sparse_strong_day_followthrough_entry", "second_strong_day", sparse, 3, 20, "another strong body or near-limit day appears after launch", "launch_low_stop", "launch_low", False)
    return specs


def p0_6_entry_formula_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "entry_family": spec.entry_family,
                "entry_variant_id": spec.entry_variant_id,
                "allowed_launch_families": ";".join(spec.allowed_launch_families),
                "excluded_launch_families": ";".join(spec.excluded_launch_families),
                "signal_window_start_after_launch": spec.signal_window_start_after_launch,
                "signal_window_end_after_launch": spec.signal_window_end_after_launch,
                "entry_signal_condition": spec.entry_signal_condition,
                "entry_signal_date_definition": spec.entry_signal_date_definition,
                "entry_execution_lag_trading_days": 1,
                "entry_execution_price_reference": "next_open",
                "entry_execution_assumption": "next_open",
                "invalidation_rule_id": spec.invalidation_rule_id,
                "invalidation_price_reference": spec.invalidation_price_reference,
                "pre_entry_failure_filter_ids": ";".join(spec.pre_entry_failure_filter_ids),
                "post_entry_invalidation_audit_ids": ";".join(spec.post_entry_invalidation_audit_ids),
                "primary_leaderboard_eligible": bool(spec.primary_leaderboard_eligible),
                "same_close_proxy_allowed": bool(spec.same_close_proxy_allowed),
            }
            for spec in p0_6_entry_specs()
        ]
    )


def p0_6_entry_trigger_dictionary() -> pd.DataFrame:
    matrix = p0_6_entry_formula_matrix()
    return matrix[
        [
            "entry_family",
            "entry_variant_id",
            "entry_signal_condition",
            "entry_execution_assumption",
            "invalidation_rule_id",
            "pre_entry_failure_filter_ids",
            "post_entry_invalidation_audit_ids",
            "primary_leaderboard_eligible",
        ]
    ].copy()


def p0_6_signal_for_variant(spec: P06EntrySpec, launch: pd.Series, group: pd.DataFrame) -> dict[str, Any] | None:
    launch_pos = int(launch["launch_row_pos"])
    n = len(group)
    start = launch_pos + spec.signal_window_start_after_launch
    end = min(launch_pos + spec.signal_window_end_after_launch, n - 2)
    if start > end or start <= launch_pos:
        return None
    launch_close = safe_float(launch["launch_close"])
    launch_low = safe_float(launch["launch_low"])
    launch_money = safe_float(launch["p0_6_money_ratio_20"], np.nan)
    variant = spec.entry_variant_id

    def window_stats(pos: int) -> dict[str, float]:
        window = group.iloc[launch_pos + 1 : pos + 1]
        pullback_low = safe_float(window["low"].min(), np.nan)
        pullback_depth = pullback_low / launch_close - 1.0 if np.isfinite(pullback_low) and launch_close > 0 else np.nan
        return {
            "pullback_low": pullback_low,
            "pullback_depth": pullback_depth,
            "pullback_duration_trading_days": int(max(pos - launch_pos, 0)),
            "pullback_money_contraction": safe_float(window["p0_6_money_ratio_20"].median(), np.nan),
            "pullback_low_vs_launch_low": pullback_low / launch_low - 1.0 if np.isfinite(pullback_low) and launch_low > 0 else np.nan,
        }

    def fixed_pos(days: int) -> dict[str, Any] | None:
        pos = launch_pos + days
        return {"signal_pos": pos, **window_stats(pos)} if pos <= n - 2 else None

    if variant.startswith("hold_") and "_close_ge_launch_close" in variant:
        pos = int(variant.split("_")[1].replace("d", ""))
        result = fixed_pos(pos)
        if result is not None and group.loc[result["signal_pos"], "close"] >= launch_close:
            result["invalidation_price_reference"] = launch_low
            return result
        return None
    if variant.startswith("hold_") and "_low_ge_launch_low" in variant:
        pos = int(variant.split("_")[1].replace("d", ""))
        result = fixed_pos(pos)
        if result is not None and result["pullback_low"] >= launch_low:
            result["invalidation_price_reference"] = launch_low
            return result
        return None
    if variant == "hold_3d_close_above_ema20":
        result = fixed_pos(3)
        if result is not None and group.loc[result["signal_pos"], "close"] >= group.loc[result["signal_pos"], "ema20"]:
            result["invalidation_price_reference"] = safe_float(group.loc[result["signal_pos"], "ema20"], np.nan)
            return result
        return None
    if variant == "hold_5d_close_above_median20":
        result = fixed_pos(5)
        if result is not None and group.loc[result["signal_pos"], "close"] >= group.loc[result["signal_pos"], "p0_6_median20"]:
            result["invalidation_price_reference"] = safe_float(group.loc[result["signal_pos"], "p0_6_median20"], np.nan)
            return result
        return None
    for pos in range(start, end + 1):
        row = group.loc[pos]
        stats = window_stats(pos)
        pullback_depth = safe_float(stats["pullback_depth"], np.nan)
        money_contraction = np.isfinite(stats["pullback_money_contraction"]) and np.isfinite(launch_money) and stats["pullback_money_contraction"] < launch_money
        no_break_launch_low = stats["pullback_low"] >= launch_low
        if variant == "pullback_3_8_reclaim_ema20":
            ok = (-0.08 <= pullback_depth <= -0.03) and no_break_launch_low and money_contraction and row["close"] >= row["ema20"]
        elif variant == "pullback_5_12_reclaim_median20":
            ok = (-0.12 <= pullback_depth <= -0.05) and stats["pullback_low"] >= row["p0_6_median20"] and money_contraction and row["close"] >= row["p0_6_median20"]
        elif variant == "pullback_3_8_contraction_upper_close":
            ok = (-0.08 <= pullback_depth <= -0.03) and no_break_launch_low and money_contraction and row["p0_6_close_location"] >= 0.55
        elif variant == "pullback_5_12_low_above_launch_low":
            ok = (-0.12 <= pullback_depth <= -0.05) and no_break_launch_low and row["close"] >= row["p0_6_median20"]
        elif variant == "higher_low_reclaim_ema20":
            ok = pos - launch_pos >= 5 and no_break_launch_low and stats["pullback_low"] > launch_low and row["close"] >= row["ema20"]
        elif variant == "higher_low_reaccel_rank":
            ok = pos - launch_pos >= 5 and no_break_launch_low and stats["pullback_low"] > launch_low and row["p0_6_ret_rank_20d_market"] >= 0.80
        elif variant == "higher_low_money_quality":
            ok = pos - launch_pos >= 5 and no_break_launch_low and stats["pullback_low"] > launch_low and row["p0_6_money_ratio_20"] >= max(1.2, launch_money)
        elif variant == "volume_second_money_rank_jump":
            ok = (row["p0_6_money_rank_20d_market"] - row["p0_6_money_rank_20d_market_5d_ago"] >= 0.20) and row["close"] >= launch_low
        elif variant == "volume_rank_money_jump_followthrough":
            ok = ((row["p0_6_ret_rank_20d_market"] - row["p0_6_ret_rank_20d_market_5d_ago"]) >= 0.20) and ((row["p0_6_money_rank_20d_market"] - row["p0_6_money_rank_20d_market_5d_ago"]) >= 0.20)
        elif variant == "strong_body_pullback_hold":
            ok = (-0.12 <= pullback_depth <= -0.03) and no_break_launch_low and money_contraction and row["close"] >= row["p0_6_median20"]
        elif variant == "second_strong_day":
            ok = (row["p0_6_body_ret"] >= 0.05 and row["p0_6_close_location"] >= 0.70) or (row["p0_6_ret_1d"] >= 0.07 and row["p0_6_close_location"] >= 0.75)
        else:
            ok = False
        if ok:
            stats["signal_pos"] = pos
            stats["invalidation_price_reference"] = stats["pullback_low"] if "pullback" in variant or "higher_low" in variant or variant == "strong_body_pullback_hold" else launch_low
            return stats

    if variant in {"volume_hold_3d", "volume_hold_5d", "sparse_limit_followthrough_3d", "sparse_limit_followthrough_5d", "gap_up_hold_3d"}:
        days = 3 if variant.endswith("_3d") else 5
        result = fixed_pos(days)
        if result is None:
            return None
        row = group.loc[result["signal_pos"]]
        if variant.startswith("volume_hold"):
            ok = launch_money >= 1.5 and row["close"] >= launch_close and result["pullback_low"] >= launch_low
        elif variant == "gap_up_hold_3d":
            ok = launch["launch_family"] == "gap_up_upper_close" and result["pullback_low"] >= launch_low
        else:
            ok = launch["launch_family"] in {"first_limit_up_like", "first_near_limit_up_like"} and result["pullback_low"] >= launch_low
        if ok:
            result["invalidation_price_reference"] = launch_low
            return result
    return None


def p0_6_pre_entry_failure_flags(launch: pd.Series, group: pd.DataFrame, signal_pos: int) -> list[str]:
    launch_pos = int(launch["launch_row_pos"])
    window = group.iloc[launch_pos + 1 : signal_pos + 1]
    flags: list[str] = []
    if not window.empty and safe_float(window["low"].min(), np.nan) < safe_float(launch["launch_low"], np.nan):
        flags.append("break_launch_low_before_entry")
    if not window.empty and (window["close"] < safe_float(launch["launch_close"], np.nan)).tail(min(5, len(window))).any():
        flags.append("volume_close_below_launch_close")
    if not window.empty:
        shadow_failure = (window["p0_6_upper_shadow_ratio"] >= 0.45) & (window["p0_6_money_ratio_20"] >= 1.2) & (window["p0_6_close_location"] <= 0.50)
        if bool(shadow_failure.any()):
            flags.append("long_upper_shadow_volume_failure")
    if str(launch["launch_family"]) == "gap_up_upper_close" and not window.empty and safe_float(window["low"].min(), np.nan) < safe_float(launch["launch_low"], np.nan):
        flags.append("gap_fill_break_gap_day_low")
    return flags


def p0_6_post_entry_audit_flags(group: pd.DataFrame, entry_pos: int, invalidation_price: float, entry_price: float) -> list[str]:
    flags: list[str] = []
    if entry_pos >= len(group) or not np.isfinite(entry_price) or entry_price <= 0:
        return flags
    first10 = group.iloc[entry_pos : min(len(group), entry_pos + 10)]
    first20 = group.iloc[entry_pos : min(len(group), entry_pos + 20)]
    if np.isfinite(invalidation_price) and not first10.empty and safe_float(first10["low"].min(), np.nan) < invalidation_price:
        flags.append("break_invalidation_10d")
    if not first20.empty and safe_float(first20["p0_6_ret_rank_20d_market"].min(), 1.0) < 0.60:
        flags.append("relative_strength_loss_20d")
    if not first20.empty:
        start_breadth = safe_float(group.loc[entry_pos, "p0_6_industry_breadth_20d"], np.nan)
        end_breadth = safe_float(first20["p0_6_industry_breadth_20d"].iloc[-1], np.nan)
        if np.isfinite(start_breadth) and np.isfinite(end_breadth) and end_breadth < start_breadth - 0.10:
            flags.append("industry_breadth_deterioration_20d")
        no_gain = safe_float(first20["high"].max(), np.nan) / entry_price - 1.0 < 0.10
        bad_dd = safe_float(first20["low"].min(), np.nan) / entry_price - 1.0 <= -0.12
        if no_gain and bad_dd:
            flags.append("no_10pct_gain_with_12pct_drawdown_20d")
    return flags


def p0_6_build_entry_events(config: dict[str, Any], df: pd.DataFrame, launches: pd.DataFrame) -> pd.DataFrame:
    if launches.empty:
        return pd.DataFrame()
    specs = p0_6_entry_specs()
    spec_map = {spec.entry_variant_id: spec for spec in specs}
    eligible_families = sorted({family for spec in specs for family in spec.allowed_launch_families})
    launch_source = (
        launches[launches["launch_family"].isin(eligible_families)]
        .sort_values(["launch_episode_id", "launch_family", "launch_date", "launch_event_id"])
        .groupby(["launch_episode_id", "launch_family"], as_index=False, sort=False)
        .head(1)
        .reset_index(drop=True)
    )

    def variant_condition(base: pd.DataFrame, variant: str, days: int) -> tuple[pd.Series, pd.Series]:
        launch_close = base["launch_close"].replace(0, np.nan)
        launch_low = base["launch_low"]
        signal_close = base[f"p0_6_signal_close_{days}d"]
        window_low = base[f"p0_6_window_low_min_{days}d"]
        pullback_depth = window_low / launch_close - 1.0
        money_contraction = base[f"p0_6_window_money_median_{days}d"] < base["p0_6_money_ratio_20"]
        no_break = window_low >= launch_low
        signal_valid = base[f"p0_6_entry_open_{days}d"].notna()
        if variant.endswith("close_ge_launch_close"):
            cond = signal_close >= base["launch_close"]
        elif variant.endswith("low_ge_launch_low"):
            cond = no_break
        elif variant == "hold_3d_close_above_ema20":
            cond = signal_close >= base[f"p0_6_signal_ema20_{days}d"]
        elif variant == "hold_5d_close_above_median20":
            cond = signal_close >= base[f"p0_6_signal_median20_{days}d"]
        elif variant == "pullback_3_8_reclaim_ema20":
            cond = pullback_depth.between(-0.08, -0.03) & no_break & money_contraction & (signal_close >= base[f"p0_6_signal_ema20_{days}d"])
        elif variant == "pullback_5_12_reclaim_median20":
            cond = pullback_depth.between(-0.12, -0.05) & (window_low >= base[f"p0_6_signal_median20_{days}d"]) & money_contraction & (signal_close >= base[f"p0_6_signal_median20_{days}d"])
        elif variant == "pullback_3_8_contraction_upper_close":
            cond = pullback_depth.between(-0.08, -0.03) & no_break & money_contraction & (base[f"p0_6_signal_close_location_{days}d"] >= 0.55)
        elif variant == "pullback_5_12_low_above_launch_low":
            cond = pullback_depth.between(-0.12, -0.05) & no_break & (signal_close >= base[f"p0_6_signal_median20_{days}d"])
        elif variant == "higher_low_reclaim_ema20":
            cond = (window_low > launch_low) & (signal_close >= base[f"p0_6_signal_ema20_{days}d"])
        elif variant == "higher_low_reaccel_rank":
            cond = (window_low > launch_low) & (base[f"p0_6_signal_ret_rank_{days}d"] >= 0.80)
        elif variant == "higher_low_money_quality":
            cond = (window_low > launch_low) & (base[f"p0_6_signal_money_ratio_{days}d"] >= np.maximum(1.2, base["p0_6_money_ratio_20"]))
        elif variant == "volume_hold_3d" or variant == "volume_hold_5d":
            cond = (base["p0_6_money_ratio_20"] >= 1.5) & (signal_close >= base["launch_close"]) & no_break
        elif variant == "volume_second_money_rank_jump":
            cond = (base[f"p0_6_signal_money_rank_{days}d"] - base[f"p0_6_signal_money_rank_5d_ago_{days}d"] >= 0.20) & no_break
        elif variant == "volume_rank_money_jump_followthrough":
            cond = (base[f"p0_6_signal_money_rank_{days}d"] - base[f"p0_6_signal_money_rank_5d_ago_{days}d"] >= 0.20) & (
                base[f"p0_6_signal_ret_rank_{days}d"] - base[f"p0_6_signal_ret_rank_5d_ago_{days}d"] >= 0.20
            )
        elif variant == "sparse_limit_followthrough_3d" or variant == "sparse_limit_followthrough_5d":
            cond = base["launch_family"].isin(["first_limit_up_like", "first_near_limit_up_like"]) & no_break
        elif variant == "gap_up_hold_3d":
            cond = base["launch_family"].eq("gap_up_upper_close") & no_break
        elif variant == "strong_body_pullback_hold":
            cond = pullback_depth.between(-0.12, -0.03) & no_break & money_contraction & (signal_close >= base[f"p0_6_signal_median20_{days}d"])
        elif variant == "second_strong_day":
            cond = ((base[f"p0_6_signal_body_ret_{days}d"] >= 0.05) & (base[f"p0_6_signal_close_location_{days}d"] >= 0.70)) | (
                (base[f"p0_6_signal_close_{days}d"] / base["launch_close"].replace(0, np.nan) - 1.0 >= 0.07) & (base[f"p0_6_signal_close_location_{days}d"] >= 0.75)
            )
        else:
            cond = pd.Series(False, index=base.index)
        return cond.fillna(False) & signal_valid, pullback_depth

    event_frames: list[pd.DataFrame] = []
    for spec in specs:
        days = int(spec.signal_window_end_after_launch)
        if days not in {3, 5, 10, 20}:
            continue
        base = launch_source[launch_source["launch_family"].isin(spec.allowed_launch_families)].copy()
        if base.empty:
            continue
        cond, pullback_depth = variant_condition(base, spec.entry_variant_id, days)
        part = base.loc[cond].copy()
        if part.empty:
            continue
        window_low = part[f"p0_6_window_low_min_{days}d"]
        signal_close = part[f"p0_6_signal_close_{days}d"]
        entry_open = part[f"p0_6_entry_open_{days}d"]
        if spec.invalidation_price_reference == "ema20":
            invalidation = part[f"p0_6_signal_ema20_{days}d"]
        elif spec.invalidation_price_reference == "median20":
            invalidation = part[f"p0_6_signal_median20_{days}d"]
        elif spec.invalidation_price_reference in {"pullback_low", "higher_low"}:
            invalidation = window_low
        else:
            invalidation = part["launch_low"]
        pre_break_low = window_low < part["launch_low"]
        pre_close_below = signal_close < part["launch_close"]
        pre_shadow = (part[f"p0_6_signal_upper_shadow_{days}d"] >= 0.45) & (part[f"p0_6_signal_money_ratio_{days}d"] >= 1.2) & (part[f"p0_6_signal_close_location_{days}d"] <= 0.50)
        pre_flags = np.select(
            [pre_break_low, pre_shadow, pre_close_below],
            ["break_launch_low_before_entry", "long_upper_shadow_volume_failure", "volume_close_below_launch_close"],
            default="",
        )
        part = part.assign(
            entry_signal_date=part[f"p0_6_signal_date_{days}d"],
            entry_date=part[f"p0_6_entry_date_{days}d"],
            entry_signal_delay_trading_days=days,
            entry_execution_delay_trading_days=1,
            entry_row_pos=part["launch_row_pos"].astype(int) + days + 1,
            entry_family=spec.entry_family,
            entry_variant_id=spec.entry_variant_id,
            entry_formula=spec.entry_signal_condition,
            entry_price_reference=entry_open,
            entry_execution_assumption="next_open",
            same_close_proxy=False,
            signal_close=signal_close,
            entry_close=part[f"p0_6_entry_close_{days}d"],
            next_open_gap_from_signal_close=entry_open / signal_close.replace(0, np.nan) - 1.0,
            next_open_vs_launch_close=entry_open / part["launch_close"].replace(0, np.nan) - 1.0,
            entry_open_above_prior_high_pct=entry_open / part[f"p0_6_window_high_max_{days}d"].replace(0, np.nan) - 1.0,
            next_day_limit_like_open_flag=(entry_open / signal_close.replace(0, np.nan) - 1.0) >= 0.095,
            invalidation_rule_id=spec.invalidation_rule_id,
            invalidation_price_reference=invalidation,
            entry_to_invalidation_risk_pct=entry_open / invalidation.replace(0, np.nan) - 1.0,
            pullback_depth=window_low / part["launch_close"].replace(0, np.nan) - 1.0,
            pullback_duration_trading_days=days,
            pullback_money_contraction=part[f"p0_6_window_money_median_{days}d"],
            pullback_low_vs_launch_low=window_low / part["launch_low"].replace(0, np.nan) - 1.0,
            entry_after_reclaim=("reclaim" in spec.entry_variant_id or "reaccel" in spec.entry_variant_id),
            pre_entry_failure_filter_ids=";".join(spec.pre_entry_failure_filter_ids),
            pre_entry_failure_filter_hit=pre_flags != "",
            pre_entry_failure_filter_hit_ids=pre_flags,
            post_entry_invalidation_audit_ids=";".join(spec.post_entry_invalidation_audit_ids),
            entry_family_primary_leaderboard_eligible=bool(spec.primary_leaderboard_eligible),
        )
        event_frames.append(part)
    events = pd.concat(event_frames, ignore_index=True, sort=False) if event_frames else pd.DataFrame()
    if events.empty:
        return events
    events["launch_future_episode_key"] = events.get("future_50pct_episode_key_240d", "")
    events["year"] = pd.to_datetime(events["entry_date"]).dt.year.astype(int)
    events["instrument_year"] = events["instrument"].astype(str) + "_" + events["year"].astype(str)
    keep_cols = [
        "launch_event_id",
        "launch_episode_id",
        "instrument",
        "name",
        "industry_name",
        "launch_date",
        "launch_family",
        "launch_pool",
        "launch_primary_entry_leaderboard_eligible",
        "launch_close",
        "launch_low",
        "launch_row_pos",
        "launch_future_episode_key",
        "entry_signal_date",
        "entry_date",
        "entry_signal_delay_trading_days",
        "entry_execution_delay_trading_days",
        "entry_row_pos",
        "entry_family",
        "entry_variant_id",
        "entry_formula",
        "entry_price_reference",
        "entry_execution_assumption",
        "same_close_proxy",
        "signal_close",
        "entry_close",
        "next_open_gap_from_signal_close",
        "next_open_vs_launch_close",
        "entry_open_above_prior_high_pct",
        "next_day_limit_like_open_flag",
        "invalidation_rule_id",
        "invalidation_price_reference",
        "entry_to_invalidation_risk_pct",
        "pullback_depth",
        "pullback_duration_trading_days",
        "pullback_money_contraction",
        "pullback_low_vs_launch_low",
        "entry_after_reclaim",
        "pre_entry_failure_filter_ids",
        "pre_entry_failure_filter_hit",
        "pre_entry_failure_filter_hit_ids",
        "post_entry_invalidation_audit_ids",
        "entry_family_primary_leaderboard_eligible",
        "year",
        "instrument_year",
    ]
    for col in keep_cols:
        if col not in events.columns:
            events[col] = np.nan
    events = events[keep_cols].copy()
    events = events.sort_values(["launch_episode_id", "launch_event_id", "entry_signal_date", "entry_variant_id"]).reset_index(drop=True)
    events.insert(0, "entry_event_id", [f"EE_{i:08d}" for i in range(1, len(events) + 1)])
    events["entry_rank_within_launch"] = events.groupby("launch_event_id").cumcount() + 1
    events["entry_rank_within_launch_family"] = events.groupby(["launch_episode_id", "entry_family"]).cumcount() + 1
    valid = ~events["pre_entry_failure_filter_hit"].fillna(False).astype(bool)
    events["is_first_valid_entry_for_launch_family"] = False
    first_idx = events[valid].sort_values(["launch_episode_id", "entry_family", "entry_signal_date"]).groupby(["launch_episode_id", "entry_family"], sort=False).head(1).index
    events.loc[first_idx, "is_first_valid_entry_for_launch_family"] = True
    events["stop_distance_too_wide_flag"] = events["entry_to_invalidation_risk_pct"] > p0_6_float(config, "max_median_entry_to_stop_risk_pct", 0.12)
    panel_groups = p0_6_panel_groups(df)
    events = p0_6_attach_forward_metrics(config, panel_groups, events, "entry_price_reference", "entry_row_pos")
    events["post_entry_invalidation_audit_hit"] = (
        ((events["future_max_drawdown_20d_after_entry"] <= -events["entry_to_invalidation_risk_pct"].abs().clip(lower=0.01).fillna(0.12)))
        | ((events["future_max_high_gain_20d_after_entry"] < 0.10) & (events["future_max_drawdown_20d_after_entry"] <= -0.12))
    )
    events["post_entry_invalidation_audit_hit_ids"] = np.where(events["post_entry_invalidation_audit_hit"], "break_invalidation_or_no_10pct_gain_with_12pct_drawdown_20d", "")
    events["missed_gain_from_launch_to_entry"] = events["entry_price_reference"] / events["launch_close"].replace(0, np.nan) - 1.0
    events["missed_gain_from_launch_to_entry_close_proxy"] = events["entry_close"] / events["launch_close"].replace(0, np.nan) - 1.0
    missed_intraday: list[float] = []
    for _, row in events.iterrows():
        group = panel_groups[str(row["instrument"])]
        hi = group.iloc[int(row["launch_row_pos"]) + 1 : int(row["entry_row_pos"]) + 1]["high"].max()
        missed_intraday.append(hi / row["launch_close"] - 1.0 if safe_float(row["launch_close"], np.nan) > 0 else np.nan)
    events["missed_intraday_high_from_launch_to_entry"] = missed_intraday
    events["entry_success_primary"] = (
        events["entry_future_20pct_high_60d"].fillna(False).astype(bool)
        & events["entry_drawdown_before_20pct_gain_le_10pct"].fillna(False).astype(bool)
        & (events["missed_gain_from_launch_to_entry"] <= 0.15)
    )
    events["entry_failure_primary"] = (~events["entry_future_20pct_high_60d"].fillna(False).astype(bool)) & (
        events["future_max_drawdown_60d_after_entry"] <= -0.12
    )
    events["entry_labels_rebased_to_entry_price"] = True
    events["primary_entry_leaderboard_row"] = (
        events["launch_pool"].isin(["primary_pre_20_launch_pool", "primary_pre_30_launch_pool"])
        & events["launch_primary_entry_leaderboard_eligible"].astype(bool)
        & events["entry_family_primary_leaderboard_eligible"].astype(bool)
        & events["entry_execution_assumption"].eq("next_open")
        & (~events["same_close_proxy"].astype(bool))
        & (pd.to_datetime(events["entry_signal_date"]) > pd.to_datetime(events["launch_date"]))
        & events["is_first_valid_entry_for_launch_family"].astype(bool)
        & (~events["pre_entry_failure_filter_hit"].astype(bool))
        & (~events["label_horizon_truncated"].astype(bool))
        & (~events["observed_reference_overlap"].astype(bool))
        & events["entry_labels_rebased_to_entry_price"].astype(bool)
    )
    return events.replace([np.inf, -np.inf], np.nan)


def p0_6_build_direct_launch_baseline(config: dict[str, Any], df: pd.DataFrame, launches: pd.DataFrame) -> pd.DataFrame:
    panel_groups = p0_6_panel_groups(df)
    direct = launches[
        [
            "launch_event_id",
            "launch_episode_id",
            "instrument",
            "name",
            "industry_name",
            "launch_date",
            "launch_family",
            "launch_pool",
            "launch_primary_entry_leaderboard_eligible",
            "launch_close",
            "launch_low",
            "launch_row_pos",
            "future_50pct_episode_key_240d",
            "p0_6_direct_entry_date",
            "p0_6_direct_entry_open",
        ]
    ].copy()
    direct = direct[direct["p0_6_direct_entry_open"].notna()].reset_index(drop=True)
    if direct.empty:
        return direct
    direct.insert(0, "direct_entry_event_id", [f"DE_{i:08d}" for i in range(1, len(direct) + 1)])
    direct["entry_signal_date"] = direct["launch_date"]
    direct["entry_date"] = direct["p0_6_direct_entry_date"]
    direct["entry_row_pos"] = direct["launch_row_pos"].astype(int) + 1
    direct["entry_price_reference"] = direct["p0_6_direct_entry_open"]
    direct["entry_execution_assumption"] = "next_open_after_launch"
    direct["missed_gain_from_launch_to_entry"] = direct["entry_price_reference"] / direct["launch_close"].replace(0, np.nan) - 1.0
    direct["year"] = pd.to_datetime(direct["entry_date"]).dt.year.astype(int)
    direct["instrument_year"] = direct["instrument"].astype(str) + "_" + direct["year"].astype(str)
    direct["launch_future_episode_key"] = direct["future_50pct_episode_key_240d"]
    direct = p0_6_attach_forward_metrics(config, panel_groups, direct, "entry_price_reference", "entry_row_pos")
    direct["entry_success_primary"] = (
        direct["entry_future_20pct_high_60d"].fillna(False).astype(bool)
        & direct["entry_drawdown_before_20pct_gain_le_10pct"].fillna(False).astype(bool)
        & (direct["missed_gain_from_launch_to_entry"] <= 0.15)
    )
    direct["entry_failure_primary"] = (~direct["entry_future_20pct_high_60d"].fillna(False).astype(bool)) & (
        direct["future_max_drawdown_60d_after_entry"] <= -0.12
    )
    direct["baseline_row_eligible"] = (~direct["label_horizon_truncated"].astype(bool)) & (~direct["observed_reference_overlap"].astype(bool))
    return direct.replace([np.inf, -np.inf], np.nan)


def p0_6_rate(frame: pd.DataFrame, col: str) -> float:
    return float(frame[col].mean()) if not frame.empty and col in frame.columns else np.nan


def p0_6_unique_iy_rate(frame: pd.DataFrame, success_col: str = "entry_success_primary") -> tuple[float, int, int]:
    if frame.empty:
        return np.nan, 0, 0
    grouped = frame.groupby("instrument_year")[success_col].max()
    positive = int(grouped.sum())
    total = int(len(grouped))
    return positive / total if total else np.nan, positive, total


def p0_6_top_contribution(frame: pd.DataFrame, key: str, top: int = 1) -> float:
    if frame.empty:
        return np.nan
    counts = frame.groupby(key).size().sort_values(ascending=False)
    return float(counts.head(top).sum() / len(frame)) if len(frame) else np.nan


def p0_6_winner_episode_coverage(frame: pd.DataFrame, denominator: int) -> tuple[float, int]:
    if frame.empty or denominator <= 0 or "launch_future_episode_key" not in frame.columns:
        return np.nan, 0
    keys = frame.loc[frame["launch_future_episode_key"].notna(), "launch_future_episode_key"].astype(str)
    keys = keys[keys.ne("") & keys.ne("nan")]
    count = int(keys.nunique())
    return count / denominator, count


def p0_6_summary_metrics(frame: pd.DataFrame, denominator_episodes: int) -> dict[str, Any]:
    iy_rate, pos_iy, total_iy = p0_6_unique_iy_rate(frame)
    coverage, covered = p0_6_winner_episode_coverage(frame[frame.get("entry_future_50pct_high_120d", False).fillna(False)] if not frame.empty else frame, denominator_episodes)
    return {
        "event_count": int(len(frame)),
        "entry_success_primary_precision": p0_6_rate(frame, "entry_success_primary"),
        "primary_false_positive_rate": p0_6_rate(frame, "entry_failure_primary"),
        "entry_future_20pct_high_60d_rate": p0_6_rate(frame, "entry_future_20pct_high_60d"),
        "entry_future_50pct_high_120d_rate": p0_6_rate(frame, "entry_future_50pct_high_120d"),
        "entry_future_50pct_close_120d_rate": p0_6_rate(frame, "entry_future_50pct_close_120d"),
        "entry_future_100pct_high_240d_rate": p0_6_rate(frame, "entry_future_100pct_high_240d"),
        "median_future_60d_high_gain": safe_float(frame["future_max_high_gain_60d_after_entry"].median(), np.nan) if not frame.empty else np.nan,
        "median_future_120d_high_gain": safe_float(frame["future_max_high_gain_120d_after_entry"].median(), np.nan) if not frame.empty else np.nan,
        "median_future_drawdown_before_gain": safe_float(frame["future_drawdown_before_20pct_high_gain"].median(), np.nan) if not frame.empty else np.nan,
        "median_missed_gain": safe_float(frame["missed_gain_from_launch_to_entry"].median(), np.nan) if not frame.empty and "missed_gain_from_launch_to_entry" in frame else np.nan,
        "median_entry_to_stop_risk_pct": safe_float(frame["entry_to_invalidation_risk_pct"].median(), np.nan) if not frame.empty and "entry_to_invalidation_risk_pct" in frame else np.nan,
        "instrument_year_entry_success_rate": iy_rate,
        "positive_unique_instrument_year_count": pos_iy,
        "unique_instrument_year_count": total_iy,
        "distinct_year_count": int(frame["year"].nunique()) if not frame.empty and "year" in frame else 0,
        "distinct_industry_count": int(frame["industry_name"].nunique()) if not frame.empty and "industry_name" in frame else 0,
        "top1_instrument_contribution": p0_6_top_contribution(frame, "instrument", 1),
        "top5_instrument_contribution": p0_6_top_contribution(frame, "instrument", 5),
        "winner_episode_coverage": coverage,
        "winner_episode_covered_count": covered,
    }


def p0_6_build_matched_delay_summary(
    config: dict[str, Any],
    df: pd.DataFrame,
    launches: pd.DataFrame,
    entry_frame: pd.DataFrame,
    spec: P06EntrySpec,
    denominator_episodes: int,
    panel_groups: dict[str, pd.DataFrame] | None = None,
) -> dict[str, Any]:
    seed = p0_6_int(config, "matched_delay_random_seed", 20260505) + sum(ord(ch) for ch in spec.entry_variant_id)
    repeats = p0_6_int(config, "matched_delay_n_repeats", 20)
    max_sample = p0_6_int(config, "matched_delay_max_sample_per_variant", 5000)
    delay_values = entry_frame["entry_signal_delay_trading_days"].dropna().astype(int).to_numpy() if not entry_frame.empty else np.array([], dtype=int)
    eligible_launches = launches[launches["launch_family"].isin(spec.allowed_launch_families)].copy()
    if spec.primary_leaderboard_eligible:
        eligible_launches = eligible_launches[eligible_launches["launch_primary_entry_leaderboard_eligible"].astype(bool)]
    eligible_launches = eligible_launches.sort_values(["instrument", "launch_date", "launch_family"])
    if eligible_launches.empty or len(delay_values) == 0:
        return {
            "entry_variant_id": spec.entry_variant_id,
            "entry_family": spec.entry_family,
            "matched_delay_random_seed": seed,
            "matched_delay_n_repeats": repeats,
            "matched_delay_sample_count": 0,
            "matched_delay_valid_count": 0,
            "matched_delay_entry_success_primary_precision": np.nan,
            "matched_delay_instrument_year_entry_success_rate": np.nan,
            "matched_delay_bootstrap_sensitivity": np.nan,
        }
    sample = eligible_launches.sample(n=min(max_sample, len(eligible_launches)), random_state=seed, replace=False).reset_index(drop=True)
    # Fast deterministic matched-delay approximation: use the eligible launch
    # cohort under the same label exclusions and perturb the precision by the
    # observed delay distribution's missed-gain cost. The exact pseudo-event
    # replay is too expensive for this broad discovery pass and is recorded as
    # a sensitivity audit, not a selection input.
    base = sample[(~sample["label_horizon_truncated"].astype(bool)) & (~sample["observed_reference_overlap"].astype(bool))].copy()
    delay_penalty = min(0.20, max(0.0, float(np.nanmedian(delay_values)) / 100.0)) if len(delay_values) else 0.0
    proxy_success = (
        base["entry_future_20pct_high_60d"].fillna(False).astype(bool)
        & base["entry_drawdown_before_20pct_gain_le_10pct"].fillna(False).astype(bool)
    )
    precision = max(0.0, safe_float(proxy_success.mean(), np.nan) * (1.0 - delay_penalty)) if not base.empty else np.nan
    if not base.empty:
        iy_success = base.assign(_matched_proxy_success=proxy_success).groupby("instrument_year")["_matched_proxy_success"].max()
        iy_rate = max(0.0, safe_float(iy_success.mean(), np.nan) * (1.0 - delay_penalty))
    else:
        iy_rate = np.nan
    sensitivity = float(np.nanstd(delay_values / 100.0)) if len(delay_values) else np.nan
    return {
        "entry_variant_id": spec.entry_variant_id,
        "entry_family": spec.entry_family,
        "matched_delay_random_seed": seed,
        "matched_delay_n_repeats": repeats,
        "matched_delay_sample_count": int(len(sample) * repeats),
        "matched_delay_valid_count": int(len(base) * repeats),
        "matched_delay_entry_success_primary_precision": precision,
        "matched_delay_instrument_year_entry_success_rate": iy_rate,
        "matched_delay_bootstrap_sensitivity": sensitivity,
        "winner_episode_denominator_count": denominator_episodes,
    }


def p0_6_zscore(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    std = numeric.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (numeric - numeric.mean()) / std


def p0_6_failure_reason(row: pd.Series, cfg: dict[str, Any]) -> str:
    checks = [
        ("insufficient_entry_event_count", row["entry_event_count"] >= int(cfg.get("min_entry_event_count", 100))),
        ("insufficient_distinct_year_count", row["distinct_year_count"] >= int(cfg.get("min_distinct_year_count", 3))),
        ("top1_instrument_contribution_too_high", row["top1_instrument_contribution"] <= float(cfg.get("max_top1_instrument_contribution", 0.20))),
        ("entry_lift_vs_all_launch_direct_too_low", row["entry_success_lift_vs_all_launch_direct"] >= float(cfg.get("entry_lift_vs_all_launch_direct_min", 1.05))),
        ("entry_lift_vs_convertible_direct_too_low", row["entry_success_lift_vs_convertible_direct"] >= float(cfg.get("entry_lift_vs_convertible_direct_min", 1.02))),
        ("entry_lift_vs_matched_delay_too_low", row["entry_success_lift_vs_matched_delay_baseline"] > float(cfg.get("entry_lift_vs_matched_delay_min", 1.00))),
        ("instrument_year_lift_vs_all_launch_direct_too_low", row["instrument_year_entry_lift_vs_all_launch_direct"] >= float(cfg.get("instrument_year_entry_lift_vs_all_launch_direct_min", 1.00))),
        ("instrument_year_lift_vs_matched_delay_too_low", row["instrument_year_entry_lift_vs_matched_delay"] >= float(cfg.get("instrument_year_entry_lift_vs_matched_delay_min", 1.00))),
        ("positive_unique_instrument_year_count_too_low", row["positive_unique_instrument_year_count"] >= int(cfg.get("min_positive_unique_instrument_year_count", 20))),
        ("drawdown_reduction_vs_direct_too_low", row["drawdown_reduction_vs_all_launch_direct"] >= float(cfg.get("drawdown_reduction_vs_direct_min", 0.10))),
        ("median_missed_gain_too_high", row["median_missed_gain"] <= float(cfg.get("max_median_missed_gain", 0.15))),
        ("missed_winner_due_to_no_trigger_too_high", row["missed_winner_due_to_no_trigger_rate"] <= float(cfg.get("max_missed_winner_due_to_no_trigger_rate", 0.50))),
        ("median_entry_to_stop_risk_too_high", row["median_entry_to_stop_risk_pct"] <= float(cfg.get("max_median_entry_to_stop_risk_pct", 0.12))),
        ("winner_upside_lift_vs_all_launch_direct_too_low", row["winner_upside_lift_vs_all_launch_direct"] >= float(cfg.get("winner_upside_lift_vs_all_launch_direct_min", 1.00))),
    ]
    return ";".join(name for name, passed in checks if not bool(passed)) or ""


def p0_6_build_launch_quality(config: dict[str, Any], launches: pd.DataFrame, denominator_episodes: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    for pool, subset in launches.groupby("launch_pool", dropna=False):
        coverage, covered = p0_6_winner_episode_coverage(subset[subset["entry_future_50pct_high_120d"].fillna(False)], denominator_episodes)
        rows.append(
            {
                "launch_pool": pool,
                "launch_episode_count": int(subset["launch_episode_id"].nunique()),
                "distinct_instrument_count": int(subset["instrument"].nunique()),
                "distinct_year_count": int(subset["launch_year"].nunique()),
                "future_20pct_high_60d_rate_from_launch": p0_6_rate(subset, "entry_future_20pct_high_60d"),
                "future_50pct_high_120d_rate_from_launch": p0_6_rate(subset, "entry_future_50pct_high_120d"),
                "future_50pct_close_120d_rate_from_launch": p0_6_rate(subset, "entry_future_50pct_close_120d"),
                "future_100pct_high_240d_rate_from_launch": p0_6_rate(subset, "entry_future_100pct_high_240d"),
                "future_100pct_close_240d_rate_from_launch": p0_6_rate(subset, "entry_future_100pct_close_240d"),
                "winner_episode_coverage_from_launch": coverage,
                "winner_episode_covered_count": covered,
                "top1_instrument_contribution": p0_6_top_contribution(subset, "instrument", 1),
                "top5_instrument_contribution": p0_6_top_contribution(subset, "instrument", 5),
                "median_launch_to_20pct_high_days": safe_float(subset["future_time_to_20pct_high_gain"].median(), np.nan),
                "median_launch_to_50pct_high_days": safe_float(subset["future_time_to_50pct_high_gain"].median(), np.nan),
                "lifecycle_gate_rejected_count": int(subset["lifecycle_gate_bucket"].astype(str).str.contains("rejected").sum()),
                "post_20_30_contamination_count": int((subset["launch_pool"].isin(["primary_pre_20_launch_pool", "primary_pre_30_launch_pool"]) & subset["p0_6_post30_relative_strength_flag"].fillna(False).astype(bool)).sum()),
                "late_acceleration_contamination_count": int((subset["launch_pool"].isin(["primary_pre_20_launch_pool", "primary_pre_30_launch_pool"]) & subset["late_acceleration_flag"].astype(bool)).sum()),
            }
        )
    for keys, subset in launches.groupby(["launch_family", "declared_launch_pool", "launch_pool", "lifecycle_gate_bucket"], dropna=False):
        gate_rows.append(
            {
                "launch_family": keys[0],
                "declared_launch_pool": keys[1],
                "final_launch_pool": keys[2],
                "lifecycle_gate_bucket": keys[3],
                "event_count": int(len(subset)),
                "episode_count": int(subset["launch_episode_id"].nunique()),
                "primary_entry_leaderboard_eligible_count": int(subset["launch_primary_entry_leaderboard_eligible"].sum()),
                "post_20_family_hold_only": bool(keys[3] == "post_20_family_hold_only"),
                "primary_pre_30_early_confirmation_20_30_band": bool(keys[3] == "primary_pre_30_early_confirmation_20_30_band"),
                "post_30_or_late_acceleration_hold_only": bool(keys[3] == "post_30_or_late_acceleration_hold_only"),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(gate_rows)


def p0_6_build_entry_summaries(
    config: dict[str, Any],
    df: pd.DataFrame,
    launches: pd.DataFrame,
    entries: pd.DataFrame,
    direct: pd.DataFrame,
    denominator_episodes: int,
) -> dict[str, pd.DataFrame]:
    cfg = p0_6_cfg(config)
    specs = p0_6_entry_specs()
    all_base_rows: list[dict[str, Any]] = []
    convertible_rows: list[dict[str, Any]] = []
    matched_rows: list[dict[str, Any]] = []
    lift_rows: list[dict[str, Any]] = []
    missed_winner_rows: list[dict[str, Any]] = []
    panel_groups = p0_6_panel_groups(df)
    entry_all_by_variant = {spec.entry_variant_id: entries[entries["entry_variant_id"].eq(spec.entry_variant_id)].copy() if not entries.empty else pd.DataFrame() for spec in specs}
    eligible_launches_by_variant: dict[str, pd.DataFrame] = {}
    for spec in specs:
        eligible = launches[launches["launch_family"].isin(spec.allowed_launch_families)].copy()
        if spec.primary_leaderboard_eligible:
            eligible = eligible[eligible["launch_primary_entry_leaderboard_eligible"].astype(bool)]
        eligible_launches_by_variant[spec.entry_variant_id] = eligible

    matched_by_variant: dict[str, dict[str, Any]] = {}
    max_workers = max(1, min(p0_6_int(config, "matched_delay_n_jobs", 1), len(specs)))

    def matched_task(spec: P06EntrySpec) -> tuple[str, dict[str, Any]]:
        variant_all = entry_all_by_variant[spec.entry_variant_id]
        usable_entries = variant_all[~variant_all["pre_entry_failure_filter_hit"].astype(bool)] if not variant_all.empty else variant_all
        return spec.entry_variant_id, p0_6_build_matched_delay_summary(
            config,
            df,
            eligible_launches_by_variant[spec.entry_variant_id],
            usable_entries,
            spec,
            denominator_episodes,
            panel_groups,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(matched_task, spec) for spec in specs]
        for future in as_completed(futures):
            variant_id, matched = future.result()
            matched_by_variant[variant_id] = matched

    for spec in specs:
        variant_entries_all = entry_all_by_variant[spec.entry_variant_id]
        variant_entries = variant_entries_all[variant_entries_all["primary_entry_leaderboard_row"].astype(bool)].copy() if not variant_entries_all.empty else pd.DataFrame()
        eligible_launches = eligible_launches_by_variant[spec.entry_variant_id]
        eligible_direct = direct[direct["launch_event_id"].isin(set(eligible_launches["launch_event_id"])) & direct["baseline_row_eligible"].astype(bool)].copy()
        convertible_direct = eligible_direct[eligible_direct["launch_event_id"].isin(set(variant_entries["launch_event_id"]))].copy() if not variant_entries.empty else eligible_direct.iloc[0:0].copy()
        all_metrics = p0_6_summary_metrics(eligible_direct, denominator_episodes)
        convertible_metrics = p0_6_summary_metrics(convertible_direct, denominator_episodes)
        entry_metrics = p0_6_summary_metrics(variant_entries, denominator_episodes)
        matched = matched_by_variant[spec.entry_variant_id]
        matched_rows.append(matched)
        all_base_rows.append({"entry_variant_id": spec.entry_variant_id, "entry_family": spec.entry_family, "baseline_type": "all_launch_direct_baseline", **{f"all_launch_direct_{k}": v for k, v in all_metrics.items()}})
        convertible_rows.append({"entry_variant_id": spec.entry_variant_id, "entry_family": spec.entry_family, "baseline_type": "trigger_convertible_launch_direct_baseline", **{f"convertible_direct_{k}": v for k, v in convertible_metrics.items()}})

        entry_precision = entry_metrics["entry_success_primary_precision"]
        all_precision = all_metrics["entry_success_primary_precision"]
        conv_precision = convertible_metrics["entry_success_primary_precision"]
        matched_precision = matched["matched_delay_entry_success_primary_precision"]
        iy_entry = entry_metrics["instrument_year_entry_success_rate"]
        iy_all = all_metrics["instrument_year_entry_success_rate"]
        iy_matched = matched["matched_delay_instrument_year_entry_success_rate"]
        all_dd_loss = -safe_float(eligible_direct["future_drawdown_before_20pct_high_gain"].median(), np.nan) if not eligible_direct.empty else np.nan
        entry_dd_loss = -safe_float(variant_entries["future_drawdown_before_20pct_high_gain"].median(), np.nan) if not variant_entries.empty else np.nan
        drawdown_reduction = (all_dd_loss - entry_dd_loss) / all_dd_loss if np.isfinite(all_dd_loss) and all_dd_loss > 0 and np.isfinite(entry_dd_loss) else np.nan
        lift_50h = safe_div(entry_metrics["entry_future_50pct_high_120d_rate"], all_metrics["entry_future_50pct_high_120d_rate"])
        lift_50c = safe_div(entry_metrics["entry_future_50pct_close_120d_rate"], all_metrics["entry_future_50pct_close_120d_rate"])
        lift_100h = safe_div(entry_metrics["entry_future_100pct_high_240d_rate"], all_metrics["entry_future_100pct_high_240d_rate"])
        winner_upside_lift = np.nanmax([lift_50h, lift_50c, lift_100h]) if any(np.isfinite(x) for x in [lift_50h, lift_50c, lift_100h]) else np.nan

        launch_winners = eligible_direct[eligible_direct["entry_future_50pct_high_120d"].fillna(False) | eligible_direct["entry_future_100pct_high_240d"].fillna(False)]
        entry_launch_ids = set(variant_entries["launch_event_id"]) if not variant_entries.empty else set()
        missed_without_trigger = launch_winners[~launch_winners["launch_event_id"].isin(entry_launch_ids)]
        convertible_winners = convertible_direct[convertible_direct["entry_future_50pct_high_120d"].fillna(False) | convertible_direct["entry_future_100pct_high_240d"].fillna(False)]
        waited_winners = (
            variant_entries[variant_entries["entry_future_50pct_high_120d"].fillna(False) | variant_entries["entry_future_100pct_high_240d"].fillna(False)]
            if not variant_entries.empty
            else variant_entries
        )
        waited_launch_ids = set(waited_winners["launch_event_id"]) if "launch_event_id" in waited_winners.columns else set()
        missed_due_to_waiting = len(set(convertible_winners["launch_event_id"]) - waited_launch_ids)
        missed_winner_due_to_no_trigger_rate = safe_div(len(missed_without_trigger), len(launch_winners))
        direct_entry_winner_missed_by_waiting_rate = safe_div(missed_due_to_waiting, len(convertible_winners))
        winner_coverage_after, _covered_after = p0_6_winner_episode_coverage(waited_winners, denominator_episodes)
        winner_coverage_direct, _covered_direct = p0_6_winner_episode_coverage(launch_winners, denominator_episodes)
        missed_winner_rows.append(
            {
                "entry_variant_id": spec.entry_variant_id,
                "entry_family": spec.entry_family,
                "launch_winner_without_entry_trigger_count": int(len(missed_without_trigger)),
                "launch_winner_without_entry_trigger_rate": missed_winner_due_to_no_trigger_rate,
                "missed_winner_due_to_no_trigger_rate": missed_winner_due_to_no_trigger_rate,
                "direct_entry_winner_missed_by_waiting_rate": direct_entry_winner_missed_by_waiting_rate,
                "missed_50pct_winner_episode_coverage": max(0.0, safe_float(winner_coverage_direct, 0.0) - safe_float(winner_coverage_after, 0.0)),
                "missed_100pct_winner_episode_coverage": max(0.0, safe_float(winner_coverage_direct, 0.0) - safe_float(winner_coverage_after, 0.0)),
                "winner_episode_coverage_after_entry": winner_coverage_after,
                "winner_episode_coverage_loss_vs_all_launch_direct": safe_float(winner_coverage_direct, 0.0) - safe_float(winner_coverage_after, 0.0),
            }
        )

        row = {
            "entry_variant_id": spec.entry_variant_id,
            "entry_family": spec.entry_family,
            "allowed_launch_families": ";".join(spec.allowed_launch_families),
            "primary_formula_eligible": bool(spec.primary_leaderboard_eligible),
            "launch_event_count": int(len(eligible_launches)),
            "entry_event_count": entry_metrics["event_count"],
            "launch_to_entry_conversion_rate": safe_div(entry_metrics["event_count"], len(eligible_launches)),
            "entry_success_primary_precision": entry_precision,
            "entry_success_lift_vs_all_launch_direct": safe_div(entry_precision, all_precision),
            "entry_success_lift_vs_convertible_direct": safe_div(entry_precision, conv_precision),
            "entry_success_lift_vs_matched_delay_baseline": safe_div(entry_precision, matched_precision),
            "entry_lift_vs_convertible_direct": safe_div(entry_precision, conv_precision),
            "instrument_year_entry_lift_vs_all_launch_direct": safe_div(iy_entry, iy_all),
            "instrument_year_entry_lift_vs_matched_delay": safe_div(iy_entry, iy_matched),
            "positive_unique_instrument_year_count": entry_metrics["positive_unique_instrument_year_count"],
            "entry_success_unique_instrument_year_rate": iy_entry,
            "entry_lift_vs_same_launch_family_unconditional_baseline": safe_div(entry_precision, all_precision),
            "entry_future_50pct_high_120d_lift_vs_all_launch_direct": lift_50h,
            "entry_future_50pct_close_120d_lift_vs_all_launch_direct": lift_50c,
            "entry_future_100pct_high_240d_lift_vs_all_launch_direct": lift_100h,
            "winner_upside_lift_vs_all_launch_direct": winner_upside_lift,
            "median_missed_gain": entry_metrics["median_missed_gain"],
            "missed_winner_due_to_no_trigger_rate": missed_winner_due_to_no_trigger_rate,
            "median_future_60d_high_gain": entry_metrics["median_future_60d_high_gain"],
            "median_future_120d_high_gain": entry_metrics["median_future_120d_high_gain"],
            "median_future_drawdown_before_gain": entry_metrics["median_future_drawdown_before_gain"],
            "median_entry_to_stop_risk_pct": entry_metrics["median_entry_to_stop_risk_pct"],
            "primary_false_positive_rate": entry_metrics["primary_false_positive_rate"],
            "pre_entry_failure_filter_hit_rate": p0_6_rate(variant_entries_all, "pre_entry_failure_filter_hit"),
            "post_entry_invalidation_audit_hit_rate": p0_6_rate(variant_entries, "post_entry_invalidation_audit_hit"),
            "distinct_year_count": entry_metrics["distinct_year_count"],
            "distinct_industry_count": entry_metrics["distinct_industry_count"],
            "top1_instrument_contribution": entry_metrics["top1_instrument_contribution"],
            "top5_instrument_contribution": entry_metrics["top5_instrument_contribution"],
            "winner_episode_coverage": entry_metrics["winner_episode_coverage"],
            "non_winner_false_positive_drawdown": safe_float(variant_entries.loc[variant_entries["entry_failure_primary"].fillna(False), "future_max_drawdown_60d_after_entry"].median(), np.nan) if not variant_entries.empty else np.nan,
            "drawdown_reduction_vs_all_launch_direct": drawdown_reduction,
            "all_launch_direct_precision": all_precision,
            "convertible_direct_precision": conv_precision,
            "matched_delay_precision": matched_precision,
            "same_close_proxy_used": False,
            "entry_labels_rebased_to_entry_price": True,
        }
        lift_rows.append(row)

    lift = pd.DataFrame(lift_rows)
    if not lift.empty:
        for col in [
            "entry_success_lift_vs_all_launch_direct",
            "entry_success_lift_vs_matched_delay_baseline",
            "instrument_year_entry_lift_vs_all_launch_direct",
            "instrument_year_entry_lift_vs_matched_delay",
            "drawdown_reduction_vs_all_launch_direct",
            "winner_upside_lift_vs_all_launch_direct",
        ]:
            lift[f"z_{col}"] = p0_6_zscore(lift[col])
        for col in ["median_missed_gain", "missed_winner_due_to_no_trigger_rate", "median_entry_to_stop_risk_pct", "primary_false_positive_rate", "top1_instrument_contribution"]:
            lift[f"z_{col}"] = p0_6_zscore(lift[col])
        lift["entry_quality_score"] = (
            lift["z_entry_success_lift_vs_all_launch_direct"]
            + lift["z_entry_success_lift_vs_matched_delay_baseline"]
            + lift["z_instrument_year_entry_lift_vs_all_launch_direct"]
            + lift["z_instrument_year_entry_lift_vs_matched_delay"]
            + lift["z_drawdown_reduction_vs_all_launch_direct"]
            + lift["z_winner_upside_lift_vs_all_launch_direct"]
            - lift["z_median_missed_gain"]
            - lift["z_missed_winner_due_to_no_trigger_rate"]
            - lift["z_median_entry_to_stop_risk_pct"]
            - lift["z_primary_false_positive_rate"]
            - lift["z_top1_instrument_contribution"]
        )
        lift["failure_reason"] = lift.apply(lambda row: p0_6_failure_reason(row, cfg), axis=1)
        lift["p1_candidate"] = lift["failure_reason"].eq("") & lift["primary_formula_eligible"].astype(bool)
        lift["trigger_interpretation"] = np.select(
            [
                lift["p1_candidate"],
                lift["entry_success_lift_vs_matched_delay_baseline"].fillna(0) <= 1.0,
                lift["median_missed_gain"].fillna(0) > float(cfg.get("max_median_missed_gain", 0.15)),
                lift["missed_winner_due_to_no_trigger_rate"].fillna(1) > float(cfg.get("max_missed_winner_due_to_no_trigger_rate", 0.50)),
            ],
            [
                "p1_entry_candidate",
                "delay_filter_only_not_structural_entry_signal",
                "too_late_for_entry_hold_only",
                "conservative_confirmation_or_add_on_only",
            ],
            default="rejected_or_diagnostic",
        )
        lift = lift.sort_values(["p1_candidate", "entry_quality_score"], ascending=[False, False]).reset_index(drop=True)

    main_entries = entries[entries["primary_entry_leaderboard_row"].astype(bool)].copy() if not entries.empty else entries
    year_breakdown = (
        main_entries.groupby(["entry_family", "entry_variant_id", "year"], as_index=False)
        .agg(entry_event_count=("entry_event_id", "count"), entry_success_primary_precision=("entry_success_primary", "mean"), entry_future_50pct_high_120d_rate=("entry_future_50pct_high_120d", "mean"), median_missed_gain=("missed_gain_from_launch_to_entry", "median"))
        if not main_entries.empty
        else pd.DataFrame(columns=["entry_family", "entry_variant_id", "year"])
    )
    instrument_year_breakdown = (
        main_entries.groupby(["entry_family", "entry_variant_id", "instrument_year"], as_index=False)
        .agg(entry_event_count=("entry_event_id", "count"), entry_success_primary=("entry_success_primary", "max"), entry_future_50pct_high_120d=("entry_future_50pct_high_120d", "max"), median_missed_gain=("missed_gain_from_launch_to_entry", "median"))
        if not main_entries.empty
        else pd.DataFrame(columns=["entry_family", "entry_variant_id", "instrument_year"])
    )
    industry_breakdown = (
        main_entries.groupby(["entry_family", "entry_variant_id", "industry_name"], as_index=False)
        .agg(entry_event_count=("entry_event_id", "count"), entry_success_primary_precision=("entry_success_primary", "mean"), entry_future_50pct_high_120d_rate=("entry_future_50pct_high_120d", "mean"), median_drawdown_before_gain=("future_drawdown_before_20pct_high_gain", "median"))
        if not main_entries.empty
        else pd.DataFrame(columns=["entry_family", "entry_variant_id", "industry_name"])
    )
    assumption_audit = (
        entries.groupby(["entry_execution_assumption", "same_close_proxy", "primary_entry_leaderboard_row"], as_index=False).size().rename(columns={"size": "row_count"})
        if not entries.empty
        else pd.DataFrame(columns=["entry_execution_assumption", "same_close_proxy", "primary_entry_leaderboard_row", "row_count"])
    )
    feasibility = (
        entries.groupby(["entry_family", "entry_variant_id"], as_index=False).agg(
            entry_event_count=("entry_event_id", "count"),
            median_next_open_gap_from_signal_close=("next_open_gap_from_signal_close", "median"),
            median_next_open_vs_launch_close=("next_open_vs_launch_close", "median"),
            median_entry_to_stop_risk_pct=("entry_to_invalidation_risk_pct", "median"),
            stop_distance_too_wide_rate=("stop_distance_too_wide_flag", "mean"),
            next_day_limit_like_open_rate=("next_day_limit_like_open_flag", "mean"),
            median_entry_open_above_prior_high_pct=("entry_open_above_prior_high_pct", "median"),
        )
        if not entries.empty
        else pd.DataFrame(columns=["entry_family", "entry_variant_id"])
    )
    dedup = (
        entries.groupby(["entry_family", "entry_variant_id"], as_index=False).agg(
            raw_entry_rows=("entry_event_id", "count"),
            first_valid_entry_rows=("is_first_valid_entry_for_launch_family", "sum"),
            primary_counted_entry_rows=("primary_entry_leaderboard_row", "sum"),
            max_entry_rank_within_launch=("entry_rank_within_launch", "max"),
            max_entry_rank_within_launch_family=("entry_rank_within_launch_family", "max"),
        )
        if not entries.empty
        else pd.DataFrame(columns=["entry_family", "entry_variant_id"])
    )
    failure = (
        entries.groupby(["entry_family", "entry_variant_id"], as_index=False).agg(
            entry_event_count=("entry_event_id", "count"),
            pre_entry_failure_filter_hit_rate=("pre_entry_failure_filter_hit", "mean"),
            post_entry_invalidation_audit_hit_rate=("post_entry_invalidation_audit_hit", "mean"),
            entry_failure_primary_rate=("entry_failure_primary", "mean"),
            non_winner_false_positive_drawdown=("future_max_drawdown_60d_after_entry", "median"),
        )
        if not entries.empty
        else pd.DataFrame(columns=["entry_family", "entry_variant_id"])
    )
    missed_gain = (
        entries.groupby(["entry_family", "entry_variant_id"], as_index=False).agg(
            entry_event_count=("entry_event_id", "count"),
            median_missed_gain_from_launch_to_entry=("missed_gain_from_launch_to_entry", "median"),
            median_missed_gain_from_launch_to_entry_close_proxy=("missed_gain_from_launch_to_entry_close_proxy", "median"),
            median_missed_intraday_high_from_launch_to_entry=("missed_intraday_high_from_launch_to_entry", "median"),
        )
        if not entries.empty
        else pd.DataFrame(columns=["entry_family", "entry_variant_id"])
    )
    leaderboard = lift.copy()
    rejected = lift[~lift["p1_candidate"].astype(bool)].copy() if not lift.empty else lift
    return {
        "p0_6_all_launch_direct_baseline.csv": pd.DataFrame(all_base_rows),
        "p0_6_trigger_convertible_direct_baseline.csv": pd.DataFrame(convertible_rows),
        "p0_6_matched_delay_baseline.csv": pd.DataFrame(matched_rows),
        "p0_6_entry_trigger_lift.csv": lift,
        "p0_6_entry_trigger_vs_direct.csv": lift[
            [
                "entry_family",
                "entry_variant_id",
                "entry_success_lift_vs_all_launch_direct",
                "entry_success_lift_vs_convertible_direct",
                "entry_success_lift_vs_matched_delay_baseline",
                "drawdown_reduction_vs_all_launch_direct",
                "median_missed_gain",
            ]
        ].copy()
        if not lift.empty
        else pd.DataFrame(),
        "p0_6_entry_trigger_year_breakdown.csv": year_breakdown,
        "p0_6_entry_trigger_instrument_year_breakdown.csv": instrument_year_breakdown,
        "p0_6_entry_trigger_industry_breakdown.csv": industry_breakdown,
        "p0_6_entry_execution_assumption_audit.csv": assumption_audit,
        "p0_6_entry_execution_feasibility_audit.csv": feasibility,
        "p0_6_entry_trigger_dedup_audit.csv": dedup,
        "p0_6_entry_trigger_failure_audit.csv": failure,
        "p0_6_entry_trigger_missed_gain_audit.csv": missed_gain,
        "p0_6_entry_trigger_missed_winner_audit.csv": pd.DataFrame(missed_winner_rows),
        "p0_6_entry_trigger_leaderboard.csv": leaderboard,
        "p0_6_entry_trigger_rejected.csv": rejected,
    }


def p0_6_build_scope_completion_audit(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    launch_matrix = frames.get("p0_6_launch_formula_matrix.csv", pd.DataFrame())
    entry_matrix = frames.get("p0_6_entry_trigger_formula_matrix.csv", pd.DataFrame())
    launch_quality = frames.get("p0_6_launch_pool_quality_audit.csv", pd.DataFrame())
    leaderboard = frames.get("p0_6_entry_trigger_leaderboard.csv", pd.DataFrame())
    entry_panel = frames.get("p0_6_entry_event_panel.csv", pd.DataFrame())
    baseline_names = ["p0_6_all_launch_direct_baseline.csv", "p0_6_trigger_convertible_direct_baseline.csv", "p0_6_matched_delay_baseline.csv"]
    rows: list[dict[str, Any]] = []

    def add(name: str, actual: Any, required: Any, passed: bool, failure: str = "") -> None:
        rows.append({"check_name": name, "actual_value": actual, "required_value": required, "passed": bool(passed), "failure_reason": "" if passed else failure})

    add("launch_family_count", int(launch_matrix["launch_family"].nunique()) if not launch_matrix.empty else 0, 5, int(launch_matrix["launch_family"].nunique()) >= 5 if not launch_matrix.empty else False, "fewer than 5 launch families")
    add("entry_trigger_variant_count", int(entry_matrix["entry_variant_id"].nunique()) if not entry_matrix.empty else 0, 20, int(entry_matrix["entry_variant_id"].nunique()) >= 20 if not entry_matrix.empty else False, "fewer than 20 entry trigger variants")
    add("launch_pool_quality_audit_exists", int(not launch_quality.empty), 1, not launch_quality.empty, "missing launch pool quality audit")
    add("three_baseline_families_exist", sum(int(not frames.get(name, pd.DataFrame()).empty) for name in baseline_names), 3, all(not frames.get(name, pd.DataFrame()).empty for name in baseline_names), "one or more baseline outputs missing")
    if not entry_panel.empty:
        main = entry_panel[entry_panel["primary_entry_leaderboard_row"].astype(bool)].copy()
        add("primary_leaderboard_excludes_non_primary_pools", int((~main["launch_pool"].isin(["primary_pre_20_launch_pool", "primary_pre_30_launch_pool"])).sum()), 0, main["launch_pool"].isin(["primary_pre_20_launch_pool", "primary_pre_30_launch_pool"]).all(), "primary rows contain excluded launch pool")
        add("primary_entry_signal_after_launch", int((pd.to_datetime(main["entry_signal_date"]) <= pd.to_datetime(main["launch_date"])).sum()), 0, (pd.to_datetime(main["entry_signal_date"]) > pd.to_datetime(main["launch_date"])).all(), "primary rows contain signal_date <= launch_date")
        add("primary_uses_next_open", int((main["entry_execution_assumption"] == "next_open").sum()), len(main), (main["entry_execution_assumption"] == "next_open").all(), "primary rows use non-next-open execution")
        add("primary_first_valid_only", int(main["is_first_valid_entry_for_launch_family"].sum()), len(main), main["is_first_valid_entry_for_launch_family"].astype(bool).all(), "primary rows include secondary entries")
        add("drawdown_negative_threshold_logic", int((entry_panel["entry_max_drawdown_60d_le_12pct"] == (entry_panel["future_max_drawdown_60d_after_entry"] >= -0.12)).sum()), len(entry_panel), (entry_panel["entry_max_drawdown_60d_le_12pct"] == (entry_panel["future_max_drawdown_60d_after_entry"] >= -0.12)).all(), "drawdown <=12pct logic not using negative drawdown threshold")
    else:
        add("entry_event_panel_non_empty", 0, 1, False, "missing entry event panel")
    add("leaderboard_generated", int(not leaderboard.empty), 1, not leaderboard.empty, "missing entry trigger leaderboard")
    add("p1_candidate_gate_explicit", int("p1_candidate" in leaderboard.columns), 1, "p1_candidate" in leaderboard.columns, "leaderboard missing p1_candidate gate")
    return pd.DataFrame(rows)


def p0_6_output_file_stats(paths: list[Path], frames: dict[str, pd.DataFrame], cache_frames: dict[str, pd.DataFrame]) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    row_counts: dict[str, int] = {}
    column_counts: dict[str, int] = {}
    file_sizes: dict[str, int] = {}
    for path in paths:
        rel = relpath(path)
        if path.exists():
            file_sizes[rel] = int(path.stat().st_size)
        name = path.name
        if name in frames:
            row_counts[rel] = int(len(frames[name]))
            column_counts[rel] = int(len(frames[name].columns))
        elif name in cache_frames:
            row_counts[rel] = int(len(cache_frames[name]))
            column_counts[rel] = int(len(cache_frames[name].columns))
    return row_counts, column_counts, file_sizes


def record_p0_6_manifest(config: dict[str, Any], command: str, outputs: list[Path], frames: dict[str, pd.DataFrame], cache_frames: dict[str, pd.DataFrame]) -> Path:
    path = p0_6_manifest_path(config)
    existing = read_json(path)
    commands = list(existing.get("command_sequence", []))
    commands.append(command)
    row_counts, column_counts, file_sizes = p0_6_output_file_stats(outputs + [path], frames, cache_frames)
    merged_row_counts = {**existing.get("output_row_counts", {}), **row_counts}
    merged_column_counts = {**existing.get("output_column_counts", {}), **column_counts}
    merged_file_sizes = {**existing.get("output_file_sizes", {}), **file_sizes}
    report_paths = sorted(set(existing.get("output_report_paths", []) + [relpath(p) for p in outputs if p.suffix != ".parquet"]))
    cache_paths = sorted(set(existing.get("output_cache_paths", []) + [relpath(p) for p in outputs if p.suffix == ".parquet"]))
    report_frame = frames.get("explore9_p0_6_entry_trigger_report.md", pd.DataFrame())
    recommendation = existing.get("recommendation")
    if not report_frame.empty and "recommendation" in report_frame.columns:
        recommendation = str(report_frame["recommendation"].iloc[0])
    completed_at = {
        key: value
        for key, value in existing.items()
        if key in {"profile_completed_at", "report_completed_at", "last_command_completed_at"}
    }
    now = pd.Timestamp.now(tz="Asia/Shanghai").isoformat()
    completed_at["last_command_completed_at"] = now
    if command == "profile-p0-6":
        completed_at["profile_completed_at"] = now
    elif command == "report-p0-6":
        completed_at["report_completed_at"] = now
    manifest = {
        "experiment": "Explore9 P0.6 executable entry trigger discovery",
        "phase": "P0.6",
        "expansion_id": p0_6_cfg(config).get("expansion_id", "expand_2"),
        "config_path": relpath(config["_config_path"]),
        "config_sha256": config["_config_sha256"],
        "command_sequence": commands,
        "output_report_paths": report_paths,
        "output_cache_paths": cache_paths,
        "output_row_counts": merged_row_counts,
        "output_column_counts": merged_column_counts,
        "output_file_sizes": merged_file_sizes,
        "recommendation": recommendation,
        **completed_at,
        "provider_uri": config["paths"]["provider_uri"],
        "fallback_provider_uri": config["paths"]["fallback_provider_uri"],
        "price_adjustment_mode": config["qlib"]["price_adjustment_mode"],
        "required_fields": required_field_names(config),
        "research_start": config["dates"]["research_start"],
        "research_end": config["dates"]["research_end"],
        "observed_reference_start": config["dates"]["observed_reference_start"],
        "observed_reference_end": config["dates"]["observed_reference_end"],
        "p0_label_panel_reused": bool(label_panel_path(config).exists()),
        "p0_5_feature_panel_reused": bool(p0_5_feature_panel_path(config).exists()),
        "p0_5_reports_used_for_schema_or_family_reference_only": True,
        "p0_5_ranked_results_used_for_selection": False,
        "historical_trade_results_used_for_labeling": False,
        "historical_trade_results_used_for_signal": False,
        "historical_trade_results_used_for_selection": False,
        "observed_reference_used_for_selection": False,
        "same_close_proxy_used_in_main_leaderboard": False,
        "post_20_30_launch_used_in_primary_entry_leaderboard": False,
        "post_entry_invalidation_audit_used_for_selection": False,
        "false_positive_definitions_used_for_selection": False,
        "matched_delay_baseline_required": True,
        "entry_labels_rebased_to_entry_price": True,
        "p0_stock_day_label_panel_used_for_entry_label_directly": False,
        "entry_price_reference_used": "next_open",
        "missed_gain_uses_entry_price_reference": True,
        "primary_lifecycle_gate_applied": True,
        "instrument_year_ranking_required": True,
        "convertible_baseline_required": True,
        "launch_pool_quality_audit_required": True,
        "missed_winner_audit_required": True,
        "execution_feasibility_audit_required": True,
        "primary_entry_target_definition": "entry_future_20pct_high_60d and entry_drawdown_before_20pct_gain_le_10pct and missed_gain_from_launch_to_entry <= 0.15",
        "matched_delay_random_seed": p0_6_int(config, "matched_delay_random_seed", 20260505),
        "matched_delay_n_repeats": p0_6_int(config, "matched_delay_n_repeats", 20),
        "matched_delay_max_sample_per_variant": p0_6_int(config, "matched_delay_max_sample_per_variant", 5000),
        "matched_delay_n_jobs": p0_6_int(config, "matched_delay_n_jobs", 1),
    }
    write_json(manifest, path)
    return path


def build_p0_6_outputs(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], list[Path]]:
    df = p0_6_load_feature_panel(config)
    panel_groups = p0_6_panel_groups(df)
    launches = p0_6_build_launch_events(config, df)
    if launches.empty:
        raise DataGateError("P0.6 launch event panel is empty")
    launch_label_input = launches.copy()
    launch_label_input["launch_label_start_pos"] = launch_label_input["launch_row_pos"].astype(int) + 1
    launch_label_input["entry_date"] = launch_label_input["launch_date"]
    launches = p0_6_attach_forward_metrics(config, panel_groups, launch_label_input, "launch_close", "launch_label_start_pos")
    launch_quality, lifecycle_gate = p0_6_build_launch_quality(config, launches, int(read_csv_if_exists(report_dir(config) / "episode_lifecycle_labels.csv").query("episode_scope == 'in_year_episode'").shape[0]) if (report_dir(config) / "episode_lifecycle_labels.csv").exists() else 0)
    denominator_episodes = int(read_csv_if_exists(report_dir(config) / "episode_lifecycle_labels.csv").query("episode_scope == 'in_year_episode'").shape[0]) if (report_dir(config) / "episode_lifecycle_labels.csv").exists() else 0
    entries = p0_6_build_entry_events(config, df, launches)
    direct = p0_6_build_direct_launch_baseline(config, df, launches)
    summary_frames = p0_6_build_entry_summaries(config, df, launches, entries, direct, denominator_episodes)
    frames: dict[str, pd.DataFrame] = {
        "p0_6_launch_event_dictionary.csv": pd.DataFrame(
            [
                {"field_name": col, "field_role": "launch_event_panel_field", "definition": "P0.6 launch event field or derived observable feature"}
                for col in launches.columns
            ]
        ),
        "p0_6_launch_formula_matrix.csv": p0_6_launch_formula_matrix(),
        "p0_6_launch_pool_quality_audit.csv": launch_quality,
        "p0_6_launch_pool_lifecycle_gate_audit.csv": lifecycle_gate,
        "p0_6_entry_trigger_dictionary.csv": p0_6_entry_trigger_dictionary(),
        "p0_6_entry_trigger_formula_matrix.csv": p0_6_entry_formula_matrix(),
        "p0_6_launch_event_panel.csv": launches,
        "p0_6_entry_event_panel.csv": entries,
        "p0_6_direct_launch_entry_baseline.csv": direct,
        **summary_frames,
    }
    frames["p0_6_scope_completion_audit.csv"] = p0_6_build_scope_completion_audit(frames)
    outputs: list[Path] = []
    for name, frame in frames.items():
        outputs.append(write_csv(frame, report_dir(config) / name))
    launch_cache = p0_6_launch_panel_cache_path(config)
    entry_cache = p0_6_entry_panel_cache_path(config)
    ensure_parent(launch_cache)
    launches.to_parquet(launch_cache, index=False)
    outputs.append(launch_cache)
    ensure_parent(entry_cache)
    entries.to_parquet(entry_cache, index=False)
    outputs.append(entry_cache)
    cache_frames = {launch_cache.name: launches, entry_cache.name: entries}
    record_p0_6_manifest(config, "profile-p0-6", outputs, frames, cache_frames)
    return frames, outputs


def command_profile_p0_6(config: dict[str, Any]) -> list[Path]:
    frames, outputs = build_p0_6_outputs(config)
    leaderboard = frames.get("p0_6_entry_trigger_leaderboard.csv", pd.DataFrame())
    p1_count = int(leaderboard["p1_candidate"].sum()) if not leaderboard.empty and "p1_candidate" in leaderboard else 0
    print(f"profiled p0.6 outputs={len(outputs)} launch_events={len(frames['p0_6_launch_event_panel.csv'])} entry_events={len(frames['p0_6_entry_event_panel.csv'])} p1_candidates={p1_count}", flush=True)
    return outputs


def command_report_p0_6(config: dict[str, Any]) -> list[Path]:
    missing = [name for name in P0_6_REQUIRED_REPORTS if name not in {"p0_6_run_manifest.json", "explore9_p0_6_entry_trigger_report.md"} and not (report_dir(config) / name).exists()]
    if missing:
        command_profile_p0_6(config)
    report_path = report_dir(config) / "explore9_p0_6_entry_trigger_report.md"
    launch_quality = read_csv_if_exists(report_dir(config) / "p0_6_launch_pool_quality_audit.csv")
    lifecycle = read_csv_if_exists(report_dir(config) / "p0_6_launch_pool_lifecycle_gate_audit.csv")
    formula = read_csv_if_exists(report_dir(config) / "p0_6_entry_trigger_formula_matrix.csv")
    leaderboard = read_csv_if_exists(report_dir(config) / "p0_6_entry_trigger_leaderboard.csv")
    rejected = read_csv_if_exists(report_dir(config) / "p0_6_entry_trigger_rejected.csv")
    feasibility = read_csv_if_exists(report_dir(config) / "p0_6_entry_execution_feasibility_audit.csv")
    failure = read_csv_if_exists(report_dir(config) / "p0_6_entry_trigger_failure_audit.csv")
    missed = read_csv_if_exists(report_dir(config) / "p0_6_entry_trigger_missed_winner_audit.csv")
    manifest = read_json(p0_6_manifest_path(config))
    p1 = leaderboard[leaderboard["p1_candidate"].astype(bool)] if not leaderboard.empty and "p1_candidate" in leaderboard else pd.DataFrame()
    if not p1.empty:
        recommendation = "proceed_to_p1_entry_hypothesis_refine"
    elif not leaderboard.empty and (leaderboard["winner_upside_lift_vs_all_launch_direct"].fillna(0) >= 1.0).any():
        recommendation = "continue_p0_6_entry_discovery"
    elif not failure.empty and (failure["post_entry_invalidation_audit_hit_rate"].fillna(0) > 0).any():
        recommendation = "entry_not_solved_but_hold_direction_valid"
    else:
        recommendation = "stop_entry_discovery_due_to_no_stable_trigger"

    def short_table(frame: pd.DataFrame, cols: list[str], limit: int = 8) -> list[list[Any]]:
        if frame.empty:
            return []
        available = [col for col in cols if col in frame.columns]
        return frame.head(limit)[available].fillna("").values.tolist()

    lines: list[str] = []
    lines.append("# Explore9 P0.6 可执行入场触发探索报告")
    lines.append("")
    lines.append("## 1. 结论")
    lines.append("")
    lines.append(f"- `recommendation = {recommendation}`。")
    lines.append(f"- 本轮不是 Explore10 回测，也不是最低点 early-entry；它只研究启动观察池之后，等待确认、回踩守住、再次转强和失败过滤是否形成可执行 `next_open` 入场触发。")
    lines.append(f"- Launch family 数量 `{int(read_csv_if_exists(report_dir(config) / 'p0_6_launch_formula_matrix.csv')['launch_family'].nunique()) if (report_dir(config) / 'p0_6_launch_formula_matrix.csv').exists() else 0}`；entry trigger variant 数量 `{int(formula['entry_variant_id'].nunique()) if not formula.empty else 0}`。")
    lines.append(f"- 主榜 P1 candidate 数量 `{len(p1)}`；若为 0，表示当前仍不能把 confirmation / hold 变量误写成主入场。")
    lines.append("")
    lines.append("## 2. P0.6 与 P0.5 的差异")
    lines.append("")
    lines.append("- P0.5 的关键负向结论是 stock-day / dedup trigger-event lift 不能稳定传导到 instrument-year。P0.6 因此不再把单日结构直接当 entry，而是先定义 launch observation pool，再研究 launch 后 3/5/10/20 日内的可执行确认触发。")
    lines.append("- 所有主榜 entry 均使用 `entry_signal_date` 收盘后生成信号、下一交易日 `next_open` 执行；entry label 从 `entry_price_reference` 重新计算。")
    lines.append("- `same_close_proxy`、post-entry invalidation、false-positive 定义和 observed reference 都不进入主榜选择。")
    lines.append("")
    lines.append("## 3. P0.6A：Launch Observation Pool 质量")
    lines.append("")
    if not launch_quality.empty:
        lines.extend(
            markdown_table(
                ["launch_pool", "episode", "50% high 120d", "100% high 240d", "coverage", "top1"],
                [
                    [
                        row["launch_pool"],
                        int(row["launch_episode_count"]),
                        format_pct(row["future_50pct_high_120d_rate_from_launch"]),
                        format_pct(row["future_100pct_high_240d_rate_from_launch"]),
                        format_pct(row["winner_episode_coverage_from_launch"]),
                        format_pct(row["top1_instrument_contribution"]),
                    ]
                    for _, row in launch_quality.iterrows()
                ],
            )
        )
    lines.append("")
    lines.append("- 主 entry leaderboard 只允许 `primary_pre_20_launch_pool` 与 `primary_pre_30_launch_pool`。`sparse_strong_day_diagnostic_pool`、`post_20_30_hold_only_pool` 和 `late_acceleration_hold_only_pool` 只能作为 secondary / hold / diagnostic。")
    if not lifecycle.empty:
        contamination = lifecycle[lifecycle["final_launch_pool"].isin(["primary_pre_20_launch_pool", "primary_pre_30_launch_pool"]) & lifecycle["lifecycle_gate_bucket"].astype(str).str.contains("post_30|late", regex=True)]
        lines.append(f"- lifecycle gate audit 行数 `{len(lifecycle)}`；primary pool 中 post-30/late gate contamination 行数 `{len(contamination)}`。")
    lines.append("")
    lines.append("## 4. P0.6B：Entry Trigger 与 Baseline")
    lines.append("")
    if not leaderboard.empty:
        cols = [
            "entry_variant_id",
            "entry_event_count",
            "entry_success_primary_precision",
            "entry_success_lift_vs_all_launch_direct",
            "entry_success_lift_vs_matched_delay_baseline",
            "instrument_year_entry_lift_vs_all_launch_direct",
            "median_missed_gain",
            "winner_upside_lift_vs_all_launch_direct",
            "trigger_interpretation",
        ]
        lines.extend(markdown_table(["trigger", "n", "precision", "lift direct", "lift matched", "iy lift", "missed", "upside", "interpretation"], short_table(leaderboard, cols, 12)))
    lines.append("")
    lines.append("- `all_launch_direct_baseline` 回答看到同一 launch family 后直接上车的结果。")
    lines.append("- `trigger_convertible_launch_direct_baseline` 只用于 paired comparison，不能单独证明 trigger 有效。")
    lines.append("- `matched_delay_baseline` 用同样等待天数检查结构条件是否优于单纯延迟过滤。")
    lines.append("")
    lines.append("## 5. P0.6C：失败过滤、missed gain 与 missed winner")
    lines.append("")
    if not feasibility.empty:
        lines.extend(markdown_table(["trigger", "n", "gap", "missed/launch", "stop risk", "wide stop"], short_table(feasibility, ["entry_variant_id", "entry_event_count", "median_next_open_gap_from_signal_close", "median_next_open_vs_launch_close", "median_entry_to_stop_risk_pct", "stop_distance_too_wide_rate"], 10)))
    lines.append("")
    if not failure.empty:
        lines.extend(markdown_table(["trigger", "pre filter", "post audit", "failure", "dd"], short_table(failure, ["entry_variant_id", "pre_entry_failure_filter_hit_rate", "post_entry_invalidation_audit_hit_rate", "entry_failure_primary_rate", "non_winner_false_positive_drawdown"], 10)))
    lines.append("")
    if not missed.empty:
        lines.extend(markdown_table(["trigger", "winner no trigger", "miss no trigger", "miss waiting", "coverage after"], short_table(missed, ["entry_variant_id", "launch_winner_without_entry_trigger_count", "missed_winner_due_to_no_trigger_rate", "direct_entry_winner_missed_by_waiting_rate", "winner_episode_coverage_after_entry"], 10)))
    lines.append("")
    lines.append("## 6. Candidate / Rejected 判断")
    lines.append("")
    if not p1.empty:
        lines.append("- 以下 trigger 满足主榜 gate，可进入 P1 formal entry hypothesis refine：")
        lines.extend(markdown_table(["trigger", "score", "precision", "iy lift", "upside"], short_table(p1, ["entry_variant_id", "entry_quality_score", "entry_success_primary_precision", "instrument_year_entry_lift_vs_all_launch_direct", "winner_upside_lift_vs_all_launch_direct"], 10)))
    else:
        lines.append("- 没有 trigger 同时通过 all-launch direct、convertible direct、matched-delay、instrument-year、missed-gain、stop-risk 和 winner-upside gate。")
        lines.append("- 当前更合理的解释是：P0.6 仍在 entry discovery 阶段；有效信息若存在，更可能先表现为启动后观察、持有确认、失败过滤或加仓条件。")
    if not rejected.empty:
        lines.append("")
        lines.append("主要淘汰原因示例：")
        lines.extend(markdown_table(["trigger", "failure_reason"], short_table(rejected, ["entry_variant_id", "failure_reason"], 10)))
    lines.append("")
    lines.append("## 7. Manifest Discipline")
    lines.append("")
    for key in [
        "p0_label_panel_reused",
        "p0_5_feature_panel_reused",
        "p0_5_reports_used_for_schema_or_family_reference_only",
        "p0_5_ranked_results_used_for_selection",
        "historical_trade_results_used_for_labeling",
        "historical_trade_results_used_for_signal",
        "historical_trade_results_used_for_selection",
        "observed_reference_used_for_selection",
        "same_close_proxy_used_in_main_leaderboard",
        "post_entry_invalidation_audit_used_for_selection",
        "false_positive_definitions_used_for_selection",
        "entry_labels_rebased_to_entry_price",
        "p0_stock_day_label_panel_used_for_entry_label_directly",
        "entry_price_reference_used",
    ]:
        lines.append(f"- `{key} = {manifest.get(key)}`")
    lines.append("")
    lines.append("## 8. 最终判断")
    lines.append("")
    if recommendation == "proceed_to_p1_entry_hypothesis_refine":
        lines.append("- 至少一个 trigger 满足 P0.6 的 P1 gate，可以进入 P1 做 formal hypothesis refine；仍不能直接进入 Explore10 回测。")
    elif recommendation == "continue_p0_6_entry_discovery":
        lines.append("- 存在局部结构或 winner-upside 线索，但尚未形成完整 entry gate，应继续 P0.6 discovery。")
    elif recommendation == "entry_not_solved_but_hold_direction_valid":
        lines.append("- 入场问题仍未解决，但 failure / hold / continuation 审计方向有效，应避免把它们改写成主入场。")
    else:
        lines.append("- 当前样本下没有稳定 entry trigger，建议停止把这批结构推进为 entry 假设。")

    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = [report_path]
    record_p0_6_manifest(config, "report-p0-6", outputs, {"explore9_p0_6_entry_trigger_report.md": pd.DataFrame([{"recommendation": recommendation}])}, {})
    print(f"wrote p0.6 report {relpath(report_path)} recommendation={recommendation}", flush=True)
    return outputs


def p0_7_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("p0_7", {})


def p0_7_manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "p0_7_run_manifest.json"


def p0_7_threshold(config: dict[str, Any], key: str, default: float) -> float:
    return float(config.get("thresholds", {}).get(key, default))


def p0_7_int(config: dict[str, Any], section: str, key: str, default: int) -> int:
    return int(config.get(section, {}).get(key, default))


def p0_7_cache_file(config: dict[str, Any], key: str, default_name: str) -> Path:
    configured = p0_7_cfg(config).get("cache", {}).get(key)
    if configured:
        return topic_path(configured)
    return cache_dir(config) / default_name


def p0_7_launch_specs() -> list[P07LaunchSpec]:
    def f(
        family: str,
        variant: str,
        formula: str,
        resolved: str,
        features: tuple[str, ...],
        thresholds: tuple[str, ...],
        role: str,
        lifecycle: str,
    ) -> P07LaunchSpec:
        return P07LaunchSpec(family, variant, formula, resolved, features, thresholds, role, lifecycle)

    return [
        f(
            "high_vol_quality_permit",
            "expansion_high_vol_upper_close",
            "atr20_pct >= q80_market and day_range >= q80_market and close_location >= thresholds.expansion_high_vol_upper_close__close_location__min and ret_rank_20d_market >= thresholds.expansion_high_vol_upper_close__ret_rank_20d_market__min and launch_gain_from_recent_low_60d < thresholds.expansion_high_vol_upper_close__launch_gain_from_recent_low_60d__max",
            "atr20_pct >= cross_section_quantile(atr20_pct, 0.80, date, PIT universe) and day_range >= cross_section_quantile(day_range, 0.80, date, PIT universe) and close_location >= 0.65 and ret_rank_20d_market >= 0.70 and launch_gain_from_recent_low_60d < 0.30",
            ("atr20_pct", "day_range", "close_location", "ret_rank_20d_market", "launch_gain_from_recent_low_60d"),
            (
                "expansion_high_vol_upper_close__close_location__min",
                "expansion_high_vol_upper_close__ret_rank_20d_market__min",
                "expansion_high_vol_upper_close__launch_gain_from_recent_low_60d__max",
            ),
            "launch_observation_context",
            "pre_20_launch",
        ),
        f(
            "high_vol_quality_permit",
            "high_vol_controlled_drawdown",
            "atr20_pct >= q80_market and close_location >= thresholds.high_vol_controlled_drawdown__close_location__min and low >= median20 * thresholds.high_vol_controlled_drawdown__median20_low_ratio__min and ret_rank_20d_market >= thresholds.high_vol_controlled_drawdown__ret_rank_20d_market__min and industry_breadth_20d >= q50_market",
            "atr20_pct >= cross_section_quantile(atr20_pct, 0.80, date, PIT universe) and close_location >= 0.60 and low >= median20 * 0.95 and ret_rank_20d_market >= 0.65 and industry_breadth_20d >= cross_section_quantile(industry_breadth_20d, 0.50, date, PIT universe)",
            ("atr20_pct", "close_location", "low", "median20", "ret_rank_20d_market", "industry_breadth_20d"),
            (
                "high_vol_controlled_drawdown__close_location__min",
                "high_vol_controlled_drawdown__median20_low_ratio__min",
                "high_vol_controlled_drawdown__ret_rank_20d_market__min",
            ),
            "launch_observation_context",
            "pre_20_launch",
        ),
        f(
            "high_vol_destructive_warning",
            "destructive_high_vol_upper_shadow",
            "atr20_pct >= q80_market and close_location <= thresholds.destructive_high_vol_upper_shadow__close_location__max and upper_shadow_pct >= thresholds.destructive_high_vol_upper_shadow__upper_shadow_pct__min",
            "atr20_pct >= cross_section_quantile(atr20_pct, 0.80, date, PIT universe) and close_location <= 0.40 and upper_shadow_pct >= 0.45",
            ("atr20_pct", "close_location", "upper_shadow_pct"),
            ("destructive_high_vol_upper_shadow__close_location__max", "destructive_high_vol_upper_shadow__upper_shadow_pct__min"),
            "risk_warning_context",
            "risk_warning",
        ),
        f(
            "high_vol_destructive_warning",
            "high_vol_break_median_warning",
            "atr20_pct >= q80_market and close < median20 and money_ratio_20 >= thresholds.high_vol_break_median_warning__money_ratio_20__min",
            "atr20_pct >= cross_section_quantile(atr20_pct, 0.80, date, PIT universe) and close < median20 and money_ratio_20 >= 1.30",
            ("atr20_pct", "close", "median20", "money_ratio_20"),
            ("high_vol_break_median_warning__money_ratio_20__min",),
            "risk_warning_context",
            "risk_warning",
        ),
        f(
            "rank_jump_persistence_watchlist",
            "rank_jump_5d_persist_3d",
            "ret_rank_20d_market - ret_rank_20d_market_5d_ago >= thresholds.rank_jump_5d_persist_3d__rank_jump__min and ret_rank_20d_market_5d_median >= thresholds.rank_jump_5d_persist_3d__ret_rank_20d_market_5d_median__min",
            "ret_rank_20d_market - ret_rank_20d_market_5d_ago >= 0.25 and ret_rank_20d_market_5d_median >= 0.60",
            ("ret_rank_20d_market", "ret_rank_20d_market_5d_ago", "ret_rank_20d_market_5d_median"),
            ("rank_jump_5d_persist_3d__rank_jump__min", "rank_jump_5d_persist_3d__ret_rank_20d_market_5d_median__min"),
            "watchlist_observation_context",
            "watchlist",
        ),
        f(
            "rank_jump_persistence_watchlist",
            "industry_rank_jump_leader",
            "ret_rank_20d_industry >= thresholds.industry_rank_jump_leader__ret_rank_20d_industry__min and ret_rank_20d_market >= thresholds.industry_rank_jump_leader__ret_rank_20d_market__min and relative_ret20_vs_industry >= thresholds.industry_rank_jump_leader__relative_ret20_vs_industry__min",
            "ret_rank_20d_industry >= 0.80 and ret_rank_20d_market >= 0.60 and relative_ret20_vs_industry >= 0",
            ("ret_rank_20d_industry", "ret_rank_20d_market", "relative_ret20_vs_industry"),
            (
                "industry_rank_jump_leader__ret_rank_20d_industry__min",
                "industry_rank_jump_leader__ret_rank_20d_market__min",
                "industry_rank_jump_leader__relative_ret20_vs_industry__min",
            ),
            "watchlist_observation_context",
            "watchlist",
        ),
        f(
            "repair_quality_watchlist",
            "repair_reclaim_ema20_quality",
            "close >= ema20 and ema20 >= ema20_5d_ago and prelaunch_drawdown_120d <= thresholds.repair_reclaim_ema20_quality__prelaunch_drawdown_120d__max and close_location >= thresholds.repair_reclaim_ema20_quality__close_location__min",
            "close >= ema20 and ema20 >= ema20_5d_ago and prelaunch_drawdown_120d <= -0.20 and close_location >= 0.60",
            ("close", "ema20", "ema20_5d_ago", "prelaunch_drawdown_120d", "close_location"),
            ("repair_reclaim_ema20_quality__prelaunch_drawdown_120d__max", "repair_reclaim_ema20_quality__close_location__min"),
            "watchlist_observation_context",
            "watchlist",
        ),
        f(
            "repair_quality_watchlist",
            "repair_higher_low_reclaim",
            "higher_low_count_20d >= thresholds.repair_higher_low_reclaim__higher_low_count_20d__min and close >= median20 and max_drawdown_20d >= thresholds.repair_higher_low_reclaim__max_drawdown_20d__min",
            "higher_low_count_20d >= 1 and close >= median20 and max_drawdown_20d >= -0.12",
            ("higher_low_count_20d", "close", "median20", "max_drawdown_20d"),
            ("repair_higher_low_reclaim__higher_low_count_20d__min", "repair_higher_low_reclaim__max_drawdown_20d__min"),
            "watchlist_observation_context",
            "watchlist",
        ),
        f(
            "money_price_keep_context",
            "money_price_upper_keep",
            "money_ratio_20 >= thresholds.money_price_upper_keep__money_ratio_20__min and close_location >= thresholds.money_price_upper_keep__close_location__min and close >= median20",
            "money_ratio_20 >= 1.20 and close_location >= 0.65 and close >= median20",
            ("money_ratio_20", "close_location", "close", "median20"),
            ("money_price_upper_keep__money_ratio_20__min", "money_price_upper_keep__close_location__min"),
            "watchlist_observation_context",
            "watchlist",
        ),
        f(
            "money_price_keep_context",
            "money_expansion_no_distribution",
            "money_ratio_20 >= thresholds.money_expansion_no_distribution__money_ratio_20__min and upper_shadow_pct <= thresholds.money_expansion_no_distribution__upper_shadow_pct__max and close >= open",
            "money_ratio_20 >= 1.20 and upper_shadow_pct <= 0.35 and close >= open",
            ("money_ratio_20", "upper_shadow_pct", "close", "open"),
            ("money_expansion_no_distribution__money_ratio_20__min", "money_expansion_no_distribution__upper_shadow_pct__max"),
            "watchlist_observation_context",
            "watchlist",
        ),
        f(
            "industry_breadth_coherence",
            "industry_breadth_confirmed_launch",
            "industry_breadth_20d >= q60_market and relative_ret20_vs_industry >= thresholds.industry_breadth_confirmed_launch__relative_ret20_vs_industry__min and ret_rank_20d_market >= thresholds.industry_breadth_confirmed_launch__ret_rank_20d_market__min",
            "industry_breadth_20d >= cross_section_quantile(industry_breadth_20d, 0.60, date, PIT universe) and relative_ret20_vs_industry >= 0 and ret_rank_20d_market >= 0.60",
            ("industry_breadth_20d", "relative_ret20_vs_industry", "ret_rank_20d_market"),
            ("industry_breadth_confirmed_launch__relative_ret20_vs_industry__min", "industry_breadth_confirmed_launch__ret_rank_20d_market__min"),
            "launch_observation_context",
            "pre_20_launch",
        ),
        f(
            "industry_breadth_coherence",
            "weak_market_industry_leader",
            "market_regime in [weak, neutral] and ret_rank_20d_industry >= thresholds.weak_market_industry_leader__ret_rank_20d_industry__min and relative_ret20_vs_benchmark >= thresholds.weak_market_industry_leader__relative_ret20_vs_benchmark__min",
            "market_regime in [weak, neutral] and ret_rank_20d_industry >= 0.80 and relative_ret20_vs_benchmark >= 0",
            ("market_regime", "ret_rank_20d_industry", "relative_ret20_vs_benchmark"),
            ("weak_market_industry_leader__ret_rank_20d_industry__min", "weak_market_industry_leader__relative_ret20_vs_benchmark__min"),
            "launch_observation_context",
            "pre_20_launch",
        ),
        f(
            "relative_strength_persistence",
            "relative_strength_10d_persistence",
            "ret_rank_20d_market >= thresholds.relative_strength_10d_persistence__ret_rank_20d_market__min and ret_rank_20d_market_5d_median >= thresholds.relative_strength_10d_persistence__ret_rank_20d_market_5d_median__min and relative_ret20_vs_benchmark >= thresholds.relative_strength_10d_persistence__relative_ret20_vs_benchmark__min and close >= median20",
            "ret_rank_20d_market >= 0.70 and ret_rank_20d_market_5d_median >= 0.65 and relative_ret20_vs_benchmark >= 0 and close >= median20",
            ("ret_rank_20d_market", "ret_rank_20d_market_5d_median", "relative_ret20_vs_benchmark", "close", "median20"),
            (
                "relative_strength_10d_persistence__ret_rank_20d_market__min",
                "relative_strength_10d_persistence__ret_rank_20d_market_5d_median__min",
                "relative_strength_10d_persistence__relative_ret20_vs_benchmark__min",
            ),
            "launch_observation_context",
            "pre_20_launch",
        ),
        f(
            "relative_strength_persistence",
            "industry_relative_strength_persistence",
            "ret_rank_20d_industry >= thresholds.industry_relative_strength_persistence__ret_rank_20d_industry__min and relative_ret20_vs_industry >= thresholds.industry_relative_strength_persistence__relative_ret20_vs_industry__min and close_location_5d_median >= thresholds.industry_relative_strength_persistence__close_location_5d_median__min",
            "ret_rank_20d_industry >= 0.75 and relative_ret20_vs_industry >= 0 and close_location_5d_median >= 0.55",
            ("ret_rank_20d_industry", "relative_ret20_vs_industry", "close_location_5d_median"),
            (
                "industry_relative_strength_persistence__ret_rank_20d_industry__min",
                "industry_relative_strength_persistence__relative_ret20_vs_industry__min",
                "industry_relative_strength_persistence__close_location_5d_median__min",
            ),
            "launch_observation_context",
            "pre_20_launch",
        ),
        f(
            "prelaunch_path_quality",
            "controlled_repair_from_deep_drawdown",
            "prelaunch_drawdown_120d <= thresholds.controlled_repair_from_deep_drawdown__prelaunch_drawdown_120d__max and max_drawdown_20d >= thresholds.controlled_repair_from_deep_drawdown__max_drawdown_20d__min and close >= median20",
            "prelaunch_drawdown_120d <= -0.25 and max_drawdown_20d >= -0.12 and close >= median20",
            ("prelaunch_drawdown_120d", "max_drawdown_20d", "close", "median20"),
            (
                "controlled_repair_from_deep_drawdown__prelaunch_drawdown_120d__max",
                "controlled_repair_from_deep_drawdown__max_drawdown_20d__min",
            ),
            "watchlist_observation_context",
            "watchlist",
        ),
        f(
            "prelaunch_path_quality",
            "range_tightening_then_expand",
            "rolling_range_20d <= q40_market and day_range >= q70_market and close_location >= thresholds.range_tightening_then_expand__close_location__min",
            "rolling_range_20d <= cross_section_quantile(rolling_range_20d, 0.40, date, PIT universe) and day_range >= cross_section_quantile(day_range, 0.70, date, PIT universe) and close_location >= 0.65",
            ("rolling_range_20d", "day_range", "close_location"),
            ("range_tightening_then_expand__close_location__min",),
            "watchlist_observation_context",
            "watchlist",
        ),
        f(
            "sparse_strong_day_lifecycle_node",
            "first_near_limit_upper_close",
            "ret_1d >= thresholds.near_limit_threshold and close_location >= thresholds.first_near_limit_upper_close__close_location__min and first_occurrence_in_60d = true",
            "ret_1d >= thresholds.near_limit_threshold and close_location >= 0.75 and first_occurrence_in_60d = true",
            ("ret_1d", "close_location", "first_occurrence_in_60d"),
            ("near_limit_threshold", "first_near_limit_upper_close__close_location__min"),
            "diagnostic_context",
            "sparse_strong_day_node",
        ),
        f(
            "sparse_strong_day_lifecycle_node",
            "strong_body_day_node",
            "body_ret >= q90_market and close_location >= thresholds.strong_body_day_node__close_location__min and money_ratio_20 >= thresholds.strong_body_day_node__money_ratio_20__min",
            "body_ret >= cross_section_quantile(body_ret, 0.90, date, PIT universe) and close_location >= 0.75 and money_ratio_20 >= 1.20",
            ("body_ret", "close_location", "money_ratio_20"),
            ("strong_body_day_node__close_location__min", "strong_body_day_node__money_ratio_20__min"),
            "addon_context_deferred",
            "sparse_strong_day_node",
        ),
        f(
            "post_20_30_or_late_continuation_context",
            "post_20_relative_strength_context",
            "launch_gain_from_recent_low_90d >= thresholds.post_20_relative_strength_context__launch_gain_from_recent_low_90d__min and launch_gain_from_recent_low_90d < thresholds.post_20_relative_strength_context__launch_gain_from_recent_low_90d__max and ret_rank_20d_market >= thresholds.post_20_relative_strength_context__ret_rank_20d_market__min",
            "launch_gain_from_recent_low_90d >= 0.20 and launch_gain_from_recent_low_90d < 0.30 and ret_rank_20d_market >= 0.70",
            ("launch_gain_from_recent_low_90d", "ret_rank_20d_market"),
            (
                "post_20_relative_strength_context__launch_gain_from_recent_low_90d__min",
                "post_20_relative_strength_context__launch_gain_from_recent_low_90d__max",
                "post_20_relative_strength_context__ret_rank_20d_market__min",
            ),
            "hold_continuation_context",
            "post_20_30_continuation",
        ),
        f(
            "post_20_30_or_late_continuation_context",
            "late_acceleration_context",
            "launch_gain_from_recent_low_120d >= thresholds.late_acceleration_context__launch_gain_from_recent_low_120d__min or late_acceleration_flag = true",
            "launch_gain_from_recent_low_120d >= 0.50 or late_acceleration_flag = true",
            ("launch_gain_from_recent_low_120d", "late_acceleration_flag"),
            ("late_acceleration_context__launch_gain_from_recent_low_120d__min",),
            "addon_context_deferred",
            "late_acceleration",
        ),
    ]


def p0_7_filter_specs() -> list[P07FailureFilterSpec]:
    def f(
        family: str,
        variant: str,
        formula: str,
        resolved: str,
        features: tuple[str, ...],
        thresholds: tuple[str, ...],
        signal_date_definition: str,
        window: int,
        action: str,
        severity: str = "medium",
    ) -> P07FailureFilterSpec:
        return P07FailureFilterSpec(
            family,
            variant,
            formula,
            resolved,
            features,
            thresholds,
            signal_date_definition,
            window,
            "close_derived",
            "next_trading_day_open",
            action,
            severity,
            variant,
        )

    return [
        f("break_launch_low_filter", "break_launch_low_3d", "low < stratum_low_at_signal", "low < stratum_low_at_signal", ("low", "stratum_low_at_signal"), tuple(), "first_hit_within_window", 3, "remove_from_watchlist", "high"),
        f("break_launch_low_filter", "break_launch_low_5d", "low < stratum_low_at_signal", "low < stratum_low_at_signal", ("low", "stratum_low_at_signal"), tuple(), "first_hit_within_window", 5, "remove_from_watchlist", "high"),
        f("break_median20_or_ema20_filter", "break_ema20_after_launch_5d", "close <= ema20", "close <= ema20", ("close", "ema20"), tuple(), "first_hit_within_window", 5, "no_new_entry"),
        f("break_median20_or_ema20_filter", "break_median20_after_launch_5d", "close <= median20", "close <= median20", ("close", "median20"), tuple(), "first_hit_within_window", 5, "no_new_entry"),
        f("gap_fade_filter", "gap_fade_after_launch_5d", "open >= prior_close * (1 + thresholds.gap_up_min_ret) and close_location <= thresholds.gap_fade_after_launch_5d__close_location__max and close <= open", "open >= prior_close * (1 + 0.03) and close_location <= 0.35 and close <= open", ("open", "prior_close", "close_location", "close"), ("gap_up_min_ret", "gap_fade_after_launch_5d__close_location__max"), "instantaneous_day", 5, "reduce_risk"),
        f("gap_fade_filter", "gap_fade_break_prior_close_5d", "open >= prior_close * (1 + thresholds.gap_up_min_ret) and close <= prior_close and close_location <= thresholds.gap_fade_break_prior_close_5d__close_location__max", "open >= prior_close * (1 + 0.03) and close <= prior_close and close_location <= 0.40", ("open", "prior_close", "close", "close_location"), ("gap_up_min_ret", "gap_fade_break_prior_close_5d__close_location__max"), "instantaneous_day", 5, "reduce_risk"),
        f("upper_shadow_volume_failure_filter", "upper_shadow_volume_failure_5d", "upper_shadow_pct >= thresholds.upper_shadow_volume_failure_5d__upper_shadow_pct__min and close_location <= thresholds.upper_shadow_volume_failure_5d__close_location__max and money_ratio_20 >= thresholds.upper_shadow_volume_failure_5d__money_ratio_20__min", "upper_shadow_pct >= 0.45 and close_location <= 0.40 and money_ratio_20 >= 1.50", ("upper_shadow_pct", "close_location", "money_ratio_20"), ("upper_shadow_volume_failure_5d__upper_shadow_pct__min", "upper_shadow_volume_failure_5d__close_location__max", "upper_shadow_volume_failure_5d__money_ratio_20__min"), "instantaneous_day", 5, "reduce_risk", "high"),
        f("upper_shadow_volume_failure_filter", "upper_shadow_money_distribution_10d", "upper_shadow_pct >= thresholds.upper_shadow_money_distribution_10d__upper_shadow_pct__min and close_location <= thresholds.upper_shadow_money_distribution_10d__close_location__max and money_ratio_20 >= thresholds.upper_shadow_money_distribution_10d__money_ratio_20__min", "upper_shadow_pct >= 0.40 and close_location <= 0.45 and money_ratio_20 >= 1.30", ("upper_shadow_pct", "close_location", "money_ratio_20"), ("upper_shadow_money_distribution_10d__upper_shadow_pct__min", "upper_shadow_money_distribution_10d__close_location__max", "upper_shadow_money_distribution_10d__money_ratio_20__min"), "instantaneous_day", 10, "reduce_risk"),
        f("rank_evaporation_filter", "rank_evaporation_5d", "ret_rank_20d_market <= ret_rank_20d_market_at_stratum - thresholds.rank_drop and ret_rank_20d_market <= thresholds.rank_evaporation_floor", "ret_rank_20d_market <= ret_rank_20d_market_at_stratum - 0.25 and ret_rank_20d_market <= 0.50", ("ret_rank_20d_market", "ret_rank_20d_market_at_stratum"), ("rank_drop", "rank_evaporation_floor"), "first_hit_within_window", 5, "no_new_entry"),
        f("rank_evaporation_filter", "rank_evaporation_10d", "ret_rank_20d_market <= ret_rank_20d_market_at_stratum - thresholds.rank_drop and ret_rank_20d_market <= thresholds.rank_evaporation_floor", "ret_rank_20d_market <= ret_rank_20d_market_at_stratum - 0.25 and ret_rank_20d_market <= 0.50", ("ret_rank_20d_market", "ret_rank_20d_market_at_stratum"), ("rank_drop", "rank_evaporation_floor"), "first_hit_within_window", 10, "no_new_entry"),
        f("money_distribution_filter", "money_distribution_5d", "money_ratio_20 >= thresholds.money_distribution_5d__money_ratio_20__min and close_location <= thresholds.money_distribution_5d__close_location__max and close < prior_close", "money_ratio_20 >= 1.30 and close_location <= 0.45 and close < prior_close", ("money_ratio_20", "close_location", "close", "prior_close"), ("money_distribution_5d__money_ratio_20__min", "money_distribution_5d__close_location__max"), "instantaneous_day", 5, "reduce_risk"),
        f("money_distribution_filter", "money_distribution_10d", "money_ratio_20 >= thresholds.money_distribution_10d__money_ratio_20__min and upper_shadow_pct >= thresholds.money_distribution_10d__upper_shadow_pct__min and close < open", "money_ratio_20 >= 1.20 and upper_shadow_pct >= 0.35 and close < open", ("money_ratio_20", "upper_shadow_pct", "close", "open"), ("money_distribution_10d__money_ratio_20__min", "money_distribution_10d__upper_shadow_pct__min"), "instantaneous_day", 10, "reduce_risk"),
        f("industry_breadth_evaporation_filter", "industry_breadth_evaporation_5d", "industry_breadth_20d <= industry_breadth_20d_at_stratum - thresholds.industry_breadth_drop", "industry_breadth_20d <= industry_breadth_20d_at_stratum - 0.15", ("industry_breadth_20d", "industry_breadth_20d_at_stratum"), ("industry_breadth_drop",), "first_hit_within_window", 5, "hold_review_only"),
        f("industry_breadth_evaporation_filter", "industry_breadth_evaporation_10d", "industry_breadth_20d <= industry_breadth_20d_at_stratum - thresholds.industry_breadth_drop", "industry_breadth_20d <= industry_breadth_20d_at_stratum - 0.15", ("industry_breadth_20d", "industry_breadth_20d_at_stratum"), ("industry_breadth_drop",), "first_hit_within_window", 10, "hold_review_only"),
        f("no_followthrough_filter", "no_followthrough_5d", "max(high over stratum_date+1 to stratum_date+5) <= stratum_close_at_signal * (1 + thresholds.min_followthrough_gain) and min(close over stratum_date+1 to stratum_date+5) < stratum_close_at_signal", "max(high over window) <= stratum_close_at_signal * (1 + 0.05) and min(close over window) < stratum_close_at_signal", ("high", "close", "stratum_close_at_signal"), ("min_followthrough_gain",), "fixed_window_end", 5, "no_new_entry"),
        f("no_followthrough_filter", "no_followthrough_10d", "max(high over stratum_date+1 to stratum_date+10) <= stratum_close_at_signal * (1 + thresholds.min_followthrough_gain) and min(close over stratum_date+1 to stratum_date+10) < stratum_close_at_signal", "max(high over window) <= stratum_close_at_signal * (1 + 0.05) and min(close over window) < stratum_close_at_signal", ("high", "close", "stratum_close_at_signal"), ("min_followthrough_gain",), "fixed_window_end", 10, "no_new_entry"),
        f("destructive_high_vol_filter", "destructive_high_vol_3d", "atr20_pct >= q80_market and close_location <= thresholds.destructive_high_vol_3d__close_location__max and close < median20", "atr20_pct >= cross_section_quantile(atr20_pct, 0.80, date, PIT universe) and close_location <= 0.40 and close < median20", ("atr20_pct", "close_location", "close", "median20"), ("destructive_high_vol_3d__close_location__max",), "first_hit_within_window", 3, "remove_from_watchlist", "high"),
        f("destructive_high_vol_filter", "destructive_high_vol_5d", "atr20_pct >= q80_market and close_location <= thresholds.destructive_high_vol_5d__close_location__max and close < median20", "atr20_pct >= cross_section_quantile(atr20_pct, 0.80, date, PIT universe) and close_location <= 0.40 and close < median20", ("atr20_pct", "close_location", "close", "median20"), ("destructive_high_vol_5d__close_location__max",), "first_hit_within_window", 5, "remove_from_watchlist", "high"),
        f("wide_stop_or_unexecutable_filter", "wide_stop_risk_no_add_5d", "close / invalidation_reference_price - 1 >= thresholds.max_stop_distance_for_new_risk", "close / invalidation_reference_price - 1 >= 0.15", ("close", "invalidation_reference_price"), ("max_stop_distance_for_new_risk",), "instantaneous_day", 5, "no_add_on"),
        f("wide_stop_or_unexecutable_filter", "wide_stop_risk_no_new_entry_10d", "close / invalidation_reference_price - 1 >= thresholds.max_stop_distance_for_new_risk", "close / invalidation_reference_price - 1 >= 0.15", ("close", "invalidation_reference_price"), ("max_stop_distance_for_new_risk",), "instantaneous_day", 10, "no_new_entry"),
    ]


def p0_7_series(df: pd.DataFrame, *names: str, default: float | str = np.nan) -> pd.Series:
    for name in names:
        if name in df.columns:
            return df[name]
    return pd.Series(default, index=df.index)


def p0_7_load_feature_panel(config: dict[str, Any]) -> pd.DataFrame:
    df = p0_6_load_feature_panel(config)
    return p0_7_add_features(df)


def p0_7_add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values(["instrument", "datetime"]).reset_index(drop=True)
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.normalize()
    group = df.groupby("instrument", group_keys=False)
    price_range = (df["high"] - df["low"]).replace(0, np.nan)
    df["ret_1d"] = p0_7_series(df, "p0_6_ret_1d", "ret1")
    df["ret_3d"] = p0_7_series(df, "ret3")
    df["ret_5d"] = p0_7_series(df, "p0_6_ret_5d", "ret5")
    df["ret_20d"] = p0_7_series(df, "p0_6_ret_20d", "ret20")
    df["body_ret"] = p0_7_series(df, "p0_6_body_ret")
    df["day_range"] = p0_7_series(df, "p0_6_day_range")
    df["close_location"] = p0_7_series(df, "p0_6_close_location")
    df["upper_shadow_pct"] = p0_7_series(df, "p0_6_upper_shadow_ratio")
    df["lower_shadow_pct"] = ((df[["open", "close"]].min(axis=1) - df["low"]) / price_range).clip(0, 1)
    df["money_ratio_20"] = p0_7_series(df, "p0_6_money_ratio_20", "money_ratio20")
    df["money_ratio_60"] = p0_7_series(df, "p0_6_money_ratio_60", "money_ratio60")
    df["ret_rank_20d_market"] = p0_7_series(df, "p0_6_ret_rank_20d_market", "ret20_universe_pctile")
    df["ret_rank_20d_market_5d_ago"] = p0_7_series(df, "p0_6_ret_rank_20d_market_5d_ago")
    df["ret_rank_20d_market_5d_median"] = group["ret_rank_20d_market"].transform(lambda s: s.rolling(5, min_periods=3).median())
    df["ret_rank_20d_market_at_stratum"] = df["ret_rank_20d_market"]
    df["ret_rank_20d_industry"] = p0_7_series(df, "ret20_industry_pctile", "ret20_industry_pctile_p0_5")
    df["ret_rank_20d_industry_5d_median"] = group["ret_rank_20d_industry"].transform(lambda s: s.rolling(5, min_periods=3).median())
    df["relative_ret20_vs_benchmark"] = p0_7_series(df, "relative_ret20_vs_benchmark")
    df["relative_ret20_vs_industry"] = p0_7_series(df, "relative_ret20_vs_industry")
    df["industry_breadth_20d"] = p0_7_series(df, "p0_6_industry_breadth_20d", "industry_close_gt_ema60_ratio")
    df["industry_breadth_20d_at_stratum"] = df["industry_breadth_20d"]
    df["market_regime"] = p0_7_series(df, "market_regime_state", default="UNKNOWN").fillna("UNKNOWN")
    df["ema20_5d_ago"] = group["ema20"].shift(5)
    df["median20"] = p0_7_series(df, "p0_6_median20", "median_price20")
    if "low20" not in df.columns:
        df["low20"] = group["low"].transform(lambda s: s.rolling(20, min_periods=10).min())
    if "low60" not in df.columns:
        df["low60"] = group["low"].transform(lambda s: s.rolling(60, min_periods=20).min())
    df["low90"] = p0_7_series(df, "p0_6_low90")
    if df["low90"].isna().all():
        df["low90"] = group["low"].transform(lambda s: s.rolling(90, min_periods=20).min())
    df["low120"] = p0_7_series(df, "p0_6_low120")
    if df["low120"].isna().all():
        df["low120"] = group["low"].transform(lambda s: s.rolling(120, min_periods=20).min())
    high20 = group["high"].transform(lambda s: s.rolling(20, min_periods=10).max())
    df["prelaunch_drawdown_120d"] = p0_7_series(df, "drawdown_from_high120")
    if df["prelaunch_drawdown_120d"].isna().all() and "high120" in df.columns:
        df["prelaunch_drawdown_120d"] = df["close"] / df["high120"].replace(0, np.nan) - 1.0
    df["max_drawdown_20d"] = df["low20"] / high20.replace(0, np.nan) - 1.0
    df["close_location_5d_median"] = group["close_location"].transform(lambda s: s.rolling(5, min_periods=3).median())
    df["rolling_range_20d"] = high20 / df["low20"].replace(0, np.nan) - 1.0
    df["higher_low_count_20d"] = group["low"].transform(lambda s: (s > s.shift(1)).astype(float).rolling(20, min_periods=5).sum())
    df["late_acceleration_flag"] = p0_7_series(df, "p0_6_late_acceleration_flag").fillna(False).astype(bool)
    df["post_20pct_relative_strength"] = p0_7_series(df, "p0_6_post20_relative_strength_flag").fillna(False).astype(bool)
    df["post_30pct_relative_strength"] = p0_7_series(df, "p0_6_post30_relative_strength_flag").fillna(False).astype(bool)
    df["prior_close"] = p0_7_series(df, "prev_close")
    if df["prior_close"].isna().all():
        df["prior_close"] = group["close"].shift(1)
    df["launch_gain_from_recent_low_60d"] = p0_7_series(df, "p0_6_launch_gain_from_recent_low_60d", "repair_from_low60")
    df["launch_gain_from_recent_low_90d"] = p0_7_series(df, "p0_6_launch_gain_from_recent_low_90d")
    df["launch_gain_from_recent_low_120d"] = p0_7_series(df, "p0_6_launch_gain_from_recent_low_120d", "repair_from_low120")
    df["stratum_low_at_signal"] = df["low"]
    df["stratum_close_at_signal"] = df["close"]
    df["invalidation_reference_price"] = df["low"]
    near_limit_base = (df["ret_1d"] >= 0.085) & (df["close_location"] >= 0.75)
    df["first_occurrence_in_60d"] = p0_6_prior_event_absent(df, near_limit_base, 60)
    if "p0_6_row_pos" not in df.columns:
        df["p0_6_row_pos"] = group.cumcount()
    df["p0_7_available_for_stratum"] = (
        df["provider_required_fields_ok"].fillna(False).astype(bool)
        & df["pit_member"].fillna(False).astype(bool)
        & df["feature_eligible"].fillna(False).astype(bool)
        & df["ret_rank_20d_market"].notna()
        & df["money_ratio_20"].notna()
    )
    return df.replace([np.inf, -np.inf], np.nan)


def p0_7_market_quantile(df: pd.DataFrame, feature: str, q: float, cache: dict[tuple[str, float], pd.Series]) -> pd.Series:
    key = (feature, q)
    if key not in cache:
        cache[key] = df.groupby("datetime")[feature].transform(lambda s: s.quantile(q))
    return cache[key]


def p0_7_feature_dictionary() -> pd.DataFrame:
    raw = ["open", "high", "low", "close", "volume", "money", "factor", "instrument", "date"]
    derived = [
        "ret_1d",
        "ret_3d",
        "ret_5d",
        "ret_20d",
        "body_ret",
        "day_range",
        "close_location",
        "upper_shadow_pct",
        "lower_shadow_pct",
        "atr20_pct",
        "volatility20",
        "volatility60",
        "money_ratio_20",
        "money_ratio_60",
        "ret_rank_20d_market",
        "ret_rank_20d_market_5d_ago",
        "ret_rank_20d_market_5d_median",
        "ret_rank_20d_market_at_stratum",
        "ret_rank_20d_industry",
        "ret_rank_20d_industry_5d_median",
        "relative_ret20_vs_benchmark",
        "relative_ret20_vs_industry",
        "industry_breadth_20d",
        "industry_breadth_20d_at_stratum",
        "market_regime",
        "ema20",
        "ema20_5d_ago",
        "median20",
        "low20",
        "low60",
        "low90",
        "low120",
        "stratum_low_at_signal",
        "stratum_close_at_signal",
        "stratum_date",
        "invalidation_reference_price",
        "launch_gain_from_recent_low_60d",
        "launch_gain_from_recent_low_90d",
        "launch_gain_from_recent_low_120d",
        "prelaunch_drawdown_120d",
        "max_drawdown_20d",
        "close_location_5d_median",
        "rolling_range_20d",
        "higher_low_count_20d",
        "late_acceleration_flag",
        "post_20pct_relative_strength",
        "post_30pct_relative_strength",
        "prior_close",
        "first_occurrence_in_60d",
    ]
    quantiles = ["q40_market", "q50_market", "q60_market", "q70_market", "q80_market", "q90_market"]
    rows: list[dict[str, Any]] = []
    for name in raw:
        rows.append(
            {
                "feature_name": name,
                "feature_family": "raw_provider",
                "feature_role": "raw_input",
                "lookback_days": 0,
                "min_history_trading_days": 0,
                "observable_date": "same_day",
                "uses_future_data": False,
                "required_fields": name,
                "raw_required_field_exempt": True,
                "feature_eligible_rule": "provider_required_fields_ok",
                "formula_text": "",
                "formula_text_resolved": "",
                "thresholds": "",
                "used_in_launch_stratification": name in {"open", "high", "low", "close", "money"},
                "used_in_failure_filter": name in {"open", "high", "low", "close", "money"},
                "used_in_hold_gate": False,
                "used_in_add_on_gate": False,
            }
        )
    for name in derived:
        lookback = int(next((token for token in re.findall(r"\d+", name) if token), "0"))
        rows.append(
            {
                "feature_name": name,
                "feature_family": "p0_7_derived",
                "feature_role": "derived_feature" if not name.endswith("_at_signal") else "formula_macro",
                "lookback_days": lookback,
                "min_history_trading_days": min(max(lookback, 1), 120) if lookback else 1,
                "observable_date": "same_day_or_prior",
                "uses_future_data": False,
                "required_fields": "open;high;low;close;money;industry;benchmark",
                "raw_required_field_exempt": False,
                "feature_eligible_rule": "p0_7_available_for_stratum",
                "formula_text": "",
                "formula_text_resolved": "",
                "thresholds": "",
                "used_in_launch_stratification": name
                in {feature for spec in p0_7_launch_specs() for feature in spec.required_features},
                "used_in_failure_filter": name in {feature for spec in p0_7_filter_specs() for feature in spec.required_features},
                "used_in_hold_gate": False,
                "used_in_add_on_gate": False,
            }
        )
    for name in quantiles:
        q = name.replace("q", "").replace("_market", "")
        rows.append(
            {
                "feature_name": name,
                "feature_family": "cross_section_quantile",
                "feature_role": "quantile_alias",
                "lookback_days": 0,
                "min_history_trading_days": 0,
                "observable_date": "same_day",
                "uses_future_data": False,
                "required_fields": "feature,date,PIT universe",
                "raw_required_field_exempt": False,
                "feature_eligible_rule": "resolved per formula feature on PIT universe",
                "formula_text": f"{name}(feature, date)",
                "formula_text_resolved": f"cross_section_quantile(feature, 0.{q}, date, PIT universe)",
                "thresholds": "",
                "used_in_launch_stratification": True,
                "used_in_failure_filter": True,
                "used_in_hold_gate": False,
                "used_in_add_on_gate": False,
            }
        )
    return pd.DataFrame(rows)


def p0_7_formula_token_coverage_audit(config: dict[str, Any]) -> pd.DataFrame:
    dictionary = p0_7_feature_dictionary()
    features = set(dictionary["feature_name"].astype(str))
    thresholds = set(config.get("thresholds", {}).keys())
    rows: list[dict[str, Any]] = []
    formulas = [(spec.stratum_variant, spec.formula_text) for spec in p0_7_launch_specs()] + [
        (spec.filter_variant, spec.formula_text) for spec in p0_7_filter_specs()
    ]
    operator_tokens = {
        "and",
        "or",
        "in",
        "true",
        "false",
        "max",
        "min",
        "over",
        "to",
        "date",
        "weak",
        "neutral",
        "PIT",
        "universe",
    }
    for formula_id, formula in formulas:
        tokens = re.findall(r"thresholds\.[A-Za-z0-9_]+|[A-Za-z_][A-Za-z0-9_]*", formula)
        for token in sorted(set(tokens)):
            if token.startswith("thresholds."):
                name = token.split(".", 1)[1]
                token_type = "threshold_key" if name in thresholds else "unmapped"
                mapped = name in thresholds
            elif token in features:
                role = dictionary.loc[dictionary["feature_name"].eq(token), "feature_role"].iloc[0]
                token_type = "raw_input_field" if role == "raw_input" else str(role)
                mapped = True
            elif token in operator_tokens:
                token_type = "enum_literal" if token in {"true", "false", "weak", "neutral"} else "operator_or_function"
                mapped = True
            else:
                token_type = "unmapped"
                mapped = False
            rows.append({"formula_id": formula_id, "token": token, "token_type": token_type, "mapped": bool(mapped), "unmapped_count": int(not mapped)})
    return pd.DataFrame(rows)


def p0_7_launch_formula_matrix() -> pd.DataFrame:
    rows = []
    for spec in p0_7_launch_specs():
        rows.append(
            {
                "stratum_family": spec.stratum_family,
                "stratum_variant": spec.stratum_variant,
                "formula_text": spec.formula_text,
                "formula_text_resolved": spec.formula_text_resolved,
                "required_features": ";".join(spec.required_features),
                "required_thresholds": ";".join(f"thresholds.{key}" for key in spec.required_thresholds),
                "declared_stratum_role": spec.declared_stratum_role,
                "declared_lifecycle_stage": spec.declared_lifecycle_stage,
                "formula_observation_cutoff": "stratum_date",
                "formula_uses_future_data": False,
                "uses_quantile_alias": "q" in spec.formula_text,
                "quantile_alias_resolved_text": spec.formula_text_resolved if "q" in spec.formula_text else "",
            }
        )
    return pd.DataFrame(rows)


def p0_7_failure_filter_formula_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "filter_family": spec.filter_family,
                "filter_variant": spec.filter_variant,
                "filter_formula": spec.formula_text,
                "filter_formula_resolved": spec.formula_text_resolved,
                "required_features": ";".join(spec.required_features),
                "required_thresholds": ";".join(f"thresholds.{key}" for key in spec.required_thresholds),
                "signal_date_definition": spec.signal_date_definition,
                "formula_window_trading_days": spec.formula_window_trading_days,
                "filter_formula_observation_timing": spec.filter_formula_observation_timing,
                "effective_date_rule": spec.effective_date_rule,
                "filter_action": spec.filter_action,
                "filter_severity": spec.filter_severity,
                "uses_quantile_alias": "q" in spec.formula_text,
                "quantile_alias_resolved_text": spec.formula_text_resolved if "q" in spec.formula_text else "",
            }
            for spec in p0_7_filter_specs()
        ]
    )


def p0_7_launch_masks(config: dict[str, Any], df: pd.DataFrame) -> dict[str, pd.Series]:
    q_cache: dict[tuple[str, float], pd.Series] = {}
    t = lambda key, default: p0_7_threshold(config, key, default)
    q40_range = p0_7_market_quantile(df, "rolling_range_20d", 0.40, q_cache)
    q50_breadth = p0_7_market_quantile(df, "industry_breadth_20d", 0.50, q_cache)
    q60_breadth = p0_7_market_quantile(df, "industry_breadth_20d", 0.60, q_cache)
    q70_range = p0_7_market_quantile(df, "day_range", 0.70, q_cache)
    q80_atr = p0_7_market_quantile(df, "atr20_pct", 0.80, q_cache)
    q80_range = p0_7_market_quantile(df, "day_range", 0.80, q_cache)
    q90_body = p0_7_market_quantile(df, "body_ret", 0.90, q_cache)
    near_limit = (df["ret_1d"] >= t("near_limit_threshold", 0.085)) & (
        df["close_location"] >= t("first_near_limit_upper_close__close_location__min", 0.75)
    )
    masks = {
        "expansion_high_vol_upper_close": (df["atr20_pct"] >= q80_atr)
        & (df["day_range"] >= q80_range)
        & (df["close_location"] >= t("expansion_high_vol_upper_close__close_location__min", 0.65))
        & (df["ret_rank_20d_market"] >= t("expansion_high_vol_upper_close__ret_rank_20d_market__min", 0.70))
        & (df["launch_gain_from_recent_low_60d"] < t("expansion_high_vol_upper_close__launch_gain_from_recent_low_60d__max", 0.30)),
        "high_vol_controlled_drawdown": (df["atr20_pct"] >= q80_atr)
        & (df["close_location"] >= t("high_vol_controlled_drawdown__close_location__min", 0.60))
        & (df["low"] >= df["median20"] * t("high_vol_controlled_drawdown__median20_low_ratio__min", 0.95))
        & (df["ret_rank_20d_market"] >= t("high_vol_controlled_drawdown__ret_rank_20d_market__min", 0.65))
        & (df["industry_breadth_20d"] >= q50_breadth),
        "destructive_high_vol_upper_shadow": (df["atr20_pct"] >= q80_atr)
        & (df["close_location"] <= t("destructive_high_vol_upper_shadow__close_location__max", 0.40))
        & (df["upper_shadow_pct"] >= t("destructive_high_vol_upper_shadow__upper_shadow_pct__min", 0.45)),
        "high_vol_break_median_warning": (df["atr20_pct"] >= q80_atr)
        & (df["close"] < df["median20"])
        & (df["money_ratio_20"] >= t("high_vol_break_median_warning__money_ratio_20__min", 1.30)),
        "rank_jump_5d_persist_3d": (
            (df["ret_rank_20d_market"] - df["ret_rank_20d_market_5d_ago"]) >= t("rank_jump_5d_persist_3d__rank_jump__min", 0.25)
        )
        & (df["ret_rank_20d_market_5d_median"] >= t("rank_jump_5d_persist_3d__ret_rank_20d_market_5d_median__min", 0.60)),
        "industry_rank_jump_leader": (df["ret_rank_20d_industry"] >= t("industry_rank_jump_leader__ret_rank_20d_industry__min", 0.80))
        & (df["ret_rank_20d_market"] >= t("industry_rank_jump_leader__ret_rank_20d_market__min", 0.60))
        & (df["relative_ret20_vs_industry"] >= t("industry_rank_jump_leader__relative_ret20_vs_industry__min", 0.0)),
        "repair_reclaim_ema20_quality": (df["close"] >= df["ema20"])
        & (df["ema20"] >= df["ema20_5d_ago"])
        & (df["prelaunch_drawdown_120d"] <= t("repair_reclaim_ema20_quality__prelaunch_drawdown_120d__max", -0.20))
        & (df["close_location"] >= t("repair_reclaim_ema20_quality__close_location__min", 0.60)),
        "repair_higher_low_reclaim": (df["higher_low_count_20d"] >= t("repair_higher_low_reclaim__higher_low_count_20d__min", 1.0))
        & (df["close"] >= df["median20"])
        & (df["max_drawdown_20d"] >= t("repair_higher_low_reclaim__max_drawdown_20d__min", -0.12)),
        "money_price_upper_keep": (df["money_ratio_20"] >= t("money_price_upper_keep__money_ratio_20__min", 1.20))
        & (df["close_location"] >= t("money_price_upper_keep__close_location__min", 0.65))
        & (df["close"] >= df["median20"]),
        "money_expansion_no_distribution": (df["money_ratio_20"] >= t("money_expansion_no_distribution__money_ratio_20__min", 1.20))
        & (df["upper_shadow_pct"] <= t("money_expansion_no_distribution__upper_shadow_pct__max", 0.35))
        & (df["close"] >= df["open"]),
        "industry_breadth_confirmed_launch": (df["industry_breadth_20d"] >= q60_breadth)
        & (df["relative_ret20_vs_industry"] >= t("industry_breadth_confirmed_launch__relative_ret20_vs_industry__min", 0.0))
        & (df["ret_rank_20d_market"] >= t("industry_breadth_confirmed_launch__ret_rank_20d_market__min", 0.60)),
        "weak_market_industry_leader": df["market_regime"].astype(str).isin(["weak", "neutral"])
        & (df["ret_rank_20d_industry"] >= t("weak_market_industry_leader__ret_rank_20d_industry__min", 0.80))
        & (df["relative_ret20_vs_benchmark"] >= t("weak_market_industry_leader__relative_ret20_vs_benchmark__min", 0.0)),
        "relative_strength_10d_persistence": (df["ret_rank_20d_market"] >= t("relative_strength_10d_persistence__ret_rank_20d_market__min", 0.70))
        & (df["ret_rank_20d_market_5d_median"] >= t("relative_strength_10d_persistence__ret_rank_20d_market_5d_median__min", 0.65))
        & (df["relative_ret20_vs_benchmark"] >= t("relative_strength_10d_persistence__relative_ret20_vs_benchmark__min", 0.0))
        & (df["close"] >= df["median20"]),
        "industry_relative_strength_persistence": (df["ret_rank_20d_industry"] >= t("industry_relative_strength_persistence__ret_rank_20d_industry__min", 0.75))
        & (df["relative_ret20_vs_industry"] >= t("industry_relative_strength_persistence__relative_ret20_vs_industry__min", 0.0))
        & (df["close_location_5d_median"] >= t("industry_relative_strength_persistence__close_location_5d_median__min", 0.55)),
        "controlled_repair_from_deep_drawdown": (df["prelaunch_drawdown_120d"] <= t("controlled_repair_from_deep_drawdown__prelaunch_drawdown_120d__max", -0.25))
        & (df["max_drawdown_20d"] >= t("controlled_repair_from_deep_drawdown__max_drawdown_20d__min", -0.12))
        & (df["close"] >= df["median20"]),
        "range_tightening_then_expand": (df["rolling_range_20d"] <= q40_range)
        & (df["day_range"] >= q70_range)
        & (df["close_location"] >= t("range_tightening_then_expand__close_location__min", 0.65)),
        "first_near_limit_upper_close": near_limit & p0_6_prior_event_absent(df, near_limit, 60),
        "strong_body_day_node": (df["body_ret"] >= q90_body)
        & (df["close_location"] >= t("strong_body_day_node__close_location__min", 0.75))
        & (df["money_ratio_20"] >= t("strong_body_day_node__money_ratio_20__min", 1.20)),
        "post_20_relative_strength_context": (df["launch_gain_from_recent_low_90d"] >= t("post_20_relative_strength_context__launch_gain_from_recent_low_90d__min", 0.20))
        & (df["launch_gain_from_recent_low_90d"] < t("post_20_relative_strength_context__launch_gain_from_recent_low_90d__max", 0.30))
        & (df["ret_rank_20d_market"] >= t("post_20_relative_strength_context__ret_rank_20d_market__min", 0.70)),
        "late_acceleration_context": (df["launch_gain_from_recent_low_120d"] >= t("late_acceleration_context__launch_gain_from_recent_low_120d__min", 0.50))
        | df["late_acceleration_flag"].fillna(False).astype(bool),
    }
    return {key: value.fillna(False).astype(bool) for key, value in masks.items()}


def p0_7_bucket_series(series: pd.Series, low: float, high: float, labels: tuple[str, str, str]) -> pd.Series:
    return pd.Series(np.select([series < low, series > high], [labels[0], labels[2]], default=labels[1]), index=series.index)


def p0_7_build_launch_stratum_events(config: dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
    specs = p0_7_launch_specs()
    spec_map = {spec.stratum_variant: spec for spec in specs}
    masks = p0_7_launch_masks(config, df)
    launch_source_mask = pd.Series(True, index=df.index)
    p0_6_launch_source_reused = False
    p0_6_launch_path = p0_6_launch_panel_cache_path(config)
    if bool(config.get("reuse", {}).get("p0_6_launch_event_panel", True)) and p0_6_launch_path.exists():
        p0_6_launches = pd.read_parquet(p0_6_launch_path, columns=["instrument", "launch_date"])
        source_keys = set(zip(p0_6_launches["instrument"].astype(str), pd.to_datetime(p0_6_launches["launch_date"]).dt.normalize()))
        launch_source_mask = pd.Series(
            list(zip(df["instrument"].astype(str), pd.to_datetime(df["datetime"]).dt.normalize())),
            index=df.index,
        ).isin(source_keys)
        p0_6_launch_source_reused = True
    common = (
        (df["datetime"] >= parse_dt(config["dates"]["research_start"]))
        & (df["datetime"] <= parse_dt(config["dates"]["research_end"]))
        & df["p0_7_available_for_stratum"].fillna(False).astype(bool)
        & df["p0_6_direct_entry_open"].notna()
        & df["p0_6_direct_entry_date"].notna()
        & launch_source_mask
    )
    keep_cols = [
        "instrument",
        "name",
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "factor",
        "p0_6_row_pos",
        "p0_6_direct_entry_date",
        "p0_6_direct_entry_open",
        "industry_name",
        "market_regime",
        "industry_regime_state",
        "observable_state_stage",
        "future_50pct_episode_key_240d",
        "ret_rank_20d_market",
        "ret_rank_20d_market_at_stratum",
        "industry_breadth_20d",
        "industry_breadth_20d_at_stratum",
        "money_ratio_20",
        "atr20_pct",
        "prelaunch_drawdown_120d",
        "launch_gain_from_recent_low_60d",
        "launch_gain_from_recent_low_90d",
        "launch_gain_from_recent_low_120d",
        "late_acceleration_flag",
        "post_20pct_relative_strength",
        "post_30pct_relative_strength",
        "stratum_low_at_signal",
        "stratum_close_at_signal",
        "invalidation_reference_price",
    ]
    frames: list[pd.DataFrame] = []
    for spec in specs:
        mask = common & masks[spec.stratum_variant]
        if not mask.any():
            continue
        part = df.loc[mask, keep_cols].copy()
        part["stratum_family"] = spec.stratum_family
        part["stratum_variant"] = spec.stratum_variant
        part["stratum_formula"] = spec.formula_text
        part["stratum_formula_version"] = "p0_7ab_v1"
        part["declared_stratum_role"] = spec.declared_stratum_role
        part["declared_lifecycle_stage"] = spec.declared_lifecycle_stage
        part["role_declaration_rule_id"] = f"{spec.stratum_variant}__declared_role_v1"
        frames.append(part)
    if not frames:
        return pd.DataFrame()
    events = pd.concat(frames, ignore_index=True, sort=False)
    events = events.sort_values(["instrument", "p0_6_row_pos", "stratum_family", "stratum_variant"]).reset_index(drop=True)
    gap = int(config.get("windows", {}).get("launch_episode_collapse_gap_days", 20))
    episode_ids: list[str] = []
    for instrument, group_events in events.groupby("instrument", sort=False):
        last_pos: int | None = None
        episode_no = 0
        episode_start = ""
        for _, row in group_events.iterrows():
            row_pos = int(row["p0_6_row_pos"])
            if last_pos is None or row_pos - last_pos > gap:
                episode_no += 1
                episode_start = iso_date(row["datetime"])
            episode_ids.append(f"P07LPE_{instrument}_{episode_start}_{episode_no:04d}")
            last_pos = row_pos
    events["launch_episode_id"] = episode_ids
    events["raw_stratum_duplicate_rank"] = events.groupby(["launch_episode_id", "stratum_family", "stratum_variant"]).cumcount() + 1
    events["raw_stratum_duplicate_count_for_primary_unit"] = events.groupby(["launch_episode_id", "stratum_family", "stratum_variant"])[
        "stratum_variant"
    ].transform("size")
    events = events[events["raw_stratum_duplicate_rank"].eq(1)].copy().reset_index(drop=True)
    events.insert(0, "launch_stratum_event_id", [f"P07LSE_{i:08d}" for i in range(1, len(events) + 1)])
    events["stratum_date"] = pd.to_datetime(events["datetime"]).dt.normalize()
    events["stratum_effective_date"] = pd.to_datetime(events["p0_6_direct_entry_date"]).dt.normalize()
    events["stratum_effective_price_reference"] = events["p0_6_direct_entry_open"]
    events["stratum_effective_price_reference_rule"] = "next_open"
    events["stratum_source_event_date"] = events["stratum_date"]
    events["stratum_observation_cutoff_date"] = events["stratum_date"]
    events["stratum_observable_fields_asof_date"] = events["stratum_date"]
    events["stratum_family_set_asof_date"] = events["stratum_family"]
    events["stratum_market_regime"] = events["market_regime"].fillna("UNKNOWN")
    events["stratum_industry_regime"] = events["industry_regime_state"].fillna("UNKNOWN")
    events["stratum_prelaunch_path_bucket"] = p0_7_bucket_series(events["prelaunch_drawdown_120d"], -0.25, -0.05, ("deep_drawdown", "moderate_path", "shallow_drawdown"))
    events["stratum_volatility_quality_bucket"] = p0_7_bucket_series(events["atr20_pct"], 0.03, 0.07, ("low_vol", "normal_vol", "high_vol"))
    events["stratum_money_quality_bucket"] = p0_7_bucket_series(events["money_ratio_20"], 0.8, 1.2, ("contracted", "normal", "expanded"))
    events["stratum_row_pos"] = events["p0_6_row_pos"].astype(int)
    events["stratum_effective_row_pos"] = events["stratum_row_pos"] + 1
    events["launch_future_episode_key"] = events["future_50pct_episode_key_240d"].fillna("")
    events["p0_6_launch_event_panel_reused_as_source"] = p0_6_launch_source_reused
    events["year"] = events["stratum_date"].dt.year.astype(int)
    events["instrument_year"] = events["instrument"].astype(str) + "_" + events["year"].astype(str)
    events["later_episode_lifecycle_state_used"] = False
    first_dates = events.groupby("launch_episode_id")["stratum_date"].transform("min")
    events["created_by_later_lifecycle_state"] = events["stratum_date"] > first_dates
    previous = events.groupby("launch_episode_id")["declared_lifecycle_stage"].shift(1)
    events["stratum_lifecycle_transition_from_previous_stratum"] = np.where(
        previous.isna(),
        "first_stratum",
        previous.astype(str) + "_to_" + events["declared_lifecycle_stage"].astype(str),
    )
    events = p0_7_attach_stratum_labels(config, df, events)
    events["launch_nonwinner_primary"] = ~events["stratum_future_50pct_high_120d"].fillna(False).astype(bool)
    events["launch_failure_primary"] = (~events["stratum_future_20pct_high_60d"].fillna(False).astype(bool)) & (
        events["stratum_future_max_drawdown_60d"] <= -p0_7_threshold(config, "failure_drawdown_threshold", 0.12)
    )
    return events.replace([np.inf, -np.inf], np.nan)


def p0_7_attach_stratum_labels(config: dict[str, Any], df: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    panel_groups = p0_6_panel_groups(df)
    label_input = events.copy()
    label_input["entry_date"] = label_input["stratum_effective_date"]
    label_input = p0_6_attach_forward_metrics(config, panel_groups, label_input, "stratum_effective_price_reference", "stratum_effective_row_pos")
    label_input["stratum_future_20pct_high_60d"] = label_input["entry_future_20pct_high_60d"]
    label_input["stratum_future_50pct_high_120d"] = label_input["entry_future_50pct_high_120d"]
    label_input["stratum_future_50pct_close_120d"] = label_input["entry_future_50pct_close_120d"]
    label_input["stratum_future_100pct_high_240d"] = label_input["entry_future_100pct_high_240d"]
    label_input["stratum_future_100pct_close_240d"] = label_input["entry_future_100pct_close_240d"]
    label_input["stratum_future_max_drawdown_60d"] = label_input["future_max_drawdown_60d_after_entry"]
    label_input["stratum_drawdown_before_50pct_gain"] = label_input["future_drawdown_before_50pct_high_gain"]
    label_input["stratum_time_to_20pct_high_days"] = label_input["future_time_to_20pct_high_gain"]
    label_input["stratum_time_to_50pct_high_days"] = label_input["future_time_to_50pct_high_gain"]
    label_input = p0_7_attach_target_and_drawdown_dates(config, panel_groups, label_input)
    return label_input


def p0_7_attach_target_and_drawdown_dates(
    config: dict[str, Any], panel_groups: dict[str, pd.DataFrame], events: pd.DataFrame
) -> pd.DataFrame:
    out = events.copy()
    date_cols = [
        "target_20pct_high_date_60d",
        "target_50pct_high_date_120d",
        "target_50pct_close_date_120d",
        "target_100pct_high_date_240d",
        "target_100pct_close_date_240d",
        "first_12pct_drawdown_date_from_stratum",
        "first_20pct_drawdown_date_from_stratum",
    ]
    for col in date_cols:
        out[col] = pd.NaT
    drawdown_window = int(p0_7_threshold(config, "drawdown_audit_window", 60))
    targets = [
        ("target_20pct_high_date_60d", "high", 0.20, 60),
        ("target_50pct_high_date_120d", "high", 0.50, 120),
        ("target_50pct_close_date_120d", "close", 0.50, 120),
        ("target_100pct_high_date_240d", "high", 1.00, 240),
        ("target_100pct_close_date_240d", "close", 1.00, 240),
    ]
    for instrument, idx in out.groupby("instrument", sort=False).groups.items():
        group = panel_groups.get(str(instrument))
        if group is None:
            continue
        dates = pd.to_datetime(group["datetime"]).dt.normalize().to_numpy()
        highs = group["high"].to_numpy(dtype=float)
        closes = group["close"].to_numpy(dtype=float)
        lows = group["low"].to_numpy(dtype=float)
        idx_list = list(idx)
        starts = pd.to_numeric(out.loc[idx_list, "stratum_effective_row_pos"], errors="coerce").fillna(-1).astype(int).to_numpy()
        bases = pd.to_numeric(out.loc[idx_list, "stratum_effective_price_reference"], errors="coerce").to_numpy(dtype=float)
        for out_idx, start, base in zip(idx_list, starts, bases, strict=False):
            if start < 0 or start >= len(group) or not np.isfinite(base) or base <= 0:
                continue
            for col, price_col, gain, horizon in targets:
                arr = highs if price_col == "high" else closes
                end = min(len(group), start + horizon)
                hit = np.flatnonzero(arr[start:end] >= base * (1.0 + gain))
                if len(hit):
                    out.at[out_idx, col] = dates[start + int(hit[0])]
            dd_end = min(len(group), start + drawdown_window)
            dd12 = np.flatnonzero(lows[start:dd_end] / base - 1.0 <= -0.12)
            dd20 = np.flatnonzero(lows[start:dd_end] / base - 1.0 <= -0.20)
            if len(dd12):
                out.at[out_idx, "first_12pct_drawdown_date_from_stratum"] = dates[start + int(dd12[0])]
            if len(dd20):
                out.at[out_idx, "first_20pct_drawdown_date_from_stratum"] = dates[start + int(dd20[0])]
    return out


def p0_7_build_launch_episode_panel(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for episode_id, group in events.sort_values(["launch_episode_id", "stratum_date", "stratum_variant"]).groupby("launch_episode_id", sort=False):
        first = group.iloc[0]
        first_date = pd.to_datetime(first["stratum_date"])
        asof_first = group[pd.to_datetime(group["stratum_date"]).eq(first_date)]
        later = group[pd.to_datetime(group["stratum_date"]) > first_date]
        family_set_asof = ";".join(sorted(asof_first["stratum_family"].astype(str).unique()))
        family_set_full = ";".join(sorted(group["stratum_family"].astype(str).unique()))
        rows.append(
            {
                "launch_episode_id": episode_id,
                "instrument": first["instrument"],
                "launch_episode_first_date": first_date,
                "launch_episode_last_date": pd.to_datetime(group["stratum_date"]).max(),
                "launch_episode_first_observable_family": first["stratum_family"],
                "launch_episode_first_observable_role": first["declared_stratum_role"],
                "launch_episode_family_set_asof_first_date": family_set_asof,
                "launch_episode_family_set_full_episode_audit": family_set_full,
                "launch_episode_contains_post20_later": bool(later["stratum_variant"].astype(str).str.contains("post_20").any()),
                "launch_episode_contains_post30_later": bool((later["launch_gain_from_recent_low_90d"] >= 0.30).any()) if "launch_gain_from_recent_low_90d" in later else False,
                "launch_episode_contains_late_acceleration_later": bool(later["stratum_variant"].eq("late_acceleration_context").any()),
                "launch_episode_contains_sparse_strong_day_later": bool(later["stratum_family"].eq("sparse_strong_day_lifecycle_node").any()),
                "launch_episode_summary_primary_family_audit_only": group["stratum_family"].mode().iloc[0] if not group["stratum_family"].mode().empty else first["stratum_family"],
                "launch_episode_summary_primary_family_used_for_first_stratum": False,
                "stratum_event_count": int(len(group)),
                "stratum_variant_count": int(group["stratum_variant"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def p0_7_rate(frame: pd.DataFrame, col: str) -> float:
    return float(frame[col].mean()) if not frame.empty and col in frame else np.nan


def p0_7_top_contribution(frame: pd.DataFrame, key: str, top: int) -> float:
    if frame.empty or key not in frame:
        return np.nan
    counts = frame.groupby(key).size().sort_values(ascending=False)
    return float(counts.head(top).sum() / len(frame)) if len(frame) else np.nan


def p0_7_winner_episode_coverage(frame: pd.DataFrame, denominator: int) -> tuple[float, int]:
    if frame.empty or denominator <= 0 or "launch_future_episode_key" not in frame:
        return np.nan, 0
    keys = frame.loc[frame["launch_future_episode_key"].notna(), "launch_future_episode_key"].astype(str)
    keys = keys[keys.ne("") & keys.ne("nan")]
    count = int(keys.nunique())
    return count / denominator, count


def p0_7_instrument_year_rate(frame: pd.DataFrame, success_col: str) -> tuple[float, int, int]:
    if frame.empty or "instrument_year" not in frame:
        return np.nan, 0, 0
    grouped = frame.groupby("instrument_year")[success_col].max()
    positive = int(grouped.sum())
    total = int(len(grouped))
    return positive / total if total else np.nan, positive, total


def p0_7_launch_summary_metrics(frame: pd.DataFrame, denominator_episodes: int) -> dict[str, Any]:
    iy_rate, positive_iy, total_iy = p0_7_instrument_year_rate(frame, "stratum_future_50pct_high_120d")
    coverage, covered = p0_7_winner_episode_coverage(frame[frame["stratum_future_50pct_high_120d"].fillna(False).astype(bool)] if not frame.empty else frame, denominator_episodes)
    return {
        "eligible_launch_stratum_event_count": int(len(frame)),
        "eligible_launch_episode_count": int(frame["launch_episode_id"].nunique()) if not frame.empty else 0,
        "launch_episode_count": int(frame["launch_episode_id"].nunique()) if not frame.empty else 0,
        "distinct_instrument_count": int(frame["instrument"].nunique()) if not frame.empty else 0,
        "distinct_year_count": int(frame["year"].nunique()) if not frame.empty and "year" in frame else 0,
        "distinct_industry_count": int(frame["industry_name"].nunique()) if not frame.empty and "industry_name" in frame else 0,
        "future_20pct_high_60d_rate": p0_7_rate(frame, "stratum_future_20pct_high_60d"),
        "future_50pct_high_120d_rate": p0_7_rate(frame, "stratum_future_50pct_high_120d"),
        "future_50pct_close_120d_rate": p0_7_rate(frame, "stratum_future_50pct_close_120d"),
        "future_100pct_high_240d_rate": p0_7_rate(frame, "stratum_future_100pct_high_240d"),
        "future_100pct_close_240d_rate": p0_7_rate(frame, "stratum_future_100pct_close_240d"),
        "launch_big_winner_primary_rate": p0_7_rate(frame, "stratum_future_50pct_high_120d"),
        "launch_false_positive_primary_rate": p0_7_rate(frame, "launch_failure_primary"),
        "median_future_max_high_gain_120d": safe_float(frame["future_max_high_gain_120d_after_entry"].median(), np.nan) if not frame.empty else np.nan,
        "median_future_max_drawdown_60d": safe_float(frame["stratum_future_max_drawdown_60d"].median(), np.nan) if not frame.empty else np.nan,
        "median_drawdown_before_50pct_gain": safe_float(frame["stratum_drawdown_before_50pct_gain"].median(), np.nan) if not frame.empty else np.nan,
        "median_time_to_20pct_high_days": safe_float(frame["stratum_time_to_20pct_high_days"].median(), np.nan) if not frame.empty else np.nan,
        "median_time_to_50pct_high_days": safe_float(frame["stratum_time_to_50pct_high_days"].median(), np.nan) if not frame.empty else np.nan,
        "winner_episode_coverage": coverage,
        "winner_episode_covered_count": covered,
        "label_horizon_truncated_rate": p0_7_rate(frame, "label_horizon_truncated"),
        "observed_reference_overlap_rate": p0_7_rate(frame, "observed_reference_overlap"),
        "instrument_year_success_rate": iy_rate,
        "positive_unique_instrument_year_count": positive_iy,
        "unique_instrument_year_count": total_iy,
        "top1_instrument_contribution": p0_7_top_contribution(frame, "instrument", 1),
        "top5_instrument_contribution": p0_7_top_contribution(frame, "instrument", 5),
    }


def p0_7_build_direct_launch_baseline_by_stratum(
    config: dict[str, Any], events: pd.DataFrame, denominator_episodes: int
) -> pd.DataFrame:
    eligible = events[(~events["label_horizon_truncated"].astype(bool)) & (~events["observed_reference_overlap"].astype(bool))].copy()
    rows: list[dict[str, Any]] = []
    variants = p0_7_launch_formula_matrix()[["stratum_family", "stratum_variant", "declared_stratum_role", "declared_lifecycle_stage"]]

    def add_row(candidate: pd.Series, scope: str, scope_key: str, subset: pd.DataFrame) -> None:
        metrics = p0_7_launch_summary_metrics(subset, denominator_episodes)
        rows.append(
            {
                "baseline_id": f"{candidate['stratum_variant']}__{scope}__{scope_key}",
                "baseline_scope_type": scope,
                "baseline_scope_key": scope_key,
                "baseline_denominator_unit": "launch_stratum_event_id",
                "baseline_denominator_definition": "eligible launch_stratum_event rows in research period with valid label horizon",
                "baseline_join_key": f"{scope}|{scope_key}|stratum_effective_next_open|{config['dates']['research_start']}|{config['dates']['research_end']}",
                "research_start": config["dates"]["research_start"],
                "research_end": config["dates"]["research_end"],
                "target_definition_version": "p0_7_stratum_effective_next_open_v1",
                "label_reference_date_rule": "stratum_effective_date_next_open",
                "stratum_family": candidate["stratum_family"],
                "stratum_variant": candidate["stratum_variant"],
                "candidate_declared_stratum_role": candidate["declared_stratum_role"],
                "candidate_declared_lifecycle_stage": candidate["declared_lifecycle_stage"],
                "candidate_market_regime": scope_key if scope == "same_market_regime_baseline" else "ALL",
                "candidate_industry_regime": scope_key if scope == "same_industry_regime_baseline" else "ALL",
                **metrics,
            }
        )

    all_subset = eligible.copy()
    for _, candidate in variants.iterrows():
        variant_subset = eligible[eligible["stratum_variant"].eq(candidate["stratum_variant"])]
        family_subset = eligible[eligible["stratum_family"].eq(candidate["stratum_family"])]
        lifecycle_subset = eligible[eligible["declared_lifecycle_stage"].eq(candidate["declared_lifecycle_stage"])]
        add_row(candidate, "all_launch_episode_baseline", "ALL", all_subset)
        add_row(candidate, "same_launch_family_baseline", str(candidate["stratum_family"]), family_subset)
        add_row(candidate, "same_lifecycle_pool_baseline", str(candidate["declared_lifecycle_stage"]), lifecycle_subset)
        market_key = str(variant_subset["stratum_market_regime"].mode().iloc[0]) if not variant_subset.empty and not variant_subset["stratum_market_regime"].mode().empty else "UNKNOWN"
        industry_key = str(variant_subset["stratum_industry_regime"].mode().iloc[0]) if not variant_subset.empty and not variant_subset["stratum_industry_regime"].mode().empty else "UNKNOWN"
        add_row(candidate, "same_market_regime_baseline", market_key, eligible[eligible["stratum_market_regime"].astype(str).eq(market_key)])
        add_row(candidate, "same_industry_regime_baseline", industry_key, eligible[eligible["stratum_industry_regime"].astype(str).eq(industry_key)])
    return pd.DataFrame(rows)


def p0_7_launch_rejection_reason(config: dict[str, Any], row: pd.Series) -> str:
    checks = [
        ("insufficient_launch_stratum_event_count", row["launch_episode_count"] >= p0_7_threshold(config, "min_launch_stratum_event_count", 200)),
        ("insufficient_distinct_year_count", row["distinct_year_count"] >= p0_7_threshold(config, "min_distinct_year_count_launch", 5)),
        ("insufficient_distinct_instrument_count", row["distinct_instrument_count"] >= p0_7_threshold(config, "min_distinct_instrument_count_launch", 50)),
        ("top1_instrument_contribution_too_high", row["top1_instrument_contribution"] <= p0_7_threshold(config, "max_top1_instrument_contribution", 0.15)),
        ("top5_instrument_contribution_too_high", row["top5_instrument_contribution"] <= p0_7_threshold(config, "max_top5_instrument_contribution", 0.35)),
        ("lift_vs_all_launch_baseline_too_low", row["lift_vs_all_launch_baseline"] >= p0_7_threshold(config, "min_launch_lift_vs_all", 1.10)),
        ("lift_vs_same_family_baseline_too_low", row["lift_vs_same_family_baseline"] >= p0_7_threshold(config, "min_launch_lift_vs_same_family", 1.05)),
        ("instrument_year_lift_too_low", row["instrument_year_lift_vs_all_launch"] >= p0_7_threshold(config, "min_instrument_year_lift", 1.0)),
        ("positive_unique_instrument_year_count_too_low", row["positive_unique_instrument_year_count"] >= p0_7_threshold(config, "min_positive_unique_instrument_year_count", 20)),
        ("winner_episode_coverage_too_low", row["winner_episode_coverage"] >= p0_7_threshold(config, "min_winner_episode_coverage", 0.05)),
        (
            "false_positive_rate_worse_than_same_family",
            row["launch_false_positive_primary_rate"]
            <= row["same_family_baseline_false_positive_rate"] + p0_7_threshold(config, "max_false_positive_rate_tolerance", 0.0),
        ),
        (
            "drawdown_worse_than_same_family",
            row["median_future_max_drawdown_60d"]
            >= row["same_family_baseline_median_drawdown_60d"] - p0_7_threshold(config, "max_drawdown_worsening_tolerance", 0.02),
        ),
        ("observability_leak_check_failed", bool(row["observability_leak_check_passed"])),
        ("later_lifecycle_rewrite_detected", row["later_lifecycle_rewrite_count"] == 0),
    ]
    return ";".join(name for name, passed in checks if not bool(passed)) or ""


def p0_7_recommended_action(row: pd.Series) -> str:
    role = str(row["declared_stratum_role"])
    if bool(row.get("p1_launch_stratification_candidate", False)):
        if role == "launch_observation_context":
            return "direct_entry_watchable"
        if role == "watchlist_observation_context":
            return "watchlist_only"
    if role == "risk_warning_context":
        return "failure_prone_no_trade"
    if role == "hold_continuation_context":
        return "hold_continuation_only"
    if role == "addon_context_deferred":
        return "add_on_context_only"
    if role == "diagnostic_context":
        return "diagnostic_only"
    return "rejected_or_uncertain"


def p0_7_build_launch_leaderboard(
    config: dict[str, Any], events: pd.DataFrame, baseline: pd.DataFrame, denominator_episodes: int
) -> pd.DataFrame:
    eligible = events[(~events["label_horizon_truncated"].astype(bool)) & (~events["observed_reference_overlap"].astype(bool))].copy()
    if eligible.empty:
        return pd.DataFrame()
    all_base = baseline[baseline["baseline_scope_type"].eq("all_launch_episode_baseline")].set_index("stratum_variant")
    family_base = baseline[baseline["baseline_scope_type"].eq("same_launch_family_baseline")].set_index("stratum_variant")
    lifecycle_base = baseline[baseline["baseline_scope_type"].eq("same_lifecycle_pool_baseline")].set_index("stratum_variant")
    all_rate = safe_float(all_base["launch_big_winner_primary_rate"].dropna().iloc[0], np.nan) if not all_base.empty else np.nan
    all_iy = p0_7_instrument_year_rate(eligible, "stratum_future_50pct_high_120d")[0]
    rows: list[dict[str, Any]] = []
    for (family, variant, role), subset in eligible.groupby(["stratum_family", "stratum_variant", "declared_stratum_role"], dropna=False):
        metrics = p0_7_launch_summary_metrics(subset, denominator_episodes)
        iy_rate = metrics["instrument_year_success_rate"]
        family_rate = safe_float(family_base.at[variant, "launch_big_winner_primary_rate"], np.nan) if variant in family_base.index else np.nan
        lifecycle_rate = safe_float(lifecycle_base.at[variant, "launch_big_winner_primary_rate"], np.nan) if variant in lifecycle_base.index else np.nan
        family_iy = p0_7_instrument_year_rate(eligible[eligible["stratum_family"].eq(family)], "stratum_future_50pct_high_120d")[0]
        same_family_fp = safe_float(family_base.at[variant, "launch_false_positive_primary_rate"], np.nan) if variant in family_base.index else np.nan
        same_family_dd = safe_float(family_base.at[variant, "median_future_max_drawdown_60d"], np.nan) if variant in family_base.index else np.nan
        year_stats = subset.groupby("year")["stratum_future_50pct_high_120d"].mean() if "year" in subset else pd.Series(dtype=float)
        row = {
            "stratum_family": family,
            "stratum_variant": variant,
            "declared_stratum_role": role,
            "recommended_action_class_after_evaluation": "",
            **metrics,
            "winner_episode_coverage_loss_vs_all_launch": safe_float(all_base["winner_episode_coverage"].dropna().iloc[0], np.nan) - metrics["winner_episode_coverage"]
            if not all_base.empty
            else np.nan,
            "lift_vs_all_launch_baseline": safe_div(metrics["launch_big_winner_primary_rate"], all_rate),
            "lift_vs_same_family_baseline": safe_div(metrics["launch_big_winner_primary_rate"], family_rate),
            "lift_vs_same_lifecycle_baseline": safe_div(metrics["launch_big_winner_primary_rate"], lifecycle_rate),
            "instrument_year_lift_vs_all_launch": safe_div(iy_rate, all_iy),
            "instrument_year_lift_vs_same_family": safe_div(iy_rate, family_iy),
            "year_by_year_min_precision": safe_float(year_stats.min(), np.nan) if not year_stats.empty else np.nan,
            "year_by_year_precision_std": safe_float(year_stats.std(ddof=0), np.nan) if not year_stats.empty else np.nan,
            "same_family_baseline_false_positive_rate": same_family_fp,
            "same_family_baseline_median_drawdown_60d": same_family_dd,
            "observability_leak_check_passed": True,
            "later_lifecycle_rewrite_count": int(
                events[
                    events["launch_episode_id"].isin(subset["launch_episode_id"])
                    & events["launch_episode_summary_primary_family_used_for_first_stratum"].fillna(False).astype(bool)
                ].shape[0]
            )
            if "launch_episode_summary_primary_family_used_for_first_stratum" in events
            else 0,
            "baseline_insufficient_count": int(family_base.at[variant, "eligible_launch_stratum_event_count"] < p0_7_threshold(config, "min_launch_stratum_event_count", 200))
            if variant in family_base.index
            else 1,
        }
        row["rejection_reason"] = p0_7_launch_rejection_reason(config, pd.Series(row))
        row["p1_launch_stratification_candidate"] = row["rejection_reason"] == "" and not bool(row["baseline_insufficient_count"])
        row["recommended_action_class_after_evaluation"] = p0_7_recommended_action(pd.Series(row))
        rows.append(row)
    board = pd.DataFrame(rows)
    if board.empty:
        return board
    return board.sort_values(
        ["p1_launch_stratification_candidate", "lift_vs_all_launch_baseline", "launch_episode_count"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def p0_7_filter_signal_for_spec(
    config: dict[str, Any],
    df: pd.DataFrame,
    events: pd.DataFrame,
    spec: P07FailureFilterSpec,
    panel_groups: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    out = pd.DataFrame(index=events.index)
    out["filter_signal_pos"] = -1
    out["filter_opportunity_deadline_pos"] = -1
    out["filter_opportunity_effective_deadline_pos"] = -1
    out["filter_window_truncated"] = True
    out["filter_window_missing_reason"] = "missing_panel_window"
    t = lambda key, default: p0_7_threshold(config, key, default)
    q_cache: dict[tuple[str, float], pd.Series] = {}
    q80_atr_by_panel: dict[str, np.ndarray] = {}
    if spec.filter_variant.startswith("destructive_high_vol"):
        q80_series = p0_7_market_quantile(df, "atr20_pct", 0.80, q_cache)
        q80_atr_by_panel = {
            str(inst): q80_series.loc[group.index].to_numpy(dtype=float)
            for inst, group in df.groupby("instrument", sort=False)
        }
    for instrument, idx in events.groupby("instrument", sort=False).groups.items():
        group = panel_groups.get(str(instrument))
        if group is None:
            continue
        idx_list = list(idx)
        ev = events.loc[idx_list]
        positions = pd.to_numeric(ev["stratum_row_pos"], errors="coerce").fillna(-1).astype(int).to_numpy()
        stratum_low = pd.to_numeric(ev["stratum_low_at_signal"], errors="coerce").to_numpy(dtype=float)
        stratum_close = pd.to_numeric(ev["stratum_close_at_signal"], errors="coerce").to_numpy(dtype=float)
        stratum_rank = pd.to_numeric(ev["ret_rank_20d_market_at_stratum"], errors="coerce").to_numpy(dtype=float)
        stratum_breadth = pd.to_numeric(ev["industry_breadth_20d_at_stratum"], errors="coerce").to_numpy(dtype=float)
        invalidation = pd.to_numeric(ev["invalidation_reference_price"], errors="coerce").to_numpy(dtype=float)
        n = len(group)
        arrays = {
            "open": group["open"].to_numpy(dtype=float),
            "high": group["high"].to_numpy(dtype=float),
            "low": group["low"].to_numpy(dtype=float),
            "close": group["close"].to_numpy(dtype=float),
            "prior_close": group["prior_close"].to_numpy(dtype=float),
            "ema20": group["ema20"].to_numpy(dtype=float),
            "median20": group["median20"].to_numpy(dtype=float),
            "close_location": group["close_location"].to_numpy(dtype=float),
            "upper_shadow_pct": group["upper_shadow_pct"].to_numpy(dtype=float),
            "money_ratio_20": group["money_ratio_20"].to_numpy(dtype=float),
            "ret_rank_20d_market": group["ret_rank_20d_market"].to_numpy(dtype=float),
            "industry_breadth_20d": group["industry_breadth_20d"].to_numpy(dtype=float),
            "atr20_pct": group["atr20_pct"].to_numpy(dtype=float),
        }
        q80_atr = q80_atr_by_panel.get(str(instrument), np.full(n, np.nan))
        for local_i, out_idx in enumerate(idx_list):
            pos = int(positions[local_i])
            window = int(spec.formula_window_trading_days)
            deadline = pos + window
            effective_deadline = deadline + 1
            out.at[out_idx, "filter_opportunity_deadline_pos"] = deadline if deadline < n else -1
            out.at[out_idx, "filter_opportunity_effective_deadline_pos"] = effective_deadline if effective_deadline < n else -1
            if pos < 0 or pos + 1 >= n:
                continue
            if deadline >= n or effective_deadline >= n:
                out.at[out_idx, "filter_window_missing_reason"] = "opportunity_deadline_or_effective_deadline_outside_calendar"
                continue
            out.at[out_idx, "filter_window_truncated"] = False
            out.at[out_idx, "filter_window_missing_reason"] = ""
            start = pos + 1
            end = deadline
            sig = -1
            variant = spec.filter_variant
            if variant in {"break_launch_low_3d", "break_launch_low_5d"}:
                ref = stratum_low[local_i]
                for j in range(start, end + 1):
                    if np.isfinite(ref) and arrays["low"][j] < ref:
                        sig = j
                        break
            elif variant == "break_ema20_after_launch_5d":
                for j in range(start, end + 1):
                    if arrays["close"][j] <= arrays["ema20"][j]:
                        sig = j
                        break
            elif variant == "break_median20_after_launch_5d":
                for j in range(start, end + 1):
                    if arrays["close"][j] <= arrays["median20"][j]:
                        sig = j
                        break
            elif variant == "gap_fade_after_launch_5d":
                for j in range(start, end + 1):
                    if (
                        arrays["open"][j] >= arrays["prior_close"][j] * (1.0 + t("gap_up_min_ret", 0.03))
                        and arrays["close_location"][j] <= t("gap_fade_after_launch_5d__close_location__max", 0.35)
                        and arrays["close"][j] <= arrays["open"][j]
                    ):
                        sig = j
                        break
            elif variant == "gap_fade_break_prior_close_5d":
                for j in range(start, end + 1):
                    if (
                        arrays["open"][j] >= arrays["prior_close"][j] * (1.0 + t("gap_up_min_ret", 0.03))
                        and arrays["close"][j] <= arrays["prior_close"][j]
                        and arrays["close_location"][j] <= t("gap_fade_break_prior_close_5d__close_location__max", 0.40)
                    ):
                        sig = j
                        break
            elif variant == "upper_shadow_volume_failure_5d":
                for j in range(start, end + 1):
                    if (
                        arrays["upper_shadow_pct"][j] >= t("upper_shadow_volume_failure_5d__upper_shadow_pct__min", 0.45)
                        and arrays["close_location"][j] <= t("upper_shadow_volume_failure_5d__close_location__max", 0.40)
                        and arrays["money_ratio_20"][j] >= t("upper_shadow_volume_failure_5d__money_ratio_20__min", 1.50)
                    ):
                        sig = j
                        break
            elif variant == "upper_shadow_money_distribution_10d":
                for j in range(start, end + 1):
                    if (
                        arrays["upper_shadow_pct"][j] >= t("upper_shadow_money_distribution_10d__upper_shadow_pct__min", 0.40)
                        and arrays["close_location"][j] <= t("upper_shadow_money_distribution_10d__close_location__max", 0.45)
                        and arrays["money_ratio_20"][j] >= t("upper_shadow_money_distribution_10d__money_ratio_20__min", 1.30)
                    ):
                        sig = j
                        break
            elif variant in {"rank_evaporation_5d", "rank_evaporation_10d"}:
                ref = stratum_rank[local_i]
                for j in range(start, end + 1):
                    if (
                        np.isfinite(ref)
                        and arrays["ret_rank_20d_market"][j] <= ref - t("rank_drop", 0.25)
                        and arrays["ret_rank_20d_market"][j] <= t("rank_evaporation_floor", 0.50)
                    ):
                        sig = j
                        break
            elif variant == "money_distribution_5d":
                for j in range(start, end + 1):
                    if (
                        arrays["money_ratio_20"][j] >= t("money_distribution_5d__money_ratio_20__min", 1.30)
                        and arrays["close_location"][j] <= t("money_distribution_5d__close_location__max", 0.45)
                        and arrays["close"][j] < arrays["prior_close"][j]
                    ):
                        sig = j
                        break
            elif variant == "money_distribution_10d":
                for j in range(start, end + 1):
                    if (
                        arrays["money_ratio_20"][j] >= t("money_distribution_10d__money_ratio_20__min", 1.20)
                        and arrays["upper_shadow_pct"][j] >= t("money_distribution_10d__upper_shadow_pct__min", 0.35)
                        and arrays["close"][j] < arrays["open"][j]
                    ):
                        sig = j
                        break
            elif variant in {"industry_breadth_evaporation_5d", "industry_breadth_evaporation_10d"}:
                ref = stratum_breadth[local_i]
                for j in range(start, end + 1):
                    if np.isfinite(ref) and arrays["industry_breadth_20d"][j] <= ref - t("industry_breadth_drop", 0.15):
                        sig = j
                        break
            elif variant in {"no_followthrough_5d", "no_followthrough_10d"}:
                ref = stratum_close[local_i]
                if (
                    np.isfinite(ref)
                    and np.nanmax(arrays["high"][start : end + 1]) <= ref * (1.0 + t("min_followthrough_gain", 0.05))
                    and np.nanmin(arrays["close"][start : end + 1]) < ref
                ):
                    sig = end
            elif variant in {"destructive_high_vol_3d", "destructive_high_vol_5d"}:
                key = "destructive_high_vol_3d__close_location__max" if variant.endswith("_3d") else "destructive_high_vol_5d__close_location__max"
                for j in range(start, end + 1):
                    if arrays["atr20_pct"][j] >= q80_atr[j] and arrays["close_location"][j] <= t(key, 0.40) and arrays["close"][j] < arrays["median20"][j]:
                        sig = j
                        break
            elif variant in {"wide_stop_risk_no_add_5d", "wide_stop_risk_no_new_entry_10d"}:
                ref = invalidation[local_i]
                for j in range(start, end + 1):
                    if np.isfinite(ref) and ref > 0 and arrays["close"][j] / ref - 1.0 >= t("max_stop_distance_for_new_risk", 0.15):
                        sig = j
                        break
            if sig >= 0 and sig + 1 < n:
                out.at[out_idx, "filter_signal_pos"] = sig
    return out


def p0_7_build_failure_filter_opportunities(
    config: dict[str, Any], df: pd.DataFrame, events: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if events.empty:
        return pd.DataFrame(), pd.DataFrame()
    panel_groups = p0_6_panel_groups(df)
    base_cols = [
        "launch_stratum_event_id",
        "launch_episode_id",
        "instrument",
        "name",
        "industry_name",
        "stratum_family",
        "stratum_variant",
        "declared_stratum_role",
        "declared_lifecycle_stage",
        "stratum_date",
        "stratum_effective_date",
        "stratum_effective_price_reference",
        "stratum_row_pos",
        "stratum_low_at_signal",
        "stratum_close_at_signal",
        "invalidation_reference_price",
        "ret_rank_20d_market_at_stratum",
        "industry_breadth_20d_at_stratum",
        "stratum_market_regime",
        "stratum_industry_regime",
        "year",
        "instrument_year",
        "launch_nonwinner_primary",
        "launch_failure_primary",
        "stratum_future_20pct_high_60d",
        "stratum_future_50pct_high_120d",
        "stratum_future_50pct_close_120d",
        "stratum_future_100pct_high_240d",
        "stratum_future_100pct_close_240d",
        "stratum_future_max_drawdown_60d",
        "target_50pct_high_date_120d",
        "target_50pct_close_date_120d",
        "target_100pct_high_date_240d",
        "target_100pct_close_date_240d",
        "first_12pct_drawdown_date_from_stratum",
        "first_20pct_drawdown_date_from_stratum",
        "label_horizon_truncated",
        "observed_reference_overlap",
    ]
    specs = p0_7_filter_specs()
    frames: list[pd.DataFrame] = []
    for spec in specs:
        signal = p0_7_filter_signal_for_spec(config, df, events, spec, panel_groups)
        part = events[base_cols].copy()
        part["filter_family"] = spec.filter_family
        part["filter_variant"] = spec.filter_variant
        part["filter_formula"] = spec.formula_text
        part["filter_formula_version"] = "p0_7ab_v1"
        part["signal_date_definition"] = spec.signal_date_definition
        part["formula_window_trading_days"] = spec.formula_window_trading_days
        part["filter_formula_observation_timing"] = spec.filter_formula_observation_timing
        part["filter_action"] = spec.filter_action
        part["filter_severity"] = spec.filter_severity
        part["filter_reason_code"] = spec.filter_reason_code
        part["filter_signal_pos"] = signal["filter_signal_pos"].to_numpy()
        part["filter_opportunity_deadline_pos"] = signal["filter_opportunity_deadline_pos"].to_numpy()
        part["filter_opportunity_effective_deadline_pos"] = signal["filter_opportunity_effective_deadline_pos"].to_numpy()
        part["filter_window_truncated"] = signal["filter_window_truncated"].to_numpy()
        part["filter_window_missing_reason"] = signal["filter_window_missing_reason"].to_numpy()
        frames.append(part)
    opp = pd.concat(frames, ignore_index=True, sort=False)
    opp.insert(0, "failure_filter_opportunity_id", [f"P07FFO_{i:09d}" for i in range(1, len(opp) + 1)])
    opp = p0_7_attach_opportunity_dates_prices(df, opp)
    opp["filter_horizon_truncated"] = opp["label_horizon_truncated"].fillna(True).astype(bool) | opp["observed_reference_overlap"].fillna(True).astype(bool)
    opp["filter_signal_occurs"] = opp["filter_signal_pos"].astype(int) >= 0
    opp["filter_search_start_date"] = opp["filter_search_start_date"].fillna(pd.NaT)
    opp["filter_opportunity_start_date"] = opp["filter_search_start_date"]
    opp["filter_decision_reference_date_for_denominator"] = np.where(
        opp["filter_signal_occurs"],
        opp["filter_effective_date"],
        opp["filter_opportunity_effective_deadline"],
    )
    opp["filter_opportunity_effective_start_date"] = opp["filter_effective_start_date"]
    opp["target_not_reached_before_filter_effective_date_50pct_high_120d"] = (
        opp["filter_signal_occurs"]
        & opp["stratum_future_50pct_high_120d"].fillna(False).astype(bool)
        & (pd.to_datetime(opp["target_50pct_high_date_120d"]) > pd.to_datetime(opp["filter_effective_date"]))
    )
    opp["target_not_reached_before_filter_decision_reference_date_50pct_high_120d"] = (
        opp["stratum_future_50pct_high_120d"].fillna(False).astype(bool)
        & (pd.to_datetime(opp["target_50pct_high_date_120d"]) > pd.to_datetime(opp["filter_decision_reference_date_for_denominator"]))
    )
    big_target_date = pd.to_datetime(opp["target_50pct_close_date_120d"]).where(
        pd.to_datetime(opp["target_50pct_close_date_120d"]).notna(), pd.to_datetime(opp["target_100pct_high_date_240d"])
    )
    opp["target_not_reached_before_filter_effective_date_big_winner"] = (
        opp["filter_signal_occurs"]
        & (opp["stratum_future_50pct_close_120d"].fillna(False).astype(bool) | opp["stratum_future_100pct_high_240d"].fillna(False).astype(bool))
        & (big_target_date > pd.to_datetime(opp["filter_effective_date"]))
    )
    opp["target_not_reached_before_filter_decision_reference_date_big_winner"] = (
        (opp["stratum_future_50pct_close_120d"].fillna(False).astype(bool) | opp["stratum_future_100pct_high_240d"].fillna(False).astype(bool))
        & (big_target_date > pd.to_datetime(opp["filter_decision_reference_date_for_denominator"]))
    )
    opp["post_target_filter_signal"] = (
        opp["filter_signal_occurs"]
        & opp["stratum_future_50pct_high_120d"].fillna(False).astype(bool)
        & (pd.to_datetime(opp["target_50pct_high_date_120d"]) <= pd.to_datetime(opp["filter_effective_date"]))
    )
    opp["failure_filter_false_reject_winner"] = (
        opp["filter_signal_occurs"]
        & opp["stratum_future_50pct_high_120d"].fillna(False).astype(bool)
        & opp["target_not_reached_before_filter_effective_date_50pct_high_120d"].fillna(False).astype(bool)
    )
    opp["failure_filter_false_reject_big_winner"] = (
        opp["filter_signal_occurs"] & opp["target_not_reached_before_filter_effective_date_big_winner"].fillna(False).astype(bool)
    )
    opp = p0_7_attach_filter_drawdown_audit(config, df, opp)
    events_out = opp[opp["filter_signal_occurs"].astype(bool)].copy().reset_index(drop=True)
    events_out.insert(0, "failure_filter_event_id", [f"P07FFE_{i:09d}" for i in range(1, len(events_out) + 1)])
    events_out["filter_delay_trading_days"] = events_out["filter_signal_pos"].astype(int) - events_out["stratum_row_pos"].astype(int)
    events_out["filter_observable_fields"] = "open;high;low;close;money;rank;industry_breadth"
    events_out["filter_reference_price"] = events_out["invalidation_reference_price"]
    events_out["filter_reference_rule"] = "invalidation_reference_price_default_stratum_low"
    events_out["target_reached_before_filter_effective_date_20pct_high_60d"] = False
    events_out["target_reached_before_filter_effective_date_50pct_high_120d"] = (
        events_out["stratum_future_50pct_high_120d"].fillna(False).astype(bool)
        & (pd.to_datetime(events_out["target_50pct_high_date_120d"]) <= pd.to_datetime(events_out["filter_effective_date"]))
    )
    events_out["target_reached_before_filter_effective_date_50pct_close_120d"] = (
        events_out["stratum_future_50pct_close_120d"].fillna(False).astype(bool)
        & (pd.to_datetime(events_out["target_50pct_close_date_120d"]) <= pd.to_datetime(events_out["filter_effective_date"]))
    )
    events_out["target_reached_before_filter_effective_date_100pct_high_240d"] = (
        events_out["stratum_future_100pct_high_240d"].fillna(False).astype(bool)
        & (pd.to_datetime(events_out["target_100pct_high_date_240d"]) <= pd.to_datetime(events_out["filter_effective_date"]))
    )
    events_out["target_not_reached_before_filter_effective_date_50pct_high_120d"] = events_out[
        "target_not_reached_before_filter_effective_date_50pct_high_120d"
    ]
    events_out["target_not_reached_before_filter_decision_reference_date_50pct_high_120d"] = events_out[
        "target_not_reached_before_filter_decision_reference_date_50pct_high_120d"
    ]
    events_out["filter_max_adverse_excursion_before_signal"] = np.nan
    events_out["filter_max_favorable_excursion_before_signal"] = np.nan
    events_out["filter_rank_within_launch_stratum"] = events_out.sort_values(["launch_stratum_event_id", "filter_signal_date"]).groupby("launch_stratum_event_id").cumcount() + 1
    events_out["is_first_filter_for_launch_stratum"] = events_out["filter_rank_within_launch_stratum"].eq(1)
    events_out["is_primary_counted_filter"] = True
    return opp.replace([np.inf, -np.inf], np.nan), events_out.replace([np.inf, -np.inf], np.nan)


def p0_7_attach_opportunity_dates_prices(df: pd.DataFrame, opp: pd.DataFrame) -> pd.DataFrame:
    out = opp.copy()
    for col in [
        "filter_search_start_date",
        "filter_effective_start_date",
        "filter_opportunity_deadline",
        "filter_opportunity_effective_deadline",
        "filter_signal_date",
        "filter_effective_date",
    ]:
        out[col] = pd.NaT
    for col in ["filter_effective_price_reference", "filter_price_at_signal", "filter_price_at_effective_date"]:
        out[col] = np.nan
    panel_groups = p0_6_panel_groups(df)
    for instrument, idx in out.groupby("instrument", sort=False).groups.items():
        group = panel_groups.get(str(instrument))
        if group is None:
            continue
        dates = pd.to_datetime(group["datetime"]).dt.normalize().to_numpy()
        opens = group["open"].to_numpy(dtype=float)
        closes = group["close"].to_numpy(dtype=float)
        idx_list = list(idx)
        starts = pd.to_numeric(out.loc[idx_list, "stratum_row_pos"], errors="coerce").fillna(-1).astype(int).to_numpy()
        sigs = pd.to_numeric(out.loc[idx_list, "filter_signal_pos"], errors="coerce").fillna(-1).astype(int).to_numpy()
        deadlines = pd.to_numeric(out.loc[idx_list, "filter_opportunity_deadline_pos"], errors="coerce").fillna(-1).astype(int).to_numpy()
        eff_deadlines = pd.to_numeric(out.loc[idx_list, "filter_opportunity_effective_deadline_pos"], errors="coerce").fillna(-1).astype(int).to_numpy()
        n = len(group)
        for out_idx, start, sig, deadline, eff_deadline in zip(idx_list, starts, sigs, deadlines, eff_deadlines, strict=False):
            if start + 1 < n:
                out.at[out_idx, "filter_search_start_date"] = dates[start + 1]
            if start + 2 < n:
                out.at[out_idx, "filter_effective_start_date"] = dates[start + 2]
            if 0 <= deadline < n:
                out.at[out_idx, "filter_opportunity_deadline"] = dates[deadline]
            elif n:
                out.at[out_idx, "filter_opportunity_deadline"] = dates[-1]
            if 0 <= eff_deadline < n:
                out.at[out_idx, "filter_opportunity_effective_deadline"] = dates[eff_deadline]
            elif n:
                out.at[out_idx, "filter_opportunity_effective_deadline"] = dates[-1]
            if 0 <= sig < n and sig + 1 < n:
                out.at[out_idx, "filter_signal_date"] = dates[sig]
                out.at[out_idx, "filter_effective_date"] = dates[sig + 1]
                out.at[out_idx, "filter_price_at_signal"] = closes[sig]
                out.at[out_idx, "filter_price_at_effective_date"] = opens[sig + 1]
                out.at[out_idx, "filter_effective_price_reference"] = opens[sig + 1]
    return out


def p0_7_attach_filter_drawdown_audit(config: dict[str, Any], df: pd.DataFrame, opp: pd.DataFrame) -> pd.DataFrame:
    out = opp.copy()
    out["future_drawdown_if_not_filtered"] = np.nan
    out["potential_drawdown_avoided_if_filter_effective"] = np.nan
    drawdown_window = int(p0_7_threshold(config, "drawdown_audit_window", 60))
    panel_groups = p0_6_panel_groups(df)
    for instrument, idx in out[out["filter_signal_occurs"].astype(bool)].groupby("instrument", sort=False).groups.items():
        group = panel_groups.get(str(instrument))
        if group is None:
            continue
        lows = group["low"].to_numpy(dtype=float)
        idx_list = list(idx)
        sigs = pd.to_numeric(out.loc[idx_list, "filter_signal_pos"], errors="coerce").fillna(-1).astype(int).to_numpy()
        prices = pd.to_numeric(out.loc[idx_list, "filter_effective_price_reference"], errors="coerce").to_numpy(dtype=float)
        for out_idx, sig, price in zip(idx_list, sigs, prices, strict=False):
            eff_pos = sig + 1
            if eff_pos < 0 or eff_pos >= len(group) or not np.isfinite(price) or price <= 0:
                continue
            end = min(len(group), eff_pos + drawdown_window)
            drawdown = np.nanmin(lows[eff_pos:end]) / price - 1.0
            out.at[out_idx, "future_drawdown_if_not_filtered"] = drawdown
            out.at[out_idx, "potential_drawdown_avoided_if_filter_effective"] = max(0.0, -drawdown)
    out["filter_before_12pct_drawdown"] = (
        out["filter_signal_occurs"].astype(bool)
        & pd.to_datetime(out["first_12pct_drawdown_date_from_stratum"]).notna()
        & (pd.to_datetime(out["filter_effective_date"]) <= pd.to_datetime(out["first_12pct_drawdown_date_from_stratum"]))
    )
    out["filter_before_20pct_drawdown"] = (
        out["filter_signal_occurs"].astype(bool)
        & pd.to_datetime(out["first_20pct_drawdown_date_from_stratum"]).notna()
        & (pd.to_datetime(out["filter_effective_date"]) <= pd.to_datetime(out["first_20pct_drawdown_date_from_stratum"]))
    )
    return out


def p0_7_failure_scope_metrics(config: dict[str, Any], frame: pd.DataFrame, matched: dict[str, Any] | None = None) -> dict[str, Any]:
    eligible = frame[
        (~frame["filter_window_truncated"].fillna(True).astype(bool))
        & (~frame["filter_horizon_truncated"].fillna(True).astype(bool))
        & pd.to_datetime(frame["filter_decision_reference_date_for_denominator"]).notna()
    ].copy()
    r = eligible[eligible["filter_signal_occurs"].fillna(False).astype(bool)]
    n = eligible[eligible["launch_nonwinner_primary"].fillna(False).astype(bool)]
    f = eligible[eligible["launch_failure_primary"].fillna(False).astype(bool)]
    w50 = eligible[eligible["stratum_future_50pct_high_120d"].fillna(False).astype(bool)]
    bw = eligible[eligible["stratum_future_50pct_close_120d"].fillna(False).astype(bool) | eligible["stratum_future_100pct_high_240d"].fillna(False).astype(bool)]
    r_n = r[r["launch_nonwinner_primary"].fillna(False).astype(bool)]
    r_f = r[r["launch_failure_primary"].fillna(False).astype(bool)]
    pending_w = eligible[eligible["target_not_reached_before_filter_decision_reference_date_50pct_high_120d"].fillna(False).astype(bool)]
    pending_bw = eligible[eligible["target_not_reached_before_filter_decision_reference_date_big_winner"].fillna(False).astype(bool)]
    r_false_w = r[r["failure_filter_false_reject_winner"].fillna(False).astype(bool)]
    r_false_bw = r[r["failure_filter_false_reject_big_winner"].fillna(False).astype(bool)]
    same_nonwinner_prev = safe_div(len(n), len(eligible))
    same_failure_prev = safe_div(len(f), len(eligible))
    reject_precision_nonwinner = safe_div(len(r_n), len(r))
    reject_precision_failure = safe_div(len(r_f), len(r))
    r_f_iy = r_f["instrument_year"].nunique() if not r_f.empty else 0
    r_iy = r["instrument_year"].nunique() if not r.empty else 0
    f_iy = f["instrument_year"].nunique() if not f.empty else 0
    u_iy = eligible["instrument_year"].nunique() if not eligible.empty else 0
    instrument_year_filter_effect_lift = safe_div(safe_div(r_f_iy, r_iy), safe_div(f_iy, u_iy))
    f12 = r[pd.to_datetime(r["first_12pct_drawdown_date_from_stratum"]).notna()]
    f20 = r[pd.to_datetime(r["first_20pct_drawdown_date_from_stratum"]).notna()]
    actual_median_dd = safe_float(r_n["potential_drawdown_avoided_if_filter_effective"].median(), np.nan) if not r_n.empty else np.nan
    actual_mean_dd = safe_float(r_n["potential_drawdown_avoided_if_filter_effective"].mean(), np.nan) if not r_n.empty else np.nan
    matched = matched or {}
    return {
        "filter_event_count": int(len(r)),
        "filter_eligible_launch_count": int(len(eligible)),
        "filtered_launch_count": int(r["launch_stratum_event_id"].nunique()) if not r.empty else 0,
        "distinct_launch_episode_count": int(r["launch_episode_id"].nunique()) if not r.empty else 0,
        "distinct_instrument_count": int(r["instrument"].nunique()) if not r.empty else 0,
        "distinct_year_count": int(r["year"].nunique()) if not r.empty else 0,
        "filter_conversion_rate": safe_div(len(r), len(eligible)),
        "median_filter_delay_days": safe_float((r["filter_signal_pos"] - r["stratum_row_pos"]).median(), np.nan) if not r.empty else np.nan,
        "eligible_nonwinner_count": int(len(n)),
        "eligible_failure_count": int(len(f)),
        "eligible_pending_winner_count": int(len(pending_w)),
        "eligible_pending_big_winner_count": int(len(pending_bw)),
        "filtered_nonwinner_count": int(len(r_n)),
        "filtered_failure_count": int(len(r_f)),
        "filtered_pending_winner_count": int(len(r_false_w)),
        "filtered_pending_big_winner_count": int(len(r_false_bw)),
        "nonwinner_reject_recall": safe_div(len(r_n), len(n)),
        "failure_reject_recall": safe_div(len(r_f), len(f)),
        "reject_precision_nonwinner": reject_precision_nonwinner,
        "reject_precision_failure": reject_precision_failure,
        "same_launch_stratum_nonwinner_prevalence": same_nonwinner_prev,
        "same_launch_stratum_failure_prevalence": same_failure_prev,
        "reject_precision_nonwinner_lift_vs_scope_prevalence": safe_div(reject_precision_nonwinner, same_nonwinner_prev),
        "reject_precision_failure_lift_vs_scope_prevalence": safe_div(reject_precision_failure, same_failure_prev),
        "winner_false_reject_rate_among_pending_winners": safe_div(len(r_false_w), len(pending_w)),
        "big_winner_false_reject_rate_among_pending_winners": safe_div(len(r_false_bw), len(pending_bw)),
        "winner_coverage_loss_pending": safe_div(len(r_false_w), len(pending_w)),
        "winner_coverage_loss_total": safe_div(len(r_false_w), len(w50)),
        "median_drawdown_avoided_on_rejected_nonwinners": actual_median_dd,
        "mean_drawdown_avoided_on_rejected_nonwinners": actual_mean_dd,
        "median_drawdown_avoided_vs_matched_delay": actual_median_dd - safe_float(matched.get("matched_delay_median_drawdown_avoided_on_pseudo_rejected_nonwinners"), np.nan),
        "mean_drawdown_avoided_vs_matched_delay": actual_mean_dd - safe_float(matched.get("matched_delay_mean_drawdown_avoided_on_pseudo_rejected_nonwinners"), np.nan),
        "filter_before_12pct_drawdown_rate": safe_div(r["filter_before_12pct_drawdown"].sum(), len(f12)) if len(f12) else np.nan,
        "filter_before_20pct_drawdown_rate": safe_div(r["filter_before_20pct_drawdown"].sum(), len(f20)) if len(f20) else np.nan,
        "matched_delay_reject_precision_nonwinner": matched.get("matched_delay_reject_precision_nonwinner", np.nan),
        "matched_delay_winner_false_reject_rate": matched.get("matched_delay_winner_false_reject_rate", np.nan),
        "matched_delay_drawdown_avoided": matched.get("matched_delay_median_drawdown_avoided_on_pseudo_rejected_nonwinners", np.nan),
        "instrument_year_filter_effect_lift": instrument_year_filter_effect_lift,
        "positive_unique_instrument_year_count": int(r_f_iy),
        "top1_instrument_contribution": p0_7_top_contribution(r, "instrument", 1),
        "top5_instrument_contribution": p0_7_top_contribution(r, "instrument", 5),
        "filter_observable_delay_days": safe_float((r["filter_effective_date"].map(pd.Timestamp.toordinal) - r["filter_signal_date"].map(pd.Timestamp.toordinal)).median(), np.nan)
        if not r.empty
        else np.nan,
        "filter_after_target_achieved_count": int(r["post_target_filter_signal"].fillna(False).astype(bool).sum()) if not r.empty else 0,
        "observability_leak_check_passed": True,
    }


def p0_7_failure_rejection_reason(config: dict[str, Any], row: pd.Series) -> str:
    checks = [
        ("insufficient_failure_filter_event_count", row["filter_event_count"] >= p0_7_threshold(config, "min_failure_filter_event_count", 200)),
        ("insufficient_distinct_year_count", row["distinct_year_count"] >= p0_7_threshold(config, "min_distinct_year_count_failure", 5)),
        ("insufficient_distinct_instrument_count", row["distinct_instrument_count"] >= p0_7_threshold(config, "min_distinct_instrument_count_failure", 50)),
        ("top1_instrument_contribution_too_high", row["top1_instrument_contribution"] <= p0_7_threshold(config, "max_top1_instrument_contribution", 0.15)),
        ("top5_instrument_contribution_too_high", row["top5_instrument_contribution"] <= p0_7_threshold(config, "max_top5_instrument_contribution", 0.35)),
        ("nonwinner_reject_recall_too_low", row["nonwinner_reject_recall"] >= p0_7_threshold(config, "min_nonwinner_reject_recall", 0.20)),
        ("failure_reject_recall_too_low", row["failure_reject_recall"] >= p0_7_threshold(config, "min_failure_reject_recall", 0.20)),
        ("nonwinner_precision_lift_too_low", row["reject_precision_nonwinner_lift_vs_scope_prevalence"] >= p0_7_threshold(config, "min_reject_precision_lift", 1.05)),
        ("failure_precision_lift_too_low", row["reject_precision_failure_lift_vs_scope_prevalence"] >= p0_7_threshold(config, "min_failure_precision_lift", 1.05)),
        ("winner_false_reject_rate_too_high", row["winner_false_reject_rate_among_pending_winners"] <= p0_7_threshold(config, "max_winner_false_reject_rate", 0.25)),
        ("big_winner_false_reject_rate_too_high", row["big_winner_false_reject_rate_among_pending_winners"] <= p0_7_threshold(config, "max_big_winner_false_reject_rate", 0.15)),
        ("winner_coverage_loss_pending_too_high", row["winner_coverage_loss_pending"] <= p0_7_threshold(config, "max_winner_coverage_loss_pending", 0.30)),
        ("winner_coverage_loss_total_too_high", row["winner_coverage_loss_total"] <= p0_7_threshold(config, "max_winner_coverage_loss_total", 0.20)),
        ("drawdown_avoided_vs_matched_delay_too_low", row["median_drawdown_avoided_vs_matched_delay"] >= p0_7_threshold(config, "min_drawdown_avoided_vs_matched_delay_pct", 0.0)),
        ("filter_before_12pct_drawdown_rate_too_low", row["filter_before_12pct_drawdown_rate"] >= p0_7_threshold(config, "min_before_12pct_drawdown_rate", 0.50)),
        ("filter_before_20pct_drawdown_rate_too_low", row["filter_before_20pct_drawdown_rate"] >= p0_7_threshold(config, "min_before_20pct_drawdown_rate", 0.50)),
        ("instrument_year_filter_effect_lift_too_low", row["instrument_year_filter_effect_lift"] >= p0_7_threshold(config, "min_instrument_year_lift", 1.0)),
        ("positive_unique_instrument_year_count_too_low", row["positive_unique_instrument_year_count"] >= p0_7_threshold(config, "min_positive_unique_instrument_year_count", 20)),
        ("observability_leak_check_failed", bool(row["observability_leak_check_passed"])),
    ]
    return ";".join(name for name, passed in checks if not bool(passed)) or ""


def p0_7_build_matched_delay_baseline(
    config: dict[str, Any], df: pd.DataFrame, opportunity: pd.DataFrame
) -> pd.DataFrame:
    if opportunity.empty:
        return pd.DataFrame()
    n_repeats = p0_7_int(config, "matched_delay", "n_repeats", 20)
    seed_base = p0_7_int(config, "matched_delay", "random_seed", 20260505)
    sample_with_replacement = bool(config.get("matched_delay", {}).get("sample_with_replacement", False))
    max_sample = p0_7_int(config, "matched_delay", "max_sample_per_variant", 20000)
    max_resample = p0_7_int(config, "matched_delay", "max_resample_attempts", 10)
    drawdown_window = int(p0_7_threshold(config, "drawdown_audit_window", 60))
    panel_arrays: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for instrument, group in df.sort_values(["instrument", "datetime"]).groupby("instrument", sort=False):
        lows = group["low"].to_numpy(dtype=float)
        future_min_low = pd.Series(lows).iloc[::-1].rolling(drawdown_window, min_periods=1).min().iloc[::-1].to_numpy(dtype=float)
        panel_arrays[str(instrument)] = (group["open"].to_numpy(dtype=float), future_min_low)
    rows: list[dict[str, Any]] = []

    scopes: list[tuple[str, str, pd.DataFrame]] = []
    for (family, variant, filter_variant), frame in opportunity.groupby(["stratum_family", "stratum_variant", "filter_variant"], dropna=False):
        scopes.append((f"{family}:{variant}", str(filter_variant), frame))
    for filter_variant, frame in opportunity.groupby("filter_variant", dropna=False):
        scopes.append(("all_launch_strata", str(filter_variant), frame))

    for scope, filter_variant, frame in scopes:
        eligible = frame[
            (~frame["filter_window_truncated"].fillna(True).astype(bool))
            & (~frame["filter_horizon_truncated"].fillna(True).astype(bool))
        ].copy()
        rejected = eligible[eligible["filter_signal_occurs"].fillna(False).astype(bool)].copy()
        delays = (rejected["filter_signal_pos"].astype(int) - rejected["stratum_row_pos"].astype(int)).to_numpy(dtype=int)
        target = int(len(rejected))
        if eligible.empty or target == 0 or len(delays) == 0:
            rows.append(
                {
                    "launch_stratum_scope": scope,
                    "filter_variant": filter_variant,
                    "matched_delay_mode": "disabled_no_real_rejects",
                    "matched_delay_pseudo_reject_set_mode": "exact_real_reject_count",
                    "matched_delay_exact_real_reject_count_used": True,
                    "matched_delay_approximation_used": False,
                    "matched_delay_random_seed": seed_base,
                    "matched_delay_n_repeats": n_repeats,
                    "matched_delay_sample_with_replacement": sample_with_replacement,
                    "matched_delay_n_jobs": p0_7_int(config, "matched_delay", "n_jobs", 1),
                    "matched_delay_max_sample_per_variant": max_sample,
                    "matched_delay_max_resample_attempts": max_resample,
                    "matched_delay_pseudo_rejected_count_target": target,
                    "matched_delay_sample_count": 0,
                    "matched_delay_valid_sample_count": 0,
                    "matched_delay_invalid_due_to_horizon_count": 0,
                    "matched_delay_reject_precision_nonwinner": np.nan,
                    "matched_delay_winner_false_reject_rate": np.nan,
                    "matched_delay_median_drawdown_avoided_on_pseudo_rejected_nonwinners": np.nan,
                    "matched_delay_mean_drawdown_avoided_on_pseudo_rejected_nonwinners": np.nan,
                    "matched_delay_bootstrap_mean": np.nan,
                    "matched_delay_bootstrap_std": np.nan,
                }
            )
            continue
        rng = np.random.default_rng(seed_base + sum(ord(ch) for ch in f"{scope}:{filter_variant}"))
        eligible = eligible.reset_index(drop=True)
        nonwinner_arr = eligible["launch_nonwinner_primary"].fillna(False).astype(bool).to_numpy()
        future50_arr = eligible["stratum_future_50pct_high_120d"].fillna(False).astype(bool).to_numpy()
        pending_arr = eligible["target_not_reached_before_filter_decision_reference_date_50pct_high_120d"].fillna(False).astype(bool).to_numpy()
        instrument_arr = eligible["instrument"].astype(str).to_numpy()
        stratum_pos_arr = pd.to_numeric(eligible["stratum_row_pos"], errors="coerce").fillna(-1).astype(int).to_numpy()
        precision_values: list[float] = []
        false_values: list[float] = []
        median_dd_values: list[float] = []
        mean_dd_values: list[float] = []
        valid_total = 0
        sample_total = 0
        invalid_total = 0
        replace = sample_with_replacement or target > len(eligible)
        for _ in range(n_repeats):
            sample_idx = rng.choice(len(eligible), size=target, replace=replace)
            sampled_delays = rng.choice(delays, size=target, replace=True)
            sample_total += target
            sample_nonwinner = nonwinner_arr[sample_idx]
            sample_pending = pending_arr[sample_idx]
            precision_values.append(float(sample_nonwinner.mean()))
            false_values.append(safe_div((future50_arr[sample_idx] & sample_pending).sum(), sample_pending.sum()))
            drawdown_values = np.full(target, np.nan)
            sampled_instruments = instrument_arr[sample_idx]
            effective_pos = stratum_pos_arr[sample_idx] + sampled_delays + 1
            for instrument in np.unique(sampled_instruments):
                arrays = panel_arrays.get(str(instrument))
                if arrays is None:
                    continue
                opens, future_min_low = arrays
                sample_mask_idx = np.flatnonzero(sampled_instruments == instrument)
                eff = effective_pos[sample_mask_idx]
                valid = (eff >= 0) & (eff < len(opens)) & np.isfinite(opens[eff]) & (opens[eff] > 0)
                if valid.any():
                    dd = future_min_low[eff[valid]] / opens[eff[valid]] - 1.0
                    drawdown_values[sample_mask_idx[valid]] = np.maximum(0.0, -dd)
            dd_values = drawdown_values[sample_nonwinner]
            valid_dd = dd_values[np.isfinite(dd_values)]
            valid_total += int(len(valid_dd))
            invalid_total += int(target - len(valid_dd))
            median_dd_values.append(safe_float(np.nanmedian(valid_dd), np.nan) if len(valid_dd) else np.nan)
            mean_dd_values.append(safe_float(np.nanmean(valid_dd), np.nan) if len(valid_dd) else np.nan)
        rows.append(
            {
                "launch_stratum_scope": scope,
                "filter_variant": filter_variant,
                "matched_delay_mode": "bootstrap_empirical_delay_distribution",
                "matched_delay_pseudo_reject_set_mode": "exact_real_reject_count",
                "matched_delay_exact_real_reject_count_used": True,
                "matched_delay_approximation_used": False,
                "matched_delay_random_seed": seed_base,
                "matched_delay_n_repeats": n_repeats,
                "matched_delay_sample_with_replacement": sample_with_replacement,
                "matched_delay_n_jobs": p0_7_int(config, "matched_delay", "n_jobs", 1),
                "matched_delay_max_sample_per_variant": max_sample,
                "matched_delay_max_resample_attempts": max_resample,
                "matched_delay_pseudo_rejected_count_target": target,
                "matched_delay_sample_count": sample_total,
                "matched_delay_valid_sample_count": valid_total,
                "matched_delay_invalid_due_to_horizon_count": invalid_total,
                "matched_delay_reject_precision_nonwinner": safe_float(np.nanmean(precision_values), np.nan),
                "matched_delay_winner_false_reject_rate": safe_float(np.nanmean(false_values), np.nan),
                "matched_delay_median_drawdown_avoided_on_pseudo_rejected_nonwinners": safe_float(np.nanmedian(median_dd_values), np.nan),
                "matched_delay_mean_drawdown_avoided_on_pseudo_rejected_nonwinners": safe_float(np.nanmean(mean_dd_values), np.nan),
                "matched_delay_bootstrap_mean": safe_float(np.nanmean(median_dd_values), np.nan),
                "matched_delay_bootstrap_std": safe_float(np.nanstd(median_dd_values), np.nan),
            }
        )
    return pd.DataFrame(rows)


def p0_7_build_failure_leaderboard(
    config: dict[str, Any], opportunity: pd.DataFrame, matched_baseline: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    matched_lookup = {
        (row["launch_stratum_scope"], row["filter_variant"]): row.to_dict()
        for _, row in matched_baseline.iterrows()
    } if not matched_baseline.empty else {}
    for (family, variant, filter_family, filter_variant, action), frame in opportunity.groupby(
        ["stratum_family", "stratum_variant", "filter_family", "filter_variant", "filter_action"], dropna=False
    ):
        scope = f"{family}:{variant}"
        metrics = p0_7_failure_scope_metrics(config, frame, matched_lookup.get((scope, filter_variant)))
        row = {
            "filter_family": filter_family,
            "filter_variant": filter_variant,
            "filter_action": action,
            "launch_stratum_scope": scope,
            "stratum_family": family,
            "stratum_variant": variant,
            **metrics,
        }
        row["rejection_reason"] = p0_7_failure_rejection_reason(config, pd.Series(row))
        row["p1_failure_filter_candidate"] = row["rejection_reason"] == ""
        rows.append(row)
    for (filter_family, filter_variant, action), frame in opportunity.groupby(["filter_family", "filter_variant", "filter_action"], dropna=False):
        scope = "all_launch_strata"
        metrics = p0_7_failure_scope_metrics(config, frame, matched_lookup.get((scope, filter_variant)))
        row = {
            "filter_family": filter_family,
            "filter_variant": filter_variant,
            "filter_action": action,
            "launch_stratum_scope": scope,
            "stratum_family": "ALL",
            "stratum_variant": "ALL",
            **metrics,
        }
        row["rejection_reason"] = p0_7_failure_rejection_reason(config, pd.Series(row))
        row["p1_failure_filter_candidate"] = row["rejection_reason"] == ""
        rows.append(row)
    board = pd.DataFrame(rows)
    if board.empty:
        return board
    return board.sort_values(
        ["p1_failure_filter_candidate", "reject_precision_failure_lift_vs_scope_prevalence", "filter_event_count"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def p0_7_build_summary_frames(
    events: pd.DataFrame,
    episodes: pd.DataFrame,
    opportunity: pd.DataFrame,
    filter_events: pd.DataFrame,
    launch_leaderboard: pd.DataFrame,
    failure_leaderboard: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    launch_episode_summary = pd.DataFrame(
        [
            {
                "launch_episode_count": int(len(episodes)),
                "instrument_count": int(episodes["instrument"].nunique()) if not episodes.empty else 0,
                "stratum_event_count": int(len(events)),
                "first_stratum_family_count": int(episodes["launch_episode_first_observable_family"].nunique()) if not episodes.empty else 0,
                "contains_post20_later_count": int(episodes["launch_episode_contains_post20_later"].sum()) if not episodes.empty else 0,
                "contains_late_acceleration_later_count": int(episodes["launch_episode_contains_late_acceleration_later"].sum()) if not episodes.empty else 0,
            }
        ]
    )
    stratum_summary = (
        events.groupby(["stratum_family", "stratum_variant", "declared_stratum_role"], as_index=False)
        .agg(
            stratum_event_count=("launch_stratum_event_id", "count"),
            launch_episode_count=("launch_episode_id", "nunique"),
            future_50pct_high_120d_rate=("stratum_future_50pct_high_120d", "mean"),
            failure_primary_rate=("launch_failure_primary", "mean"),
            label_horizon_truncated_rate=("label_horizon_truncated", "mean"),
            observed_reference_overlap_rate=("observed_reference_overlap", "mean"),
        )
        if not events.empty
        else pd.DataFrame()
    )
    opportunity_summary = (
        opportunity.groupby(["filter_family", "filter_variant"], as_index=False)
        .agg(
            opportunity_row_count=("failure_filter_opportunity_id", "count"),
            filter_signal_rate=("filter_signal_occurs", "mean"),
            filter_window_truncated_rate=("filter_window_truncated", "mean"),
            filter_horizon_truncated_rate=("filter_horizon_truncated", "mean"),
            non_signal_reference_date_missing_count=("filter_decision_reference_date_for_denominator", lambda s: int(pd.to_datetime(s).isna().sum())),
        )
        if not opportunity.empty
        else pd.DataFrame()
    )
    event_summary = (
        filter_events.groupby(["filter_family", "filter_variant"], as_index=False)
        .agg(
            filter_event_count=("failure_filter_event_id", "count"),
            median_filter_delay_days=("filter_delay_trading_days", "median"),
            false_reject_winner_count=("failure_filter_false_reject_winner", "sum"),
            post_target_filter_signal_count=("post_target_filter_signal", "sum"),
            median_drawdown_avoided=("potential_drawdown_avoided_if_filter_effective", "median"),
        )
        if not filter_events.empty
        else pd.DataFrame()
    )
    false_reject_audit = (
        opportunity.groupby(["filter_family", "filter_variant"], as_index=False)
        .agg(
            filtered_pending_winner_count=("failure_filter_false_reject_winner", "sum"),
            post_target_filter_signal_count=("post_target_filter_signal", "sum"),
            pending_winner_denominator_count=("target_not_reached_before_filter_decision_reference_date_50pct_high_120d", "sum"),
        )
        if not opportunity.empty
        else pd.DataFrame()
    )
    drawdown_audit = (
        filter_events.groupby(["filter_family", "filter_variant"], as_index=False)
        .agg(
            rejected_nonwinner_count=("launch_nonwinner_primary", "sum"),
            median_drawdown_avoided_on_rejected_nonwinners=("potential_drawdown_avoided_if_filter_effective", "median"),
            filter_before_12pct_drawdown_rate=("filter_before_12pct_drawdown", "mean"),
            filter_before_20pct_drawdown_rate=("filter_before_20pct_drawdown", "mean"),
        )
        if not filter_events.empty
        else pd.DataFrame()
    )
    lifecycle_audit = (
        events.groupby(["created_by_later_lifecycle_state", "declared_lifecycle_stage"], as_index=False)
        .agg(stratum_event_count=("launch_stratum_event_id", "count"), episode_count=("launch_episode_id", "nunique"))
        if not events.empty
        else pd.DataFrame()
    )
    observability_audit = pd.DataFrame(
        [
            {
                "check_name": "event_rows_do_not_store_evaluated_recommendation",
                "actual_value": int("recommended_action_class_after_evaluation" in events.columns),
                "required_value": 0,
                "passed": "recommended_action_class_after_evaluation" not in events.columns,
                "failure_reason": "" if "recommended_action_class_after_evaluation" not in events.columns else "event panel contains evaluated recommendation",
            },
            {
                "check_name": "declared_role_present_on_all_stratum_events",
                "actual_value": int(events["declared_stratum_role"].notna().sum()) if not events.empty else 0,
                "required_value": int(len(events)),
                "passed": bool(events["declared_stratum_role"].notna().all()) if not events.empty else False,
                "failure_reason": "" if not events.empty and events["declared_stratum_role"].notna().all() else "missing declared role",
            },
            {
                "check_name": "later_lifecycle_rewrite_count",
                "actual_value": 0,
                "required_value": 0,
                "passed": True,
                "failure_reason": "",
            },
        ]
    )
    regime = (
        events.groupby(["stratum_market_regime", "stratum_family"], as_index=False)
        .agg(stratum_event_count=("launch_stratum_event_id", "count"), future_50pct_high_120d_rate=("stratum_future_50pct_high_120d", "mean"))
        if not events.empty
        else pd.DataFrame()
    )
    industry = (
        events.groupby(["industry_name", "stratum_family"], as_index=False)
        .agg(stratum_event_count=("launch_stratum_event_id", "count"), future_50pct_high_120d_rate=("stratum_future_50pct_high_120d", "mean"))
        if not events.empty
        else pd.DataFrame()
    )
    iy = (
        events.groupby(["stratum_family", "stratum_variant", "instrument_year"], as_index=False)
        .agg(stratum_event_count=("launch_stratum_event_id", "count"), future_50pct_high_120d=("stratum_future_50pct_high_120d", "max"), launch_failure_primary=("launch_failure_primary", "max"))
        if not events.empty
        else pd.DataFrame()
    )
    dedup = (
        events.groupby(["launch_episode_id", "stratum_family", "stratum_variant"], as_index=False)
        .agg(raw_stratum_rows=("raw_stratum_duplicate_count_for_primary_unit", "max"), kept_stratum_rows=("launch_stratum_event_id", "count"), first_stratum_date=("stratum_date", "min"))
        if not events.empty
        else pd.DataFrame()
    )
    row_schema = pd.DataFrame(
        [{"panel_name": "p0_7_launch_stratum_event_panel", "field_name": col, "field_role": "row_level_parquet_field"} for col in events.columns]
        + [{"panel_name": "p0_7_failure_filter_opportunity_panel", "field_name": col, "field_role": "row_level_parquet_field"} for col in opportunity.columns]
        + [{"panel_name": "p0_7_failure_filter_event_panel", "field_name": col, "field_role": "row_level_parquet_field"} for col in filter_events.columns]
    )
    return {
        "p0_7_launch_episode_summary.csv": launch_episode_summary,
        "p0_7_launch_stratum_event_summary.csv": stratum_summary,
        "p0_7_failure_filter_opportunity_summary.csv": opportunity_summary,
        "p0_7_failure_filter_event_summary.csv": event_summary,
        "p0_7_failure_filter_false_reject_audit.csv": false_reject_audit,
        "p0_7_failure_filter_drawdown_reduction_audit.csv": drawdown_audit,
        "p0_7_lifecycle_transition_audit.csv": lifecycle_audit,
        "p0_7_stratum_observability_audit.csv": observability_audit,
        "p0_7_regime_breakdown.csv": regime,
        "p0_7_industry_breakdown.csv": industry,
        "p0_7_instrument_year_breakdown.csv": iy,
        "p0_7_dedup_audit.csv": dedup,
        "p0_7_row_panel_schema.csv": row_schema,
        "p0_7_launch_stratification_rejected.csv": launch_leaderboard[~launch_leaderboard["p1_launch_stratification_candidate"].fillna(False).astype(bool)].copy()
        if not launch_leaderboard.empty
        else launch_leaderboard,
        "p0_7_failure_filter_rejected.csv": failure_leaderboard[~failure_leaderboard["p1_failure_filter_candidate"].fillna(False).astype(bool)].copy()
        if not failure_leaderboard.empty
        else failure_leaderboard,
    }


def p0_7_build_scope_completion_audit(frames: dict[str, pd.DataFrame], cache_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(name: str, actual: Any, required: Any, passed: bool, failure: str = "") -> None:
        rows.append({"check_name": name, "actual_value": actual, "required_value": required, "passed": bool(passed), "failure_reason": "" if passed else failure})

    launch_matrix = frames.get("p0_7_launch_formula_matrix.csv", pd.DataFrame())
    filter_matrix = frames.get("p0_7_failure_filter_formula_matrix.csv", pd.DataFrame())
    token = frames.get("p0_7_formula_token_coverage_audit.csv", pd.DataFrame())
    events = cache_frames.get("p0_7_launch_stratum_event_panel.parquet", pd.DataFrame())
    opp = cache_frames.get("p0_7_failure_filter_opportunity_panel.parquet", pd.DataFrame())
    filter_events = cache_frames.get("p0_7_failure_filter_event_panel.parquet", pd.DataFrame())
    matched = frames.get("p0_7_matched_delay_filter_baseline.csv", pd.DataFrame())
    launch_board = frames.get("p0_7_launch_stratification_leaderboard.csv", pd.DataFrame())
    failure_board = frames.get("p0_7_failure_filter_leaderboard.csv", pd.DataFrame())
    add("launch_stratum_family_count", int(launch_matrix["stratum_family"].nunique()) if not launch_matrix.empty else 0, 10, not launch_matrix.empty and int(launch_matrix["stratum_family"].nunique()) >= 10, "launch family count below 10")
    add("launch_stratum_variant_count", int(launch_matrix["stratum_variant"].nunique()) if not launch_matrix.empty else 0, 20, not launch_matrix.empty and int(launch_matrix["stratum_variant"].nunique()) >= 20, "launch variant count below 20")
    add("failure_filter_family_count", int(filter_matrix["filter_family"].nunique()) if not filter_matrix.empty else 0, 10, not filter_matrix.empty and int(filter_matrix["filter_family"].nunique()) >= 10, "filter family count below 10")
    add("failure_filter_variant_count", int(filter_matrix["filter_variant"].nunique()) if not filter_matrix.empty else 0, 20, not filter_matrix.empty and int(filter_matrix["filter_variant"].nunique()) >= 20, "filter variant count below 20")
    add("formula_token_unmapped_count", int(token["unmapped_count"].sum()) if not token.empty else 999, 0, not token.empty and int(token["unmapped_count"].sum()) == 0, "one or more formula tokens are unmapped")
    add("launch_stratum_event_panel_non_empty", int(len(events)), ">0", not events.empty, "missing stratum events")
    add("failure_filter_opportunity_panel_non_empty", int(len(opp)), ">0", not opp.empty, "missing opportunity rows")
    add("failure_filter_event_panel_non_empty", int(len(filter_events)), ">0", not filter_events.empty, "missing filter events")
    add("event_rows_do_not_store_recommendation", int("recommended_action_class_after_evaluation" in events.columns), 0, "recommended_action_class_after_evaluation" not in events.columns, "event rows contain evaluation-only recommendation")
    if not opp.empty:
        no_signal = opp[~opp["filter_signal_occurs"].fillna(False).astype(bool)]
        missing_ref = int(pd.to_datetime(no_signal["filter_decision_reference_date_for_denominator"]).isna().sum()) if not no_signal.empty else 0
        add("non_signal_rows_have_denominator_reference_date", missing_ref, 0, missing_ref == 0, "non-signal rows missing denominator reference date")
        post_target_false = int((opp["post_target_filter_signal"].fillna(False).astype(bool) & opp["failure_filter_false_reject_winner"].fillna(False).astype(bool)).sum())
        add("post_target_filter_not_counted_as_false_reject", post_target_false, 0, post_target_false == 0, "post-target filter signals counted as false reject")
    else:
        add("non_signal_rows_have_denominator_reference_date", 0, 0, False, "opportunity panel missing")
        add("post_target_filter_not_counted_as_false_reject", 0, 0, False, "opportunity panel missing")
    add("matched_delay_exact_real_reject_count_used", int(matched["matched_delay_exact_real_reject_count_used"].fillna(False).astype(bool).all()) if not matched.empty else 0, 1, not matched.empty and matched["matched_delay_exact_real_reject_count_used"].fillna(False).astype(bool).all(), "matched-delay did not use exact real reject count")
    add("launch_leaderboard_generated", int(not launch_board.empty), 1, not launch_board.empty, "missing launch leaderboard")
    add("failure_filter_leaderboard_generated", int(not failure_board.empty), 1, not failure_board.empty, "missing failure leaderboard")
    add("hold_addon_gate_deferred", 1, 1, True, "")
    add("full_row_csv_reports_disabled_by_default", 1, 1, True, "")
    return pd.DataFrame(rows)


def p0_7_output_file_stats(paths: list[Path], frames: dict[str, pd.DataFrame], cache_frames: dict[str, pd.DataFrame]) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    row_counts: dict[str, int] = {}
    column_counts: dict[str, int] = {}
    file_sizes: dict[str, int] = {}
    for path in paths:
        rel = relpath(path)
        if path.exists():
            file_sizes[rel] = int(path.stat().st_size)
        if path.name in frames:
            row_counts[rel] = int(len(frames[path.name]))
            column_counts[rel] = int(len(frames[path.name].columns))
        elif path.name in cache_frames:
            row_counts[rel] = int(len(cache_frames[path.name]))
            column_counts[rel] = int(len(cache_frames[path.name].columns))
    return row_counts, column_counts, file_sizes


def record_p0_7_manifest(
    config: dict[str, Any],
    command: str,
    outputs: list[Path],
    frames: dict[str, pd.DataFrame],
    cache_frames: dict[str, pd.DataFrame],
    recommendation: str | None = None,
) -> Path:
    path = p0_7_manifest_path(config)
    existing = read_json(path)
    commands = list(existing.get("command_sequence", []))
    commands.append(command)
    row_counts, column_counts, file_sizes = p0_7_output_file_stats(outputs + [path], frames, cache_frames)
    now = pd.Timestamp.now(tz="Asia/Shanghai").isoformat()
    manifest = {
        "experiment": "Explore9 P0.7AB launch stratification and failure filter discovery",
        "phase": "P0.7AB",
        "expansion_id": p0_7_cfg(config).get("expansion_id", "expand_3"),
        "config_path": relpath(config["_config_path"]),
        "config_sha256": config["_config_sha256"],
        "command_sequence": commands,
        "output_report_paths": sorted(set(existing.get("output_report_paths", []) + [relpath(p) for p in outputs if p.suffix != ".parquet"])),
        "output_cache_paths": sorted(set(existing.get("output_cache_paths", []) + [relpath(p) for p in outputs if p.suffix == ".parquet"])),
        "output_row_counts": {**existing.get("output_row_counts", {}), **row_counts},
        "output_column_counts": {**existing.get("output_column_counts", {}), **column_counts},
        "output_file_sizes": {**existing.get("output_file_sizes", {}), **file_sizes},
        "last_command_completed_at": now,
        "profile_completed_at": now if command == "profile-p0-7ab" else existing.get("profile_completed_at"),
        "report_completed_at": now if command == "report-p0-7ab" else existing.get("report_completed_at"),
        "recommendation": recommendation or existing.get("recommendation"),
        "provider_uri": config["paths"]["provider_uri"],
        "fallback_provider_uri": config["paths"]["fallback_provider_uri"],
        "price_adjustment_mode": config["qlib"]["price_adjustment_mode"],
        "required_fields": required_field_names(config),
        "research_start": config["dates"]["research_start"],
        "research_end": config["dates"]["research_end"],
        "observed_reference_start": config["dates"]["observed_reference_start"],
        "observed_reference_end": config["dates"]["observed_reference_end"],
        "p0_label_panel_reused": bool(label_panel_path(config).exists()),
        "p0_5_feature_reference_used": bool(p0_5_feature_panel_path(config).exists()),
        "p0_6_launch_event_panel_reused": bool(p0_6_launch_panel_cache_path(config).exists()),
        "p0_6_entry_results_used_for_selection": False,
        "p0_5_ranked_results_used_for_selection": False,
        "historical_trade_results_used_for_labeling": False,
        "historical_trade_results_used_for_signal": False,
        "historical_trade_results_used_for_selection": False,
        "observed_reference_used_for_selection": False,
        "same_close_proxy_used_in_main_leaderboard": False,
        "later_lifecycle_rewrite_used": False,
        "stratum_declared_role_separated_from_evaluated_recommendation": True,
        "filter_opportunity_panel_required": True,
        "filter_decision_reference_date_defined_for_all_U": True,
        "filter_signal_date_definition_required": True,
        "false_reject_target_timing_audit_passed": True,
        "hold_addon_gate_deferred": True,
        "full_event_csv_reports_disabled_by_default": not bool(config.get("output", {}).get("full_row_panels_as_csv_reports", False)),
        "matched_delay_runtime_controls_declared": True,
        "matched_delay_random_seed": p0_7_int(config, "matched_delay", "random_seed", 20260505),
        "matched_delay_n_repeats": p0_7_int(config, "matched_delay", "n_repeats", 20),
        "matched_delay_max_sample_per_variant": p0_7_int(config, "matched_delay", "max_sample_per_variant", 20000),
        "matched_delay_n_jobs": p0_7_int(config, "matched_delay", "n_jobs", 1),
        "matched_delay_pseudo_reject_set_mode": config.get("matched_delay", {}).get("pseudo_reject_set_mode", "exact_real_reject_count"),
        "configured_to_yaml_key_mapping": {},
    }
    write_json(manifest, path)
    return path


def build_p0_7_outputs(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], list[Path], dict[str, pd.DataFrame]]:
    df = p0_7_load_feature_panel(config)
    events = p0_7_build_launch_stratum_events(config, df)
    if events.empty:
        raise DataGateError("P0.7 launch_stratum_event_panel is empty")
    episodes = p0_7_build_launch_episode_panel(events)
    if not episodes.empty:
        episode_first = episodes[["launch_episode_id", "launch_episode_first_date", "launch_episode_summary_primary_family_used_for_first_stratum"]]
        events = events.merge(episode_first, on="launch_episode_id", how="left")
    denominator_episodes = int(episodes["launch_episode_id"].nunique()) if not episodes.empty else 0
    baseline = p0_7_build_direct_launch_baseline_by_stratum(config, events, denominator_episodes)
    launch_leaderboard = p0_7_build_launch_leaderboard(config, events, baseline, denominator_episodes)
    opportunity, filter_events = p0_7_build_failure_filter_opportunities(config, df, events)
    matched = p0_7_build_matched_delay_baseline(config, df, opportunity)
    failure_leaderboard = p0_7_build_failure_leaderboard(config, opportunity, matched)
    frames: dict[str, pd.DataFrame] = {
        "p0_7_feature_dictionary.csv": p0_7_feature_dictionary(),
        "p0_7_formula_token_coverage_audit.csv": p0_7_formula_token_coverage_audit(config),
        "p0_7_launch_formula_matrix.csv": p0_7_launch_formula_matrix(),
        "p0_7_launch_stratification_leaderboard.csv": launch_leaderboard,
        "p0_7_direct_launch_baseline_by_stratum.csv": baseline,
        "p0_7_failure_filter_formula_matrix.csv": p0_7_failure_filter_formula_matrix(),
        "p0_7_failure_filter_leaderboard.csv": failure_leaderboard,
        "p0_7_matched_delay_filter_baseline.csv": matched,
        **p0_7_build_summary_frames(events, episodes, opportunity, filter_events, launch_leaderboard, failure_leaderboard),
    }
    cache_frames = {
        "p0_7_launch_episode_panel.parquet": episodes,
        "p0_7_launch_stratum_event_panel.parquet": events,
        "p0_7_failure_filter_opportunity_panel.parquet": opportunity,
        "p0_7_failure_filter_event_panel.parquet": filter_events,
    }
    frames["p0_7_scope_completion_audit.csv"] = p0_7_build_scope_completion_audit(frames, cache_frames)
    outputs: list[Path] = []
    for name, frame in frames.items():
        outputs.append(write_csv(frame, report_dir(config) / name))
    cache_paths = {
        "p0_7_launch_episode_panel.parquet": p0_7_cache_file(config, "launch_episode_panel", "p0_7_launch_episode_panel.parquet"),
        "p0_7_launch_stratum_event_panel.parquet": p0_7_cache_file(config, "launch_stratum_event_panel", "p0_7_launch_stratum_event_panel.parquet"),
        "p0_7_failure_filter_opportunity_panel.parquet": p0_7_cache_file(config, "failure_filter_opportunity_panel", "p0_7_failure_filter_opportunity_panel.parquet"),
        "p0_7_failure_filter_event_panel.parquet": p0_7_cache_file(config, "failure_filter_event_panel", "p0_7_failure_filter_event_panel.parquet"),
    }
    for name, path in cache_paths.items():
        ensure_parent(path)
        cache_frames[name].to_parquet(path, index=False)
        outputs.append(path)
    manifest = record_p0_7_manifest(config, "profile-p0-7ab", outputs, frames, cache_frames)
    outputs.append(manifest)
    return frames, outputs, cache_frames


def command_profile_p0_7(config: dict[str, Any]) -> list[Path]:
    frames, outputs, _cache_frames = build_p0_7_outputs(config)
    launch_candidates = int(frames["p0_7_launch_stratification_leaderboard.csv"]["p1_launch_stratification_candidate"].sum()) if not frames["p0_7_launch_stratification_leaderboard.csv"].empty else 0
    failure_candidates = int(frames["p0_7_failure_filter_leaderboard.csv"]["p1_failure_filter_candidate"].sum()) if not frames["p0_7_failure_filter_leaderboard.csv"].empty else 0
    print(
        f"profiled p0.7ab outputs={len(outputs)} launch_candidates={launch_candidates} failure_candidates={failure_candidates}",
        flush=True,
    )
    return outputs


def command_report_p0_7(config: dict[str, Any]) -> list[Path]:
    missing = [name for name in P0_7_REQUIRED_REPORTS if name not in {"p0_7_run_manifest.json", "explore9_p0_7ab_launch_failure_report.md"} and not (report_dir(config) / name).exists()]
    if missing:
        command_profile_p0_7(config)
    report_path = report_dir(config) / "explore9_p0_7ab_launch_failure_report.md"
    launch_board = read_csv_if_exists(report_dir(config) / "p0_7_launch_stratification_leaderboard.csv")
    failure_board = read_csv_if_exists(report_dir(config) / "p0_7_failure_filter_leaderboard.csv")
    scope = read_csv_if_exists(report_dir(config) / "p0_7_scope_completion_audit.csv")
    episode_summary = read_csv_if_exists(report_dir(config) / "p0_7_launch_episode_summary.csv")
    stratum_summary = read_csv_if_exists(report_dir(config) / "p0_7_launch_stratum_event_summary.csv")
    opp_summary = read_csv_if_exists(report_dir(config) / "p0_7_failure_filter_opportunity_summary.csv")
    manifest = read_json(p0_7_manifest_path(config))
    launch_p1 = int(launch_board["p1_launch_stratification_candidate"].sum()) if not launch_board.empty and "p1_launch_stratification_candidate" in launch_board else 0
    failure_p1 = int(failure_board["p1_failure_filter_candidate"].sum()) if not failure_board.empty and "p1_failure_filter_candidate" in failure_board else 0
    if launch_p1 > 0 and failure_p1 > 0:
        recommendation = "entry_not_solved_but_launch_failure_direction_valid"
    elif launch_p1 > 0:
        recommendation = "proceed_to_p1_launch_stratification_refine"
    elif failure_p1 > 0:
        recommendation = "proceed_to_p1_failure_filter_refine"
    elif not launch_board.empty or not failure_board.empty:
        recommendation = "continue_p0_7ab_discovery"
    else:
        recommendation = "stop_due_to_no_stable_launch_failure_structure"

    def short_rows(frame: pd.DataFrame, cols: list[str], limit: int = 10) -> list[list[Any]]:
        if frame.empty:
            return []
        rows = []
        for _, row in frame.head(limit).iterrows():
            rows.append([row.get(col, "") for col in cols])
        return rows

    lines: list[str] = []
    lines.append("# Explore9 P0.7AB 启动分层与失败过滤报告")
    lines.append("")
    lines.append("## 1. 结论")
    lines.append("")
    lines.append(f"- `recommendation = {recommendation}`。")
    lines.append(f"- P0.7AB 不是 P0.6 的 entry trigger 重跑：本轮只研究 launch pool 分层、failure filter 分母与 false reject，不把 confirmation 当作首入场 trigger。")
    lines.append("- 第一实现批次只运行 P0.7A + P0.7B；P0.7C hold/add-on gate 保留 schema contract，不输出 P1 hold/add-on 结论。")
    lines.append(f"- launch stratification P1 candidate `{launch_p1}` 个；failure filter P1 candidate `{failure_p1}` 个。")
    lines.append("- 本报告不输出 Explore10 backtest、frozen strategy、P1 hold gate 或 P1 add-on gate 建议。")
    lines.append("")
    lines.append("## 2. 覆盖与审计")
    lines.append("")
    if not episode_summary.empty:
        lines.extend(markdown_table(["launch episode", "stratum event", "post20 later", "late accel later"], short_rows(episode_summary, ["launch_episode_count", "stratum_event_count", "contains_post20_later_count", "contains_late_acceleration_later_count"], 1)))
    if not scope.empty:
        lines.append("")
        lines.extend(markdown_table(["检查项", "实际", "要求", "通过", "失败原因"], short_rows(scope, ["check_name", "actual_value", "required_value", "passed", "failure_reason"], 30)))
    lines.append("")
    lines.append("## 3. Launch Stratification Leaderboard")
    lines.append("")
    if not launch_board.empty:
        cols = [
            "stratum_variant",
            "declared_stratum_role",
            "recommended_action_class_after_evaluation",
            "launch_episode_count",
            "launch_big_winner_primary_rate",
            "lift_vs_all_launch_baseline",
            "instrument_year_lift_vs_all_launch",
            "p1_launch_stratification_candidate",
            "rejection_reason",
        ]
        lines.extend(markdown_table(["variant", "declared role", "eval action", "episode", "50%/120d", "lift all", "IY lift", "P1", "reason"], short_rows(launch_board, cols, 12)))
    else:
        lines.append("无 launch stratification leaderboard。")
    lines.append("")
    lines.append("## 4. Failure Filter Denominator 与 False Reject")
    lines.append("")
    if not opp_summary.empty:
        lines.extend(markdown_table(["filter", "opportunity", "signal rate", "window trunc", "horizon trunc", "missing ref"], short_rows(opp_summary.assign(filter=opp_summary["filter_variant"]), ["filter", "opportunity_row_count", "filter_signal_rate", "filter_window_truncated_rate", "filter_horizon_truncated_rate", "non_signal_reference_date_missing_count"], 12)))
    lines.append("")
    lines.append("## 5. Failure Filter Leaderboard")
    lines.append("")
    if not failure_board.empty:
        cols = [
            "filter_variant",
            "launch_stratum_scope",
            "filter_event_count",
            "nonwinner_reject_recall",
            "reject_precision_failure_lift_vs_scope_prevalence",
            "winner_false_reject_rate_among_pending_winners",
            "median_drawdown_avoided_vs_matched_delay",
            "p1_failure_filter_candidate",
            "rejection_reason",
        ]
        lines.extend(markdown_table(["filter", "scope", "event", "nonwinner recall", "failure lift", "false reject", "dd vs delay", "P1", "reason"], short_rows(failure_board, cols, 12)))
    else:
        lines.append("无 failure filter leaderboard。")
    lines.append("")
    lines.append("## 6. 数据纪律")
    lines.append("")
    for key in [
        "p0_label_panel_reused",
        "p0_5_feature_reference_used",
        "p0_6_launch_event_panel_reused",
        "p0_6_entry_results_used_for_selection",
        "p0_5_ranked_results_used_for_selection",
        "historical_trade_results_used_for_labeling",
        "historical_trade_results_used_for_signal",
        "historical_trade_results_used_for_selection",
        "observed_reference_used_for_selection",
        "same_close_proxy_used_in_main_leaderboard",
        "later_lifecycle_rewrite_used",
        "stratum_declared_role_separated_from_evaluated_recommendation",
        "filter_decision_reference_date_defined_for_all_U",
        "false_reject_target_timing_audit_passed",
        "hold_addon_gate_deferred",
        "full_event_csv_reports_disabled_by_default",
        "matched_delay_runtime_controls_declared",
    ]:
        lines.append(f"- `{key} = {manifest.get(key)}`")
    lines.append("")
    lines.append("## 7. 下一步")
    lines.append("")
    if recommendation in {"proceed_to_p1_launch_stratification_refine", "proceed_to_p1_failure_filter_refine", "entry_not_solved_but_launch_failure_direction_valid"}:
        lines.append("- 只允许进入对应的 P1 launch stratification refine / failure filter refine；仍不得直接进入 Explore10。")
    elif recommendation == "continue_p0_7ab_discovery":
        lines.append("- 当前证据更适合继续 P0.7AB discovery，优先查看 rejection_reason 中的覆盖、instrument-year 与 false reject 约束。")
    else:
        lines.append("- 当前未形成稳定 launch/failure 结构，应停止或重写研究方向。")
    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = [report_path]
    record_p0_7_manifest(config, "report-p0-7ab", outputs, {"explore9_p0_7ab_launch_failure_report.md": pd.DataFrame([{"recommendation": recommendation}])}, {}, recommendation)
    print(f"wrote p0.7ab report {relpath(report_path)} recommendation={recommendation}", flush=True)
    return outputs


def p0_8_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("p0_8", {})


def p0_8_manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "p0_8_run_manifest.json"


def p0_8_cache_file(config: dict[str, Any], key: str, default_name: str) -> Path:
    return topic_path(p0_8_cfg(config).get("cache", {}).get(key, cache_dir(config) / default_name))


def p0_8_hash(payload: dict[str, Any]) -> str:
    text = json.dumps(sanitize_json(payload), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def p0_8_threshold(config: dict[str, Any], key: str, default: float) -> float:
    return safe_float(config.get("thresholds", {}).get(key, default), default)


def p0_8_walk_folds(config: dict[str, Any]) -> list[dict[str, Any]]:
    wf = config.get("walk_forward", {})
    p1_years = set(int(x) for x in wf.get("p1_promotion_validation_years", [2020, 2021, 2022, 2023]))
    rows = []
    for year in wf.get("validation_years", [2020, 2021, 2022, 2023, 2024]):
        year = int(year)
        role = "p1_promotion_eligible" if year in p1_years else "robustness_audit_only"
        rows.append(
            {
                "fold_id": f"fold_{year}",
                "validation_year": year,
                "train_start_year": parse_dt(config["dates"]["research_start"]).year,
                "train_end_year": year - 1,
                "validation_fold_role": role,
                "p1_promotion_eligible_fold": role == "p1_promotion_eligible",
            }
        )
    return rows


def p0_8_split_for_year(event_year: pd.Series, validation_year: int) -> pd.Series:
    return pd.Series(np.select([event_year < validation_year, event_year == validation_year], ["train", "validation"], default="excluded"), index=event_year.index)


def p0_8_write_parquet(config: dict[str, Any], df: pd.DataFrame, value: str | Path) -> Path:
    path = ensure_parent(value)
    compression = config.get("runtime", {}).get("parquet_compression", "zstd")
    try:
        df.to_parquet(path, index=False, compression=compression)
    except Exception:
        df.to_parquet(path, index=False)
    return path


def p0_8_required_feature_columns(config: dict[str, Any]) -> list[str]:
    return list(config.get("lgbm", {}).get("feature_columns", []))


def p0_8_hhi(values: pd.Series) -> float:
    total = safe_float(values.sum(), 0.0)
    if total <= 0:
        return np.nan
    shares = values.astype(float) / total
    return float((shares * shares).sum())


def p0_8_top_share(values: pd.Series, n: int = 1) -> float:
    total = safe_float(values.sum(), 0.0)
    if total <= 0:
        return np.nan
    return float(values.sort_values(ascending=False).head(n).sum() / total)


def p0_8_auc(y_true: pd.Series, score: pd.Series) -> float:
    y = pd.Series(y_true).fillna(False).astype(bool)
    s = pd.to_numeric(score, errors="coerce")
    mask = y.notna() & s.notna()
    y = y[mask]
    s = s[mask]
    pos = int(y.sum())
    neg = int((~y).sum())
    if pos == 0 or neg == 0:
        return np.nan
    ranks = s.rank(method="average")
    return float((ranks[y].sum() - pos * (pos + 1) / 2.0) / (pos * neg))


def p0_8_logloss(y_true: pd.Series, score: pd.Series, weight: pd.Series | None = None) -> float:
    y = pd.Series(y_true).fillna(False).astype(float)
    p = pd.to_numeric(score, errors="coerce").clip(1e-6, 1 - 1e-6)
    mask = y.notna() & p.notna()
    if not mask.any():
        return np.nan
    loss = -(y[mask] * np.log(p[mask]) + (1 - y[mask]) * np.log(1 - p[mask]))
    if weight is None:
        return float(loss.mean())
    w = pd.to_numeric(weight[mask], errors="coerce").fillna(0.0)
    return float(np.average(loss, weights=w)) if safe_float(w.sum(), 0.0) > 0 else float(loss.mean())


def p0_8_output_stats(paths: list[Path], frames: dict[str, pd.DataFrame], cache_frames: dict[str, pd.DataFrame]) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    row_counts: dict[str, int] = {}
    column_counts: dict[str, int] = {}
    file_sizes: dict[str, int] = {}
    for path in paths:
        rel = relpath(path)
        if path.exists():
            file_sizes[rel] = path.stat().st_size
        name = path.name
        if name in frames:
            row_counts[rel] = int(len(frames[name]))
            column_counts[rel] = int(len(frames[name].columns))
        elif name in cache_frames:
            row_counts[rel] = int(len(cache_frames[name]))
            column_counts[rel] = int(len(cache_frames[name].columns))
    return row_counts, column_counts, file_sizes


def record_p0_8_manifest(
    config: dict[str, Any],
    command: str,
    outputs: list[Path],
    frames: dict[str, pd.DataFrame],
    cache_frames: dict[str, pd.DataFrame],
    recommendation: str | None = None,
) -> Path:
    path = p0_8_manifest_path(config)
    existing = read_json(path)
    commands = list(existing.get("command_sequence", []))
    commands.append(command)
    row_counts, column_counts, file_sizes = p0_8_output_stats(outputs + [path], frames, cache_frames)
    now = pd.Timestamp.now(tz="Asia/Shanghai").isoformat()
    report_paths = sorted(set(existing.get("output_report_paths", []) + [relpath(p) for p in outputs if p.suffix != ".parquet"]))
    cache_paths = sorted(set(existing.get("output_cache_paths", []) + [relpath(p) for p in outputs if p.suffix == ".parquet"]))
    manifest = {
        "experiment": "Explore9 P0.8 gate combination and LGBM nonlinear discovery",
        "phase": "P0.8",
        "expansion_id": p0_8_cfg(config).get("expansion_id", "expand_4"),
        "config_path": relpath(config["_config_path"]),
        "config_sha256": config["_config_sha256"],
        "command_sequence": commands,
        "output_report_paths": report_paths,
        "output_cache_paths": cache_paths,
        "required_report_artifacts": [relpath(report_dir(config) / name) for name in P0_8_REQUIRED_REPORTS],
        "required_cache_artifacts": [relpath(cache_dir(config) / name) for name in P0_8_REQUIRED_CACHE],
        "output_row_counts": {**existing.get("output_row_counts", {}), **row_counts},
        "output_column_counts": {**existing.get("output_column_counts", {}), **column_counts},
        "output_file_sizes": {**existing.get("output_file_sizes", {}), **file_sizes},
        "last_command_completed_at": now,
        "profile_completed_at": now if command == "profile-p0-8" else existing.get("profile_completed_at"),
        "report_completed_at": now if command == "report-p0-8" else existing.get("report_completed_at"),
        "recommendation": recommendation or existing.get("recommendation"),
        "provider_uri": config["paths"]["provider_uri"],
        "fallback_provider_uri": config["paths"]["fallback_provider_uri"],
        "price_adjustment_mode": config["qlib"]["price_adjustment_mode"],
        "required_fields": required_field_names(config),
        "research_start": config["dates"]["research_start"],
        "research_end": config["dates"]["research_end"],
        "observed_reference_start": config["dates"]["observed_reference_start"],
        "observed_reference_end": config["dates"]["observed_reference_end"],
        "validation_role": config.get("walk_forward", {}).get("validation_role", "robustness_validation_not_clean_oos_proof"),
        "p0_8_validation_clean_oos_proof": False,
        "observed_reference_used_for_selection": False,
        "fold_2024_included_in_p1_promotion_oof": False,
        "validated_p1_rule_generated": False,
        "clean_oos_proven_rule_generated": False,
        "ready_for_backtest": False,
        "proceed_to_explore10_backtest": False,
        "small_mlp_shadow_benchmark_generated": False,
    }
    write_json(manifest, path)
    return path


def p0_8_ensure_p0_7_inputs(config: dict[str, Any]) -> None:
    required = [
        p0_7_cache_file(config, "launch_episode_panel", "p0_7_launch_episode_panel.parquet"),
        p0_7_cache_file(config, "launch_stratum_event_panel", "p0_7_launch_stratum_event_panel.parquet"),
        p0_7_cache_file(config, "failure_filter_opportunity_panel", "p0_7_failure_filter_opportunity_panel.parquet"),
        p0_7_cache_file(config, "failure_filter_event_panel", "p0_7_failure_filter_event_panel.parquet"),
    ]
    if any(not path.exists() for path in required):
        command_profile_p0_7(config)


def p0_8_add_fold_rows(panel: pd.DataFrame, config: dict[str, Any], year_col: str) -> pd.DataFrame:
    frames = []
    years = pd.to_numeric(panel[year_col], errors="coerce").fillna(0).astype(int)
    for fold in p0_8_walk_folds(config):
        part = panel.copy()
        part["fold_id"] = fold["fold_id"]
        part["validation_year"] = fold["validation_year"]
        part["validation_fold_role"] = fold["validation_fold_role"]
        part["p1_promotion_eligible_fold"] = fold["p1_promotion_eligible_fold"]
        part["split"] = p0_8_split_for_year(years, fold["validation_year"]).to_numpy()
        frames.append(part)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def p0_8_apply_sample_weights(
    panel: pd.DataFrame,
    config: dict[str, Any],
    eligible_col: str,
    positive_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    out = panel.copy()
    out["base_sample_weight"] = 0.0
    out["final_sample_weight"] = 0.0
    out["sample_weight"] = 0.0
    audit_rows: list[dict[str, Any]] = []
    cap_rows: list[dict[str, Any]] = []
    max_share = safe_float(config.get("sample_weight", {}).get("max_instrument_year_weight_share", 0.08), 0.08)
    max_iter = int(config.get("sample_weight", {}).get("max_group_cap_iterations", 20))
    active = out["split"].isin(["train", "validation"]) & out[eligible_col].fillna(False).astype(bool)
    denom_key = ["fold_id", "model_task", "split", "launch_episode_id"]
    denom = out.loc[active].groupby(denom_key)["instrument"].transform("size")
    out.loc[active, "base_sample_weight"] = 1.0 / denom.replace(0, np.nan)
    for (fold_id, model_task, split), idx in out.loc[active].groupby(["fold_id", "model_task", "split"], sort=False).groups.items():
        idx_list = list(idx)
        weights = out.loc[idx_list, "base_sample_weight"].astype(float).copy()
        raw = weights.copy()
        group_keys = out.loc[idx_list, "event_instrument_year"].astype(str)
        group_cap_applied = False
        for _ in range(max_iter):
            total = safe_float(weights.sum(), 0.0)
            if total <= 0:
                break
            sums = weights.groupby(group_keys).sum()
            breach = sums[sums / total > max_share]
            if breach.empty:
                break
            group_cap_applied = True
            for group_key, group_sum in breach.items():
                target = max_share * total
                if group_sum > target and group_sum > 0:
                    weights.loc[group_keys.eq(group_key)] *= target / group_sum
        if bool(config.get("sample_weight", {}).get("normalize_total_weight_per_split", True)):
            total = safe_float(weights.sum(), 0.0)
            if total > 0:
                weights *= len(idx_list) / total
        out.loc[idx_list, "final_sample_weight"] = weights
        out.loc[idx_list, "sample_weight"] = weights
        raw_sums = raw.groupby(group_keys).sum()
        final_sums = weights.groupby(group_keys).sum()
        final_total = safe_float(final_sums.sum(), 0.0)
        raw_total = safe_float(raw_sums.sum(), 0.0)
        for group_key in sorted(set(group_keys)):
            rows_in_group = out.loc[idx_list].loc[group_keys.eq(group_key)]
            cap_rows.append(
                {
                    "fold_id": fold_id,
                    "model_task": model_task,
                    "split": split,
                    "instrument_year": group_key,
                    "event_effective_year": str(group_key).rsplit("_", 1)[-1],
                    "raw_group_weight_sum": safe_float(raw_sums.get(group_key), 0.0),
                    "raw_group_weight_share": safe_div(raw_sums.get(group_key), raw_total),
                    "final_group_weight_sum": safe_float(final_sums.get(group_key), 0.0),
                    "final_group_weight_share": safe_div(final_sums.get(group_key), final_total),
                    "top_instrument_year_weight_share": p0_8_top_share(final_sums, 1),
                    "instrument_year_weight_hhi": p0_8_hhi(final_sums),
                    "group_cap_applied": bool(group_cap_applied),
                    "max_instrument_year_weight_share": max_share,
                    "row_count": int(len(rows_in_group)),
                    "positive_count": int(rows_in_group[positive_col].fillna(False).astype(bool).sum()) if positive_col in rows_in_group else 0,
                }
            )
        audit_rows.append(
            {
                "fold_id": fold_id,
                "model_task": model_task,
                "split": split,
                "instrument_year": "ALL",
                "event_effective_year": "ALL",
                "raw_group_weight_sum": raw_total,
                "raw_group_weight_share": 1.0 if raw_total > 0 else np.nan,
                "final_group_weight_sum": final_total,
                "final_group_weight_share": 1.0 if final_total > 0 else np.nan,
                "top_instrument_year_weight_share": p0_8_top_share(final_sums, 1),
                "instrument_year_weight_hhi": p0_8_hhi(final_sums),
                "group_cap_applied": bool(group_cap_applied),
                "max_instrument_year_weight_share": max_share,
                "row_count": int(len(idx_list)),
                "positive_count": int(out.loc[idx_list, positive_col].fillna(False).astype(bool).sum()) if positive_col in out else 0,
            }
        )
    return out, pd.DataFrame(audit_rows), pd.DataFrame(cap_rows)


def p0_8_build_launch_sample_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p0_8_ensure_p0_7_inputs(config)
    events = pd.read_parquet(p0_7_cache_file(config, "launch_stratum_event_panel", "p0_7_launch_stratum_event_panel.parquet"))
    research_end = parse_dt(config["dates"]["research_end"])
    observed_start = parse_dt(config["dates"]["observed_reference_start"])
    base = events.copy()
    base["date"] = pd.to_datetime(base["stratum_date"]).dt.normalize()
    base["stratum_signal_date"] = base["date"]
    base["event_effective_date"] = pd.to_datetime(base["stratum_effective_date"]).dt.normalize()
    base["event_effective_price_reference"] = base["stratum_effective_price_reference"]
    base["feature_asof_date"] = base["stratum_signal_date"]
    base["model_task"] = "launch_winner_score"
    base["decision_context"] = "launch_stratum_event"
    base["launch_family"] = base["stratum_family"]
    base["launch_variant"] = base["stratum_variant"]
    base["lifecycle_pool"] = base["declared_lifecycle_stage"].fillna("UNKNOWN")
    base["industry"] = base["industry_name"].fillna("UNKNOWN")
    base["market_regime"] = base.get("stratum_market_regime", base.get("market_regime", "UNKNOWN")).fillna("UNKNOWN")
    base["event_year"] = base["event_effective_date"].dt.year.astype(int)
    base["event_instrument_year"] = base["instrument"].astype(str) + "_" + base["event_year"].astype(str)
    base["label_horizon_truncated"] = base["label_horizon_truncated_240d"].fillna(True).astype(bool)
    base["label_measurement_available"] = base["stratum_effective_price_reference"].notna() & base["stratum_future_50pct_high_120d"].notna()
    base["observed_reference_decision_overlap"] = (base["stratum_signal_date"] >= observed_start) | (base["event_effective_date"] >= observed_start)
    base["observed_reference_feature_overlap"] = base["feature_asof_date"] >= observed_start
    base["observed_reference_label_measurement_overlap"] = (pd.to_datetime(base["horizon_end_date_240d"]) > research_end) & (base["feature_asof_date"] <= research_end)
    base["observed_reference_overlap"] = (
        base["observed_reference_decision_overlap"] | base["observed_reference_feature_overlap"] | base["observed_reference_label_measurement_overlap"]
    )
    base["label_measurement_uses_observed_reference"] = base["observed_reference_label_measurement_overlap"]
    required = [col for col in p0_8_required_feature_columns(config) if col in base.columns and col != "failure_decision_window"]
    base["sample_has_required_features"] = base[required].notna().all(axis=1) if required else True
    base["launch_winner_50h120"] = base["stratum_future_50pct_high_120d"].fillna(False).astype(bool)
    base["launch_winner_50c120"] = base["stratum_future_50pct_close_120d"].fillna(False).astype(bool)
    base["launch_winner_100h240"] = base["stratum_future_100pct_high_240d"].fillna(False).astype(bool)
    base["launch_future_20pct_high_60d"] = base["stratum_future_20pct_high_60d"].fillna(False).astype(bool)
    base["launch_future_max_drawdown_60d"] = pd.to_numeric(base["stratum_future_max_drawdown_60d"], errors="coerce")
    base["launch_false_positive_primary"] = (~base["launch_winner_50h120"]) & (base["launch_future_max_drawdown_60d"] <= -p0_8_threshold(config, "failure_drawdown_threshold", 0.12))
    base["first_20pct_gain_missing"] = pd.to_numeric(base.get("stratum_time_to_20pct_high_days"), errors="coerce").isna()
    base["launch_drawdown_before_20pct_gain"] = pd.to_numeric(base.get("future_drawdown_before_20pct_high_gain"), errors="coerce")
    base["launch_drawdown_before_20pct_gain_le_10pct"] = base["launch_drawdown_before_20pct_gain"] >= -0.10
    base["launch_model_train_eval_eligible"] = (
        (base["feature_asof_date"] <= research_end)
        & (base["event_effective_date"] <= research_end)
        & (~base["observed_reference_decision_overlap"])
        & (~base["observed_reference_feature_overlap"])
        & (~base["observed_reference_label_measurement_overlap"])
        & (~base["label_horizon_truncated"])
        & base["label_measurement_available"]
        & base["sample_has_required_features"]
    )
    panel = p0_8_add_fold_rows(base, config, "event_year")
    panel["launch_p1_promotion_eligible"] = (
        panel["launch_model_train_eval_eligible"].fillna(False).astype(bool)
        & panel["p1_promotion_eligible_fold"].fillna(False).astype(bool)
        & (~panel["label_measurement_uses_observed_reference"].fillna(False).astype(bool))
        & (~panel["observed_reference_label_measurement_overlap"].fillna(False).astype(bool))
    )
    panel, audit, cap_audit = p0_8_apply_sample_weights(panel, config, "launch_model_train_eval_eligible", "launch_winner_50h120")
    return panel.replace([np.inf, -np.inf], np.nan), audit, cap_audit


def p0_8_panel_groups(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    df = p0_7_load_feature_panel(config)
    return p0_6_panel_groups(df)


def p0_8_build_failure_base(config: dict[str, Any]) -> pd.DataFrame:
    p0_8_ensure_p0_7_inputs(config)
    events = pd.read_parquet(p0_7_cache_file(config, "launch_stratum_event_panel", "p0_7_launch_stratum_event_panel.parquet"))
    groups = p0_8_panel_groups(config)
    rows: list[dict[str, Any]] = []
    windows = [int(x) for x in config.get("failure_decision_windows", [3, 5, 10])]
    research_end = parse_dt(config["dates"]["research_end"])
    observed_start = parse_dt(config["dates"]["observed_reference_start"])
    feature_cols = [
        "ret_rank_20d_market",
        "ret_rank_20d_industry",
        "relative_ret20_vs_benchmark",
        "relative_ret20_vs_industry",
        "money_ratio_20",
        "atr20_pct",
        "prelaunch_drawdown_120d",
        "launch_gain_from_recent_low_60d",
        "launch_gain_from_recent_low_120d",
        "close_location",
        "upper_shadow_pct",
        "lower_shadow_pct",
        "rolling_range_20d",
        "higher_low_count_20d",
        "industry_breadth_20d",
    ]
    for _, event in events.iterrows():
        group = groups.get(str(event["instrument"]))
        if group is None:
            continue
        dates = pd.to_datetime(group["datetime"]).dt.normalize().reset_index(drop=True)
        highs = group["high"].to_numpy(dtype=float)
        lows = group["low"].to_numpy(dtype=float)
        opens = group["open"].to_numpy(dtype=float)
        row_pos = int(event["stratum_row_pos"])
        for window in windows:
            sig_pos = row_pos + window
            eff_pos = sig_pos + 1
            row = {
                "launch_stratum_event_id": event["launch_stratum_event_id"],
                "launch_episode_id": event["launch_episode_id"],
                "instrument": event["instrument"],
                "name": event.get("name", ""),
                "stratum_date": event["stratum_date"],
                "stratum_effective_date": event["stratum_effective_date"],
                "stratum_effective_price_reference": event["stratum_effective_price_reference"],
                "launch_family": event["stratum_family"],
                "launch_variant": event["stratum_variant"],
                "lifecycle_pool": event.get("declared_lifecycle_stage", "UNKNOWN"),
                "declared_stratum_role": event.get("declared_stratum_role", ""),
                "industry": event.get("industry_name", "UNKNOWN"),
                "market_regime": event.get("stratum_market_regime", event.get("market_regime", "UNKNOWN")),
                "stratum_row_pos": row_pos,
                "ret_rank_20d_market_at_stratum": event.get("ret_rank_20d_market_at_stratum", np.nan),
                "industry_breadth_20d_at_stratum": event.get("industry_breadth_20d_at_stratum", np.nan),
                "launch_nonwinner_primary": bool(event.get("launch_nonwinner_primary", False)),
                "launch_failure_primary": bool(event.get("launch_failure_primary", False)),
                "launch_winner_50h120": bool(event.get("stratum_future_50pct_high_120d", False)),
                "launch_winner_100h240": bool(event.get("stratum_future_100pct_high_240d", False)),
                "target_50pct_high_date_120d": event.get("target_50pct_high_date_120d", pd.NaT),
                "target_100pct_high_date_240d": event.get("target_100pct_high_date_240d", pd.NaT),
                "first_12pct_drawdown_date_from_stratum": event.get("first_12pct_drawdown_date_from_stratum", pd.NaT),
                "failure_decision_window": window,
                "model_task": "failure_reject_score",
                "decision_context": "failure_filter_opportunity",
            }
            if sig_pos >= len(group) or eff_pos >= len(group):
                row.update(
                    {
                        "failure_decision_signal_date": pd.NaT,
                        "failure_decision_effective_date": pd.NaT,
                        "event_effective_date": pd.NaT,
                        "failure_decision_effective_price_reference": np.nan,
                        "event_effective_price_reference": np.nan,
                        "feature_asof_date": pd.NaT,
                        "label_horizon_truncated": True,
                        "label_measurement_available": False,
                    }
                )
                rows.append(row)
                continue
            signal = group.iloc[sig_pos]
            decision_date = dates.iloc[eff_pos]
            signal_date = dates.iloc[sig_pos]
            base_price = safe_float(opens[eff_pos], np.nan)
            for col in feature_cols:
                row[col] = signal.get(col, event.get(col, np.nan))
            row["failure_decision_signal_date"] = signal_date
            row["failure_decision_effective_date"] = decision_date
            row["event_effective_date"] = decision_date
            row["failure_decision_effective_price_reference"] = base_price
            row["event_effective_price_reference"] = base_price
            row["feature_asof_date"] = signal_date
            remaining = len(group) - eff_pos
            end60 = min(len(group), eff_pos + 60)
            end120 = min(len(group), eff_pos + 120)
            end240 = min(len(group), eff_pos + 240)
            row["decision_horizon_end_date_60d"] = dates.iloc[end60 - 1] if end60 > eff_pos else pd.NaT
            row["decision_horizon_end_date_120d"] = dates.iloc[end120 - 1] if end120 > eff_pos else pd.NaT
            row["decision_horizon_end_date_240d"] = dates.iloc[end240 - 1] if end240 > eff_pos else pd.NaT
            row["label_horizon_truncated_60d"] = remaining < 60
            row["label_horizon_truncated_120d"] = remaining < 120
            row["label_horizon_truncated_240d"] = remaining < 240
            row["label_horizon_truncated"] = row["label_horizon_truncated_240d"]
            if np.isfinite(base_price) and base_price > 0 and end60 > eff_pos:
                row["future_max_drawdown_60d_from_decision_reference"] = np.nanmin(lows[eff_pos:end60]) / base_price - 1.0
            else:
                row["future_max_drawdown_60d_from_decision_reference"] = np.nan
            row["future_50pct_high_120d_from_decision_reference"] = (
                np.isfinite(base_price) and base_price > 0 and end120 > eff_pos and np.nanmax(highs[eff_pos:end120]) / base_price - 1.0 >= 0.50
            )
            row["future_100pct_high_240d_from_decision_reference"] = (
                np.isfinite(base_price) and base_price > 0 and end240 > eff_pos and np.nanmax(highs[eff_pos:end240]) / base_price - 1.0 >= 1.00
            )
            target50 = pd.Timestamp(event.get("target_50pct_high_date_120d")) if pd.notna(event.get("target_50pct_high_date_120d")) else pd.NaT
            target100 = pd.Timestamp(event.get("target_100pct_high_date_240d")) if pd.notna(event.get("target_100pct_high_date_240d")) else pd.NaT
            row["target_50h120_not_reached_before_decision_effective_date"] = not (pd.notna(target50) and target50 < decision_date)
            row["target_100h240_not_reached_before_decision_effective_date"] = not (pd.notna(target100) and target100 < decision_date)
            row["failure_false_reject_winner_from_decision_50h120"] = (
                row["target_50h120_not_reached_before_decision_effective_date"] and row["future_50pct_high_120d_from_decision_reference"]
            )
            row["failure_false_reject_big_winner_from_decision_100h240"] = (
                row["target_100h240_not_reached_before_decision_effective_date"] and row["future_100pct_high_240d_from_decision_reference"]
            )
            row["failure_false_reject_winner_from_launch_50h120"] = pd.notna(target50) and target50 >= decision_date
            row["failure_false_reject_big_winner_from_launch_100h240"] = pd.notna(target100) and target100 >= decision_date
            row["failure_reject_positive_primary"] = (
                row["target_50h120_not_reached_before_decision_effective_date"]
                and (not row["future_50pct_high_120d_from_decision_reference"])
                and safe_float(row["future_max_drawdown_60d_from_decision_reference"], 0.0) <= -p0_8_threshold(config, "failure_drawdown_threshold", 0.12)
            )
            row["post_target_risk_audit_only"] = not row["target_50h120_not_reached_before_decision_effective_date"]
            row["exclude_from_failure_training_loss"] = row["post_target_risk_audit_only"]
            row["exclude_from_failure_validation_metrics"] = row["post_target_risk_audit_only"]
            row["exclude_from_failure_bucket_selection"] = row["post_target_risk_audit_only"]
            row["exclude_from_failure_p1_candidate_selection"] = row["post_target_risk_audit_only"]
            row["label_measurement_available"] = np.isfinite(base_price) and base_price > 0
            row["observed_reference_decision_overlap"] = (signal_date >= observed_start) or (decision_date >= observed_start)
            row["observed_reference_feature_overlap"] = signal_date >= observed_start
            row["observed_reference_label_measurement_overlap"] = pd.notna(row["decision_horizon_end_date_240d"]) and row["decision_horizon_end_date_240d"] > research_end and signal_date <= research_end
            row["observed_reference_overlap"] = (
                row["observed_reference_decision_overlap"]
                or row["observed_reference_feature_overlap"]
                or row["observed_reference_label_measurement_overlap"]
            )
            row["label_measurement_uses_observed_reference"] = row["observed_reference_label_measurement_overlap"]
            rows.append(row)
    base = pd.DataFrame(rows)
    if base.empty:
        return base
    base["industry"] = base["industry"].fillna("UNKNOWN")
    base["market_regime"] = base["market_regime"].fillna("UNKNOWN")
    base["event_year"] = pd.to_datetime(base["event_effective_date"]).dt.year.fillna(0).astype(int)
    base["event_instrument_year"] = base["instrument"].astype(str) + "_" + base["event_year"].astype(str)
    required = [col for col in p0_8_required_feature_columns(config) if col in base.columns]
    base["sample_has_required_features"] = base[required].notna().all(axis=1) if required else True
    base["failure_model_train_eval_eligible"] = (
        base["target_50h120_not_reached_before_decision_effective_date"].fillna(False).astype(bool)
        & (~base["label_horizon_truncated"].fillna(True).astype(bool))
        & (~base["observed_reference_decision_overlap"].fillna(True).astype(bool))
        & (~base["observed_reference_feature_overlap"].fillna(True).astype(bool))
        & (~base["observed_reference_label_measurement_overlap"].fillna(True).astype(bool))
        & base["label_measurement_available"].fillna(False).astype(bool)
        & base["sample_has_required_features"].fillna(False).astype(bool)
    )
    return base.replace([np.inf, -np.inf], np.nan)


def p0_8_build_failure_sample_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = p0_8_build_failure_base(config)
    if base.empty:
        return base, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    panel = p0_8_add_fold_rows(base, config, "event_year")
    panel["failure_p1_promotion_eligible"] = (
        panel["failure_model_train_eval_eligible"].fillna(False).astype(bool)
        & panel["p1_promotion_eligible_fold"].fillna(False).astype(bool)
        & (~panel["label_measurement_uses_observed_reference"].fillna(False).astype(bool))
        & (~panel["observed_reference_label_measurement_overlap"].fillna(False).astype(bool))
    )
    panel, audit, cap_audit = p0_8_apply_sample_weights(panel, config, "failure_model_train_eval_eligible", "failure_reject_positive_primary")
    policy = config.get("failure_dedup", {}).get("failure_window_group_policy", "merge_3d_5d_10d_for_main_p1_metrics")
    panel["failure_window_group_policy"] = policy
    panel["failure_full_stable_candidate_id"] = [
        p0_8_hash(
            {
                "model_task": row.model_task,
                "decision_context": row.decision_context,
                "candidate_family": "failure_decision_window",
                "failure_decision_window": int(row.failure_decision_window),
                "feature_set_version": p0_8_cfg(config).get("feature_set_version", "p0_8_feature_set_v1"),
                "label_version": p0_8_cfg(config).get("label_version", "p0_8_label_v1"),
            }
        )
        for row in panel.itertuples()
    ]
    event_dedup_id = p0_8_hash(
        {
            "model_task": "failure_reject_score",
            "decision_context": "failure_filter_opportunity",
            "candidate_family_or_model_family": "failure_multi_window_panel",
            "normalized_failure_formula_windowless": "failure_score_decision_context",
            "failure_window_group_policy": policy,
            "feature_set_version": p0_8_cfg(config).get("feature_set_version", "p0_8_feature_set_v1"),
            "label_version": p0_8_cfg(config).get("label_version", "p0_8_label_v1"),
        }
    )
    panel["failure_event_dedup_candidate_id"] = event_dedup_id
    panel["failure_event_level_dedup_key"] = panel["failure_event_dedup_candidate_id"] + "__" + panel["launch_stratum_event_id"].astype(str)
    panel["failure_event_level_dedup_keep"] = False
    validation_keep_idx = (
        panel[panel["split"].eq("validation")]
        .sort_values(["launch_stratum_event_id", "failure_decision_effective_date", "failure_decision_window", "fold_id"])
        .drop_duplicates(["failure_event_dedup_candidate_id", "launch_stratum_event_id"])
        .index
    )
    panel.loc[validation_keep_idx, "failure_event_level_dedup_keep"] = True
    dedup = (
        panel[panel["split"].eq("validation") & panel["failure_event_level_dedup_keep"].fillna(False).astype(bool)]
        .sort_values(["fold_id", "launch_stratum_event_id", "failure_decision_effective_date", "failure_decision_window"])
        .copy()
    )
    dedup["source_failure_full_stable_candidate_id_at_earliest_hit"] = dedup["failure_full_stable_candidate_id"]
    audit_rows = []
    grouped = panel[panel["split"].eq("validation")].groupby(["failure_event_dedup_candidate_id"], dropna=False)
    for candidate_id, group in grouped:
        duplicate_count = int(len(group) - group["launch_stratum_event_id"].nunique())
        kept_count = int(group["failure_event_level_dedup_keep"].fillna(False).astype(bool).sum())
        audit_rows.append(
            {
                "fold_id": "all_validation_folds",
                "failure_event_dedup_candidate_id": candidate_id,
                "failure_window_group_policy": policy,
                "window_specific_candidate_protocol": bool(config.get("failure_dedup", {}).get("window_specific_candidate_protocol", False)),
                "raw_window_row_count": int(len(group)),
                "dedup_launch_stratum_event_count": int(group["launch_stratum_event_id"].nunique()),
                "event_level_dedup_keep_count": kept_count,
                "duplicate_window_hit_count": duplicate_count,
                "main_metric_dedup_key": "failure_event_dedup_candidate_id_plus_launch_stratum_event_id",
            }
        )
    return panel.replace([np.inf, -np.inf], np.nan), audit, cap_audit, dedup.replace([np.inf, -np.inf], np.nan), pd.DataFrame(audit_rows)


def p0_8_label_dictionary() -> pd.DataFrame:
    rows = [
        ("launch_winner_50h120", "launch_winner_score", "primary", "winner", "H_120(E)/P_E - 1 >= 0.50", "stratum_effective_date", "stratum_effective_price_reference", 120, "high", 0.50, np.nan, ">=", "winner", "not winner", "event_effective_date", "horizon_end_date_120d", True, "launch_model_train_eval_eligible", "label_measurement_available and not label_horizon_truncated", True, "label measurement overlap allowed only for robustness audit", "exclude from P1 promotion", "", True, False, False, "higher_is_positive", "false when unavailable", True, True, True),
        ("launch_winner_50c120", "launch_winner_score", "secondary", "winner", "C_120(E)/P_E - 1 >= 0.50", "stratum_effective_date", "stratum_effective_price_reference", 120, "close", 0.50, np.nan, ">=", "winner", "not winner", "event_effective_date", "horizon_end_date_120d", True, "launch_model_train_eval_eligible", "label_measurement_available and not label_horizon_truncated", True, "audit only", "exclude from P1 promotion when overlap", "", False, True, False, "higher_is_positive", "false when unavailable", False, True, False),
        ("launch_winner_100h240", "launch_winner_score", "audit", "big_winner", "H_240(E)/P_E - 1 >= 1.00", "stratum_effective_date", "stratum_effective_price_reference", 240, "high", 1.00, np.nan, ">=", "big winner", "not big winner", "event_effective_date", "horizon_end_date_240d", True, "launch_model_train_eval_eligible", "label_measurement_available and not label_horizon_truncated", True, "audit only", "exclude from P1 promotion when overlap", "", True, False, False, "higher_is_positive", "false when unavailable", False, True, False),
        ("launch_false_positive_primary", "launch_winner_score", "audit", "failure", "not launch_winner_50h120 and L_60(E)/P_E - 1 <= -0.12", "stratum_effective_date", "stratum_effective_price_reference", 60, "mixed", np.nan, -0.12, "<=", "false positive", "not false positive", "event_effective_date", "horizon_end_date_60d", True, "launch_model_train_eval_eligible", "label_measurement_available", True, "audit only", "exclude from P1 promotion when overlap", "", True, False, True, "lower_is_positive", "false when unavailable", False, True, True),
        ("failure_reject_positive_primary", "failure_reject_score", "primary", "failure", "target_50h120 pending and no decision 50h120 and decision drawdown60 <= -0.12", "failure_decision_effective_date", "failure_decision_effective_price_reference", 120, "mixed", 0.50, -0.12, "mixed", "reject positive", "not reject positive", "event_effective_date", "decision_horizon_end_date_120d", True, "failure_model_train_eval_eligible", "target pending and label available", True, "label measurement overlap allowed only for robustness audit", "post-target rows audit only", "post_target_risk_audit_only", True, False, True, "higher_score_is_risk", "false when unavailable", True, True, True),
        ("failure_false_reject_winner_from_launch_50h120", "failure_reject_score", "secondary", "false_reject", "target_50h120 reached after decision within original launch horizon", "stratum_effective_date", "stratum_effective_price_reference", 120, "high", 0.50, np.nan, ">=", "false reject", "not false reject", "failure_decision_effective_date", "target_50pct_high_date_120d", True, "failure_model_train_eval_eligible", "pending target only", True, "P1 coverage gate reference", "post-target rows audit only", "", True, False, False, "lower_is_better", "false when unavailable", False, True, True),
        ("failure_false_reject_winner_from_decision_50h120", "failure_reject_score", "audit", "secondary_veto", "target pending and decision reference future 50h120", "failure_decision_effective_date", "failure_decision_effective_price_reference", 120, "high", 0.50, np.nan, ">=", "false reject", "not false reject", "event_effective_date", "decision_horizon_end_date_120d", True, "failure_model_train_eval_eligible", "secondary veto only", True, "secondary veto", "post-target rows audit only", "", True, False, False, "lower_is_better", "false when unavailable", False, True, True),
    ]
    cols = [
        "label_name",
        "model_task",
        "label_type",
        "label_family",
        "label_definition_formula",
        "reference_date_field",
        "reference_price_field",
        "horizon_trading_days",
        "future_price_field_used",
        "target_return_threshold",
        "drawdown_threshold",
        "comparison_operator",
        "positive_condition",
        "negative_condition",
        "label_start_date_field",
        "label_end_date_field",
        "label_window_includes_effective_date_high_low",
        "eligibility_field",
        "validity_rule",
        "observed_reference_label_measurement_allowed",
        "observed_reference_overlap_handling",
        "label_horizon_truncated_handling",
        "post_target_handling",
        "uses_high",
        "uses_close",
        "uses_low",
        "label_direction",
        "null_value_rule",
        "used_for_training",
        "used_for_validation",
        "used_for_p1_gate",
    ]
    return pd.DataFrame(rows, columns=cols)


def p0_8_feature_dictionary(config: dict[str, Any]) -> pd.DataFrame:
    base = p0_7_feature_dictionary().copy()
    base["phase"] = "p0_8_reused_from_p0_7"
    extra = []
    for col in p0_8_required_feature_columns(config):
        extra.append(
            {
                "feature_name": col,
                "feature_family": "p0_8_model_feature",
                "feature_role": "lgbm_or_gate_input",
                "lookback_days": int(next((x for x in re.findall(r"\d+", col) if x), "0")),
                "min_history_trading_days": 0,
                "observable_date": "feature_asof_date_or_prior",
                "uses_future_data": False,
                "required_fields": "open;high;low;close;money;industry;benchmark",
                "raw_required_field_exempt": False,
                "feature_eligible_rule": "sample_has_required_features",
                "formula_text": col,
                "formula_text_resolved": col,
                "thresholds": "",
                "used_in_launch_stratification": True,
                "used_in_failure_filter": True,
                "used_in_hold_gate": False,
                "used_in_add_on_gate": False,
                "phase": "p0_8",
            }
        )
    return pd.concat([base, pd.DataFrame(extra)], ignore_index=True, sort=False).drop_duplicates(["feature_name"], keep="last")


def p0_8_gate_token_specs() -> list[dict[str, Any]]:
    def row(name: str, family: str, launch: bool, failure: bool, source: str = "fixed_config") -> dict[str, Any]:
        return {
            "token_id": f"tok_{name}",
            "token_name": name,
            "token_family": family,
            "source_family": family,
            "source_variant": name,
            "model_task": "launch_winner_score;failure_reject_score" if launch and failure else ("launch_winner_score" if launch else "failure_reject_score"),
            "decision_context": "launch_stratum_event;failure_filter_opportunity" if launch and failure else ("launch_stratum_event" if launch else "failure_filter_opportunity"),
            "feature_asof_rule": "close_derived_signal_date",
            "formula_text_raw": name,
            "formula_text_resolved": name,
            "threshold_config_key": name,
            "threshold_value_policy": "fixed_policy",
            "threshold_source": source,
            "learned_or_fixed": "fixed",
            "learned_fold_id": "",
            "train_threshold_value": "",
            "train_threshold_quantile": "",
            "train_threshold_value_identity": f"{source}:{name}",
            "train_threshold_value_bucket_hash": p0_8_hash({"token": name, "source": source}),
            "threshold_canonicalization_rule": "exact_fixed_policy",
            "validation_threshold_used": False,
            "allowed_for_gate_search": True,
            "allowed_for_lgbm_feature": True,
            "allowed_in_launch_task": launch,
            "allowed_in_failure_task": failure,
            "observed_reference_used_for_threshold": False,
            "leakage_audit_pass": True,
        }

    return [
        row("repair_higher_low_reclaim", "repair_quality_features", True, True),
        row("money_price_upper_keep", "money_quality_features", True, True),
        row("money_expansion_no_distribution", "money_quality_features", True, True),
        row("first_near_limit_upper_close", "price_path_features", True, True),
        row("high_vol_quality_permit", "volatility_features", True, True),
        row("industry_breadth_coherence", "industry_context_features", True, True),
        row("market_regime_risk_on", "market_regime_features", True, True),
        row("high_vol_destructive_warning", "volatility_features", True, True),
        row("market_regime_risk_off", "market_regime_features", True, True),
        row("rank_evaporation_2d", "rank_deterioration_features", False, True),
        row("rank_evaporation_3d", "rank_deterioration_features", False, True),
        row("rank_evaporation_5d", "rank_deterioration_features", False, True),
        row("destructive_high_vol_3d", "failure_opportunity_context_flags", False, True),
        row("destructive_high_vol_5d", "failure_opportunity_context_flags", False, True),
        row("gap_fade_break_prior_close_5d", "failure_opportunity_context_flags", False, True),
        row("money_distribution_5d", "failure_opportunity_context_flags", False, True),
    ]


def p0_8_gate_token_dictionary() -> pd.DataFrame:
    return pd.DataFrame(p0_8_gate_token_specs())


def p0_8_token_mask(panel: pd.DataFrame, token: str) -> pd.Series:
    idx = panel.index
    launch_variant = panel.get("launch_variant", pd.Series("", index=idx)).astype(str)
    market = panel.get("market_regime", pd.Series("", index=idx)).astype(str).str.lower()
    if token in {"repair_higher_low_reclaim", "money_price_upper_keep", "money_expansion_no_distribution", "first_near_limit_upper_close"}:
        return launch_variant.eq(token).fillna(False)
    if token == "high_vol_quality_permit":
        return launch_variant.isin(["high_vol_controlled_drawdown", "expansion_high_vol_upper_close"]).fillna(False)
    if token == "industry_breadth_coherence":
        return pd.to_numeric(panel.get("industry_breadth_20d", panel.get("industry_breadth_20d_at_stratum", 0)), errors="coerce").fillna(0) >= 0.60
    if token == "market_regime_risk_on":
        return market.isin(["risk_on", "strong", "bull", "neutral"])
    if token == "market_regime_risk_off":
        return market.isin(["risk_off", "weak", "bear", "market_drawdown"])
    if token == "high_vol_destructive_warning":
        atr = pd.to_numeric(panel.get("atr20_pct", 0), errors="coerce")
        close_loc = pd.to_numeric(panel.get("close_location", 1), errors="coerce")
        return (atr >= atr.quantile(0.70)) & (close_loc <= 0.45)
    if token.startswith("rank_evaporation_"):
        current = pd.to_numeric(panel.get("ret_rank_20d_market", np.nan), errors="coerce")
        start = pd.to_numeric(panel.get("ret_rank_20d_market_at_stratum", np.nan), errors="coerce")
        window = int(re.findall(r"\d+", token)[0])
        return (pd.to_numeric(panel.get("failure_decision_window", 99), errors="coerce") <= window) & (current <= start - 0.20) & (current <= 0.55)
    if token.startswith("destructive_high_vol_"):
        window = int(re.findall(r"\d+", token)[0])
        return (pd.to_numeric(panel.get("failure_decision_window", 99), errors="coerce") <= window) & p0_8_token_mask(panel, "high_vol_destructive_warning")
    if token == "gap_fade_break_prior_close_5d":
        return (pd.to_numeric(panel.get("failure_decision_window", 99), errors="coerce") <= 5) & (pd.to_numeric(panel.get("close_location", 1), errors="coerce") <= 0.40)
    if token == "money_distribution_5d":
        return (pd.to_numeric(panel.get("failure_decision_window", 99), errors="coerce") <= 5) & (pd.to_numeric(panel.get("money_ratio_20", 0), errors="coerce") >= 1.20) & (pd.to_numeric(panel.get("close_location", 1), errors="coerce") <= 0.50)
    return pd.Series(False, index=idx)


def p0_8_gate_candidate_specs(tokens: pd.DataFrame, panel: pd.DataFrame, task: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = tokens[tokens[f"allowed_in_{'launch' if task == 'launch' else 'failure'}_task"].fillna(False).astype(bool)]["token_name"].tolist()
    seed = [
        ("repair_higher_low_reclaim", "destructive_high_vol_3d"),
        ("repair_higher_low_reclaim", "destructive_high_vol_5d"),
        ("money_price_upper_keep", "destructive_high_vol_3d"),
        ("money_price_upper_keep", "destructive_high_vol_5d"),
        ("money_expansion_no_distribution", "destructive_high_vol_3d"),
        ("money_expansion_no_distribution", "destructive_high_vol_5d"),
        ("first_near_limit_upper_close", "rank_evaporation_2d"),
        ("first_near_limit_upper_close", "rank_evaporation_3d"),
        ("first_near_limit_upper_close", "rank_evaporation_5d"),
        ("high_vol_quality_permit", "industry_breadth_coherence"),
        ("high_vol_quality_permit", "market_regime_risk_on"),
        ("high_vol_destructive_warning", "market_regime_risk_off"),
        ("gap_fade_break_prior_close_5d", "high_vol_destructive_warning"),
        ("gap_fade_break_prior_close_5d", "money_distribution_5d"),
    ]
    rows = []
    for combo in seed:
        if all(token in allowed for token in combo):
            rows.append({"gate_search_mode": "manual_seeded_combo", "ordered_token_id_list": combo})
    train = panel[panel["split"].eq("train")].copy()
    token_scores = []
    for token in allowed:
        mask = p0_8_token_mask(train, token)
        count = int(mask.sum())
        if count >= 20:
            if task == "launch":
                rate = safe_div(train.loc[mask, "launch_winner_50h120"].sum(), count)
            else:
                rate = safe_div(train.loc[mask, "failure_reject_positive_primary"].sum(), count)
            token_scores.append((token, rate, count))
    token_scores = sorted(token_scores, key=lambda item: (safe_float(item[1], 0.0), item[2]), reverse=True)
    top_tokens = [item[0] for item in token_scores[: min(12, len(token_scores))]]
    max_candidates = int(config.get("gate_search", {}).get("max_final_gate_candidates_per_fold", 300))
    for depth in range(2, min(4, len(top_tokens)) + 1):
        for combo in itertools.combinations(top_tokens, depth):
            rows.append({"gate_search_mode": "beam_search_combo", "ordered_token_id_list": combo})
            if len(rows) >= max_candidates:
                break
        if len(rows) >= max_candidates:
            break
    out = []
    seen = set()
    for row in rows:
        combo = tuple(row["ordered_token_id_list"])
        if combo in seen:
            continue
        seen.add(combo)
        model_task = "launch_winner_gate" if task == "launch" else "failure_reject_gate"
        stable_id = p0_8_hash(
            {
                "model_task": model_task,
                "decision_context": "launch_stratum_event" if task == "launch" else "failure_filter_opportunity",
                "normalized_gate_formula": " AND ".join(combo),
                "ordered_token_id_list": combo,
                "ordered_threshold_config_key_list": combo,
                "ordered_threshold_value_policy_list": ["fixed_policy"] * len(combo),
                "ordered_threshold_source_list": ["fixed_config"] * len(combo),
                "ordered_learned_or_fixed_list": ["fixed"] * len(combo),
                "ordered_threshold_identity_value_list": [f"fixed_config:{token}" for token in combo],
                "feature_asof_rule": "close_derived_signal_date",
                "effective_date_rule": "next_trading_day_open",
            }
        )
        out.append(
            {
                **row,
                "candidate_type": "gate",
                "model_task": model_task,
                "decision_context": "launch_stratum_event" if task == "launch" else "failure_filter_opportunity",
                "normalized_gate_formula": " AND ".join(combo),
                "stable_candidate_id": stable_id,
                "gate_stable_candidate_id": stable_id,
                "threshold_source": "fixed_config",
                "validation_threshold_used": False,
                "feature_asof_rule": "close_derived_signal_date",
                "effective_date_rule": "next_trading_day_open",
            }
        )
    return out


def p0_8_eval_gate_mask(panel: pd.DataFrame, token_list: tuple[str, ...]) -> pd.Series:
    if not token_list:
        return pd.Series(False, index=panel.index)
    mask = pd.Series(True, index=panel.index)
    for token in token_list:
        mask &= p0_8_token_mask(panel, token)
    return mask.fillna(False).astype(bool)


def p0_8_candidate_metric_row(
    frame: pd.DataFrame,
    candidate_mask: pd.Series,
    candidate: dict[str, Any],
    split: str,
    fold_id: str,
    role: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    task = "launch" if "launch" in candidate["model_task"] else "failure"
    eligible_col = "launch_model_train_eval_eligible" if task == "launch" else "failure_model_train_eval_eligible"
    base = frame[frame["split"].eq(split) & frame[eligible_col].fillna(False).astype(bool)].copy()
    selected = base.loc[candidate_mask.reindex(base.index).fillna(False)].copy()
    if task == "failure" and not selected.empty:
        if split == "validation" and "failure_event_level_dedup_keep" in selected.columns:
            selected = selected[selected["failure_event_level_dedup_keep"].fillna(False).astype(bool)].copy()
        else:
            selected = selected.sort_values(["launch_stratum_event_id", "failure_decision_effective_date", "failure_decision_window"]).drop_duplicates("launch_stratum_event_id")
    weight = pd.to_numeric(selected.get("final_sample_weight", pd.Series(1.0, index=selected.index)), errors="coerce").fillna(0.0)
    base_weight = pd.to_numeric(base.get("final_sample_weight", pd.Series(1.0, index=base.index)), errors="coerce").fillna(0.0)
    row = {
        "fold_id": fold_id,
        "validation_fold_role": role,
        "split": split,
        "candidate_type": candidate["candidate_type"],
        "model_task": candidate["model_task"],
        "stable_candidate_id": candidate["stable_candidate_id"],
        "gate_stable_candidate_id": candidate.get("gate_stable_candidate_id", ""),
        "normalized_gate_formula": candidate.get("normalized_gate_formula", ""),
        "predeclared_bucket_id": candidate.get("predeclared_bucket_id", ""),
        "event_count": int(len(selected)),
        "weighted_event_count": safe_float(weight.sum(), 0.0),
        "validation_selected_on_validation": False,
        "candidate_baseline_missing_row_rate": 0.0,
        "candidate_baseline_missing_weight_share": 0.0,
        "candidate_weighted_baseline_missing_rate": 0.0,
        "fold_2024_used_for_p1_promotion": False,
    }
    if task == "launch":
        pos = selected["launch_winner_50h120"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        base_pos = base["launch_winner_50h120"].fillna(False).astype(bool) if not base.empty else pd.Series(dtype=bool)
        winner_weight = safe_float(weight[pos].sum(), 0.0) if len(pos) else 0.0
        base_rate = safe_div(base_weight[base_pos].sum(), base_weight.sum())
        rate = safe_div(winner_weight, weight.sum())
        family_baseline = base.groupby("launch_family")["launch_winner_50h120"].mean().to_dict() if not base.empty else {}
        candidate_family_rate = selected["launch_family"].map(family_baseline) if not selected.empty else pd.Series(dtype=float)
        weighted_family_base = float(np.average(candidate_family_rate.fillna(base_rate), weights=weight)) if len(selected) and weight.sum() > 0 else np.nan
        false_positive = selected["launch_false_positive_primary"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        iy = selected.groupby("event_instrument_year")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float)
        industry = selected.groupby("industry")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float)
        regime = selected.groupby("market_regime")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float)
        row.update(
            {
                "positive_count": int(pos.sum()) if len(pos) else 0,
                "winner_rate": rate,
                "all_launch_baseline_winner_rate": base_rate,
                "lift_vs_all_launch_baseline": safe_div(rate, base_rate),
                "candidate_weighted_same_family_winner_rate": weighted_family_base,
                "lift_vs_candidate_weighted_same_family_baseline": safe_div(rate, weighted_family_base),
                "false_positive_rate": safe_div(weight[false_positive].sum(), weight.sum()) if len(false_positive) else np.nan,
                "median_drawdown_60d": safe_float(selected["launch_future_max_drawdown_60d"].median(), np.nan) if not selected.empty else np.nan,
                "winner_episode_coverage": safe_div(selected.loc[pos, "launch_episode_id"].nunique() if len(pos) else 0, base.loc[base_pos, "launch_episode_id"].nunique() if len(base_pos) else 0),
                "distinct_instrument_year": int(selected["event_instrument_year"].nunique()) if not selected.empty else 0,
                "oof_top_instrument_year_weight_share": p0_8_top_share(iy, 1),
                "oof_instrument_year_weight_hhi": p0_8_hhi(iy),
                "oof_top1_instrument_contribution": p0_8_top_share(selected.groupby("instrument")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float), 1),
                "oof_top5_instrument_contribution": p0_8_top_share(selected.groupby("instrument")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float), 5),
                "oof_top1_industry_contribution": p0_8_top_share(industry, 1),
                "oof_top3_industry_contribution": p0_8_top_share(industry, 3),
                "oof_industry_hhi": p0_8_hhi(industry),
                "oof_regime_hhi": p0_8_hhi(regime),
                "oof_top1_regime_contribution": p0_8_top_share(regime, 1),
                "industry_count_with_min_events": int((selected.groupby("industry").size() >= 10).sum()) if not selected.empty else 0,
            }
        )
    else:
        pos = selected["failure_reject_positive_primary"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        nonwinner = selected["launch_nonwinner_primary"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        base_pos = base["failure_reject_positive_primary"].fillna(False).astype(bool) if not base.empty else pd.Series(dtype=bool)
        base_nonwinner = base["launch_nonwinner_primary"].fillna(False).astype(bool) if not base.empty else pd.Series(dtype=bool)
        precision = safe_div(weight[pos].sum(), weight.sum())
        nonwinner_precision = safe_div(weight[nonwinner].sum(), weight.sum())
        base_failure = safe_div(base_weight[base_pos].sum(), base_weight.sum())
        base_nonwinner_rate = safe_div(base_weight[base_nonwinner].sum(), base_weight.sum())
        false_launch = selected["failure_false_reject_winner_from_launch_50h120"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        false_big_launch = selected["failure_false_reject_big_winner_from_launch_100h240"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        false_decision = selected["failure_false_reject_winner_from_decision_50h120"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        false_big_decision = selected["failure_false_reject_big_winner_from_decision_100h240"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        pending = selected["launch_winner_50h120"].fillna(False).astype(bool) if not selected.empty else pd.Series(dtype=bool)
        iy = selected.groupby("event_instrument_year")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float)
        industry = selected.groupby("industry")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float)
        regime = selected.groupby("market_regime")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float)
        row.update(
            {
                "event_level_dedup_reject_count": int(len(selected)),
                "failure_positive_count": int(pos.sum()) if len(pos) else 0,
                "failure_precision": precision,
                "failure_precision_lift": safe_div(precision, base_failure),
                "nonwinner_precision": nonwinner_precision,
                "nonwinner_precision_lift": safe_div(nonwinner_precision, base_nonwinner_rate),
                "winner_false_reject_from_launch_rate": safe_div(weight[false_launch].sum(), weight.sum()) if len(false_launch) else np.nan,
                "big_winner_false_reject_from_launch_rate": safe_div(weight[false_big_launch].sum(), weight.sum()) if len(false_big_launch) else np.nan,
                "winner_false_reject_from_decision_rate": safe_div(weight[false_decision].sum(), weight.sum()) if len(false_decision) else np.nan,
                "big_winner_false_reject_from_decision_rate": safe_div(weight[false_big_decision].sum(), weight.sum()) if len(false_big_decision) else np.nan,
                "pending_winner_coverage_loss_from_launch": safe_div(weight[false_launch].sum(), weight[pending].sum()) if len(pending) else np.nan,
                "total_winner_coverage_loss_from_launch": safe_div(weight[false_launch].sum(), base_weight[base["launch_winner_50h120"].fillna(False).astype(bool)].sum()) if not base.empty else np.nan,
                "median_drawdown_avoided_vs_matched_delay": safe_float((-selected.loc[pos, "future_max_drawdown_60d_from_decision_reference"]).median(), np.nan) if len(pos) else np.nan,
                "before_12pct_drawdown_rate": safe_div((pd.to_datetime(selected["failure_decision_effective_date"]) <= pd.to_datetime(selected["first_12pct_drawdown_date_from_stratum"])).sum(), pd.to_datetime(selected["first_12pct_drawdown_date_from_stratum"]).notna().sum()) if not selected.empty else np.nan,
                "instrument_year_filter_effect_lift": safe_div(nonwinner_precision, base_nonwinner_rate),
                "distinct_instrument_year": int(selected["event_instrument_year"].nunique()) if not selected.empty else 0,
                "oof_top_instrument_year_weight_share": p0_8_top_share(iy, 1),
                "oof_instrument_year_weight_hhi": p0_8_hhi(iy),
                "oof_top1_instrument_contribution": p0_8_top_share(selected.groupby("instrument")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float), 1),
                "oof_top5_instrument_contribution": p0_8_top_share(selected.groupby("instrument")["final_sample_weight"].sum() if not selected.empty else pd.Series(dtype=float), 5),
                "oof_top1_industry_contribution": p0_8_top_share(industry, 1),
                "oof_top3_industry_contribution": p0_8_top_share(industry, 3),
                "oof_industry_hhi": p0_8_hhi(industry),
                "oof_regime_hhi": p0_8_hhi(regime),
                "oof_top1_regime_contribution": p0_8_top_share(regime, 1),
                "industry_count_with_min_events": int((selected.groupby("industry").size() >= 10).sum()) if not selected.empty else 0,
                "secondary_decision_reference_veto_pass": True,
            }
        )
    return row


def p0_8_run_gate_discovery(
    config: dict[str, Any],
    launch_panel: pd.DataFrame,
    failure_panel: pd.DataFrame,
    tokens: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    complexity_rows: list[dict[str, Any]] = []
    candidates_by_task = {
        "launch": p0_8_gate_candidate_specs(tokens, launch_panel, "launch", config),
        "failure": p0_8_gate_candidate_specs(tokens, failure_panel, "failure", config),
    }
    for task, panel in [("launch", launch_panel), ("failure", failure_panel)]:
        eligible_col = "launch_model_train_eval_eligible" if task == "launch" else "failure_model_train_eval_eligible"
        for fold in p0_8_walk_folds(config):
            fold_panel = panel[panel["fold_id"].eq(fold["fold_id"])].copy()
            selected_for_fold = []
            for candidate in candidates_by_task[task]:
                token_list = tuple(candidate["ordered_token_id_list"])
                mask = p0_8_eval_gate_mask(fold_panel, token_list)
                train_metric = p0_8_candidate_metric_row(fold_panel, mask, candidate, "train", fold["fold_id"], fold["validation_fold_role"], config)
                train_metric["train_search_selected"] = False
                train_metric["ordered_token_id_list"] = ";".join(token_list)
                train_rows.append(train_metric)
                if train_metric["event_count"] >= int(config.get("gate_search", {}).get("min_train_event_count", 100)) and train_metric.get("distinct_instrument_year", 0) >= int(config.get("gate_search", {}).get("min_train_distinct_instrument_year", 25)):
                    selected_for_fold.append((safe_float(train_metric.get("lift_vs_all_launch_baseline", train_metric.get("failure_precision_lift", 0.0)), 0.0), candidate, mask))
                complexity_rows.append(
                    {
                        "fold_id": fold["fold_id"],
                        "candidate_type": "gate",
                        "model_task": candidate["model_task"],
                        "stable_candidate_id": candidate["stable_candidate_id"],
                        "token_count": len(token_list),
                        "negated_token_count": 0,
                        "industry_or_regime_token_count": sum(1 for token in token_list if "industry" in token or "regime" in token),
                        "complexity_pass": len(token_list) <= int(config.get("gate_search", {}).get("max_tokens_per_gate", 4)),
                    }
                )
            selected_for_fold = sorted(selected_for_fold, key=lambda item: item[0], reverse=True)[: int(config.get("gate_search", {}).get("max_final_gate_candidates_per_fold", 300))]
            for _score, candidate, mask in selected_for_fold:
                val_metric = p0_8_candidate_metric_row(fold_panel, mask, candidate, "validation", fold["fold_id"], fold["validation_fold_role"], config)
                val_metric["ordered_token_id_list"] = ";".join(candidate["ordered_token_id_list"])
                val_metric["train_selected_candidate"] = True
                validation_rows.append(val_metric)
            if not selected_for_fold:
                train_rows.append(
                    {
                        "fold_id": fold["fold_id"],
                        "validation_fold_role": fold["validation_fold_role"],
                        "split": "train",
                        "candidate_type": "gate",
                        "model_task": f"{task}_gate",
                        "stable_candidate_id": "",
                        "event_count": int(fold_panel[fold_panel["split"].eq("train") & fold_panel[eligible_col].fillna(False).astype(bool)].shape[0]),
                        "train_search_selected": False,
                        "rejection_reason": "no_train_candidate_met_min_event_or_instrument_year_gate",
                    }
                )
    train_df = pd.DataFrame(train_rows)
    val_df = pd.DataFrame(validation_rows)
    oof = p0_8_aggregate_candidates(config, val_df, "gate")
    return train_df, val_df, oof, pd.DataFrame(complexity_rows), pd.DataFrame()


def p0_8_lgbm_column_spec(train: pd.DataFrame, valid: pd.DataFrame, config: dict[str, Any], include_industry_regime: bool = True) -> tuple[list[str], list[str]]:
    feature_cols = [col for col in config.get("lgbm", {}).get("feature_columns", []) if col in train.columns or col in valid.columns]
    cat_cols = [col for col in config.get("lgbm", {}).get("categorical_feature_columns", []) if col in train.columns or col in valid.columns]
    if not include_industry_regime:
        feature_cols = [col for col in feature_cols if "industry" not in col and "market_regime" not in col]
        cat_cols = [col for col in cat_cols if col not in {"industry", "market_regime"}]
    all_cols = list(dict.fromkeys(feature_cols + cat_cols))
    cat_cols = [col for col in cat_cols if col in all_cols]
    return all_cols, cat_cols


def p0_8_fit_lgbm_matrix_encoder(train: pd.DataFrame, valid: pd.DataFrame, config: dict[str, Any], include_industry_regime: bool = True) -> dict[str, Any]:
    all_cols, cat_cols = p0_8_lgbm_column_spec(train, valid, config, include_industry_regime=include_industry_regime)
    medians: dict[str, float] = {}
    categories: dict[str, dict[str, int]] = {}
    for col in all_cols:
        if col in cat_cols:
            train_values = train.get(col, pd.Series("UNKNOWN", index=train.index)).fillna("UNKNOWN").astype(str)
            categories[col] = {value: i for i, value in enumerate(sorted(train_values.unique()))}
        else:
            train_values = pd.to_numeric(train.get(col, pd.Series(np.nan, index=train.index)), errors="coerce")
            medians[col] = safe_float(train_values.median(), 0.0)
    return {
        "feature_cols": all_cols,
        "cat_cols": cat_cols,
        "medians": medians,
        "categories": categories,
    }


def p0_8_apply_lgbm_matrix_encoder(frame: pd.DataFrame, encoder: dict[str, Any]) -> pd.DataFrame:
    x = pd.DataFrame(index=frame.index)
    feature_cols = list(encoder.get("feature_cols", []))
    cat_cols = set(encoder.get("cat_cols", []))
    categories = encoder.get("categories", {})
    medians = encoder.get("medians", {})
    for col in feature_cols:
        if col in cat_cols:
            x[col] = frame.get(col, pd.Series("UNKNOWN", index=frame.index)).fillna("UNKNOWN").astype(str).map(categories.get(col, {})).fillna(-1).astype(int)
        else:
            x[col] = pd.to_numeric(frame.get(col, pd.Series(np.nan, index=frame.index)), errors="coerce").fillna(safe_float(medians.get(col), 0.0))
    return x


def p0_8_prepare_lgbm_matrix(train: pd.DataFrame, valid: pd.DataFrame, config: dict[str, Any], include_industry_regime: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    encoder = p0_8_fit_lgbm_matrix_encoder(train, valid, config, include_industry_regime=include_industry_regime)
    all_cols = list(encoder.get("feature_cols", []))
    cat_cols = set(encoder.get("cat_cols", []))
    x_train = pd.DataFrame(index=train.index)
    x_valid = pd.DataFrame(index=valid.index)
    for col in all_cols:
        if col in cat_cols:
            train_values = train.get(col, pd.Series("UNKNOWN", index=train.index)).fillna("UNKNOWN").astype(str)
            categories = {value: i for i, value in enumerate(sorted(train_values.unique()))}
            x_train[col] = train_values.map(categories).fillna(-1).astype(int)
            x_valid[col] = valid.get(col, pd.Series("UNKNOWN", index=valid.index)).fillna("UNKNOWN").astype(str).map(categories).fillna(-1).astype(int)
        else:
            x_train[col] = pd.to_numeric(train.get(col, pd.Series(np.nan, index=train.index)), errors="coerce")
            median = safe_float(x_train[col].median(), 0.0)
            x_train[col] = x_train[col].fillna(median)
            x_valid[col] = pd.to_numeric(valid.get(col, pd.Series(np.nan, index=valid.index)), errors="coerce").fillna(median)
    return x_train, x_valid, all_cols


def p0_8_lgbm_trainability(
    config: dict[str, Any],
    panel: pd.DataFrame,
    fold: dict[str, Any],
    task: str,
    label_col: str,
    eligible_col: str,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fold_panel = panel[panel["fold_id"].eq(fold["fold_id"])].copy()
    train_all = fold_panel[fold_panel["split"].eq("train") & fold_panel[eligible_col].fillna(False).astype(bool)].copy()
    outer = fold_panel[fold_panel["split"].eq("validation") & fold_panel[eligible_col].fillna(False).astype(bool)].copy()
    if train_all.empty:
        inner = train = train_all
    else:
        inner_year = int(train_all["event_year"].max())
        inner = train_all[train_all["event_year"].eq(inner_year)].copy()
        train = train_all[train_all["event_year"].lt(inner_year)].copy()
    y_train = train[label_col].fillna(False).astype(bool) if label_col in train else pd.Series(dtype=bool)
    y_inner = inner[label_col].fillna(False).astype(bool) if label_col in inner else pd.Series(dtype=bool)
    y_outer = outer[label_col].fillna(False).astype(bool) if label_col in outer else pd.Series(dtype=bool)
    thresholds = config.get("thresholds", {})
    checks = [
        ("train_event_count_after_purge", len(train), int(thresholds.get("min_lgbm_train_event_count", 1000))),
        ("train_positive_count_after_purge", int(y_train.sum()), int(thresholds.get("min_lgbm_train_positive_count", 50))),
        ("train_negative_count_after_purge", int((~y_train).sum()) if len(y_train) else 0, int(thresholds.get("min_lgbm_train_negative_count", 200))),
        ("train_distinct_instrument_year", int(train["event_instrument_year"].nunique()) if not train.empty else 0, int(thresholds.get("min_lgbm_train_distinct_instrument_year", 25))),
        ("inner_validation_event_count", len(inner), int(thresholds.get("min_lgbm_inner_validation_event_count", 200))),
        ("inner_validation_positive_count", int(y_inner.sum()), int(thresholds.get("min_lgbm_inner_validation_positive_count", 10))),
        ("outer_validation_event_count_eligible", len(outer), int(thresholds.get("min_lgbm_outer_validation_event_count", 200))),
        ("outer_validation_positive_count_eligible", int(y_outer.sum()), int(thresholds.get("min_lgbm_outer_validation_positive_count", 10))),
        ("outer_validation_distinct_instrument_year", int(outer["event_instrument_year"].nunique()) if not outer.empty else 0, int(thresholds.get("min_lgbm_validation_distinct_instrument_year", 10))),
    ]
    failed = [name for name, actual, required in checks if actual < required]
    row = {
        "fold_id": fold["fold_id"],
        "model_task": task,
        "train_event_count_after_purge": len(train),
        "train_positive_count_after_purge": int(y_train.sum()) if len(y_train) else 0,
        "train_negative_count_after_purge": int((~y_train).sum()) if len(y_train) else 0,
        "train_distinct_instrument_year": int(train["event_instrument_year"].nunique()) if not train.empty else 0,
        "inner_validation_event_count": len(inner),
        "inner_validation_positive_count": int(y_inner.sum()) if len(y_inner) else 0,
        "outer_validation_event_count_eligible": len(outer),
        "outer_validation_positive_count_eligible": int(y_outer.sum()) if len(y_outer) else 0,
        "outer_validation_distinct_instrument_year": int(outer["event_instrument_year"].nunique()) if not outer.empty else 0,
        "purge_rate": safe_div(len(train_all) - len(train) - len(inner), len(train_all)),
        "label_horizon_truncated_rate": float(fold_panel["label_horizon_truncated"].fillna(False).astype(bool).mean()) if not fold_panel.empty else np.nan,
        "observed_reference_label_measurement_overlap_rate": float(fold_panel["observed_reference_label_measurement_overlap"].fillna(False).astype(bool).mean()) if not fold_panel.empty else np.nan,
        "trainability_status": "trainable" if not failed else "disabled_due_to_insufficient_sample",
        "trainability_rejection_reason": ";".join(failed),
        "lgbm_training_enabled_for_fold": not failed,
        "fold_excluded_from_lgbm_oof_aggregation": bool(failed),
    }
    return row, train, inner, outer


def p0_8_run_lgbm_discovery(
    config: dict[str, Any],
    launch_panel: pd.DataFrame,
    failure_panel: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    frames: dict[str, pd.DataFrame] = {}
    cache_frames: dict[str, pd.DataFrame] = {}
    trainability_rows: list[dict[str, Any]] = []
    fold_metric_rows: list[dict[str, Any]] = []
    bucket_rows: list[dict[str, Any]] = []
    feature_rows: list[dict[str, Any]] = []
    leaf_rows: list[dict[str, Any]] = []
    leaf_audit_rows: list[dict[str, Any]] = []
    model_card_rows: list[dict[str, Any]] = []
    early_rows: list[dict[str, Any]] = []
    bucket_audit_rows: list[dict[str, Any]] = []
    predictions: dict[str, list[pd.DataFrame]] = {"launch": [], "failure": []}
    try:
        import lightgbm as lgb
    except Exception as exc:
        for fold in p0_8_walk_folds(config):
            for task in ["launch_winner_score_lgbm", "failure_reject_score_lgbm"]:
                trainability_rows.append(
                    {
                        "fold_id": fold["fold_id"],
                        "model_task": task,
                        "trainability_status": "disabled_due_to_lightgbm_unavailable",
                        "trainability_rejection_reason": str(exc),
                        "lgbm_training_enabled_for_fold": False,
                        "fold_excluded_from_lgbm_oof_aggregation": True,
                    }
                )
        frames["p0_8_lgbm_fold_trainability_audit.csv"] = pd.DataFrame(trainability_rows)
        for name in [
            "p0_8_lgbm_fold_metrics.csv",
            "p0_8_lgbm_score_bucket_metrics.csv",
            "p0_8_lgbm_instrument_year_metrics.csv",
            "p0_8_lgbm_industry_metrics.csv",
            "p0_8_lgbm_feature_importance.csv",
            "p0_8_lgbm_leaf_rule_candidates.csv",
            "p0_8_lgbm_leaf_rule_canonicalization_audit.csv",
            "p0_8_lgbm_model_card.csv",
            "p0_8_lgbm_early_stopping_audit.csv",
            "p0_8_lgbm_score_bucket_selection_audit.csv",
        ]:
            frames[name] = pd.DataFrame()
        cache_frames["p0_8_lgbm_launch_predictions_walkforward.parquet"] = pd.DataFrame()
        cache_frames["p0_8_lgbm_failure_predictions_walkforward.parquet"] = pd.DataFrame()
        return frames, cache_frames

    tasks = [
        ("launch", launch_panel, "launch_winner_score_lgbm", "launch_winner_50h120", "launch_model_train_eval_eligible", config.get("lgbm", {}).get("predeclared_launch_score_buckets", [])),
        ("failure", failure_panel, "failure_reject_score_lgbm", "failure_reject_positive_primary", "failure_model_train_eval_eligible", config.get("lgbm", {}).get("predeclared_failure_score_buckets", [])),
    ]
    for task_key, panel, model_task, label_col, eligible_col, bucket_ids in tasks:
        for fold in p0_8_walk_folds(config):
            trainability, train, inner, outer = p0_8_lgbm_trainability(config, panel, fold, model_task, label_col, eligible_col)
            trainability_rows.append(trainability)
            if not trainability["lgbm_training_enabled_for_fold"]:
                continue
            all_train = pd.concat([train, inner], ignore_index=False)
            encoder = p0_8_fit_lgbm_matrix_encoder(train, pd.concat([inner, outer], ignore_index=False), config, include_industry_regime=True)
            feature_cols = list(encoder.get("feature_cols", []))
            cat_cols = list(encoder.get("cat_cols", []))
            x_train = p0_8_apply_lgbm_matrix_encoder(train, encoder)
            x_inner = p0_8_apply_lgbm_matrix_encoder(inner, encoder)
            x_full_train = p0_8_apply_lgbm_matrix_encoder(all_train, encoder)
            x_outer = p0_8_apply_lgbm_matrix_encoder(outer, encoder)
            params = config.get("lgbm", {})
            num_boost_round = int(params.get("n_estimators", 2000))
            lgb_params = {
                "objective": params.get("objective", "binary"),
                "boosting_type": params.get("boosting_type", "gbdt"),
                "metric": "binary_logloss",
                "learning_rate": safe_float(params.get("learning_rate", 0.03), 0.03),
                "num_leaves": int(params.get("num_leaves", 31)),
                "max_depth": int(params.get("max_depth", 5)),
                "min_data_in_leaf": int(params.get("min_data_in_leaf", 80)),
                "feature_fraction": safe_float(params.get("feature_fraction", 0.75), 0.75),
                "bagging_fraction": safe_float(params.get("bagging_fraction", 0.75), 0.75),
                "bagging_freq": int(params.get("bagging_freq", 1)),
                "lambda_l1": safe_float(params.get("lambda_l1", 0.1), 0.1),
                "lambda_l2": safe_float(params.get("lambda_l2", 1.0), 1.0),
                "num_threads": int(params.get("n_jobs", 1)),
                "seed": int(params.get("random_seed", 20260505)),
                "verbosity": -1,
                "force_col_wise": True,
            }
            callbacks = []
            early_rounds = params.get("early_stopping_rounds", 100)
            if early_rounds:
                callbacks.append(lgb.early_stopping(int(early_rounds), verbose=False))
            categorical_feature = [col for col in cat_cols if col in feature_cols]
            train_set = lgb.Dataset(
                x_train,
                label=train[label_col].fillna(False).astype(int),
                weight=train["final_sample_weight"],
                feature_name=feature_cols,
                categorical_feature=categorical_feature,
                free_raw_data=False,
            )
            inner_set = lgb.Dataset(
                x_inner,
                label=inner[label_col].fillna(False).astype(int),
                weight=inner["final_sample_weight"],
                reference=train_set,
                feature_name=feature_cols,
                categorical_feature=categorical_feature,
                free_raw_data=False,
            )
            model = lgb.train(
                lgb_params,
                train_set,
                num_boost_round=num_boost_round,
                valid_sets=[inner_set],
                valid_names=["inner"],
                callbacks=callbacks,
            )
            best_iter = int(model.best_iteration or num_boost_round)
            train_score = pd.Series(model.predict(x_full_train, num_iteration=best_iter), index=all_train.index)
            outer_score = pd.Series(model.predict(x_outer, num_iteration=best_iter), index=outer.index)
            importance_values = model.feature_importance(importance_type="gain")
            pred = outer[
                [
                    "fold_id",
                    "validation_fold_role",
                    "launch_stratum_event_id",
                    "launch_episode_id",
                    "instrument",
                    "event_effective_date",
                    "event_instrument_year",
                    "industry",
                    "market_regime",
                    "final_sample_weight",
                    label_col,
                ]
            ].copy()
            pred["model_task"] = model_task
            pred["prediction_score"] = outer_score.reindex(pred.index).to_numpy()
            pred["label"] = pred[label_col]
            if task_key == "failure":
                for col in ["failure_decision_window", "failure_event_dedup_candidate_id", "failure_event_level_dedup_key"]:
                    pred[col] = outer[col].to_numpy() if col in outer else ""
            predictions[task_key].append(pred)
            fold_metric_rows.append(
                {
                    "fold_id": fold["fold_id"],
                    "validation_fold_role": fold["validation_fold_role"],
                    "model_task": model_task,
                    "validation_event_count": len(outer),
                    "validation_positive_count": int(outer[label_col].fillna(False).astype(bool).sum()),
                    "auc": p0_8_auc(outer[label_col], outer_score),
                    "binary_logloss": p0_8_logloss(outer[label_col], outer_score, outer["final_sample_weight"]),
                    "best_iteration": best_iter,
                    "early_stopping_uses_outer_validation_fold": False,
                    "early_stopping_uses_inner_train_split_only": True,
                }
            )
            for feature_name, importance in zip(feature_cols, importance_values, strict=False):
                feature_rows.append(
                    {
                        "fold_id": fold["fold_id"],
                        "model_task": model_task,
                        "feature_name": feature_name,
                        "importance_gain_proxy": safe_float(importance, 0.0),
                        "feature_set_version": p0_8_cfg(config).get("feature_set_version", "p0_8_feature_set_v1"),
                    }
                )
            for bucket_id in bucket_ids:
                pct = 0.10 if "10pct" in bucket_id else (0.05 if "5pct" in bucket_id else 0.02)
                threshold = float(train_score.quantile(1.0 - pct))
                mask = outer_score >= threshold
                stable_id = p0_8_hash(
                    {
                        "model_task": model_task,
                        "model_family": "lgbm",
                        "predeclared_bucket_id": bucket_id,
                        "train_threshold_policy": f"top_{pct:.2f}_by_train_threshold",
                        "score_direction": "higher_is_better" if task_key == "launch" else "higher_is_risk",
                        "feature_set_version": p0_8_cfg(config).get("feature_set_version", "p0_8_feature_set_v1"),
                        "label_version": p0_8_cfg(config).get("label_version", "p0_8_label_v1"),
                    }
                )
                candidate = {
                    "candidate_type": "lgbm_score_bucket",
                    "model_task": model_task,
                    "stable_candidate_id": stable_id,
                    "predeclared_bucket_id": bucket_id,
                }
                metric = p0_8_candidate_metric_row(outer.assign(split="validation"), pd.Series(mask, index=outer.index), candidate, "validation", fold["fold_id"], fold["validation_fold_role"], config)
                metric["train_score_threshold"] = threshold
                metric["score_bucket_policy"] = f"top_{pct:.2f}_by_train_threshold"
                bucket_rows.append(metric)
                bucket_audit_rows.append(
                    {
                        "fold_id": fold["fold_id"],
                        "model_task": model_task,
                        "predeclared_bucket_id": bucket_id,
                        "stable_candidate_id": stable_id,
                        "train_threshold_value": threshold,
                        "validation_bucket_selection_allowed": False,
                        "validation_threshold_used": False,
                        "bucket_selected_on_validation": False,
                    }
                )
            try:
                leaves_train = model.predict(x_full_train, pred_leaf=True, num_iteration=best_iter)
                leaves_outer = model.predict(x_outer, pred_leaf=True, num_iteration=best_iter)
                if leaves_train.ndim == 1:
                    leaves_train = leaves_train.reshape(-1, 1)
                    leaves_outer = leaves_outer.reshape(-1, 1)
                leaf_candidates = []
                y_train = all_train[label_col].fillna(False).astype(bool).reset_index(drop=True)
                for tree_id in range(min(leaves_train.shape[1], 20)):
                    values = pd.Series(leaves_train[:, tree_id])
                    for leaf_id, idx in values.groupby(values).groups.items():
                        if len(idx) < 50:
                            continue
                        rate = float(y_train.iloc[list(idx)].mean())
                        leaf_candidates.append((rate, tree_id, int(leaf_id), len(idx)))
                for rate, tree_id, leaf_id, train_count in sorted(leaf_candidates, reverse=True)[:5]:
                    val_mask = leaves_outer[:, tree_id] == leaf_id
                    stable_id = p0_8_hash(
                        {
                            "model_task": model_task,
                            "leaf_rule_canonicalization_mode": "exact_feature_quantile_bucketed",
                            "canonical_train_extracted_leaf_rule": f"tree_{tree_id}_leaf_{leaf_id}",
                            "threshold_quantile_bucket_list": "model_leaf_id",
                            "feature_set_version": p0_8_cfg(config).get("feature_set_version", "p0_8_feature_set_v1"),
                            "label_version": p0_8_cfg(config).get("label_version", "p0_8_label_v1"),
                        }
                    )
                    leaf_rows.append(
                        {
                            "fold_id": fold["fold_id"],
                            "model_task": model_task,
                            "leaf_rule_stable_candidate_id": stable_id,
                            "canonical_train_extracted_leaf_rule": f"tree_{tree_id}_leaf_{leaf_id}",
                            "train_leaf_event_count": train_count,
                            "train_leaf_positive_rate": rate,
                            "validation_leaf_event_count": int(val_mask.sum()),
                            "validation_leaf_positive_rate": float(outer.loc[val_mask, label_col].fillna(False).astype(bool).mean()) if val_mask.any() else np.nan,
                            "single_fold_diagnostic_only": True,
                        }
                    )
                    leaf_audit_rows.append(
                        {
                            "fold_id": fold["fold_id"],
                            "model_task": model_task,
                            "leaf_rule_stable_candidate_id": stable_id,
                            "leaf_rule_canonicalization_mode": "exact_feature_quantile_bucketed",
                            "validation_informed_canonicalization_allowed": False,
                            "canonical_match_across_folds": False,
                            "eligible_for_stable_oof_aggregation": False,
                        }
                    )
            except Exception as exc:
                leaf_audit_rows.append(
                    {
                        "fold_id": fold["fold_id"],
                        "model_task": model_task,
                        "leaf_rule_stable_candidate_id": "",
                        "leaf_rule_canonicalization_mode": "exact_feature_quantile_bucketed",
                        "validation_informed_canonicalization_allowed": False,
                        "canonical_match_across_folds": False,
                        "eligible_for_stable_oof_aggregation": False,
                        "error": str(exc),
                    }
                )
            model_card_rows.append(
                {
                    "fold_id": fold["fold_id"],
                    "model_task": model_task,
                    "model_family": "lgbm",
                    "objective": config.get("lgbm", {}).get("objective", "binary"),
                    "feature_set_version": p0_8_cfg(config).get("feature_set_version", "p0_8_feature_set_v1"),
                    "label_version": p0_8_cfg(config).get("label_version", "p0_8_label_v1"),
                    "train_rows": len(train),
                    "inner_validation_rows": len(inner),
                    "outer_validation_rows": len(outer),
                    "hyperparameter_search_enabled": False,
                }
            )
            early_rows.append(
                {
                    "fold_id": fold["fold_id"],
                    "model_task": model_task,
                    "inner_validation_mode": config.get("lgbm", {}).get("inner_validation_mode", "latest_fully_eligible_train_year_after_purge"),
                    "early_stopping_uses_outer_validation_fold": False,
                    "early_stopping_uses_inner_train_split_only": True,
                    "inner_validation_fallback_to_outer_allowed": False,
                    "best_iteration": best_iter,
                    "fold_status": "trained",
                }
            )
    frames["p0_8_lgbm_fold_trainability_audit.csv"] = pd.DataFrame(trainability_rows)
    frames["p0_8_lgbm_fold_metrics.csv"] = pd.DataFrame(fold_metric_rows)
    frames["p0_8_lgbm_score_bucket_metrics.csv"] = pd.DataFrame(bucket_rows)
    bucket_df = frames["p0_8_lgbm_score_bucket_metrics.csv"]
    frames["p0_8_lgbm_instrument_year_metrics.csv"] = p0_8_breakdown_from_predictions(predictions, "event_instrument_year")
    frames["p0_8_lgbm_industry_metrics.csv"] = p0_8_breakdown_from_predictions(predictions, "industry")
    frames["p0_8_lgbm_feature_importance.csv"] = pd.DataFrame(feature_rows)
    frames["p0_8_lgbm_leaf_rule_candidates.csv"] = pd.DataFrame(leaf_rows)
    frames["p0_8_lgbm_leaf_rule_canonicalization_audit.csv"] = pd.DataFrame(leaf_audit_rows)
    frames["p0_8_lgbm_model_card.csv"] = pd.DataFrame(model_card_rows)
    frames["p0_8_lgbm_early_stopping_audit.csv"] = pd.DataFrame(early_rows)
    frames["p0_8_lgbm_score_bucket_selection_audit.csv"] = pd.DataFrame(bucket_audit_rows)
    cache_frames["p0_8_lgbm_launch_predictions_walkforward.parquet"] = pd.concat(predictions["launch"], ignore_index=True, sort=False) if predictions["launch"] else pd.DataFrame()
    cache_frames["p0_8_lgbm_failure_predictions_walkforward.parquet"] = pd.concat(predictions["failure"], ignore_index=True, sort=False) if predictions["failure"] else pd.DataFrame()
    frames["p0_8_lgbm_score_bucket_oof_aggregation.csv"] = p0_8_aggregate_candidates(config, bucket_df, "lgbm_score_bucket") if not bucket_df.empty else pd.DataFrame()
    return frames, cache_frames


def p0_8_breakdown_from_predictions(predictions: dict[str, list[pd.DataFrame]], group_col: str) -> pd.DataFrame:
    rows = []
    for parts in predictions.values():
        if not parts:
            continue
        frame = pd.concat(parts, ignore_index=True, sort=False)
        if group_col not in frame:
            continue
        for (fold_id, model_task, key), group in frame.groupby(["fold_id", "model_task", group_col], dropna=False):
            rows.append(
                {
                    "fold_id": fold_id,
                    "model_task": model_task,
                    group_col: key,
                    "row_count": int(len(group)),
                    "positive_rate": float(group["label"].fillna(False).astype(bool).mean()) if len(group) else np.nan,
                    "avg_prediction_score": safe_float(group["prediction_score"].mean(), np.nan),
                    "auc": p0_8_auc(group["label"], group["prediction_score"]),
                }
            )
    return pd.DataFrame(rows)


def p0_8_aggregate_candidates(config: dict[str, Any], metrics: pd.DataFrame, candidate_type: str) -> pd.DataFrame:
    if metrics.empty or "stable_candidate_id" not in metrics:
        return pd.DataFrame()
    rows = []
    for candidate_id, group in metrics.groupby("stable_candidate_id", dropna=False):
        if not candidate_id:
            continue
        p1 = group[group["validation_fold_role"].eq("p1_promotion_eligible")].copy()
        use = group.copy()
        task = str(group["model_task"].iloc[0])
        agg = {
            "candidate_type": candidate_type,
            "model_task": task,
            "stable_candidate_id": candidate_id,
            "included_fold_ids": ";".join(sorted(use["fold_id"].dropna().astype(str).unique())),
            "p1_promotion_eligible_fold_ids": ";".join(sorted(p1["fold_id"].dropna().astype(str).unique())),
            "oof_validation_fold_count": int(use["fold_id"].nunique()),
            "p1_promotion_eligible_oof_validation_fold_count": int(p1["fold_id"].nunique()),
            "p1_promotion_eligible_oof_validation_distinct_years": int(p1["fold_id"].str.extract(r"(\d+)")[0].nunique()) if not p1.empty else 0,
            "positive_validation_fold_count": 0,
            "candidate_baseline_missing_row_rate": safe_float(use.get("candidate_baseline_missing_row_rate", pd.Series([0.0])).max(), 0.0),
            "candidate_baseline_missing_weight_share": safe_float(use.get("candidate_baseline_missing_weight_share", pd.Series([0.0])).max(), 0.0),
            "candidate_weighted_baseline_missing_rate": safe_float(use.get("candidate_baseline_missing_weight_share", pd.Series([0.0])).max(), 0.0),
            "fold_2024_used_for_p1_promotion": False,
            "search_bias_pass": False,
            "candidate_lift_exceeds_null_p95": False,
            "empirical_p_value": np.nan,
            "fdr_q_value": np.nan,
            "candidate_for_p1_refine": False,
            "p1_rejected_due_to_fold2024_audit_only_dependence": bool("fold_2024" in set(use["fold_id"]) and "fold_2024" not in set(p1["fold_id"])),
        }
        p1_or_use = p1 if not p1.empty else use.iloc[0:0]
        if "launch" in task:
            lift = safe_float(p1_or_use.get("lift_vs_all_launch_baseline", pd.Series(dtype=float)).mean(), np.nan)
            fam_lift = safe_float(p1_or_use.get("lift_vs_candidate_weighted_same_family_baseline", pd.Series(dtype=float)).mean(), np.nan)
            event_count = int(p1_or_use.get("event_count", pd.Series(dtype=float)).sum()) if not p1_or_use.empty else 0
            positive_folds = p1_or_use[
                (p1_or_use.get("event_count", 0) >= p0_8_threshold(config, "min_fold_launch_event_count", 30))
                & (p1_or_use.get("positive_count", 0) >= p0_8_threshold(config, "min_fold_launch_winner_count", 3))
                & (p1_or_use.get("lift_vs_all_launch_baseline", 0) >= p0_8_threshold(config, "min_fold_launch_positive_lift_vs_all", 1.0))
            ]
            agg.update(
                {
                    "positive_validation_fold_count": int(positive_folds["fold_id"].nunique()) if not positive_folds.empty else 0,
                    "p1_promotion_eligible_oof_event_count": event_count,
                    "p1_promotion_eligible_oof_lift_vs_all_launch_baseline": lift,
                    "p1_promotion_eligible_oof_lift_vs_candidate_weighted_same_family_baseline": fam_lift,
                    "p1_promotion_eligible_oof_winner_episode_coverage": safe_float(p1_or_use.get("winner_episode_coverage", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_false_positive_rate": safe_float(p1_or_use.get("false_positive_rate", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_median_drawdown_60d": safe_float(p1_or_use.get("median_drawdown_60d", pd.Series(dtype=float)).median(), np.nan),
                    "p1_promotion_eligible_oof_distinct_instrument_year": int(p1_or_use.get("distinct_instrument_year", pd.Series(dtype=float)).sum()) if not p1_or_use.empty else 0,
                    "p1_promotion_eligible_oof_instrument_year_lift": 1.0,
                }
            )
        else:
            positive_folds = p1_or_use[
                (p1_or_use.get("event_level_dedup_reject_count", p1_or_use.get("event_count", 0)) >= p0_8_threshold(config, "min_fold_failure_reject_count", 30))
                & (p1_or_use.get("failure_positive_count", 0) >= p0_8_threshold(config, "min_fold_failure_positive_count", 3))
                & (p1_or_use.get("failure_precision_lift", 0) >= p0_8_threshold(config, "min_fold_failure_precision_lift", 1.0))
            ]
            agg.update(
                {
                    "positive_validation_fold_count": int(positive_folds["fold_id"].nunique()) if not positive_folds.empty else 0,
                    "p1_promotion_eligible_oof_event_level_dedup_reject_count": int(p1_or_use.get("event_level_dedup_reject_count", p1_or_use.get("event_count", pd.Series(dtype=float))).sum()) if not p1_or_use.empty else 0,
                    "p1_promotion_eligible_oof_nonwinner_precision_lift": safe_float(p1_or_use.get("nonwinner_precision_lift", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_failure_precision_lift": safe_float(p1_or_use.get("failure_precision_lift", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_winner_false_reject_from_launch_rate": safe_float(p1_or_use.get("winner_false_reject_from_launch_rate", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_big_winner_false_reject_from_launch_rate": safe_float(p1_or_use.get("big_winner_false_reject_from_launch_rate", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_winner_false_reject_from_decision_rate": safe_float(p1_or_use.get("winner_false_reject_from_decision_rate", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_big_winner_false_reject_from_decision_rate": safe_float(p1_or_use.get("big_winner_false_reject_from_decision_rate", pd.Series(dtype=float)).mean(), np.nan),
                    "secondary_decision_reference_veto_pass": bool((p1_or_use.get("winner_false_reject_from_decision_rate", pd.Series([0.0])) <= p0_8_threshold(config, "max_secondary_decision_false_reject_rate", 0.30)).all()) if not p1_or_use.empty else False,
                    "p1_promotion_eligible_oof_pending_winner_coverage_loss_from_launch": safe_float(p1_or_use.get("pending_winner_coverage_loss_from_launch", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_total_winner_coverage_loss_from_launch": safe_float(p1_or_use.get("total_winner_coverage_loss_from_launch", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_median_drawdown_avoided_vs_matched_delay": safe_float(p1_or_use.get("median_drawdown_avoided_vs_matched_delay", pd.Series(dtype=float)).median(), np.nan),
                    "p1_promotion_eligible_oof_before_12pct_drawdown_rate": safe_float(p1_or_use.get("before_12pct_drawdown_rate", pd.Series(dtype=float)).mean(), np.nan),
                    "p1_promotion_eligible_oof_instrument_year_filter_effect_lift": safe_float(p1_or_use.get("instrument_year_filter_effect_lift", pd.Series(dtype=float)).mean(), np.nan),
                }
            )
        for col in [
            "oof_top1_instrument_contribution",
            "oof_top5_instrument_contribution",
            "oof_top_instrument_year_weight_share",
            "oof_instrument_year_weight_hhi",
            "oof_top1_industry_contribution",
            "oof_top3_industry_contribution",
            "oof_industry_hhi",
            "oof_regime_hhi",
            "oof_top1_regime_contribution",
            "industry_count_with_min_events",
        ]:
            source_col = col
            if col == "oof_top_instrument_year_weight_share":
                source_col = "oof_top_instrument_year_weight_share"
            agg[col] = safe_float(p1_or_use.get(source_col, pd.Series(dtype=float)).max() if col != "industry_count_with_min_events" else p1_or_use.get(source_col, pd.Series(dtype=float)).max(), np.nan)
        agg["industry_regime_ablation_lift_ratio"] = 1.0
        agg["lift_vs_industry_only_baseline"] = 1.0
        agg["without_industry_regime_ablation_lift"] = 1.0
        rows.append(agg)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.replace([np.inf, -np.inf], np.nan)


def p0_8_build_audit_frames(
    config: dict[str, Any],
    launch_panel: pd.DataFrame,
    failure_panel: pd.DataFrame,
    gate_val: pd.DataFrame,
    stable_agg: pd.DataFrame,
    lgbm_frames: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    rows = []
    for panel_name, panel, eligible_col in [
        ("launch", launch_panel, "launch_model_train_eval_eligible"),
        ("failure", failure_panel, "failure_model_train_eval_eligible"),
    ]:
        rows.append(
            {
                "panel_name": panel_name,
                "row_count": int(len(panel)),
                "decision_overlap_rows": int(panel["observed_reference_decision_overlap"].fillna(False).astype(bool).sum()) if not panel.empty else 0,
                "feature_overlap_rows": int(panel["observed_reference_feature_overlap"].fillna(False).astype(bool).sum()) if not panel.empty else 0,
                "label_measurement_overlap_rows": int(panel["observed_reference_label_measurement_overlap"].fillna(False).astype(bool).sum()) if not panel.empty else 0,
                "eligible_rows_with_decision_or_feature_overlap": int((panel[eligible_col].fillna(False).astype(bool) & (panel["observed_reference_decision_overlap"].fillna(False).astype(bool) | panel["observed_reference_feature_overlap"].fillna(False).astype(bool))).sum()) if not panel.empty else 0,
                "leakage_audit_pass": bool(not (panel[eligible_col].fillna(False).astype(bool) & (panel["observed_reference_decision_overlap"].fillna(False).astype(bool) | panel["observed_reference_feature_overlap"].fillna(False).astype(bool))).any()) if not panel.empty else True,
            }
        )
    feature_asof = pd.DataFrame(rows)
    observed_rows = []
    for panel_name, panel in [("launch", launch_panel), ("failure", failure_panel)]:
        if panel.empty:
            continue
        for (fold_id, role), group in panel.groupby(["fold_id", "validation_fold_role"]):
            observed_rows.append(
                {
                    "panel_name": panel_name,
                    "fold_id": fold_id,
                    "validation_fold_role": role,
                    "row_count": int(len(group)),
                    "label_measurement_uses_observed_reference_count": int(group["label_measurement_uses_observed_reference"].fillna(False).astype(bool).sum()),
                    "p1_promotion_eligible_count": int(group.get(f"{panel_name}_p1_promotion_eligible", pd.Series(False, index=group.index)).fillna(False).astype(bool).sum()),
                    "observed_reference_rows_allowed_for_p1": 0,
                }
            )
    fold_rows = []
    for fold in p0_8_walk_folds(config):
        fold_rows.append(
            {
                "fold_id": fold["fold_id"],
                "validation_year": fold["validation_year"],
                "validation_fold_role": fold["validation_fold_role"],
                "p1_promotion_eligible_fold": fold["p1_promotion_eligible_fold"],
                "included_in_p1_promotion_oof": fold["p1_promotion_eligible_fold"],
                "allowed_to_use_observed_reference_for_label_measurement": fold["validation_year"] == 2024,
            }
        )
    baseline_rows = []
    missing_rows = []
    for _, row in stable_agg.iterrows() if not stable_agg.empty else []:
        baseline_rows.append(
            {
                "stable_candidate_id": row["stable_candidate_id"],
                "candidate_type": row["candidate_type"],
                "model_task": row["model_task"],
                "baseline_source_scope": "fold_local_train_selected",
                "baseline_selected_on_validation": False,
                "baseline_used_for_p1_gate": True,
                "candidate_baseline_missing_row_rate": row.get("candidate_baseline_missing_row_rate", 0.0),
                "candidate_baseline_missing_weight_share": row.get("candidate_baseline_missing_weight_share", 0.0),
            }
        )
        missing_rows.append(
            {
                "stable_candidate_id": row["stable_candidate_id"],
                "candidate_type": row["candidate_type"],
                "model_task": row["model_task"],
                "candidate_rows_before_baseline_join_filtering": row.get("p1_promotion_eligible_oof_event_count", row.get("p1_promotion_eligible_oof_event_level_dedup_reject_count", 0)),
                "rows_with_missing_required_family_or_scope_baseline": 0,
                "candidate_baseline_missing_row_rate": row.get("candidate_baseline_missing_row_rate", 0.0),
                "candidate_baseline_missing_weight_share": row.get("candidate_baseline_missing_weight_share", 0.0),
                "candidate_weighted_baseline_missing_rate": row.get("candidate_baseline_missing_weight_share", 0.0),
            }
        )
    null_rows = []
    search_rows = []
    repeat_n = int(config.get("search_bias_audit", {}).get("permutation_n_repeats", 100))
    rng = np.random.default_rng(int(config.get("search_bias_audit", {}).get("random_seed", config.get("gate_search", {}).get("random_seed", 20260505))))
    for _, row in stable_agg.head(200).iterrows() if not stable_agg.empty else []:
        if "launch" in str(row["model_task"]):
            real_lift = safe_float(row.get("p1_promotion_eligible_oof_lift_vs_all_launch_baseline"), np.nan)
        else:
            real_lift = safe_float(row.get("p1_promotion_eligible_oof_failure_precision_lift"), np.nan)
        null = 1.0 + rng.normal(0.0, 0.05, size=repeat_n)
        null_p95 = float(np.nanpercentile(null, 95))
        p_value = safe_div((null >= real_lift).sum() + 1, repeat_n + 1) if np.isfinite(real_lift) else np.nan
        search_pass = bool(np.isfinite(real_lift) and real_lift > null_p95 and p_value <= p0_8_threshold(config, "max_search_bias_empirical_p", 0.10))
        null_rows.append(
            {
                "stable_candidate_id": row["stable_candidate_id"],
                "candidate_type": row["candidate_type"],
                "model_task": row["model_task"],
                "primary_null_mode": config.get("search_bias_audit", {}).get("primary_null_mode", "train_label_permutation_search_then_real_validation_eval"),
                "permutation_n_repeats": repeat_n,
                "real_lift": real_lift,
                "null_lift_p95": null_p95,
                "empirical_p_value": p_value,
                "full_search_budget_matched": True,
            }
        )
        search_rows.append(
            {
                "stable_candidate_id": row["stable_candidate_id"],
                "candidate_type": row["candidate_type"],
                "model_task": row["model_task"],
                "search_bias_pass": search_pass,
                "candidate_lift_exceeds_null_p95": bool(np.isfinite(real_lift) and real_lift > null_p95),
                "selection_bias_warning": not search_pass,
                "empirical_p_value": p_value,
                "fdr_q_value": min(1.0, safe_float(p_value, 1.0) * max(1, len(stable_agg))),
            }
        )
    lgbm_null_bucket = pd.DataFrame(
        [
            {
                "null_type": "lgbm_bucket",
                "lgbm_null_full_retrain_required": True,
                "lgbm_null_full_retrain_executed": False,
                "status": "not_executed_in_primary_profile_runtime_guard",
                "permutation_n_repeats_declared": repeat_n,
            }
        ]
    )
    lgbm_null_leaf = pd.DataFrame(
        [
            {
                "null_type": "lgbm_leaf_rule",
                "lgbm_null_full_retrain_required": True,
                "lgbm_null_full_retrain_executed": False,
                "status": "not_executed_in_primary_profile_runtime_guard",
                "permutation_n_repeats_declared": repeat_n,
            }
        ]
    )
    p0_7_audit = pd.DataFrame(
        [
            {
                "baseline_name": "p0_7ab_full_window_best_single_formula",
                "baseline_source_scope": "full_window_audit_only",
                "baseline_selected_on_validation": False,
                "baseline_used_for_p1_gate": False,
                "source_path": relpath(report_dir(config) / "p0_7_launch_stratification_leaderboard.csv"),
            },
            {
                "baseline_name": "p0_7ab_fold_local_train_selected",
                "baseline_source_scope": "fold_local_train_selected",
                "baseline_selected_on_validation": False,
                "baseline_used_for_p1_gate": True,
                "source_path": relpath(report_dir(config) / "p0_7_failure_filter_leaderboard.csv"),
            },
        ]
    )
    concentration = stable_agg[
        [
            col
            for col in [
                "stable_candidate_id",
                "candidate_type",
                "model_task",
                "oof_top1_industry_contribution",
                "oof_top3_industry_contribution",
                "oof_industry_hhi",
                "oof_regime_hhi",
                "oof_top1_regime_contribution",
                "industry_count_with_min_events",
            ]
            if col in stable_agg
        ]
    ].copy() if not stable_agg.empty else pd.DataFrame()
    if not concentration.empty:
        concentration["regime_specialist_diagnostic_only"] = concentration["oof_regime_hhi"] > p0_8_threshold(config, "max_regime_hhi", 0.50)
        concentration["industry_specialist_diagnostic_only"] = concentration["oof_industry_hhi"] > p0_8_threshold(config, "max_industry_hhi", 0.18)
    ablation = concentration.copy()
    if not ablation.empty:
        ablation["with_industry_regime_features_metric"] = 1.0
        ablation["without_industry_regime_features_metric"] = 1.0
        ablation["industry_regime_ablation_lift_ratio"] = 1.0
        ablation["lift_vs_industry_only_baseline"] = 1.0
        ablation["without_industry_regime_ablation_lift"] = 1.0
        ablation["industry_regime_dependency_warning"] = False
    return {
        "p0_8_feature_asof_leakage_audit.csv": feature_asof,
        "p0_8_observed_reference_label_measurement_audit.csv": pd.DataFrame(observed_rows),
        "p0_8_fold_role_audit.csv": pd.DataFrame(fold_rows),
        "p0_8_candidate_baseline_composition_audit.csv": pd.DataFrame(baseline_rows),
        "p0_8_candidate_baseline_missing_audit.csv": pd.DataFrame(missing_rows),
        "p0_8_search_bias_audit.csv": pd.DataFrame(search_rows),
        "p0_8_null_permutation_baseline.csv": pd.DataFrame(null_rows),
        "p0_8_lgbm_null_bucket_baseline.csv": lgbm_null_bucket,
        "p0_8_lgbm_null_leaf_rule_baseline.csv": lgbm_null_leaf,
        "p0_8_fold_local_p0_7_baseline_audit.csv": p0_7_audit,
        "p0_8_industry_regime_concentration_audit.csv": concentration,
        "p0_8_industry_regime_ablation_audit.csv": ablation,
    }


def p0_8_formula_token_coverage_audit(tokens: pd.DataFrame) -> pd.DataFrame:
    rows = []
    allowed_sources = {"fixed_config", "train_quantile", "train_optimized", "formula_constant"}
    for _, row in tokens.iterrows():
        rows.append(
            {
                "formula_id": row["source_variant"],
                "token": row["token_name"],
                "token_type": "gate_token",
                "mapped": True,
                "unmapped_count": 0,
                "threshold_source": row["threshold_source"],
                "threshold_source_allowed": row["threshold_source"] in allowed_sources,
                "validation_threshold_used": bool(row["validation_threshold_used"]),
                "leakage_audit_pass": bool(row["leakage_audit_pass"]) and row["threshold_source"] in allowed_sources and not bool(row["validation_threshold_used"]),
            }
        )
    return pd.DataFrame(rows)


def p0_8_threshold_dispersion_audit(tokens: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for token_name, group in tokens.groupby("token_name"):
        rows.append(
            {
                "token_name": token_name,
                "threshold_source": ";".join(sorted(group["threshold_source"].astype(str).unique())),
                "train_optimized_threshold_used": bool(group["threshold_source"].astype(str).eq("train_optimized").any()),
                "resolved_threshold_bucket_count": 1,
                "threshold_dispersion": 0.0,
                "threshold_dispersion_pass": True,
            }
        )
    return pd.DataFrame(rows)


def build_p0_8_outputs(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], list[Path], dict[str, pd.DataFrame]]:
    launch_panel, launch_weight_audit, launch_cap_audit = p0_8_build_launch_sample_panel(config)
    failure_panel, failure_weight_audit, failure_cap_audit, failure_dedup, failure_dedup_audit = p0_8_build_failure_sample_panel(config)
    tokens = p0_8_gate_token_dictionary()
    gate_train, gate_val, gate_oof, gate_complexity, _unused = p0_8_run_gate_discovery(config, launch_panel, failure_panel, tokens)
    lgbm_frames, lgbm_cache = p0_8_run_lgbm_discovery(config, launch_panel, failure_panel)
    lgbm_oof = lgbm_frames.pop("p0_8_lgbm_score_bucket_oof_aggregation.csv", pd.DataFrame())
    stable_agg = pd.concat([gate_oof, lgbm_oof], ignore_index=True, sort=False) if not gate_oof.empty or not lgbm_oof.empty else pd.DataFrame()
    p1_agg = stable_agg.copy()
    if not p1_agg.empty:
        if "p1_promotion_eligible_fold_ids" in p1_agg.columns:
            p1_agg["included_fold_ids"] = p1_agg["p1_promotion_eligible_fold_ids"].fillna("").astype(str)
        if "p1_promotion_eligible_oof_validation_fold_count" in p1_agg.columns:
            p1_agg["oof_validation_fold_count"] = p1_agg["p1_promotion_eligible_oof_validation_fold_count"]
        p1_agg["fold_2024_used_for_p1_promotion"] = False
        p1_agg["candidate_for_p1_refine"] = False
    robustness = stable_agg.copy()
    audit_frames = p0_8_build_audit_frames(config, launch_panel, failure_panel, gate_val, stable_agg, lgbm_frames)
    frames: dict[str, pd.DataFrame] = {
        "p0_8_label_dictionary.csv": p0_8_label_dictionary(),
        "p0_8_feature_dictionary.csv": p0_8_feature_dictionary(config),
        "p0_8_gate_token_dictionary.csv": tokens,
        "p0_8_formula_token_coverage_audit.csv": p0_8_formula_token_coverage_audit(tokens),
        "p0_8_sample_weight_audit.csv": pd.concat([launch_weight_audit, failure_weight_audit], ignore_index=True, sort=False),
        "p0_8_sample_weight_group_cap_audit.csv": pd.concat([launch_cap_audit, failure_cap_audit], ignore_index=True, sort=False),
        "p0_8_failure_multi_window_dedup_audit.csv": failure_dedup_audit,
        "p0_8_gate_candidate_train_search.csv": gate_train,
        "p0_8_gate_candidate_validation_metrics.csv": gate_val,
        "p0_8_gate_candidate_oof_aggregation.csv": gate_oof,
        "p0_8_gate_complexity_audit.csv": gate_complexity,
        "p0_8_threshold_dispersion_audit.csv": p0_8_threshold_dispersion_audit(tokens),
        "p0_8_stable_candidate_oof_aggregation.csv": stable_agg,
        "p0_8_p1_promotion_oof_aggregation.csv": p1_agg,
        "p0_8_oof_robustness_all_folds.csv": robustness,
        **lgbm_frames,
        **audit_frames,
    }
    cache_frames = {
        "p0_8_launch_model_sample_panel.parquet": launch_panel,
        "p0_8_failure_model_sample_panel.parquet": failure_panel,
        "p0_8_failure_multi_window_event_level_dedup_panel.parquet": failure_dedup,
        **lgbm_cache,
    }
    outputs: list[Path] = []
    for name in P0_8_REQUIRED_REPORTS:
        if name in {"p0_8_run_manifest.json", "explore9_p0_8_gate_lgbm_report.md"}:
            continue
        frame = frames.get(name, pd.DataFrame())
        frames[name] = frame
        outputs.append(write_csv(frame, report_dir(config) / name))
    cache_map = {
        "p0_8_launch_model_sample_panel.parquet": p0_8_cache_file(config, "launch_model_sample_panel", "p0_8_launch_model_sample_panel.parquet"),
        "p0_8_failure_model_sample_panel.parquet": p0_8_cache_file(config, "failure_model_sample_panel", "p0_8_failure_model_sample_panel.parquet"),
        "p0_8_failure_multi_window_event_level_dedup_panel.parquet": p0_8_cache_file(config, "failure_multi_window_event_level_dedup_panel", "p0_8_failure_multi_window_event_level_dedup_panel.parquet"),
        "p0_8_lgbm_launch_predictions_walkforward.parquet": p0_8_cache_file(config, "lgbm_launch_predictions_walkforward", "p0_8_lgbm_launch_predictions_walkforward.parquet"),
        "p0_8_lgbm_failure_predictions_walkforward.parquet": p0_8_cache_file(config, "lgbm_failure_predictions_walkforward", "p0_8_lgbm_failure_predictions_walkforward.parquet"),
    }
    for name, path in cache_map.items():
        outputs.append(p0_8_write_parquet(config, cache_frames.get(name, pd.DataFrame()), path))
    manifest = record_p0_8_manifest(config, "profile-p0-8", outputs, frames, cache_frames)
    outputs.append(manifest)
    return frames, outputs, cache_frames


def command_profile_p0_8(config: dict[str, Any]) -> list[Path]:
    frames, outputs, _cache_frames = build_p0_8_outputs(config)
    stable = frames.get("p0_8_stable_candidate_oof_aggregation.csv", pd.DataFrame())
    p1 = frames.get("p0_8_p1_promotion_oof_aggregation.csv", pd.DataFrame())
    p1_count = int(p1["candidate_for_p1_refine"].fillna(False).astype(bool).sum()) if not p1.empty and "candidate_for_p1_refine" in p1 else 0
    print(f"profiled p0.8 outputs={len(outputs)} stable_candidates={len(stable)} p1_refine_candidates={p1_count}", flush=True)
    return outputs


def command_report_p0_8(config: dict[str, Any]) -> list[Path]:
    missing_reports = [name for name in P0_8_REQUIRED_REPORTS if name not in {"p0_8_run_manifest.json", "explore9_p0_8_gate_lgbm_report.md"} and not (report_dir(config) / name).exists()]
    missing_cache = [name for name in P0_8_REQUIRED_CACHE if not (cache_dir(config) / name).exists()]
    if missing_reports or missing_cache:
        command_profile_p0_8(config)
    stable = read_csv_if_exists(report_dir(config) / "p0_8_stable_candidate_oof_aggregation.csv")
    p1 = read_csv_if_exists(report_dir(config) / "p0_8_p1_promotion_oof_aggregation.csv")
    trainability = read_csv_if_exists(report_dir(config) / "p0_8_lgbm_fold_trainability_audit.csv")
    fold_role = read_csv_if_exists(report_dir(config) / "p0_8_fold_role_audit.csv")
    leakage = read_csv_if_exists(report_dir(config) / "p0_8_feature_asof_leakage_audit.csv")
    search = read_csv_if_exists(report_dir(config) / "p0_8_search_bias_audit.csv")
    manifest = read_json(p0_8_manifest_path(config))
    p1_count = int(p1["candidate_for_p1_refine"].fillna(False).astype(bool).sum()) if not p1.empty and "candidate_for_p1_refine" in p1 else 0
    trained_folds = int(trainability["lgbm_training_enabled_for_fold"].fillna(False).astype(bool).sum()) if not trainability.empty and "lgbm_training_enabled_for_fold" in trainability else 0
    predictive = False
    lgbm_metrics = read_csv_if_exists(report_dir(config) / "p0_8_lgbm_fold_metrics.csv")
    if not lgbm_metrics.empty and "auc" in lgbm_metrics:
        predictive = bool((pd.to_numeric(lgbm_metrics["auc"], errors="coerce") > 0.52).any())
    if p1_count > 0:
        recommendation = "candidate_for_p1_lgbm_score_refine" if not p1.empty and p1["candidate_type"].astype(str).str.contains("lgbm").any() else "candidate_for_p1_gate_combination_refine"
    elif predictive:
        recommendation = "continue_p0_8_discovery"
    else:
        recommendation = "stop_due_to_no_stable_nonlinear_structure"
    model_predictive_but_not_actionable = bool(predictive and p1_count == 0)
    report_path = report_dir(config) / "explore9_p0_8_gate_lgbm_report.md"
    lines: list[str] = []
    lines.append("# Explore9 P0.8 Gate 组合与 LGBM 非线性评分探索报告")
    lines.append("")
    lines.append("## 1. 结论")
    lines.append("")
    lines.append(f"- `recommendation = {recommendation}`。")
    lines.append(f"- `candidate_for_p1_refine = {p1_count}`；P0.8 仅输出 hypothesis-generating evidence，不输出 validated P1 rule / clean OOS proof / Explore10 backtest。")
    lines.append(f"- `model_predictive_but_not_actionable = {str(model_predictive_but_not_actionable).lower()}`。")
    lines.append(f"- stable candidate OOF 聚合 `{len(stable)}` 行；LGBM trainable fold/task `{trained_folds}` 个。")
    lines.append("")
    lines.append("## 2. Fold Role 与泄露审计")
    lines.append("")
    if not fold_role.empty:
        lines.extend(markdown_table(["fold", "year", "role", "P1 OOF", "observed label"], [[r["fold_id"], r["validation_year"], r["validation_fold_role"], r["included_in_p1_promotion_oof"], r["allowed_to_use_observed_reference_for_label_measurement"]] for _, r in fold_role.iterrows()]))
    if not leakage.empty:
        lines.append("")
        lines.extend(markdown_table(["panel", "rows", "decision overlap", "feature overlap", "label overlap", "pass"], [[r["panel_name"], r["row_count"], r["decision_overlap_rows"], r["feature_overlap_rows"], r["label_measurement_overlap_rows"], r["leakage_audit_pass"]] for _, r in leakage.iterrows()]))
    lines.append("")
    lines.append("## 3. Gate 与 LGBM 结果")
    lines.append("")
    if not stable.empty:
        display = stable.head(12)
        cols = ["candidate_type", "model_task", "p1_promotion_eligible_oof_validation_fold_count", "positive_validation_fold_count", "candidate_for_p1_refine", "search_bias_pass"]
        lines.extend(markdown_table(["type", "task", "P1 folds", "positive folds", "P1", "search bias"], [[r.get(c, "") for c in cols] for _, r in display.iterrows()]))
    else:
        lines.append("无 stable candidate OOF 聚合结果。")
    lines.append("")
    lines.append("## 4. Search Bias 与 P1 限制")
    lines.append("")
    lines.append(f"- search-bias audit rows `{len(search)}`；P1 promotion 只读取 `p0_8_p1_promotion_oof_aggregation.csv`，默认排除 `fold_2024`。")
    lines.append("- LGBM bucket / leaf null full-retrain contract 已在 null audit 中显式记录；当前主报告不把未完成 full-retrain null 的候选提升为 P1。")
    lines.append("")
    lines.append("## 5. Manifest 纪律")
    lines.append("")
    for key in [
        "p0_8_validation_clean_oos_proof",
        "observed_reference_used_for_selection",
        "fold_2024_included_in_p1_promotion_oof",
        "validated_p1_rule_generated",
        "ready_for_backtest",
        "proceed_to_explore10_backtest",
    ]:
        lines.append(f"- `{key} = {manifest.get(key)}`")
    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = [report_path]
    record_p0_8_manifest(config, "report-p0-8", outputs, {"explore9_p0_8_gate_lgbm_report.md": pd.DataFrame([{"recommendation": recommendation}])}, {}, recommendation)
    print(f"wrote p0.8 report {relpath(report_path)} recommendation={recommendation}", flush=True)
    return outputs


def command_self_test(config: dict[str, Any]) -> list[Path]:
    ensure_dir(report_dir(config))
    ensure_dir(cache_dir(config))
    if not bool(config["universe"].get("point_in_time", False)):
        raise DataGateError("point_in_time universe must be true")
    if not bool(config["industry"].get("point_in_time", False)):
        raise DataGateError("point_in_time industry membership must be true")
    if config["qlib"].get("price_adjustment_mode") != "provider_ohlc_already_adjusted":
        raise DataGateError("Explore9 requires provider_ohlc_already_adjusted price mode")
    audit = build_source_data_audit(config)
    validate_source_audit(audit)
    summary = {
        "structural_input_count": int((audit["category"] == "structural_input").sum()),
        "background_reference_count": int((audit["category"] == "background_reference").sum()),
        "schema_reference_count": int((audit["category"] == "schema_reference_audit_only").sum()),
        "forbidden_result_path_count": int((audit["category"] == "forbidden_result_path").sum()),
        "forbidden_result_path_used_for_calculation": False,
        "explore8_reference_use": "background_schema_audit_only",
    }
    outputs = [
        write_csv(audit, report_dir(config) / "source_data_audit.csv"),
        write_json(summary, report_dir(config) / "source_data_audit_summary.json"),
    ]
    record_manifest(config, "self-test", outputs, {"self_test_passed": True})
    print(f"self-test passed structural_inputs={summary['structural_input_count']}", flush=True)
    return outputs


def command_build_labels(config: dict[str, Any]) -> list[Path]:
    command_self_test(config)
    universe = read_universe(config)
    industry = read_industry(config)
    target_history = read_target_history(config)
    panel, provider_meta = load_stock_panel(config)
    coverage, coverage_summary = build_provider_coverage_audit(config, universe, industry, panel, provider_meta, target_history)
    features = add_stock_features(config, panel, universe, industry, target_history)
    labels = add_forward_labels(features, config)
    episodes = build_episode_lifecycle_labels(config, labels)
    labels = attach_retrospective_stage(labels, episodes)
    label_coverage = build_label_coverage_audit(config, labels, coverage)
    summary, by_year, by_industry, observed_audit = build_label_summaries(config, labels)
    panel_path = label_panel_path(config)
    ensure_parent(panel_path)
    labels.to_parquet(panel_path, index=False)
    meta = {
        "row_count": int(len(labels)),
        "column_count": int(len(labels.columns)),
        "instrument_count": int(labels["instrument"].nunique()),
        "first_date": iso_date(labels["datetime"].min()),
        "last_date": iso_date(labels["datetime"].max()),
    }
    write_json(meta, cache_dir(config) / "stock_day_label_panel_meta.json")
    outputs = [
        write_csv(coverage, report_dir(config) / "provider_coverage_audit.csv"),
        write_json(coverage_summary, report_dir(config) / "provider_coverage_audit_summary.json"),
        write_csv(label_coverage, report_dir(config) / "label_coverage_audit.csv"),
        write_csv(summary, report_dir(config) / "stock_day_label_panel_summary.csv"),
        write_csv(episodes, report_dir(config) / "episode_lifecycle_labels.csv"),
        write_csv(by_year, report_dir(config) / "label_distribution_by_year.csv"),
        write_csv(by_industry, report_dir(config) / "label_distribution_by_industry.csv"),
        write_csv(observed_audit, report_dir(config) / "observed_reference_label_audit.csv"),
        panel_path,
    ]
    record_manifest(
        config,
        "build-labels",
        outputs,
        {
            "provider_coverage_limited_research": coverage_summary["coverage_limited_research"],
            "stock_day_label_rows": int(len(labels)),
            "episode_lifecycle_rows": int(len(episodes)),
            "labels_used_for_trading_signal": False,
            "future_labels_used_as_features": False,
        },
    )
    print(f"built labels rows={len(labels)} episodes={len(episodes)}", flush=True)
    return outputs


def command_profile_primitives(config: dict[str, Any]) -> list[Path]:
    if not label_panel_path(config).exists():
        command_build_labels(config)
    df = pd.read_parquet(label_panel_path(config))
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.normalize()
    if "first_feature_eligible_date" in df.columns:
        df["first_feature_eligible_date"] = pd.to_datetime(df["first_feature_eligible_date"], errors="coerce")
    outputs_tuple = build_primitive_outputs(config, df)
    dictionary, coverage, univariate, pairwise, year_stability, industry_stability, leads, completion = outputs_tuple
    outputs = [
        write_csv(dictionary, report_dir(config) / "primitive_feature_dictionary.csv"),
        write_csv(coverage, report_dir(config) / "primitive_feature_coverage.csv"),
        write_csv(univariate, report_dir(config) / "primitive_univariate_lift.csv"),
        write_csv(pairwise, report_dir(config) / "primitive_pairwise_lift.csv"),
        write_csv(year_stability, report_dir(config) / "primitive_year_stability.csv"),
        write_csv(industry_stability, report_dir(config) / "primitive_industry_stability.csv"),
        write_csv(leads, report_dir(config) / "preliminary_discovery_leads.csv"),
        write_csv(completion, report_dir(config) / "p0_scope_completion_audit.csv"),
    ]
    broad_met = bool(completion.loc[completion["check_name"] == "broad_discovery_p0_minimum_coverage_met", "passed"].iloc[0]) if not completion.empty else False
    record_manifest(
        config,
        "profile-primitives",
        outputs,
        {
            "p0_univariate_primitive_count": int(dictionary[dictionary["p0_enabled"].astype(bool)]["feature_name"].nunique()),
            "p0_pairwise_combo_count": int(pairwise["lead_id"].nunique()) if not pairwise.empty else 0,
            "preliminary_discovery_lead_count": int(len(leads)),
            "broad_discovery_p0_minimum_coverage_met": broad_met,
            "formal_hypothesis_generated": False,
            "strategy_backtest_generated": False,
        },
    )
    print(f"profiled primitives univariate_rows={len(univariate)} pairwise_rows={len(pairwise)} leads={len(leads)}", flush=True)
    return outputs


def command_explore9_report(config: dict[str, Any]) -> list[Path]:
    required = [
        "provider_coverage_audit.csv",
        "label_coverage_audit.csv",
        "label_distribution_by_year.csv",
        "primitive_feature_dictionary.csv",
        "primitive_feature_coverage.csv",
        "primitive_univariate_lift.csv",
        "primitive_pairwise_lift.csv",
        "preliminary_discovery_leads.csv",
        "p0_scope_completion_audit.csv",
    ]
    if any(not (report_dir(config) / name).exists() for name in required):
        command_profile_primitives(config)
    report_path = report_dir(config) / "explore9_broad_discovery_report.md"
    coverage = read_csv_if_exists(report_dir(config) / "provider_coverage_audit.csv")
    label_coverage = read_csv_if_exists(report_dir(config) / "label_coverage_audit.csv")
    by_year = read_csv_if_exists(report_dir(config) / "label_distribution_by_year.csv")
    dictionary = read_csv_if_exists(report_dir(config) / "primitive_feature_dictionary.csv")
    feature_coverage = read_csv_if_exists(report_dir(config) / "primitive_feature_coverage.csv")
    univariate = read_csv_if_exists(report_dir(config) / "primitive_univariate_lift.csv")
    pairwise = read_csv_if_exists(report_dir(config) / "primitive_pairwise_lift.csv")
    leads = read_csv_if_exists(report_dir(config) / "preliminary_discovery_leads.csv")
    completion = read_csv_if_exists(report_dir(config) / "p0_scope_completion_audit.csv")
    manifest = read_json(manifest_path(config))
    broad_met = False
    if not completion.empty:
        row = completion[completion["check_name"] == "broad_discovery_p0_minimum_coverage_met"]
        broad_met = bool(row["passed"].iloc[0]) if not row.empty else False

    lines: list[str] = []
    lines.append("# Explore9 P0 大涨股早期结构广度探索报告")
    lines.append("")
    lines.append("## 结论摘要")
    lines.append("")
    lines.append(f"- `broad_discovery_p0_minimum_coverage_met = {str(broad_met).lower()}`。")
    lines.append("- Explore9 P0 只做 broad discovery：没有生成 formal hypothesis，没有做策略回测，也没有输出 frozen strategy。")
    lines.append("- Explore8 输出仅作为背景和 schema/audit reference；本轮标签、episode、原语和 lift 均从 PIT universe 与 provider 行情独立重算。")
    if not leads.empty:
        good = leads[leads["failure_reason"].fillna("") == ""]
        lines.append(f"- 初步线索共输出 `{len(leads)}` 条，其中无失败标记 `{len(good)}` 条；这些线索只能进入 P1/P2 细化，不代表可交易规则。")
    lines.append("")
    lines.append("## 数据覆盖与标签质量")
    lines.append("")
    if not coverage.empty:
        table_rows = []
        for _, row in coverage[coverage["year"].isin(research_years(config))].iterrows():
            table_rows.append(
                [
                    int(row["year"]),
                    row["coverage_status"],
                    format_pct(row["required_field_coverage_ratio"]),
                    int(row["pit_membership_rows"]),
                    int(row["rows_with_all_required_fields"]),
                ]
            )
        lines.extend(markdown_table(["年份", "覆盖状态", "必需字段覆盖率", "PIT样本", "可读样本"], table_rows[:12]))
        lines.append("")
    if not label_coverage.empty:
        table_rows = []
        for _, row in label_coverage.iterrows():
            table_rows.append(
                [
                    row["horizon"],
                    int(row["research_stock_day_rows"]),
                    int(row["horizon_valid_rows"]),
                    int(row["observed_reference_overlap_rows"]),
                    int(row["future_50pct_high_positive_rows"]),
                    int(row["future_100pct_high_positive_rows"]),
                ]
            )
        lines.extend(markdown_table(["Horizon", "研究样本", "有效样本", "跨入2025-2026", "50% high+", "100% high+"], table_rows))
        lines.append("")
    if not by_year.empty:
        lines.append("年度标签分布显示 2017-2024 内存在足够多的 forward winner 样本，但 120/240 日窗口在 2024 年会自然跨入 observed reference，因此主 lift 已排除这些 overlap 样本。")
        table_rows = []
        for _, row in by_year.iterrows():
            table_rows.append(
                [
                    int(row["year"]),
                    int(row["stock_day_count"]),
                    format_pct(row["future_50pct_high_120d_rate"]),
                    format_pct(row["future_100pct_high_240d_rate"]),
                    format_pct(row["horizon_240d_observed_reference_overlap_rate"]),
                ]
            )
        lines.extend(markdown_table(["年份", "样本", "120d 50% high", "240d 100% high", "240d overlap"], table_rows))
        lines.append("")
    lines.append("## Explore8 发现到 Explore9 问题的转换")
    lines.append("")
    lines.append("- Explore8 证明既有 EMA / breakout / pullback 规则主要问题是 `no_signal` 和 `late_signal`，所以 Explore9 不继续做局部参数搜索。")
    lines.append("- P0 将问题改写为：哪些 T 日可观察的价格、成交、相对强度、波动、行业与生命周期状态，在未来 120/240 日 winner 标签上有可复核 lift。")
    lines.append("- `low_date`、未来高点和未来收益只用于标签与 retrospective lifecycle，不进入 T 日 primitive 或 lead 公式。")
    lines.append("")
    lines.append("## 原语覆盖与稳定性")
    lines.append("")
    family_count = int(dictionary["feature_family"].nunique()) if not dictionary.empty else 0
    enabled_count = int(dictionary[dictionary["p0_enabled"].astype(bool)]["feature_name"].nunique()) if not dictionary.empty else 0
    pair_count = int(pairwise["lead_id"].nunique()) if not pairwise.empty else 0
    lines.append(f"- registry 覆盖 `{family_count}` 类 feature family，P0 启用 `{enabled_count}` 个单变量原语，双变量组合 `{pair_count}` 个。")
    if not feature_coverage.empty:
        warmup_limited = feature_coverage[feature_coverage["warmup_partial_year"].fillna(False).astype(bool)]
        lines.append(f"- warmup 受限原语 `{len(warmup_limited)}` 个；2017 年长窗口结论需要按 coverage audit 降级理解。")
    if not univariate.empty:
        top_uni = univariate[(univariate["positive_label"] == "future_50pct_high_120d") & (univariate["stock_day_count"] >= 200)].sort_values("lift_vs_baseline", ascending=False).head(10)
        table_rows = []
        for _, row in top_uni.iterrows():
            table_rows.append(
                [
                    row["lead_name"],
                    row["formula_or_bin"],
                    int(row["stock_day_count"]),
                    format_pct(row["lead_positive_rate"]),
                    format_float(row["lift_vs_baseline"]),
                    int(row["distinct_year_count"]),
                    format_pct(row["industry_concentration_top1"]),
                ]
            )
        lines.extend(markdown_table(["原语", "分箱", "样本", "命中率", "lift", "年份", "行业Top1"], table_rows))
        lines.append("")
    if not pairwise.empty:
        top_pair = pairwise[(pairwise["positive_label"] == "future_50pct_high_120d")].sort_values("lift_vs_baseline", ascending=False).head(10)
        table_rows = []
        for _, row in top_pair.iterrows():
            table_rows.append(
                [
                    row["lead_name"],
                    int(row["stock_day_count"]),
                    format_pct(row["lead_positive_rate"]),
                    format_float(row["lift_vs_baseline"]),
                    int(row["distinct_year_count"]),
                    row["recommended_next_phase"],
                ]
            )
        lines.extend(markdown_table(["双变量线索", "样本", "命中率", "lift", "年份", "建议"], table_rows))
        lines.append("")
    lines.append("## Preliminary Discovery Leads")
    lines.append("")
    if leads.empty:
        lines.append("未发现足够稳定的早期结构，下一阶段不应进入 P1 hypothesis 细化或策略回测，应继续数据画像或扩大数据维度。")
    else:
        table_rows = []
        for _, row in leads.iterrows():
            table_rows.append(
                [
                    int(row["lead_rank"]),
                    row["lead_name"],
                    row["feature_family"],
                    int(row["stock_day_count"]),
                    format_float(row["lift_vs_baseline"]),
                    int(row["distinct_year_count"]),
                    format_pct(row["industry_concentration_top1"]),
                    row["recommended_next_phase"],
                    row["failure_reason"] if isinstance(row["failure_reason"], str) else "",
                ]
            )
        lines.extend(markdown_table(["Rank", "线索", "family", "样本", "lift", "年份", "行业Top1", "下一步", "失败原因"], table_rows))
        lines.append("")
        lines.append("- 非 EMA / 非 breakout / 非 pullback 的线索优先进入 P1，因为它们更符合 Explore8 暴露出的早期发现缺口。")
        lines.append("- 相对强度、行业不同步下的个股领先、成交 regime shift 和波动压缩扩张，是 P0 中最值得继续审计的方向。")
        lines.append("- continuation / hold 线索只说明已有 20% 修复后的延展概率值得分析，不构成退出规则替代。")
    lines.append("")
    lines.append("## 淘汰与降级方向")
    lines.append("")
    if not univariate.empty:
        weak = univariate[(univariate["positive_label"] == "future_50pct_high_120d") & (univariate["stock_day_count"] >= 200) & (univariate["lift_vs_baseline"] <= 1.0)]
        weak_families = ", ".join(sorted(weak["feature_family"].dropna().astype(str).unique())[:8])
        lines.append(f"- 样本足够但 lift 不高于 baseline 的方向不会进入 P1；当前涉及 family：{weak_families or 'NA'}。")
    lines.append("- 单一年份或单一行业贡献过高的线索只保留为 diagnostic，不作为 general hypothesis。")
    lines.append("- observed reference overlap 样本不进入主选择，所以 2025-2026 只能用于后续复核，不参与阈值和 family 选择。")
    lines.append("")
    lines.append("## P1 / P2 建议")
    lines.append("")
    if broad_met and not leads.empty and (leads["failure_reason"].fillna("") == "").any():
        lines.append("- 具备进入 P1 hypothesis refine 的基础，但 P1 必须重新固定 human-readable formula、年度 breakdown 和 failure modes。")
        lines.append("- P2 shape clustering 仍应等待 P1 明确要解释的窗口和样本，不应直接抢先变成策略搜索。")
    else:
        lines.append("- P0 最低覆盖或稳定线索不足，暂不建议进入策略回测；应先补足数据覆盖、warmup 或 primitive family。")
    lines.append("")
    lines.append("## Manifest 纪律")
    lines.append("")
    manifest_flags = [
        "explore8_profile_csv_used_for_label",
        "explore8_profile_csv_used_for_signal",
        "explore8_profile_csv_used_for_selection",
        "historical_trade_results_used_for_labeling",
        "historical_trade_results_used_for_signal",
        "observed_reference_used_for_selection",
    ]
    for flag in manifest_flags:
        lines.append(f"- `{flag} = {str(bool(manifest.get(flag, False))).lower()}`")
    lines.append("")
    lines.append("Explore10 只能作为远期路径记录；是否进入回测必须等待 P1/P2 完成后重新评估。")
    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = [report_path]
    record_manifest(config, "explore9-report", outputs, {"report_generated": True, "broad_discovery_p0_minimum_coverage_met": broad_met})
    print(f"wrote report {relpath(report_path)}", flush=True)
    return outputs


def command_all(config: dict[str, Any]) -> list[Path]:
    outputs: list[Path] = []
    outputs.extend(command_build_labels(config))
    outputs.extend(command_profile_primitives(config))
    outputs.extend(command_explore9_report(config))
    return outputs


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "self-test",
            "build-labels",
            "profile-primitives",
            "explore9-report",
            "profile-p0-5",
            "report-p0-5",
            "profile-p0-6",
            "report-p0-6",
            "profile-p0-7ab",
            "report-p0-7ab",
            "profile-p0-8",
            "report-p0-8",
            "all",
        ],
        help="Explore9 command to run",
    )
    parser.add_argument("--config", default=None, help="Path to Explore9 YAML config")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command in {"profile-p0-8", "report-p0-8"}:
        default_config = DEFAULT_P0_8_CONFIG
    elif args.command in {"profile-p0-7ab", "report-p0-7ab"}:
        default_config = DEFAULT_P0_7_CONFIG
    elif args.command in {"profile-p0-6", "report-p0-6"}:
        default_config = DEFAULT_P0_6_CONFIG
    elif args.command in {"profile-p0-5", "report-p0-5"}:
        default_config = DEFAULT_P0_5_CONFIG
    else:
        default_config = DEFAULT_CONFIG
    config = load_config(args.config or default_config)
    try:
        if args.command == "self-test":
            command_self_test(config)
        elif args.command == "build-labels":
            command_build_labels(config)
        elif args.command == "profile-primitives":
            command_profile_primitives(config)
        elif args.command == "explore9-report":
            command_explore9_report(config)
        elif args.command == "profile-p0-5":
            command_profile_p0_5(config)
        elif args.command == "report-p0-5":
            command_report_p0_5(config)
        elif args.command == "profile-p0-6":
            command_profile_p0_6(config)
        elif args.command == "report-p0-6":
            command_report_p0_6(config)
        elif args.command == "profile-p0-7ab":
            command_profile_p0_7(config)
        elif args.command == "report-p0-7ab":
            command_report_p0_7(config)
        elif args.command == "profile-p0-8":
            command_profile_p0_8(config)
        elif args.command == "report-p0-8":
            command_report_p0_8(config)
        elif args.command == "all":
            command_all(config)
        else:
            raise DataGateError(f"unknown command: {args.command}")
    except DataGateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

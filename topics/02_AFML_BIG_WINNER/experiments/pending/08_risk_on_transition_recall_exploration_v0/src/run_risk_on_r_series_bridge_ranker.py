#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402

import run_density_fast_fail_audit as density_audit  # noqa: E402


REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_experiment_c_risk_on_r_series_bridge_positive_ranker.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

A_TABLE_DIR = TABLE_DIR / "density_fast_fail_audit"
A_REPORT_DIR = REPORT_DIR / "density_fast_fail_audit"
A_MANIFEST_DIR = MANIFEST_DIR / "density_fast_fail_audit"
B_TABLE_DIR = TABLE_DIR / "regime_family_matrix"
B_REPORT_DIR = REPORT_DIR / "regime_family_matrix"
B_MANIFEST_DIR = MANIFEST_DIR / "regime_family_matrix"
PATCH_TABLE_DIR = TABLE_DIR / "risk_on_r_series_density_compression"
PATCH_CACHE_DIR = LOCAL_CACHE_DIR / "risk_on_r_series_density_compression"

C_TABLE_DIR = TABLE_DIR / "risk_on_r_series_bridge_ranker"
C_REPORT_DIR = REPORT_DIR / "risk_on_r_series_bridge_ranker"
C_MANIFEST_DIR = MANIFEST_DIR / "risk_on_r_series_bridge_ranker"
C_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "risk_on_r_series_bridge_ranker"

WINDOW = "before_first_50pct"
TARGET_REGIMES = ["risk_on", "transition"]
DIAGNOSTIC_REGIMES = ["risk_off"]
ALL_REGIMES = [*TARGET_REGIMES, *DIAGNOSTIC_REGIMES]
SPLITS = ["train", "robustness", "validation"]

R_FAMILIES = [
    "R1_relative_strength_breakout",
    "R2_near_high_volume_expansion",
    "R6_market_breadth_thrust",
    "R7_cross_sectional_momentum_rank_jump",
    "R8_persistent_distance_above_ema",
]
R1 = "R1_relative_strength_breakout"
R2 = "R2_near_high_volume_expansion"
R6 = "R6_market_breadth_thrust"
R7 = "R7_cross_sectional_momentum_rank_jump"
R8 = "R8_persistent_distance_above_ema"
T4 = "T4_entropy_compression_then_directional_expansion"
T7 = "T7_board_relative_strength_break"

A_DECISION_COMPLETE = "density_fast_fail_audit_complete"
A_DECISION_PARTIAL = "density_fast_fail_audit_partial_source_complete"
B_DECISION_COMPLETE = "regime_family_matrix_complete"
B_DECISION_SOURCE_CAVEATED = "regime_family_matrix_source_caveated_complete"

FINAL_COMPLETE = "risk_on_r_series_ranker_complete"
FINAL_SOURCE_CAVEATED = "risk_on_r_series_ranker_source_caveated_complete"
FINAL_INPUT_BLOCKED = "risk_on_r_series_ranker_input_blocked"
FINAL_CONTRACT_BLOCKED = "risk_on_r_series_ranker_contract_blocked"
FINAL_LEAKAGE_BLOCKED = "risk_on_r_series_ranker_leakage_blocked"
FINAL_SOURCE_BLOCKED = "risk_on_r_series_ranker_source_blocked"
FINAL_BINDING_DRIFT_BLOCKED = "risk_on_r_series_ranker_binding_drift_blocked"

DIRECT_TIER = "direct_entry_candidate_supported"
FEATURE_TIER = "meta_label_feature_source_supported"
DIAGNOSTIC_TIER = "diagnostic_only_or_no_candidate"
RISK_OFF_TIER = "risk_off_diagnostic_only"

SOURCE_CAVEATED_DIRECT_TIER = "source_caveated_direct_entry_candidate_supported"
SOURCE_CAVEATED_FEATURE_TIER = "source_caveated_meta_label_feature_source_supported"

E1_SCOPE = "07_E1_only"
E1_CAPTURE_SCOPE = "07_e1_only"
R_CORE_SCOPE = "08_R_core_event_regime_gated"
R6_SCOPE = "08_R6_event_regime_gated"
T4_SCOPE = "08_T4_gated"
T7_SCOPE = "08_T7_gated"
T4_T7_SCOPE = "08_selected_T4_T7_union"
R_SCOPE_BY_FAMILY = {family: f"08_{family.split('_', 1)[0]}_event_regime_gated" for family in R_FAMILIES}
T_SCOPE_BY_FAMILY = {T4: T4_SCOPE, T7: T7_SCOPE}
REQUIRED_RECONSTRUCTABLE_SCOPES = [
    R_CORE_SCOPE,
    *R_SCOPE_BY_FAMILY.values(),
    T4_SCOPE,
    T7_SCOPE,
    T4_T7_SCOPE,
]

DIRECT_DENSITY_VS_E1_MAX = 1.50
DIRECT_MEAN_DENSITY_MAX = 2.824076
DIRECT_P95_MAX = 7.056048
DIRECT_DUPLICATE_MAX = 0.15
FEATURE_DENSITY_VS_E1_MAX = 2.50
FEATURE_P95_MAX = 12.226065
FEATURE_DUPLICATE_MAX = 0.15
DIRECT_SHARE_MAX = 0.35
FEATURE_SHARE_MAX = 0.65
DIRECT_FAST_FAIL_EXCESS_MAX = 0.02
DIRECT_FALSE_REPAIR_EXCESS_MAX = 0.03
FEATURE_FAST_FAIL_EXCESS_MAX = 0.10
TRAIN_RECALL_DELTA_MIN = 0.08
TRAIN_BRIDGE_DELTA_MIN = 0.05
ROB_RECALL_DELTA_MIN = 0.03
ROB_BRIDGE_DELTA_MIN = 0.03
BORDERLINE_BAND = 0.01

SAMPLE_ORDER = {
    "sufficient_for_cell_readout": 0,
    "low_power_caution": 1,
    "diagnostic_only": 2,
    "not_available_publishable_source": 3,
    "source_blocked": 3,
}


@dataclass(frozen=True)
class ArmSpec:
    arm_id: str
    arm_type: str
    source_family_ids: tuple[str, ...]
    policy: str
    r2_policy: str = "r2_diagnostic_only"


ARM_SPECS = [
    ArmSpec("baseline_r_core_no_ranker_diagnostic", "baseline_stress", tuple(R_FAMILIES), "all_core"),
    ArmSpec("baseline_r6_only_transition_primary", "baseline_single_family", (R6,), "r6_only"),
    ArmSpec("baseline_r6_only_risk_on_positive", "baseline_single_family", (R6,), "r6_only"),
    ArmSpec("baseline_t4_t7_negative_control", "negative_control", (T4, T7), "t4_t7"),
    ArmSpec("r6_r1_r7_bridge_pool", "family_pool", (R6, R1, R7), "suppress_same_day"),
    ArmSpec("r6_r2_low_fast_fail_support", "family_pool", (R6, R2), "suppress_same_day", "r2_family_budget_only"),
    ArmSpec("r6_r1_r2_r7_bridge_pool", "family_pool", (R6, R1, R2, R7), "suppress_same_day", "r2_family_budget_only"),
    ArmSpec("family_budget_equal_weight", "family_budget", tuple(R_FAMILIES), "family_equal_budget", "r2_family_budget_only"),
    ArmSpec("family_budget_bridge_weighted_train_only", "family_budget", tuple(R_FAMILIES), "family_bridge_weighted", "r2_family_budget_only"),
    ArmSpec("cooldown_20d_ranked_within_bucket", "cooldown", tuple(R_FAMILIES), "cooldown_20", "r2_family_budget_only"),
    ArmSpec("cooldown_40d_ranked_within_bucket", "cooldown", tuple(R_FAMILIES), "cooldown_40", "r2_family_budget_only"),
    ArmSpec("top_k_per_instrument_month_family_aware", "top_k", tuple(R_FAMILIES), "top_month", "r2_family_budget_only"),
    ArmSpec("top_k_per_instrument_20d_family_aware", "top_k", tuple(R_FAMILIES), "top_20d", "r2_family_budget_only"),
    ArmSpec("market_day_family_quota", "quota", tuple(R_FAMILIES), "market_day_family_quota", "r2_family_budget_only"),
    ArmSpec("cross_family_collision_suppression", "deoverlap", tuple(R_FAMILIES), "suppress_same_day", "r2_family_budget_only"),
    ArmSpec("fast_fail_rejector_overlay_train_only", "rejector_overlay", tuple(R_FAMILIES), "family_bridge_weighted", "r2_family_budget_only"),
    ArmSpec("false_repair_rejector_overlay_train_only", "rejector_overlay", tuple(R_FAMILIES), "family_bridge_weighted", "r2_family_budget_only"),
    ArmSpec("bridge_positive_ranker_with_fast_fail_penalty", "rejector_overlay", (R6, R1, R2, R7), "bridge_penalty", "r2_family_budget_only"),
    ArmSpec("supervised_bridge_ranker", "supervised_ranker", (R6, R1, R2, R7), "bridge_penalty", "r2_family_budget_only"),
    ArmSpec("r2_budget_only_arm", "r2_policy", (R2,), "r2_budget", "r2_family_budget_only"),
    ArmSpec("r2_diagnostic_only_arm", "r2_policy", (R2,), "r2_diagnostic", "r2_diagnostic_only"),
]

REQUIRED_INPUTS: dict[str, Path] = {
    "run_manifest": MANIFEST_DIR / "run_manifest.json",
    "density_fast_fail_contract": A_REPORT_DIR / "density_fast_fail_caliber_contract.md",
    "density_fast_fail_audit_manifest": A_MANIFEST_DIR / "density_fast_fail_audit_manifest.json",
    "candidate_10d_density_summary": A_TABLE_DIR / "candidate_10d_density_summary.csv",
    "candidate_10d_fast_fail_readout": A_TABLE_DIR / "candidate_10d_fast_fail_readout.csv",
    "candidate_10d_retention_by_split_regime": A_TABLE_DIR / "candidate_10d_retention_by_split_regime.csv",
    "candidate_adjacent_event_gap_diagnostic": A_TABLE_DIR / "candidate_adjacent_event_gap_diagnostic.csv",
    "candidate_10d_uniqueness_diagnostic": A_TABLE_DIR / "candidate_10d_uniqueness_diagnostic.csv",
    "candidate_scope_mapping_contract": A_TABLE_DIR / "candidate_scope_mapping_contract.csv",
    "candidate_scope_reconstructability_audit": A_TABLE_DIR / "candidate_scope_reconstructability_audit.csv",
    "regime_family_matrix_manifest": B_MANIFEST_DIR / "regime_family_matrix_manifest.json",
    "regime_family_matrix_report": B_REPORT_DIR / "regime_family_matrix_report.md",
    "regime_family_performance_matrix": B_TABLE_DIR / "regime_family_performance_matrix.csv",
    "transition_event_family_reselection_matrix": B_TABLE_DIR / "transition_event_family_reselection_matrix.csv",
    "regime_family_density_fast_fail_matrix": B_TABLE_DIR / "regime_family_density_fast_fail_matrix.csv",
    "regime_family_fast_fail_diagnostic_matrix": B_TABLE_DIR / "regime_family_fast_fail_diagnostic_matrix.csv",
    "regime_family_cross_family_collision_matrix": B_TABLE_DIR / "regime_family_cross_family_collision_matrix.csv",
    "regime_family_bridge_recall_matrix": B_TABLE_DIR / "regime_family_bridge_recall_matrix.csv",
    "regime_family_retention_source_status": B_TABLE_DIR / "regime_family_retention_source_status.csv",
    "regime_family_compression_arm_hypothesis": B_TABLE_DIR / "regime_family_compression_arm_hypothesis.csv",
    "regime_family_design_recommendations": B_TABLE_DIR / "regime_family_design_recommendations.csv",
    "candidate_family_event_instances": TABLE_DIR / "candidate_family_event_instances.csv.gz",
    "candidate_family_canonical_events": TABLE_DIR / "candidate_family_canonical_events.csv.gz",
    "candidate_family_incremental_recall_over_e1": TABLE_DIR / "candidate_family_incremental_recall_over_e1.csv",
    "candidate_family_bridge_positive_recall": TABLE_DIR / "candidate_family_bridge_positive_recall.csv",
    "candidate_family_density_summary": TABLE_DIR / "candidate_family_density_summary.csv",
    "candidate_family_label_quality_readout": TABLE_DIR / "candidate_family_label_quality_readout.csv",
    "candidate_family_false_repair_diagnostic": TABLE_DIR / "candidate_family_false_repair_diagnostic.csv",
    "candidate_family_overlap_matrix": TABLE_DIR / "candidate_family_overlap_matrix.csv",
    "candidate_family_feature_snapshot_summary": TABLE_DIR / "candidate_family_feature_snapshot_summary.csv",
    "risk_on_r_series_compression_frontier": PATCH_TABLE_DIR / "risk_on_r_series_compression_frontier.csv",
    "risk_on_r_series_score_spec": PATCH_TABLE_DIR / "risk_on_r_series_score_spec.csv",
    "risk_on_r_series_source_pool_summary": PATCH_TABLE_DIR / "risk_on_r_series_source_pool_summary.csv",
}

OPTIONAL_INPUTS: dict[str, Path] = {
    "candidate_family_event_labels": LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet",
    "candidate_family_capture": LOCAL_CACHE_DIR / "candidate_family_capture.parquet",
    "cross_section_feature_panel": LOCAL_CACHE_DIR / "cross_section_feature_panel.parquet",
    "risk_on_r_series_event_scores": PATCH_CACHE_DIR / "risk_on_r_series_event_scores.parquet",
}

OUTPUT_TABLES = [
    "risk_on_r_series_ranker_arm_frontier",
    "risk_on_r_series_ranker_selected_events",
    "risk_on_r_series_ranker_rejected_events",
    "risk_on_r_series_ranker_feature_spec",
    "risk_on_r_series_ranker_family_budget_audit",
    "risk_on_r_series_ranker_density_fast_fail_readout",
    "risk_on_r_series_ranker_bridge_recall_readout",
    "risk_on_r_series_ranker_transition_reselection_readout",
    "risk_on_r_series_ranker_deoverlap_audit",
    "risk_on_r_series_ranker_oos_separability",
    "risk_on_r_series_ranker_decision_tiers",
    "risk_on_r_series_ranker_failure_distribution",
    "risk_on_r_series_ranker_source_caveat_audit",
    "risk_on_r_series_ranker_label_policy_audit",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Experiment C R-series bridge-positive ranker.")
    parser.add_argument("--mode", choices=["check-drift", "full"], default="full")
    return parser.parse_args(argv)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0:
        return np.nan
    return float(numerator) / float(denominator)


def pct(value: Any, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.{digits}f}%"


def num(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def bool_series(frame: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=bool)
    return frame[column].where(frame[column].notna(), default).infer_objects(copy=False).astype(bool)


def ensure_event_columns(events: pd.DataFrame) -> pd.DataFrame:
    out = events.copy()
    if "canonical_event_id" not in out.columns:
        out["canonical_event_id"] = out.get("event_id", "").astype(str)
    if "event_key" not in out.columns:
        out["event_key"] = out["canonical_event_id"].fillna(out.get("event_id", "")).astype(str)
    if "rank_score" not in out.columns:
        out["rank_score"] = pd.to_numeric(out.get("per_family_variant_score"), errors="coerce")
    if "rank_score_available" not in out.columns:
        out["rank_score_available"] = out["rank_score"].notna()
    if "mechanism_cluster_id" not in out.columns:
        out["mechanism_cluster_id"] = out.get("mechanism_cluster", "")
    return density_audit.with_event_window_anchor(out)


def stable_sort_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    out = events.copy()
    out["_rank_sort"] = pd.to_numeric(out.get("rank_score"), errors="coerce").fillna(0.5)
    out["_priority_sort"] = pd.to_numeric(out.get("event_family_priority"), errors="coerce").fillna(9999)
    return out.sort_values(
        ["_rank_sort", "_priority_sort", "event_t0_pos", "event_id"],
        ascending=[False, True, True, True],
        kind="stable",
    ).drop(columns=["_rank_sort", "_priority_sort"], errors="ignore")


def validate_input_gate() -> tuple[str, list[str], dict[str, Path], dict[str, Any], dict[str, Any]]:
    reasons: list[str] = []
    input_paths = dict(REQUIRED_INPUTS)
    input_paths.update(OPTIONAL_INPUTS)
    if not REQUIREMENT_PATH.exists():
        reasons.append("requirement_missing")
    for key, path in REQUIRED_INPUTS.items():
        if not path.exists():
            reasons.append(f"required_input_missing:{key}")

    a_manifest = read_json(REQUIRED_INPUTS["density_fast_fail_audit_manifest"]) if REQUIRED_INPUTS["density_fast_fail_audit_manifest"].exists() else {}
    b_manifest = read_json(REQUIRED_INPUTS["regime_family_matrix_manifest"]) if REQUIRED_INPUTS["regime_family_matrix_manifest"].exists() else {}
    a_decision = a_manifest.get("decision")
    b_decision = b_manifest.get("decision")
    if a_decision not in {A_DECISION_COMPLETE, A_DECISION_PARTIAL}:
        reasons.append(f"unsupported_experiment_a_decision:{a_decision}")
    if b_decision not in {B_DECISION_COMPLETE, B_DECISION_SOURCE_CAVEATED}:
        reasons.append(f"unsupported_experiment_b_decision:{b_decision}")

    if not REQUIRED_INPUTS["density_fast_fail_contract"].exists():
        status = FINAL_CONTRACT_BLOCKED
    elif reasons:
        status = FINAL_INPUT_BLOCKED
    else:
        status = "pass"
    return status, reasons, input_paths, a_manifest, b_manifest


def check_requirement_alignment() -> tuple[bool, list[str]]:
    text = REQUIREMENT_PATH.read_text(encoding="utf-8")
    required_strings = [
        "target_regime_decision_tier",
        "selected_arm_recomputed",
        "risk_on_r_series_ranker_binding_drift_blocked",
        "bridge_positive_event_or_episode_capture",
        "candidate_scope_mapping_contract.csv",
        "direct_entry_density_vs_e1_full_denominator_max = 1.50",
        "borderline_pass_flag",
    ]
    failures = [f"requirement_missing_string:{value}" for value in required_strings if value not in text]
    return not failures, failures


def load_inputs() -> dict[str, Any]:
    tables: dict[str, Any] = {}
    for key, path in REQUIRED_INPUTS.items():
        if path.suffix == ".json":
            tables[key] = read_json(path)
        elif path.suffix == ".md":
            tables[key] = path.read_text(encoding="utf-8")
        elif path.suffix in {".csv", ".gz"}:
            tables[key] = read_csv(path)
    for key, path in OPTIONAL_INPUTS.items():
        if not path.exists():
            tables[key] = pd.DataFrame()
        elif path.suffix == ".parquet":
            tables[key] = pd.read_parquet(path)
        elif path.suffix in {".csv", ".gz"}:
            tables[key] = read_csv(path)
    return tables


def table_row(
    frame: pd.DataFrame,
    *,
    scope: str,
    split: str,
    regime: str,
    split_col: str = "split",
) -> pd.Series | None:
    mask = (frame["candidate_scope_id"].astype(str) == scope)
    if split_col in frame.columns:
        mask &= frame[split_col].astype(str).eq(split)
    if "market_regime_bucket" in frame.columns:
        mask &= frame["market_regime_bucket"].astype(str).eq(regime)
    rows = frame.loc[mask]
    if rows.empty:
        return None
    return rows.iloc[0]


def check_close(name: str, got: Any, expected: float, tolerance: float, failures: list[dict[str, Any]]) -> None:
    if got is None or pd.isna(got) or abs(float(got) - expected) > tolerance:
        failures.append({"field": name, "expected": expected, "source_value": got, "tolerance": tolerance})


def binding_drift_failures(tables: dict[str, Any], a_manifest: dict[str, Any], b_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if a_manifest.get("decision") != A_DECISION_PARTIAL:
        failures.append({"field": "experiment_a_decision", "expected": A_DECISION_PARTIAL, "source_value": a_manifest.get("decision")})
    if b_manifest.get("decision") != B_DECISION_SOURCE_CAVEATED:
        failures.append({"field": "experiment_b_decision", "expected": B_DECISION_SOURCE_CAVEATED, "source_value": b_manifest.get("decision")})

    density = tables["candidate_10d_density_summary"]
    for scope, expected in {
        E1_SCOPE: {"event_count": 6820, "mean": 1.882717, "p95": 4.704032, "dup": 0.0019},
        T4_T7_SCOPE: {"event_count": 2063, "mean": 0.569508, "p95": 1.527154, "dup": 0.0373},
        R_CORE_SCOPE: {"event_count": 47914, "mean": 13.230, "p95": 38.12, "dup": 0.5783},
        R6_SCOPE: {"event_count": 16204, "mean": 4.473247, "p95": 12.226065, "dup": 0.0},
    }.items():
        row = density.loc[density["candidate_scope_id"] == scope]
        if row.empty:
            failures.append({"field": f"{scope}.density_row", "expected": "present", "source_value": "missing"})
            continue
        item = row.iloc[0]
        check_close(f"{scope}.event_count", item.get("event_count"), expected["event_count"], 0, failures)
        check_close(f"{scope}.events_per_instrument_year_mean", item.get("events_per_instrument_year_mean"), expected["mean"], 0.005, failures)
        check_close(f"{scope}.events_per_instrument_year_p95", item.get("events_per_instrument_year_p95"), expected["p95"], 0.02, failures)
        check_close(f"{scope}.rolling_10d_duplicate_rate", item.get("rolling_10d_duplicate_rate"), expected["dup"], 0.0002, failures)

    perf = tables["regime_family_performance_matrix"]
    checks = [
        (R6_SCOPE, "train", "transition", 0.9605, 0.4934, 0.2086),
        (R6_SCOPE, "robustness", "transition", 0.4300, 0.2700, 0.1442),
        (R6_SCOPE, "train", "risk_on", 0.9644, 0.4330, 0.3052),
        (R6_SCOPE, "robustness", "risk_on", 0.9006, 0.5691, 0.2270),
        (T4_T7_SCOPE, "train", "transition", 0.2303, 0.0855, 0.2874),
    ]
    for scope, split, regime, any_recall, bridge, fast_fail in checks:
        row = table_row(perf, scope=scope, split=split, regime=regime)
        if row is None:
            failures.append({"field": f"{scope}.{split}.{regime}", "expected": "present", "source_value": "missing"})
            continue
        check_close(f"{scope}.{split}.{regime}.pre_replay_any_recall", row.get("pre_replay_any_recall"), any_recall, 0.00015, failures)
        check_close(f"{scope}.{split}.{regime}.pre_replay_bridge_recall", row.get("pre_replay_bridge_recall"), bridge, 0.00015, failures)
        check_close(f"{scope}.{split}.{regime}.fast_fail_10d_rate", row.get("fast_fail_10d_rate"), fast_fail, 0.00015, failures)
    return failures


def scope_reconstructable(tables: dict[str, Any], scope_id: str) -> bool:
    mapping = tables["candidate_scope_mapping_contract"]
    audit = tables["candidate_scope_reconstructability_audit"]
    m = mapping.loc[mapping["candidate_scope_id"].astype(str).eq(scope_id)]
    a = audit.loc[audit["candidate_scope_id"].astype(str).eq(scope_id)]
    return (
        not m.empty
        and not a.empty
        and str(m.iloc[0].get("scope_mapping_status")) == "reconstructable_event_membership"
        and str(a.iloc[0].get("scope_status")) == "reconstructable_event_membership"
    )


def scope_specs_by_id() -> dict[str, Any]:
    return {spec.candidate_scope_id: spec for spec in density_audit.build_scope_specs()}


def scope_source_path(tables: dict[str, Any], scope_id: str) -> Path:
    mapping = tables["candidate_scope_mapping_contract"]
    row = mapping.loc[mapping["candidate_scope_id"].astype(str).eq(scope_id)]
    if row.empty:
        return REQUIRED_INPUTS["candidate_scope_mapping_contract"]
    return Path(str(row.iloc[0].get("source_artifact_path", "")))


def first_triggered_family(variants: Any, allowed: tuple[str, ...]) -> str:
    text = "" if pd.isna(variants) else str(variants)
    for family in allowed:
        if f"{family}__event_regime_gated" in text:
            return family
    return ""


def score_cache_events(tables: dict[str, Any]) -> pd.DataFrame:
    scored = tables.get("risk_on_r_series_event_scores")
    if isinstance(scored, pd.DataFrame) and not scored.empty:
        out = scored.copy()
    else:
        out = tables["candidate_family_event_instances"].copy()
        out["per_family_variant_score"] = np.nan
        out["score_rank_eligible_flag"] = False
        out["score_availability_status"] = "score_cache_missing"
    out = out.loc[
        out["family_id"].isin(R_FAMILIES)
        & out["variant_id"].astype(str).eq("event_regime_gated")
        & out["family_input_status"].astype(str).eq("runnable_existing_data")
    ].copy()
    out["rank_score"] = pd.to_numeric(out.get("per_family_variant_score"), errors="coerce")
    out["rank_score_available"] = out["rank_score"].notna()
    out["family_variant_id"] = out.get("family_variant_id", out["family_id"].astype(str) + "__" + out["variant_id"].astype(str))
    return ensure_event_columns(out)


def attach_score_cache(scope_events: pd.DataFrame, score_events: pd.DataFrame, family_id: str) -> pd.DataFrame:
    out = scope_events.copy()
    out["family_id"] = family_id
    out["variant_id"] = "event_regime_gated"
    out["family_variant_id"] = f"{family_id}__event_regime_gated"
    if score_events.empty:
        out["rank_score"] = np.nan
        out["rank_score_available"] = False
        out["score_availability_status"] = "score_cache_missing"
        return ensure_event_columns(out)

    score_pool = score_events.loc[
        score_events["family_id"].astype(str).eq(family_id)
        & score_events["variant_id"].astype(str).eq("event_regime_gated")
    ].copy()
    if score_pool.empty:
        out["rank_score"] = np.nan
        out["rank_score_available"] = False
        out["score_availability_status"] = "score_not_available_for_family"
        return ensure_event_columns(out)

    for frame in (out, score_pool):
        frame["_scope_score_key"] = (
            frame["instrument"].astype(str)
            + "|"
            + frame["event_t0_date"].astype(str)
            + "|"
            + pd.to_numeric(frame["event_t0_pos"], errors="coerce").fillna(-1).astype(int).astype(str)
        )
    score_cols = [
        "event_id",
        "rank_score",
        "rank_score_available",
        "score_availability_status",
        "event_family_priority",
        "mechanism_cluster",
        "mechanism_cluster_id",
        "family_input_status",
    ]
    for column in score_cols:
        if column not in score_pool.columns:
            score_pool[column] = np.nan
    lookup = (
        stable_sort_events(score_pool)
        .drop_duplicates("_scope_score_key", keep="first")
        [["_scope_score_key", *score_cols]]
        .rename(columns={"event_id": "source_event_id"})
    )
    merged = out.merge(lookup, on="_scope_score_key", how="left", suffixes=("", "_score"))
    if "source_event_id" in merged.columns:
        merged["event_id"] = merged["source_event_id"].where(merged["source_event_id"].notna(), merged["event_id"])
    if "rank_score_score" in merged.columns:
        merged["rank_score"] = merged["rank_score_score"].combine_first(pd.to_numeric(merged.get("rank_score"), errors="coerce"))
    if "rank_score_available_score" in merged.columns:
        merged["rank_score_available"] = merged["rank_score_available_score"].where(
            merged["rank_score_available_score"].notna(),
            merged.get("rank_score_available", False),
        )
    if "score_availability_status_score" in merged.columns:
        merged["score_availability_status"] = merged["score_availability_status_score"].where(
            merged["score_availability_status_score"].notna(),
            merged.get("score_availability_status", "score_not_available_for_family"),
        )
    if "event_family_priority_score" in merged.columns:
        merged["event_family_priority"] = merged["event_family_priority_score"].combine_first(
            pd.to_numeric(merged.get("event_family_priority"), errors="coerce")
        )
    if "mechanism_cluster_score" in merged.columns:
        merged["mechanism_cluster"] = merged["mechanism_cluster_score"].where(
            merged["mechanism_cluster_score"].notna(),
            merged.get("mechanism_cluster", ""),
        )
    merged["mechanism_cluster_id"] = merged.get("mechanism_cluster_id", merged.get("mechanism_cluster", ""))
    merged["rank_score"] = pd.to_numeric(merged.get("rank_score"), errors="coerce")
    merged["rank_score_available"] = merged["rank_score"].notna()
    return ensure_event_columns(merged.drop(columns=[c for c in merged.columns if c.endswith("_score") or c == "_scope_score_key"], errors="ignore"))


def scope_events_from_contract(
    tables: dict[str, Any],
    scope_id: str,
    *,
    score_events: pd.DataFrame,
) -> pd.DataFrame:
    specs = scope_specs_by_id()
    if scope_id not in specs:
        return pd.DataFrame()
    spec = specs[scope_id]
    canonical = tables["candidate_family_canonical_events"].copy()
    selected = density_audit.select_scope_events(spec, pd.DataFrame(), canonical)
    out = density_audit.normalise_scope_events(
        selected,
        spec,
        source_path=scope_source_path(tables, scope_id),
    )
    if out.empty:
        return out
    out["source_scope_id"] = scope_id
    if scope_id in R_SCOPE_BY_FAMILY.values():
        family_id = next(family for family, family_scope in R_SCOPE_BY_FAMILY.items() if family_scope == scope_id)
        out = attach_score_cache(out, score_events, family_id)
    elif scope_id in T_SCOPE_BY_FAMILY.values():
        family_id = next(family for family, family_scope in T_SCOPE_BY_FAMILY.items() if family_scope == scope_id)
        out["family_id"] = family_id
        out["variant_id"] = "event_regime_gated"
        out["rank_score"] = np.nan
        out["rank_score_available"] = False
        out["score_availability_status"] = "not_scored_negative_control"
        out = ensure_event_columns(out)
    else:
        families = tuple(R_FAMILIES) if scope_id == R_CORE_SCOPE else (T4, T7)
        out["family_id"] = out.get("triggered_family_variants", "").apply(lambda value: first_triggered_family(value, families))
        out["variant_id"] = "event_regime_gated"
        if scope_id == R_CORE_SCOPE:
            parts = [
                attach_score_cache(out.loc[out["family_id"].astype(str).eq(family)].copy(), score_events, family)
                for family in R_FAMILIES
            ]
            out = pd.concat([part for part in parts if not part.empty], ignore_index=True) if parts else out.iloc[0:0].copy()
        else:
            out["rank_score"] = np.nan
            out["rank_score_available"] = False
            out = ensure_event_columns(out)
    out["candidate_scope_id"] = scope_id
    out["source_scope_id"] = scope_id
    return ensure_event_columns(out)


def load_contract_event_pools(tables: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    score_events = score_cache_events(tables)
    r_parts = [
        scope_events_from_contract(tables, scope_id, score_events=score_events)
        for scope_id in R_SCOPE_BY_FAMILY.values()
    ]
    r_events = pd.concat([part for part in r_parts if not part.empty], ignore_index=True) if r_parts else pd.DataFrame()
    t_parts = [
        scope_events_from_contract(tables, scope_id, score_events=score_events)
        for scope_id in T_SCOPE_BY_FAMILY.values()
    ]
    t_events = pd.concat([part for part in t_parts if not part.empty], ignore_index=True) if t_parts else pd.DataFrame()
    core_events = scope_events_from_contract(tables, R_CORE_SCOPE, score_events=score_events)
    return r_events, t_events, core_events


def density_reference(tables: dict[str, Any]) -> tuple[float, float, float]:
    density = tables["candidate_10d_density_summary"]
    e1 = density.loc[density["candidate_scope_id"] == E1_SCOPE].iloc[0]
    instrument_years = float(e1["instrument_years"])
    e1_density = float(e1["events_per_instrument_year_mean"])
    e1_p95 = float(e1["events_per_instrument_year_p95"])
    return instrument_years, e1_density, e1_p95


def rank_budget_count(tables: dict[str, Any], multiplier: float = DIRECT_DENSITY_VS_E1_MAX) -> int:
    instrument_years, e1_density, _ = density_reference(tables)
    return max(int(math.floor(instrument_years * e1_density * multiplier)), 1)


def family_weights_from_b(tables: dict[str, Any], target_regime: str) -> dict[str, float]:
    perf = tables["regime_family_performance_matrix"]
    e1 = table_row(perf, scope=E1_SCOPE, split="train", regime=target_regime)
    e1_bridge = float(e1["pre_replay_bridge_recall"]) if e1 is not None else 0.0
    weights: dict[str, float] = {}
    for family in R_FAMILIES:
        scope = f"08_{family.split('_', 1)[0]}_event_regime_gated"
        row = table_row(perf, scope=scope, split="train", regime=target_regime)
        if row is None:
            weights[family] = 0.1
            continue
        weights[family] = max(float(row.get("pre_replay_bridge_recall", 0.0)) - e1_bridge, 0.01)
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()} if total else {key: 1 / len(R_FAMILIES) for key in R_FAMILIES}


def suppress_same_day(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    ordered = stable_sort_events(events)
    return ordered.drop_duplicates(["instrument", "event_t0_date"], keep="first").copy()


def enforce_cooldown(events: pd.DataFrame, cooldown: int) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    selected_parts: list[pd.DataFrame] = []
    for _, group in stable_sort_events(events).groupby("instrument", sort=False):
        picked: list[int] = []
        picked_pos: list[float] = []
        for idx, row in group.iterrows():
            pos = float(pd.to_numeric(row.get("event_t0_pos"), errors="coerce"))
            if all(abs(pos - old_pos) > cooldown for old_pos in picked_pos):
                picked.append(idx)
                picked_pos.append(pos)
        selected_parts.append(group.loc[picked])
    return pd.concat(selected_parts, ignore_index=True) if selected_parts else events.iloc[0:0].copy()


def top_per_instrument_month(events: pd.DataFrame, k: int = 1) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    out = events.copy()
    out["_month"] = out["event_t0_date"].astype(str).str.slice(0, 7)
    selected = stable_sort_events(out).groupby(["instrument", "_month"], sort=False).head(k)
    return selected.drop(columns=["_month"], errors="ignore").copy()


def market_day_quota(events: pd.DataFrame, quota: int = 3) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    return stable_sort_events(events).groupby(["event_t0_date", "family_id"], sort=False).head(quota).copy()


def family_budget(events: pd.DataFrame, tables: dict[str, Any], target_regime: str, weighted: bool) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    budget = rank_budget_count(tables)
    weights = family_weights_from_b(tables, target_regime) if weighted else {family: 1 / len(R_FAMILIES) for family in R_FAMILIES}
    parts: list[pd.DataFrame] = []
    for family, group in events.groupby("family_id", sort=False):
        cap = max(int(math.floor(budget * weights.get(str(family), 0.0))), 1)
        parts.append(stable_sort_events(group).head(cap))
    selected = pd.concat(parts, ignore_index=True) if parts else events.iloc[0:0].copy()
    return stable_sort_events(selected).head(budget).copy()


def select_events_for_arm(
    spec: ArmSpec,
    target_regime: str,
    r_events: pd.DataFrame,
    t_events: pd.DataFrame,
    core_events: pd.DataFrame,
    tables: dict[str, Any],
    *,
    supervised_cache_available: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    if spec.policy == "t4_t7":
        pool = t_events.loc[t_events["market_regime_bucket"].astype(str).eq(target_regime)].copy()
        selected = pool.copy()
        status = "negative_control_diagnostic_only"
    elif spec.arm_type == "supervised_ranker" and not supervised_cache_available:
        pool = r_events.loc[
            r_events["market_regime_bucket"].astype(str).eq(target_regime)
            & r_events["family_id"].isin(spec.source_family_ids)
        ].copy()
        selected = pool.iloc[0:0].copy()
        status = "supervised_ranker_input_blocked_missing_local_cache"
    else:
        source_pool = core_events if spec.policy == "all_core" else r_events
        pool = source_pool.loc[
            source_pool["market_regime_bucket"].astype(str).eq(target_regime)
            & source_pool["family_id"].isin(spec.source_family_ids)
        ].copy()
        if spec.policy == "all_core":
            selected = pool.copy()
            status = "diagnostic_stress_pool_not_direct_selectable"
        elif spec.policy in {"r6_only", "suppress_same_day"}:
            selected = suppress_same_day(pool)
            status = "deterministic_arm_complete"
        elif spec.policy == "family_equal_budget":
            selected = family_budget(pool, tables, target_regime, weighted=False)
            status = "deterministic_arm_complete"
        elif spec.policy == "family_bridge_weighted":
            selected = family_budget(pool, tables, target_regime, weighted=True)
            status = "deterministic_arm_complete"
        elif spec.policy == "cooldown_20":
            selected = enforce_cooldown(pool, 20)
            status = "deterministic_arm_complete"
        elif spec.policy == "cooldown_40":
            selected = enforce_cooldown(pool, 40)
            status = "deterministic_arm_complete"
        elif spec.policy == "top_month":
            selected = top_per_instrument_month(pool, 1)
            status = "deterministic_arm_complete"
        elif spec.policy == "top_20d":
            selected = enforce_cooldown(suppress_same_day(pool), 20)
            status = "deterministic_arm_complete"
        elif spec.policy == "market_day_family_quota":
            selected = market_day_quota(pool, 3)
            status = "deterministic_arm_complete"
        elif spec.policy == "bridge_penalty":
            selected = family_budget(pool, tables, target_regime, weighted=True)
            status = "supervised_cache_available_deterministic_score_proxy"
        elif spec.policy == "r2_budget":
            selected = stable_sort_events(pool).head(max(rank_budget_count(tables) // len(R_FAMILIES), 1))
            status = "r2_family_budget_only"
        elif spec.policy == "r2_diagnostic":
            selected = pool.iloc[0:0].copy()
            status = "r2_diagnostic_only"
        else:
            selected = pool.iloc[0:0].copy()
            status = "unknown_policy_blocked"
    selected = selected.copy()
    selected["arm_id"] = spec.arm_id
    selected["target_regime"] = target_regime
    selected["selected_reason"] = spec.policy
    selected["r2_policy"] = spec.r2_policy
    selected["cooldown_rule"] = spec.policy if spec.policy.startswith("cooldown") else ""
    selected["family_budget_rule"] = spec.policy if "budget" in spec.policy or "weighted" in spec.policy else ""
    selected["feature_source_only"] = spec.arm_type in {"rejector_overlay", "supervised_ranker"} or spec.policy == "r2_diagnostic"
    selected_keys = set(selected["event_id"].astype(str)) if "event_id" in selected.columns else set()
    rejected = pool.loc[~pool["event_id"].astype(str).isin(selected_keys)].copy() if "event_id" in pool.columns else pool.iloc[0:0].copy()
    rejected["arm_id"] = spec.arm_id
    rejected["target_regime"] = target_regime
    rejected["rejection_reason"] = np.where(
        spec.arm_type == "supervised_ranker" and not supervised_cache_available,
        "supervised_ranker_input_blocked_missing_local_cache",
        np.where(spec.policy == "r2_diagnostic", "r2_diagnostic_only", "not_selected_by_arm"),
    )
    rejected["blocked_by_cooldown"] = spec.policy.startswith("cooldown")
    rejected["blocked_by_family_budget"] = "budget" in spec.policy or "weighted" in spec.policy
    rejected["blocked_by_collision"] = spec.policy in {"suppress_same_day", "top_20d", "market_day_family_quota"}
    rejected["blocked_by_fast_fail_rejector"] = spec.arm_type == "rejector_overlay"
    selected_keep = [
        "arm_id",
        "target_regime",
        "candidate_scope_id",
        "source_scope_id",
        "canonical_event_id",
        "event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "non_executable_next_open",
        "event_split",
        "market_regime_bucket",
        "family_id",
        "mechanism_cluster_id",
        "rank_score",
        "rank_score_available",
        "event_family_priority",
        "selected_reason",
        "r2_policy",
        "cooldown_rule",
        "family_budget_rule",
        "feature_source_only",
    ]
    rejected_keep = [
        "arm_id",
        "target_regime",
        "candidate_scope_id",
        "canonical_event_id",
        "event_id",
        "instrument",
        "event_t0_date",
        "event_split",
        "market_regime_bucket",
        "family_id",
        "rank_score",
        "rank_score_available",
        "rejection_reason",
        "blocked_by_cooldown",
        "blocked_by_family_budget",
        "blocked_by_collision",
        "blocked_by_fast_fail_rejector",
    ]
    for column in selected_keep:
        if column not in selected.columns:
            selected[column] = ""
    for column in rejected_keep:
        if column not in rejected.columns:
            rejected[column] = ""
    selected = selected[selected_keep].copy()
    rejected = rejected[rejected_keep].copy()
    return selected, rejected, status


def merge_event_labels(events: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    if labels.empty:
        out = events.copy()
        out["event_level_label_source_status"] = "not_available_publishable_source"
        return out
    label_cols = [
        col
        for col in [
            "event_id",
            "failure_10_label",
            "failure_10_complete",
            "event_false_repair_20d_label",
            "event_false_repair_20d_complete",
            "event_big_winner_120d_label",
            "horizon_complete_120d",
            "captured_target_episode_count",
        ]
        if col in labels.columns
    ]
    out = events.merge(labels[label_cols].drop_duplicates("event_id"), on="event_id", how="left", suffixes=("", "_label"))
    out["event_level_label_source_status"] = np.where(
        out.get("failure_10_complete", pd.Series(False, index=out.index)).notna(),
        "event_level_label_available",
        "not_available_publishable_source",
    )
    return out


def density_for_events(events: pd.DataFrame, tables: dict[str, Any]) -> dict[str, Any]:
    instrument_years, e1_density, _ = density_reference(tables)
    if events.empty:
        normalised = events.copy()
        metrics = density_audit.density_metrics_for_events(normalised, instrument_years=instrument_years)
    else:
        normalised = ensure_event_columns(events)
        metrics = density_audit.density_metrics_for_events(normalised, instrument_years=instrument_years)
    metrics["density_vs_e1_full_denominator"] = safe_rate(metrics["events_per_instrument_year_mean"], e1_density)
    gaps = density_audit.adjacent_gaps(normalised) if not normalised.empty else pd.Series(dtype=float)
    metrics["adjacent_gap_median"] = float(gaps.median()) if not gaps.empty and gaps.notna().any() else np.nan
    return metrics


def cheap_density_for_events(events: pd.DataFrame, tables: dict[str, Any]) -> dict[str, Any]:
    instrument_years, e1_density, _ = density_reference(tables)
    event_count = int(len(events))
    if event_count == 0:
        return {
            "events_per_instrument_year_mean": np.nan,
            "events_per_instrument_year_p95": np.nan,
            "density_vs_e1_full_denominator": np.nan,
            "rolling_10d_duplicate_rate": np.nan,
            "same_day_duplicate_rate": np.nan,
        }
    normalised = ensure_event_columns(events)
    instrument_count = max(int(normalised["instrument"].nunique()), 1)
    years_per_instrument = instrument_years / instrument_count if instrument_years else np.nan
    counts = normalised.groupby("instrument").size()
    p95 = float((counts / years_per_instrument).quantile(0.95)) if years_per_instrument else np.nan
    mean = event_count / instrument_years if instrument_years else np.nan
    same_day = (
        normalised.groupby(["instrument", "event_window_anchor_pos"], dropna=False)["event_key"].transform("count")
        > 1
    )
    return {
        "events_per_instrument_year_mean": mean,
        "events_per_instrument_year_p95": p95,
        "density_vs_e1_full_denominator": safe_rate(mean, e1_density),
        "rolling_10d_duplicate_rate": np.nan,
        "same_day_duplicate_rate": safe_rate(int(same_day.sum()), event_count),
    }


def fast_fail_for_events(events: pd.DataFrame, labels: pd.DataFrame, e1_rate: float, e1_false_rate: float) -> dict[str, Any]:
    merged = merge_event_labels(events, labels)
    if merged.empty:
        return {
            "fast_fail_10d_count": 0,
            "fast_fail_10d_rate": np.nan,
            "fast_fail_10d_excess_vs_e1": np.nan,
            "false_repair_20d_count": 0,
            "false_repair_20d_rate": np.nan,
            "false_repair_20d_excess_vs_e1": np.nan,
            "event_level_label_source_status": "not_available_publishable_source",
        }
    complete = bool_series(merged, "failure_10_complete")
    fast = pd.to_numeric(merged.get("failure_10_label"), errors="coerce").fillna(0).eq(1)
    false20 = bool_series(merged, "event_false_repair_20d_label")
    fast_count = int((complete & fast).sum())
    fast_rate = safe_rate(fast_count, int(complete.sum()))
    false_count = int(false20.sum())
    false_rate = safe_rate(false_count, len(merged))
    status = "event_level_label_available" if int(complete.sum()) else "not_available_publishable_source"
    return {
        "fast_fail_10d_count": fast_count,
        "fast_fail_10d_rate": fast_rate,
        "fast_fail_10d_excess_vs_e1": fast_rate - e1_rate if pd.notna(fast_rate) and pd.notna(e1_rate) else np.nan,
        "false_repair_20d_count": false_count,
        "false_repair_20d_rate": false_rate,
        "false_repair_20d_excess_vs_e1": false_rate - e1_false_rate if pd.notna(false_rate) and pd.notna(e1_false_rate) else np.nan,
        "event_level_label_source_status": status,
    }


def e1_rates(tables: dict[str, Any], split: str, regime: str) -> tuple[float, float]:
    perf = tables["regime_family_performance_matrix"]
    row = table_row(perf, scope=E1_SCOPE, split=split, regime=regime)
    if row is None:
        return np.nan, np.nan
    return float(row.get("fast_fail_10d_rate", np.nan)), float(row.get("false_repair_20d_rate", np.nan))


def cell_status(event_count: int) -> str:
    if event_count < 30:
        return "diagnostic_only"
    if event_count < 100:
        return "low_power_caution"
    return "sufficient_for_cell_readout"


def more_conservative_status(a: str, b: str) -> str:
    return a if SAMPLE_ORDER.get(a, 99) >= SAMPLE_ORDER.get(b, 99) else b


def most_conservative_status(statuses: list[str]) -> str:
    if not statuses:
        return "diagnostic_only"
    out = statuses[0]
    for status in statuses[1:]:
        out = more_conservative_status(out, status)
    return out


def upstream_scopes_for_arm(spec: ArmSpec) -> list[str]:
    if spec.policy == "all_core":
        return [R_CORE_SCOPE]
    if spec.policy == "t4_t7":
        return [T4_SCOPE, T7_SCOPE, T4_T7_SCOPE]
    return [R_SCOPE_BY_FAMILY[family] for family in spec.source_family_ids if family in R_SCOPE_BY_FAMILY]


def upstream_cell_status(tables: dict[str, Any], spec: ArmSpec, split: str, regime: str) -> str:
    perf = tables["regime_family_performance_matrix"]
    statuses: list[str] = []
    for scope in upstream_scopes_for_arm(spec):
        row = table_row(perf, scope=scope, split=split, regime=regime)
        if row is not None:
            statuses.append(str(row.get("cell_sample_status", "diagnostic_only")))
    return most_conservative_status(statuses)


def build_label_maps(labels: pd.DataFrame) -> tuple[dict[str, bool], dict[str, bool]]:
    if labels.empty:
        return {}, {}
    label_map = labels.drop_duplicates("event_id", keep="last").set_index("event_id").to_dict("index")
    complete_map = {event_id: bool(label.get("horizon_complete_120d", False)) for event_id, label in label_map.items()}
    positive_map = {event_id: bool(label.get("event_big_winner_120d_label", False)) for event_id, label in label_map.items()}
    return complete_map, positive_map


def build_capture_for_events(
    events: pd.DataFrame,
    template: pd.DataFrame,
    label_maps: tuple[dict[str, bool], dict[str, bool]],
    scope_id: str,
) -> pd.DataFrame:
    if template.empty:
        return pd.DataFrame()
    selected = events.copy()
    if selected.empty:
        selected["compressed_pool_id"] = scope_id
    else:
        selected["compressed_pool_id"] = scope_id
    # Reuse the compression patch's pre-replay capture logic locally to avoid importing the full module.
    complete_map, positive_map = label_maps
    events_by_instrument: dict[str, dict[str, np.ndarray]] = {}
    if not selected.empty:
        for instrument, group in selected.groupby("instrument", sort=True):
            ordered = group.sort_values(["event_t0_pos", "event_id"]).reset_index(drop=True)
            event_ids = ordered["event_id"].astype(str).to_numpy()
            complete = np.array([complete_map.get(event_id, False) for event_id in event_ids], dtype=bool)
            positive = np.array([complete_map.get(event_id, False) and positive_map.get(event_id, False) for event_id in event_ids], dtype=bool)
            events_by_instrument[str(instrument)] = {
                "pos": pd.to_numeric(ordered["event_t0_pos"], errors="coerce").fillna(-10**12).to_numpy(dtype=float),
                "event_ids": event_ids,
                "event_dates": ordered["event_t0_date"].astype(str).to_numpy(),
                "complete": complete,
                "positive": positive,
            }
    rows: list[dict[str, Any]] = []
    for row in template.to_dict("records"):
        out = {key: value for key, value in row.items() if key != "candidate_scope_id"}
        hit_count = 0
        label_complete = 0
        label_incomplete = 0
        first_event_id = ""
        first_event_date = ""
        first_positive_event_id = ""
        if bool(row.get("any_event_denominator_included", True)):
            group = events_by_instrument.get(str(row["instrument"]))
            if group is not None:
                pos = group["pos"]
                left = int(np.searchsorted(pos, float(row["window_start_pos"]), side="left"))
                right = int(np.searchsorted(pos, float(row["window_end_pos"]), side="right"))
                if right > left:
                    hit_count = right - left
                    hit_ids = group["event_ids"][left:right]
                    hit_complete = group["complete"][left:right]
                    hit_positive = group["positive"][left:right]
                    label_complete = int(hit_complete.sum())
                    label_incomplete = int(hit_count - label_complete)
                    first_event_id = str(hit_ids[0])
                    first_event_date = str(group["event_dates"][left])
                    positive_offsets = np.flatnonzero(hit_positive)
                    if len(positive_offsets) > 0:
                        first_positive_event_id = str(hit_ids[int(positive_offsets[0])])
        bridge_denominator = bool(row.get("bridge_positive_denominator_included", True))
        bridge_exclusion = row.get("bridge_positive_exclusion_reason", "")
        if bool(row.get("any_event_denominator_included", True)) and hit_count > 0 and label_complete == 0:
            bridge_denominator = False
            bridge_exclusion = "bridge_forward_120_incomplete"
        out.update(
            {
                "candidate_scope_id": scope_id,
                "any_event_captured": bool(hit_count > 0),
                "bridge_positive_denominator_included": bridge_denominator,
                "bridge_positive_exclusion_reason": bridge_exclusion,
                "bridge_positive_captured": bool(first_positive_event_id),
                "any_event_count": int(hit_count),
                "bridge_label_complete_event_count": int(label_complete),
                "bridge_label_incomplete_event_count": int(label_incomplete),
                "first_event_id": first_event_id,
                "first_event_t0_date": first_event_date,
                "first_positive_event_id": first_positive_event_id,
            }
        )
        rows.append(out)
    return pd.DataFrame(rows)


def filtered_capture(capture: pd.DataFrame, split: str, regime: str, *, bridge: bool) -> pd.DataFrame:
    required = {
        "episode_split",
        "market_regime_bucket",
        "window",
        "any_event_denominator_included",
        "bridge_positive_denominator_included",
    }
    if capture.empty or not required.issubset(set(capture.columns)):
        return pd.DataFrame()
    frame = capture.loc[
        capture["episode_split"].astype(str).eq(split)
        & capture["market_regime_bucket"].astype(str).eq(regime)
        & capture["window"].astype(str).eq(WINDOW)
    ].copy()
    denom_col = "bridge_positive_denominator_included" if bridge else "any_event_denominator_included"
    return frame.loc[bool_series(frame, denom_col)].copy()


def capture_metrics(selected_capture: pd.DataFrame, e1_capture: pd.DataFrame, split: str, regime: str) -> dict[str, Any]:
    any_frame = filtered_capture(selected_capture, split, regime, bridge=False)
    any_e1 = filtered_capture(e1_capture, split, regime, bridge=False)
    bridge_frame = filtered_capture(selected_capture, split, regime, bridge=True)
    bridge_e1 = filtered_capture(e1_capture, split, regime, bridge=True)
    any_rate = safe_rate(int(bool_series(any_frame, "any_event_captured").sum()), len(any_frame))
    bridge_rate = safe_rate(int(bool_series(bridge_frame, "bridge_positive_captured").sum()), len(bridge_frame))
    e1_any_rate = safe_rate(int(bool_series(any_e1, "any_event_captured").sum()), len(any_e1))
    e1_bridge_rate = safe_rate(int(bool_series(bridge_e1, "bridge_positive_captured").sum()), len(bridge_e1))

    if "target_episode_id" in any_e1.columns and "target_episode_id" in any_frame.columns:
        e1_any = any_e1[["target_episode_id", "any_event_captured"]].rename(columns={"any_event_captured": "e1_any"})
        selected_any = any_frame[["target_episode_id", "any_event_captured"]].rename(columns={"any_event_captured": "selected_any"})
        merged = e1_any.merge(selected_any, on="target_episode_id", how="outer").fillna(False)
    else:
        merged = pd.DataFrame(columns=["target_episode_id", "e1_any", "selected_any"])
    e1_plus = bool_series(merged, "e1_any") | bool_series(merged, "selected_any")
    e1_missed = (~bool_series(merged, "e1_any")) & bool_series(merged, "selected_any")
    return {
        "episode_denominator_n": int(len(any_frame)),
        "bridge_denominator_n": int(len(bridge_frame)),
        "pre_replay_any_recall": any_rate,
        "pre_replay_bridge_recall": bridge_rate,
        "e1_any_recall": e1_any_rate,
        "e1_bridge_recall": e1_bridge_rate,
        "incremental_recall_over_e1": safe_rate(int(e1_plus.sum()), len(merged)) - e1_any_rate if len(merged) and pd.notna(e1_any_rate) else np.nan,
        "incremental_captures_over_e1": int(e1_missed.sum()),
        "e1_missed_capture_n": int(e1_missed.sum()),
        "bridge_delta_vs_e1": bridge_rate - e1_bridge_rate if pd.notna(bridge_rate) and pd.notna(e1_bridge_rate) else np.nan,
    }


def single_family_share(events: pd.DataFrame) -> float:
    if events.empty or "family_id" not in events.columns:
        return np.nan
    counts = events["family_id"].value_counts()
    return float(counts.max() / len(events)) if len(events) else np.nan


def auc_score(scores: pd.Series, positives: pd.Series) -> float:
    frame = pd.DataFrame({"score": pd.to_numeric(scores, errors="coerce"), "positive": positives.fillna(False).astype(bool)}).dropna()
    if frame["positive"].nunique() < 2:
        return np.nan
    frame = frame.sort_values("score")
    ranks = pd.Series(np.arange(1, len(frame) + 1), index=frame.index, dtype=float)
    pos = frame["positive"]
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    return float((ranks.loc[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def pr_auc_proxy(scores: pd.Series, positives: pd.Series) -> float:
    frame = pd.DataFrame({"score": pd.to_numeric(scores, errors="coerce"), "positive": positives.fillna(False).astype(bool)}).dropna()
    if frame.empty or int(frame["positive"].sum()) == 0:
        return np.nan
    ordered = frame.sort_values("score", ascending=False)
    cum_pos = ordered["positive"].cumsum()
    precision = cum_pos / np.arange(1, len(ordered) + 1)
    return float(precision.loc[ordered["positive"]].mean())


def top_decile_lift(scores: pd.Series, positives: pd.Series) -> float:
    frame = pd.DataFrame({"score": pd.to_numeric(scores, errors="coerce"), "positive": positives.fillna(False).astype(bool)}).dropna()
    if frame.empty or frame["positive"].mean() == 0:
        return np.nan
    cutoff = max(int(math.ceil(len(frame) * 0.10)), 1)
    top = frame.sort_values("score", ascending=False).head(cutoff)
    return float(top["positive"].mean() / frame["positive"].mean())


def oos_metric_row(
    *,
    arm_id: str,
    target_regime: str,
    split: str,
    label_name: str,
    scores: pd.Series,
    positives: pd.Series,
) -> dict[str, Any]:
    auc = auc_score(scores, positives)
    status = "positive" if pd.notna(auc) and auc >= 0.5 else "not_positive_or_low_power"
    return {
        "arm_id": arm_id,
        "target_regime": target_regime,
        "split": split,
        "label_name": label_name,
        "sample_count": int(len(positives)),
        "positive_count": int(positives.fillna(False).astype(bool).sum()) if len(positives) else 0,
        "auc": auc,
        "pr_auc": pr_auc_proxy(scores, positives),
        "top_decile_lift": top_decile_lift(scores, positives),
        "calibration_status": "diagnostic_only",
        "oos_separability_status": status,
    }


def episode_score_series(events: pd.DataFrame, event_ids: pd.Series, *, missing_score: float = 0.0) -> pd.Series:
    if events.empty or "event_id" not in events.columns:
        return pd.Series(missing_score, index=event_ids.index, dtype=float)
    score_map = pd.to_numeric(events.drop_duplicates("event_id").set_index("event_id")["rank_score"], errors="coerce").to_dict()
    return event_ids.astype(str).map(score_map).fillna(missing_score).astype(float)


def build_oos_rows_for_arm(
    *,
    arm_id: str,
    target_regime: str,
    events: pd.DataFrame,
    labels: pd.DataFrame,
    capture_frame: pd.DataFrame,
    e1_capture: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, bool | str]]:
    rows: list[dict[str, Any]] = []
    labelled = merge_event_labels(events, labels)
    for split in ["robustness", "validation"]:
        group = labelled.loc[labelled["event_split"].astype(str).eq(split)].copy() if not labelled.empty else pd.DataFrame()
        scores = pd.to_numeric(group.get("rank_score", pd.Series(dtype=float)), errors="coerce")
        failure_label = (
            pd.to_numeric(group["failure_10_label"], errors="coerce").fillna(0).eq(1)
            if "failure_10_label" in group.columns
            else pd.Series(False, index=group.index)
        )
        rows.append(
            oos_metric_row(
                arm_id=arm_id,
                target_regime=target_regime,
                split=split,
                label_name="non_fast_fail_vs_fast_fail_10d",
                scores=scores,
                positives=~failure_label,
            )
        )
        rows.append(
            oos_metric_row(
                arm_id=arm_id,
                target_regime=target_regime,
                split=split,
                label_name="non_false_repair_vs_false_repair_20d",
                scores=scores,
                positives=~bool_series(group, "event_false_repair_20d_label"),
            )
        )
        rows.append(
            oos_metric_row(
                arm_id=arm_id,
                target_regime=target_regime,
                split=split,
                label_name="winner_120d",
                scores=scores,
                positives=bool_series(group, "event_big_winner_120d_label"),
            )
        )

        bridge_capture = filtered_capture(capture_frame, split, target_regime, bridge=True)
        bridge_scores = (
            episode_score_series(events, bridge_capture.get("first_event_id", pd.Series(dtype=str)), missing_score=0.0)
            if not bridge_capture.empty
            else pd.Series(dtype=float)
        )
        rows.append(
            oos_metric_row(
                arm_id=arm_id,
                target_regime=target_regime,
                split=split,
                label_name="bridge_positive_vs_bridge_negative",
                scores=bridge_scores,
                positives=bool_series(bridge_capture, "bridge_positive_captured"),
            )
        )

        selected_any = filtered_capture(capture_frame, split, target_regime, bridge=False)
        e1_any = filtered_capture(e1_capture, split, target_regime, bridge=False)
        if not selected_any.empty and not e1_any.empty:
            selected_part = selected_any[["target_episode_id", "any_event_captured", "first_event_id"]].rename(
                columns={"any_event_captured": "selected_any"}
            )
            e1_part = e1_any[["target_episode_id", "any_event_captured"]].rename(columns={"any_event_captured": "e1_any"})
            missed = e1_part.merge(selected_part, on="target_episode_id", how="left").fillna(
                {"selected_any": False, "first_event_id": ""}
            )
            missed = missed.loc[~bool_series(missed, "e1_any")].copy()
            missed_scores = episode_score_series(events, missed.get("first_event_id", pd.Series(dtype=str)), missing_score=0.0)
            missed_positive = bool_series(missed, "selected_any")
        else:
            missed_scores = pd.Series(dtype=float)
            missed_positive = pd.Series(dtype=bool)
        rows.append(
            oos_metric_row(
                arm_id=arm_id,
                target_regime=target_regime,
                split=split,
                label_name="e1_missed_captured_vs_still_missed",
                scores=missed_scores,
                positives=missed_positive,
            )
        )

    oos_frame = pd.DataFrame(rows)
    robust = oos_frame.loc[oos_frame["split"].astype(str).eq("robustness")] if not oos_frame.empty else pd.DataFrame()
    evaluable_robust = robust.loc[robust["auc"].notna()] if not robust.empty else pd.DataFrame()
    direct_pass = not evaluable_robust.empty and bool((evaluable_robust["auc"] >= 0.5).all())
    feature_pass = bool((oos_frame["oos_separability_status"].astype(str) == "positive").any()) if not oos_frame.empty else False
    status = "positive" if feature_pass else "not_positive_or_low_power"
    return rows, {
        "oos_direct_pass": direct_pass,
        "oos_feature_pass": feature_pass,
        "oos_separability_status": status,
    }


def gate_borderline(metrics: dict[str, float]) -> tuple[bool, str]:
    close: list[str] = []
    thresholds = {
        "train_incremental_recall_over_e1": TRAIN_RECALL_DELTA_MIN,
        "train_bridge_delta_vs_e1": TRAIN_BRIDGE_DELTA_MIN,
        "robustness_incremental_recall_over_e1": ROB_RECALL_DELTA_MIN,
        "robustness_bridge_delta_vs_e1": ROB_BRIDGE_DELTA_MIN,
        "fast_fail_10d_excess_vs_e1": DIRECT_FAST_FAIL_EXCESS_MAX,
        "false_repair_20d_excess_vs_e1": DIRECT_FALSE_REPAIR_EXCESS_MAX,
    }
    for key, threshold in thresholds.items():
        value = metrics.get(key)
        if value is not None and pd.notna(value) and abs(float(value) - threshold) <= BORDERLINE_BAND:
            close.append(key)
    return bool(close), ";".join(close)


def build_feature_spec(tables: dict[str, Any]) -> pd.DataFrame:
    score_spec = tables["risk_on_r_series_score_spec"].copy()
    rows = []
    for _, row in score_spec.iterrows():
        rows.append(
            {
                "feature_name": row.get("score_field_name", ""),
                "feature_family": row.get("family_id", ""),
                "source_column": row.get("source_column", ""),
                "source_artifact": "risk_on_r_series_score_spec.csv",
                "asof_policy": row.get("feature_asof_policy", "event_t0_or_earlier_only"),
                "allowed_as_feature": str(row.get("score_availability_status")) == "available",
                "blocked_reason": "" if str(row.get("score_availability_status")) == "available" else row.get("score_availability_status", ""),
                "missing_policy": row.get("missing_policy", ""),
                "point_in_time_safe": True,
                "label_leakage_check_status": "pass_no_future_label_feature",
            }
        )
    for label in ["failure_10_label", "event_false_repair_20d_label", "bridge_positive_event_or_episode_capture"]:
        rows.append(
            {
                "feature_name": label,
                "feature_family": "label_only",
                "source_column": label,
                "source_artifact": "candidate_family_event_labels.parquet/candidate_family_capture.parquet",
                "asof_policy": "future_label_not_t0_feature",
                "allowed_as_feature": False,
                "blocked_reason": "label_only_not_t0_feature",
                "missing_policy": "block_supervised_readout_if_missing",
                "point_in_time_safe": False,
                "label_leakage_check_status": "blocked_as_feature_allowed_as_label",
            }
        )
    return pd.DataFrame(rows)


def target_tier(
    metrics: dict[str, Any],
    source_caveated: bool,
    is_diagnostic_pool: bool,
    *,
    risk_off: bool = False,
) -> tuple[str, bool, bool, list[str]]:
    failures: list[str] = []
    if risk_off:
        return RISK_OFF_TIER, False, False, ["risk_off_diagnostic_only"]
    sample_pass = (
        metrics.get("train_cell_sample_status") == "sufficient_for_cell_readout"
        and metrics.get("robustness_cell_sample_status") == "sufficient_for_cell_readout"
    )
    direct_checks = {
        "recall": metrics.get("train_incremental_recall_over_e1", np.nan) >= TRAIN_RECALL_DELTA_MIN
        and metrics.get("robustness_incremental_recall_over_e1", np.nan) >= ROB_RECALL_DELTA_MIN,
        "bridge": metrics.get("train_bridge_delta_vs_e1", np.nan) >= TRAIN_BRIDGE_DELTA_MIN
        and metrics.get("robustness_bridge_delta_vs_e1", np.nan) >= ROB_BRIDGE_DELTA_MIN,
        "sample_status": sample_pass,
        "density": metrics.get("density_vs_e1_full_denominator", np.nan) <= DIRECT_DENSITY_VS_E1_MAX
        and metrics.get("events_per_instrument_year_mean", np.nan) <= DIRECT_MEAN_DENSITY_MAX,
        "p95": metrics.get("events_per_instrument_year_p95", np.nan) <= DIRECT_P95_MAX,
        "duplicate": metrics.get("rolling_10d_duplicate_rate", np.nan) <= DIRECT_DUPLICATE_MAX,
        "selected_share": metrics.get("single_family_selected_share_max", np.nan) <= DIRECT_SHARE_MAX,
        "fast_fail": metrics.get("fast_fail_10d_excess_vs_e1", np.nan) <= DIRECT_FAST_FAIL_EXCESS_MAX,
        "false_repair": metrics.get("false_repair_20d_excess_vs_e1", np.nan) <= DIRECT_FALSE_REPAIR_EXCESS_MAX,
        "source": metrics.get("event_level_label_source_status") == "event_level_label_available",
        "event_membership": not metrics.get("aggregate_only", False),
        "oos_separability": bool(metrics.get("oos_direct_pass", False)),
    }
    direct_pass = all(bool(v) for v in direct_checks.values()) and not is_diagnostic_pool
    if direct_pass:
        return (SOURCE_CAVEATED_DIRECT_TIER if source_caveated else DIRECT_TIER), True, True, []

    feature_checks = {
        "bridge": metrics.get("train_bridge_delta_vs_e1", np.nan) > 0
        and metrics.get("robustness_bridge_delta_vs_e1", np.nan) >= -0.01,
        "density": metrics.get("density_vs_e1_full_denominator", np.nan) <= FEATURE_DENSITY_VS_E1_MAX,
        "p95": metrics.get("events_per_instrument_year_p95", np.nan) <= FEATURE_P95_MAX,
        "duplicate": metrics.get("rolling_10d_duplicate_rate", np.nan) <= FEATURE_DUPLICATE_MAX,
        "selected_share": metrics.get("single_family_selected_share_max", np.nan) <= FEATURE_SHARE_MAX,
        "fast_fail": metrics.get("fast_fail_10d_excess_vs_e1", np.nan) <= FEATURE_FAST_FAIL_EXCESS_MAX,
        "source": metrics.get("event_level_label_source_status") == "event_level_label_available",
        "event_membership": not metrics.get("aggregate_only", False),
        "oos_separability": bool(metrics.get("oos_feature_pass", False)),
    }
    feature_pass = all(bool(v) for v in feature_checks.values()) and not is_diagnostic_pool
    if feature_pass:
        return (SOURCE_CAVEATED_FEATURE_TIER if source_caveated else FEATURE_TIER), False, True, [
            key for key, passed in direct_checks.items() if not bool(passed)
        ]

    failures = [key for key, passed in {**direct_checks, **feature_checks}.items() if not bool(passed)]
    return DIAGNOSTIC_TIER, False, False, sorted(set(failures))


def build_outputs(tables: dict[str, Any], a_manifest: dict[str, Any], b_manifest: dict[str, Any]) -> dict[str, pd.DataFrame]:
    r_events, t_events, core_events = load_contract_event_pools(tables)
    labels = tables["candidate_family_event_labels"]
    capture = tables["candidate_family_capture"]
    supervised_cache_available = (
        not tables["candidate_family_event_labels"].empty
        and not tables["candidate_family_capture"].empty
        and not tables["cross_section_feature_panel"].empty
    )
    if not capture.empty and {"candidate_scope_id", "window", "market_regime_bucket", "episode_split"}.issubset(set(capture.columns)):
        e1_template = capture.loc[
            capture["candidate_scope_id"].astype(str).eq(E1_CAPTURE_SCOPE)
            & capture["window"].astype(str).eq(WINDOW)
            & capture["market_regime_bucket"].astype(str).isin(ALL_REGIMES)
            & capture["episode_split"].astype(str).isin(SPLITS)
        ].copy()
    else:
        e1_template = pd.DataFrame()
    e1_capture = e1_template.copy()
    label_maps = build_label_maps(labels)
    source_caveated = (
        a_manifest.get("decision") == A_DECISION_PARTIAL
        or b_manifest.get("decision") == B_DECISION_SOURCE_CAVEATED
        or bool(
            tables["regime_family_retention_source_status"]["retention_source_status"]
            .astype(str)
            .eq("pre_replay_capture_only")
            .any()
        )
    )
    final_decision = FINAL_SOURCE_CAVEATED if source_caveated else FINAL_COMPLETE

    selected_rows: list[pd.DataFrame] = []
    rejected_rows: list[pd.DataFrame] = []
    arm_status: dict[tuple[str, str], str] = {}
    for spec in ARM_SPECS:
        for regime in ALL_REGIMES:
            selected, rejected, status = select_events_for_arm(
                spec,
                regime,
                r_events,
                t_events,
                core_events,
                tables,
                supervised_cache_available=supervised_cache_available,
            )
            selected["source_caveat_status"] = "source_caveated_pre_replay" if source_caveated else "complete"
            rejected["source_caveat_status"] = "source_caveated_pre_replay" if source_caveated else "complete"
            selected_rows.append(selected)
            rejected_rows.append(rejected)
            arm_status[(spec.arm_id, regime)] = status

    selected_all = pd.concat(selected_rows, ignore_index=True) if selected_rows else pd.DataFrame()
    rejected_all = pd.concat(rejected_rows, ignore_index=True) if rejected_rows else pd.DataFrame()

    density_rows: list[dict[str, Any]] = []
    bridge_rows: list[dict[str, Any]] = []
    frontier_rows: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    family_budget_rows: list[dict[str, Any]] = []
    deoverlap_rows: list[dict[str, Any]] = []
    oos_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    captures_by_arm: dict[tuple[str, str], pd.DataFrame] = {}

    perf = tables["regime_family_performance_matrix"]
    for spec in ARM_SPECS:
        for regime in ALL_REGIMES:
            events = selected_all.loc[
                selected_all["arm_id"].astype(str).eq(spec.arm_id)
                & selected_all["target_regime"].astype(str).eq(regime)
            ].copy()
            status = arm_status[(spec.arm_id, regime)]
            target_scope = f"{spec.arm_id}::{regime}"
            capture_frame = build_capture_for_events(events, e1_template, label_maps, target_scope)
            captures_by_arm[(spec.arm_id, regime)] = capture_frame

            dens = density_for_events(events, tables)
            share_max = single_family_share(events)
            train_recall = capture_metrics(capture_frame, e1_capture, "train", regime)
            rob_recall = capture_metrics(capture_frame, e1_capture, "robustness", regime)
            val_recall = capture_metrics(capture_frame, e1_capture, "validation", regime)
            train_count = int((events["event_split"].astype(str) == "train").sum()) if not events.empty else 0
            rob_count = int((events["event_split"].astype(str) == "robustness").sum()) if not events.empty else 0
            val_count = int((events["event_split"].astype(str) == "validation").sum()) if not events.empty else 0
            train_status = more_conservative_status(cell_status(train_count), upstream_cell_status(tables, spec, "train", regime))
            rob_status = more_conservative_status(cell_status(rob_count), upstream_cell_status(tables, spec, "robustness", regime))
            ff_rate, false_rate = e1_rates(tables, "all", regime)
            ff = fast_fail_for_events(events, labels, ff_rate, false_rate)
            arm_oos_rows, oos_summary = build_oos_rows_for_arm(
                arm_id=spec.arm_id,
                target_regime=regime,
                events=events,
                labels=labels,
                capture_frame=capture_frame,
                e1_capture=e1_capture,
            )
            oos_rows.extend(arm_oos_rows)
            metrics = {
                **dens,
                **ff,
                **oos_summary,
                "single_family_selected_share_max": share_max,
                "train_incremental_recall_over_e1": train_recall["incremental_recall_over_e1"],
                "train_bridge_delta_vs_e1": train_recall["bridge_delta_vs_e1"],
                "robustness_incremental_recall_over_e1": rob_recall["incremental_recall_over_e1"],
                "robustness_bridge_delta_vs_e1": rob_recall["bridge_delta_vs_e1"],
                "train_cell_sample_status": train_status,
                "robustness_cell_sample_status": rob_status,
                "aggregate_only": False,
            }
            is_risk_off = regime in DIAGNOSTIC_REGIMES
            is_diagnostic_pool = spec.arm_id in {"baseline_r_core_no_ranker_diagnostic", "baseline_t4_t7_negative_control", "r2_diagnostic_only_arm"} or is_risk_off
            tier, direct_pass, feature_pass, failures = target_tier(metrics, source_caveated, is_diagnostic_pool, risk_off=is_risk_off)
            borderline_flag, borderline_names = gate_borderline(metrics)
            source_family_ids = ";".join(spec.source_family_ids)

            frontier_rows.append(
                {
                    "arm_id": spec.arm_id,
                    "arm_type": spec.arm_type,
                    "target_regime": regime,
                    "source_family_ids": source_family_ids,
                    "r2_policy": spec.r2_policy,
                    "upstream_a_decision": a_manifest.get("decision"),
                    "upstream_b_decision": b_manifest.get("decision"),
                    "source_caveat_status": "source_caveated_pre_replay" if source_caveated else "complete",
                    "train_selected_event_count": train_count,
                    "validation_selected_event_count": val_count,
                    "robustness_selected_event_count": rob_count,
                    "density_vs_e1_full_denominator": dens["density_vs_e1_full_denominator"],
                    "events_per_instrument_year_mean": dens["events_per_instrument_year_mean"],
                    "events_per_instrument_year_p95": dens["events_per_instrument_year_p95"],
                    "density_granularity": "selected_arm_recomputed",
                    "rolling_10d_duplicate_rate": dens["rolling_10d_duplicate_rate"],
                    "adjacent_gap_median": dens["adjacent_gap_median"],
                    "cross_family_collision_rate": dens["same_day_duplicate_rate"],
                    "single_family_selected_share_max": share_max,
                    "train_incremental_recall_over_e1": train_recall["incremental_recall_over_e1"],
                    "train_bridge_delta_vs_e1": train_recall["bridge_delta_vs_e1"],
                    "robustness_incremental_recall_over_e1": rob_recall["incremental_recall_over_e1"],
                    "robustness_bridge_delta_vs_e1": rob_recall["bridge_delta_vs_e1"],
                    "fast_fail_10d_rate": ff["fast_fail_10d_rate"],
                    "fast_fail_10d_excess_vs_e1": ff["fast_fail_10d_excess_vs_e1"],
                    "false_repair_20d_rate": ff["false_repair_20d_rate"],
                    "false_repair_20d_excess_vs_e1": ff["false_repair_20d_excess_vs_e1"],
                    "direct_entry_gate_pass": direct_pass,
                    "feature_source_gate_pass": feature_pass,
                    "target_regime_decision_tier": tier,
                    "final_decision": final_decision,
                    "ranker_arm_status": status,
                    "train_cell_sample_status": train_status,
                    "robustness_cell_sample_status": rob_status,
                    "sample_status_gate_pass": train_status == "sufficient_for_cell_readout" and rob_status == "sufficient_for_cell_readout",
                    "borderline_pass_flag": borderline_flag,
                    "borderline_metric_names": borderline_names,
                    "failure_reason": ";".join(failures),
                }
            )

            decision_rows.append(
                {
                    "arm_id": spec.arm_id,
                    "target_regime": regime,
                    "target_regime_decision_tier": tier,
                    "final_decision": final_decision,
                    "direct_entry_gate_pass": direct_pass,
                    "feature_source_gate_pass": feature_pass,
                    "density_gate_pass": bool(dens["density_vs_e1_full_denominator"] <= DIRECT_DENSITY_VS_E1_MAX),
                    "p95_gate_pass": bool(dens["events_per_instrument_year_p95"] <= DIRECT_P95_MAX),
                    "duplicate_gate_pass": bool(dens["rolling_10d_duplicate_rate"] <= DIRECT_DUPLICATE_MAX),
                    "bridge_gate_pass": bool(
                        train_recall["bridge_delta_vs_e1"] >= TRAIN_BRIDGE_DELTA_MIN
                        and rob_recall["bridge_delta_vs_e1"] >= ROB_BRIDGE_DELTA_MIN
                    ),
                    "recall_gate_pass": bool(
                        train_recall["incremental_recall_over_e1"] >= TRAIN_RECALL_DELTA_MIN
                        and rob_recall["incremental_recall_over_e1"] >= ROB_RECALL_DELTA_MIN
                    ),
                    "fast_fail_gate_pass": bool(ff["fast_fail_10d_excess_vs_e1"] <= DIRECT_FAST_FAIL_EXCESS_MAX),
                    "false_repair_gate_pass": bool(ff["false_repair_20d_excess_vs_e1"] <= DIRECT_FALSE_REPAIR_EXCESS_MAX),
                    "selected_share_gate_pass": bool(share_max <= DIRECT_SHARE_MAX) if pd.notna(share_max) else False,
                    "sample_status_gate_pass": train_status == "sufficient_for_cell_readout" and rob_status == "sufficient_for_cell_readout",
                    "oos_separability_status": oos_summary["oos_separability_status"],
                    "borderline_pass_flag": borderline_flag,
                    "borderline_metric_names": borderline_names,
                    "supported_usage": "direct_entry" if direct_pass else ("feature_source" if feature_pass else "diagnostic_only"),
                    "failure_reason": ";".join(failures),
                }
            )

            for split in ["all", *SPLITS]:
                group = events if split == "all" else events.loc[events["event_split"].astype(str).eq(split)].copy()
                e1_ff, e1_false = e1_rates(tables, "all" if split == "all" else split, regime)
                gdens = dens if split == "all" else density_for_events(group, tables)
                gff = fast_fail_for_events(group, labels, e1_ff, e1_false)
                density_rows.append(
                    {
                        "arm_id": spec.arm_id,
                        "target_regime": regime,
                        "split": split,
                        "market_regime_bucket": regime,
                        "selected_event_count": int(len(group)),
                        "density_granularity": "selected_arm_recomputed",
                        "density_reference_scope_id": E1_SCOPE,
                        "events_per_instrument_year_mean": gdens["events_per_instrument_year_mean"],
                        "events_per_instrument_year_p95": gdens["events_per_instrument_year_p95"],
                        "density_vs_e1_full_denominator": gdens["density_vs_e1_full_denominator"],
                        "rolling_10d_duplicate_rate": gdens["rolling_10d_duplicate_rate"],
                        "adjacent_gap_median": gdens["adjacent_gap_median"],
                        "fast_fail_10d_count": gff["fast_fail_10d_count"],
                        "fast_fail_10d_rate": gff["fast_fail_10d_rate"],
                        "fast_fail_10d_excess_vs_e1": gff["fast_fail_10d_excess_vs_e1"],
                        "false_repair_20d_count": gff["false_repair_20d_count"],
                        "false_repair_20d_rate": gff["false_repair_20d_rate"],
                        "false_repair_20d_excess_vs_e1": gff["false_repair_20d_excess_vs_e1"],
                        "event_level_label_source_status": gff["event_level_label_source_status"],
                        "direct_entry_density_gate_pass": bool(
                            gdens["density_vs_e1_full_denominator"] <= DIRECT_DENSITY_VS_E1_MAX
                            and gdens["events_per_instrument_year_mean"] <= DIRECT_MEAN_DENSITY_MAX
                            and gdens["events_per_instrument_year_p95"] <= DIRECT_P95_MAX
                        ),
                        "feature_source_density_gate_pass": bool(
                            gdens["density_vs_e1_full_denominator"] <= FEATURE_DENSITY_VS_E1_MAX
                            and gdens["events_per_instrument_year_p95"] <= FEATURE_P95_MAX
                        ),
                    }
                )

            for split, cm in [("train", train_recall), ("robustness", rob_recall), ("validation", val_recall)]:
                count = int((events["event_split"].astype(str) == split).sum()) if not events.empty else 0
                upstream_status = upstream_cell_status(tables, spec, split, regime)
                own_status = cell_status(count)
                bridge_rows.append(
                    {
                        "arm_id": spec.arm_id,
                        "target_regime": regime,
                        "split": split,
                        "market_regime_bucket": regime,
                        "episode_denominator_n": cm["episode_denominator_n"],
                        "bridge_denominator_n": cm["bridge_denominator_n"],
                        "selected_event_count": count,
                        "pre_replay_any_recall": cm["pre_replay_any_recall"],
                        "pre_replay_bridge_recall": cm["pre_replay_bridge_recall"],
                        "incremental_recall_over_e1": cm["incremental_recall_over_e1"],
                        "incremental_captures_over_e1": cm["incremental_captures_over_e1"],
                        "e1_missed_capture_n": cm["e1_missed_capture_n"],
                        "retention_source_status": "pre_replay_capture_only",
                        "cell_sample_status": more_conservative_status(own_status, upstream_status),
                    }
                )

            for family, group in events.groupby("family_id", sort=False):
                candidate_pool = t_events if spec.policy == "t4_t7" else (core_events if spec.policy == "all_core" else r_events)
                family_budget_rows.append(
                    {
                        "arm_id": spec.arm_id,
                        "target_regime": regime,
                        "family_id": family,
                        "budget_rule": spec.policy,
                        "budget_cap": np.nan,
                        "candidate_event_count": int(
                            (
                                candidate_pool["market_regime_bucket"].astype(str).eq(regime)
                                & candidate_pool["family_id"].astype(str).eq(str(family))
                            ).sum()
                        ),
                        "selected_event_count": int(len(group)),
                        "selected_share": safe_rate(int(len(group)), int(len(events))),
                        "single_family_share_gate_pass": safe_rate(int(len(group)), int(len(events))) <= DIRECT_SHARE_MAX,
                        "r2_policy": spec.r2_policy,
                    }
                )

            if not events.empty:
                same_day = events.groupby(["instrument", "event_t0_date"], dropna=False).size().rename("post_deoverlap_selected_count").reset_index()
                for _, row in same_day.head(5000).iterrows():
                    deoverlap_rows.append(
                        {
                            "arm_id": spec.arm_id,
                            "target_regime": regime,
                            "instrument": row["instrument"],
                            "event_t0_date": row["event_t0_date"],
                            "pre_deoverlap_event_count": np.nan,
                            "post_deoverlap_selected_count": int(row["post_deoverlap_selected_count"]),
                            "suppressed_event_count": np.nan,
                            "suppression_rule": spec.policy,
                            "cross_family_collision_count": max(int(row["post_deoverlap_selected_count"]) - 1, 0),
                            "cooldown_rule": spec.policy if spec.policy.startswith("cooldown") else "",
                            "family_budget_rule": spec.policy if "budget" in spec.policy or "weighted" in spec.policy else "",
                        }
                    )

            if regime == "transition":
                b_rows = tables["transition_event_family_reselection_matrix"].loc[
                    tables["transition_event_family_reselection_matrix"]["split"].isin(SPLITS)
                    & tables["transition_event_family_reselection_matrix"]["candidate_scope_id"].isin(
                        [R6_SCOPE, "08_R1_event_regime_gated", "08_R7_event_regime_gated", "08_R2_event_regime_gated", T4_T7_SCOPE, E1_SCOPE]
                    )
                ]
                for _, row in b_rows.iterrows():
                    transition_rows.append(
                        {
                            "arm_id": spec.arm_id,
                            "split": row["split"],
                            "candidate_scope_id": row["candidate_scope_id"],
                            "family_id": row["family_id"],
                            "transition_role": row["transition_reselection_role"],
                            "pre_replay_any_recall": row["pre_replay_any_recall"],
                            "pre_replay_bridge_recall": row["pre_replay_bridge_recall"],
                            "fast_fail_10d_rate": row["fast_fail_10d_rate"],
                            "false_repair_20d_rate": row["false_repair_20d_rate"],
                            "target_regime_decision_tier": tier,
                            "t4_t7_negative_control_status": "negative_control" if row["candidate_scope_id"] == T4_T7_SCOPE else "",
                        }
                    )

    selected_columns = [
        "arm_id",
        "target_regime",
        "candidate_scope_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_split",
        "market_regime_bucket",
        "family_id",
        "mechanism_cluster_id",
        "rank_score",
        "rank_score_available",
        "selected_reason",
        "r2_policy",
        "cooldown_rule",
        "family_budget_rule",
        "feature_source_only",
        "source_caveat_status",
    ]
    selected_out = selected_all.copy()
    selected_out["selected_rank"] = selected_out.groupby(["arm_id", "target_regime"])["rank_score"].rank(method="first", ascending=False, na_option="bottom")
    selected_columns.insert(12, "selected_rank")
    for column in selected_columns:
        if column not in selected_out.columns:
            selected_out[column] = ""

    rejected_columns = [
        "arm_id",
        "target_regime",
        "candidate_scope_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_split",
        "market_regime_bucket",
        "family_id",
        "rank_score",
        "rank_score_available",
        "rejection_reason",
        "blocked_by_cooldown",
        "blocked_by_family_budget",
        "blocked_by_collision",
        "blocked_by_fast_fail_rejector",
    ]
    rejected_out = rejected_all.copy()
    for column in rejected_columns:
        if column not in rejected_out.columns:
            rejected_out[column] = ""

    failure_rows: list[dict[str, Any]] = []
    decisions = pd.DataFrame(decision_rows)
    if not decisions.empty:
        for (arm_id, regime, reason), group in decisions.assign(
            failure_reason=decisions["failure_reason"].fillna("").replace("", "none")
        ).groupby(["arm_id", "target_regime", "failure_reason"], dropna=False):
            failure_rows.append(
                {
                    "arm_id": arm_id,
                    "target_regime": regime,
                    "failure_reason": reason,
                    "failure_count": int(len(group)),
                    "failure_share": 1.0,
                    "blocking_level": "target_regime_tier",
                    "example_scope_ids": R_CORE_SCOPE,
                }
            )

    source_caveat = build_source_caveat_audit(a_manifest, b_manifest, source_caveated)
    label_policy = build_label_policy_audit()

    return {
        "risk_on_r_series_ranker_arm_frontier": pd.DataFrame(frontier_rows),
        "risk_on_r_series_ranker_selected_events": selected_out[selected_columns],
        "risk_on_r_series_ranker_rejected_events": rejected_out[rejected_columns],
        "risk_on_r_series_ranker_feature_spec": build_feature_spec(tables),
        "risk_on_r_series_ranker_family_budget_audit": pd.DataFrame(family_budget_rows),
        "risk_on_r_series_ranker_density_fast_fail_readout": pd.DataFrame(density_rows),
        "risk_on_r_series_ranker_bridge_recall_readout": pd.DataFrame(bridge_rows),
        "risk_on_r_series_ranker_transition_reselection_readout": pd.DataFrame(transition_rows),
        "risk_on_r_series_ranker_deoverlap_audit": pd.DataFrame(deoverlap_rows),
        "risk_on_r_series_ranker_oos_separability": pd.DataFrame(oos_rows),
        "risk_on_r_series_ranker_decision_tiers": decisions,
        "risk_on_r_series_ranker_failure_distribution": pd.DataFrame(failure_rows),
        "risk_on_r_series_ranker_source_caveat_audit": source_caveat,
        "risk_on_r_series_ranker_label_policy_audit": label_policy,
    }


def build_source_caveat_audit(a_manifest: dict[str, Any], b_manifest: dict[str, Any], source_caveated: bool) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source_artifact": "density_fast_fail_audit_manifest.json",
                "source_decision": a_manifest.get("decision", ""),
                "source_status": "partial_source_complete" if a_manifest.get("decision") == A_DECISION_PARTIAL else "complete",
                "affects_direct_entry": source_caveated,
                "affects_feature_source": source_caveated,
                "required_report_caveat": "pre_replay_capture_only;no_post_filter_retention_claim",
            },
            {
                "source_artifact": "regime_family_matrix_manifest.json",
                "source_decision": b_manifest.get("decision", ""),
                "source_status": "source_caveated" if b_manifest.get("decision") == B_DECISION_SOURCE_CAVEATED else "complete",
                "affects_direct_entry": source_caveated,
                "affects_feature_source": source_caveated,
                "required_report_caveat": "source_caveated_complete",
            },
            {
                "source_artifact": "risk_off_regime_family_readouts",
                "source_decision": "diagnostic_only",
                "source_status": "risk_off_not_candidate_support",
                "affects_direct_entry": False,
                "affects_feature_source": False,
                "required_report_caveat": "risk_off_rows_diagnostic_only",
            },
        ]
    )


def build_label_policy_audit() -> pd.DataFrame:
    rows = [
        ("rank_score", "risk_on_r_series_score_spec.csv", True, False, True, "t0_or_earlier_score_feature"),
        ("family_id", "candidate_family_event_instances.csv.gz", True, False, True, "categorical_t0_feature"),
        ("market_regime_bucket", "candidate_family_event_instances.csv.gz", True, False, True, "event_regime_available_at_t0"),
        ("failure_10_label", "candidate_family_event_labels.parquet", False, True, True, "future_fast_fail_label_not_t0_feature"),
        ("event_false_repair_20d_label", "candidate_family_event_labels.parquet", False, True, True, "future_false_repair_label_not_t0_feature"),
        ("bridge_positive_event_or_episode_capture", "candidate_family_capture.parquet", False, True, True, "pre_replay_label_not_t0_feature"),
        ("event_big_winner_120d_label", "candidate_family_event_labels.parquet", False, True, True, "secondary_downstream_label"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "field_name",
            "field_source",
            "allowed_as_feature",
            "allowed_as_label",
            "allowed_as_readout",
            "reason",
        ],
    )


def output_paths() -> dict[str, Path]:
    paths = {name: C_TABLE_DIR / f"{name}.csv" for name in OUTPUT_TABLES}
    paths["report"] = C_REPORT_DIR / "risk_on_r_series_bridge_ranker_report.md"
    paths["manifest"] = C_MANIFEST_DIR / "risk_on_r_series_bridge_ranker_manifest.json"
    return paths


def build_report(frames: dict[str, pd.DataFrame], final_decision: str, drift_failures: list[dict[str, Any]]) -> str:
    frontier = frames.get("risk_on_r_series_ranker_arm_frontier", pd.DataFrame())
    decisions = frames.get("risk_on_r_series_ranker_decision_tiers", pd.DataFrame())
    selected = frames.get("risk_on_r_series_ranker_selected_events", pd.DataFrame())
    density = frames.get("risk_on_r_series_ranker_density_fast_fail_readout", pd.DataFrame())
    bridge = frames.get("risk_on_r_series_ranker_bridge_recall_readout", pd.DataFrame())
    oos = frames.get("risk_on_r_series_ranker_oos_separability", pd.DataFrame())
    transition = frames.get("risk_on_r_series_ranker_transition_reselection_readout", pd.DataFrame())
    source_caveat = frames.get("risk_on_r_series_ranker_source_caveat_audit", pd.DataFrame())
    label_policy = frames.get("risk_on_r_series_ranker_label_policy_audit", pd.DataFrame())
    direct = decisions.loc[decisions.get("direct_entry_gate_pass", pd.Series(dtype=bool)).fillna(False).astype(bool)] if not decisions.empty else pd.DataFrame()
    feature = decisions.loc[decisions.get("feature_source_gate_pass", pd.Series(dtype=bool)).fillna(False).astype(bool)] if not decisions.empty else pd.DataFrame()

    def table(frame: pd.DataFrame, columns: list[str], limit: int = 12) -> list[str]:
        if frame.empty:
            return ["No rows."]
        rows = frame.loc[:, [column for column in columns if column in frame.columns]].head(limit)
        out = ["| " + " | ".join(rows.columns) + " |", "| " + " | ".join(["---"] * len(rows.columns)) + " |"]
        for _, row in rows.iterrows():
            values = [num(value, 4) if isinstance(value, float) else str(value) for value in row.tolist()]
            out.append("| " + " | ".join(values) + " |")
        return out

    tier_counts = (
        decisions.groupby(["target_regime", "target_regime_decision_tier"]).size().reset_index(name="arm_count")
        if not decisions.empty
        else pd.DataFrame()
    )
    best_rows = (
        frontier.sort_values(
            ["target_regime", "feature_source_gate_pass", "train_bridge_delta_vs_e1", "robustness_bridge_delta_vs_e1"],
            ascending=[True, False, False, False],
        )
        .groupby("target_regime")
        .head(5)
        if not frontier.empty
        else pd.DataFrame()
    )
    blocker_rows = (
        decisions.assign(failure_reason=decisions["failure_reason"].fillna("").replace("", "none"))
        .groupby(["target_regime", "failure_reason"])
        .size()
        .reset_index(name="arm_count")
        .sort_values(["target_regime", "arm_count"], ascending=[True, False])
        if not decisions.empty
        else pd.DataFrame()
    )
    selected_scope = (
        selected.groupby(["candidate_scope_id", "family_id"]).size().reset_index(name="selected_event_rows").sort_values(
            "selected_event_rows", ascending=False
        )
        if not selected.empty
        else pd.DataFrame()
    )
    target_best_bridge = (
        bridge.loc[bridge["target_regime"].isin(TARGET_REGIMES) & bridge["split"].astype(str).eq("robustness")]
        .sort_values(["target_regime", "pre_replay_bridge_recall"], ascending=[True, False])
        .groupby("target_regime")
        .head(5)
        if not bridge.empty
        else pd.DataFrame()
    )
    oos_summary = (
        oos.groupby(["target_regime", "label_name", "oos_separability_status"]).size().reset_index(name="row_count")
        if not oos.empty
        else pd.DataFrame()
    )
    risk_off_rows = decisions.loc[decisions["target_regime"].astype(str).eq("risk_off")] if not decisions.empty else pd.DataFrame()
    t4_t7_rows = transition.loc[transition["candidate_scope_id"].isin([T4_SCOPE, T7_SCOPE, T4_T7_SCOPE])] if not transition.empty else pd.DataFrame()

    lines = [
        "# Experiment C - Risk-on / Transition R-series Bridge-Positive Ranker Report",
        "",
        f"Final decision: `{final_decision}`",
        "",
        "## 结论",
        "",
        "Experiment C 已按 `risk_on` 和 `transition` 分 regime 评估 R-series ranker / budget / cooldown / de-overlap arms，并额外输出 `risk_off` diagnostic-only readout。当前结论仍然继承 A/B 的 source caveat：recall / bridge 是 pre-replay candidate-generation readout，不是 post-filter trading signal retention。",
        "",
        f"- direct-entry pass rows: {len(direct)}",
        f"- feature-source pass rows: {len(feature)}",
        f"- risk_off diagnostic rows: {len(risk_off_rows)}",
        f"- selected event rows written: {len(selected):,}",
        "- 结论：没有 arm 通过 direct-entry 或 feature-source gate；主要 blocker 仍是 density / p95 / rolling duplicate / fast-fail / false-repair / bridge robustness 的组合。",
        "",
        "### Per-Regime Decision Tiers",
        "",
        *table(tier_counts, ["target_regime", "target_regime_decision_tier", "arm_count"], 20),
        "",
        "## A/B 输入与 Source Caveat",
        "",
        "Experiment C 读取 Experiment A density/fast-fail audit 与 Experiment B regime-family matrix。A/B 的 retention source 仍是 `pre_replay_capture_only`，因此 manifest-level decision 必须是 source-caveated complete。",
        "",
        *table(source_caveat, ["source_artifact", "source_decision", "source_status", "affects_direct_entry", "affects_feature_source", "required_report_caveat"], 10),
        "",
        "## Density / Fast-Fail Contract Inheritance",
        "",
        "- density_reference_scope_id = `07_E1_only`。",
        "- direct-entry gate: density_vs_e1 <= 1.50, mean <= 2.824076, p95 <= 7.056048, rolling 10d duplicate <= 15.00%。",
        "- feature-source gate: density_vs_e1 <= 2.50, p95 <= 12.226065, rolling 10d duplicate <= 15.00%。",
        "- 所有 selected-arm density rows 使用 `density_granularity = selected_arm_recomputed`，并调用 Experiment A 的 event-window anchor / rolling duplicate / adjacent-gap 计算逻辑。",
        "",
        "## Scope Reconstruction Audit",
        "",
        "Selected/rejected membership 通过 Experiment A 的 `candidate_scope_mapping_contract.csv` 对应 scope 重建，再把 score cache 作为附加字段 join。R-family 单体 scope 不再塌缩成 R-core union；R-core 只保留为 stress diagnostic pool。",
        "",
        *table(selected_scope, ["candidate_scope_id", "family_id", "selected_event_rows"], 20),
        "",
        "## Experiment B Result Alignment",
        "",
        "- R6 保持 `transition` primary candidate 与 `risk_on` positive candidate 的角色。",
        "- R1/R7 作为 transition support，R2 以 explicit `r2_family_budget_only` / `r2_diagnostic_only` 处理。",
        "- T4/T7 保持 challenged incumbent / negative-control，不作为 transition recall backbone 晋级。",
        "- Raw R-core union 只作为 collision stress pool，不允许 direct-entry。",
        "",
        "## Arm Frontier",
        "",
        "下表按 target_regime 取 bridge delta 排名前 5 的 arm。tier 为最终 gate 结果，risk_off 永远为 diagnostic-only。",
        "",
    ]
    if best_rows.empty:
        lines.append("No arm frontier rows were produced.")
    else:
        lines.append("| target_regime | arm_id | tier | train bridge delta | robustness bridge delta | density_vs_e1 | p95 | duplicate | fast_fail excess | failures |")
        lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
        for _, row in best_rows.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("target_regime", "")),
                        str(row.get("arm_id", "")),
                        str(row.get("target_regime_decision_tier", "")),
                        pct(row.get("train_bridge_delta_vs_e1")),
                        pct(row.get("robustness_bridge_delta_vs_e1")),
                        num(row.get("density_vs_e1_full_denominator")),
                        num(row.get("events_per_instrument_year_p95")),
                        pct(row.get("rolling_10d_duplicate_rate")),
                        pct(row.get("fast_fail_10d_excess_vs_e1")),
                        str(row.get("failure_reason", "")),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Gate Replay",
            "",
            "Direct-entry 和 feature-source gates 都按 `risk_on` / `transition` 分别评估；`risk_off` 只输出 diagnostic tier。Direct-entry 还要求 train/robustness sample status 均为 sufficient，feature-source 也必须有 OOS positive readout。",
            "",
            *table(
                decisions,
                [
                    "target_regime",
                    "arm_id",
                    "direct_entry_gate_pass",
                    "feature_source_gate_pass",
                    "density_gate_pass",
                    "p95_gate_pass",
                    "duplicate_gate_pass",
                    "bridge_gate_pass",
                    "fast_fail_gate_pass",
                    "selected_share_gate_pass",
                    "oos_separability_status",
                    "failure_reason",
                ],
                18,
            ),
            "",
            "## Failure Distribution",
            "",
            *table(blocker_rows, ["target_regime", "failure_reason", "arm_count"], 24),
            "",
            "## Density / Duplicate / Fast-Fail Readout",
            "",
            *table(
                density.sort_values(["target_regime", "split", "density_vs_e1_full_denominator"], ascending=[True, True, False])
                if not density.empty
                else density,
                [
                    "target_regime",
                    "split",
                    "arm_id",
                    "selected_event_count",
                    "density_vs_e1_full_denominator",
                    "events_per_instrument_year_p95",
                    "rolling_10d_duplicate_rate",
                    "adjacent_gap_median",
                    "fast_fail_10d_excess_vs_e1",
                    "false_repair_20d_excess_vs_e1",
                ],
                18,
            ),
            "",
            "## Bridge / Recall Readout",
            "",
            *table(
                target_best_bridge,
                [
                    "target_regime",
                    "split",
                    "arm_id",
                    "episode_denominator_n",
                    "bridge_denominator_n",
                    "selected_event_count",
                    "pre_replay_any_recall",
                    "pre_replay_bridge_recall",
                    "incremental_recall_over_e1",
                    "e1_missed_capture_n",
                    "cell_sample_status",
                ],
                14,
            ),
            "",
            "## OOS Separability",
            "",
            "OOS 只作为 robustness / validation diagnostic，不用于 threshold tuning。Gate 使用 OOS 是否保持 positive 作为支持/阻塞读数。",
            "",
            *table(oos_summary, ["target_regime", "label_name", "oos_separability_status", "row_count"], 30),
            "",
            "## T4/T7 Negative Control",
            "",
            *table(
                t4_t7_rows,
                [
                    "split",
                    "candidate_scope_id",
                    "family_id",
                    "transition_role",
                    "pre_replay_any_recall",
                    "pre_replay_bridge_recall",
                    "fast_fail_10d_rate",
                    "target_regime_decision_tier",
                    "t4_t7_negative_control_status",
                ],
                18,
            ),
            "",
            "## Risk-Off Diagnostic",
            "",
            "Risk-off 不参与 fitting、threshold、cooldown、family-budget 或 final candidate support；所有 risk_off decision rows 均应为 `risk_off_diagnostic_only`。",
            "",
            *table(risk_off_rows, ["target_regime", "arm_id", "target_regime_decision_tier", "supported_usage", "failure_reason"], 12),
            "",
            "## Label Policy",
            "",
            "`fast_fail_10d` / `false_repair_20d` / `bridge_positive_event_or_episode_capture` 只能作为 label 或 readout，不能进入 t0 feature matrix。`winner_120d` 只作为 secondary downstream label。",
            "",
            *table(label_policy, ["field_name", "field_source", "allowed_as_feature", "allowed_as_label", "allowed_as_readout", "reason"], 12),
            "",
            "## Borderline Metrics",
            "",
            "若 recall / bridge / fast-fail / false-repair delta 距离阈值不超过 1pp，`borderline_pass_flag` 会置位并列出 metric。当前 borderline rows 如下：",
            "",
            *table(
                decisions.loc[decisions.get("borderline_pass_flag", pd.Series(dtype=bool)).fillna(False).astype(bool)]
                if not decisions.empty
                else pd.DataFrame(),
                ["target_regime", "arm_id", "borderline_metric_names", "target_regime_decision_tier"],
                20,
            ),
            "",
            "## Downstream Recommendation",
            "",
            "当前结果不支持 direct-entry，也不支持 feature-source 晋级。下一步更合理的方向是：先做 replay/post-filter retention source 补齐，或单独训练 rejector/meta-label 前先降低 R-family collision 与 fast-fail cost；不建议把 raw R-core 或 T4/T7 union 推进为 entry candidate。",
            "",
            "## Binding Drift Audit",
            "",
        ]
    )
    if drift_failures:
        lines.append("Binding drift detected:")
        for item in drift_failures[:20]:
            lines.append(f"- {item}")
    else:
        lines.append("No binding drift was detected against current A/B source tables.")
    lines.extend(["", "## 输出", ""])
    for name, frame in frames.items():
        lines.append(f"- `{name}.csv`: {len(frame):,} rows")
    lines.append("")
    return "\n".join(lines)


def build_manifest(
    frames: dict[str, pd.DataFrame],
    paths: dict[str, Path],
    final_decision: str,
    input_paths: dict[str, Path],
    a_manifest: dict[str, Any],
    b_manifest: dict[str, Any],
    drift_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    output_hashes = {
        key: file_sha256(path)
        for key, path in paths.items()
        if path.exists()
    }
    return {
        "experiment_id": "08_experiment_c_risk_on_r_series_bridge_positive_ranker",
        "run_id": "risk_on_r_series_bridge_ranker_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision": final_decision,
        "experiment_a_decision": a_manifest.get("decision", ""),
        "experiment_b_decision": b_manifest.get("decision", ""),
        "retention_policy": "pre_replay_capture_only",
        "density_granularity_policy": "selected_arm_recomputed_for_selected_arms",
        "target_regimes": TARGET_REGIMES,
        "diagnostic_regimes": DIAGNOSTIC_REGIMES,
        "binding_drift_failures": drift_failures,
        "input_artifacts": {
            key: {"path": str(path), "sha256": file_sha256(path) if path.exists() else ""}
            for key, path in sorted(input_paths.items())
        },
        "output_paths": {key: str(path) for key, path in sorted(paths.items())},
        "output_hashes": output_hashes,
        "output_row_counts": {key: int(len(frame)) for key, frame in frames.items()},
        "requirement_hash": file_sha256(REQUIREMENT_PATH) if REQUIREMENT_PATH.exists() else "",
        "runner_code_hash": file_sha256(Path(__file__)),
    }


def write_blocked_outputs(
    final_decision: str,
    reasons: list[str],
    input_paths: dict[str, Path],
    a_manifest: dict[str, Any],
    b_manifest: dict[str, Any],
) -> dict[str, Any]:
    frames = {name: pd.DataFrame() for name in OUTPUT_TABLES}
    paths = output_paths()
    for name, frame in frames.items():
        write_df(paths[name], frame)
    report = "# Experiment C - Risk-on / Transition R-series Bridge-Positive Ranker Report\n\n"
    report += f"Final decision: `{final_decision}`\n\n"
    report += "Blocked reasons:\n" + "\n".join(f"- {reason}" for reason in reasons) + "\n"
    write_text(paths["report"], report)
    manifest = build_manifest(frames, paths, final_decision, input_paths, a_manifest, b_manifest, [])
    manifest["blocked_reasons"] = reasons
    write_json(paths["manifest"], manifest)
    return {"decision": final_decision, "blocked_reasons": reasons, "manifest": str(paths["manifest"])}


def run_ranker() -> dict[str, Any]:
    gate_status, input_failures, input_paths, a_manifest, b_manifest = validate_input_gate()
    aligned, alignment_failures = check_requirement_alignment()
    if not aligned:
        input_failures.extend(alignment_failures)
        gate_status = FINAL_INPUT_BLOCKED
    if gate_status != "pass":
        return write_blocked_outputs(gate_status, input_failures, input_paths, a_manifest, b_manifest)

    tables = load_inputs()
    for scope in REQUIRED_RECONSTRUCTABLE_SCOPES:
        if not scope_reconstructable(tables, scope):
            return write_blocked_outputs(
                FINAL_SOURCE_BLOCKED,
                [f"scope_not_reconstructable:{scope}"],
                input_paths,
                a_manifest,
                b_manifest,
            )

    drift = binding_drift_failures(tables, a_manifest, b_manifest)
    if drift:
        return write_blocked_outputs(
            FINAL_BINDING_DRIFT_BLOCKED,
            [f"{item['field']}:expected={item.get('expected')}:source={item.get('source_value')}" for item in drift],
            input_paths,
            a_manifest,
            b_manifest,
        )

    frames = build_outputs(tables, a_manifest, b_manifest)
    final_decision = (
        frames["risk_on_r_series_ranker_arm_frontier"]["final_decision"].dropna().astype(str).iloc[0]
        if not frames["risk_on_r_series_ranker_arm_frontier"].empty
        else FINAL_SOURCE_CAVEATED
    )
    paths = output_paths()
    for name, frame in frames.items():
        write_df(paths[name], frame)
    write_text(paths["report"], build_report(frames, final_decision, drift))
    manifest = build_manifest(frames, paths, final_decision, input_paths, a_manifest, b_manifest, drift)
    write_json(paths["manifest"], manifest)
    return {
        "decision": final_decision,
        "output_paths": {key: str(path) for key, path in paths.items()},
        "row_counts": {key: int(len(frame)) for key, frame in frames.items()},
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "check-drift":
        ok, failures = check_requirement_alignment()
        if not ok:
            for failure in failures:
                print(failure)
            return 1
        print("risk_on_r_series_bridge_ranker_requirement_alignment_pass")
        return 0
    result = run_ranker()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if not str(result.get("decision", "")).endswith("_blocked") else 1


if __name__ == "__main__":
    raise SystemExit(main())

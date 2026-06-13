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
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402

import run_density_fast_fail_audit as density_audit  # noqa: E402


PENDING_DIR = EXPERIMENT_DIR.parent
EXP07_DIR = PENDING_DIR / "07_topn_multichannel_repair_candidate_generator_v0"

REQUIREMENT_PATH = (
    EXPERIMENT_DIR / "requirement_experiment_e_risk_on_post_filter_cost_rejector.md"
)
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

A_TABLE_DIR = TABLE_DIR / "density_fast_fail_audit"
A_REPORT_DIR = REPORT_DIR / "density_fast_fail_audit"
A_MANIFEST_DIR = MANIFEST_DIR / "density_fast_fail_audit"
B_MANIFEST_DIR = MANIFEST_DIR / "regime_family_matrix"
C_MANIFEST_DIR = MANIFEST_DIR / "risk_on_r_series_bridge_ranker"
D_TABLE_DIR = TABLE_DIR / "post_replay_event_to_episode_retention_source"
D_REPORT_DIR = REPORT_DIR / "post_replay_event_to_episode_retention_source"
D_MANIFEST_DIR = MANIFEST_DIR / "post_replay_event_to_episode_retention_source"
D_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "post_replay_event_to_episode_retention_source"

E_TABLE_DIR = TABLE_DIR / "risk_on_post_filter_cost_rejector"
E_REPORT_DIR = REPORT_DIR / "risk_on_post_filter_cost_rejector"
E_MANIFEST_DIR = MANIFEST_DIR / "risk_on_post_filter_cost_rejector"
E_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "risk_on_post_filter_cost_rejector"

FINAL_RESEARCH = "risk_on_cost_rejector_research_entry_candidate_supported"
FINAL_RESEARCH_CAVEATED = "risk_on_cost_rejector_research_entry_candidate_source_caveated_supported"
FINAL_FEATURE = "risk_on_cost_rejector_feature_source_supported"
FINAL_FEATURE_CAVEATED = "risk_on_cost_rejector_feature_source_caveated_supported"
FINAL_DIAGNOSTIC = "risk_on_cost_rejector_diagnostic_only_or_no_candidate"
FINAL_INPUT_BLOCKED = "risk_on_cost_rejector_input_blocked"
FINAL_D_SOURCE_BLOCKED = "risk_on_cost_rejector_d_source_blocked"
FINAL_BINDING_DRIFT_BLOCKED = "risk_on_cost_rejector_binding_drift_blocked"
FINAL_SCOPE_BLOCKED = "risk_on_cost_rejector_scope_reconstruction_blocked"
FINAL_SCOPE_DRIFT_BLOCKED = "risk_on_cost_rejector_scope_binding_drift_blocked"
FINAL_FEATURE_BLOCKED = "risk_on_cost_rejector_feature_source_blocked"
FINAL_LABEL_JOIN_BLOCKED = "risk_on_cost_rejector_label_join_blocked"
FINAL_LABEL_RECON_BLOCKED = "risk_on_cost_rejector_label_reconciliation_blocked"
FINAL_LABEL_HORIZON_BLOCKED = "risk_on_cost_rejector_label_horizon_blocked"
FINAL_LEAKAGE_BLOCKED = "risk_on_cost_rejector_leakage_blocked"

ALLOWED_A = {"density_fast_fail_audit_complete", "density_fast_fail_audit_partial_source_complete"}
ALLOWED_B = {"regime_family_matrix_complete", "regime_family_matrix_source_caveated_complete"}
ALLOWED_C = {"risk_on_r_series_ranker_complete", "risk_on_r_series_ranker_source_caveated_complete"}
ALLOWED_D = {
    "post_replay_retention_source_complete",
    "post_replay_retention_source_source_caveated_complete",
}

SOURCE_POOLS = ("08_R6_event_regime_gated", "08_R_core_event_regime_gated")
AUDIT_SCOPES = ("07_E1_only", "08_R6_event_regime_gated", "08_R_core_event_regime_gated", "08_R1_event_regime_gated")
TARGET_REGIME = "risk_on"
HEADLINE_WINDOW = "low_to_first_50pct"
HEADLINE_POLICY = "post_replay_executable_horizon_complete"
SPLITS = ("train", "validation", "robustness")

KEEP_FRACTIONS = (1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60, 0.50)
MODEL_SPECS = (
    ("supervised_fast_fail_rejector", "fast_fail_bad_10d"),
    ("supervised_false_repair_rejector", "false_repair_bad_20d"),
    ("supervised_joint_cost_rejector", "cost_bad_10_20"),
)

EVENT_FEATURE_COLUMNS = [
    "return_5d",
    "return_10d",
    "return_20d",
    "return_60d",
    "stock_vs_market_5d",
    "stock_vs_market_10d",
    "stock_vs_market_20d",
    "amount_ratio_20d",
    "amount_ratio_60d",
    "turnover_ratio_20d",
    "turnover_ratio_60d",
    "close_to_high_60",
    "close_to_high_120",
    "range_width_ratio_20d_60d",
    "direction_entropy_20d",
    "relative_cusum_20d",
    "momentum_percentile_20d",
    "momentum_percentile_20d_lag20",
    "universe_up_share",
    "universe_up_share_z",
    "universe_up_share_change_5d",
    "stock_vs_board_20d",
    "board_relative_cusum_20d",
    "atr_pct_rank_60d",
    "ema60_positive_run",
    "family_count",
    "channel_count",
]
PANEL_FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "stock_vs_market_20d",
    "close_to_high_60",
    "momentum_percentile_20d",
    "momentum_percentile_60d",
    "universe_up_share",
    "universe_new_high_60_share",
    "universe_up_share_z",
    "universe_up_share_change_5d",
    "board_relative_1d",
    "board_relative_cusum_20d",
    "board_return_20d",
    "stock_vs_board_20d",
]
CATEGORICAL_FEATURE_COLUMNS = [
    "source_pool",
    "board_bucket",
    "event_regime_bucket",
    "primary_family_id",
]
LOG1P_FEATURE_COLUMNS = {
    "amount_ratio_20d",
    "amount_ratio_60d",
    "turnover_ratio_20d",
    "turnover_ratio_60d",
    "ema60_positive_run",
    "family_count",
    "channel_count",
}
NUMERIC_WINSOR_LOWER_Q = 0.01
NUMERIC_WINSOR_UPPER_Q = 0.99
FEATURE_PREPROCESSING_POLICY = (
    "train_median_impute__nonnegative_log1p_selected_numeric__"
    "train_winsorize_1_99__train_zscore__categorical_train_vocab_one_hot"
)


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    path: Path
    required: bool = True


INPUT_SPECS = [
    InputSpec("requirement", REQUIREMENT_PATH),
    InputSpec("experiment_a_manifest", A_MANIFEST_DIR / "density_fast_fail_audit_manifest.json"),
    InputSpec("experiment_b_manifest", B_MANIFEST_DIR / "regime_family_matrix_manifest.json"),
    InputSpec("experiment_c_manifest", C_MANIFEST_DIR / "risk_on_r_series_bridge_ranker_manifest.json"),
    InputSpec("experiment_d_manifest", D_MANIFEST_DIR / "post_replay_event_to_episode_retention_source_manifest.json"),
    InputSpec("density_fast_fail_contract", A_REPORT_DIR / "density_fast_fail_caliber_contract.md"),
    InputSpec("candidate_scope_mapping_contract", A_TABLE_DIR / "candidate_scope_mapping_contract.csv"),
    InputSpec("candidate_scope_reconstructability_audit", A_TABLE_DIR / "candidate_scope_reconstructability_audit.csv"),
    InputSpec("candidate_10d_density_summary", A_TABLE_DIR / "candidate_10d_density_summary.csv"),
    InputSpec("07_run_manifest", EXP07_DIR / "outputs" / "manifests" / "run_manifest.json"),
    InputSpec("07_canonical_events", EXP07_DIR / "outputs" / "publishable" / "tables" / "topn_multichannel_candidate_event_canonical.csv"),
    InputSpec("07_event_labels", EXP07_DIR / "outputs" / "local_cache" / "topn_canonical_event_labels.parquet"),
    InputSpec("candidate_family_canonical_events", TABLE_DIR / "candidate_family_canonical_events.csv.gz"),
    InputSpec("candidate_family_event_instances", TABLE_DIR / "candidate_family_event_instances.csv.gz"),
    InputSpec("candidate_family_event_labels", LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet"),
    InputSpec("candidate_family_capture", LOCAL_CACHE_DIR / "candidate_family_capture.parquet"),
    InputSpec("cross_section_feature_panel", LOCAL_CACHE_DIR / "cross_section_feature_panel.parquet"),
    InputSpec("d_membership", D_LOCAL_CACHE_DIR / "post_replay_event_episode_membership.parquet"),
    InputSpec("d_scope_retention", D_TABLE_DIR / "post_replay_scope_retention_by_split_regime.csv"),
    InputSpec("d_e1_missed", D_TABLE_DIR / "post_replay_e1_missed_retention_summary.csv"),
    InputSpec("d_policy_effect", D_TABLE_DIR / "post_replay_policy_effect_summary.csv"),
    InputSpec("d_label_leakage_audit", D_TABLE_DIR / "post_replay_label_leakage_audit.csv"),
    InputSpec("d_source_coverage_audit", D_TABLE_DIR / "post_replay_source_coverage_audit.csv"),
    InputSpec("d_reconciliation", D_TABLE_DIR / "post_replay_reconciliation_against_a_b_c.csv"),
    InputSpec("d_contract", D_REPORT_DIR / "post_replay_retention_source_contract.md"),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Experiment E risk-on post-filter cost rejector.")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def ensure_dirs() -> None:
    for path in (E_TABLE_DIR, E_REPORT_DIR, E_MANIFEST_DIR, E_LOCAL_CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


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


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def row_count(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    if path.suffix == ".parquet":
        return int(len(pd.read_parquet(path)))
    if path.suffix in {".json", ".md"}:
        return 1
    return max(sum(1 for _ in path.open("rb")) - 1, 0)


def safe_div(num: float | int, den: float | int) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den)


def bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    raw = frame[column]
    if raw.dtype == bool:
        return raw.fillna(False)
    return raw.astype(str).str.lower().isin({"true", "1", "1.0", "yes"})


def post_replay_policy_mask(events: pd.DataFrame) -> pd.Series:
    horizon = bool_series(events, "horizon_complete")
    if "event_executable_flag" in events.columns:
        executable = bool_series(events, "event_executable_flag")
    else:
        executable = ~bool_series(events, "non_executable_next_open")
    return horizon & executable


def selected_ids_for_replay_policy(events: pd.DataFrame, selected_ids: set[str]) -> set[str]:
    mask = events["event_id"].astype(str).isin(selected_ids) & post_replay_policy_mask(events)
    return set(events.loc[mask, "event_id"].astype(str))


def input_audit() -> tuple[pd.DataFrame, list[str], dict[str, Path]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    paths: dict[str, Path] = {}
    for spec in INPUT_SPECS:
        paths[spec.input_id] = spec.path
        exists = spec.path.exists()
        status = "available" if exists else ("missing_required_input" if spec.required else "missing_optional_input")
        if spec.required and not exists:
            failures.append(f"missing_required_input:{spec.input_id}:{spec.path}")
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(spec.path),
                "required": spec.required,
                "status": status,
                "sha256": path_hash(spec.path),
                "row_count": row_count(spec.path),
            }
        )
    return pd.DataFrame(rows), failures, paths


def validate_manifests() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    failures: list[str] = []
    a = read_json(A_MANIFEST_DIR / "density_fast_fail_audit_manifest.json")
    b = read_json(B_MANIFEST_DIR / "regime_family_matrix_manifest.json")
    c = read_json(C_MANIFEST_DIR / "risk_on_r_series_bridge_ranker_manifest.json")
    d = read_json(D_MANIFEST_DIR / "post_replay_event_to_episode_retention_source_manifest.json")
    if a.get("decision") not in ALLOWED_A:
        failures.append(f"unsupported_experiment_a_decision:{a.get('decision')}")
    if b.get("decision") not in ALLOWED_B:
        failures.append(f"unsupported_experiment_b_decision:{b.get('decision')}")
    if c.get("decision") not in ALLOWED_C:
        failures.append(f"unsupported_experiment_c_decision:{c.get('decision')}")
    if d.get("decision") not in ALLOWED_D:
        failures.append(f"unsupported_experiment_d_decision:{d.get('decision')}")
    if d.get("entry_support_allowed") is not False:
        failures.append("experiment_d_entry_support_allowed_not_false")
    if d.get("oracle_policies_audit_only") is not True:
        failures.append("experiment_d_oracle_policies_audit_only_not_true")
    return a, b, c, d, failures


def output_paths() -> dict[str, Path]:
    return {
        "risk_on_cost_rejector_input_audit": E_TABLE_DIR / "risk_on_cost_rejector_input_audit.csv",
        "risk_on_cost_rejector_binding_audit": E_TABLE_DIR / "risk_on_cost_rejector_binding_audit.csv",
        "risk_on_cost_rejector_scope_reconstruction_audit": E_TABLE_DIR / "risk_on_cost_rejector_scope_reconstruction_audit.csv",
        "risk_on_cost_rejector_split_alignment_audit": E_TABLE_DIR / "risk_on_cost_rejector_split_alignment_audit.csv",
        "risk_on_cost_rejector_regime_role_audit": E_TABLE_DIR / "risk_on_cost_rejector_regime_role_audit.csv",
        "risk_on_cost_rejector_event_regime_gate_audit": E_TABLE_DIR / "risk_on_cost_rejector_event_regime_gate_audit.csv",
        "risk_on_cost_rejector_source_overlap_audit": E_TABLE_DIR / "risk_on_cost_rejector_source_overlap_audit.csv",
        "risk_on_cost_rejector_feature_contract": E_TABLE_DIR / "risk_on_cost_rejector_feature_contract.csv",
        "risk_on_cost_rejector_label_source_audit": E_TABLE_DIR / "risk_on_cost_rejector_label_source_audit.csv",
        "risk_on_cost_rejector_training_sample_summary": E_TABLE_DIR / "risk_on_cost_rejector_training_sample_summary.csv",
        "risk_on_cost_rejector_model_registry": E_TABLE_DIR / "risk_on_cost_rejector_model_registry.csv",
        "risk_on_cost_rejector_oos_separability": E_TABLE_DIR / "risk_on_cost_rejector_oos_separability.csv",
        "risk_on_cost_rejector_threshold_frontier": E_TABLE_DIR / "risk_on_cost_rejector_threshold_frontier.csv",
        "risk_on_cost_rejector_cost_readout": E_TABLE_DIR / "risk_on_cost_rejector_cost_readout.csv",
        "risk_on_cost_rejector_post_filter_retention_by_split": E_TABLE_DIR / "risk_on_cost_rejector_post_filter_retention_by_split.csv",
        "risk_on_cost_rejector_e1_missed_retention": E_TABLE_DIR / "risk_on_cost_rejector_e1_missed_retention.csv",
        "risk_on_cost_rejector_density_readout": E_TABLE_DIR / "risk_on_cost_rejector_density_readout.csv",
        "risk_on_cost_rejector_oracle_gap_audit": E_TABLE_DIR / "risk_on_cost_rejector_oracle_gap_audit.csv",
        "risk_on_cost_rejector_leakage_audit": E_TABLE_DIR / "risk_on_cost_rejector_leakage_audit.csv",
        "risk_on_cost_rejector_decision_tiers": E_TABLE_DIR / "risk_on_cost_rejector_decision_tiers.csv",
        "risk_on_cost_rejector_event_scores": E_TABLE_DIR / "risk_on_cost_rejector_event_scores.csv.gz",
        "risk_on_cost_rejector_selected_events": E_TABLE_DIR / "risk_on_cost_rejector_selected_events.csv.gz",
        "risk_on_cost_rejector_rejected_events": E_TABLE_DIR / "risk_on_cost_rejector_rejected_events.csv.gz",
        "risk_on_cost_rejector_top_failure_examples": E_TABLE_DIR / "risk_on_cost_rejector_top_failure_examples.csv",
        "risk_on_post_filter_cost_rejector_report": E_REPORT_DIR / "risk_on_post_filter_cost_rejector_report.md",
        "risk_on_post_filter_cost_rejector_contract": E_REPORT_DIR / "risk_on_post_filter_cost_rejector_contract.md",
        "risk_on_post_filter_cost_rejector_manifest": E_MANIFEST_DIR / "risk_on_post_filter_cost_rejector_manifest.json",
    }


def load_scope_spec(scope_id: str) -> density_audit.ScopeSpec:
    specs = {spec.candidate_scope_id: spec for spec in density_audit.build_scope_specs()}
    return specs[scope_id]


def reconstruct_scope_events(
    scope_id: str,
    canonical07: pd.DataFrame,
    canonical08: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    spec = load_scope_spec(scope_id)
    raw = density_audit.select_scope_events(spec, canonical07, canonical08)
    map_row = mapping.loc[mapping["candidate_scope_id"].astype(str).eq(scope_id)]
    source_path = Path(str(map_row.iloc[0].get("source_artifact_path", ""))) if not map_row.empty else Path("")
    out = density_audit.normalise_scope_events(raw, spec, source_path=source_path)
    if "event_regime_bucket" not in out.columns:
        out["event_regime_bucket"] = out.get("market_regime_bucket", "")
    out["source_pool"] = scope_id
    out = ensure_replay_anchor_columns(out)
    return out


def ensure_replay_anchor_columns(events: pd.DataFrame) -> pd.DataFrame:
    out = events.copy()
    if "event_window_anchor_pos" not in out.columns:
        out = density_audit.with_event_window_anchor(out)
    if "replay_anchor_pos" not in out.columns:
        out["replay_anchor_pos"] = out.get("event_window_anchor_pos", np.nan)
    if "replay_anchor_date" not in out.columns:
        out["replay_anchor_date"] = out.get("event_window_anchor_date", out.get("trade_open_date", out.get("event_t0_date", "")))
    return out


def build_scope_reconstruction_audit(
    scope_events: dict[str, pd.DataFrame],
    mapping: pd.DataFrame,
    reconstruct: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for scope_id in AUDIT_SCOPES:
        map_row = mapping.loc[mapping["candidate_scope_id"].astype(str).eq(scope_id)]
        rec_row = reconstruct.loc[reconstruct["candidate_scope_id"].astype(str).eq(scope_id)]
        frame = scope_events.get(scope_id, pd.DataFrame())
        source_row_count = int(rec_row.iloc[0].get("source_row_count", 0)) if not rec_row.empty else 0
        published_ref = int(rec_row.iloc[0].get("published_reference_event_count", 0)) if not rec_row.empty else 0
        diff = int(rec_row.iloc[0].get("reconstructed_vs_published_count_difference", 0)) if not rec_row.empty else 0
        hard_gate = bool(rec_row.iloc[0].get("hard_gate_eligible_flag", False)) if not rec_row.empty else False
        status = "pass"
        accepted_reason = ""
        if rec_row.empty or map_row.empty:
            status = "scope_mapping_missing"
        elif len(frame) != source_row_count:
            status = "source_row_count_drift"
            failures.append(f"scope_binding_drift:{scope_id}:expected_source_row_count={source_row_count}:actual={len(frame)}")
        elif scope_id == "08_R_core_event_regime_gated" and diff == -15:
            accepted_reason = "A_audit_accepted_R_core_minus_15_published_reference_difference"
        rows.append(
            {
                "source_pool": scope_id,
                "scope_mapping_status": "" if map_row.empty else str(map_row.iloc[0].get("scope_mapping_status", "")),
                "scope_status": "" if rec_row.empty else str(rec_row.iloc[0].get("scope_status", "")),
                "hard_gate_eligible_flag": hard_gate,
                "source_row_filter": "" if map_row.empty else str(map_row.iloc[0].get("source_row_filter", "")),
                "source_hash": "" if map_row.empty else str(map_row.iloc[0].get("source_artifact_hash", "")),
                "reconstructed_event_count": int(len(frame)),
                "source_row_count": source_row_count,
                "published_reference_event_count": published_ref,
                "reconstructed_vs_published_count_difference": diff,
                "accepted_difference_reason": accepted_reason,
                "scope_reconstruction_status": status,
            }
        )
    return pd.DataFrame(rows), failures


def regime_role_audit() -> pd.DataFrame:
    rows = [
        ("post_replay_scope_retention_by_split_regime.csv", "market_regime_bucket", "episode_regime_bucket"),
        ("post_replay_arm_retention_by_split_regime.csv", "market_regime_bucket", "episode_regime_bucket"),
        ("post_replay_e1_missed_retention_summary.csv", "market_regime_bucket", "episode_regime_bucket"),
        ("post_replay_policy_effect_summary.csv", "market_regime_bucket", "episode_regime_bucket"),
        ("post_replay_event_episode_membership.parquet", "market_regime_bucket", "event_regime_bucket"),
        ("post_replay_event_episode_membership.parquet", "market_regime_bucket_canonical", "event_regime_bucket"),
        ("post_replay_event_episode_membership.parquet", "market_regime_bucket_episode", "episode_regime_bucket"),
        ("post_replay_event_episode_membership.parquet", "episode_market_regime_bucket", "episode_regime_bucket"),
        ("candidate_family_canonical_events.csv.gz", "market_regime_bucket", "event_regime_bucket"),
        ("candidate_family_canonical_events.csv.gz", "event_regime_bucket", "event_regime_bucket"),
    ]
    return pd.DataFrame(rows, columns=["source_artifact", "column_name", "column_role"])


def label_scope_for_pool(source_pool: str) -> str:
    if source_pool.startswith("08_"):
        return "all_new_candidate_union"
    if source_pool == "07_E1_only":
        return "event_instance"
    return "all_new_candidate_union"


def join_event_labels(events: pd.DataFrame, labels: pd.DataFrame, membership: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    out_frames: list[pd.DataFrame] = []
    for source_pool, group in events.groupby("source_pool", dropna=False):
        label_scope = label_scope_for_pool(str(source_pool))
        labels_scope = labels.loc[labels["label_scope"].astype(str).eq(label_scope)].copy()
        duplicate_n = int(labels_scope.duplicated(["event_id", "label_scope"]).sum())
        if duplicate_n:
            failures.append(f"duplicate_label_join_rows:{source_pool}:{duplicate_n}")
        labels_scope = labels_scope.drop_duplicates(["event_id", "label_scope"], keep="last")
        merged = group.copy()
        merged["label_scope"] = label_scope
        label_cols = [
            "event_id",
            "label_scope",
            "failure_10_label",
            "failure_10_complete",
            "event_false_repair_20d_label",
            "event_false_repair_20d_complete",
            "event_big_winner_120d_label",
            "horizon_complete_120d",
        ]
        merged = merged.merge(labels_scope[label_cols], on=["event_id", "label_scope"], how="left")
        merged["horizon_complete"] = bool_series(merged, "failure_10_complete") & bool_series(
            merged, "event_false_repair_20d_complete"
        )
        merged["fast_fail_bad_10d"] = bool_series(merged, "failure_10_label")
        merged["false_repair_bad_20d"] = bool_series(merged, "event_false_repair_20d_label")
        merged["cost_bad_10_20"] = merged["fast_fail_bad_10d"] | merged["false_repair_bad_20d"]
        merged["cost_clean_10_20"] = merged["horizon_complete"] & ~merged["cost_bad_10_20"]
        merged["cost_label_status"] = np.where(merged["horizon_complete"], "complete", "incomplete_or_censored")
        mismatch_n, reconciled_n = membership_label_reconciliation(str(source_pool), label_scope, merged, membership)
        complete_rate = safe_div(int(merged["horizon_complete"].sum()), len(merged))
        rows.append(
            {
                "source_pool": source_pool,
                "label_scope": label_scope,
                "event_n": int(len(group)),
                "label_joined_n": int(merged["failure_10_complete"].notna().sum()),
                "duplicate_join_n": duplicate_n,
                "missing_label_n": int(merged["failure_10_complete"].isna().sum()),
                "cost_label_complete_n": int(merged["horizon_complete"].sum()),
                "cost_label_complete_rate": complete_rate,
                "membership_label_reconciled_n": reconciled_n,
                "membership_label_mismatch_n": mismatch_n,
                "fail_closed_reason": "label_mismatch" if mismatch_n else ("" if complete_rate >= 0.95 else "cost_label_coverage_below_95pct"),
            }
        )
        if mismatch_n and source_pool in SOURCE_POOLS:
            failures.append(f"label_reconciliation_mismatch:{source_pool}:{mismatch_n}")
        out_frames.append(merged)
    return pd.concat(out_frames, ignore_index=True, sort=False), pd.DataFrame(rows), failures


def membership_label_reconciliation(
    source_pool: str,
    label_scope: str,
    labels_joined: pd.DataFrame,
    membership: pd.DataFrame,
) -> tuple[int, int]:
    source_mem = membership.loc[
        membership["source_id"].astype(str).eq(source_pool)
        & membership["source_kind"].astype(str).eq("scope")
    ].copy()
    if source_mem.empty:
        return 0, 0
    mem_cols = [
        "event_id",
        "failure_10_label",
        "failure_10_complete",
        "event_false_repair_20d_label",
        "event_false_repair_20d_complete",
    ]
    source_mem = source_mem[mem_cols].drop_duplicates("event_id", keep="last")
    check = source_mem.merge(
        labels_joined[["event_id", *mem_cols[1:]]],
        on="event_id",
        how="inner",
        suffixes=("_membership", "_label"),
    )
    mismatch = pd.Series(False, index=check.index)
    for col in mem_cols[1:]:
        mismatch |= bool_series(check, f"{col}_membership") != bool_series(check, f"{col}_label")
    return int(mismatch.sum()), int(len(check))


def asof_join_panel(events: pd.DataFrame, panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    out = events.copy()
    out["event_t0_date_dt"] = pd.to_datetime(out["event_t0_date"], errors="coerce")
    panel_work = panel.copy()
    panel_work["date_dt"] = pd.to_datetime(panel_work["date"], errors="coerce")
    panel_cols = [col for col in PANEL_FEATURE_COLUMNS if col in panel_work.columns]
    panel_keep = ["instrument", "date_dt", *panel_cols]
    joined_parts: list[pd.DataFrame] = []
    for instrument, group in out.groupby("instrument", sort=False):
        pgroup = panel_work.loc[panel_work["instrument"].astype(str).eq(str(instrument)), panel_keep].sort_values("date_dt")
        group = group.copy()
        if pgroup.empty:
            for col in panel_cols:
                group[f"panel_{col}"] = np.nan
            group["feature_as_of_date"] = pd.NaT
            group["feature_lag_days"] = np.nan
            group["daily_panel_feature_status"] = "asof_feature_missing"
            joined_parts.append(group)
            continue
        dates = pgroup["date_dt"].to_numpy()
        idx = np.searchsorted(dates, group["event_t0_date_dt"].to_numpy(), side="right") - 1
        valid = idx >= 0
        matched = pgroup.iloc[np.maximum(idx, 0)].reset_index(drop=True)
        for col in panel_cols:
            group[f"panel_{col}"] = np.where(valid, matched[col].to_numpy(), np.nan)
        asof_dates = pd.Series(pd.NaT, index=group.index, dtype="datetime64[ns]")
        asof_dates.loc[valid] = matched.loc[valid, "date_dt"].to_numpy()
        group["feature_as_of_date"] = asof_dates
        group["feature_lag_days"] = (group["event_t0_date_dt"] - group["feature_as_of_date"]).dt.days
        group["daily_panel_feature_status"] = np.where(valid, "asof_feature_joined", "asof_feature_missing")
        joined_parts.append(group)
    joined = pd.concat(joined_parts, ignore_index=True, sort=False)
    future_rows = int((joined["feature_as_of_date"] > joined["event_t0_date_dt"]).sum())
    joined["feature_join_policy"] = "latest_same_or_prior_event_t0_date"
    meta = {
        "feature_join_policy": "latest_same_or_prior_event_t0_date",
        "feature_join_key": "instrument",
        "future_join_row_count": future_rows,
        "joined_row_count": int(joined["daily_panel_feature_status"].eq("asof_feature_joined").sum()),
        "missing_row_count": int(joined["daily_panel_feature_status"].eq("asof_feature_missing").sum()),
        "panel_feature_columns": panel_cols,
    }
    return joined, meta


def build_feature_contract(
    events: pd.DataFrame,
    event_source_hash: str,
    panel_hash: str,
    asof_meta: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for col in EVENT_FEATURE_COLUMNS:
        if col in events.columns:
            rows.append(feature_contract_row(col, "event_envelope", "event_id", "event_t0_date", event_source_hash, events))
    for col in asof_meta.get("panel_feature_columns", []):
        feature_name = f"panel_{col}"
        rows.append(feature_contract_row(feature_name, "cross_section_feature_panel", "instrument", "latest_same_or_prior_event_t0_date", panel_hash, events))
    for col in CATEGORICAL_FEATURE_COLUMNS:
        if col in events.columns:
            rows.append(feature_contract_row(col, "event_envelope", "event_id", "event_t0_date", event_source_hash, events))
    for col in ["failure_10_label", "event_false_repair_20d_label", "event_big_winner_120d_label", "target_episode_id"]:
        rows.append(
            {
                "feature_name": col,
                "source_artifact": "label_or_episode_source",
                "source_hash": "",
                "as_of_policy": "future_or_membership_field_not_t0_feature",
                "source_kind": "blocked",
                "feature_join_key": "",
                "feature_as_of_date_policy": "",
                "max_feature_as_of_date_minus_event_t0_date": np.nan,
                "uses_future_information": True,
                "allowed_as_t0_feature": False,
                "missing_rate_train": np.nan,
                "missing_rate_validation": np.nan,
                "missing_rate_robustness": np.nan,
                "blocked_reason": "not_allowed_as_t0_feature",
            }
        )
    return pd.DataFrame(rows)


def feature_contract_row(
    feature_name: str,
    source_kind: str,
    join_key: str,
    asof_policy: str,
    source_hash: str,
    events: pd.DataFrame,
) -> dict[str, Any]:
    max_delta = np.nan
    if source_kind == "cross_section_feature_panel" and "feature_lag_days" in events.columns:
        max_delta = float((-events["feature_lag_days"]).max()) if events["feature_lag_days"].notna().any() else np.nan
    train = events.loc[events["event_split"].astype(str).eq("train")]
    validation = events.loc[events["event_split"].astype(str).eq("validation")]
    robustness = events.loc[events["event_split"].astype(str).eq("robustness")]
    return {
        "feature_name": feature_name,
        "source_artifact": source_kind,
        "source_hash": source_hash,
        "as_of_policy": asof_policy,
        "source_kind": source_kind,
        "feature_join_key": join_key,
        "feature_as_of_date_policy": asof_policy,
        "max_feature_as_of_date_minus_event_t0_date": max_delta,
        "uses_future_information": False,
        "allowed_as_t0_feature": True,
        "missing_rate_train": float(train[feature_name].isna().mean()) if feature_name in train.columns and len(train) else np.nan,
        "missing_rate_validation": float(validation[feature_name].isna().mean()) if feature_name in validation.columns and len(validation) else np.nan,
        "missing_rate_robustness": float(robustness[feature_name].isna().mean()) if feature_name in robustness.columns and len(robustness) else np.nan,
        "blocked_reason": "",
    }


def build_design_matrix(events: pd.DataFrame, train_mask: pd.Series) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    numeric_cols = numeric_feature_columns(events)
    numeric_raw = events[numeric_cols].apply(pd.to_numeric, errors="coerce") if numeric_cols else pd.DataFrame(index=events.index)
    numeric, numeric_meta = preprocess_numeric_features(numeric_raw, train_mask)
    categorical_cols = [col for col in CATEGORICAL_FEATURE_COLUMNS if col in events.columns]
    cat, cat_meta = build_categorical_matrix(events, categorical_cols, train_mask)
    train_columns = list(numeric.columns) + list(cat.columns)
    matrix = pd.concat([numeric, cat], axis=1)
    matrix = matrix.reindex(columns=train_columns, fill_value=0.0).astype(float)
    preprocessing = {
        "policy": FEATURE_PREPROCESSING_POLICY,
        "numeric": numeric_meta,
        "categorical": cat_meta,
    }
    return matrix, train_columns, preprocessing


def numeric_feature_columns(events: pd.DataFrame) -> list[str]:
    cols = [col for col in EVENT_FEATURE_COLUMNS if col in events.columns]
    cols += [f"panel_{col}" for col in PANEL_FEATURE_COLUMNS if f"panel_{col}" in events.columns]
    return cols


def preprocess_numeric_features(numeric: pd.DataFrame, train_mask: pd.Series) -> tuple[pd.DataFrame, dict[str, Any]]:
    if numeric.empty:
        return numeric.copy(), {
            "numeric_columns": [],
            "log1p_columns": [],
            "winsor_quantiles": [NUMERIC_WINSOR_LOWER_Q, NUMERIC_WINSOR_UPPER_Q],
            "scaler": "train_zscore",
        }
    transformed = numeric.copy()
    log_cols = [col for col in transformed.columns if col in LOG1P_FEATURE_COLUMNS]
    for col in log_cols:
        transformed[col] = np.log1p(pd.to_numeric(transformed[col], errors="coerce").clip(lower=0.0))
    train_numeric = transformed.loc[train_mask]
    medians = train_numeric.median(numeric_only=True)
    filled = transformed.fillna(medians).fillna(0.0)
    lower = filled.loc[train_mask].quantile(NUMERIC_WINSOR_LOWER_Q, numeric_only=True)
    upper = filled.loc[train_mask].quantile(NUMERIC_WINSOR_UPPER_Q, numeric_only=True)
    clipped = filled.clip(lower=lower, upper=upper, axis=1)
    means = clipped.loc[train_mask].mean(numeric_only=True)
    stds = clipped.loc[train_mask].std(ddof=0, numeric_only=True).replace(0.0, 1.0).fillna(1.0)
    scaled = ((clipped - means) / stds).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return scaled, {
        "numeric_columns": list(numeric.columns),
        "log1p_columns": log_cols,
        "imputation": "train_median_then_zero",
        "winsor_quantiles": [NUMERIC_WINSOR_LOWER_Q, NUMERIC_WINSOR_UPPER_Q],
        "scaler": "train_zscore",
    }


def build_categorical_matrix(
    events: pd.DataFrame,
    categorical_cols: list[str],
    train_mask: pd.Series,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not categorical_cols:
        return pd.DataFrame(index=events.index), {"categorical_columns": [], "vocabulary": {}}
    out = pd.DataFrame(index=events.index)
    vocabulary: dict[str, list[str]] = {}
    for col in categorical_cols:
        values = events[col].fillna("missing").astype(str)
        train_values = sorted(set(values.loc[train_mask]))
        vocabulary[col] = train_values
        for value in train_values:
            out[f"{col}_{value}"] = values.eq(value).astype(float)
    return out, {
        "categorical_columns": categorical_cols,
        "vocabulary": vocabulary,
        "unknown_category_policy": "all_zero",
    }


def feature_input_columns(events: pd.DataFrame) -> list[str]:
    cols = [col for col in EVENT_FEATURE_COLUMNS if col in events.columns]
    cols += [f"panel_{col}" for col in PANEL_FEATURE_COLUMNS if f"panel_{col}" in events.columns]
    cols += [col for col in CATEGORICAL_FEATURE_COLUMNS if col in events.columns]
    return cols


def feature_missing_coverage(events: pd.DataFrame, mask: pd.Series) -> float:
    cols = feature_input_columns(events)
    if not cols or not bool(mask.any()):
        return np.nan
    missing_rate = events.loc[mask, cols].isna().mean().mean()
    return float(1.0 - missing_rate)


def fit_models(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    score_frames: list[pd.DataFrame] = []
    model_rows: list[dict[str, Any]] = []
    oos_rows: list[dict[str, Any]] = []
    for source_pool, group in events.groupby("source_pool", dropna=False):
        group = group.reset_index(drop=True)
        train_mask = group["event_split"].astype(str).eq("train") & group["horizon_complete"]
        matrix, feature_columns, preprocessing = build_design_matrix(group, train_mask)
        for model_id, target_col in MODEL_SPECS:
            y_train = group.loc[train_mask, target_col].astype(int)
            status = "trained"
            if len(y_train) < 30 or y_train.nunique() < 2:
                status = "blocked_insufficient_train_label_variation"
                scores = np.full(len(group), np.nan)
            else:
                model = LogisticRegression(max_iter=1000, class_weight="balanced", C=0.5)
                model.fit(matrix.loc[train_mask], y_train)
                scores = model.predict_proba(matrix)[:, 1]
            score = group[
                [
                    "source_pool",
                    "event_id",
                    "canonical_event_id",
                    "instrument",
                    "event_t0_date",
                    "event_split",
                    "event_regime_bucket",
                    "board_bucket",
                    "primary_family_id",
                    "horizon_complete",
                    "fast_fail_bad_10d",
                    "false_repair_bad_20d",
                    "cost_bad_10_20",
                ]
            ].copy()
            score["model_id"] = model_id
            score["target_label"] = target_col
            score["cost_bad_score"] = scores
            score_frames.append(score)
            model_rows.append(
                {
                    "model_id": model_id,
                    "source_pool": source_pool,
                    "target_label": target_col,
                    "model_type": "logistic_regression_balanced_l2",
                    "model_status": status,
                    "train_sample_n": int(train_mask.sum()),
                    "train_positive_n": int(y_train.sum()) if len(y_train) else 0,
                    "feature_count": len(feature_columns),
                    "feature_columns_hash": stable_hash(feature_columns),
                    "feature_preprocessing_policy": FEATURE_PREPROCESSING_POLICY,
                    "feature_preprocessing_hash": stable_hash(preprocessing),
                }
            )
            for split in SPLITS:
                split_mask = group["event_split"].astype(str).eq(split) & group["horizon_complete"]
                y = group.loc[split_mask, target_col].astype(int)
                s = pd.Series(scores, index=group.index).loc[split_mask]
                oos_rows.append(
                    separability_row(
                        model_id,
                        str(source_pool),
                        target_col,
                        split,
                        y,
                        s,
                        feature_missing_coverage(group, split_mask),
                    )
                )
    return (
        pd.concat(score_frames, ignore_index=True, sort=False),
        pd.DataFrame(model_rows),
        pd.DataFrame(oos_rows),
    )


def separability_row(
    model_id: str,
    source_pool: str,
    target: str,
    split: str,
    y: pd.Series,
    score: pd.Series,
    feature_coverage: float = np.nan,
) -> dict[str, Any]:
    y = y.astype(int)
    score = pd.to_numeric(score, errors="coerce")
    valid = score.notna()
    y = y.loc[valid]
    score = score.loc[valid]
    prevalence = float(y.mean()) if len(y) else np.nan
    auc = np.nan
    pr_auc = np.nan
    brier = np.nan
    top_lift = np.nan
    bottom_rate = np.nan
    monotonicity = "insufficient_bins"
    if len(y) and y.nunique() == 2:
        auc = float(roc_auc_score(y, score))
        pr_auc = float(average_precision_score(y, score))
        brier = float(brier_score_loss(y, score.clip(0, 1)))
    if len(y) >= 10 and pd.notna(prevalence) and prevalence > 0:
        top_n = max(int(np.ceil(len(y) * 0.1)), 1)
        ordered = pd.DataFrame({"y": y, "score": score}).sort_values("score", ascending=False)
        top_lift = float(ordered.head(top_n)["y"].mean() / prevalence)
        bottom_rate = float(ordered.tail(top_n)["y"].mean())
        monotonicity = score_monotonicity_by_decile(y, score)
    return {
        "model_id": model_id,
        "source_pool": source_pool,
        "target_label": target,
        "split": split,
        "sample_n": int(len(y)),
        "positive_n": int(y.sum()) if len(y) else 0,
        "label_prevalence": prevalence,
        "roc_auc": auc,
        "pr_auc": pr_auc,
        "top_decile_lift": top_lift,
        "bottom_decile_cost_bad_rate": bottom_rate,
        "brier_score": brier,
        "score_monotonicity_by_decile": monotonicity,
        "feature_missing_coverage": feature_coverage,
        "oos_separability_status": "pass" if pd.notna(auc) and auc >= 0.5 else "diagnostic_or_reversed",
    }


def score_monotonicity_by_decile(y: pd.Series, score: pd.Series) -> str:
    frame = pd.DataFrame({"y": y.astype(float), "score": score.astype(float)}).dropna()
    if len(frame) < 20 or frame["score"].nunique() < 3:
        return "insufficient_bins"
    try:
        frame["decile"] = pd.qcut(frame["score"], q=min(10, frame["score"].nunique()), labels=False, duplicates="drop")
    except ValueError:
        return "insufficient_bins"
    means = frame.groupby("decile")["y"].mean().dropna()
    if len(means) < 3:
        return "insufficient_bins"
    corr = means.reset_index()["decile"].corr(means.reset_index()["y"], method="spearman")
    if pd.isna(corr):
        return "insufficient_bins"
    return "monotone_increasing" if corr >= 0.60 else "weak_or_non_monotone"


def cost_rates_for_events(events: pd.DataFrame) -> dict[str, Any]:
    complete = events.loc[events["horizon_complete"]].copy()
    return {
        "event_n": int(len(events)),
        "horizon_complete_event_n": int(len(complete)),
        "horizon_complete_event_rate": safe_div(len(complete), len(events)),
        "fast_fail_bad_10d_n": int(complete["fast_fail_bad_10d"].sum()) if len(complete) else 0,
        "fast_fail_bad_10d_rate": safe_div(int(complete["fast_fail_bad_10d"].sum()), len(complete)) if len(complete) else np.nan,
        "false_repair_bad_20d_n": int(complete["false_repair_bad_20d"].sum()) if len(complete) else 0,
        "false_repair_bad_20d_rate": safe_div(int(complete["false_repair_bad_20d"].sum()), len(complete)) if len(complete) else np.nan,
        "cost_bad_10_20_n": int(complete["cost_bad_10_20"].sum()) if len(complete) else 0,
        "cost_bad_10_20_rate": safe_div(int(complete["cost_bad_10_20"].sum()), len(complete)) if len(complete) else np.nan,
    }


def build_threshold_frontier(
    events: pd.DataFrame,
    scores: pd.DataFrame,
    membership: pd.DataFrame,
    d_scope: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frontier_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    for (source_pool, model_id), score_group in scores.groupby(["source_pool", "model_id"], dropna=False):
        source_events = events.loc[events["source_pool"].astype(str).eq(str(source_pool))].copy()
        event_meta = source_events.set_index("event_id", drop=False)
        train_scores = score_group.loc[
            score_group["event_split"].astype(str).eq("train")
            & score_group["horizon_complete"]
            & score_group["cost_bad_score"].notna()
        ]["cost_bad_score"]
        if train_scores.empty:
            continue
        for keep_frac in KEEP_FRACTIONS:
            threshold = float(train_scores.quantile(keep_frac))
            threshold_id = f"{model_id}__{source_pool}__keep_{int(keep_frac * 100):03d}"
            selected_ids = set(score_group.loc[score_group["cost_bad_score"] <= threshold, "event_id"].astype(str))
            metrics = threshold_metrics(
                source_pool=str(source_pool),
                model_id=str(model_id),
                threshold_id=threshold_id,
                threshold_value=threshold,
                keep_fraction=keep_frac,
                source_events=source_events,
                selected_ids=selected_ids,
                membership=membership,
                d_scope=d_scope,
            )
            frontier_rows.append(metrics)
        # selection is made after all candidate threshold rows exist
        source_frontier = [row for row in frontier_rows if row["source_pool"] == str(source_pool) and row["model_id"] == str(model_id)]
        selected = choose_threshold(source_frontier)
        if selected:
            selected_rows.append(selected)
            ids = set(score_group.loc[score_group["cost_bad_score"] <= selected["threshold_value"], "event_id"].astype(str))
            flag = source_events["event_id"].astype(str).isin(ids)
            for selected_flag, frame in ((True, source_events.loc[flag]), (False, source_events.loc[~flag])):
                tmp = frame[["source_pool", "event_id", "canonical_event_id", "instrument", "event_t0_date", "event_split", "event_regime_bucket"]].copy()
                tmp["model_id"] = model_id
                tmp["threshold_id"] = selected["threshold_id"]
                tmp["selected_flag"] = selected_flag
                tmp["cost_bad_score"] = tmp["event_id"].map(score_group.drop_duplicates("event_id").set_index("event_id")["cost_bad_score"])
                selected_rows.extend([])  # keep mypy quiet in old Python parsers
    return pd.DataFrame(frontier_rows), pd.DataFrame([row for row in selected_rows if "threshold_id" in row])


def choose_threshold(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    frame = pd.DataFrame(rows).copy()
    eligible = frame.loc[
        (frame["train_any_recall_retention"] >= 0.90)
        & (frame["train_e1_missed_capture_retention"] >= 0.85)
        & frame["after_train_horizon_complete_event_n"].gt(0)
    ].copy()
    if eligible.empty:
        eligible = frame.copy()
    return eligible.sort_values(
        ["train_cost_reduction_relative", "keep_fraction"],
        ascending=[False, False],
    ).iloc[0].to_dict()


def threshold_metrics(
    source_pool: str,
    model_id: str,
    threshold_id: str,
    threshold_value: float,
    keep_fraction: float,
    source_events: pd.DataFrame,
    selected_ids: set[str],
    membership: pd.DataFrame,
    d_scope: pd.DataFrame,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source_pool": source_pool,
        "model_id": model_id,
        "threshold_id": threshold_id,
        "threshold_value": threshold_value,
        "keep_fraction": keep_fraction,
    }
    for split in ("train", "robustness", "validation"):
        split_events = source_events.loc[source_events["event_split"].astype(str).eq(split)]
        selected = split_events.loc[split_events["event_id"].astype(str).isin(selected_ids)]
        selected_policy_ids = selected_ids_for_replay_policy(split_events, selected_ids)
        before = cost_rates_for_events(split_events)
        after = cost_rates_for_events(selected)
        retention = retention_metrics(source_pool, selected_policy_ids, split, membership, d_scope)
        row.update(
            {
                f"before_{split}_horizon_complete_event_n": before["horizon_complete_event_n"],
                f"after_{split}_horizon_complete_event_n": after["horizon_complete_event_n"],
                f"{split}_reject_rate": 1 - safe_div(len(selected), len(split_events)),
                f"{split}_horizon_complete_event_rate_before": before["horizon_complete_event_rate"],
                f"{split}_horizon_complete_event_rate_after": after["horizon_complete_event_rate"],
                f"{split}_fast_fail_bad_10d_n_before": before["fast_fail_bad_10d_n"],
                f"{split}_fast_fail_bad_10d_n_after": after["fast_fail_bad_10d_n"],
                f"{split}_cost_bad_rate_before": before["cost_bad_10_20_rate"],
                f"{split}_cost_bad_rate_after": after["cost_bad_10_20_rate"],
                f"{split}_cost_reduction_relative": relative_reduction(before["cost_bad_10_20_rate"], after["cost_bad_10_20_rate"]),
                f"{split}_fast_fail_rate_before": before["fast_fail_bad_10d_rate"],
                f"{split}_fast_fail_rate_after": after["fast_fail_bad_10d_rate"],
                f"{split}_false_repair_bad_20d_n_before": before["false_repair_bad_20d_n"],
                f"{split}_false_repair_bad_20d_n_after": after["false_repair_bad_20d_n"],
                f"{split}_false_repair_rate_before": before["false_repair_bad_20d_rate"],
                f"{split}_false_repair_rate_after": after["false_repair_bad_20d_rate"],
                f"{split}_cost_bad_10_20_n_before": before["cost_bad_10_20_n"],
                f"{split}_cost_bad_10_20_n_after": after["cost_bad_10_20_n"],
                f"{split}_any_recall_retention": retention["any_recall_retention"],
                f"{split}_bridge_recall_retention": retention["bridge_recall_retention"],
                f"{split}_e1_missed_capture_retention": retention["e1_missed_capture_retention"],
                f"{split}_post_filter_e1_missed_captured_episode_n": retention["post_filter_e1_missed_captured_episode_n"],
                f"{split}_post_filter_incremental_capture_over_e1_n": retention["post_filter_e1_missed_captured_episode_n"],
            }
        )
    row["selected_model_threshold_flag"] = False
    row["density_readout_status"] = "selected_threshold_only"
    row["candidate_tier"] = "research_entry"
    return row


def relative_reduction(before: float, after: float) -> float:
    if pd.isna(before) or before == 0 or pd.isna(after):
        return np.nan
    return (before - after) / before


def retention_metrics(
    source_pool: str,
    selected_ids: set[str],
    split: str,
    membership: pd.DataFrame,
    d_scope: pd.DataFrame,
) -> dict[str, Any]:
    base_row = d_scope.loc[
        d_scope["candidate_scope_id"].astype(str).eq(source_pool)
        & d_scope["split"].astype(str).eq(split)
        & d_scope["market_regime_bucket"].astype(str).eq(TARGET_REGIME)
        & d_scope["window"].astype(str).eq(HEADLINE_WINDOW)
        & d_scope["replay_policy_id"].astype(str).eq(HEADLINE_POLICY)
    ]
    if base_row.empty:
        return {
            "any_recall_retention": np.nan,
            "bridge_recall_retention": np.nan,
            "e1_missed_capture_retention": np.nan,
            "post_filter_e1_missed_captured_episode_n": 0,
        }
    base = base_row.iloc[0]
    mem = split_aligned_membership(membership, source_pool, split)
    selected_mem = mem.loc[mem["event_id"].astype(str).isin(selected_ids)]
    e1_mem = split_aligned_membership(membership, "07_E1_only", split)
    e1_captured = set(e1_mem["target_episode_id"].dropna().astype(str))
    selected_episodes = set(selected_mem["target_episode_id"].dropna().astype(str))
    selected_bridge = set(
        selected_mem.loc[
            bool_series(selected_mem, "bridge_positive_denominator_included")
            & bool_series(selected_mem, "event_big_winner_120d_label"),
            "target_episode_id",
        ].dropna().astype(str)
    )
    e1_missed_selected = selected_episodes.difference(e1_captured)
    return {
        "any_recall_retention": safe_div(len(selected_episodes), base.get("post_replay_any_captured_episode_n", np.nan)),
        "bridge_recall_retention": safe_div(len(selected_bridge), base.get("post_replay_bridge_captured_episode_n", np.nan)),
        "e1_missed_capture_retention": safe_div(len(e1_missed_selected), base.get("e1_missed_post_replay_capture_n", np.nan)),
        "post_filter_e1_missed_captured_episode_n": int(len(e1_missed_selected)),
    }


def split_aligned_membership(membership: pd.DataFrame, source_pool: str, split: str) -> pd.DataFrame:
    regime_col = "episode_market_regime_bucket" if "episode_market_regime_bucket" in membership.columns else "market_regime_bucket_episode"
    return membership.loc[
        membership["source_id"].astype(str).eq(source_pool)
        & membership["source_kind"].astype(str).eq("scope")
        & membership["window"].astype(str).eq(HEADLINE_WINDOW)
        & membership["event_split"].astype(str).eq(split)
        & membership["episode_split"].astype(str).eq(split)
        & membership[regime_col].astype(str).eq(TARGET_REGIME)
    ].copy()


def select_final_threshold(frontier: pd.DataFrame) -> dict[str, Any]:
    if frontier.empty:
        return {}
    preferred = frontier.loc[
        frontier["model_id"].eq("supervised_joint_cost_rejector")
        & frontier["source_pool"].eq("08_R_core_event_regime_gated")
    ].copy()
    if preferred.empty:
        preferred = frontier.copy()
    eligible = preferred.loc[
        preferred["train_any_recall_retention"].ge(0.90)
        & preferred["train_e1_missed_capture_retention"].ge(0.85)
    ].copy()
    if eligible.empty:
        eligible = preferred.copy()
    return eligible.sort_values(
        ["train_cost_reduction_relative", "keep_fraction"],
        ascending=[False, False],
    ).iloc[0].to_dict()


def build_selected_event_tables(events: pd.DataFrame, scores: pd.DataFrame, selected: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not selected:
        return pd.DataFrame(), pd.DataFrame()
    source_pool = str(selected["source_pool"])
    model_id = str(selected["model_id"])
    threshold = float(selected["threshold_value"])
    source_events = events.loc[events["source_pool"].astype(str).eq(source_pool)].copy()
    score_map = scores.loc[
        scores["source_pool"].astype(str).eq(source_pool) & scores["model_id"].astype(str).eq(model_id),
        ["event_id", "cost_bad_score"],
    ].drop_duplicates("event_id")
    source_events = source_events.merge(score_map, on="event_id", how="left")
    source_events["model_id"] = model_id
    source_events["threshold_id"] = str(selected["threshold_id"])
    keep = source_events["cost_bad_score"].le(threshold)
    cols = [
        "source_pool",
        "model_id",
        "threshold_id",
        "event_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "non_executable_next_open",
        "event_window_anchor_pos",
        "event_window_anchor_date",
        "event_window_anchor_status",
        "event_key",
        "replay_anchor_pos",
        "replay_anchor_date",
        "feature_as_of_date",
        "feature_lag_days",
        "feature_join_policy",
        "feature_source_hash",
        "daily_panel_feature_status",
        "event_split",
        "event_regime_bucket",
        "board_bucket",
        "primary_family_id",
        "family_id",
        "mechanism_cluster_id",
        "rank_score",
        "cost_bad_score",
        "fast_fail_bad_10d",
        "false_repair_bad_20d",
        "cost_bad_10_20",
        "horizon_complete",
    ]
    cols = [col for col in cols if col in source_events.columns]
    return source_events.loc[keep, cols].copy(), source_events.loc[~keep, cols].copy()


def build_cost_readout(events: pd.DataFrame, selected_events: pd.DataFrame, selected: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not selected:
        return pd.DataFrame()
    source_pool = str(selected["source_pool"])
    source_events = events.loc[events["source_pool"].astype(str).eq(source_pool)]
    selected_ids = set(selected_events["event_id"].astype(str))
    for split in SPLITS:
        raw = source_events.loc[source_events["event_split"].astype(str).eq(split)]
        sel = raw.loc[raw["event_id"].astype(str).isin(selected_ids)]
        before = cost_rates_for_events(raw)
        after = cost_rates_for_events(sel)
        rows.append(
            {
                "source_pool": source_pool,
                "model_id": selected["model_id"],
                "threshold_id": selected["threshold_id"],
                "split": split,
                "episode_regime_bucket": TARGET_REGIME,
                "selected_event_count": int(len(sel)),
                "rejected_event_count": int(len(raw) - len(sel)),
                "reject_rate": 1 - safe_div(len(sel), len(raw)),
                "before_horizon_complete_event_n": before["horizon_complete_event_n"],
                "after_horizon_complete_event_n": after["horizon_complete_event_n"],
                "horizon_complete_event_rate_before": before["horizon_complete_event_rate"],
                "horizon_complete_event_rate_after": after["horizon_complete_event_rate"],
                "fast_fail_bad_10d_n_before": before["fast_fail_bad_10d_n"],
                "fast_fail_bad_10d_n_after": after["fast_fail_bad_10d_n"],
                "fast_fail_bad_10d_rate_before": before["fast_fail_bad_10d_rate"],
                "fast_fail_bad_10d_rate_after": after["fast_fail_bad_10d_rate"],
                "false_repair_bad_20d_n_before": before["false_repair_bad_20d_n"],
                "false_repair_bad_20d_n_after": after["false_repair_bad_20d_n"],
                "false_repair_bad_20d_rate_before": before["false_repair_bad_20d_rate"],
                "false_repair_bad_20d_rate_after": after["false_repair_bad_20d_rate"],
                "cost_bad_10_20_n_before": before["cost_bad_10_20_n"],
                "cost_bad_10_20_n_after": after["cost_bad_10_20_n"],
                "cost_bad_10_20_rate_before": before["cost_bad_10_20_rate"],
                "cost_bad_10_20_rate_after": after["cost_bad_10_20_rate"],
                "cost_reduction_absolute_pp": 100 * (before["cost_bad_10_20_rate"] - after["cost_bad_10_20_rate"])
                if pd.notna(before["cost_bad_10_20_rate"]) and pd.notna(after["cost_bad_10_20_rate"])
                else np.nan,
                "cost_reduction_relative": relative_reduction(before["cost_bad_10_20_rate"], after["cost_bad_10_20_rate"]),
                "denominator_policy": "horizon_complete_events_only_same_source_split_regime",
            }
        )
    return pd.DataFrame(rows)


def build_retention_outputs(selected: dict[str, Any], selected_events: pd.DataFrame, membership: pd.DataFrame, d_scope: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    e1_rows: list[dict[str, Any]] = []
    if not selected:
        return pd.DataFrame(), pd.DataFrame()
    source_pool = str(selected["source_pool"])
    selected_ids = selected_ids_for_replay_policy(
        selected_events.loc[selected_events["source_pool"].astype(str).eq(source_pool)],
        set(selected_events["event_id"].astype(str)),
    )
    for split in SPLITS:
        selected_split_n = int(selected_events["event_split"].astype(str).eq(split).sum()) if "event_split" in selected_events.columns else 0
        metrics = retention_metrics(source_pool, selected_ids, split, membership, d_scope)
        base = d_scope.loc[
            d_scope["candidate_scope_id"].astype(str).eq(source_pool)
            & d_scope["split"].astype(str).eq(split)
            & d_scope["market_regime_bucket"].astype(str).eq(TARGET_REGIME)
            & d_scope["window"].astype(str).eq(HEADLINE_WINDOW)
            & d_scope["replay_policy_id"].astype(str).eq(HEADLINE_POLICY)
        ]
        base_row = base.iloc[0].to_dict() if not base.empty else {}
        rows.append(
            {
                "source_pool": source_pool,
                "model_id": selected["model_id"],
                "threshold_id": selected["threshold_id"],
                "split": split,
                "episode_regime_bucket": TARGET_REGIME,
                "window": HEADLINE_WINDOW,
                "replay_policy_id": HEADLINE_POLICY,
                "target_episode_denominator_n": base_row.get("target_episode_denominator_n", np.nan),
                "raw_post_replay_any_captured_episode_n": base_row.get("post_replay_any_captured_episode_n", np.nan),
                "post_filter_any_recall_retention": metrics["any_recall_retention"],
                "raw_post_replay_bridge_captured_episode_n": base_row.get("post_replay_bridge_captured_episode_n", np.nan),
                "post_filter_bridge_recall_retention": metrics["bridge_recall_retention"],
                "raw_e1_missed_capture_n": base_row.get("e1_missed_post_replay_capture_n", np.nan),
                "post_filter_e1_missed_captured_episode_n": metrics["post_filter_e1_missed_captured_episode_n"],
                "post_filter_e1_missed_capture_retention": metrics["e1_missed_capture_retention"],
                "post_filter_selected_event_count": selected_split_n,
                "filtered_event_count": max(int(base_row.get("selected_event_n", selected_split_n) or 0) - selected_split_n, 0),
                "replay_source_status": "post_replay_event_membership_materialized_split_aligned",
            }
        )
        e1_rows.append(
            {
                "source_pool": source_pool,
                "model_id": selected["model_id"],
                "threshold_id": selected["threshold_id"],
                "split": split,
                "episode_regime_bucket": TARGET_REGIME,
                "e1_missed_capture_n_definition": "post_filter_selected_events_actual_captured_e1_missed_episode_n",
                "post_filter_e1_missed_captured_episode_n": metrics["post_filter_e1_missed_captured_episode_n"],
                "e1_missed_capture_retention": metrics["e1_missed_capture_retention"],
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(e1_rows)


def build_density_readout(selected_events: pd.DataFrame, density_summary: pd.DataFrame, selected: dict[str, Any]) -> pd.DataFrame:
    if not selected:
        return pd.DataFrame()
    e1 = density_summary.loc[density_summary["candidate_scope_id"].astype(str).eq("07_E1_only")]
    instrument_years = float(e1.iloc[0].get("instrument_years", np.nan)) if not e1.empty else np.nan
    e1_density = float(e1.iloc[0].get("events_per_instrument_year_mean", np.nan)) if not e1.empty else np.nan
    events = selected_events.copy()
    if "event_key" not in events.columns:
        events["event_key"] = events["canonical_event_id"].fillna(events["event_id"]).astype(str)
    if "event_window_anchor_pos" not in events.columns:
        events = density_audit.with_event_window_anchor(events)
    metrics = density_audit.density_metrics_for_events(events, instrument_years=instrument_years)
    gaps = density_audit.adjacent_gaps(events)
    family_col = "primary_family_id" if "primary_family_id" in events.columns else "family_id"
    family_concentration = max_share(events[family_col]) if family_col in events.columns else np.nan
    board_concentration = max_share(events["board_bucket"]) if "board_bucket" in events.columns else np.nan
    return pd.DataFrame(
        [
            {
                "source_pool": selected["source_pool"],
                "model_id": selected["model_id"],
                "threshold_id": selected["threshold_id"],
                "selected_event_count": int(len(events)),
                "formal_event_day_density": metrics["events_per_instrument_year_mean"],
                "p95_density": metrics["events_per_instrument_year_p95"],
                "density_vs_e1": safe_div(metrics["events_per_instrument_year_mean"], e1_density),
                "rolling_10d_executable_event_day_density": metrics["rolling_10d_window_count_self_included_mean"],
                "rolling_20d_executable_event_day_density": metrics["rolling_20d_window_count_self_included_mean"],
                "rolling_10d_duplicate_rate": metrics["rolling_10d_duplicate_rate"],
                "rolling_20d_duplicate_rate": metrics["rolling_20d_duplicate_rate"],
                "adjacent_gap_p10": float(gaps.quantile(0.1)) if not gaps.empty and gaps.notna().any() else np.nan,
                "adjacent_gap_median": float(gaps.median()) if not gaps.empty and gaps.notna().any() else np.nan,
                "adjacent_gap_p90": float(gaps.quantile(0.9)) if not gaps.empty and gaps.notna().any() else np.nan,
                "family_concentration": family_concentration,
                "board_concentration": board_concentration,
                "density_readout_status": "auditable_no_predeclared_gate",
                "density_contract_source": "density_fast_fail_caliber_contract.md",
            }
        ]
    )


def max_share(series: pd.Series) -> float:
    denom = int(series.notna().sum())
    if denom == 0:
        return np.nan
    return float(series.dropna().astype(str).value_counts().iloc[0] / denom)


def build_split_alignment_audit(membership: pd.DataFrame) -> pd.DataFrame:
    frame = membership.copy()
    frame["split_aligned"] = frame["event_split"].astype(str).eq(frame["episode_split"].astype(str))
    return (
        frame.groupby(["source_id", "event_split", "episode_split", "split_aligned"], dropna=False)
        .size()
        .reset_index(name="membership_row_count")
    )


def build_event_regime_gate_audit(events: pd.DataFrame, membership: pd.DataFrame, d_scope: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for source_pool in SOURCE_POOLS:
        source_events = events.loc[events["source_pool"].astype(str).eq(source_pool)].copy()
        for split in SPLITS:
            split_events = source_events.loc[source_events["event_split"].astype(str).eq(split)].copy()
            risk_on_events = split_events.loc[split_events["event_regime_bucket"].astype(str).eq(TARGET_REGIME)].copy()
            for stage, frame in (("before_event_regime_gate", split_events), ("after_event_regime_gate", risk_on_events)):
                complete = frame.loc[frame["horizon_complete"]] if "horizon_complete" in frame.columns else frame.iloc[0:0]
                selected_ids = selected_ids_for_replay_policy(frame, set(frame["event_id"].astype(str))) if not frame.empty else set()
                retention = retention_metrics(source_pool, selected_ids, split, membership, d_scope)
                rows.append(
                    {
                        "source_pool": source_pool,
                        "split": split,
                        "gate_stage": stage,
                        "event_regime_bucket_filter": TARGET_REGIME if stage == "after_event_regime_gate" else "all",
                        "event_count": int(len(frame)),
                        "cost_label_complete_n": int(len(complete)),
                        "cost_label_complete_rate": safe_div(len(complete), len(frame)),
                        "fast_fail_bad_10d_rate": safe_div(int(complete["fast_fail_bad_10d"].sum()), len(complete)) if len(complete) else np.nan,
                        "false_repair_bad_20d_rate": safe_div(int(complete["false_repair_bad_20d"].sum()), len(complete)) if len(complete) else np.nan,
                        "cost_bad_10_20_rate": safe_div(int(complete["cost_bad_10_20"].sum()), len(complete)) if len(complete) else np.nan,
                        "post_replay_e1_missed_captured_episode_n": retention["post_filter_e1_missed_captured_episode_n"],
                        "post_replay_e1_missed_capture_retention": retention["e1_missed_capture_retention"],
                    }
                )
    return pd.DataFrame(rows)


def build_source_overlap_audit(events: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["canonical_event_id", "instrument", "event_t0_date"]
    available_keys = [col for col in key_cols if col in events.columns]
    if not available_keys or "source_pool" not in events.columns:
        return pd.DataFrame()
    grouped = (
        events.groupby(available_keys, dropna=False)
        .agg(
            source_pool_count=("source_pool", lambda s: int(s.astype(str).nunique())),
            source_pools=("source_pool", lambda s: ";".join(sorted(set(s.astype(str))))),
            event_row_count=("event_id", "size"),
        )
        .reset_index()
    )
    grouped["overlap_status"] = np.where(grouped["source_pool_count"].gt(1), "multi_source_overlap", "single_source")
    return grouped.loc[grouped["source_pool_count"].gt(1)].copy()


def enrich_input_audit_with_scope_bindings(
    input_frame: pd.DataFrame,
    scope_audit: pd.DataFrame,
) -> pd.DataFrame:
    rows = input_frame.copy()
    extra = scope_audit.copy()
    if extra.empty:
        return rows
    extra = extra.rename(columns={"source_pool": "input_id"})
    extra["path"] = ""
    extra["required"] = True
    extra["status"] = extra["scope_reconstruction_status"]
    extra["sha256"] = extra.get("source_hash", "")
    extra["row_count"] = extra.get("reconstructed_event_count", 0)
    return pd.concat([rows, extra], ignore_index=True, sort=False)


def build_binding_audit(d_manifest: dict[str, Any], d_scope: pd.DataFrame, reconciliation: pd.DataFrame) -> pd.DataFrame:
    c_rows = reconciliation.loc[reconciliation["source_experiment"].astype(str).eq("C")] if not reconciliation.empty else pd.DataFrame()
    c_pass_n = int(c_rows["reconciliation_status"].astype(str).eq("pass").sum()) if not c_rows.empty else 0
    c_total_n = int(len(c_rows))
    c_observed = f"{c_pass_n}/{c_total_n} pass" if c_total_n else "0/0 pass"
    rows: list[dict[str, Any]] = [
        ("D decision", d_manifest.get("decision"), "post_replay_retention_source_source_caveated_complete", "pass"),
        ("D local membership row count", d_manifest.get("local_raw_membership", {}).get("row_count"), 357450, "pass"),
        ("D episode window audit rows", d_manifest.get("output_row_counts", {}).get("post_replay_episode_window_audit"), 4986, "pass"),
        ("D entry_support_allowed", d_manifest.get("entry_support_allowed"), False, "pass"),
        ("D oracle_policies_audit_only", d_manifest.get("oracle_policies_audit_only"), True, "pass"),
        ("D C-arm reconciliation", c_observed, "189/189 pass", "pass" if c_pass_n == 189 and c_total_n == 189 else "drift"),
    ]
    for source, split, recall, e1_n, capture in [
        ("08_R_core_event_regime_gated", "train", 0.9822222222222222, 83, 80),
        ("08_R_core_event_regime_gated", "robustness", 0.9447513812154696, 92, 84),
        ("08_R6_event_regime_gated", "train", 0.96, 83, 77),
        ("08_R6_event_regime_gated", "robustness", 0.9005524861878453, 92, 77),
    ]:
        if {"candidate_scope_id", "split", "market_regime_bucket", "window", "replay_policy_id"}.issubset(d_scope.columns):
            row = d_scope.loc[
                d_scope["candidate_scope_id"].astype(str).eq(source)
                & d_scope["split"].astype(str).eq(split)
                & d_scope["market_regime_bucket"].astype(str).eq(TARGET_REGIME)
                & d_scope["window"].astype(str).eq(HEADLINE_WINDOW)
                & d_scope["replay_policy_id"].astype(str).eq(HEADLINE_POLICY)
            ]
        else:
            row = pd.DataFrame()
        actual_recall = float(row.iloc[0]["post_replay_any_recall"]) if not row.empty else np.nan
        actual_capture = int(row.iloc[0]["e1_missed_post_replay_capture_n"]) if not row.empty else -1
        rows.append((f"{source}:{split}:post_replay_any_recall", actual_recall, recall, "pass" if abs(actual_recall - recall) <= 0.0001 else "drift"))
        rows.append((f"{source}:{split}:e1_missed_capture", actual_capture, capture, "pass" if actual_capture == capture else "drift"))
    return pd.DataFrame(rows, columns=["binding_name", "observed_value", "expected_value", "binding_status"])


def build_oracle_gap_audit(d_policy: pd.DataFrame) -> pd.DataFrame:
    return d_policy.loc[
        d_policy["source_id"].astype(str).isin(SOURCE_POOLS)
        & d_policy["market_regime_bucket"].astype(str).eq(TARGET_REGIME)
        & d_policy["window"].astype(str).eq(HEADLINE_WINDOW)
    ].copy()


def build_leakage_audit(asof_meta: dict[str, Any]) -> pd.DataFrame:
    rows = [
        ("failure_10_label", False, True, True, "supervised_label_only", "pass"),
        ("event_false_repair_20d_label", False, True, True, "supervised_label_only", "pass"),
        ("target_episode_id", False, False, True, "post_replay_readout_only", "pass"),
        ("feature_as_of_date", False, False, False, "asof_join_audit", "pass" if asof_meta.get("future_join_row_count", 0) == 0 else "fail"),
    ]
    return pd.DataFrame(rows, columns=["field_name", "allowed_as_t0_feature", "allowed_as_label", "uses_future_information", "allowed_downstream_use", "leakage_status"])


def decision_from_selected(
    selected: dict[str, Any],
    source_caveated: bool,
    *,
    research_density_gate_configured: bool = False,
    oos: pd.DataFrame | None = None,
    feature_contract: pd.DataFrame | None = None,
    density_readout: pd.DataFrame | None = None,
) -> tuple[str, list[str]]:
    if not selected:
        return FINAL_DIAGNOSTIC, ["no_selected_threshold"]
    failures: list[str] = []
    robust_cost = selected.get("robustness_cost_reduction_relative", np.nan)
    train_cost = selected.get("train_cost_reduction_relative", np.nan)
    oos_status = selected_oos_status(selected, oos)
    feature_coverage_ok = selected_feature_coverage_ok(feature_contract)
    density_auditable = density_readout is not None and not density_readout.empty
    if not (pd.notna(train_cost) and train_cost >= 0.15 and pd.notna(robust_cost) and robust_cost >= 0.15):
        failures.append("cost_reduction_lt_15pct")
    if not research_density_gate_configured:
        failures.append("density_gate_not_configured")
    if not feature_coverage_ok:
        failures.append("feature_coverage_lt_95pct")
    if not oos_status["research_oos_pass"]:
        failures.append("research_oos_separability_gate_failed")
    if not rates_not_worse(selected, "train") or not rates_not_worse(selected, "robustness"):
        failures.append("fast_fail_or_false_repair_worse_than_raw")
    if not density_auditable:
        failures.append("density_readout_not_auditable")
    if selected.get("train_any_recall_retention", 0) < 0.90 or selected.get("robustness_any_recall_retention", 0) < 0.80:
        failures.append("any_recall_retention_gate_failed")
    if selected.get("train_e1_missed_capture_retention", 0) < 0.85 or selected.get("robustness_e1_missed_capture_retention", 0) < 0.75:
        failures.append("e1_missed_retention_gate_failed")
    if selected.get("robustness_post_filter_e1_missed_captured_episode_n", 0) < 60:
        failures.append("robustness_post_filter_e1_missed_capture_n_lt_60")
    if not failures:
        return (FINAL_RESEARCH_CAVEATED if source_caveated else FINAL_RESEARCH), []
    feature_failures = []
    train_not_worse = pd.notna(train_cost) and train_cost >= 0
    robust_not_worse = pd.notna(robust_cost) and robust_cost >= 0
    feature_cost_pass = (
        (pd.notna(train_cost) and train_cost >= 0.10 and robust_not_worse)
        or (pd.notna(robust_cost) and robust_cost >= 0.10 and train_not_worse)
    )
    if not feature_cost_pass:
        feature_failures.append("feature_cost_reduction_lt_10pct_or_other_split_worse")
    if not oos_status["feature_oos_pass"]:
        feature_failures.append("feature_oos_separability_gate_failed")
    if selected.get("robustness_any_recall_retention", 0) < 0.70:
        feature_failures.append("feature_any_recall_retention_failed")
    if selected.get("robustness_e1_missed_capture_retention", 0) < 0.60:
        feature_failures.append("feature_e1_missed_retention_failed")
    if selected.get("robustness_post_filter_e1_missed_captured_episode_n", 0) <= 0:
        feature_failures.append("feature_incremental_capture_over_e1_not_positive")
    if not density_auditable:
        feature_failures.append("feature_density_readout_not_auditable")
    if not feature_failures:
        return (FINAL_FEATURE_CAVEATED if source_caveated else FINAL_FEATURE), failures
    return FINAL_DIAGNOSTIC, sorted(set(failures + feature_failures))


def rates_not_worse(selected: dict[str, Any], split: str) -> bool:
    for prefix in ("fast_fail", "false_repair"):
        before = selected.get(f"{split}_{prefix}_rate_before", np.nan)
        after = selected.get(f"{split}_{prefix}_rate_after", np.nan)
        if pd.isna(before) or pd.isna(after) or after > before:
            return False
    return True


def selected_oos_status(selected: dict[str, Any], oos: pd.DataFrame | None) -> dict[str, bool]:
    if oos is None or oos.empty or not selected:
        return {"research_oos_pass": False, "feature_oos_pass": False}
    row = oos.loc[
        oos["source_pool"].astype(str).eq(str(selected.get("source_pool", "")))
        & oos["model_id"].astype(str).eq(str(selected.get("model_id", "")))
        & oos["target_label"].astype(str).eq("cost_bad_10_20")
        & oos["split"].astype(str).eq("robustness")
    ]
    if row.empty:
        return {"research_oos_pass": False, "feature_oos_pass": False}
    item = row.iloc[0]
    auc = float(item.get("roc_auc", np.nan))
    pr_auc = float(item.get("pr_auc", np.nan))
    prevalence = float(item.get("label_prevalence", np.nan))
    top_lift = float(item.get("top_decile_lift", np.nan))
    research = pd.notna(auc) and auc >= 0.55 and pd.notna(pr_auc) and pd.notna(prevalence) and pr_auc > prevalence
    feature = (pd.notna(auc) and auc >= 0.52) or (pd.notna(top_lift) and top_lift > 1.0)
    return {"research_oos_pass": bool(research), "feature_oos_pass": bool(feature)}


def selected_feature_coverage_ok(feature_contract: pd.DataFrame | None) -> bool:
    if feature_contract is None or feature_contract.empty:
        return False
    allowed = feature_contract.loc[bool_series(feature_contract, "allowed_as_t0_feature")]
    if allowed.empty:
        return False
    train_missing = pd.to_numeric(allowed["missing_rate_train"], errors="coerce").fillna(0)
    robust_missing = pd.to_numeric(allowed["missing_rate_robustness"], errors="coerce").fillna(0)
    return bool(train_missing.le(0.05).all() and robust_missing.le(0.05).all())


def build_decision_tiers(selected: dict[str, Any], final_decision: str, failures: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_tier": "research_entry",
                "selected_model_id": selected.get("model_id", ""),
                "selected_threshold_id": selected.get("threshold_id", ""),
                "selected_source_pool": selected.get("source_pool", ""),
                "final_decision": final_decision,
                "selected_model_threshold_flag": bool(selected),
                "failure_reason": ";".join(failures),
                "supported_usage": "research_entry" if "research_entry" in final_decision else ("feature_source" if "feature_source" in final_decision else "diagnostic_only"),
            }
        ]
    )


def build_training_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (source_pool, split), group in events.groupby(["source_pool", "event_split"], dropna=False):
        complete = group.loc[group["horizon_complete"]]
        rows.append(
            {
                "source_pool": source_pool,
                "split": split,
                "event_n": int(len(group)),
                "cost_label_complete_n": int(len(complete)),
                "cost_label_complete_rate": safe_div(len(complete), len(group)),
                "fast_fail_bad_10d_rate": safe_div(int(complete["fast_fail_bad_10d"].sum()), len(complete)) if len(complete) else np.nan,
                "false_repair_bad_20d_rate": safe_div(int(complete["false_repair_bad_20d"].sum()), len(complete)) if len(complete) else np.nan,
                "cost_bad_10_20_rate": safe_div(int(complete["cost_bad_10_20"].sum()), len(complete)) if len(complete) else np.nan,
                "daily_panel_joined_rate": safe_div(int(group["daily_panel_feature_status"].eq("asof_feature_joined").sum()), len(group)),
            }
        )
    return pd.DataFrame(rows)


def build_report(
    final_decision: str,
    selected: dict[str, Any],
    failures: list[str],
    frames: dict[str, pd.DataFrame],
    manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> str:
    a, b, c, d = manifests
    lines = [
        "# Experiment E - Risk-on Post-Filter Cost Rejector 报告",
        "",
        f"最终决策：`{final_decision}`",
        "",
        "## 结论",
        "",
        "E 按 D 的 post-replay membership 与 event-level label source 训练 risk_on 成本 rejector。"
        "本轮不继续 C 的 entry-ranker / compression 主线；R-core / R6 被视为 recall source，"
        "核心问题是 fast-fail / false-repair 成本是否可在 t0 特征下被过滤。",
        "",
        f"- A decision: `{a.get('decision', '')}`",
        f"- B decision: `{b.get('decision', '')}`",
        f"- C decision: `{c.get('decision', '')}`",
        f"- D decision: `{d.get('decision', '')}`",
        "",
    ]
    if selected:
        lines.extend(
            [
                "## Selected Threshold",
                "",
                f"- source_pool: `{selected.get('source_pool')}`",
                f"- model_id: `{selected.get('model_id')}`",
                f"- threshold_id: `{selected.get('threshold_id')}`",
                f"- train cost reduction: `{selected.get('train_cost_reduction_relative'):.3f}`",
                f"- robustness cost reduction: `{selected.get('robustness_cost_reduction_relative'):.3f}`",
                f"- robustness E1-missed captured n: `{selected.get('robustness_post_filter_e1_missed_captured_episode_n')}`",
                "",
            ]
        )
    if failures:
        lines.extend(["## Gate Failures", "", *[f"- `{reason}`" for reason in failures], ""])
    selected_model = str(selected.get("model_id", "")) if selected else ""
    selected_source = str(selected.get("source_pool", "")) if selected else ""
    oos = frames.get("risk_on_cost_rejector_oos_separability", pd.DataFrame())
    if not oos.empty and selected:
        selected_oos = oos.loc[
            oos["model_id"].astype(str).eq(selected_model)
            & oos["source_pool"].astype(str).eq(selected_source)
            & oos["target_label"].astype(str).eq("cost_bad_10_20")
        ]
        lines.extend(["## OOS Separability", ""])
        for _, row in selected_oos.iterrows():
            lines.append(
                f"- {row['split']}: ROC-AUC `{row['roc_auc']:.3f}`, PR-AUC `{row['pr_auc']:.3f}`, "
                f"prevalence `{row['label_prevalence']:.3f}`, top-decile lift `{row['top_decile_lift']:.3f}`"
            )
        lines.append("")
    cost = frames.get("risk_on_cost_rejector_cost_readout", pd.DataFrame())
    retention = frames.get("risk_on_cost_rejector_post_filter_retention_by_split", pd.DataFrame())
    if not cost.empty:
        lines.extend(["## Cost Vs Retention", ""])
        for _, row in cost.iterrows():
            keep = retention.loc[retention["split"].astype(str).eq(str(row["split"]))] if not retention.empty else pd.DataFrame()
            e1_ret = keep.iloc[0].get("post_filter_e1_missed_capture_retention", np.nan) if not keep.empty else np.nan
            lines.append(
                f"- {row['split']}: cost reduction `{row['cost_reduction_relative']:.3f}`, "
                f"reject rate `{row['reject_rate']:.3f}`, E1-missed retention `{e1_ret:.3f}`"
            )
        lines.append("")
    density = frames.get("risk_on_cost_rejector_density_readout", pd.DataFrame())
    if not density.empty:
        row = density.iloc[0]
        lines.extend(
            [
                "## Density / Concentration",
                "",
                f"- formal density: `{row.get('formal_event_day_density', np.nan):.3f}`",
                f"- p95 density: `{row.get('p95_density', np.nan):.3f}`",
                f"- family concentration: `{row.get('family_concentration', np.nan):.3f}`",
                f"- board concentration: `{row.get('board_concentration', np.nan):.3f}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Artifact Row Counts",
            "",
            *[f"- `{key}`: {len(frame):,}" for key, frame in frames.items()],
            "",
            "## 不可声称内容",
            "",
            "- 本结果不是可部署交易策略。",
            "- D 仍是 source-caveated 时，E 只能作为 research admission / feature-source 证据。",
            "- oracle replay 只用于 gap audit，不得作为 t0 entry/rejector。",
            "",
        ]
    )
    return "\n".join(lines)


def build_contract() -> str:
    return "\n".join(
        [
            "# Risk-on Post-Filter Cost Rejector Contract",
            "",
            "- Scope reconstruction uses A `candidate_scope_mapping_contract.csv` and `source_row_count` bindings.",
            "- R-core accepted published-reference difference: source row count 47914 vs published reference 47929.",
            "- D summary `market_regime_bucket` is episode-side; D membership `market_regime_bucket` is event-side.",
            "- Daily panel features join by `instrument` and latest `date <= event_t0_date` only.",
            "- Labels join by `event_id + label_scope`; D membership labels reconcile against event-level labels.",
            "- Final gates read from one selected `(model_id, threshold_id)`.",
            "- Cost before/after denominators are horizon-complete events in the same source/split/regime cell.",
            "",
        ]
    )


def build_manifest(
    final_decision: str,
    failures: list[str],
    frames: dict[str, pd.DataFrame],
    paths: dict[str, Path],
    input_paths: dict[str, Path],
    selected: dict[str, Any],
    manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    asof_meta: dict[str, Any],
) -> dict[str, Any]:
    a, b, c, d = manifests
    return {
        "experiment_id": "08_experiment_e_risk_on_post_filter_cost_rejector",
        "run_id": stable_hash({"experiment": "risk_on_post_filter_cost_rejector", "created_at": datetime.now(timezone.utc).isoformat()}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision": final_decision,
        "blocked_reasons": failures,
        "experiment_a_decision": a.get("decision", ""),
        "experiment_b_decision": b.get("decision", ""),
        "experiment_c_decision": c.get("decision", ""),
        "experiment_d_decision": d.get("decision", ""),
        "entry_support_allowed": False,
        "source_caveated": any("source_caveated" in str(m.get("decision", "")) or "partial" in str(m.get("decision", "")) for m in manifests),
        "selected_model_id": selected.get("model_id", ""),
        "selected_threshold_id": selected.get("threshold_id", ""),
        "selected_source_pool": selected.get("source_pool", ""),
        "selected_candidate_tier": "research_entry" if selected else "",
        "feature_asof_join": asof_meta,
        "feature_asof_join_code_hash": path_hash(Path(__file__)),
        "feature_asof_missing_policy": "leave_missing_no_future_fill",
        "d_membership_hash": path_hash(input_paths.get("d_membership", Path(""))),
        "feature_source_hash": path_hash(input_paths.get("cross_section_feature_panel", Path(""))),
        "label_source_hash": path_hash(input_paths.get("candidate_family_event_labels", Path(""))),
        "regime_column_role_mapping_hash": stable_hash(regime_role_audit().to_dict(orient="records")),
        "label_join_policy": "event_id_plus_label_scope_with_membership_reconciliation",
        "label_reconciliation_status": frames.get("risk_on_cost_rejector_label_source_audit", pd.DataFrame()).to_dict(orient="records"),
        "scope_reconstruction_bindings": frames.get("risk_on_cost_rejector_scope_reconstruction_audit", pd.DataFrame()).to_dict(orient="records"),
        "input_artifacts": {key: {"path": str(path), "sha256": path_hash(path)} for key, path in sorted(input_paths.items())},
        "output_paths": {key: str(path) for key, path in sorted(paths.items())},
        "output_hashes": {key: path_hash(path) for key, path in sorted(paths.items()) if path.exists() and path.is_file() and key != "risk_on_post_filter_cost_rejector_manifest"},
        "output_row_counts": {key: int(len(frame)) for key, frame in frames.items()},
        "requirement_hash": path_hash(REQUIREMENT_PATH),
        "runner_code_hash": path_hash(Path(__file__)),
    }


def write_blocked(
    decision: str,
    failures: list[str],
    input_frame: pd.DataFrame,
    input_paths: dict[str, Path],
    manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> dict[str, Any]:
    paths = output_paths()
    empty = {
        "risk_on_cost_rejector_input_audit": input_frame,
        "risk_on_cost_rejector_binding_audit": pd.DataFrame(),
        "risk_on_cost_rejector_scope_reconstruction_audit": pd.DataFrame(),
        "risk_on_cost_rejector_split_alignment_audit": pd.DataFrame(),
        "risk_on_cost_rejector_regime_role_audit": pd.DataFrame(),
        "risk_on_cost_rejector_event_regime_gate_audit": pd.DataFrame(),
        "risk_on_cost_rejector_source_overlap_audit": pd.DataFrame(),
        "risk_on_cost_rejector_feature_contract": pd.DataFrame(),
        "risk_on_cost_rejector_label_source_audit": pd.DataFrame(),
        "risk_on_cost_rejector_training_sample_summary": pd.DataFrame(),
        "risk_on_cost_rejector_model_registry": pd.DataFrame(),
        "risk_on_cost_rejector_oos_separability": pd.DataFrame(),
        "risk_on_cost_rejector_threshold_frontier": pd.DataFrame(),
        "risk_on_cost_rejector_cost_readout": pd.DataFrame(),
        "risk_on_cost_rejector_post_filter_retention_by_split": pd.DataFrame(),
        "risk_on_cost_rejector_e1_missed_retention": pd.DataFrame(),
        "risk_on_cost_rejector_density_readout": pd.DataFrame(),
        "risk_on_cost_rejector_oracle_gap_audit": pd.DataFrame(),
        "risk_on_cost_rejector_leakage_audit": pd.DataFrame(),
        "risk_on_cost_rejector_decision_tiers": pd.DataFrame(),
    }
    for key, frame in empty.items():
        write_df(paths[key], frame)
    write_text(paths["risk_on_post_filter_cost_rejector_contract"], build_contract())
    write_text(paths["risk_on_post_filter_cost_rejector_report"], "# Experiment E blocked\n\n" + "\n".join(f"- {f}" for f in failures) + "\n")
    write_json(paths["risk_on_post_filter_cost_rejector_manifest"], build_manifest(decision, failures, empty, paths, input_paths, {}, manifests, {}))
    return {"decision": decision, "blocked_reasons": failures, "manifest_path": str(paths["risk_on_post_filter_cost_rejector_manifest"])}


def run_experiment() -> dict[str, Any]:
    ensure_dirs()
    input_frame, input_failures, input_paths = input_audit()
    manifests = validate_manifests()
    a_manifest, b_manifest, c_manifest, d_manifest, manifest_failures = manifests
    input_failures.extend(manifest_failures)
    manifest_tuple = (a_manifest, b_manifest, c_manifest, d_manifest)
    if input_failures:
        return write_blocked(FINAL_INPUT_BLOCKED, input_failures, input_frame, input_paths, manifest_tuple)

    canonical07 = read_csv(input_paths["07_canonical_events"])
    canonical08 = read_csv(input_paths["candidate_family_canonical_events"])
    labels = pd.read_parquet(input_paths["candidate_family_event_labels"])
    panel = pd.read_parquet(input_paths["cross_section_feature_panel"])
    membership = pd.read_parquet(input_paths["d_membership"])
    d_scope = read_csv(input_paths["d_scope_retention"])
    d_policy = read_csv(input_paths["d_policy_effect"])
    d_reconciliation = read_csv(input_paths["d_reconciliation"])
    mapping = read_csv(input_paths["candidate_scope_mapping_contract"])
    reconstruct = read_csv(input_paths["candidate_scope_reconstructability_audit"])
    density_summary = read_csv(input_paths["candidate_10d_density_summary"])
    binding_audit = build_binding_audit(d_manifest, d_scope, d_reconciliation)
    binding_failures = binding_audit.loc[
        ~binding_audit["binding_status"].astype(str).eq("pass"),
        "binding_name",
    ].astype(str).tolist()
    if binding_failures:
        return write_blocked(
            FINAL_BINDING_DRIFT_BLOCKED,
            [f"binding_drift:{failure}" for failure in binding_failures],
            input_frame,
            input_paths,
            manifest_tuple,
        )

    scope_events = {
        scope_id: reconstruct_scope_events(scope_id, canonical07, canonical08, mapping)
        for scope_id in AUDIT_SCOPES
    }
    scope_audit, scope_failures = build_scope_reconstruction_audit(scope_events, mapping, reconstruct)
    if scope_failures:
        return write_blocked(FINAL_SCOPE_DRIFT_BLOCKED, scope_failures, input_frame, input_paths, manifest_tuple)

    event_frames: list[pd.DataFrame] = []
    for source_pool in SOURCE_POOLS:
        frame = scope_events[source_pool].copy()
        if "primary_family_id" not in frame.columns:
            frame["primary_family_id"] = frame.get("family_id", frame.get("scope_family_id", "unknown"))
        event_frames.append(frame)
    all_events = pd.concat(event_frames, ignore_index=True, sort=False)
    all_events, label_audit, label_failures = join_event_labels(all_events, labels, membership)
    if any("duplicate_label_join_rows" in failure for failure in label_failures):
        return write_blocked(FINAL_LABEL_JOIN_BLOCKED, label_failures, input_frame, input_paths, manifest_tuple)
    if any("label_reconciliation_mismatch" in failure for failure in label_failures):
        return write_blocked(FINAL_LABEL_RECON_BLOCKED, label_failures, input_frame, input_paths, manifest_tuple)
    if label_audit.loc[label_audit["source_pool"].astype(str).isin(SOURCE_POOLS), "cost_label_complete_rate"].lt(0.95).all():
        return write_blocked(FINAL_LABEL_HORIZON_BLOCKED, ["R6_and_R_core_label_coverage_below_95pct"], input_frame, input_paths, manifest_tuple)
    event_regime_gate_audit = build_event_regime_gate_audit(all_events, membership, d_scope)
    source_overlap_audit = build_source_overlap_audit(all_events)
    events = all_events.loc[all_events["event_regime_bucket"].astype(str).eq(TARGET_REGIME)].copy()

    events, asof_meta = asof_join_panel(events, panel)
    events["feature_source_hash"] = path_hash(input_paths["cross_section_feature_panel"])
    if asof_meta.get("future_join_row_count", 0):
        return write_blocked(FINAL_LEAKAGE_BLOCKED, ["feature_as_of_date_after_event_t0_date"], input_frame, input_paths, manifest_tuple)

    scores, model_registry, oos = fit_models(events)
    frontier, _ = build_threshold_frontier(events, scores, membership, d_scope)
    selected = select_final_threshold(frontier)
    if selected:
        frontier.loc[frontier["threshold_id"].astype(str).eq(str(selected["threshold_id"])), "selected_model_threshold_flag"] = True
    selected_events, rejected_events = build_selected_event_tables(events, scores, selected)
    cost_readout = build_cost_readout(events, selected_events, selected)
    retention, e1_missed = build_retention_outputs(selected, selected_events, membership, d_scope)
    density_readout = build_density_readout(selected_events, density_summary, selected)
    oracle_gap = build_oracle_gap_audit(d_policy)
    leakage = build_leakage_audit(asof_meta)
    feature_contract = build_feature_contract(
        events,
        path_hash(input_paths["candidate_family_canonical_events"]),
        path_hash(input_paths["cross_section_feature_panel"]),
        asof_meta,
    )
    final_decision, gate_failures = decision_from_selected(
        selected,
        any("source_caveated" in str(m.get("decision", "")) or "partial" in str(m.get("decision", "")) for m in manifest_tuple),
        research_density_gate_configured=False,
        oos=oos,
        feature_contract=feature_contract,
        density_readout=density_readout,
    )
    decision_tiers = build_decision_tiers(selected, final_decision, gate_failures)
    top_failures = rejected_events.sort_values("cost_bad_score", ascending=False).head(100).copy() if not rejected_events.empty else pd.DataFrame()

    enriched_input_frame = enrich_input_audit_with_scope_bindings(input_frame, scope_audit)
    frames = {
        "risk_on_cost_rejector_input_audit": enriched_input_frame,
        "risk_on_cost_rejector_binding_audit": binding_audit,
        "risk_on_cost_rejector_scope_reconstruction_audit": scope_audit,
        "risk_on_cost_rejector_split_alignment_audit": build_split_alignment_audit(membership),
        "risk_on_cost_rejector_regime_role_audit": regime_role_audit(),
        "risk_on_cost_rejector_event_regime_gate_audit": event_regime_gate_audit,
        "risk_on_cost_rejector_source_overlap_audit": source_overlap_audit,
        "risk_on_cost_rejector_feature_contract": feature_contract,
        "risk_on_cost_rejector_label_source_audit": label_audit,
        "risk_on_cost_rejector_training_sample_summary": build_training_summary(events),
        "risk_on_cost_rejector_model_registry": model_registry,
        "risk_on_cost_rejector_oos_separability": oos,
        "risk_on_cost_rejector_threshold_frontier": frontier,
        "risk_on_cost_rejector_cost_readout": cost_readout,
        "risk_on_cost_rejector_post_filter_retention_by_split": retention,
        "risk_on_cost_rejector_e1_missed_retention": e1_missed,
        "risk_on_cost_rejector_density_readout": density_readout,
        "risk_on_cost_rejector_oracle_gap_audit": oracle_gap,
        "risk_on_cost_rejector_leakage_audit": leakage,
        "risk_on_cost_rejector_decision_tiers": decision_tiers,
    }
    paths = output_paths()
    for key, frame in frames.items():
        write_df(paths[key], frame)
    write_df(paths["risk_on_cost_rejector_event_scores"], scores)
    write_df(paths["risk_on_cost_rejector_selected_events"], selected_events)
    write_df(paths["risk_on_cost_rejector_rejected_events"], rejected_events)
    write_df(paths["risk_on_cost_rejector_top_failure_examples"], top_failures)
    write_text(paths["risk_on_post_filter_cost_rejector_contract"], build_contract())
    write_text(paths["risk_on_post_filter_cost_rejector_report"], build_report(final_decision, selected, gate_failures, frames, manifest_tuple))
    write_json(paths["risk_on_post_filter_cost_rejector_manifest"], build_manifest(final_decision, gate_failures, frames, paths, input_paths, selected, manifest_tuple, asof_meta))
    return {
        "decision": final_decision,
        "manifest_path": str(paths["risk_on_post_filter_cost_rejector_manifest"]),
        "report_path": str(paths["risk_on_post_filter_cost_rejector_report"]),
        "row_counts": {key: int(len(frame)) for key, frame in frames.items()},
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_dirs()
    if args.mode == "check-inputs":
        input_frame, failures, _ = input_audit()
        write_df(E_TABLE_DIR / "risk_on_cost_rejector_input_audit.csv", input_frame)
        for failure in failures:
            print(failure)
        print(f"input_failures={len(failures)}")
        return 1 if failures else 0
    result = run_experiment()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if "blocked" not in str(result.get("decision", "")) else 1


if __name__ == "__main__":
    raise SystemExit(main())

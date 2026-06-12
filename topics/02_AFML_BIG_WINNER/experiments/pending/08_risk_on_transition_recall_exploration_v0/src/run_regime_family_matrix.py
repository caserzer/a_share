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


PENDING_DIR = EXPERIMENT_DIR.parent
EXP07_DIR = PENDING_DIR / "07_topn_multichannel_repair_candidate_generator_v0"

REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_experiment_b_regime_family_matrix.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

AUDIT_TABLE_DIR = TABLE_DIR / "density_fast_fail_audit"
AUDIT_REPORT_DIR = REPORT_DIR / "density_fast_fail_audit"
AUDIT_MANIFEST_DIR = MANIFEST_DIR / "density_fast_fail_audit"

B_TABLE_DIR = TABLE_DIR / "regime_family_matrix"
B_REPORT_DIR = REPORT_DIR / "regime_family_matrix"
B_MANIFEST_DIR = MANIFEST_DIR / "regime_family_matrix"
B_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "regime_family_matrix"

BEFORE_FIRST_50 = "before_first_50pct"

DECISION_COMPLETE = "regime_family_matrix_complete"
DECISION_CONTRACT_BLOCKED = "regime_family_matrix_contract_blocked"
DECISION_INPUT_BLOCKED = "regime_family_matrix_input_blocked"
DECISION_WAITING = "regime_family_matrix_waiting_for_density_contract"
DECISION_SOURCE_CAVEATED = "regime_family_matrix_source_caveated_complete"
DECISION_TRANSITION_INCONCLUSIVE = "regime_family_matrix_transition_reselection_inconclusive"

A_DECISION_COMPLETE = "density_fast_fail_audit_complete"
A_DECISION_PARTIAL = "density_fast_fail_audit_partial_source_complete"
ALLOWED_A_DECISIONS = {A_DECISION_COMPLETE, A_DECISION_PARTIAL}

SAMPLE_ORDER = {
    "sufficient_for_cell_readout": 0,
    "low_power_caution": 1,
    "diagnostic_only": 2,
}

R_FAMILIES = [
    "R1_relative_strength_breakout",
    "R2_near_high_volume_expansion",
    "R6_market_breadth_thrust",
    "R7_cross_sectional_momentum_rank_jump",
    "R8_persistent_distance_above_ema",
]


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    paths: tuple[Path, ...]
    required_columns: tuple[str, ...] = ()
    required: bool = True


@dataclass(frozen=True)
class ScopeMeta:
    candidate_scope_id: str
    family_id: str
    candidate_scope_type: str
    mechanism_cluster: str
    source_kind: str
    reference_scope_id: str
    required_family: bool = True


def p(*parts: str) -> Path:
    return EXPERIMENT_DIR.joinpath(*parts)


INPUT_SPECS = [
    InputSpec("run_manifest", (EXPERIMENT_DIR / "outputs" / "manifests" / "run_manifest.json",)),
    InputSpec(
        "density_fast_fail_audit_manifest",
        (AUDIT_MANIFEST_DIR / "density_fast_fail_audit_manifest.json",),
    ),
    InputSpec(
        "density_fast_fail_caliber_contract",
        (AUDIT_REPORT_DIR / "density_fast_fail_caliber_contract.md",),
    ),
    InputSpec(
        "density_fast_fail_audit_report",
        (AUDIT_REPORT_DIR / "density_fast_fail_audit_report.md",),
    ),
    InputSpec(
        "density_fast_fail_audit_gate_summary",
        (AUDIT_TABLE_DIR / "density_fast_fail_audit_gate_summary.csv",),
        ("candidate_scope_id",),
    ),
    InputSpec(
        "candidate_scope_mapping_contract",
        (AUDIT_TABLE_DIR / "candidate_scope_mapping_contract.csv",),
        ("candidate_scope_id", "scope_mapping_status"),
    ),
    InputSpec(
        "candidate_scope_reconstructability_audit",
        (AUDIT_TABLE_DIR / "candidate_scope_reconstructability_audit.csv",),
        ("candidate_scope_id", "scope_status"),
    ),
    InputSpec(
        "candidate_density_caliber_crosswalk",
        (AUDIT_TABLE_DIR / "candidate_density_caliber_crosswalk.csv",),
        ("candidate_scope_id", "final_diagnostic_alert_status"),
    ),
    InputSpec(
        "candidate_10d_density_summary",
        (AUDIT_TABLE_DIR / "candidate_10d_density_summary.csv",),
        (
            "candidate_scope_id",
            "events_per_instrument_year_mean",
            "events_per_instrument_year_p95",
            "rolling_10d_duplicate_rate",
        ),
    ),
    InputSpec(
        "candidate_10d_uniqueness_diagnostic",
        (AUDIT_TABLE_DIR / "candidate_10d_uniqueness_diagnostic.csv",),
        (
            "candidate_scope_id",
            "event_split",
            "market_regime_bucket",
            "event_uniqueness_10d_p10",
            "concurrency_p95",
        ),
    ),
    InputSpec(
        "candidate_10d_fast_fail_readout",
        (AUDIT_TABLE_DIR / "candidate_10d_fast_fail_readout.csv",),
        (
            "candidate_scope_id",
            "event_split",
            "market_regime_bucket",
            "fast_fail_10d_count",
            "fast_fail_10d_rate",
            "false_repair_20d_count",
            "false_repair_20d_rate",
        ),
    ),
    InputSpec(
        "candidate_10d_retention_by_split_regime",
        (AUDIT_TABLE_DIR / "candidate_10d_retention_by_split_regime.csv",),
        (
            "candidate_scope_id",
            "episode_split",
            "market_regime_bucket",
            "target_episode_denominator",
            "pre_replay_any_recall",
            "pre_replay_bridge_recall",
            "retention_source_status",
        ),
    ),
    InputSpec(
        "candidate_adjacent_event_gap_diagnostic",
        (AUDIT_TABLE_DIR / "candidate_adjacent_event_gap_diagnostic.csv",),
        (
            "candidate_scope_id",
            "event_split",
            "market_regime_bucket",
            "adjacent_gap_median",
            "gap_lt_10d_rate",
        ),
    ),
    InputSpec(
        "candidate_10d_density_vs_episode_density_comparison",
        (AUDIT_TABLE_DIR / "candidate_10d_density_vs_episode_density_comparison.csv",),
        ("candidate_scope_id",),
    ),
    InputSpec(
        "candidate_family_event_instances",
        (
            TABLE_DIR / "candidate_family_event_instances.csv",
            TABLE_DIR / "candidate_family_event_instances.csv.gz",
        ),
        ("event_id", "instrument", "event_split", "market_regime_bucket"),
    ),
    InputSpec(
        "candidate_family_canonical_events",
        (
            TABLE_DIR / "candidate_family_canonical_events.csv",
            TABLE_DIR / "candidate_family_canonical_events.csv.gz",
        ),
        ("event_id", "instrument", "family_id", "variant_id"),
    ),
    InputSpec(
        "candidate_family_incremental_recall_over_e1",
        (TABLE_DIR / "candidate_family_incremental_recall_over_e1.csv",),
        (
            "candidate_scope_id",
            "episode_split",
            "market_regime_bucket",
            "window",
            "incremental_recall_over_e1",
        ),
    ),
    InputSpec(
        "candidate_family_bridge_positive_recall",
        (TABLE_DIR / "candidate_family_bridge_positive_recall.csv",),
        ("candidate_scope_id", "episode_split", "market_regime_bucket", "window", "recall"),
    ),
    InputSpec(
        "candidate_family_recall_by_split_regime",
        (TABLE_DIR / "candidate_family_recall_by_split_regime.csv",),
        ("candidate_scope_id", "episode_split", "market_regime_bucket", "window", "recall"),
    ),
    InputSpec(
        "candidate_family_density_summary",
        (TABLE_DIR / "candidate_family_density_summary.csv",),
        ("candidate_scope_id", "events_per_instrument_year_mean"),
    ),
    InputSpec(
        "candidate_family_label_quality_readout",
        (TABLE_DIR / "candidate_family_label_quality_readout.csv",),
        ("candidate_scope_id", "label_completeness_rate", "next_open_executable_rate"),
    ),
    InputSpec(
        "candidate_family_false_repair_diagnostic",
        (TABLE_DIR / "candidate_family_false_repair_diagnostic.csv",),
        ("candidate_scope_id", "false_repair_20d_rate"),
    ),
    InputSpec(
        "candidate_family_overlap_matrix",
        (TABLE_DIR / "candidate_family_overlap_matrix.csv",),
        ("left_scope_id", "right_scope_id", "jaccard_overlap"),
    ),
    InputSpec(
        "candidate_family_mechanism_cluster_summary",
        (TABLE_DIR / "candidate_family_mechanism_cluster_summary.csv",),
        ("candidate_scope_id", "mechanism_cluster"),
    ),
    InputSpec(
        "regime_recall_baseline_07_e1_only",
        (TABLE_DIR / "regime_recall_baseline_07_e1_only.csv",),
    ),
    InputSpec(
        "topn_channel_recall_contribution",
        (
            EXP07_DIR
            / "outputs"
            / "publishable"
            / "tables"
            / "topn_channel_recall_contribution.csv",
        ),
        ("channel_id", "recall", "incremental_recall"),
    ),
    InputSpec(
        "topn_channel_density_summary",
        (
            EXP07_DIR
            / "outputs"
            / "publishable"
            / "tables"
            / "topn_channel_density_summary.csv",
        ),
        ("channel_id", "events_per_instrument_year_mean", "events_per_instrument_year_p95"),
    ),
    InputSpec(
        "topn_false_repair_diagnostic",
        (
            EXP07_DIR
            / "outputs"
            / "publishable"
            / "tables"
            / "topn_false_repair_diagnostic.csv",
        ),
        ("event_split", "market_regime_bucket", "primary_channel", "false_repair_20d_rate"),
    ),
    InputSpec(
        "r_series_compression_frontier",
        (
            TABLE_DIR
            / "risk_on_r_series_density_compression"
            / "risk_on_r_series_compression_frontier.csv",
        ),
        ("compression_arm_id", "canonical_event_count", "density_vs_e1_full_denominator"),
        required=False,
    ),
]


A_SCOPE_META = {
    "07_E1_only": ScopeMeta(
        "07_E1_only",
        "E1_early_ema60_repair",
        "07_e1_only",
        "repair_reclaim_cluster",
        "experiment_a_scope",
        "07_e1_only",
    ),
    "07_full_union": ScopeMeta(
        "07_full_union",
        "07_full_union",
        "07_full_union",
        "repair_reclaim_cluster",
        "experiment_a_scope",
        "07_full_union",
    ),
    "08_selected_T4_T7_union": ScopeMeta(
        "08_selected_T4_T7_union",
        "selected_T4_T7_union",
        "08_candidate_union",
        "transition_candidate_union",
        "experiment_a_scope",
        "selected_candidate_union",
    ),
    "08_T4_gated": ScopeMeta(
        "08_T4_gated",
        "T4_entropy_compression_then_directional_expansion",
        "08_candidate_family_variant",
        "compression_break_cluster",
        "experiment_a_scope",
        "T4_entropy_compression_then_directional_expansion__event_regime_gated",
    ),
    "08_T7_gated": ScopeMeta(
        "08_T7_gated",
        "T7_board_relative_strength_break",
        "08_candidate_family_variant",
        "board_style_cluster",
        "experiment_a_scope",
        "T7_board_relative_strength_break__event_regime_gated",
    ),
    "08_R_core_event_regime_gated": ScopeMeta(
        "08_R_core_event_regime_gated",
        "R_core_event_regime_gated",
        "08_candidate_union",
        "risk_on_r_series_cluster",
        "experiment_a_scope",
        "event_regime_gated_only",
    ),
    **{
        f"08_{family.split('_', 1)[0]}_event_regime_gated": ScopeMeta(
            f"08_{family.split('_', 1)[0]}_event_regime_gated",
            family,
            "08_candidate_family_variant",
            "risk_on_r_series_cluster",
            "experiment_a_scope",
            f"{family}__event_regime_gated",
        )
        for family in R_FAMILIES
    },
}

E_CONTEXT_META = {
    "07_E2_channel": ScopeMeta(
        "07_E2_channel",
        "E2_same_day_confirmation_tag",
        "07_channel_context",
        "repair_reclaim_cluster",
        "07_context_only",
        "E2_money_vwap_repair_confirmation",
    ),
    "07_E3_channel": ScopeMeta(
        "07_E3_channel",
        "E3_persistence_quality",
        "07_channel_context",
        "repair_reclaim_cluster",
        "07_context_only",
        "E3_rank_persistence",
    ),
    "07_E6_channel": ScopeMeta(
        "07_E6_channel",
        "E6_continuation_tag",
        "07_channel_context",
        "repair_reclaim_cluster",
        "07_context_only",
        "E6_continuation_discriminator",
    ),
}

SCOPE_META = {**A_SCOPE_META, **E_CONTEXT_META}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Experiment B regime x family matrix.")
    parser.add_argument(
        "--mode",
        choices=["check-inputs", "full", "planning-pass"],
        default="full",
        help="Check inputs or run the full matrix.",
    )
    return parser.parse_args(argv)


def ensure_dirs() -> None:
    for path in (B_TABLE_DIR, B_REPORT_DIR, B_MANIFEST_DIR, B_LOCAL_CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)


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
    frame.to_csv(path, index=False)
    return path


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def resolve_input(spec: InputSpec) -> Path:
    for path in spec.paths:
        if path.exists() and path.is_file():
            return path
    return spec.paths[0]


def read_columns(path: Path) -> tuple[list[str], str]:
    if not path.exists():
        return [], "missing"
    if path.suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
            return [], "readable_non_tabular"
        except Exception:
            return [], "unreadable"
    if path.suffix == ".md":
        try:
            path.read_text(encoding="utf-8")
            return [], "readable_non_tabular"
        except Exception:
            return [], "unreadable"
    if path.stat().st_size <= 1:
        return [], "empty"
    try:
        return pd.read_csv(path, nrows=0).columns.tolist(), "readable_tabular"
    except Exception:
        return [], "unreadable"


def input_audit() -> tuple[pd.DataFrame, list[str], dict[str, Path]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    resolved: dict[str, Path] = {}
    for spec in INPUT_SPECS:
        path = resolve_input(spec)
        resolved[spec.input_id] = path
        exists = path.exists() and path.is_file()
        columns, readability = read_columns(path)
        missing_columns = sorted(set(spec.required_columns) - set(columns))
        if not exists:
            status = "missing_required_input" if spec.required else "missing_optional_input"
        elif readability == "empty":
            status = "empty_required_input" if spec.required else "empty_optional_input"
        elif readability == "unreadable":
            status = "unreadable_required_input" if spec.required else "unreadable_optional_input"
        elif missing_columns:
            status = (
                "schema_incompatible_required_input"
                if spec.required
                else "schema_incompatible_optional_input"
            )
        else:
            status = "ok"
        if spec.required and status != "ok":
            failures.append(f"{status}:{spec.input_id}")
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(path),
                "input_kind": "required" if spec.required else "optional",
                "exists": exists,
                "readability_status": readability,
                "status": status,
                "missing_required_columns": ";".join(missing_columns),
                "actual_columns": ";".join(columns),
                "sha256": path_hash(path),
            }
        )
    return pd.DataFrame(rows), failures, resolved


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 1:
        return pd.DataFrame()
    try:
        return read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_na(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value)


def safe_float(value: Any, default: float = np.nan) -> float:
    if value is None or pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.2f}%"


def sample_status(episode_denominator: Any, bridge_denominator: Any) -> str:
    if pd.isna(episode_denominator) or pd.isna(bridge_denominator):
        return "diagnostic_only"
    if float(episode_denominator) < 30 or float(bridge_denominator) < 30:
        return "diagnostic_only"
    if float(episode_denominator) < 100 or float(bridge_denominator) < 100:
        return "low_power_caution"
    return "sufficient_for_cell_readout"


def normalize_sample_status(value: Any) -> str:
    if pd.isna(value):
        return "sufficient_for_cell_readout"
    status = str(value)
    return status if status in SAMPLE_ORDER else "diagnostic_only"


def more_conservative_status(left: Any, right: Any) -> str:
    left_status = normalize_sample_status(left)
    right_status = normalize_sample_status(right)
    return left_status if SAMPLE_ORDER.get(left_status, 9) >= SAMPLE_ORDER.get(right_status, 9) else right_status


def status_resolution(left: Any, right: Any) -> str:
    if pd.isna(left) and pd.isna(right):
        return "computed_only"
    if normalize_sample_status(left) == normalize_sample_status(right):
        return "same_status"
    return "conservative_override"


def build_base_cells(
    fast_fail: pd.DataFrame,
    uniqueness: pd.DataFrame,
    gap: pd.DataFrame,
    retention: pd.DataFrame,
    false_repair_07: pd.DataFrame,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for frame, split_col in [
        (fast_fail, "event_split"),
        (uniqueness, "event_split"),
        (gap, "event_split"),
        (retention, "episode_split"),
    ]:
        subset = frame[["candidate_scope_id", split_col, "market_regime_bucket"]].copy()
        subset = subset.rename(columns={split_col: "split"})
        frames.append(subset)
    if not false_repair_07.empty:
        e_context = false_repair_07[
            ["event_split", "market_regime_bucket", "primary_channel"]
        ].copy()
        e_context["candidate_scope_id"] = e_context["primary_channel"].map(
            {
                "E2_money_vwap_repair_confirmation": "07_E2_channel",
                "E3_rank_persistence": "07_E3_channel",
                "E6_continuation_discriminator": "07_E6_channel",
            }
        )
        e_context = e_context.dropna(subset=["candidate_scope_id"])
        e_context = e_context.rename(columns={"event_split": "split"})
        frames.append(e_context[["candidate_scope_id", "split", "market_regime_bucket"]])
    cells = pd.concat(frames, ignore_index=True).drop_duplicates()
    cells = cells[cells["candidate_scope_id"].isin(SCOPE_META)].reset_index(drop=True)
    cells["family_id"] = cells["candidate_scope_id"].map(lambda x: SCOPE_META[x].family_id)
    cells["candidate_scope_type"] = cells["candidate_scope_id"].map(
        lambda x: SCOPE_META[x].candidate_scope_type
    )
    cells["mechanism_cluster"] = cells["candidate_scope_id"].map(
        lambda x: SCOPE_META[x].mechanism_cluster
    )
    cells["source_kind"] = cells["candidate_scope_id"].map(lambda x: SCOPE_META[x].source_kind)
    cells["reference_scope_id"] = cells["candidate_scope_id"].map(
        lambda x: SCOPE_META[x].reference_scope_id
    )
    return cells


def join_scope_density(cells: pd.DataFrame, density: pd.DataFrame) -> pd.DataFrame:
    density_cols = [
        "candidate_scope_id",
        "event_count",
        "executable_event_count",
        "failure_10_complete_event_count",
        "events_per_instrument_year_mean",
        "events_per_instrument_year_p95",
        "rolling_10d_duplicate_rate",
        "density_vs_07_E1_only",
        "scope_status",
    ]
    available = [col for col in density_cols if col in density.columns]
    out = cells.merge(density[available], on="candidate_scope_id", how="left")
    out = out.rename(
        columns={
            "event_count": "scope_event_count",
            "scope_status": "source_scope_status",
            "density_vs_07_E1_only": "scope_density_vs_07_E1_only",
        }
    )
    out["density_granularity"] = np.where(
        out["scope_event_count"].notna(), "scope_level_only", "not_available_publishable_source"
    )
    out["density_source_split"] = np.where(out["scope_event_count"].notna(), "all", "")
    out["density_source_regime"] = np.where(out["scope_event_count"].notna(), "all", "")
    out["density_cell_recomputed_flag"] = False
    return out


def build_incremental_lookup(incremental: pd.DataFrame) -> pd.DataFrame:
    if incremental.empty:
        return pd.DataFrame()
    inc = incremental[incremental["window"].eq(BEFORE_FIRST_50)].copy()
    inc = inc.rename(columns={"episode_split": "split"})
    return inc[
        [
            "candidate_scope_id",
            "split",
            "market_regime_bucket",
            "incremental_recall_over_e1",
            "incremental_captures_over_e1",
            "denominator_episodes",
        ]
    ].copy()


def merge_incremental(perf: pd.DataFrame, incremental: pd.DataFrame) -> pd.DataFrame:
    lookup = build_incremental_lookup(incremental)
    lookup = lookup.rename(columns={"candidate_scope_id": "reference_scope_id"})
    out = perf.merge(
        lookup,
        on=["reference_scope_id", "split", "market_regime_bucket"],
        how="left",
    )
    out["incremental_recall_source_status"] = np.where(
        out["incremental_recall_over_e1"].notna(),
        "candidate_family_incremental_recall_over_e1",
        "not_available_publishable_source",
    )
    e1_mask = out["candidate_scope_id"].eq("07_E1_only")
    out.loc[e1_mask, "incremental_recall_over_e1"] = 0.0
    out.loc[e1_mask, "incremental_captures_over_e1"] = 0.0
    out.loc[e1_mask, "incremental_recall_source_status"] = "baseline_zero"
    t_gated = out["candidate_scope_id"].isin(["08_T4_gated", "08_T7_gated"])
    out.loc[t_gated, ["incremental_recall_over_e1", "incremental_captures_over_e1"]] = np.nan
    out.loc[t_gated, "incremental_recall_source_status"] = "not_available_publishable_source"
    return out


def add_07_context(
    perf: pd.DataFrame,
    channel_recall: pd.DataFrame,
    channel_density: pd.DataFrame,
    false_repair_07: pd.DataFrame,
) -> pd.DataFrame:
    if channel_recall.empty and channel_density.empty and false_repair_07.empty:
        return perf
    channel_to_scope = {
        "E2_money_vwap_repair_confirmation": "07_E2_channel",
        "E3_rank_persistence": "07_E3_channel",
        "E6_continuation_discriminator": "07_E6_channel",
    }
    recall = channel_recall.copy()
    recall["candidate_scope_id"] = recall["channel_id"].map(channel_to_scope)
    recall = recall.dropna(subset=["candidate_scope_id"])
    recall = recall.rename(
        columns={
            "recall": "channel_pre_replay_any_recall",
            "incremental_recall": "channel_incremental_recall_over_e1",
            "incremental_captured_episode_count": "channel_incremental_captures_over_e1",
        }
    )
    density = channel_density.copy()
    density["candidate_scope_id"] = density["channel_id"].map(channel_to_scope)
    density = density.dropna(subset=["candidate_scope_id"])
    density = density.rename(
        columns={
            "event_count": "channel_scope_event_count",
            "events_per_instrument_year_mean": "channel_events_per_instrument_year_mean",
            "events_per_instrument_year_p95": "channel_events_per_instrument_year_p95",
        }
    )
    false_repair = false_repair_07.copy()
    false_repair["candidate_scope_id"] = false_repair["primary_channel"].map(channel_to_scope)
    false_repair = false_repair.dropna(subset=["candidate_scope_id"])
    false_repair = false_repair.rename(columns={"event_split": "split"})
    false_cols = [
        "candidate_scope_id",
        "split",
        "market_regime_bucket",
        "event_count",
        "false_repair_10d_count",
        "false_repair_10d_rate",
        "false_repair_20d_count",
        "false_repair_20d_rate",
    ]
    out = perf.merge(
        recall[
            [
                "candidate_scope_id",
                "target_episode_count",
                "captured_episode_count",
                "channel_pre_replay_any_recall",
                "channel_incremental_recall_over_e1",
                "channel_incremental_captures_over_e1",
            ]
        ],
        on="candidate_scope_id",
        how="left",
    )
    out = out.merge(
        density[
            [
                "candidate_scope_id",
                "channel_scope_event_count",
                "channel_events_per_instrument_year_mean",
                "channel_events_per_instrument_year_p95",
            ]
        ],
        on="candidate_scope_id",
        how="left",
    )
    out = out.merge(false_repair[false_cols], on=["candidate_scope_id", "split", "market_regime_bucket"], how="left", suffixes=("", "_07"))
    e_context = out["candidate_scope_id"].isin(E_CONTEXT_META)
    all_all = e_context & out["split"].eq("all") & out["market_regime_bucket"].eq("all")
    out.loc[all_all, "episode_denominator_n"] = out.loc[all_all, "target_episode_count"]
    out.loc[all_all, "bridge_denominator_n"] = out.loc[all_all, "target_episode_count"]
    out.loc[all_all, "candidate_captured_episode_n"] = out.loc[all_all, "captured_episode_count"]
    out.loc[all_all, "pre_replay_any_recall"] = out.loc[
        all_all, "channel_pre_replay_any_recall"
    ]
    out.loc[all_all, "before_first_50pct_any_recall"] = out.loc[
        all_all, "channel_pre_replay_any_recall"
    ]
    out.loc[e_context, "incremental_recall_over_e1"] = out.loc[
        e_context, "channel_incremental_recall_over_e1"
    ]
    out.loc[e_context, "incremental_captures_over_e1"] = out.loc[
        e_context, "channel_incremental_captures_over_e1"
    ]
    out.loc[e_context, "incremental_recall_source_status"] = "topn_channel_recall_contribution"
    out.loc[e_context & out["channel_incremental_recall_over_e1"].isna(), "incremental_recall_source_status"] = (
        "not_available_publishable_source"
    )
    out.loc[e_context, "scope_event_count"] = out.loc[e_context, "channel_scope_event_count"]
    out.loc[e_context, "events_per_instrument_year_mean"] = out.loc[
        e_context, "channel_events_per_instrument_year_mean"
    ]
    out.loc[e_context, "events_per_instrument_year_p95"] = out.loc[
        e_context, "channel_events_per_instrument_year_p95"
    ]
    out.loc[e_context, "density_granularity"] = "scope_level_only"
    out.loc[e_context, "density_source_split"] = "all"
    out.loc[e_context, "density_source_regime"] = "all"
    out.loc[e_context, "density_cell_recomputed_flag"] = False
    out.loc[e_context, "source_scope_status"] = "07_context_only_not_experiment_a_scope"
    out.loc[e_context, "experiment_a_source_caveat"] = "not_in_experiment_a_scope"
    out.loc[e_context, "fast_fail_10d_rate"] = out.loc[e_context, "false_repair_10d_rate"]
    return out.drop(
        columns=[
            col
            for col in [
                "channel_pre_replay_any_recall",
                "channel_incremental_recall_over_e1",
                "channel_incremental_captures_over_e1",
                "channel_scope_event_count",
                "channel_events_per_instrument_year_mean",
                "channel_events_per_instrument_year_p95",
                "target_episode_count",
                "captured_episode_count",
                "event_count_07",
            ]
            if col in out.columns
        ]
    )


def build_performance_matrix(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fast_fail = tables["candidate_10d_fast_fail_readout"]
    uniqueness = tables["candidate_10d_uniqueness_diagnostic"]
    gap = tables["candidate_adjacent_event_gap_diagnostic"]
    retention = tables["candidate_10d_retention_by_split_regime"]
    density = tables["candidate_10d_density_summary"]
    reconstruct = tables["candidate_scope_reconstructability_audit"]
    crosswalk = tables["candidate_density_caliber_crosswalk"]
    label_quality = tables["candidate_family_label_quality_readout"]

    cells = build_base_cells(
        fast_fail,
        uniqueness,
        gap,
        retention,
        tables["topn_false_repair_diagnostic"],
    )
    perf = join_scope_density(cells, density)
    perf = perf.merge(
        fast_fail.rename(columns={"event_split": "split", "event_count": "fast_fail_event_n"}),
        on=["candidate_scope_id", "split", "market_regime_bucket"],
        how="left",
    )
    ret = retention.rename(
        columns={
            "episode_split": "split",
            "target_episode_denominator": "episode_denominator_n",
            "cell_sample_status": "experiment_a_cell_sample_status",
        }
    )
    perf = perf.merge(
        ret[
            [
                "candidate_scope_id",
                "split",
                "market_regime_bucket",
                "episode_denominator_n",
                "pre_replay_any_recall",
                "post_replay_any_recall",
                "pre_replay_bridge_recall",
                "post_replay_bridge_recall",
                "e1_missed_capture_retention",
                "retention_source_status",
                "experiment_a_cell_sample_status",
            ]
        ],
        on=["candidate_scope_id", "split", "market_regime_bucket"],
        how="left",
    )
    uniq = uniqueness.rename(
        columns={"event_split": "split", "event_count": "uniqueness_event_n"}
    )
    perf = perf.merge(
        uniq[
            [
                "candidate_scope_id",
                "split",
                "market_regime_bucket",
                "uniqueness_event_n",
                "event_uniqueness_10d_p10",
                "event_uniqueness_10d_low_share",
                "concurrency_p95",
                "uniqueness_diagnostic_alert_flag",
            ]
        ],
        on=["candidate_scope_id", "split", "market_regime_bucket"],
        how="left",
    )
    gap_renamed = gap.rename(columns={"event_split": "split", "gap_lt_10d_rate": "adjacent_gap_lt_10d_share"})
    perf = perf.merge(
        gap_renamed[
            [
                "candidate_scope_id",
                "split",
                "market_regime_bucket",
                "adjacent_gap_median",
                "adjacent_gap_lt_10d_share",
                "diagnostic_alert_flag",
            ]
        ],
        on=["candidate_scope_id", "split", "market_regime_bucket"],
        how="left",
    )
    perf = perf.merge(
        reconstruct[
            [
                "candidate_scope_id",
                "scope_status",
                "event_level_label_source_status",
                "episode_capture_source_status",
                "hard_gate_eligible_flag",
            ]
        ].rename(
            columns={
                "scope_status": "reconstructability_scope_status",
                "event_level_label_source_status": "reconstruct_event_level_label_source_status",
            }
        ),
        on="candidate_scope_id",
        how="left",
    )
    perf["source_scope_status"] = perf["source_scope_status"].fillna(
        perf["reconstructability_scope_status"]
    )
    perf = perf.merge(
        crosswalk[
            [
                "candidate_scope_id",
                "final_diagnostic_alert_status",
                "final_hard_gate_status",
            ]
        ].rename(
            columns={
                "final_diagnostic_alert_status": "experiment_a_density_alert_status",
                "final_hard_gate_status": "experiment_a_hard_gate_status",
            }
        ),
        on="candidate_scope_id",
        how="left",
    )
    perf = merge_incremental(perf, tables["candidate_family_incremental_recall_over_e1"])
    perf = add_07_context(
        perf,
        tables["topn_channel_recall_contribution"],
        tables["topn_channel_density_summary"],
        tables["topn_false_repair_diagnostic"],
    )

    # Scope/cell source notes.
    perf["event_n"] = perf["fast_fail_event_n"].combine_first(perf["uniqueness_event_n"]).combine_first(
        perf["scope_event_count"]
    )
    perf["bridge_denominator_n"] = np.where(
        perf["pre_replay_bridge_recall"].notna(), perf["episode_denominator_n"], np.nan
    )
    perf["candidate_captured_episode_n"] = (
        perf["pre_replay_any_recall"] * perf["episode_denominator_n"]
    ).round()
    perf["before_first_50pct_any_recall"] = perf["pre_replay_any_recall"]
    perf["bridge_positive_recall"] = perf["pre_replay_bridge_recall"]
    perf["e1_missed_capture_n"] = (
        perf["e1_missed_capture_retention"] * perf["episode_denominator_n"]
    ).round()
    perf["post_replay_any_recall"] = np.nan
    perf["post_replay_bridge_recall"] = np.nan
    perf["fast_fail_diagnostic_label_usage"] = "diagnostic_only_not_t0_feature"
    perf["density_cell_recomputed_flag"] = False
    perf["density_granularity"] = perf["density_granularity"].fillna(
        "not_available_publishable_source"
    )
    perf["density_source_split"] = perf["density_source_split"].fillna("")
    perf["density_source_regime"] = perf["density_source_regime"].fillna("")

    perf["computed_cell_sample_status"] = [
        sample_status(ep, br)
        for ep, br in zip(perf["episode_denominator_n"], perf["bridge_denominator_n"])
    ]
    perf["cell_sample_status"] = [
        more_conservative_status(a, c)
        for a, c in zip(perf["experiment_a_cell_sample_status"], perf["computed_cell_sample_status"])
    ]
    perf["cell_sample_status_resolution"] = [
        status_resolution(a, c)
        for a, c in zip(perf["experiment_a_cell_sample_status"], perf["computed_cell_sample_status"])
    ]

    # Same-cell E1 fast-fail baseline; fallback to all/all.
    e1 = perf[perf["candidate_scope_id"].eq("07_E1_only")][
        ["split", "market_regime_bucket", "fast_fail_10d_rate"]
    ].rename(columns={"fast_fail_10d_rate": "e1_fast_fail_same_cell"})
    perf = perf.merge(e1, on=["split", "market_regime_bucket"], how="left")
    e1_all = perf.loc[
        perf["candidate_scope_id"].eq("07_E1_only")
        & perf["split"].eq("all")
        & perf["market_regime_bucket"].eq("all"),
        "fast_fail_10d_rate",
    ]
    e1_all_value = float(e1_all.iloc[0]) if len(e1_all) else np.nan
    perf["e1_fast_fail_same_cell"] = perf["e1_fast_fail_same_cell"].fillna(e1_all_value)
    perf["fast_fail_excess_vs_e1_pp"] = (
        perf["fast_fail_10d_rate"] - perf["e1_fast_fail_same_cell"]
    )

    r_core = perf[perf["candidate_scope_id"].eq("08_R_core_event_regime_gated")][
        ["split", "market_regime_bucket", "rolling_10d_duplicate_rate"]
    ].rename(columns={"rolling_10d_duplicate_rate": "r_core_collision_10d_rate"})
    perf = perf.merge(r_core, on=["split", "market_regime_bucket"], how="left")
    is_r = perf["family_id"].isin(R_FAMILIES + ["R_core_event_regime_gated"])
    perf["cross_family_collision_10d_rate"] = np.where(
        is_r, perf["r_core_collision_10d_rate"], np.nan
    )

    # Label quality is variant-keyed context; use it where reference scope ids match.
    quality = label_quality.copy()
    if not quality.empty:
        quality = quality.rename(
            columns={
                "event_split": "split",
                "event_regime_bucket": "market_regime_bucket",
                "candidate_scope_id": "reference_scope_id",
            }
        )
        quality = (
            quality.groupby(["reference_scope_id", "split", "market_regime_bucket"], as_index=False)
            .agg(
                label_completeness_rate=("label_completeness_rate", "mean"),
                next_open_executable_rate=("next_open_executable_rate", "mean"),
            )
        )
        perf = perf.merge(
            quality,
            on=["reference_scope_id", "split", "market_regime_bucket"],
            how="left",
        )
    else:
        perf["label_completeness_rate"] = np.nan
        perf["next_open_executable_rate"] = np.nan

    perf["single_family_density_share"] = np.nan
    perf["mechanism_cluster_share"] = np.nan
    retention_source_fallback = pd.Series("", index=perf.index, dtype=object)
    retention_source_fallback.loc[
        perf["candidate_scope_id"].eq("08_R_core_event_regime_gated")
    ] = "scope_capture_not_available"
    retention_source_fallback.loc[
        perf["source_kind"].eq("07_context_only")
    ] = "07_context_not_in_a_retention"
    perf["retention_source_status"] = perf["retention_source_status"].fillna(
        retention_source_fallback
    )
    perf["experiment_a_source_caveat"] = perf.get("experiment_a_source_caveat", pd.Series(index=perf.index, dtype=object))
    perf["experiment_a_source_caveat"] = perf["experiment_a_source_caveat"].fillna("")
    perf.loc[
        perf["retention_source_status"].eq("pre_replay_capture_only"),
        "experiment_a_source_caveat",
    ] = "pre_replay_capture_only_not_post_filter_retention"
    perf.loc[
        perf["candidate_scope_id"].eq("08_R_core_event_regime_gated"),
        "experiment_a_source_caveat",
    ] = "scope_capture_not_available"
    perf.loc[
        perf["source_kind"].eq("07_context_only"),
        "experiment_a_source_caveat",
    ] = "not_in_experiment_a_scope"

    perf["transition_reselection_role"] = ""
    perf["family_regime_role_recommendation"] = [
        classify_family_role(row) for _, row in perf.iterrows()
    ]
    perf.loc[
        perf["market_regime_bucket"].eq("transition"),
        "transition_reselection_role",
    ] = [
        classify_transition_role(row)
        for _, row in perf[perf["market_regime_bucket"].eq("transition")].iterrows()
    ]
    perf = mark_transition_primary(perf)

    required_cols = [
        "candidate_scope_id",
        "family_id",
        "candidate_scope_type",
        "mechanism_cluster",
        "source_kind",
        "reference_scope_id",
        "split",
        "market_regime_bucket",
        "source_scope_id",
        "source_scope_status",
        "retention_source_status",
        "episode_denominator_n",
        "bridge_denominator_n",
        "event_n",
        "candidate_captured_episode_n",
        "before_first_50pct_any_recall",
        "bridge_positive_recall",
        "pre_replay_any_recall",
        "pre_replay_bridge_recall",
        "post_replay_any_recall",
        "post_replay_bridge_recall",
        "incremental_recall_over_e1",
        "incremental_captures_over_e1",
        "incremental_recall_source_status",
        "e1_missed_capture_n",
        "failure_10_complete_event_count",
        "fast_fail_10d_count",
        "fast_fail_10d_rate",
        "fast_fail_excess_vs_e1_pp",
        "false_repair_20d_count",
        "false_repair_20d_rate",
        "non_executable_event_count",
        "horizon_incomplete_10d_count",
        "label_source_column",
        "fast_fail_definition_id",
        "label_mapping_status",
        "event_level_label_source_status",
        "fast_fail_diagnostic_label_usage",
        "events_per_instrument_year_mean",
        "events_per_instrument_year_p95",
        "rolling_10d_duplicate_rate",
        "density_granularity",
        "density_source_split",
        "density_source_regime",
        "density_cell_recomputed_flag",
        "event_uniqueness_10d_p10",
        "event_uniqueness_10d_low_share",
        "concurrency_p95",
        "adjacent_gap_median",
        "adjacent_gap_lt_10d_share",
        "cross_family_collision_10d_rate",
        "single_family_density_share",
        "mechanism_cluster_share",
        "label_completeness_rate",
        "next_open_executable_rate",
        "experiment_a_density_alert_status",
        "experiment_a_source_caveat",
        "transition_reselection_role",
        "experiment_a_cell_sample_status",
        "computed_cell_sample_status",
        "cell_sample_status",
        "cell_sample_status_resolution",
        "family_regime_role_recommendation",
    ]
    perf["source_scope_id"] = perf["candidate_scope_id"]
    for col in required_cols:
        if col not in perf.columns:
            perf[col] = np.nan
    return perf[required_cols].sort_values(
        ["candidate_scope_id", "split", "market_regime_bucket"]
    )


def classify_family_role(row: pd.Series) -> str:
    scope = str(row["candidate_scope_id"])
    status = str(row.get("cell_sample_status", ""))
    if scope == "08_R_core_event_regime_gated":
        return "union_collision_diagnostic_only"
    if status == "diagnostic_only":
        return "sample_blocked"
    if str(row.get("source_scope_status", "")).startswith("scope_capture_not"):
        return "source_blocked"
    if (
        str(row.get("source_kind", "")) == "experiment_a_scope"
        and str(row.get("market_regime_bucket", "")) in {"risk_off", "risk_on", "transition"}
        and str(row.get("split", "")) in {"train", "robustness", "validation"}
        and pd.isna(row.get("fast_fail_10d_rate"))
    ):
        return "source_blocked"
    if scope in {"08_T4_gated", "08_T7_gated", "08_selected_T4_T7_union"}:
        return "quality_filter_required"
    if scope == "07_full_union":
        return "density_or_fast_fail_blocked"
    if str(row.get("family_id", "")) in R_FAMILIES:
        return "collision_deoverlap_required"
    if scope == "07_E1_only":
        return "backbone_candidate"
    if str(row.get("source_kind", "")) == "07_context_only":
        return "context_tag_only"
    return "context_tag_only"


def classify_transition_role(row: pd.Series) -> str:
    scope = str(row["candidate_scope_id"])
    if str(row.get("cell_sample_status", "")) == "diagnostic_only":
        return "transition_inconclusive"
    if scope == "08_R_core_event_regime_gated":
        return "transition_context_only"
    if scope in {"08_T4_gated", "08_T7_gated", "08_selected_T4_T7_union"}:
        return "transition_quality_filter_candidate"
    if str(row.get("source_scope_status", "")).startswith("scope_capture_not"):
        return "transition_source_blocked"
    if str(row.get("family_id", "")) in R_FAMILIES:
        return "transition_support_feature"
    if scope == "07_E1_only":
        return "transition_context_only"
    if str(row.get("source_kind", "")) == "07_context_only":
        return "transition_context_only"
    return "transition_inconclusive"


def transition_score(row: pd.Series) -> float:
    recall = safe_float(row.get("pre_replay_any_recall"), 0.0)
    bridge = safe_float(row.get("pre_replay_bridge_recall"), 0.0)
    fast_fail = safe_float(row.get("fast_fail_10d_rate"), 0.5)
    collision = safe_float(row.get("cross_family_collision_10d_rate"), 0.0)
    return recall + bridge - 0.5 * fast_fail - 0.2 * collision


def mark_transition_primary(perf: pd.DataFrame) -> pd.DataFrame:
    out = perf.copy()
    transition = out[
        out["market_regime_bucket"].eq("transition")
        & out["split"].isin(["train", "robustness"])
        & out["family_id"].isin(R_FAMILIES)
        & out["pre_replay_any_recall"].notna()
    ].copy()
    if transition.empty:
        return out
    transition["score"] = transition.apply(transition_score, axis=1)
    for split, group in transition.groupby("split"):
        idx = group["score"].idxmax()
        out.loc[idx, "transition_reselection_role"] = "transition_primary_candidate"
    return out


def build_experiment_a_alignment(
    perf: pd.DataFrame,
    a_manifest: dict[str, Any],
    input_audit_frame: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    all_all = perf[perf["split"].eq("all") & perf["market_regime_bucket"].eq("all")]
    for _, row in all_all.iterrows():
        rows.append(
            {
                "candidate_scope_id": row["candidate_scope_id"],
                "family_id": row["family_id"],
                "source_kind": row["source_kind"],
                "experiment_a_decision": a_manifest.get("decision", ""),
                "event_n": row["event_n"],
                "pre_replay_any_recall": row["pre_replay_any_recall"],
                "pre_replay_bridge_recall": row["pre_replay_bridge_recall"],
                "rolling_10d_duplicate_rate": row["rolling_10d_duplicate_rate"],
                "event_uniqueness_10d_p10": row["event_uniqueness_10d_p10"],
                "fast_fail_10d_rate": row["fast_fail_10d_rate"],
                "false_repair_20d_rate": row["false_repair_20d_rate"],
                "density_granularity": row["density_granularity"],
                "source_caveat": row["experiment_a_source_caveat"],
                "b_interpretation": row["family_regime_role_recommendation"],
            }
        )
    return pd.DataFrame(rows)


def build_sample_guardrail(perf: pd.DataFrame) -> pd.DataFrame:
    return perf[
        [
            "candidate_scope_id",
            "family_id",
            "split",
            "market_regime_bucket",
            "episode_denominator_n",
            "bridge_denominator_n",
            "experiment_a_cell_sample_status",
            "computed_cell_sample_status",
            "cell_sample_status",
            "cell_sample_status_resolution",
            "retention_source_status",
            "experiment_a_source_caveat",
        ]
    ].copy()


def build_density_fast_fail_matrix(perf: pd.DataFrame) -> pd.DataFrame:
    return perf[
        [
            "candidate_scope_id",
            "family_id",
            "split",
            "market_regime_bucket",
            "event_n",
            "events_per_instrument_year_mean",
            "events_per_instrument_year_p95",
            "rolling_10d_duplicate_rate",
            "density_granularity",
            "density_source_split",
            "density_source_regime",
            "density_cell_recomputed_flag",
            "event_uniqueness_10d_p10",
            "concurrency_p95",
            "adjacent_gap_median",
            "adjacent_gap_lt_10d_share",
            "fast_fail_10d_count",
            "fast_fail_10d_rate",
            "fast_fail_excess_vs_e1_pp",
            "false_repair_20d_count",
            "false_repair_20d_rate",
            "experiment_a_density_alert_status",
        ]
    ].copy()


def build_fast_fail_diagnostic_matrix(perf: pd.DataFrame) -> pd.DataFrame:
    out = perf[
        [
            "candidate_scope_id",
            "family_id",
            "split",
            "market_regime_bucket",
            "event_n",
            "failure_10_complete_event_count",
            "fast_fail_10d_count",
            "fast_fail_10d_rate",
            "false_repair_20d_count",
            "false_repair_20d_rate",
            "non_executable_event_count",
            "horizon_incomplete_10d_count",
            "label_source_column",
            "fast_fail_definition_id",
            "label_mapping_status",
            "event_level_label_source_status",
            "fast_fail_diagnostic_label_usage",
        ]
    ].copy()
    return out.rename(columns={"split": "event_split", "event_n": "event_count"})


def build_bridge_recall_matrix(perf: pd.DataFrame) -> pd.DataFrame:
    return perf[
        [
            "candidate_scope_id",
            "family_id",
            "split",
            "market_regime_bucket",
            "episode_denominator_n",
            "bridge_denominator_n",
            "pre_replay_any_recall",
            "pre_replay_bridge_recall",
            "post_replay_any_recall",
            "post_replay_bridge_recall",
            "incremental_recall_over_e1",
            "incremental_captures_over_e1",
            "incremental_recall_source_status",
            "retention_source_status",
        ]
    ].copy()


def build_overlap_concentration_matrix(overlap: pd.DataFrame) -> pd.DataFrame:
    if overlap.empty:
        return pd.DataFrame(
            columns=[
                "left_scope_id",
                "right_scope_id",
                "mapped_left_candidate_scope_id",
                "mapped_right_candidate_scope_id",
                "jaccard_overlap",
                "left_overlap_rate",
                "right_overlap_rate",
                "high_risk_overlap_pair",
            ]
        )
    ref_to_a = {meta.reference_scope_id: scope for scope, meta in SCOPE_META.items()}
    out = overlap.copy()
    out["mapped_left_candidate_scope_id"] = out["left_scope_id"].map(ref_to_a).fillna("")
    out["mapped_right_candidate_scope_id"] = out["right_scope_id"].map(ref_to_a).fillna("")
    relevant = out["mapped_left_candidate_scope_id"].ne("") | out["mapped_right_candidate_scope_id"].ne("")
    out = out[relevant].copy()
    if out.empty:
        out = overlap.nlargest(min(len(overlap), 100), "jaccard_overlap").copy()
        out["mapped_left_candidate_scope_id"] = ""
        out["mapped_right_candidate_scope_id"] = ""
    columns = [
        "left_scope_id",
        "right_scope_id",
        "mapped_left_candidate_scope_id",
        "mapped_right_candidate_scope_id",
        "left_episode_count",
        "right_episode_count",
        "overlap_episode_count",
        "left_overlap_rate",
        "right_overlap_rate",
        "jaccard_overlap",
        "same_day_overlap_count",
        "same_day_jaccard",
        "same_episode_different_day_overlap_count",
        "high_risk_overlap_pair",
    ]
    for col in columns:
        if col not in out.columns:
            out[col] = np.nan
    return out[columns].sort_values("jaccard_overlap", ascending=False)


def build_cross_family_collision_matrix(perf: pd.DataFrame) -> pd.DataFrame:
    r_core = perf[perf["candidate_scope_id"].eq("08_R_core_event_regime_gated")][
        [
            "split",
            "market_regime_bucket",
            "event_n",
            "rolling_10d_duplicate_rate",
            "event_uniqueness_10d_p10",
            "concurrency_p95",
            "adjacent_gap_median",
            "fast_fail_10d_rate",
        ]
    ].rename(
        columns={
            "event_n": "r_core_event_n",
            "rolling_10d_duplicate_rate": "r_core_rolling_10d_duplicate_rate",
            "event_uniqueness_10d_p10": "r_core_event_uniqueness_10d_p10",
            "concurrency_p95": "r_core_concurrency_p95",
            "adjacent_gap_median": "r_core_adjacent_gap_median",
            "fast_fail_10d_rate": "r_core_fast_fail_10d_rate",
        }
    )
    r_individual = perf[perf["family_id"].isin(R_FAMILIES)][
        [
            "candidate_scope_id",
            "family_id",
            "split",
            "market_regime_bucket",
            "event_n",
            "rolling_10d_duplicate_rate",
            "event_uniqueness_10d_p10",
            "concurrency_p95",
            "fast_fail_10d_rate",
            "pre_replay_any_recall",
            "pre_replay_bridge_recall",
        ]
    ].copy()
    out = r_individual.merge(r_core, on=["split", "market_regime_bucket"], how="left")
    out["collision_interpretation"] = np.where(
        out["r_core_rolling_10d_duplicate_rate"].fillna(0) > 0.10,
        "individual_sparse_but_r_core_cross_family_collision",
        "no_r_core_collision_alert",
    )
    return out


def build_retention_source_status(perf: pd.DataFrame) -> pd.DataFrame:
    return perf[
        [
            "candidate_scope_id",
            "family_id",
            "split",
            "market_regime_bucket",
            "retention_source_status",
            "episode_denominator_n",
            "pre_replay_any_recall",
            "pre_replay_bridge_recall",
            "post_replay_any_recall",
            "post_replay_bridge_recall",
            "experiment_a_source_caveat",
            "cell_sample_status",
        ]
    ].copy()


def build_transition_reselection_matrix(perf: pd.DataFrame) -> pd.DataFrame:
    out = perf[perf["market_regime_bucket"].eq("transition")].copy()
    out["transition_score"] = out.apply(transition_score, axis=1)
    out["t4_t7_source_rule"] = np.where(
        out["candidate_scope_id"].isin(["08_T4_gated", "08_T7_gated"]),
        "recall_bridge_from_candidate_10d_retention_by_split_regime",
        "",
    )
    columns = [
        "candidate_scope_id",
        "family_id",
        "split",
        "market_regime_bucket",
        "transition_reselection_role",
        "transition_score",
        "pre_replay_any_recall",
        "pre_replay_bridge_recall",
        "incremental_recall_over_e1",
        "incremental_recall_source_status",
        "fast_fail_10d_rate",
        "false_repair_20d_rate",
        "rolling_10d_duplicate_rate",
        "density_granularity",
        "event_uniqueness_10d_p10",
        "cross_family_collision_10d_rate",
        "cell_sample_status",
        "experiment_a_source_caveat",
        "t4_t7_source_rule",
    ]
    return out[columns].sort_values(["split", "transition_score"], ascending=[True, False])


def build_compression_arm_hypothesis(frontier: pd.DataFrame) -> pd.DataFrame:
    if frontier.empty:
        return pd.DataFrame(
            [
                {
                    "compression_arm_id": "not_available",
                    "compression_source_status": "aggregate_frontier_not_available",
                    "event_membership_status": "not_available",
                    "recommendation": "rebuild selected-event membership before using compression arms",
                }
            ]
        )
    out = frontier.copy()
    out["compression_source_status"] = "aggregate_frontier_only_no_event_membership"
    out["event_membership_status"] = "not_reconstructable_in_experiment_a"
    out["role_in_b"] = "hypothesis_only"
    keep = [
        "compression_arm_id",
        "canonical_event_count",
        "density_vs_e1_full_denominator",
        "density_full_denominator",
        "events_per_instrument_year_p95",
        "train_risk_on_incremental_recall_over_e1",
        "robustness_risk_on_incremental_recall_over_e1",
        "gate_status",
        "failure_reason",
        "compression_source_status",
        "event_membership_status",
        "role_in_b",
    ]
    for col in keep:
        if col not in out.columns:
            out[col] = np.nan
    return out[keep].sort_values("density_vs_e1_full_denominator")


def build_design_recommendations(perf: pd.DataFrame, decision: str) -> pd.DataFrame:
    transition = build_transition_reselection_matrix(perf)
    primary = transition[transition["transition_reselection_role"].eq("transition_primary_candidate")]
    primary_families = ";".join(primary["family_id"].dropna().astype(str).unique())
    t4_rows = transition[transition["candidate_scope_id"].isin(["08_T4_gated", "08_T7_gated"])]
    t4_fast_fail = t4_rows["fast_fail_10d_rate"].dropna().mean()
    rows = [
        {
            "recommendation_id": "transition_reselection",
            "target_experiment": "Experiment C / later transition family decomposition",
            "recommendation": (
                f"Use {primary_families or 'no_primary_candidate'} as transition candidates; "
                "keep T4/T7 as quality-filter or negative-control context."
            ),
            "evidence": "transition split recall/bridge plus fast-fail diagnostics",
            "status": "source_caveated_design_recommendation",
        },
        {
            "recommendation_id": "r_core_deoverlap",
            "target_experiment": "Experiment C",
            "recommendation": "Evaluate R-family de-overlap, cooldown, top-k, or ranker before any R-core union.",
            "evidence": "R individual scopes are sparse but R-core rolling 10d duplicate is high.",
            "status": "required_before_direct_entry",
        },
        {
            "recommendation_id": "t4_t7_quality_filter",
            "target_experiment": "Transition signal repair",
            "recommendation": "Use 08_T4_gated / 08_T7_gated only as challenged incumbents unless quality filters reduce fast-fail.",
            "evidence": f"mean transition T4/T7 fast_fail_10d_rate={t4_fast_fail:.4f}"
            if not pd.isna(t4_fast_fail)
            else "T4/T7 fast-fail evidence unavailable",
            "status": "quality_filter_required",
        },
        {
            "recommendation_id": "density_granularity",
            "target_experiment": "Any downstream use of B matrix",
            "recommendation": "Treat scope-level density as scope-level only; do not infer split/regime density.",
            "evidence": "candidate_10d_density_summary.csv has no split/regime columns.",
            "status": "contract_constraint",
        },
        {
            "recommendation_id": "final_decision",
            "target_experiment": "B publication",
            "recommendation": f"Publish with final decision {decision}.",
            "evidence": "Experiment A is partial-source and retention is pre-replay only.",
            "status": decision,
        },
    ]
    return pd.DataFrame(rows)


def decide(a_manifest: dict[str, Any], perf: pd.DataFrame, input_failures: list[str]) -> str:
    if any("density_fast_fail_caliber_contract" in failure for failure in input_failures):
        return DECISION_CONTRACT_BLOCKED
    if input_failures:
        return DECISION_INPUT_BLOCKED
    if a_manifest.get("decision") not in ALLOWED_A_DECISIONS:
        return DECISION_INPUT_BLOCKED
    has_pre_replay = perf["retention_source_status"].eq("pre_replay_capture_only").any()
    if a_manifest.get("decision") == A_DECISION_PARTIAL or has_pre_replay:
        return DECISION_SOURCE_CAVEATED
    transition = build_transition_reselection_matrix(perf)
    if transition["transition_reselection_role"].eq("transition_primary_candidate").sum() == 0:
        return DECISION_TRANSITION_INCONCLUSIVE
    return DECISION_COMPLETE


def build_waiting_report(decision: str, input_audit_frame: pd.DataFrame) -> str:
    missing = input_audit_frame[input_audit_frame["status"].ne("ok")][
        ["input_id", "input_kind", "status", "missing_required_columns"]
    ].copy()
    lines = [
        "# Regime x Event-Family Performance Matrix Planning Report",
        "",
        f"Final decision: `{decision}`",
        "",
        "This is a schema / planning pass only. It does not emit family support claims.",
        "",
        "## Input Status",
        "",
    ]
    if missing.empty:
        lines.append("All declared inputs are available.")
    else:
        lines.append(missing.to_markdown(index=False))
    return "\n".join(lines)


def build_report(
    decision: str,
    perf: pd.DataFrame,
    transition: pd.DataFrame,
    collision: pd.DataFrame,
    a_manifest: dict[str, Any],
) -> str:
    def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
        if frame.empty:
            return "No rows available."
        available = [col for col in columns if col in frame.columns]
        if not available:
            return "No requested columns available."
        return frame[available].head(max_rows).to_markdown(index=False)

    def regime_top(regime: str) -> pd.DataFrame:
        rows = perf[
            perf["market_regime_bucket"].eq(regime)
            & perf["split"].isin(["train", "robustness", "validation"])
        ].copy()
        rows["sort_recall"] = rows["pre_replay_any_recall"].fillna(-1)
        rows["sort_bridge"] = rows["pre_replay_bridge_recall"].fillna(-1)
        return rows.sort_values(
            ["split", "sort_recall", "sort_bridge"],
            ascending=[True, False, False],
        )

    def role_matrix() -> pd.DataFrame:
        rows = perf[
            perf["split"].isin(["train", "robustness"])
            & perf["market_regime_bucket"].isin(["risk_off", "risk_on", "transition"])
        ].copy()
        return (
            rows.groupby(
                ["market_regime_bucket", "family_regime_role_recommendation"],
                dropna=False,
            )
            .size()
            .reset_index(name="cell_count")
            .sort_values(["market_regime_bucket", "cell_count"], ascending=[True, False])
        )

    all_all = perf[perf["split"].eq("all") & perf["market_regime_bucket"].eq("all")]
    e1 = all_all[all_all["candidate_scope_id"].eq("07_E1_only")]
    t4 = perf[
        perf["candidate_scope_id"].eq("08_selected_T4_T7_union")
        & perf["market_regime_bucket"].eq("transition")
        & perf["split"].isin(["train", "robustness", "validation"])
    ]
    primary = transition[transition["transition_reselection_role"].eq("transition_primary_candidate")]
    rcore = all_all[all_all["candidate_scope_id"].eq("08_R_core_event_regime_gated")]
    sample_summary = (
        perf.groupby(["split", "market_regime_bucket", "cell_sample_status"], dropna=False)
        .size()
        .reset_index(name="cell_count")
        .sort_values(["split", "market_regime_bucket", "cell_sample_status"])
    )
    density_summary = all_all[
        all_all["candidate_scope_id"].isin(
            [
                "07_E1_only",
                "07_full_union",
                "08_selected_T4_T7_union",
                "08_R_core_event_regime_gated",
                "08_R1_event_regime_gated",
                "08_R2_event_regime_gated",
                "08_R6_event_regime_gated",
                "08_R7_event_regime_gated",
                "08_R8_event_regime_gated",
            ]
        )
    ].copy()
    t4_individual = perf[
        perf["candidate_scope_id"].isin(["08_T4_gated", "08_T7_gated"])
        & perf["market_regime_bucket"].eq("transition")
        & perf["split"].isin(["train", "robustness", "validation"])
    ].copy()
    fast_fail_source_summary = (
        perf.groupby(
            [
                "label_source_column",
                "fast_fail_definition_id",
                "label_mapping_status",
                "event_level_label_source_status",
                "fast_fail_diagnostic_label_usage",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="cell_count")
        .sort_values("cell_count", ascending=False)
    )
    small_cells = perf[
        perf["cell_sample_status"].isin(["diagnostic_only", "low_power_caution"])
        & perf["split"].isin(["train", "robustness", "validation"])
    ].copy()

    lines = [
        "# Regime x Event-Family Performance Matrix Report",
        "",
        f"Final decision: `{decision}`",
        "",
        "## One-Page Conclusion",
        "",
        (
            f"Experiment A decision is `{a_manifest.get('decision', '')}`; B therefore publishes "
            "a source-caveated design matrix rather than direct-entry support."
        ),
        (
            "Scope-level density is joined into split/regime cells with "
            "`density_granularity = scope_level_only`; B does not recompute split/regime density."
        ),
        (
            "All support language is diagnostic design language only. This run does not emit "
            "direct-entry support, because retention is pre-replay capture only."
        ),
    ]
    if not e1.empty:
        row = e1.iloc[0]
        lines.append(
            f"E1 remains the sparse baseline: fast-fail {pct(row['fast_fail_10d_rate'])}, "
            f"rolling 10d duplicate {pct(row['rolling_10d_duplicate_rate'])}."
        )
    if not rcore.empty:
        row = rcore.iloc[0]
        lines.append(
            f"R-core remains collision diagnostic only: rolling 10d duplicate "
            f"{pct(row['rolling_10d_duplicate_rate'])}, uniqueness p10 "
            f"{row['event_uniqueness_10d_p10']:.3f}."
        )
    if not t4.empty:
        train = t4[t4["split"].eq("train")]
        if not train.empty:
            row = train.iloc[0]
            lines.append(
                f"T4/T7 transition train recall is weak: pre-replay any recall "
                f"{pct(row['pre_replay_any_recall'])}, bridge {pct(row['pre_replay_bridge_recall'])}, "
                f"fast-fail {pct(row['fast_fail_10d_rate'])}."
            )
    if not primary.empty:
        primary_pairs = ", ".join(
            f"{r.family_id} ({r.split})" for r in primary.itertuples(index=False)
        )
        lines.append(
            "Transition primary candidates under B diagnostics: "
            f"{primary_pairs}. These require quality filters because fast-fail remains "
            "a label-derived cost, not an entry feature."
        )
    else:
        lines.append("No transition primary candidate cleared all diagnostics without caveat.")

    lines.extend(
        [
            "",
            "## Experiment A Alignment Summary",
            "",
            markdown_table(
                density_summary.sort_values("candidate_scope_id"),
                [
                    "candidate_scope_id",
                    "event_n",
                    "pre_replay_any_recall",
                    "pre_replay_bridge_recall",
                    "rolling_10d_duplicate_rate",
                    "event_uniqueness_10d_p10",
                    "fast_fail_10d_rate",
                    "false_repair_20d_rate",
                    "experiment_a_source_caveat",
                ],
                max_rows=12,
            ),
            "",
            "## Sample And Source Guardrails",
            "",
            "- Retention is `pre_replay_capture_only`; post-replay recall fields remain empty.",
            "- `08_T4_gated` / `08_T7_gated` recall and bridge are read from Experiment A retention.",
            "- T4/T7 incremental recall may be `not_available_publishable_source` and does not source-block by itself.",
            "- R compression arms are aggregate-only hypotheses until selected-event membership is rebuilt.",
            "",
            markdown_table(
                sample_summary,
                ["split", "market_regime_bucket", "cell_sample_status", "cell_count"],
                max_rows=24,
            ),
            "",
            "## Family Role Matrix By Regime",
            "",
            markdown_table(
                role_matrix(),
                ["market_regime_bucket", "family_regime_role_recommendation", "cell_count"],
                max_rows=24,
            ),
            "",
            "## Risk-Off Findings",
            "",
            (
                "Risk-off cells are treated conservatively. E1 remains the clean repair baseline; "
                "other families need bridge evidence without adding fast-fail cost."
            ),
            "",
            markdown_table(
                regime_top("risk_off"),
                [
                    "split",
                    "family_id",
                    "candidate_scope_id",
                    "pre_replay_any_recall",
                    "pre_replay_bridge_recall",
                    "fast_fail_10d_rate",
                    "cell_sample_status",
                    "family_regime_role_recommendation",
                ],
                max_rows=12,
            ),
            "",
            "## Risk-On Findings",
            "",
            (
                "Risk-on R families carry strong pre-replay recall, but raw R-core is not a "
                "support candidate because the union creates cross-family 10d collision."
            ),
            "",
            markdown_table(
                regime_top("risk_on"),
                [
                    "split",
                    "family_id",
                    "candidate_scope_id",
                    "pre_replay_any_recall",
                    "pre_replay_bridge_recall",
                    "fast_fail_10d_rate",
                    "rolling_10d_duplicate_rate",
                    "family_regime_role_recommendation",
                ],
                max_rows=12,
            ),
            "",
            "## Transition Findings",
            "",
            (
                "T4/T7 is retained as a challenged incumbent, not the default transition answer. "
                "R6 is the strongest transition candidate in train and robustness by recall/bridge, "
                "but it still needs de-overlap and quality filtering before any downstream entry design."
            ),
        ]
    )
    trans_cols = [
        "split",
        "family_id",
        "candidate_scope_id",
        "transition_reselection_role",
        "pre_replay_any_recall",
        "pre_replay_bridge_recall",
        "fast_fail_10d_rate",
        "cell_sample_status",
        "experiment_a_source_caveat",
    ]
    trans_head = transition[
        transition["split"].isin(["train", "robustness", "validation"])
    ].copy()
    trans_head["split_order"] = trans_head["split"].map(
        {"train": 0, "robustness": 1, "validation": 2}
    )
    trans_head = trans_head.sort_values(
        ["split_order", "transition_score"],
        ascending=[True, False],
    )
    lines.append(trans_head[trans_cols].head(12).to_markdown(index=False))
    lines.extend(
        [
            "",
            "## T4 / T7 Individual-Vs-Union Caveat",
            "",
            (
                "`08_selected_T4_T7_union` is union context only. Individual roles use "
                "`08_T4_gated` and `08_T7_gated`, whose recall and bridge fields come from "
                "`candidate_10d_retention_by_split_regime.csv`."
            ),
            "",
            markdown_table(
                t4_individual,
                [
                    "split",
                    "candidate_scope_id",
                    "pre_replay_any_recall",
                    "pre_replay_bridge_recall",
                    "incremental_recall_over_e1",
                    "incremental_recall_source_status",
                    "fast_fail_10d_rate",
                    "transition_reselection_role",
                ],
                max_rows=12,
            ),
            "",
            "## Density / Fast-Fail / Uniqueness",
            "",
            (
                "Density fields are scope-level only: `events_per_instrument_year_mean`, "
                "`events_per_instrument_year_p95`, and `rolling_10d_duplicate_rate` are joined "
                "by scope id and marked with `density_cell_recomputed_flag = False`. "
                "Fast-fail 10d and false-repair 20d are label-derived diagnostics only."
            ),
            "",
            markdown_table(
                density_summary.sort_values("fast_fail_10d_rate", ascending=False),
                [
                    "candidate_scope_id",
                    "events_per_instrument_year_mean",
                    "events_per_instrument_year_p95",
                    "rolling_10d_duplicate_rate",
                    "density_granularity",
                    "density_cell_recomputed_flag",
                    "fast_fail_10d_rate",
                    "false_repair_20d_rate",
                    "event_uniqueness_10d_p10",
                ],
                max_rows=12,
            ),
            "",
            "## Fast-Fail Diagnostic Source Fields",
            "",
            (
                "`fast_fail_10d_*` and `false_repair_20d_*` are aggregate diagnostic labels. "
                "The table below exposes `label_source_column`, `fast_fail_definition_id`, "
                "`label_mapping_status`, and `event_level_label_source_status`; these fields are "
                "not t0 entry features."
            ),
            "",
            markdown_table(
                fast_fail_source_summary,
                [
                    "label_source_column",
                    "fast_fail_definition_id",
                    "label_mapping_status",
                    "event_level_label_source_status",
                    "fast_fail_diagnostic_label_usage",
                    "cell_count",
                ],
                max_rows=12,
            ),
            "",
            "",
            "## R-Core Collision",
            "",
        ]
    )
    if not collision.empty:
        lines.append(
            collision[
                [
                    "family_id",
                    "split",
                    "market_regime_bucket",
                    "r_core_rolling_10d_duplicate_rate",
                    "collision_interpretation",
                ]
            ]
            .head(12)
            .to_markdown(index=False)
        )
    else:
        lines.append("No R-core collision rows were available.")
    lines.extend(
        [
            "",
            "## Retention Source Caveat",
            "",
            (
                "Experiment A retention is `pre_replay_capture_only`. Therefore "
                "`post_replay_any_recall` and `post_replay_bridge_recall` remain null, and B "
                "cannot claim that any family survives a post-fast-fail or post-filter replay."
            ),
            "",
            "## Compression-Arm Hypothesis",
            "",
            (
                "R-series compression arms are retained only as aggregate hypotheses. They are "
                "not used in family role classification because selected-event membership is not "
                "available in a publishable source."
            ),
            "",
            "## Small-Cell Caveats",
            "",
            markdown_table(
                small_cells.sort_values(
                    ["split", "market_regime_bucket", "candidate_scope_id"]
                ),
                [
                    "split",
                    "market_regime_bucket",
                    "candidate_scope_id",
                    "episode_denominator_n",
                    "bridge_denominator_n",
                    "experiment_a_cell_sample_status",
                    "computed_cell_sample_status",
                    "cell_sample_status",
                    "cell_sample_status_resolution",
                ],
                max_rows=16,
            ),
            "",
            "## Experiment C Recommendations",
            "",
            "- Rebuild transition-family decomposition around R6 first, with fast-fail quality filters.",
            "- Keep T4/T7 as challenged incumbent and negative-control context until quality filters improve it.",
            "- Do not use R-core union directly; evaluate cooldown, top-k, de-overlap, or a positive ranker.",
            "- Treat fast-fail 10d / false-repair 20d as diagnostic labels and rejector targets, not t0 entry features.",
            "",
            "## Output Contract Notes",
            "",
            "- `regime_family_performance_matrix.csv` is the master cell matrix.",
            "- `regime_family_density_fast_fail_matrix.csv` carries scope-level density caveats.",
            "- `transition_event_family_reselection_matrix.csv` contains transition-specific roles.",
            "- `regime_family_design_recommendations.csv` contains downstream design actions.",
        ]
    )
    return "\n".join(lines)


def build_manifest(
    decision: str,
    output_paths: dict[str, Path],
    input_audit_frame: pd.DataFrame,
    a_manifest: dict[str, Any],
    frames: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    return {
        "experiment_id": "08_experiment_b_regime_family_matrix",
        "run_id": stable_hash(
            {
                "experiment": "regime_family_matrix",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "experiment_a_decision": a_manifest.get("decision", ""),
        "runner_code_hash": path_hash(Path(__file__)),
        "requirement_hash": path_hash(REQUIREMENT_PATH),
        "density_granularity_policy": "scope_level_density_join_only_no_split_regime_recompute",
        "retention_policy": "pre_replay_capture_only_is_source_caveated",
        "input_artifacts": input_audit_frame.to_dict(orient="records"),
        "output_hashes": {
            key: path_hash(path)
            for key, path in sorted(output_paths.items())
            if key != "regime_family_matrix_manifest" and path.exists()
        },
        "output_paths": {key: str(path) for key, path in sorted(output_paths.items())},
        "output_row_counts": {key: int(len(frame)) for key, frame in frames.items()},
    }


def output_paths() -> dict[str, Path]:
    return {
        "regime_family_experiment_a_alignment": B_TABLE_DIR
        / "regime_family_experiment_a_alignment.csv",
        "regime_family_performance_matrix": B_TABLE_DIR
        / "regime_family_performance_matrix.csv",
        "regime_family_sample_guardrail": B_TABLE_DIR / "regime_family_sample_guardrail.csv",
        "regime_family_density_fast_fail_matrix": B_TABLE_DIR
        / "regime_family_density_fast_fail_matrix.csv",
        "regime_family_fast_fail_diagnostic_matrix": B_TABLE_DIR
        / "regime_family_fast_fail_diagnostic_matrix.csv",
        "regime_family_bridge_recall_matrix": B_TABLE_DIR
        / "regime_family_bridge_recall_matrix.csv",
        "regime_family_overlap_concentration_matrix": B_TABLE_DIR
        / "regime_family_overlap_concentration_matrix.csv",
        "regime_family_cross_family_collision_matrix": B_TABLE_DIR
        / "regime_family_cross_family_collision_matrix.csv",
        "regime_family_retention_source_status": B_TABLE_DIR
        / "regime_family_retention_source_status.csv",
        "transition_event_family_reselection_matrix": B_TABLE_DIR
        / "transition_event_family_reselection_matrix.csv",
        "regime_family_compression_arm_hypothesis": B_TABLE_DIR
        / "regime_family_compression_arm_hypothesis.csv",
        "regime_family_design_recommendations": B_TABLE_DIR
        / "regime_family_design_recommendations.csv",
        "regime_family_matrix_report": B_REPORT_DIR / "regime_family_matrix_report.md",
        "regime_family_matrix_manifest": B_MANIFEST_DIR
        / "regime_family_matrix_manifest.json",
        "input_artifact_audit": B_TABLE_DIR / "input_artifact_audit.csv",
    }


def run_matrix(planning_pass: bool = False) -> dict[str, Any]:
    ensure_dirs()
    input_frame, input_failures, resolved = input_audit()
    paths = output_paths()
    write_df(paths["input_artifact_audit"], input_frame)

    a_manifest: dict[str, Any] = {}
    if resolved["density_fast_fail_audit_manifest"].exists():
        a_manifest = load_json(resolved["density_fast_fail_audit_manifest"])

    if input_failures:
        decision = (
            DECISION_CONTRACT_BLOCKED
            if any("density_fast_fail_caliber_contract" in failure for failure in input_failures)
            else DECISION_WAITING
            if planning_pass
            else DECISION_INPUT_BLOCKED
        )
        if decision == DECISION_WAITING:
            write_text(paths["regime_family_matrix_report"], build_waiting_report(decision, input_frame))
        write_json(
            paths["regime_family_matrix_manifest"],
            build_manifest(decision, paths, input_frame, a_manifest, {}),
        )
        return {"decision": decision, "manifest_path": str(paths["regime_family_matrix_manifest"])}

    tables = {
        "candidate_10d_density_summary": read_csv(resolved["candidate_10d_density_summary"]),
        "candidate_10d_uniqueness_diagnostic": read_csv(
            resolved["candidate_10d_uniqueness_diagnostic"]
        ),
        "candidate_adjacent_event_gap_diagnostic": read_csv(
            resolved["candidate_adjacent_event_gap_diagnostic"]
        ),
        "candidate_10d_fast_fail_readout": read_csv(
            resolved["candidate_10d_fast_fail_readout"]
        ),
        "candidate_10d_retention_by_split_regime": read_csv(
            resolved["candidate_10d_retention_by_split_regime"]
        ),
        "candidate_scope_reconstructability_audit": read_csv(
            resolved["candidate_scope_reconstructability_audit"]
        ),
        "candidate_density_caliber_crosswalk": read_csv(
            resolved["candidate_density_caliber_crosswalk"]
        ),
        "candidate_family_incremental_recall_over_e1": read_csv(
            resolved["candidate_family_incremental_recall_over_e1"]
        ),
        "candidate_family_label_quality_readout": read_csv(
            resolved["candidate_family_label_quality_readout"]
        ),
        "candidate_family_overlap_matrix": read_csv(resolved["candidate_family_overlap_matrix"]),
        "topn_channel_recall_contribution": read_csv(
            resolved["topn_channel_recall_contribution"]
        ),
        "topn_channel_density_summary": read_csv(resolved["topn_channel_density_summary"]),
        "topn_false_repair_diagnostic": read_csv(resolved["topn_false_repair_diagnostic"]),
        "r_series_compression_frontier": read_optional_csv(
            resolved["r_series_compression_frontier"]
        ),
    }

    perf = build_performance_matrix(tables)
    decision = decide(a_manifest, perf, input_failures)
    transition = build_transition_reselection_matrix(perf)
    collision = build_cross_family_collision_matrix(perf)

    frames = {
        "regime_family_experiment_a_alignment": build_experiment_a_alignment(
            perf, a_manifest, input_frame
        ),
        "regime_family_performance_matrix": perf,
        "regime_family_sample_guardrail": build_sample_guardrail(perf),
        "regime_family_density_fast_fail_matrix": build_density_fast_fail_matrix(perf),
        "regime_family_fast_fail_diagnostic_matrix": build_fast_fail_diagnostic_matrix(perf),
        "regime_family_bridge_recall_matrix": build_bridge_recall_matrix(perf),
        "regime_family_overlap_concentration_matrix": build_overlap_concentration_matrix(
            tables["candidate_family_overlap_matrix"]
        ),
        "regime_family_cross_family_collision_matrix": collision,
        "regime_family_retention_source_status": build_retention_source_status(perf),
        "transition_event_family_reselection_matrix": transition,
        "regime_family_compression_arm_hypothesis": build_compression_arm_hypothesis(
            tables["r_series_compression_frontier"]
        ),
        "regime_family_design_recommendations": build_design_recommendations(perf, decision),
    }
    for key, frame in frames.items():
        write_df(paths[key], frame)
    write_text(
        paths["regime_family_matrix_report"],
        build_report(decision, perf, transition, collision, a_manifest),
    )
    write_json(
        paths["regime_family_matrix_manifest"],
        build_manifest(decision, paths, input_frame, a_manifest, frames),
    )
    return {
        "decision": decision,
        "performance_rows": len(perf),
        "transition_rows": len(transition),
        "manifest_path": str(paths["regime_family_matrix_manifest"]),
        "report_path": str(paths["regime_family_matrix_report"]),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_dirs()
    if args.mode == "check-inputs":
        input_frame, failures, _ = input_audit()
        write_df(B_TABLE_DIR / "input_artifact_audit.csv", input_frame)
        print(f"input_failures={len(failures)}")
        for failure in failures:
            print(failure)
        return 1 if failures else 0
    result = run_matrix(planning_pass=args.mode == "planning-pass")
    print(f"decision={result['decision']}")
    if "performance_rows" in result:
        print(f"performance_rows={result['performance_rows']}")
        print(f"transition_rows={result['transition_rows']}")
    print(f"manifest={result['manifest_path']}")
    if "report_path" in result:
        print(f"report={result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

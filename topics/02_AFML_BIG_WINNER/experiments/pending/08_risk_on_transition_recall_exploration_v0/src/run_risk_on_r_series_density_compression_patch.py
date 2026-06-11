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

import pipeline  # noqa: E402
from afml_big_winner.config import stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402


PATCH_REQUIREMENT = EXPERIMENT_DIR / "requirement_patch_risk_on_r_series_density_compression.md"
DEFAULT_SOURCE_MANIFEST = EXPERIMENT_DIR / "outputs" / "manifests" / "run_manifest.json"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"
PATCH_TABLE_DIR = TABLE_DIR / "risk_on_r_series_density_compression"
PATCH_REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports" / "risk_on_r_series_density_compression"
PATCH_MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests" / "risk_on_r_series_density_compression"
PATCH_CACHE_DIR = LOCAL_CACHE_DIR / "risk_on_r_series_density_compression"

WINDOW = "before_first_50pct"
RISK_ON = "risk_on"
E1_SCOPE = "07_e1_only"
FULL_07_SCOPE = "07_full_union"
SOURCE_VARIANT_POLICY = "event_regime_gated_first"
UNSCORED_CANONICAL_POLICY = "retain_and_audit"
RAW_R_POOL_DEFINITION = (
    "canonical union of runnable candidate_family_variant events from R1,R6,R7,R8,R2 before any compression"
)

CORE_FAMILIES = [
    "R1_relative_strength_breakout",
    "R6_market_breadth_thrust",
    "R7_cross_sectional_momentum_rank_jump",
    "R8_persistent_distance_above_ema",
    "R2_near_high_volume_expansion",
]
OPTIONAL_FAMILIES = ["R3_vcp_breakout"]
NEGATIVE_CONTROL_FAMILY = "R5_growth_or_small_style_confirmation"
R2_FAMILY = "R2_near_high_volume_expansion"

AVAILABLE_SCORE_SOURCE_COLUMNS = [
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "stock_vs_market_20d",
    "close_to_high_60",
    "rolling_high_60",
    "new_high_60_flag",
    "momentum_percentile_20d",
    "momentum_percentile_60d",
    "momentum_percentile_20d_lag20",
    "universe_up_share",
    "universe_new_high_60_share",
    "universe_up_share_z",
    "universe_up_share_change_5d",
    "board_relative_1d",
    "board_relative_cusum_20d",
    "board_return_20d",
    "stock_vs_board_20d",
]
FROZEN_FEATURE_PANEL_COLUMNS = [
    "date",
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "stock_vs_market_20d",
    "close_to_high_60",
    "rolling_high_60",
    "close",
    "market_regime_bucket",
    "instrument",
    "board_bucket",
    "total_market_cap_cny",
    "history_observed_sessions_before_usable_date",
    "momentum_percentile_20d",
    "momentum_percentile_60d",
    "new_high_60_flag",
    "up_flag",
    "momentum_percentile_20d_lag20",
    "evaluated_member_count",
    "universe_up_share",
    "universe_new_high_60_share",
    "universe_equal_weight_return_x",
    "universe_up_share_z",
    "universe_up_share_change_5d",
    "board_equal_weight_return",
    "universe_equal_weight_return_y",
    "board_relative_1d",
    "board_relative_cusum_20d",
    "board_return_20d",
    "stock_vs_board_20d",
]

SCORE_SPECS: dict[str, list[dict[str, Any]]] = {
    "R1_relative_strength_breakout": [
        {"score_field_name": "stock_vs_market_20d", "source_column": "stock_vs_market_20d"},
        {"score_field_name": "stock_vs_board_20d", "source_column": "stock_vs_board_20d"},
        {"score_field_name": "return_60d", "source_column": "return_60d"},
    ],
    "R6_market_breadth_thrust": [
        {"score_field_name": "universe_up_share_z", "source_column": "universe_up_share_z"},
        {
            "score_field_name": "universe_up_share_change_5d",
            "source_column": "universe_up_share_change_5d",
        },
    ],
    "R7_cross_sectional_momentum_rank_jump": [
        {"score_field_name": "momentum_percentile_20d", "source_column": "momentum_percentile_20d"},
        {
            "score_field_name": "momentum_percentile_20d_delta",
            "source_column": "momentum_percentile_20d;momentum_percentile_20d_lag20",
            "derived": "momentum_percentile_20d_minus_lag20",
        },
    ],
    "R8_persistent_distance_above_ema": [
        {"score_field_name": "return_60d", "source_column": "return_60d"},
        {"score_field_name": "momentum_percentile_60d", "source_column": "momentum_percentile_60d"},
        {"score_field_name": "close_to_high_60", "source_column": "close_to_high_60"},
    ],
    "R3_vcp_breakout": [
        {"score_field_name": "close_to_high_60", "source_column": "close_to_high_60"},
    ],
}

REQUIRED_SOURCE_TABLES = {
    "candidate_family_event_instances": TABLE_DIR / "candidate_family_event_instances.csv",
    "candidate_family_canonical_events": TABLE_DIR / "candidate_family_canonical_events.csv",
    "candidate_family_incremental_recall_over_e1": TABLE_DIR / "candidate_family_incremental_recall_over_e1.csv",
    "candidate_family_bridge_positive_recall": TABLE_DIR / "candidate_family_bridge_positive_recall.csv",
    "candidate_family_bridge_exclusion_audit": TABLE_DIR / "candidate_family_bridge_exclusion_audit.csv",
    "candidate_family_density_summary": TABLE_DIR / "candidate_family_density_summary.csv",
    "candidate_family_label_quality_readout": TABLE_DIR / "candidate_family_label_quality_readout.csv",
    "candidate_family_false_repair_diagnostic": TABLE_DIR / "candidate_family_false_repair_diagnostic.csv",
    "candidate_family_overlap_matrix": TABLE_DIR / "candidate_family_overlap_matrix.csv",
    "candidate_family_cluster_ablation": TABLE_DIR / "candidate_family_cluster_ablation.csv",
    "candidate_vs_e1_timing_basis_comparison": TABLE_DIR / "candidate_vs_e1_timing_basis_comparison.csv",
    "candidate_family_run_capability_summary": TABLE_DIR / "candidate_family_run_capability_summary.csv",
    "regime_recall_baseline_07_e1_only": TABLE_DIR / "regime_recall_baseline_07_e1_only.csv",
}
LOCAL_CACHE_INPUTS = {
    "candidate_family_event_labels": LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet",
    "candidate_family_capture": LOCAL_CACHE_DIR / "candidate_family_capture.parquet",
    "cross_section_feature_panel": LOCAL_CACHE_DIR / "cross_section_feature_panel.parquet",
}

OUTPUT_TABLE_NAMES = [
    "risk_on_r_series_density_binding_preflight",
    "risk_on_r_series_score_spec",
    "risk_on_r_series_source_pool_summary",
    "risk_on_r_series_compression_frontier",
    "risk_on_r_series_selected_compressed_variants",
    "risk_on_r_series_compressed_canonical_events",
    "risk_on_r_series_recall_bridge_density_by_split",
    "risk_on_r_series_threshold_sensitivity",
    "risk_on_r_series_label_quality_readout",
    "risk_on_r_series_overlap_diagnostic",
    "risk_on_r_series_gate_summary",
]

TRAIN_BRIDGE_DELTA_MIN = 0.05
ROBUSTNESS_BRIDGE_DELTA_MIN = 0.05
RECALL_MIN = 0.08
DENSITY_VS_E1_MAX = 1.00
P95_MAX = 4.0
LABEL_COMPLETENESS_MIN = 0.70
NEXT_OPEN_EXECUTABLE_MIN = 0.95
SINGLE_FAMILY_SHARE_MAX = 0.65
DOWNSTREAM_FAMILY_SHARE_MAX = 0.35
VALIDATION_RISK_ON_SMALL_DENOMINATOR = 30


@dataclass(frozen=True)
class ArmResult:
    arm_id: str
    events: pd.DataFrame
    selected: bool = False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 08 risk-on R-series density compression patch.")
    parser.add_argument("--source-manifest", default=str(DEFAULT_SOURCE_MANIFEST), help="Source 08 run manifest.")
    parser.add_argument(
        "--mode",
        choices=["check-drift", "full"],
        default="full",
        help="Check code/requirement alignment or run patch.",
    )
    return parser.parse_args(argv)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.1f}%"


def num(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0:
        return np.nan
    return float(numerator) / float(denominator)


def split_semicolon(value: Any) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [item for item in str(value).split(";") if item]


def collect_hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {key: file_sha256(path) for key, path in sorted(paths.items()) if path.exists()}


def artifact_metadata(paths: dict[str, Path], frames: dict[str, pd.DataFrame] | None = None) -> dict[str, Any]:
    frames = frames or {}
    out: dict[str, Any] = {}
    for key, path in sorted(paths.items()):
        item: dict[str, Any] = {
            "path": str(path.resolve()),
            "sha256": file_sha256(path) if path.exists() else "",
        }
        frame = frames.get(key)
        if frame is not None:
            item["row_count"] = int(len(frame))
            item["column_schema"] = pipeline.frame_schema(frame)
        out[key] = item
    return out


def validate_input_gate(source_manifest_path: Path) -> tuple[str, list[str], dict[str, Path], dict[str, Any]]:
    reasons: list[str] = []
    input_paths = {"source_08_manifest": source_manifest_path, "patch_requirement": PATCH_REQUIREMENT}
    input_paths.update(REQUIRED_SOURCE_TABLES)
    input_paths.update(LOCAL_CACHE_INPUTS)

    if not source_manifest_path.exists():
        reasons.append("source_manifest_missing")
        source_manifest: dict[str, Any] = {}
    else:
        source_manifest = read_json(source_manifest_path)
        if source_manifest.get("run_scope") != "full":
            reasons.append("source_manifest_not_full")

    for key, path in REQUIRED_SOURCE_TABLES.items():
        if not path.exists():
            reasons.append(f"required_table_missing:{key}")
    for key, path in LOCAL_CACHE_INPUTS.items():
        if not path.exists():
            reasons.append(f"local_cache_missing:{key}")
    if not PATCH_REQUIREMENT.exists():
        reasons.append("patch_requirement_missing")

    source_hashes = source_manifest.get("output_hashes", {}) if source_manifest else {}
    hash_key_map = {
        "candidate_family_event_instances": "candidate_event_instances",
        "candidate_family_canonical_events": "candidate_canonical_events",
        "candidate_family_incremental_recall_over_e1": "incremental_recall",
        "candidate_family_bridge_positive_recall": "bridge_positive_recall",
        "candidate_family_bridge_exclusion_audit": "bridge_exclusion_audit",
        "candidate_family_density_summary": "density_summary",
        "candidate_family_label_quality_readout": "label_quality",
        "candidate_family_false_repair_diagnostic": "false_repair_diagnostic",
        "candidate_family_overlap_matrix": "overlap_matrix",
        "candidate_family_cluster_ablation": "cluster_ablation",
        "candidate_vs_e1_timing_basis_comparison": "timing_basis_comparison",
        "candidate_family_run_capability_summary": "run_capability",
        "regime_recall_baseline_07_e1_only": "regime_recall_baseline",
        "candidate_family_event_labels": "candidate_labels_local",
        "candidate_family_capture": "candidate_capture_local",
        "cross_section_feature_panel": "feature_panel_local",
    }
    for local_key, manifest_key in hash_key_map.items():
        path = input_paths.get(local_key)
        if not path or not path.exists() or not source_hashes:
            continue
        expected = str(source_hashes.get(manifest_key, ""))
        if expected and file_sha256(path) != expected:
            reasons.append(f"source_hash_mismatch:{local_key}")

    return ("pass" if not reasons else "blocked"), reasons, input_paths, source_manifest


def check_requirement_alignment() -> tuple[bool, list[str]]:
    text = PATCH_REQUIREMENT.read_text(encoding="utf-8")
    failures: list[str] = []
    required_strings = [
        "compression_source_variant_policy = event_regime_gated_first",
        "unscored_canonical_policy = retain_and_audit",
        "robustness risk_on bridge recall delta vs E1 >= `+5 pct`",
        "R2 | non-scored by default",
        "proxy_score_used = true",
        "variant-level spot check",
        "event_big_winner_120d` ranker arm 只能 diagnostic",
    ]
    for value in required_strings:
        if value not in text:
            failures.append(f"requirement_missing_string:{value}")

    unavailable_defaults = {"stock_vs_market_10d", "close_to_ema60", "close_to_ema20", "ema60_positive_run"}
    for specs in SCORE_SPECS.values():
        for spec in specs:
            source_column = str(spec["source_column"])
            for column in source_column.split(";"):
                if column in unavailable_defaults:
                    failures.append(f"default_score_uses_unavailable_column:{column}")
                if column not in AVAILABLE_SCORE_SOURCE_COLUMNS:
                    failures.append(f"default_score_not_in_frozen_panel:{column}")
    if SOURCE_VARIANT_POLICY != "event_regime_gated_first":
        failures.append("source_variant_policy_drift")
    if UNSCORED_CANONICAL_POLICY != "retain_and_audit":
        failures.append("unscored_policy_drift")
    if ROBUSTNESS_BRIDGE_DELTA_MIN != 0.05:
        failures.append("robustness_bridge_gate_drift")
    missing_outputs = [
        name for name in OUTPUT_TABLE_NAMES if name.replace("risk_on_r_series_", "") not in text and name not in text
    ]
    if missing_outputs:
        failures.append("output_table_list_drift:" + ",".join(missing_outputs))
    return not failures, failures


def load_inputs() -> dict[str, pd.DataFrame]:
    return {
        "instances": pd.read_csv(REQUIRED_SOURCE_TABLES["candidate_family_event_instances"], low_memory=False),
        "canonical": pd.read_csv(REQUIRED_SOURCE_TABLES["candidate_family_canonical_events"], low_memory=False),
        "incremental": pd.read_csv(REQUIRED_SOURCE_TABLES["candidate_family_incremental_recall_over_e1"]),
        "bridge": pd.read_csv(REQUIRED_SOURCE_TABLES["candidate_family_bridge_positive_recall"]),
        "bridge_exclusion": pd.read_csv(REQUIRED_SOURCE_TABLES["candidate_family_bridge_exclusion_audit"]),
        "density": pd.read_csv(REQUIRED_SOURCE_TABLES["candidate_family_density_summary"]),
        "label_quality_source": pd.read_csv(REQUIRED_SOURCE_TABLES["candidate_family_label_quality_readout"]),
        "capture": pd.read_parquet(LOCAL_CACHE_INPUTS["candidate_family_capture"]),
        "labels": pd.read_parquet(LOCAL_CACHE_INPUTS["candidate_family_event_labels"]),
        "feature_panel": pd.read_parquet(LOCAL_CACHE_INPUTS["cross_section_feature_panel"]),
    }


def bridge_frame_for_scope(bridge: pd.DataFrame, scope_type: str | None = None) -> pd.DataFrame:
    frame = bridge.loc[
        (bridge["metric_basis"] == "bridge_positive_event")
        & (bridge["market_regime_bucket"] == RISK_ON)
        & (bridge["window"] == WINDOW)
        & (bridge["episode_split"].isin(["train", "robustness"]))
        & (bridge["board_bucket"] == "all")
    ].copy()
    if scope_type is not None:
        frame = frame.loc[frame["candidate_scope_type"] == scope_type].copy()
    return frame


def build_preflight(tables: dict[str, pd.DataFrame], source_hash: str, requirement_hash: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    incremental = tables["incremental"]
    bridge = bridge_frame_for_scope(tables["bridge"])
    density = tables["density"]
    e1_bridge = (
        bridge.loc[bridge["candidate_scope_id"] == E1_SCOPE, ["episode_split", "recall"]]
        .rename(columns={"recall": "e1_bridge_recall"})
        .drop_duplicates()
    )
    scopes = [pipeline.FAMILY_SCOPE, pipeline.FAMILY_VARIANT_SCOPE]
    rows: list[pd.DataFrame] = []
    for scope in scopes:
        inc = incremental.loc[
            (incremental["candidate_scope_type"] == scope)
            & (incremental["family_id"].isin(CORE_FAMILIES + OPTIONAL_FAMILIES + [NEGATIVE_CONTROL_FAMILY]))
            & (incremental["market_regime_bucket"] == RISK_ON)
            & (incremental["window"] == WINDOW)
            & (incremental["episode_split"].isin(["train", "robustness"]))
        ].copy()
        br = bridge.loc[
            (bridge["candidate_scope_type"] == scope)
            & (bridge["family_id"].isin(CORE_FAMILIES + OPTIONAL_FAMILIES + [NEGATIVE_CONTROL_FAMILY]))
        ][["candidate_scope_id", "episode_split", "recall"]].rename(columns={"recall": "bridge_recall"})
        part = inc.merge(br, on=["candidate_scope_id", "episode_split"], how="left")
        part = part.merge(e1_bridge, on="episode_split", how="left")
        part = part.merge(
            density[
                [
                    "candidate_scope_id",
                    "density_vs_e1_full_denominator",
                    "events_per_instrument_year_p95",
                ]
            ],
            on="candidate_scope_id",
            how="left",
        )
        rows.append(part)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    out["bridge_recall_delta_vs_e1"] = out["bridge_recall"] - out["e1_bridge_recall"]
    out["recall_gate_pass"] = out["incremental_recall_over_e1"] >= RECALL_MIN
    out["bridge_gate_pass"] = out["bridge_recall_delta_vs_e1"] >= -0.03
    out["density_binding_flag"] = (
        out["recall_gate_pass"]
        & out["bridge_gate_pass"]
        & (out["density_vs_e1_full_denominator"] > 1.0)
    )
    out["negative_control_flag"] = out["family_id"] == NEGATIVE_CONTROL_FAMILY
    out["family_level_density_binding_flag"] = out["candidate_scope_type"].eq(pipeline.FAMILY_SCOPE) & out[
        "density_binding_flag"
    ]
    out["variant_level_spot_check_flag"] = out["candidate_scope_type"].eq(pipeline.FAMILY_VARIANT_SCOPE)
    out["source_regime_column_name"] = "market_regime_bucket"
    out["source_market_regime_bucket"] = out["market_regime_bucket"]
    out["episode_regime_bucket"] = out["market_regime_bucket"]
    out["source_08_manifest_hash"] = source_hash
    out["patch_requirement_hash"] = requirement_hash

    family_confirmed = set()
    for family, group in out.loc[out["candidate_scope_type"] == pipeline.FAMILY_SCOPE].groupby("family_id"):
        splits = set(group.loc[group["density_binding_flag"], "episode_split"].astype(str))
        if {"train", "robustness"}.issubset(splits):
            family_confirmed.add(family)
    variant_confirmed = set()
    for family, group in out.loc[out["candidate_scope_type"] == pipeline.FAMILY_VARIANT_SCOPE].groupby("family_id"):
        by_scope = group.groupby("candidate_scope_id")
        if any({"train", "robustness"}.issubset(set(g.loc[g["density_binding_flag"], "episode_split"].astype(str))) for _, g in by_scope):
            variant_confirmed.add(family)
    out["variant_level_confirmed_family_flag"] = out["family_id"].isin(variant_confirmed)
    r5 = out.loc[(out["family_id"] == NEGATIVE_CONTROL_FAMILY) & (out["candidate_scope_type"] == pipeline.FAMILY_SCOPE)]
    r5_negative = bool(
        not r5.empty
        and (r5["density_vs_e1_full_denominator"].max() <= 1.0)
        and (r5["bridge_recall_delta_vs_e1"].min() < -0.03)
    )
    decision = (
        "risk_on_r_series_density_binding_confirmed"
        if len(family_confirmed.intersection(CORE_FAMILIES)) >= 4
        and len(variant_confirmed.intersection(CORE_FAMILIES)) >= 4
        and r5_negative
        else "risk_on_r_series_density_binding_not_confirmed"
    )
    summary = {
        "density_binding_preflight_decision": decision,
        "family_level_confirmed_core_count": len(family_confirmed.intersection(CORE_FAMILIES)),
        "variant_level_confirmed_core_count": len(variant_confirmed.intersection(CORE_FAMILIES)),
        "family_level_confirmed_core_families": sorted(family_confirmed.intersection(CORE_FAMILIES)),
        "variant_level_confirmed_core_families": sorted(variant_confirmed.intersection(CORE_FAMILIES)),
        "r5_negative_control_confirmed": r5_negative,
    }
    columns = [
        "candidate_scope_type",
        "candidate_scope_id",
        "family_id",
        "variant_id",
        "episode_split",
        "source_regime_column_name",
        "source_market_regime_bucket",
        "episode_regime_bucket",
        "window",
        "incremental_recall_over_e1",
        "bridge_recall",
        "e1_bridge_recall",
        "bridge_recall_delta_vs_e1",
        "density_vs_e1_full_denominator",
        "events_per_instrument_year_p95",
        "recall_gate_pass",
        "bridge_gate_pass",
        "density_binding_flag",
        "negative_control_flag",
        "family_level_density_binding_flag",
        "variant_level_spot_check_flag",
        "variant_level_confirmed_family_flag",
        "source_08_manifest_hash",
        "patch_requirement_hash",
    ]
    return out[columns].sort_values(["candidate_scope_type", "family_id", "variant_id", "episode_split"]), summary


def build_score_spec(feature_panel: pd.DataFrame, source_hash: str, requirement_hash: str) -> pd.DataFrame:
    available = set(feature_panel.columns)
    rows: list[dict[str, Any]] = []
    for family in CORE_FAMILIES + OPTIONAL_FAMILIES:
        if family == R2_FAMILY:
            rows.append(
                {
                    "score_spec_id": "score_spec_v1",
                    "family_id": family,
                    "variant_id": "event_regime_gated",
                    "score_field_name": "non_scored_volume_unavailable",
                    "source_column": "",
                    "source_column_required_flag": False,
                    "score_direction": "not_applicable",
                    "score_transform": "not_applicable",
                    "normalization_scope": "not_applicable",
                    "missing_policy": "non_scored_core_family_retain_and_audit",
                    "tie_break_policy": "not_score_rank_eligible",
                    "feature_asof_policy": "t0_or_earlier_only",
                    "source_column_presence_status": "not_available",
                    "score_availability_status": "core_semantic_score_unavailable",
                    "proxy_score_used": False,
                    "missing_semantic_feature": "amount_or_volume_expansion",
                    "recompute_required_flag": True,
                    "recomputed_from_source_artifacts": False,
                    "source_08_manifest_hash": source_hash,
                    "patch_requirement_hash": requirement_hash,
                }
            )
            continue
        for spec in SCORE_SPECS.get(family, []):
            source_columns = str(spec["source_column"]).split(";")
            present = all(column in available for column in source_columns)
            rows.append(
                {
                    "score_spec_id": "score_spec_v1",
                    "family_id": family,
                    "variant_id": "event_regime_gated",
                    "score_field_name": spec["score_field_name"],
                    "source_column": spec["source_column"],
                    "source_column_required_flag": True,
                    "score_direction": "higher_is_stronger",
                    "score_transform": "per_family_train_risk_on_percentile_rank",
                    "normalization_scope": "family_variant_train_risk_on_source_events",
                    "missing_policy": "missing_score_field_fails_arm_for_that_family",
                    "tie_break_policy": "higher_train_bridge_delta_then_lower_density_then_family_id",
                    "feature_asof_policy": "event_t0_or_earlier_only",
                    "source_column_presence_status": "present" if present else "missing",
                    "score_availability_status": "available" if present else "score_source_column_missing",
                    "proxy_score_used": family in {"R8_persistent_distance_above_ema", "R3_vcp_breakout"},
                    "missing_semantic_feature": "ema_distance" if family == "R8_persistent_distance_above_ema" else "",
                    "recompute_required_flag": False,
                    "recomputed_from_source_artifacts": False,
                    "source_08_manifest_hash": source_hash,
                    "patch_requirement_hash": requirement_hash,
                }
            )
    return pd.DataFrame(rows)


def percentile_by_train_distribution(values: pd.Series, train_values: pd.Series) -> pd.Series:
    train = pd.to_numeric(train_values, errors="coerce").dropna().sort_values().to_numpy()
    vals = pd.to_numeric(values, errors="coerce")
    if len(train) == 0:
        return pd.Series(np.nan, index=values.index)
    ranks = np.searchsorted(train, vals.to_numpy(dtype=float), side="right") / float(len(train))
    ranks[vals.isna().to_numpy()] = np.nan
    return pd.Series(ranks, index=values.index)


def score_instances(instances: pd.DataFrame, score_spec: pd.DataFrame) -> pd.DataFrame:
    out = instances.copy()
    out["per_family_variant_score"] = np.nan
    out["score_rank_eligible_flag"] = False
    out["score_spec_id"] = "score_spec_v1"
    out["score_availability_status"] = "not_scored"
    for (family, variant), group_idx in out.groupby(["family_id", "variant_id"], sort=False).groups.items():
        if family == R2_FAMILY:
            out.loc[group_idx, "score_availability_status"] = "core_semantic_score_unavailable"
            continue
        specs = score_spec.loc[
            (score_spec["family_id"] == family)
            & (score_spec["variant_id"] == variant)
            & (score_spec["score_availability_status"] == "available")
        ]
        if specs.empty:
            out.loc[group_idx, "score_availability_status"] = "score_source_column_missing"
            continue
        idx = list(group_idx)
        scores: list[pd.Series] = []
        family_frame = out.loc[idx]
        train_mask = (family_frame["event_split"] == "train") & (family_frame["market_regime_bucket"] == RISK_ON)
        for spec in specs.to_dict("records"):
            if spec["score_field_name"] == "momentum_percentile_20d_delta":
                values = (
                    pd.to_numeric(family_frame["momentum_percentile_20d"], errors="coerce")
                    - pd.to_numeric(family_frame["momentum_percentile_20d_lag20"], errors="coerce")
                )
            else:
                values = pd.to_numeric(family_frame[str(spec["source_column"])], errors="coerce")
            scores.append(percentile_by_train_distribution(values, values.loc[train_mask]))
        score = pd.concat(scores, axis=1).mean(axis=1, skipna=True)
        out.loc[idx, "per_family_variant_score"] = score
        out.loc[idx, "score_rank_eligible_flag"] = score.notna()
        out.loc[idx, "score_availability_status"] = "available"
    return out


def source_instances(instances: pd.DataFrame, *, gated_only: bool) -> pd.DataFrame:
    frame = instances.loc[
        instances["family_id"].isin(CORE_FAMILIES)
        & (instances["family_input_status"] == "runnable_existing_data")
    ].copy()
    if gated_only:
        frame = frame.loc[frame["variant_id"] == "event_regime_gated"].copy()
    return frame


def attach_missing_score_features(instances: pd.DataFrame, feature_panel: pd.DataFrame) -> pd.DataFrame:
    needed_columns: set[str] = set()
    for specs in SCORE_SPECS.values():
        for spec in specs:
            needed_columns.update(str(spec["source_column"]).split(";"))
    missing_columns = sorted(column for column in needed_columns if column not in instances.columns)
    if not missing_columns:
        return instances.copy()

    panel = feature_panel.rename(columns={"date": "event_t0_date"}).copy()
    panel["event_t0_date"] = panel["event_t0_date"].astype(str)
    out = instances.copy()
    out["event_t0_date"] = out["event_t0_date"].astype(str)
    feature_columns = ["instrument", "event_t0_date", *missing_columns]
    available_feature_columns = [column for column in feature_columns if column in panel.columns]
    return out.merge(
        panel[available_feature_columns].drop_duplicates(["instrument", "event_t0_date"]),
        on=["instrument", "event_t0_date"],
        how="left",
    )


def ordered_unique_join(values: pd.Series) -> str:
    return ";".join(dict.fromkeys(values.dropna().astype(str).tolist()))


def score_map_json(group: pd.DataFrame) -> str:
    mapping = {
        str(variant): None if pd.isna(score) else float(score)
        for variant, score in zip(group["family_variant_id"], group["per_family_variant_score"])
    }
    return json.dumps(mapping, ensure_ascii=False, sort_keys=True)


def finalize_canonical_events(frame: pd.DataFrame, arm_id: str) -> pd.DataFrame:
    out = frame.copy()
    unscored = ~out["score_rank_eligible_flag"].fillna(False).astype(bool)
    out["canonical_event_id"] = (
        out["instrument"].astype(str)
        + "_"
        + out["event_t0_date"].astype(str).str.replace("-", "", regex=False)
        + "_"
        + arm_id
    )
    out["compressed_pool_id"] = arm_id
    out["compression_arm_id"] = arm_id
    out["primary_family_id"] = out["family_id"].astype(str)
    out["primary_variant_id"] = out["variant_id"].astype(str)
    out["primary_score_family"] = np.where(unscored, "", out["family_id"].astype(str))
    out["canonical_score"] = np.where(
        unscored,
        np.nan,
        pd.to_numeric(out["per_family_variant_score"], errors="coerce"),
    )
    out["score_spec_id"] = "score_spec_v1"
    out["score_rank_eligible_flag"] = ~unscored
    out["unscored_canonical_event_flag"] = unscored
    out["unscored_canonical_policy"] = np.where(unscored, UNSCORED_CANONICAL_POLICY, "")
    out["compression_keep_flag"] = True
    out["compression_reason"] = np.where(unscored, "unscored_canonical_retained", "selected_by_arm")
    out["episode_regime_bucket"] = ""
    return out.drop(columns=["score_sort_value"], errors="ignore")


def canonicalize_scored(instances: pd.DataFrame, arm_id: str) -> pd.DataFrame:
    if instances.empty:
        return pd.DataFrame()
    work = instances.copy()
    work["score_rank_eligible_flag"] = work["score_rank_eligible_flag"].fillna(False).astype(bool)
    work["score_sort_value"] = np.where(
        work["score_rank_eligible_flag"],
        pd.to_numeric(work["per_family_variant_score"], errors="coerce").fillna(-np.inf),
        -np.inf,
    )
    keys = ["instrument", "event_t0_date"]
    group_size = work.groupby(keys, sort=False)["event_id"].transform("size")
    singletons = work.loc[group_size == 1].copy()
    if not singletons.empty:
        singletons["triggered_family_variants"] = singletons["family_variant_id"].astype(str)
        singletons["triggered_family_ids"] = singletons["family_id"].astype(str)
        singletons["raw_source_event_ids"] = singletons["event_id"].astype(str)
        singletons["raw_cluster_event_count"] = 1
        singletons["per_family_variant_scores"] = [
            json.dumps(
                {str(variant): None if pd.isna(score) else float(score)},
                ensure_ascii=False,
                sort_keys=True,
            )
            for variant, score in zip(singletons["family_variant_id"], singletons["per_family_variant_score"])
        ]
        singletons = finalize_canonical_events(singletons, arm_id)

    duplicates = work.loc[group_size > 1].copy()
    if duplicates.empty:
        return singletons.sort_values(keys).reset_index(drop=True)

    ordered = duplicates.sort_values([*keys, "event_family_priority", "event_id"]).copy()
    primary = (
        duplicates.sort_values(
            [*keys, "score_sort_value", "event_family_priority", "event_id"],
            ascending=[True, True, False, True, True],
        )
        .drop_duplicates(keys, keep="first")
        .drop(columns=["score_sort_value"], errors="ignore")
        .copy()
    )
    aggregate = (
        ordered.groupby(keys, sort=False)
        .agg(
            triggered_family_variants=("family_variant_id", ordered_unique_join),
            triggered_family_ids=("family_id", ordered_unique_join),
            raw_source_event_ids=("event_id", lambda values: ";".join(values.astype(str))),
            raw_cluster_event_count=("event_id", "size"),
        )
        .reset_index()
    )
    score_maps = (
        ordered.groupby(keys, sort=False)[["family_variant_id", "per_family_variant_score"]]
        .apply(score_map_json)
        .rename("per_family_variant_scores")
        .reset_index()
    )
    out = primary.merge(aggregate, on=keys, how="left").merge(score_maps, on=keys, how="left")
    out = finalize_canonical_events(out, arm_id)
    parts = [out] if singletons.empty else [singletons, out]
    return pd.concat(parts, ignore_index=True).sort_values(keys).reset_index(drop=True)


def event_day_key(events: pd.DataFrame) -> pd.Series:
    return events["instrument"].astype(str) + "|" + events["event_t0_date"].astype(str)


def arm_raw_pool(scored_instances: pd.DataFrame) -> pd.DataFrame:
    return canonicalize_scored(scored_instances, "raw_r_series_variant_pool")


def arm_gated_only(scored_instances: pd.DataFrame) -> pd.DataFrame:
    return canonicalize_scored(scored_instances, "event_regime_gated_only")


def arm_single_family(scored_instances: pd.DataFrame, family: str) -> pd.DataFrame:
    return canonicalize_scored(scored_instances.loc[scored_instances["family_id"] == family], f"single_family_best_variant__{family}")


def arm_family_quantile(scored_instances: pd.DataFrame, quantile: float) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for family, group in scored_instances.groupby("family_id", sort=True):
        if family == R2_FAMILY:
            parts.append(group.copy())
            continue
        train = group.loc[
            (group["event_split"] == "train")
            & (group["market_regime_bucket"] == RISK_ON)
            & group["score_rank_eligible_flag"].fillna(False).astype(bool)
        ]
        threshold = pd.to_numeric(train["per_family_variant_score"], errors="coerce").quantile(quantile)
        if pd.isna(threshold):
            continue
        parts.append(group.loc[pd.to_numeric(group["per_family_variant_score"], errors="coerce") >= threshold].copy())
    arm_id = f"family_score_quantile_cut__q{str(quantile).replace('.', '')}"
    return canonicalize_scored(pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(), arm_id)


def arm_consensus(scored_instances: pd.DataFrame, min_count: int) -> pd.DataFrame:
    base = canonicalize_scored(scored_instances, f"consensus_family_count__min{min_count}")
    if base.empty:
        return base
    counts = base["triggered_family_ids"].map(lambda value: len(set(split_semicolon(value))))
    return base.loc[counts >= min_count].copy()


def arm_top_k(scored_instances: pd.DataFrame, k: int) -> pd.DataFrame:
    base = canonicalize_scored(scored_instances, f"top_k_per_instrument_month__k{k}")
    if base.empty:
        return base
    scored = base.loc[base["score_rank_eligible_flag"].fillna(False).astype(bool)].copy()
    unscored = base.loc[~base["score_rank_eligible_flag"].fillna(False).astype(bool)].copy()
    scored["month_bucket"] = (pd.to_numeric(scored["event_t0_pos"], errors="coerce") // 21).astype("Int64")
    kept = scored.sort_values(["instrument", "month_bucket", "canonical_score"], ascending=[True, True, False]).groupby(
        ["instrument", "month_bucket"], dropna=False
    ).head(k)
    return pd.concat([kept.drop(columns=["month_bucket"], errors="ignore"), unscored], ignore_index=True)


def arm_cooldown(scored_instances: pd.DataFrame, cooldown: int) -> pd.DataFrame:
    base = canonicalize_scored(scored_instances, f"cooldown_after_selected_event__{cooldown}d")
    if base.empty:
        return base
    rows: list[pd.DataFrame] = []
    for _, group in base.sort_values(["instrument", "event_t0_pos", "canonical_score"], ascending=[True, True, False]).groupby("instrument", sort=True):
        last_pos = -10**9
        keep_idx: list[int] = []
        for idx, row in group.iterrows():
            pos = int(row["event_t0_pos"])
            if pos - last_pos >= cooldown:
                keep_idx.append(idx)
                last_pos = pos
        rows.append(group.loc[keep_idx])
    return pd.concat(rows, ignore_index=True) if rows else base.iloc[0:0].copy()


def arm_market_day_top_pct(scored_instances: pd.DataFrame, pct_keep: float) -> pd.DataFrame:
    arm_id = f"market_day_top_percentile__top{int(pct_keep * 100)}pct"
    base = canonicalize_scored(scored_instances, arm_id)
    if base.empty:
        return base
    scored = base.loc[base["score_rank_eligible_flag"].fillna(False).astype(bool)].copy()
    unscored = base.loc[~base["score_rank_eligible_flag"].fillna(False).astype(bool)].copy()
    kept_parts: list[pd.DataFrame] = []
    for _, group in scored.groupby("event_t0_date", sort=True):
        n = max(1, int(math.ceil(len(group) * pct_keep)))
        kept_parts.append(group.sort_values("canonical_score", ascending=False).head(n))
    kept = pd.concat(kept_parts, ignore_index=True) if kept_parts else scored.iloc[0:0]
    return pd.concat([kept, unscored], ignore_index=True)


def arm_overlap_deconcentration(scored_instances: pd.DataFrame) -> pd.DataFrame:
    base = canonicalize_scored(scored_instances, "overlap_deconcentration")
    if base.empty:
        return base
    base["triggered_family_ids_original"] = base["triggered_family_ids"]
    base["triggered_family_variants_original"] = base["triggered_family_variants"]
    base["triggered_family_ids"] = base["primary_family_id"]
    base["triggered_family_variants"] = base["primary_family_id"].astype(str) + "__" + base["primary_variant_id"].astype(str)
    return base


def build_arms(scored_raw: pd.DataFrame, scored_gated: pd.DataFrame) -> dict[str, pd.DataFrame]:
    arms: dict[str, pd.DataFrame] = {
        "raw_r_series_variant_pool": arm_raw_pool(scored_raw),
        "event_regime_gated_only": arm_gated_only(scored_gated),
    }
    for family in CORE_FAMILIES:
        arms[f"single_family_best_variant__{family}"] = arm_single_family(scored_gated, family)
    for q in [0.70, 0.80, 0.90, 0.95, 0.975]:
        arms[f"family_score_quantile_cut__q{str(q).replace('.', '')}"] = arm_family_quantile(scored_gated, q)
    for min_count in [2, 3]:
        arms[f"consensus_family_count__min{min_count}"] = arm_consensus(scored_gated, min_count)
    for k in [1, 2, 3]:
        arms[f"top_k_per_instrument_month__k{k}"] = arm_top_k(scored_gated, k)
    for cooldown in [10, 20, 40]:
        arms[f"cooldown_after_selected_event__{cooldown}d"] = arm_cooldown(scored_gated, cooldown)
    for pct_keep in [0.05, 0.10, 0.20]:
        arms[f"market_day_top_percentile__top{int(pct_keep * 100)}pct"] = arm_market_day_top_pct(scored_gated, pct_keep)
    arms["overlap_deconcentration"] = arm_overlap_deconcentration(scored_gated)
    return arms


def build_capture_from_template(events: pd.DataFrame, template: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    label_map = labels.set_index("event_id").to_dict("index") if not labels.empty else {}
    complete_map = {
        event_id: bool(label.get("horizon_complete_120d", False))
        for event_id, label in label_map.items()
    }
    positive_map = {
        event_id: bool(label.get("event_big_winner_120d_label", False))
        for event_id, label in label_map.items()
    }
    if events.empty:
        events_by_instrument: dict[str, dict[str, np.ndarray]] = {}
    else:
        events_by_instrument = {}
        for instrument, group in events.groupby("instrument", sort=True):
            ordered = group.sort_values(["event_t0_pos", "event_family_priority", "event_id"]).reset_index(drop=True)
            event_ids = ordered["event_id"].astype(str).to_numpy()
            complete = np.array([complete_map.get(event_id, False) for event_id in event_ids], dtype=bool)
            positive = np.array(
                [complete_map.get(event_id, False) and positive_map.get(event_id, False) for event_id in event_ids],
                dtype=bool,
            )
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
        if not bool(row.get("any_event_denominator_included", True)):
            hit_count = 0
        else:
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
                "candidate_scope_id": events["compressed_pool_id"].iloc[0] if not events.empty else "",
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


def build_bridge_recall(capture_map: dict[str, pd.DataFrame], metadata: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope_id, capture in capture_map.items():
        meta = metadata[scope_id]
        for split in pipeline.SPLITS:
            for regime in pipeline.REGIMES:
                for window in pipeline.WINDOWS:
                    frame = pipeline.capture_filter(capture, split, regime, window)
                    frame = frame.loc[frame["bridge_positive_denominator_included"].fillna(False).astype(bool)]
                    rows.append(
                        {
                            **meta,
                            "episode_split": split,
                            "market_regime_bucket": regime,
                            "board_bucket": "all",
                            "window": window,
                            "metric_basis": "bridge_positive_event",
                            "numerator": int(frame["bridge_positive_captured"].fillna(False).astype(bool).sum()),
                            "denominator": int(len(frame)),
                            "excluded_count": int(len(pipeline.capture_filter(capture, split, regime, window)) - len(frame)),
                            "recall": safe_rate(
                                int(frame["bridge_positive_captured"].fillna(False).astype(bool).sum()),
                                len(frame),
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def build_any_recall(capture_map: dict[str, pd.DataFrame], metadata: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope_id, capture in capture_map.items():
        meta = metadata[scope_id]
        for split in pipeline.SPLITS:
            for regime in pipeline.REGIMES:
                for window in pipeline.WINDOWS:
                    frame = pipeline.capture_filter(capture, split, regime, window)
                    frame = frame.loc[frame["any_event_denominator_included"].fillna(False).astype(bool)]
                    rows.append(
                        {
                            **meta,
                            "episode_split": split,
                            "market_regime_bucket": regime,
                            "board_bucket": "all",
                            "window": window,
                            "metric_basis": "capture_any_event",
                            "numerator": int(frame["any_event_captured"].fillna(False).astype(bool).sum()),
                            "denominator": int(len(frame)),
                            "excluded_count": int(len(pipeline.capture_filter(capture, split, regime, window)) - len(frame)),
                            "recall": safe_rate(
                                int(frame["any_event_captured"].fillna(False).astype(bool).sum()),
                                len(frame),
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def e1_universe_years(density: pd.DataFrame) -> tuple[float, int, float]:
    e1 = density.loc[density["candidate_scope_id"] == E1_SCOPE].iloc[0]
    e1_count = int(e1["event_count"])
    e1_density = float(e1["density_full_denominator"])
    return float(e1_count / e1_density), e1_count, e1_density


def family_share(events: pd.DataFrame) -> tuple[float, str]:
    if events.empty:
        return np.nan, "{}"
    counts: dict[str, int] = {}
    for value in events["triggered_family_ids"].fillna("").astype(str):
        for family in set(split_semicolon(value)):
            counts[family] = counts.get(family, 0) + 1
    shares = {key: value / len(events) for key, value in sorted(counts.items())}
    return (max(shares.values()) if shares else np.nan), json.dumps(shares, ensure_ascii=False, sort_keys=True)


def density_for_events(events: pd.DataFrame, density_source: pd.DataFrame) -> dict[str, Any]:
    universe_years, _, e1_density = e1_universe_years(density_source)
    event_count = int(len(events))
    full_density = event_count / universe_years if universe_years else np.nan
    p95 = pipeline.event_density_nonzero(events)[2] if not events.empty else np.nan
    share_max, share_json = family_share(events)
    return {
        "event_count": event_count,
        "canonical_event_count": event_count,
        "density_vs_e1_full_denominator": full_density / e1_density if e1_density else np.nan,
        "density_full_denominator": full_density,
        "events_per_instrument_year_p95": p95,
        "single_family_density_share_max": share_max,
        "triggered_family_share": share_json,
    }


def label_quality_for_events(events: pd.DataFrame, labels: pd.DataFrame) -> dict[str, Any]:
    if events.empty:
        return {
            "label_completeness_rate": np.nan,
            "next_open_executable_rate": np.nan,
            "event_big_winner_120d_rate": np.nan,
        }
    frame = events.merge(labels, on="event_id", how="left", suffixes=("", "_label"))
    complete = frame.loc[frame["candidate_outcome_120d_status"] == pipeline._p04.NOT_MISSING]
    executable = (~frame["non_executable_next_open"].fillna(False).astype(bool)).sum()
    return {
        "label_completeness_rate": safe_rate(len(complete), len(frame)),
        "next_open_executable_rate": safe_rate(int(executable), len(frame)),
        "event_big_winner_120d_rate": safe_rate(
            int(complete["event_big_winner_120d_label"].fillna(False).astype(bool).sum()),
            len(complete),
        ),
    }


def metric_value(frame: pd.DataFrame, scope_id: str, split: str, regime: str, column: str) -> float:
    row = frame.loc[
        (frame["candidate_scope_id"] == scope_id)
        & (frame["episode_split"] == split)
        & (frame["market_regime_bucket"] == regime)
        & (frame["window"] == WINDOW)
    ]
    if row.empty:
        return np.nan
    return float(row.iloc[0][column])


def build_frontier(
    arms: dict[str, pd.DataFrame],
    captures: dict[str, pd.DataFrame],
    incremental: pd.DataFrame,
    bridge: pd.DataFrame,
    density_source: pd.DataFrame,
    labels: pd.DataFrame,
) -> pd.DataFrame:
    e1_bridge = bridge.loc[bridge["candidate_scope_id"] == E1_SCOPE]
    rows: list[dict[str, Any]] = []
    for arm_id, events in arms.items():
        dens = density_for_events(events, density_source)
        label = label_quality_for_events(events, labels)
        bridge_train = metric_value(bridge, arm_id, "train", RISK_ON, "recall")
        bridge_rob = metric_value(bridge, arm_id, "robustness", RISK_ON, "recall")
        e1_train = metric_value(e1_bridge, E1_SCOPE, "train", RISK_ON, "recall")
        e1_rob = metric_value(e1_bridge, E1_SCOPE, "robustness", RISK_ON, "recall")
        train_delta = bridge_train - e1_train if pd.notna(bridge_train) and pd.notna(e1_train) else np.nan
        rob_delta = bridge_rob - e1_rob if pd.notna(bridge_rob) and pd.notna(e1_rob) else np.nan
        train_inc = metric_value(incremental, arm_id, "train", RISK_ON, "incremental_recall_over_e1")
        val_inc = metric_value(incremental, arm_id, "validation", RISK_ON, "incremental_recall_over_e1")
        rob_inc = metric_value(incremental, arm_id, "robustness", RISK_ON, "incremental_recall_over_e1")
        val_den = metric_value(incremental, arm_id, "validation", RISK_ON, "denominator_episodes")
        unscored_count = int(events.get("unscored_canonical_event_flag", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not events.empty else 0
        failures = []
        if label["label_completeness_rate"] < LABEL_COMPLETENESS_MIN:
            failures.append("label_completeness")
        if label["next_open_executable_rate"] < NEXT_OPEN_EXECUTABLE_MIN:
            failures.append("next_open_execution")
        if pd.isna(train_delta) or train_delta < TRAIN_BRIDGE_DELTA_MIN:
            failures.append("train_bridge")
        if pd.isna(train_inc) or train_inc < RECALL_MIN:
            failures.append("train_recall")
        if pd.isna(dens["density_vs_e1_full_denominator"]) or dens["density_vs_e1_full_denominator"] > DENSITY_VS_E1_MAX:
            failures.append("density")
        if pd.notna(dens["events_per_instrument_year_p95"]) and dens["events_per_instrument_year_p95"] > P95_MAX:
            failures.append("p95")
        if pd.notna(dens["single_family_density_share_max"]) and dens["single_family_density_share_max"] > SINGLE_FAMILY_SHARE_MAX:
            failures.append("family_share_65")
        score = (
            4.0 * (train_delta if pd.notna(train_delta) else -1.0)
            + 3.0 * (train_inc if pd.notna(train_inc) else -1.0)
            - 2.0 * max((dens["density_vs_e1_full_denominator"] if pd.notna(dens["density_vs_e1_full_denominator"]) else 99.0) - 1.0, 0.0)
            - 1.0 * max((dens["events_per_instrument_year_p95"] if pd.notna(dens["events_per_instrument_year_p95"]) else 99.0) - 4.0, 0.0)
        )
        rows.append(
            {
                "compression_arm_id": arm_id,
                "source_family_set": ";".join(CORE_FAMILIES),
                "source_variant_set": "event_regime_gated" if arm_id != "raw_r_series_variant_pool" else "all_runnable_variants",
                "threshold_policy": arm_id,
                "score_spec_id": "score_spec_v1",
                "score_spec_hash": "",
                "selected_by_train_only_flag": False,
                "post_train_selection_read_only_metric": True,
                "compression_source_variant_policy": SOURCE_VARIANT_POLICY
                if arm_id != "raw_r_series_variant_pool"
                else "all_runnable_variants_upper_bound",
                "allow_ungated_compression_source": arm_id == "raw_r_series_variant_pool",
                "source_variant_fallback_reason": "",
                "unscored_canonical_policy": UNSCORED_CANONICAL_POLICY,
                "unscored_canonical_event_count": unscored_count,
                "unscored_canonical_density_share": safe_rate(unscored_count, len(events)),
                **dens,
                "density_compression_ratio_vs_raw_r_pool": np.nan,
                "raw_r_pool_definition": RAW_R_POOL_DEFINITION,
                "train_risk_on_incremental_recall_over_e1": train_inc,
                "train_risk_on_bridge_recall_delta_vs_e1": train_delta,
                "validation_risk_on_incremental_recall_over_e1": val_inc,
                "validation_risk_on_sample_small_flag": bool(pd.notna(val_den) and val_den < VALIDATION_RISK_ON_SMALL_DENOMINATOR),
                "robustness_risk_on_incremental_recall_over_e1": rob_inc,
                "robustness_risk_on_bridge_recall_delta_vs_e1": rob_delta,
                **label,
                "downstream_entry_family_share_35pct_pass": bool(
                    pd.notna(dens["single_family_density_share_max"])
                    and dens["single_family_density_share_max"] <= DOWNSTREAM_FAMILY_SHARE_MAX
                ),
                "direct_entry_union_support_status": "not_supported_as_direct_entry_union_due_to_35pct_family_share_gate"
                if pd.notna(dens["single_family_density_share_max"])
                and dens["single_family_density_share_max"] > DOWNSTREAM_FAMILY_SHARE_MAX
                else "direct_entry_family_share_pass",
                "ranker_arm_status": "not_evaluated_deterministic_run",
                "gate_status": "train_pass" if not failures else "train_blocked",
                "failure_reason": ";".join(failures),
                "selection_score": score,
            }
        )
    frontier = pd.DataFrame(rows)
    raw_count = frontier.loc[frontier["compression_arm_id"] == "raw_r_series_variant_pool", "event_count"]
    raw_count_value = float(raw_count.iloc[0]) if not raw_count.empty and raw_count.iloc[0] else np.nan
    frontier["density_compression_ratio_vs_raw_r_pool"] = frontier["event_count"] / raw_count_value
    score_spec_path = PATCH_TABLE_DIR / "risk_on_r_series_score_spec.csv"
    if score_spec_path.exists():
        frontier["score_spec_hash"] = file_sha256(score_spec_path)
    return frontier


def select_train_arm(frontier: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    candidates = frontier.loc[
        (frontier["compression_arm_id"] != "raw_r_series_variant_pool")
        & (frontier["failure_reason"].fillna("") == "")
    ].copy()
    if candidates.empty:
        out = frontier.copy()
        return "", out
    candidates = candidates.sort_values(
        [
            "selection_score",
            "density_vs_e1_full_denominator",
            "train_risk_on_bridge_recall_delta_vs_e1",
            "train_risk_on_incremental_recall_over_e1",
            "events_per_instrument_year_p95",
            "compression_arm_id",
        ],
        ascending=[False, True, False, False, True, True],
    )
    selected = str(candidates.iloc[0]["compression_arm_id"])
    out = frontier.copy()
    out.loc[out["compression_arm_id"] == selected, "selected_by_train_only_flag"] = True
    return selected, out


def final_decision(frontier: pd.DataFrame, selected_arm: str) -> tuple[str, dict[str, Any]]:
    if not selected_arm:
        return "risk_on_r_series_no_compression_candidate", {"gate_failures": "train_no_candidate"}
    row = frontier.loc[frontier["compression_arm_id"] == selected_arm].iloc[0]
    failures: list[str] = []
    if row["robustness_risk_on_incremental_recall_over_e1"] < RECALL_MIN:
        failures.append("robustness_recall")
    if row["robustness_risk_on_bridge_recall_delta_vs_e1"] < ROBUSTNESS_BRIDGE_DELTA_MIN:
        failures.append("robustness_bridge")
    if row["density_vs_e1_full_denominator"] > DENSITY_VS_E1_MAX:
        failures.append("density")
    if pd.notna(row["events_per_instrument_year_p95"]) and row["events_per_instrument_year_p95"] > P95_MAX:
        failures.append("p95")
    if row["label_completeness_rate"] < LABEL_COMPLETENESS_MIN:
        failures.append("label")
    if row["next_open_executable_rate"] < NEXT_OPEN_EXECUTABLE_MIN:
        failures.append("execution")
    if row["single_family_density_share_max"] > SINGLE_FAMILY_SHARE_MAX:
        failures.append("family_share_65")
    if not failures:
        decision = "risk_on_r_series_density_compressed_candidate_supported_for_meta_label"
    elif "density" in failures:
        decision = "risk_on_r_series_density_still_blocked"
    elif "robustness_bridge" in failures:
        decision = "risk_on_r_series_bridge_degraded_blocked"
    elif "robustness_recall" in failures:
        decision = "risk_on_r_series_overfit_blocked"
    else:
        decision = "risk_on_r_series_diagnostic_only"
    return decision, {
        "selected_compression_arm_id": selected_arm,
        "gate_failures": ";".join(failures),
        "train_risk_on_incremental_recall_over_e1": row["train_risk_on_incremental_recall_over_e1"],
        "robustness_risk_on_incremental_recall_over_e1": row["robustness_risk_on_incremental_recall_over_e1"],
        "train_risk_on_bridge_recall_delta_vs_e1": row["train_risk_on_bridge_recall_delta_vs_e1"],
        "robustness_risk_on_bridge_recall_delta_vs_e1": row["robustness_risk_on_bridge_recall_delta_vs_e1"],
        "density_vs_e1_full_denominator": row["density_vs_e1_full_denominator"],
        "events_per_instrument_year_p95": row["events_per_instrument_year_p95"],
        "single_family_density_share_max": row["single_family_density_share_max"],
        "downstream_entry_family_share_35pct_pass": bool(row["downstream_entry_family_share_35pct_pass"]),
    }


def source_pool_summary(scored_raw: pd.DataFrame, scored_gated: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, frame in [("raw_r_series_variant_pool", scored_raw), ("event_regime_gated_source_pool", scored_gated)]:
        for family, group in frame.groupby("family_id", sort=True):
            rows.append(
                {
                    "source_pool_id": name,
                    "family_id": family,
                    "variant_ids": ";".join(sorted(group["variant_id"].dropna().astype(str).unique())),
                    "source_event_count": int(len(group)),
                    "scored_event_count": int(group["score_rank_eligible_flag"].fillna(False).astype(bool).sum()),
                    "unscored_event_count": int((~group["score_rank_eligible_flag"].fillna(False).astype(bool)).sum()),
                    "score_availability_status": ";".join(sorted(group["score_availability_status"].dropna().astype(str).unique())),
                    "compression_source_variant_policy": SOURCE_VARIANT_POLICY if name != "raw_r_series_variant_pool" else "all_runnable_variants_upper_bound",
                }
            )
    return pd.DataFrame(rows)


def selected_variants(selected_events: pd.DataFrame, scored_gated: pd.DataFrame, selected_arm: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if selected_events.empty:
        return pd.DataFrame()
    before = scored_gated.groupby(["family_id", "variant_id"], dropna=False).size().to_dict()
    after_counts: dict[tuple[str, str], int] = {}
    total = len(selected_events)
    for _, event in selected_events.iterrows():
        for family, variant in zip(
            split_semicolon(event.get("triggered_family_ids", "")),
            [item.split("__")[-1] if "__" in item else "" for item in split_semicolon(event.get("triggered_family_variants", ""))],
        ):
            key = (family, variant or "event_regime_gated")
            after_counts[key] = after_counts.get(key, 0) + 1
    for rank, ((family, variant), count) in enumerate(sorted(after_counts.items()), start=1):
        rows.append(
            {
                "compressed_pool_id": selected_arm,
                "compression_arm_id": selected_arm,
                "family_id": family,
                "variant_id": variant,
                "source_pool_role": "core" if family in CORE_FAMILIES else "optional_or_negative",
                "source_event_count_before_compression": int(before.get((family, variant), 0)),
                "source_event_count_after_compression": int(count),
                "family_density_share_after_compression": safe_rate(count, total),
                "train_selection_rank": rank,
                "selection_reason": "selected_by_train_only_compression_arm",
                "negative_control_flag": family == NEGATIVE_CONTROL_FAMILY,
            }
        )
    return pd.DataFrame(rows)


def overlap_diagnostic(selected_events: pd.DataFrame, arms: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    selected_keys = set(event_day_key(selected_events)) if not selected_events.empty else set()
    for arm_id, events in arms.items():
        keys = set(event_day_key(events)) if not events.empty else set()
        rows.append(
            {
                "compressed_pool_id": selected_events["compressed_pool_id"].iloc[0] if not selected_events.empty else "",
                "comparison_scope_id": arm_id,
                "selected_event_count": len(selected_keys),
                "comparison_event_count": len(keys),
                "intersection_event_count": len(selected_keys.intersection(keys)),
                "selected_overlap_share": safe_rate(len(selected_keys.intersection(keys)), len(selected_keys)),
                "comparison_overlap_share": safe_rate(len(selected_keys.intersection(keys)), len(keys)),
            }
        )
    return pd.DataFrame(rows)


def gate_summary_frame(decision: str, preflight: dict[str, Any], selected_metrics: dict[str, Any]) -> pd.DataFrame:
    failures = str(selected_metrics.get("gate_failures", ""))
    return pd.DataFrame(
        [
            {
                "risk_on_r_series_density_compression_decision": decision,
                "density_binding_preflight_decision": preflight.get("density_binding_preflight_decision", ""),
                "selected_compression_arm_id": selected_metrics.get("selected_compression_arm_id", ""),
                "recall_gate_pass": "robustness_recall" not in failures,
                "bridge_gate_pass": "robustness_bridge" not in failures,
                "density_gate_pass": "density" not in failures,
                "p95_density_gate_pass": "p95" not in failures,
                "label_execution_gate_pass": "label" not in failures and "execution" not in failures,
                "overfit_gate_pass": "robustness_recall" not in failures and "robustness_bridge" not in failures,
                "gate_failures": failures,
                "train_risk_on_incremental_recall_over_e1": selected_metrics.get("train_risk_on_incremental_recall_over_e1", np.nan),
                "robustness_risk_on_incremental_recall_over_e1": selected_metrics.get("robustness_risk_on_incremental_recall_over_e1", np.nan),
                "train_risk_on_bridge_recall_delta_vs_e1": selected_metrics.get("train_risk_on_bridge_recall_delta_vs_e1", np.nan),
                "robustness_risk_on_bridge_recall_delta_vs_e1": selected_metrics.get("robustness_risk_on_bridge_recall_delta_vs_e1", np.nan),
                "density_vs_e1_full_denominator": selected_metrics.get("density_vs_e1_full_denominator", np.nan),
                "events_per_instrument_year_p95": selected_metrics.get("events_per_instrument_year_p95", np.nan),
                "single_family_density_share_max": selected_metrics.get("single_family_density_share_max", np.nan),
                "downstream_entry_family_share_35pct_pass": selected_metrics.get("downstream_entry_family_share_35pct_pass", False),
                "validation_risk_on_sample_small_flag": True,
            }
        ]
    )


def read_patch_table(name: str) -> pd.DataFrame:
    path = PATCH_TABLE_DIR / f"{name}.csv"
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 1 else pd.DataFrame()


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_无数据_"
    rows = ["| " + " | ".join(frame.columns) + " |", "| " + " | ".join(["---"] * len(frame.columns)) + " |"]
    for _, item in frame.iterrows():
        rows.append("| " + " | ".join(str(item[column]) for column in frame.columns) + " |")
    return "\n".join(rows)


def format_report_frontier(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in [
        "train_risk_on_incremental_recall_over_e1",
        "train_risk_on_bridge_recall_delta_vs_e1",
        "robustness_risk_on_incremental_recall_over_e1",
        "robustness_risk_on_bridge_recall_delta_vs_e1",
        "single_family_density_share_max",
    ]:
        if column in out:
            out[column] = out[column].map(pct)
    for column in ["density_vs_e1_full_denominator", "events_per_instrument_year_p95", "selection_score"]:
        if column in out:
            out[column] = out[column].map(lambda value: num(value, 2))
    return out


def write_report(path: Path, decision: str, preflight: dict[str, Any], selected_metrics: dict[str, Any], frontier: pd.DataFrame) -> Path:
    selected = selected_metrics.get("selected_compression_arm_id", "")
    selected_row = frontier.loc[frontier["compression_arm_id"] == selected]
    row = selected_row.iloc[0].to_dict() if not selected_row.empty else {}
    preflight_frame = read_patch_table("risk_on_r_series_density_binding_preflight")
    score_spec = read_patch_table("risk_on_r_series_score_spec")
    source_pool = read_patch_table("risk_on_r_series_source_pool_summary")
    selected_events = read_patch_table("risk_on_r_series_compressed_canonical_events")

    core_and_control = CORE_FAMILIES + [NEGATIVE_CONTROL_FAMILY]
    preflight_view = preflight_frame.loc[
        (preflight_frame.get("candidate_scope_type", "") == pipeline.FAMILY_SCOPE)
        & preflight_frame.get("family_id", pd.Series(dtype=str)).isin(core_and_control)
    ].copy()
    if not preflight_view.empty:
        preflight_view = preflight_view[
            [
                "family_id",
                "episode_split",
                "incremental_recall_over_e1",
                "bridge_recall_delta_vs_e1",
                "density_vs_e1_full_denominator",
                "events_per_instrument_year_p95",
                "density_binding_flag",
            ]
        ].copy()
        preflight_view["incremental_recall_over_e1"] = preflight_view["incremental_recall_over_e1"].map(pct)
        preflight_view["bridge_recall_delta_vs_e1"] = preflight_view["bridge_recall_delta_vs_e1"].map(pct)
        preflight_view["density_vs_e1_full_denominator"] = preflight_view["density_vs_e1_full_denominator"].map(
            lambda value: f"{num(value, 2)}x"
        )
        preflight_view["events_per_instrument_year_p95"] = preflight_view["events_per_instrument_year_p95"].map(
            lambda value: num(value, 1)
        )

    score_view = pd.DataFrame()
    if not score_spec.empty:
        score_view = (
            score_spec.groupby("family_id", sort=True)
            .agg(
                score_fields=("score_field_name", lambda values: "; ".join(values.astype(str))),
                source_columns=(
                    "source_column",
                    lambda values: "; ".join(
                        v for v in values.fillna("").astype(str) if v and v.lower() != "nan"
                    ),
                ),
                score_status=("score_availability_status", lambda values: "; ".join(sorted(set(values.astype(str))))),
                proxy_score_used=("proxy_score_used", "max"),
                recompute_required=("recompute_required_flag", "max"),
            )
            .reset_index()
        )

    frontier_cols = [
        "compression_arm_id",
        "event_count",
        "density_vs_e1_full_denominator",
        "events_per_instrument_year_p95",
        "single_family_density_share_max",
        "train_risk_on_incremental_recall_over_e1",
        "train_risk_on_bridge_recall_delta_vs_e1",
        "robustness_risk_on_incremental_recall_over_e1",
        "robustness_risk_on_bridge_recall_delta_vs_e1",
        "failure_reason",
        "selection_score",
    ]
    frontier_view = (
        format_report_frontier(frontier[frontier_cols].sort_values("selection_score", ascending=False).head(10))
        if not frontier.empty
        else pd.DataFrame()
    )
    closest_cols = [
        "compression_arm_id",
        "event_count",
        "density_vs_e1_full_denominator",
        "events_per_instrument_year_p95",
        "single_family_density_share_max",
        "train_risk_on_incremental_recall_over_e1",
        "train_risk_on_bridge_recall_delta_vs_e1",
        "failure_reason",
        "selection_score",
    ]
    closest_density = (
        format_report_frontier(
            frontier[closest_cols]
            .sort_values(["density_vs_e1_full_denominator", "selection_score"], ascending=[True, False])
            .head(8)
        )
        if not frontier.empty
        else pd.DataFrame()
    )
    failure_counts = frontier["failure_reason"].value_counts(dropna=False).reset_index() if not frontier.empty else pd.DataFrame()
    if not failure_counts.empty:
        failure_counts.columns = ["failure_reason", "arm_count"]

    pass_counts = {
        "train_recall_pass": int((frontier["train_risk_on_incremental_recall_over_e1"] >= RECALL_MIN).sum()) if not frontier.empty else 0,
        "train_bridge_pass": int((frontier["train_risk_on_bridge_recall_delta_vs_e1"] >= TRAIN_BRIDGE_DELTA_MIN).sum()) if not frontier.empty else 0,
        "density_pass": int((frontier["density_vs_e1_full_denominator"] <= DENSITY_VS_E1_MAX).sum()) if not frontier.empty else 0,
        "p95_pass": int((frontier["events_per_instrument_year_p95"] <= P95_MAX).sum()) if not frontier.empty else 0,
        "family65_pass": int((frontier["single_family_density_share_max"] <= SINGLE_FAMILY_SHARE_MAX).sum()) if not frontier.empty else 0,
        "total": int(len(frontier)),
    }
    r2_arm = f"single_family_best_variant__{R2_FAMILY}"
    r2_row = frontier.loc[frontier["compression_arm_id"] == r2_arm] if not frontier.empty else pd.DataFrame()
    r2 = r2_row.iloc[0].to_dict() if not r2_row.empty else {}
    gated_row = frontier.loc[frontier["compression_arm_id"] == "event_regime_gated_only"] if not frontier.empty else pd.DataFrame()
    gated = gated_row.iloc[0].to_dict() if not gated_row.empty else {}
    raw_row = frontier.loc[frontier["compression_arm_id"] == "raw_r_series_variant_pool"] if not frontier.empty else pd.DataFrame()
    raw = raw_row.iloc[0].to_dict() if not raw_row.empty else {}

    text = f"""# Risk-on R 系列 Density Compression Patch 报告

## 1. 一页结论

patch decision: `{decision}`

preflight decision: `{preflight.get('density_binding_preflight_decision', '')}`

selected compression arm: `{selected or 'none'}`

本 patch 只评估 R 系列作为 risk_on high-recall / high-bridge source pool 的 density compression；它不是交易信号、不是模型、不是回测。

本次结论很明确：preflight 证明 R1/R2/R6/R7/R8 的 risk_on 问题主要是 density-binding，不是 bridge-binding；但当前 deterministic compression arms 没有任何一个能同时通过 train recall、train bridge、density、p95 与 family-share guard，因此输出 `risk_on_r_series_no_compression_candidate`。这是有效实验结论，不应改用 validation / robustness 表现更好的 arm 来补救。

frontier 通过项计数：train recall `{pass_counts['train_recall_pass']}/{pass_counts['total']}`，train bridge `{pass_counts['train_bridge_pass']}/{pass_counts['total']}`，density `<= 1.0x` `{pass_counts['density_pass']}/{pass_counts['total']}`，p95 `<= 4` `{pass_counts['p95_pass']}/{pass_counts['total']}`，single-family share `<= 65%` `{pass_counts['family65_pass']}/{pass_counts['total']}`。瓶颈仍然集中在 density / p95 / concentration。

## 2. Preflight 复核

- family-level confirmed core families: `{','.join(preflight.get('family_level_confirmed_core_families', []))}`
- variant-level confirmed core families: `{','.join(preflight.get('variant_level_confirmed_core_families', []))}`
- R5 negative control confirmed: `{preflight.get('r5_negative_control_confirmed')}`

{markdown_table(preflight_view)}

R5 是关键反例：它 density 低，但 recall 与 bridge 都差，因此 low density 本身不是好信号。R1/R2/R6/R7/R8 则相反：recall 与 bridge 均为正，主要卡在 density 和 p95。

原 08 的 `train_selection_max_density_vs_e1 = 0.50` 对 risk_on R 系列有害，因为它会把这些 high-bridge R family 在 selection 前置阶段排除，只留下低 density 但 bridge 更弱的候选。

## 3. Scope 与 Source Pool

preflight 的 family all-variants 只用于诊断机制；真正实现从 candidate family variant / event level 开始。默认 source policy 是 `event_regime_gated_first`，ungated 只作为 upper bound / sensitivity。

{markdown_table(source_pool)}

raw R pool 事件数 `{int(raw.get('event_count', 0) or 0)}`，density `{num(raw.get('density_vs_e1_full_denominator'), 2)}x`，p95 `{num(raw.get('events_per_instrument_year_p95'), 1)}`；event-regime-gated source pool 事件数 `{int(gated.get('event_count', 0) or 0)}`，density `{num(gated.get('density_vs_e1_full_denominator'), 2)}x`，p95 `{num(gated.get('events_per_instrument_year_p95'), 1)}`。gated 起步降低了密度，但仍远高于 `<= 1.0x` gate。

## 4. Score Spec 与字段约束

当前 `cross_section_feature_panel.parquet` 冻结为 31 列：

```text
{', '.join(FROZEN_FEATURE_PANEL_COLUMNS)}
```

本 patch 的 score spec 只使用这些 t0 可见字段。原 review 中提到但当前 panel 不可得的字段包括：`stock_vs_market_10d`、`close_to_ema60`、`close_to_ema20`、`ema60_positive_run`、`amount_ratio_20d`、`close_position_in_range`、`range_width_ratio_20d_60d`。这些字段不得被静默替代。

{markdown_table(score_view)}

R8 的 EMA-distance 原始字段不可得，因此显式使用 `return_60d` / `momentum_percentile_60d` / `close_to_high_60` 作为 proxy，并在 score spec 中标记 `proxy_score_used = true` 与 `missing_semantic_feature = ema_distance`。

R2 的核心语义是 near-high volume expansion，但当前 feature panel 没有 amount / volume 强度字段，因此 R2 默认是 non-scored core family。R2-only canonical events 采用 `unscored_canonical_policy = retain_and_audit`：不参与 score 排序，但保留并计入 density / recall / bridge / overlap audit，禁止 silent drop。

R2 单 family arm 的审计读数：canonical events `{int(r2.get('event_count', 0) or 0)}`，unscored canonical events `{int(r2.get('unscored_canonical_event_count', 0) or 0)}`，unscored density share `{pct(r2.get('unscored_canonical_density_share'))}`，train recall `{pct(r2.get('train_risk_on_incremental_recall_over_e1'))}`，train bridge delta `{pct(r2.get('train_risk_on_bridge_recall_delta_vs_e1'))}`，robustness recall `{pct(r2.get('robustness_risk_on_incremental_recall_over_e1'))}`，robustness bridge delta `{pct(r2.get('robustness_risk_on_bridge_recall_delta_vs_e1'))}`。它 recall 有价值，但 train bridge delta 低于 `+5 pct`，且 density / family-share 仍不过。

## 5. Compression Frontier

train-only selection 使用 train risk_on evidence；validation / robustness 是 read-only support/block，不参与换 arm。

### 5.1 Selection Score Top Arms

{markdown_table(frontier_view)}

### 5.2 最接近 Density Gate 的 Arms

{markdown_table(closest_density)}

### 5.3 Failure Distribution

{markdown_table(failure_counts)}

唯一通过 `density <= 1.0x` 的 `consensus_family_count__min3` 把 density 压到 `0.45x`、p95 压到 `2.0`，但 train bridge delta 为 `-17.7 pct`，说明简单共振过滤会压坏 bridge quality。多数保持 bridge 的 arms 仍然 density / p95 过高。

## 6. Selected Pool

| metric | value |
|---|---:|
| train risk_on incremental recall | {pct(row.get('train_risk_on_incremental_recall_over_e1'))} |
| robustness risk_on incremental recall | {pct(row.get('robustness_risk_on_incremental_recall_over_e1'))} |
| train risk_on bridge delta | {pct(row.get('train_risk_on_bridge_recall_delta_vs_e1'))} |
| robustness risk_on bridge delta | {pct(row.get('robustness_risk_on_bridge_recall_delta_vs_e1'))} |
| density vs E1 | {num(row.get('density_vs_e1_full_denominator'), 3)}x |
| p95 events / instrument-year | {num(row.get('events_per_instrument_year_p95'), 2)} |
| single-family density share max | {pct(row.get('single_family_density_share_max'))} |
| downstream 35 pct family-share pass | `{row.get('downstream_entry_family_share_35pct_pass', False)}` |
| label completeness | {pct(row.get('label_completeness_rate'))} |
| next-open executable | {pct(row.get('next_open_executable_rate'))} |
| unscored canonical events | {int(row.get('unscored_canonical_event_count', 0) or 0)} |

当前没有 selected compressed pool，因此 `risk_on_r_series_compressed_canonical_events.csv` 和 `risk_on_r_series_selected_compressed_variants.csv` 只有 schema / 空结果，可审计地表示没有 train-pass arm。selected event count = `{0 if selected_events.empty else len(selected_events)}`。

validation risk_on denominator 小于 `{VALIDATION_RISK_ON_SMALL_DENOMINATOR}` 时只作 diagnostic。本次没有 selected arm，因此 validation / robustness 不触发 support；frontier 中仍保留所有 arms 的 read-only validation / robustness metrics。

## 7. Gate 解释与后续方向

`risk_on_r_series_density_still_blocked`、`risk_on_r_series_bridge_degraded_blocked`、`risk_on_r_series_overfit_blocked` 和本次的 `risk_on_r_series_no_compression_candidate` 都是可接受实验结论。它们说明当前 deterministic compression 还没有找到“保留 R 系列 high bridge，同时把 density 压到 1.0x 以下”的切法。

`single_family_density_share <= 65%` 是本 patch 的 meta-label feature-source concentration guard，不等于 downstream direct-entry union 的 35% family-share gate。frontier 中 `downstream_entry_family_share_35pct_pass` 仍作为 read-only diagnostic 输出；若未来某 arm 只在 35%-65% 之间通过，本 patch 只能支持它作为 meta-label feature source，不能直接作为 09 entry union。

与 `requirement_patch_regime_specific_unions.md` 的关系：regime-specific union patch 是消融诊断，回答 risk_on / transition 分开选是否改变结论；本 patch 是 risk_on P0 主线。对 risk_on R 系列，下一阶段重点不是再换 regime selection，而是在 high-bridge R-series 候选池上做更有监督边界的 density compression / ranker，例如 bridge-positive ranker 或显式 amount/volume recompute 后的 R2 score。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run_patch(source_manifest_path: Path) -> dict[str, Any]:
    input_status, input_reasons, input_paths, source_manifest = validate_input_gate(source_manifest_path)
    source_hash = file_sha256(source_manifest_path) if source_manifest_path.exists() else ""
    requirement_hash = file_sha256(PATCH_REQUIREMENT) if PATCH_REQUIREMENT.exists() else ""
    output_frames: dict[str, pd.DataFrame] = {}
    output_paths: dict[str, Path] = {}
    PATCH_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    PATCH_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PATCH_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    PATCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if input_status != "pass":
        decision = "risk_on_r_series_input_blocked"
        gate_summary = {"input_gate_result": input_status, "input_gate_failures": input_reasons}
        manifest_path = PATCH_MANIFEST_DIR / "risk_on_r_series_density_compression_manifest.json"
        write_json(
            manifest_path,
            {
                "experiment_name": "08 risk-on R-series density compression patch",
                "decision": decision,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "input_gate_result": input_status,
                "input_gate_failures": input_reasons,
                "source_08_manifest_hash": source_hash,
                "patch_requirement_hash": requirement_hash,
            },
        )
        return {"decision": decision, "manifest_path": str(manifest_path)}

    tables = load_inputs()
    preflight, preflight_summary = build_preflight(tables, source_hash, requirement_hash)
    output_frames["risk_on_r_series_density_binding_preflight"] = preflight
    if preflight_summary["density_binding_preflight_decision"] != "risk_on_r_series_density_binding_confirmed":
        decision = "risk_on_r_series_density_binding_not_confirmed"
        selected_metrics: dict[str, Any] = {"gate_failures": "density_binding_preflight"}
        frontier = pd.DataFrame()
        gate_summary = gate_summary_frame(decision, preflight_summary, selected_metrics)
        output_frames["risk_on_r_series_gate_summary"] = gate_summary
    else:
        score_spec = build_score_spec(tables["feature_panel"], source_hash, requirement_hash)
        output_frames["risk_on_r_series_score_spec"] = score_spec
        score_spec_path = PATCH_TABLE_DIR / "risk_on_r_series_score_spec.csv"
        write_df(score_spec_path, score_spec)
        output_paths["risk_on_r_series_score_spec"] = score_spec_path

        raw_instances = attach_missing_score_features(
            source_instances(tables["instances"], gated_only=False),
            tables["feature_panel"],
        )
        gated_instances = attach_missing_score_features(
            source_instances(tables["instances"], gated_only=True),
            tables["feature_panel"],
        )
        scored_raw = score_instances(raw_instances, score_spec)
        scored_gated = score_instances(gated_instances, score_spec)
        event_scores_path = PATCH_CACHE_DIR / "risk_on_r_series_event_scores.parquet"
        write_df(event_scores_path, scored_gated)
        output_frames["risk_on_r_series_event_scores_local"] = scored_gated

        arms = build_arms(scored_raw, scored_gated)
        template = tables["capture"].loc[tables["capture"]["candidate_scope_id"] == E1_SCOPE].copy()
        labels = tables["labels"].loc[tables["labels"]["label_scope"] == "event_instance"].copy()
        captures = {arm_id: build_capture_from_template(events, template, labels) for arm_id, events in arms.items()}
        metadata = {
            arm_id: pipeline.scope_metadata(
                arm_id,
                pipeline.UNION_SCOPE,
                "risk_on_r_series_compressed_candidate_pool",
                "compressed_pool",
                "runnable_existing_data",
                "risk_on_r_series_density_compression",
            )
            for arm_id in arms
        }
        e1_capture = tables["capture"].loc[tables["capture"]["candidate_scope_id"] == E1_SCOPE].copy()
        full_capture = tables["capture"].loc[tables["capture"]["candidate_scope_id"] == FULL_07_SCOPE].copy()
        incremental = pipeline.build_incremental_recall(captures, metadata, e1_capture, full_capture)
        bridge_custom = build_bridge_recall(captures, metadata)
        bridge_e1 = build_bridge_recall({E1_SCOPE: e1_capture}, {E1_SCOPE: pipeline.scope_metadata(E1_SCOPE, E1_SCOPE)})
        bridge = pd.concat([bridge_custom, bridge_e1], ignore_index=True)
        any_recall = build_any_recall(captures, metadata)
        frontier = build_frontier(arms, captures, incremental, bridge, tables["density"], labels)
        selected_arm, frontier = select_train_arm(frontier)
        decision, selected_metrics = final_decision(frontier, selected_arm)
        gate_summary = gate_summary_frame(decision, preflight_summary, selected_metrics)
        selected_events = arms.get(selected_arm, pd.DataFrame()).copy()

        output_frames.update(
            {
                "risk_on_r_series_source_pool_summary": source_pool_summary(scored_raw, scored_gated),
                "risk_on_r_series_compression_frontier": frontier,
                "risk_on_r_series_selected_compressed_variants": selected_variants(selected_events, scored_gated, selected_arm),
                "risk_on_r_series_compressed_canonical_events": selected_events,
                "risk_on_r_series_recall_bridge_density_by_split": pd.concat(
                    [
                        incremental.assign(metric_family="incremental_recall"),
                        bridge_custom.assign(metric_family="bridge_recall"),
                        any_recall.assign(metric_family="any_recall"),
                    ],
                    ignore_index=True,
                    sort=False,
                ),
                "risk_on_r_series_threshold_sensitivity": frontier.copy(),
                "risk_on_r_series_label_quality_readout": pd.DataFrame(
                    [
                        {
                            "compression_arm_id": arm_id,
                            **label_quality_for_events(events, labels),
                        }
                        for arm_id, events in arms.items()
                    ]
                ),
                "risk_on_r_series_overlap_diagnostic": overlap_diagnostic(selected_events, arms),
                "risk_on_r_series_gate_summary": gate_summary,
            }
        )

    for name in OUTPUT_TABLE_NAMES:
        frame = output_frames.get(name, pd.DataFrame())
        path = PATCH_TABLE_DIR / f"{name}.csv"
        write_df(path, frame)
        output_paths[name] = path
    report_path = PATCH_REPORT_DIR / "risk_on_r_series_density_compression_report.md"
    write_report(
        report_path,
        str(output_frames["risk_on_r_series_gate_summary"].iloc[0]["risk_on_r_series_density_compression_decision"]),
        preflight_summary,
        output_frames["risk_on_r_series_gate_summary"].iloc[0].to_dict(),
        output_frames.get("risk_on_r_series_compression_frontier", pd.DataFrame()),
    )
    output_paths["report"] = report_path
    event_scores_path = PATCH_CACHE_DIR / "risk_on_r_series_event_scores.parquet"
    if event_scores_path.exists():
        output_paths["risk_on_r_series_event_scores_local"] = event_scores_path

    manifest_path = PATCH_MANIFEST_DIR / "risk_on_r_series_density_compression_manifest.json"
    final_decision_value = str(
        output_frames["risk_on_r_series_gate_summary"].iloc[0]["risk_on_r_series_density_compression_decision"]
    )
    manifest = {
        "experiment_name": "08 risk-on R-series density compression patch",
        "run_scope": "risk_on_r_series_density_compression_patch",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_git_revision": pipeline.git_revision(),
        "decision": final_decision_value,
        "source_08_manifest_path": str(source_manifest_path.resolve()),
        "source_08_manifest_hash": source_hash,
        "source_08_decision": source_manifest.get("decision", ""),
        "patch_requirement_path": str(PATCH_REQUIREMENT.resolve()),
        "patch_requirement_hash": requirement_hash,
        "input_gate_result": input_status,
        "input_gate_failures": input_reasons,
        "density_binding_preflight": preflight_summary,
        "selected_compression_arm_id": output_frames["risk_on_r_series_gate_summary"].iloc[0].get(
            "selected_compression_arm_id", ""
        ),
        "train_only_selection_config": {
            "train_bridge_delta_min": TRAIN_BRIDGE_DELTA_MIN,
            "robustness_bridge_delta_min": ROBUSTNESS_BRIDGE_DELTA_MIN,
            "recall_min": RECALL_MIN,
            "density_vs_e1_max": DENSITY_VS_E1_MAX,
            "p95_max": P95_MAX,
            "single_family_share_max": SINGLE_FAMILY_SHARE_MAX,
            "source_variant_policy": SOURCE_VARIANT_POLICY,
            "unscored_canonical_policy": UNSCORED_CANONICAL_POLICY,
        },
        "ranker_arm_status": "not_evaluated_deterministic_run",
        "ranker_label_horizon_cutoff_purge_policy": "not_evaluated",
        "input_paths": {key: str(value.resolve()) for key, value in sorted(input_paths.items())},
        "input_hashes": collect_hashes(input_paths),
        "output_paths": {key: str(value.resolve()) for key, value in sorted(output_paths.items())},
        "output_hashes": collect_hashes(output_paths),
        "input_artifacts": artifact_metadata(input_paths),
        "output_artifacts": artifact_metadata(output_paths, output_frames),
    }
    write_json(manifest_path, manifest)
    return {
        "decision": final_decision_value,
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "check-drift":
        ok, failures = check_requirement_alignment()
        print(f"alignment_status={'pass' if ok else 'fail'}")
        if failures:
            print("alignment_failures=" + ";".join(failures))
        return 0 if ok else 2
    result = run_patch(Path(args.source_manifest).resolve())
    print(f"decision={result['decision']}")
    print(f"manifest={result['manifest_path']}")
    if "report_path" in result:
        print(f"report={result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

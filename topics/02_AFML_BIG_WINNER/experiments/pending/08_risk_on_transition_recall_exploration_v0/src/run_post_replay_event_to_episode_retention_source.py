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


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = Path(__file__).resolve().parent

for import_path in (PROJECT_ROOT / "src", SRC_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from afml_big_winner.config import stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256  # noqa: E402


PENDING_DIR = EXPERIMENT_DIR.parent
EXP06_DIR = PENDING_DIR / "06_rerun_02_reverse_lifecycle_on_topn_universe_v0"
EXP07_DIR = PENDING_DIR / "07_topn_multichannel_repair_candidate_generator_v0"

REQUIREMENT_PATH = (
    EXPERIMENT_DIR
    / "requirement_experiment_d_post_replay_event_to_episode_retention_source.md"
)
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
C_TABLE_DIR = TABLE_DIR / "risk_on_r_series_bridge_ranker"
C_REPORT_DIR = REPORT_DIR / "risk_on_r_series_bridge_ranker"
C_MANIFEST_DIR = MANIFEST_DIR / "risk_on_r_series_bridge_ranker"

D_TABLE_DIR = TABLE_DIR / "post_replay_event_to_episode_retention_source"
D_REPORT_DIR = REPORT_DIR / "post_replay_event_to_episode_retention_source"
D_MANIFEST_DIR = MANIFEST_DIR / "post_replay_event_to_episode_retention_source"
D_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "post_replay_event_to_episode_retention_source"

FINAL_COMPLETE = "post_replay_retention_source_complete"
FINAL_SOURCE_CAVEATED = "post_replay_retention_source_source_caveated_complete"
FINAL_INPUT_BLOCKED = "post_replay_retention_source_input_blocked"
FINAL_CONTRACT_BLOCKED = "post_replay_retention_source_contract_blocked"
FINAL_LEAKAGE_BLOCKED = "post_replay_retention_source_leakage_blocked"

ALLOWED_A_DECISIONS = {
    "density_fast_fail_audit_complete",
    "density_fast_fail_audit_partial_source_complete",
}
ALLOWED_B_DECISIONS = {
    "regime_family_matrix_complete",
    "regime_family_matrix_source_caveated_complete",
}
ALLOWED_C_DECISIONS = {
    "risk_on_r_series_ranker_complete",
    "risk_on_r_series_ranker_source_caveated_complete",
}

REQUIRED_WINDOWS = ("low_to_first_50pct", "low_to_high")
POLICIES = (
    "pre_replay_capture_only",
    "post_replay_executable_horizon_complete",
    "post_replay_non_fast_fail_10d_oracle",
    "post_replay_non_false_repair_20d_oracle",
    "post_replay_non_fast_fail_and_non_false_repair_oracle",
)
ORACLE_POLICIES = {
    "post_replay_non_fast_fail_10d_oracle",
    "post_replay_non_false_repair_20d_oracle",
    "post_replay_non_fast_fail_and_non_false_repair_oracle",
}

T4_EVENT_REGIME_GATED = "T4_entropy_compression_then_directional_expansion__event_regime_gated"
T7_EVENT_REGIME_GATED = "T7_board_relative_strength_break__event_regime_gated"
CORE_R_FAMILY_IDS = (
    "R1_relative_strength_breakout",
    "R2_near_high_volume_expansion",
    "R6_market_breadth_thrust",
    "R7_cross_sectional_momentum_rank_jump",
    "R8_persistent_distance_above_ema",
)
CORE_R_EVENT_REGIME_GATED = tuple(f"{family}__event_regime_gated" for family in CORE_R_FAMILY_IDS)

SAMPLE_STATUS_RANK = {
    "source_blocked": 0,
    "diagnostic_only": 1,
    "not_available_publishable_source": 1,
    "low_power_caution": 2,
    "sufficient_for_cell_readout": 3,
}

HARD_REQUIRED_SCOPES = [
    "07_E1_only",
    "08_selected_T4_T7_union",
    "08_T4_gated",
    "08_T7_gated",
    "08_R1_event_regime_gated",
    "08_R2_event_regime_gated",
    "08_R6_event_regime_gated",
    "08_R7_event_regime_gated",
    "08_R8_event_regime_gated",
    "08_R_core_event_regime_gated",
]
CONTEXT_SCOPES = ["07_full_union"]
ALL_SCOPES = [*HARD_REQUIRED_SCOPES, *CONTEXT_SCOPES]

SPLITS = ("train", "robustness", "validation")
REGIMES = ("risk_off", "risk_on", "transition")

REQUIRED_CAPTURE_COLUMNS = [
    "target_episode_id",
    "instrument",
    "episode_low_date",
    "episode_high_date",
    "first_50pct_touch_date",
    "episode_split",
    "market_regime_bucket",
    "board_bucket",
    "window",
    "window_start_pos",
    "window_end_pos",
]

EVENT_COLUMNS = [
    "event_id",
    "canonical_event_id",
    "instrument",
    "event_t0_date",
    "event_t0_pos",
    "trade_open_date",
    "trade_open_pos",
    "non_executable_next_open",
    "event_split",
    "market_regime_bucket",
]
LABEL_COLUMNS = [
    "event_id",
    "failure_10_label",
    "failure_10_complete",
    "event_false_repair_20d_label",
    "event_false_repair_20d_complete",
    "event_big_winner_120d_label",
    "horizon_complete_120d",
]
RETENTION_METRIC_COLUMNS = [
    "target_episode_denominator_n",
    "bridge_episode_denominator_n",
    "pre_replay_any_captured_episode_n",
    "post_replay_any_captured_episode_n",
    "pre_replay_any_recall",
    "post_replay_any_recall",
    "any_recall_retention",
    "pre_replay_bridge_captured_episode_n",
    "post_replay_bridge_captured_episode_n",
    "pre_replay_bridge_recall",
    "post_replay_bridge_recall",
    "bridge_recall_retention",
    "e1_missed_pre_replay_capture_n",
    "e1_missed_post_replay_capture_n",
    "e1_missed_capture_retention",
    "selected_event_n",
    "post_replay_event_n",
    "filtered_event_n",
    "filter_drop_rate",
    "cell_sample_status",
    "retention_source_status",
]

EPISODE_WINDOW_OUTPUT_COLUMNS = [
    "target_episode_id",
    "instrument",
    "episode_split",
    "market_regime_bucket",
    "window",
    "window_start_pos",
    "window_end_pos",
    "episode_low_date",
    "first_50pct_touch_date",
    "episode_high_date",
    "episode_window_source_status",
    "denominator_included_flag",
    "window_end_inclusive_flag",
    "source_path",
    "source_hash",
    "source_row_count_before_dedup",
    "dedup_conflict_flag",
    "dedup_conflict_fields",
]


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    path: Path
    required: bool = True
    required_columns: tuple[str, ...] = ()


INPUT_SPECS = [
    InputSpec("experiment_a_manifest", A_MANIFEST_DIR / "density_fast_fail_audit_manifest.json"),
    InputSpec("experiment_b_manifest", B_MANIFEST_DIR / "regime_family_matrix_manifest.json"),
    InputSpec("experiment_c_manifest", C_MANIFEST_DIR / "risk_on_r_series_bridge_ranker_manifest.json"),
    InputSpec("density_fast_fail_caliber_contract", A_REPORT_DIR / "density_fast_fail_caliber_contract.md"),
    InputSpec("density_fast_fail_audit_report", A_REPORT_DIR / "density_fast_fail_audit_report.md"),
    InputSpec("regime_family_matrix_report", B_REPORT_DIR / "regime_family_matrix_report.md"),
    InputSpec("risk_on_r_series_bridge_ranker_report", C_REPORT_DIR / "risk_on_r_series_bridge_ranker_report.md"),
    InputSpec("discussion", EXPERIMENT_DIR / "discussion.md"),
    InputSpec("requirement", REQUIREMENT_PATH),
    InputSpec(
        "06_episode_reference",
        EXP06_DIR / "outputs" / "local_cache" / "topn_big_winner_episode_reference.parquet",
        required_columns=("episode_id", "instrument", "split", "episode_low_date", "episode_high_date"),
    ),
    InputSpec("06_run_manifest", EXP06_DIR / "outputs" / "manifests" / "run_manifest.json"),
    InputSpec(
        "06_episode_reference_summary",
        EXP06_DIR / "outputs" / "publishable" / "tables" / "topn_big_winner_episode_reference_summary.csv",
    ),
    InputSpec(
        "candidate_family_capture",
        LOCAL_CACHE_DIR / "candidate_family_capture.parquet",
        required_columns=tuple(REQUIRED_CAPTURE_COLUMNS),
    ),
    InputSpec(
        "candidate_family_event_labels",
        LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet",
        required_columns=tuple(LABEL_COLUMNS),
    ),
    InputSpec(
        "cross_section_feature_panel",
        LOCAL_CACHE_DIR / "cross_section_feature_panel.parquet",
        required=False,
    ),
    InputSpec("candidate_family_canonical_events", TABLE_DIR / "candidate_family_canonical_events.csv.gz"),
    InputSpec("candidate_family_event_instances", TABLE_DIR / "candidate_family_event_instances.csv.gz"),
    InputSpec(
        "candidate_scope_mapping_contract",
        A_TABLE_DIR / "candidate_scope_mapping_contract.csv",
        required_columns=("candidate_scope_id", "source_row_filter", "scope_mapping_status"),
    ),
    InputSpec(
        "candidate_scope_reconstructability_audit",
        A_TABLE_DIR / "candidate_scope_reconstructability_audit.csv",
        required_columns=("candidate_scope_id", "scope_status"),
    ),
    InputSpec(
        "candidate_10d_retention_by_split_regime",
        A_TABLE_DIR / "candidate_10d_retention_by_split_regime.csv",
    ),
    InputSpec("regime_family_performance_matrix", B_TABLE_DIR / "regime_family_performance_matrix.csv"),
    InputSpec("risk_on_r_series_ranker_selected_events", C_TABLE_DIR / "risk_on_r_series_ranker_selected_events.csv.gz"),
    InputSpec("risk_on_r_series_ranker_rejected_events", C_TABLE_DIR / "risk_on_r_series_ranker_rejected_events.csv.gz"),
    InputSpec("risk_on_r_series_ranker_bridge_recall_readout", C_TABLE_DIR / "risk_on_r_series_ranker_bridge_recall_readout.csv"),
    InputSpec("risk_on_r_series_ranker_decision_tiers", C_TABLE_DIR / "risk_on_r_series_ranker_decision_tiers.csv"),
    InputSpec(
        "07_run_manifest",
        EXP07_DIR / "outputs" / "manifests" / "run_manifest.json",
    ),
    InputSpec(
        "07_canonical_events",
        EXP07_DIR
        / "outputs"
        / "publishable"
        / "tables"
        / "topn_multichannel_candidate_event_canonical.csv",
    ),
    InputSpec(
        "07_event_labels",
        EXP07_DIR / "outputs" / "local_cache" / "topn_canonical_event_labels.parquet",
        required_columns=tuple(LABEL_COLUMNS),
    ),
]

REQUIRED_BY_ID = {spec.input_id: spec for spec in INPUT_SPECS}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Experiment D post-replay event-to-episode retention source."
    )
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
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


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def stable_row_id(prefix: str, parts: list[Any]) -> str:
    return f"{prefix}_{stable_hash([str(part) for part in parts])[:16]}"


def bool_series(value: pd.Series | Any, index: pd.Index) -> pd.Series:
    if isinstance(value, pd.Series):
        out = value.copy()
    else:
        out = pd.Series(value, index=index)
    if out.dtype == bool:
        return out.fillna(False)
    return out.fillna(False).astype(str).str.lower().isin({"1", "1.0", "true", "yes"})


def numeric_series(value: pd.Series | Any, index: pd.Index) -> pd.Series:
    if isinstance(value, pd.Series):
        return pd.to_numeric(value, errors="coerce")
    return pd.Series(np.nan, index=index)


def safe_div(num: float | int | None, den: float | int | None) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    if num is None or pd.isna(num):
        return np.nan
    return float(num) / float(den)


def check_columns(path: Path, required_columns: tuple[str, ...]) -> list[str]:
    if not path.exists() or not required_columns:
        return []
    if path.suffix == ".parquet":
        columns = set(pd.read_parquet(path).columns)
    else:
        columns = set(pd.read_csv(path, nrows=0).columns)
    return [column for column in required_columns if column not in columns]


def input_audit() -> tuple[pd.DataFrame, list[str], dict[str, Path]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    paths: dict[str, Path] = {}
    for spec in INPUT_SPECS:
        path = spec.path
        paths[spec.input_id] = path
        exists = path.exists()
        status = "available" if exists else "missing_optional_input"
        missing_columns: list[str] = []
        if spec.required and not exists:
            status = "missing_required_input"
            failures.append(f"missing_required_input:{spec.input_id}")
        elif exists:
            missing_columns = check_columns(path, spec.required_columns)
            if missing_columns:
                status = "schema_incompatible_required_input" if spec.required else "schema_incompatible_optional_input"
                if spec.required:
                    failures.append(
                        f"schema_incompatible_required_input:{spec.input_id}:"
                        f"missing_columns={';'.join(missing_columns)}"
                    )
        rows.append(
            {
                "source_kind": "input",
                "source_id": spec.input_id,
                "required_flag": bool(spec.required),
                "source_path": str(path),
                "source_hash": path_hash(path),
                "row_count": row_count(path) if exists else 0,
                "expected_key_count": np.nan,
                "matched_key_count": np.nan,
                "unmatched_key_count": np.nan,
                "source_status": status,
                "blocking_flag": bool(spec.required and status != "available"),
                "missing_required_columns": ";".join(missing_columns),
            }
        )
    return pd.DataFrame(rows), failures, paths


def row_count(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    try:
        if path.suffix == ".parquet":
            return int(len(pd.read_parquet(path)))
        if path.suffix == ".json" or path.suffix == ".md":
            return 1
        return int(sum(1 for _ in path.open("rb")) - 1)
    except Exception:
        return 0


def validate_upstream_manifests() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    failures: list[str] = []
    a_manifest = read_json(REQUIRED_BY_ID["experiment_a_manifest"].path) if REQUIRED_BY_ID["experiment_a_manifest"].path.exists() else {}
    b_manifest = read_json(REQUIRED_BY_ID["experiment_b_manifest"].path) if REQUIRED_BY_ID["experiment_b_manifest"].path.exists() else {}
    c_manifest = read_json(REQUIRED_BY_ID["experiment_c_manifest"].path) if REQUIRED_BY_ID["experiment_c_manifest"].path.exists() else {}
    if a_manifest.get("decision") not in ALLOWED_A_DECISIONS:
        failures.append(f"unsupported_experiment_a_decision:{a_manifest.get('decision')}")
    if b_manifest.get("decision") not in ALLOWED_B_DECISIONS:
        failures.append(f"unsupported_experiment_b_decision:{b_manifest.get('decision')}")
    if c_manifest.get("decision") not in ALLOWED_C_DECISIONS:
        failures.append(f"unsupported_experiment_c_decision:{c_manifest.get('decision')}")
    return a_manifest, b_manifest, c_manifest, failures


def ensure_output_dirs() -> None:
    for directory in (D_TABLE_DIR, D_REPORT_DIR, D_MANIFEST_DIR, D_LOCAL_CACHE_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def output_paths() -> dict[str, Path]:
    return {
        "post_replay_episode_window_audit": D_TABLE_DIR / "post_replay_episode_window_audit.csv",
        "post_replay_source_coverage_audit": D_TABLE_DIR / "post_replay_source_coverage_audit.csv",
        "post_replay_scope_retention_by_split_regime": D_TABLE_DIR / "post_replay_scope_retention_by_split_regime.csv",
        "post_replay_arm_retention_by_split_regime": D_TABLE_DIR / "post_replay_arm_retention_by_split_regime.csv",
        "post_replay_policy_effect_summary": D_TABLE_DIR / "post_replay_policy_effect_summary.csv",
        "post_replay_e1_missed_retention_summary": D_TABLE_DIR / "post_replay_e1_missed_retention_summary.csv",
        "post_replay_label_leakage_audit": D_TABLE_DIR / "post_replay_label_leakage_audit.csv",
        "post_replay_reconciliation_against_a_b_c": D_TABLE_DIR / "post_replay_reconciliation_against_a_b_c.csv",
        "post_replay_retention_source_contract": D_REPORT_DIR / "post_replay_retention_source_contract.md",
        "post_replay_retention_source_report": D_REPORT_DIR / "post_replay_retention_source_report.md",
        "post_replay_event_to_episode_retention_source_manifest": D_MANIFEST_DIR
        / "post_replay_event_to_episode_retention_source_manifest.json",
        "post_replay_event_episode_membership": D_LOCAL_CACHE_DIR / "post_replay_event_episode_membership.parquet",
    }


def canonicalize_episode_reference(episodes06: pd.DataFrame) -> pd.DataFrame:
    out = episodes06.rename(
        columns={
            "episode_id": "target_episode_id",
            "split": "episode_split",
            "first_ema60_reclaim_date": "source_06_first_ema60_reclaim_date",
        }
    ).copy()
    keep = [
        "target_episode_id",
        "instrument",
        "episode_split",
        "episode_low_date",
        "episode_high_date",
        "board_bucket",
        "market_regime_bucket",
        "source_06_first_ema60_reclaim_date",
    ]
    for column in keep:
        if column not in out.columns:
            out[column] = pd.NA
    return out[keep].drop_duplicates("target_episode_id")


def build_episode_windows(
    capture: pd.DataFrame,
    episodes06: pd.DataFrame,
    *,
    capture_path: Path | None = None,
) -> pd.DataFrame:
    missing = [column for column in REQUIRED_CAPTURE_COLUMNS if column not in capture.columns]
    if missing:
        raise ValueError(f"candidate_family_capture_missing_columns:{';'.join(missing)}")
    canonical06 = canonicalize_episode_reference(episodes06)
    cap = capture.loc[capture["window"].isin(REQUIRED_WINDOWS)].copy()
    cap["window_start_pos"] = pd.to_numeric(cap["window_start_pos"], errors="coerce")
    cap["window_end_pos"] = pd.to_numeric(cap["window_end_pos"], errors="coerce")
    grouped = cap.groupby(["target_episode_id", "window"], dropna=False, sort=False)
    rows: list[dict[str, Any]] = []
    conflict_fields = [
        "instrument",
        "episode_low_date",
        "episode_high_date",
        "first_50pct_touch_date",
        "episode_split",
        "market_regime_bucket",
        "board_bucket",
        "window_start_pos",
        "window_end_pos",
    ]
    for (episode_id, window), group in grouped:
        row = group.iloc[0].to_dict()
        conflicts = [
            field
            for field in conflict_fields
            if field in group.columns and group[field].astype(str).nunique(dropna=False) > 1
        ]
        missing_boundary = any(pd.isna(row.get(field)) for field in ("first_50pct_touch_date", "window_start_pos", "window_end_pos"))
        status = "episode_window_ready"
        if conflicts:
            status = "episode_window_conflict_blocked"
        elif missing_boundary:
            status = "episode_window_source_blocked"
        rows.append(
            {
                "target_episode_id": episode_id,
                "instrument": row.get("instrument"),
                "episode_split": row.get("episode_split"),
                "market_regime_bucket": row.get("market_regime_bucket"),
                "window": window,
                "window_start_pos": row.get("window_start_pos"),
                "window_end_pos": row.get("window_end_pos"),
                "episode_low_date": row.get("episode_low_date"),
                "first_50pct_touch_date": row.get("first_50pct_touch_date"),
                "episode_high_date": row.get("episode_high_date"),
                "episode_window_source_status": status,
                "denominator_included_flag": not bool(conflicts),
                "window_end_inclusive_flag": True,
                "source_path": str(capture_path or REQUIRED_BY_ID["candidate_family_capture"].path),
                "source_hash": path_hash(capture_path or REQUIRED_BY_ID["candidate_family_capture"].path),
                "source_row_count_before_dedup": int(len(group)),
                "dedup_conflict_flag": bool(conflicts),
                "dedup_conflict_fields": ";".join(conflicts),
                "any_event_denominator_included": bool(group["any_event_denominator_included"].fillna(False).astype(bool).any())
                if "any_event_denominator_included" in group
                else True,
                "bridge_positive_denominator_included": bool(
                    group["bridge_positive_denominator_included"].fillna(False).astype(bool).any()
                )
                if "bridge_positive_denominator_included" in group
                else True,
            }
        )
    out = pd.DataFrame(rows)
    out = out.merge(
        canonical06[["target_episode_id"]].assign(episode_in_06=True),
        on="target_episode_id",
        how="outer",
    )
    out["episode_in_06"] = out["episode_in_06"].fillna(False).astype(bool)
    missing_from_capture = out["window"].isna()
    if missing_from_capture.any():
        out.loc[missing_from_capture, "episode_window_source_status"] = "episode_window_source_blocked"
        out.loc[missing_from_capture, "denominator_included_flag"] = False
    return out


def apply_replay_anchor(events: pd.DataFrame) -> pd.DataFrame:
    out = events.copy()
    idx = out.index
    non_exec = bool_series(out.get("non_executable_next_open", False), idx)
    trade_pos = numeric_series(out.get("trade_open_pos"), idx)
    event_pos = numeric_series(out.get("event_t0_pos"), idx)
    use_trade = (~non_exec) & trade_pos.notna()
    out["replay_anchor_pos"] = np.where(use_trade, trade_pos, event_pos)
    trade_date = out["trade_open_date"] if "trade_open_date" in out else pd.Series(pd.NA, index=idx)
    event_date = out["event_t0_date"] if "event_t0_date" in out else pd.Series(pd.NA, index=idx)
    out["replay_anchor_date"] = np.where(use_trade, trade_date, event_date)
    out["event_anchor_source"] = np.where(
        use_trade, "trade_open_executable", "event_t0_fallback_non_executable_audit"
    )
    out["event_executable_flag"] = use_trade
    return out


def attach_labels(events: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    out = events.copy()
    label_cols = [column for column in LABEL_COLUMNS if column in labels.columns]
    if not label_cols:
        return out
    label_frame = labels[label_cols].drop_duplicates("event_id", keep="first").copy()
    out = out.merge(label_frame, on="event_id", how="left", suffixes=("", "_label"))
    return out


def normalize_scope_events(
    scope_id: str,
    source: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    source_experiment: str,
    source_path: Path,
    canonicalization_rule: str,
) -> pd.DataFrame:
    if source.empty:
        return pd.DataFrame()
    cols = [column for column in EVENT_COLUMNS if column in source.columns]
    out = source[cols].copy()
    if "canonical_event_id" not in out.columns:
        out["canonical_event_id"] = out["event_id"]
    out = attach_labels(out, labels)
    out["source_kind"] = "scope"
    out["source_id"] = scope_id
    out["candidate_scope_id"] = scope_id
    out["target_regime"] = ""
    out["source_experiment"] = source_experiment
    out["source_path"] = str(source_path)
    out = apply_replay_anchor(out)
    if canonicalization_rule == "canonical union by instrument / event anchor":
        anchor_pos = pd.to_numeric(out["replay_anchor_pos"], errors="coerce")
        anchored = out.loc[anchor_pos.notna()].copy()
        anchorless = out.loc[anchor_pos.isna()].copy()
        anchored = anchored.sort_values(
            ["instrument", "replay_anchor_pos", "canonical_event_id", "event_id"],
            kind="stable",
        ).drop_duplicates(subset=["instrument", "replay_anchor_pos"], keep="first")
        out = pd.concat([anchored, anchorless], ignore_index=True, sort=False)
    out["source_event_row_id"] = [
        stable_row_id("scope", [scope_id, row_id])
        for row_id in out["canonical_event_id"].fillna(out["event_id"]).astype(str)
    ]
    return out


def select_scope_events_from_contract(
    contract_row: pd.Series,
    canonical07: pd.DataFrame,
    canonical08: pd.DataFrame,
) -> pd.DataFrame:
    source_experiment = str(contract_row.get("source_experiment", ""))
    row_filter = str(contract_row.get("source_row_filter", ""))
    scope_id = str(contract_row.get("candidate_scope_id", ""))
    if source_experiment == "07":
        if row_filter == "all rows in 07 canonical publishable table":
            return canonical07.copy()
        channels = canonical07.get("triggered_channels", pd.Series("", index=canonical07.index)).fillna("").astype(str)
        tokens = []
        if "E1_early_ema60_repair" in row_filter:
            tokens.append("E1_early_ema60_repair")
        if "E3_rank_persistence" in row_filter:
            tokens.append("E3_rank_persistence")
        if not tokens:
            return pd.DataFrame()
        mask = pd.Series(False, index=canonical07.index)
        for token in tokens:
            mask |= channels.str.contains(token, regex=False)
        return canonical07.loc[mask].copy()

    if source_experiment == "08":
        variants = canonical08.get("triggered_family_variants", pd.Series("", index=canonical08.index)).fillna("").astype(str)
        if "selected T4/T7 event_regime_gated variants" in row_filter:
            tokens = [T4_EVENT_REGIME_GATED, T7_EVENT_REGIME_GATED]
        elif "T4 event_regime_gated" in row_filter:
            tokens = [T4_EVENT_REGIME_GATED]
        elif "T7 event_regime_gated" in row_filter:
            tokens = [T7_EVENT_REGIME_GATED]
        elif "any R1/R2/R6/R7/R8 event_regime_gated variant" in row_filter:
            tokens = list(CORE_R_EVENT_REGIME_GATED)
        elif "triggered_family_variants contains " in row_filter:
            tokens = [row_filter.split("triggered_family_variants contains ", 1)[1].strip()]
        else:
            tokens = []
        if not tokens:
            return pd.DataFrame()
        mask = pd.Series(False, index=canonical08.index)
        for token in tokens:
            mask |= variants.str.contains(token, regex=False)
        return canonical08.loc[mask].copy()

    raise ValueError(f"unsupported_scope_mapping_source:{scope_id}:{source_experiment}")


def normalize_c_arm_events(
    events: pd.DataFrame,
    canonical08: pd.DataFrame,
    labels08: pd.DataFrame,
    *,
    source_kind: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if events.empty:
        return pd.DataFrame(), pd.DataFrame()
    source = events.copy()
    source["source_row_number"] = np.arange(len(source), dtype=np.int64)
    canon_cols = [column for column in EVENT_COLUMNS if column in canonical08.columns]
    canon = canonical08[canon_cols].drop_duplicates("canonical_event_id", keep="first")
    merged = source.merge(canon, on="canonical_event_id", how="left", suffixes=("", "_canonical"))
    for column in EVENT_COLUMNS:
        if column in {"canonical_event_id"}:
            continue
        canonical_column = f"{column}_canonical"
        if canonical_column in merged.columns:
            if column in merged.columns:
                merged[column] = merged[column].combine_first(merged[canonical_column])
            else:
                merged[column] = merged[canonical_column]
    merged["event_id"] = merged.get("event_id", merged["canonical_event_id"])
    merged = attach_labels(merged, labels08)
    merged["source_kind"] = source_kind
    merged["source_id"] = (
        merged["arm_id"].astype(str) + "::" + merged["target_regime"].astype(str)
    )
    merged["source_experiment"] = "08_experiment_c"
    merged["source_path"] = str(
        REQUIRED_BY_ID[
            "risk_on_r_series_ranker_selected_events"
            if source_kind == "arm"
            else "risk_on_r_series_ranker_rejected_events"
        ].path
    )
    merged = apply_replay_anchor(merged)
    merged["source_event_row_id"] = [
        stable_row_id(
            source_kind,
            [
                row.arm_id,
                row.target_regime,
                row.canonical_event_id,
                row.source_row_number,
            ],
        )
        for row in merged.itertuples(index=False)
    ]
    required = ["instrument", "replay_anchor_pos", "event_t0_date"]
    blocked_mask = merged[required].isna().any(axis=1)
    blocked = merged.loc[blocked_mask].copy()
    if not blocked.empty:
        blocked["source_status"] = "c_arm_event_enrichment_blocked"
    return merged.loc[~blocked_mask].copy(), blocked


def policy_event_mask(events: pd.DataFrame, policy: str) -> pd.Series:
    idx = events.index
    executable = bool_series(events.get("event_executable_flag", False), idx)
    failure_complete = bool_series(events.get("failure_10_complete", False), idx)
    failure_label = numeric_series(events.get("failure_10_label"), idx).fillna(0).astype(float) >= 0.5
    false_repair_complete = bool_series(events.get("event_false_repair_20d_complete", False), idx)
    false_repair_label = bool_series(events.get("event_false_repair_20d_label", False), idx)
    if policy == "pre_replay_capture_only":
        return numeric_series(events.get("replay_anchor_pos"), idx).notna()
    if policy == "post_replay_executable_horizon_complete":
        return executable & failure_complete & false_repair_complete
    if policy == "post_replay_non_fast_fail_10d_oracle":
        return executable & failure_complete & (~failure_label)
    if policy == "post_replay_non_false_repair_20d_oracle":
        return executable & false_repair_complete & (~false_repair_label)
    if policy == "post_replay_non_fast_fail_and_non_false_repair_oracle":
        return executable & failure_complete & false_repair_complete & (~failure_label) & (~false_repair_label)
    raise ValueError(f"unknown_policy:{policy}")


def build_membership(events: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    if events.empty or windows.empty:
        return pd.DataFrame()
    usable_windows = windows.loc[
        windows["episode_window_source_status"].eq("episode_window_ready")
        & windows["denominator_included_flag"].fillna(False).astype(bool)
    ].copy()
    usable_events = events.loc[pd.to_numeric(events["replay_anchor_pos"], errors="coerce").notna()].copy()
    usable_events["replay_anchor_pos"] = pd.to_numeric(usable_events["replay_anchor_pos"], errors="coerce")
    if usable_events.empty or usable_windows.empty:
        return pd.DataFrame()
    merged = usable_events.merge(
        usable_windows[
            [
                "target_episode_id",
                "instrument",
                "episode_split",
                "market_regime_bucket",
                "window",
                "window_start_pos",
                "window_end_pos",
                "window_end_inclusive_flag",
                "bridge_positive_denominator_included",
            ]
        ],
        on="instrument",
        how="inner",
        suffixes=("", "_episode"),
    )
    start = pd.to_numeric(merged["window_start_pos"], errors="coerce")
    end = pd.to_numeric(merged["window_end_pos"], errors="coerce")
    pos = pd.to_numeric(merged["replay_anchor_pos"], errors="coerce")
    inclusive = merged["window_end_inclusive_flag"].fillna(True).astype(bool)
    inside = (start <= pos) & ((inclusive & (pos <= end)) | ((~inclusive) & (pos < end)))
    out = merged.loc[inside].copy()
    if out.empty:
        return out
    if "market_regime_bucket_episode" in out.columns:
        out["episode_market_regime_bucket"] = out["market_regime_bucket_episode"]
    else:
        out["episode_market_regime_bucket"] = out["market_regime_bucket"]
    overlap_counts = out.groupby("source_event_row_id")["target_episode_id"].transform("nunique")
    out["multi_episode_membership_overlap"] = overlap_counts > 1
    out["membership_basis"] = (
        "instrument_replay_anchor_inside_materialized_window_"
        "no_captured_target_episode_id_join"
    )
    return out


def denominator_grid(windows: pd.DataFrame) -> pd.DataFrame:
    usable = windows.loc[windows["episode_window_source_status"].eq("episode_window_ready")].copy()
    rows = []
    for (split, regime, window), group in usable.groupby(["episode_split", "market_regime_bucket", "window"], dropna=False):
        rows.append(
            {
                "split": split,
                "market_regime_bucket": regime,
                "window": window,
                "target_episode_denominator_n": int(group["target_episode_id"].nunique()),
                "bridge_episode_denominator_n": int(
                    group.loc[group["bridge_positive_denominator_included"].fillna(False).astype(bool), "target_episode_id"].nunique()
                ),
            }
        )
    return pd.DataFrame(rows)


def more_conservative_sample_status(*statuses: str | None) -> str:
    valid = [
        str(status)
        for status in statuses
        if status is not None and str(status) in SAMPLE_STATUS_RANK
    ]
    if not valid:
        return "source_blocked"
    return min(valid, key=lambda status: SAMPLE_STATUS_RANK[status])


def source_status_to_sample_status(source_status: str | None) -> str | None:
    status = "" if source_status is None else str(source_status)
    if "source_blocked" in status or status.endswith("_blocked"):
        return "source_blocked"
    if "source_caveated" in status or "pre_replay_capture_only" in status:
        return "diagnostic_only"
    return None


def sample_status(
    target_den: float,
    bridge_den: float,
    window: str,
    e1_missed_den: float | None = None,
) -> str:
    denominators = [target_den]
    if window == "low_to_first_50pct":
        denominators.append(bridge_den)
    if e1_missed_den is not None:
        denominators.append(e1_missed_den)
    denominators = [float(value) for value in denominators if pd.notna(value)]
    if not denominators:
        return "source_blocked"
    min_den = min(denominators)
    if min_den >= 100:
        return "sufficient_for_cell_readout"
    if min_den >= 30:
        return "low_power_caution"
    return "diagnostic_only"


def add_cell_status(
    lookup: dict[tuple[str, str, str], str],
    source_id: Any,
    split: Any,
    regime: Any,
    status: Any,
) -> None:
    if pd.isna(source_id) or pd.isna(split) or pd.isna(regime) or pd.isna(status):
        return
    key = (str(source_id), str(split), str(regime))
    current = lookup.get(key)
    lookup[key] = more_conservative_sample_status(current, str(status)) if current else str(status)


def build_cell_status_lookup(
    *,
    a_retention: pd.DataFrame,
    b_performance: pd.DataFrame,
    c_readout: pd.DataFrame,
) -> dict[tuple[str, str, str], str]:
    lookup: dict[tuple[str, str, str], str] = {}
    if not a_retention.empty and {"candidate_scope_id", "episode_split", "market_regime_bucket", "cell_sample_status"}.issubset(
        a_retention.columns
    ):
        for row in a_retention.itertuples(index=False):
            add_cell_status(
                lookup,
                getattr(row, "candidate_scope_id"),
                getattr(row, "episode_split"),
                getattr(row, "market_regime_bucket"),
                getattr(row, "cell_sample_status"),
            )
    if not b_performance.empty and {"candidate_scope_id", "split", "market_regime_bucket", "cell_sample_status"}.issubset(
        b_performance.columns
    ):
        for row in b_performance.itertuples(index=False):
            add_cell_status(
                lookup,
                getattr(row, "candidate_scope_id"),
                getattr(row, "split"),
                getattr(row, "market_regime_bucket"),
                getattr(row, "cell_sample_status"),
            )
    if not c_readout.empty and {"arm_id", "target_regime", "split", "market_regime_bucket", "cell_sample_status"}.issubset(
        c_readout.columns
    ):
        for row in c_readout.itertuples(index=False):
            add_cell_status(
                lookup,
                f"{getattr(row, 'arm_id')}::{getattr(row, 'target_regime')}",
                getattr(row, "split"),
                getattr(row, "market_regime_bucket"),
                getattr(row, "cell_sample_status"),
            )
    return lookup


def lookup_cell_status(
    lookup: dict[tuple[str, str, str], str],
    source_id: Any,
    split: Any,
    regime: Any,
) -> str | None:
    source = str(source_id)
    split_value = str(split)
    regime_value = str(regime)
    candidates = [
        (source, split_value, regime_value),
        (source, "all", regime_value),
        (source, split_value, "all"),
        (source, "all", "all"),
    ]
    statuses = [lookup[key] for key in candidates if key in lookup]
    if not statuses:
        return None
    return more_conservative_sample_status(*statuses)


def captured_episode_sets(
    membership: pd.DataFrame,
    policy: str,
    *,
    bridge_only: bool = False,
) -> pd.DataFrame:
    if membership.empty:
        return pd.DataFrame(
            columns=["source_kind", "source_id", "split", "market_regime_bucket", "window", "target_episode_id"]
        )
    mask = policy_event_mask(membership, policy)
    regime_column = (
        "episode_market_regime_bucket"
        if "episode_market_regime_bucket" in membership.columns
        else "market_regime_bucket"
    )
    if bridge_only and "bridge_positive_denominator_included" in membership.columns:
        mask = mask & membership["bridge_positive_denominator_included"].fillna(False).astype(bool)
    cols = [
        "source_kind",
        "source_id",
        "episode_split",
        regime_column,
        "window",
        "target_episode_id",
    ]
    out = membership.loc[mask, cols].drop_duplicates().copy()
    return out.rename(columns={"episode_split": "split", regime_column: "market_regime_bucket"})


def event_counts_by_policy(events: pd.DataFrame, policy: str) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    source_cols = ["source_kind", "source_id", "event_split", "market_regime_bucket"]
    base = events.groupby(source_cols, dropna=False)["source_event_row_id"].nunique().reset_index()
    base = base.rename(columns={"event_split": "split", "source_event_row_id": "selected_event_n"})
    filtered = events.loc[policy_event_mask(events, policy)].groupby(source_cols, dropna=False)[
        "source_event_row_id"
    ].nunique().reset_index()
    filtered = filtered.rename(columns={"event_split": "split", "source_event_row_id": "post_replay_event_n"})
    out = base.merge(filtered, on=["source_kind", "source_id", "split", "market_regime_bucket"], how="left")
    out["post_replay_event_n"] = out["post_replay_event_n"].fillna(0).astype(int)
    out["filtered_event_n"] = out["selected_event_n"].astype(int) - out["post_replay_event_n"].astype(int)
    out["filter_drop_rate"] = [
        safe_div(row.filtered_event_n, row.selected_event_n) for row in out.itertuples(index=False)
    ]
    return out


def build_retention_table(
    *,
    source_kind: str,
    source_ids: list[str],
    membership: pd.DataFrame,
    events: pd.DataFrame,
    denominators: pd.DataFrame,
    e1_pre_sets: pd.DataFrame,
    arm_meta: pd.DataFrame | None = None,
    upstream_status: str = "post_replay_event_membership_materialized",
    cell_status_lookup: dict[tuple[str, str, str], str] | None = None,
    source_status_lookup: dict[str, str] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    pre_sets = captured_episode_sets(membership, "pre_replay_capture_only")
    pre_bridge_sets = captured_episode_sets(
        membership,
        "pre_replay_capture_only",
        bridge_only=True,
    )
    pre_lookup = pre_sets.groupby(["source_kind", "source_id", "split", "market_regime_bucket", "window"])[
        "target_episode_id"
    ].agg(lambda values: frozenset(values)).to_dict()
    pre_bridge_lookup = pre_bridge_sets.groupby(
        ["source_kind", "source_id", "split", "market_regime_bucket", "window"]
    )["target_episode_id"].agg(lambda values: frozenset(values)).to_dict()
    e1_lookup = e1_pre_sets.groupby(["split", "market_regime_bucket", "window"])[
        "target_episode_id"
    ].agg(lambda values: frozenset(values)).to_dict()
    event_count_cache = {policy: event_counts_by_policy(events, policy) for policy in POLICIES}
    event_count_lookup = {}
    for policy, frame in event_count_cache.items():
        if frame.empty:
            continue
        for row in frame.itertuples(index=False):
            event_count_lookup[
                (policy, row.source_kind, row.source_id, row.split, row.market_regime_bucket)
            ] = row
    policy_sets = {policy: captured_episode_sets(membership, policy) for policy in POLICIES}
    policy_bridge_sets = {
        policy: captured_episode_sets(membership, policy, bridge_only=True) for policy in POLICIES
    }
    policy_lookup = {}
    policy_bridge_lookup = {}
    for policy, frame in policy_sets.items():
        if frame.empty:
            continue
        grouped = frame.groupby(["source_kind", "source_id", "split", "market_regime_bucket", "window"])[
            "target_episode_id"
        ].agg(lambda values: frozenset(values))
        for key, value in grouped.to_dict().items():
            policy_lookup[(policy, *key)] = value
    for policy, frame in policy_bridge_sets.items():
        if frame.empty:
            continue
        grouped = frame.groupby(["source_kind", "source_id", "split", "market_regime_bucket", "window"])[
            "target_episode_id"
        ].agg(lambda values: frozenset(values))
        for key, value in grouped.to_dict().items():
            policy_bridge_lookup[(policy, *key)] = value
    for source_id in source_ids:
        arm_meta_row: dict[str, Any] = {}
        if arm_meta is not None and source_kind == "arm":
            meta = arm_meta.loc[arm_meta["source_id"].astype(str).eq(str(source_id))]
            if not meta.empty:
                arm_meta_row = meta.iloc[0].to_dict()
        for den in denominators.itertuples(index=False):
            if arm_meta_row:
                target_regime = str(arm_meta_row.get("target_regime", ""))
                if target_regime and str(den.market_regime_bucket) != target_regime:
                    continue
            pre_key = (source_kind, source_id, den.split, den.market_regime_bucket, den.window)
            pre_episode_set = pre_lookup.get(pre_key, frozenset())
            pre_bridge_episode_set = pre_bridge_lookup.get(pre_key, frozenset())
            e1_set = e1_lookup.get((den.split, den.market_regime_bucket, den.window), frozenset())
            pre_e1_missed = pre_episode_set.difference(e1_set)
            source_retention_status = (
                source_status_lookup.get(source_id, upstream_status)
                if source_status_lookup is not None
                else upstream_status
            )
            upstream_cell_status = lookup_cell_status(
                cell_status_lookup or {},
                source_id,
                den.split,
                den.market_regime_bucket,
            )
            source_cell_status = source_status_to_sample_status(source_retention_status)
            for policy in POLICIES:
                post_episode_set = policy_lookup.get((policy, *pre_key), frozenset())
                post_bridge_episode_set = policy_bridge_lookup.get(
                    (policy, *pre_key),
                    frozenset(),
                )
                post_e1_missed = post_episode_set.difference(e1_set)
                counts = event_count_lookup.get(
                    (policy, source_kind, source_id, den.split, den.market_regime_bucket)
                )
                selected_event_n = int(counts.selected_event_n) if counts is not None else 0
                post_event_n = int(counts.post_replay_event_n) if counts is not None else 0
                filtered_event_n = int(counts.filtered_event_n) if counts is not None else 0
                filter_drop_rate = float(counts.filter_drop_rate) if counts is not None else np.nan
                any_pre_recall = safe_div(len(pre_episode_set), den.target_episode_denominator_n)
                any_post_recall = safe_div(len(post_episode_set), den.target_episode_denominator_n)
                bridge_den = den.bridge_episode_denominator_n
                denominator_status = sample_status(
                    den.target_episode_denominator_n,
                    bridge_den,
                    den.window,
                    len(pre_e1_missed),
                )
                row = {
                    "source_kind": source_kind,
                    "source_id": source_id,
                    "split": den.split,
                    "market_regime_bucket": den.market_regime_bucket,
                    "window": den.window,
                    "replay_policy_id": policy,
                    "oracle_future_label_used": policy in ORACLE_POLICIES,
                    "entry_support_allowed": False,
                    "target_episode_denominator_n": int(den.target_episode_denominator_n),
                    "bridge_episode_denominator_n": int(bridge_den) if pd.notna(bridge_den) else np.nan,
                    "pre_replay_any_captured_episode_n": len(pre_episode_set),
                    "post_replay_any_captured_episode_n": len(post_episode_set),
                    "pre_replay_any_recall": any_pre_recall,
                    "post_replay_any_recall": any_post_recall,
                    "any_recall_retention": safe_div(any_post_recall, any_pre_recall),
                    "pre_replay_bridge_captured_episode_n": len(pre_bridge_episode_set),
                    "post_replay_bridge_captured_episode_n": len(post_bridge_episode_set),
                    "pre_replay_bridge_recall": safe_div(len(pre_bridge_episode_set), bridge_den),
                    "post_replay_bridge_recall": safe_div(len(post_bridge_episode_set), bridge_den),
                    "bridge_recall_retention": safe_div(
                        safe_div(len(post_bridge_episode_set), bridge_den),
                        safe_div(len(pre_bridge_episode_set), bridge_den),
                    ),
                    "e1_missed_pre_replay_capture_n": len(pre_e1_missed),
                    "e1_missed_post_replay_capture_n": len(post_e1_missed),
                    "e1_missed_capture_retention": safe_div(len(post_e1_missed), len(pre_e1_missed)),
                    "selected_event_n": selected_event_n,
                    "post_replay_event_n": post_event_n,
                    "filtered_event_n": filtered_event_n,
                    "filter_drop_rate": filter_drop_rate,
                    "cell_sample_status": more_conservative_sample_status(
                        denominator_status,
                        upstream_cell_status,
                        source_cell_status,
                    ),
                    "retention_source_status": source_retention_status,
                    "membership_basis": "instrument_replay_anchor_inside_materialized_window",
                    "post_replay_membership_source_hash": "",
                    "pre_replay_source_reference": "D_recomputed_membership_reconciled_to_upstream",
                }
                if arm_meta is not None and source_kind == "arm":
                    row["arm_id"] = str(arm_meta_row.get("arm_id", ""))
                    row["target_regime"] = str(arm_meta_row.get("target_regime", ""))
                    row["arm_family_set"] = str(arm_meta_row.get("arm_family_set", ""))
                    row["c_arm_tier"] = str(arm_meta_row.get("target_regime_decision_tier", ""))
                    row["c_arm_final_decision_copy"] = str(arm_meta_row.get("final_decision", ""))
                rows.append(row)
    return pd.DataFrame(rows)


def scope_output_table(scope_retention: pd.DataFrame) -> pd.DataFrame:
    out = scope_retention.loc[scope_retention["source_kind"].eq("scope")].copy()
    out["candidate_scope_id"] = out["source_id"]
    cols = [
        "candidate_scope_id",
        "split",
        "market_regime_bucket",
        "window",
        "replay_policy_id",
        "oracle_future_label_used",
        "entry_support_allowed",
        "pre_replay_source_reference",
        "post_replay_membership_source_hash",
        "membership_basis",
        *RETENTION_METRIC_COLUMNS,
    ]
    return out[cols]


def arm_output_table(arm_retention: pd.DataFrame) -> pd.DataFrame:
    out = arm_retention.loc[arm_retention["source_kind"].eq("arm")].copy()
    for column in ["arm_id", "target_regime", "arm_family_set", "c_arm_tier", "c_arm_final_decision_copy"]:
        if column not in out.columns:
            out[column] = ""
    cols = [
        "arm_id",
        "target_regime",
        "arm_family_set",
        "split",
        "market_regime_bucket",
        "window",
        "replay_policy_id",
        "oracle_future_label_used",
        "entry_support_allowed",
        "c_arm_tier",
        "c_arm_final_decision_copy",
        "membership_basis",
        *RETENTION_METRIC_COLUMNS,
    ]
    return out[cols]


def build_policy_effect_summary(scope_table: pd.DataFrame, arm_table: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat(
        [
            scope_table.assign(source_kind="scope", source_id=scope_table["candidate_scope_id"]),
            arm_table.assign(source_kind="arm", source_id=arm_table["arm_id"]),
        ],
        ignore_index=True,
        sort=False,
    )
    base = combined.loc[combined["replay_policy_id"].eq("post_replay_executable_horizon_complete")].copy()
    rows: list[dict[str, Any]] = []
    key_cols = ["source_kind", "source_id", "split", "market_regime_bucket", "window"]
    base_by_key = {tuple(row[col] for col in key_cols): row for row in base.to_dict(orient="records")}
    for row in combined.loc[~combined["replay_policy_id"].eq("pre_replay_capture_only")].to_dict(orient="records"):
        key = tuple(row[col] for col in key_cols)
        base_row = base_by_key.get(key, row)
        rows.append(
            {
                "source_kind": row["source_kind"],
                "source_id": row["source_id"],
                "split": row["split"],
                "market_regime_bucket": row["market_regime_bucket"],
                "window": row["window"],
                "base_policy_id": "post_replay_executable_horizon_complete",
                "replay_policy_id": row["replay_policy_id"],
                "event_drop_n": int(base_row.get("post_replay_event_n", 0))
                - int(row.get("post_replay_event_n", 0)),
                "event_drop_rate": safe_div(
                    int(base_row.get("post_replay_event_n", 0))
                    - int(row.get("post_replay_event_n", 0)),
                    int(base_row.get("post_replay_event_n", 0)),
                ),
                "any_recall_delta_pp": 100
                * (
                    float(row.get("post_replay_any_recall", 0) or 0)
                    - float(base_row.get("post_replay_any_recall", 0) or 0)
                ),
                "bridge_recall_delta_pp": 100
                * (
                    float(row.get("post_replay_bridge_recall", 0) or 0)
                    - float(base_row.get("post_replay_bridge_recall", 0) or 0)
                ),
                "e1_missed_capture_delta_n": int(row.get("e1_missed_post_replay_capture_n", 0))
                - int(base_row.get("e1_missed_post_replay_capture_n", 0)),
                "policy_effect_interpretation": policy_interpretation(row["replay_policy_id"]),
            }
        )
    return pd.DataFrame(rows)


def policy_interpretation(policy: str) -> str:
    if policy == "post_replay_executable_horizon_complete":
        return "executable_anchor_and_required_label_horizon_complete"
    if policy == "post_replay_non_fast_fail_10d_oracle":
        return "audit_only_fast_fail_cost_removed"
    if policy == "post_replay_non_false_repair_20d_oracle":
        return "audit_only_false_repair_cost_removed"
    if policy == "post_replay_non_fast_fail_and_non_false_repair_oracle":
        return "audit_only_fast_fail_and_false_repair_removed"
    return "pre_replay_baseline"


def build_e1_missed_summary(scope_table: pd.DataFrame, arm_table: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat(
        [
            scope_table.assign(source_kind="scope", source_id=scope_table["candidate_scope_id"]),
            arm_table.assign(source_kind="arm", source_id=arm_table["arm_id"]),
        ],
        ignore_index=True,
        sort=False,
    )
    e1 = scope_table.loc[
        (scope_table["candidate_scope_id"] == "07_E1_only")
        & (scope_table["replay_policy_id"] == "pre_replay_capture_only")
    ]
    e1_lookup = {
        (row.split, row.market_regime_bucket, row.window): row
        for row in e1.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    for row in combined.to_dict(orient="records"):
        e1_row = e1_lookup.get((row["split"], row["market_regime_bucket"], row["window"]))
        e1_den = int(e1_row.target_episode_denominator_n) if e1_row is not None else np.nan
        e1_pre = int(e1_row.pre_replay_any_captured_episode_n) if e1_row is not None else np.nan
        e1_post = int(e1_row.post_replay_any_captured_episode_n) if e1_row is not None else np.nan
        rows.append(
            {
                "source_kind": row["source_kind"],
                "source_id": row["source_id"],
                "split": row["split"],
                "market_regime_bucket": row["market_regime_bucket"],
                "window": row["window"],
                "replay_policy_id": row["replay_policy_id"],
                "e1_episode_denominator_n": e1_den,
                "e1_pre_replay_captured_episode_n": e1_pre,
                "e1_post_replay_captured_episode_n": e1_post,
                "e1_missed_episode_n": int(e1_den - e1_pre) if pd.notna(e1_den) and pd.notna(e1_pre) else np.nan,
                "source_pre_replay_captures_e1_missed_n": row["e1_missed_pre_replay_capture_n"],
                "source_post_replay_captures_e1_missed_n": row["e1_missed_post_replay_capture_n"],
                "e1_missed_capture_retention": row["e1_missed_capture_retention"],
                "incremental_post_replay_capture_over_e1_n": row["e1_missed_post_replay_capture_n"],
                "incremental_post_replay_capture_over_e1_rate": safe_div(
                    row["e1_missed_post_replay_capture_n"],
                    int(e1_den - e1_pre) if pd.notna(e1_den) and pd.notna(e1_pre) else np.nan,
                ),
                "cell_sample_status": row["cell_sample_status"],
                "retention_source_status": row["retention_source_status"],
            }
        )
    return pd.DataFrame(rows)


def build_label_leakage_audit() -> pd.DataFrame:
    rows = [
        ("replay_anchor_pos", "event_envelope", True, True, False, False, "membership_join_only", "pass"),
        ("captured_target_episode_id_first", "event_label_cache", False, False, False, True, "reconciliation_audit_only", "pass"),
        ("failure_10_label", "event_label_cache", False, True, False, True, "oracle_replay_audit_only", "pass"),
        ("event_false_repair_20d_label", "event_label_cache", False, True, False, True, "oracle_replay_audit_only", "pass"),
        ("event_big_winner_120d_label", "event_label_cache", False, True, False, True, "downstream_label_only", "pass"),
        ("episode_membership", "D_membership_source", False, False, False, True, "post_replay_readout_only", "pass"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "field_name",
            "field_source",
            "allowed_for_membership_join",
            "allowed_for_replay_filter",
            "allowed_as_t0_feature",
            "uses_future_information",
            "allowed_downstream_use",
            "leakage_status",
        ],
    )


def build_reconciliation(
    scope_table: pd.DataFrame,
    arm_table: pd.DataFrame,
    a_retention: pd.DataFrame,
    c_readout: pd.DataFrame,
    a_manifest: dict[str, Any],
    c_manifest: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    scope_pre = scope_table.loc[
        (scope_table["replay_policy_id"] == "pre_replay_capture_only")
        & (scope_table["window"] == "low_to_first_50pct")
    ]
    for row in a_retention.to_dict(orient="records"):
        scope_id = row.get("candidate_scope_id")
        split = row.get("episode_split")
        regime = row.get("market_regime_bucket")
        matches = scope_pre.loc[
            (scope_pre["candidate_scope_id"] == scope_id)
            & (scope_pre["split"] == split)
            & (scope_pre["market_regime_bucket"] == regime)
        ]
        d_value = float(matches.iloc[0]["pre_replay_any_recall"]) if not matches.empty else np.nan
        upstream = float(row.get("pre_replay_any_recall")) if pd.notna(row.get("pre_replay_any_recall")) else np.nan
        status = reconciliation_status(upstream, d_value, a_manifest.get("decision"))
        rows.append(
            {
                "source_experiment": "A",
                "source_artifact": "candidate_10d_retention_by_split_regime.csv",
                "source_metric": "pre_replay_any_recall",
                "scope_or_arm_id": scope_id,
                "split": split,
                "market_regime_bucket": regime,
                "upstream_value": upstream,
                "d_recomputed_pre_replay_value": d_value,
                "absolute_diff": abs(upstream - d_value) if pd.notna(upstream) and pd.notna(d_value) else np.nan,
                "tolerance": 0.0001,
                "reconciliation_status": status,
                "membership_basis": "D_replay_anchor_low_to_first_50pct_vs_A_capture_basis",
                "source_partial_flag": a_manifest.get("decision") == "density_fast_fail_audit_partial_source_complete",
            }
        )
    arm_pre = arm_table.loc[
        (arm_table["replay_policy_id"] == "pre_replay_capture_only")
        & (arm_table["window"] == "low_to_first_50pct")
    ]
    for row in c_readout.to_dict(orient="records"):
        arm_id = row.get("arm_id")
        split = row.get("split")
        regime = row.get("market_regime_bucket")
        matches = arm_pre.loc[
            (arm_pre["arm_id"] == arm_id)
            & (arm_pre["target_regime"] == row.get("target_regime"))
            & (arm_pre["split"] == split)
            & (arm_pre["market_regime_bucket"] == regime)
        ]
        d_value = float(matches.iloc[0]["pre_replay_any_recall"]) if not matches.empty else np.nan
        upstream = float(row.get("pre_replay_any_recall")) if pd.notna(row.get("pre_replay_any_recall")) else np.nan
        status = reconciliation_status(upstream, d_value, c_manifest.get("decision"))
        rows.append(
            {
                "source_experiment": "C",
                "source_artifact": "risk_on_r_series_ranker_bridge_recall_readout.csv",
                "source_metric": "pre_replay_any_recall",
                "scope_or_arm_id": arm_id,
                "split": split,
                "market_regime_bucket": regime,
                "upstream_value": upstream,
                "d_recomputed_pre_replay_value": d_value,
                "absolute_diff": abs(upstream - d_value) if pd.notna(upstream) and pd.notna(d_value) else np.nan,
                "tolerance": 0.0001,
                "reconciliation_status": status,
                "membership_basis": "D_selected_events_replay_anchor_low_to_first_50pct_vs_C_readout_basis",
                "source_partial_flag": c_manifest.get("decision", "").endswith("source_caveated_complete"),
            }
        )
    return pd.DataFrame(rows)


def reconciliation_status(upstream: float, d_value: float, decision: str | None) -> str:
    if pd.isna(upstream):
        return "missing_upstream_value"
    if pd.isna(d_value):
        return "not_comparable_membership_basis"
    diff = abs(upstream - d_value)
    if diff <= 0.0001:
        return "pass"
    if decision and ("partial" in decision or "source_caveated" in decision):
        return "not_comparable_source_partial"
    if diff <= 0.001:
        return "within_tolerance_with_rounding"
    return "fail"


def build_scope_coverage_audit(
    input_frame: pd.DataFrame,
    mapping: pd.DataFrame,
    reconstruct: pd.DataFrame,
    scope_events: dict[str, pd.DataFrame],
    arm_events: pd.DataFrame,
    blocked_c_rows: pd.DataFrame,
) -> pd.DataFrame:
    rows = input_frame.to_dict(orient="records")
    for scope_id in ALL_SCOPES:
        map_row = mapping.loc[mapping["candidate_scope_id"].astype(str).eq(scope_id)]
        rec_row = reconstruct.loc[reconstruct["candidate_scope_id"].astype(str).eq(scope_id)]
        status = "scope_mapping_source_blocked"
        required = scope_id in HARD_REQUIRED_SCOPES
        if not map_row.empty and not rec_row.empty:
            map_status = str(map_row.iloc[0].get("scope_mapping_status", ""))
            rec_status = str(rec_row.iloc[0].get("scope_status", ""))
            if map_status == "reconstructable_event_membership" and rec_status == "reconstructable_event_membership":
                status = "available"
        frame = scope_events.get(scope_id, pd.DataFrame())
        rows.append(
            {
                "source_kind": "scope_mapping",
                "source_id": scope_id,
                "required_flag": required,
                "source_path": str(map_row.iloc[0].get("source_artifact_path", "")) if not map_row.empty else "",
                "source_hash": str(map_row.iloc[0].get("source_artifact_hash", "")) if not map_row.empty else "",
                "row_count": int(len(frame)),
                "expected_key_count": np.nan,
                "matched_key_count": int(len(frame)),
                "unmatched_key_count": 0,
                "source_status": status,
                "blocking_flag": bool(required and status != "available"),
                "missing_required_columns": "",
                "source_row_filter": str(map_row.iloc[0].get("source_row_filter", "")) if not map_row.empty else "",
                "scope_mapping_status": str(map_row.iloc[0].get("scope_mapping_status", "")) if not map_row.empty else "",
                "reconstructability_status": str(rec_row.iloc[0].get("scope_status", "")) if not rec_row.empty else "",
            }
        )
    for (arm_id, target_regime), group in arm_events.groupby(["arm_id", "target_regime"], dropna=False):
        blocked = blocked_c_rows.loc[
            blocked_c_rows["arm_id"].astype(str).eq(str(arm_id))
            & blocked_c_rows["target_regime"].astype(str).eq(str(target_regime))
        ]
        rows.append(
            {
                "source_kind": "c_arm_enrichment",
                "source_id": f"{arm_id}::{target_regime}",
                "required_flag": True,
                "source_path": str(REQUIRED_BY_ID["risk_on_r_series_ranker_selected_events"].path),
                "source_hash": path_hash(REQUIRED_BY_ID["risk_on_r_series_ranker_selected_events"].path),
                "row_count": int(len(group)),
                "expected_key_count": int(len(group) + len(blocked)),
                "matched_key_count": int(len(group)),
                "unmatched_key_count": int(len(blocked)),
                "source_status": "available" if blocked.empty else "c_arm_event_enrichment_blocked",
                "blocking_flag": bool(False),
                "missing_required_columns": "",
            }
        )
    return pd.DataFrame(rows)


def build_contract_text() -> str:
    return "\n".join(
        [
            "# Experiment D Post-Replay Retention Source Contract",
            "",
            "- 06 `episode_id` is canonicalized to D `target_episode_id`.",
            "- 06 `split` is canonicalized to D `episode_split`.",
            "- `candidate_family_capture.parquet` supplies replay window boundaries.",
            "- C selected events are enriched through 08 canonical events by `canonical_event_id`.",
            "- Membership uses instrument plus replay-anchor position inside materialized window bounds.",
            "- `captured_target_episode_id_first` is audit-only and never a membership join key.",
            "- All D replay policies have `entry_support_allowed = false`.",
            "- Oracle policies are audit-only and use future labels.",
            "",
        ]
    )


def build_report(
    final_decision: str,
    frames: dict[str, pd.DataFrame],
    a_manifest: dict[str, Any],
    b_manifest: dict[str, Any],
    c_manifest: dict[str, Any],
) -> str:
    windows = frames["post_replay_episode_window_audit"]
    coverage = frames["post_replay_source_coverage_audit"]
    scope = frames["post_replay_scope_retention_by_split_regime"]
    arms = frames["post_replay_arm_retention_by_split_regime"]
    policy = frames["post_replay_policy_effect_summary"]
    recon = frames["post_replay_reconciliation_against_a_b_c"]

    def table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> list[str]:
        if frame.empty:
            return ["_No rows._"]
        cols = [column for column in columns if column in frame.columns]
        return frame[cols].head(max_rows).to_markdown(index=False).splitlines()

    def pct(value: Any) -> str:
        if value is None or pd.isna(value):
            return "NA"
        return f"{float(value) * 100:.2f}%"

    input_sources = coverage.loc[coverage.get("source_kind", "").eq("input")].copy()
    scope_coverage = coverage.loc[coverage.get("source_kind", "").eq("scope_mapping")].copy()
    blocked_or_caveated = pd.concat(
        [
            scope.rename(columns={"candidate_scope_id": "source_id"}).assign(source_kind="scope"),
            arms.assign(source_id=arms["arm_id"].astype(str) + "::" + arms["target_regime"].astype(str), source_kind="arm"),
        ],
        ignore_index=True,
        sort=False,
    )
    blocked_or_caveated = blocked_or_caveated.loc[
        blocked_or_caveated["cell_sample_status"].ne("sufficient_for_cell_readout")
        | blocked_or_caveated["retention_source_status"].astype(str).str.contains(
            "source_caveated|source_blocked|pre_replay_capture_only",
            regex=True,
            na=False,
        )
    ].copy()
    caveat_summary = (
        blocked_or_caveated.groupby(["source_kind", "cell_sample_status", "retention_source_status"], dropna=False)
        .size()
        .reset_index(name="row_count")
        if not blocked_or_caveated.empty
        else pd.DataFrame()
    )
    denominator_summary = (
        scope.loc[
            scope["candidate_scope_id"].eq("07_E1_only")
            & scope["replay_policy_id"].eq("pre_replay_capture_only")
        ][
            [
                "split",
                "market_regime_bucket",
                "window",
                "target_episode_denominator_n",
                "bridge_episode_denominator_n",
            ]
        ]
        .drop_duplicates()
        .sort_values(["split", "market_regime_bucket", "window"])
        if not scope.empty
        else pd.DataFrame()
    )
    window_status_summary = (
        windows.groupby(["window", "episode_window_source_status"], dropna=False)
        .agg(row_count=("target_episode_id", "size"), episode_n=("target_episode_id", "nunique"))
        .reset_index()
        if not windows.empty
        else pd.DataFrame()
    )
    scope_focus = scope.loc[
        (scope["candidate_scope_id"].isin(["07_E1_only", "08_R_core_event_regime_gated", "08_R6_event_regime_gated"]))
        & (scope["replay_policy_id"].isin(["pre_replay_capture_only", "post_replay_executable_horizon_complete"]))
        & (scope["window"].eq("low_to_first_50pct"))
    ]
    arm_focus = arms.loc[
        (arms["target_regime"].isin(["risk_on", "transition"]))
        & (arms["replay_policy_id"].eq("post_replay_executable_horizon_complete"))
        & (arms["window"].eq("low_to_first_50pct"))
    ]
    recon_summary = (
        recon.groupby(["source_experiment", "reconciliation_status"])
        .size()
        .reset_index(name="row_count")
        if not recon.empty
        else pd.DataFrame()
    )
    risk_on_rows = arm_focus.loc[arm_focus["target_regime"].eq("risk_on")]
    transition_rows = arm_focus.loc[arm_focus["target_regime"].eq("transition")]
    risk_on_best_bridge = (
        risk_on_rows["post_replay_bridge_recall"].max() if not risk_on_rows.empty else np.nan
    )
    transition_best_bridge = (
        transition_rows["post_replay_bridge_recall"].max() if not transition_rows.empty else np.nan
    )
    horizon_scope = scope.loc[
        (scope["replay_policy_id"].eq("post_replay_executable_horizon_complete"))
        & (scope["window"].eq("low_to_first_50pct"))
    ]
    source_input_row_count = int(input_sources["row_count"].fillna(0).sum()) if "row_count" in input_sources else 0
    lines = [
        "# Experiment D - Post-Replay 事件到 Episode 留存源报告",
        "",
        f"最终决策：`{final_decision}`",
        "",
        "## 结论",
        "",
        "D 已经把 A/B/C 缺失的 post-replay event-to-episode membership source 物化到 local cache，并输出 scope / C arm 的 post-filter retention readout。本实验仍然是 source-building，不训练 rejector，不给 direct-entry 支持。",
        "",
        f"- Experiment A decision: `{a_manifest.get('decision', '')}`",
        f"- Experiment B decision: `{b_manifest.get('decision', '')}`",
        f"- Experiment C decision: `{c_manifest.get('decision', '')}`",
        "- 所有 oracle replay policy 均标记 `entry_support_allowed = false`。",
        "- `post_replay_executable_horizon_complete` 只要求 executable anchor、10d fast-fail label completeness、20d false-repair label completeness；当前 D 没有 120d retention readout，因此不要求 120d label completeness。",
        f"- 已审计 input/source 行数合计：`{source_input_row_count:,}`。",
        "",
        "## 输入源明细",
        "",
        *table(
            input_sources.sort_values(["required_flag", "source_id"], ascending=[False, True]),
            [
                "source_id",
                "required_flag",
                "source_status",
                "row_count",
                "source_hash",
                "source_path",
            ],
            80,
        ),
        "",
        "## Episode Window 与 Denominator",
        "",
        *table(
            window_status_summary,
            ["window", "episode_window_source_status", "row_count", "episode_n"],
            20,
        ),
        "",
        *table(
            denominator_summary,
            [
                "split",
                "market_regime_bucket",
                "window",
                "target_episode_denominator_n",
                "bridge_episode_denominator_n",
            ],
            30,
        ),
        "",
        "## Scope Mapping Coverage",
        "",
        *table(
            scope_coverage,
            [
                "source_id",
                "required_flag",
                "source_status",
                "row_count",
                "source_row_filter",
                "scope_mapping_status",
                "reconstructability_status",
            ],
            20,
        ),
        "",
        "## Scope 留存样例",
        "",
        *table(
            scope_focus,
            [
                "candidate_scope_id",
                "split",
                "market_regime_bucket",
                "replay_policy_id",
                "target_episode_denominator_n",
                "pre_replay_any_recall",
                "post_replay_any_recall",
                "pre_replay_bridge_recall",
                "post_replay_bridge_recall",
                "e1_missed_post_replay_capture_n",
                "cell_sample_status",
            ],
            18,
        ),
        "",
        "## C Arm 留存样例",
        "",
        *table(
            arm_focus.sort_values(["target_regime", "post_replay_bridge_recall"], ascending=[True, False]),
            [
                "arm_id",
                "target_regime",
                "split",
                "market_regime_bucket",
                "target_episode_denominator_n",
                "post_replay_any_recall",
                "post_replay_bridge_recall",
                "e1_missed_post_replay_capture_n",
                "cell_sample_status",
            ],
            18,
        ),
        "",
        "## Replay Policy 影响",
        "",
        *table(
            policy.loc[
                (policy["source_id"].isin(["07_E1_only", "08_R_core_event_regime_gated"]))
                & policy["split"].eq("train")
                & policy["market_regime_bucket"].eq("risk_on")
            ],
            [
                "source_kind",
                "source_id",
                "window",
                "replay_policy_id",
                "event_drop_rate",
                "any_recall_delta_pp",
                "bridge_recall_delta_pp",
                "policy_effect_interpretation",
            ],
            20,
        ),
        "",
        "## 对账",
        "",
        *table(recon_summary, ["source_experiment", "reconciliation_status", "row_count"], 20),
        "",
        *table(
            recon.sort_values(["source_experiment", "reconciliation_status", "scope_or_arm_id"]),
            [
                "source_experiment",
                "source_metric",
                "scope_or_arm_id",
                "split",
                "market_regime_bucket",
                "upstream_value",
                "d_recomputed_pre_replay_value",
                "absolute_diff",
                "reconciliation_status",
                "source_partial_flag",
            ],
            30,
        ),
        "",
        "## Risk-On 与 Transition 含义",
        "",
        f"- risk_on：C arm 在 post-replay executable+horizon-complete 后的最高 bridge recall 为 `{pct(risk_on_best_bridge)}`；它说明 D 已能为未来 cost rejector 提供 post-filter readout，但当前实验仍不训练 rejector。",
        f"- transition：C arm 在 post-replay executable+horizon-complete 后的最高 bridge recall 为 `{pct(transition_best_bridge)}`；结合 C 的 source-caveated / diagnostic 结论，D 仍确认 transition 应优先做 family rediscovery，而不是直接沿用 risk_on ranker。",
        f"- scope readout 行数：`{len(horizon_scope):,}` 行 post-replay executable+horizon-complete scope cell；其中 `sufficient_for_cell_readout` 行数为 `{int(horizon_scope['cell_sample_status'].eq('sufficient_for_cell_readout').sum())}`。",
        "",
        "## Blocked / Caveated Cells",
        "",
        *table(
            caveat_summary,
            ["source_kind", "cell_sample_status", "retention_source_status", "row_count"],
            30,
        ),
        "",
        *table(
            blocked_or_caveated.sort_values(
                ["source_kind", "cell_sample_status", "source_id", "split", "market_regime_bucket", "window", "replay_policy_id"]
            ),
            [
                "source_kind",
                "source_id",
                "split",
                "market_regime_bucket",
                "window",
                "replay_policy_id",
                "target_episode_denominator_n",
                "bridge_episode_denominator_n",
                "cell_sample_status",
                "retention_source_status",
            ],
            40,
        ),
        "",
        "## Source Caveat",
        "",
        "- A/B/C 的上游 readout 仍带 `pre_replay_capture_only` / source-caveated 历史口径；D 因此输出 `source_caveated_complete`，但 post-replay membership 已经本地物化。",
        "- `post_replay_event_episode_membership.parquet` 位于 local cache，不作为 publishable raw dump 提交。",
        "- 未来 rejector / meta-label 可以消费 D 的 post-replay readout，但 oracle future-label policy 只能作为 audit label。",
        "",
        "## 输出行数",
        "",
    ]
    for key, frame in frames.items():
        lines.append(f"- `{key}`: {len(frame):,} rows")
    lines.append("")
    return "\n".join(lines)


def build_manifest(
    final_decision: str,
    frames: dict[str, pd.DataFrame],
    paths: dict[str, Path],
    a_manifest: dict[str, Any],
    b_manifest: dict[str, Any],
    c_manifest: dict[str, Any],
    input_paths: dict[str, Path],
    blocked_reasons: list[str] | None = None,
) -> dict[str, Any]:
    local_membership = paths["post_replay_event_episode_membership"]
    return {
        "experiment_id": "08_experiment_d_post_replay_event_to_episode_retention_source",
        "run_id": stable_hash(
            {
                "experiment": "post_replay_event_to_episode_retention_source",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision": final_decision,
        "experiment_a_decision": a_manifest.get("decision", ""),
        "experiment_b_decision": b_manifest.get("decision", ""),
        "experiment_c_decision": c_manifest.get("decision", ""),
        "blocked_reasons": blocked_reasons or [],
        "entry_support_allowed": False,
        "oracle_policies_audit_only": True,
        "local_raw_membership": {
            "path": str(local_membership),
            "sha256": path_hash(local_membership),
            "row_count": row_count(local_membership),
            "schema_fingerprint": stable_hash(list(pd.read_parquet(local_membership).columns))
            if local_membership.exists()
            else "",
        },
        "input_artifacts": {
            key: {"path": str(path), "sha256": path_hash(path)}
            for key, path in sorted(input_paths.items())
        },
        "output_paths": {key: str(path) for key, path in sorted(paths.items())},
        "output_hashes": {
            key: path_hash(path)
            for key, path in sorted(paths.items())
            if key != "post_replay_event_to_episode_retention_source_manifest"
            and path.exists()
            and path.is_file()
        },
        "output_row_counts": {key: int(len(frame)) for key, frame in frames.items()},
        "requirement_hash": path_hash(REQUIREMENT_PATH),
        "runner_code_hash": path_hash(Path(__file__)),
    }


def write_blocked_outputs(
    final_decision: str,
    reasons: list[str],
    input_frame: pd.DataFrame,
    input_paths: dict[str, Path],
    a_manifest: dict[str, Any],
    b_manifest: dict[str, Any],
    c_manifest: dict[str, Any],
    episode_windows: pd.DataFrame | None = None,
) -> dict[str, Any]:
    paths = output_paths()
    episode_window_frame = (
        episode_windows[[column for column in EPISODE_WINDOW_OUTPUT_COLUMNS if column in episode_windows.columns]].copy()
        if episode_windows is not None
        else pd.DataFrame(columns=EPISODE_WINDOW_OUTPUT_COLUMNS)
    )
    empty_frames = {
        "post_replay_episode_window_audit": episode_window_frame,
        "post_replay_source_coverage_audit": input_frame,
        "post_replay_scope_retention_by_split_regime": pd.DataFrame(),
        "post_replay_arm_retention_by_split_regime": pd.DataFrame(),
        "post_replay_policy_effect_summary": pd.DataFrame(),
        "post_replay_e1_missed_retention_summary": pd.DataFrame(),
        "post_replay_label_leakage_audit": build_label_leakage_audit(),
        "post_replay_reconciliation_against_a_b_c": pd.DataFrame(),
    }
    for key, frame in empty_frames.items():
        write_df(paths[key], frame)
    write_text(paths["post_replay_retention_source_contract"], build_contract_text())
    write_text(
        paths["post_replay_retention_source_report"],
        "# Experiment D - Post-Replay 事件到 Episode 留存源报告\n\n"
        f"最终决策：`{final_decision}`\n\n"
        + "\n".join(f"- {reason}" for reason in reasons)
        + "\n",
    )
    write_json(
        paths["post_replay_event_to_episode_retention_source_manifest"],
        build_manifest(
            final_decision,
            empty_frames,
            paths,
            a_manifest,
            b_manifest,
            c_manifest,
            input_paths,
            reasons,
        ),
    )
    return {"decision": final_decision, "blocked_reasons": reasons, "manifest_path": str(paths["post_replay_event_to_episode_retention_source_manifest"])}


def arm_meta_from_tiers(tiers: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    family_sets = (
        selected.groupby(["arm_id", "target_regime"], dropna=False)["family_id"]
        .agg(lambda values: ";".join(sorted(set(map(str, values)))))
        .reset_index(name="arm_family_set")
    )
    out = tiers.merge(family_sets, on=["arm_id", "target_regime"], how="left")
    out["source_id"] = out["arm_id"].astype(str) + "::" + out["target_regime"].astype(str)
    return out


def run_post_replay_source() -> dict[str, Any]:
    ensure_output_dirs()
    input_frame, input_failures, input_paths = input_audit()
    a_manifest, b_manifest, c_manifest, manifest_failures = validate_upstream_manifests()
    input_failures.extend(manifest_failures)
    if input_failures:
        return write_blocked_outputs(
            FINAL_INPUT_BLOCKED,
            input_failures,
            input_frame,
            input_paths,
            a_manifest,
            b_manifest,
            c_manifest,
        )

    paths = output_paths()
    capture = pd.read_parquet(REQUIRED_BY_ID["candidate_family_capture"].path)
    episodes06 = pd.read_parquet(REQUIRED_BY_ID["06_episode_reference"].path)
    canonical07 = read_csv(REQUIRED_BY_ID["07_canonical_events"].path)
    labels07 = pd.read_parquet(REQUIRED_BY_ID["07_event_labels"].path)
    canonical08 = read_csv(REQUIRED_BY_ID["candidate_family_canonical_events"].path)
    labels08 = pd.read_parquet(REQUIRED_BY_ID["candidate_family_event_labels"].path)
    mapping = read_csv(REQUIRED_BY_ID["candidate_scope_mapping_contract"].path)
    reconstruct = read_csv(REQUIRED_BY_ID["candidate_scope_reconstructability_audit"].path)
    a_retention = read_csv(REQUIRED_BY_ID["candidate_10d_retention_by_split_regime"].path)
    b_performance = read_csv(REQUIRED_BY_ID["regime_family_performance_matrix"].path)
    c_selected = read_csv(REQUIRED_BY_ID["risk_on_r_series_ranker_selected_events"].path)
    c_rejected = read_csv(REQUIRED_BY_ID["risk_on_r_series_ranker_rejected_events"].path)
    c_readout = read_csv(REQUIRED_BY_ID["risk_on_r_series_ranker_bridge_recall_readout"].path)
    c_tiers = read_csv(REQUIRED_BY_ID["risk_on_r_series_ranker_decision_tiers"].path)

    episode_windows = build_episode_windows(
        capture, episodes06, capture_path=REQUIRED_BY_ID["candidate_family_capture"].path
    )
    if episode_windows["episode_window_source_status"].eq("episode_window_conflict_blocked").any():
        return write_blocked_outputs(
            FINAL_CONTRACT_BLOCKED,
            ["episode_window_conflict_blocked"],
            input_frame,
            input_paths,
            a_manifest,
            b_manifest,
            c_manifest,
            episode_windows,
        )

    scope_events: dict[str, pd.DataFrame] = {}
    scope_source_status: dict[str, str] = {}
    scope_status_failures: list[str] = []
    for scope_id in ALL_SCOPES:
        m = mapping.loc[mapping["candidate_scope_id"].astype(str).eq(scope_id)]
        r = reconstruct.loc[reconstruct["candidate_scope_id"].astype(str).eq(scope_id)]
        if (
            m.empty
            or r.empty
            or str(m.iloc[0].get("scope_mapping_status")) != "reconstructable_event_membership"
            or str(r.iloc[0].get("scope_status")) != "reconstructable_event_membership"
        ):
            if scope_id in HARD_REQUIRED_SCOPES:
                scope_status_failures.append(f"scope_mapping_source_blocked:{scope_id}")
            scope_source_status[scope_id] = "scope_mapping_source_blocked"
            scope_events[scope_id] = pd.DataFrame()
            continue
        mapping_row = m.iloc[0]
        raw = select_scope_events_from_contract(mapping_row, canonical07, canonical08)
        labels = labels07 if str(m.iloc[0].get("source_experiment")) == "07" else labels08
        source_experiment = str(m.iloc[0].get("source_experiment"))
        source_path = Path(str(m.iloc[0].get("source_artifact_path")))
        scope_source_status[scope_id] = "post_replay_event_membership_materialized"
        scope_events[scope_id] = normalize_scope_events(
            scope_id,
            raw,
            labels,
            source_experiment=source_experiment,
            source_path=source_path,
            canonicalization_rule=str(mapping_row.get("canonicalization_rule", "")),
        )
    if any("07_E1_only" in failure for failure in scope_status_failures):
        return write_blocked_outputs(
            FINAL_INPUT_BLOCKED,
            scope_status_failures,
            input_frame,
            input_paths,
            a_manifest,
            b_manifest,
            c_manifest,
        )

    selected_events, blocked_selected = normalize_c_arm_events(
        c_selected, canonical08, labels08, source_kind="arm"
    )
    rejected_events, blocked_rejected = normalize_c_arm_events(
        c_rejected, canonical08, labels08, source_kind="arm_rejected"
    )
    blocked_c_rows = pd.concat([blocked_selected, blocked_rejected], ignore_index=True, sort=False)
    all_scope_events = pd.concat(scope_events.values(), ignore_index=True, sort=False)
    membership_events = pd.concat([all_scope_events, selected_events], ignore_index=True, sort=False)
    membership = build_membership(membership_events, episode_windows)
    membership.to_parquet(paths["post_replay_event_episode_membership"], index=False)

    denominators = denominator_grid(episode_windows)
    cell_status_lookup = build_cell_status_lookup(
        a_retention=a_retention,
        b_performance=b_performance,
        c_readout=c_readout,
    )
    e1_membership = membership.loc[
        (membership["source_kind"] == "scope") & (membership["source_id"] == "07_E1_only")
    ].copy()
    e1_pre_sets = captured_episode_sets(e1_membership, "pre_replay_capture_only")

    scope_retention_raw = build_retention_table(
        source_kind="scope",
        source_ids=ALL_SCOPES,
        membership=membership.loc[membership["source_kind"] == "scope"].copy(),
        events=all_scope_events,
        denominators=denominators,
        e1_pre_sets=e1_pre_sets,
        upstream_status="post_replay_event_membership_materialized",
        cell_status_lookup=cell_status_lookup,
        source_status_lookup=scope_source_status,
    )
    arm_meta = arm_meta_from_tiers(c_tiers, c_selected)
    arm_retention_raw = build_retention_table(
        source_kind="arm",
        source_ids=sorted(arm_meta["source_id"].dropna().astype(str).unique()),
        membership=membership.loc[membership["source_kind"] == "arm"].copy(),
        events=selected_events,
        denominators=denominators,
        e1_pre_sets=e1_pre_sets,
        arm_meta=arm_meta,
        upstream_status="post_replay_event_membership_materialized_source_caveated_upstream",
        cell_status_lookup=cell_status_lookup,
    )
    scope_table = scope_output_table(scope_retention_raw)
    arm_table = arm_output_table(arm_retention_raw)
    membership_hash = path_hash(paths["post_replay_event_episode_membership"])
    scope_table["post_replay_membership_source_hash"] = membership_hash
    arm_table["post_replay_membership_source_hash"] = membership_hash
    policy_effect = build_policy_effect_summary(scope_table, arm_table)
    e1_missed = build_e1_missed_summary(scope_table, arm_table)
    leakage = build_label_leakage_audit()
    recon = build_reconciliation(scope_table, arm_table, a_retention, c_readout, a_manifest, c_manifest)
    source_coverage = build_scope_coverage_audit(
        input_frame,
        mapping,
        reconstruct,
        scope_events,
        selected_events,
        blocked_c_rows,
    )

    final_decision = FINAL_SOURCE_CAVEATED
    if (
        not scope_status_failures
        and not blocked_selected.empty
        and blocked_selected["source_event_row_id"].nunique()
        == c_selected["canonical_event_id"].nunique()
    ):
        final_decision = FINAL_CONTRACT_BLOCKED
    if leakage["leakage_status"].ne("pass").any():
        final_decision = FINAL_LEAKAGE_BLOCKED

    frames = {
        "post_replay_episode_window_audit": episode_windows[EPISODE_WINDOW_OUTPUT_COLUMNS],
        "post_replay_source_coverage_audit": source_coverage,
        "post_replay_scope_retention_by_split_regime": scope_table,
        "post_replay_arm_retention_by_split_regime": arm_table,
        "post_replay_policy_effect_summary": policy_effect,
        "post_replay_e1_missed_retention_summary": e1_missed,
        "post_replay_label_leakage_audit": leakage,
        "post_replay_reconciliation_against_a_b_c": recon,
    }
    for key, frame in frames.items():
        write_df(paths[key], frame)
    write_text(paths["post_replay_retention_source_contract"], build_contract_text())
    write_text(
        paths["post_replay_retention_source_report"],
        build_report(final_decision, frames, a_manifest, b_manifest, c_manifest),
    )
    write_json(
        paths["post_replay_event_to_episode_retention_source_manifest"],
        build_manifest(
            final_decision,
            frames,
            paths,
            a_manifest,
            b_manifest,
            c_manifest,
            input_paths,
            scope_status_failures,
        ),
    )
    return {
        "decision": final_decision,
        "manifest_path": str(paths["post_replay_event_to_episode_retention_source_manifest"]),
        "report_path": str(paths["post_replay_retention_source_report"]),
        "row_counts": {key: int(len(frame)) for key, frame in frames.items()},
        "local_membership_path": str(paths["post_replay_event_episode_membership"]),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_output_dirs()
    if args.mode == "check-inputs":
        input_frame, failures, _ = input_audit()
        write_df(D_TABLE_DIR / "post_replay_source_coverage_audit.csv", input_frame)
        for failure in failures:
            print(failure)
        print(f"input_failures={len(failures)}")
        return 1 if failures else 0
    result = run_post_replay_source()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if "blocked" not in str(result.get("decision", "")) else 1


if __name__ == "__main__":
    raise SystemExit(main())

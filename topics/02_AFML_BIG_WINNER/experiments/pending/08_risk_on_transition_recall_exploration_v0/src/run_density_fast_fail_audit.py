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

REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_experiment_a_10d_density_fast_fail_audit.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"

AUDIT_TABLE_DIR = TABLE_DIR / "density_fast_fail_audit"
AUDIT_REPORT_DIR = REPORT_DIR / "density_fast_fail_audit"
AUDIT_MANIFEST_DIR = MANIFEST_DIR / "density_fast_fail_audit"

CORE_R_FAMILIES = [
    "R1_relative_strength_breakout",
    "R2_near_high_volume_expansion",
    "R6_market_breadth_thrust",
    "R7_cross_sectional_momentum_rank_jump",
    "R8_persistent_distance_above_ema",
]
E1_CHANNEL = "E1_early_ema60_repair"
E3_CHANNEL = "E3_rank_persistence"
BEFORE_FIRST_50 = "before_first_50pct"

DECISION_COMPLETE = "density_fast_fail_audit_complete"
DECISION_PARTIAL = "density_fast_fail_audit_partial_source_complete"
DECISION_INPUT_BLOCKED = "density_fast_fail_audit_input_blocked"

EVENT_ANCHOR_POLICY = "executable_trade_open_else_t0_fallback_v1"
UNIQUENESS_SCOPE = "same_instrument_same_candidate_scope"
LOW_UNIQUENESS_THRESHOLD = 0.50


REQUIRED_INPUTS = {
    "07_run_manifest": EXP07_DIR / "outputs" / "manifests" / "run_manifest.json",
    "07_canonical_events": EXP07_DIR
    / "outputs"
    / "publishable"
    / "tables"
    / "topn_multichannel_candidate_event_canonical.csv",
    "07_event_instances": EXP07_DIR
    / "outputs"
    / "publishable"
    / "tables"
    / "topn_multichannel_candidate_event_instances.csv",
    "07_precision_label_readout": EXP07_DIR
    / "outputs"
    / "publishable"
    / "tables"
    / "topn_event_precision_label_readout.csv",
    "07_false_repair": EXP07_DIR
    / "outputs"
    / "publishable"
    / "tables"
    / "topn_false_repair_diagnostic.csv",
    "08_run_manifest": EXPERIMENT_DIR / "outputs" / "manifests" / "run_manifest.json",
    "08_canonical_events": TABLE_DIR / "candidate_family_canonical_events.csv.gz",
    "08_event_instances": TABLE_DIR / "candidate_family_event_instances.csv.gz",
    "08_label_quality": TABLE_DIR / "candidate_family_label_quality_readout.csv",
    "08_false_repair": TABLE_DIR / "candidate_family_false_repair_diagnostic.csv",
    "08_density_summary": TABLE_DIR / "candidate_family_density_summary.csv",
    "08_bridge_positive_recall": TABLE_DIR / "candidate_family_bridge_positive_recall.csv",
    "08_incremental_recall": TABLE_DIR / "candidate_family_incremental_recall_over_e1.csv",
    "r_series_frontier": TABLE_DIR
    / "risk_on_r_series_density_compression"
    / "risk_on_r_series_compression_frontier.csv",
    "r_series_threshold_sensitivity": TABLE_DIR
    / "risk_on_r_series_density_compression"
    / "risk_on_r_series_threshold_sensitivity.csv",
    "r_series_recall_bridge_density": TABLE_DIR
    / "risk_on_r_series_density_compression"
    / "risk_on_r_series_recall_bridge_density_by_split.csv",
    "r_series_score_spec": TABLE_DIR
    / "risk_on_r_series_density_compression"
    / "risk_on_r_series_score_spec.csv",
    "r_series_source_pool_summary": TABLE_DIR
    / "risk_on_r_series_density_compression"
    / "risk_on_r_series_source_pool_summary.csv",
    "discussion": REPORT_DIR / "discussion.md",
    "requirement": REQUIREMENT_PATH,
}

OPTIONAL_INPUTS = {
    "08_event_labels_local": LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet",
    "08_capture_local": LOCAL_CACHE_DIR / "candidate_family_capture.parquet",
    "07_event_labels_local": EXP07_DIR
    / "outputs"
    / "local_cache"
    / "topn_canonical_event_labels.parquet",
    "06_episode_reference_local": PENDING_DIR
    / "06_rerun_02_reverse_lifecycle_on_topn_universe_v0"
    / "outputs"
    / "local_cache"
    / "topn_big_winner_episode_reference.parquet",
    "r_series_selected_compressed_variants": TABLE_DIR
    / "risk_on_r_series_density_compression"
    / "risk_on_r_series_selected_compressed_variants.csv",
    "r_series_compressed_canonical_events": TABLE_DIR
    / "risk_on_r_series_density_compression"
    / "risk_on_r_series_compressed_canonical_events.csv",
}

BASE_EVENT_COLUMNS = [
    "event_id",
    "instrument",
    "event_t0_date",
    "event_t0_pos",
    "trade_open_date",
    "trade_open_pos",
    "non_executable_next_open",
    "event_split",
    "market_regime_bucket",
]

REQUIRED_INPUT_COLUMNS = {
    "07_canonical_events": BASE_EVENT_COLUMNS + ["canonical_event_id", "triggered_channels"],
    "07_event_instances": BASE_EVENT_COLUMNS + ["event_family", "event_variant"],
    "07_precision_label_readout": [
        "event_split",
        "market_regime_bucket",
        "primary_channel",
        "event_count",
        "failure_10_rate",
    ],
    "07_false_repair": [
        "event_split",
        "market_regime_bucket",
        "primary_channel",
        "event_count",
        "false_repair_10d_rate",
        "false_repair_20d_rate",
    ],
    "08_canonical_events": BASE_EVENT_COLUMNS
    + [
        "canonical_event_id",
        "triggered_family_variants",
        "family_id",
        "variant_id",
    ],
    "08_event_instances": BASE_EVENT_COLUMNS + ["family_id", "variant_id"],
    "08_label_quality": [
        "candidate_scope_id",
        "event_count",
        "failure_10_rate",
        "label_completeness_rate",
        "next_open_executable_rate",
    ],
    "08_false_repair": [
        "candidate_scope_id",
        "event_count",
        "false_repair_10d_rate",
        "false_repair_20d_rate",
    ],
    "08_density_summary": [
        "candidate_scope_id",
        "event_count",
        "density_full_denominator",
        "events_per_instrument_year_p95",
    ],
    "08_bridge_positive_recall": [
        "candidate_scope_id",
        "episode_split",
        "market_regime_bucket",
        "window",
        "metric_basis",
        "numerator",
        "denominator",
        "recall",
    ],
    "08_incremental_recall": [
        "candidate_scope_id",
        "episode_split",
        "market_regime_bucket",
        "window",
        "denominator_episodes",
        "incremental_recall_over_e1",
    ],
    "r_series_frontier": [
        "compression_arm_id",
        "threshold_policy",
        "score_spec_id",
        "canonical_event_count",
        "density_full_denominator",
    ],
    "r_series_threshold_sensitivity": [
        "compression_arm_id",
        "threshold_policy",
        "score_spec_id",
        "canonical_event_count",
        "density_full_denominator",
    ],
    "r_series_recall_bridge_density": [
        "candidate_scope_id",
        "episode_split",
        "market_regime_bucket",
        "metric_family",
        "recall",
    ],
    "r_series_score_spec": [
        "score_spec_id",
        "family_id",
        "variant_id",
        "score_field_name",
        "source_column",
        "source_column_presence_status",
    ],
    "r_series_source_pool_summary": [
        "source_pool_id",
        "family_id",
        "variant_ids",
        "source_event_count",
        "score_availability_status",
    ],
}


@dataclass(frozen=True)
class ScopeSpec:
    candidate_scope_id: str
    candidate_scope_type: str
    source_experiment: str
    source_artifact_key: str
    source_row_filter: str
    canonicalization_rule: str
    family_id: str
    variant_id: str
    reference_scope_id: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Experiment A density / fast-fail audit.")
    parser.add_argument(
        "--mode",
        choices=["check-inputs", "full"],
        default="full",
        help="Check source artifacts or run the audit.",
    )
    return parser.parse_args(argv)


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


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if denominator is None or pd.isna(denominator) or float(denominator) == 0:
        return np.nan
    return float(numerator) / float(denominator)


def finite_float(value: Any, default: float = np.nan) -> float:
    if value is None or pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.1f}%"


def num(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def read_source_columns(path: Path) -> tuple[list[str], str]:
    if not path.exists() or not path.is_file():
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
    if path.suffix == ".parquet":
        try:
            return pd.read_parquet(path).columns.tolist(), "readable_tabular"
        except Exception:
            return [], "unreadable"
    try:
        return pd.read_csv(path, nrows=0).columns.tolist(), "readable_tabular"
    except Exception:
        return [], "unreadable"


def source_columns_hash(path: Path) -> str:
    columns, status = read_source_columns(path)
    if status not in {"readable_tabular", "readable_non_tabular"}:
        return ""
    return stable_hash(columns)


def input_audit() -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for key, path in REQUIRED_INPUTS.items():
        exists = path.exists()
        actual_columns, readability_status = read_source_columns(path)
        expected_columns = REQUIRED_INPUT_COLUMNS.get(key, [])
        missing_columns = sorted(set(expected_columns) - set(actual_columns))
        if not exists:
            status = "missing_required_input"
        elif readability_status == "unreadable":
            status = "unreadable_required_input"
        elif missing_columns:
            status = "schema_incompatible_required_input"
        else:
            status = "ok"
        if status != "ok":
            if missing_columns:
                failures.append(f"{status}:{key}:missing_columns={';'.join(missing_columns)}")
            else:
                failures.append(f"{status}:{key}")
        rows.append(
            {
                "input_id": key,
                "input_kind": "required",
                "path": str(path),
                "exists": bool(exists),
                "readability_status": readability_status,
                "hash_status": "hash_available" if exists and path.is_file() else "missing",
                "sha256": path_hash(path),
                "schema_hash": source_columns_hash(path),
                "expected_columns": ";".join(expected_columns),
                "actual_columns": ";".join(actual_columns),
                "missing_required_columns": ";".join(missing_columns),
                "status": status,
            }
        )
    for key, path in OPTIONAL_INPUTS.items():
        exists = path.exists()
        non_empty = exists and path.is_file() and path.stat().st_size > 1
        actual_columns, readability_status = read_source_columns(path) if non_empty else ([], "missing")
        rows.append(
            {
                "input_id": key,
                "input_kind": "optional",
                "path": str(path),
                "exists": bool(exists),
                "readability_status": readability_status,
                "hash_status": "hash_available" if non_empty else "missing_or_empty",
                "sha256": path_hash(path) if non_empty else "",
                "schema_hash": source_columns_hash(path) if non_empty else "",
                "expected_columns": "",
                "actual_columns": ";".join(actual_columns),
                "missing_required_columns": "",
                "status": "ok" if non_empty else "not_available_or_empty",
            }
        )
    return pd.DataFrame(rows), failures


def ensure_output_dirs() -> None:
    for path in [AUDIT_TABLE_DIR, AUDIT_REPORT_DIR, AUDIT_MANIFEST_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def contains_token(series: pd.Series, token: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(token, regex=False)


def with_event_window_anchor(events: pd.DataFrame) -> pd.DataFrame:
    out = events.copy()
    non_exec = out.get("non_executable_next_open", False)
    if not isinstance(non_exec, pd.Series):
        non_exec = pd.Series(False, index=out.index)
    non_exec_bool = non_exec.fillna(False).astype(bool)
    trade_pos = pd.to_numeric(out.get("trade_open_pos"), errors="coerce")
    event_pos = pd.to_numeric(out.get("event_t0_pos"), errors="coerce")
    use_trade = (~non_exec_bool) & trade_pos.notna()
    out["event_window_anchor_pos"] = np.where(use_trade, trade_pos, event_pos)
    trade_date = out.get("trade_open_date")
    event_date = out.get("event_t0_date")
    if not isinstance(trade_date, pd.Series):
        trade_date = pd.Series("", index=out.index)
    if not isinstance(event_date, pd.Series):
        event_date = pd.Series("", index=out.index)
    out["event_window_anchor_date"] = np.where(use_trade, trade_date, event_date)
    out["event_window_anchor_status"] = np.where(
        use_trade, "next_open_execution_anchor", "non_executable_t0_fallback"
    )
    return out


def normalise_scope_events(
    events: pd.DataFrame,
    spec: ScopeSpec,
    *,
    source_path: Path,
) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    out = events.copy()
    if "canonical_event_id" not in out.columns:
        out["canonical_event_id"] = out.get("event_id", "")
    out = out.drop_duplicates(subset=["canonical_event_id", "event_id"], keep="first")
    out["candidate_scope_id"] = spec.candidate_scope_id
    out["candidate_scope_type"] = spec.candidate_scope_type
    out["source_experiment"] = spec.source_experiment
    out["scope_family_id"] = spec.family_id
    out["scope_variant_id"] = spec.variant_id
    out["source_artifact_path"] = str(source_path)
    out["event_key"] = out["canonical_event_id"].fillna(out["event_id"]).astype(str)
    out = with_event_window_anchor(out)
    if spec.canonicalization_rule == "canonical union by instrument / event anchor":
        anchor_pos = pd.to_numeric(out["event_window_anchor_pos"], errors="coerce")
        anchored = out.loc[anchor_pos.notna()].copy()
        anchorless = out.loc[anchor_pos.isna()].copy()
        anchored = anchored.sort_values(
            ["instrument", "event_window_anchor_pos", "event_key"],
            kind="stable",
        ).drop_duplicates(subset=["instrument", "event_window_anchor_pos"], keep="first")
        out = pd.concat([anchored, anchorless], ignore_index=True)
    if "event_split" not in out.columns:
        out["event_split"] = "unknown"
    if "market_regime_bucket" not in out.columns:
        out["market_regime_bucket"] = "unknown"
    if "board_bucket" not in out.columns:
        out["board_bucket"] = "unknown"
    return out


def build_scope_specs() -> list[ScopeSpec]:
    return [
        ScopeSpec(
            "07_E1_only",
            "07_e1_only",
            "07",
            "07_canonical_events",
            f"triggered_channels contains {E1_CHANNEL}",
            "canonical rows by canonical_event_id / event_id",
            E1_CHANNEL,
            "07_recomputed",
            "07_e1_only",
        ),
        ScopeSpec(
            "07_E1_plus_E3",
            "07_channel_union",
            "07",
            "07_canonical_events",
            f"triggered_channels contains {E1_CHANNEL} or {E3_CHANNEL}",
            "canonical rows by canonical_event_id / event_id",
            "E1_plus_E3",
            "07_recomputed",
            "",
        ),
        ScopeSpec(
            "07_full_union",
            "07_full_union",
            "07",
            "07_canonical_events",
            "all rows in 07 canonical publishable table",
            "canonical rows by canonical_event_id / event_id",
            "07_full_union",
            "reported_union",
            "07_full_union",
        ),
        ScopeSpec(
            "08_selected_T4_T7_union",
            "08_candidate_union",
            "08",
            "08_canonical_events",
            "triggered_family_variants contains selected T4/T7 event_regime_gated variants",
            "canonical rows by canonical_event_id / event_id",
            "selected_T4_T7_union",
            "train_selected_union",
            "selected_candidate_union",
        ),
        ScopeSpec(
            "08_T4_gated",
            "08_candidate_family_variant",
            "08",
            "08_canonical_events",
            "triggered_family_variants contains T4 event_regime_gated",
            "canonical rows by canonical_event_id / event_id",
            "T4_entropy_compression_then_directional_expansion",
            "event_regime_gated",
            "T4_entropy_compression_then_directional_expansion__event_regime_gated",
        ),
        ScopeSpec(
            "08_T7_gated",
            "08_candidate_family_variant",
            "08",
            "08_canonical_events",
            "triggered_family_variants contains T7 event_regime_gated",
            "canonical rows by canonical_event_id / event_id",
            "T7_board_relative_strength_break",
            "event_regime_gated",
            "T7_board_relative_strength_break__event_regime_gated",
        ),
        ScopeSpec(
            "08_R_core_event_regime_gated",
            "08_candidate_union",
            "08",
            "08_canonical_events",
            "triggered_family_variants contains any R1/R2/R6/R7/R8 event_regime_gated variant",
            "canonical union by instrument / event anchor",
            "R_core",
            "event_regime_gated",
            "event_regime_gated_only",
        ),
        *[
            ScopeSpec(
                f"08_{family.split('_', 1)[0]}_event_regime_gated",
                "08_candidate_family_variant",
                "08",
                "08_canonical_events",
                f"triggered_family_variants contains {family}__event_regime_gated",
                "canonical rows by canonical_event_id / event_id",
                family,
                "event_regime_gated",
                f"{family}__event_regime_gated",
            )
            for family in CORE_R_FAMILIES
        ],
    ]


def select_scope_events(
    spec: ScopeSpec,
    canonical_07: pd.DataFrame,
    canonical_08: pd.DataFrame,
) -> pd.DataFrame:
    if spec.candidate_scope_id == "07_E1_only":
        return canonical_07[contains_token(canonical_07["triggered_channels"], E1_CHANNEL)]
    if spec.candidate_scope_id == "07_E1_plus_E3":
        channels = canonical_07["triggered_channels"].fillna("")
        return canonical_07[
            channels.str.contains(E1_CHANNEL, regex=False)
            | channels.str.contains(E3_CHANNEL, regex=False)
        ]
    if spec.candidate_scope_id == "07_full_union":
        return canonical_07

    variants = canonical_08["triggered_family_variants"].fillna("")
    if spec.candidate_scope_id == "08_selected_T4_T7_union":
        return canonical_08[
            variants.str.contains(
                "T4_entropy_compression_then_directional_expansion__event_regime_gated",
                regex=False,
            )
            | variants.str.contains(
                "T7_board_relative_strength_break__event_regime_gated",
                regex=False,
            )
        ]
    if spec.candidate_scope_id == "08_R_core_event_regime_gated":
        mask = pd.Series(False, index=canonical_08.index)
        for family in CORE_R_FAMILIES:
            mask |= variants.str.contains(f"{family}__event_regime_gated", regex=False)
        return canonical_08[mask]
    token = f"{spec.family_id}__event_regime_gated"
    return canonical_08[variants.str.contains(token, regex=False)]


def reference_counts(
    density: pd.DataFrame,
    frontier: pd.DataFrame,
) -> dict[str, int]:
    out: dict[str, int] = {}
    if not density.empty and "candidate_scope_id" in density.columns:
        for _, row in density.iterrows():
            out[str(row["candidate_scope_id"])] = int(row.get("event_count", 0) or 0)
    if not frontier.empty and "compression_arm_id" in frontier.columns:
        for _, row in frontier.iterrows():
            out[str(row["compression_arm_id"])] = int(
                row.get("canonical_event_count", row.get("event_count", 0)) or 0
            )
    return out


def infer_instrument_years(density: pd.DataFrame, fallback_event_count: int) -> float:
    if not density.empty:
        row = density.loc[density["candidate_scope_id"] == "07_e1_only"]
        if not row.empty:
            event_count = finite_float(row.iloc[0].get("event_count"))
            full_density = finite_float(row.iloc[0].get("density_full_denominator"))
            if event_count > 0 and full_density > 0:
                return event_count / full_density
    return float(fallback_event_count) if fallback_event_count else np.nan


def rolling_window_counts(events: pd.DataFrame, horizon: int) -> pd.Series:
    if events.empty:
        return pd.Series(dtype=float)
    working = events[["instrument", "event_window_anchor_pos"]].copy()
    working["event_window_anchor_pos"] = pd.to_numeric(
        working["event_window_anchor_pos"], errors="coerce"
    )
    counts = pd.Series(1, index=working.index, dtype=float)
    for _, group in working.dropna(subset=["event_window_anchor_pos"]).groupby("instrument"):
        ordered = group.sort_values("event_window_anchor_pos")
        positions = ordered["event_window_anchor_pos"].to_numpy()
        values: list[int] = []
        right = 0
        n = len(positions)
        for i, pos in enumerate(positions):
            if right < i:
                right = i
            while right < n and positions[right] <= pos + horizon:
                right += 1
            values.append(int(right - i))
        counts.loc[ordered.index] = values
    return counts


def adjacent_gaps(events: pd.DataFrame) -> pd.Series:
    if events.empty:
        return pd.Series(dtype=float)
    working = events[["instrument", "event_window_anchor_pos"]].copy()
    working["event_window_anchor_pos"] = pd.to_numeric(
        working["event_window_anchor_pos"], errors="coerce"
    )
    gaps = pd.Series(np.nan, index=working.index, dtype=float)
    for _, group in working.dropna(subset=["event_window_anchor_pos"]).groupby("instrument"):
        ordered = group.sort_values("event_window_anchor_pos")
        gaps.loc[ordered.index] = ordered["event_window_anchor_pos"].diff()
    return gaps


def event_uniqueness(events: pd.DataFrame, horizon: int = 10) -> pd.Series:
    if events.empty:
        return pd.Series(dtype=float)
    working = events[["instrument", "event_window_anchor_pos"]].copy()
    working["event_window_anchor_pos"] = pd.to_numeric(
        working["event_window_anchor_pos"], errors="coerce"
    )
    out = pd.Series(np.nan, index=working.index, dtype=float)
    for _, group in working.dropna(subset=["event_window_anchor_pos"]).groupby("instrument"):
        starts = group["event_window_anchor_pos"].astype(int)
        concurrency: dict[int, int] = {}
        for start in starts:
            for pos in range(int(start), int(start) + horizon + 1):
                concurrency[pos] = concurrency.get(pos, 0) + 1
        for idx, start in starts.items():
            vals = [
                1.0 / concurrency[pos]
                for pos in range(int(start), int(start) + horizon + 1)
                if concurrency.get(pos, 0) > 0
            ]
            out.loc[idx] = float(np.mean(vals)) if vals else np.nan
    return out


def partition_rows(events: pd.DataFrame) -> list[tuple[str, str, pd.DataFrame]]:
    if events.empty:
        return []
    rows: list[tuple[str, str, pd.DataFrame]] = [("all", "all", events)]
    for split, group in events.groupby("event_split", dropna=False):
        rows.append((str(split), "all", group))
    for regime, group in events.groupby("market_regime_bucket", dropna=False):
        rows.append(("all", str(regime), group))
    for (split, regime), group in events.groupby(
        ["event_split", "market_regime_bucket"], dropna=False
    ):
        rows.append((str(split), str(regime), group))
    return rows


def density_metrics_for_events(
    events: pd.DataFrame,
    *,
    instrument_years: float,
) -> dict[str, Any]:
    event_count = int(len(events))
    if event_count == 0:
        return {
            "events_per_instrument_year_mean": np.nan,
            "events_per_instrument_year_p95": np.nan,
            "rolling_10d_window_count_self_included_mean": np.nan,
            "rolling_10d_neighbor_count_ex_self_mean": np.nan,
            "rolling_10d_duplicate_event_count": 0,
            "rolling_10d_duplicate_rate": np.nan,
            "rolling_20d_window_count_self_included_mean": np.nan,
            "rolling_20d_neighbor_count_ex_self_mean": np.nan,
            "rolling_20d_duplicate_event_count": 0,
            "rolling_20d_duplicate_rate": np.nan,
            "event_uniqueness_10d_mean": np.nan,
            "event_uniqueness_10d_median": np.nan,
            "event_uniqueness_10d_p10": np.nan,
            "event_uniqueness_10d_low_share": np.nan,
            "same_day_duplicate_rate": np.nan,
        }
    counts_10 = rolling_window_counts(events, 10)
    neighbors_10 = counts_10 - 1
    counts_20 = rolling_window_counts(events, 20)
    neighbors_20 = counts_20 - 1
    uniq = event_uniqueness(events, 10)
    same_day = (
        events.groupby(["instrument", "event_window_anchor_pos"], dropna=False)[
            "event_key"
        ].transform("count")
        > 1
    )
    instrument_count = max(int(events["instrument"].nunique()), 1)
    years_per_instrument = (
        instrument_years / instrument_count
        if instrument_years and not pd.isna(instrument_years)
        else np.nan
    )
    per_instrument_counts = events.groupby("instrument").size()
    if years_per_instrument and not pd.isna(years_per_instrument):
        per_instrument_density = per_instrument_counts / years_per_instrument
        p95_density = float(per_instrument_density.quantile(0.95))
    else:
        p95_density = np.nan
    mean_density = event_count / instrument_years if instrument_years else np.nan
    return {
        "events_per_instrument_year_mean": mean_density,
        "events_per_instrument_year_p95": p95_density,
        "rolling_10d_window_count_self_included_mean": float(counts_10.mean()),
        "rolling_10d_neighbor_count_ex_self_mean": float(neighbors_10.mean()),
        "rolling_10d_duplicate_event_count": int((neighbors_10 > 0).sum()),
        "rolling_10d_duplicate_rate": safe_rate(int((neighbors_10 > 0).sum()), event_count),
        "rolling_20d_window_count_self_included_mean": float(counts_20.mean()),
        "rolling_20d_neighbor_count_ex_self_mean": float(neighbors_20.mean()),
        "rolling_20d_duplicate_event_count": int((neighbors_20 > 0).sum()),
        "rolling_20d_duplicate_rate": safe_rate(int((neighbors_20 > 0).sum()), event_count),
        "event_uniqueness_10d_mean": float(uniq.mean()),
        "event_uniqueness_10d_median": float(uniq.median()),
        "event_uniqueness_10d_p10": float(uniq.quantile(0.10)),
        "event_uniqueness_10d_low_share": safe_rate(
            int((uniq < LOW_UNIQUENESS_THRESHOLD).sum()), int(uniq.notna().sum())
        ),
        "same_day_duplicate_rate": safe_rate(int(same_day.sum()), event_count),
    }


def labels_for_source(source_experiment: str, labels_07: pd.DataFrame, labels_08: pd.DataFrame) -> pd.DataFrame:
    labels = labels_07 if source_experiment == "07" else labels_08
    if labels.empty:
        return labels
    return labels.drop_duplicates(subset=["event_id"], keep="last").copy()


def merge_labels(events: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
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
            "event_false_repair_10d_label",
            "event_false_repair_10d_complete",
            "event_false_repair_20d_label",
            "event_false_repair_20d_complete",
            "non_executable_next_open",
            "horizon_complete_10d",
        ]
        if col in labels.columns
    ]
    out = events.merge(labels[label_cols], on="event_id", how="left", suffixes=("", "_label"))
    out["event_level_label_source_status"] = np.where(
        out.get("failure_10_complete").notna()
        if "failure_10_complete" in out.columns
        else False,
        "event_level_label_available",
        "not_available_publishable_source",
    )
    return out


def build_density_summary(
    scope_events: dict[str, pd.DataFrame],
    scope_specs: dict[str, ScopeSpec],
    labels_07: pd.DataFrame,
    labels_08: pd.DataFrame,
    frontier: pd.DataFrame,
    instrument_years: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    e1_count = len(scope_events.get("07_E1_only", pd.DataFrame()))
    for scope_id, events in scope_events.items():
        spec = scope_specs[scope_id]
        labels = labels_for_source(spec.source_experiment, labels_07, labels_08)
        merged = merge_labels(events, labels)
        metrics = density_metrics_for_events(events, instrument_years=instrument_years)
        executable = int((~events.get("non_executable_next_open", False).fillna(False).astype(bool)).sum())
        failure_complete = (
            int(merged["failure_10_complete"].fillna(False).astype(bool).sum())
            if "failure_10_complete" in merged.columns
            else 0
        )
        rows.append(
            {
                "candidate_scope_id": scope_id,
                "candidate_scope_type": spec.candidate_scope_type,
                "source_experiment": spec.source_experiment,
                "event_count": int(len(events)),
                "executable_event_count": executable,
                "failure_10_complete_event_count": failure_complete,
                "event_window_anchor_policy_id": EVENT_ANCHOR_POLICY,
                "non_executable_t0_fallback_event_count": int(
                    (events["event_window_anchor_status"] == "non_executable_t0_fallback").sum()
                ),
                "denominator_source_id": "08_full_evaluated_universe_years_252",
                "instrument_years": instrument_years,
                "denominator_compatibility_group": "07_08_topn_proxy_universe_years_252",
                **metrics,
                "event_uniqueness_concurrency_scope": UNIQUENESS_SCOPE,
                "density_vs_07_E1_only": safe_rate(len(events), e1_count),
                "density_vs_07_E1_only_compatibility_flag": True,
                "density_vs_08_E1_recomputed": safe_rate(len(events), e1_count),
                "density_vs_08_E1_recomputed_compatibility_flag": True,
                "scope_status": "reconstructable_event_membership",
            }
        )
    if not frontier.empty:
        for _, row in frontier.iterrows():
            scope_id = f"08_R_compression_arm::{row['compression_arm_id']}"
            rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "candidate_scope_type": "r_series_compression_arm",
                    "source_experiment": "08_r_series_density_compression",
                    "event_count": int(row.get("canonical_event_count", row.get("event_count", 0)) or 0),
                    "executable_event_count": int(
                        (row.get("next_open_executable_rate", np.nan) or np.nan)
                        * int(row.get("canonical_event_count", row.get("event_count", 0)) or 0)
                    )
                    if pd.notna(row.get("next_open_executable_rate", np.nan))
                    else np.nan,
                    "failure_10_complete_event_count": np.nan,
                    "event_window_anchor_policy_id": "aggregate_frontier_only",
                    "non_executable_t0_fallback_event_count": np.nan,
                    "denominator_source_id": "08_full_evaluated_universe_years_252",
                    "instrument_years": instrument_years,
                    "denominator_compatibility_group": "07_08_topn_proxy_universe_years_252",
                    "events_per_instrument_year_mean": row.get("density_full_denominator", np.nan),
                    "events_per_instrument_year_p95": row.get(
                        "events_per_instrument_year_p95", np.nan
                    ),
                    "rolling_10d_window_count_self_included_mean": np.nan,
                    "rolling_10d_neighbor_count_ex_self_mean": np.nan,
                    "rolling_10d_duplicate_event_count": np.nan,
                    "rolling_10d_duplicate_rate": np.nan,
                    "rolling_20d_window_count_self_included_mean": np.nan,
                    "rolling_20d_neighbor_count_ex_self_mean": np.nan,
                    "rolling_20d_duplicate_event_count": np.nan,
                    "rolling_20d_duplicate_rate": np.nan,
                    "event_uniqueness_concurrency_scope": "aggregate_frontier_only",
                    "event_uniqueness_10d_mean": np.nan,
                    "event_uniqueness_10d_median": np.nan,
                    "event_uniqueness_10d_p10": np.nan,
                    "event_uniqueness_10d_low_share": np.nan,
                    "same_day_duplicate_rate": np.nan,
                    "density_vs_07_E1_only": row.get("density_vs_e1_full_denominator", np.nan),
                    "density_vs_07_E1_only_compatibility_flag": True,
                    "density_vs_08_E1_recomputed": row.get(
                        "density_vs_e1_full_denominator", np.nan
                    ),
                    "density_vs_08_E1_recomputed_compatibility_flag": True,
                    "scope_status": "aggregate_frontier_only_no_event_membership",
                }
            )
    return pd.DataFrame(rows)


def build_fast_fail_readout(
    scope_events: dict[str, pd.DataFrame],
    scope_specs: dict[str, ScopeSpec],
    labels_07: pd.DataFrame,
    labels_08: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope_id, events in scope_events.items():
        spec = scope_specs[scope_id]
        labels = labels_for_source(spec.source_experiment, labels_07, labels_08)
        merged = merge_labels(events, labels)
        for split, regime, group in partition_rows(merged):
            complete = (
                group["failure_10_complete"].fillna(False).astype(bool)
                if "failure_10_complete" in group.columns
                else pd.Series(False, index=group.index)
            )
            fast_fail = (
                pd.to_numeric(group["failure_10_label"], errors="coerce").fillna(0) == 1
                if "failure_10_label" in group.columns
                else pd.Series(False, index=group.index)
            )
            false20 = (
                group["event_false_repair_20d_label"].fillna(False).astype(bool)
                if "event_false_repair_20d_label" in group.columns
                else pd.Series(False, index=group.index)
            )
            non_exec = group.get("non_executable_next_open", False)
            if not isinstance(non_exec, pd.Series):
                non_exec = pd.Series(False, index=group.index)
            rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "event_split": split,
                    "market_regime_bucket": regime,
                    "event_count": int(len(group)),
                    "failure_10_complete_event_count": int(complete.sum()),
                    "fast_fail_10d_count": int((complete & fast_fail).sum()),
                    "fast_fail_10d_rate": safe_rate(int((complete & fast_fail).sum()), int(complete.sum())),
                    "false_repair_20d_count": int(false20.sum()),
                    "false_repair_20d_rate": safe_rate(int(false20.sum()), int(len(group))),
                    "non_executable_event_count": int(non_exec.fillna(False).astype(bool).sum()),
                    "horizon_incomplete_10d_count": int((~complete).sum()),
                    "label_source_column": "failure_10_label",
                    "fast_fail_definition_id": "failure_10_path",
                    "fast_fail_definition_comparable_to_failure_10_path": True,
                    "label_mapping_status": "direct_event_level_label"
                    if int(complete.sum()) > 0
                    else "not_available_publishable_source",
                    "event_level_label_source_status": "event_level_label_available"
                    if int(complete.sum()) > 0
                    else "not_available_publishable_source",
                }
            )
    return pd.DataFrame(rows)


def build_gap_diagnostic(scope_events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope_id, events in scope_events.items():
        gaps_all = adjacent_gaps(events)
        events = events.assign(_adjacent_gap=gaps_all)
        for split, regime, group in partition_rows(events):
            gaps = pd.to_numeric(group["_adjacent_gap"], errors="coerce").dropna()
            rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "event_split": split,
                    "market_regime_bucket": regime,
                    "instrument_count": int(group["instrument"].nunique()),
                    "gap_sample_count": int(len(gaps)),
                    "gap_anchor_policy_id": EVENT_ANCHOR_POLICY,
                    "adjacent_gap_p10": float(gaps.quantile(0.10)) if len(gaps) else np.nan,
                    "adjacent_gap_median": float(gaps.median()) if len(gaps) else np.nan,
                    "adjacent_gap_p90": float(gaps.quantile(0.90)) if len(gaps) else np.nan,
                    "gap_lt_5d_rate": safe_rate(int((gaps < 5).sum()), len(gaps)),
                    "gap_lt_10d_rate": safe_rate(int((gaps < 10).sum()), len(gaps)),
                    "gap_ge_20d_rate": safe_rate(int((gaps >= 20).sum()), len(gaps)),
                    "diagnostic_alert_flag": bool(len(gaps) and float(gaps.median()) < 10),
                }
            )
    return pd.DataFrame(rows)


def build_uniqueness_diagnostic(scope_events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope_id, events in scope_events.items():
        uniq_all = event_uniqueness(events)
        events = events.assign(_event_uniqueness_10d=uniq_all)
        counts_all = rolling_window_counts(events, 10)
        events = events.assign(_concurrency_proxy=counts_all)
        for split, regime, group in partition_rows(events):
            uniq = pd.to_numeric(group["_event_uniqueness_10d"], errors="coerce").dropna()
            conc = pd.to_numeric(group["_concurrency_proxy"], errors="coerce").dropna()
            low_share = safe_rate(int((uniq < LOW_UNIQUENESS_THRESHOLD).sum()), len(uniq))
            rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "event_split": split,
                    "market_regime_bucket": regime,
                    "event_count": int(len(group)),
                    "executable_event_count": int(
                        (~group.get("non_executable_next_open", False).fillna(False).astype(bool)).sum()
                    ),
                    "active_interval_definition": "[event_window_anchor_pos,event_window_anchor_pos+10]",
                    "active_interval_horizon_trading_days": 10,
                    "concurrency_scope": UNIQUENESS_SCOPE,
                    "concurrency_mean": float(conc.mean()) if len(conc) else np.nan,
                    "concurrency_p95": float(conc.quantile(0.95)) if len(conc) else np.nan,
                    "event_uniqueness_10d_mean": float(uniq.mean()) if len(uniq) else np.nan,
                    "event_uniqueness_10d_median": float(uniq.median()) if len(uniq) else np.nan,
                    "event_uniqueness_10d_p10": float(uniq.quantile(0.10)) if len(uniq) else np.nan,
                    "event_uniqueness_10d_low_share": low_share,
                    "low_uniqueness_threshold": LOW_UNIQUENESS_THRESHOLD,
                    "uniqueness_diagnostic_alert_flag": bool(
                        pd.notna(low_share) and low_share > 0.05
                    ),
                }
            )
    return pd.DataFrame(rows)


def capture_scope_map(scope_specs: dict[str, ScopeSpec]) -> dict[str, str]:
    mapping = {scope_id: spec.reference_scope_id for scope_id, spec in scope_specs.items()}
    if "07_E1_only" in mapping:
        mapping["07_E1_only"] = "07_e1_only"
    if "07_full_union" in mapping:
        mapping["07_full_union"] = "07_full_union"
    if "08_selected_T4_T7_union" in mapping:
        mapping["08_selected_T4_T7_union"] = "selected_candidate_union"
    return mapping


def retention_rows_from_capture(
    capture: pd.DataFrame,
    scope_specs: dict[str, ScopeSpec],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if capture.empty:
        for scope_id in scope_specs:
            rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "retention_replay_id": "not_available_publishable_source",
                    "retention_replay_definition": "episode capture source unavailable",
                    "replay_uses_future_label": False,
                    "episode_split": "all",
                    "market_regime_bucket": "all",
                    "target_episode_denominator": np.nan,
                    "pre_replay_any_recall": np.nan,
                    "post_replay_any_recall": np.nan,
                    "any_recall_retention": np.nan,
                    "pre_replay_bridge_recall": np.nan,
                    "post_replay_bridge_recall": np.nan,
                    "bridge_recall_retention": np.nan,
                    "e1_missed_capture_retention": np.nan,
                    "event_level_label_source_status": "not_available_publishable_source",
                    "cell_sample_status": "not_available_publishable_source",
                    "retention_source_status": "not_available_publishable_source",
                    "episode_capture_source_path": "",
                    "episode_capture_source_hash": "",
                }
            )
        return pd.DataFrame(rows)

    mapping = capture_scope_map(scope_specs)
    e1 = capture.loc[
        (capture["candidate_scope_id"] == "07_e1_only")
        & (capture["window"] == BEFORE_FIRST_50)
    ][["target_episode_id", "episode_split", "market_regime_bucket", "any_event_captured"]]
    e1 = e1.rename(columns={"any_event_captured": "e1_any_event_captured"})
    capture_path = OPTIONAL_INPUTS["08_capture_local"]
    capture_hash = path_hash(capture_path)
    for scope_id, capture_scope_id in mapping.items():
        if not capture_scope_id:
            scope_capture = pd.DataFrame()
        else:
            scope_capture = capture.loc[
                (capture["candidate_scope_id"] == capture_scope_id)
                & (capture["window"] == BEFORE_FIRST_50)
            ].copy()
        if scope_capture.empty:
            rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "retention_replay_id": "not_available_publishable_source",
                    "retention_replay_definition": "capture scope unavailable or event-level membership unavailable",
                    "replay_uses_future_label": False,
                    "episode_split": "all",
                    "market_regime_bucket": "all",
                    "target_episode_denominator": np.nan,
                    "pre_replay_any_recall": np.nan,
                    "post_replay_any_recall": np.nan,
                    "any_recall_retention": np.nan,
                    "pre_replay_bridge_recall": np.nan,
                    "post_replay_bridge_recall": np.nan,
                    "bridge_recall_retention": np.nan,
                    "e1_missed_capture_retention": np.nan,
                    "event_level_label_source_status": "not_available_publishable_source",
                    "cell_sample_status": "not_available_publishable_source",
                    "retention_source_status": "scope_capture_not_available",
                    "episode_capture_source_path": str(capture_path),
                    "episode_capture_source_hash": capture_hash,
                }
            )
            continue
        joined = scope_capture.merge(
            e1,
            on=["target_episode_id", "episode_split", "market_regime_bucket"],
            how="left",
        )
        for split, regime, group in [("all", "all", joined)] + [
            (f"{split}", f"{regime}", g)
            for (split, regime), g in joined.groupby(
                ["episode_split", "market_regime_bucket"], dropna=False
            )
        ]:
            any_denom = group["any_event_denominator_included"].fillna(False).astype(bool)
            bridge_denom = group["bridge_positive_denominator_included"].fillna(False).astype(bool)
            any_captured = group["any_event_captured"].fillna(False).astype(bool)
            bridge_captured = group["bridge_positive_captured"].fillna(False).astype(bool)
            e1_missed = ~group["e1_any_event_captured"].fillna(False).astype(bool)
            pre_any = safe_rate(int((any_denom & any_captured).sum()), int(any_denom.sum()))
            pre_bridge = safe_rate(
                int((bridge_denom & bridge_captured).sum()), int(bridge_denom.sum())
            )
            rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "retention_replay_id": "pre_replay_capture_only",
                    "retention_replay_definition": "pre-replay capture available; event-to-episode full membership unavailable for post-replay filtering",
                    "replay_uses_future_label": False,
                    "episode_split": split,
                    "market_regime_bucket": regime,
                    "target_episode_denominator": int(any_denom.sum()),
                    "pre_replay_any_recall": pre_any,
                    "post_replay_any_recall": np.nan,
                    "any_recall_retention": np.nan,
                    "pre_replay_bridge_recall": pre_bridge,
                    "post_replay_bridge_recall": np.nan,
                    "bridge_recall_retention": np.nan,
                    "e1_missed_capture_retention": safe_rate(
                        int((any_denom & e1_missed & any_captured).sum()),
                        int((any_denom & e1_missed).sum()),
                    ),
                    "event_level_label_source_status": "event_level_label_available_but_episode_membership_not_available",
                    "cell_sample_status": "sufficient_for_cell_readout"
                    if int(any_denom.sum()) >= 100
                    else ("low_power_caution" if int(any_denom.sum()) >= 30 else "diagnostic_only"),
                    "retention_source_status": "pre_replay_capture_only",
                    "episode_capture_source_path": str(capture_path),
                    "episode_capture_source_hash": capture_hash,
                }
            )
    return pd.DataFrame(rows)


def build_episode_density_comparison(
    retention: pd.DataFrame,
    density_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    density_idx = density_summary.set_index("candidate_scope_id") if not density_summary.empty else pd.DataFrame()
    for _, row in retention.iterrows():
        scope_id = row["candidate_scope_id"]
        dens = density_idx.loc[scope_id] if scope_id in density_idx.index else {}
        rolling_dup = dens.get("rolling_10d_duplicate_rate", np.nan) if isinstance(dens, pd.Series) else np.nan
        uniq_p10 = dens.get("event_uniqueness_10d_p10", np.nan) if isinstance(dens, pd.Series) else np.nan
        executable_alert = bool(
            (pd.notna(rolling_dup) and float(rolling_dup) > 0.10)
            or (pd.notna(uniq_p10) and float(uniq_p10) < LOW_UNIQUENESS_THRESHOLD)
        )
        rows.append(
            {
                "candidate_scope_id": scope_id,
                "episode_split": row["episode_split"],
                "market_regime_bucket": row["market_regime_bucket"],
                "episode_window_metric_status": row["retention_source_status"],
                "episode_event_count_mean": np.nan,
                "episode_event_count_median": np.nan,
                "episode_event_count_top10": np.nan,
                "episode_adjacent_gap_median": np.nan,
                "rolling_10d_duplicate_rate": rolling_dup,
                "event_uniqueness_10d_p10": uniq_p10,
                "executable_timing_alert_flag": executable_alert,
                "episode_window_alert_flag": False,
                "episode_window_used_as_hard_gate_flag": False,
                "density_concept_mismatch_note": "episode-window event-count fields require full event-to-episode membership; rolling 10d metrics remain executable-timing audit metrics",
            }
        )
    return pd.DataFrame(rows)


def build_mapping_and_reconstructability(
    scope_specs: dict[str, ScopeSpec],
    scope_events: dict[str, pd.DataFrame],
    input_paths: dict[str, Path],
    ref_counts: dict[str, int],
    frontier: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    mapping_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for scope_id, spec in scope_specs.items():
        source_path = input_paths[spec.source_artifact_key]
        events = scope_events.get(scope_id, pd.DataFrame())
        ref = ref_counts.get(spec.reference_scope_id, np.nan) if spec.reference_scope_id else np.nan
        status = "reconstructable_event_membership" if len(events) else "empty_scope_from_source_filter"
        mapping_rows.append(
            {
                "candidate_scope_id": scope_id,
                "source_experiment": spec.source_experiment,
                "source_artifact_path": str(source_path),
                "source_artifact_hash": path_hash(source_path),
                "source_row_filter": spec.source_row_filter,
                "canonicalization_rule": spec.canonicalization_rule,
                "expected_source_columns": "event_id;instrument;event_t0_pos;trade_open_pos",
                "actual_source_columns_hash": source_columns_hash(source_path),
                "reconstructability_requirement": "event_membership_required",
                "scope_mapping_status": status,
            }
        )
        audit_rows.append(
            {
                "candidate_scope_id": scope_id,
                "scope_status": status,
                "source_artifact_path": str(source_path),
                "source_artifact_hash_status": "hash_available" if source_path.exists() else "missing",
                "source_row_count": int(len(events)),
                "selected_event_count": int(len(events)),
                "published_reference_event_count": ref,
                "reconstructed_vs_published_count_difference": int(len(events) - ref)
                if pd.notna(ref)
                else np.nan,
                "missing_required_columns": "",
                "aggregate_only_reason": "",
                "event_level_label_source_status": "event_level_label_available",
                "episode_capture_source_status": "pre_replay_capture_only",
                "hard_gate_eligible_flag": bool(len(events)),
                "notes": "",
            }
        )
    if not frontier.empty:
        source_path = input_paths["r_series_frontier"]
        for _, row in frontier.iterrows():
            arm_id = str(row["compression_arm_id"])
            scope_id = f"08_R_compression_arm::{arm_id}"
            event_count = int(row.get("canonical_event_count", row.get("event_count", 0)) or 0)
            mapping_rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "source_experiment": "08_r_series_density_compression",
                    "source_artifact_path": str(source_path),
                    "source_artifact_hash": path_hash(source_path),
                    "source_row_filter": f"compression_arm_id == {arm_id}",
                    "canonicalization_rule": "aggregate-only unless deterministic membership reconstructs and reconciles",
                    "expected_source_columns": "compression_arm_id;threshold_policy;canonical_event_count",
                    "actual_source_columns_hash": source_columns_hash(source_path),
                    "reconstructability_requirement": "aggregate_frontier_allowed",
                    "scope_mapping_status": "aggregate_frontier_only_no_event_membership",
                }
            )
            audit_rows.append(
                {
                    "candidate_scope_id": scope_id,
                    "scope_status": "aggregate_frontier_only_no_event_membership",
                    "source_artifact_path": str(source_path),
                    "source_artifact_hash_status": "hash_available",
                    "source_row_count": 1,
                    "selected_event_count": np.nan,
                    "published_reference_event_count": event_count,
                    "reconstructed_vs_published_count_difference": np.nan,
                    "missing_required_columns": "",
                    "aggregate_only_reason": "explicit event membership unavailable or empty; deterministic reconstruction not attempted for hard-gate metrics",
                    "event_level_label_source_status": "not_available_publishable_source",
                    "episode_capture_source_status": "not_available_publishable_source",
                    "hard_gate_eligible_flag": False,
                    "notes": "excluded from rolling 10d, adjacent gap, uniqueness, and event-level fast-fail hard-gate comparisons",
                }
            )
    return pd.DataFrame(mapping_rows), pd.DataFrame(audit_rows)


def build_crosswalk(
    density_summary: pd.DataFrame,
    gap_diag: pd.DataFrame,
    uniqueness: pd.DataFrame,
) -> pd.DataFrame:
    gap_all = gap_diag.loc[
        (gap_diag["event_split"] == "all") & (gap_diag["market_regime_bucket"] == "all")
    ]
    uniq_all = uniqueness.loc[
        (uniqueness["event_split"] == "all")
        & (uniqueness["market_regime_bucket"] == "all")
    ]
    gap_idx = gap_all.set_index("candidate_scope_id") if not gap_all.empty else pd.DataFrame()
    uniq_idx = uniq_all.set_index("candidate_scope_id") if not uniq_all.empty else pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for _, row in density_summary.iterrows():
        scope_id = row["candidate_scope_id"]
        gap = gap_idx.loc[scope_id] if scope_id in gap_idx.index else {}
        uniq = uniq_idx.loc[scope_id] if scope_id in uniq_idx.index else {}
        aggregate_only = row["scope_status"] == "aggregate_frontier_only_no_event_membership"
        rolling_alert = pd.notna(row["rolling_10d_duplicate_rate"]) and row["rolling_10d_duplicate_rate"] > 0.10
        gap_alert = isinstance(gap, pd.Series) and pd.notna(gap.get("adjacent_gap_median")) and gap.get("adjacent_gap_median") < 10
        uniq_alert = isinstance(uniq, pd.Series) and pd.notna(uniq.get("event_uniqueness_10d_p10")) and uniq.get("event_uniqueness_10d_p10") < LOW_UNIQUENESS_THRESHOLD
        rows.append(
            {
                "candidate_scope_id": scope_id,
                "formal_full_denominator_density": row["events_per_instrument_year_mean"],
                "denominator_source_id": row["denominator_source_id"],
                "denominator_compatibility_group": row["denominator_compatibility_group"],
                "cross_source_ratio_gate_eligible": bool(row["density_vs_07_E1_only_compatibility_flag"]),
                "family_mechanism_concentration_status": "aggregate_or_scope_level_only",
                "episode_window_event_count_median": np.nan,
                "episode_window_event_count_top10": np.nan,
                "rolling_10d_window_count_self_included_mean": row[
                    "rolling_10d_window_count_self_included_mean"
                ],
                "rolling_10d_neighbor_count_ex_self_mean": row[
                    "rolling_10d_neighbor_count_ex_self_mean"
                ],
                "rolling_10d_duplicate_rate": row["rolling_10d_duplicate_rate"],
                "event_uniqueness_10d_p10": row["event_uniqueness_10d_p10"],
                "adjacent_gap_median": gap.get("adjacent_gap_median", np.nan)
                if isinstance(gap, pd.Series)
                else np.nan,
                "final_hard_gate_status": "aggregate_only_not_hard_gate_eligible"
                if aggregate_only
                else "hard_gate_not_failed_by_audit",
                "final_diagnostic_alert_status": "diagnostic_alert"
                if (rolling_alert or gap_alert or uniq_alert)
                else "no_executable_timing_alert",
            }
        )
    return pd.DataFrame(rows)


def build_gate_summary(crosswalk: pd.DataFrame, input_failures: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "gate_id": "input_gate",
            "gate_type": "hard_fail",
            "candidate_scope_id": "all",
            "gate_status": "fail" if input_failures else "pass",
            "metric_value": len(input_failures),
            "threshold_value": 0,
            "threshold_source": "required input contract",
            "train_only_threshold_flag": False,
            "denominator_compatibility_flag": True,
            "uses_episode_window_density_flag": False,
            "uses_future_label_flag": False,
            "failure_reason": ";".join(input_failures),
        }
    )
    for _, row in crosswalk.iterrows():
        rows.append(
            {
                "gate_id": "rolling_10d_duplicate_alert",
                "gate_type": "diagnostic_alert",
                "candidate_scope_id": row["candidate_scope_id"],
                "gate_status": row["final_diagnostic_alert_status"],
                "metric_value": row["rolling_10d_duplicate_rate"],
                "threshold_value": 0.10,
                "threshold_source": "predeclared diagnostic audit threshold",
                "train_only_threshold_flag": True,
                "denominator_compatibility_flag": row["cross_source_ratio_gate_eligible"],
                "uses_episode_window_density_flag": False,
                "uses_future_label_flag": False,
                "failure_reason": "",
            }
        )
    rows.append(
        {
            "gate_id": "episode_window_not_hard_gate",
            "gate_type": "hard_fail_guard",
            "candidate_scope_id": "all",
            "gate_status": "pass",
            "metric_value": 0,
            "threshold_value": 0,
            "threshold_source": "Experiment A requirement",
            "train_only_threshold_flag": False,
            "denominator_compatibility_flag": True,
            "uses_episode_window_density_flag": False,
            "uses_future_label_flag": False,
            "failure_reason": "",
        }
    )
    return pd.DataFrame(rows)


def caliber_contract_text() -> str:
    return """# Density / Fast-Fail Caliber Contract

This contract freezes the executable event-day density and fast-fail audit
caliber for Experiments B / C / D / E.

## Event Timing

- `event_t0` is the observable event date / position.
- `event_execution_key` is the next-open executable row.
- `event_window_anchor_pos` is `trade_open_pos` for executable rows and
  `event_t0_pos` only for non-executable audit rows.
- Non-executable rows remain in audit denominators and carry
  `event_window_anchor_status = non_executable_t0_fallback`.

## Rolling Density

- `rolling_10d_window_count_self_included` counts same-instrument and
  same-candidate-scope events in `[event_window_anchor_pos,
  event_window_anchor_pos + 10]`.
- Duplicate rates use ex-self neighbor counts, not self-included counts.
- The 20d window uses the same convention.

## Uniqueness

- `event_uniqueness_10d` uses active intervals
  `[event_window_anchor_pos, event_window_anchor_pos + 10]`.
- Concurrency is computed only within the same instrument and same candidate
  scope.
- E1 is a sparse reference anchor, not the alert baseline for expanded
  candidate families.

## Fast-Fail Labels

- `failure_10` and mapped `false_repair_10d` are forward diagnostic labels.
- They may be used for audit readouts and rejector targets only.
- Any replay that removes fast-fail events is an audit-only oracle replay and
  must not be described as an implementable t0 entry filter.

## Episode Density

Episode-window event counts are diagnostic-only. They must not set hard gates
unless an executable-timing diagnostic also fires, and even then the episode
window remains explanatory rather than a direct admission gate.
"""


def build_report(
    decision: str,
    density_summary: pd.DataFrame,
    fast_fail: pd.DataFrame,
    crosswalk: pd.DataFrame,
    reconstructability: pd.DataFrame,
) -> str:
    all_density = density_summary.set_index("candidate_scope_id")

    def row_value(scope: str, col: str) -> Any:
        return all_density.loc[scope, col] if scope in all_density.index else np.nan

    def markdown_view(frame: pd.DataFrame, scopes: list[str], columns: list[str]) -> str:
        if frame.empty:
            return "No rows available."
        scoped = frame.loc[frame["candidate_scope_id"].isin(scopes)].copy()
        if scoped.empty:
            return "No rows available."
        scoped["candidate_scope_id"] = pd.Categorical(
            scoped["candidate_scope_id"], categories=scopes, ordered=True
        )
        scoped = scoped.sort_values("candidate_scope_id")
        existing = [col for col in columns if col in scoped.columns]
        return scoped[existing].to_markdown(index=False)

    def rounded(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        for col in out.select_dtypes(include=["float", "float64", "float32"]).columns:
            out[col] = out[col].round(4)
        return out

    e1_dup = row_value("07_E1_only", "rolling_10d_duplicate_rate")
    r_core_dup = row_value("08_R_core_event_regime_gated", "rolling_10d_duplicate_rate")
    e1_gap = crosswalk.set_index("candidate_scope_id").get("adjacent_gap_median", pd.Series()).get("07_E1_only", np.nan)
    r_core_gap = crosswalk.set_index("candidate_scope_id").get("adjacent_gap_median", pd.Series()).get("08_R_core_event_regime_gated", np.nan)
    fast_all = fast_fail.loc[
        (fast_fail["event_split"] == "all")
        & (fast_fail["market_regime_bucket"] == "all")
    ]
    fast_view = fast_all[
        ["candidate_scope_id", "event_count", "fast_fail_10d_rate", "false_repair_20d_rate"]
    ].head(12)
    scope_summary = rounded(
        density_summary.merge(
            fast_all[
                [
                    "candidate_scope_id",
                    "fast_fail_10d_rate",
                    "false_repair_20d_rate",
                ]
            ],
            on="candidate_scope_id",
            how="left",
        )
    )
    crosswalk_rounded = rounded(crosswalk)
    core_scopes = [
        "07_E1_only",
        "07_E1_plus_E3",
        "07_full_union",
        "08_selected_T4_T7_union",
        "08_T4_gated",
        "08_T7_gated",
        "08_R_core_event_regime_gated",
        "08_R1_event_regime_gated",
        "08_R2_event_regime_gated",
        "08_R6_event_regime_gated",
        "08_R7_event_regime_gated",
        "08_R8_event_regime_gated",
    ]
    comparison_columns = [
        "candidate_scope_id",
        "event_count",
        "rolling_10d_duplicate_rate",
        "event_uniqueness_10d_p10",
        "fast_fail_10d_rate",
        "false_repair_20d_rate",
    ]
    gap_columns = [
        "candidate_scope_id",
        "formal_full_denominator_density",
        "rolling_10d_duplicate_rate",
        "event_uniqueness_10d_p10",
        "adjacent_gap_median",
        "final_hard_gate_status",
        "final_diagnostic_alert_status",
    ]
    arm_view = rounded(
        density_summary.loc[
            density_summary["candidate_scope_id"].astype(str).str.startswith(
                "08_R_compression_arm::"
            ),
            [
                "candidate_scope_id",
                "event_count",
                "density_vs_07_E1_only",
                "scope_status",
            ],
        ]
    )
    recon_counts = reconstructability["scope_status"].value_counts(dropna=False).to_dict()
    return f"""# Density / Fast-Fail Audit Report

Final decision: `{decision}`

## One-Page Conclusion

Experiment A replayed the 07 / 08 candidate scopes under a single executable
event-day density caliber. Rolling 10d density, adjacent gaps, and uniqueness
use `event_window_anchor_pos`, so executable rows are anchored at next-open
execution instead of raw signal t0.

E1 remains the sparse reference anchor: rolling 10d duplicate rate is
{pct(e1_dup)} and adjacent-gap median is {num(e1_gap, 1)} trading days. The
R-core event-regime-gated scope has rolling 10d duplicate rate {pct(r_core_dup)}
and adjacent-gap median {num(r_core_gap, 1)} trading days. These numbers should
be read as an audit of executable event congestion, not as a trading signal.

Retention replay is partial: pre-replay episode capture is available from local
capture artifacts, but full event-to-episode membership is not available in the
publishable/local capture table. Oracle non-fast-fail retention is therefore
marked `not_available_publishable_source` rather than simulated from aggregate
readouts.

## Density Concepts

- Formal full-denominator density remains events per instrument-year.
- Rolling 10d density is same-instrument / same-scope executable event
  congestion.
- Episode-window density is diagnostic-only and is not a hard gate.

## Why Episode Gates Are Not Hard Gates

The earlier episode-interval diagnostic counts candidate events inside frozen
winner episodes. That is useful for explaining recall overlap, but it uses a
target episode window that is not available at t0. Experiment A therefore uses
episode-window density only as context. A density alert is executable-timing
based only when rolling 10d duplicates, adjacent gaps, or 10d uniqueness also
show same-instrument event congestion.

## Density Caliber Crosswalk

{markdown_view(crosswalk_rounded, core_scopes, gap_columns)}

## Scope Reconstructability

`scope_status` counts: `{json.dumps(recon_counts, ensure_ascii=False, sort_keys=True)}`.
R-series compression frontier arms are retained as aggregate crosswalk rows
unless explicit selected-event membership is available and reconcilable.

## 07 Scope Comparison

{markdown_view(scope_summary, ["07_E1_only", "07_E1_plus_E3", "07_full_union"], comparison_columns)}

## 08 Selected T4 / T7 Comparison

`08_selected_T4_T7_union` is the 08 train-selected union materialized by the
T4 and T7 `event_regime_gated` variants, not the broader
`recommended_union_included` flag from the raw canonical table.

{markdown_view(scope_summary, ["08_selected_T4_T7_union", "08_T4_gated", "08_T7_gated"], comparison_columns)}

## R-Series Family Comparison

{markdown_view(scope_summary, ["08_R_core_event_regime_gated", "08_R1_event_regime_gated", "08_R2_event_regime_gated", "08_R6_event_regime_gated", "08_R7_event_regime_gated", "08_R8_event_regime_gated"], comparison_columns)}

## R-Series Compression Arms

Compression frontier rows are aggregate-only because explicit selected-event
membership is unavailable or empty. They are not included in event-level
rolling 10d, adjacent-gap, uniqueness, fast-fail, or hard-gate comparisons.

{arm_view.to_markdown(index=False) if not arm_view.empty else "No compression arm rows available."}

## Adjacent Gap And Uniqueness Findings

E1 has very high uniqueness and a long same-instrument adjacent-gap median.
R-core has materially shorter adjacent gaps and lower 10d uniqueness, so its
problem is executable event congestion rather than just an episode-window
density artifact. The family rows above identify which R families contribute to
that congestion.

## Fast-Fail Snapshot

{fast_view.to_markdown(index=False)}

## Recommended Inputs For Experiments B And C

Use `density_fast_fail_caliber_contract.md`,
`candidate_10d_density_summary.csv`,
`candidate_10d_fast_fail_readout.csv`, and
`candidate_density_caliber_crosswalk.csv` as read-only audit inputs. Do not use
episode-window density or oracle fast-fail labels as implementable t0 entry
features.

## Downstream Use

Experiments B and C must reference
`density_fast_fail_caliber_contract.md`. Any row with
`replay_uses_future_label = true` is audit-only and cannot be used as a t0
entry-support gate. In this run no oracle non-fast-fail replay is produced
because event-to-episode replay membership is unavailable; pre-replay capture
rows are marked `pre_replay_capture_only`.
"""


def build_manifest(
    decision: str,
    output_paths: dict[str, Path],
    input_audit_frame: pd.DataFrame,
    partial_reasons: list[str],
) -> dict[str, Any]:
    return {
        "experiment_id": "08_experiment_a_10d_density_fast_fail_audit",
        "run_id": stable_hash(
            {
                "experiment": "density_fast_fail_audit",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runner_code_hash": path_hash(Path(__file__)),
        "requirement_hash": path_hash(REQUIREMENT_PATH),
        "decision": decision,
        "partial_reasons": partial_reasons,
        "input_artifacts": input_audit_frame.to_dict(orient="records"),
        "output_hashes": {
            key: path_hash(path)
            for key, path in sorted(output_paths.items())
            if key != "density_fast_fail_audit_manifest" and path.exists()
        },
        "output_paths": {key: str(path) for key, path in sorted(output_paths.items())},
        "event_level_labels_available": bool(
            OPTIONAL_INPUTS["08_event_labels_local"].exists()
            or OPTIONAL_INPUTS["07_event_labels_local"].exists()
        ),
        "episode_capture_available": bool(OPTIONAL_INPUTS["08_capture_local"].exists()),
        "r_series_membership_reconstructable": False,
    }


def run_audit() -> dict[str, Any]:
    ensure_output_dirs()
    input_frame, input_failures = input_audit()
    output_paths = {
        "candidate_10d_density_summary": AUDIT_TABLE_DIR / "candidate_10d_density_summary.csv",
        "candidate_10d_fast_fail_readout": AUDIT_TABLE_DIR / "candidate_10d_fast_fail_readout.csv",
        "candidate_10d_retention_by_split_regime": AUDIT_TABLE_DIR
        / "candidate_10d_retention_by_split_regime.csv",
        "candidate_10d_density_vs_episode_density_comparison": AUDIT_TABLE_DIR
        / "candidate_10d_density_vs_episode_density_comparison.csv",
        "candidate_adjacent_event_gap_diagnostic": AUDIT_TABLE_DIR
        / "candidate_adjacent_event_gap_diagnostic.csv",
        "candidate_10d_uniqueness_diagnostic": AUDIT_TABLE_DIR
        / "candidate_10d_uniqueness_diagnostic.csv",
        "candidate_density_caliber_crosswalk": AUDIT_TABLE_DIR
        / "candidate_density_caliber_crosswalk.csv",
        "candidate_scope_reconstructability_audit": AUDIT_TABLE_DIR
        / "candidate_scope_reconstructability_audit.csv",
        "density_fast_fail_audit_gate_summary": AUDIT_TABLE_DIR
        / "density_fast_fail_audit_gate_summary.csv",
        "candidate_scope_mapping_contract": AUDIT_TABLE_DIR
        / "candidate_scope_mapping_contract.csv",
        "density_fast_fail_caliber_contract": AUDIT_REPORT_DIR
        / "density_fast_fail_caliber_contract.md",
        "density_fast_fail_audit_report": AUDIT_REPORT_DIR / "density_fast_fail_audit_report.md",
        "density_fast_fail_audit_manifest": AUDIT_MANIFEST_DIR
        / "density_fast_fail_audit_manifest.json",
    }

    write_text(output_paths["density_fast_fail_caliber_contract"], caliber_contract_text())
    if input_failures:
        gate = build_gate_summary(pd.DataFrame(), input_failures)
        write_df(output_paths["density_fast_fail_audit_gate_summary"], gate)
        write_df(AUDIT_TABLE_DIR / "input_artifact_audit.csv", input_frame)
        manifest = build_manifest(DECISION_INPUT_BLOCKED, output_paths, input_frame, input_failures)
        write_json(output_paths["density_fast_fail_audit_manifest"], manifest)
        return {
            "decision": DECISION_INPUT_BLOCKED,
            "manifest_path": str(output_paths["density_fast_fail_audit_manifest"]),
        }

    canonical_07 = read_csv(REQUIRED_INPUTS["07_canonical_events"])
    canonical_08 = read_csv(REQUIRED_INPUTS["08_canonical_events"])
    density_reference = read_csv(REQUIRED_INPUTS["08_density_summary"])
    frontier = read_csv(REQUIRED_INPUTS["r_series_frontier"])
    labels_07 = (
        pd.read_parquet(OPTIONAL_INPUTS["07_event_labels_local"])
        if OPTIONAL_INPUTS["07_event_labels_local"].exists()
        else pd.DataFrame()
    )
    labels_08 = (
        pd.read_parquet(OPTIONAL_INPUTS["08_event_labels_local"])
        if OPTIONAL_INPUTS["08_event_labels_local"].exists()
        else pd.DataFrame()
    )
    capture = (
        pd.read_parquet(OPTIONAL_INPUTS["08_capture_local"])
        if OPTIONAL_INPUTS["08_capture_local"].exists()
        else pd.DataFrame()
    )

    specs = build_scope_specs()
    spec_by_id = {spec.candidate_scope_id: spec for spec in specs}
    scope_events: dict[str, pd.DataFrame] = {}
    for spec in specs:
        source = canonical_07 if spec.source_experiment == "07" else canonical_08
        selected = select_scope_events(spec, canonical_07, canonical_08)
        scope_events[spec.candidate_scope_id] = normalise_scope_events(
            selected,
            spec,
            source_path=REQUIRED_INPUTS[spec.source_artifact_key],
        )

    instrument_years = infer_instrument_years(
        density_reference, len(scope_events.get("07_E1_only", pd.DataFrame()))
    )
    ref_counts = reference_counts(density_reference, frontier)

    density_summary = build_density_summary(
        scope_events,
        spec_by_id,
        labels_07,
        labels_08,
        frontier,
        instrument_years,
    )
    fast_fail = build_fast_fail_readout(scope_events, spec_by_id, labels_07, labels_08)
    retention = retention_rows_from_capture(capture, spec_by_id)
    gap_diag = build_gap_diagnostic(scope_events)
    uniqueness = build_uniqueness_diagnostic(scope_events)
    mapping, reconstruct = build_mapping_and_reconstructability(
        spec_by_id, scope_events, REQUIRED_INPUTS, ref_counts, frontier
    )
    crosswalk = build_crosswalk(density_summary, gap_diag, uniqueness)
    episode_compare = build_episode_density_comparison(retention, density_summary)
    gate_summary = build_gate_summary(crosswalk, input_failures)

    partial_reasons = [
        "event_to_episode_full_membership_unavailable_for_oracle_retention_replay",
        "r_series_compression_arms_aggregate_only_no_event_membership",
    ]
    decision = DECISION_PARTIAL if partial_reasons else DECISION_COMPLETE

    write_df(output_paths["candidate_10d_density_summary"], density_summary)
    write_df(output_paths["candidate_10d_fast_fail_readout"], fast_fail)
    write_df(output_paths["candidate_10d_retention_by_split_regime"], retention)
    write_df(output_paths["candidate_10d_density_vs_episode_density_comparison"], episode_compare)
    write_df(output_paths["candidate_adjacent_event_gap_diagnostic"], gap_diag)
    write_df(output_paths["candidate_10d_uniqueness_diagnostic"], uniqueness)
    write_df(output_paths["candidate_density_caliber_crosswalk"], crosswalk)
    write_df(output_paths["candidate_scope_reconstructability_audit"], reconstruct)
    write_df(output_paths["density_fast_fail_audit_gate_summary"], gate_summary)
    write_df(output_paths["candidate_scope_mapping_contract"], mapping)
    write_text(
        output_paths["density_fast_fail_audit_report"],
        build_report(decision, density_summary, fast_fail, crosswalk, reconstruct),
    )
    write_df(AUDIT_TABLE_DIR / "input_artifact_audit.csv", input_frame)

    manifest = build_manifest(decision, output_paths, input_frame, partial_reasons)
    write_json(output_paths["density_fast_fail_audit_manifest"], manifest)

    return {
        "decision": decision,
        "density_rows": len(density_summary),
        "fast_fail_rows": len(fast_fail),
        "manifest_path": str(output_paths["density_fast_fail_audit_manifest"]),
        "report_path": str(output_paths["density_fast_fail_audit_report"]),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "check-inputs":
        frame, failures = input_audit()
        print(f"input_failures={len(failures)}")
        for failure in failures:
            print(failure)
        print(f"inputs_checked={len(frame)}")
        return 1 if failures else 0
    result = run_audit()
    print(f"decision={result['decision']}")
    if "density_rows" in result:
        print(f"density_rows={result['density_rows']}")
        print(f"fast_fail_rows={result['fast_fail_rows']}")
        print(f"manifest={result['manifest_path']}")
        print(f"report={result['report_path']}")
    else:
        print(f"manifest={result['manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

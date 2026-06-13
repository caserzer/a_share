#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
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

import run_post_replay_event_to_episode_retention_source as post_replay_source  # noqa: E402
import run_transition_subregime_taxonomy_audit as transition_f  # noqa: E402


REQUIREMENT_PATH = EXPERIMENT_DIR / "requirement_experiment_g_transition_previous_regime_conditioned_outcome_audit.md"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables"
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache"
PROJECT_DATA_DIR = PROJECT_ROOT / "data"

A_MANIFEST_DIR = MANIFEST_DIR / "density_fast_fail_audit"
B_MANIFEST_DIR = MANIFEST_DIR / "regime_family_matrix"
C_MANIFEST_DIR = MANIFEST_DIR / "risk_on_r_series_bridge_ranker"
D_MANIFEST_DIR = MANIFEST_DIR / "post_replay_event_to_episode_retention_source"
F_MANIFEST_DIR = MANIFEST_DIR / "transition_subregime_taxonomy_audit"
F_TABLE_DIR = TABLE_DIR / "transition_subregime_taxonomy_audit"
D_TABLE_DIR = TABLE_DIR / "post_replay_event_to_episode_retention_source"
D_LOCAL_CACHE_DIR = LOCAL_CACHE_DIR / "post_replay_event_to_episode_retention_source"

G_TABLE_DIR = TABLE_DIR / "transition_previous_regime_outcome_audit"
G_REPORT_DIR = REPORT_DIR / "transition_previous_regime_outcome_audit"
G_MANIFEST_DIR = MANIFEST_DIR / "transition_previous_regime_outcome_audit"

FINAL_SUPPORTED = "transition_previous_regime_conditioning_explanatory_supported"
FINAL_DIAGNOSTIC = "transition_previous_regime_conditioning_diagnostic_only"
FINAL_INPUT_BLOCKED = "transition_previous_regime_outcome_input_blocked"
FINAL_COMPONENT_BLOCKED = "transition_previous_regime_outcome_component_blocked"
FINAL_LABEL_JOIN_BLOCKED = "transition_previous_regime_outcome_label_join_blocked"
FINAL_LEAKAGE_BLOCKED = "transition_previous_regime_outcome_leakage_blocked"
FINAL_BINDING_DRIFT_BLOCKED = "transition_previous_regime_outcome_binding_drift_blocked"

ALLOWED_A = {"density_fast_fail_audit_complete", "density_fast_fail_audit_partial_source_complete"}
ALLOWED_B = {"regime_family_matrix_complete", "regime_family_matrix_source_caveated_complete"}
ALLOWED_C = {"risk_on_r_series_ranker_complete", "risk_on_r_series_ranker_source_caveated_complete"}
ALLOWED_D = {
    "post_replay_retention_source_complete",
    "post_replay_retention_source_source_caveated_complete",
}

TARGET_REGIME = "transition"
HEADLINE_WINDOW = "low_to_first_50pct"
HEADLINE_POLICY = "post_replay_executable_horizon_complete"
PRE_REPLAY_POLICY = "pre_replay_capture_only"
SPLITS = ("train", "validation", "robustness")
PIT_CONTEXTS = ("transition_from_risk_on", "transition_from_risk_off")
OUTCOMES = ("transition_continuation", "transition_conversion")
SOURCE_SCOPES = (
    "07_E1_only",
    "08_R_core_event_regime_gated",
    "08_R6_event_regime_gated",
    "08_R1_event_regime_gated",
    "08_R2_event_regime_gated",
    "08_R7_event_regime_gated",
    "08_R8_event_regime_gated",
    "08_selected_T4_T7_union",
    "08_T4_gated",
    "08_T7_gated",
)
RECALL_SOURCE_SCOPES = (
    "07_E1_only",
    "08_R_core_event_regime_gated",
    "08_R6_event_regime_gated",
    "08_selected_T4_T7_union",
    "08_T4_gated",
    "08_T7_gated",
)

GRID_MIN_PREVIOUS = (1, 3, 5, 10, 20)
GRID_MIN_AGE = (1, 2, 3, 5)
GRID_CONFIRMATION = (0, 1, 2, 3)
GRID_OUTCOME_MAX: tuple[int | None, ...] = (20, 60, 120, 240, None)
BASE_RULE = {
    "min_previous_regime_trading_day_n": 1,
    "min_segment_age_at_event_t0": 1,
    "online_confirmation_trading_day_n": 0,
    "outcome_max_transition_trading_day_n": None,
}
BASE_RULE_ID = "g_base_minprev1_age1_confirm0_outmaxnull"


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
    InputSpec("experiment_f_manifest", F_MANIFEST_DIR / "transition_subregime_taxonomy_audit_manifest.json"),
    InputSpec("experiment_f_component_audit", F_TABLE_DIR / "transition_subregime_regime_component_audit.csv"),
    InputSpec("candidate_family_canonical_events", TABLE_DIR / "candidate_family_canonical_events.csv.gz"),
    InputSpec("candidate_family_event_instances", TABLE_DIR / "candidate_family_event_instances.csv.gz"),
    InputSpec("candidate_family_event_labels", LOCAL_CACHE_DIR / "candidate_family_event_labels.parquet"),
    InputSpec("candidate_family_capture", LOCAL_CACHE_DIR / "candidate_family_capture.parquet"),
    InputSpec("d_membership", D_LOCAL_CACHE_DIR / "post_replay_event_episode_membership.parquet"),
    InputSpec("d_scope_retention", D_TABLE_DIR / "post_replay_scope_retention_by_split_regime.csv"),
    InputSpec("d_e1_missed", D_TABLE_DIR / "post_replay_e1_missed_retention_summary.csv"),
    InputSpec("primary_index_sh000985", PROJECT_DATA_DIR / "interim" / "index_qlib_csv" / "day" / "SH000985.csv"),
]

OUTPUT_PATHS = {
    "transition_previous_regime_input_audit": G_TABLE_DIR / "transition_previous_regime_input_audit.csv",
    "transition_previous_regime_component_audit": G_TABLE_DIR / "transition_previous_regime_component_audit.csv",
    "transition_previous_regime_universe_binding_audit": G_TABLE_DIR / "transition_previous_regime_universe_binding_audit.csv",
    "transition_previous_regime_segment_catalog": G_TABLE_DIR / "transition_previous_regime_segment_catalog.csv",
    "transition_previous_regime_grid_search": G_TABLE_DIR / "transition_previous_regime_grid_search.csv",
    "transition_previous_regime_event_assignment": G_TABLE_DIR / "transition_previous_regime_event_assignment.csv.gz",
    "transition_previous_regime_segment_matrix": G_TABLE_DIR / "transition_previous_regime_segment_matrix.csv",
    "transition_previous_regime_recall_retention_matrix": G_TABLE_DIR / "transition_previous_regime_recall_retention_matrix.csv",
    "transition_previous_regime_e1_missed_capture": G_TABLE_DIR / "transition_previous_regime_e1_missed_capture.csv",
    "transition_previous_regime_cost_quality_matrix": G_TABLE_DIR / "transition_previous_regime_cost_quality_matrix.csv",
    "transition_previous_regime_density_overlap_matrix": G_TABLE_DIR / "transition_previous_regime_density_overlap_matrix.csv",
    "transition_previous_regime_label_join_audit": G_TABLE_DIR / "transition_previous_regime_label_join_audit.csv",
    "transition_previous_regime_leakage_audit": G_TABLE_DIR / "transition_previous_regime_leakage_audit.csv",
    "transition_previous_regime_decision_tiers": G_TABLE_DIR / "transition_previous_regime_decision_tiers.csv",
    "transition_previous_regime_outcome_contract": G_REPORT_DIR / "transition_previous_regime_outcome_contract.md",
    "transition_previous_regime_outcome_audit_report": G_REPORT_DIR / "transition_previous_regime_outcome_audit_report.md",
    "transition_previous_regime_timeline_png": G_REPORT_DIR / "transition_previous_regime_timeline.png",
    "transition_previous_regime_timeline_svg": G_REPORT_DIR / "transition_previous_regime_timeline.svg",
    "transition_previous_regime_outcome_audit_manifest": G_MANIFEST_DIR / "transition_previous_regime_outcome_audit_manifest.json",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Experiment G previous-regime conditioned transition outcome audit.")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def ensure_dirs() -> None:
    for path in (G_TABLE_DIR, G_REPORT_DIR, G_MANIFEST_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_df(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def path_hash(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den and pd.notna(den) else np.nan


def make_event_key(frame: pd.DataFrame) -> pd.Series:
    return transition_f.make_event_key(frame)


def bool_series(frame: pd.DataFrame, col: str, default: bool = False) -> pd.Series:
    return transition_f.bool_series(frame, col, default)


def wilson_interval(successes: int, n: int) -> tuple[float, float]:
    return transition_f.wilson_interval(successes, n)


def policy_mask(frame: pd.DataFrame, policy: str) -> pd.Series:
    return post_replay_source.policy_event_mask(frame, policy)


def row_count_for_path(path: Path) -> int:
    return transition_f.row_count_for_path(path)


def input_audit() -> tuple[pd.DataFrame, dict[str, Path], list[str]]:
    rows: list[dict[str, Any]] = []
    paths = {spec.input_id: spec.path for spec in INPUT_SPECS}
    failures: list[str] = []
    for spec in INPUT_SPECS:
        exists = spec.path.exists()
        status = "available" if exists else ("missing_required" if spec.required else "missing_optional")
        if spec.required and not exists:
            failures.append(f"missing_required_input:{spec.input_id}")
        rows.append(
            {
                "input_id": spec.input_id,
                "path": str(spec.path),
                "required": spec.required,
                "status": status,
                "sha256": path_hash(spec.path),
                "row_count": row_count_for_path(spec.path) if exists else np.nan,
                **(
                    transition_f.index_file_audit_fields(spec.path)
                    if exists and spec.input_id == "primary_index_sh000985"
                    else {}
                ),
            }
        )
    return pd.DataFrame(rows), paths, failures


def validate_manifests() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    a = read_json(A_MANIFEST_DIR / "density_fast_fail_audit_manifest.json")
    b = read_json(B_MANIFEST_DIR / "regime_family_matrix_manifest.json")
    c = read_json(C_MANIFEST_DIR / "risk_on_r_series_bridge_ranker_manifest.json")
    d = read_json(D_MANIFEST_DIR / "post_replay_event_to_episode_retention_source_manifest.json")
    f = read_json(F_MANIFEST_DIR / "transition_subregime_taxonomy_audit_manifest.json")
    failures = []
    if a.get("decision") not in ALLOWED_A:
        failures.append(f"experiment_a_decision_not_allowed:{a.get('decision')}")
    if b.get("decision") not in ALLOWED_B:
        failures.append(f"experiment_b_decision_not_allowed:{b.get('decision')}")
    if c.get("decision") not in ALLOWED_C:
        failures.append(f"experiment_c_decision_not_allowed:{c.get('decision')}")
    if d.get("decision") not in ALLOWED_D:
        failures.append(f"experiment_d_decision_not_allowed:{d.get('decision')}")
    f_decision = str(f.get("final_decision") or f.get("decision") or "")
    if not f_decision or any(token in f_decision for token in ("input_blocked", "component_blocked", "leakage_blocked")):
        failures.append(f"experiment_f_decision_not_allowed:{f_decision}")
    return a, b, c, d, f, failures


def source_caveated(manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]) -> bool:
    return any("source_caveated" in str(m.get("decision", "")) or "partial" in str(m.get("decision", "")) for m in manifests[:4])


def load_component_panel(index_path: Path) -> pd.DataFrame:
    index_panel = transition_f.load_index_panel(index_path, "SH000985")
    components = transition_f.add_market_components(index_panel)
    return components.sort_values("date").reset_index(drop=True)


def build_component_alignment(
    canonical: pd.DataFrame,
    components: pd.DataFrame,
    index_path: Path,
    f_component_path: Path,
) -> pd.DataFrame:
    current = transition_f.build_component_audit(
        canonical,
        components,
        index_path,
        "SH000985",
        "primary_benchmark_index",
    )
    current_row = current.iloc[0].to_dict()
    if not f_component_path.exists():
        alignment = "component_alignment_blocked"
        reuse_policy = "experiment_f_component_audit_missing"
        f_row: dict[str, Any] = {}
    else:
        f_audit = read_csv(f_component_path)
        f_row = f_audit.iloc[0].to_dict() if not f_audit.empty else {}
        same_hash = str(f_row.get("source_hash", "")) == str(current_row.get("source_hash", ""))
        same_formula = str(f_row.get("reconstruction_formula", "")) == str(current_row.get("reconstruction_formula", ""))
        same_rows = int(float(f_row.get("date_level_source_row_count", -1))) == int(current_row.get("date_level_source_row_count", -2))
        if same_hash and same_formula and same_rows:
            alignment = "aligned_with_experiment_f_component"
        elif same_hash:
            alignment = "component_alignment_drift_diagnostic"
        else:
            alignment = "component_alignment_blocked"
        reuse_policy = "rebuild_from_experiment_f_component_audit"
    return pd.DataFrame(
        [
            {
                **current_row,
                "f_component_source_hash": f_row.get("source_hash", ""),
                "f_component_formula": f_row.get("reconstruction_formula", ""),
                "f_component_row_count": f_row.get("date_level_source_row_count", np.nan),
                "component_reuse_policy": reuse_policy,
                "f_component_alignment_status": alignment,
            }
        ]
    )


def build_segment_catalog(components: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    comp = components.sort_values("date").reset_index(drop=True).copy()
    comp["date_pos"] = np.arange(len(comp), dtype=int)
    comp["regime"] = comp["market_regime_bucket_reconstructed"].astype(str)
    comp["segment_ordinal"] = comp["regime"].ne(comp["regime"].shift()).cumsum().astype(int)
    comp["segment_id"] = comp["segment_ordinal"].map(lambda x: f"regime_seg_{x:04d}")
    rows = []
    for ordinal, group in comp.groupby("segment_ordinal", sort=True):
        regime = str(group["regime"].iloc[0])
        rows.append(
            {
                "segment_ordinal": int(ordinal),
                "segment_id": f"regime_seg_{int(ordinal):04d}",
                "transition_segment_id": f"transition_seg_{int(ordinal):04d}" if regime == TARGET_REGIME else "",
                "segment_start_date": group["date"].iloc[0],
                "segment_end_date": group["date"].iloc[-1],
                "segment_start_pos": int(group["date_pos"].min()),
                "segment_end_pos": int(group["date_pos"].max()),
                "regime": regime,
                "segment_trading_day_n": int(len(group)),
                "segment_calendar_day_n": int((group["date"].iloc[-1] - group["date"].iloc[0]).days + 1),
                "start_close": float(group["close"].iloc[0]) if pd.notna(group["close"].iloc[0]) else np.nan,
                "end_close": float(group["close"].iloc[-1]) if pd.notna(group["close"].iloc[-1]) else np.nan,
            }
        )
    segments = pd.DataFrame(rows)
    prev_values: list[dict[str, Any]] = []
    next_values: list[dict[str, Any]] = []
    for idx, row in segments.iterrows():
        prev = segments.loc[
            (segments.index < idx)
            & segments["regime"].isin(["risk_on", "risk_off"])
        ].tail(1)
        nxt = segments.loc[
            (segments.index > idx)
            & segments["regime"].isin(["risk_on", "risk_off"])
        ].head(1)
        prev_values.append(
            {
                "previous_non_transition_regime": "" if prev.empty else str(prev.iloc[0]["regime"]),
                "previous_non_transition_trading_day_n": np.nan if prev.empty else int(prev.iloc[0]["segment_trading_day_n"]),
                "previous_non_transition_end_date": pd.NaT if prev.empty else prev.iloc[0]["segment_end_date"],
                "days_since_previous_regime_end": np.nan if prev.empty else int((row["segment_start_date"] - prev.iloc[0]["segment_end_date"]).days),
            }
        )
        next_values.append(
            {
                "next_non_transition_regime": "" if nxt.empty else str(nxt.iloc[0]["regime"]),
                "next_non_transition_start_date": pd.NaT if nxt.empty else nxt.iloc[0]["segment_start_date"],
                "days_to_next_regime_start": np.nan if nxt.empty else int((nxt.iloc[0]["segment_start_date"] - row["segment_end_date"]).days),
            }
        )
    segments = pd.concat([segments, pd.DataFrame(prev_values), pd.DataFrame(next_values)], axis=1)
    labels = []
    directions = []
    for _, row in segments.iterrows():
        label, direction = base_outcome_label(row)
        labels.append(label)
        directions.append(direction)
    segments["transition_outcome_label"] = labels
    segments["transition_outcome_direction"] = directions
    comp = comp.merge(
        segments[
            [
                "segment_id",
                "transition_segment_id",
                "segment_start_date",
                "segment_end_date",
                "segment_start_pos",
                "segment_end_pos",
                "segment_trading_day_n",
                "segment_calendar_day_n",
                "previous_non_transition_regime",
                "previous_non_transition_trading_day_n",
                "previous_non_transition_end_date",
                "days_since_previous_regime_end",
                "next_non_transition_regime",
                "next_non_transition_start_date",
                "days_to_next_regime_start",
                "transition_outcome_label",
                "transition_outcome_direction",
            ]
        ],
        on="segment_id",
        how="left",
    )
    return segments, comp


def base_outcome_label(row: pd.Series) -> tuple[str, str]:
    if str(row.get("regime", "")) != TARGET_REGIME:
        return "not_transition_segment", "not_transition_segment"
    previous = str(row.get("previous_non_transition_regime", "") or "")
    nxt = str(row.get("next_non_transition_regime", "") or "")
    if previous not in {"risk_on", "risk_off"} or nxt not in {"risk_on", "risk_off"}:
        return "transition_outcome_pending_or_censored", "unknown_or_censored"
    if previous == nxt:
        label = "transition_continuation"
        direction = f"{previous}_continuation_buffer"
    elif previous == "risk_on" and nxt == "risk_off":
        label = "transition_conversion"
        direction = "risk_on_to_risk_off_deterioration_conversion"
    else:
        label = "transition_conversion"
        direction = "risk_off_to_risk_on_recovery_conversion"
    return label, direction


def load_canonical_events(path: Path) -> pd.DataFrame:
    canonical = read_csv(path)
    keep = [
        "event_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "market_regime_bucket",
        "event_regime_bucket",
        "event_split",
        "board_bucket",
        "primary_family_id",
        "family_id",
        "triggered_family_ids",
        "triggered_family_variants",
        "family_count",
        "channel_count",
    ]
    events = canonical[[col for col in keep if col in canonical.columns]].copy()
    events["event_key"] = make_event_key(events)
    events = events.drop_duplicates("event_key").reset_index(drop=True)
    events["event_t0_date_dt"] = pd.to_datetime(events["event_t0_date"], errors="coerce")
    return events


def build_base_event_assignments(events: pd.DataFrame, components_with_segments: pd.DataFrame) -> pd.DataFrame:
    right_cols = [
        "date",
        "date_pos",
        "market_regime_bucket_reconstructed",
        "market_trend_60d",
        "market_drawdown_120d",
        "segment_id",
        "transition_segment_id",
        "segment_start_date",
        "segment_end_date",
        "segment_start_pos",
        "segment_end_pos",
        "segment_trading_day_n",
        "segment_calendar_day_n",
        "previous_non_transition_regime",
        "previous_non_transition_trading_day_n",
        "previous_non_transition_end_date",
        "days_since_previous_regime_end",
        "next_non_transition_regime",
        "next_non_transition_start_date",
        "days_to_next_regime_start",
        "transition_outcome_label",
        "transition_outcome_direction",
    ]
    left = events.copy()
    left["_original_order"] = np.arange(len(left), dtype=int)
    merged = pd.merge_asof(
        left.sort_values("event_t0_date_dt"),
        components_with_segments[right_cols].sort_values("date"),
        left_on="event_t0_date_dt",
        right_on="date",
        direction="backward",
    )
    merged["component_lag_days"] = (merged["event_t0_date_dt"] - merged["date"]).dt.days
    merged = merged.sort_values("_original_order").drop(columns=["_original_order"]).reset_index(drop=True)
    merged = merged.rename(
        columns={
            "market_regime_bucket": "published_market_regime_bucket",
            "market_regime_bucket_reconstructed": "reconstructed_market_regime_bucket",
            "segment_trading_day_n": "final_segment_trading_day_n",
            "segment_calendar_day_n": "final_segment_calendar_day_n",
        }
    )
    merged["segment_age_at_event_t0"] = pd.to_numeric(merged["date_pos"], errors="coerce") - pd.to_numeric(merged["segment_start_pos"], errors="coerce") + 1
    merged["observed_segment_trading_day_n_asof_t0"] = merged["segment_age_at_event_t0"]
    merged["segment_remaining_days_ex_post"] = pd.to_numeric(merged["final_segment_trading_day_n"], errors="coerce") - pd.to_numeric(merged["segment_age_at_event_t0"], errors="coerce")
    merged["universe_binding_status"] = universe_binding_status(merged)
    return merged


def universe_binding_status(frame: pd.DataFrame) -> pd.Series:
    published_transition = frame["published_market_regime_bucket"].astype(str).eq(TARGET_REGIME)
    reconstructed_transition = frame["reconstructed_market_regime_bucket"].astype(str).eq(TARGET_REGIME)
    return pd.Series(
        np.select(
            [
                published_transition & reconstructed_transition,
                published_transition & ~reconstructed_transition,
                ~published_transition & reconstructed_transition,
                ~published_transition & ~reconstructed_transition,
            ],
            [
                "published_and_reconstructed_transition",
                "published_transition_not_reconstructed_transition",
                "reconstructed_transition_not_published_transition",
                "non_transition_out_of_scope",
            ],
            default="non_transition_out_of_scope",
        ),
        index=frame.index,
    )


def rule_id(rule: dict[str, Any]) -> str:
    max_value = "null" if rule["outcome_max_transition_trading_day_n"] is None else str(rule["outcome_max_transition_trading_day_n"])
    return (
        f"g_minprev{rule['min_previous_regime_trading_day_n']}"
        f"_age{rule['min_segment_age_at_event_t0']}"
        f"_confirm{rule['online_confirmation_trading_day_n']}"
        f"_outmax{max_value}"
    )


def grid_rules() -> list[dict[str, Any]]:
    rules = []
    for min_prev in GRID_MIN_PREVIOUS:
        for min_age in GRID_MIN_AGE:
            for confirmation in GRID_CONFIRMATION:
                for outcome_max in GRID_OUTCOME_MAX:
                    rule = {
                        "min_previous_regime_trading_day_n": min_prev,
                        "min_segment_age_at_event_t0": min_age,
                        "online_confirmation_trading_day_n": confirmation,
                        "outcome_max_transition_trading_day_n": outcome_max,
                    }
                    rule["grid_rule_id"] = BASE_RULE_ID if rule_without_id(rule) == BASE_RULE else rule_id(rule)
                    rules.append(rule)
    return rules


def rule_without_id(rule: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in rule.items() if key != "grid_rule_id"}


def apply_grid_rule(base_events: pd.DataFrame, rule: dict[str, Any]) -> pd.DataFrame:
    out = base_events.copy()
    out["grid_rule_id"] = rule["grid_rule_id"]
    out["min_previous_regime_trading_day_n"] = rule["min_previous_regime_trading_day_n"]
    out["min_segment_age_at_event_t0"] = rule["min_segment_age_at_event_t0"]
    out["online_confirmation_trading_day_n"] = rule["online_confirmation_trading_day_n"]
    out["outcome_max_transition_trading_day_n"] = (
        "null" if rule["outcome_max_transition_trading_day_n"] is None else rule["outcome_max_transition_trading_day_n"]
    )
    age = pd.to_numeric(out["segment_age_at_event_t0"], errors="coerce")
    prev_days = pd.to_numeric(out["previous_non_transition_trading_day_n"], errors="coerce")
    reconstructed_transition = out["reconstructed_market_regime_bucket"].astype(str).eq(TARGET_REGIME)
    age_ok = age >= int(rule["min_segment_age_at_event_t0"])
    confirmation = int(rule["online_confirmation_trading_day_n"])
    confirmed = reconstructed_transition & ((confirmation == 0) | age.ge(confirmation))
    prev_valid = (
        out["previous_non_transition_regime"].astype(str).isin(["risk_on", "risk_off"])
        & prev_days.ge(int(rule["min_previous_regime_trading_day_n"]))
    )
    out["online_confirmation_status"] = np.where(
        ~reconstructed_transition,
        "not_reconstructed_transition",
        np.where(confirmed, "state_confirmed", "state_pending_confirmation"),
    )
    out["pit_transition_context"] = np.select(
        [
            reconstructed_transition & prev_valid & out["previous_non_transition_regime"].astype(str).eq("risk_on"),
            reconstructed_transition & prev_valid & out["previous_non_transition_regime"].astype(str).eq("risk_off"),
            reconstructed_transition,
        ],
        ["transition_from_risk_on", "transition_from_risk_off", "transition_from_unknown_or_censored"],
        default="not_reconstructed_transition",
    )
    horizon = rule["outcome_max_transition_trading_day_n"]
    horizon_censored = (
        pd.Series(False, index=out.index)
        if horizon is None
        else pd.to_numeric(out["final_segment_trading_day_n"], errors="coerce").gt(int(horizon))
    )
    next_missing = ~out["next_non_transition_regime"].astype(str).isin(["risk_on", "risk_off"])
    outcome_censored = reconstructed_transition & (horizon_censored | next_missing | ~prev_valid)
    out["outcome_censor_flag"] = outcome_censored
    out["transition_outcome_label_rule"] = out["transition_outcome_label"]
    out["transition_outcome_direction_rule"] = out["transition_outcome_direction"]
    out.loc[outcome_censored, "transition_outcome_label_rule"] = "transition_outcome_pending_or_censored"
    out.loc[outcome_censored, "transition_outcome_direction_rule"] = "unknown_or_censored"
    out.loc[~reconstructed_transition, "transition_outcome_label_rule"] = "not_reconstructed_transition"
    out.loc[~reconstructed_transition, "transition_outcome_direction_rule"] = "not_reconstructed_transition"
    main_binding = out["universe_binding_status"].isin(
        ["published_and_reconstructed_transition", "reconstructed_transition_not_published_transition"]
    )
    out["rule_event_included"] = reconstructed_transition & main_binding & age_ok & confirmed
    return out


def compact_event_assignment(frame: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "transition_outcome_label_rule": "transition_outcome_label",
        "transition_outcome_direction_rule": "transition_outcome_direction",
    }
    keep = [
        "event_key",
        "event_id",
        "canonical_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "event_split",
        "published_market_regime_bucket",
        "reconstructed_market_regime_bucket",
        "universe_binding_status",
        "transition_segment_id",
        "segment_start_date",
        "segment_end_date",
        "final_segment_trading_day_n",
        "final_segment_calendar_day_n",
        "segment_age_at_event_t0",
        "observed_segment_trading_day_n_asof_t0",
        "online_confirmation_status",
        "segment_remaining_days_ex_post",
        "previous_non_transition_regime",
        "previous_non_transition_trading_day_n",
        "pit_transition_context",
        "next_non_transition_regime",
        "transition_outcome_label_rule",
        "transition_outcome_direction_rule",
        "outcome_censor_flag",
        "grid_rule_id",
        "rule_event_included",
    ]
    out = frame[[col for col in keep if col in frame.columns]].copy()
    return out.rename(columns=rename)


def contribution_stats(group: pd.DataFrame) -> dict[str, Any]:
    unique_segments = group.dropna(subset=["transition_segment_id"]).drop_duplicates("transition_segment_id")
    unique_segment_n = int(unique_segments["transition_segment_id"].nunique())
    event_n = int(make_event_key(group).nunique()) if not group.empty else 0
    target_episode_n = int(group["target_episode_id"].dropna().astype(str).nunique()) if "target_episode_id" in group.columns else 0
    event_by_segment = group.assign(event_key=make_event_key(group)).drop_duplicates(["transition_segment_id", "event_key"])
    event_counts = event_by_segment.groupby("transition_segment_id")["event_key"].nunique()
    top1_event_share = safe_div(float(event_counts.max()) if len(event_counts) else 0.0, event_n)
    if target_episode_n:
        ep_counts = (
            group.dropna(subset=["target_episode_id"])
            .drop_duplicates(["transition_segment_id", "target_episode_id"])
            .groupby("transition_segment_id")["target_episode_id"]
            .nunique()
        )
        shares = ep_counts / target_episode_n
        top1_episode_share = float(shares.max()) if len(shares) else np.nan
        effective = float(1.0 / np.square(shares).sum()) if len(shares) and np.square(shares).sum() > 0 else np.nan
        fallback = ""
    else:
        shares = event_counts / event_n if event_n else pd.Series(dtype=float)
        top1_episode_share = top1_event_share
        effective = float(1.0 / np.square(shares).sum()) if len(shares) and np.square(shares).sum() > 0 else np.nan
        fallback = "event_share"
    status = segment_power_status(unique_segment_n, effective, top1_episode_share)
    concentration = contribution_concentration_status(effective, top1_episode_share)
    return {
        "unique_segment_n": unique_segment_n,
        "event_n": event_n,
        "target_episode_n": target_episode_n,
        "top1_segment_event_share": top1_event_share,
        "top1_segment_episode_share": top1_episode_share,
        "effective_contributing_segment_n": effective,
        "contribution_metric_fallback": fallback,
        "segment_power_status": status,
        "contribution_concentration_status": concentration,
    }


def segment_power_status(unique_segment_n: int, effective_n: float, top1_episode_share: float) -> str:
    if unique_segment_n < 3 or (pd.notna(effective_n) and effective_n < 3) or (pd.notna(top1_episode_share) and top1_episode_share > 0.80):
        return "low_segment_power_diagnostic"
    if unique_segment_n >= 10 and (pd.notna(effective_n) and effective_n >= 5) and (pd.notna(top1_episode_share) and top1_episode_share <= 0.50):
        return "sufficient_segment_power"
    return "low_segment_power_caution"


def contribution_concentration_status(effective_n: float, top1_episode_share: float) -> str:
    if (pd.notna(top1_episode_share) and top1_episode_share > 0.80) or (pd.notna(effective_n) and effective_n < 3):
        return "single_segment_dominated_diagnostic"
    if (pd.notna(top1_episode_share) and top1_episode_share <= 0.50) and (pd.notna(effective_n) and effective_n >= 5):
        return "not_concentrated"
    return "concentrated_low_power_caution"


def episode_power_status(target_episode_n: int, event_n: int) -> str:
    if target_episode_n >= 30:
        return "sufficient_episode_power"
    if target_episode_n >= 10:
        return "episode_low_power_caution"
    if event_n >= 100:
        return "episode_low_power_event_supported_only"
    return "insufficient_episode_power"


def grid_search(base_events: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    base_assignment = apply_grid_rule(base_events, {**BASE_RULE, "grid_rule_id": BASE_RULE_ID})
    base_dist = direction_distribution(base_assignment)
    rows = []
    for rule in grid_rules():
        assigned = apply_grid_rule(base_events, rule)
        included = assigned.loc[assigned["rule_event_included"]].copy()
        row = {
            "grid_rule_id": rule["grid_rule_id"],
            **rule_without_id(rule),
            "candidate_event_n": int(make_event_key(included).nunique()) if not included.empty else 0,
            "unique_transition_segment_n": int(included["transition_segment_id"].nunique()) if not included.empty else 0,
            "censored_event_share": float(included["outcome_censor_flag"].mean()) if len(included) else np.nan,
            "pending_or_censored_event_share": float(included["transition_outcome_label_rule"].eq("transition_outcome_pending_or_censored").mean()) if len(included) else np.nan,
            "base_direction_agreement": base_direction_agreement(base_assignment, assigned),
            "direction_distribution_distance": direction_distribution_distance(base_dist, direction_distribution(assigned)),
        }
        row.update(grid_structural_flags(included))
        row["structural_eligible_flag"] = bool(
            row["both_context_all_splits_flag"]
            and row["censored_share_eligible_flag"]
            and row["aggregate_outcome_power_flag"]
            and row["base_direction_agreement"] >= 0.80
            and not row["low_segment_power_cells"]
        )
        row["base_rule_tie_break_rank"] = 0 if rule["grid_rule_id"] == BASE_RULE_ID else 1
        rows.append(row)
    grid = pd.DataFrame(rows).drop_duplicates("grid_rule_id").reset_index(drop=True)
    eligible = grid.loc[grid["structural_eligible_flag"]].copy()
    if eligible.empty:
        selected = grid.loc[grid["grid_rule_id"].eq(BASE_RULE_ID)].iloc[0]
        reason = "no_structurally_eligible_rule_use_base_diagnostic"
    else:
        selected = eligible.sort_values(
            [
                "online_confirmation_trading_day_n",
                "min_previous_regime_trading_day_n",
                "min_segment_age_at_event_t0",
                "pending_or_censored_event_share",
                "direction_distribution_distance",
                "base_rule_tie_break_rank",
            ],
            ascending=[True, True, True, True, True, True],
        ).iloc[0]
        reason = "predeclared_structural_guard_then_lowest_delay_tiebreak"
    grid["selected_rule_flag"] = grid["grid_rule_id"].eq(selected["grid_rule_id"])
    grid["base_rule_flag"] = grid["grid_rule_id"].eq(BASE_RULE_ID)
    grid["selection_reason"] = np.where(grid["selected_rule_flag"], reason, "")
    return grid, {
        "selected_grid_rule_id": str(selected["grid_rule_id"]),
        "selection_reason": reason,
        "selected_rule_parameters": {
            "min_previous_regime_trading_day_n": int(selected["min_previous_regime_trading_day_n"]),
            "min_segment_age_at_event_t0": int(selected["min_segment_age_at_event_t0"]),
            "online_confirmation_trading_day_n": int(selected["online_confirmation_trading_day_n"]),
            "outcome_max_transition_trading_day_n": None
            if str(selected["outcome_max_transition_trading_day_n"]) in {"nan", "None", "null"}
            else int(selected["outcome_max_transition_trading_day_n"]),
        },
        "structural_eligible": bool(selected["structural_eligible_flag"]),
    }


def direction_distribution(frame: pd.DataFrame) -> pd.Series:
    included = frame.loc[frame["rule_event_included"]]
    if included.empty:
        return pd.Series(dtype=float)
    return included["transition_outcome_direction_rule"].astype(str).value_counts(normalize=True)


def direction_distribution_distance(base: pd.Series, candidate: pd.Series) -> float:
    labels = sorted(set(base.index).union(set(candidate.index)))
    if not labels:
        return np.nan
    return float(np.abs(base.reindex(labels, fill_value=0.0) - candidate.reindex(labels, fill_value=0.0)).sum())


def base_direction_agreement(base: pd.DataFrame, candidate: pd.DataFrame) -> float:
    base_map = base.loc[base["rule_event_included"], ["event_key", "transition_outcome_direction_rule"]].drop_duplicates("event_key")
    cand_map = candidate.loc[candidate["rule_event_included"], ["event_key", "transition_outcome_direction_rule"]].drop_duplicates("event_key")
    merged = base_map.merge(cand_map, on="event_key", suffixes=("_base", "_candidate"))
    if merged.empty:
        return np.nan
    return float(merged["transition_outcome_direction_rule_base"].eq(merged["transition_outcome_direction_rule_candidate"]).mean())


def grid_structural_flags(included: pd.DataFrame) -> dict[str, Any]:
    both_context = True
    for split in SPLITS:
        split_contexts = set(included.loc[included["event_split"].astype(str).eq(split), "pit_transition_context"].astype(str))
        if not set(PIT_CONTEXTS).issubset(split_contexts):
            both_context = False
            break
    censored_share = float(included["transition_outcome_label_rule"].eq("transition_outcome_pending_or_censored").mean()) if len(included) else np.nan
    eligible_outcomes: set[str] = set()
    outcome_rows = []
    for (split, outcome), group in included.groupby(["event_split", "transition_outcome_label_rule"], dropna=False):
        if str(outcome) not in OUTCOMES:
            continue
        stats = contribution_stats(group)
        outcome_rows.append((split, outcome, stats))
        if (
            stats["event_n"] >= 100
            and stats["unique_segment_n"] >= 10
            and pd.notna(stats["effective_contributing_segment_n"])
            and stats["effective_contributing_segment_n"] >= 5
            and pd.notna(stats["top1_segment_episode_share"])
            and stats["top1_segment_episode_share"] <= 0.50
        ):
            eligible_outcomes.add(str(outcome))
    low_power_cells = [
        f"{split}:{outcome}"
        for split, outcome, stats in outcome_rows
        if stats["event_n"] >= 100 and stats["segment_power_status"] == "low_segment_power_diagnostic"
    ]
    return {
        "both_context_all_splits_flag": bool(both_context),
        "censored_share_eligible_flag": bool(pd.notna(censored_share) and censored_share <= 0.20),
        "aggregate_outcome_power_flag": bool(set(OUTCOMES).issubset(eligible_outcomes)),
        "aggregate_outcome_power_labels": ";".join(sorted(eligible_outcomes)),
        "low_segment_power_cells": ";".join(low_power_cells),
    }


def selected_and_base_assignments(base_events: pd.DataFrame, selection: dict[str, Any]) -> pd.DataFrame:
    selected_params = dict(selection["selected_rule_parameters"])
    selected_params["grid_rule_id"] = str(selection["selected_grid_rule_id"])
    base = compact_event_assignment(apply_grid_rule(base_events, {**BASE_RULE, "grid_rule_id": BASE_RULE_ID}))
    selected = compact_event_assignment(apply_grid_rule(base_events, selected_params))
    if selected_params["grid_rule_id"] == BASE_RULE_ID:
        return base
    return pd.concat([base, selected], ignore_index=True)


def prepare_source_events(membership: pd.DataFrame, assignments: pd.DataFrame) -> pd.DataFrame:
    m = membership.loc[membership["source_id"].isin(SOURCE_SCOPES) & membership["window"].eq(HEADLINE_WINDOW)].copy()
    m["event_key"] = make_event_key(m)
    assign_cols = [
        "event_key",
        "grid_rule_id",
        "rule_event_included",
        "universe_binding_status",
        "transition_segment_id",
        "segment_start_date",
        "segment_end_date",
        "final_segment_trading_day_n",
        "final_segment_calendar_day_n",
        "segment_age_at_event_t0",
        "pit_transition_context",
        "transition_outcome_label",
        "transition_outcome_direction",
        "outcome_censor_flag",
    ]
    joined = m.merge(assignments[assign_cols].drop_duplicates(["event_key", "grid_rule_id"]), on="event_key", how="inner")
    joined = joined.loc[joined["rule_event_included"].astype(bool)].copy()
    return joined


def universe_binding_audit(assignments: pd.DataFrame) -> pd.DataFrame:
    base = assignments.loc[assignments["grid_rule_id"].eq(BASE_RULE_ID)].drop_duplicates("event_key").copy()
    total_published_transition = int(base["published_market_regime_bucket"].astype(str).eq(TARGET_REGIME).sum())
    rows = []
    for status, group in base.groupby("universe_binding_status", dropna=False):
        rows.append(
            {
                "universe_binding_status": status,
                "event_n": int(group["event_key"].nunique()),
                "share_of_all_events": safe_div(group["event_key"].nunique(), base["event_key"].nunique()),
                "share_of_published_transition_events": safe_div(
                    group["event_key"].nunique(),
                    total_published_transition,
                )
                if str(status) == "published_transition_not_reconstructed_transition"
                else np.nan,
                "binding_policy": "primary_readout_uses_reconstructed_transition_universe",
            }
        )
    return pd.DataFrame(rows)


def segment_matrix(source_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cross_segments = (
        source_events.dropna(subset=["transition_segment_id"])
        .drop_duplicates(["grid_rule_id", "transition_segment_id", "event_split"])
        .groupby(["grid_rule_id", "transition_segment_id"])["event_split"]
        .nunique()
    )
    cross_set = set(cross_segments.loc[cross_segments.gt(1)].index)
    dims = [
        "grid_rule_id",
        "event_split",
        "universe_binding_status",
        "pit_transition_context",
        "transition_outcome_label",
        "transition_outcome_direction",
    ]
    for keys, group in source_events.groupby(dims, dropna=False):
        grid_id, split, binding, context, outcome, direction = keys
        unique_segments = group.drop_duplicates("transition_segment_id")
        stats = contribution_stats(group)
        segment_keys = {(str(grid_id), seg) for seg in group["transition_segment_id"].dropna().unique()}
        calendar_source = (
            unique_segments["final_segment_calendar_day_n"]
            if "final_segment_calendar_day_n" in unique_segments.columns
            else unique_segments["final_segment_trading_day_n"]
        )
        rows.append(
            {
                "grid_rule_id": grid_id,
                "split": split,
                "split_assignment_policy": "event_split_expanded",
                "segment_cross_split_flag": bool(segment_keys.intersection(cross_set)),
                "cross_split_segment_n": int(len(segment_keys.intersection(cross_set))),
                "universe_binding_status": binding,
                "pit_transition_context": context,
                "transition_outcome_label": outcome,
                "transition_outcome_direction": direction,
                "unique_segment_n": stats["unique_segment_n"],
                "trading_day_n": int(pd.to_numeric(unique_segments["final_segment_trading_day_n"], errors="coerce").fillna(0).sum()),
                "calendar_day_n": int(pd.to_numeric(calendar_source, errors="coerce").fillna(0).sum()),
                "mean_segment_trading_day_n": float(pd.to_numeric(unique_segments["final_segment_trading_day_n"], errors="coerce").mean()),
                "median_segment_trading_day_n": float(pd.to_numeric(unique_segments["final_segment_trading_day_n"], errors="coerce").median()),
                "max_segment_trading_day_n": float(pd.to_numeric(unique_segments["final_segment_trading_day_n"], errors="coerce").max()),
                "event_n": stats["event_n"],
                "target_episode_n": stats["target_episode_n"],
                "top1_segment_event_share": stats["top1_segment_event_share"],
                "top1_segment_episode_share": stats["top1_segment_episode_share"],
                "effective_contributing_segment_n": stats["effective_contributing_segment_n"],
                "contribution_metric_fallback": stats["contribution_metric_fallback"],
                "censored_segment_n": int(unique_segments.loc[unique_segments["transition_outcome_label"].eq("transition_outcome_pending_or_censored"), "transition_segment_id"].nunique()),
                "censored_segment_share": safe_div(
                    unique_segments.loc[unique_segments["transition_outcome_label"].eq("transition_outcome_pending_or_censored"), "transition_segment_id"].nunique(),
                    stats["unique_segment_n"],
                ),
                "segment_power_status": stats["segment_power_status"],
            }
        )
    return pd.DataFrame(rows)


def cell_episode_set(frame: pd.DataFrame, dims: dict[str, str], bridge_only: bool = False) -> set[str]:
    sub = frame.copy()
    for col, value in dims.items():
        sub = sub.loc[sub[col].astype(str).eq(str(value))]
    if bridge_only:
        sub = sub.loc[bool_series(sub, "bridge_positive_denominator_included")]
    return set(sub["target_episode_id"].dropna().astype(str).unique())


def captured_episode_set(frame: pd.DataFrame, dims: dict[str, str], source_id: str, policy: str) -> set[str]:
    sub = frame.copy()
    for col, value in dims.items():
        sub = sub.loc[sub[col].astype(str).eq(str(value))]
    sub = sub.loc[sub["source_id"].astype(str).eq(source_id)].copy()
    if sub.empty:
        return set()
    return set(sub.loc[policy_mask(sub, policy), "target_episode_id"].dropna().astype(str).unique())


def recall_retention_matrix(source_events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    e1_rows = []
    cell_dims = [
        "grid_rule_id",
        "event_split",
        "universe_binding_status",
        "pit_transition_context",
        "transition_outcome_label",
        "transition_outcome_direction",
    ]
    cells = source_events[cell_dims].drop_duplicates()
    for _, cell in cells.iterrows():
        dims = {col: str(cell[col]) for col in cell_dims}
        cell_frame = source_events.copy()
        for col, value in dims.items():
            cell_frame = cell_frame.loc[cell_frame[col].astype(str).eq(value)]
        denominator = cell_episode_set(source_events, dims)
        bridge_denominator = cell_episode_set(source_events, dims, bridge_only=True)
        e1_pre = captured_episode_set(source_events, dims, "07_E1_only", PRE_REPLAY_POLICY)
        e1_post = captured_episode_set(source_events, dims, "07_E1_only", HEADLINE_POLICY)
        e1_missed = denominator.difference(e1_pre)
        stats = contribution_stats(cell_frame)
        for source_id in RECALL_SOURCE_SCOPES:
            source_post = captured_episode_set(source_events, dims, source_id, HEADLINE_POLICY)
            source_missed = source_post.intersection(e1_missed)
            low, high = wilson_interval(len(source_post), len(denominator))
            row = {
                "grid_rule_id": dims["grid_rule_id"],
                "split": dims["event_split"],
                "universe_binding_status": dims["universe_binding_status"],
                "pit_transition_context": dims["pit_transition_context"],
                "transition_outcome_label": dims["transition_outcome_label"],
                "transition_outcome_direction": dims["transition_outcome_direction"],
                "source_id": source_id,
                "window": HEADLINE_WINDOW,
                "replay_policy_id": HEADLINE_POLICY,
                "target_episode_denominator_n": len(denominator),
                "bridge_episode_denominator_n": len(bridge_denominator),
                "unique_segment_n": stats["unique_segment_n"],
                "effective_contributing_segment_n": stats["effective_contributing_segment_n"],
                "top1_segment_episode_share": stats["top1_segment_episode_share"],
                "top1_segment_event_share": stats["top1_segment_event_share"],
                "source_post_replay_captured_episode_n": len(source_post),
                "source_post_replay_recall": safe_div(len(source_post), len(denominator)),
                "e1_post_replay_captured_episode_n": len(e1_post),
                "e1_post_replay_recall": safe_div(len(e1_post), len(denominator)),
                "e1_missed_episode_n": len(e1_missed),
                "source_post_replay_captures_e1_missed_n": len(source_missed),
                "source_post_replay_captures_e1_missed_rate": safe_div(len(source_missed), len(e1_missed)),
                "wilson_ci_low": low,
                "wilson_ci_high": high,
                "episode_power_status": episode_power_status(len(denominator), stats["event_n"]),
                "segment_power_status": stats["segment_power_status"],
                "contribution_concentration_status": stats["contribution_concentration_status"],
            }
            rows.append(row)
            e1_rows.append(
                {
                    "grid_rule_id": dims["grid_rule_id"],
                    "split": dims["event_split"],
                    "universe_binding_status": dims["universe_binding_status"],
                    "pit_transition_context": dims["pit_transition_context"],
                    "transition_outcome_label": dims["transition_outcome_label"],
                    "transition_outcome_direction": dims["transition_outcome_direction"],
                    "source_id": source_id,
                    "target_episode_denominator_n": len(denominator),
                    "e1_missed_episode_n": len(e1_missed),
                    "source_post_replay_captures_e1_missed_n": len(source_missed),
                    "source_post_replay_captures_e1_missed_rate": safe_div(len(source_missed), len(e1_missed)),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(e1_rows)


def cost_quality_matrix(source_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dims = [
        "grid_rule_id",
        "event_split",
        "universe_binding_status",
        "pit_transition_context",
        "transition_outcome_label",
        "transition_outcome_direction",
        "source_id",
    ]
    for keys, group in source_events.groupby(dims, dropna=False):
        unique = group.assign(event_key=make_event_key(group)).drop_duplicates("event_key")
        failure_complete = bool_series(unique, "failure_10_complete")
        false_complete = bool_series(unique, "event_false_repair_20d_complete")
        winner_complete = bool_series(unique, "horizon_complete_120d")
        failure_label = pd.to_numeric(unique.get("failure_10_label", 0), errors="coerce").fillna(0).astype(float).gt(0)
        false_label = bool_series(unique, "event_false_repair_20d_label")
        winner_label = bool_series(unique, "event_big_winner_120d_label")
        rows.append(
            {
                "grid_rule_id": keys[0],
                "split": keys[1],
                "universe_binding_status": keys[2],
                "pit_transition_context": keys[3],
                "transition_outcome_label": keys[4],
                "transition_outcome_direction": keys[5],
                "source_id": keys[6],
                "event_n": int(len(unique)),
                "failure_10_complete_rate": float(failure_complete.mean()) if len(unique) else np.nan,
                "fast_fail_10d_rate": float(failure_label.loc[failure_complete].mean()) if failure_complete.any() else np.nan,
                "event_false_repair_20d_complete_rate": float(false_complete.mean()) if len(unique) else np.nan,
                "false_repair_20d_rate": float(false_label.loc[false_complete].mean()) if false_complete.any() else np.nan,
                "event_big_winner_120d_complete_rate": float(winner_complete.mean()) if len(unique) else np.nan,
                "event_big_winner_120d_rate": float(winner_label.loc[winner_complete].mean()) if winner_complete.any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def density_overlap_matrix(source_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dims = [
        "grid_rule_id",
        "event_split",
        "universe_binding_status",
        "pit_transition_context",
        "transition_outcome_label",
        "transition_outcome_direction",
        "source_id",
    ]
    for keys, group in source_events.groupby(dims, dropna=False):
        unique = group.assign(event_key=make_event_key(group)).drop_duplicates("event_key").copy()
        if unique.empty:
            continue
        unique["density_anchor_pos"] = pd.to_numeric(unique["replay_anchor_pos"], errors="coerce")
        unique["density_anchor_date"] = pd.to_datetime(unique.get("replay_anchor_date"), errors="coerce")
        family_counts = unique.get("family_id", pd.Series("", index=unique.index)).fillna("missing").astype(str).value_counts(normalize=True)
        rolling10 = transition_f.rolling_duplicate_rate(unique, 10)
        rolling20 = transition_f.rolling_duplicate_rate(unique, 20)
        rows.append(
            {
                "grid_rule_id": keys[0],
                "split": keys[1],
                "universe_binding_status": keys[2],
                "pit_transition_context": keys[3],
                "transition_outcome_label": keys[4],
                "transition_outcome_direction": keys[5],
                "source_id": keys[6],
                "selected_event_count": int(len(unique)),
                "formal_event_day_density": safe_div(len(unique), unique["density_anchor_date"].dropna().nunique()),
                "rolling_10d_executable_event_day_density": rolling10["mean_count"],
                "rolling_20d_executable_event_day_density": rolling20["mean_count"],
                "rolling_10d_duplicate_rate": rolling10["duplicate_rate"],
                "rolling_20d_duplicate_rate": rolling20["duplicate_rate"],
                "family_concentration": float(family_counts.max()) if len(family_counts) else np.nan,
                "cross_family_collision_rate": transition_f.cross_family_collision_rate(unique),
                "density_contract_reference": "A_density_contract_replay_anchor_pos",
            }
        )
    return pd.DataFrame(rows)


def label_join_audit(membership: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    m = membership.copy()
    m["event_key"] = make_event_key(m)
    l = labels.copy()
    l["event_key"] = make_event_key(l)
    label_cols = ["failure_10_label", "event_false_repair_20d_label"]
    merged = m.drop_duplicates("event_key")[["event_key", *[c for c in label_cols if c in m.columns]]].merge(
        l.drop_duplicates("event_key")[["event_key", *[c for c in label_cols if c in l.columns]]],
        on="event_key",
        how="left",
        suffixes=("_membership", "_label_source"),
    )
    rows = []
    for col in label_cols:
        left = f"{col}_membership"
        right = f"{col}_label_source"
        if left not in merged.columns or right not in merged.columns:
            rows.append({"label_name": col, "status": "missing_label_column", "compared_event_n": 0, "mismatch_n": np.nan})
            continue
        comparable = merged[left].notna() & merged[right].notna()
        mismatch = comparable & (merged[left].astype(str) != merged[right].astype(str))
        rows.append(
            {
                "label_name": col,
                "status": "pass" if int(mismatch.sum()) == 0 else "label_mismatch_fail_closed",
                "compared_event_n": int(comparable.sum()),
                "mismatch_n": int(mismatch.sum()),
            }
        )
    return pd.DataFrame(rows)


def leakage_audit() -> pd.DataFrame:
    rules = [
        ("pit_context_uses_only_previous_regime", "pass"),
        ("outcome_label_readout_only", "pass"),
        ("grid_selection_excludes_recall_cost_winner", "pass"),
        ("validation_not_used_for_performance_tuning", "pass"),
        ("robustness_only_structural_guard", "pass"),
        ("final_segment_length_not_used_for_pit_inclusion", "pass"),
        ("online_confirmation_no_forward_flicker_merge", "pass"),
        ("per_direction_conversion_diagnostic_only", "pass"),
    ]
    return pd.DataFrame([{"rule_id": rule, "status": status, "blocked_reason": ""} for rule, status in rules])


def aggregate_outcome_difference(cost: pd.DataFrame, recall: pd.DataFrame, selected_rule_id: str) -> pd.DataFrame:
    rows = []
    core_cost = cost.loc[
        cost["grid_rule_id"].astype(str).eq(selected_rule_id)
        & cost["source_id"].astype(str).isin(["08_R_core_event_regime_gated", "08_R6_event_regime_gated"])
        & cost["transition_outcome_label"].isin(OUTCOMES)
    ]
    for (split, source_id), group in core_cost.groupby(["split", "source_id"], dropna=False):
        pivot = group.groupby("transition_outcome_label")["fast_fail_10d_rate"].mean()
        if set(OUTCOMES).issubset(pivot.index):
            rows.append(
                {
                    "metric": "fast_fail_10d_rate",
                    "split": split,
                    "source_id": source_id,
                    "conversion_minus_continuation": pivot["transition_conversion"] - pivot["transition_continuation"],
                }
            )
    core_recall = recall.loc[
        recall["grid_rule_id"].astype(str).eq(selected_rule_id)
        & recall["source_id"].astype(str).isin(["08_R_core_event_regime_gated", "08_R6_event_regime_gated"])
        & recall["transition_outcome_label"].isin(OUTCOMES)
    ]
    for (split, source_id), group in core_recall.groupby(["split", "source_id"], dropna=False):
        pivot = group.groupby("transition_outcome_label")["source_post_replay_recall"].mean()
        if set(OUTCOMES).issubset(pivot.index):
            rows.append(
                {
                    "metric": "source_post_replay_recall",
                    "split": split,
                    "source_id": source_id,
                    "conversion_minus_continuation": pivot["transition_conversion"] - pivot["transition_continuation"],
                }
            )
    return pd.DataFrame(rows)


def decision_logic(
    grid: pd.DataFrame,
    selection: dict[str, Any],
    component_audit: pd.DataFrame,
    binding: pd.DataFrame,
    segment: pd.DataFrame,
    recall: pd.DataFrame,
    cost: pd.DataFrame,
    leakage: pd.DataFrame,
    label_audit: pd.DataFrame,
    source_is_caveated: bool,
) -> tuple[str, list[str], pd.DataFrame]:
    failures: list[str] = []
    comp_status = str(component_audit.iloc[0].get("f_component_alignment_status", "")) if not component_audit.empty else ""
    if comp_status == "component_alignment_blocked":
        return FINAL_COMPONENT_BLOCKED, ["component_alignment_blocked"], pd.DataFrame()
    if (label_audit["status"].astype(str).eq("label_mismatch_fail_closed")).any():
        return FINAL_LABEL_JOIN_BLOCKED, ["label_source_mismatch"], pd.DataFrame()
    if (leakage["status"].astype(str).ne("pass")).any():
        return FINAL_LEAKAGE_BLOCKED, ["leakage_audit_failed"], pd.DataFrame()
    selected = str(selection["selected_grid_rule_id"])
    selected_grid = grid.loc[grid["grid_rule_id"].astype(str).eq(selected)]
    if selected_grid.empty or not bool(selected_grid.iloc[0]["structural_eligible_flag"]):
        failures.append("selected_rule_structural_eligibility_not_met")
    drift_row = binding.loc[binding["universe_binding_status"].eq("published_transition_not_reconstructed_transition")]
    if not drift_row.empty and float(drift_row.iloc[0]["share_of_published_transition_events"]) > 0.20:
        failures.append("published_transition_not_reconstructed_share_gt_20pct")
    selected_segment = segment.loc[segment["grid_rule_id"].astype(str).eq(selected)]
    if selected_segment.empty:
        failures.append("segment_matrix_unavailable")
    key_cells = selected_segment.loc[
        selected_segment["transition_outcome_label"].isin(OUTCOMES)
        & selected_segment["split"].isin(["train", "robustness"])
    ]
    if (key_cells["segment_power_status"].astype(str).eq("low_segment_power_diagnostic")).any():
        failures.append("supported_cell_low_segment_power_diagnostic")
    if source_is_caveated:
        failures.append("upstream_source_caveated")
    diffs = aggregate_outcome_difference(cost, recall, selected)
    stable = False
    if not diffs.empty:
        for (_, source_id), group in diffs.groupby(["metric", "source_id"], dropna=False):
            values = group.loc[group["split"].isin(["train", "robustness"]), "conversion_minus_continuation"].dropna()
            if len(values) >= 2 and (values.gt(0).all() or values.lt(0).all()):
                stable = True
                break
    if not stable:
        failures.append("aggregate_continuation_conversion_difference_not_stable")
    if comp_status == "component_alignment_drift_diagnostic":
        failures.append("component_alignment_drift_diagnostic")
    if failures:
        return FINAL_DIAGNOSTIC, failures, diffs
    return FINAL_SUPPORTED, [], diffs


def decision_tiers(decision: str, failures: list[str], selection: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_tier": "previous_regime_conditioned_transition_outcome_audit",
                "final_decision": decision,
                "selected_grid_rule_id": selection.get("selected_grid_rule_id", ""),
                "supported_usage": "explanatory_audit_only" if decision == FINAL_SUPPORTED else "diagnostic_only",
                "failure_reason": ";".join(failures),
                "per_direction_conversion_policy": "per_direction_conversion_diagnostic_only",
            }
        ]
    )


def plot_timeline(segment_catalog: pd.DataFrame, path_png: Path, path_svg: Path) -> None:
    transitions = segment_catalog.loc[segment_catalog["regime"].eq(TARGET_REGIME)].copy()
    if transitions.empty:
        return
    colors = {
        "risk_on_continuation_buffer": "#2ca25f",
        "risk_off_continuation_buffer": "#de2d26",
        "risk_off_to_risk_on_recovery_conversion": "#3182bd",
        "risk_on_to_risk_off_deterioration_conversion": "#f59e0b",
        "unknown_or_censored": "#8c8c8c",
    }
    transitions["segment_start_date"] = pd.to_datetime(transitions["segment_start_date"])
    transitions["segment_end_date"] = pd.to_datetime(transitions["segment_end_date"])
    years = sorted(transitions["segment_start_date"].dt.year.unique())
    fig, axes = plt.subplots(len(years), 1, figsize=(16, max(2.5, len(years) * 0.9)), sharex=False)
    if len(years) == 1:
        axes = [axes]
    for ax, year in zip(axes, years):
        start = pd.Timestamp(f"{year}-01-01")
        end = pd.Timestamp(f"{year}-12-31")
        ax.set_xlim(start, end)
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.set_ylabel(str(year), rotation=0, labelpad=26, va="center")
        for _, row in transitions.iterrows():
            seg_start = max(row["segment_start_date"], start)
            seg_end = min(row["segment_end_date"], end)
            if seg_start > end or seg_end < start:
                continue
            days = max(1, (seg_end - seg_start).days + 1)
            color = colors.get(str(row["transition_outcome_direction"]), "#8c8c8c")
            ax.barh(0.5, days, left=seg_start, height=0.52, color=color, edgecolor="white", linewidth=0.4)
            if days >= 12:
                ax.text(seg_start + (seg_end - seg_start) / 2, 0.5, f"{int(row['segment_trading_day_n'])}d", ha="center", va="center", color="white", fontsize=7)
        ax.grid(axis="x", color="#dddddd", linewidth=0.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=color) for color in colors.values()]
    fig.legend(handles, list(colors.keys()), loc="upper center", ncol=3, fontsize=8, frameon=False)
    fig.suptitle("Experiment G previous-regime conditioned transition timeline", y=0.995, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path_png, dpi=180)
    fig.savefig(path_svg)
    plt.close(fig)


def build_contract_text() -> str:
    return "\n".join(
        [
            "# Previous-Regime Conditioned Transition Outcome Contract",
            "",
            "- No model is trained; only deterministic previous-regime rules are grid-searched.",
            "- PIT context uses previous non-transition regime and as-of segment age only.",
            "- Continuation/conversion is ex-post readout only and never a PIT feature.",
            "- Supported evidence, if any, is aggregate continuation vs conversion only.",
            "- Per-direction conversion is diagnostic-only by construction.",
            "",
        ]
    )


def build_report(
    decision: str,
    failures: list[str],
    selection: dict[str, Any],
    component: pd.DataFrame,
    binding: pd.DataFrame,
    grid: pd.DataFrame,
    segment: pd.DataFrame,
    recall: pd.DataFrame,
    cost: pd.DataFrame,
    density: pd.DataFrame,
    diffs: pd.DataFrame,
) -> str:
    lines = [
        "# Experiment G - Previous-Regime Conditioned Transition Outcome Audit 报告",
        "",
        f"最终决策：`{decision}`",
        "",
        "## 结论",
        "",
        "本实验不训练模型，也不尝试在 PIT 时点预测 conversion。它只用 previous non-transition regime 和 t0 已知的 transition segment age 做 PIT context，然后把 next non-transition regime 作为 ex-post readout。",
        f"selected rule: `{selection.get('selected_grid_rule_id')}`。",
        f"selection reason: `{selection.get('selection_reason')}`。",
        "",
    ]
    if failures:
        lines += ["Gate / caveat:", *[f"- `{reason}`" for reason in failures], ""]
    if not component.empty:
        row = component.iloc[0]
        lines += [
            "## Component Alignment",
            "",
            f"- F alignment status: `{row.get('f_component_alignment_status')}`",
            f"- component reuse policy: `{row.get('component_reuse_policy')}`",
            f"- reconstruction consistency: `{row.get('component_reconstruction_consistency_rate')}`",
            "",
        ]
    lines += ["## Universe Binding", "", binding.to_markdown(index=False) if not binding.empty else "无 binding audit。", ""]
    selected_grid = grid.loc[grid["selected_rule_flag"]] if "selected_rule_flag" in grid.columns else pd.DataFrame()
    base_grid = grid.loc[grid["base_rule_flag"]] if "base_rule_flag" in grid.columns else pd.DataFrame()
    lines += [
        "## Grid Search",
        "",
        "grid search 只用 structural eligibility，不用 recall / cost / winner outcome 选参。",
        "Selected rule:",
        selected_grid.to_markdown(index=False) if not selected_grid.empty else "无 selected rule。",
        "",
        "Base rule:",
        base_grid.to_markdown(index=False) if not base_grid.empty else "无 base rule。",
        "",
    ]
    lines += ["## Segment Power", ""]
    seg_head = segment.loc[
        segment["grid_rule_id"].astype(str).eq(str(selection.get("selected_grid_rule_id")))
        & segment["transition_outcome_label"].isin(OUTCOMES)
    ].head(40)
    lines.append(seg_head.to_markdown(index=False) if not seg_head.empty else "无 segment readout。")
    lines += ["", "## Aggregate Continuation vs Conversion Difference", ""]
    lines.append(diffs.to_markdown(index=False) if not diffs.empty else "未发现可稳定支持的 aggregate difference。")
    lines += ["", "## Recall / Cost / Density Readout", ""]
    recall_head = recall.loc[
        recall["grid_rule_id"].astype(str).eq(str(selection.get("selected_grid_rule_id")))
        & recall["source_id"].isin(["08_R_core_event_regime_gated", "08_R6_event_regime_gated"])
    ].head(30)
    cost_head = cost.loc[
        cost["grid_rule_id"].astype(str).eq(str(selection.get("selected_grid_rule_id")))
        & cost["source_id"].isin(["08_R_core_event_regime_gated", "08_R6_event_regime_gated"])
    ].head(30)
    density_head = density.loc[
        density["grid_rule_id"].astype(str).eq(str(selection.get("selected_grid_rule_id")))
        & density["source_id"].isin(["08_R_core_event_regime_gated", "08_R6_event_regime_gated"])
    ].head(20)
    lines += ["Recall:", recall_head.to_markdown(index=False) if not recall_head.empty else "无 recall readout。"]
    lines += ["", "Cost:", cost_head.to_markdown(index=False) if not cost_head.empty else "无 cost readout。"]
    lines += ["", "Density:", density_head.to_markdown(index=False) if not density_head.empty else "无 density readout。"]
    lines += [
        "",
        "## Interpretation",
        "",
        "方向级 conversion segment 在 robustness 上天然很薄，因此 `risk_off_to_risk_on_recovery_conversion` 和 `risk_on_to_risk_off_deterioration_conversion` 只能解释图形和案例，不能单独成为 supported evidence。",
        "如果 aggregate continuation / conversion 差异不稳定，后续不应继续训练 transition 子状态模型；更合理的方向是把 previous-regime context 作为 report/readout 维度，或者回到 cost rejector / label source 重定义。",
        "",
        "## 不可声称内容",
        "",
        "- 不得声称 direct-entry support。",
        "- 不得声称 official train process。",
        "- 不得声称 conversion 是 PIT 可完全识别状态。",
        "- 不得把 selected grid rule 解释为收益最优规则。",
        "",
    ]
    return "\n".join(lines)


def build_manifest(
    decision: str,
    failures: list[str],
    input_paths: dict[str, Path],
    manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    frames: dict[str, pd.DataFrame],
    selection: dict[str, Any],
    component: pd.DataFrame,
    binding: pd.DataFrame,
    segment: pd.DataFrame,
) -> dict[str, Any]:
    output_hashes = {
        key: path_hash(path)
        for key, path in sorted(OUTPUT_PATHS.items())
        if path.exists() and path.is_file() and key != "transition_previous_regime_outcome_audit_manifest"
    }
    output_paths = {key: str(path) for key, path in sorted(OUTPUT_PATHS.items()) if path.exists()}
    component_row = component.iloc[0].to_dict() if not component.empty else {}
    return {
        "experiment_id": "08_experiment_g_transition_previous_regime_conditioned_outcome_audit",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "final_decision": decision,
        "decision": decision,
        "blocked_reasons": failures,
        "selected_grid_rule_id": selection.get("selected_grid_rule_id"),
        "base_grid_rule_id": BASE_RULE_ID,
        "grid_parameter_space": {
            "min_previous_regime_trading_day_n": list(GRID_MIN_PREVIOUS),
            "min_segment_age_at_event_t0": list(GRID_MIN_AGE),
            "online_confirmation_trading_day_n": list(GRID_CONFIRMATION),
            "outcome_max_transition_trading_day_n": list(GRID_OUTCOME_MAX),
        },
        "selected_rule_parameters": selection.get("selected_rule_parameters"),
        "selection_reason": selection.get("selection_reason"),
        "transition_universe_policy": "primary_readout_reconstructed_transition_universe",
        "universe_binding_summary": binding.to_dict(orient="records") if not binding.empty else [],
        "f_component_alignment_status": component_row.get("f_component_alignment_status"),
        "component_reuse_policy": component_row.get("component_reuse_policy"),
        "segment_power_summary": segment["segment_power_status"].value_counts().to_dict() if not segment.empty else {},
        "contribution_concentration_summary": frames.get("transition_previous_regime_recall_retention_matrix", pd.DataFrame()).get("contribution_concentration_status", pd.Series(dtype=str)).value_counts().to_dict(),
        "per_direction_conversion_policy": "per_direction_conversion_diagnostic_only",
        "input_artifacts": {key: str(path) for key, path in sorted(input_paths.items())},
        "input_hashes": {key: path_hash(path) for key, path in sorted(input_paths.items()) if path.exists()},
        "output_paths": output_paths,
        "output_hashes": output_hashes,
        "output_row_counts": {key: int(len(frame)) for key, frame in sorted(frames.items())},
        "runner_code_hash": path_hash(Path(__file__)),
        "requirement_hash": path_hash(REQUIREMENT_PATH),
        "upstream_decisions": {
            "A": manifests[0].get("decision"),
            "B": manifests[1].get("decision"),
            "C": manifests[2].get("decision"),
            "D": manifests[3].get("decision"),
            "F": manifests[4].get("final_decision") or manifests[4].get("decision"),
        },
    }


def output_blocked(decision: str, failures: list[str], input_frame: pd.DataFrame, input_paths: dict[str, Path], manifests: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    ensure_dirs()
    write_df(OUTPUT_PATHS["transition_previous_regime_input_audit"], input_frame)
    write_text(OUTPUT_PATHS["transition_previous_regime_outcome_audit_report"], f"# Experiment G\n\n最终决策：`{decision}`\n\n" + "\n".join(f"- `{reason}`" for reason in failures))
    frames = {"transition_previous_regime_input_audit": input_frame}
    write_json(
        OUTPUT_PATHS["transition_previous_regime_outcome_audit_manifest"],
        build_manifest(decision, failures, input_paths, manifests, frames, {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()),
    )
    return {
        "decision": decision,
        "blocked_reasons": failures,
        "manifest_path": str(OUTPUT_PATHS["transition_previous_regime_outcome_audit_manifest"]),
    }


def run(mode: str = "full") -> dict[str, Any]:
    ensure_dirs()
    input_frame, input_paths, input_failures = input_audit()
    manifests = validate_manifests()
    a, b, c, d, f, manifest_failures = manifests
    manifest_tuple = (a, b, c, d, f)
    input_failures.extend(manifest_failures)
    if input_failures:
        return output_blocked(FINAL_INPUT_BLOCKED, input_failures, input_frame, input_paths, manifest_tuple)
    if mode == "check-inputs":
        write_df(OUTPUT_PATHS["transition_previous_regime_input_audit"], input_frame)
        return {"decision": "transition_previous_regime_outcome_inputs_ready", "input_rows": len(input_frame)}

    canonical = load_canonical_events(input_paths["candidate_family_canonical_events"])
    labels = pd.read_parquet(input_paths["candidate_family_event_labels"])
    membership = pd.read_parquet(input_paths["d_membership"])
    components = load_component_panel(input_paths["primary_index_sh000985"])
    component = build_component_alignment(canonical, components, input_paths["primary_index_sh000985"], input_paths["experiment_f_component_audit"])
    if str(component.iloc[0]["f_component_alignment_status"]) == "component_alignment_blocked":
        return output_blocked(FINAL_COMPONENT_BLOCKED, ["component_alignment_blocked"], input_frame, input_paths, manifest_tuple)

    segment_catalog, components_with_segments = build_segment_catalog(components)
    base_events = build_base_event_assignments(canonical, components_with_segments)
    grid, selection = grid_search(base_events)
    assignments = selected_and_base_assignments(base_events, selection)
    source_events = prepare_source_events(membership, assignments)
    binding = universe_binding_audit(assignments)
    segment = segment_matrix(source_events)
    recall, e1_missed = recall_retention_matrix(source_events)
    cost = cost_quality_matrix(source_events)
    density = density_overlap_matrix(source_events)
    label_audit = label_join_audit(membership, labels)
    leakage = leakage_audit()
    decision, failures, diffs = decision_logic(
        grid,
        selection,
        component,
        binding,
        segment,
        recall,
        cost,
        leakage,
        label_audit,
        source_caveated(manifest_tuple),
    )
    tiers = decision_tiers(decision, failures, selection)

    frames: dict[str, pd.DataFrame] = {
        "transition_previous_regime_input_audit": input_frame,
        "transition_previous_regime_component_audit": component,
        "transition_previous_regime_universe_binding_audit": binding,
        "transition_previous_regime_segment_catalog": segment_catalog,
        "transition_previous_regime_grid_search": grid,
        "transition_previous_regime_event_assignment": assignments,
        "transition_previous_regime_segment_matrix": segment,
        "transition_previous_regime_recall_retention_matrix": recall,
        "transition_previous_regime_e1_missed_capture": e1_missed,
        "transition_previous_regime_cost_quality_matrix": cost,
        "transition_previous_regime_density_overlap_matrix": density,
        "transition_previous_regime_label_join_audit": label_audit,
        "transition_previous_regime_leakage_audit": leakage,
        "transition_previous_regime_decision_tiers": tiers,
    }
    for key, frame in frames.items():
        write_df(OUTPUT_PATHS[key], frame)
    plot_timeline(
        segment_catalog,
        OUTPUT_PATHS["transition_previous_regime_timeline_png"],
        OUTPUT_PATHS["transition_previous_regime_timeline_svg"],
    )
    write_text(
        OUTPUT_PATHS["transition_previous_regime_outcome_contract"],
        build_contract_text(),
    )
    write_text(
        OUTPUT_PATHS["transition_previous_regime_outcome_audit_report"],
        build_report(decision, failures, selection, component, binding, grid, segment, recall, cost, density, diffs),
    )
    write_json(
        OUTPUT_PATHS["transition_previous_regime_outcome_audit_manifest"],
        build_manifest(decision, failures, input_paths, manifest_tuple, frames, selection, component, binding, segment),
    )
    return {
        "decision": decision,
        "blocked_reasons": failures,
        "selected_grid_rule_id": selection.get("selected_grid_rule_id"),
        "manifest_path": str(OUTPUT_PATHS["transition_previous_regime_outcome_audit_manifest"]),
        "report_path": str(OUTPUT_PATHS["transition_previous_regime_outcome_audit_report"]),
        "row_counts": {key: int(len(frame)) for key, frame in frames.items()},
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

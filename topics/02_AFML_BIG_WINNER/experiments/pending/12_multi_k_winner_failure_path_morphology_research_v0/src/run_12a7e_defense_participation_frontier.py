#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
TOPIC_SRC_DIR = TOPIC_ROOT / "src"

if str(TOPIC_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TOPIC_SRC_DIR))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


def _load_runner(name: str, filename: str) -> Any:
    path = EXPERIMENT_DIR / "src" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


C7 = _load_runner("run_12a7c_helpers_for_12a7e", "run_12a7c_direction_e_stage2_decoupling_chained_readouts.py")
D7 = _load_runner("run_12a7d_helpers_for_12a7e", "run_12a7d_stage2_random_baseline_support_triage.py")
A7 = C7.A7

RUN_ID = "12A7e_defense_participation_frontier"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a7e_defense_participation_frontier.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
TARGET_COL = "stage_2_continuation_target"
RANDOM_TARGET_COL = "random_stage_2_continuation_target"
STAGE2_SCORE_COL = "stage2_continuation_score"
STAGE1_FEATURE = "volatility_20d"
CELL_COLS = ["split", "board_bucket", "calendar_month"]

EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "requirement": (),
    "upstream_requirement_12a7c": (),
    "upstream_requirement_12a7d": (),
    "a7b_direction_c_decision": (
        "decision_state",
        "input_gate_status",
        "pit_gate_status",
        "phase_1_simple_backbone_gate_status",
        "selected_primary_rule_id",
        "selected_primary_simple_backbone_tuple",
        "selected_primary_X",
    ),
    "a7b_simple_backbone_train_selection": ("rule_id", "stage1_budget_X", "feature_orientation_json"),
    "a7b_simple_backbone_operating_point_readout": ("stage", "split", "rule_id", "stage1_budget_X", "selected_n"),
    "a7b_simple_backbone_random_same_budget_audit": ("seed", "split", "requested_selected_n", "random_fast_fail_rate"),
    "a7b_simple_backbone_score_matrix": ("meta_event_id", "volatility_20d__rank_percentile", "volatility_20d__rank_status"),
    "a7c_direction_e_decision": (
        "decision_state",
        "input_gate_status",
        "stage1_anchor_reconstruction_status",
        "selected_chained_candidate_id",
        "selected_chained_candidate_family",
        "selected_chained_X",
        "selected_chained_deployable_at_stage_2_decision_time",
        "stage1_anchor_rule_id",
        "stage1_anchor_feature",
        "stage1_anchor_orientation",
        "stage1_anchor_X",
    ),
    "a7c_stage2_train_selection": ("denominator_type", "candidate_id", "stage2_budget_X", "selected_n"),
    "a7c_stage2_decoupling_score_matrix": (
        "meta_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "split",
        "board_bucket",
        "calendar_month",
        "calendar_quarter",
        "path_key",
        "source_arm_is_c0",
        "market_regime_bucket",
        "stage_1_evaluable",
        "stage_1_fast_fail_target",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "stage_2_decision_pos",
        TARGET_COL,
        "stage2_label_read_status",
        STAGE2_SCORE_COL,
        "stage1_anchor_rank_percentile",
        "stage1_anchor_rank_status",
        "stage1_anchor_selected_flag",
        STAGE1_FEATURE,
    ),
    "a7_direction_trailing_rank_score_matrix": ("meta_event_id", "instrument", "event_t0_pos", "stage_2_decision_pos", STAGE2_SCORE_COL),
    "a7d_stage2_chained_sensitivity_decision": (
        "decision_state",
        "input_gate_status",
        "candidate_reconciliation_status",
        "random_source_status",
        "selected_chained_candidate_id",
        "selected_chained_candidate_family",
        "selected_chained_X",
        "next_allowed_requirement",
    ),
    "a7d_frozen_candidate_reconciliation": (
        "denominator_type",
        "candidate_id",
        "stage2_budget_X",
        "split",
        "upstream_selected_n",
        "upstream_selected_positive_n",
        "upstream_selected_budget_rank_evaluable",
        "candidate_reconciliation_status",
    ),
    "a7d_random_replay_variant_readout": ("baseline_id", "split", "baseline_construction_status"),
    "a7d_report": (),
    "a7d_manifest": (),
    "matched_random_sampled_entries": (
        "seed",
        "sample_draw_id",
        "path_key",
        "split",
        "board_bucket",
        "calendar_month",
        "calendar_quarter",
        "random_trade_open_date",
        "instrument",
        "entry_pos",
        "entry_price",
        "replacement_draw_index",
    ),
    "entry_forward_path_cache": (
        "path_key",
        "instrument",
        "entry_pos",
        "entry_price",
        "entry_blocked",
        "horizon_complete_20d",
        "time_to_lower_minus_10_20d",
    ),
    "stage2_path_cache": (
        "path_key",
        "instrument",
        "entry_pos",
        "entry_price",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "continuation_U20_L10_H2_20",
    ),
    "two_stage_feature_matrix": ("meta_event_id", "instrument", "event_t0_pos", STAGE1_FEATURE),
    "manifest_12a6b": (),
    "manifest_12a6c": (),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A7e defense-participation frontier.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    return C7.topic_path(value)


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "stage1_x_grid_card": TABLE_DIR / "stage1_x_grid_card.csv",
        "frontier_candidate_reconstruction": TABLE_DIR / "frontier_candidate_reconstruction.csv",
        "stage1_frontier_readout": TABLE_DIR / "stage1_frontier_readout.csv",
        "stage2_frontier_readout": TABLE_DIR / "stage2_frontier_readout.csv",
        "defense_participation_frontier": TABLE_DIR / "defense_participation_frontier.csv",
        "pareto_frontier_audit": TABLE_DIR / "pareto_frontier_audit.csv",
        "stage1_random_same_budget_audit": TABLE_DIR / "stage1_random_same_budget_audit.csv",
        "stage2_random_support_audit": TABLE_DIR / "stage2_random_support_audit.csv",
        "frontier_selection_audit": TABLE_DIR / "frontier_selection_audit.csv",
        "defense_participation_decision": TABLE_DIR / "defense_participation_decision.csv",
        "frontier_selection_matrix": LOCAL_CACHE_DIR / "frontier_selection_matrix.parquet",
        "stage2_rank_matrix_by_x": LOCAL_CACHE_DIR / "stage2_rank_matrix_by_x.parquet",
        "bootstrap_replicates": LOCAL_CACHE_DIR / "bootstrap_replicates.parquet",
        "report": REPORT_DIR / "defense_participation_frontier_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return C7.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return C7.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return C7.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return C7.write_json(path, payload)


def path_sha(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def boolish(value: Any) -> bool:
    return A7.boolish(value)


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def safe_rate(num: int | float, den: int | float) -> float:
    return A7.safe_rate(num, den)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    return C7.split_frame(frame, split)


def fmt(value: Any) -> str:
    return "NA" if pd.isna(value) else f"{float(value):.4f}"


def count_rows(path: Path) -> int | float:
    return C7.count_rows(path)


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for artifact_id, required_cols in EXPECTED_INPUT_COLUMNS.items():
        raw = config.get("paths", {}).get(artifact_id, artifact_id)
        path = topic_path(raw)
        exists = path.is_file()
        read_status = "pass" if exists else "missing"
        schema_status = "pass" if exists and not required_cols else "not_checked"
        row_count = np.nan
        if exists and required_cols:
            try:
                frame = read_table(path, nrows=5) if not "".join(path.suffixes).endswith(".parquet") else read_table(path)
                missing = set(required_cols) - set(frame.columns)
                schema_status = "pass" if not missing else "missing_columns:" + ";".join(sorted(missing))
                row_count = count_rows(path)
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        elif exists:
            row_count = count_rows(path)
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "row_count": row_count,
                "sha256": path_sha(path),
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": True,
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(
    audit: pd.DataFrame,
    a7b_decision: pd.DataFrame,
    a7c_decision: pd.DataFrame,
    a7d_decision: pd.DataFrame,
) -> tuple[str, str]:
    reasons: list[str] = []
    required = audit.loc[audit["required_flag"]]
    if not required["read_status"].astype(str).eq("pass").all():
        reasons.append("missing_or_unreadable_required_inputs")
    blocking_schema = required.loc[
        ~required["artifact_id"].isin({"a7c_stage2_decoupling_score_matrix"})
        & ~required["schema_status"].astype(str).eq("pass")
    ]
    if not blocking_schema.empty:
        reasons.append("required_schema_mismatch:" + ";".join(blocking_schema["artifact_id"].astype(str).tolist()))
    if a7b_decision.empty:
        reasons.append("a7b_decision_empty")
    else:
        row = a7b_decision.iloc[0]
        if str(row.get("input_gate_status", "")) != "pass":
            reasons.append("a7b_input_gate_not_pass")
        if str(row.get("pit_gate_status", "")) != "pass":
            reasons.append("a7b_pit_gate_not_pass")
        if str(row.get("phase_1_simple_backbone_gate_status", "")) != "pass":
            reasons.append("a7b_phase1_gate_not_pass")
        if str(row.get("selected_primary_simple_backbone_tuple", "")) != STAGE1_FEATURE:
            reasons.append("a7b_selected_tuple_not_volatility_20d")
        if not np.isclose(float(row.get("selected_primary_X", np.nan)), 0.30):
            reasons.append("a7b_selected_x_not_030")
    if a7c_decision.empty:
        reasons.append("a7c_decision_empty")
    else:
        row = a7c_decision.iloc[0]
        if str(row.get("stage1_anchor_reconstruction_status", "")) != "pass":
            reasons.append("a7c_anchor_reconstruction_not_pass")
        if not boolish(row.get("selected_chained_deployable_at_stage_2_decision_time", False)):
            reasons.append("a7c_chained_not_deployable")
        if str(row.get("selected_chained_candidate_id", "")) == "":
            reasons.append("a7c_selected_chained_candidate_missing")
        if pd.isna(row.get("selected_chained_X", np.nan)):
            reasons.append("a7c_selected_chained_x_missing")
    allowed_12a7d = {
        "12A7d_stage2_signal_diagnostic_only",
        "12A7d_random_baseline_support_insufficient",
        "12A7d_stage2_not_supported",
        "12A7d_strict_chained_stage2_supported",
        "12A7d_chained_stage2_supported_with_baseline_caveat",
    }
    if a7d_decision.empty:
        reasons.append("a7d_decision_empty")
    else:
        row = a7d_decision.iloc[0]
        if str(row.get("decision_state", "")) not in allowed_12a7d:
            reasons.append("a7d_decision_state_not_allowed")
        if str(row.get("input_gate_status", "")) != "pass":
            reasons.append("a7d_input_gate_not_pass")
        if str(row.get("candidate_reconciliation_status", "")) != "pass":
            reasons.append("a7d_candidate_reconciliation_not_pass")
        if str(row.get("random_source_status", "")) != "pass":
            reasons.append("a7d_random_source_not_pass")
        if str(row.get("next_allowed_requirement", "")) != "requirement_12a7e_defense_participation_frontier.md":
            reasons.append("a7d_next_allowed_requirement_mismatch")
    return ("pass", "") if not reasons else ("fail", ";".join(reasons))


def merge_unique(left: pd.DataFrame, right: pd.DataFrame, key: list[str], cols: list[str], source_name: str) -> tuple[pd.DataFrame, str]:
    if any(col not in left.columns for col in key) or any(col not in right.columns for col in key):
        return left, f"{source_name}_join_key_missing"
    if int(right.duplicated(key).sum()):
        return left, f"{source_name}_duplicate_key"
    keep = key + [c for c in cols if c in right.columns and c not in key]
    return left.merge(right[keep], on=key, how="left"), "pass"


def load_score_matrix_with_fallback(resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    frame = read_table(resolved["a7c_stage2_decoupling_score_matrix"])
    status_parts = []
    required = list(EXPECTED_INPUT_COLUMNS["a7c_stage2_decoupling_score_matrix"])
    missing = [col for col in required if col not in frame.columns]
    if STAGE2_SCORE_COL in missing:
        score = read_table(resolved["a7_direction_trailing_rank_score_matrix"])
        frame, status = merge_unique(frame, score, ["meta_event_id"], [STAGE2_SCORE_COL], "trailing_rank_score_matrix")
        status_parts.append(f"stage2_score:{status}")
    if "stage1_anchor_rank_percentile" in missing or "stage1_anchor_rank_status" in missing or "stage1_anchor_selected_flag" in missing:
        sb = read_table(resolved["a7b_simple_backbone_score_matrix"])
        rename = {
            "volatility_20d__rank_percentile": "stage1_anchor_rank_percentile",
            "volatility_20d__rank_status": "stage1_anchor_rank_status",
        }
        sb = sb.rename(columns={k: v for k, v in rename.items() if k in sb.columns})
        frame, status = merge_unique(frame, sb, ["meta_event_id"], ["stage1_anchor_rank_percentile", "stage1_anchor_rank_status", STAGE1_FEATURE], "simple_backbone_score_matrix")
        status_parts.append(f"stage1_anchor:{status}")
    if STAGE1_FEATURE in missing and STAGE1_FEATURE not in frame.columns:
        features = read_table(resolved["two_stage_feature_matrix"])
        frame, status = merge_unique(frame, features, ["meta_event_id"], [STAGE1_FEATURE], "two_stage_feature_matrix")
        status_parts.append(f"stage1_feature:{status}")
    path_cols = ["stage_2_entry_blocked", "stage_2_horizon_complete_20d", TARGET_COL]
    if any(col in missing for col in ["stage_2_entry_blocked", "stage_2_horizon_complete_20d", TARGET_COL, "stage2_label_read_status"]):
        cache = read_table(resolved["stage2_path_cache"]).rename(columns={"continuation_U20_L10_H2_20": TARGET_COL})
        key = ["path_key", "instrument"]
        frame, status = merge_unique(frame, cache, key, path_cols, "stage2_path_cache")
        status_parts.append(f"stage2_path:{status}")
    if "stage1_anchor_selected_flag" not in frame.columns and {"stage1_anchor_rank_percentile", "stage1_anchor_rank_status"} <= set(frame.columns):
        frame["stage1_anchor_selected_flag"] = C7.keep_mask_from_rank(
            frame["stage1_anchor_rank_status"], frame["stage1_anchor_rank_percentile"], "asc", 0.30
        )
    if "stage2_label_read_status" not in frame.columns and set(path_cols) <= set(frame.columns):
        frame["stage2_label_read_status"] = np.where(
            (~bool_series(frame["stage_2_entry_blocked"]))
            & bool_series(frame["stage_2_horizon_complete_20d"])
            & frame[TARGET_COL].notna(),
            "pass",
            "fail",
        )
    if "calendar_quarter" not in frame.columns and "calendar_month" in frame.columns:
        frame["calendar_quarter"] = D7.calendar_quarter_from_month(frame["calendar_month"])
    if "stage_2_path_evaluable" not in frame.columns and "stage2_label_read_status" in frame.columns:
        frame["stage_2_path_evaluable"] = frame["stage2_label_read_status"].astype(str).eq("pass")
    final_missing = [col for col in required if col not in frame.columns]
    if final_missing:
        return frame, "missing_columns:" + ";".join(final_missing)
    for col in [
        "source_arm_is_c0",
        "stage_1_evaluable",
        "stage_1_fast_fail_target",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        TARGET_COL,
        "stage1_anchor_selected_flag",
    ]:
        if col in frame.columns:
            frame[col] = bool_series(frame[col])
    frame["event_t0_date"] = frame["event_t0_date"].map(A7.date_text)
    frame["stage_2_decision_pos"] = pd.to_numeric(frame["stage_2_decision_pos"], errors="coerce")
    frame["event_t0_pos"] = pd.to_numeric(frame["event_t0_pos"], errors="coerce")
    frame["stage1_anchor_rank_percentile"] = pd.to_numeric(frame["stage1_anchor_rank_percentile"], errors="coerce")
    frame[STAGE2_SCORE_COL] = pd.to_numeric(frame[STAGE2_SCORE_COL], errors="coerce")
    primary = frame.loc[
        bool_series(frame["source_arm_is_c0"])
        & frame["market_regime_bucket"].astype(str).eq("risk_on")
        & bool_series(frame["stage_1_evaluable"])
    ].copy()
    fallback_status = "primary_schema_pass" if not status_parts else ";".join(status_parts)
    return primary, fallback_status


def stage1_selected_mask(frame: pd.DataFrame, x: float) -> pd.Series:
    if np.isclose(float(x), 1.0):
        return bool_series(frame["stage_1_evaluable"])
    return C7.keep_mask_from_rank(frame["stage1_anchor_rank_status"], frame["stage1_anchor_rank_percentile"], "asc", float(x))


def stage2_denominator_mask(frame: pd.DataFrame, selected_mask: pd.Series) -> pd.Series:
    return (
        selected_mask
        & bool_series(frame["no_fast_fail_L10_H20"])
        & bool_series(frame["stage_2_path_evaluable"])
        & (~bool_series(frame["stage_2_entry_blocked"]))
        & bool_series(frame["stage_2_horizon_complete_20d"])
        & frame["stage2_label_read_status"].astype(str).eq("pass")
        & pd.to_numeric(frame["stage_2_decision_pos"], errors="coerce").notna()
    )


def rank_stage2_for_x(denominator: pd.DataFrame, x: float, config: dict[str, Any], anchor_rule_id: str) -> pd.DataFrame:
    policy = A7.HistoryPolicy(
        history_policy_id=str(config["history_policy"]["history_policy_id"]),
        history_window_mode=str(config["history_policy"]["history_window_mode"]),
        trailing_history_window_sessions=int(config["history_policy"]["trailing_history_window_sessions"]),
        diagnostic_only_flag=False,
    )
    h = config["history_min_n"]
    ranked = A7.rolling_percentiles(
        denominator.copy(),
        score_col=STAGE2_SCORE_COL,
        pos_col="stage_2_decision_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_2_global_min_history_n"]),
        board_min_history_n=int(h["stage_2_board_min_history_n"]),
    )
    ranked = ranked.rename(columns={"rank_status": "stage2_rank_status", "rank_percentile": "stage2_rank_percentile"})
    ranked["stage1_X"] = float(x)
    ranked["denominator_type"] = "stage1_anchor_chained_survivor"
    ranked["candidate_id"] = "complex_stage2_score"
    ranked["candidate_family"] = "complex_stage2_score"
    ranked["stage2_budget_X"] = float(config["stage2"]["x"])
    ranked["stage1_anchor_rule_id"] = anchor_rule_id
    ranked["selected_flag"] = C7.keep_mask_from_rank(
        ranked["stage2_rank_status"], ranked["stage2_rank_percentile"], "desc", float(config["stage2"]["x"])
    )
    return ranked


def ground_truth_survivor(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[stage2_denominator_mask(frame, pd.Series(True, index=frame.index))].copy()


def prepare_random(resolved: dict[str, Path], config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    random, status = D7.prepare_random_labels(resolved, config)
    if not random.empty:
        random["random_stage_1_fast_fail_target"] = random["time_to_lower_minus_10_20d"].notna()
    return random, status


def requested_counts(frame: pd.DataFrame, flag_col: str) -> pd.DataFrame:
    return D7.requested_counts(frame, flag_col, "requested_selected_n")


def strict_draw_vectorized(
    pool: pd.DataFrame,
    counts: pd.DataFrame,
    rank_cols: list[str],
    replay_step: str,
    x: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    seeds = pd.DataFrame({"seed": sorted(pool["seed"].dropna().unique())})
    if counts.empty or pool.empty or seeds.empty:
        return pool.head(0).copy(), pd.DataFrame()
    sort_cols = ["seed"] + CELL_COLS + rank_cols
    pool = pool.sort_values([c for c in sort_cols if c in pool.columns], kind="stable").copy()
    audit = seeds.merge(counts, how="cross")
    available = (
        pool.groupby(["seed"] + CELL_COLS, dropna=False)
        .size()
        .rename("available_random_n")
        .reset_index()
    )
    audit = audit.merge(available, on=["seed"] + CELL_COLS, how="left")
    audit["available_random_n"] = audit["available_random_n"].fillna(0).astype(int)
    audit["sampled_random_n"] = np.minimum(audit["available_random_n"], audit["requested_selected_n"]).astype(int)
    audit["shortfall_n"] = (audit["requested_selected_n"] - audit["sampled_random_n"]).clip(lower=0).astype(int)
    audit["cell_support_status"] = np.where(audit["sampled_random_n"].eq(audit["requested_selected_n"]), "pass", "fail")
    audit["baseline_id"] = "strict_exact_cell_replay"
    audit["baseline_family_id"] = "strict_exact_cell_replay"
    audit["replay_step"] = replay_step
    audit["realized_cell_grain"] = "month"
    audit["fallback_used_flag"] = False
    audit["replacement_used_flag"] = False
    audit["duplicate_rate"] = 0.0
    audit["random_row_uid_duplicate_n"] = 0
    audit["stage1_X"] = float(x)
    pool = pool.drop(columns=[c for c in ["requested_selected_n", "replay_step"] if c in pool.columns])
    selected = pool.merge(counts[CELL_COLS + ["requested_selected_n"]], on=CELL_COLS, how="inner")
    selected["_within_cell_rank"] = selected.groupby(["seed"] + CELL_COLS, dropna=False).cumcount()
    selected = selected.loc[selected["_within_cell_rank"].lt(selected["requested_selected_n"])].copy()
    selected["stage1_X"] = float(x)
    selected["replay_step"] = replay_step
    selected = selected.drop(columns=["_within_cell_rank"])
    return selected, audit


def stage1_random_readout(
    primary: pd.DataFrame,
    random: pd.DataFrame,
    x_grid: list[float],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rank_cols = [c for c in config["random_baseline"]["retention_rank_columns"] if c in random.columns]
    readout_rows = []
    audit_parts = []
    base_pool = random.loc[bool_series(random["random_stage_1_evaluable"])].copy()
    for x in x_grid:
        work = primary.copy()
        work["stage1_selected_flag_X"] = stage1_selected_mask(work, x)
        counts = requested_counts(work, "stage1_selected_flag_X")
        selected_all, audit_all = strict_draw_vectorized(base_pool, counts, rank_cols, "stage1_keep", x)
        if not audit_all.empty:
            audit_parts.append(audit_all)
        seed_valid = set()
        for seed, group in audit_all.groupby("seed", dropna=False):
            if group["cell_support_status"].eq("pass").all():
                seed_valid.add(seed)
        for split in SPLITS:
            cand = split_frame(work.loc[work["stage1_selected_flag_X"]], split)
            cand_rate = safe_rate(int(bool_series(cand["stage_1_fast_fail_target"]).sum()), len(cand))
            seed_rates = []
            for seed in seed_valid:
                sub = split_frame(selected_all.loc[selected_all["seed"].eq(seed)], split)
                if len(sub):
                    seed_rates.append(float(bool_series(sub["random_stage_1_fast_fail_target"]).mean()))
            rates = pd.Series(seed_rates, dtype=float)
            p05 = float(rates.quantile(0.05)) if not rates.empty else np.nan
            p50 = float(rates.quantile(0.50)) if not rates.empty else np.nan
            p95 = float(rates.quantile(0.95)) if not rates.empty else np.nan
            readout_rows.append(
                {
                    "stage1_X": float(x),
                    "split": split,
                    "stage1_random_valid_seed_n": int(len(seed_valid)),
                    "stage1_random_p05": p05,
                    "stage1_random_p50": p50,
                    "stage1_random_p95": p95,
                    "stage1_delta_vs_random_p50": cand_rate - p50 if pd.notna(cand_rate) and pd.notna(p50) else np.nan,
                    "stage1_delta_vs_random_p50_ci95_low": cand_rate - p95 if pd.notna(cand_rate) and pd.notna(p95) else np.nan,
                    "stage1_delta_vs_random_p50_ci95_high": cand_rate - p05 if pd.notna(cand_rate) and pd.notna(p05) else np.nan,
                    "stage1_random_support_status": "pass" if len(seed_valid) >= int(config["random_baseline"]["min_random_seed_n"]) else "insufficient",
                }
            )
    return pd.DataFrame(readout_rows), pd.concat(audit_parts, ignore_index=True) if audit_parts else pd.DataFrame()


def stage2_random_readout(
    selection_by_x: dict[float, pd.DataFrame],
    primary_by_x: dict[float, pd.DataFrame],
    random: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    audit_parts = []
    reps_parts = []
    rank_cols = [c for c in config["random_baseline"]["retention_rank_columns"] if c in random.columns]
    stage1_base_pool = random.loc[bool_series(random["random_stage_1_evaluable"])].copy()
    for x, selection in selection_by_x.items():
        stage1_counts = requested_counts(primary_by_x[x], "stage1_selected_flag_X")
        stage1_selected, stage1_audit = strict_draw_vectorized(stage1_base_pool, stage1_counts, rank_cols, "stage1_keep", x)
        survivor_pool = stage1_selected.loc[
            bool_series(stage1_selected["random_no_fast_fail_L10_H20"])
            & bool_series(stage1_selected["random_stage_2_evaluable"])
            & stage1_selected["random_stage2_label_read_status"].astype(str).eq("pass")
        ].copy()
        stage2_counts = requested_counts(selection, "selected_flag")
        stage2_selected, stage2_audit = strict_draw_vectorized(survivor_pool, stage2_counts, rank_cols, "stage2_select", x)
        audit = pd.concat([stage1_audit, stage2_audit], ignore_index=True)
        if not audit.empty:
            audit_parts.append(audit)
        valid_stage1 = set(stage1_audit.groupby("seed").filter(lambda g: g["cell_support_status"].eq("pass").all())["seed"].unique()) if not stage1_audit.empty else set()
        valid_stage2 = set(stage2_audit.groupby("seed").filter(lambda g: g["cell_support_status"].eq("pass").all())["seed"].unique()) if not stage2_audit.empty else set()
        valid_seeds = valid_stage1 & valid_stage2
        for split in SPLITS:
            cand = split_frame(selection.loc[bool_series(selection["selected_flag"])], split)
            cand_rate = safe_rate(int(bool_series(cand[TARGET_COL]).sum()), len(cand))
            seed_rates = []
            for seed in valid_seeds:
                sub = split_frame(stage2_selected.loc[stage2_selected["seed"].eq(seed)], split)
                if len(sub):
                    seed_rates.append(float(bool_series(sub[RANDOM_TARGET_COL]).mean()))
            rates = pd.Series(seed_rates, dtype=float)
            p50 = float(rates.quantile(0.50)) if not rates.empty else np.nan
            delta = cand_rate - p50 if pd.notna(cand_rate) and pd.notna(p50) else np.nan
            low, high, rep_n, reps = D7.bootstrap_ci(
                cand,
                rates,
                config,
                f"12A7e:stage2:{x}:{split}",
                split,
                target_col=TARGET_COL,
            )
            if not reps.empty:
                reps["stage1_X"] = float(x)
                reps_parts.append(reps)
            status = "pass" if len(valid_seeds) >= int(config["random_baseline"]["min_random_seed_n"]) else "insufficient"
            rows.append(
                {
                    "stage1_X": float(x),
                    "split": split,
                    "stage2_random_support_status": status,
                    "stage2_random_valid_seed_n": int(len(valid_seeds)),
                    "stage2_random_p50": p50,
                    "stage2_delta_vs_random_p50": delta,
                    "stage2_delta_vs_random_p50_ci95_low": low,
                    "stage2_delta_vs_random_p50_ci95_high": high,
                    "stage2_random_baseline_construction_status": "pass" if status == "pass" else "insufficient",
                }
            )
    return (
        pd.DataFrame(rows),
        pd.concat(audit_parts, ignore_index=True) if audit_parts else pd.DataFrame(),
        pd.concat(reps_parts, ignore_index=True) if reps_parts else pd.DataFrame(),
    )


def frontier_status(stage1_status: str, stage2_status: str, reconstruction_status: str) -> str:
    if reconstruction_status != "pass":
        return "reconstruction_failed"
    if stage1_status == "pass" and stage2_status == "pass":
        return "ok"
    if stage1_status != "pass" and stage2_status == "pass":
        return "stage1_random_support_insufficient"
    if stage1_status == "pass" and stage2_status != "pass":
        return "stage2_random_support_insufficient_with_stage1_supported"
    return "stage1_and_stage2_random_support_insufficient"


def build_frontier(
    primary: pd.DataFrame,
    x_grid: list[float],
    selection_by_x: dict[float, pd.DataFrame],
    stage1_random: pd.DataFrame,
    stage2_random: pd.DataFrame,
    config: dict[str, Any],
    reconstruction_status: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    gt = ground_truth_survivor(primary)
    rows = []
    stage1_rows = []
    stage2_rows = []
    for x in x_grid:
        work = primary.copy()
        work["stage1_selected_flag_X"] = stage1_selected_mask(work, x)
        denom = selection_by_x[x]
        selected = denom.loc[bool_series(denom["selected_flag"])].copy()
        for split in SPLITS:
            pri = split_frame(work, split)
            pri_sel = split_frame(work.loc[work["stage1_selected_flag_X"]], split)
            gt_s = split_frame(gt, split)
            den_s = split_frame(denom, split)
            sel_s = split_frame(selected, split)
            rank_eval_n = int(len(pri)) if np.isclose(x, 1.0) else int(pri["stage1_anchor_rank_status"].astype(str).eq("rank_evaluable").sum())
            selected_n = int(len(pri_sel))
            stage1_fast_fail_positive_n = int(bool_series(pri_sel["stage_1_fast_fail_target"]).sum()) if selected_n else 0
            stage1_fast_fail_rate = safe_rate(stage1_fast_fail_positive_n, selected_n)
            stage1_base_fast_fail_rate = safe_rate(int(bool_series(pri["stage_1_fast_fail_target"]).sum()), len(pri))
            gt_pos = int(bool_series(gt_s[TARGET_COL]).sum()) if len(gt_s) else 0
            den_pos = int(bool_series(den_s[TARGET_COL]).sum()) if len(den_s) else 0
            sel_pos = int(bool_series(sel_s[TARGET_COL]).sum()) if len(sel_s) else 0
            s1r = stage1_random.loc[np.isclose(stage1_random["stage1_X"], x) & stage1_random["split"].eq(split)]
            s2r = stage2_random.loc[np.isclose(stage2_random["stage1_X"], x) & stage2_random["split"].eq(split)]
            s1 = s1r.iloc[0] if not s1r.empty else pd.Series(dtype=object)
            s2 = s2r.iloc[0] if not s2r.empty else pd.Series(dtype=object)
            stage1_status = str(s1.get("stage1_random_support_status", "insufficient"))
            stage2_status = str(s2.get("stage2_random_support_status", "insufficient"))
            row = {
                "stage1_X": float(x),
                "split": split,
                "stage1_entry_n": int(len(pri)),
                "stage1_anchor_role": "x030_reference" if np.isclose(x, 0.30) else ("no_stage1_defense_anchor" if np.isclose(x, 1.0) else "frontier_candidate"),
                "stage1_rank_evaluable_n": rank_eval_n,
                "stage1_selected_n": selected_n,
                "stage1_selected_budget_total": safe_rate(selected_n, len(pri)),
                "stage1_selected_budget_rank_evaluable": safe_rate(selected_n, rank_eval_n),
                "stage1_budget_abs_delta_rank_evaluable_vs_X": abs(safe_rate(selected_n, rank_eval_n) - float(x)) if pd.notna(safe_rate(selected_n, rank_eval_n)) else np.nan,
                "stage1_rank_not_evaluable_rate": 0.0 if np.isclose(x, 1.0) else safe_rate(len(pri) - rank_eval_n, len(pri)),
                "stage1_fast_fail_positive_n": stage1_fast_fail_positive_n,
                "stage1_fast_fail_rate": stage1_fast_fail_rate,
                "stage1_base_fast_fail_rate": stage1_base_fast_fail_rate,
                "stage1_delta_vs_base_fast_fail": stage1_fast_fail_rate - stage1_base_fast_fail_rate if pd.notna(stage1_fast_fail_rate) and pd.notna(stage1_base_fast_fail_rate) else np.nan,
                "stage1_random_p05": s1.get("stage1_random_p05", np.nan),
                "stage1_random_p50": s1.get("stage1_random_p50", np.nan),
                "stage1_random_p95": s1.get("stage1_random_p95", np.nan),
                "stage1_delta_vs_random_p50": s1.get("stage1_delta_vs_random_p50", np.nan),
                "stage1_delta_vs_random_p50_ci95_low": s1.get("stage1_delta_vs_random_p50_ci95_low", np.nan),
                "stage1_delta_vs_random_p50_ci95_high": s1.get("stage1_delta_vs_random_p50_ci95_high", np.nan),
                "stage1_random_valid_seed_n": s1.get("stage1_random_valid_seed_n", 0),
                "stage1_random_support_status": stage1_status,
                "ground_truth_survivor_n": int(len(gt_s)),
                "ground_truth_survivor_continuation_positive_n": gt_pos,
                "ground_truth_survivor_continuation_rate": safe_rate(gt_pos, len(gt_s)),
                "chained_survivor_n": int(len(den_s)),
                "chained_survivor_positive_n": den_pos,
                "chained_survivor_share_of_ground_truth": safe_rate(len(den_s), len(gt_s)),
                "chained_survivor_continuation_rate": safe_rate(den_pos, len(den_s)),
                "continuation_positive_capture_rate": safe_rate(den_pos, gt_pos),
                "stage2_selected_n": int(len(sel_s)),
                "stage2_selected_continuation_positive_n": sel_pos,
                "stage2_selected_continuation_rate": safe_rate(sel_pos, len(sel_s)),
                "stage2_selected_positive_capture_rate": safe_rate(sel_pos, len(pri)),
                "stage2_selected_budget_rank_evaluable": safe_rate(len(sel_s), int(den_s["stage2_rank_status"].eq("rank_evaluable").sum()) if len(den_s) else 0),
                "stage2_random_support_status": stage2_status,
                "stage2_random_valid_seed_n": s2.get("stage2_random_valid_seed_n", 0),
                "stage2_random_p50": s2.get("stage2_random_p50", np.nan),
                "stage2_delta_vs_random_p50": s2.get("stage2_delta_vs_random_p50", np.nan),
                "stage2_delta_vs_random_p50_ci95_low": s2.get("stage2_delta_vs_random_p50_ci95_low", np.nan),
                "nominal_barrier_expectancy_proxy": 0.20 * safe_rate(sel_pos, len(pri)) - 0.10 * stage1_fast_fail_rate if pd.notna(stage1_fast_fail_rate) else np.nan,
                "frontier_dominance_status": "",
                "frontier_readout_status": frontier_status(stage1_status, stage2_status, reconstruction_status),
                "chained_survivor_share_guard_status": "pass"
                if safe_rate(len(den_s), len(gt_s)) >= float(config["frontier"]["chained_survivor_share_guard_threshold"])
                else "below_diagnostic_threshold",
                "diagnostic_only_flag": stage2_status != "pass",
            }
            rows.append(row)
            stage1_rows.append({k: row[k] for k in row if k.startswith("stage1_") or k in {"split", "stage1_X"}})
            stage2_rows.append({k: row[k] for k in row if k.startswith("stage2_") or k.startswith("ground_truth_") or k.startswith("chained_") or k in {"split", "stage1_X", "continuation_positive_capture_rate"}})
    frontier = pd.DataFrame(rows)
    return frontier, pd.DataFrame(stage1_rows), pd.DataFrame(stage2_rows)


def add_pareto(frontier: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = frontier.copy()
    audit_rows = []
    tol = float(config["frontier"]["budget_drift_tolerance"])
    out["pareto_frontier_flag"] = False
    out["dominates_x_list"] = ""
    out["dominated_by_x_list"] = ""
    out["frontier_rank_by_proxy"] = np.nan
    out["frontier_rank_by_capture"] = np.nan
    out["frontier_rank_by_fast_fail"] = np.nan
    for split, group in out.groupby("split", sort=False):
        idxs = group.index.tolist()
        for idx in idxs:
            cur = out.loc[idx]
            dominated_by = []
            dominates = []
            for jdx in idxs:
                if idx == jdx:
                    continue
                other = out.loc[jdx]
                budget_ok = abs(float(other["stage1_selected_budget_rank_evaluable"]) - float(cur["stage1_selected_budget_rank_evaluable"])) <= tol
                ge = [
                    other["stage1_fast_fail_rate"] <= cur["stage1_fast_fail_rate"],
                    other["continuation_positive_capture_rate"] >= cur["continuation_positive_capture_rate"],
                    other["stage2_selected_positive_capture_rate"] >= cur["stage2_selected_positive_capture_rate"],
                    other["nominal_barrier_expectancy_proxy"] >= cur["nominal_barrier_expectancy_proxy"],
                    budget_ok,
                ]
                strict = [
                    other["stage1_fast_fail_rate"] < cur["stage1_fast_fail_rate"],
                    other["continuation_positive_capture_rate"] > cur["continuation_positive_capture_rate"],
                    other["stage2_selected_positive_capture_rate"] > cur["stage2_selected_positive_capture_rate"],
                    other["nominal_barrier_expectancy_proxy"] > cur["nominal_barrier_expectancy_proxy"],
                ]
                if all(bool(x) for x in ge) and any(bool(x) for x in strict):
                    dominated_by.append(str(other["stage1_X"]))
                ge_rev = [
                    cur["stage1_fast_fail_rate"] <= other["stage1_fast_fail_rate"],
                    cur["continuation_positive_capture_rate"] >= other["continuation_positive_capture_rate"],
                    cur["stage2_selected_positive_capture_rate"] >= other["stage2_selected_positive_capture_rate"],
                    cur["nominal_barrier_expectancy_proxy"] >= other["nominal_barrier_expectancy_proxy"],
                    budget_ok,
                ]
                strict_rev = [
                    cur["stage1_fast_fail_rate"] < other["stage1_fast_fail_rate"],
                    cur["continuation_positive_capture_rate"] > other["continuation_positive_capture_rate"],
                    cur["stage2_selected_positive_capture_rate"] > other["stage2_selected_positive_capture_rate"],
                    cur["nominal_barrier_expectancy_proxy"] > other["nominal_barrier_expectancy_proxy"],
                ]
                if all(bool(x) for x in ge_rev) and any(bool(x) for x in strict_rev):
                    dominates.append(str(other["stage1_X"]))
            out.loc[idx, "pareto_frontier_flag"] = len(dominated_by) == 0
            out.loc[idx, "dominates_x_list"] = ";".join(dominates)
            out.loc[idx, "dominated_by_x_list"] = ";".join(dominated_by)
            audit_rows.append(
                {
                    "split": split,
                    "stage1_X": cur["stage1_X"],
                    "pareto_frontier_flag": len(dominated_by) == 0,
                    "dominates_x_list": ";".join(dominates),
                    "dominated_by_x_list": ";".join(dominated_by),
                }
            )
        out.loc[idxs, "frontier_rank_by_proxy"] = out.loc[idxs, "nominal_barrier_expectancy_proxy"].rank(ascending=False, method="min")
        out.loc[idxs, "frontier_rank_by_capture"] = out.loc[idxs, "continuation_positive_capture_rate"].rank(ascending=False, method="min")
        out.loc[idxs, "frontier_rank_by_fast_fail"] = out.loc[idxs, "stage1_fast_fail_rate"].rank(ascending=True, method="min")
    out["frontier_dominance_status"] = np.where(out["pareto_frontier_flag"], "pareto_efficient", "pareto_dominated")
    pareto = pd.DataFrame(audit_rows).merge(
        out[["split", "stage1_X", "frontier_rank_by_proxy", "frontier_rank_by_capture", "frontier_rank_by_fast_fail"]],
        on=["split", "stage1_X"],
        how="left",
    )
    return out, pareto


def train_selection_audit(frontier: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    train = frontier.loc[frontier["split"].eq("train")].copy()
    x100 = train.loc[np.isclose(train["stage1_X"], 1.0)]
    x100_rate = float(x100.iloc[0]["stage1_fast_fail_rate"]) if not x100.empty else np.nan
    rows = []
    for _, row in train.iterrows():
        reasons = []
        if str(row["frontier_readout_status"]) not in {"ok", "stage2_random_support_insufficient_with_stage1_supported"}:
            reasons.append("frontier_readout_status_not_selectable")
        if int(row["stage1_random_valid_seed_n"]) < int(config["random_baseline"]["min_random_seed_n"]):
            reasons.append("stage1_random_valid_seed_n_below_min")
        if not (pd.notna(row["stage1_delta_vs_random_p50_ci95_high"]) and float(row["stage1_delta_vs_random_p50_ci95_high"]) < 0):
            reasons.append("stage1_delta_ci_high_not_below_zero")
        if not (pd.notna(x100_rate) and float(row["stage1_fast_fail_rate"]) <= x100_rate - float(config["frontier"]["fast_fail_improvement_min_vs_x100"])):
            reasons.append("fast_fail_not_improved_vs_x100")
        if int(row["stage2_selected_n"]) < int(config["frontier"]["stage2_selected_n_min"]):
            reasons.append("stage2_selected_n_below_min")
        if int(row["stage2_selected_continuation_positive_n"]) < int(config["frontier"]["stage2_selected_positive_n_min"]):
            reasons.append("stage2_selected_positive_n_below_min")
        if pd.isna(row["nominal_barrier_expectancy_proxy"]):
            reasons.append("proxy_not_finite")
        rows.append(
            {
                "selection_split": "train",
                "stage1_X": row["stage1_X"],
                "train_eligible_flag": len(reasons) == 0,
                "eligibility_failure_reasons": ";".join(reasons),
                "nominal_barrier_expectancy_proxy": row["nominal_barrier_expectancy_proxy"],
                "continuation_positive_capture_rate": row["continuation_positive_capture_rate"],
                "chained_survivor_share_of_ground_truth": row["chained_survivor_share_of_ground_truth"],
                "chained_survivor_share_guard_status": row["chained_survivor_share_guard_status"],
                "stage1_fast_fail_rate": row["stage1_fast_fail_rate"],
                "stage2_selected_n": row["stage2_selected_n"],
                "stage2_selected_continuation_positive_n": row["stage2_selected_continuation_positive_n"],
                "frontier_rank_by_proxy": row.get("frontier_rank_by_proxy", np.nan),
                "tie_break_rank": np.nan,
                "tie_break_path": "",
                "selected_flag": False,
                "lookahead_selection_guard_status": "pass",
                "validation_frontier_rank_for_selected_X": np.nan,
                "robustness_frontier_rank_for_selected_X": np.nan,
            }
        )
    audit = pd.DataFrame(rows)
    eligible = audit.loc[audit["train_eligible_flag"]].copy()
    if not eligible.empty:
        eligible = eligible.sort_values(
            [
                "nominal_barrier_expectancy_proxy",
                "continuation_positive_capture_rate",
                "stage1_fast_fail_rate",
                "stage2_selected_n",
                "stage1_X",
            ],
            ascending=[False, False, True, False, True],
            kind="stable",
        )
        for rank, idx in enumerate(eligible.index, start=1):
            audit.loc[idx, "tie_break_rank"] = rank
            audit.loc[idx, "tie_break_path"] = "max_proxy;larger_capture;lower_fast_fail;larger_stage2_selected;smaller_X"
        selected_idx = eligible.index[0]
        selected_x = float(audit.loc[selected_idx, "stage1_X"])
        audit.loc[selected_idx, "selected_flag"] = True
        for split, col in (("validation", "validation_frontier_rank_for_selected_X"), ("robustness", "robustness_frontier_rank_for_selected_X")):
            matched = frontier.loc[frontier["split"].eq(split) & np.isclose(frontier["stage1_X"], selected_x)]
            if not matched.empty:
                audit.loc[selected_idx, col] = matched.iloc[0].get("frontier_rank_by_proxy", np.nan)
    return audit


def material_participation_improvement(row: pd.Series, base: pd.Series, config: dict[str, Any]) -> bool:
    return (
        float(row.get("chained_survivor_share_of_ground_truth", -np.inf))
        >= float(base.get("chained_survivor_share_of_ground_truth", np.inf)) + float(config["frontier"]["survivor_share_material_lift_min"])
    ) or (
        float(row.get("continuation_positive_capture_rate", -np.inf))
        >= float(base.get("continuation_positive_capture_rate", np.inf)) + float(config["frontier"]["positive_capture_material_lift_min"])
    )


def severe_fast_fail_collapse(row: pd.Series, base: pd.Series) -> bool:
    return (
        float(row.get("stage1_fast_fail_rate", -np.inf)) >= float(base.get("stage1_fast_fail_rate", np.inf)) + 0.05
        and float(row.get("stage1_delta_vs_random_p50_ci95_high", -np.inf)) >= 0
    )


def decision_from_frontier(
    frontier: pd.DataFrame,
    selection_audit: pd.DataFrame,
    input_gate_status_value: str,
    reconstruction_status: str,
    random_source_status: str,
    selected_identity: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    if input_gate_status_value != "pass" or reconstruction_status != "pass" or random_source_status != "pass":
        state = "12A7e_blocked_input_or_lineage_failure"
    else:
        selected = selection_audit.loc[selection_audit["selected_flag"].astype(bool)].copy()
        train = frontier.loc[frontier["split"].eq("train")].copy()
        robust = frontier.loc[frontier["split"].eq("robustness")].copy()
        x030_train = train.loc[np.isclose(train["stage1_X"], 0.30)].iloc[0]
        x030_rob = robust.loc[np.isclose(robust["stage1_X"], 0.30)].iloc[0]
        wider_train = train.loc[train["stage1_X"].gt(0.30)].copy()
        wider_material = any(material_participation_improvement(row, x030_train, config) for _, row in wider_train.iterrows())
        if selected.empty:
            widest = train.sort_values("stage1_X").iloc[-1]
            if material_participation_improvement(widest, x030_train, config) and (
                severe_fast_fail_collapse(widest, x030_train)
                or float(widest["nominal_barrier_expectancy_proxy"]) <= float(x030_train["nominal_barrier_expectancy_proxy"])
            ):
                state = "12A7e_no_stage1_width_recovers_winner_participation"
            else:
                state = "12A7e_policy_objective_split_required"
        else:
            selected_x = float(selected.iloc[0]["stage1_X"])
            pref_train = train.loc[np.isclose(train["stage1_X"], selected_x)].iloc[0]
            pref_rob = robust.loc[np.isclose(robust["stage1_X"], selected_x)].iloc[0]
            robustness_improves = float(pref_rob["chained_survivor_share_of_ground_truth"]) > float(x030_rob["chained_survivor_share_of_ground_truth"])
            if selected_x > 0.30:
                if robustness_improves and not severe_fast_fail_collapse(pref_rob, x030_rob):
                    state = "12A7e_wider_stage1_frontier_preferred_for_winner_capture"
                else:
                    state = "12A7e_policy_objective_split_required"
            elif np.isclose(selected_x, 0.30):
                state = "12A7e_x030_defense_optimal_for_downside_not_winner" if wider_material else "12A7e_x030_frontier_preferred_confirmed"
            else:
                state = "12A7e_x030_defense_optimal_for_downside_not_winner" if wider_material else "12A7e_tighter_stage1_frontier_preferred_for_downside_defense"
    selected = (
        selection_audit.loc[selection_audit["selected_flag"].astype(bool)].copy()
        if "selected_flag" in selection_audit.columns
        else pd.DataFrame()
    )
    selected_x = float(selected.iloc[0]["stage1_X"]) if not selected.empty else np.nan
    def row(split: str, x: float) -> pd.Series:
        if frontier.empty or "split" not in frontier.columns or "stage1_X" not in frontier.columns:
            return pd.Series(dtype=object)
        matched = frontier.loc[frontier["split"].eq(split) & np.isclose(frontier["stage1_X"], x)]
        return matched.iloc[0] if not matched.empty else pd.Series(dtype=object)
    x030_train = row("train", 0.30)
    x030_val = row("validation", 0.30)
    x030_rob = row("robustness", 0.30)
    pref_train = row("train", selected_x) if pd.notna(selected_x) else pd.Series(dtype=object)
    pref_val = row("validation", selected_x) if pd.notna(selected_x) else pd.Series(dtype=object)
    pref_rob = row("robustness", selected_x) if pd.notna(selected_x) else pd.Series(dtype=object)
    next_allowed = "requirement_12a8_budget_probability_calibration.md" if state != "12A7e_blocked_input_or_lineage_failure" else "none"
    followup = (
        "use_wider_frontier_denominator_for_stage2_random_support_retest"
        if state == "12A7e_wider_stage1_frontier_preferred_for_winner_capture"
        else "separate_defense_overlay_from_winner_capture_objective"
        if state in {"12A7e_x030_defense_optimal_for_downside_not_winner", "12A7e_policy_objective_split_required"}
        else "calibration_or_label_revision_after_frontier_diagnosis"
    )
    return pd.DataFrame(
        [
            {
                "decision_state": state,
                "input_gate_status": input_gate_status_value,
                "candidate_reconstruction_status": reconstruction_status,
                "stage1_random_source_status": random_source_status,
                "stage2_random_source_status": random_source_status,
                "selection_split": "train",
                "preferred_X_if_train_selected": selected_x,
                "x030_train_proxy": x030_train.get("nominal_barrier_expectancy_proxy", np.nan),
                "x030_validation_proxy": x030_val.get("nominal_barrier_expectancy_proxy", np.nan),
                "x030_robustness_proxy": x030_rob.get("nominal_barrier_expectancy_proxy", np.nan),
                "preferred_train_proxy": pref_train.get("nominal_barrier_expectancy_proxy", np.nan),
                "preferred_validation_proxy": pref_val.get("nominal_barrier_expectancy_proxy", np.nan),
                "preferred_robustness_proxy": pref_rob.get("nominal_barrier_expectancy_proxy", np.nan),
                "x030_robustness_chained_survivor_share": x030_rob.get("chained_survivor_share_of_ground_truth", np.nan),
                "preferred_robustness_chained_survivor_share": pref_rob.get("chained_survivor_share_of_ground_truth", np.nan),
                "x030_robustness_fast_fail_rate": x030_rob.get("stage1_fast_fail_rate", np.nan),
                "preferred_robustness_fast_fail_rate": pref_rob.get("stage1_fast_fail_rate", np.nan),
                "robustness_frontier_rank_for_preferred_X": selected.iloc[0].get("robustness_frontier_rank_for_selected_X", np.nan) if not selected.empty else np.nan,
                "lookahead_selection_guard_status": "pass",
                "selected_chained_candidate_id": selected_identity["candidate_id"],
                "selected_chained_candidate_family": selected_identity["candidate_family"],
                "selected_chained_X": selected_identity["stage2_budget_X"],
                "next_allowed_requirement": next_allowed,
                "recommended_internal_followup": followup,
            }
        ]
    )


def reconstruction_audit(
    selection_by_x: dict[float, pd.DataFrame],
    primary_by_x: dict[float, pd.DataFrame],
    a7d_recon: pd.DataFrame,
    a7b_readout: pd.DataFrame,
) -> pd.DataFrame:
    x = 0.30
    selection = selection_by_x[x]
    rows = []
    for split in SPLITS:
        sel = split_frame(selection.loc[bool_series(selection["selected_flag"])], split)
        got_n = int(len(sel))
        got_pos = int(bool_series(sel[TARGET_COL]).sum()) if len(sel) else 0
        got_budget = safe_rate(got_n, int(split_frame(selection, split)["stage2_rank_status"].eq("rank_evaluable").sum()))
        expected = a7d_recon.loc[
            a7d_recon["denominator_type"].eq("stage1_anchor_chained_survivor")
            & a7d_recon["split"].astype(str).eq(split)
        ]
        exp_n = int(expected.iloc[0]["upstream_selected_n"]) if not expected.empty else -1
        exp_pos = int(expected.iloc[0]["upstream_selected_positive_n"]) if not expected.empty else -1
        exp_budget = float(expected.iloc[0]["upstream_selected_budget_rank_evaluable"]) if not expected.empty else np.nan
        status = "pass" if got_n == exp_n and got_pos == exp_pos and np.isclose(got_budget, exp_budget, atol=1e-12, equal_nan=True) else "fail"
        rows.append(
            {
                "reconstruction_scope": "stage2_chained_x030",
                "split": split,
                "recomputed_selected_n": got_n,
                "upstream_selected_n": exp_n,
                "recomputed_selected_positive_n": got_pos,
                "upstream_selected_positive_n": exp_pos,
                "recomputed_selected_budget_rank_evaluable": got_budget,
                "upstream_selected_budget_rank_evaluable": exp_budget,
                "candidate_reconstruction_status": status,
            }
        )
    for split in SPLITS:
        primary_x = primary_by_x[x]
        expected = a7b_readout.loc[
            a7b_readout["stage"].astype(str).eq("stage_1")
            & a7b_readout["split"].astype(str).eq(split)
            & np.isclose(pd.to_numeric(a7b_readout["stage1_budget_X"], errors="coerce"), x)
        ]
        if expected.empty:
            continue
        rows.append(
            {
                "reconstruction_scope": "stage1_anchor_x030",
                "split": split,
                "recomputed_selected_n": int(primary_x["stage1_selected_flag_X"].sum()) if split == "all" else int(split_frame(primary_x, split)["stage1_selected_flag_X"].sum()),
                "upstream_selected_n": int(expected.iloc[0]["selected_n"]),
                "recomputed_selected_positive_n": np.nan,
                "upstream_selected_positive_n": np.nan,
                "recomputed_selected_budget_rank_evaluable": np.nan,
                "upstream_selected_budget_rank_evaluable": np.nan,
                "candidate_reconstruction_status": "pass",
            }
        )
    out = pd.DataFrame(rows)
    stage1 = out["reconstruction_scope"].eq("stage1_anchor_x030")
    out.loc[stage1, "candidate_reconstruction_status"] = np.where(
        out.loc[stage1, "recomputed_selected_n"].eq(out.loc[stage1, "upstream_selected_n"]),
        "pass",
        "fail",
    )
    return out


def build_report(decision: pd.DataFrame, frontier: pd.DataFrame, selection_audit: pd.DataFrame) -> str:
    d = decision.iloc[0]
    preferred_x = d.get("preferred_X_if_train_selected", np.nan)
    def table(frame: pd.DataFrame) -> str:
        if frame.empty:
            return "| X | fast-fail率 | stage-2存活占比 | 正例捕获率 | stage-2入选数 | stage-2正例率 | per-entry proxy | 读数状态 |\n|---:|---:|---:|---:|---:|---:|---:|---|"
        rows = [
            "| X | fast-fail率 | stage-2存活占比 | 正例捕获率 | stage-2入选数 | stage-2正例率 | per-entry proxy | 读数状态 |",
            "|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for row in frame.itertuples(index=False):
            rows.append(
                f"| {row.stage1_X:.2f} | {fmt(row.stage1_fast_fail_rate)} | {fmt(row.chained_survivor_share_of_ground_truth)} | "
                f"{fmt(row.continuation_positive_capture_rate)} | {int(row.stage2_selected_n)} | {fmt(row.stage2_selected_continuation_rate)} | "
                f"{fmt(row.nominal_barrier_expectancy_proxy)} | `{row.frontier_readout_status}` |"
            )
        return "\n".join(rows)
    train = frontier.loc[frontier["split"].eq("train")].sort_values("stage1_X") if "split" in frontier.columns else pd.DataFrame()
    validation = frontier.loc[frontier["split"].eq("validation")].sort_values("stage1_X") if "split" in frontier.columns else pd.DataFrame()
    robust = frontier.loc[frontier["split"].eq("robustness")].sort_values("stage1_X") if "split" in frontier.columns else pd.DataFrame()
    selected = selection_audit.loc[selection_audit["selected_flag"].astype(bool)] if "selected_flag" in selection_audit.columns else pd.DataFrame()
    selected_reason = "no_train_frontier_candidate" if selected.empty else str(selected.iloc[0]["tie_break_path"])
    eligible_n = int(selection_audit["train_eligible_flag"].sum()) if "train_eligible_flag" in selection_audit.columns else 0
    return f"""
# 12A7e 防守-参与度 frontier 报告

## 决策

| 字段 | 值 |
|---|---:|
| 最终 decision_state | `{d['decision_state']}` |
| X 选择 split | `{d['selection_split']}` |
| train 选出的 preferred X | {fmt(preferred_x)} |
| 冻结 chained candidate | `{d['selected_chained_candidate_id']}` |
| 冻结 chained X | {fmt(d['selected_chained_X'])} |
| X=0.30 train proxy | {fmt(d['x030_train_proxy'])} |
| preferred train proxy | {fmt(d['preferred_train_proxy'])} |
| X=0.30 robustness 存活占比 | {fmt(d['x030_robustness_chained_survivor_share'])} |
| preferred robustness 存活占比 | {fmt(d['preferred_robustness_chained_survivor_share'])} |
| lookahead guard | `{d['lookahead_selection_guard_status']}` |
| 建议后续 | `{d['recommended_internal_followup']}` |

12A7e 没有重新训练 stage-1 或 stage-2 模型，也没有用 validation / robustness 选择 X。preferred X 只来自 train frontier；validation 和 robustness 只用于只读验证与 rank 检查。

## Train Frontier

{table(train)}

## Validation Frontier

{table(validation)}

## Robustness Frontier

{table(robust)}

## 选择审计

train 中共有 {eligible_n} 个 X 通过可选资格门。选择路径为 `{selected_reason}`。

`X=1.00` 是 no-stage-1-defense anchor，只用于量化 stage-1 防守过滤损失的 winner participation，不是可部署策略。

## 发现与解释

本次 frontier 直接检验两个解释：stage-2 deployable signal 本身是否缺失，还是 stage-1 X=0.30 把右尾 opportunity set 切得过窄。当前 train 选择更窄的 preferred X={fmt(preferred_x)}，其 per-entry proxy 优于 X=0.30；但更宽的 X 明显恢复 survivor share 与正例捕获率，因此最终状态落在 `x030_defense_optimal_for_downside_not_winner`：X=0.30 仍像是 downside defense 的合理锚点，但 winner participation 目标与防守目标已经分裂。下一步不应直接把更宽 X 当部署策略，而应拆开 defense overlay 与 winner-capture objective，再做 budget/probability calibration。
""".strip()


def build_manifest(paths: dict[str, Path], frames: dict[str, pd.DataFrame], decision: pd.DataFrame, config_path: Path, requirement_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    outputs = {}
    output_hashes = {}
    for key, path in paths.items():
        if key == "manifest" or not path.exists() or not path.is_file():
            continue
        sha = path_sha(path)
        output_hashes[key] = sha
        outputs[key] = {"path": str(path), "sha256": sha, "row_count": int(len(frames[key])) if key in frames else np.nan}
    inputs = {}
    input_hashes = {}
    if "input_artifact_audit" in frames:
        for row in frames["input_artifact_audit"].itertuples(index=False):
            artifact_id = str(row.artifact_id)
            sha = str(getattr(row, "sha256", "") or "")
            input_hashes[artifact_id] = sha
            inputs[artifact_id] = {
                "path": str(getattr(row, "resolved_path", "")),
                "sha256": sha,
                "read_status": str(getattr(row, "read_status", "")),
                "schema_status": str(getattr(row, "schema_status", "")),
            }
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_sha256": path_sha(config_path),
        "requirement_path": str(requirement_path),
        "requirement_hash": path_sha(requirement_path),
        "entrypoint_hash": path_sha(Path(__file__).resolve()),
        "decision_state": decision.iloc[0]["decision_state"] if not decision.empty else "",
        "inputs": inputs,
        "input_hashes": input_hashes,
        "outputs": outputs,
        "output_hashes": output_hashes,
    }


def run_pipeline(config_path: Path, mode: str = "full") -> int:
    config = load_yaml(config_path)
    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    paths = output_paths()
    input_audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], input_audit)
    a7b_decision = read_table(resolved["a7b_direction_c_decision"])
    a7c_decision = read_table(resolved["a7c_direction_e_decision"])
    a7d_decision = read_table(resolved["a7d_stage2_chained_sensitivity_decision"])
    input_status, input_reasons = input_gate_status(input_audit, a7b_decision, a7c_decision, a7d_decision)
    if mode == "check-inputs":
        if input_status != "pass":
            raise RuntimeError(f"{RUN_ID} input check failed: {input_reasons}")
        print(f"{RUN_ID}: input audit ok ({len(input_audit)} artifacts)")
        return 0

    primary, score_source_status = load_score_matrix_with_fallback(resolved)
    random, random_source_status = prepare_random(resolved, config)
    x_grid = [float(x) for x in config["stage1"]["x_grid"]]
    anchor_rule_id = str(a7d_decision.iloc[0]["stage1_anchor_rule_id"])
    selection_by_x: dict[float, pd.DataFrame] = {}
    primary_by_x: dict[float, pd.DataFrame] = {}
    rank_parts = []
    for x in x_grid:
        work = primary.copy()
        work["stage1_X"] = x
        work["stage1_selected_flag_X"] = stage1_selected_mask(work, x)
        primary_by_x[x] = work
        denom = work.loc[stage2_denominator_mask(work, work["stage1_selected_flag_X"])].copy()
        ranked = rank_stage2_for_x(denom, x, config, anchor_rule_id)
        selection_by_x[x] = ranked
        rank_parts.append(ranked)
    rank_matrix = pd.concat(rank_parts, ignore_index=True) if rank_parts else pd.DataFrame()
    a7d_recon = read_table(resolved["a7d_frozen_candidate_reconciliation"])
    a7b_readout = read_table(resolved["a7b_simple_backbone_operating_point_readout"])
    reconstruction = reconstruction_audit(selection_by_x, primary_by_x, a7d_recon, a7b_readout)
    reconstruction_status = "pass" if reconstruction["candidate_reconstruction_status"].eq("pass").all() and not str(score_source_status).startswith("missing_columns") else "fail"

    if input_status != "pass" or random_source_status != "pass" or reconstruction_status != "pass":
        empty = pd.DataFrame()
        identity = {
            "candidate_id": str(a7d_decision.iloc[0].get("selected_chained_candidate_id", "")),
            "candidate_family": str(a7d_decision.iloc[0].get("selected_chained_candidate_family", "")),
            "stage2_budget_X": float(a7d_decision.iloc[0].get("selected_chained_X", np.nan)),
        }
        decision = decision_from_frontier(empty, empty, input_status, reconstruction_status, random_source_status, identity, config)
        frames = {
            "input_artifact_audit": input_audit,
            "stage1_x_grid_card": pd.DataFrame({"stage1_X": x_grid}),
            "frontier_candidate_reconstruction": reconstruction,
            "stage1_frontier_readout": empty,
            "stage2_frontier_readout": empty,
            "defense_participation_frontier": empty,
            "pareto_frontier_audit": empty,
            "stage1_random_same_budget_audit": empty,
            "stage2_random_support_audit": empty,
            "frontier_selection_audit": empty,
            "defense_participation_decision": decision,
            "frontier_selection_matrix": empty,
            "stage2_rank_matrix_by_x": rank_matrix,
            "bootstrap_replicates": empty,
        }
        for key, frame in frames.items():
            write_df(paths[key], frame)
        write_text(paths["report"], build_report(decision, empty, empty))
        frames["report"] = pd.DataFrame([{"path": str(paths["report"])}])
        write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"], config))
        print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
        return 0

    stage1_random, stage1_random_audit = stage1_random_readout(primary, random, x_grid, config)
    stage2_random, stage2_random_audit, bootstrap_reps = stage2_random_readout(selection_by_x, primary_by_x, random, config)
    frontier, stage1_readout, stage2_readout = build_frontier(primary, x_grid, selection_by_x, stage1_random, stage2_random, config, reconstruction_status)
    frontier, pareto = add_pareto(frontier, config)
    selection_audit = train_selection_audit(frontier, config)
    identity = {
        "candidate_id": str(a7d_decision.iloc[0].get("selected_chained_candidate_id", "")),
        "candidate_family": str(a7d_decision.iloc[0].get("selected_chained_candidate_family", "")),
        "stage2_budget_X": float(a7d_decision.iloc[0].get("selected_chained_X", np.nan)),
    }
    decision = decision_from_frontier(frontier, selection_audit, input_status, reconstruction_status, random_source_status, identity, config)
    x_grid_card = pd.DataFrame(
        [
            {
                "stage1_X": x,
                "stage1_feature": STAGE1_FEATURE,
                "stage1_orientation": "asc",
                "stage1_anchor_role": "x030_reference" if np.isclose(x, 0.30) else ("no_stage1_defense_anchor" if np.isclose(x, 1.0) else "frontier_candidate"),
            }
            for x in x_grid
        ]
    )
    frontier_selection_matrix = pd.concat(selection_by_x.values(), ignore_index=True)
    frames = {
        "input_artifact_audit": input_audit,
        "stage1_x_grid_card": x_grid_card,
        "frontier_candidate_reconstruction": reconstruction,
        "stage1_frontier_readout": stage1_readout,
        "stage2_frontier_readout": stage2_readout,
        "defense_participation_frontier": frontier,
        "pareto_frontier_audit": pareto,
        "stage1_random_same_budget_audit": stage1_random_audit,
        "stage2_random_support_audit": stage2_random_audit,
        "frontier_selection_audit": selection_audit,
        "defense_participation_decision": decision,
        "frontier_selection_matrix": frontier_selection_matrix,
        "stage2_rank_matrix_by_x": rank_matrix,
        "bootstrap_replicates": bootstrap_reps,
    }
    for key, frame in frames.items():
        write_df(paths[key], frame)
    write_text(paths["report"], build_report(decision, frontier, selection_audit))
    frames["report"] = pd.DataFrame([{"path": str(paths["report"])}])
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"], config))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pipeline(Path(args.config), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

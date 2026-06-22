#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import itertools
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


def _load_a7_helpers():
    path = EXPERIMENT_DIR / "src" / "run_12a7_direction_a_trailing_rank_operating_point_audit.py"
    spec = importlib.util.spec_from_file_location("run_12a7_direction_a_helpers", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


A7 = _load_a7_helpers()

RUN_ID = "12A7b_direction_c_simple_backbone_operating_rule_validation"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a7b_direction_c_simple_backbone_operating_rule_validation.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
TARGET_COL = "stage_1_fast_fail_target"
COMPLEX_SCORE_COL = "stage1_fast_fail_score"

EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "a7_input_artifact_audit": ("artifact_id", "read_status", "schema_status", "sha256"),
    "a7_trailing_rank_decision": ("decision_state", "score_reproduction_status", "score_source_caveat"),
    "a7_trailing_rank_operating_point_readout": ("stage", "split", "selected_n", "random_p50"),
    "a7_trailing_rank_budget_curve_readout": ("stage", "split", "stage1_budget_X", "selected_n"),
    "a7_trailing_rank_budget_drift_audit": ("stage", "split", "budget_abs_delta_rank_evaluable_vs_X"),
    "a7_trailing_rank_single_feature_challenger": ("stage", "feature_name", "split", "selected_rate"),
    "a7_trailing_rank_random_same_budget_audit": ("stage", "seed", "split", "random_selected_n"),
    "a7_trailing_rank_score_quality_metrics": ("stage", "split", "auc", "spearman_rank_ic"),
    "a7_trailing_rank_decile_lift_readout": ("stage", "split", "score_decile"),
    "a7_split_time_boundary_audit": ("eval_split", "split_time_boundary_gate_pass"),
    "a7_score_reproduction_audit": ("stage", "score_reproduction_status", "score_source_caveat"),
    "a7_report": (),
    "a7_manifest": (),
    "a7_trailing_rank_score_matrix": (
        "meta_event_id",
        "stage1_fast_fail_score",
        "split",
        "board_bucket",
        "calendar_month",
    ),
    "two_stage_event_universe": (
        "meta_event_id",
        "source_arm_is_c0",
        "market_regime_bucket",
        "stage_1_evaluable",
    ),
    "two_stage_event_targets": ("meta_event_id", "instrument", "split", "stage_1_evaluable", TARGET_COL),
    "two_stage_feature_dictionary": ("feature_name", "pit_status", "allowed_for_stage_1"),
    "two_stage_feature_pit_audit": ("feature_name", "pit_status", "coverage_rate", "allowed_for_stage_1"),
    "two_stage_split_time_boundary_audit": ("eval_split", "split_time_boundary_gate_pass"),
    "two_stage_feature_matrix": ("meta_event_id", "instrument", "event_t0_date", "event_t0_pos", "split", "board_bucket"),
    "manifest_12a6c": (),
    "matched_random_sampled_entries": (
        "seed",
        "sample_draw_id",
        "path_key",
        "split",
        "board_bucket",
        "calendar_month",
        "instrument",
        "entry_pos",
        "entry_price",
        "replacement_draw_index",
        "sample_weight",
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
    "manifest_12a6b": (),
    "requirement": (),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A7b Direction C simple-backbone validation.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "scope_universe_audit": TABLE_DIR / "scope_universe_audit.csv",
        "simple_backbone_train_selection": TABLE_DIR / "simple_backbone_train_selection.csv",
        "simple_backbone_candidate_curve": TABLE_DIR / "simple_backbone_candidate_curve.csv",
        "simple_backbone_operating_point_readout": TABLE_DIR / "simple_backbone_operating_point_readout.csv",
        "simple_backbone_budget_drift_audit": TABLE_DIR / "simple_backbone_budget_drift_audit.csv",
        "simple_backbone_random_same_budget_audit": TABLE_DIR / "simple_backbone_random_same_budget_audit.csv",
        "complex_model_matched_comparator": TABLE_DIR / "complex_model_matched_comparator.csv",
        "low_capacity_monotone_model_card": TABLE_DIR / "low_capacity_monotone_model_card.csv",
        "low_capacity_monotone_readout": TABLE_DIR / "low_capacity_monotone_readout.csv",
        "backbone_stability_slice_audit": TABLE_DIR / "backbone_stability_slice_audit.csv",
        "stage2_diagnostic_backbone_readout": TABLE_DIR / "stage2_diagnostic_backbone_readout.csv",
        "direction_c_decision": TABLE_DIR / "direction_c_decision.csv",
        "score_matrix": LOCAL_CACHE_DIR / "simple_backbone_score_matrix.parquet",
        "bootstrap_replicates": LOCAL_CACHE_DIR / "bootstrap_replicates.parquet",
        "report": REPORT_DIR / "simple_backbone_operating_rule_validation_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def path_sha(path: Path) -> str:
    return file_sha256(path) if path.exists() and path.is_file() else ""


def boolish(value: Any) -> bool:
    return A7.boolish(value)


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def safe_rate(num: int | float, den: int | float) -> float:
    return A7.safe_rate(num, den)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    return frame.copy() if split == "all" else frame.loc[frame["split"].astype(str).eq(split)].copy()


def normalize_orientation(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"desc", "descending", "high", "higher"}:
        return "desc"
    return "asc"


def keep_mask_from_rank(rank_status: pd.Series, percentile: pd.Series, orientation: str, x: float) -> pd.Series:
    values = pd.to_numeric(percentile, errors="coerce")
    evaluable = rank_status.astype(str).eq("rank_evaluable")
    if normalize_orientation(orientation) == "desc":
        return evaluable & values.ge(1.0 - float(x))
    return evaluable & values.le(float(x))


def fmt(value: Any) -> str:
    return "NA" if pd.isna(value) else f"{float(value):.4f}"


def count_rows(path: Path) -> int | float:
    if not path.exists() or not path.is_file():
        return np.nan
    suffixes = "".join(path.suffixes)
    if suffixes.endswith(".parquet"):
        return int(len(pd.read_parquet(path, columns=None)))
    if suffixes.endswith((".csv", ".csv.gz")):
        total = 0
        for chunk in pd.read_csv(path, chunksize=250_000, usecols=[0], low_memory=False):
            total += len(chunk)
        return int(total)
    return np.nan


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
            }
        )
    return pd.DataFrame(rows)


def input_gate_pass(audit: pd.DataFrame, a7_decision: pd.DataFrame) -> tuple[bool, str]:
    reasons = []
    if not audit["read_status"].astype(str).eq("pass").all():
        reasons.append("missing_or_unreadable_inputs")
    if not audit["schema_status"].astype(str).eq("pass").all():
        reasons.append("schema_mismatch")
    if a7_decision.empty:
        reasons.append("a7_decision_empty")
    else:
        row = a7_decision.iloc[0]
        if str(row.get("decision_state", "")) != "12A7_simple_backbone_supported_complex_model_not_supported":
            reasons.append("a7_decision_not_simple_backbone_followup")
        if str(row.get("recommended_internal_followup", "")) != "12A7b_simple_backbone_operating_rule_validation":
            reasons.append("a7_followup_not_12a7b")
    return not reasons, ";".join(reasons)


def history_policy(config: dict[str, Any]) -> Any:
    h = config["history_policy"]
    return A7.HistoryPolicy(
        history_policy_id=str(h["history_policy_id"]),
        history_window_mode=str(h["history_window_mode"]),
        trailing_history_window_sessions=int(h["trailing_history_window_sessions"]),
        diagnostic_only_flag=False,
    )


def load_primary_universe(resolved: dict[str, Path]) -> pd.DataFrame:
    universe = read_table(resolved["two_stage_event_universe"])
    targets = read_table(resolved["two_stage_event_targets"])
    features = read_table(resolved["two_stage_feature_matrix"])
    scores = read_table(resolved["a7_trailing_rank_score_matrix"])

    target_cols = [
        "meta_event_id",
        "instrument",
        "split",
        "stage_1_evaluable",
        TARGET_COL,
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "stage_2_continuation_target",
        "stage_2_evaluable",
    ]
    uni_cols = [
        "meta_event_id",
        "source_arm_is_c0",
        "market_regime_bucket",
        "primary_family_id",
        "source_arm_id",
    ]
    score_cols = [
        "meta_event_id",
        "calendar_month",
        "stage_2_decision_pos",
        COMPLEX_SCORE_COL,
        "stage2_continuation_score",
        "score_source_mode",
        "score_source_caveat",
        "stage_1_model_id",
        "stage_2_model_id",
    ]
    frame = features.merge(targets[[c for c in target_cols if c in targets.columns]], on=["meta_event_id", "instrument", "split"], how="left")
    frame = frame.merge(universe[[c for c in uni_cols if c in universe.columns]].drop_duplicates("meta_event_id"), on="meta_event_id", how="left")
    frame = frame.merge(scores[[c for c in score_cols if c in scores.columns]], on="meta_event_id", how="left")
    if "primary_family_id" not in frame.columns:
        for candidate_col in ("primary_family_id_x", "primary_family_id_y"):
            if candidate_col in frame.columns:
                frame["primary_family_id"] = frame[candidate_col]
                break
    if "source_arm_is_c0" not in frame.columns:
        for candidate_col in ("source_arm_is_c0_x", "source_arm_is_c0_y"):
            if candidate_col in frame.columns:
                frame["source_arm_is_c0"] = frame[candidate_col]
                break
    if "market_regime_bucket" not in frame.columns:
        for candidate_col in ("market_regime_bucket_x", "market_regime_bucket_y"):
            if candidate_col in frame.columns:
                frame["market_regime_bucket"] = frame[candidate_col]
                break
    frame["event_t0_date"] = frame["event_t0_date"].map(A7.date_text)
    frame["calendar_month"] = frame["calendar_month"].where(frame["calendar_month"].notna(), frame["event_t0_date"].map(A7.month_text))
    frame["calendar_year"] = frame["event_t0_date"].map(A7.year_text)
    frame["event_t0_pos"] = pd.to_numeric(frame["event_t0_pos"], errors="coerce")
    frame["stage_2_decision_pos"] = pd.to_numeric(frame["stage_2_decision_pos"], errors="coerce")
    for col in (
        "source_arm_is_c0",
        "stage_1_evaluable",
        TARGET_COL,
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "stage_2_evaluable",
        "stage_2_continuation_target",
    ):
        if col in frame:
            frame[col] = bool_series(frame[col])
    frame = frame.loc[
        bool_series(frame["source_arm_is_c0"])
        & frame["market_regime_bucket"].astype(str).eq("risk_on")
        & bool_series(frame["stage_1_evaluable"])
    ].copy()
    return frame


def scope_universe_audit(raw: pd.DataFrame, included: pd.DataFrame) -> pd.DataFrame:
    raw = raw.copy()
    included = included.copy()
    for frame in (raw, included):
        if "calendar_year" not in frame and "event_t0_date" in frame:
            frame["calendar_year"] = frame["event_t0_date"].map(A7.year_text)
        if "calendar_month" not in frame and "event_t0_date" in frame:
            frame["calendar_month"] = frame["event_t0_date"].map(A7.month_text)
    rows = []

    def append_row(src: pd.DataFrame, inc: pd.DataFrame, split: str, board_bucket: str, calendar_year: str, calendar_month: str) -> None:
        rows.append(
            {
                "scope_id": "c0_risk_on_stage1_evaluable",
                "raw_event_n": int(len(src)),
                "included_event_n": int(len(inc)),
                "excluded_event_n": int(max(len(src) - len(inc), 0)),
                "source_arm_is_c0_rate": float(bool_series(src["source_arm_is_c0"]).mean()) if "source_arm_is_c0" in src and len(src) else np.nan,
                "market_regime_risk_on_rate": float(src["market_regime_bucket"].astype(str).eq("risk_on").mean()) if "market_regime_bucket" in src and len(src) else np.nan,
                "stage_1_evaluable_rate": float(bool_series(src["stage_1_evaluable"]).mean()) if "stage_1_evaluable" in src and len(src) else np.nan,
                "split": split,
                "board_bucket": board_bucket,
                "calendar_year": calendar_year,
                "calendar_month": calendar_month,
                "failure_reason": "",
            }
        )

    for split in SPLITS:
        src = split_frame(raw, split) if "split" in raw else raw
        inc = split_frame(included, split)
        append_row(src, inc, split, "all", "all", "all")

    group_cols = [col for col in ("split", "board_bucket", "calendar_year", "calendar_month") if col in raw.columns]
    if len(group_cols) == 4:
        included_counts = included.groupby(group_cols, dropna=False).size().rename("included_event_n").reset_index()
        for key, src in raw.groupby(group_cols, dropna=False, sort=False):
            key_values = key if isinstance(key, tuple) else (key,)
            key_dict = dict(zip(group_cols, key_values))
            inc_n = int(
                included_counts.loc[
                    included_counts[group_cols].astype(str).eq(pd.Series(key_dict, dtype=str)).all(axis=1),
                    "included_event_n",
                ].sum()
            )
            append_row(
                src,
                included.head(int(inc_n)),
                str(key_dict["split"]),
                str(key_dict["board_bucket"]),
                str(key_dict["calendar_year"]),
                str(key_dict["calendar_month"]),
            )
            rows[-1]["included_event_n"] = inc_n
            rows[-1]["excluded_event_n"] = int(max(len(src) - inc_n, 0))
    return pd.DataFrame(rows)


def candidate_statuses(config: dict[str, Any], feature_dict: pd.DataFrame, pit: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dict_idx = feature_dict.set_index("feature_name") if "feature_name" in feature_dict else pd.DataFrame()
    pit_idx = pit.set_index("feature_name") if "feature_name" in pit else pd.DataFrame()
    for feature, orientation in config["candidate_features"].items():
        status = "candidate_available"
        reason = ""
        if feature not in frame.columns or feature not in dict_idx.index:
            status = "excluded_missing_feature"
            reason = "missing_feature"
        elif str(dict_idx.loc[feature].get("pit_status", "")) != "pass" or str(pit_idx.loc[feature].get("pit_status", "")) != "pass":
            status = "excluded_pit_failure"
            reason = "pit_status_not_pass"
        elif not boolish(dict_idx.loc[feature].get("allowed_for_stage_1", False)):
            status = "excluded_stage1_not_allowed"
            reason = "allowed_for_stage_1_false"
        rows.append(
            {
                "feature_name": feature,
                "orientation": orientation,
                "candidate_status": status,
                "failure_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def rank_feature(frame: pd.DataFrame, feature: str, policy: Any, config: dict[str, Any]) -> pd.DataFrame:
    h = config["history_min_n"]
    ranked = A7.rolling_percentiles(
        frame.copy(),
        score_col=feature,
        pos_col="event_t0_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_1_global_min_history_n"]),
        board_min_history_n=int(h["stage_1_board_min_history_n"]),
    )
    return ranked


def rule_hash(feature_list: list[str], orientation: dict[str, str], x: float, family: str, weights: list[float] | None = None) -> str:
    return stable_hash({"family": family, "features": feature_list, "orientation": orientation, "x": x, "weights": weights or []})[:16]


def selection_from_rank(
    ranked: pd.DataFrame,
    *,
    rule_id: str,
    rule_family: str,
    validation_phase: str,
    feature_list: list[str],
    orientation: dict[str, str],
    x: float,
    score_col: str,
    percentile_col: str = "rank_percentile",
    rank_status_col: str = "rank_status",
) -> pd.DataFrame:
    out = ranked.copy()
    out["rule_id"] = rule_id
    out["rule_family"] = rule_family
    out["validation_phase"] = validation_phase
    out["feature_list"] = "|".join(feature_list)
    out["feature_orientation_json"] = json.dumps(orientation, sort_keys=True)
    out["feature_list_hash"] = stable_hash(feature_list)
    out["history_policy_id"] = "board_then_global_rolling_504_sessions"
    out["history_window_mode"] = "rolling_sessions"
    out["trailing_history_window_sessions"] = 504
    out["stage1_budget_X"] = float(x)
    out["score_col"] = score_col
    score_orientation = normalize_orientation(next(iter(orientation.values()))) if len(feature_list) == 1 else "asc"
    out["selected_flag"] = keep_mask_from_rank(out[rank_status_col], out[percentile_col], score_orientation, float(x))
    out["diagnostic_only_flag"] = False
    return out


def readout_for_selection(selection: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if selection.empty:
        return pd.DataFrame()
    first = selection.iloc[0]
    for split in SPLITS:
        frame = split_frame(selection, split)
        selected = frame.loc[bool_series(frame["selected_flag"])]
        rank_eval = frame.loc[frame["rank_status"].eq("rank_evaluable")]
        denom_pos = int(bool_series(frame[TARGET_COL]).sum())
        rank_eval_pos = int(bool_series(rank_eval[TARGET_COL]).sum())
        selected_pos = int(bool_series(selected[TARGET_COL]).sum())
        selected_rate = safe_rate(selected_pos, len(selected))
        base_rate = safe_rate(denom_pos, len(frame))
        rank_not = int(frame["rank_status"].ne("rank_evaluable").sum())
        rows.append(
            {
                "stage": "stage_1",
                "split": split,
                "rule_id": first["rule_id"],
                "rule_family": first["rule_family"],
                "validation_phase": first["validation_phase"],
                "phase_1_simple_backbone_gate_status": "",
                "phase_2_enabled": False,
                "complex_score_reproduction_status": "",
                "complex_score_source_caveat": "",
                "complex_score_caveat_flag": False,
                "complex_near_miss_flag": False,
                "complex_ci_cross_zero_flag": False,
                "complex_comparator_status": "",
                "feature_list": first["feature_list"],
                "feature_orientation_json": first["feature_orientation_json"],
                "feature_list_hash": first["feature_list_hash"],
                "history_policy_id": first["history_policy_id"],
                "history_window_mode": first["history_window_mode"],
                "trailing_history_window_sessions": first["trailing_history_window_sessions"],
                "stage1_budget_X": float(first["stage1_budget_X"]),
                "denominator_n": int(len(frame)),
                "rank_evaluable_n": int(len(rank_eval)),
                "rank_not_evaluable_n": rank_not,
                "denominator_positive_n": denom_pos,
                "rank_evaluable_positive_n": rank_eval_pos,
                "selected_n": int(len(selected)),
                "selected_positive_n": selected_pos,
                "selected_budget_total": safe_rate(len(selected), len(frame)),
                "selected_budget_rank_evaluable": safe_rate(len(selected), len(rank_eval)),
                "common_denominator_n": np.nan,
                "common_denominator_coverage_vs_complex_model": np.nan,
                "common_denominator_coverage_vs_simple_backbone": np.nan,
                "selected_fast_fail_rate": selected_rate,
                "base_fast_fail_rate": base_rate,
                "delta_vs_base": selected_rate - base_rate if pd.notna(selected_rate) and pd.notna(base_rate) else np.nan,
                "random_p05": np.nan,
                "random_p50": np.nan,
                "random_p95": np.nan,
                "delta_vs_random_p50": np.nan,
                "delta_vs_random_p50_ci95_low": np.nan,
                "delta_vs_random_p50_ci95_high": np.nan,
                "complex_model_matched_rate": np.nan,
                "delta_vs_complex_model": np.nan,
                "delta_vs_complex_model_ci95_low": np.nan,
                "delta_vs_complex_model_ci95_high": np.nan,
                "simple_backbone_matched_rate": np.nan,
                "delta_vs_simple_backbone": np.nan,
                "delta_vs_simple_backbone_ci95_low": np.nan,
                "delta_vs_simple_backbone_ci95_high": np.nan,
                "bootstrap_denominator_positive_n": selected_pos,
                "bootstrap_replicate_valid_n": 0,
                "readout_status": "ok",
                "diagnostic_only_flag": bool(first["diagnostic_only_flag"]),
            }
        )
    return pd.DataFrame(rows)


def budget_drift_for_selection(selection: pd.DataFrame) -> pd.DataFrame:
    rows = []
    first = selection.iloc[0]
    x = float(first["stage1_budget_X"])
    for split in SPLITS:
        frame = split_frame(selection, split)
        selected_n = int(bool_series(frame["selected_flag"]).sum())
        rank_eval_n = int(frame["rank_status"].eq("rank_evaluable").sum())
        total_budget = safe_rate(selected_n, len(frame))
        eval_budget = safe_rate(selected_n, rank_eval_n)
        rows.append(
            {
                "split": split,
                "rule_id": first["rule_id"],
                "rule_family": first["rule_family"],
                "validation_phase": first["validation_phase"],
                "feature_list": first["feature_list"],
                "stage1_budget_X": x,
                "selected_budget_total": total_budget,
                "selected_budget_rank_evaluable": eval_budget,
                "budget_abs_delta_total_vs_X": abs(total_budget - x) if pd.notna(total_budget) else np.nan,
                "budget_abs_delta_rank_evaluable_vs_X": abs(eval_budget - x) if pd.notna(eval_budget) else np.nan,
                "rank_not_evaluable_rate": safe_rate(frame["rank_status"].ne("rank_evaluable").sum(), len(frame)),
                "board_history_used_rate": safe_rate(frame["history_scope"].eq("board").sum(), len(frame)),
                "global_fallback_rate": safe_rate(frame["history_scope"].eq("global").sum(), len(frame)),
                "history_n_p05": frame["history_n"].quantile(0.05) if len(frame) else np.nan,
                "history_n_p50": frame["history_n"].quantile(0.50) if len(frame) else np.nan,
                "history_n_p95": frame["history_n"].quantile(0.95) if len(frame) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def random_rank_columns(random: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    return [col for col in config["random_baseline"]["retention_rank_columns"] if col in random.columns]


def prepare_random_labels(resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    random = read_table(resolved["matched_random_sampled_entries"])
    cache = read_table(resolved["entry_forward_path_cache"])
    key = ["path_key", "instrument", "entry_pos", "entry_price"]
    cache_dup = int(cache.duplicated(key).sum())
    if cache_dup:
        raise RuntimeError(f"entry_forward_path_cache duplicate join keys: {cache_dup}")
    random = random.merge(cache[key + ["entry_blocked", "horizon_complete_20d", "time_to_lower_minus_10_20d"]], on=key, how="left")
    random["path_label_join_status"] = np.where(random["entry_blocked"].notna(), "pass", "missing_cache_match")
    random["cache_key_unique_status"] = "pass"
    random["random_fast_fail_read_status"] = np.where(
        random["path_label_join_status"].eq("pass") & (~bool_series(random["entry_blocked"])) & bool_series(random["horizon_complete_20d"]),
        "pass",
        "fail",
    )
    random["random_fast_fail_target"] = random["time_to_lower_minus_10_20d"].notna()
    if not random["random_fast_fail_read_status"].eq("pass").all():
        return random, "fail"
    return random, "pass"


def random_replay(selection: pd.DataFrame, random: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    first = selection.iloc[0]
    cell_cols = ["split", "board_bucket", "calendar_month"]
    cells = (
        selection.loc[bool_series(selection["selected_flag"]) & selection["split"].astype(str).ne("all")]
        .groupby(cell_cols, dropna=False)
        .size()
        .rename("requested_selected_n")
        .reset_index()
    )
    if cells.empty:
        return random.head(0), pd.DataFrame(), pd.DataFrame(), "fail"
    seeds = pd.DataFrame({"seed": sorted(random["seed"].dropna().unique())})
    audit_base = seeds.assign(_k=1).merge(cells.assign(_k=1), on="_k").drop(columns="_k")
    rank_cols = random_rank_columns(random, config)
    eligible = random.loc[random["random_fast_fail_read_status"].eq("pass")].merge(cells, on=cell_cols, how="inner")
    eligible = eligible.sort_values(["seed"] + cell_cols + rank_cols, kind="stable")
    eligible["_rank_in_cell"] = eligible.groupby(["seed"] + cell_cols, dropna=False).cumcount() + 1
    eligible["_selected"] = eligible["_rank_in_cell"].le(eligible["requested_selected_n"])
    selected = eligible.loc[eligible["_selected"]].copy()
    available = eligible.groupby(["seed"] + cell_cols, dropna=False).size().rename("available_random_n").reset_index()
    sampled = selected.groupby(["seed"] + cell_cols, dropna=False).size().rename("sampled_random_n").reset_index()
    audit = audit_base.merge(available, on=["seed"] + cell_cols, how="left").merge(sampled, on=["seed"] + cell_cols, how="left")
    audit[["available_random_n", "sampled_random_n"]] = audit[["available_random_n", "sampled_random_n"]].fillna(0).astype(int)
    audit["replacement_used_flag"] = False
    if "replacement_used_flag" in selected:
        repl = selected.groupby(["seed"] + cell_cols, dropna=False)["replacement_used_flag"].any().reset_index()
        audit = audit.drop(columns=["replacement_used_flag"]).merge(repl, on=["seed"] + cell_cols, how="left")
        audit["replacement_used_flag"] = bool_series(audit["replacement_used_flag"])
    pos = selected.groupby(["seed"] + cell_cols, dropna=False)["random_fast_fail_target"].apply(lambda s: int(bool_series(s).sum())).rename("random_fast_fail_positive_n").reset_index()
    audit = audit.merge(pos, on=["seed"] + cell_cols, how="left")
    audit["random_fast_fail_positive_n"] = audit["random_fast_fail_positive_n"].fillna(0).astype(int)
    audit["random_fast_fail_rate"] = audit["random_fast_fail_positive_n"] / audit["sampled_random_n"].replace(0, np.nan)
    audit["sampling_status"] = np.where(audit["sampled_random_n"].eq(audit["requested_selected_n"]), "ok", "insufficient_random_cell")
    audit["path_label_join_status"] = "pass"
    audit["cache_key_unique_status"] = "pass"
    audit["random_replay_status"] = np.where(audit["sampling_status"].eq("ok"), "pass", "fail")
    for col, value in {
        "rule_id": first["rule_id"],
        "rule_family": first["rule_family"],
        "validation_phase": first["validation_phase"],
        "stage": "stage_1",
        "feature_list": first["feature_list"],
        "stage1_budget_X": float(first["stage1_budget_X"]),
    }.items():
        audit.insert(0, col, value)
    valid_seed = audit.groupby("seed")["random_replay_status"].apply(lambda s: s.eq("pass").all())
    valid_seed_ids = set(valid_seed.loc[valid_seed].index)
    selected = selected.loc[selected["seed"].isin(valid_seed_ids)].copy()
    seed_rates = []
    for seed, seed_group in selected.groupby("seed", sort=False):
        for split in SPLITS:
            sub = split_frame(seed_group, split)
            seed_rates.append(
                {
                    "seed": seed,
                    "split": split,
                    "random_rate": safe_rate(int(bool_series(sub["random_fast_fail_target"]).sum()), len(sub)),
                }
            )
    seed_rates_df = pd.DataFrame(seed_rates)
    if seed_rates_df.empty:
        quant = pd.DataFrame(columns=["split", "random_p05", "random_p50", "random_p95", "valid_seed_n"])
    else:
        quant = (
            seed_rates_df.groupby("split")["random_rate"]
            .quantile([0.05, 0.50, 0.95])
            .unstack()
            .reset_index()
        )
        quant.columns = ["split", "random_p05", "random_p50", "random_p95"]
        quant["valid_seed_n"] = len(valid_seed_ids)
    status = "pass" if len(valid_seed_ids) >= int(config["random_baseline"]["min_random_seed_n"]) else "fail"
    return selected, audit, quant, status


def attach_random(readout: pd.DataFrame, quant: pd.DataFrame) -> pd.DataFrame:
    out = readout.copy()
    if quant.empty:
        return out
    out = out.merge(quant, on="split", how="left", suffixes=("", "_new"))
    for col in ("random_p05", "random_p50", "random_p95"):
        new_col = f"{col}_new"
        if new_col in out:
            out[col] = out[new_col].combine_first(out[col])
            out = out.drop(columns=[new_col])
    out["delta_vs_random_p50"] = out["selected_fast_fail_rate"] - out["random_p50"]
    return out


def bootstrap_random_ci(
    model_selected: pd.DataFrame,
    random_selected: pd.DataFrame,
    config: dict[str, Any],
    label: str,
    split: str,
) -> tuple[float, float, int, pd.DataFrame]:
    n_resamples = int(config["bootstrap"]["n_resamples"])
    if model_selected.empty or random_selected.empty:
        return np.nan, np.nan, 0, pd.DataFrame()
    seed_rates = []
    for _, group in random_selected.groupby("seed", sort=False):
        seed_rates.append(safe_rate(int(bool_series(group["random_fast_fail_target"]).sum()), len(group)))
    seed_rates = np.asarray([x for x in seed_rates if pd.notna(x)], dtype=float)
    if len(seed_rates) == 0:
        return np.nan, np.nan, 0, pd.DataFrame()
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]))
    y = bool_series(model_selected[TARGET_COL]).astype(float).to_numpy()
    deltas = []
    for i in range(n_resamples):
        model_rate = float(rng.choice(y, size=len(y), replace=True).mean())
        rand_rate = float(np.median(rng.choice(seed_rates, size=len(seed_rates), replace=True)))
        deltas.append(model_rate - rand_rate)
    reps = pd.DataFrame({"comparison_id": label, "split": split, "replicate_id": np.arange(n_resamples), "delta": deltas})
    return (
        float(np.quantile(deltas, float(config["bootstrap"]["ci_low_q"]))),
        float(np.quantile(deltas, float(config["bootstrap"]["ci_high_q"]))),
        n_resamples,
        reps,
    )


def bootstrap_paired_ci_for_target(
    base: pd.DataFrame,
    left_flag: str,
    right_flag: str,
    target_col: str,
    label: str,
    split: str,
    config: dict[str, Any],
) -> tuple[float, float, int, pd.DataFrame]:
    base = split_frame(base, split)
    if base.empty or not bool_series(base[left_flag]).any() or not bool_series(base[right_flag]).any():
        return np.nan, np.nan, 0, pd.DataFrame()
    y = bool_series(base[target_col]).astype(float).to_numpy()
    left = bool_series(base[left_flag]).to_numpy(dtype=bool)
    right = bool_series(base[right_flag]).to_numpy(dtype=bool)
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]) + 17)
    n_resamples = int(config["bootstrap"]["n_resamples"])
    idx_src = np.arange(len(base))
    deltas = []
    for _ in range(n_resamples):
        idx = rng.choice(idx_src, size=len(idx_src), replace=True)
        l = left[idx]
        r = right[idx]
        if not l.any() or not r.any():
            continue
        sample_y = y[idx]
        deltas.append(float(sample_y[l].mean() - sample_y[r].mean()))
    reps = pd.DataFrame({"comparison_id": label, "split": split, "replicate_id": np.arange(len(deltas)), "delta": deltas})
    if not deltas:
        return np.nan, np.nan, 0, reps
    return (
        float(np.quantile(deltas, float(config["bootstrap"]["ci_low_q"]))),
        float(np.quantile(deltas, float(config["bootstrap"]["ci_high_q"]))),
        len(deltas),
        reps,
    )


def bootstrap_paired_ci(
    base: pd.DataFrame,
    left_flag: str,
    right_flag: str,
    label: str,
    split: str,
    config: dict[str, Any],
) -> tuple[float, float, int, pd.DataFrame]:
    return bootstrap_paired_ci_for_target(base, left_flag, right_flag, TARGET_COL, label, split, config)


def seeded_rng(config: dict[str, Any], label: str) -> np.random.Generator:
    offset = int(stable_hash(label)[:8], 16)
    return np.random.default_rng(int(config["bootstrap"]["seed"]) + offset)


def random_quantiles(values: list[float]) -> dict[str, float | int]:
    clean = np.asarray([x for x in values if pd.notna(x)], dtype=float)
    if len(clean) == 0:
        return {"random_p05": np.nan, "random_p50": np.nan, "random_p95": np.nan, "valid_seed_n": 0}
    return {
        "random_p05": float(np.quantile(clean, 0.05)),
        "random_p50": float(np.quantile(clean, 0.50)),
        "random_p95": float(np.quantile(clean, 0.95)),
        "valid_seed_n": int(len(clean)),
    }


def random_p50_within_slice(frame: pd.DataFrame, selected_n: int, target_col: str, config: dict[str, Any], label: str) -> dict[str, float | int]:
    if selected_n <= 0 or selected_n > len(frame):
        return random_quantiles([])
    ordered = frame.sort_values([col for col in ("instrument", "event_t0_date", "meta_event_id") if col in frame.columns], kind="stable")
    target = bool_series(ordered[target_col]).astype(float).to_numpy()
    idx = np.arange(len(ordered))
    rng = seeded_rng(config, label)
    seed_n = int(config["random_baseline"].get("min_random_seed_n", 100))
    rates = []
    for _ in range(seed_n):
        picked = rng.choice(idx, size=selected_n, replace=False)
        rates.append(float(target[picked].mean()))
    return random_quantiles(rates)


def matched_random_quantiles_by_cell(
    frame: pd.DataFrame,
    selected_flag_col: str,
    target_col: str,
    config: dict[str, Any],
    split: str,
    label: str,
) -> dict[str, float | int]:
    sub = split_frame(frame, split)
    if sub.empty or selected_flag_col not in sub:
        return random_quantiles([])
    cell_cols = ["board_bucket", "calendar_month"]
    if split == "all" and "split" in sub.columns:
        cell_cols = ["split"] + cell_cols
    cell_cols = [col for col in cell_cols if col in sub.columns]
    if not cell_cols:
        return random_p50_within_slice(sub, int(bool_series(sub[selected_flag_col]).sum()), target_col, config, label)
    selected_counts = sub.loc[bool_series(sub[selected_flag_col])].groupby(cell_cols, dropna=False).size().rename("selected_n")
    if selected_counts.empty:
        return random_quantiles([])
    sort_cols = [col for col in ("instrument", "event_t0_date", "meta_event_id") if col in sub.columns]
    groups = {}
    for key, group in sub.groupby(cell_cols, dropna=False, sort=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        ordered = group.sort_values(sort_cols, kind="stable") if sort_cols else group
        groups[key_tuple] = bool_series(ordered[target_col]).astype(float).to_numpy()
    rng = seeded_rng(config, label)
    seed_n = int(config["random_baseline"].get("min_random_seed_n", 100))
    rates = []
    for _ in range(seed_n):
        targets = []
        for key, selected_n in selected_counts.items():
            key_tuple = key if isinstance(key, tuple) else (key,)
            target = groups.get(key_tuple)
            if target is None or int(selected_n) <= 0 or int(selected_n) > len(target):
                continue
            picked = rng.choice(np.arange(len(target)), size=int(selected_n), replace=False)
            targets.extend(target[picked].tolist())
        if targets:
            rates.append(float(np.mean(targets)))
    return random_quantiles(rates)


def update_random_ci(readout: pd.DataFrame, selection: pd.DataFrame, random_selected: pd.DataFrame, config: dict[str, Any], label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = readout.copy()
    reps = []
    for split in SPLITS:
        model_sel = split_frame(selection.loc[bool_series(selection["selected_flag"])], split)
        rand_sel = split_frame(random_selected, split)
        low, high, valid_n, rep = bootstrap_random_ci(model_sel, rand_sel, config, label, split)
        mask = out["split"].eq(split)
        out.loc[mask, "delta_vs_random_p50_ci95_low"] = low
        out.loc[mask, "delta_vs_random_p50_ci95_high"] = high
        out.loc[mask, "bootstrap_replicate_valid_n"] = valid_n
        if not rep.empty:
            reps.append(rep)
    return out, pd.concat(reps, ignore_index=True) if reps else pd.DataFrame()


def train_selection(candidate_curve: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    train = candidate_curve.loc[candidate_curve["split"].eq("train")].copy()
    g = config["gates"]
    train["minimum_train_eligible"] = (
        (train["selected_n"] >= int(g["train_selected_n_min"]))
        & (train["rank_evaluable_n"] >= int(g["train_rank_evaluable_n_min"]))
        & (train["denominator_positive_n"] >= int(g["train_denominator_positive_n_min"]))
    )
    eligible = train.loc[train["minimum_train_eligible"]].copy()
    if eligible.empty:
        return pd.DataFrame(
            [
                {
                    "selection_status": "no_train_eligible_backbone_tuple",
                    "phase_1_simple_backbone_gate_status": "diagnostic_only",
                    "decision_state_if_terminal": "12A7b_backbone_diagnostic_only",
                }
            ]
        )
    eligible["train_random_uplift_gate_pass"] = eligible["delta_vs_random_p50"] <= float(g["train_delta_vs_random_p50_max"])
    eligible = eligible.loc[eligible["train_random_uplift_gate_pass"]].copy()
    if eligible.empty:
        return pd.DataFrame(
            [
                {
                    "selection_status": "no_train_random_uplift_candidate",
                    "phase_1_simple_backbone_gate_status": "fail",
                    "decision_state_if_terminal": "12A7b_no_simple_backbone_transport",
                }
            ]
        )
    eligible["_rate_rank"] = eligible["selected_fast_fail_rate"]
    eligible = eligible.sort_values(
        ["_rate_rank", "selected_n", "feature_list", "stage1_budget_X"],
        ascending=[True, False, True, True],
        kind="stable",
    )
    row = eligible.iloc[0].to_dict()
    row.update(
        {
            "selection_status": "selected_train_frozen",
            "phase_1_simple_backbone_gate_status": "pending_robustness",
            "decision_state_if_terminal": "",
            "tie_break_path": "lowest_train_fast_fail_rate;larger_selected_n;feature_name_ASC;X_ASC",
            "phase_1_selected_tuple_frozen": True,
            "x_capacity_comment": "selected X is train-frozen and later judged by robustness budget and CI gates",
        }
    )
    return pd.DataFrame([row])


def matched_complex_comparator(
    selection: pd.DataFrame,
    frame: pd.DataFrame,
    policy: Any,
    config: dict[str, Any],
    a7_decision: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    h = config["history_min_n"]
    complex_rank = A7.rolling_percentiles(
        frame.copy(),
        score_col=COMPLEX_SCORE_COL,
        pos_col="event_t0_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_1_global_min_history_n"]),
        board_min_history_n=int(h["stage_1_board_min_history_n"]),
    )[["meta_event_id", "rank_status"]].rename(columns={"rank_status": "complex_rank_status"})
    base = selection.merge(complex_rank, on="meta_event_id", how="left")
    base["_candidate_rank_evaluable"] = base["rank_status"].eq("rank_evaluable")
    base["_complex_rank_evaluable"] = base["complex_rank_status"].eq("rank_evaluable")
    base["_common"] = base["_candidate_rank_evaluable"] & base["_complex_rank_evaluable"]
    base["_candidate_selected_common"] = bool_series(base["selected_flag"]) & base["_common"]
    base["_complex_selected_common"] = False
    cell_cols = ["split", "board_bucket", "calendar_month"]
    selected_parts = []
    for cell, group in base.loc[base["_common"]].groupby(cell_cols, dropna=False):
        k = int(base.loc[base["_candidate_selected_common"] & base["split"].eq(cell[0]) & base["board_bucket"].eq(cell[1]) & base["calendar_month"].eq(cell[2])].shape[0])
        picked = group.sort_values([COMPLEX_SCORE_COL, "instrument", "event_t0_date", "meta_event_id"], kind="stable").head(k)
        selected_parts.append(picked[["meta_event_id"]])
    if selected_parts:
        complex_ids = set(pd.concat(selected_parts, ignore_index=True)["meta_event_id"].astype(str))
        base["_complex_selected_common"] = base["meta_event_id"].astype(str).isin(complex_ids) & base["_common"]
    caveat = ""
    repro = ""
    if not a7_decision.empty:
        repro = str(a7_decision.iloc[0].get("score_reproduction_status", ""))
        raw_caveat = a7_decision.iloc[0].get("score_source_caveat", "")
        caveat = "" if pd.isna(raw_caveat) else str(raw_caveat)
    rows = []
    reps = []
    guard = float(config["gates"]["complex_delta_near_miss_guard"])
    for split in SPLITS:
        sub = split_frame(base, split)
        common = sub.loc[sub["_common"]]
        candidate = common.loc[bool_series(common["_candidate_selected_common"])]
        comp = common.loc[bool_series(common["_complex_selected_common"])]
        cand_rate = safe_rate(int(bool_series(candidate[TARGET_COL]).sum()), len(candidate))
        comp_rate = safe_rate(int(bool_series(comp[TARGET_COL]).sum()), len(comp))
        low, high, valid_n, rep = bootstrap_paired_ci(common, "_candidate_selected_common", "_complex_selected_common", "candidate_minus_complex_model", split, config)
        if not rep.empty:
            reps.append(rep)
        delta = cand_rate - comp_rate if pd.notna(cand_rate) and pd.notna(comp_rate) else np.nan
        caveat_flag = bool(caveat)
        near_flag = pd.notna(delta) and abs(delta) <= guard
        cross_flag = pd.notna(low) and pd.notna(high) and low <= 0 <= high
        if caveat_flag:
            status = "numerical_near_miss_diagnostic"
        elif near_flag:
            status = "complex_parity_or_near_miss"
        elif cross_flag:
            status = "complex_parity_or_uncertain"
        elif pd.notna(high) and high < 0:
            status = "candidate_beats_complex_model"
        elif pd.notna(low) and low > 0:
            status = "complex_model_beats_candidate_diagnostic"
        else:
            status = "complex_comparator_inconclusive"
        rows.append(
            {
                "split": split,
                "rule_id": selection.iloc[0]["rule_id"],
                "common_denominator_n": int(len(common)),
                "candidate_rank_evaluable_n": int(sub["_candidate_rank_evaluable"].sum()),
                "complex_rank_evaluable_n": int(sub["_complex_rank_evaluable"].sum()),
                "common_denominator_coverage_vs_complex_model": safe_rate(len(common), sub["_candidate_rank_evaluable"].sum()),
                "candidate_matched_selected_n": int(len(candidate)),
                "complex_model_matched_selected_n": int(len(comp)),
                "candidate_matched_rate": cand_rate,
                "complex_model_matched_rate": comp_rate,
                "delta_vs_complex_model": delta,
                "delta_vs_complex_model_ci95_low": low,
                "delta_vs_complex_model_ci95_high": high,
                "bootstrap_replicate_valid_n": valid_n,
                "complex_score_reproduction_status": repro,
                "complex_score_source_caveat": caveat,
                "complex_score_caveat_flag": caveat_flag,
                "complex_near_miss_flag": near_flag,
                "complex_ci_cross_zero_flag": cross_flag,
                "complex_comparator_status": status,
                "diagnostic_only_flag": True,
            }
        )
    return pd.DataFrame(rows), base, pd.concat(reps, ignore_index=True) if reps else pd.DataFrame()


def merge_complex_into_readout(readout: pd.DataFrame, comp: pd.DataFrame) -> pd.DataFrame:
    out = readout.copy()
    cols = [
        "split",
        "common_denominator_n",
        "common_denominator_coverage_vs_complex_model",
        "complex_model_matched_rate",
        "delta_vs_complex_model",
        "delta_vs_complex_model_ci95_low",
        "delta_vs_complex_model_ci95_high",
        "complex_score_reproduction_status",
        "complex_score_source_caveat",
        "complex_score_caveat_flag",
        "complex_near_miss_flag",
        "complex_ci_cross_zero_flag",
        "complex_comparator_status",
    ]
    out = out.merge(comp[cols], on="split", how="left", suffixes=("", "_complex"))
    for col in cols:
        if col == "split":
            continue
        c = f"{col}_complex"
        if c in out:
            out[col] = out[c].where(out[c].notna(), out[col])
            out = out.drop(columns=[c])
    return out


def phase1_support_reasons(row: pd.Series, drift: pd.Series, config: dict[str, Any]) -> list[str]:
    g = config["gates"]
    reasons = []
    if int(row.get("selected_n", 0)) < int(g["selected_n_min"]):
        reasons.append("selected_n_below_min")
    if int(row.get("denominator_positive_n", 0)) < int(g["denominator_positive_n_min"]):
        reasons.append("denominator_positive_n_below_min")
    if int(row.get("bootstrap_replicate_valid_n", 0)) < int(config["bootstrap"]["bootstrap_min_valid_replicates"]):
        reasons.append("bootstrap_replicate_valid_n_below_min")
    if float(row.get("delta_vs_random_p50", np.inf)) > float(g["delta_vs_random_p50_max"]):
        reasons.append("delta_vs_random_p50_not_supported")
    if float(row.get("delta_vs_random_p50_ci95_high", np.inf)) >= 0:
        reasons.append("random_ci_crosses_zero")
    if float(row.get("selected_budget_total", np.inf)) > float(g["selected_budget_total_max"]):
        reasons.append("selected_budget_total_above_max")
    if float(drift.get("budget_abs_delta_rank_evaluable_vs_X", np.inf)) > float(g["budget_abs_delta_rank_evaluable_vs_X_max"]):
        reasons.append("budget_abs_delta_rank_evaluable_vs_X_above_max")
    if float(drift.get("rank_not_evaluable_rate", np.inf)) > float(g["rank_not_evaluable_rate_max"]):
        reasons.append("rank_not_evaluable_rate_above_max")
    if not (
        float(row.get("selected_fast_fail_rate", np.inf)) < float(row.get("base_fast_fail_rate", -np.inf))
        and float(row.get("selected_fast_fail_rate", np.inf)) < float(row.get("random_p50", -np.inf))
    ):
        reasons.append("direction_stability_failed")
    return reasons


def feature_percentile_cache(feature_ranked: dict[str, pd.DataFrame], frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[["meta_event_id"]].copy()
    for feature, ranked in feature_ranked.items():
        cols = ranked[["meta_event_id", "rank_percentile", "rank_status"]].rename(
            columns={"rank_percentile": f"{feature}__rank_percentile", "rank_status": f"{feature}__rank_status"}
        )
        out = out.merge(cols, on="meta_event_id", how="left")
    return out


def monotone_candidates(
    frame: pd.DataFrame,
    feature_ranked: dict[str, pd.DataFrame],
    selected_feature: str,
    selected_x: float,
    policy: Any,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    pct = feature_percentile_cache(feature_ranked, frame)
    base = frame.merge(pct, on="meta_event_id", how="left")
    features = list(config["candidate_features"].keys())
    others = [f for f in features if f != selected_feature]
    specs = []
    for other in others:
        for weights in config["monotone"]["two_feature_weights"]:
            specs.append(([selected_feature, other], [float(w) for w in weights]))
    for pair in itertools.combinations(others, 2):
        for weights in config["monotone"]["three_feature_weights"]:
            specs.append(([selected_feature, pair[0], pair[1]], [float(w) for w in weights]))
    h = config["history_min_n"]
    rows = []
    selections = {}
    for feature_list, weights in specs:
        candidate = base.copy()
        score = np.zeros(len(candidate), dtype=float)
        valid = np.ones(len(candidate), dtype=bool)
        for feature, weight in zip(feature_list, weights):
            pct_col = f"{feature}__rank_percentile"
            status_col = f"{feature}__rank_status"
            vals = pd.to_numeric(candidate[pct_col], errors="coerce").to_numpy(dtype=float)
            score += float(weight) * vals
            valid &= candidate[status_col].astype(str).eq("rank_evaluable").to_numpy() & np.isfinite(vals)
        candidate["monotone_risk_score"] = np.where(valid, score, np.nan)
        ranked = A7.rolling_percentiles(
            candidate,
            score_col="monotone_risk_score",
            pos_col="event_t0_pos",
            board_col="board_bucket",
            policy=policy,
            global_min_history_n=int(h["stage_1_global_min_history_n"]),
            board_min_history_n=int(h["stage_1_board_min_history_n"]),
        )
        rid = "lowcap_" + rule_hash(feature_list, {f: config["candidate_features"][f] for f in feature_list}, selected_x, "monotone_additive_rank_score", weights)
        sel = selection_from_rank(
            ranked,
            rule_id=rid,
            rule_family="monotone_additive_rank_score",
            validation_phase="phase_2_low_capacity_monotone",
            feature_list=feature_list,
            orientation={f: config["candidate_features"][f] for f in feature_list},
            x=selected_x,
            score_col="monotone_risk_score",
        )
        selections[rid] = sel
        train = split_frame(sel, "train")
        train_selected = train.loc[bool_series(train["selected_flag"])]
        train_rate = safe_rate(int(bool_series(train_selected[TARGET_COL]).sum()), len(train_selected))
        train_budget = safe_rate(len(train_selected), train["rank_status"].eq("rank_evaluable").sum())
        rows.append(
            {
                "rule_id": rid,
                "rule_family": "monotone_additive_rank_score",
                "feature_list": "|".join(feature_list),
                "feature_orientation_json": json.dumps({f: config["candidate_features"][f] for f in feature_list}, sort_keys=True),
                "weight_json": json.dumps(weights),
                "feature_count": len(feature_list),
                "must_include_feature": selected_feature,
                "stage1_budget_X": selected_x,
                "train_selected_n": int(len(train_selected)),
                "train_fast_fail_rate": train_rate,
                "train_selected_n_drift": abs(train_budget - selected_x) if pd.notna(train_budget) else np.nan,
                "all_monotone_additive_score_constraints_satisfied": all(w >= 0 for w in weights) and abs(sum(weights) - 1.0) <= 0.02 and len(feature_list) <= 3,
                "low_capacity_status": "candidate_available",
                "diagnostic_only_flag": False,
            }
        )
    return pd.DataFrame(rows), selections


def select_low_capacity(card: pd.DataFrame) -> pd.Series:
    usable = card.loc[card["all_monotone_additive_score_constraints_satisfied"]].copy()
    if usable.empty:
        return pd.Series(dtype=object)
    usable = usable.sort_values(
        ["train_fast_fail_rate", "feature_count", "train_selected_n_drift", "feature_list", "weight_json"],
        ascending=[True, True, True, True, True],
        kind="stable",
    )
    return usable.iloc[0]


def simple_backbone_matched_for_lowcap(lowcap: pd.DataFrame, backbone: pd.DataFrame, selected_feature: str, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = lowcap.merge(
        backbone[["meta_event_id", "rank_status", "rank_percentile", "selected_flag"]].rename(
            columns={
                "rank_status": "simple_rank_status",
                "rank_percentile": "simple_rank_percentile",
                "selected_flag": "simple_original_selected",
            }
        ),
        on="meta_event_id",
        how="left",
    )
    base["_common"] = base["rank_status"].eq("rank_evaluable") & base["simple_rank_status"].eq("rank_evaluable")
    base["_lowcap_selected_common"] = bool_series(base["selected_flag"]) & base["_common"]
    base["_simple_matched_selected"] = False
    cell_cols = ["split", "board_bucket", "calendar_month"]
    parts = []
    for cell, group in base.loc[base["_common"]].groupby(cell_cols, dropna=False):
        k = int(base.loc[base["_lowcap_selected_common"] & base["split"].eq(cell[0]) & base["board_bucket"].eq(cell[1]) & base["calendar_month"].eq(cell[2])].shape[0])
        picked = group.sort_values(["simple_rank_percentile", "instrument", "event_t0_date", "meta_event_id"], kind="stable").head(k)
        parts.append(picked[["meta_event_id"]])
    if parts:
        ids = set(pd.concat(parts, ignore_index=True)["meta_event_id"].astype(str))
        base["_simple_matched_selected"] = base["meta_event_id"].astype(str).isin(ids) & base["_common"]
    rows = []
    reps = []
    for split in SPLITS:
        common = split_frame(base.loc[base["_common"]], split)
        low = common.loc[bool_series(common["_lowcap_selected_common"])]
        simple = common.loc[bool_series(common["_simple_matched_selected"])]
        low_rate = safe_rate(int(bool_series(low[TARGET_COL]).sum()), len(low))
        simple_rate = safe_rate(int(bool_series(simple[TARGET_COL]).sum()), len(simple))
        ci_low, ci_high, valid_n, rep = bootstrap_paired_ci(common, "_lowcap_selected_common", "_simple_matched_selected", "low_capacity_minus_simple_backbone", split, config)
        if not rep.empty:
            reps.append(rep)
        rows.append(
            {
                "split": split,
                "common_denominator_n": int(len(common)),
                "common_denominator_coverage_vs_simple_backbone": safe_rate(len(common), len(split_frame(lowcap, split).loc[lambda x: x["rank_status"].eq("rank_evaluable")])),
                "low_capacity_selected_n": int(len(low)),
                "simple_backbone_matched_selected_n": int(len(simple)),
                "low_capacity_fast_fail_rate": low_rate,
                "simple_backbone_matched_rate": simple_rate,
                "delta_vs_simple_backbone": low_rate - simple_rate if pd.notna(low_rate) and pd.notna(simple_rate) else np.nan,
                "delta_vs_simple_backbone_ci95_low": ci_low,
                "delta_vs_simple_backbone_ci95_high": ci_high,
                "bootstrap_replicate_valid_n": valid_n,
                "matched_simple_feature_name": selected_feature,
            }
        )
    return pd.DataFrame(rows), base, pd.concat(reps, ignore_index=True) if reps else pd.DataFrame()


def merge_simple_match(readout: pd.DataFrame, simple_match: pd.DataFrame) -> pd.DataFrame:
    out = readout.merge(simple_match, on="split", how="left", suffixes=("", "_match"))
    for col in (
        "common_denominator_n",
        "common_denominator_coverage_vs_simple_backbone",
        "simple_backbone_matched_rate",
        "delta_vs_simple_backbone",
        "delta_vs_simple_backbone_ci95_low",
        "delta_vs_simple_backbone_ci95_high",
        "bootstrap_replicate_valid_n",
    ):
        c = f"{col}_match"
        if c in out:
            out[col] = out[c].where(out[c].notna(), out[col])
            out = out.drop(columns=[c])
    return out


def stability_slices(selection: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    slice_specs = [
        ("split", ["split"]),
        ("calendar_year", ["split", "calendar_year"]),
        ("board_bucket", ["split", "board_bucket"]),
        ("primary_family_id", ["split", "primary_family_id"]),
        ("calendar_month", ["split", "calendar_month"]),
    ]
    for slice_type, group_cols in slice_specs:
        for key, group in selection.groupby(group_cols, dropna=False):
            selected = group.loc[bool_series(group["selected_flag"])]
            selected_n = len(selected)
            selected_rate = safe_rate(int(bool_series(selected[TARGET_COL]).sum()), selected_n)
            base_rate = safe_rate(int(bool_series(group[TARGET_COL]).sum()), len(group))
            status = "insufficient_n"
            random_stats = random_p50_within_slice(group, selected_n, TARGET_COL, config, f"stability:{slice_type}:{key}")
            random_p50 = random_stats["random_p50"]
            if selected_n >= 100:
                if pd.notna(selected_rate) and pd.notna(base_rate) and selected_rate >= base_rate:
                    status = "fail"
                elif pd.notna(selected_rate) and pd.notna(random_p50) and selected_rate < random_p50:
                    status = "pass"
                else:
                    status = "weak"
            row = {
                "split": "all",
                "calendar_year": "all",
                "board_bucket": "all",
                "primary_family_id": "all",
                "calendar_month": "all",
                "slice_type": slice_type,
                "selected_n": int(selected_n),
                "selected_fast_fail_rate": selected_rate,
                "base_fast_fail_rate": base_rate,
                "delta_vs_base": selected_rate - base_rate if pd.notna(selected_rate) and pd.notna(base_rate) else np.nan,
                "random_p50": random_p50,
                "delta_vs_random_p50": selected_rate - random_p50 if pd.notna(selected_rate) and pd.notna(random_p50) else np.nan,
                "budget_total": safe_rate(selected_n, len(group)),
                "budget_rank_evaluable": safe_rate(selected_n, group["rank_status"].eq("rank_evaluable").sum()),
                "rank_not_evaluable_rate": safe_rate(group["rank_status"].ne("rank_evaluable").sum(), len(group)),
                "direction_status": status,
            }
            if not isinstance(key, tuple):
                key = (key,)
            for col, value in zip(group_cols, key):
                row[col] = value
            rows.append(row)
    return pd.DataFrame(rows)


def stage2_diagnostic(frame: pd.DataFrame, config: dict[str, Any], policy: Any, phase1_selection: pd.DataFrame | None = None) -> pd.DataFrame:
    spec = config["stage2_diagnostic"]
    feature = str(spec["feature_name"])
    rows = []
    if feature not in frame:
        return pd.DataFrame(rows)
    source = frame.loc[
        bool_series(frame["no_fast_fail_L10_H20"])
        & bool_series(frame["stage_2_path_evaluable"])
        & (~bool_series(frame["stage_2_entry_blocked"]))
        & bool_series(frame["stage_2_horizon_complete_20d"])
    ].copy()
    if source.empty:
        return pd.DataFrame(rows)
    if phase1_selection is not None and not phase1_selection.empty:
        chain = phase1_selection[["meta_event_id", "selected_flag"]].rename(columns={"selected_flag": "stage1_simple_backbone_selected_flag"})
        source = source.merge(chain, on="meta_event_id", how="left")
        source["stage1_simple_backbone_selected_flag"] = bool_series(source["stage1_simple_backbone_selected_flag"].fillna(False))
    else:
        source["stage1_simple_backbone_selected_flag"] = False
    h = config["history_min_n"]
    ranked = A7.rolling_percentiles(
        source,
        score_col=feature,
        pos_col="stage_2_decision_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_2_global_min_history_n"]),
        board_min_history_n=int(h["stage_2_board_min_history_n"]),
    )
    complex_ranked = pd.DataFrame()
    if "stage2_continuation_score" in source and source["stage2_continuation_score"].notna().any():
        complex_ranked = A7.rolling_percentiles(
            source.copy(),
            score_col="stage2_continuation_score",
            pos_col="stage_2_decision_pos",
            board_col="board_bucket",
            policy=policy,
            global_min_history_n=int(h["stage_2_global_min_history_n"]),
            board_min_history_n=int(h["stage_2_board_min_history_n"]),
        )[["meta_event_id", "rank_status"]].rename(columns={"rank_status": "complex_stage2_rank_status"})

    def continuation_rate(data: pd.DataFrame) -> float:
        return safe_rate(int(bool_series(data["stage_2_continuation_target"]).sum()), len(data))

    def append_stage2_row(
        *,
        split: str,
        readout: str,
        denominator: pd.DataFrame,
        selected: pd.DataFrame,
        x: float | None,
        rank_evaluable_n: int,
        random_stats: dict[str, float | int] | None = None,
        complex_stats: dict[str, float | int | str] | None = None,
        rate_override: float | None = None,
    ) -> None:
        random_stats = random_stats or random_quantiles([])
        complex_stats = complex_stats or {}
        selected_rate = rate_override if rate_override is not None else continuation_rate(selected)
        base_rate = continuation_rate(denominator)
        rows.append(
            {
                "split": split,
                "diagnostic_readout": readout,
                "feature_name": feature,
                "orientation": spec["orientation"],
                "stage2_X": np.nan if x is None else float(x),
                "denominator_n": int(len(denominator)),
                "rank_evaluable_n": int(rank_evaluable_n),
                "selected_n": int(len(selected)),
                "selected_continuation_n": int(bool_series(selected["stage_2_continuation_target"]).sum()) if rate_override is None else np.nan,
                "selected_continuation_rate": selected_rate,
                "base_continuation_rate": base_rate,
                "random_p05": random_stats["random_p05"],
                "random_p50": random_stats["random_p50"],
                "random_p95": random_stats["random_p95"],
                "delta_vs_random_p50": selected_rate - random_stats["random_p50"] if pd.notna(selected_rate) and pd.notna(random_stats["random_p50"]) else np.nan,
                "valid_seed_n": random_stats["valid_seed_n"],
                "common_denominator_n": complex_stats.get("common_denominator_n", np.nan),
                "simple_stage2_selected_n": complex_stats.get("simple_stage2_selected_n", np.nan),
                "complex_stage2_matched_selected_n": complex_stats.get("complex_stage2_matched_selected_n", np.nan),
                "complex_stage2_matched_rate": complex_stats.get("complex_stage2_matched_rate", np.nan),
                "delta_vs_complex_stage2": complex_stats.get("delta_vs_complex_stage2", np.nan),
                "delta_vs_complex_stage2_ci95_low": complex_stats.get("delta_vs_complex_stage2_ci95_low", np.nan),
                "delta_vs_complex_stage2_ci95_high": complex_stats.get("delta_vs_complex_stage2_ci95_high", np.nan),
                "stage2_complex_comparator_status": complex_stats.get("stage2_complex_comparator_status", ""),
                "stage_2_diagnostic_only": True,
                "not_allowed_for_12A7b_decision_state": True,
            }
        )

    def complex_stage2_stats(selection: pd.DataFrame, split: str) -> dict[str, float | int | str]:
        if complex_ranked.empty:
            return {"stage2_complex_comparator_status": "missing_stage2_complex_score"}
        base = selection.merge(complex_ranked, on="meta_event_id", how="left")
        base["_common"] = base["rank_status"].eq("rank_evaluable") & base["complex_stage2_rank_status"].eq("rank_evaluable")
        base["_simple_stage2_selected_common"] = bool_series(base["selected_flag"]) & base["_common"]
        base["_complex_stage2_selected_common"] = False
        cell_cols = ["split", "board_bucket", "calendar_month"]
        parts = []
        for cell, group in base.loc[base["_common"]].groupby(cell_cols, dropna=False):
            k = int(
                base.loc[
                    base["_simple_stage2_selected_common"]
                    & base["split"].eq(cell[0])
                    & base["board_bucket"].eq(cell[1])
                    & base["calendar_month"].eq(cell[2])
                ].shape[0]
            )
            picked = group.sort_values(
                ["stage2_continuation_score", "instrument", "event_t0_date", "meta_event_id"],
                ascending=[False, True, True, True],
                kind="stable",
            ).head(k)
            parts.append(picked[["meta_event_id"]])
        if parts:
            ids = set(pd.concat(parts, ignore_index=True)["meta_event_id"].astype(str))
            base["_complex_stage2_selected_common"] = base["meta_event_id"].astype(str).isin(ids) & base["_common"]
        common = split_frame(base.loc[base["_common"]], split)
        simple = common.loc[bool_series(common["_simple_stage2_selected_common"])]
        complex_selected = common.loc[bool_series(common["_complex_stage2_selected_common"])]
        simple_rate = continuation_rate(simple)
        complex_rate = continuation_rate(complex_selected)
        low, high, valid_n, _rep = bootstrap_paired_ci_for_target(
            common,
            "_simple_stage2_selected_common",
            "_complex_stage2_selected_common",
            "stage_2_continuation_target",
            "simple_stage2_minus_complex_stage2",
            split,
            config,
        )
        if pd.notna(low) and pd.notna(high) and high < 0:
            status = "complex_stage2_beats_simple_diagnostic"
        elif pd.notna(low) and low > 0:
            status = "simple_stage2_beats_complex_diagnostic"
        elif pd.notna(low) and pd.notna(high) and low <= 0 <= high:
            status = "stage2_complex_parity_or_uncertain"
        else:
            status = "stage2_complex_comparator_inconclusive"
        return {
            "common_denominator_n": int(len(common)),
            "simple_stage2_selected_n": int(len(simple)),
            "complex_stage2_matched_selected_n": int(len(complex_selected)),
            "complex_stage2_matched_rate": complex_rate,
            "delta_vs_complex_stage2": simple_rate - complex_rate if pd.notna(simple_rate) and pd.notna(complex_rate) else np.nan,
            "delta_vs_complex_stage2_ci95_low": low,
            "delta_vs_complex_stage2_ci95_high": high,
            "stage2_complex_bootstrap_valid_n": valid_n,
            "stage2_complex_comparator_status": status,
        }

    for split in SPLITS:
        sub_source = split_frame(source, split)
        append_stage2_row(
            split=split,
            readout="ground_truth_no_fast_fail_survivor_readout",
            denominator=sub_source,
            selected=sub_source,
            x=None,
            rank_evaluable_n=len(sub_source),
        )
        chained = sub_source.loc[bool_series(sub_source["stage1_simple_backbone_selected_flag"])]
        append_stage2_row(
            split=split,
            readout="stage1_simple_backbone_chained_survivor_readout",
            denominator=sub_source,
            selected=chained,
            x=None,
            rank_evaluable_n=len(sub_source),
        )

    for x in spec["stage2_X_grid"]:
        selected_flag = keep_mask_from_rank(ranked["rank_status"], ranked["rank_percentile"], str(spec["orientation"]), float(x))
        tmp = ranked.assign(selected_flag=selected_flag)
        for split in SPLITS:
            sub = split_frame(tmp, split)
            selected = sub.loc[bool_series(sub["selected_flag"])]
            random_stats = matched_random_quantiles_by_cell(
                tmp,
                "selected_flag",
                "stage_2_continuation_target",
                config,
                split,
                f"stage2_random:{feature}:{x}:{split}",
            )
            append_stage2_row(
                split=split,
                readout="matched_random_same_budget_readout",
                denominator=sub,
                selected=selected,
                x=float(x),
                rank_evaluable_n=int(sub["rank_status"].eq("rank_evaluable").sum()),
                random_stats=random_stats,
                rate_override=random_stats["random_p50"],
            )
            append_stage2_row(
                split=split,
                readout="simple_stage2_backbone_vs_complex_stage2_readout",
                denominator=sub,
                selected=selected,
                x=float(x),
                rank_evaluable_n=int(sub["rank_status"].eq("rank_evaluable").sum()),
                random_stats=random_stats,
                complex_stats=complex_stage2_stats(tmp, split),
            )
    return pd.DataFrame(rows)


def lowcap_support_reasons(row: pd.Series, drift: pd.Series, config: dict[str, Any]) -> list[str]:
    g = config["gates"]
    reasons = []
    if int(row.get("selected_n", 0)) < int(g["selected_n_min"]):
        reasons.append("selected_n_below_min")
    if int(row.get("denominator_positive_n", 0)) < int(g["denominator_positive_n_min"]):
        reasons.append("denominator_positive_n_below_min")
    if int(row.get("bootstrap_replicate_valid_n", 0)) < int(config["bootstrap"]["bootstrap_min_valid_replicates"]):
        reasons.append("bootstrap_replicate_valid_n_below_min")
    if float(row.get("delta_vs_simple_backbone", np.inf)) > float(g["low_capacity_delta_vs_simple_backbone_max"]):
        reasons.append("delta_vs_simple_backbone_not_supported")
    if float(row.get("delta_vs_simple_backbone_ci95_high", np.inf)) >= 0:
        reasons.append("simple_backbone_ci_crosses_zero")
    if float(drift.get("budget_abs_delta_rank_evaluable_vs_X", np.inf)) > float(g["budget_abs_delta_rank_evaluable_vs_X_max"]):
        reasons.append("budget_abs_delta_rank_evaluable_vs_X_above_max")
    if float(drift.get("rank_not_evaluable_rate", np.inf)) > float(g["rank_not_evaluable_rate_max"]):
        reasons.append("rank_not_evaluable_rate_above_max")
    return reasons


def decision_row(
    input_ok: bool,
    input_reasons: str,
    train_sel: pd.DataFrame,
    phase1_readout: pd.DataFrame,
    phase1_drift: pd.DataFrame,
    phase1_reasons: list[str],
    lowcap_readout: pd.DataFrame,
    lowcap_drift: pd.DataFrame,
    lowcap_reasons: list[str],
    config: dict[str, Any],
) -> pd.DataFrame:
    train_status = str(train_sel.iloc[0].get("selection_status", "")) if not train_sel.empty else "no_selection"
    p1_rob = phase1_readout.loc[phase1_readout["split"].eq("robustness")].iloc[0] if not phase1_readout.empty else pd.Series(dtype=object)
    p1_drift = phase1_drift.loc[phase1_drift["split"].eq("robustness")].iloc[0] if not phase1_drift.empty else pd.Series(dtype=object)
    lc_rob = lowcap_readout.loc[lowcap_readout["split"].eq("robustness")].iloc[0] if not lowcap_readout.empty else pd.Series(dtype=object)
    p1_pass = not phase1_reasons and train_status == "selected_train_frozen"
    lc_pass = p1_pass and not lowcap_reasons and not lowcap_readout.empty
    if not input_ok:
        state = "12A7b_blocked_input_or_pit_failure"
    elif train_status == "no_train_eligible_backbone_tuple":
        state = "12A7b_backbone_diagnostic_only"
    elif train_status == "no_train_random_uplift_candidate" or "direction_stability_failed" in phase1_reasons or "delta_vs_random_p50_not_supported" in phase1_reasons:
        state = "12A7b_no_simple_backbone_transport"
    elif not p1_pass:
        state = "12A7b_backbone_diagnostic_only"
    elif lc_pass:
        state = "12A7b_low_capacity_monotone_supported_over_backbone"
    else:
        state = "12A7b_simple_backbone_supported_low_capacity_not_supported"
    if state == "12A7b_low_capacity_monotone_supported_over_backbone":
        followup = "low_capacity_backbone_chained_stage2_validation"
        next_allowed = "none"
    elif state == "12A7b_simple_backbone_supported_low_capacity_not_supported":
        followup = "simple_backbone_policy_replay_or_12A8_calibration_scope_review"
        next_allowed = "none"
    elif state in {"12A7b_backbone_diagnostic_only", "12A7b_no_simple_backbone_transport"}:
        followup = ""
        next_allowed = "requirement_12a9_vol_scaled_label_stability_and_separability_audit.md"
    else:
        followup = ""
        next_allowed = "none"
    reasons = []
    if not input_ok:
        reasons.append(input_reasons)
    reasons.extend(phase1_reasons)
    reasons.extend("phase2_" + item for item in lowcap_reasons)
    return pd.DataFrame(
        [
            {
                "decision_state": state,
                "input_gate_status": "pass" if input_ok else "fail",
                "pit_gate_status": "pass" if input_ok else "fail",
                "phase_1_simple_backbone_gate_status": "pass" if p1_pass else ("diagnostic_only" if state == "12A7b_backbone_diagnostic_only" else "fail"),
                "phase_2_enabled": bool(p1_pass),
                "phase_2_execution_policy": config["monotone"]["phase_2_execution_policy"],
                "phase_2_config_skip_allowed": False,
                "selected_primary_rule_id": p1_rob.get("rule_id", ""),
                "selected_primary_simple_backbone_tuple": train_sel.iloc[0].get("feature_list", "") if not train_sel.empty else "",
                "selected_primary_X": train_sel.iloc[0].get("stage1_budget_X", np.nan) if not train_sel.empty else np.nan,
                "robustness_selected_n": p1_rob.get("selected_n", np.nan),
                "robustness_budget_total": p1_rob.get("selected_budget_total", np.nan),
                "robustness_budget_abs_delta_rank_evaluable_vs_X": p1_drift.get("budget_abs_delta_rank_evaluable_vs_X", np.nan),
                "robustness_fast_fail_rate": p1_rob.get("selected_fast_fail_rate", np.nan),
                "robustness_delta_vs_random_p50": p1_rob.get("delta_vs_random_p50", np.nan),
                "robustness_delta_vs_random_p50_ci95_low": p1_rob.get("delta_vs_random_p50_ci95_low", np.nan),
                "robustness_delta_vs_random_p50_ci95_high": p1_rob.get("delta_vs_random_p50_ci95_high", np.nan),
                "robustness_delta_vs_complex_model": p1_rob.get("delta_vs_complex_model", np.nan),
                "robustness_delta_vs_complex_model_ci95_low": p1_rob.get("delta_vs_complex_model_ci95_low", np.nan),
                "robustness_delta_vs_complex_model_ci95_high": p1_rob.get("delta_vs_complex_model_ci95_high", np.nan),
                "complex_score_source_caveat": p1_rob.get("complex_score_source_caveat", ""),
                "complex_comparator_status": p1_rob.get("complex_comparator_status", ""),
                "low_capacity_rule_id": lc_rob.get("rule_id", ""),
                "low_capacity_vs_simple_backbone_delta": lc_rob.get("delta_vs_simple_backbone", np.nan),
                "low_capacity_vs_simple_backbone_ci95_low": lc_rob.get("delta_vs_simple_backbone_ci95_low", np.nan),
                "low_capacity_vs_simple_backbone_ci95_high": lc_rob.get("delta_vs_simple_backbone_ci95_high", np.nan),
                "validation_gate_role": "readout_only_stress_split",
                "gate_failure_reasons": ";".join([x for x in reasons if x]),
                "next_allowed_requirement": next_allowed,
                "recommended_internal_followup": followup,
            }
        ]
    )


def build_report(
    decision: pd.DataFrame,
    phase1_readout: pd.DataFrame,
    phase1_drift: pd.DataFrame,
    stability: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    validation = phase1_readout.loc[phase1_readout["split"].eq("validation")].iloc[0] if not phase1_readout.empty and phase1_readout["split"].eq("validation").any() else pd.Series(dtype=object)
    validation_drift = phase1_drift.loc[phase1_drift["split"].eq("validation")].iloc[0] if not phase1_drift.empty and phase1_drift["split"].eq("validation").any() else pd.Series(dtype=object)
    robust_stability = stability.loc[stability["split"].eq("robustness")] if not stability.empty and "split" in stability else pd.DataFrame()
    status_counts = robust_stability["direction_status"].value_counts().to_dict() if not robust_stability.empty else {}
    stress_warning = (
        "validation readout-only stress: "
        f"selected_n={fmt(validation.get('selected_n', np.nan))}, "
        f"budget_total={fmt(validation.get('selected_budget_total', np.nan))}, "
        f"budget_abs_delta_rank_evaluable_vs_X={fmt(validation_drift.get('budget_abs_delta_rank_evaluable_vs_X', np.nan))}, "
        f"delta_vs_random_p50={fmt(validation.get('delta_vs_random_p50', np.nan))}"
    )
    weak_or_fail = int(status_counts.get("weak", 0)) + int(status_counts.get("fail", 0))
    stability_warning = (
        "no robustness sign inversion or slope-collapse slice detected"
        if weak_or_fail == 0
        else f"robustness stability stress: weak_or_fail_slice_n={weak_or_fail}, status_counts={json.dumps(status_counts, sort_keys=True)}"
    )
    return f"""
# 12A7b Direction C simple-backbone operating-rule validation report

## Decision

| field | value |
|---|---:|
| final decision | `{d['decision_state']}` |
| selected primary simple backbone tuple | `{d['selected_primary_simple_backbone_tuple']}` |
| selected X | {fmt(d['selected_primary_X'])} |
| robustness selected_n | {fmt(d['robustness_selected_n'])} |
| robustness budget_total | {fmt(d['robustness_budget_total'])} |
| robustness budget_abs_delta_rank_evaluable_vs_X | {fmt(d['robustness_budget_abs_delta_rank_evaluable_vs_X'])} |
| robustness fast_fail_rate | {fmt(d['robustness_fast_fail_rate'])} |
| delta_vs_random_p50 | {fmt(d['robustness_delta_vs_random_p50'])} |
| delta_vs_random_p50 CI low | {fmt(d['robustness_delta_vs_random_p50_ci95_low'])} |
| delta_vs_random_p50 CI high | {fmt(d['robustness_delta_vs_random_p50_ci95_high'])} |
| delta_vs_complex_model | {fmt(d['robustness_delta_vs_complex_model'])} |
| delta_vs_complex_model CI low | {fmt(d['robustness_delta_vs_complex_model_ci95_low'])} |
| delta_vs_complex_model CI high | {fmt(d['robustness_delta_vs_complex_model_ci95_high'])} |
| complex_score_source_caveat | `{d['complex_score_source_caveat']}` |
| complex_comparator_status | `{d['complex_comparator_status']}` |
| phase_2_execution_policy | `{d['phase_2_execution_policy']}` |
| low_capacity_vs_simple_backbone_delta | {fmt(d['low_capacity_vs_simple_backbone_delta'])} |
| low_capacity_vs_simple_backbone CI low | {fmt(d['low_capacity_vs_simple_backbone_ci95_low'])} |
| low_capacity_vs_simple_backbone CI high | {fmt(d['low_capacity_vs_simple_backbone_ci95_high'])} |
| validation_gate_role | `{d['validation_gate_role']}` |
| validation stress warning | {stress_warning} |
| robustness stability warning | {stability_warning} |
| recommended next step | `{d['recommended_internal_followup']}` |

Validation is readout-only because prior 12A6c / 12A7 evidence shows a pathological low-base-rate budget-drift interval.
No feature, orientation, X, or model capacity was chosen using validation or robustness.
If phase-1 simple backbone passes, phase-2 low-capacity monotone validation was mandatory and could not be skipped by config.
The conclusion applies only to C0 risk_on events, not all regimes.

Gate failure reasons: `{d['gate_failure_reasons']}`
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
        "requirement_path": str(requirement_path),
        "requirement_hash": path_sha(requirement_path),
        "entrypoint_hash": path_sha(Path(__file__).resolve()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_sha256": path_sha(config_path),
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
    a7_decision = read_table(resolved["a7_trailing_rank_decision"]) if resolved["a7_trailing_rank_decision"].exists() else pd.DataFrame()
    input_ok, input_reasons = input_gate_pass(input_audit, a7_decision)
    if mode == "check-inputs":
        if not input_ok:
            raise RuntimeError(f"12A7b input check failed: {input_reasons}")
        print(f"{RUN_ID}: input audit ok ({len(input_audit)} artifacts)")
        return 0
    if not input_ok:
        raise RuntimeError(f"12A7b required inputs missing or invalid: {input_reasons}")

    feature_dict = read_table(resolved["two_stage_feature_dictionary"])
    pit = read_table(resolved["two_stage_feature_pit_audit"])
    raw_universe = read_table(resolved["two_stage_event_universe"])
    frame = load_primary_universe(resolved)
    policy = history_policy(config)
    scope_audit = scope_universe_audit(raw_universe, frame)
    candidate_status = candidate_statuses(config, feature_dict, pit, frame)
    available = candidate_status.loc[candidate_status["candidate_status"].eq("candidate_available")]
    if available.empty:
        raise RuntimeError("12A7b has no PIT-valid stage-1 backbone candidate")

    random_labels, random_status = prepare_random_labels(resolved)
    if random_status != "pass":
        raise RuntimeError("12A7b random labels failed path-cache read status")

    feature_ranked = {feature: rank_feature(frame, feature, policy, config) for feature in available["feature_name"].astype(str)}
    candidate_readouts = []
    candidate_drifts = []
    random_audits = []
    bootstrap_reps = []
    selections = {}
    score_matrix = frame.copy()
    for feature, ranked in feature_ranked.items():
        score_matrix[f"{feature}__rank_percentile"] = ranked["rank_percentile"].to_numpy()
        score_matrix[f"{feature}__rank_status"] = ranked["rank_status"].to_numpy()
        orientation = str(config["candidate_features"][feature])
        for x in [float(v) for v in config["stage1_X_grid"]]:
            rid = "simple_" + rule_hash([feature], {feature: orientation}, x, "single_feature_backbone")
            selection = selection_from_rank(
                ranked,
                rule_id=rid,
                rule_family="single_feature_backbone",
                validation_phase="phase_1_single_feature_backbone",
                feature_list=[feature],
                orientation={feature: orientation},
                x=x,
                score_col=feature,
            )
            selections[rid] = selection
            readout = readout_for_selection(selection)
            random_selected, random_audit, quant, replay_status = random_replay(selection, random_labels, config)
            random_audits.append(random_audit)
            readout = attach_random(readout, quant)
            readout, reps = update_random_ci(readout, selection, random_selected, config, rid + "_random")
            if not reps.empty:
                bootstrap_reps.append(reps)
            readout["readout_status"] = "ok" if replay_status == "pass" else "random_replay_failed"
            candidate_readouts.append(readout)
            candidate_drifts.append(budget_drift_for_selection(selection))

    candidate_curve = pd.concat(candidate_readouts, ignore_index=True)
    budget_drift = pd.concat(candidate_drifts, ignore_index=True)
    train_sel = train_selection(candidate_curve, config)

    phase1_readout = pd.DataFrame()
    phase1_drift = pd.DataFrame()
    phase1_selection = pd.DataFrame()
    complex_comp = pd.DataFrame()
    phase1_reasons = []
    selected_feature = ""
    selected_x = np.nan
    if str(train_sel.iloc[0].get("selection_status", "")) == "selected_train_frozen":
        selected_rule_id = str(train_sel.iloc[0]["rule_id"])
        selected_feature = str(train_sel.iloc[0]["feature_list"])
        selected_x = float(train_sel.iloc[0]["stage1_budget_X"])
        phase1_selection = selections[selected_rule_id]
        phase1_readout = candidate_curve.loc[candidate_curve["rule_id"].eq(selected_rule_id)].copy()
        phase1_drift = budget_drift.loc[budget_drift["rule_id"].eq(selected_rule_id)].copy()
        complex_comp, complex_base, complex_reps = matched_complex_comparator(phase1_selection, frame, policy, config, a7_decision)
        if not complex_reps.empty:
            bootstrap_reps.append(complex_reps)
        phase1_readout = merge_complex_into_readout(phase1_readout, complex_comp)
        rob = phase1_readout.loc[phase1_readout["split"].eq("robustness")].iloc[0]
        rob_drift = phase1_drift.loc[phase1_drift["split"].eq("robustness")].iloc[0]
        phase1_reasons = phase1_support_reasons(rob, rob_drift, config)
        phase1_readout["phase_1_simple_backbone_gate_status"] = "pass" if not phase1_reasons else "fail"
    else:
        phase1_reasons = [str(train_sel.iloc[0].get("selection_status", "selection_failed"))]

    phase1_pass = not phase1_reasons and not phase1_readout.empty

    lowcap_card = pd.DataFrame()
    lowcap_readout = pd.DataFrame()
    lowcap_drift = pd.DataFrame()
    lowcap_reasons = []
    lowcap_random_audit = pd.DataFrame()
    simple_match = pd.DataFrame()
    if phase1_pass:
        lowcap_card, lowcap_selections = monotone_candidates(frame, feature_ranked, selected_feature, selected_x, policy, config)
        picked = select_low_capacity(lowcap_card)
        if picked.empty:
            lowcap_reasons = ["no_low_capacity_candidate"]
        else:
            lowcap_card["selected_low_capacity_rule"] = lowcap_card["rule_id"].astype(str).eq(str(picked["rule_id"]))
            lowcap_selection = lowcap_selections[str(picked["rule_id"])]
            lowcap_readout = readout_for_selection(lowcap_selection)
            lowcap_drift = budget_drift_for_selection(lowcap_selection)
            random_selected, lowcap_random_audit, quant, replay_status = random_replay(lowcap_selection, random_labels, config)
            lowcap_readout = attach_random(lowcap_readout, quant)
            lowcap_readout, reps = update_random_ci(lowcap_readout, lowcap_selection, random_selected, config, str(picked["rule_id"]) + "_random")
            if not reps.empty:
                bootstrap_reps.append(reps)
            simple_match, simple_base, simple_reps = simple_backbone_matched_for_lowcap(lowcap_selection, phase1_selection, selected_feature, config)
            if not simple_reps.empty:
                bootstrap_reps.append(simple_reps)
            lowcap_readout = merge_simple_match(lowcap_readout, simple_match)
            lowcap_readout["phase_1_simple_backbone_gate_status"] = "pass"
            lowcap_readout["phase_2_enabled"] = True
            rob = lowcap_readout.loc[lowcap_readout["split"].eq("robustness")].iloc[0]
            rob_drift = lowcap_drift.loc[lowcap_drift["split"].eq("robustness")].iloc[0]
            lowcap_reasons = lowcap_support_reasons(rob, rob_drift, config)
            lowcap_card["low_capacity_status"] = np.where(lowcap_card["selected_low_capacity_rule"], "selected_train_frozen", lowcap_card["low_capacity_status"])
    else:
        lowcap_card = pd.DataFrame(
            [
                {
                    "rule_id": "low_capacity_skipped",
                    "rule_family": "monotone_additive_rank_score",
                    "low_capacity_status": "skipped_backbone_not_supported",
                    "diagnostic_only_flag": True,
                    "not_allowed_for_decision": True,
                }
            ]
        )
        lowcap_readout = pd.DataFrame(
            [
                {
                    "stage": "stage_1",
                    "split": "robustness",
                    "rule_id": "low_capacity_skipped",
                    "rule_family": "monotone_additive_rank_score",
                    "validation_phase": "phase_2_low_capacity_monotone",
                    "phase_1_simple_backbone_gate_status": "fail",
                    "phase_2_enabled": False,
                    "readout_status": "skipped_backbone_not_supported",
                    "diagnostic_only_flag": True,
                }
            ]
        )

    stability = stability_slices(phase1_selection, config) if not phase1_selection.empty else pd.DataFrame()
    stage2_diag = stage2_diagnostic(frame, config, policy, phase1_selection)

    decision = decision_row(
        input_ok,
        input_reasons,
        train_sel,
        phase1_readout,
        phase1_drift,
        phase1_reasons,
        lowcap_readout,
        lowcap_drift,
        lowcap_reasons,
        config,
    )

    random_audit_all = pd.concat([pd.concat(random_audits, ignore_index=True), lowcap_random_audit], ignore_index=True)
    bootstrap_all = pd.concat(bootstrap_reps, ignore_index=True) if bootstrap_reps else pd.DataFrame(columns=["comparison_id", "split", "replicate_id", "delta"])
    score_matrix["selected_primary_simple_backbone_rule_id"] = decision.iloc[0].get("selected_primary_rule_id", "")

    frames = {
        "input_artifact_audit": input_audit,
        "scope_universe_audit": scope_audit,
        "simple_backbone_train_selection": train_sel,
        "simple_backbone_candidate_curve": candidate_curve,
        "simple_backbone_operating_point_readout": phase1_readout if not phase1_readout.empty else candidate_curve.head(0),
        "simple_backbone_budget_drift_audit": phase1_drift if not phase1_drift.empty else budget_drift.head(0),
        "simple_backbone_random_same_budget_audit": random_audit_all,
        "complex_model_matched_comparator": complex_comp,
        "low_capacity_monotone_model_card": lowcap_card,
        "low_capacity_monotone_readout": lowcap_readout,
        "backbone_stability_slice_audit": stability,
        "stage2_diagnostic_backbone_readout": stage2_diag,
        "direction_c_decision": decision,
        "score_matrix": score_matrix,
        "bootstrap_replicates": bootstrap_all,
    }
    for key, frame_out in frames.items():
        write_df(paths[key], frame_out)
    write_text(paths["report"], build_report(decision, phase1_readout, phase1_drift, stability))
    frames["report"] = pd.DataFrame([{"path": str(paths["report"])}])
    manifest = build_manifest(paths, frames, decision, config_path, resolved["requirement"], config)
    write_json(paths["manifest"], manifest)
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pipeline(Path(args.config), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

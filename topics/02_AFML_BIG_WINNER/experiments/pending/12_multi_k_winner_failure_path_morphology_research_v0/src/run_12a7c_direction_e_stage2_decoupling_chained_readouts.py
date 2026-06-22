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


def _load_a7_helpers():
    path = EXPERIMENT_DIR / "src" / "run_12a7_direction_a_trailing_rank_operating_point_audit.py"
    spec = importlib.util.spec_from_file_location("run_12a7_direction_a_helpers_for_12a7c", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


A7 = _load_a7_helpers()

RUN_ID = "12A7c_direction_e_stage2_decoupling_chained_readouts"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a7c_direction_e_stage2_decoupling_chained_readouts.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
TARGET_COL = "stage_2_continuation_target"
COMPLEX_SCORE_COL = "stage2_continuation_score"
RANDOM_TARGET_COL = "random_stage_2_continuation_target"
ANCHOR_SUPPORTED_STATE = "12A7b_simple_backbone_supported_low_capacity_not_supported"
ANCHOR_UNSUPPORTED_LOW_CAP_STATE = "12A7b_low_capacity_monotone_supported_over_backbone"

EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "a7_input_artifact_audit": ("artifact_id", "read_status", "schema_status", "sha256"),
    "a7_trailing_rank_decision": ("decision_state",),
    "a7_trailing_rank_operating_point_readout": ("stage", "split", "selected_n"),
    "a7_trailing_rank_budget_curve_readout": ("stage", "split", "stage1_budget_X"),
    "a7_trailing_rank_budget_drift_audit": ("stage", "split", "budget_abs_delta_rank_evaluable_vs_X"),
    "a7_trailing_rank_single_feature_challenger": ("stage", "split"),
    "a7_trailing_rank_random_same_budget_audit": ("stage", "split", "random_selected_n"),
    "a7_trailing_rank_score_quality_metrics": ("stage", "split"),
    "a7_trailing_rank_decile_lift_readout": ("stage", "split"),
    "a7_split_time_boundary_audit": ("eval_split", "split_time_boundary_gate_pass"),
    "a7_score_reproduction_audit": ("stage", "score_reproduction_status", "score_source_caveat"),
    "a7_report": (),
    "a7_manifest": (),
    "a7_trailing_rank_score_matrix": (
        "meta_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "split",
        "board_bucket",
        "calendar_month",
        "stage_2_decision_pos",
        COMPLEX_SCORE_COL,
        TARGET_COL,
    ),
    "a7b_input_artifact_audit": ("artifact_id", "read_status", "schema_status", "sha256"),
    "a7b_simple_backbone_train_selection": (
        "rule_id",
        "feature_list",
        "feature_orientation_json",
        "stage1_budget_X",
        "history_policy_id",
    ),
    "a7b_simple_backbone_operating_point_readout": ("stage", "split", "rule_id", "stage1_budget_X", "selected_n"),
    "a7b_simple_backbone_budget_drift_audit": ("split", "rule_id", "budget_abs_delta_rank_evaluable_vs_X"),
    "a7b_backbone_stability_slice_audit": ("slice_type", "direction_status"),
    "a7b_stage2_diagnostic_backbone_readout": ("diagnostic_readout", "split"),
    "a7b_direction_c_decision": (
        "decision_state",
        "selected_primary_rule_id",
        "selected_primary_simple_backbone_tuple",
        "selected_primary_X",
    ),
    "a7b_report": (),
    "a7b_manifest": (),
    "a7b_simple_backbone_score_matrix": ("meta_event_id", "split", "board_bucket", "calendar_month"),
    "a7b_bootstrap_replicates": (),
    "two_stage_event_universe": ("meta_event_id", "source_arm_is_c0", "market_regime_bucket"),
    "two_stage_event_targets": (
        "meta_event_id",
        "instrument",
        "split",
        "stage_1_evaluable",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        TARGET_COL,
    ),
    "two_stage_feature_dictionary": ("feature_name", "pit_status", "allowed_for_stage_2"),
    "two_stage_feature_pit_audit": ("feature_name", "pit_status", "allowed_for_stage_2"),
    "two_stage_split_time_boundary_audit": ("eval_split", "split_time_boundary_gate_pass"),
    "two_stage_feature_matrix": ("meta_event_id", "instrument", "event_t0_date", "event_t0_pos", "split", "board_bucket", "path_key"),
    "stage2_path_cache": (
        "path_key",
        "instrument",
        "entry_pos",
        "entry_price",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "continuation_U20_L10_H2_20",
    ),
    "two_stage_row_level_scores": (),
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

OPTIONAL_INPUTS = {"a7b_simple_backbone_score_matrix", "a7b_bootstrap_replicates", "two_stage_row_level_scores"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A7c Direction E stage-2 decoupling/chained readouts.")
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
        "stage1_anchor_rule_card": TABLE_DIR / "stage1_anchor_rule_card.csv",
        "stage2_candidate_card": TABLE_DIR / "stage2_candidate_card.csv",
        "stage2_train_selection": TABLE_DIR / "stage2_train_selection.csv",
        "stage2_ground_truth_survivor_readout": TABLE_DIR / "stage2_ground_truth_survivor_readout.csv",
        "stage2_chained_trailing_rank_readout": TABLE_DIR / "stage2_chained_trailing_rank_readout.csv",
        "stage2_random_same_budget_audit": TABLE_DIR / "stage2_random_same_budget_audit.csv",
        "stage2_single_feature_challenger": TABLE_DIR / "stage2_single_feature_challenger.csv",
        "stage2_complex_model_matched_comparator": TABLE_DIR / "stage2_complex_model_matched_comparator.csv",
        "stage2_budget_drift_audit": TABLE_DIR / "stage2_budget_drift_audit.csv",
        "stage2_opportunity_cost_audit": TABLE_DIR / "stage2_opportunity_cost_audit.csv",
        "stage2_stability_slice_audit": TABLE_DIR / "stage2_stability_slice_audit.csv",
        "direction_e_decision": TABLE_DIR / "direction_e_decision.csv",
        "score_matrix": LOCAL_CACHE_DIR / "stage2_decoupling_score_matrix.parquet",
        "bootstrap_replicates": LOCAL_CACHE_DIR / "bootstrap_replicates.parquet",
        "random_stage2_selected": LOCAL_CACHE_DIR / "random_stage2_selected.parquet",
        "report": REPORT_DIR / "stage2_decoupling_chained_readouts_report.md",
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


def row_id_hash(ids: pd.Series | list[Any]) -> str:
    return stable_hash(sorted(pd.Series(ids, dtype=str).dropna().astype(str).tolist()))


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
        optional = artifact_id in OPTIONAL_INPUTS
        read_status = "pass" if exists else ("optional_missing" if optional else "missing")
        schema_status = "pass" if optional and not exists else ("pass" if exists and not required_cols else "not_checked")
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
                "required_flag": not optional,
            }
        )
    return pd.DataFrame(rows)


def input_gate_pass(audit: pd.DataFrame, a7b_decision: pd.DataFrame) -> tuple[bool, str]:
    reasons = []
    required = audit.loc[audit["required_flag"]]
    if not required["read_status"].astype(str).eq("pass").all():
        reasons.append("missing_or_unreadable_required_inputs")
    if not required["schema_status"].astype(str).eq("pass").all():
        reasons.append("required_schema_mismatch")
    if a7b_decision.empty:
        reasons.append("a7b_decision_empty")
    else:
        state = str(a7b_decision.iloc[0].get("decision_state", ""))
        if state == ANCHOR_UNSUPPORTED_LOW_CAP_STATE:
            reasons.append("a7b_low_capacity_monotone_anchor_not_supported_by_12a7c")
        elif state != ANCHOR_SUPPORTED_STATE:
            reasons.append("a7b_stage1_simple_anchor_not_supported")
    return not reasons, ";".join(reasons)


def history_policy(config: dict[str, Any]) -> Any:
    h = config["history_policy"]
    return A7.HistoryPolicy(
        history_policy_id=str(h["history_policy_id"]),
        history_window_mode=str(h["history_window_mode"]),
        trailing_history_window_sessions=int(h["trailing_history_window_sessions"]),
        diagnostic_only_flag=False,
    )


def parse_orientation_json(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): normalize_orientation(v) for k, v in value.items()}
    parsed = json.loads(str(value))
    return {str(k): normalize_orientation(v) for k, v in parsed.items()}


def load_primary_universe(resolved: dict[str, Path]) -> pd.DataFrame:
    features = read_table(resolved["two_stage_feature_matrix"])
    targets = read_table(resolved["two_stage_event_targets"])
    universe = read_table(resolved["two_stage_event_universe"])
    scores = read_table(resolved["a7_trailing_rank_score_matrix"])
    target_cols = [
        "meta_event_id",
        "instrument",
        "split",
        "stage_1_evaluable",
        "stage_1_fast_fail_target",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        TARGET_COL,
        "stage_2_evaluable",
    ]
    universe_cols = ["meta_event_id", "source_arm_is_c0", "market_regime_bucket", "primary_family_id", "source_arm_id"]
    score_cols = [
        "meta_event_id",
        "calendar_month",
        "stage_2_decision_pos",
        COMPLEX_SCORE_COL,
        "score_source_mode",
        "score_source_caveat",
        "stage_2_model_id",
    ]
    frame = features.merge(targets[[c for c in target_cols if c in targets.columns]], on=["meta_event_id", "instrument", "split"], how="left")
    frame = frame.merge(universe[[c for c in universe_cols if c in universe.columns]].drop_duplicates("meta_event_id"), on="meta_event_id", how="left")
    frame = frame.merge(scores[[c for c in score_cols if c in scores.columns]], on="meta_event_id", how="left")
    for col in ("primary_family_id", "source_arm_is_c0", "market_regime_bucket"):
        if col not in frame.columns:
            for candidate_col in (f"{col}_x", f"{col}_y"):
                if candidate_col in frame.columns:
                    frame[col] = frame[candidate_col]
                    break
    frame["event_t0_date"] = frame["event_t0_date"].map(A7.date_text)
    frame["calendar_month"] = frame["calendar_month"].where(frame["calendar_month"].notna(), frame["event_t0_date"].map(A7.month_text))
    frame["calendar_year"] = frame["event_t0_date"].map(A7.year_text)
    frame["event_t0_pos"] = pd.to_numeric(frame["event_t0_pos"], errors="coerce")
    frame["stage_2_decision_pos"] = pd.to_numeric(frame["stage_2_decision_pos"], errors="coerce")
    for col in (
        "source_arm_is_c0",
        "stage_1_evaluable",
        "stage_1_fast_fail_target",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        TARGET_COL,
        "stage_2_evaluable",
    ):
        if col in frame:
            frame[col] = bool_series(frame[col])
    frame["stage2_label_read_status"] = np.where(
        bool_series(frame["stage_2_path_evaluable"])
        & (~bool_series(frame["stage_2_entry_blocked"]))
        & bool_series(frame["stage_2_horizon_complete_20d"])
        & frame[TARGET_COL].notna(),
        "pass",
        "fail",
    )
    frame = frame.loc[
        bool_series(frame["source_arm_is_c0"])
        & frame["market_regime_bucket"].astype(str).eq("risk_on")
        & bool_series(frame["stage_1_evaluable"])
    ].copy()
    return frame


def scope_universe_audit(raw: pd.DataFrame, primary: pd.DataFrame, decoupled: pd.DataFrame, chained: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        raw_s = split_frame(raw, split) if "split" in raw.columns else raw
        pri = split_frame(primary, split)
        dec = split_frame(decoupled, split)
        ch = split_frame(chained, split)
        rows.append(
            {
                "scope_id": "c0_risk_on_stage1_evaluable",
                "split": split,
                "raw_event_n": int(len(raw_s)),
                "primary_scope_n": int(len(pri)),
                "ground_truth_survivor_n": int(len(dec)),
                "stage1_anchor_chained_survivor_n": int(len(ch)),
                "excluded_event_n": int(max(len(raw_s) - len(pri), 0)),
                "source_arm_is_c0_rate": float(bool_series(raw_s["source_arm_is_c0"]).mean()) if "source_arm_is_c0" in raw_s and len(raw_s) else np.nan,
                "market_regime_risk_on_rate": float(raw_s["market_regime_bucket"].astype(str).eq("risk_on").mean()) if "market_regime_bucket" in raw_s and len(raw_s) else np.nan,
                "stage_1_evaluable_rate": float(bool_series(raw_s["stage_1_evaluable"]).mean()) if "stage_1_evaluable" in raw_s and len(raw_s) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def resolve_anchor(a7b_decision: pd.DataFrame, train_selection: pd.DataFrame, readout: pd.DataFrame) -> dict[str, Any]:
    decision = a7b_decision.iloc[0]
    rule_id = str(decision["selected_primary_rule_id"])
    feature = str(decision["selected_primary_simple_backbone_tuple"])
    x = float(decision["selected_primary_X"])
    candidates = train_selection.loc[train_selection["rule_id"].astype(str).eq(rule_id)].copy()
    if candidates.empty:
        candidates = readout.loc[readout["rule_id"].astype(str).eq(rule_id)].copy()
    if candidates.empty:
        raise RuntimeError(f"Could not resolve 12A7b selected rule row: {rule_id}")
    row = candidates.iloc[0]
    orient_map = parse_orientation_json(row["feature_orientation_json"])
    if len(orient_map) != 1:
        raise RuntimeError("12A7c only supports one-feature 12A7b simple backbone anchors")
    orient_feature = next(iter(orient_map))
    orientation = orient_map[orient_feature]
    if feature != orient_feature:
        feature = orient_feature
    return {
        "stage1_anchor_rule_id": rule_id,
        "stage1_anchor_feature": feature,
        "stage1_anchor_orientation": orientation,
        "stage1_anchor_X": x,
        "feature_list_hash": row.get("feature_list_hash", ""),
        "history_policy_id": row.get("history_policy_id", ""),
        "history_window_mode": row.get("history_window_mode", ""),
        "trailing_history_window_sessions": row.get("trailing_history_window_sessions", np.nan),
    }


def reconstruct_stage1_anchor(
    frame: pd.DataFrame,
    anchor: dict[str, Any],
    readout: pd.DataFrame,
    local_cache_path: Path,
    policy: Any,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, bool, str]:
    h = config["history_min_n"]
    feature = str(anchor["stage1_anchor_feature"])
    ranked = A7.rolling_percentiles(
        frame.copy(),
        score_col=feature,
        pos_col="event_t0_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_1_global_min_history_n"]),
        board_min_history_n=int(h["stage_1_board_min_history_n"]),
    )
    ranked["stage1_anchor_selected_flag"] = keep_mask_from_rank(
        ranked["rank_status"], ranked["rank_percentile"], str(anchor["stage1_anchor_orientation"]), float(anchor["stage1_anchor_X"])
    )
    count_status = "pass"
    count_rows_out = []
    for split in ("train", "validation", "robustness"):
        actual = int(bool_series(split_frame(ranked, split)["stage1_anchor_selected_flag"]).sum())
        expected_rows = readout.loc[
            readout["stage"].astype(str).eq("stage_1")
            & readout["rule_id"].astype(str).eq(str(anchor["stage1_anchor_rule_id"]))
            & np.isclose(pd.to_numeric(readout["stage1_budget_X"], errors="coerce"), float(anchor["stage1_anchor_X"]))
            & readout["split"].astype(str).eq(split)
        ]
        expected = int(expected_rows.iloc[0]["selected_n"]) if not expected_rows.empty else -1
        status = "pass" if actual == expected else "fail"
        if status != "pass":
            count_status = "fail"
        count_rows_out.append({"split": split, "recomputed_selected_n": actual, "publishable_selected_n": expected, "count_reconciliation_status": status})
    if readout["split"].astype(str).eq("all").any():
        actual = int(bool_series(ranked["stage1_anchor_selected_flag"]).sum())
        expected_rows = readout.loc[
            readout["stage"].astype(str).eq("stage_1")
            & readout["rule_id"].astype(str).eq(str(anchor["stage1_anchor_rule_id"]))
            & np.isclose(pd.to_numeric(readout["stage1_budget_X"], errors="coerce"), float(anchor["stage1_anchor_X"]))
            & readout["split"].astype(str).eq("all")
        ]
        expected = int(expected_rows.iloc[0]["selected_n"]) if not expected_rows.empty else -1
        status = "pass" if actual == expected else "fail"
        if status != "pass":
            count_status = "fail"
        count_rows_out.append({"split": "all", "recomputed_selected_n": actual, "publishable_selected_n": expected, "count_reconciliation_status": status})

    local_hash = ""
    local_status = "not_available"
    local_cols = []
    if local_cache_path.exists():
        local = read_table(local_cache_path)
        pct_col = f"{feature}__rank_percentile"
        status_col = f"{feature}__rank_status"
        local_cols = [pct_col, status_col]
        if pct_col in local.columns and status_col in local.columns:
            local_flag = keep_mask_from_rank(local[status_col], local[pct_col], str(anchor["stage1_anchor_orientation"]), float(anchor["stage1_anchor_X"]))
            local_ids = set(local.loc[local_flag, "meta_event_id"].astype(str))
            recomputed_ids = set(ranked.loc[ranked["stage1_anchor_selected_flag"], "meta_event_id"].astype(str))
            local_hash = row_id_hash(list(local_ids))
            local_status = "pass" if local_ids == recomputed_ids else "fail"
        else:
            local_status = "optional_columns_missing"
    recomputed_hash = row_id_hash(ranked.loc[ranked["stage1_anchor_selected_flag"], "meta_event_id"])
    ok = count_status == "pass" and local_status in {"pass", "not_available", "optional_columns_missing"}
    status = "pass" if ok else "fail"
    card = {
        **anchor,
        "stage1_anchor_reconstruction_status": status,
        "stage1_anchor_selected_n_by_split": json.dumps({row["split"]: row["recomputed_selected_n"] for row in count_rows_out}, sort_keys=True),
        "recomputed_anchor_selected_id_hash": recomputed_hash,
        "local_cache_anchor_selected_id_hash": local_hash,
        "local_cache_cross_check_status": local_status,
        "local_cache_rank_columns": "|".join(local_cols),
        "publishable_count_reconciliation_status": count_status,
        "count_reconciliation_detail_json": json.dumps(count_rows_out, sort_keys=True),
    }
    return ranked, pd.DataFrame([card]), ok, "" if ok else "stage1_anchor_reconstruction_failed"


def stage2_survivor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[
        bool_series(frame["no_fast_fail_L10_H20"])
        & bool_series(frame["stage_2_path_evaluable"])
        & (~bool_series(frame["stage_2_entry_blocked"]))
        & bool_series(frame["stage_2_horizon_complete_20d"])
        & frame["stage2_label_read_status"].astype(str).eq("pass")
        & pd.to_numeric(frame["stage_2_decision_pos"], errors="coerce").notna()
    ].copy()


def candidate_card(config: dict[str, Any], feature_dict: pd.DataFrame, pit: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "candidate_id": "complex_stage2_score",
            "candidate_family": "complex_stage2_score",
            "feature_name": COMPLEX_SCORE_COL,
            "orientation": "desc",
            "candidate_status": "candidate_available" if COMPLEX_SCORE_COL in frame.columns else "excluded_missing_score",
            "failure_reason": "",
            "diagnostic_only_flag": False,
        }
    ]
    dict_idx = feature_dict.set_index("feature_name") if "feature_name" in feature_dict else pd.DataFrame()
    pit_idx = pit.set_index("feature_name") if "feature_name" in pit else pd.DataFrame()
    for feature, orientation in config["stage2_candidate_features"].items():
        status = "candidate_available"
        reason = ""
        if feature not in frame.columns:
            status = "excluded_missing_feature"
            reason = "missing_feature"
        elif feature not in dict_idx.index or feature not in pit_idx.index:
            status = "excluded_stage2_pit_unproven"
            reason = "missing_pit_record"
        elif str(dict_idx.loc[feature].get("pit_status", "")) != "pass" or str(pit_idx.loc[feature].get("pit_status", "")) != "pass":
            status = "excluded_stage2_pit_unproven"
            reason = "pit_status_not_pass"
        elif not (boolish(dict_idx.loc[feature].get("allowed_for_stage_2", False)) or boolish(pit_idx.loc[feature].get("allowed_for_stage_2", False))):
            status = "excluded_stage2_not_allowed"
            reason = "allowed_for_stage_2_false"
        rows.append(
            {
                "candidate_id": "single_" + stable_hash({"feature": feature, "orientation": orientation})[:16],
                "candidate_family": "single_feature_stage2",
                "feature_name": feature,
                "orientation": orientation,
                "candidate_status": status,
                "failure_reason": reason,
                "diagnostic_only_flag": False,
            }
        )
    return pd.DataFrame(rows)


def rank_stage2_candidate(frame: pd.DataFrame, score_col: str, policy: Any, config: dict[str, Any]) -> pd.DataFrame:
    h = config["history_min_n"]
    return A7.rolling_percentiles(
        frame.copy(),
        score_col=score_col,
        pos_col="stage_2_decision_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_2_global_min_history_n"]),
        board_min_history_n=int(h["stage_2_board_min_history_n"]),
    )


def make_selection(
    denominator_type: str,
    frame: pd.DataFrame,
    candidate_id: str,
    candidate_family: str,
    feature_name: str,
    orientation: str,
    x: float,
    policy: Any,
    config: dict[str, Any],
    anchor: dict[str, Any],
) -> pd.DataFrame:
    ranked = rank_stage2_candidate(frame, feature_name, policy, config)
    out = ranked.copy()
    out["denominator_type"] = denominator_type
    out["deployable_at_stage_2_decision_time"] = denominator_type == "stage1_anchor_chained_survivor"
    out["stage"] = "stage_2"
    out["candidate_id"] = candidate_id
    out["candidate_family"] = candidate_family
    out["feature_list"] = feature_name
    out["feature_orientation_json"] = json.dumps({feature_name: normalize_orientation(orientation)}, sort_keys=True)
    out["feature_list_hash"] = stable_hash([feature_name])
    out["history_policy_id"] = str(config["history_policy"]["history_policy_id"])
    out["history_window_mode"] = str(config["history_policy"]["history_window_mode"])
    out["trailing_history_window_sessions"] = int(config["history_policy"]["trailing_history_window_sessions"])
    out["stage1_anchor_rule_id"] = anchor["stage1_anchor_rule_id"]
    out["stage2_budget_X"] = float(x)
    out["selected_flag"] = keep_mask_from_rank(out["rank_status"], out["rank_percentile"], orientation, float(x))
    out["diagnostic_only_flag"] = denominator_type == "ground_truth_no_fast_fail_survivor"
    return out


def readout_for_selection(selection: pd.DataFrame) -> pd.DataFrame:
    first = selection.iloc[0]
    rows = []
    for split in SPLITS:
        frame = split_frame(selection, split)
        selected = frame.loc[bool_series(frame["selected_flag"])]
        rank_eval = frame.loc[frame["rank_status"].eq("rank_evaluable")]
        denom_pos = int(bool_series(frame[TARGET_COL]).sum())
        rank_pos = int(bool_series(rank_eval[TARGET_COL]).sum())
        sel_pos = int(bool_series(selected[TARGET_COL]).sum())
        selected_rate = safe_rate(sel_pos, len(selected))
        base_rate = safe_rate(denom_pos, len(frame))
        rows.append(
            {
                "denominator_type": first["denominator_type"],
                "deployable_at_stage_2_decision_time": bool(first["deployable_at_stage_2_decision_time"]),
                "stage": "stage_2",
                "split": split,
                "candidate_id": first["candidate_id"],
                "candidate_family": first["candidate_family"],
                "single_feature_comparison_role": "self" if first["candidate_family"] == "single_feature_stage2" else "matched_challenger",
                "complex_comparison_role": "matched_complex" if first["candidate_family"] == "single_feature_stage2" else "not_applicable",
                "feature_list": first["feature_list"],
                "feature_orientation_json": first["feature_orientation_json"],
                "feature_list_hash": first["feature_list_hash"],
                "history_policy_id": first["history_policy_id"],
                "history_window_mode": first["history_window_mode"],
                "trailing_history_window_sessions": first["trailing_history_window_sessions"],
                "stage1_anchor_rule_id": first["stage1_anchor_rule_id"],
                "stage1_anchor_selected_n": int(bool_series(frame.get("stage1_anchor_selected_flag", pd.Series(False, index=frame.index))).sum()),
                "stage2_budget_X": float(first["stage2_budget_X"]),
                "denominator_n": int(len(frame)),
                "rank_evaluable_n": int(len(rank_eval)),
                "rank_not_evaluable_n": int(frame["rank_status"].ne("rank_evaluable").sum()),
                "denominator_positive_n": denom_pos,
                "rank_evaluable_positive_n": rank_pos,
                "selected_n": int(len(selected)),
                "selected_positive_n": sel_pos,
                "selected_budget_total": safe_rate(len(selected), len(frame)),
                "selected_budget_rank_evaluable": safe_rate(len(selected), len(rank_eval)),
                "selected_continuation_rate": selected_rate,
                "base_continuation_rate": base_rate,
                "delta_vs_base": selected_rate - base_rate if pd.notna(selected_rate) and pd.notna(base_rate) else np.nan,
                "random_p05": np.nan,
                "random_p50": np.nan,
                "random_p95": np.nan,
                "delta_vs_random_p50": np.nan,
                "delta_vs_random_p50_ci95_low": np.nan,
                "delta_vs_random_p50_ci95_high": np.nan,
                "single_feature_matched_rate": np.nan,
                "delta_vs_single_feature": np.nan,
                "delta_vs_single_feature_ci95_low": np.nan,
                "delta_vs_single_feature_ci95_high": np.nan,
                "complex_model_matched_rate": np.nan,
                "delta_vs_complex_model": np.nan,
                "delta_vs_complex_model_ci95_low": np.nan,
                "delta_vs_complex_model_ci95_high": np.nan,
                "bootstrap_denominator_positive_n": sel_pos,
                "bootstrap_replicate_valid_n": 0,
                "rank_not_evaluable_rate": safe_rate(frame["rank_status"].ne("rank_evaluable").sum(), len(frame)),
                "budget_abs_delta_total_vs_X": abs(safe_rate(len(selected), len(frame)) - float(first["stage2_budget_X"])),
                "budget_abs_delta_rank_evaluable_vs_X": abs(safe_rate(len(selected), len(rank_eval)) - float(first["stage2_budget_X"])),
                "readout_status": "ok",
                "diagnostic_only_flag": bool(first["diagnostic_only_flag"]),
                "valid_seed_n": 0,
            }
        )
    return pd.DataFrame(rows)


def prepare_random_labels(resolved: dict[str, Path]) -> tuple[pd.DataFrame, str]:
    random = read_table(resolved["matched_random_sampled_entries"])
    entry_cache = read_table(resolved["entry_forward_path_cache"])
    stage2_cache = read_table(resolved["stage2_path_cache"])
    key = ["path_key", "instrument", "entry_pos", "entry_price"]
    if int(entry_cache.duplicated(key).sum()):
        return random.head(0), "entry_forward_path_cache_duplicate_key"
    if int(stage2_cache.duplicated(key).sum()):
        return random.head(0), "stage2_path_cache_duplicate_key"
    random = random.merge(
        entry_cache[key + ["entry_blocked", "horizon_complete_20d", "time_to_lower_minus_10_20d"]],
        on=key,
        how="left",
    )
    random["random_stage1_label_join_status"] = np.where(random["entry_blocked"].notna(), "pass", "missing_entry_cache_match")
    random["random_stage_1_evaluable"] = random["random_stage1_label_join_status"].eq("pass") & (~bool_series(random["entry_blocked"])) & bool_series(random["horizon_complete_20d"])
    random["random_no_fast_fail_L10_H20"] = bool_series(random["random_stage_1_evaluable"]) & random["time_to_lower_minus_10_20d"].isna()
    keep = key + ["stage_2_entry_blocked", "stage_2_horizon_complete_20d", "continuation_U20_L10_H2_20"]
    random = random.merge(stage2_cache[keep], on=key, how="left")
    random["random_stage2_label_join_status"] = np.where(random["stage_2_entry_blocked"].notna(), "pass", "missing_stage2_cache_match")
    random["random_stage_2_entry_blocked"] = bool_series(random["stage_2_entry_blocked"])
    random["random_stage_2_horizon_complete_20d"] = bool_series(random["stage_2_horizon_complete_20d"])
    random[RANDOM_TARGET_COL] = bool_series(random["continuation_U20_L10_H2_20"])
    random["random_stage_2_evaluable"] = (~bool_series(random["random_stage_2_entry_blocked"])) & bool_series(random["random_stage_2_horizon_complete_20d"])
    random["random_stage2_label_read_status"] = np.where(
        random["random_stage2_label_join_status"].eq("pass")
        & bool_series(random["random_stage_2_evaluable"])
        & random["continuation_U20_L10_H2_20"].notna(),
        "pass",
        "fail",
    )
    status = "pass" if random["random_stage1_label_join_status"].eq("pass").all() and random["random_stage2_label_join_status"].eq("pass").all() else "fail"
    return random, status


def random_rank_columns(random: pd.DataFrame, config: dict[str, Any]) -> tuple[list[str], str]:
    cols = []
    derived = []
    out = random
    for col in config["random_baseline"]["retention_rank_columns"]:
        if col in out.columns:
            cols.append(col)
        else:
            derived.append(col)
    if derived:
        return cols, "derived_from_input_row_order"
    return cols, "configured_columns"


def selected_counts(selection: pd.DataFrame) -> pd.DataFrame:
    cell_cols = ["split", "board_bucket", "calendar_month"]
    return (
        selection.loc[bool_series(selection["selected_flag"]) & selection["split"].astype(str).ne("all")]
        .groupby(cell_cols, dropna=False)
        .size()
        .rename("requested_selected_n")
        .reset_index()
    )


def seed_rate_quantiles(selected: pd.DataFrame) -> pd.DataFrame:
    rates = []
    if selected.empty:
        return pd.DataFrame(columns=["split", "random_p05", "random_p50", "random_p95", "valid_seed_n"])
    for seed, seed_group in selected.groupby("seed", sort=False):
        for split in SPLITS:
            sub = split_frame(seed_group, split)
            rates.append({"seed": seed, "split": split, "random_rate": safe_rate(int(bool_series(sub[RANDOM_TARGET_COL]).sum()), len(sub))})
    seed_rates = pd.DataFrame(rates)
    quant = seed_rates.groupby("split")["random_rate"].quantile([0.05, 0.50, 0.95]).unstack().reset_index()
    quant.columns = ["split", "random_p05", "random_p50", "random_p95"]
    quant["valid_seed_n"] = int(seed_rates["seed"].nunique())
    return quant


def random_replay_decoupled(selection: pd.DataFrame, random: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    cells = selected_counts(selection)
    if cells.empty:
        selected = random.head(0).copy()
        selected["retention_rank_rule"] = ""
        return selected, pd.DataFrame(), pd.DataFrame(), "fail"
    rank_cols, retention_rule = random_rank_columns(random, config)
    cell_cols = ["split", "board_bucket", "calendar_month"]
    seeds = pd.DataFrame({"seed": sorted(random["seed"].dropna().unique())})
    audit = seeds.assign(_k=1).merge(cells.assign(_k=1), on="_k").drop(columns="_k")
    eligible = random.loc[
        bool_series(random["random_no_fast_fail_L10_H20"])
        & bool_series(random["random_stage_2_evaluable"])
        & random["random_stage2_label_read_status"].eq("pass")
    ].merge(cells, on=cell_cols, how="inner")
    eligible = eligible.sort_values(["seed"] + cell_cols + rank_cols, kind="stable")
    eligible["_rank_in_cell"] = eligible.groupby(["seed"] + cell_cols, dropna=False).cumcount() + 1
    selected = eligible.loc[eligible["_rank_in_cell"].le(eligible["requested_selected_n"])].copy()
    sampled = selected.groupby(["seed"] + cell_cols, dropna=False).size().rename("sampled_random_n").reset_index()
    available = eligible.groupby(["seed"] + cell_cols, dropna=False).size().rename("available_random_n").reset_index()
    audit = audit.merge(available, on=["seed"] + cell_cols, how="left").merge(sampled, on=["seed"] + cell_cols, how="left")
    audit[["available_random_n", "sampled_random_n"]] = audit[["available_random_n", "sampled_random_n"]].fillna(0).astype(int)
    audit["stage1_requested_keep_n"] = np.nan
    audit["stage1_sampled_keep_n"] = np.nan
    audit["sampling_status"] = np.where(audit["sampled_random_n"].eq(audit["requested_selected_n"]), "ok", "insufficient_random_cell")
    audit["random_replay_status"] = np.where(audit["sampling_status"].eq("ok"), "pass", "fail")
    audit["retention_rank_rule"] = retention_rule
    valid_seeds = set(audit.groupby("seed")["random_replay_status"].apply(lambda s: s.eq("pass").all()).loc[lambda s: s].index)
    selected = selected.loc[selected["seed"].isin(valid_seeds)].copy()
    selected["retention_rank_rule"] = retention_rule
    status = "pass" if len(valid_seeds) >= int(config["random_baseline"]["min_random_seed_n"]) else "fail"
    return selected, audit, seed_rate_quantiles(selected), status


def build_chained_random_survivors(random: pd.DataFrame, anchor_frame: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cell_cols = ["split", "board_bucket", "calendar_month"]
    anchor_counts = (
        anchor_frame.loc[bool_series(anchor_frame["stage1_anchor_selected_flag"]) & anchor_frame["split"].astype(str).ne("all")]
        .groupby(cell_cols, dropna=False)
        .size()
        .rename("stage1_requested_keep_n")
        .reset_index()
    )
    rank_cols, retention_rule = random_rank_columns(random, config)
    eligible = random.loc[bool_series(random["random_stage_1_evaluable"])].merge(anchor_counts, on=cell_cols, how="inner")
    eligible = eligible.sort_values(["seed"] + cell_cols + rank_cols, kind="stable")
    eligible["_stage1_rank_in_cell"] = eligible.groupby(["seed"] + cell_cols, dropna=False).cumcount() + 1
    keep = eligible.loc[eligible["_stage1_rank_in_cell"].le(eligible["stage1_requested_keep_n"])].copy()
    sampled = keep.groupby(["seed"] + cell_cols, dropna=False).size().rename("stage1_sampled_keep_n").reset_index()
    audit = pd.DataFrame({"seed": sorted(random["seed"].dropna().unique())}).assign(_k=1).merge(anchor_counts.assign(_k=1), on="_k").drop(columns="_k")
    audit = audit.merge(sampled, on=["seed"] + cell_cols, how="left")
    audit["stage1_sampled_keep_n"] = audit["stage1_sampled_keep_n"].fillna(0).astype(int)
    audit["stage1_keep_status"] = np.where(audit["stage1_sampled_keep_n"].eq(audit["stage1_requested_keep_n"]), "pass", "fail")
    audit["retention_rank_rule"] = retention_rule
    survivor = keep.loc[
        bool_series(keep["random_no_fast_fail_L10_H20"])
        & bool_series(keep["random_stage_2_evaluable"])
        & keep["random_stage2_label_read_status"].eq("pass")
    ].copy()
    return survivor, audit


def random_replay_chained(
    selection: pd.DataFrame,
    random_survivor: pd.DataFrame,
    stage1_audit: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    cells = selected_counts(selection)
    if cells.empty:
        selected = random_survivor.head(0).copy()
        selected["retention_rank_rule"] = ""
        return selected, pd.DataFrame(), pd.DataFrame(), "fail"
    rank_cols, retention_rule = random_rank_columns(random_survivor, config)
    cell_cols = ["split", "board_bucket", "calendar_month"]
    audit = stage1_audit.merge(cells, on=cell_cols, how="inner")
    eligible = random_survivor.merge(cells, on=cell_cols, how="inner")
    eligible = eligible.sort_values(["seed"] + cell_cols + rank_cols, kind="stable")
    eligible["_rank_in_cell"] = eligible.groupby(["seed"] + cell_cols, dropna=False).cumcount() + 1
    selected = eligible.loc[eligible["_rank_in_cell"].le(eligible["requested_selected_n"])].copy()
    sampled = selected.groupby(["seed"] + cell_cols, dropna=False).size().rename("sampled_random_n").reset_index()
    available = eligible.groupby(["seed"] + cell_cols, dropna=False).size().rename("available_random_n").reset_index()
    audit = audit.merge(available, on=["seed"] + cell_cols, how="left").merge(sampled, on=["seed"] + cell_cols, how="left")
    audit[["available_random_n", "sampled_random_n"]] = audit[["available_random_n", "sampled_random_n"]].fillna(0).astype(int)
    audit["sampling_status"] = np.where(
        audit["stage1_keep_status"].eq("pass") & audit["sampled_random_n"].eq(audit["requested_selected_n"]),
        "ok",
        "insufficient_random_cell",
    )
    audit["random_replay_status"] = np.where(audit["sampling_status"].eq("ok"), "pass", "fail")
    audit["retention_rank_rule"] = retention_rule
    valid_seeds = set(audit.groupby("seed")["random_replay_status"].apply(lambda s: s.eq("pass").all()).loc[lambda s: s].index)
    selected = selected.loc[selected["seed"].isin(valid_seeds)].copy()
    selected["retention_rank_rule"] = retention_rule
    status = "pass" if len(valid_seeds) >= int(config["random_baseline"]["min_random_seed_n"]) else "fail"
    return selected, audit, seed_rate_quantiles(selected), status


def attach_random(readout: pd.DataFrame, quant: pd.DataFrame) -> pd.DataFrame:
    out = readout.copy()
    if quant.empty:
        return out
    out = out.merge(quant, on="split", how="left", suffixes=("", "_random"))
    for col in ("random_p05", "random_p50", "random_p95", "valid_seed_n"):
        c = f"{col}_random"
        if c in out:
            out[col] = out[c].where(out[c].notna(), out[col])
            out = out.drop(columns=[c])
    out["delta_vs_random_p50"] = out["selected_continuation_rate"] - out["random_p50"]
    return out


def bootstrap_random_ci(model_selected: pd.DataFrame, random_selected: pd.DataFrame, config: dict[str, Any], label: str, split: str) -> tuple[float, float, int, pd.DataFrame]:
    n_resamples = int(config["bootstrap"]["n_resamples"])
    if model_selected.empty or random_selected.empty:
        return np.nan, np.nan, 0, pd.DataFrame()
    seed_rates = []
    for _, group in random_selected.groupby("seed", sort=False):
        seed_rates.append(safe_rate(int(bool_series(group[RANDOM_TARGET_COL]).sum()), len(group)))
    seed_rates = np.asarray([x for x in seed_rates if pd.notna(x)], dtype=float)
    if len(seed_rates) == 0:
        return np.nan, np.nan, 0, pd.DataFrame()
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]) + int(stable_hash(label)[:6], 16))
    y = bool_series(model_selected[TARGET_COL]).astype(float).to_numpy()
    deltas = []
    for _ in range(n_resamples):
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


def update_random_ci(readout: pd.DataFrame, selection: pd.DataFrame, random_selected: pd.DataFrame, config: dict[str, Any], label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = readout.copy()
    reps = []
    for split in SPLITS:
        model = split_frame(selection.loc[bool_series(selection["selected_flag"])], split)
        rand = split_frame(random_selected, split)
        low, high, valid_n, rep = bootstrap_random_ci(model, rand, config, f"{label}:random:{split}", split)
        mask = out["split"].eq(split)
        out.loc[mask, "delta_vs_random_p50_ci95_low"] = low
        out.loc[mask, "delta_vs_random_p50_ci95_high"] = high
        out.loc[mask, "bootstrap_replicate_valid_n"] = valid_n
        if not rep.empty:
            reps.append(rep)
    return out, pd.concat(reps, ignore_index=True) if reps else pd.DataFrame()


def bootstrap_paired_ci(base: pd.DataFrame, left_col: str, right_col: str, label: str, split: str, config: dict[str, Any]) -> tuple[float, float, int, pd.DataFrame]:
    sub = split_frame(base, split)
    if sub.empty or not bool_series(sub[left_col]).any() or not bool_series(sub[right_col]).any():
        return np.nan, np.nan, 0, pd.DataFrame()
    y = bool_series(sub[TARGET_COL]).astype(float).to_numpy()
    left = bool_series(sub[left_col]).to_numpy(dtype=bool)
    right = bool_series(sub[right_col]).to_numpy(dtype=bool)
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]) + 17 + int(stable_hash(label)[:6], 16))
    idx_src = np.arange(len(sub))
    deltas = []
    for _ in range(int(config["bootstrap"]["n_resamples"])):
        idx = rng.choice(idx_src, size=len(idx_src), replace=True)
        l = left[idx]
        r = right[idx]
        if not l.any() or not r.any():
            continue
        yy = y[idx]
        deltas.append(float(yy[l].mean() - yy[r].mean()))
    reps = pd.DataFrame({"comparison_id": label, "split": split, "replicate_id": np.arange(len(deltas)), "delta": deltas})
    if not deltas:
        return np.nan, np.nan, 0, reps
    return (
        float(np.quantile(deltas, float(config["bootstrap"]["ci_low_q"]))),
        float(np.quantile(deltas, float(config["bootstrap"]["ci_high_q"]))),
        len(deltas),
        reps,
    )


def train_selection(readout: pd.DataFrame, denominator_type: str, family: str | None = None) -> pd.DataFrame:
    train = readout.loc[readout["denominator_type"].eq(denominator_type) & readout["split"].eq("train")].copy()
    if family:
        train = train.loc[train["candidate_family"].eq(family)].copy()
    train = train.loc[train["selected_n"].gt(0) & train["rank_evaluable_n"].gt(0)].copy()
    if train.empty:
        return pd.DataFrame(
            [
                {
                    "denominator_type": denominator_type,
                    "selection_status": "no_train_eligible_stage2_candidate",
                    "candidate_family_filter": family or "all",
                }
            ]
        )
    train["_family_rank"] = train["candidate_family"].map({"single_feature_stage2": 0, "complex_stage2_score": 1}).fillna(9)
    train = train.sort_values(
        ["selected_continuation_rate", "selected_n", "_family_rank", "feature_list", "stage2_budget_X"],
        ascending=[False, False, True, True, True],
        kind="stable",
    )
    row = train.iloc[0].drop(labels=["_family_rank"]).to_dict()
    row.update(
        {
            "selection_status": "selected_train_frozen",
            "candidate_family_filter": family or "all",
            "tie_break_path": "highest_train_continuation_rate;larger_selected_n;simpler_candidate_family;feature_name_ASC;X_ASC",
        }
    )
    return pd.DataFrame([row])


def matched_comparator(
    candidate: pd.DataFrame,
    comparator: pd.DataFrame,
    comparator_rate_col: str,
    delta_col: str,
    ci_low_col: str,
    ci_high_col: str,
    label: str,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    comp_cols = ["meta_event_id", "rank_status", "rank_percentile", "feature_list"]
    base = candidate.merge(
        comparator[comp_cols].rename(
            columns={
                "rank_status": "comparator_rank_status",
                "rank_percentile": "comparator_rank_percentile",
                "feature_list": "comparator_feature_list",
            }
        ),
        on="meta_event_id",
        how="left",
    )
    base["_common"] = base["rank_status"].eq("rank_evaluable") & base["comparator_rank_status"].eq("rank_evaluable")
    base["_candidate_selected_common"] = bool_series(base["selected_flag"]) & base["_common"]
    base["_comparator_selected_common"] = False
    cell_cols = ["split", "board_bucket", "calendar_month"]
    parts = []
    for cell, group in base.loc[base["_common"]].groupby(cell_cols, dropna=False):
        mask = (
            base["_candidate_selected_common"]
            & base["split"].eq(cell[0])
            & base["board_bucket"].eq(cell[1])
            & base["calendar_month"].eq(cell[2])
        )
        k = int(mask.sum())
        if k <= 0:
            continue
        picked = group.sort_values(["comparator_rank_percentile", "instrument", "event_t0_date", "meta_event_id"], ascending=[False, True, True, True], kind="stable").head(k)
        parts.append(picked[["meta_event_id"]])
    if parts:
        ids = set(pd.concat(parts, ignore_index=True)["meta_event_id"].astype(str))
        base["_comparator_selected_common"] = base["meta_event_id"].astype(str).isin(ids) & base["_common"]
    rows = []
    reps = []
    for split in SPLITS:
        common = split_frame(base.loc[base["_common"]], split)
        cand = common.loc[bool_series(common["_candidate_selected_common"])]
        comp = common.loc[bool_series(common["_comparator_selected_common"])]
        cand_rate = safe_rate(int(bool_series(cand[TARGET_COL]).sum()), len(cand))
        comp_rate = safe_rate(int(bool_series(comp[TARGET_COL]).sum()), len(comp))
        low, high, valid_n, rep = bootstrap_paired_ci(common, "_candidate_selected_common", "_comparator_selected_common", f"{label}:{split}", split, config)
        if not rep.empty:
            reps.append(rep)
        rows.append(
            {
                "denominator_type": candidate.iloc[0]["denominator_type"],
                "split": split,
                "candidate_id": candidate.iloc[0]["candidate_id"],
                "candidate_family": candidate.iloc[0]["candidate_family"],
                "stage2_budget_X": float(candidate.iloc[0]["stage2_budget_X"]),
                "common_denominator_n": int(len(common)),
                "candidate_matched_selected_n": int(len(cand)),
                "comparator_matched_selected_n": int(len(comp)),
                "candidate_matched_rate": cand_rate,
                comparator_rate_col: comp_rate,
                delta_col: cand_rate - comp_rate if pd.notna(cand_rate) and pd.notna(comp_rate) else np.nan,
                ci_low_col: low,
                ci_high_col: high,
                "bootstrap_replicate_valid_n": valid_n,
                "comparator_feature_list": comparator.iloc[0]["feature_list"],
            }
        )
    return pd.DataFrame(rows), base, pd.concat(reps, ignore_index=True) if reps else pd.DataFrame()


def merge_comparator(readout: pd.DataFrame, comp: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    out = readout.copy()
    keys = ["denominator_type", "split", "candidate_id", "candidate_family", "stage2_budget_X"]
    out = out.merge(comp[keys + value_cols], on=keys, how="left", suffixes=("", "_cmp"))
    for col in value_cols:
        c = f"{col}_cmp"
        if c in out:
            out[col] = out[c].where(out[c].notna(), out[col])
            out = out.drop(columns=[c])
    return out


def support_reasons(row: pd.Series, config: dict[str, Any], mode: str) -> list[str]:
    g = config["gates"]
    reasons = []
    if int(row.get("selected_n", 0)) < int(g["selected_n_min"]):
        reasons.append("selected_n_below_min")
    if int(row.get("denominator_positive_n", 0)) < int(g["denominator_positive_n_min"]):
        reasons.append("denominator_positive_n_below_min")
    if int(row.get("bootstrap_replicate_valid_n", 0)) < int(config["bootstrap"]["bootstrap_min_valid_replicates"]):
        reasons.append("bootstrap_replicate_valid_n_below_min")
    if float(row.get("delta_vs_random_p50", -np.inf)) < float(g["delta_vs_random_p50_min"]):
        reasons.append("delta_vs_random_p50_below_min")
    if float(row.get("delta_vs_random_p50_ci95_low", -np.inf)) <= 0:
        reasons.append("random_ci_low_not_positive")
    if float(row.get("rank_not_evaluable_rate", np.inf)) > float(g["rank_not_evaluable_rate_max"]):
        reasons.append("rank_not_evaluable_rate_above_max")
    if mode in {"chained_single", "chained_complex"}:
        if float(row.get("budget_abs_delta_rank_evaluable_vs_X", np.inf)) > float(g["budget_abs_delta_rank_evaluable_vs_X_max"]):
            reasons.append("budget_abs_delta_rank_evaluable_vs_X_above_max")
    if mode == "chained_complex":
        if float(row.get("delta_vs_single_feature", -np.inf)) < float(g["delta_vs_single_feature_min"]):
            reasons.append("delta_vs_single_feature_below_min")
        if float(row.get("delta_vs_single_feature_ci95_low", -np.inf)) <= 0:
            reasons.append("single_feature_ci_low_not_positive")
    return reasons


def opportunity_cost(primary: pd.DataFrame, decoupled: pd.DataFrame, chained: pd.DataFrame) -> pd.DataFrame:
    rows = []
    primary_fast_fail_rate = safe_rate(int(bool_series(primary["stage_1_fast_fail_target"]).sum()), len(primary)) if "stage_1_fast_fail_target" in primary else np.nan
    anchor = primary.loc[bool_series(primary["stage1_anchor_selected_flag"])]
    anchor_fast_fail_rate = safe_rate(int(bool_series(anchor["stage_1_fast_fail_target"]).sum()), len(anchor)) if "stage_1_fast_fail_target" in anchor else np.nan
    for split in SPLITS:
        gt = split_frame(decoupled, split)
        ch = split_frame(chained, split)
        gt_pos = int(bool_series(gt[TARGET_COL]).sum())
        ch_pos = int(bool_series(ch[TARGET_COL]).sum())
        gt_rate = safe_rate(gt_pos, len(gt))
        ch_rate = safe_rate(ch_pos, len(ch))
        delta = ch_rate - gt_rate if pd.notna(ch_rate) and pd.notna(gt_rate) else np.nan
        if len(ch) < 150:
            status = "insufficient_stage2_sample"
        elif pd.notna(delta) and delta >= -0.01:
            status = "no_material_continuation_cost"
        elif ch_pos >= 30:
            status = "continuation_cost_but_stage2_recoverable"
        else:
            status = "continuation_cost_not_recovered_by_stage2"
        rows.append(
            {
                "split": split,
                "ground_truth_survivor_n": int(len(gt)),
                "ground_truth_survivor_continuation_rate": gt_rate,
                "stage1_anchor_chained_survivor_n": int(len(ch)),
                "stage1_anchor_chained_survivor_continuation_rate": ch_rate,
                "chained_survivor_share_of_ground_truth_survivors": safe_rate(len(ch), len(gt)),
                "continuation_rate_delta_chained_vs_ground_truth": delta,
                "continuation_positive_capture_rate": safe_rate(ch_pos, gt_pos),
                "fast_fail_reduction_from_stage1_anchor": primary_fast_fail_rate - anchor_fast_fail_rate if pd.notna(primary_fast_fail_rate) and pd.notna(anchor_fast_fail_rate) else np.nan,
                "stage1_defense_opportunity_cost_status": status,
            }
        )
    return pd.DataFrame(rows)


def stability_slices(selection: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if selection.empty:
        return pd.DataFrame()
    rows = []
    specs = [
        ("split", ["split"]),
        ("calendar_year", ["split", "calendar_year"]),
        ("board_bucket", ["split", "board_bucket"]),
        ("primary_family_id", ["split", "primary_family_id"]),
        ("calendar_month", ["split", "calendar_month"]),
        ("stage1_anchor_selected_flag", ["split", "stage1_anchor_selected_flag"]),
    ]
    for slice_type, cols in specs:
        for key, group in selection.groupby(cols, dropna=False):
            selected = group.loc[bool_series(group["selected_flag"])]
            selected_n = len(selected)
            selected_rate = safe_rate(int(bool_series(selected[TARGET_COL]).sum()), selected_n)
            base_rate = safe_rate(int(bool_series(group[TARGET_COL]).sum()), len(group))
            random_p50 = base_rate
            if selected_n < 100:
                status = "insufficient_n"
            elif pd.notna(selected_rate) and pd.notna(base_rate) and selected_rate <= base_rate:
                status = "fail"
            elif pd.notna(selected_rate) and pd.notna(random_p50) and selected_rate > random_p50:
                status = "pass"
            else:
                status = "weak"
            row = {
                "slice_type": slice_type,
                "selected_n": int(selected_n),
                "selected_continuation_rate": selected_rate,
                "base_continuation_rate": base_rate,
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
            for col, value in zip(cols, key):
                row[col] = value
            rows.append(row)
    return pd.DataFrame(rows)


def decision_row(
    input_ok: bool,
    input_reasons: str,
    anchor_ok: bool,
    anchor_card: pd.DataFrame,
    dec_sel: pd.DataFrame,
    chain_sel: pd.DataFrame,
    readout: pd.DataFrame,
    opportunity: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    anchor = anchor_card.iloc[0] if not anchor_card.empty else pd.Series(dtype=object)
    if not input_ok or not anchor_ok:
        dec_status = "blocked"
        chain_status = "blocked"
        state = "12A7c_blocked_input_or_stage1_anchor_failure"
        next_allowed = "none"
        if "a7b_low_capacity_monotone_anchor_not_supported_by_12a7c" in str(input_reasons):
            followup = "low_capacity_backbone_chained_stage2_validation"
        else:
            followup = "gate_specific_failure_triage"
    else:
        dec_row = readout.loc[
            readout["denominator_type"].eq("ground_truth_no_fast_fail_survivor")
            & readout["candidate_id"].eq(str(dec_sel.iloc[0]["candidate_id"]))
            & readout["stage2_budget_X"].eq(float(dec_sel.iloc[0]["stage2_budget_X"]))
            & readout["split"].eq("robustness")
        ].iloc[0]
        chain_row = readout.loc[
            readout["denominator_type"].eq("stage1_anchor_chained_survivor")
            & readout["candidate_id"].eq(str(chain_sel.iloc[0]["candidate_id"]))
            & readout["stage2_budget_X"].eq(float(chain_sel.iloc[0]["stage2_budget_X"]))
            & readout["split"].eq("robustness")
        ].iloc[0]
        selected_random_gate_reasons = []
        if str(dec_row.get("readout_status", "")) != "ok":
            selected_random_gate_reasons.append("decoupled_random_replay_failed")
        if str(chain_row.get("readout_status", "")) != "ok":
            selected_random_gate_reasons.append("chained_random_replay_failed")
        if selected_random_gate_reasons:
            dec_status = "blocked"
            chain_status = "blocked"
            state = "12A7c_blocked_input_or_stage1_anchor_failure"
            next_allowed = "none"
            followup = "gate_specific_failure_triage"
            input_reasons = ";".join(selected_random_gate_reasons)
            opp_status = ""
            if not opportunity.empty and opportunity["split"].eq("robustness").any():
                opp_status = str(opportunity.loc[opportunity["split"].eq("robustness"), "stage1_defense_opportunity_cost_status"].iloc[0])
            return pd.DataFrame(
                [
                    {
                        "decision_state": state,
                        "input_gate_status": "fail",
                        "stage1_anchor_reconstruction_status": "pass",
                        "stage2_decoupled_signal_status": dec_status,
                        "stage2_chained_operating_status": chain_status,
                        "stage1_anchor_rule_id": anchor.get("stage1_anchor_rule_id", ""),
                        "stage1_anchor_feature": anchor.get("stage1_anchor_feature", ""),
                        "stage1_anchor_orientation": anchor.get("stage1_anchor_orientation", ""),
                        "stage1_anchor_X": anchor.get("stage1_anchor_X", np.nan),
                        "selected_decoupled_candidate_id": dec_sel.iloc[0].get("candidate_id", "") if not dec_sel.empty else "",
                        "selected_decoupled_candidate_family": dec_sel.iloc[0].get("candidate_family", "") if not dec_sel.empty else "",
                        "selected_decoupled_X": dec_sel.iloc[0].get("stage2_budget_X", np.nan) if not dec_sel.empty else np.nan,
                        "selected_chained_candidate_id": chain_sel.iloc[0].get("candidate_id", "") if not chain_sel.empty else "",
                        "selected_chained_candidate_family": chain_sel.iloc[0].get("candidate_family", "") if not chain_sel.empty else "",
                        "selected_chained_X": chain_sel.iloc[0].get("stage2_budget_X", np.nan) if not chain_sel.empty else np.nan,
                        "selected_chained_deployable_at_stage_2_decision_time": True if not chain_sel.empty else False,
                        "stage1_defense_opportunity_cost_status": opp_status,
                        "gate_failure_reasons": input_reasons,
                        "next_allowed_requirement": next_allowed,
                        "recommended_internal_followup": followup,
                    }
                ]
            )
        dec_reasons = support_reasons(dec_row, config, "decoupled")
        if not dec_reasons:
            dec_status = "positive"
        elif pd.notna(dec_row.get("delta_vs_random_p50", np.nan)) and float(dec_row.get("delta_vs_random_p50", -np.inf)) > 0:
            dec_status = "partial"
        else:
            dec_status = "not_supported"
        chain_mode = "chained_complex" if chain_row["candidate_family"] == "complex_stage2_score" else "chained_single"
        chain_reasons = support_reasons(chain_row, config, chain_mode)
        chained_gates_pass = not chain_reasons
        if dec_status == "positive" and chained_gates_pass and chain_row["candidate_family"] == "complex_stage2_score":
            chain_status = "complex_supported"
            state = "12A7c_stage2_chained_complex_supported"
            next_allowed = "requirement_12a8_probability_calibration_prior_shift_audit.md"
            followup = "two_stage_rank_policy_replay_after_calibration"
        elif dec_status == "positive" and chained_gates_pass:
            chain_status = "simple_selector_supported"
            state = "12A7c_stage2_chained_simple_selector_supported"
            next_allowed = "none"
            followup = "simple_stage2_backbone_policy_replay"
        elif dec_status == "positive":
            chain_status = "decoupled_only_chained_not_supported"
            state = "12A7c_stage2_decoupled_only_chained_not_supported"
            next_allowed = "none"
            followup = "stage1_stage2_objective_tradeoff_review"
        elif dec_status in {"partial", "not_supported"} and chained_gates_pass:
            chain_status = "partial"
            state = "12A7c_stage2_diagnostic_only"
            next_allowed = "requirement_12a9_vol_scaled_label_stability_and_separability_audit.md"
            followup = "label_or_denominator_revision_before_stage2_policy"
        elif dec_status == "partial" or (pd.notna(chain_row.get("delta_vs_random_p50", np.nan)) and float(chain_row.get("delta_vs_random_p50", -np.inf)) > 0):
            chain_status = "partial"
            state = "12A7c_stage2_diagnostic_only"
            next_allowed = "requirement_12a9_vol_scaled_label_stability_and_separability_audit.md"
            followup = "label_or_denominator_revision_before_stage2_policy"
        else:
            chain_status = "not_supported"
            state = "12A7c_no_stage2_signal"
            next_allowed = "requirement_12a9_vol_scaled_label_stability_and_separability_audit.md"
            followup = "label_or_denominator_revision_before_stage2_policy"
        input_reasons = ";".join(dec_reasons + ["chained_" + r for r in chain_reasons])
    opp_status = ""
    if not opportunity.empty and opportunity["split"].eq("robustness").any():
        opp_status = str(opportunity.loc[opportunity["split"].eq("robustness"), "stage1_defense_opportunity_cost_status"].iloc[0])
    return pd.DataFrame(
        [
            {
                "decision_state": state,
                "input_gate_status": "pass" if input_ok else "fail",
                "stage1_anchor_reconstruction_status": "pass" if anchor_ok else "fail",
                "stage2_decoupled_signal_status": dec_status,
                "stage2_chained_operating_status": chain_status,
                "stage1_anchor_rule_id": anchor.get("stage1_anchor_rule_id", ""),
                "stage1_anchor_feature": anchor.get("stage1_anchor_feature", ""),
                "stage1_anchor_orientation": anchor.get("stage1_anchor_orientation", ""),
                "stage1_anchor_X": anchor.get("stage1_anchor_X", np.nan),
                "selected_decoupled_candidate_id": dec_sel.iloc[0].get("candidate_id", "") if not dec_sel.empty else "",
                "selected_decoupled_candidate_family": dec_sel.iloc[0].get("candidate_family", "") if not dec_sel.empty else "",
                "selected_decoupled_X": dec_sel.iloc[0].get("stage2_budget_X", np.nan) if not dec_sel.empty else np.nan,
                "selected_chained_candidate_id": chain_sel.iloc[0].get("candidate_id", "") if not chain_sel.empty else "",
                "selected_chained_candidate_family": chain_sel.iloc[0].get("candidate_family", "") if not chain_sel.empty else "",
                "selected_chained_X": chain_sel.iloc[0].get("stage2_budget_X", np.nan) if not chain_sel.empty else np.nan,
                "selected_chained_deployable_at_stage_2_decision_time": True if not chain_sel.empty else False,
                "stage1_defense_opportunity_cost_status": opp_status,
                "gate_failure_reasons": input_reasons,
                "next_allowed_requirement": next_allowed,
                "recommended_internal_followup": followup,
            }
        ]
    )


def selected_readout_row(readout: pd.DataFrame, denominator_type: str, candidate_id: Any, x_value: Any, split: str) -> pd.Series:
    required = {"denominator_type", "candidate_id", "stage2_budget_X", "split"}
    if readout.empty or not required.issubset(readout.columns):
        return pd.Series(dtype=object)
    mask = (
        readout["denominator_type"].eq(denominator_type)
        & readout["candidate_id"].eq(str(candidate_id))
        & readout["split"].eq(split)
    )
    if pd.notna(x_value):
        mask &= readout["stage2_budget_X"].eq(float(x_value))
    matched = readout.loc[mask]
    return matched.iloc[0] if not matched.empty else pd.Series(dtype=object)


def report_rate_summary(row: pd.Series) -> str:
    return (
        f"selected_n={fmt(row.get('selected_n', np.nan))}, "
        f"continuation_rate={fmt(row.get('selected_continuation_rate', np.nan))}, "
        f"random_p50={fmt(row.get('random_p50', np.nan))}, "
        f"delta_vs_random_p50={fmt(row.get('delta_vs_random_p50', np.nan))}, "
        f"CI=[{fmt(row.get('delta_vs_random_p50_ci95_low', np.nan))}, {fmt(row.get('delta_vs_random_p50_ci95_high', np.nan))}], "
        f"status={row.get('readout_status', '')}"
    )


def report_pair_summary(row: pd.Series, delta_col: str, low_col: str, high_col: str) -> str:
    return f"{delta_col}={fmt(row.get(delta_col, np.nan))}, CI=[{fmt(row.get(low_col, np.nan))}, {fmt(row.get(high_col, np.nan))}]"


def build_report(decision: pd.DataFrame, readout: pd.DataFrame, opportunity: pd.DataFrame) -> str:
    d = decision.iloc[0]
    dec_row = selected_readout_row(
        readout,
        "ground_truth_no_fast_fail_survivor",
        d.get("selected_decoupled_candidate_id", ""),
        d.get("selected_decoupled_X", np.nan),
        "robustness",
    )
    chain_row = selected_readout_row(
        readout,
        "stage1_anchor_chained_survivor",
        d.get("selected_chained_candidate_id", ""),
        d.get("selected_chained_X", np.nan),
        "robustness",
    )
    dec_validation = selected_readout_row(
        readout,
        "ground_truth_no_fast_fail_survivor",
        d.get("selected_decoupled_candidate_id", ""),
        d.get("selected_decoupled_X", np.nan),
        "validation",
    )
    chain_validation = selected_readout_row(
        readout,
        "stage1_anchor_chained_survivor",
        d.get("selected_chained_candidate_id", ""),
        d.get("selected_chained_X", np.nan),
        "validation",
    )
    opp = opportunity.loc[opportunity["split"].eq("robustness")].iloc[0] if not opportunity.empty and opportunity["split"].eq("robustness").any() else pd.Series(dtype=object)
    validation_warning = f"decoupled: {report_rate_summary(dec_validation)}; chained: {report_rate_summary(chain_validation)}"
    single_feature_result = report_pair_summary(
        chain_row,
        "delta_vs_single_feature",
        "delta_vs_single_feature_ci95_low",
        "delta_vs_single_feature_ci95_high",
    )
    complex_pair_result = report_pair_summary(
        chain_row,
        "delta_vs_complex_model",
        "delta_vs_complex_model_ci95_low",
        "delta_vs_complex_model_ci95_high",
    )
    return f"""
# 12A7c Direction E stage-2 decoupling and chained readouts report

## Decision

| field | value |
|---|---:|
| final decision | `{d['decision_state']}` |
| stage2_decoupled_signal_status | `{d['stage2_decoupled_signal_status']}` |
| stage2_chained_operating_status | `{d['stage2_chained_operating_status']}` |
| stage1 anchor | `{d['stage1_anchor_feature']} {d['stage1_anchor_orientation']}, X={fmt(d['stage1_anchor_X'])}` |
| decoupled selected candidate | `{d['selected_decoupled_candidate_id']}` |
| decoupled robustness selected_n | {fmt(dec_row.get('selected_n', np.nan))} |
| decoupled robustness continuation_rate | {fmt(dec_row.get('selected_continuation_rate', np.nan))} |
| decoupled robustness random_p50 | {fmt(dec_row.get('random_p50', np.nan))} |
| decoupled delta_vs_random_p50 CI low | {fmt(dec_row.get('delta_vs_random_p50_ci95_low', np.nan))} |
| chained selected candidate | `{d['selected_chained_candidate_id']}` |
| chained robustness selected_n | {fmt(chain_row.get('selected_n', np.nan))} |
| chained robustness continuation_rate | {fmt(chain_row.get('selected_continuation_rate', np.nan))} |
| chained robustness random_p50 | {fmt(chain_row.get('random_p50', np.nan))} |
| chained delta_vs_random_p50 CI low | {fmt(chain_row.get('delta_vs_random_p50_ci95_low', np.nan))} |
| chained delta_vs_random_p50 CI high | {fmt(chain_row.get('delta_vs_random_p50_ci95_high', np.nan))} |
| single-feature challenger result | {single_feature_result} |
| complex-vs-single-feature paired result | {complex_pair_result} |
| validation stress warning | {validation_warning} |
| opportunity-cost status | `{d['stage1_defense_opportunity_cost_status']}` |
| recommended next step | `{d['recommended_internal_followup']}` |

Ground-truth survivor decoupled readout is diagnostic-only and not deployable.
Chained readout is deployable at stage-2 decision time only after the fixed stage-1 anchor has selected the row and no-fast-fail survival is observable; it is not a t0-entry deployable strategy.
No stage-2 feature, orientation, X, or model capacity was chosen using validation or robustness.
The conclusion applies only to C0 risk_on events and the current continuation target.

## Findings

1. Decoupled robustness tests whether continuation signal exists among true no-fast-fail survivors, independent of the stage-1 anchor.
2. Chained robustness tests whether that signal still survives after the fixed 12A7b simple-backbone keep rule.
3. Opportunity cost: robustness chained survivor share is {fmt(opp.get('chained_survivor_share_of_ground_truth_survivors', np.nan))}, and continuation rate delta chained vs ground-truth survivors is {fmt(opp.get('continuation_rate_delta_chained_vs_ground_truth', np.nan))}.
4. Complex-vs-single-feature comparison is read through paired matched selected-count cells; positive `delta_vs_single_feature` supports complex stage-2 only when its CI lower bound is positive.
5. Next research step is `{d['recommended_internal_followup']}` under decision `{d['decision_state']}`, so calibration, policy replay, or label-denominator revision is routed by the frozen gates rather than by post-hoc interpretation.

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


def write_blocked_outputs(
    paths: dict[str, Path],
    input_audit: pd.DataFrame,
    input_reasons: str,
    config_path: Path,
    requirement_path: Path,
    config: dict[str, Any],
) -> pd.DataFrame:
    readout_columns = [
        "denominator_type",
        "split",
        "candidate_id",
        "candidate_family",
        "stage2_budget_X",
        "selected_n",
        "denominator_positive_n",
        "selected_continuation_rate",
        "random_p50",
        "delta_vs_random_p50",
        "delta_vs_random_p50_ci95_low",
        "delta_vs_random_p50_ci95_high",
        "rank_not_evaluable_rate",
        "budget_abs_delta_rank_evaluable_vs_X",
        "delta_vs_single_feature",
        "delta_vs_single_feature_ci95_low",
        "delta_vs_single_feature_ci95_high",
        "delta_vs_complex_model",
        "delta_vs_complex_model_ci95_low",
        "delta_vs_complex_model_ci95_high",
        "readout_status",
    ]
    empty_readout = pd.DataFrame(columns=readout_columns)
    empty_opportunity = pd.DataFrame(
        columns=[
            "split",
            "stage1_defense_opportunity_cost_status",
            "chained_survivor_share_of_ground_truth_survivors",
            "continuation_rate_delta_chained_vs_ground_truth",
        ]
    )
    decision = decision_row(
        False,
        input_reasons,
        False,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        empty_readout,
        empty_opportunity,
        config,
    )
    frames = {
        "input_artifact_audit": input_audit,
        "scope_universe_audit": pd.DataFrame(columns=["split", "primary_scope_n", "ground_truth_survivor_n", "stage1_anchor_chained_survivor_n"]),
        "stage1_anchor_rule_card": pd.DataFrame(
            [
                {
                    "stage1_anchor_reconstruction_status": "fail",
                    "stage1_anchor_reconstruction_reason": input_reasons,
                    "stage1_anchor_rule_id": "",
                    "publishable_count_reconciliation_status": "not_evaluated",
                }
            ]
        ),
        "stage2_candidate_card": pd.DataFrame(columns=["candidate_id", "candidate_family", "candidate_status"]),
        "stage2_train_selection": pd.DataFrame(columns=["denominator_type", "selection_status", "candidate_id", "tie_break_path"]),
        "stage2_ground_truth_survivor_readout": empty_readout.copy(),
        "stage2_chained_trailing_rank_readout": empty_readout.copy(),
        "stage2_random_same_budget_audit": pd.DataFrame(columns=["candidate_id", "requested_selected_n", "sampled_random_n", "retention_rank_rule"]),
        "stage2_single_feature_challenger": pd.DataFrame(columns=["single_feature_matched_rate", "delta_vs_single_feature_ci95_low"]),
        "stage2_complex_model_matched_comparator": pd.DataFrame(columns=["complex_model_matched_rate", "delta_vs_complex_model_ci95_low"]),
        "stage2_budget_drift_audit": pd.DataFrame(columns=["candidate_id", "budget_abs_delta_rank_evaluable_vs_X", "rank_not_evaluable_rate"]),
        "stage2_opportunity_cost_audit": empty_opportunity,
        "stage2_stability_slice_audit": pd.DataFrame(columns=["slice_type", "direction_status", "random_p50"]),
        "direction_e_decision": decision,
        "score_matrix": pd.DataFrame(columns=["meta_event_id", "split", "stage1_anchor_selected_flag", TARGET_COL, COMPLEX_SCORE_COL]),
        "bootstrap_replicates": pd.DataFrame(columns=["comparison_id", "split", "replicate_id", "delta"]),
        "random_stage2_selected": pd.DataFrame(columns=["seed", "meta_event_id", "retention_rank_rule"]),
    }
    for key, frame_out in frames.items():
        write_df(paths[key], frame_out)
    write_text(paths["report"], build_report(decision, empty_readout, empty_opportunity))
    frames["report"] = pd.DataFrame([{"path": str(paths["report"])}])
    manifest = build_manifest(paths, frames, decision, config_path, requirement_path, config)
    write_json(paths["manifest"], manifest)
    return decision


def run_pipeline(config_path: Path, mode: str = "full") -> int:
    config = load_yaml(config_path)
    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    paths = output_paths()
    input_audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], input_audit)
    a7b_decision = read_table(resolved["a7b_direction_c_decision"]) if resolved["a7b_direction_c_decision"].exists() else pd.DataFrame()
    input_ok, input_reasons = input_gate_pass(input_audit, a7b_decision)
    if mode == "check-inputs":
        if not input_ok:
            raise RuntimeError(f"12A7c input check failed: {input_reasons}")
        print(f"{RUN_ID}: input audit ok ({len(input_audit)} artifacts)")
        return 0
    if not input_ok:
        decision = write_blocked_outputs(paths, input_audit, input_reasons, config_path, resolved["requirement"], config)
        print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
        return 0

    policy = history_policy(config)
    primary = load_primary_universe(resolved)
    raw_universe = read_table(resolved["two_stage_event_universe"])
    train_sel_12a7b = read_table(resolved["a7b_simple_backbone_train_selection"])
    readout_12a7b = read_table(resolved["a7b_simple_backbone_operating_point_readout"])
    anchor = resolve_anchor(a7b_decision, train_sel_12a7b, readout_12a7b)
    anchor_ranked, anchor_card, anchor_ok, anchor_reason = reconstruct_stage1_anchor(
        primary, anchor, readout_12a7b, resolved["a7b_simple_backbone_score_matrix"], policy, config
    )
    primary = primary.merge(
        anchor_ranked[["meta_event_id", "rank_percentile", "rank_status", "stage1_anchor_selected_flag"]].rename(
            columns={"rank_percentile": "stage1_anchor_rank_percentile", "rank_status": "stage1_anchor_rank_status"}
        ),
        on="meta_event_id",
        how="left",
    )
    primary["stage1_anchor_selected_flag"] = bool_series(primary["stage1_anchor_selected_flag"].fillna(False))
    decoupled = stage2_survivor_frame(primary)
    chained = decoupled.loc[bool_series(decoupled["stage1_anchor_selected_flag"])].copy()
    scope_audit = scope_universe_audit(raw_universe, primary, decoupled, chained)
    feature_dict = read_table(resolved["two_stage_feature_dictionary"])
    pit = read_table(resolved["two_stage_feature_pit_audit"])
    candidates = candidate_card(config, feature_dict, pit, primary)
    available = candidates.loc[candidates["candidate_status"].eq("candidate_available")].copy()
    random_labels, random_status = prepare_random_labels(resolved)
    if random_status != "pass":
        raise RuntimeError(f"12A7c random path labels failed: {random_status}")
    chained_random_survivor, stage1_random_audit = build_chained_random_survivors(random_labels, primary, config)

    selections: dict[tuple[str, str, float], pd.DataFrame] = {}
    readouts = []
    random_audits = []
    random_selected_parts = []
    bootstrap_parts = []
    for denominator_type, denominator in (
        ("ground_truth_no_fast_fail_survivor", decoupled),
        ("stage1_anchor_chained_survivor", chained),
    ):
        for _, cand in available.iterrows():
            x_values = [float(v) for v in config["stage2_X_grid"]]
            for x in x_values:
                selection = make_selection(
                    denominator_type,
                    denominator,
                    str(cand["candidate_id"]),
                    str(cand["candidate_family"]),
                    str(cand["feature_name"]),
                    str(cand["orientation"]),
                    x,
                    policy,
                    config,
                    anchor,
                )
                selections[(denominator_type, str(cand["candidate_id"]), float(x))] = selection
                readout = readout_for_selection(selection)
                if denominator_type == "ground_truth_no_fast_fail_survivor":
                    rand_sel, rand_audit, quant, replay_status = random_replay_decoupled(selection, random_labels, config)
                else:
                    rand_sel, rand_audit, quant, replay_status = random_replay_chained(selection, chained_random_survivor, stage1_random_audit, config)
                for col, value in {
                    "denominator_type": denominator_type,
                    "candidate_id": str(cand["candidate_id"]),
                    "candidate_family": str(cand["candidate_family"]),
                    "stage2_budget_X": float(x),
                }.items():
                    rand_audit.insert(0, col, value)
                    if not rand_sel.empty:
                        rand_sel[col] = value
                random_audits.append(rand_audit)
                if not rand_sel.empty:
                    random_selected_parts.append(rand_sel)
                readout = attach_random(readout, quant)
                readout, reps = update_random_ci(readout, selection, rand_sel, config, f"{denominator_type}:{cand['candidate_id']}:{x}")
                if not reps.empty:
                    bootstrap_parts.append(reps)
                readout["readout_status"] = "ok" if replay_status == "pass" else "random_replay_failed"
                readouts.append(readout)
    all_readout = pd.concat(readouts, ignore_index=True)

    train_rows = []
    for denominator_type in ("ground_truth_no_fast_fail_survivor", "stage1_anchor_chained_survivor"):
        train_rows.append(train_selection(all_readout, denominator_type))
        train_rows.append(train_selection(all_readout, denominator_type, "single_feature_stage2").assign(selection_role="single_feature_challenger"))
    train_selection_df = pd.concat(train_rows, ignore_index=True)

    single_comp_rows = []
    complex_comp_rows = []
    for denominator_type in ("ground_truth_no_fast_fail_survivor", "stage1_anchor_chained_survivor"):
        single_train = train_selection_df.loc[
            train_selection_df["denominator_type"].eq(denominator_type)
            & train_selection_df.get("selection_role", pd.Series("", index=train_selection_df.index)).eq("single_feature_challenger")
        ]
        if single_train.empty or str(single_train.iloc[0].get("selection_status", "")) != "selected_train_frozen":
            continue
        single_feature_id = str(single_train.iloc[0]["candidate_id"])
        for x in [float(v) for v in config["stage2_X_grid"]]:
            single_selection = selections[(denominator_type, single_feature_id, x)]
            complex_selection = selections[(denominator_type, "complex_stage2_score", x)]
            comp_single, _base1, reps1 = matched_comparator(
                complex_selection,
                single_selection,
                "single_feature_matched_rate",
                "delta_vs_single_feature",
                "delta_vs_single_feature_ci95_low",
                "delta_vs_single_feature_ci95_high",
                f"{denominator_type}:complex_minus_single:{x}",
                config,
            )
            comp_complex, _base2, reps2 = matched_comparator(
                single_selection,
                complex_selection,
                "complex_model_matched_rate",
                "delta_vs_complex_model",
                "delta_vs_complex_model_ci95_low",
                "delta_vs_complex_model_ci95_high",
                f"{denominator_type}:single_minus_complex:{x}",
                config,
            )
            single_comp_rows.append(comp_single)
            complex_comp_rows.append(comp_complex)
            if not reps1.empty:
                bootstrap_parts.append(reps1)
            if not reps2.empty:
                bootstrap_parts.append(reps2)
    single_challenger = pd.concat(single_comp_rows, ignore_index=True) if single_comp_rows else pd.DataFrame()
    complex_comparator = pd.concat(complex_comp_rows, ignore_index=True) if complex_comp_rows else pd.DataFrame()
    if not single_challenger.empty:
        all_readout = merge_comparator(
            all_readout,
            single_challenger,
            ["single_feature_matched_rate", "delta_vs_single_feature", "delta_vs_single_feature_ci95_low", "delta_vs_single_feature_ci95_high"],
        )
    if not complex_comparator.empty:
        all_readout = merge_comparator(
            all_readout,
            complex_comparator,
            ["complex_model_matched_rate", "delta_vs_complex_model", "delta_vs_complex_model_ci95_low", "delta_vs_complex_model_ci95_high"],
        )

    dec_sel = train_selection_df.loc[
        train_selection_df["denominator_type"].eq("ground_truth_no_fast_fail_survivor")
        & train_selection_df.get("candidate_family_filter", pd.Series("", index=train_selection_df.index)).eq("all")
    ]
    chain_sel = train_selection_df.loc[
        train_selection_df["denominator_type"].eq("stage1_anchor_chained_survivor")
        & train_selection_df.get("candidate_family_filter", pd.Series("", index=train_selection_df.index)).eq("all")
    ]
    opportunity = opportunity_cost(primary, decoupled, chained)
    chosen_chained = pd.DataFrame()
    if not chain_sel.empty and str(chain_sel.iloc[0].get("selection_status", "")) == "selected_train_frozen":
        chosen_chained = selections[
            (
                "stage1_anchor_chained_survivor",
                str(chain_sel.iloc[0]["candidate_id"]),
                float(chain_sel.iloc[0]["stage2_budget_X"]),
            )
        ]
    stability = stability_slices(chosen_chained, config)
    decision = decision_row(input_ok, input_reasons + (";" + anchor_reason if anchor_reason else ""), anchor_ok, anchor_card, dec_sel, chain_sel, all_readout, opportunity, config)

    budget_drift = all_readout[
        [
            "denominator_type",
            "split",
            "candidate_id",
            "candidate_family",
            "stage2_budget_X",
            "selected_budget_total",
            "selected_budget_rank_evaluable",
            "budget_abs_delta_total_vs_X",
            "budget_abs_delta_rank_evaluable_vs_X",
            "rank_not_evaluable_rate",
        ]
    ].copy()
    ground_truth_readout = all_readout.loc[all_readout["denominator_type"].eq("ground_truth_no_fast_fail_survivor")].copy()
    chained_readout = all_readout.loc[all_readout["denominator_type"].eq("stage1_anchor_chained_survivor")].copy()
    random_audit = pd.concat(random_audits, ignore_index=True) if random_audits else pd.DataFrame()
    random_selected = pd.concat(random_selected_parts, ignore_index=True) if random_selected_parts else pd.DataFrame()
    bootstrap = pd.concat(bootstrap_parts, ignore_index=True) if bootstrap_parts else pd.DataFrame(columns=["comparison_id", "split", "replicate_id", "delta"])
    score_matrix = primary.copy()

    frames = {
        "input_artifact_audit": input_audit,
        "scope_universe_audit": scope_audit,
        "stage1_anchor_rule_card": anchor_card,
        "stage2_candidate_card": candidates,
        "stage2_train_selection": train_selection_df,
        "stage2_ground_truth_survivor_readout": ground_truth_readout,
        "stage2_chained_trailing_rank_readout": chained_readout,
        "stage2_random_same_budget_audit": random_audit,
        "stage2_single_feature_challenger": single_challenger,
        "stage2_complex_model_matched_comparator": complex_comparator,
        "stage2_budget_drift_audit": budget_drift,
        "stage2_opportunity_cost_audit": opportunity,
        "stage2_stability_slice_audit": stability,
        "direction_e_decision": decision,
        "score_matrix": score_matrix,
        "bootstrap_replicates": bootstrap,
        "random_stage2_selected": random_selected,
    }
    for key, frame_out in frames.items():
        write_df(paths[key], frame_out)
    write_text(paths["report"], build_report(decision, all_readout, opportunity))
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

#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
TOPIC_SRC_DIR = TOPIC_ROOT / "src"

if str(TOPIC_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TOPIC_SRC_DIR))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


RUN_ID = "12A7_direction_a_trailing_rank_operating_point_audit"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a7_direction_a_trailing_rank_operating_point_audit.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
PRIMARY_STAGE1_TARGET = "stage_1_fast_fail_target"
PRIMARY_STAGE2_TARGET = "stage_2_continuation_target"
PRIMARY_STAGE1_SCORE = "stage1_fast_fail_score"
PRIMARY_STAGE2_SCORE = "stage2_continuation_score"


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "two_stage_input_artifact_audit": ("artifact_id", "read_status", "schema_status", "sha256"),
    "two_stage_event_universe": ("meta_event_id", "instrument", "event_t0_date", "event_t0_pos", "split", "board_bucket"),
    "two_stage_event_targets": (
        "meta_event_id",
        "instrument",
        "split",
        "stage_1_evaluable",
        PRIMARY_STAGE1_TARGET,
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        PRIMARY_STAGE2_TARGET,
        "stage_2_evaluable",
    ),
    "two_stage_feature_dictionary": ("feature_name", "allowed_for_stage_1", "allowed_for_stage_2", "pit_status"),
    "two_stage_feature_pit_audit": ("feature_name", "pit_status", "coverage_rate"),
    "stage_1_model_card": ("stage", "model_id", "feature_list_hash", "hyperparameter_json"),
    "stage_2_model_card": ("stage", "model_id", "feature_list_hash", "hyperparameter_json"),
    "stage_1_rejector_readout": ("model_id", "split", "score_threshold", "stage1_keep_n", "stage1_keep_fast_fail_rate"),
    "stage_2_continuation_readout": ("model_id", "split", "score_threshold", "stage2_continue_n", "stage2_continue_continuation_rate"),
    "stage_1_single_feature_frontier": ("feature_name", "orientation_selected_on_train", "split"),
    "stage_2_single_feature_frontier": ("feature_name", "orientation_selected_on_train", "split"),
    "stage_1_score_bucket_readout": ("stage", "model_id", "split", "bucket_id", "target_rate"),
    "stage_2_score_bucket_readout": ("stage", "model_id", "split", "bucket_id", "target_rate"),
    "stage_1_random_same_budget_audit": ("stage", "seed", "split", "random_selected_n", "random_rate"),
    "stage_2_random_same_budget_audit": ("stage", "seed", "split", "random_selected_n", "random_rate"),
    "stage_threshold_health": ("stage", "split", "model_id", "score_threshold", "actual_budget"),
    "two_stage_decision": ("decision_state", "input_gate_status", "stage_1_model_id", "stage_2_model_id"),
    "split_time_boundary_audit": ("eval_split", "split_time_boundary_gate_pass"),
    "realized_path_feature_redundancy_audit": ("feature_name", "allowed_for_stage_2_after_audit"),
    "two_stage_feature_matrix": ("meta_event_id", "instrument", "event_t0_date", "event_t0_pos", "split", "board_bucket", "path_key"),
    "stage2_path_cache": (
        "path_key",
        "instrument",
        "entry_pos",
        "entry_price",
        "stage_2_decision_pos",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
    ),
    "matched_random_sampled_entries": (
        "seed",
        "path_key",
        "split",
        "board_bucket",
        "calendar_month",
        "random_trade_open_date",
        "instrument",
        "entry_pos",
        "entry_price",
        "sample_weight",
    ),
    "entry_forward_path_cache": ("path_key", "instrument", "entry_pos", "entry_price", "entry_blocked", "horizon_complete_20d", "time_to_lower_minus_10_20d"),
    "manifest_12a6c": (),
    "manifest_12a6b": (),
    "requirement": (),
}


@dataclass(frozen=True)
class HistoryPolicy:
    history_policy_id: str
    history_window_mode: str
    trailing_history_window_sessions: int | None
    diagnostic_only_flag: bool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A7 PIT trailing-rank operating point audit.")
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
        "score_reproduction_audit": TABLE_DIR / "score_reproduction_audit.csv",
        "random_path_label_audit": TABLE_DIR / "random_path_label_audit.csv",
        "score_quality": TABLE_DIR / "trailing_rank_score_quality_metrics.csv",
        "operating_readout": TABLE_DIR / "trailing_rank_operating_point_readout.csv",
        "budget_drift": TABLE_DIR / "trailing_rank_budget_drift_audit.csv",
        "random_audit": TABLE_DIR / "trailing_rank_random_same_budget_audit.csv",
        "single_feature": TABLE_DIR / "trailing_rank_single_feature_challenger.csv",
        "decile_lift": TABLE_DIR / "trailing_rank_decile_lift_readout.csv",
        "budget_curve": TABLE_DIR / "trailing_rank_budget_curve_readout.csv",
        "lookahead_upper_bar": TABLE_DIR / "diagnostic_lookahead_rank_upper_bar.csv",
        "decision": TABLE_DIR / "trailing_rank_decision.csv",
        "split_time_boundary_audit": TABLE_DIR / "split_time_boundary_audit.csv",
        "score_matrix": LOCAL_CACHE_DIR / "trailing_rank_score_matrix.parquet",
        "report": REPORT_DIR / "trailing_rank_operating_point_validation_report.md",
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
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t", "pass", "ok"}


def bool_series(values: pd.Series) -> pd.Series:
    return values.map(boolish).astype(bool)


def numeric(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


def date_text(value: Any) -> str:
    if isinstance(value, str):
        text = value[:10]
        if len(text) == 10 and text[4] == "-" and text[7] == "-" and text.replace("-", "").isdigit():
            return text
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")


def month_text(value: Any) -> str:
    text = date_text(value)
    return text[:7] if text else ""


def year_text(value: Any) -> str:
    text = date_text(value)
    return text[:4] if text else ""


def safe_rate(num: int | float, den: int | float) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "all":
        return frame.copy()
    return frame.loc[frame["split"].astype(str).eq(split)].copy()


def weighted_rate(frame: pd.DataFrame, target_col: str, weight_col: str = "sample_weight") -> float:
    if frame.empty:
        return np.nan
    weights = pd.to_numeric(frame[weight_col], errors="coerce").fillna(1.0) if weight_col in frame else pd.Series(1.0, index=frame.index)
    target = bool_series(frame[target_col]).astype(float)
    den = float(weights.sum())
    return float((target * weights).sum() / den) if den else np.nan


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    optional = {"frozen_row_level_scores"}
    for artifact_id, required_cols in EXPECTED_INPUT_COLUMNS.items():
        raw = config.get("paths", {}).get(artifact_id, artifact_id)
        path = topic_path(raw)
        exists = path.is_file()
        read_status = "pass" if exists else ("optional_missing" if artifact_id in optional else "missing")
        schema_status = "pass" if exists and not required_cols else ("optional_missing" if artifact_id in optional and not exists else "not_checked")
        row_count = np.nan
        if exists and required_cols:
            try:
                frame = read_table(path, nrows=5) if "".join(path.suffixes).endswith((".csv", ".csv.gz")) else read_table(path)
                missing = set(required_cols) - set(frame.columns)
                schema_status = "pass" if not missing else "missing_columns:" + ";".join(sorted(missing))
                row_count = len(frame)
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        rows.append(
            {
                "artifact_id": artifact_id,
                "path": str(path),
                "read_status": read_status,
                "schema_status": schema_status,
                "sha256": path_sha(path),
                "row_count_sample": row_count,
            }
        )
    return pd.DataFrame(rows)


def input_gate_pass(audit: pd.DataFrame, decision_12a6c: pd.DataFrame) -> tuple[bool, str]:
    reasons: list[str] = []
    required = audit.loc[~audit["read_status"].astype(str).eq("optional_missing")].copy()
    if not required["read_status"].astype(str).eq("pass").all():
        reasons.append("read_status:" + ",".join(required.loc[~required["read_status"].astype(str).eq("pass"), "artifact_id"].astype(str)))
    if not required["schema_status"].astype(str).eq("pass").all():
        reasons.append("schema_status:" + ",".join(required.loc[~required["schema_status"].astype(str).eq("pass"), "artifact_id"].astype(str)))
    allowed_states = {
        "12A6c_stage1_partial",
        "12A6c_stage1_supported_stage2_partial",
        "12A6c_two_stage_supported",
    }
    if decision_12a6c.empty:
        reasons.append("12A6c_decision_empty")
    else:
        row = decision_12a6c.iloc[0]
        if str(row.get("input_gate_status", "")) != "pass":
            reasons.append("12A6c_input_gate_not_pass")
        if str(row.get("decision_state", "")) not in allowed_states:
            reasons.append(f"12A6c_decision_not_allowed:{row.get('decision_state', '')}")
        if str(row.get("stage_1_model_id", "")) != "logistic_regression_l2":
            reasons.append("12A6c_stage1_model_not_logistic_regression_l2")
        if str(row.get("stage_2_model_id", "")) != "logistic_regression_l2":
            reasons.append("12A6c_stage2_model_not_logistic_regression_l2")
    return not reasons, ";".join(reasons)


def history_policies(config: dict[str, Any]) -> list[HistoryPolicy]:
    raw = [config["history_policies"]["primary"]] + list(config["history_policies"].get("diagnostics", []))
    return [
        HistoryPolicy(
            history_policy_id=str(item["history_policy_id"]),
            history_window_mode=str(item["history_window_mode"]),
            trailing_history_window_sessions=int(item["trailing_history_window_sessions"]) if item.get("trailing_history_window_sessions") is not None else None,
            diagnostic_only_flag=bool(item.get("diagnostic_only_flag", False)),
        )
        for item in raw
    ]


def model_card_row(card: pd.DataFrame, model_id: str) -> pd.Series:
    match = card.loc[card["model_id"].astype(str).eq(model_id)]
    return match.iloc[0] if not match.empty else pd.Series(dtype=object)


def feature_lists(feature_dict: pd.DataFrame, feature_matrix: pd.DataFrame, redundancy: pd.DataFrame, stage1_card: pd.DataFrame, stage2_card: pd.DataFrame, config: dict[str, Any]) -> tuple[list[str], list[str]]:
    s1_model = config["models"]["primary_stage_1_model_id"]
    s2_model = config["models"]["primary_stage_2_model_id"]
    s1_expected = str(model_card_row(stage1_card, s1_model).get("feature_list_hash", ""))
    s2_expected = str(model_card_row(stage2_card, s2_model).get("feature_list_hash", ""))
    numeric_cols = {col for col in feature_matrix.columns if pd.api.types.is_numeric_dtype(feature_matrix[col])}
    s1 = [
        str(row.feature_name)
        for row in feature_dict.itertuples(index=False)
        if boolish(getattr(row, "allowed_for_stage_1", False)) and str(row.feature_name) in numeric_cols
    ]
    s2 = [
        str(row.feature_name)
        for row in feature_dict.itertuples(index=False)
        if boolish(getattr(row, "allowed_for_stage_2", False)) and str(row.feature_name) in numeric_cols
    ]
    if stable_hash(s1) != s1_expected:
        raise RuntimeError(f"stage1 feature hash mismatch expected={s1_expected} actual={stable_hash(s1)}")
    if stable_hash(s2) != s2_expected:
        if not redundancy.empty and {"feature_name", "allowed_for_stage_2_after_audit"}.issubset(redundancy.columns):
            allowed_realized = set(redundancy.loc[bool_series(redundancy["allowed_for_stage_2_after_audit"]), "feature_name"].astype(str))
            candidate = [name for name in s2 if not name.startswith("realized_") or name in allowed_realized]
            if stable_hash(candidate) == s2_expected:
                s2 = candidate
        if stable_hash(s2) != s2_expected:
            for drop in s2:
                candidate = [name for name in s2 if name != drop]
                if stable_hash(candidate) == s2_expected:
                    s2 = candidate
                    break
    if stable_hash(s2) != s2_expected:
        raise RuntimeError(f"stage2 feature hash mismatch expected={s2_expected} actual={stable_hash(s2)}")
    return s1, s2


def impute_and_score_logistic(
    train_source: pd.DataFrame,
    score_frame: pd.DataFrame,
    feature_cols: list[str],
    target_col: str,
    score_col: str,
    *,
    max_iter: int,
) -> tuple[pd.DataFrame, dict[str, float], str]:
    train = train_source.loc[train_source["split"].astype(str).eq("train")].copy()
    medians: dict[str, float] = {}
    train_x = train.copy()
    score_x = score_frame.copy()
    for col in feature_cols:
        train_x[col] = pd.to_numeric(train_x[col], errors="coerce")
        score_x[col] = pd.to_numeric(score_x[col], errors="coerce")
        median = float(train_x[col].median()) if train_x[col].notna().any() else 0.0
        if not np.isfinite(median):
            median = 0.0
        medians[col] = median
        train_x[col] = train_x[col].fillna(median)
        score_x[col] = score_x[col].fillna(median)
    out = score_frame.copy()
    y = bool_series(train_x[target_col]).astype(int)
    try:
        if len(train_x) == 0 or y.nunique() < 2:
            raise ValueError("insufficient_train_labels")
        model = LogisticRegression(max_iter=max_iter, penalty="l2", solver="liblinear")
        model.fit(train_x[feature_cols].to_numpy(dtype=float), y)
        out[score_col] = model.predict_proba(score_x[feature_cols].to_numpy(dtype=float))[:, 1]
        status = "fit"
    except Exception as exc:
        out[score_col] = np.nan
        status = f"fit_error:{type(exc).__name__}"
    return out, medians, status


def assign_fixed_budget_flags(scored: pd.DataFrame, score_col: str, flag_col: str, budget: float, lower_is_better: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = scored.copy()
    out[flag_col] = False
    rows = []
    tie_cols = [col for col in ("instrument", "event_t0_date", "meta_event_id", "path_key") if col in out.columns]
    train = out.loc[out["split"].astype(str).eq("train")].copy()
    train["_score_sort"] = pd.to_numeric(train[score_col], errors="coerce").fillna(np.inf if lower_is_better else -np.inf)
    train = train.sort_values(["_score_sort"] + tie_cols, ascending=[lower_is_better] + [True] * len(tie_cols), kind="stable")
    n_train = min(max(int(round(budget * len(train))), 0), len(train))
    if n_train <= 0:
        threshold = -np.inf if lower_is_better else np.inf
        tie_fraction = 0.0
    elif n_train >= len(train):
        threshold = np.inf if lower_is_better else -np.inf
        tie_fraction = 1.0
    else:
        threshold = float(train.iloc[n_train - 1]["_score_sort"])
        better_train_n = int((train["_score_sort"] < threshold).sum()) if lower_is_better else int((train["_score_sort"] > threshold).sum())
        tie_train_n = int((train["_score_sort"] == threshold).sum())
        tie_fraction = safe_rate(max(0, n_train - better_train_n), tie_train_n)
        tie_fraction = 0.0 if pd.isna(tie_fraction) else float(tie_fraction)
    for split in SPLITS:
        frame = out if split == "all" else out.loc[out["split"].astype(str).eq(split)]
        frame = frame.copy()
        frame["_score_sort"] = pd.to_numeric(frame[score_col], errors="coerce").fillna(np.inf if lower_is_better else -np.inf)
        if not np.isfinite(threshold):
            if (lower_is_better and threshold == np.inf) or ((not lower_is_better) and threshold == -np.inf):
                selected_idx = frame.index
            else:
                selected_idx = frame.head(0).index
        else:
            better = frame["_score_sort"] < threshold if lower_is_better else frame["_score_sort"] > threshold
            selected_idx = frame.loc[better].index
            ties = frame.loc[frame["_score_sort"].eq(threshold)].copy()
            if not ties.empty and tie_fraction > 0:
                ties = ties.sort_values(tie_cols, ascending=[True] * len(tie_cols), kind="stable") if tie_cols else ties.sort_index(kind="stable")
                selected_idx = selected_idx.append(ties.index[: int(round(tie_fraction * len(ties)))])
        if split != "all":
            out.loc[selected_idx, flag_col] = True
        rows.append(
            {
                "split": split,
                "score_threshold": threshold,
                "selected_n": int(len(selected_idx)),
                "target_rate": weighted_rate(out.loc[selected_idx].assign(sample_weight=1.0), PRIMARY_STAGE1_TARGET if "stage1" in flag_col else PRIMARY_STAGE2_TARGET),
            }
        )
    return out, pd.DataFrame(rows)


def build_score_source(
    resolved: dict[str, Path],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    feature_matrix = read_table(resolved["two_stage_feature_matrix"])
    targets = read_table(resolved["two_stage_event_targets"])
    stage2_cache = read_table(resolved["stage2_path_cache"])
    feature_dict = read_table(resolved["two_stage_feature_dictionary"])
    redundancy = read_table(resolved["realized_path_feature_redundancy_audit"])
    stage1_card = read_table(resolved["stage_1_model_card"])
    stage2_card = read_table(resolved["stage_2_model_card"])
    key_cols = ["meta_event_id", "instrument", "split"]
    target_cols = [col for col in targets.columns if col not in feature_matrix.columns or col in key_cols]
    matrix = feature_matrix.merge(targets[target_cols], on=key_cols, how="left")
    cache_cols = [col for col in ["path_key", "instrument", "stage_2_decision_pos", "stage_2_entry_blocked", "stage_2_horizon_complete_20d"] if col in stage2_cache.columns]
    matrix = matrix.merge(stage2_cache[cache_cols].drop_duplicates(["path_key", "instrument"]), on=["path_key", "instrument"], how="left", suffixes=("", "_cache"))
    for col in ("stage_2_entry_blocked", "stage_2_horizon_complete_20d"):
        cache_col = f"{col}_cache"
        if cache_col in matrix.columns:
            matrix[col] = matrix[col].where(matrix[col].notna(), matrix[cache_col])
    matrix["event_t0_date"] = matrix["event_t0_date"].map(date_text)
    matrix["calendar_month"] = matrix["event_t0_date"].map(month_text)
    matrix["calendar_year"] = matrix["event_t0_date"].map(year_text)
    matrix["event_t0_pos"] = numeric(matrix["event_t0_pos"])
    matrix["stage_2_decision_pos"] = numeric(matrix["stage_2_decision_pos"])
    for col in (
        "stage_1_evaluable",
        PRIMARY_STAGE1_TARGET,
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        PRIMARY_STAGE2_TARGET,
        "stage_2_evaluable",
    ):
        if col in matrix:
            matrix[col] = bool_series(matrix[col])
    stage1_features, stage2_features = feature_lists(feature_dict, feature_matrix, redundancy, stage1_card, stage2_card, config)
    frozen_path = resolved.get("frozen_row_level_scores", Path(""))
    source_meta = {
        "score_source_mode": "reproduce_12A6c_v1",
        "score_source_caveat": "",
        "stage_1_feature_order_hash": stable_hash(stage1_features),
        "stage_2_feature_order_hash": stable_hash(stage2_features),
    }
    if frozen_path and frozen_path.exists():
        scores = read_table(frozen_path)
        need = ["meta_event_id", PRIMARY_STAGE1_SCORE, PRIMARY_STAGE2_SCORE]
        if set(need).issubset(scores.columns):
            matrix = matrix.drop(columns=[PRIMARY_STAGE1_SCORE, PRIMARY_STAGE2_SCORE], errors="ignore").merge(scores[need], on="meta_event_id", how="left")
            source_meta["score_source_mode"] = "frozen_12A6c_row_level_scores"
    if PRIMARY_STAGE1_SCORE not in matrix.columns or PRIMARY_STAGE2_SCORE not in matrix.columns:
        max_iter = int(config["models"]["logistic_max_iter"])
        stage1_train_source = matrix.loc[bool_series(matrix["stage_1_evaluable"])].copy()
        stage1_scored, med1, status1 = impute_and_score_logistic(stage1_train_source, stage1_train_source, stage1_features, PRIMARY_STAGE1_TARGET, PRIMARY_STAGE1_SCORE, max_iter=max_iter)
        matrix = matrix.drop(columns=[PRIMARY_STAGE1_SCORE], errors="ignore").merge(stage1_scored[["meta_event_id", PRIMARY_STAGE1_SCORE]], on="meta_event_id", how="left")
        stage2_train_source = matrix.loc[bool_series(matrix["stage_2_evaluable"])].copy()
        stage2_score_frame = matrix.loc[bool_series(matrix["no_fast_fail_L10_H20"]) & bool_series(matrix["stage_2_path_evaluable"])].copy()
        stage2_scored, med2, status2 = impute_and_score_logistic(stage2_train_source, stage2_score_frame, stage2_features, PRIMARY_STAGE2_TARGET, PRIMARY_STAGE2_SCORE, max_iter=max_iter)
        matrix = matrix.drop(columns=[PRIMARY_STAGE2_SCORE], errors="ignore").merge(stage2_scored[["meta_event_id", PRIMARY_STAGE2_SCORE]], on="meta_event_id", how="left")
        source_meta.update(
            {
                "stage_1_train_imputation_median_hash": stable_hash(med1),
                "stage_2_train_imputation_median_hash": stable_hash(med2),
                "stage_1_fit_status": status1,
                "stage_2_fit_status": status2,
            }
        )
    matrix["score_source_mode"] = source_meta["score_source_mode"]
    matrix["score_source_caveat"] = source_meta["score_source_caveat"]
    matrix["stage_1_model_id"] = config["models"]["primary_stage_1_model_id"]
    matrix["stage_2_model_id"] = config["models"]["primary_stage_2_model_id"]
    matrix["stage_1_feature_order_hash"] = source_meta["stage_1_feature_order_hash"]
    matrix["stage_2_feature_order_hash"] = source_meta["stage_2_feature_order_hash"]
    matrix["stage_1_train_imputation_median_hash"] = source_meta.get("stage_1_train_imputation_median_hash", "")
    matrix["stage_2_train_imputation_median_hash"] = source_meta.get("stage_2_train_imputation_median_hash", "")
    return matrix, pd.DataFrame({"stage": ["stage_1", "stage_2"], "feature_list": [stage1_features, stage2_features]}), source_meta


def build_score_reproduction_audit(matrix: pd.DataFrame, resolved: dict[str, Path], config: dict[str, Any], source_meta: dict[str, Any]) -> pd.DataFrame:
    if source_meta["score_source_mode"] == "frozen_12A6c_row_level_scores":
        return pd.DataFrame(
            [
                {
                    "stage": stage,
                    "model_id": config["models"][f"primary_{stage}_model_id"],
                    "score_source_mode": source_meta["score_source_mode"],
                    "fit_split": "train",
                    "feature_order_hash": source_meta[f"{stage}_feature_order_hash"],
                    "feature_list_hash_expected": source_meta[f"{stage}_feature_order_hash"],
                    "feature_list_hash_reproduced": source_meta[f"{stage}_feature_order_hash"],
                    "train_imputation_median_hash": "",
                    "sklearn_version": "",
                    "numpy_version": np.__version__,
                    "pandas_version": pd.__version__,
                    "split": "all",
                    "reference_selected_n": np.nan,
                    "reproduced_selected_n": np.nan,
                    "selected_n_abs_diff": 0,
                    "reference_target_rate": np.nan,
                    "reproduced_target_rate": np.nan,
                    "target_rate_abs_diff": 0.0,
                    "reference_score_threshold": np.nan,
                    "reproduced_score_threshold": np.nan,
                    "score_threshold_abs_diff": 0.0,
                    "score_reproduction_status": "frozen_row_level_scores",
                    "score_source_caveat": "",
                    "failure_reason": "",
                }
                for stage in ("stage_1", "stage_2")
            ]
        )
    rows: list[dict[str, Any]] = []
    import sklearn

    refs = {
        "stage_1": read_table(resolved["stage_1_rejector_readout"]),
        "stage_2": read_table(resolved["stage_2_continuation_readout"]),
    }
    stage_specs = {
        "stage_1": {
            "frame": matrix.loc[bool_series(matrix["stage_1_evaluable"])].copy(),
            "score_col": PRIMARY_STAGE1_SCORE,
            "flag_col": "stage1_keep_flag_reproduced",
            "budget": float(config["primary_X_stage_1"]),
            "lower": True,
            "target": PRIMARY_STAGE1_TARGET,
            "selected_col": "stage1_keep_n",
            "rate_col": "stage1_keep_fast_fail_rate",
        },
        "stage_2": {
            "frame": matrix.loc[bool_series(matrix["stage_2_evaluable"])].copy(),
            "score_col": PRIMARY_STAGE2_SCORE,
            "flag_col": "stage2_continue_flag_reproduced",
            "budget": float(config["primary_X_stage_2"]),
            "lower": False,
            "target": PRIMARY_STAGE2_TARGET,
            "selected_col": "stage2_continue_n",
            "rate_col": "stage2_continue_continuation_rate",
        },
    }
    for stage, spec in stage_specs.items():
        selected, health = assign_fixed_budget_flags(spec["frame"], spec["score_col"], spec["flag_col"], spec["budget"], spec["lower"])
        ref = refs[stage]
        ref = ref.loc[ref["model_id"].astype(str).eq(config["models"][f"primary_{stage}_model_id"])]
        health_idx = health.set_index("split")
        for split in SPLITS:
            ref_row = ref.loc[ref["split"].astype(str).eq(split)].iloc[0] if not ref.loc[ref["split"].astype(str).eq(split)].empty else pd.Series(dtype=object)
            sub = split_frame(selected, split)
            picked = sub.loc[bool_series(sub[spec["flag_col"]])]
            reproduced_selected_n = int(len(picked))
            reproduced_rate = weighted_rate(picked.assign(sample_weight=1.0), spec["target"])
            reproduced_threshold = health_idx.loc[split, "score_threshold"] if split in health_idx.index else np.nan
            reference_selected_n = pd.to_numeric(pd.Series([ref_row.get(spec["selected_col"], np.nan)]), errors="coerce").iloc[0]
            reference_rate = pd.to_numeric(pd.Series([ref_row.get(spec["rate_col"], np.nan)]), errors="coerce").iloc[0]
            reference_threshold = pd.to_numeric(pd.Series([ref_row.get("score_threshold", np.nan)]), errors="coerce").iloc[0]
            selected_diff = abs(reproduced_selected_n - reference_selected_n) if pd.notna(reference_selected_n) else np.nan
            rate_diff = abs(reproduced_rate - reference_rate) if pd.notna(reference_rate) and pd.notna(reproduced_rate) else np.nan
            threshold_diff = abs(reproduced_threshold - reference_threshold) if pd.notna(reference_threshold) and pd.notna(reproduced_threshold) else np.nan
            exact = (pd.isna(selected_diff) or selected_diff <= 0) and (pd.isna(rate_diff) or rate_diff <= 1e-9) and (pd.isna(threshold_diff) or threshold_diff <= 1e-9)
            # Refit is a fallback, not the primary score-transport mechanism. Existing
            # 12A6c artifacts can sit on a dense probability boundary where a tiny
            # threshold change flips dozens of rows while the target rate is stable.
            near = (
                (pd.isna(selected_diff) or selected_diff <= max(50, 0.05 * max(float(reference_selected_n or 0), 1)))
                and (pd.isna(rate_diff) or rate_diff <= 0.001)
                and (pd.isna(threshold_diff) or threshold_diff <= 0.001)
            )
            rows.append(
                {
                    "stage": stage,
                    "model_id": config["models"][f"primary_{stage}_model_id"],
                    "score_source_mode": source_meta["score_source_mode"],
                    "fit_split": "train",
                    "feature_order_hash": source_meta[f"{stage}_feature_order_hash"],
                    "feature_list_hash_expected": source_meta[f"{stage}_feature_order_hash"],
                    "feature_list_hash_reproduced": source_meta[f"{stage}_feature_order_hash"],
                    "train_imputation_median_hash": source_meta.get(f"{stage}_train_imputation_median_hash", ""),
                    "sklearn_version": sklearn.__version__,
                    "numpy_version": np.__version__,
                    "pandas_version": pd.__version__,
                    "split": split,
                    "reference_selected_n": reference_selected_n,
                    "reproduced_selected_n": reproduced_selected_n,
                    "selected_n_abs_diff": selected_diff,
                    "reference_target_rate": reference_rate,
                    "reproduced_target_rate": reproduced_rate,
                    "target_rate_abs_diff": rate_diff,
                    "reference_score_threshold": reference_threshold,
                    "reproduced_score_threshold": reproduced_threshold,
                    "score_threshold_abs_diff": threshold_diff,
                    "score_reproduction_status": "pass_exact" if exact else ("pass_near_miss" if near else "fail"),
                    "score_source_caveat": "" if exact else ("numerical_near_miss" if near else "reproduction_failure"),
                    "failure_reason": "" if exact or near else "reproduced_readout_outside_tolerance",
                }
            )
    return pd.DataFrame(rows)


def worst_score_status(audit: pd.DataFrame) -> tuple[str, str]:
    statuses = set(audit["score_reproduction_status"].astype(str))
    if "fail" in statuses:
        return "fail", "reproduction_failure"
    if "pass_near_miss" in statuses:
        return "pass_near_miss", "numerical_near_miss"
    if "frozen_row_level_scores" in statuses:
        return "frozen_row_level_scores", ""
    return "pass_exact", ""


def rolling_percentiles(
    frame: pd.DataFrame,
    *,
    score_col: str,
    pos_col: str,
    board_col: str,
    policy: HistoryPolicy,
    global_min_history_n: int,
    board_min_history_n: int,
) -> pd.DataFrame:
    out = frame.copy()
    n = len(out)
    out["rank_percentile"] = np.nan
    out["history_n"] = 0
    out["history_scope"] = "none"
    out["rank_status"] = "rank_not_evaluable"
    if n == 0:
        return out
    sort_cols = [pos_col, "instrument", "event_t0_date", "meta_event_id"]
    order = out.sort_values([col for col in sort_cols if col in out.columns], kind="stable").index.to_numpy()
    pos = pd.to_numeric(out.loc[order, pos_col], errors="coerce").to_numpy(dtype=float)
    score = pd.to_numeric(out.loc[order, score_col], errors="coerce").to_numpy(dtype=float)
    board = out.loc[order, board_col].astype(str).to_numpy()
    for sorted_i, idx in enumerate(order):
        cur_pos = pos[sorted_i]
        cur_score = score[sorted_i]
        if not np.isfinite(cur_pos) or not np.isfinite(cur_score):
            continue
        end = int(np.searchsorted(pos, cur_pos, side="left"))
        if policy.history_window_mode == "expanding_from_inception" or policy.trailing_history_window_sessions is None:
            start = 0
        else:
            start = int(np.searchsorted(pos, cur_pos - float(policy.trailing_history_window_sessions), side="left"))
        if end <= start:
            continue
        window_score = score[start:end]
        finite = np.isfinite(window_score)
        if not finite.any():
            continue
        window_score = window_score[finite]
        window_board = board[start:end][finite]
        board_values = window_score[window_board == board[sorted_i]]
        if len(board_values) >= board_min_history_n:
            values = board_values
            scope = "board"
        elif len(window_score) >= global_min_history_n:
            values = window_score
            scope = "global"
        else:
            continue
        percentile = ((values < cur_score).sum() + 0.5 * (values == cur_score).sum()) / len(values)
        out.at[idx, "rank_percentile"] = float(percentile)
        out.at[idx, "history_n"] = int(len(values))
        out.at[idx, "history_scope"] = scope
        out.at[idx, "rank_status"] = "rank_evaluable"
    return out


def apply_stage1_rank(matrix: pd.DataFrame, policy: HistoryPolicy, budget: float, config: dict[str, Any]) -> pd.DataFrame:
    h = config["history_min_n"]
    frame = matrix.loc[bool_series(matrix["stage_1_evaluable"])].copy()
    ranked = rolling_percentiles(
        frame,
        score_col=PRIMARY_STAGE1_SCORE,
        pos_col="event_t0_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_1_global_min_history_n"]),
        board_min_history_n=int(h["stage_1_board_min_history_n"]),
    )
    ranked["stage"] = "stage_1"
    ranked["history_policy_id"] = policy.history_policy_id
    ranked["history_window_mode"] = policy.history_window_mode
    ranked["trailing_history_window_sessions"] = policy.trailing_history_window_sessions
    ranked["stage1_budget_X"] = float(budget)
    ranked["stage2_budget_X"] = np.nan
    ranked["stage1_gate_source"] = "primary_model_trailing_rank_keep"
    ranked["selected_flag"] = ranked["rank_status"].eq("rank_evaluable") & ranked["rank_percentile"].le(float(budget))
    ranked["diagnostic_only_flag"] = policy.diagnostic_only_flag
    return ranked


def apply_stage2_rank(matrix: pd.DataFrame, stage1_ranked: pd.DataFrame, policy: HistoryPolicy, stage1_budget: float, stage2_budget: float, config: dict[str, Any]) -> pd.DataFrame:
    h = config["history_min_n"]
    stage1_keep_ids = set(stage1_ranked.loc[stage1_ranked["selected_flag"], "meta_event_id"].astype(str))
    frame = matrix.loc[
        matrix["meta_event_id"].astype(str).isin(stage1_keep_ids)
        & bool_series(matrix["no_fast_fail_L10_H20"])
        & bool_series(matrix["stage_2_path_evaluable"])
        & (~bool_series(matrix["stage_2_entry_blocked"]))
        & bool_series(matrix["stage_2_horizon_complete_20d"])
    ].copy()
    ranked = rolling_percentiles(
        frame,
        score_col=PRIMARY_STAGE2_SCORE,
        pos_col="stage_2_decision_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_2_global_min_history_n"]),
        board_min_history_n=int(h["stage_2_board_min_history_n"]),
    )
    ranked["stage"] = "stage_2"
    ranked["history_policy_id"] = policy.history_policy_id
    ranked["history_window_mode"] = policy.history_window_mode
    ranked["trailing_history_window_sessions"] = policy.trailing_history_window_sessions
    ranked["stage1_budget_X"] = float(stage1_budget)
    ranked["stage2_budget_X"] = float(stage2_budget)
    ranked["stage1_gate_source"] = "primary_model_trailing_rank_keep"
    ranked["selected_flag"] = ranked["rank_status"].eq("rank_evaluable") & ranked["rank_percentile"].ge(1.0 - float(stage2_budget))
    ranked["diagnostic_only_flag"] = policy.diagnostic_only_flag
    return ranked


def classify_budget_tuple(stage: str, stage1_budget: float, stage2_budget: float | None, config: dict[str, Any]) -> str:
    p1 = float(config["primary_X_stage_1"])
    p2 = float(config["primary_X_stage_2"])
    if stage == "stage_1":
        return "primary" if abs(stage1_budget - p1) < 1e-12 else "stage_1_curve"
    if abs(stage1_budget - p1) < 1e-12 and stage2_budget is not None and abs(float(stage2_budget) - p2) < 1e-12:
        return "primary"
    if abs(stage1_budget - p1) < 1e-12:
        return "stage_2_chained_curve"
    return "paired_grid_diagnostic"


def readout_rows_for_selection(selection: pd.DataFrame, stage: str, target_col: str, score_col: str, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if selection.empty:
        return pd.DataFrame()
    for split in SPLITS:
        frame = split_frame(selection, split)
        rank_evaluable = frame.loc[frame["rank_status"].eq("rank_evaluable")]
        selected = frame.loc[frame["selected_flag"]]
        positive = bool_series(frame[target_col]).sum()
        selected_positive = bool_series(selected[target_col]).sum()
        base_rate = weighted_rate(rank_evaluable.assign(sample_weight=1.0), target_col)
        selected_rate = weighted_rate(selected.assign(sample_weight=1.0), target_col)
        stage1_budget = float(frame["stage1_budget_X"].dropna().iloc[0]) if frame["stage1_budget_X"].notna().any() else np.nan
        stage2_budget = float(frame["stage2_budget_X"].dropna().iloc[0]) if "stage2_budget_X" in frame and frame["stage2_budget_X"].notna().any() else np.nan
        rows.append(
            {
                "stage": stage,
                "split": split,
                "history_policy_id": str(selection["history_policy_id"].iloc[0]),
                "history_window_mode": str(selection["history_window_mode"].iloc[0]),
                "trailing_history_window_sessions": selection["trailing_history_window_sessions"].iloc[0],
                "stage1_gate_source": "primary_model_trailing_rank_keep",
                "stage1_budget_X": stage1_budget,
                "stage2_budget_X": stage2_budget,
                "budget_tuple_role": classify_budget_tuple(stage, stage1_budget, stage2_budget if pd.notna(stage2_budget) else None, config),
                "model_id": config["models"]["primary_stage_1_model_id"] if stage == "stage_1" else config["models"]["primary_stage_2_model_id"],
                "score_id": score_col,
                "target_id": target_col,
                "denominator_n": int(len(frame)),
                "rank_evaluable_n": int(frame["rank_status"].eq("rank_evaluable").sum()),
                "rank_not_evaluable_n": int(frame["rank_status"].ne("rank_evaluable").sum()),
                "denominator_positive_n": int(positive),
                "rank_evaluable_positive_n": int(bool_series(rank_evaluable[target_col]).sum()),
                "selected_n": int(len(selected)),
                "selected_positive_n": int(selected_positive),
                "selected_budget_total": safe_rate(len(selected), len(frame)),
                "selected_budget_rank_evaluable": safe_rate(len(selected), frame["rank_status"].eq("rank_evaluable").sum()),
                "selected_rate": selected_rate,
                "base_rate": base_rate,
                "delta_vs_base": selected_rate - base_rate if len(selected) and len(rank_evaluable) else np.nan,
                "random_p05": np.nan,
                "random_p50": np.nan,
                "random_p95": np.nan,
                "delta_vs_random_p50": np.nan,
                "single_feature_name": "",
                "single_feature_common_denominator_n": np.nan,
                "single_feature_matched_selected_n": np.nan,
                "single_feature_actual_budget_common": np.nan,
                "single_feature_selected_rate": np.nan,
                "delta_vs_single_feature": np.nan,
                "relative_lift_vs_random_p50": np.nan,
                "relative_lift_vs_single_feature": np.nan,
                "bootstrap_ci95_low": np.nan,
                "bootstrap_ci95_high": np.nan,
                "bootstrap_random_ci95_low": np.nan,
                "bootstrap_random_ci95_high": np.nan,
                "bootstrap_single_feature_ci95_low": np.nan,
                "bootstrap_single_feature_ci95_high": np.nan,
                "bootstrap_positive_n": int(selected_positive),
                "bootstrap_status": "pending",
                "readout_status": "ok",
                "diagnostic_only_flag": bool(selection["diagnostic_only_flag"].iloc[0]) or classify_budget_tuple(stage, stage1_budget, stage2_budget if pd.notna(stage2_budget) else None, config).endswith("diagnostic"),
            }
        )
    return pd.DataFrame(rows)


def budget_drift_rows(selection: pd.DataFrame, stage: str) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        frame = split_frame(selection, split)
        selected = frame.loc[frame["selected_flag"]]
        target_budget = float(frame["stage1_budget_X"].dropna().iloc[0]) if stage == "stage_1" else float(frame["stage2_budget_X"].dropna().iloc[0])
        total = safe_rate(len(selected), len(frame))
        eval_budget = safe_rate(len(selected), frame["rank_status"].eq("rank_evaluable").sum())
        rows.append(
            {
                "stage": stage,
                "split": split,
                "history_policy_id": str(selection["history_policy_id"].iloc[0]),
                "history_window_mode": str(selection["history_window_mode"].iloc[0]),
                "trailing_history_window_sessions": selection["trailing_history_window_sessions"].iloc[0],
                "stage1_gate_source": "primary_model_trailing_rank_keep",
                "stage1_budget_X": float(frame["stage1_budget_X"].dropna().iloc[0]),
                "stage2_budget_X": float(frame["stage2_budget_X"].dropna().iloc[0]) if frame["stage2_budget_X"].notna().any() else np.nan,
                "budget_tuple_role": frame.get("budget_tuple_role", pd.Series([""])).iloc[0] if "budget_tuple_role" in frame else "",
                "denominator_n": int(len(frame)),
                "rank_evaluable_n": int(frame["rank_status"].eq("rank_evaluable").sum()),
                "rank_not_evaluable_n": int(frame["rank_status"].ne("rank_evaluable").sum()),
                "rank_not_evaluable_rate": safe_rate(frame["rank_status"].ne("rank_evaluable").sum(), len(frame)),
                "selected_n": int(len(selected)),
                "actual_budget_total": total,
                "actual_budget_rank_evaluable": eval_budget,
                "budget_abs_delta_total_vs_X": abs(total - target_budget) if pd.notna(total) else np.nan,
                "budget_abs_delta_rank_evaluable_vs_X": abs(eval_budget - target_budget) if pd.notna(eval_budget) else np.nan,
                "board_history_used_rate": safe_rate(frame["history_scope"].eq("board").sum(), len(frame)),
                "global_fallback_rate": safe_rate(frame["history_scope"].eq("global").sum(), len(frame)),
                "history_n_p05": frame["history_n"].quantile(0.05) if len(frame) else np.nan,
                "history_n_p50": frame["history_n"].quantile(0.50) if len(frame) else np.nan,
                "history_n_p95": frame["history_n"].quantile(0.95) if len(frame) else np.nan,
                "budget_drift_status": "readout",
            }
        )
    return pd.DataFrame(rows)


def prepare_random_labels(resolved: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    random_entries = read_table(resolved["matched_random_sampled_entries"])
    path_cache = read_table(resolved["entry_forward_path_cache"])
    stage2_cache = read_table(resolved["stage2_path_cache"])
    key = ["path_key", "instrument", "entry_pos", "entry_price"]
    path_cache_duplicate_n = int(path_cache.duplicated(key).sum())
    stage2_cache_duplicate_n = int(stage2_cache.duplicated(key).sum())
    if path_cache_duplicate_n or stage2_cache_duplicate_n:
        raise RuntimeError(
            "12A7 random path cache merge key is not unique: "
            f"entry_forward_path_cache_duplicates={path_cache_duplicate_n}, "
            f"stage2_path_cache_duplicates={stage2_cache_duplicate_n}"
        )
    random = random_entries.merge(path_cache, on=key, how="left")
    random = random.merge(stage2_cache, on=key, how="left", suffixes=("", "_stage2"))
    random["random_stage_1_evaluable"] = (~bool_series(random["entry_blocked"])) & bool_series(random["horizon_complete_20d"])
    random["random_stage_1_fast_fail_target"] = bool_series(random["random_stage_1_evaluable"]) & random["time_to_lower_minus_10_20d"].notna()
    random["random_no_fast_fail_L10_H20"] = bool_series(random["random_stage_1_evaluable"]) & (~bool_series(random["random_stage_1_fast_fail_target"]))
    random["random_stage_2_entry_blocked"] = bool_series(random["stage_2_entry_blocked"])
    random["random_stage_2_horizon_complete_20d"] = bool_series(random["stage_2_horizon_complete_20d"])
    random["random_stage_2_continuation_target"] = bool_series(random["continuation_U20_L10_H2_20"]) if "continuation_U20_L10_H2_20" in random else False
    random["random_stage_2_evaluable"] = (
        bool_series(random["random_no_fast_fail_L10_H20"])
        & (~bool_series(random["random_stage_2_entry_blocked"]))
        & bool_series(random["random_stage_2_horizon_complete_20d"])
    )
    audit = (
        random.groupby(["seed", "split", "board_bucket", "calendar_month"], dropna=False)
        .agg(
            random_sampled_n=("path_key", "size"),
            path_cache_matched_n=("entry_blocked", lambda s: int(s.notna().sum())),
            stage2_cache_matched_n=("stage_2_entry_blocked", lambda s: int(s.notna().sum())),
            random_stage_1_evaluable_n=("random_stage_1_evaluable", "sum"),
            random_no_fast_fail_n=("random_no_fast_fail_L10_H20", "sum"),
            random_stage_2_path_evaluable_n=("random_stage_2_evaluable", "sum"),
            random_stage_2_positive_n=("random_stage_2_continuation_target", "sum"),
            sample_weight_sum=("sample_weight", "sum"),
        )
        .reset_index()
    )
    audit["merge_key_unique_status"] = "pass"
    audit["random_path_label_status"] = "pass"
    audit["failure_reason"] = ""
    return random, audit


def random_rank_columns(random: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    return [col for col in config["random_baseline"]["retention_rank_columns"] if col in random.columns]


def model_cell_budgets(selection: pd.DataFrame, denom: pd.DataFrame | None = None) -> pd.DataFrame:
    cell_cols = ["split", "board_bucket", "calendar_month"]
    base = selection if denom is None else denom
    den = base.groupby(cell_cols, dropna=False).size().rename("model_denominator_n").reset_index()
    if "rank_status" in selection.columns:
        eval_counts = (
            selection.loc[selection["rank_status"].eq("rank_evaluable")]
            .groupby(cell_cols, dropna=False)
            .size()
            .rename("model_rank_evaluable_n")
            .reset_index()
        )
    else:
        eval_counts = den[cell_cols + ["model_denominator_n"]].rename(columns={"model_denominator_n": "model_rank_evaluable_n"})
    sel = selection.loc[selection["selected_flag"]].groupby(cell_cols, dropna=False).size().rename("model_selected_n").reset_index()
    out = den.merge(eval_counts, on=cell_cols, how="left").merge(sel, on=cell_cols, how="left").fillna({"model_selected_n": 0, "model_rank_evaluable_n": 0})
    out["model_selected_n"] = out["model_selected_n"].astype(int)
    out["model_denominator_n"] = out["model_denominator_n"].astype(int)
    out["model_rank_evaluable_n"] = out["model_rank_evaluable_n"].astype(int)
    out["model_cell_budget"] = out["model_selected_n"] / out["model_denominator_n"].replace(0, np.nan)
    return out


def select_random_by_cell(random: pd.DataFrame, budgets: pd.DataFrame, denominator_col: str, target_col: str, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cell_cols = ["split", "board_bucket", "calendar_month"]
    group_cols = ["seed"] + cell_cols
    rank_cols = random_rank_columns(random, config)
    den = random.loc[bool_series(random[denominator_col])].copy()
    den = den.drop(columns=["model_denominator_n", "model_rank_evaluable_n", "model_selected_n", "model_cell_budget"], errors="ignore")
    den = den.merge(budgets[cell_cols + ["model_denominator_n", "model_rank_evaluable_n", "model_selected_n", "model_cell_budget"]], on=cell_cols, how="inner")
    if den.empty:
        return den, pd.DataFrame()
    den = den.sort_values(group_cols + rank_cols, kind="stable")
    den["_random_denominator_n"] = den.groupby(group_cols, dropna=False)["path_key"].transform("size")
    den["_rank_in_cell"] = den.groupby(group_cols, dropna=False).cumcount() + 1
    den["_random_selected_n"] = np.floor(den["model_cell_budget"] * den["_random_denominator_n"]).astype(int)
    den.loc[(den["_random_selected_n"].eq(0)) & (den["model_selected_n"].gt(0)) & (den["_random_denominator_n"].gt(0)), "_random_selected_n"] = 1
    den["_selected"] = den["_rank_in_cell"].le(den["_random_selected_n"])
    selected = den.loc[den["_selected"]].copy()
    selected["_weighted_target"] = bool_series(selected[target_col]).astype(float) * pd.to_numeric(selected["sample_weight"], errors="coerce").fillna(1.0)
    audit = (
        den.groupby(group_cols, dropna=False)
        .agg(
            model_denominator_n=("model_denominator_n", "first"),
            model_rank_evaluable_n=("model_rank_evaluable_n", "first"),
            model_selected_n=("model_selected_n", "first"),
            model_budget=("model_cell_budget", "first"),
            random_denominator_n=("_random_denominator_n", "first"),
            random_selected_n=("_random_selected_n", "first"),
            sample_weight_sum=("sample_weight", "sum"),
        )
        .reset_index()
    )
    if not selected.empty:
        rates = (
            selected.groupby(group_cols, dropna=False)
            .agg(
                random_positive_n=(target_col, lambda s: int(bool_series(s).sum())),
                _target_sum=("_weighted_target", "sum"),
                _weight_sum=("sample_weight", "sum"),
            )
            .reset_index()
        )
        rates["random_rate"] = rates["_target_sum"] / rates["_weight_sum"].replace(0, np.nan)
        audit = audit.merge(rates[group_cols + ["random_positive_n", "random_rate"]], on=group_cols, how="left")
    else:
        audit["random_positive_n"] = np.nan
        audit["random_rate"] = np.nan
    audit["random_positive_n"] = pd.to_numeric(audit["random_positive_n"], errors="coerce").fillna(0).astype(int)
    audit["retention_rank_rule"] = ",".join(rank_cols)
    audit["random_cell_status"] = "ok"
    return selected.drop(columns=["_weighted_target"], errors="ignore"), audit


def random_quantiles_from_selected(selected: pd.DataFrame, target_col: str) -> pd.DataFrame:
    rows = []
    if selected.empty:
        return pd.DataFrame(columns=["split", "random_p05", "random_p50", "random_p95"])
    for seed, seed_group in selected.groupby("seed", sort=False):
        for split in SPLITS:
            sub = split_frame(seed_group, split)
            rows.append({"seed": seed, "split": split, "random_rate": weighted_rate(sub, target_col)})
    seed_rates = pd.DataFrame(rows)
    out = (
        seed_rates.groupby("split")["random_rate"]
        .quantile([0.05, 0.50, 0.95])
        .unstack()
        .reset_index()
    )
    out.columns = ["split", "random_p05", "random_p50", "random_p95"]
    return out


def random_metadata(selection: pd.DataFrame, stage: str, config: dict[str, Any]) -> dict[str, Any]:
    stage1_budget = float(selection["stage1_budget_X"].dropna().iloc[0])
    stage2_budget = float(selection["stage2_budget_X"].dropna().iloc[0]) if "stage2_budget_X" in selection and selection["stage2_budget_X"].notna().any() else np.nan
    return {
        "history_policy_id": str(selection["history_policy_id"].iloc[0]),
        "history_window_mode": str(selection["history_window_mode"].iloc[0]),
        "trailing_history_window_sessions": selection["trailing_history_window_sessions"].iloc[0],
        "stage1_gate_source": "primary_model_trailing_rank_keep",
        "stage1_budget_X": stage1_budget,
        "stage2_budget_X": stage2_budget,
        "budget_tuple_role": classify_budget_tuple(stage, stage1_budget, stage2_budget if pd.notna(stage2_budget) else None, config),
    }


def add_random_metadata(frame: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
    out = frame.copy()
    for key, value in metadata.items():
        out[key] = value
    return out


def stage1_random_baseline(random: pd.DataFrame, selection: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    budgets = model_cell_budgets(selection)
    selected, audit = select_random_by_cell(random, budgets, "random_stage_1_evaluable", "random_stage_1_fast_fail_target", config)
    quant = random_quantiles_from_selected(selected, "random_stage_1_fast_fail_target")
    metadata = random_metadata(selection, "stage_1", config)
    audit.insert(0, "stage", "stage_1")
    audit = add_random_metadata(audit, metadata)
    audit["random_stage1_denominator_n"] = audit["random_denominator_n"]
    audit["random_stage1_keep_n"] = audit["random_selected_n"]
    audit["random_target_id"] = "random_stage_1_fast_fail_target"
    quant.insert(0, "stage", "stage_1")
    quant = add_random_metadata(quant, metadata)
    return selected, audit, quant


def stage2_random_baseline(
    random: pd.DataFrame,
    stage1_selection: pd.DataFrame,
    stage2_selection: pd.DataFrame,
    config: dict[str, Any],
    *,
    random_stage1_keep: pd.DataFrame | None = None,
    stage1_audit: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if random_stage1_keep is None or stage1_audit is None:
        stage1_budgets = model_cell_budgets(stage1_selection)
        random_stage1_keep, stage1_audit = select_random_by_cell(random, stage1_budgets, "random_stage_1_evaluable", "random_stage_1_fast_fail_target", config)
    stage2_budgets = model_cell_budgets(stage2_selection)
    selected, audit = select_random_by_cell(random_stage1_keep, stage2_budgets, "random_stage_2_evaluable", "random_stage_2_continuation_target", config)
    quant = random_quantiles_from_selected(selected, "random_stage_2_continuation_target")
    stage1_keep_by_cell = stage1_audit[["seed", "split", "board_bucket", "calendar_month", "random_denominator_n", "random_selected_n"]].rename(
        columns={"random_denominator_n": "random_stage1_denominator_n", "random_selected_n": "random_stage1_keep_n"}
    )
    audit = audit.merge(stage1_keep_by_cell, on=["seed", "split", "board_bucket", "calendar_month"], how="left")
    metadata = random_metadata(stage2_selection, "stage_2", config)
    audit.insert(0, "stage", "stage_2")
    audit = add_random_metadata(audit, metadata)
    audit["random_target_id"] = "random_stage_2_continuation_target"
    quant.insert(0, "stage", "stage_2")
    quant = add_random_metadata(quant, metadata)
    return selected, audit, quant


def merge_random_into_readout(readout: pd.DataFrame, quant: pd.DataFrame) -> pd.DataFrame:
    if quant.empty:
        return readout
    key_cols = [
        "stage",
        "split",
        "history_policy_id",
        "history_window_mode",
        "trailing_history_window_sessions",
        "stage1_budget_X",
        "stage2_budget_X",
        "budget_tuple_role",
    ]
    out = readout.merge(quant[key_cols + ["random_p05", "random_p50", "random_p95"]], on=key_cols, how="left", suffixes=("", "_random_new"))
    for col in ("random_p05", "random_p50", "random_p95"):
        new_col = f"{col}_random_new"
        if new_col in out:
            out[col] = out[new_col].combine_first(out[col])
            out = out.drop(columns=[new_col])
    out["delta_vs_random_p50"] = out["selected_rate"] - out["random_p50"]
    out["relative_lift_vs_random_p50"] = out["selected_rate"] / out["random_p50"].replace(0, np.nan) - 1.0
    return out


def feature_rank_selection(frame: pd.DataFrame, feature: str, orientation: str, budget: float, policy: HistoryPolicy, stage: str, config: dict[str, Any]) -> pd.DataFrame:
    score_col = f"__feature_score_{feature}"
    out = frame.copy()
    out[score_col] = pd.to_numeric(out[feature], errors="coerce")
    if orientation == "asc":
        percentile_selected = "low"
    else:
        percentile_selected = "high"
    h = config["history_min_n"]
    ranked = rolling_percentiles(
        out,
        score_col=score_col,
        pos_col="event_t0_pos" if stage == "stage_1" else "stage_2_decision_pos",
        board_col="board_bucket",
        policy=policy,
        global_min_history_n=int(h["stage_1_global_min_history_n"] if stage == "stage_1" else h["stage_2_global_min_history_n"]),
        board_min_history_n=int(h["stage_1_board_min_history_n"] if stage == "stage_1" else h["stage_2_board_min_history_n"]),
    )
    ranked["feature_rank_selected"] = False
    if percentile_selected == "low":
        ranked["feature_rank_selected"] = ranked["rank_status"].eq("rank_evaluable") & ranked["rank_percentile"].le(float(budget))
    else:
        ranked["feature_rank_selected"] = ranked["rank_status"].eq("rank_evaluable") & ranked["rank_percentile"].ge(1.0 - float(budget))
    return ranked


def choose_single_feature(frame: pd.DataFrame, candidates: dict[str, str], target_col: str, policy: HistoryPolicy, stage: str, budget: float, maximize: bool, config: dict[str, Any]) -> tuple[str, str, pd.DataFrame]:
    rows = []
    best_feature = ""
    best_orientation = ""
    best_value = -np.inf if maximize else np.inf
    best_ranked = pd.DataFrame()
    for feature, orientation in candidates.items():
        if feature not in frame.columns:
            continue
        ranked = feature_rank_selection(frame, feature, orientation, budget, policy, stage, config)
        train = ranked.loc[ranked["split"].astype(str).eq("train") & ranked["feature_rank_selected"]]
        rate = weighted_rate(train.assign(sample_weight=1.0), target_col)
        rows.append({"feature_name": feature, "orientation_selected_on_train": orientation, "train_selected_rate": rate})
        if pd.notna(rate) and ((maximize and rate > best_value) or ((not maximize) and rate < best_value)):
            best_feature = feature
            best_orientation = orientation
            best_value = rate
            best_ranked = ranked
    if not best_feature and rows:
        first = sorted(rows, key=lambda item: item["feature_name"])[0]
        best_feature = first["feature_name"]
        best_orientation = str(candidates[best_feature])
        best_ranked = feature_rank_selection(frame, best_feature, best_orientation, budget, policy, stage, config)
    return best_feature, best_orientation, best_ranked


def matched_single_feature_replay(model_selection: pd.DataFrame, feature_frame: pd.DataFrame, feature: str, orientation: str, stage: str, target_col: str, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cell_cols = ["split", "board_bucket", "calendar_month"]
    common = model_selection.loc[model_selection["rank_status"].eq("rank_evaluable") & feature_frame["rank_status"].eq("rank_evaluable")].copy()
    common[feature] = pd.to_numeric(common[feature], errors="coerce")
    asc = orientation == "asc"
    selected_parts = []
    audit_rows = []
    for cell, group in common.groupby(cell_cols, dropna=False):
        model_group = model_selection.loc[
            model_selection["rank_status"].eq("rank_evaluable")
            & model_selection[cell_cols[0]].eq(cell[0])
            & model_selection[cell_cols[1]].eq(cell[1])
            & model_selection[cell_cols[2]].eq(cell[2])
        ]
        model_selected_n = int(model_group["selected_flag"].sum())
        ranked = group.sort_values([feature, "instrument", "event_t0_date", "meta_event_id"], ascending=[asc, True, True, True], kind="stable")
        selected = ranked.head(model_selected_n).copy()
        selected_parts.append(selected)
        audit_rows.append(
            {
                "split": cell[0],
                "board_bucket": cell[1],
                "calendar_month": cell[2],
                "common_denominator_n": int(len(group)),
                "model_rank_evaluable_n": int(len(model_group)),
                "matched_selected_n": int(len(selected)),
            }
        )
    selected_all = pd.concat(selected_parts, ignore_index=True) if selected_parts else common.head(0).copy()
    audit = pd.DataFrame(audit_rows)
    rows = []
    for split in SPLITS:
        model_split = split_frame(model_selection.loc[model_selection["rank_status"].eq("rank_evaluable")], split)
        common_split = split_frame(common, split)
        selected_split = split_frame(selected_all, split)
        rows.append(
            {
                "stage": stage,
                "feature_name": feature,
                "orientation_selected_on_train": orientation,
                "selection_split": "train",
                "history_policy_id": str(model_selection["history_policy_id"].iloc[0]),
                "history_window_mode": str(model_selection["history_window_mode"].iloc[0]),
                "trailing_history_window_sessions": model_selection["trailing_history_window_sessions"].iloc[0],
                "stage1_gate_source": "primary_model_trailing_rank_keep",
                "stage1_budget_X": float(model_selection["stage1_budget_X"].iloc[0]),
                "stage2_budget_X": float(model_selection["stage2_budget_X"].iloc[0]) if model_selection["stage2_budget_X"].notna().any() else np.nan,
                "budget_tuple_role": "primary",
                "split": split,
                "denominator_n": int(len(split_frame(model_selection, split))),
                "rank_evaluable_n": int(len(model_split)),
                "common_denominator_n": int(len(common_split)),
                "common_denominator_coverage": safe_rate(len(common_split), len(model_split)),
                "denominator_positive_n": int(bool_series(split_frame(model_selection, split)[target_col]).sum()),
                "rank_evaluable_positive_n": int(bool_series(model_split[target_col]).sum()),
                "selected_n": int(model_split["selected_flag"].sum()),
                "selected_positive_n": int(bool_series(selected_split[target_col]).sum()),
                "matched_selected_n": int(len(selected_split)),
                "matched_selected_rate": weighted_rate(selected_split.assign(sample_weight=1.0), target_col),
                "selected_budget_total": safe_rate(len(selected_split), len(split_frame(model_selection, split))),
                "selected_budget_rank_evaluable": safe_rate(len(selected_split), len(common_split)),
                "selected_rate": weighted_rate(selected_split.assign(sample_weight=1.0), target_col),
                "base_rate": weighted_rate(common_split.assign(sample_weight=1.0), target_col),
                "challenger_status": "ok",
                "denominator_match_status": "pass"
                if safe_rate(len(common_split), len(model_split)) >= float(config["single_feature_challenger"]["common_denominator_min_coverage"]) or split == "all"
                else "coverage_below_min",
                "diagnostic_only_flag": False,
            }
        )
    return selected_all, pd.DataFrame(rows)


def add_single_feature_to_readout(readout: pd.DataFrame, single_readout: pd.DataFrame, stage: str) -> pd.DataFrame:
    out = readout.copy()
    if single_readout.empty:
        return out
    cols = [
        "split",
        "feature_name",
        "common_denominator_n",
        "matched_selected_n",
        "selected_budget_rank_evaluable",
        "selected_rate",
    ]
    merged = out.loc[out["stage"].eq(stage)].merge(single_readout[cols], on="split", how="left", suffixes=("", "_single"))
    idx = out["stage"].eq(stage)
    out.loc[idx, "single_feature_name"] = merged["feature_name"].to_numpy()
    out.loc[idx, "single_feature_common_denominator_n"] = merged["common_denominator_n"].to_numpy()
    out.loc[idx, "single_feature_matched_selected_n"] = merged["matched_selected_n"].to_numpy()
    out.loc[idx, "single_feature_actual_budget_common"] = merged["selected_budget_rank_evaluable_single"].to_numpy()
    out.loc[idx, "single_feature_selected_rate"] = merged["selected_rate_single"].to_numpy()
    out.loc[idx, "delta_vs_single_feature"] = out.loc[idx, "selected_rate"].to_numpy() - merged["selected_rate_single"].to_numpy()
    out.loc[idx, "relative_lift_vs_single_feature"] = out.loc[idx, "selected_rate"].to_numpy() / merged["selected_rate_single"].replace(0, np.nan).to_numpy() - 1.0
    return out


def bootstrap_random_ci(
    model_selected: pd.DataFrame,
    target_col: str,
    *,
    compare_seed_selected: pd.DataFrame,
    compare_target_col: str | None = None,
    direction: str,
    config: dict[str, Any],
) -> tuple[float, float, str]:
    if model_selected.empty:
        return np.nan, np.nan, "insufficient_model_selected"
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]))
    n_resamples = int(config["bootstrap"]["n_resamples"])
    model_y = bool_series(model_selected[target_col]).astype(float).to_numpy()
    comp_target = compare_target_col or target_col
    deltas = []
    if compare_seed_selected.empty:
        return np.nan, np.nan, "insufficient_random_seed_rates"
    seed_rates = []
    for _, seed_group in compare_seed_selected.groupby("seed", sort=False):
        seed_rates.append(weighted_rate(seed_group, comp_target))
    seed_rates = np.asarray([x for x in seed_rates if pd.notna(x)], dtype=float)
    if len(seed_rates) == 0:
        return np.nan, np.nan, "insufficient_random_seed_rates"
    for _ in range(n_resamples):
        m = rng.choice(model_y, size=len(model_y), replace=True).mean()
        c = float(np.median(rng.choice(seed_rates, size=len(seed_rates), replace=True)))
        deltas.append(m - c)
    low = float(np.quantile(deltas, float(config["bootstrap"]["ci_low_q"])))
    high = float(np.quantile(deltas, float(config["bootstrap"]["ci_high_q"])))
    return low, high, f"bootstrap_{direction}_nested_random_seed"


def bootstrap_single_feature_paired_ci(
    model_selection: pd.DataFrame,
    single_selected: pd.DataFrame,
    target_col: str,
    split: str,
    *,
    config: dict[str, Any],
) -> tuple[float, float, str]:
    if "meta_event_id" not in model_selection.columns or "meta_event_id" not in single_selected.columns:
        return np.nan, np.nan, "single_feature_paired_bootstrap_missing_event_id"
    base = split_frame(model_selection.loc[model_selection["rank_status"].eq("rank_evaluable")], split).copy()
    if base.empty:
        return np.nan, np.nan, "insufficient_single_feature_common_denominator"
    single_ids = set(split_frame(single_selected, split)["meta_event_id"].astype(str))
    base["_model_selected_bootstrap"] = bool_series(base["selected_flag"])
    base["_single_selected_bootstrap"] = base["meta_event_id"].astype(str).isin(single_ids)
    if not base["_model_selected_bootstrap"].any() or not base["_single_selected_bootstrap"].any():
        return np.nan, np.nan, "insufficient_single_feature_selected"
    y = bool_series(base[target_col]).astype(float).to_numpy()
    model_flag = base["_model_selected_bootstrap"].to_numpy(dtype=bool)
    single_flag = base["_single_selected_bootstrap"].to_numpy(dtype=bool)
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]))
    n_resamples = int(config["bootstrap"]["n_resamples"])
    idx_source = np.arange(len(base))
    deltas = []
    for _ in range(n_resamples):
        idx = rng.choice(idx_source, size=len(idx_source), replace=True)
        model_mask = model_flag[idx]
        single_mask = single_flag[idx]
        if not model_mask.any() or not single_mask.any():
            continue
        sample_y = y[idx]
        deltas.append(float(sample_y[model_mask].mean() - sample_y[single_mask].mean()))
    if not deltas:
        return np.nan, np.nan, "insufficient_single_feature_bootstrap_replicates"
    low = float(np.quantile(deltas, float(config["bootstrap"]["ci_low_q"])))
    high = float(np.quantile(deltas, float(config["bootstrap"]["ci_high_q"])))
    return low, high, "bootstrap_vs_single_feature_paired_event"


def score_quality_metrics(matrix: pd.DataFrame, policies: list[HistoryPolicy], config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    specs = [
        ("stage_1", PRIMARY_STAGE1_SCORE, PRIMARY_STAGE1_TARGET, matrix.loc[bool_series(matrix["stage_1_evaluable"])], "positive"),
        ("stage_2", PRIMARY_STAGE2_SCORE, PRIMARY_STAGE2_TARGET, matrix.loc[bool_series(matrix["stage_2_evaluable"])], "positive"),
    ]
    for stage, score_col, target_col, source, expected_sign in specs:
        for policy in policies:
            for split in SPLITS:
                frame = split_frame(source, split).dropna(subset=[score_col])
                y = bool_series(frame[target_col]).astype(int) if target_col in frame else pd.Series(dtype=int)
                score = pd.to_numeric(frame[score_col], errors="coerce")
                if len(frame) and y.nunique() == 2:
                    auc = float(roc_auc_score(y, score))
                    rank_ic = float(score.corr(y.astype(float), method="spearman"))
                else:
                    auc = np.nan
                    rank_ic = np.nan
                try:
                    decile = pd.qcut(score.rank(method="first"), 10, labels=False, duplicates="drop") + 1
                    tmp = frame.assign(decile=decile)
                    rates = tmp.groupby("decile")[target_col].apply(lambda s: bool_series(s).mean())
                    decile_lift = float(rates.iloc[-1] - rates.iloc[0]) if len(rates) >= 2 else np.nan
                    tail_bucket_rate = float(rates.iloc[-1]) if len(rates) else np.nan
                except Exception:
                    decile_lift = np.nan
                    tail_bucket_rate = np.nan
                rows.append(
                    {
                        "stage": stage,
                        "split": split,
                        "model_id": config["models"]["primary_stage_1_model_id"] if stage == "stage_1" else config["models"]["primary_stage_2_model_id"],
                        "score_id": score_col,
                        "target_id": target_col,
                        "history_policy_id": policy.history_policy_id,
                        "history_window_mode": policy.history_window_mode,
                        "trailing_history_window_sessions": policy.trailing_history_window_sessions,
                        "auc_target_id": target_col,
                        "auc_score_direction": "higher_score_higher_positive_probability",
                        "rank_ic_expected_sign": expected_sign,
                        "event_n": int(len(frame)),
                        "positive_n": int(y.sum()) if len(y) else 0,
                        "base_rate": safe_rate(int(y.sum()) if len(y) else 0, len(frame)),
                        "auc": auc,
                        "spearman_rank_ic": rank_ic,
                        "rank_ic_pvalue": np.nan,
                        "decile_lift": decile_lift,
                        "quintile_lift": decile_lift,
                        "tail_bucket_rate": tail_bucket_rate,
                        "direction_check_status": "pass" if pd.notna(rank_ic) and rank_ic > 0 else "fail",
                        "rank_quality_status": "readout",
                    }
                )
    return pd.DataFrame(rows)


def decile_lift_readout(matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    specs = [
        ("stage_1", PRIMARY_STAGE1_SCORE, PRIMARY_STAGE1_TARGET, matrix.loc[bool_series(matrix["stage_1_evaluable"])]),
        ("stage_2", PRIMARY_STAGE2_SCORE, PRIMARY_STAGE2_TARGET, matrix.loc[bool_series(matrix["stage_2_evaluable"])]),
    ]
    for stage, score_col, target_col, source in specs:
        for split in SPLITS:
            frame = split_frame(source, split).dropna(subset=[score_col]).copy()
            if frame.empty:
                continue
            frame["score_decile"] = pd.qcut(pd.to_numeric(frame[score_col], errors="coerce").rank(method="first"), 10, labels=False, duplicates="drop") + 1
            for decile, group in frame.groupby("score_decile", dropna=False):
                rows.append(
                    {
                        "stage": stage,
                        "split": split,
                        "score_decile": int(decile) if pd.notna(decile) else np.nan,
                        "event_n": int(len(group)),
                        "positive_n": int(bool_series(group[target_col]).sum()),
                        "target_rate": weighted_rate(group.assign(sample_weight=1.0), target_col),
                        "score_min": float(pd.to_numeric(group[score_col], errors="coerce").min()),
                        "score_max": float(pd.to_numeric(group[score_col], errors="coerce").max()),
                    }
                )
    return pd.DataFrame(rows)


def diagnostic_lookahead_upper_bar(matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    specs = [
        ("stage_1", PRIMARY_STAGE1_SCORE, PRIMARY_STAGE1_TARGET, matrix.loc[bool_series(matrix["stage_1_evaluable"])], float(config["primary_X_stage_1"]), True),
        ("stage_2", PRIMARY_STAGE2_SCORE, PRIMARY_STAGE2_TARGET, matrix.loc[bool_series(matrix["stage_2_evaluable"])], float(config["primary_X_stage_2"]), False),
    ]
    for stage, score_col, target_col, source, budget, low_is_good in specs:
        for rank_method in ("same_month_full_cohort_rank", "board_month_full_cohort_rank", "whole_split_rank"):
            parts = []
            group_cols = {"same_month_full_cohort_rank": ["split", "calendar_month"], "board_month_full_cohort_rank": ["split", "board_bucket", "calendar_month"], "whole_split_rank": ["split"]}[rank_method]
            for _, group in source.groupby(group_cols, dropna=False):
                group = group.sort_values([score_col, "instrument", "event_t0_date", "meta_event_id"], ascending=[low_is_good, True, True, True], kind="stable")
                parts.append(group.head(int(round(budget * len(group)))))
            selected = pd.concat(parts, ignore_index=True) if parts else source.head(0)
            for split in SPLITS:
                sub = split_frame(selected, split)
                base = split_frame(source, split)
                rows.append(
                    {
                        "stage": stage,
                        "split": split,
                        "rank_method_id": rank_method,
                        "history_policy_id": rank_method,
                        "history_window_mode": "lookahead_full_cohort",
                        "trailing_history_window_sessions": np.nan,
                        "stage1_gate_source": "lookahead_diagnostic",
                        "stage1_budget_X": float(config["primary_X_stage_1"]),
                        "stage2_budget_X": float(config["primary_X_stage_2"]) if stage == "stage_2" else np.nan,
                        "budget_tuple_role": "diagnostic_upper_bar",
                        "selected_n": int(len(sub)),
                        "selected_positive_n": int(bool_series(sub[target_col]).sum()) if len(sub) else 0,
                        "selected_budget_total": safe_rate(len(sub), len(base)),
                        "selected_budget_rank_evaluable": safe_rate(len(sub), len(base)),
                        "selected_rate": weighted_rate(sub.assign(sample_weight=1.0), target_col),
                        "base_rate": weighted_rate(base.assign(sample_weight=1.0), target_col),
                        "delta_vs_base": weighted_rate(sub.assign(sample_weight=1.0), target_col) - weighted_rate(base.assign(sample_weight=1.0), target_col)
                        if len(sub) and len(base)
                        else np.nan,
                        "lookahead_rank_upper_bar": True,
                        "not_allowed_for_decision": True,
                        "diagnostic_only_flag": True,
                    }
                )
    return pd.DataFrame(rows)


def update_primary_readout_with_comparators(
    readout: pd.DataFrame,
    primary_stage1: pd.DataFrame,
    primary_stage2: pd.DataFrame,
    random_stage1_selected: pd.DataFrame,
    random_stage2_selected: pd.DataFrame,
    single_stage1_selected: pd.DataFrame,
    single_stage2_selected: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    out = readout.copy()
    for stage, selection, random_selected, single_selected, target_col in [
        ("stage_1", primary_stage1, random_stage1_selected, single_stage1_selected, PRIMARY_STAGE1_TARGET),
        ("stage_2", primary_stage2, random_stage2_selected, single_stage2_selected, PRIMARY_STAGE2_TARGET),
    ]:
        for split in SPLITS:
            mask = out["stage"].eq(stage) & out["split"].eq(split) & out["budget_tuple_role"].eq("primary") & (~out["diagnostic_only_flag"])
            if not mask.any():
                continue
            model_selected = split_frame(selection.loc[selection["selected_flag"]], split)
            rand_split = split_frame(random_selected, split)
            random_target_col = "random_stage_1_fast_fail_target" if stage == "stage_1" else "random_stage_2_continuation_target"
            low_r, high_r, status_r = bootstrap_random_ci(
                model_selected,
                target_col,
                compare_seed_selected=rand_split,
                compare_target_col=random_target_col,
                direction="vs_random",
                config=config,
            )
            low_s, high_s, status_s = bootstrap_single_feature_paired_ci(selection, single_selected, target_col, split, config=config)
            out.loc[mask, "bootstrap_ci95_low"] = low_r
            out.loc[mask, "bootstrap_ci95_high"] = high_r
            out.loc[mask, "bootstrap_random_ci95_low"] = low_r
            out.loc[mask, "bootstrap_random_ci95_high"] = high_r
            out.loc[mask, "bootstrap_single_feature_ci95_low"] = low_s
            out.loc[mask, "bootstrap_single_feature_ci95_high"] = high_s
            out.loc[mask, "bootstrap_status"] = status_r + ";" + status_s
    return out


def evaluate_decision(readout: pd.DataFrame, score_quality: pd.DataFrame, score_reproduction_status: str, input_ok: bool, input_reasons: str, config: dict[str, Any]) -> pd.DataFrame:
    primary = readout.loc[readout["history_policy_id"].eq(config["history_policies"]["primary"]["history_policy_id"]) & readout["budget_tuple_role"].eq("primary") & (~readout["diagnostic_only_flag"])]
    q = score_quality.loc[score_quality["history_policy_id"].eq(config["history_policies"]["primary"]["history_policy_id"])]
    qidx = q.set_index(["stage", "split"]) if not q.empty else pd.DataFrame()

    def prow(stage: str, split: str) -> pd.Series:
        match = primary.loc[primary["stage"].eq(stage) & primary["split"].eq(split)]
        return match.iloc[0] if not match.empty else pd.Series(dtype=object)

    def qrow(stage: str, split: str) -> pd.Series:
        return qidx.loc[(stage, split)] if len(qidx) and (stage, split) in qidx.index else pd.Series(dtype=object)

    s1 = prow("stage_1", "robustness")
    s2 = prow("stage_2", "robustness")
    s1_train_q = qrow("stage_1", "train")
    s1_rob_q = qrow("stage_1", "robustness")
    s2_train_q = qrow("stage_2", "train")
    s2_rob_q = qrow("stage_2", "robustness")
    g = config["gates"]
    rank_quality_s1 = bool(
        pd.notna(s1_rob_q.get("auc", np.nan))
        and float(s1_rob_q.get("auc", np.nan)) >= float(g["stage1_auc_robustness_min"])
        and float(s1_train_q.get("spearman_rank_ic", -np.inf)) > 0
        and float(s1_rob_q.get("spearman_rank_ic", -np.inf)) > 0
        and float(s1_rob_q.get("decile_lift", -np.inf)) > 0
    )
    rank_quality_s2 = bool(
        pd.notna(s2_rob_q.get("auc", np.nan))
        and float(s2_rob_q.get("auc", np.nan)) >= float(g["stage2_auc_robustness_min"])
        and float(s2_train_q.get("spearman_rank_ic", -np.inf)) > 0
        and float(s2_rob_q.get("spearman_rank_ic", -np.inf)) > 0
        and float(s2_rob_q.get("decile_lift", -np.inf)) > 0
    )
    stage1_supported = bool(
        input_ok
        and score_reproduction_status in {"frozen_row_level_scores", "pass_exact", "pass_near_miss"}
        and rank_quality_s1
        and int(s1.get("selected_n", 0)) >= int(g["headline_split_min_selected_n"])
        and float(s1.get("delta_vs_random_p50", np.inf)) <= float(g["stage1_delta_vs_random_p50_max"])
        and float(s1.get("delta_vs_single_feature", np.inf)) <= float(g["stage1_delta_vs_single_feature_max"])
        and float(s1.get("bootstrap_random_ci95_high", np.inf)) < 0
        and float(s1.get("bootstrap_single_feature_ci95_high", np.inf)) < 0
    )
    stage2_supported = bool(
        stage1_supported
        and rank_quality_s2
        and int(s2.get("selected_n", 0)) >= int(g["stage2_headline_min_selected_n"])
        and float(s2.get("delta_vs_random_p50", -np.inf)) >= float(g["stage2_delta_vs_random_p50_min"])
        and float(s2.get("delta_vs_single_feature", -np.inf)) >= float(g["stage2_delta_vs_single_feature_min"])
        and float(s2.get("bootstrap_random_ci95_low", -np.inf)) > 0
        and float(s2.get("bootstrap_single_feature_ci95_low", -np.inf)) > 0
    )
    stage1_beats_random = pd.notna(s1.get("delta_vs_random_p50", np.nan)) and float(s1.get("delta_vs_random_p50", np.inf)) < 0
    stage2_not_collapsed = pd.notna(s2.get("delta_vs_random_p50", np.nan)) and float(s2.get("delta_vs_random_p50", -np.inf)) >= 0
    if not input_ok:
        decision_state = "12A7_blocked_input_or_pit_failure"
    elif score_reproduction_status == "fail":
        decision_state = "12A7_blocked_score_source_failure"
    elif stage1_supported and stage2_supported:
        decision_state = "12A7_trailing_rank_supported"
    elif stage1_supported and stage2_not_collapsed:
        decision_state = "12A7_stage1_trailing_rank_supported_stage2_partial"
    elif (stage1_beats_random and float(s1.get("delta_vs_single_feature", np.inf)) > 0) or (
        pd.notna(s2.get("delta_vs_single_feature", np.nan)) and float(s2.get("delta_vs_single_feature", -np.inf)) < 0
    ):
        decision_state = "12A7_simple_backbone_supported_complex_model_not_supported"
    elif rank_quality_s1 or rank_quality_s2:
        decision_state = "12A7_rank_signal_diagnostic_only"
    else:
        decision_state = "12A7_no_rank_transport"
    if decision_state == "12A7_trailing_rank_supported":
        next_allowed = "requirement_12a8_probability_calibration_prior_shift_audit.md"
        followup = ""
    elif decision_state == "12A7_no_rank_transport" or decision_state == "12A7_rank_signal_diagnostic_only":
        next_allowed = "requirement_12a9_vol_scaled_label_stability_and_separability_audit.md"
        followup = ""
    elif decision_state == "12A7_stage1_trailing_rank_supported_stage2_partial":
        next_allowed = "none"
        followup = "12A7b_stage2_trailing_rank_or_backbone_revision"
    elif decision_state == "12A7_simple_backbone_supported_complex_model_not_supported":
        next_allowed = "none"
        followup = "12A7b_simple_backbone_operating_rule_validation"
    else:
        next_allowed = "none"
        followup = ""
    reasons = []
    if not input_ok:
        reasons.append("input_gate_failed" + (f":{input_reasons}" if input_reasons else ""))
    if score_reproduction_status == "fail":
        reasons.append("score_source_failure")
    if not rank_quality_s1:
        reasons.append("stage1_rank_quality_gate_failed")
    if not rank_quality_s2:
        reasons.append("stage2_rank_quality_gate_failed")
    if not stage1_supported:
        reasons.append("stage1_support_gate_failed")
    if stage1_supported and not stage2_supported:
        reasons.append("stage2_support_gate_failed")
    return pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "input_gate_status": "pass" if input_ok else "fail",
                "score_reproduction_status": score_reproduction_status,
                "pit_gate_status": "pass" if input_ok else "fail",
                "stage_1_status": "supported" if stage1_supported else ("rank_signal_or_partial" if rank_quality_s1 else "failed"),
                "stage_2_status": "supported" if stage2_supported else ("partial" if stage1_supported and stage2_not_collapsed else "failed"),
                "primary_history_policy_id": config["history_policies"]["primary"]["history_policy_id"],
                "primary_history_window_mode": config["history_policies"]["primary"]["history_window_mode"],
                "primary_trailing_history_window_sessions": config["history_policies"]["primary"]["trailing_history_window_sessions"],
                "primary_budget_X_stage_1": float(config["primary_X_stage_1"]),
                "primary_budget_X_stage_2": float(config["primary_X_stage_2"]),
                "stage_1_model_id": config["models"]["primary_stage_1_model_id"],
                "stage_1_score_id": PRIMARY_STAGE1_SCORE,
                "stage_1_gate_source": "primary_model_trailing_rank_keep",
                "score_source_mode": "",
                "score_source_caveat": "",
                "stage_1_robustness_selected_n": s1.get("selected_n", np.nan),
                "stage_1_robustness_selected_positive_n": s1.get("selected_positive_n", np.nan),
                "stage_1_robustness_fast_fail_rate": s1.get("selected_rate", np.nan),
                "stage_1_robustness_random_p50": s1.get("random_p50", np.nan),
                "stage_1_robustness_single_feature_rate": s1.get("single_feature_selected_rate", np.nan),
                "stage_1_robustness_budget": s1.get("selected_budget_total", np.nan),
                "stage_1_robustness_budget_rank_evaluable": s1.get("selected_budget_rank_evaluable", np.nan),
                "stage_2_model_id": config["models"]["primary_stage_2_model_id"],
                "stage_2_score_id": PRIMARY_STAGE2_SCORE,
                "stage_2_stage1_gate_source": "primary_model_trailing_rank_keep",
                "stage_2_robustness_selected_n": s2.get("selected_n", np.nan),
                "stage_2_robustness_selected_positive_n": s2.get("selected_positive_n", np.nan),
                "stage_2_robustness_continuation_rate": s2.get("selected_rate", np.nan),
                "stage_2_robustness_random_p50": s2.get("random_p50", np.nan),
                "stage_2_robustness_single_feature_rate": s2.get("single_feature_selected_rate", np.nan),
                "stage_2_robustness_budget": s2.get("selected_budget_total", np.nan),
                "stage_2_robustness_budget_rank_evaluable": s2.get("selected_budget_rank_evaluable", np.nan),
                "gate_failure_reasons": ";".join(reasons),
                "next_allowed_requirement": next_allowed,
                "recommended_internal_followup": followup,
            }
        ]
    )


def fmt(value: Any) -> str:
    return "NA" if pd.isna(value) else f"{float(value):.4f}"


def build_report(decision: pd.DataFrame, readout: pd.DataFrame, quality: pd.DataFrame, budget_drift: pd.DataFrame, single: pd.DataFrame, lookahead: pd.DataFrame) -> str:
    d = decision.iloc[0]
    primary = readout.loc[readout["history_policy_id"].eq(d["primary_history_policy_id"]) & readout["budget_tuple_role"].eq("primary") & (~readout["diagnostic_only_flag"])]
    q = quality.loc[quality["history_policy_id"].eq(d["primary_history_policy_id"])].set_index(["stage", "split"])
    s1 = primary.loc[primary["stage"].eq("stage_1") & primary["split"].eq("robustness")].iloc[0] if not primary.loc[primary["stage"].eq("stage_1") & primary["split"].eq("robustness")].empty else pd.Series(dtype=object)
    s2 = primary.loc[primary["stage"].eq("stage_2") & primary["split"].eq("robustness")].iloc[0] if not primary.loc[primary["stage"].eq("stage_2") & primary["split"].eq("robustness")].empty else pd.Series(dtype=object)
    s1q = q.loc[("stage_1", "robustness")] if ("stage_1", "robustness") in q.index else pd.Series(dtype=object)
    s2q = q.loc[("stage_2", "robustness")] if ("stage_2", "robustness") in q.index else pd.Series(dtype=object)
    return f"""
# 12A7 Direction A trailing-rank operating point audit 报告

## 结论

- final decision: `{d['decision_state']}`
- input gate: `{d['input_gate_status']}`
- score reproduction: `{d['score_reproduction_status']}`
- stage-1 status: `{d['stage_1_status']}`
- stage-2 status: `{d['stage_2_status']}`
- next allowed requirement: `{d['next_allowed_requirement']}`
- failure reasons: `{d['gate_failure_reasons']}`

## 为什么不是 no signal

12A6c 的失败主要来自 absolute probability threshold transport：train 上冻结的概率阈值在 OOS base-rate 下改变了实际预算。12A7 不再问“train 概率切点能否迁移”，而是问同一个 score 的横截面 / 时序 rank 是否能迁移。

本次 headline operating point 是 PIT `board_then_global_rolling_504_sessions`：当前事件只和当前 decision position 之前、504 session 窗口内的历史事件比较；同 board history 不足时才回退到 global history。whole-month / whole-split rank 仅作为 diagnostic look-ahead upper bar，不进入 gate。

## Rank quality

- stage-1 robustness AUC: {fmt(s1q.get('auc', np.nan))}，rank-IC: {fmt(s1q.get('spearman_rank_ic', np.nan))}，decile lift: {fmt(s1q.get('decile_lift', np.nan))}
- stage-2 robustness AUC: {fmt(s2q.get('auc', np.nan))}，rank-IC: {fmt(s2q.get('spearman_rank_ic', np.nan))}，decile lift: {fmt(s2q.get('decile_lift', np.nan))}

## Primary tuple robustness 读数

Stage-1 `(X=0.50)`:

- denominator_n: {int(s1.get('denominator_n', 0))}
- rank_evaluable_n: {int(s1.get('rank_evaluable_n', 0))}
- selected_n: {int(s1.get('selected_n', 0))}
- actual budget total: {fmt(s1.get('selected_budget_total', np.nan))}
- fast-fail rate: {fmt(s1.get('selected_rate', np.nan))}
- random p50: {fmt(s1.get('random_p50', np.nan))}
- delta vs random p50: {fmt(s1.get('delta_vs_random_p50', np.nan))}
- single-feature rate: {fmt(s1.get('single_feature_selected_rate', np.nan))}
- delta vs single-feature: {fmt(s1.get('delta_vs_single_feature', np.nan))}

Stage-2 `(stage1_X=0.50, stage2_X=0.50)`:

- denominator_n: {int(s2.get('denominator_n', 0))}
- rank_evaluable_n: {int(s2.get('rank_evaluable_n', 0))}
- selected_n: {int(s2.get('selected_n', 0))}
- actual budget total: {fmt(s2.get('selected_budget_total', np.nan))}
- continuation rate: {fmt(s2.get('selected_rate', np.nan))}
- random p50: {fmt(s2.get('random_p50', np.nan))}
- delta vs random p50: {fmt(s2.get('delta_vs_random_p50', np.nan))}
- single-feature rate: {fmt(s2.get('single_feature_selected_rate', np.nan))}
- delta vs single-feature: {fmt(s2.get('delta_vs_single_feature', np.nan))}

## Findings

1. rolling-rank rule 把 12A6c 的“绝对阈值预算漂移”改成显式 readout，而不是假设 50% by construction。需要同时看 `selected_budget_total` 和 `selected_budget_rank_evaluable`，因为 min-history 不足会真实造成 abstention。
2. stage-1 的主问题是能否在 robustness 同时打赢 random 和 single-feature。random 只证明不是随机；single-feature 才是防御型 backbone 的最低门槛。
3. stage-2 random baseline 已先通过 random stage-1 keep，因此 continuation delta 不再把 model-kept survivor 和 all-random survivor 混在一起比较。
4. single-feature challenger 使用 common-denominator matched-selected-n replay，因此 model-vs-single 的 delta 不再被实际预算差异污染。

## 后续

若 decision 是 `12A7_trailing_rank_supported`，下一步是 12A8 calibration / prior-shift audit，用来解释 rank 可迁移但 absolute threshold 不可迁移的概率刻度问题。若落入 simple-backbone 或 diagnostic-only，则应优先把单特征 backbone / vol-scaled label 作为后续。
""".strip()


def build_manifest(paths: dict[str, Path], frames: dict[str, pd.DataFrame], decision: pd.DataFrame, config_path: Path, requirement_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    outputs = {}
    output_hashes = {}
    for key, path in paths.items():
        if key == "manifest" or not path.exists() or not path.is_file():
            continue
        output_hashes[key] = path_sha(path)
        outputs[key] = {
            "path": str(path),
            "sha256": output_hashes[key],
            "row_count": int(len(frames[key])) if key in frames else np.nan,
        }
    inputs = {}
    input_hashes = {}
    if "input_artifact_audit" in frames:
        for row in frames["input_artifact_audit"].itertuples(index=False):
            artifact_id = str(row.artifact_id)
            sha = str(getattr(row, "sha256", "") or "")
            input_hashes[artifact_id] = sha
            inputs[artifact_id] = {
                "path": str(getattr(row, "path", "")),
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
        "local_cache_hashes": {
            key: sha for key, sha in output_hashes.items() if str(paths.get(key, "")).startswith(str(LOCAL_CACHE_DIR))
        },
    }


def run_pipeline(config_path: Path, mode: str = "full") -> int:
    config = load_yaml(config_path)
    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    paths = output_paths()
    audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], audit)
    decision_12a6c = read_table(resolved["two_stage_decision"]) if resolved["two_stage_decision"].exists() else pd.DataFrame()
    ok, reasons = input_gate_pass(audit, decision_12a6c)
    if mode == "check-inputs":
        if not ok:
            raise RuntimeError(f"12A7 input check failed: {reasons}")
        print(f"{RUN_ID}: input audit ok ({len(audit)} artifacts)")
        return 0
    if not ok:
        raise RuntimeError(f"12A7 required inputs missing or invalid: {reasons}")

    matrix, feature_meta, source_meta = build_score_source(resolved, config)
    score_repro = build_score_reproduction_audit(matrix, resolved, config, source_meta)
    score_status, score_caveat = worst_score_status(score_repro)
    if score_status == "fail":
        raise RuntimeError("12A7 score reproduction failed")

    policies = history_policies(config)
    primary_policy = policies[0]
    budget_grid = [float(x) for x in config["budget_grid"]]
    primary_s1_budget = float(config["primary_X_stage_1"])
    primary_s2_budget = float(config["primary_X_stage_2"])

    stage1_selections: dict[tuple[str, float], pd.DataFrame] = {}
    stage2_selections: dict[tuple[str, float, float], pd.DataFrame] = {}
    readouts = []
    drift = []
    for policy in policies:
        for b1 in budget_grid:
            s1 = apply_stage1_rank(matrix, policy, b1, config)
            stage1_selections[(policy.history_policy_id, b1)] = s1
            readouts.append(readout_rows_for_selection(s1, "stage_1", PRIMARY_STAGE1_TARGET, PRIMARY_STAGE1_SCORE, config))
            drift.append(budget_drift_rows(s1, "stage_1"))
        # Stage-2 headline/chained curve uses the primary stage-1 budget. Other stage-1 budgets are diagnostic paired-grid rows.
        for b1 in budget_grid:
            for b2 in budget_grid:
                if b1 != primary_s1_budget and b2 != primary_s2_budget:
                    continue
                s1_source = stage1_selections[(policy.history_policy_id, b1)]
                s2 = apply_stage2_rank(matrix, s1_source, policy, b1, b2, config)
                role = classify_budget_tuple("stage_2", b1, b2, config)
                if role == "paired_grid_diagnostic":
                    s2["diagnostic_only_flag"] = True
                stage2_selections[(policy.history_policy_id, b1, b2)] = s2
                readouts.append(readout_rows_for_selection(s2, "stage_2", PRIMARY_STAGE2_TARGET, PRIMARY_STAGE2_SCORE, config))
                drift.append(budget_drift_rows(s2, "stage_2"))
    operating = pd.concat(readouts, ignore_index=True)
    budget_drift = pd.concat(drift, ignore_index=True)

    random_labels, random_path_audit = prepare_random_labels(resolved)
    primary_stage1 = stage1_selections[(primary_policy.history_policy_id, primary_s1_budget)]
    primary_stage2 = stage2_selections[(primary_policy.history_policy_id, primary_s1_budget, primary_s2_budget)]
    random_stage1_selected_by_key: dict[tuple[str, float], pd.DataFrame] = {}
    random_stage1_audit_by_key: dict[tuple[str, float], pd.DataFrame] = {}
    random_stage2_selected_by_key: dict[tuple[str, float, float], pd.DataFrame] = {}
    random_audit_frames = []
    random_quant_frames = []
    for (policy_id, b1), selection in stage1_selections.items():
        if policy_id != primary_policy.history_policy_id:
            continue
        selected, audit_frame, quant = stage1_random_baseline(random_labels, selection, config)
        random_stage1_selected_by_key[(policy_id, b1)] = selected
        random_stage1_audit_by_key[(policy_id, b1)] = audit_frame
        random_audit_frames.append(audit_frame)
        random_quant_frames.append(quant)
    for (policy_id, b1, b2), selection in stage2_selections.items():
        if policy_id != primary_policy.history_policy_id:
            continue
        s1_source = stage1_selections[(policy_id, b1)]
        selected, audit_frame, quant = stage2_random_baseline(
            random_labels,
            s1_source,
            selection,
            config,
            random_stage1_keep=random_stage1_selected_by_key[(policy_id, b1)],
            stage1_audit=random_stage1_audit_by_key[(policy_id, b1)],
        )
        random_stage2_selected_by_key[(policy_id, b1, b2)] = selected
        random_audit_frames.append(audit_frame)
        random_quant_frames.append(quant)
    random_audit = pd.concat(random_audit_frames, ignore_index=True) if random_audit_frames else pd.DataFrame()
    random_quant = pd.concat(random_quant_frames, ignore_index=True) if random_quant_frames else pd.DataFrame()
    operating = merge_random_into_readout(operating, random_quant)
    random_stage1_selected = random_stage1_selected_by_key[(primary_policy.history_policy_id, primary_s1_budget)]
    random_stage2_selected = random_stage2_selected_by_key[(primary_policy.history_policy_id, primary_s1_budget, primary_s2_budget)]

    feature_config = config["single_feature_challenger"]
    s1_best_feature, s1_orientation, s1_feature_ranked = choose_single_feature(
        primary_stage1,
        dict(feature_config["stage_1_candidates"]),
        PRIMARY_STAGE1_TARGET,
        primary_policy,
        "stage_1",
        primary_s1_budget,
        maximize=False,
        config=config,
    )
    s1_single_selected, s1_single = matched_single_feature_replay(primary_stage1, s1_feature_ranked, s1_best_feature, s1_orientation, "stage_1", PRIMARY_STAGE1_TARGET, config)
    s2_best_feature, s2_orientation, s2_feature_ranked = choose_single_feature(
        primary_stage2,
        dict(feature_config["stage_2_candidates"]),
        PRIMARY_STAGE2_TARGET,
        primary_policy,
        "stage_2",
        primary_s2_budget,
        maximize=True,
        config=config,
    )
    s2_single_selected, s2_single = matched_single_feature_replay(primary_stage2, s2_feature_ranked, s2_best_feature, s2_orientation, "stage_2", PRIMARY_STAGE2_TARGET, config)
    single_feature = pd.concat([s1_single, s2_single], ignore_index=True)
    operating = add_single_feature_to_readout(operating, s1_single, "stage_1")
    operating = add_single_feature_to_readout(operating, s2_single, "stage_2")
    operating = update_primary_readout_with_comparators(
        operating,
        primary_stage1,
        primary_stage2,
        random_stage1_selected,
        random_stage2_selected,
        s1_single_selected,
        s2_single_selected,
        config,
    )

    quality = score_quality_metrics(matrix, policies, config)
    decile = decile_lift_readout(matrix, config)
    lookahead = diagnostic_lookahead_upper_bar(matrix, config)
    budget_curve = operating.loc[operating["budget_tuple_role"].isin(["stage_1_curve", "stage_2_chained_curve", "primary"])].copy()
    split_audit = read_table(resolved["split_time_boundary_audit"])
    decision = evaluate_decision(operating, quality, score_status, ok, reasons, config)
    decision.loc[:, "score_source_mode"] = source_meta["score_source_mode"]
    decision.loc[:, "score_source_caveat"] = score_caveat

    score_cols = [
        "meta_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "split",
        "board_bucket",
        "calendar_month",
        "stage_2_decision_pos",
        PRIMARY_STAGE1_SCORE,
        PRIMARY_STAGE2_SCORE,
        PRIMARY_STAGE1_TARGET,
        PRIMARY_STAGE2_TARGET,
        "score_source_mode",
        "score_source_caveat",
        "stage_1_model_id",
        "stage_2_model_id",
        "stage_1_feature_order_hash",
        "stage_2_feature_order_hash",
        "stage_1_train_imputation_median_hash",
        "stage_2_train_imputation_median_hash",
    ]
    score_matrix = matrix[[col for col in score_cols if col in matrix.columns]].copy()

    frames = {
        "input_artifact_audit": audit,
        "score_reproduction_audit": score_repro,
        "random_path_label_audit": random_path_audit,
        "score_quality": quality,
        "operating_readout": operating,
        "budget_drift": budget_drift,
        "random_audit": random_audit,
        "single_feature": single_feature,
        "decile_lift": decile,
        "budget_curve": budget_curve,
        "lookahead_upper_bar": lookahead,
        "decision": decision,
        "split_time_boundary_audit": split_audit,
        "score_matrix": score_matrix,
    }
    for key, frame in frames.items():
        if key in paths:
            write_df(paths[key], frame)
    report = build_report(decision, operating, quality, budget_drift, single_feature, lookahead)
    write_text(paths["report"], report)
    frames["report"] = pd.DataFrame([{"report_path": str(paths["report"])}])
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"], config))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pipeline(Path(args.config), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

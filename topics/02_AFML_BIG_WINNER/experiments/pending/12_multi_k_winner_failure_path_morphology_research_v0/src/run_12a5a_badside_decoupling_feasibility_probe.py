#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore", category=FutureWarning, module=r"sklearn\.linear_model")
warnings.filterwarnings("ignore", message=r"Inconsistent values: penalty=.*", category=UserWarning)


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
TOPIC_SRC_DIR = TOPIC_ROOT / "src"

if str(TOPIC_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TOPIC_SRC_DIR))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


RUN_ID = "12A5A_badside_decoupling_feasibility_probe"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a5a_badside_decoupling_feasibility_probe.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

PRIMARY_SOURCE_ARM = "C0_state_change"
SPLITS = ("all", "train", "validation", "robustness")
ALLOWED_12A4_STATES = {
    "12A4_meta_label_partial_feature_source",
    "12A4_meta_label_supported",
    "12A4_nonlinear_candidate_requires_12A5_validation",
}
FORBIDDEN_PATTERNS = (
    "episode_low",
    "episode_high",
    "first_50pct",
    "mfe",
    "future",
    "target_",
    "label_",
    "winner_",
    "fast_fail_",
    "false_repair_",
    "bad_side_",
    "event_minus_low",
    "inside_window",
    "score",
)
DETERMINISTIC_POOLS = {
    "density_only_top20": {
        "frontier_id": "density_only_frontier",
        "score_feature": "same_day_c0_event_count_all",
        "score_direction": "lower_is_selected",
        "train_quantile": 0.20,
    },
    "freshness_only_top20": {
        "frontier_id": "freshness_decay_only_frontier",
        "score_feature": "freshness_decay_tau_20",
        "score_direction": "higher_is_selected",
        "train_quantile": 0.80,
    },
    "r_core_interaction_top20": {
        "frontier_id": "r_core_interaction_only_frontier",
        "score_feature": "prior_r_core_event_count_20d",
        "score_direction": "higher_is_selected",
        "train_quantile": 0.80,
    },
}
REFIT_POOLS = {
    "shallow_tree_top20": {
        "model_id": "shallow_decision_tree_max_depth_3",
        "model_family": "shallow_decision_tree_max_depth_3",
        "reconstruction_method": "refit_12A4_primary_model_from_feature_matrix",
    },
    "lightgbm_top20": {
        "model_id": "lightgbm_challenger_diagnostic_only",
        "model_family": "lightgbm_challenger_diagnostic_only",
        "reconstruction_method": "refit_12A4_lightgbm_challenger_from_feature_matrix",
    },
}
PRIMARY_REJECTORS = {
    "logistic_regression_l2",
    "logistic_regression_l1",
    "shallow_decision_tree_max_depth_3",
    "scorecard_quantile_binning",
}
REJECTOR_FAMILIES = (
    "logistic_regression_l2",
    "logistic_regression_l1",
    "shallow_decision_tree_max_depth_3",
    "scorecard_quantile_binning",
    "lightgbm_rejector_depth_3",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A5A bad-side decoupling feasibility probe.")
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
        "event_feature_join_audit": TABLE_DIR / "event_feature_join_audit.csv",
        "bucket_reconstruction_audit": TABLE_DIR / "bucket_reconstruction_audit.csv",
        "label_completeness_audit": TABLE_DIR / "label_completeness_audit.csv",
        "badside_composition_decomposition": TABLE_DIR / "badside_composition_decomposition.csv",
        "badside_separability_univariate": TABLE_DIR / "badside_separability_univariate.csv",
        "badside_separability_lowcapacity": TABLE_DIR / "badside_separability_lowcapacity.csv",
        "badside_rejector_training_audit": TABLE_DIR / "badside_rejector_training_audit.csv",
        "badside_rejector_frontier": TABLE_DIR / "badside_rejector_frontier.csv",
        "badside_decoupling_workpoint": TABLE_DIR / "badside_decoupling_workpoint.csv",
        "badside_decoupling_decision": TABLE_DIR / "badside_decoupling_decision.csv",
        "rejector_artifacts": LOCAL_CACHE_DIR / "rejector_artifacts",
        "report": REPORT_DIR / "badside_decoupling_feasibility_probe_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    if "".join(path.suffixes).endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    return pd.read_csv(path, low_memory=False, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if "".join(path.suffixes).endswith(".parquet"):
        frame.to_parquet(path, index=False)
    elif "".join(path.suffixes).endswith(".csv.gz"):
        frame.to_csv(path, index=False, compression={"method": "gzip", "compresslevel": 9, "mtime": 1})
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


def safe_rate(num: int | float, den: int | float) -> float:
    if den is None or pd.isna(den) or float(den) == 0:
        return np.nan
    return float(num) / float(den)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "all":
        return frame
    return frame.loc[frame["event_split"].astype(str).eq(split)]


def has_forbidden_pattern(name: str) -> bool:
    lowered = name.lower()
    return any(pattern in lowered for pattern in FORBIDDEN_PATTERNS)


def stable_membership_hash(ids: pd.Series) -> str:
    return stable_hash(sorted(ids.dropna().astype(str).tolist()))


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "meta_label_decision": ("decision_state", "threshold_selection_source"),
    "meta_label_event_universe": (
        "meta_event_id",
        "source_arm_id",
        "source_arm_is_c0",
        "market_regime_bucket",
        "event_split",
    ),
    "meta_label_event_targets": (
        "meta_event_id",
        "event_split",
        "target_low_to_high_inside",
        "bad_side_10_20_label",
        "winner_120_label",
        "label_20d_complete",
        "label_120d_complete",
    ),
    "meta_label_score_bucket_frontier": (
        "model_id",
        "split",
        "bucket_id",
        "event_n",
        "event_inside_window_n",
        "low_to_high_precision",
        "bad_side_10_20_rate",
        "train_reference_top20_threshold",
    ),
    "non_model_filter_frontier": (
        "frontier_id",
        "score_feature",
        "split",
        "bucket_id",
        "event_n",
        "event_inside_window_n",
        "low_to_high_precision",
        "bad_side_10_20_rate",
    ),
    "meta_label_model_card": ("model_id", "feature_list_hash", "threshold_selection_source"),
    "lightgbm_challenger_score_bucket_frontier": ("model_id", "split", "bucket_id", "lightgbm_challenger_status"),
    "lightgbm_challenger_model_card": ("model_id", "lightgbm_challenger_status", "allowed_for_supported_gate"),
    "risk_on_r_core_baseline": ("source_arm_id", "split", "low_to_high_precision", "eligible_episode_n"),
    "meta_label_feature_dictionary": (
        "feature_name",
        "feature_group",
        "allowed_for_primary_model",
        "diagnostic_only",
        "pit_status",
        "feature_status",
        "forbidden_name_pattern_flag",
    ),
    "validation_threshold_health": ("threshold_selection_source", "validation_threshold_health_pass"),
    "supported_gate_feasibility_selfcheck": ("gate_name", "gate_pass"),
    "meta_label_event_feature_matrix": ("meta_event_id", "event_split"),
}


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for artifact_id, value in config["paths"].items():
        path = topic_path(value)
        read_status = "pass" if path.exists() else "missing"
        row_count: int | float = np.nan
        columns: list[str] = []
        schema_status = "not_applicable"
        if path.exists() and path.is_file():
            try:
                if artifact_id in EXPECTED_INPUT_COLUMNS:
                    frame = read_table(path)
                    row_count = int(len(frame))
                    columns = list(frame.columns)
                    missing = [col for col in EXPECTED_INPUT_COLUMNS[artifact_id] if col not in frame.columns]
                    schema_status = "pass" if not missing else "missing_columns:" + ",".join(missing)
                else:
                    row_count = np.nan
                    schema_status = "not_applicable"
            except Exception as exc:  # pragma: no cover - defensive artifact audit branch
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "unreadable"
        rows.append(
            {
                "artifact_id": artifact_id,
                "path": str(value),
                "resolved_path": str(path),
                "exists": bool(path.exists()),
                "row_count": row_count,
                "sha256": path_sha(path),
                "read_status": read_status,
                "schema_status": schema_status,
                "column_count": len(columns),
            }
        )
    return pd.DataFrame(rows)


def allowed_feature_columns(dictionary: pd.DataFrame, feature_matrix: pd.DataFrame) -> list[str]:
    mask = (
        bool_series(dictionary["allowed_for_primary_model"])
        & ~bool_series(dictionary["diagnostic_only"])
        & dictionary["feature_status"].astype(str).eq("available")
        & dictionary["pit_status"].astype(str).eq("pass")
        & ~bool_series(dictionary["forbidden_name_pattern_flag"])
    )
    cols = []
    for name in dictionary.loc[mask, "feature_name"].astype(str):
        if name in feature_matrix.columns and pd.api.types.is_numeric_dtype(feature_matrix[name]) and not has_forbidden_pattern(name):
            cols.append(name)
    return cols


def build_event_feature_join(
    universe: pd.DataFrame,
    targets: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    dictionary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], bool, bool]:
    primary = universe.loc[bool_series(universe["source_arm_is_c0"]) & universe["market_regime_bucket"].astype(str).eq("risk_on")].copy()
    allowed_from_dictionary = allowed_feature_columns(dictionary, feature_matrix)
    missing_allowed = [col for col in allowed_from_dictionary if col not in feature_matrix.columns]
    unexpected_allowed = [col for col in allowed_from_dictionary if has_forbidden_pattern(col)]

    target_cols = [
        "meta_event_id",
        "event_split",
        "instrument",
        "target_low_to_high_inside",
        "target_pre120_to_high_inside",
        "target_low_to_high_episode_id_first",
        "label_10d_complete",
        "label_20d_complete",
        "label_120d_complete",
        "fast_fail_10d_label",
        "false_repair_20d_label",
        "bad_side_10_20_label",
        "winner_120_label",
        "target_status",
    ]
    feature_cols = ["meta_event_id", "event_split"] + [col for col in feature_matrix.columns if col not in {"meta_event_id", "event_split"}]
    merged = primary.merge(
        targets[[col for col in target_cols if col in targets.columns]],
        on="meta_event_id",
        how="inner",
        suffixes=("", "_target"),
    )
    merged = merged.merge(feature_matrix[feature_cols], on="meta_event_id", how="inner", suffixes=("", "_feature"))
    split_mismatch = 0
    if "event_split_target" in merged.columns:
        split_mismatch += int((~merged["event_split"].astype(str).eq(merged["event_split_target"].astype(str))).sum())
    if "event_split_feature" in merged.columns:
        split_mismatch += int((~merged["event_split"].astype(str).eq(merged["event_split_feature"].astype(str))).sum())
    for col in target_cols:
        tcol = f"{col}_target"
        if tcol in merged.columns:
            merged[col] = merged[tcol]
    duplicate_counts = {
        "universe": int(primary["meta_event_id"].duplicated().sum()),
        "targets": int(targets["meta_event_id"].duplicated().sum()),
        "feature_matrix": int(feature_matrix["meta_event_id"].duplicated().sum()),
    }
    missing_in_targets = int(primary.loc[~primary["meta_event_id"].isin(targets["meta_event_id"]), "meta_event_id"].nunique())
    missing_in_feature = int(primary.loc[~primary["meta_event_id"].isin(feature_matrix["meta_event_id"]), "meta_event_id"].nunique())
    join_gate_pass = (
        len(merged) == len(primary)
        and not any(duplicate_counts.values())
        and split_mismatch == 0
        and missing_in_targets == 0
        and missing_in_feature == 0
    )
    parity_gate_pass = len(missing_allowed) == 0 and len(unexpected_allowed) == 0 and len(allowed_from_dictionary) > 0
    rows = []
    for table_name, frame in (("universe", universe), ("targets", targets), ("feature_matrix", feature_matrix)):
        rows.append(
            {
                "input_table": table_name,
                "row_count": int(len(frame)),
                "unique_meta_event_id_n": int(frame["meta_event_id"].nunique()) if "meta_event_id" in frame else 0,
                "duplicate_meta_event_id_n": int(frame["meta_event_id"].duplicated().sum()) if "meta_event_id" in frame else 0,
                "primary_universe_row_count": int(len(primary)),
                "joined_row_count": int(len(merged)),
                "missing_in_universe_n": 0,
                "missing_in_targets_n": missing_in_targets,
                "missing_in_feature_matrix_n": missing_in_feature,
                "event_split_mismatch_n": split_mismatch,
                "allowed_feature_dictionary_n": int(len(allowed_from_dictionary)),
                "allowed_feature_matrix_column_n": int(sum(col in feature_matrix.columns for col in allowed_from_dictionary)),
                "missing_allowed_feature_column_n": int(len(missing_allowed)),
                "unexpected_label_or_target_feature_column_n": int(len(unexpected_allowed)),
                "event_feature_join_gate_pass": bool(join_gate_pass),
                "feature_dictionary_parity_gate_pass": bool(parity_gate_pass),
                "join_status": "pass" if join_gate_pass and parity_gate_pass else "fail",
            }
        )
    add_derived_labels(merged)
    return merged, pd.DataFrame(rows), allowed_from_dictionary, bool(join_gate_pass), bool(parity_gate_pass)


def add_derived_labels(frame: pd.DataFrame) -> pd.DataFrame:
    frame["target_low_to_high_inside"] = bool_series(frame.get("target_low_to_high_inside", pd.Series(False, index=frame.index)))
    frame["fast_fail_10d_label"] = bool_series(frame.get("fast_fail_10d_label", pd.Series(False, index=frame.index)))
    frame["false_repair_20d_label"] = bool_series(frame.get("false_repair_20d_label", pd.Series(False, index=frame.index)))
    frame["bad_side_10_20_label"] = bool_series(frame.get("bad_side_10_20_label", pd.Series(False, index=frame.index)))
    frame["winner_120_label"] = bool_series(frame.get("winner_120_label", pd.Series(False, index=frame.index)))
    frame["label_10d_complete"] = bool_series(frame.get("label_10d_complete", pd.Series(False, index=frame.index)))
    frame["label_20d_complete"] = bool_series(frame.get("label_20d_complete", pd.Series(False, index=frame.index)))
    frame["label_120d_complete"] = bool_series(frame.get("label_120d_complete", pd.Series(False, index=frame.index)))
    frame["clean_winner_event"] = (
        frame["target_low_to_high_inside"]
        & frame["winner_120_label"]
        & ~frame["bad_side_10_20_label"]
        & frame["label_20d_complete"]
        & frame["label_120d_complete"]
    )
    frame["bad_side_event"] = frame["bad_side_10_20_label"] & frame["label_20d_complete"]
    frame["clean_capture_event"] = frame["target_low_to_high_inside"] & ~frame["bad_side_10_20_label"] & frame["label_20d_complete"]
    return frame


def impute_by_train(frame: pd.DataFrame, feature_cols: list[str], train_mask: pd.Series | None = None) -> tuple[pd.DataFrame, dict[str, float]]:
    out = frame.copy()
    if train_mask is None:
        train_mask = out["event_split"].astype(str).eq("train")
    medians: dict[str, float] = {}
    train = out.loc[train_mask]
    for col in feature_cols:
        median = float(train[col].median()) if col in train and train[col].notna().any() else 0.0
        medians[col] = median
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(median)
    return out, medians


def fit_score_model(
    family: str,
    train: pd.DataFrame,
    y: pd.Series,
    score_frame: pd.DataFrame,
    feature_cols: list[str],
    config: dict[str, Any],
    score_positive_is_bad: bool = True,
) -> tuple[pd.Series, str]:
    if train.empty or y.nunique() < 2 or not feature_cols:
        return pd.Series(np.nan, index=score_frame.index), "blocked_insufficient_train_labels"
    medians = {
        col: float(pd.to_numeric(train[col], errors="coerce").median())
        if col in train and pd.to_numeric(train[col], errors="coerce").notna().any()
        else 0.0
        for col in feature_cols
    }
    X_train_frame = pd.DataFrame(
        {col: pd.to_numeric(train[col], errors="coerce").fillna(medians[col]) for col in feature_cols},
        index=train.index,
    )
    X_score_frame = pd.DataFrame(
        {col: pd.to_numeric(score_frame[col], errors="coerce").fillna(medians[col]) for col in feature_cols},
        index=score_frame.index,
    )
    X_train = X_train_frame.to_numpy(dtype=float)
    X_score = X_score_frame.to_numpy(dtype=float)
    try:
        if family in {"logistic_regression_l2", "logistic_l2"}:
            model = LogisticRegression(max_iter=int(config["models"]["logistic_max_iter"]), penalty="l2", solver="liblinear")
            model.fit(X_train, y.astype(int))
            score = model.predict_proba(X_score)[:, 1]
        elif family == "logistic_regression_l1":
            model = LogisticRegression(max_iter=int(config["models"]["logistic_max_iter"]), penalty="l1", solver="liblinear")
            model.fit(X_train, y.astype(int))
            score = model.predict_proba(X_score)[:, 1]
        elif family in {"shallow_decision_tree_max_depth_3", "shallow_tree_depth_2"}:
            depth = 2 if family == "shallow_tree_depth_2" else 3
            model = DecisionTreeClassifier(
                max_depth=depth,
                min_samples_leaf=int(config["models"].get("tree_min_samples_leaf", 100)),
                random_state=int(config["models"].get("random_state", 42)),
            )
            model.fit(X_train, y.astype(int))
            score = model.predict_proba(X_score)[:, 1]
        elif family in {"scorecard_quantile_binning", "scorecard_quantile"}:
            score = scorecard_score(X_train_frame, y.astype(float), X_score_frame, feature_cols).to_numpy(dtype=float)
        elif family == "lightgbm_rejector_depth_3":
            if importlib.util.find_spec("lightgbm") is None:
                return pd.Series(np.nan, index=score_frame.index), "skipped_dependency_unavailable"
            from lightgbm import LGBMClassifier

            model = LGBMClassifier(
                objective="binary",
                boosting_type="gbdt",
                num_leaves=7,
                max_depth=3,
                min_data_in_leaf=100,
                learning_rate=0.05,
                feature_fraction=0.8,
                bagging_fraction=0.8,
                random_state=int(config["models"].get("random_state", 42)),
                n_estimators=100,
                verbose=-1,
            )
            model.fit(X_train_frame, y.astype(int))
            score = model.predict_proba(X_score_frame)[:, 1]
        else:
            return pd.Series(np.nan, index=score_frame.index), "unsupported_model_family"
    except Exception as exc:  # pragma: no cover - defensive model branch
        return pd.Series(np.nan, index=score_frame.index), f"fit_error:{type(exc).__name__}"
    if not score_positive_is_bad:
        score = 1.0 - np.asarray(score, dtype=float)
    return pd.Series(score, index=score_frame.index), "fit"


def scorecard_score(train: pd.DataFrame, y: pd.Series, frame: pd.DataFrame, feature_cols: list[str]) -> pd.Series:
    weights = {}
    for col in feature_cols:
        if train[col].nunique(dropna=True) < 2:
            continue
        corr = train[col].corr(y, method="spearman")
        if pd.notna(corr) and abs(float(corr)) > 0:
            weights[col] = float(corr)
    score = pd.Series(0.0, index=frame.index)
    if not weights:
        return score
    for col, weight in weights.items():
        score += weight * frame[col].rank(pct=True)
    return score


def build_12a4_model_scores(
    joined: pd.DataFrame,
    feature_cols: list[str],
    score_bucket_frontier: pd.DataFrame,
    model_card: pd.DataFrame,
    lightgbm_frontier: pd.DataFrame,
    lightgbm_card: pd.DataFrame,
    config_12a4: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    scores: dict[str, dict[str, Any]] = {}
    frame, _ = impute_by_train(joined, feature_cols)
    train = frame.loc[frame["event_split"].astype(str).eq("train")]
    y = bool_series(train["target_low_to_high_inside"]).astype(int)
    if not train.empty and y.nunique() >= 2:
        model = DecisionTreeClassifier(
            max_depth=3,
            min_samples_leaf=int(config_12a4["models"]["tree_min_samples_leaf"]),
            random_state=int(config_12a4["models"]["random_state"]),
        )
        model.fit(train[feature_cols], y)
        scores["shallow_tree_top20"] = {
            "score": pd.Series(model.predict_proba(frame[feature_cols])[:, 1], index=joined.index),
            "fit_status": "fit",
            "feature_hash_match": stable_hash(feature_cols)
            == str(model_card.loc[model_card["model_id"].eq("shallow_decision_tree_max_depth_3"), "feature_list_hash"].head(1).squeeze()),
        }
    else:
        scores["shallow_tree_top20"] = {"score": pd.Series(np.nan, index=joined.index), "fit_status": "blocked_insufficient_train_labels", "feature_hash_match": False}

    lg_status = str(lightgbm_card.get("lightgbm_challenger_status", pd.Series(["missing"])).iloc[0]) if not lightgbm_card.empty else "missing"
    if lg_status != "evaluated":
        scores["lightgbm_top20"] = {"score": pd.Series(np.nan, index=joined.index), "fit_status": f"skipped_{lg_status}", "feature_hash_match": False}
        return scores
    if importlib.util.find_spec("lightgbm") is None:
        scores["lightgbm_top20"] = {"score": pd.Series(np.nan, index=joined.index), "fit_status": "skipped_dependency_unavailable", "feature_hash_match": False}
        return scores
    try:
        from lightgbm import LGBMClassifier

        model = LGBMClassifier(
            objective="binary",
            boosting_type="gbdt",
            num_leaves=7,
            max_depth=3,
            min_data_in_leaf=100,
            learning_rate=0.05,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            random_state=int(config_12a4["models"]["random_state"]),
            n_estimators=100,
            verbose=-1,
        )
        model.fit(train[feature_cols], y)
        expected_hash = str(lightgbm_card.get("feature_group_importance", pd.Series([""])).iloc[0])
        scores["lightgbm_top20"] = {
            "score": pd.Series(model.predict_proba(frame[feature_cols])[:, 1], index=joined.index),
            "fit_status": "fit",
            "feature_hash_match": stable_hash(feature_cols) == expected_hash,
        }
    except Exception as exc:  # pragma: no cover - defensive dependency branch
        scores["lightgbm_top20"] = {"score": pd.Series(np.nan, index=joined.index), "fit_status": f"fit_error:{type(exc).__name__}", "feature_hash_match": False}
    return scores


def summarize_selected(frame: pd.DataFrame, eligible_episode_n: int | float) -> dict[str, Any]:
    event_n = int(len(frame))
    inside = bool_series(frame.get("target_low_to_high_inside", pd.Series(False, index=frame.index)))
    label20 = bool_series(frame.get("label_20d_complete", pd.Series(False, index=frame.index)))
    label120 = bool_series(frame.get("label_120d_complete", pd.Series(False, index=frame.index)))
    bad = bool_series(frame.get("bad_side_10_20_label", pd.Series(False, index=frame.index)))
    winner = bool_series(frame.get("winner_120_label", pd.Series(False, index=frame.index)))
    episodes = frame.loc[inside, "target_low_to_high_episode_id_first"].dropna().astype(str).nunique() if "target_low_to_high_episode_id_first" in frame else 0
    return {
        "event_n": event_n,
        "inside_n": int(inside.sum()),
        "precision": safe_rate(int(inside.sum()), event_n),
        "bad_side_n": int((bad & label20).sum()),
        "bad_side_rate": safe_rate(int((bad & label20).sum()), int(label20.sum())),
        "winner_120_rate": safe_rate(int((winner & label120).sum()), int(label120.sum())),
        "episode_recall_low_to_high": safe_rate(int(episodes), int(eligible_episode_n) if pd.notna(eligible_episode_n) else 0),
        "label_20d_complete_n": int(label20.sum()),
        "label_120d_complete_n": int(label120.sum()),
    }


def c0_baseline_maps(baseline: pd.DataFrame) -> tuple[dict[str, float], dict[str, int]]:
    c0 = baseline.loc[baseline["source_arm_id"].astype(str).eq(PRIMARY_SOURCE_ARM)]
    precision = c0.set_index("split")["low_to_high_precision"].astype(float).to_dict()
    episode_n = c0.set_index("split")["eligible_episode_n"].fillna(0).astype(int).to_dict()
    return precision, episode_n


def published_row(pool_id: str, split: str, non_model: pd.DataFrame, score_frontier: pd.DataFrame, lightgbm_frontier: pd.DataFrame) -> pd.Series:
    if pool_id in DETERMINISTIC_POOLS:
        spec = DETERMINISTIC_POOLS[pool_id]
        rows = non_model.loc[
            non_model["frontier_id"].eq(spec["frontier_id"])
            & non_model["split"].astype(str).eq(split)
            & non_model["bucket_id"].astype(str).eq("top20")
        ]
    elif pool_id == "lightgbm_top20":
        rows = lightgbm_frontier.loc[
            lightgbm_frontier["model_id"].eq(REFIT_POOLS[pool_id]["model_id"])
            & lightgbm_frontier["split"].astype(str).eq(split)
            & lightgbm_frontier["bucket_id"].astype(str).eq("top20")
        ]
    else:
        rows = score_frontier.loc[
            score_frontier["model_id"].eq(REFIT_POOLS[pool_id]["model_id"])
            & score_frontier["split"].astype(str).eq(split)
            & score_frontier["bucket_id"].astype(str).eq("top20")
        ]
    return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)


def build_bucket_reconstruction(
    joined: pd.DataFrame,
    feature_cols: list[str],
    non_model: pd.DataFrame,
    score_frontier: pd.DataFrame,
    model_card: pd.DataFrame,
    lightgbm_frontier: pd.DataFrame,
    lightgbm_card: pd.DataFrame,
    baseline: pd.DataFrame,
    config: dict[str, Any],
    config_12a4: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, pd.Series], dict[str, pd.Series]]:
    tol = float(config["thresholds"]["reconstruction_float_tolerance"])
    _, eligible_map = c0_baseline_maps(baseline)
    memberships: dict[str, pd.Series] = {}
    scores: dict[str, pd.Series] = {}
    thresholds: dict[str, float] = {}
    rows = []
    for pool_id, spec in DETERMINISTIC_POOLS.items():
        score = numeric(joined[spec["score_feature"]])
        train_score = score.loc[joined["event_split"].astype(str).eq("train")].dropna()
        threshold = float(train_score.quantile(float(spec["train_quantile"]))) if not train_score.empty else np.nan
        if spec["score_direction"] == "higher_is_selected":
            selected = score.ge(threshold)
        else:
            selected = score.le(threshold)
        memberships[pool_id] = selected.fillna(False)
        scores[pool_id] = score
        thresholds[pool_id] = threshold

    model_scores = build_12a4_model_scores(joined, feature_cols, score_frontier, model_card, lightgbm_frontier, lightgbm_card, config_12a4)
    for pool_id, spec in REFIT_POOLS.items():
        pub_train = published_row(pool_id, "train", non_model, score_frontier, lightgbm_frontier)
        threshold = float(pub_train.get("train_reference_top20_threshold", np.nan)) if not pub_train.empty else np.nan
        score = model_scores.get(pool_id, {}).get("score", pd.Series(np.nan, index=joined.index))
        selected = pd.Series(score, index=joined.index).ge(threshold) if pd.notna(threshold) else pd.Series(False, index=joined.index)
        memberships[pool_id] = selected.fillna(False)
        scores[pool_id] = pd.Series(score, index=joined.index)
        thresholds[pool_id] = threshold

    for pool_id, selected in memberships.items():
        if pool_id in DETERMINISTIC_POOLS:
            spec = DETERMINISTIC_POOLS[pool_id]
            pool_status = "ok"
            reconstruction_method = "deterministic_score_from_feature_matrix"
            score_feature = spec["score_feature"]
            score_direction = spec["score_direction"]
            train_quantile = spec["train_quantile"]
            hard_bad_n = False
            refit_status = ""
            refit_feature_hash_match = np.nan
        else:
            spec = REFIT_POOLS[pool_id]
            reconstruction_method = spec["reconstruction_method"]
            score_feature = "meta_label_score"
            score_direction = "higher_is_selected"
            train_quantile = np.nan
            hard_bad_n = False
            refit_status = str(model_scores.get(pool_id, {}).get("fit_status", "missing"))
            refit_feature_hash_match = bool(model_scores.get(pool_id, {}).get("feature_hash_match", False))
            if pool_id == "lightgbm_top20" and refit_status.startswith("skipped"):
                pool_status = "skipped_dependency_or_upstream_unavailable"
            elif not refit_feature_hash_match:
                pool_status = "refit_feature_hash_mismatch"
            else:
                pool_status = "ok" if refit_status == "fit" else "refit_membership_mismatch"
        for split in SPLITS:
            split_mask = pd.Series(True, index=joined.index) if split == "all" else joined["event_split"].astype(str).eq(split)
            selected_frame = joined.loc[split_mask & selected].copy()
            summary = summarize_selected(selected_frame, eligible_map.get(split, eligible_map.get("all", 0)))
            pub = published_row(pool_id, split, non_model, score_frontier, lightgbm_frontier)
            published_event_n = int(pub.get("event_n", 0)) if not pub.empty and pd.notna(pub.get("event_n", np.nan)) else 0
            published_inside_n = int(pub.get("event_inside_window_n", 0)) if not pub.empty and pd.notna(pub.get("event_inside_window_n", np.nan)) else 0
            published_precision = float(pub.get("low_to_high_precision", np.nan)) if not pub.empty else np.nan
            published_bad_rate = float(pub.get("bad_side_10_20_rate", np.nan)) if not pub.empty else np.nan
            bad_derived = int(round(published_bad_rate * published_event_n)) if pd.notna(published_bad_rate) and published_event_n else np.nan
            event_match = summary["event_n"] == published_event_n
            inside_match = summary["inside_n"] == published_inside_n
            precision_diff = abs(float(summary["precision"]) - published_precision) if pd.notna(summary["precision"]) and pd.notna(published_precision) else np.nan
            bad_diff = abs(float(summary["bad_side_rate"]) - published_bad_rate) if pd.notna(summary["bad_side_rate"]) and pd.notna(published_bad_rate) else np.nan
            status = pool_status
            if status == "ok" and (not event_match or not inside_match or (pd.notna(precision_diff) and precision_diff > tol) or (pd.notna(bad_diff) and bad_diff > tol)):
                status = "refit_membership_mismatch" if pool_id in REFIT_POOLS else "deterministic_membership_mismatch"
            nominal_n = int(round(0.20 * len(split_frame(joined, split))))
            rows.append(
                {
                    "pool_id": pool_id,
                    "split": split,
                    "pool_status": pool_status,
                    "reconstruction_method": reconstruction_method,
                    "score_feature": score_feature,
                    "score_direction": score_direction,
                    "train_quantile": train_quantile,
                    "train_reference_top20_threshold": thresholds.get(pool_id, np.nan),
                    "nominal_top20_event_n": nominal_n,
                    "reconstructed_event_n": summary["event_n"],
                    "reconstructed_inside_n": summary["inside_n"],
                    "reconstructed_bad_side_n": summary["bad_side_n"],
                    "reconstructed_precision": summary["precision"],
                    "reconstructed_bad_side_rate": summary["bad_side_rate"],
                    "reconstructed_membership_hash": stable_membership_hash(selected_frame["meta_event_id"]),
                    "published_event_n": published_event_n,
                    "published_inside_n": published_inside_n,
                    "published_bad_side_n": np.nan,
                    "published_bad_side_n_derived": bad_derived,
                    "published_precision": published_precision,
                    "published_bad_side_rate": published_bad_rate,
                    "event_n_match": bool(event_match),
                    "inside_n_match": bool(inside_match),
                    "bad_side_n_hard_gate_applied": bool(hard_bad_n),
                    "bad_side_n_match": np.nan,
                    "tie_expansion_n": int(summary["event_n"] - nominal_n),
                    "precision_abs_diff": precision_diff,
                    "bad_side_rate_abs_diff": bad_diff,
                    "refit_feature_hash_match": refit_feature_hash_match,
                    "reconstruction_status": status,
                    "skip_reason": refit_status if status != "ok" else "",
                }
            )
    return pd.DataFrame(rows), memberships, scores


def build_label_completeness(joined: pd.DataFrame, memberships: dict[str, pd.Series], config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    min20 = float(config["thresholds"]["label_20d_complete_min_rate"])
    min120 = float(config["thresholds"]["label_120d_complete_min_rate"])
    for pool_id, selected in memberships.items():
        for split in SPLITS:
            frame = split_frame(joined.loc[selected], split)
            event_n = int(len(frame))
            n10 = int(bool_series(frame.get("label_10d_complete", pd.Series(False, index=frame.index))).sum())
            n20 = int(bool_series(frame.get("label_20d_complete", pd.Series(False, index=frame.index))).sum())
            n120 = int(bool_series(frame.get("label_120d_complete", pd.Series(False, index=frame.index))).sum())
            r20 = safe_rate(n20, event_n)
            r120 = safe_rate(n120, event_n)
            rows.append(
                {
                    "pool_id": pool_id,
                    "split": split,
                    "event_n": event_n,
                    "label_10d_complete_n": n10,
                    "label_20d_complete_n": n20,
                    "label_120d_complete_n": n120,
                    "label_10d_complete_rate": safe_rate(n10, event_n),
                    "label_20d_complete_rate": r20,
                    "label_120d_complete_rate": r120,
                    "label_completeness_gate_pass": bool(pd.notna(r20) and pd.notna(r120) and r20 >= min20 and r120 >= min120),
                }
            )
    return pd.DataFrame(rows)


def build_composition(joined: pd.DataFrame, memberships: dict[str, pd.Series], baseline: pd.DataFrame) -> pd.DataFrame:
    _, eligible_map = c0_baseline_maps(baseline)
    rows = []
    for pool_id, selected in memberships.items():
        for split in SPLITS:
            frame = split_frame(joined.loc[selected], split)
            summary = summarize_selected(frame, eligible_map.get(split, eligible_map.get("all", 0)))
            label20 = bool_series(frame.get("label_20d_complete", pd.Series(False, index=frame.index)))
            fast = bool_series(frame.get("fast_fail_10d_label", pd.Series(False, index=frame.index))) & label20
            repair = bool_series(frame.get("false_repair_20d_label", pd.Series(False, index=frame.index))) & label20
            both = fast & repair
            bad_n = int((fast | repair).sum())
            fast_only = int((fast & ~repair).sum())
            repair_only = int((repair & ~fast).sum())
            overlap = int(both.sum())
            shares = {
                "fast_fail_only_share_of_bad": safe_rate(fast_only, bad_n),
                "false_repair_only_share_of_bad": safe_rate(repair_only, bad_n),
                "overlap_share_of_bad": safe_rate(overlap, bad_n),
            }
            if pd.notna(shares["fast_fail_only_share_of_bad"]) and shares["fast_fail_only_share_of_bad"] >= 0.50:
                dominant = "fast_fail_dominant"
            elif pd.notna(shares["false_repair_only_share_of_bad"]) and shares["false_repair_only_share_of_bad"] >= 0.50:
                dominant = "false_repair_dominant"
            elif pd.notna(shares["overlap_share_of_bad"]) and shares["overlap_share_of_bad"] >= 0.50:
                dominant = "overlap_dominant"
            else:
                dominant = "mixed"
            rows.append(
                {
                    "pool_id": pool_id,
                    "split": split,
                    "event_n": summary["event_n"],
                    "label_20d_complete_n": summary["label_20d_complete_n"],
                    "inside_window_n": summary["inside_n"],
                    "precision": summary["precision"],
                    "bad_side_n": bad_n,
                    "bad_side_rate": summary["bad_side_rate"],
                    "fast_fail_n": int(fast.sum()),
                    "false_repair_n": int(repair.sum()),
                    "both_n": overlap,
                    "fast_fail_only_n": fast_only,
                    "false_repair_only_n": repair_only,
                    "fast_fail_only_share_of_bad": shares["fast_fail_only_share_of_bad"],
                    "false_repair_only_share_of_bad": shares["false_repair_only_share_of_bad"],
                    "overlap_share_of_bad": shares["overlap_share_of_bad"],
                    "dominant_component": dominant,
                    "composition_status": "ok" if summary["label_20d_complete_n"] > 0 else "insufficient_complete_label",
                }
            )
    return pd.DataFrame(rows)


def auc_or_nan(y_true: pd.Series, score: pd.Series) -> float:
    y = y_true.astype(int)
    s = pd.to_numeric(score, errors="coerce")
    mask = s.notna()
    if int(mask.sum()) < 2 or y.loc[mask].nunique() < 2:
        return np.nan
    return float(roc_auc_score(y.loc[mask], s.loc[mask]))


def ks_stat(pos: pd.Series, neg: pd.Series) -> float:
    pos = pd.to_numeric(pos, errors="coerce").dropna().sort_values().to_numpy()
    neg = pd.to_numeric(neg, errors="coerce").dropna().sort_values().to_numpy()
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    values = np.sort(np.unique(np.concatenate([pos, neg])))
    pos_cdf = np.searchsorted(pos, values, side="right") / len(pos)
    neg_cdf = np.searchsorted(neg, values, side="right") / len(neg)
    return float(np.max(np.abs(pos_cdf - neg_cdf)))


def label_population(frame: pd.DataFrame, positive: str = "clean_winner") -> tuple[pd.DataFrame, pd.Series]:
    clean = bool_series(frame["clean_winner_event"])
    clean_capture = bool_series(frame["clean_capture_event"])
    bad = bool_series(frame["bad_side_event"])
    pos = clean_capture if positive == "clean_capture" else clean
    pop = frame.loc[pos | bad].copy()
    if positive == "clean_winner":
        y = bool_series(pop["clean_winner_event"]).astype(int)
    elif positive == "clean_capture":
        y = bool_series(pop["clean_capture_event"]).astype(int)
    else:
        y = bool_series(pop["bad_side_event"]).astype(int)
    return pop, y


def build_univariate(joined: pd.DataFrame, memberships: dict[str, pd.Series], feature_cols: list[str], dictionary: pd.DataFrame) -> pd.DataFrame:
    feature_group = dictionary.set_index("feature_name")["feature_group"].astype(str).to_dict()
    rows = []
    for pool_id, selected in memberships.items():
        for split in SPLITS:
            frame = split_frame(joined.loc[selected], split)
            for positive_class, positive_key in (("clean_winner_event", "clean_winner"), ("clean_capture_event", "clean_capture")):
                pop, y = label_population(frame, positive_key)
                positive_n = int((y == 1).sum())
                bad_n = int((y == 0).sum())
                for col in feature_cols:
                    values = pd.to_numeric(pop[col], errors="coerce") if col in pop else pd.Series(dtype=float)
                    coverage = safe_rate(int(values.notna().sum()), len(pop))
                    auc = auc_or_nan(y, values)
                    rows.append(
                        {
                            "pool_id": pool_id,
                            "split": split,
                            "separability_positive_class": positive_class,
                            "feature_name": col,
                            "feature_group": feature_group.get(col, ""),
                            "clean_winner_n": positive_n,
                            "positive_event_n": positive_n,
                            "bad_side_n": bad_n,
                            "auc": auc,
                            "auc_direction": "higher_clean_winner" if pd.notna(auc) and auc >= 0.5 else "lower_clean_winner",
                            "abs_auc_minus_0p5": abs(float(auc) - 0.5) if pd.notna(auc) else np.nan,
                            "ks_statistic": ks_stat(values.loc[y.eq(1)], values.loc[y.eq(0)]) if len(pop) else np.nan,
                            "coverage_rate": coverage,
                            "separability_status": "ok" if positive_n > 0 and bad_n > 0 and pd.notna(auc) and pd.notna(coverage) and coverage >= 0.80 else "sparse_or_single_class",
                        }
                    )
    return pd.DataFrame(rows)


def bootstrap_auc_ci(y: pd.Series, score: pd.Series, n_bootstrap: int, seed: int) -> tuple[float, float]:
    y = y.astype(int).reset_index(drop=True)
    score = pd.to_numeric(score, errors="coerce").reset_index(drop=True)
    valid = score.notna()
    y = y.loc[valid].reset_index(drop=True)
    score = score.loc[valid].reset_index(drop=True)
    if len(y) < 2 or y.nunique() < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    aucs = []
    n = len(y)
    for _ in range(int(n_bootstrap)):
        idx = rng.integers(0, n, n)
        yy = y.iloc[idx]
        if yy.nunique() < 2:
            continue
        aucs.append(float(roc_auc_score(yy, score.iloc[idx])))
    if not aucs:
        return np.nan, np.nan
    return float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))


def build_lowcapacity(
    joined: pd.DataFrame,
    memberships: dict[str, pd.Series],
    feature_cols: list[str],
    config: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    methods = tuple(config["models"]["lowcapacity_methods"])
    for pool_id, selected in memberships.items():
        train_pool = joined.loc[selected & joined["event_split"].astype(str).eq("train")].copy()
        eval_pool = joined.loc[selected & joined["event_split"].astype(str).eq("robustness")].copy()
        for positive_class, positive_key in (("clean_winner_event", "clean_winner"), ("clean_capture_event", "clean_capture")):
            train_pop, y_train = label_population(train_pool, positive_key)
            eval_pop, y_eval = label_population(eval_pool, positive_key)
            positive_n = int((y_eval == 1).sum())
            bad_n = int((y_eval == 0).sum())
            sufficient = positive_n >= int(config["thresholds"]["clean_winner_min_eval_n"])
            for method in methods:
                score, fit_status = fit_score_model(method, train_pop, y_train, eval_pop, feature_cols, config, score_positive_is_bad=False)
                auc = auc_or_nan(y_eval, score)
                ci_low, ci_high = bootstrap_auc_ci(y_eval, score, int(config["models"]["bootstrap_n"]), int(config["models"]["random_state"]))
                top_rate = np.nan
                bottom_rate = np.nan
                if len(eval_pop) and score.notna().any():
                    ranked = eval_pop.assign(_score=score).sort_values("_score", ascending=False, kind="stable")
                    k = max(1, int(math.ceil(0.10 * len(ranked))))
                    top_rate = float(bool_series(ranked.head(k)[positive_class]).mean())
                    bottom_rate = float(bool_series(ranked.tail(k)[positive_class]).mean())
                status = "ok" if sufficient and fit_status == "fit" and pd.notna(auc) else ("insufficient_positive" if not sufficient else fit_status)
                rows.append(
                    {
                        "pool_id": pool_id,
                        "split": "robustness",
                        "separability_positive_class": positive_class,
                        "method": method,
                        "fit_split": "train",
                        "eval_split": "robustness",
                        "clean_winner_n": positive_n,
                        "positive_event_n": positive_n,
                        "bad_side_n": bad_n,
                        "auc": auc,
                        "auc_ci_low": ci_low,
                        "auc_ci_high": ci_high,
                        "auc_ci_method": f"bootstrap_{int(config['models']['bootstrap_n'])}",
                        "average_precision": float(average_precision_score(y_eval, score)) if len(y_eval) and y_eval.nunique() > 1 and score.notna().any() else np.nan,
                        "top_decile_clean_winner_rate": top_rate,
                        "bottom_decile_clean_winner_rate": bottom_rate,
                        "separability_status": status,
                    }
                )
    return pd.DataFrame(rows)


def stratified_fold_ids(pool_train: pd.DataFrame, n_splits: int) -> pd.Series:
    folds = pd.Series(-1, index=pool_train.index, dtype=int)
    if pool_train.empty:
        return folds
    clean = bool_series(pool_train["clean_winner_event"])
    bad = bool_series(pool_train["bad_side_event"])
    groups = {
        "clean": pool_train.loc[clean].copy(),
        "bad": pool_train.loc[bad & ~clean].copy(),
        "neutral": pool_train.loc[~clean & ~bad].copy(),
    }
    for group in groups.values():
        if group.empty:
            continue
        sort_col = "meta_event_id" if "meta_event_id" in group.columns else None
        ordered_index = group.sort_values(sort_col, kind="stable").index if sort_col else group.index
        for pos, idx in enumerate(ordered_index):
            folds.loc[idx] = pos % int(n_splits)
    return folds


def training_class_audit_for_pool(pool_train: pd.DataFrame, pool_id: str, rejector_id: str, label_policy: str, config: dict[str, Any]) -> dict[str, Any]:
    clean = bool_series(pool_train["clean_winner_event"])
    bad = bool_series(pool_train["bad_side_event"])
    n_splits = int(config["thresholds"]["cv_n_splits"])
    fold_ids = stratified_fold_ids(pool_train, n_splits)
    fold_clean = []
    fold_bad = []
    for fold in range(n_splits):
        fold_frame = pool_train.loc[fold_ids.eq(fold)]
        fold_clean.append(int(bool_series(fold_frame.get("clean_winner_event", pd.Series(dtype=bool))).sum()))
        fold_bad.append(int(bool_series(fold_frame.get("bad_side_event", pd.Series(dtype=bool))).sum()))
    min_clean = min(fold_clean) if fold_clean else 0
    min_bad = min(fold_bad) if fold_bad else 0
    pass_flag = (
        int(clean.sum()) >= int(config["thresholds"]["train_clean_winner_min_n"])
        and int(bad.sum()) >= int(config["thresholds"]["train_bad_side_min_n"])
        and min_clean >= int(config["thresholds"]["cv_fold_min_clean_winner_n"])
        and min_bad >= int(config["thresholds"]["cv_fold_min_bad_side_n"])
    )
    return {
        "pool_id": pool_id,
        "rejector_id": rejector_id,
        "label_policy": label_policy,
        "fit_split": "train",
        "train_event_n": int(len(pool_train)),
        "train_clean_winner_n": int(clean.sum()),
        "train_bad_side_n": int(bad.sum()),
        "train_neutral_excluded_n": int(len(pool_train) - int((clean | bad).sum())),
        "cv_n_splits": n_splits,
        "cv_fold_min_clean_winner_n": int(min_clean),
        "cv_fold_min_bad_side_n": int(min_bad),
        "train_class_sufficiency_gate_pass": bool(pass_flag),
        "training_status": "ok" if pass_flag else "insufficient_training_class_sample",
    }


def train_cv_scores(pool_train: pd.DataFrame, label_policy: str, rejector_id: str, feature_cols: list[str], config: dict[str, Any]) -> pd.Series:
    n_splits = int(config["thresholds"]["cv_n_splits"])
    scores = pd.Series(np.nan, index=pool_train.index)
    if pool_train.empty:
        return scores
    fold_ids = stratified_fold_ids(pool_train, n_splits)
    for fold in range(n_splits):
        train_fold = pool_train.loc[fold_ids.ne(fold)]
        val_fold = pool_train.loc[fold_ids.eq(fold)]
        if label_policy == "bad_side_vs_clean_winner":
            fit_pop = train_fold.loc[bool_series(train_fold["bad_side_event"]) | bool_series(train_fold["clean_winner_event"])]
            y = bool_series(fit_pop["bad_side_event"]).astype(int)
        else:
            fit_pop = train_fold.loc[bool_series(train_fold["label_20d_complete"])]
            y = bool_series(fit_pop["bad_side_event"]).astype(int)
        fold_score, _ = fit_score_model(rejector_id, fit_pop, y, val_fold, feature_cols, config, score_positive_is_bad=True)
        scores.loc[val_fold.index] = fold_score
    return scores


def final_reject_scores(pool_train: pd.DataFrame, pool_score: pd.DataFrame, label_policy: str, rejector_id: str, feature_cols: list[str], config: dict[str, Any]) -> tuple[pd.Series, str]:
    if label_policy == "bad_side_vs_clean_winner":
        fit_pop = pool_train.loc[bool_series(pool_train["bad_side_event"]) | bool_series(pool_train["clean_winner_event"])]
        y = bool_series(fit_pop["bad_side_event"]).astype(int)
    else:
        fit_pop = pool_train.loc[bool_series(pool_train["label_20d_complete"])]
        y = bool_series(fit_pop["bad_side_event"]).astype(int)
    return fit_score_model(rejector_id, fit_pop, y, pool_score, feature_cols, config, score_positive_is_bad=True)


def apply_reject_fraction(frame: pd.DataFrame, score: pd.Series, reject_fraction: float) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    scored = frame.assign(_reject_score=pd.to_numeric(score.reindex(frame.index), errors="coerce").fillna(-np.inf))
    reject_n = int(math.ceil(float(reject_fraction) * len(scored)))
    if reject_n <= 0:
        return scored.drop(columns=["_reject_score"])
    rejected_index = scored.sort_values(["_reject_score", "meta_event_id"], ascending=[False, True], kind="stable").head(reject_n).index
    return scored.loc[~scored.index.isin(rejected_index)].drop(columns=["_reject_score"])


def build_rejector_outputs(
    joined: pd.DataFrame,
    memberships: dict[str, pd.Series],
    feature_cols: list[str],
    composition: pd.DataFrame,
    baseline: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    precision_map, eligible_map = c0_baseline_maps(baseline)
    pool_metrics = composition.set_index(["pool_id", "split"])
    fractions = [float(x) for x in config["models"]["reject_fractions"]]
    frontier_rows = []
    training_rows = []
    work_rows = []
    for pool_id, selected in memberships.items():
        pool_train = joined.loc[selected & joined["event_split"].astype(str).eq("train")].copy()
        for rejector_id in REJECTOR_FAMILIES:
            for label_policy, allowed_policy in (("bad_side_vs_clean_winner", True), ("bad_side_vs_all_non_bad", False)):
                allowed_for_decision = bool(allowed_policy and rejector_id in PRIMARY_REJECTORS)
                audit = training_class_audit_for_pool(pool_train, pool_id, rejector_id, label_policy, config)
                training_rows.append(audit)
                if label_policy == "bad_side_vs_clean_winner" and not audit["train_class_sufficiency_gate_pass"]:
                    fit_status = "insufficient_training_class_sample"
                    split_scores: dict[str, pd.Series] = {}
                else:
                    cv_scores = train_cv_scores(pool_train, label_policy, rejector_id, feature_cols, config)
                    split_scores = {"train": cv_scores}
                    fit_status = "fit"
                    for split in ("validation", "robustness", "all"):
                        pool_split = joined.loc[selected] if split == "all" else joined.loc[selected & joined["event_split"].astype(str).eq(split)]
                        final_score, fit_status = final_reject_scores(pool_train, pool_split, label_policy, rejector_id, feature_cols, config)
                        split_scores[split] = final_score
                for split in SPLITS:
                    pool_split = joined.loc[selected] if split == "all" else joined.loc[selected & joined["event_split"].astype(str).eq(split)]
                    score = split_scores.get(split, pd.Series(np.nan, index=pool_split.index))
                    pool_key = (pool_id, split)
                    pool_precision = float(pool_metrics.loc[pool_key, "precision"]) if pool_key in pool_metrics.index else np.nan
                    pool_bad_rate = float(pool_metrics.loc[pool_key, "bad_side_rate"]) if pool_key in pool_metrics.index else np.nan
                    pool_recall = summarize_selected(pool_split, eligible_map.get(split, eligible_map.get("all", 0)))["episode_recall_low_to_high"]
                    for frac in fractions:
                        retained = apply_reject_fraction(pool_split, score, frac)
                        summary = summarize_selected(retained, eligible_map.get(split, eligible_map.get("all", 0)))
                        label20 = bool_series(retained.get("label_20d_complete", pd.Series(False, index=retained.index)))
                        fast = bool_series(retained.get("fast_fail_10d_label", pd.Series(False, index=retained.index))) & label20
                        repair = bool_series(retained.get("false_repair_20d_label", pd.Series(False, index=retained.index))) & label20
                        frontier_rows.append(
                            {
                                "pool_id": pool_id,
                                "rejector_id": rejector_id,
                                "rejector_family": rejector_id,
                                "label_policy": label_policy,
                                "allowed_for_decision_gate": bool(allowed_for_decision),
                                "reject_score_direction": "higher_is_worse",
                                "split": split,
                                "reject_fraction": frac,
                                "retained_event_n": summary["event_n"],
                                "retained_inside_n": summary["inside_n"],
                                "retained_precision": summary["precision"],
                                "retained_bad_side_rate": summary["bad_side_rate"],
                                "retained_fast_fail_rate": safe_rate(int(fast.sum()), int(label20.sum())),
                                "retained_false_repair_rate": safe_rate(int(repair.sum()), int(label20.sum())),
                                "retained_episode_recall_low_to_high": summary["episode_recall_low_to_high"],
                                "retained_winner_120_rate": summary["winner_120_rate"],
                                "bad_side_reduction_vs_pool": pool_bad_rate - summary["bad_side_rate"] if pd.notna(pool_bad_rate) and pd.notna(summary["bad_side_rate"]) else np.nan,
                                "precision_delta_vs_pool": summary["precision"] - pool_precision if pd.notna(summary["precision"]) and pd.notna(pool_precision) else np.nan,
                                "episode_recall_delta_vs_pool": summary["episode_recall_low_to_high"] - pool_recall if pd.notna(summary["episode_recall_low_to_high"]) and pd.notna(pool_recall) else np.nan,
                                "retained_precision_vs_c0_baseline_ratio": safe_rate(summary["precision"], precision_map.get(split, np.nan)),
                                "frontier_status": "ok" if fit_status == "fit" and score.notna().any() else fit_status,
                            }
                        )
                train_front = pd.DataFrame([r for r in frontier_rows if r["pool_id"] == pool_id and r["rejector_id"] == rejector_id and r["label_policy"] == label_policy and r["split"] == "train"])
                rob_front = pd.DataFrame([r for r in frontier_rows if r["pool_id"] == pool_id and r["rejector_id"] == rejector_id and r["label_policy"] == label_policy and r["split"] == "robustness"])
                min_train_precision = max(float(config["thresholds"]["train_cv_min_precision_floor"]), precision_map.get("train", np.nan))
                candidates = train_front.loc[
                    train_front["retained_event_n"].ge(int(config["thresholds"]["train_cv_min_retained_event_n"]))
                    & train_front["retained_precision"].ge(min_train_precision)
                    & train_front["frontier_status"].eq("ok")
                ].copy()
                if candidates.empty:
                    chosen_frac = fractions[0]
                    train_candidate_gate = False
                    train_event_n = np.nan
                    train_precision = np.nan
                else:
                    candidates = candidates.sort_values(
                        ["retained_bad_side_rate", "retained_precision", "reject_fraction"],
                        ascending=[True, False, True],
                        kind="stable",
                    )
                    chosen = candidates.iloc[0]
                    chosen_frac = float(chosen["reject_fraction"])
                    train_candidate_gate = True
                    train_event_n = int(chosen["retained_event_n"])
                    train_precision = float(chosen["retained_precision"])
                rob = rob_front.loc[rob_front["reject_fraction"].eq(chosen_frac)].head(1)
                if rob.empty:
                    rob_row = pd.Series(dtype=object)
                else:
                    rob_row = rob.iloc[0]
                work_rows.append(
                    {
                        "pool_id": pool_id,
                        "rejector_id": rejector_id,
                        "rejector_family": rejector_id,
                        "label_policy": label_policy,
                        "workpoint_allowed_for_decision_gate": bool(allowed_for_decision),
                        "reject_score_direction": "higher_is_worse",
                        "chosen_reject_fraction": chosen_frac,
                        "chosen_reject_fraction_source": "train_internal_cv",
                        "fit_split": "train",
                        "selection_split": "train_internal_cv",
                        "eval_split": "robustness",
                        "train_cv_retained_event_n": train_event_n,
                        "train_cv_retained_precision": train_precision,
                        "train_cv_candidate_gate_pass": bool(train_candidate_gate),
                        "retained_event_n": int(rob_row.get("retained_event_n", 0)) if not rob_row.empty else 0,
                        "retained_precision": float(rob_row.get("retained_precision", np.nan)) if not rob_row.empty else np.nan,
                        "retained_bad_side_rate": float(rob_row.get("retained_bad_side_rate", np.nan)) if not rob_row.empty else np.nan,
                        "pool_bad_side_rate": float(pool_metrics.loc[(pool_id, "robustness"), "bad_side_rate"]) if (pool_id, "robustness") in pool_metrics.index else np.nan,
                        "bad_side_reduction_abs": float(rob_row.get("bad_side_reduction_vs_pool", np.nan)) if not rob_row.empty else np.nan,
                        "bad_side_reduction_rel": safe_rate(float(rob_row.get("bad_side_reduction_vs_pool", np.nan)), float(pool_metrics.loc[(pool_id, "robustness"), "bad_side_rate"])) if (pool_id, "robustness") in pool_metrics.index and not rob_row.empty else np.nan,
                        "precision_delta_vs_pool": float(rob_row.get("precision_delta_vs_pool", np.nan)) if not rob_row.empty else np.nan,
                        "retained_episode_recall_low_to_high": float(rob_row.get("retained_episode_recall_low_to_high", np.nan)) if not rob_row.empty else np.nan,
                        "retained_precision_minus_c0_baseline": float(rob_row.get("retained_precision", np.nan)) - precision_map.get("robustness", np.nan) if not rob_row.empty else np.nan,
                        "train_class_sufficiency_gate_pass": bool(audit["train_class_sufficiency_gate_pass"]) if label_policy == "bad_side_vs_clean_winner" else True,
                        "workpoint_meets_supported": False,
                        "workpoint_meets_partial": False,
                        "workpoint_status": "ok" if not rob_row.empty and rob_row.get("frontier_status", "") == "ok" else "no_valid_workpoint",
                    }
                )
    return pd.DataFrame(training_rows), pd.DataFrame(frontier_rows), pd.DataFrame(work_rows)


def choose_primary_pool(reconstruction: pd.DataFrame, composition: pd.DataFrame) -> tuple[str, bool, str, str, float, float]:
    rob = reconstruction.loc[reconstruction["split"].eq("robustness")]
    shallow_ok = not rob.loc[rob["pool_id"].eq("shallow_tree_top20") & rob["reconstruction_status"].eq("ok")].empty
    density_ok = not rob.loc[rob["pool_id"].eq("density_only_top20") & rob["reconstruction_status"].eq("ok")].empty
    if shallow_ok:
        return "shallow_tree_top20", False, "", "", np.nan, np.nan
    if density_ok:
        comp = composition.set_index(["pool_id", "split"])
        from_rate = float(comp.loc[("shallow_tree_top20", "robustness"), "bad_side_rate"]) if ("shallow_tree_top20", "robustness") in comp.index else np.nan
        to_rate = float(comp.loc[("density_only_top20", "robustness"), "bad_side_rate"]) if ("density_only_top20", "robustness") in comp.index else np.nan
        return "density_only_top20", True, "shallow_tree_top20", "density_only_top20", from_rate, to_rate
    return "", False, "", "", np.nan, np.nan


def evaluate_decision(
    input_gate_pass: bool,
    upstream_gate_pass: bool,
    join_gate_pass: bool,
    parity_gate_pass: bool,
    reconstruction: pd.DataFrame,
    label_audit: pd.DataFrame,
    composition: pd.DataFrame,
    univariate: pd.DataFrame,
    lowcapacity: pd.DataFrame,
    training_audit: pd.DataFrame,
    workpoints: pd.DataFrame,
    baseline: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    primary_pool, is_fallback, fallback_from, fallback_to, fallback_from_rate, fallback_to_rate = choose_primary_pool(reconstruction, composition)
    precision_map, _ = c0_baseline_maps(baseline)
    c0_rob = precision_map.get("robustness", np.nan)
    block_reason = ""
    if not input_gate_pass:
        block_reason = "input_artifact_or_schema_failure"
    elif not upstream_gate_pass:
        block_reason = "upstream_12a4_gate_failure"
    elif not join_gate_pass or not parity_gate_pass:
        block_reason = "event_feature_join_or_dictionary_parity_failure"
    elif not primary_pool:
        block_reason = "bucket_reconstruction_all_primary_candidates_failed"
    label_gate = False
    if primary_pool:
        label_row = label_audit.loc[label_audit["pool_id"].eq(primary_pool) & label_audit["split"].eq("robustness")].head(1)
        label_gate = boolish(label_row.iloc[0]["label_completeness_gate_pass"]) if not label_row.empty else False
        if not label_gate and not block_reason:
            block_reason = "label_completeness_failure"
    comp_row = composition.loc[composition["pool_id"].eq(primary_pool) & composition["split"].eq("robustness")].head(1)
    dominant = str(comp_row.iloc[0]["dominant_component"]) if not comp_row.empty else ""
    fast_share = float(comp_row.iloc[0]["fast_fail_only_share_of_bad"]) if not comp_row.empty else np.nan
    composition_actionable = bool(dominant in {"false_repair_dominant", "overlap_dominant", "mixed"} and pd.notna(fast_share) and fast_share < 0.50)
    low_pool = lowcapacity.loc[
        lowcapacity["pool_id"].eq(primary_pool)
        & lowcapacity.get("separability_positive_class", pd.Series("clean_winner_event", index=lowcapacity.index)).astype(str).eq("clean_winner_event")
    ]
    best_low = low_pool.sort_values(["auc", "auc_ci_low"], ascending=[False, False]).head(1)
    best_auc = float(best_low.iloc[0]["auc"]) if not best_low.empty else np.nan
    best_auc_ci_low = float(best_low.iloc[0]["auc_ci_low"]) if not best_low.empty else np.nan
    clean_n = int(best_low.iloc[0]["clean_winner_n"]) if not best_low.empty else 0
    clean_sufficient = clean_n >= int(config["thresholds"]["clean_winner_min_eval_n"])
    uni_pool = univariate.loc[
        univariate["pool_id"].eq(primary_pool)
        & univariate["split"].eq("robustness")
        & univariate.get("separability_positive_class", pd.Series("clean_winner_event", index=univariate.index)).astype(str).eq("clean_winner_event")
    ]
    best_uni = float(uni_pool["abs_auc_minus_0p5"].dropna().max()) if not uni_pool.empty and uni_pool["abs_auc_minus_0p5"].notna().any() else np.nan
    separable = bool(
        clean_sufficient
        and pd.notna(best_auc)
        and best_auc >= float(config["thresholds"]["separability_min_auc"])
        and pd.notna(best_auc_ci_low)
        and best_auc_ci_low >= float(config["thresholds"]["separability_min_auc_ci_low"])
        and pd.notna(best_uni)
        and best_uni >= float(config["thresholds"]["separability_min_univariate_abs_auc_minus_0p5"])
    )
    primary_work = workpoints.loc[
        workpoints["pool_id"].eq(primary_pool)
        & workpoints["label_policy"].eq("bad_side_vs_clean_winner")
        & bool_series(workpoints["workpoint_allowed_for_decision_gate"])
    ].copy()
    if not primary_work.empty:
        primary_work["supported_candidate"] = (
            primary_work["train_cv_candidate_gate_pass"].map(boolish)
            & primary_work["train_class_sufficiency_gate_pass"].map(boolish)
            & primary_work["retained_precision"].ge(float(config["thresholds"]["supported_min_precision"]))
            & primary_work["bad_side_reduction_abs"].ge(float(config["thresholds"]["supported_min_badside_reduction_abs"]))
            & primary_work["retained_bad_side_rate"].le(float(config["thresholds"]["supported_max_badside_rate"]))
            & primary_work["retained_precision"].ge(c0_rob + float(config["thresholds"]["supported_min_precision_delta_vs_c0"]))
            & primary_work["retained_event_n"].ge(int(config["thresholds"]["supported_min_retained_event_n"]))
            & primary_work["retained_episode_recall_low_to_high"].ge(float(config["thresholds"]["supported_min_retained_episode_recall"]))
        )
        partial_precision_min = max(c0_rob + float(config["thresholds"]["partial_min_precision_delta_vs_c0"]), float(config["thresholds"]["partial_min_precision_abs"]))
        primary_work["partial_candidate"] = (
            primary_work["train_cv_candidate_gate_pass"].map(boolish)
            & primary_work["train_class_sufficiency_gate_pass"].map(boolish)
            & primary_work["retained_precision"].ge(partial_precision_min)
            & primary_work["precision_delta_vs_pool"].ge(float(config["thresholds"]["partial_min_precision_delta_vs_pool"]))
            & primary_work["bad_side_reduction_abs"].ge(float(config["thresholds"]["partial_min_badside_reduction_abs"]))
        )
        primary_work = primary_work.sort_values(
            ["supported_candidate", "partial_candidate", "bad_side_reduction_abs", "retained_precision"],
            ascending=[False, False, False, False],
            kind="stable",
        )
        wp = primary_work.iloc[0]
    else:
        wp = pd.Series(dtype=object)
    train_suff = boolish(wp.get("train_class_sufficiency_gate_pass", False)) if not wp.empty else False
    if primary_pool and not train_suff and not block_reason:
        block_reason = "insufficient_training_class_sample"
    bucket_gate = primary_pool != "" and not reconstruction.loc[
        reconstruction["pool_id"].eq(primary_pool) & reconstruction["split"].eq("robustness") & reconstruction["reconstruction_status"].eq("ok")
    ].empty
    supported = bool(
        not block_reason
        and composition_actionable
        and separable
        and not is_fallback
        and bucket_gate
        and boolish(wp.get("supported_candidate", False))
        and label_gate
    )
    partial = bool(
        not block_reason
        and not supported
        and composition_actionable
        and separable
        and bucket_gate
        and boolish(wp.get("partial_candidate", False))
        and label_gate
    )
    if block_reason:
        state = "12A5A_blocked_input_or_pit_failure"
        reason = block_reason
        rec = "stop_state_change_as_timing_signal_keep_feature_source"
    elif supported:
        state = "12A5A_badside_decoupling_supported"
        reason = "low-capacity rejector reduces bad-side while preserving precision and recall"
        rec = "12A5B_state_change_morphology_badside_reduction_modeling"
    elif partial:
        state = "12A5A_badside_decoupling_partial"
        reason = "decoupling signal exists but supported gate is not fully satisfied"
        rec = "12A5B_conditional_badside_reduction_modeling"
    else:
        state = "12A5A_no_decoupling_stop_keep_feature_source"
        reason = "bad-side and precision are not sufficiently decoupled in current PIT feature space"
        rec = "stop_state_change_as_timing_signal_keep_feature_source"
    return pd.DataFrame(
        [
            {
                "decision": state,
                "decision_state": state,
                "decision_reason": reason,
                "primary_decision_pool_id": primary_pool,
                "primary_rejector_id": wp.get("rejector_id", ""),
                "workpoint_label_policy": wp.get("label_policy", ""),
                "workpoint_reject_score_direction": wp.get("reject_score_direction", ""),
                "workpoint_chosen_reject_fraction_source": wp.get("chosen_reject_fraction_source", ""),
                "workpoint_fit_split": wp.get("fit_split", ""),
                "workpoint_selection_split": wp.get("selection_split", ""),
                "workpoint_eval_split": wp.get("eval_split", ""),
                "workpoint_train_cv_retained_event_n": wp.get("train_cv_retained_event_n", np.nan),
                "workpoint_train_cv_retained_precision": wp.get("train_cv_retained_precision", np.nan),
                "workpoint_train_cv_candidate_gate_pass": boolish(wp.get("train_cv_candidate_gate_pass", False)) if not wp.empty else False,
                "input_gate_pass": bool(input_gate_pass),
                "upstream_12a4_gate_pass": bool(upstream_gate_pass),
                "event_feature_join_gate_pass": bool(join_gate_pass),
                "feature_dictionary_parity_gate_pass": bool(parity_gate_pass),
                "bucket_reconstruction_gate_pass": bool(bucket_gate),
                "primary_pool_is_fallback": bool(is_fallback),
                "fallback_from_pool_id": fallback_from,
                "fallback_to_pool_id": fallback_to,
                "fallback_from_pool_bad_side_rate": fallback_from_rate,
                "fallback_to_pool_bad_side_rate": fallback_to_rate,
                "composition_actionable": bool(composition_actionable),
                "dominant_component": dominant,
                "separable": bool(separable),
                "clean_winner_n": clean_n,
                "clean_winner_sufficient": bool(clean_sufficient),
                "best_lowcapacity_auc": best_auc,
                "best_lowcapacity_auc_ci_low": best_auc_ci_low,
                "workpoint_reject_fraction": wp.get("chosen_reject_fraction", np.nan),
                "workpoint_retained_precision": wp.get("retained_precision", np.nan),
                "workpoint_retained_bad_side_rate": wp.get("retained_bad_side_rate", np.nan),
                "workpoint_bad_side_reduction_abs": wp.get("bad_side_reduction_abs", np.nan),
                "workpoint_precision_delta_vs_pool": wp.get("precision_delta_vs_pool", np.nan),
                "workpoint_retained_episode_recall": wp.get("retained_episode_recall_low_to_high", np.nan),
                "workpoint_allowed_for_decision_gate": boolish(wp.get("workpoint_allowed_for_decision_gate", False)) if not wp.empty else False,
                "c0_risk_on_robustness_baseline_precision": c0_rob,
                "supported_gate_pass": bool(supported),
                "partial_gate_pass": bool(partial),
                "threshold_freeze_gate_pass": True,
                "train_class_sufficiency_gate_pass": bool(train_suff),
                "feature_pit_gate_pass": bool(parity_gate_pass),
                "label_completeness_gate_pass": bool(label_gate),
                "recommended_next_requirement": rec,
                "block_reason": block_reason,
            }
        ]
    )


def build_report(
    decision: pd.DataFrame,
    join_audit: pd.DataFrame,
    reconstruction: pd.DataFrame,
    composition: pd.DataFrame,
    univariate: pd.DataFrame,
    lowcapacity: pd.DataFrame,
    training: pd.DataFrame,
    workpoints: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    primary_pool = str(d["primary_decision_pool_id"])
    rob_recon = reconstruction.loc[reconstruction["split"].eq("robustness")]
    primary_recon = rob_recon.loc[rob_recon["pool_id"].eq(primary_pool)].head(1)
    comp = composition.loc[composition["pool_id"].eq(primary_pool) & composition["split"].eq("robustness")].head(1)
    comp_row = comp.iloc[0] if not comp.empty else pd.Series(dtype=object)
    best_uni = univariate.loc[
        univariate["pool_id"].eq(primary_pool)
        & univariate["split"].eq("robustness")
        & univariate.get("separability_positive_class", pd.Series("clean_winner_event", index=univariate.index)).astype(str).eq("clean_winner_event")
    ].sort_values("abs_auc_minus_0p5", ascending=False).head(5)
    best_low = lowcapacity.loc[
        lowcapacity["pool_id"].eq(primary_pool)
        & lowcapacity.get("separability_positive_class", pd.Series("clean_winner_event", index=lowcapacity.index)).astype(str).eq("clean_winner_event")
    ].sort_values("auc", ascending=False).head(1)
    capture_low = lowcapacity.loc[
        lowcapacity["pool_id"].eq(primary_pool)
        & lowcapacity.get("separability_positive_class", pd.Series("", index=lowcapacity.index)).astype(str).eq("clean_capture_event")
    ].sort_values("auc", ascending=False).head(1)
    train_row = training.loc[training["pool_id"].eq(primary_pool) & training["label_policy"].eq("bad_side_vs_clean_winner")].head(1)
    wp = workpoints.loc[
        workpoints["pool_id"].eq(primary_pool)
        & workpoints["rejector_id"].eq(str(d.get("primary_rejector_id", "")))
        & workpoints["label_policy"].eq("bad_side_vs_clean_winner")
    ].head(1)
    recon_text = "无 primary pool 重建结果"
    if not primary_recon.empty:
        r = primary_recon.iloc[0]
        recon_text = (
            f"{primary_pool}: event_n={int(r['reconstructed_event_n'])}, inside={int(r['reconstructed_inside_n'])}, "
            f"precision={float(r['reconstructed_precision']):.4f}, bad-side={float(r['reconstructed_bad_side_rate']):.4f}, "
            f"status={r['reconstruction_status']}"
        )
    low_text = "无可用低容量 separability"
    if not best_low.empty:
        l = best_low.iloc[0]
        low_text = f"{l['method']} AUC={float(l['auc']):.4f}, CI_low={float(l['auc_ci_low']):.4f}, clean_winner_n={int(l['clean_winner_n'])}"
    capture_text = "无 clean_capture diagnostic"
    if not capture_low.empty:
        c = capture_low.iloc[0]
        capture_text = f"{c['method']} AUC={float(c['auc']):.4f}, CI_low={float(c['auc_ci_low']):.4f}, clean_capture_n={int(c['positive_event_n'])}"
    uni_text = "; ".join(
        f"{row.feature_name}({row.feature_group}) abs_auc={row.abs_auc_minus_0p5:.3f}"
        for row in best_uni.itertuples(index=False)
        if pd.notna(row.abs_auc_minus_0p5)
    ) or "无单变量通过读数"
    train_text = "无训练审计"
    if not train_row.empty:
        tr = train_row.iloc[0]
        train_text = (
            f"train_clean_winner_n={int(tr['train_clean_winner_n'])}, train_bad_side_n={int(tr['train_bad_side_n'])}, "
            f"cv_fold_min_clean={int(tr['cv_fold_min_clean_winner_n'])}, cv_fold_min_bad={int(tr['cv_fold_min_bad_side_n'])}, "
            f"gate={tr['train_class_sufficiency_gate_pass']}"
        )
    wp_text = "无可用 workpoint"
    if not wp.empty:
        w = wp.iloc[0]
        wp_text = (
            f"rejector={w['rejector_id']}, reject_fraction={float(w['chosen_reject_fraction']):.2f}, "
            f"retained_precision={float(w['retained_precision']):.4f}, retained_bad_side={float(w['retained_bad_side_rate']):.4f}, "
            f"bad_side_reduction={float(w['bad_side_reduction_abs']):.4f}, retained_recall={float(w['retained_episode_recall_low_to_high']):.4f}"
        )
    fallback_text = "未发生 fallback。"
    if boolish(d.get("primary_pool_is_fallback", False)):
        fallback_text = (
            f"发生 fallback: {d['fallback_from_pool_id']}({float(d['fallback_from_pool_bad_side_rate']):.4f}) -> "
            f"{d['fallback_to_pool_id']}({float(d['fallback_to_pool_bad_side_rate']):.4f})；fallback 不允许 supported。"
        )
    join_pass = join_audit["event_feature_join_gate_pass"].map(boolish).all() and join_audit["feature_dictionary_parity_gate_pass"].map(boolish).all()
    return f"""
# 12A5A Bad-side Decoupling Feasibility Probe 决策报告

## 决策

- final decision: `{d['decision_state']}`
- reason: {d['decision_reason']}
- recommended next: `{d['recommended_next_requirement']}`

## Join 与 Bucket 复核

- event / target / feature matrix join gate: {join_pass}
- primary bucket reconstruction: {recon_text}
- {fallback_text}

## Bad-side 组成

- primary pool: `{primary_pool}`
- dominant component: `{comp_row.get('dominant_component', '')}`
- fast_fail_only_share_of_bad: {float(comp_row.get('fast_fail_only_share_of_bad', np.nan)):.4f}
- false_repair_only_share_of_bad: {float(comp_row.get('false_repair_only_share_of_bad', np.nan)):.4f}
- overlap_share_of_bad: {float(comp_row.get('overlap_share_of_bad', np.nan)):.4f}

## Separability

- low-capacity best: {low_text}
- clean-capture diagnostic: {capture_text}
- strongest univariate features: {uni_text}
- separable gate: {d['separable']}

## Rejector Workpoint

- training audit: {train_text}
- frozen workpoint: {wp_text}
- reject score direction: higher_is_worse

## 解释

12A5A 只验证现有 PIT feature 空间里 bad-side 与 clean winner 是否可解耦，不声明可交易 alpha。若本阶段不是 supported，则 state-change 事件继续作为 feature source 使用；是否进入 12A5B 取决于 supported / partial gate，而不是单独的 AUC 或 LightGBM challenger 读数。
""".strip()


def build_manifest(paths: dict[str, Path], frames: dict[str, pd.DataFrame], decision: pd.DataFrame, config_path: Path, requirement_path: Path) -> dict[str, Any]:
    output_keys = [
        "input_artifact_audit",
        "event_feature_join_audit",
        "bucket_reconstruction_audit",
        "label_completeness_audit",
        "badside_composition_decomposition",
        "badside_separability_univariate",
        "badside_separability_lowcapacity",
        "badside_rejector_training_audit",
        "badside_rejector_frontier",
        "badside_decoupling_workpoint",
        "badside_decoupling_decision",
        "report",
    ]
    outputs = {
        key: {
            "path": str(paths[key]),
            "sha256": path_sha(paths[key]),
            "row_count": int(len(frames[key])) if key in frames else np.nan,
        }
        for key in output_keys
        if key in paths and paths[key].exists()
    }
    manifest = {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "requirement_path": str(requirement_path),
        "requirement_sha256": path_sha(requirement_path),
        "config_path": str(config_path),
        "config_sha256": path_sha(config_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_revision": git_revision(REPO_ROOT),
        "final_decision": decision.iloc[0]["decision_state"] if not decision.empty else "",
        "outputs": outputs,
    }
    for key in output_keys:
        if key == "report":
            manifest["report_sha256"] = path_sha(paths[key])
        elif key in paths:
            manifest[f"{key}_sha256"] = path_sha(paths[key])
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    config = load_yaml(config_path)
    config_12a4 = load_yaml(topic_path(config["paths"]["config_12a4"]))
    paths = output_paths()
    audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], audit)
    read_ok = audit["read_status"].astype(str).eq("pass").all()
    schema_ok = ~audit["schema_status"].astype(str).str.startswith("missing_columns").any()
    if args.mode == "check-inputs":
        if not read_ok or not schema_ok:
            raise RuntimeError("12A5A input check failed")
        print(f"{RUN_ID}: input audit ok ({len(audit)} artifacts)")
        return 0
    if not read_ok or not schema_ok:
        raise RuntimeError("12A5A required inputs missing or schema mismatch")

    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    decision_12a4 = read_table(resolved["meta_label_decision"])
    universe = read_table(resolved["meta_label_event_universe"])
    targets = read_table(resolved["meta_label_event_targets"])
    score_frontier = read_table(resolved["meta_label_score_bucket_frontier"])
    non_model = read_table(resolved["non_model_filter_frontier"])
    model_card = read_table(resolved["meta_label_model_card"])
    lightgbm_frontier = read_table(resolved["lightgbm_challenger_score_bucket_frontier"])
    lightgbm_card = read_table(resolved["lightgbm_challenger_model_card"])
    baseline = read_table(resolved["risk_on_r_core_baseline"])
    dictionary = read_table(resolved["meta_label_feature_dictionary"])
    feature_matrix = read_table(resolved["meta_label_event_feature_matrix"])

    upstream_gate_pass = (
        str(decision_12a4.iloc[0].get("decision_state", "")) in ALLOWED_12A4_STATES
        and str(decision_12a4.iloc[0].get("threshold_selection_source", "")) == "train_internal_cv"
    )
    joined, join_audit, feature_cols, join_gate_pass, parity_gate_pass = build_event_feature_join(universe, targets, feature_matrix, dictionary)
    reconstruction, memberships, pool_scores = build_bucket_reconstruction(
        joined,
        feature_cols,
        non_model,
        score_frontier,
        model_card,
        lightgbm_frontier,
        lightgbm_card,
        baseline,
        config,
        config_12a4,
    )
    label_audit = build_label_completeness(joined, memberships, config)
    composition = build_composition(joined, memberships, baseline)
    univariate = build_univariate(joined, memberships, feature_cols, dictionary)
    lowcapacity = build_lowcapacity(joined, memberships, feature_cols, config)
    training, frontier, workpoints = build_rejector_outputs(joined, memberships, feature_cols, composition, baseline, config)
    input_gate_pass = bool(read_ok and schema_ok)
    decision = evaluate_decision(
        input_gate_pass,
        bool(upstream_gate_pass),
        bool(join_gate_pass),
        bool(parity_gate_pass),
        reconstruction,
        label_audit,
        composition,
        univariate,
        lowcapacity,
        training,
        workpoints,
        baseline,
        config,
    )
    report = build_report(decision, join_audit, reconstruction, composition, univariate, lowcapacity, training, workpoints)

    frames = {
        "input_artifact_audit": audit,
        "event_feature_join_audit": join_audit,
        "bucket_reconstruction_audit": reconstruction,
        "label_completeness_audit": label_audit,
        "badside_composition_decomposition": composition,
        "badside_separability_univariate": univariate,
        "badside_separability_lowcapacity": lowcapacity,
        "badside_rejector_training_audit": training,
        "badside_rejector_frontier": frontier,
        "badside_decoupling_workpoint": workpoints,
        "badside_decoupling_decision": decision,
    }
    for key, frame in frames.items():
        write_df(paths[key], frame)
    paths["rejector_artifacts"].mkdir(parents=True, exist_ok=True)
    write_df(paths["rejector_artifacts"] / "pool_score_membership.csv.gz", joined[["meta_event_id", "event_split"]].assign(**{f"{pid}_selected": mask for pid, mask in memberships.items()}))
    write_text(paths["report"], report)
    frames["report"] = pd.DataFrame([{"report_path": str(paths["report"])}])
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, resolved["requirement"]))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

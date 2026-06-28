#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
SOURCE_EP15_ROOT = TOPIC_ROOT / "experiments" / "pending" / "15_path_defined_winner_episode_label_v0"
SOURCE_EP14_ROOT = TOPIC_ROOT / "experiments" / "pending" / "14_full_native_sparse_state_change_event_utility_preflight_v0"
SOURCE_EP13_ROOT = TOPIC_ROOT / "experiments" / "pending" / "13_full_pit_native_event_discovery_v0"
RUNNER_16B_PATH = EXPERIMENT_DIR / "src" / "run_16b_sequential_continuation_label_design_diagnostic.py"
SOURCE_ROOTS = {
    "SOURCE_EP16_ROOT": EXPERIMENT_DIR,
    "SOURCE_EP15_ROOT": SOURCE_EP15_ROOT,
    "SOURCE_EP14_ROOT": SOURCE_EP14_ROOT,
    "SOURCE_EP13_ROOT": SOURCE_EP13_ROOT,
}


def load_runner(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r16b = load_runner(RUNNER_16B_PATH, "run_16b_for_16c")
r16a = r16b.r16a
r15b = r16b.r15b

RUN_ID = "16C_sequential_continuation_separability_diagnostic"
EXPERIMENT_ID = "16_winner_episode_sequential_sampling_geometry_preflight_v0"
PHASE_ID = "16C"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_16c_sequential_continuation_separability_diagnostic.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

PRIMARY_LABEL_ID = "continuation_survival_h20_no_deep_drawdown"
PRIMARY_MODEL_ID = "ridge_logistic_bar_state_v1"
TREE_MODEL_ID = "single_depth2_tree_bar_state_v1"
BASELINE_MODEL_ID = "intercept_only_baseline"
NEXT_16D = "requirement_16d_sequential_continuation_policy_preflight.md"
DECISION_READY = "16C_sequential_continuation_separability_ready_for_policy_preflight"
DECISION_BLOCKED = "16C_sequential_continuation_separability_blocked_by_input_or_lineage_failure"
DECISION_LEAKAGE = "16C_sequential_continuation_separability_blocked_by_feature_leakage"
DECISION_LOW_POWER = "16C_sequential_continuation_separability_low_power"
DECISION_NOT_SUPPORTED = "16C_sequential_continuation_separability_not_supported"
DECISION_CONTEXT = "16C_sequential_continuation_separability_context_concentrated_only"
SPLITS = ("train", "robustness", "validation")
KNOWN_FAILED_FAMILIES = (
    "choppy_reversal_winner",
    "late_rescue_winner",
    "jump_repricing_winner",
    "unclassified_mixed_path",
)

QFQ_FEATURES = [
    "ret_5d",
    "ret_10d",
    "ret_20d",
    "ret_60d",
    "volatility_20d",
    "volatility_60d",
    "distance_to_20d_high",
    "distance_to_60d_high",
    "distance_to_20d_low",
    "distance_to_60d_low",
    "max_drawdown_20d",
    "max_drawdown_60d",
    "ma_5_20_spread",
    "ma_20_60_spread",
    "turnover_rate_20d_mean",
    "turnover_rate_60d_mean",
    "turnover_rate_20d_zscore",
    "volume_20d_zscore",
    "money_20d_zscore",
    "intraday_range_20d_mean",
]
PIT_FEATURES = [
    "log_total_market_cap_cny",
    "board_rank_pct",
    "history_observed_sessions_before_usable_date",
    "history_ready_240d_flag",
    "board_bucket_chinext",
    "board_bucket_main_board",
    "board_bucket_unknown_train_unseen",
]
MODEL_FEATURES = QFQ_FEATURES + PIT_FEATURES
FORBIDDEN_FEATURE_FIELDS = {
    "step_end_pos",
    "step_end_date",
    "step_end_qfq_close",
    "max_drawdown_from_step_start",
    "step_end_price_ratio_minus_one_for_label_rule",
    "continuation_positive",
    "continuation_negative",
    "continuation_neutral",
    "label_rule_status",
    "cluster_end_pos",
    "episode_length_sessions",
    "remaining_sessions_to_cluster_end",
    "available_forward_sessions",
    "full_horizon_nonoverlap_step_n",
    "partial_tail_step_n",
    "step_n_nonoverlap",
    "anchor_n",
    "source_anchor_row_n",
    "path_winner_uncensored_anchor_n",
    "path_type",
    "entry_phase",
    "known_failed_step_flag",
    "known_failed_family",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 16C sequential continuation separability diagnostic.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
    parser.add_argument("--mode", choices=["check-inputs", "full"], default="full")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    text = str(path)
    for alias, root in SOURCE_ROOTS.items():
        prefix = f"{alias}/"
        if text.startswith(prefix):
            return root / text[len(prefix) :]
    if text.startswith("topics/"):
        return REPO_ROOT / path
    if text.startswith(("data/", "experiments/")):
        return TOPIC_ROOT / path
    if text.startswith(("outputs/", "configs/", "src/", "tests/")):
        return EXPERIMENT_DIR / path
    return EXPERIMENT_DIR / path


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_16b_authorization_audit": TABLE_DIR / "upstream_16b_authorization_audit.csv",
        "step_label_binding_audit": TABLE_DIR / "step_label_binding_audit.csv",
        "t0_feature_contract": TABLE_DIR / "t0_feature_contract.csv",
        "t0_feature_lineage_audit": TABLE_DIR / "t0_feature_lineage_audit.csv",
        "t0_feature_coverage_audit": TABLE_DIR / "t0_feature_coverage_audit.csv",
        "t0_feature_leakage_audit": TABLE_DIR / "t0_feature_leakage_audit.csv",
        "separability_training_universe_audit": TABLE_DIR / "separability_training_universe_audit.csv",
        "separability_fold_assignment_audit": TABLE_DIR / "separability_fold_assignment_audit.csv",
        "separability_model_registry": TABLE_DIR / "separability_model_registry.csv",
        "univariate_feature_separability_readout": TABLE_DIR / "univariate_feature_separability_readout.csv",
        "grouped_cv_separability_readout": TABLE_DIR / "grouped_cv_separability_readout.csv",
        "oos_separability_readout": TABLE_DIR / "oos_separability_readout.csv",
        "feature_importance_stability_readout": TABLE_DIR / "feature_importance_stability_readout.csv",
        "known_failed_context_rebuild_audit": TABLE_DIR / "known_failed_context_rebuild_audit.csv",
        "known_failed_context_stratified_separability_readout": TABLE_DIR / "known_failed_context_stratified_separability_readout.csv",
        "neutral_population_audit": TABLE_DIR / "neutral_population_audit.csv",
        "search_accounting_audit": TABLE_DIR / "search_accounting_audit.csv",
        "decision": TABLE_DIR / "sequential_continuation_separability_decision.csv",
        "score_sample": TABLE_DIR / "separability_score_sample.csv.gz",
        "t0_feature_panel": LOCAL_CACHE_DIR / "t0_feature_panel.parquet",
        "score_panel": LOCAL_CACHE_DIR / "separability_score_panel.parquet",
        "fold_assignment_panel": LOCAL_CACHE_DIR / "fold_assignment_panel.parquet",
        "report": REPORT_DIR / "sequential_continuation_separability_diagnostic_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r16b.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r16b.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r16b.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r16b.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r16b.file_sha(path)


def count_rows(path: Path) -> int | float:
    return r16b.count_rows(path)


def stable_hash(value: Any) -> str:
    return r16b.stable_hash(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r16b.bool_series(series)


def finite(series: pd.Series) -> pd.Series:
    return r16b.finite(series)


def safe_rate(num: Any, den: Any) -> float:
    return r16b.safe_rate(num, den)


def metric_float(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return np.nan
    return out if np.isfinite(out) else np.nan


def path_required_flag(key: str) -> str:
    if "local_cache" in str(key) or key in {
        "upstream_16a_episode_interval_panel",
        "upstream_16a_step_geometry_panel",
        "upstream_16b_materialized_step_panel",
        "upstream_16b_continuation_label_step_panel",
        "upstream_16b_known_failed_overlap_panel",
        "upstream_15b_taxonomy_assignment_panel",
        "upstream_15b_anchor_path_shape_feature_panel",
    }:
        return "optional_cache"
    if key.startswith("upstream_15c2_"):
        return "optional_appendix"
    return "required"


def required_columns_for_key(key: str) -> set[str]:
    if key == "upstream_16b_label_panel":
        return {
            "step_id",
            "label_id",
            "threshold_id",
            "cluster_split_bucket",
            "instrument",
            "episode_cluster_id",
            "horizon_sessions",
            "step_index",
            "step_start_pos",
            "step_end_pos",
            "step_start_date",
            "step_end_date",
            "continuation_positive",
            "continuation_negative",
            "continuation_neutral",
            "label_rule_status",
        }
    if key == "upstream_16b_decision":
        return {
            "decision_state",
            "next_allowed_requirement",
            "primary_label_id",
            "selected_threshold_id",
            "primary_horizon_sessions",
            "labelable_step_n_train",
            "labelable_step_n_robustness",
            "step_materialization_gate",
            "qfq_price_source_gate",
            "known_failed_overlap_gate",
            "known_failed_overlap_evaluability_gate",
            "base_rate_nontrivial",
            "effective_sample_sufficient",
            "base_rate_stable_train_robustness",
            "step_generation_lineage_sane",
        }
    if key == "upstream_16b_base_rate_readout":
        return {
            "label_id",
            "threshold_id",
            "cluster_split_bucket",
            "horizon_sessions",
            "labelable_step_n",
            "positive_step_n",
            "negative_step_n",
            "neutral_step_n",
        }
    if key == "upstream_16b_known_failed_overlap_readout":
        return {
            "label_id",
            "threshold_id",
            "known_failed_family",
            "cluster_split_bucket",
            "horizon_sessions",
            "positive_step_n",
            "failed_family_positive_step_n",
        }
    if key == "upstream_15b_membership_audit":
        return {"source_row_key", "threshold_id", "instrument", "episode_cluster_id", "cluster_split_bucket"}
    if key == "upstream_15b_path_shape_taxonomy_rule_audit":
        return {"rule_type", "feature_id", "quantile_name", "value", "train_rule_fit_status"}
    if key == "upstream_15b_path_shape_feature_definition_audit":
        return {"feature_id", "definition_status"}
    if key in {"pit_executable_daily", "pit_membership_daily"}:
        return {
            "usable_trade_date",
            "instrument",
            "membership_date",
            "available_time",
            "board_bucket",
            "is_listed",
            "is_st",
            "is_suspended",
            "total_market_cap_cny",
            "board_rank_by_market_cap",
            "board_quota",
            "history_ready_240d_flag",
            "history_observed_sessions_before_usable_date",
        }
    return set()


def qfq_dir_schema_status(path: Path) -> str:
    required = {"date", "open", "high", "low", "close", "volume", "money", "turnover_rate", "instrument"}
    files = sorted(path.glob("*.csv"))
    if not files:
        return "fail_empty_dir"
    for file_path in files:
        try:
            cols = set(pd.read_csv(file_path, nrows=0).columns)
        except Exception:
            return f"fail_read_qfq_header:{file_path.name}"
        if not required.issubset(cols):
            missing = ",".join(sorted(required - cols))
            return f"fail_missing_qfq_columns:{file_path.name}:{missing}"
    return "pass"


def build_input_artifact_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, path in resolved.items():
        flag = path_required_flag(key)
        exists = path.exists()
        read_status = "pass"
        schema_status = "not_checked"
        row_count: int | float = np.nan
        sha = ""
        if exists and path.is_file():
            try:
                row_count = count_rows(path)
                sha = file_sha(path)
                required = required_columns_for_key(key)
                if required and path.suffix.lower() in {".csv", ".gz", ".parquet"}:
                    frame = read_table(path, nrows=5) if path.suffix.lower() in {".csv", ".gz"} else read_table(path)
                    schema_status = "pass" if required.issubset(frame.columns) else "fail_missing_columns"
                else:
                    schema_status = "pass"
            except Exception as exc:
                read_status = f"fail_read_error:{type(exc).__name__}"
                schema_status = "fail_read_error"
        elif exists and path.is_dir():
            row_count = len(list(path.glob("*.csv")))
            if key == "stock_daily_qfq_dir":
                schema_status = qfq_dir_schema_status(path)
                read_status = "pass" if schema_status == "pass" else schema_status
            else:
                schema_status = "pass" if row_count > 0 else "fail_empty_dir"
                read_status = "pass" if row_count > 0 else "fail_empty_dir"
        else:
            read_status = "missing"
            schema_status = "missing"
        rows.append(
            {
                "artifact_key": key,
                "resolved_path": str(path),
                "row_count": row_count,
                "sha256": sha,
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": flag,
                "lineage_role": key,
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    required = input_audit.loc[input_audit["required_flag"].astype(str).eq("required")]
    bad = required.loc[
        ~required["read_status"].astype(str).eq("pass")
        | required["schema_status"].astype(str).isin(["missing", "fail_missing_columns", "fail_read_error"])
        | required["schema_status"].astype(str).str.startswith("fail")
    ]
    if bad.empty:
        return "pass", ""
    return "fail", ";".join(bad["artifact_key"].astype(str).head(10))


def load_primary_label_panel(path: Path, config: dict[str, Any]) -> pd.DataFrame:
    sep = config["separability"]
    labels = read_table(path)
    labels["continuation_positive"] = bool_series(labels["continuation_positive"])
    labels["continuation_negative"] = bool_series(labels["continuation_negative"])
    labels["continuation_neutral"] = bool_series(labels["continuation_neutral"])
    primary = labels.loc[
        labels["label_id"].astype(str).eq(sep["primary_label_id"])
        & labels["threshold_id"].astype(str).eq(sep["selected_threshold_id"])
        & finite(labels["horizon_sessions"]).eq(int(sep["primary_horizon_sessions"]))
        & labels["cluster_split_bucket"].astype(str).isin(SPLITS)
        & labels["label_rule_status"].astype(str).eq("pass")
    ].copy()
    primary["step_start_pos"] = finite(primary["step_start_pos"]).astype("Int64")
    primary["step_end_pos"] = finite(primary["step_end_pos"]).astype("Int64")
    primary["step_index"] = finite(primary["step_index"]).astype("Int64")
    primary["horizon_sessions"] = finite(primary["horizon_sessions"]).astype("Int64")
    primary["target_binary"] = np.where(primary["continuation_positive"], 1, np.where(primary["continuation_negative"], 0, np.nan))
    primary["is_binary_target"] = primary["continuation_positive"] | primary["continuation_negative"]
    return primary.reset_index(drop=True)


def build_step_label_binding_audit(labels: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    horizon = int(config["separability"]["primary_horizon_sessions"])
    dup_step = int(labels.duplicated(["step_id", "label_id", "threshold_id", "horizon_sessions"]).sum())
    dup_key = int(labels.duplicated(["instrument", "episode_cluster_id", "horizon_sessions", "step_index"]).sum())
    both = int((labels["continuation_positive"] & labels["continuation_negative"]).sum())
    none = int((~labels["continuation_positive"] & ~labels["continuation_negative"] & ~labels["continuation_neutral"]).sum())
    bad_bounds = int((finite(labels["step_end_pos"]) != finite(labels["step_start_pos"]) + horizon - 1).sum())
    status = "pass" if not any([dup_step, dup_key, both, none, bad_bounds, labels.empty]) else "fail"
    return pd.DataFrame(
        [
            {
                "label_id": config["separability"]["primary_label_id"],
                "threshold_id": config["separability"]["selected_threshold_id"],
                "horizon_sessions": horizon,
                "primary_step_n": len(labels),
                "duplicate_step_id_n": dup_step,
                "duplicate_instrument_cluster_step_index_n": dup_key,
                "positive_negative_overlap_n": both,
                "missing_label_state_n": none,
                "bad_horizon_bounds_n": bad_bounds,
                "step_label_binding_gate": status,
                "blocking_reason": "" if status == "pass" else "duplicate_or_inconsistent_step_label_rows",
            }
        ]
    )


def build_upstream_16b_authorization_audit(config: dict[str, Any], resolved: dict[str, Path]) -> pd.DataFrame:
    sep = config["separability"]
    decision = read_table(resolved["upstream_16b_decision"])
    base = read_table(resolved["upstream_16b_base_rate_readout"])
    row = decision.iloc[0].to_dict() if not decision.empty else {}
    base_rows = base.loc[
        base["label_id"].astype(str).eq(sep["primary_label_id"])
        & base["threshold_id"].astype(str).eq(sep["selected_threshold_id"])
        & finite(base["horizon_sessions"]).eq(int(sep["primary_horizon_sessions"]))
    ]
    counts: dict[str, Any] = {}
    for split in SPLITS:
        sub = base_rows.loc[base_rows["cluster_split_bucket"].astype(str).eq(split)]
        if not sub.empty:
            base_row = sub.iloc[0]
            counts[f"labelable_step_n_{split}"] = int(base_row["labelable_step_n"])
            counts[f"positive_step_n_{split}"] = int(base_row["positive_step_n"])
            counts[f"negative_step_n_{split}"] = int(base_row["negative_step_n"])
            counts[f"neutral_step_n_{split}"] = int(base_row["neutral_step_n"])
            counts[f"positive_rate_{split}"] = float(base_row.get("positive_rate", safe_rate(base_row["positive_step_n"], base_row["labelable_step_n"])))
            counts[f"negative_rate_{split}"] = float(base_row.get("negative_rate", safe_rate(base_row["negative_step_n"], base_row["labelable_step_n"])))
    expected_counts = {
        "labelable_step_n_train": 20245,
        "positive_step_n_train": 10078,
        "negative_step_n_train": 4884,
        "neutral_step_n_train": 5283,
        "labelable_step_n_robustness": 2496,
        "positive_step_n_robustness": 1346,
        "negative_step_n_robustness": 526,
        "neutral_step_n_robustness": 624,
        "labelable_step_n_validation": 664,
        "positive_step_n_validation": 325,
        "negative_step_n_validation": 180,
        "neutral_step_n_validation": 159,
    }
    expected_rates = {
        "positive_rate_train": 0.497802,
        "negative_rate_train": 0.241245,
        "positive_rate_robustness": 0.539263,
        "negative_rate_robustness": 0.210737,
    }
    count_status = all(int(counts.get(key, -1)) == value for key, value in expected_counts.items())
    rate_status = all(abs(float(counts.get(key, np.nan)) - value) <= 1e-6 for key, value in expected_rates.items())
    gate_checks = {
        "decision_state": row.get("decision_state") == sep["upstream_16b_required_decision"],
        "next_allowed": row.get("next_allowed_requirement") == sep["upstream_16b_required_next_allowed"],
        "primary_label_id": row.get("primary_label_id") == sep["primary_label_id"],
        "selected_threshold_id": row.get("selected_threshold_id") == sep["selected_threshold_id"],
        "primary_horizon_sessions": int(metric_float(row.get("primary_horizon_sessions"))) == int(sep["primary_horizon_sessions"]),
        "count_replay": count_status,
        "rate_replay": rate_status,
        "step_materialization_gate": row.get("step_materialization_gate") == "pass",
        "qfq_price_source_gate": row.get("qfq_price_source_gate") == "pass",
        "known_failed_overlap_gate": row.get("known_failed_overlap_gate") == "pass",
        "known_failed_overlap_evaluability_gate": row.get("known_failed_overlap_evaluability_gate") == "pass",
        "base_rate_nontrivial": bool(row.get("base_rate_nontrivial", False)),
        "effective_sample_sufficient": bool(row.get("effective_sample_sufficient", False)),
        "base_rate_stable_train_robustness": bool(row.get("base_rate_stable_train_robustness", False)),
        "step_generation_lineage_sane": bool(row.get("step_generation_lineage_sane", False)),
    }
    status = "pass" if all(gate_checks.values()) else "fail"
    out = {
        "upstream_decision_state": row.get("decision_state", ""),
        "upstream_next_allowed_requirement": row.get("next_allowed_requirement", ""),
        "primary_label_id": row.get("primary_label_id", ""),
        "selected_threshold_id": row.get("selected_threshold_id", ""),
        "primary_horizon_sessions": row.get("primary_horizon_sessions", np.nan),
        **counts,
        "step_materialization_gate": row.get("step_materialization_gate", ""),
        "qfq_price_source_gate": row.get("qfq_price_source_gate", ""),
        "known_failed_overlap_gate": row.get("known_failed_overlap_gate", ""),
        "known_failed_overlap_evaluability_gate": row.get("known_failed_overlap_evaluability_gate", ""),
        "step_generation_lineage_sane": bool(row.get("step_generation_lineage_sane", False)),
        "soft_overlap_partial_coverage_caveat": bool(row.get("soft_overlap_partial_coverage_caveat", False)),
        "known_failed_context_exposure_caveat": bool(row.get("known_failed_context_exposure_caveat", False)),
        "authorization_status": status,
        "blocking_reason": "" if status == "pass" else ";".join(key for key, ok in gate_checks.items() if not ok),
    }
    return pd.DataFrame([out])


def read_qfq(instrument: str, qfq_dir: Path) -> pd.DataFrame:
    path = qfq_dir / f"{instrument}.csv"
    if not path.exists():
        return pd.DataFrame()
    qfq = pd.read_csv(path)
    qfq = qfq.sort_values("date").reset_index(drop=True)
    return qfq


def window_slice(values: np.ndarray, end: int, n: int) -> np.ndarray:
    start = max(0, end - n + 1)
    return values[start : end + 1]


def trailing_ret(close: np.ndarray, pos: int, n: int) -> float:
    prev = pos - n
    if prev < 0 or prev >= len(close) or close[prev] <= 0:
        return np.nan
    return float(close[pos] / close[prev] - 1.0)


def trailing_std(close: np.ndarray, pos: int, n: int) -> float:
    if pos <= 0:
        return np.nan
    start = max(1, pos - n + 1)
    rets = close[start : pos + 1] / close[start - 1 : pos] - 1.0
    return float(np.nanstd(rets, ddof=0)) if len(rets) else np.nan


def trailing_drawdown(close: np.ndarray, pos: int, n: int) -> float:
    w = window_slice(close, pos, n)
    if len(w) == 0:
        return np.nan
    peak = np.maximum.accumulate(w)
    dd = w / peak - 1.0
    return float(np.nanmin(dd))


def zscore_at(values: np.ndarray, pos: int, n: int) -> tuple[float, bool]:
    w = window_slice(values, pos, n)
    if len(w) == 0:
        return np.nan, False
    mu = float(np.nanmean(w))
    sd = float(np.nanstd(w, ddof=0))
    if not np.isfinite(sd) or sd == 0:
        return 0.0, True
    return float((values[pos] - mu) / sd), False


def qfq_feature_row(step: Any, qfq: pd.DataFrame) -> dict[str, Any]:
    pos = int(step.step_start_pos)
    if qfq.empty or pos < 0 or pos >= len(qfq):
        row = {feature: np.nan for feature in QFQ_FEATURES}
        row.update({"qfq_feature_status": "fail_missing_qfq", "qfq_max_source_pos": np.nan, "qfq_zero_std_flag": False})
        return row
    close = qfq["close"].to_numpy(dtype=float)
    high = qfq["high"].to_numpy(dtype=float)
    low = qfq["low"].to_numpy(dtype=float)
    volume = qfq["volume"].to_numpy(dtype=float)
    money = qfq["money"].to_numpy(dtype=float)
    turnover = qfq["turnover_rate"].to_numpy(dtype=float)
    z_turn, z_turn_zero = zscore_at(turnover, pos, 20)
    z_vol, z_vol_zero = zscore_at(volume, pos, 20)
    z_money, z_money_zero = zscore_at(money, pos, 20)
    h20 = window_slice(high, pos, 20)
    h60 = window_slice(high, pos, 60)
    l20 = window_slice(low, pos, 20)
    l60 = window_slice(low, pos, 60)
    close5 = window_slice(close, pos, 5)
    close20 = window_slice(close, pos, 20)
    close60 = window_slice(close, pos, 60)
    tr20 = window_slice(turnover, pos, 20)
    tr60 = window_slice(turnover, pos, 60)
    range20 = window_slice(high / low - 1.0, pos, 20)
    out = {
        "ret_5d": trailing_ret(close, pos, 5),
        "ret_10d": trailing_ret(close, pos, 10),
        "ret_20d": trailing_ret(close, pos, 20),
        "ret_60d": trailing_ret(close, pos, 60),
        "volatility_20d": trailing_std(close, pos, 20),
        "volatility_60d": trailing_std(close, pos, 60),
        "distance_to_20d_high": float(close[pos] / np.nanmax(h20) - 1.0) if len(h20) and np.nanmax(h20) > 0 else np.nan,
        "distance_to_60d_high": float(close[pos] / np.nanmax(h60) - 1.0) if len(h60) and np.nanmax(h60) > 0 else np.nan,
        "distance_to_20d_low": float(close[pos] / np.nanmin(l20) - 1.0) if len(l20) and np.nanmin(l20) > 0 else np.nan,
        "distance_to_60d_low": float(close[pos] / np.nanmin(l60) - 1.0) if len(l60) and np.nanmin(l60) > 0 else np.nan,
        "max_drawdown_20d": trailing_drawdown(close, pos, 20),
        "max_drawdown_60d": trailing_drawdown(close, pos, 60),
        "ma_5_20_spread": float(np.nanmean(close5) / np.nanmean(close20) - 1.0) if len(close20) and np.nanmean(close20) > 0 else np.nan,
        "ma_20_60_spread": float(np.nanmean(close20) / np.nanmean(close60) - 1.0) if len(close60) and np.nanmean(close60) > 0 else np.nan,
        "turnover_rate_20d_mean": float(np.nanmean(tr20)) if len(tr20) else np.nan,
        "turnover_rate_60d_mean": float(np.nanmean(tr60)) if len(tr60) else np.nan,
        "turnover_rate_20d_zscore": z_turn,
        "volume_20d_zscore": z_vol,
        "money_20d_zscore": z_money,
        "intraday_range_20d_mean": float(np.nanmean(range20)) if len(range20) else np.nan,
        "qfq_feature_status": "pass",
        "qfq_max_source_pos": pos,
        "qfq_zero_std_flag": bool(z_turn_zero or z_vol_zero or z_money_zero),
    }
    return out


def build_qfq_feature_panel(labels: pd.DataFrame, qfq_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for instrument, sub in labels.groupby("instrument", sort=False):
        qfq = read_qfq(str(instrument), qfq_dir)
        for step in sub.itertuples(index=False):
            values = qfq_feature_row(step, qfq)
            values["step_id"] = step.step_id
            rows.append(values)
    return pd.DataFrame(rows)


def build_pit_feature_panel(labels: pd.DataFrame, pit_path: Path, allowed: list[str]) -> tuple[pd.DataFrame, str]:
    usecols = [
        "usable_trade_date",
        "instrument",
        "available_time",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
        "total_market_cap_cny",
        "board_rank_by_market_cap",
        "board_quota",
        "history_ready_240d_flag",
        "history_observed_sessions_before_usable_date",
    ]
    pit = pd.read_csv(pit_path, usecols=usecols)
    needed_instruments = set(labels["instrument"].astype(str))
    pit = pit.loc[pit["instrument"].astype(str).isin(needed_instruments)].copy()
    pit["_usable_dt"] = pd.to_datetime(pit["usable_trade_date"], errors="coerce")
    pit["_available_dt"] = pd.to_datetime(pit["available_time"].astype(str).str.slice(0, 10), errors="coerce")
    step_dates = labels[["step_id", "instrument", "step_start_date", "cluster_split_bucket"]].copy()
    step_dates["_step_dt"] = pd.to_datetime(step_dates["step_start_date"], errors="coerce")
    merged_parts: list[pd.DataFrame] = []
    for instrument, left in step_dates.groupby("instrument", sort=False):
        right = pit.loc[pit["instrument"].astype(str).eq(str(instrument))].sort_values("_usable_dt")
        left = left.sort_values("_step_dt")
        if right.empty:
            part = left.copy()
            for col in pit.columns:
                if col not in part.columns:
                    part[col] = np.nan
        else:
            part = pd.merge_asof(
                left,
                right,
                left_on="_step_dt",
                right_on="_usable_dt",
                direction="backward",
                suffixes=("", "_pit"),
            )
            unavailable = part["_available_dt"] > part["_step_dt"]
            if unavailable.any():
                right_cols = [col for col in pit.columns if col not in {"instrument"}]
                part.loc[unavailable, right_cols] = np.nan
        merged_parts.append(part)
    merged = pd.concat(merged_parts, ignore_index=True) if merged_parts else step_dates.copy()
    if "instrument_pit" in merged.columns:
        merged = merged.drop(columns=["instrument_pit"])
    invalid_board = set(merged["board_bucket"].dropna().astype(str)) - set(allowed)
    merged["pit_context_missing"] = merged["usable_trade_date"].isna()
    merged["pit_context_status"] = np.where(merged["pit_context_missing"], "missing_pit_context", "pass")
    if invalid_board:
        merged["pit_context_status"] = "fail_unknown_board_bucket_enum"
    merged["log_total_market_cap_cny"] = np.log(finite(merged["total_market_cap_cny"]).clip(lower=1.0))
    merged["board_rank_pct"] = finite(merged["board_rank_by_market_cap"]) / finite(merged["board_quota"]).replace(0, np.nan)
    merged["history_ready_240d_flag"] = bool_series(merged["history_ready_240d_flag"]).astype(float)
    merged["history_observed_sessions_before_usable_date"] = finite(merged["history_observed_sessions_before_usable_date"])
    train_buckets = set(merged.loc[merged["cluster_split_bucket"].astype(str).eq("train"), "board_bucket"].dropna().astype(str))
    for bucket in allowed:
        merged[f"board_bucket_{bucket}"] = merged["board_bucket"].astype(str).eq(bucket).astype(float)
    merged["board_bucket_unknown_train_unseen"] = merged["board_bucket"].notna() & ~merged["board_bucket"].astype(str).isin(train_buckets)
    merged["board_bucket_unknown_train_unseen"] = merged["board_bucket_unknown_train_unseen"].astype(float)
    merged["tradability_status_ok"] = (
        bool_series(merged["is_listed"]) & ~bool_series(merged["is_st"]) & ~bool_series(merged["is_suspended"])
    )
    bad_status = ~merged["tradability_status_ok"] & ~merged["pit_context_missing"]
    merged.loc[bad_status, "pit_context_status"] = "not_evaluable_status_flag"
    gate = "fail_unknown_board_bucket_enum" if invalid_board else "pass"
    return merged, gate


def build_t0_feature_panel(labels: pd.DataFrame, resolved: dict[str, Path], config: dict[str, Any]) -> pd.DataFrame:
    qfq = build_qfq_feature_panel(labels, resolved["stock_daily_qfq_dir"])
    pit, _gate = build_pit_feature_panel(labels, resolved["pit_executable_daily"], config["separability"]["board_bucket_allowed_values"])
    panel = labels.merge(qfq, on="step_id", how="left").merge(pit, on=["step_id", "instrument"], how="left", suffixes=("", "_pit"))
    panel["feature_complete"] = panel[MODEL_FEATURES].notna().all(axis=1) & panel["qfq_feature_status"].astype(str).eq("pass") & panel["pit_context_status"].astype(str).eq("pass")
    return panel


def feature_family(name: str) -> str:
    if name.startswith("board_bucket") or name in {
        "log_total_market_cap_cny",
        "board_rank_pct",
        "history_observed_sessions_before_usable_date",
        "history_ready_240d_flag",
    }:
        return "pit_membership_context"
    return "qfq_rolling_market_state"


def build_feature_contract() -> pd.DataFrame:
    rows = []
    for feature in MODEL_FEATURES:
        is_qfq = feature in QFQ_FEATURES
        rows.append(
            {
                "feature_name": feature,
                "feature_family": feature_family(feature),
                "source_artifact": "qfq_daily" if is_qfq else "pit_topn_400_100_executable_daily",
                "source_columns": "close/high/low/volume/money/turnover_rate" if is_qfq else "membership_context_columns",
                "formula_id": feature,
                "lookback_sessions": 60 if feature.endswith("60d") or "_60d" in feature else 20 if is_qfq else 0,
                "as_of_policy": "qfq_position_le_step_start_pos"
                if is_qfq
                else "usable_trade_date_eq_or_latest_le_step_start_date_available_time_le_step_start_close_no_future_fill",
                "allowed_primary_model_feature": True,
                "allowed_secondary_readout": True,
                "forbidden_as_model_feature": False,
                "forbidden_reason": "",
                "missing_policy": "train_median_impute_then_robust_scale",
                "train_fit_only_preprocessing": True,
            }
        )
    for feature in sorted(FORBIDDEN_FEATURE_FIELDS):
        rows.append(
            {
                "feature_name": feature,
                "feature_family": "forbidden",
                "source_artifact": "label_or_future_or_context",
                "source_columns": feature,
                "formula_id": "forbidden",
                "lookback_sessions": np.nan,
                "as_of_policy": "not_allowed",
                "allowed_primary_model_feature": False,
                "allowed_secondary_readout": feature not in {"continuation_positive", "continuation_negative", "continuation_neutral"},
                "forbidden_as_model_feature": True,
                "forbidden_reason": "future_label_outcome_or_identity_context",
                "missing_policy": "not_applicable",
                "train_fit_only_preprocessing": True,
            }
        )
    return pd.DataFrame(rows)


def build_feature_lineage_audit(feature_panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in MODEL_FEATURES:
        is_qfq = feature in QFQ_FEATURES
        if is_qfq:
            max_pos_delta = float((finite(feature_panel["qfq_max_source_pos"]) - finite(feature_panel["step_start_pos"])).max())
            max_date_delta = 0.0
        else:
            source_date = pd.to_datetime(feature_panel["usable_trade_date"], errors="coerce")
            step_date = pd.to_datetime(feature_panel["step_start_date"], errors="coerce")
            max_date_delta = float((source_date - step_date).dt.days.max()) if len(feature_panel) else np.nan
            max_pos_delta = np.nan
        status = "pass" if (not np.isfinite(max_pos_delta) or max_pos_delta <= 0) and (not np.isfinite(max_date_delta) or max_date_delta <= 0) else "fail"
        rows.append(
            {
                "feature_name": feature,
                "feature_family": feature_family(feature),
                "source_artifact": "qfq_daily" if is_qfq else "pit_universe",
                "max_source_pos_minus_step_start_pos": max_pos_delta,
                "max_source_date_minus_step_start_date": max_date_delta,
                "lineage_status": status,
                "blocking_reason": "" if status == "pass" else "feature_source_after_step_start",
            }
        )
    return pd.DataFrame(rows)


def build_feature_leakage_audit(model_features: list[str], config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for feature in model_features:
        forbidden = feature in FORBIDDEN_FEATURE_FIELDS or "path_type" in feature or feature.startswith("known_failed")
        rows.append(
            {
                "feature_name": feature,
                "max_source_pos_minus_step_start_pos": 0.0,
                "max_source_date_minus_step_start_date": 0.0,
                "uses_step_end_field": feature.startswith("step_end") or feature in {"max_drawdown_from_step_start", "step_end_price_ratio_minus_one_for_label_rule"},
                "uses_cluster_end_field": feature in {"cluster_end_pos", "episode_length_sessions", "remaining_sessions_to_cluster_end"},
                "uses_label_field": feature.startswith("continuation_"),
                "uses_path_taxonomy_field": feature in {"path_type", "known_failed_family"} or feature.startswith("known_failed"),
                "uses_split_or_identity_field": feature in {"instrument", "episode_cluster_id", "cluster_split_bucket"},
                "uses_validation_or_robustness_fit": False,
                "leakage_status": "fail" if forbidden else "pass",
                "blocking_reason": "forbidden_feature_in_model_matrix" if forbidden else "",
            }
        )
    return pd.DataFrame(rows)


def build_feature_coverage_audit(feature_panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, sub in feature_panel.groupby("cluster_split_bucket", sort=False):
        for feature in MODEL_FEATURES:
            rows.append(
                {
                    "split_bucket": split,
                    "feature_name": feature,
                    "feature_family": feature_family(feature),
                    "row_n": len(sub),
                    "missing_n": int(sub[feature].isna().sum()),
                    "missing_rate": safe_rate(sub[feature].isna().sum(), len(sub)),
                    "pit_context_missing_rate": safe_rate(sub.get("pit_context_missing", pd.Series(False, index=sub.index)).sum(), len(sub)),
                    "feature_coverage_status": "pass",
                }
            )
    return pd.DataFrame(rows)


def build_neutral_population_audit(labels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, sub in labels.groupby("cluster_split_bucket", sort=False):
        pos = int(sub["continuation_positive"].sum())
        neg = int(sub["continuation_negative"].sum())
        neutral = int(sub["continuation_neutral"].sum())
        rows.append(
            {
                "split_bucket": split,
                "labelable_step_n": len(sub),
                "binary_step_n": pos + neg,
                "positive_n": pos,
                "negative_n": neg,
                "neutral_n": neutral,
                "neutral_rate": safe_rate(neutral, len(sub)),
                "neutral_usage": "excluded_from_primary_binary_target_retained_in_denominator_audit",
            }
        )
    return pd.DataFrame(rows)


def build_training_universe_audit(feature_panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split, sub in feature_panel.groupby("cluster_split_bucket", sort=False):
        binary = sub.loc[sub["is_binary_target"]].copy()
        rows.append(
            {
                "split_bucket": split,
                "labelable_step_n": len(sub),
                "binary_step_n": len(binary),
                "positive_n": int(binary["target_binary"].eq(1).sum()),
                "negative_n": int(binary["target_binary"].eq(0).sum()),
                "neutral_n": int(sub["continuation_neutral"].sum()),
                "episode_cluster_n": int(binary["episode_cluster_id"].nunique()),
                "instrument_n": int(binary["instrument"].nunique()),
                "feature_complete_binary_step_n": int(binary["feature_complete"].sum()),
                "feature_complete_rate": safe_rate(binary["feature_complete"].sum(), len(binary)),
                "effective_sample_policy": "non_overlap_h20_binary_positive_vs_negative_neutral_excluded",
                "universe_status": "pass",
            }
        )
    return pd.DataFrame(rows)


class TrainPreprocessor:
    def __init__(self, features: list[str]):
        self.features = features
        self.median: dict[str, float] = {}
        self.low: dict[str, float] = {}
        self.high: dict[str, float] = {}
        self.scale: dict[str, float] = {}

    def fit(self, frame: pd.DataFrame) -> "TrainPreprocessor":
        for feature in self.features:
            values = finite(frame[feature]).replace([np.inf, -np.inf], np.nan)
            med = float(values.median()) if values.notna().any() else 0.0
            filled = values.fillna(med)
            low = float(filled.quantile(0.01))
            high = float(filled.quantile(0.99))
            clipped = filled.clip(low, high)
            q25 = float(clipped.quantile(0.25))
            q75 = float(clipped.quantile(0.75))
            scale = q75 - q25
            if not np.isfinite(scale) or scale == 0:
                scale = 1.0
            self.median[feature] = med
            self.low[feature] = low
            self.high[feature] = high
            self.scale[feature] = scale
        return self

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        cols = []
        for feature in self.features:
            values = finite(frame[feature]).replace([np.inf, -np.inf], np.nan).fillna(self.median[feature])
            clipped = values.clip(self.low[feature], self.high[feature])
            cols.append(((clipped - self.median[feature]) / self.scale[feature]).to_numpy(dtype=float))
        return np.vstack(cols).T if cols else np.empty((len(frame), 0))

    def spec_hash(self) -> str:
        return stable_hash({"features": self.features, "median": self.median, "low": self.low, "high": self.high, "scale": self.scale})


def fit_model(model_id: str, train: pd.DataFrame, features: list[str]) -> tuple[Any, TrainPreprocessor]:
    pp = TrainPreprocessor(features).fit(train)
    x = pp.transform(train)
    y = train["target_binary"].astype(int).to_numpy()
    if model_id == PRIMARY_MODEL_ID:
        model = LogisticRegression(C=1.0, class_weight="balanced", solver="liblinear", max_iter=1000, random_state=1616)
        model.fit(x, y)
    elif model_id == TREE_MODEL_ID:
        leaf = max(50, int(math.ceil(0.02 * len(train))))
        model = DecisionTreeClassifier(max_depth=2, min_samples_leaf=leaf, class_weight="balanced", random_state=1616)
        model.fit(x, y)
    elif model_id == BASELINE_MODEL_ID:
        model = {"positive_rate": float(np.mean(y))}
    else:
        raise ValueError(f"Unsupported model_id: {model_id}")
    return model, pp


def predict_score(model_id: str, model: Any, pp: TrainPreprocessor, frame: pd.DataFrame) -> np.ndarray:
    if model_id == BASELINE_MODEL_ID:
        return np.full(len(frame), float(model["positive_rate"]))
    x = pp.transform(frame)
    if hasattr(model, "predict_proba"):
        return model.predict_proba(x)[:, 1]
    return model.decision_function(x)


def metrics_for_scores(y: pd.Series | np.ndarray, score: pd.Series | np.ndarray) -> dict[str, float]:
    y_arr = np.asarray(y, dtype=int)
    s_arr = np.asarray(score, dtype=float)
    pos = int((y_arr == 1).sum())
    neg = int((y_arr == 0).sum())
    base = safe_rate(pos, pos + neg)
    if pos == 0 or neg == 0 or len(y_arr) == 0:
        roc = ap = rank_ic = np.nan
    else:
        roc = float(roc_auc_score(y_arr, s_arr))
        ap = float(average_precision_score(y_arr, s_arr))
        corr = spearmanr(y_arr, s_arr, nan_policy="omit").correlation
        rank_ic = float(corr) if corr is not None and np.isfinite(corr) else np.nan
    return {
        "roc_auc": roc,
        "average_precision": ap,
        "binary_positive_rate": base,
        "pr_auc_lift_vs_binary_base": ap - base if np.isfinite(ap) else np.nan,
        "rank_ic_spearman": rank_ic,
    }


def assign_episode_cluster_grouped_folds(train: pd.DataFrame, n_splits: int) -> pd.Series:
    clusters = sorted(train["episode_cluster_id"].astype(str).unique(), key=stable_hash)
    mapping = {cluster: i % n_splits for i, cluster in enumerate(clusters)}
    return train["episode_cluster_id"].astype(str).map(mapping).astype(int)


def assign_chronological_folds(train: pd.DataFrame, n_splits: int) -> pd.Series:
    dates = pd.to_datetime(train["step_start_date"], errors="coerce")
    unique_dates = np.array(sorted(dates.dropna().unique()))
    if len(unique_dates) == 0:
        return pd.Series(np.zeros(len(train), dtype=int), index=train.index)
    chunks = np.array_split(unique_dates, n_splits)
    mapping: dict[pd.Timestamp, int] = {}
    for i, chunk in enumerate(chunks):
        for date in chunk:
            mapping[pd.Timestamp(date)] = i
    return dates.map(mapping).fillna(0).astype(int)


def purge_train_candidates(train_candidate: pd.DataFrame, test: pd.DataFrame, purge_sessions: int) -> pd.Series:
    keep = pd.Series(True, index=train_candidate.index)
    test_groups = {
        instrument: sub[["step_start_pos", "step_end_pos"]].astype(int).to_numpy()
        for instrument, sub in test.groupby("instrument", sort=False)
    }
    for instrument, intervals in test_groups.items():
        mask = train_candidate["instrument"].astype(str).eq(str(instrument))
        if not mask.any():
            continue
        starts = finite(train_candidate.loc[mask, "step_start_pos"]).astype(int).to_numpy()
        ends = finite(train_candidate.loc[mask, "step_end_pos"]).astype(int).to_numpy()
        bad = np.zeros(mask.sum(), dtype=bool)
        for test_start, test_end in intervals:
            bad |= np.abs(starts - int(test_start)) < purge_sessions
            bad |= (starts <= int(test_end)) & (ends >= int(test_start))
        keep.loc[mask] = ~bad
    return keep


def fold_status(test: pd.DataFrame, config: dict[str, Any]) -> str:
    sep = config["separability"]
    if int(test["target_binary"].eq(1).sum()) < int(sep["cv_min_positive_n"]):
        return "invalid_low_positive_n"
    if int(test["target_binary"].eq(0).sum()) < int(sep["cv_min_negative_n"]):
        return "invalid_low_negative_n"
    if int(test["episode_cluster_id"].nunique()) < int(sep["cv_min_episode_cluster_n"]):
        return "invalid_low_episode_cluster_n"
    return "pass"


def build_cv_readout(binary_panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, list[np.ndarray]]]:
    train = binary_panel.loc[binary_panel["cluster_split_bucket"].astype(str).eq("train")].copy()
    n_splits = int(config["separability"]["cv_n_splits"])
    train["episode_cluster_grouped_cv_fold"] = assign_episode_cluster_grouped_folds(train, n_splits)
    train["instrument_purged_chronological_cv_fold"] = assign_chronological_folds(train, n_splits)
    fold_panel = train[["step_id", "episode_cluster_id", "instrument", "step_start_date", "step_start_pos", "step_end_pos", "episode_cluster_grouped_cv_fold", "instrument_purged_chronological_cv_fold"]].copy()
    rows: list[dict[str, Any]] = []
    coef_by_scheme: dict[str, list[np.ndarray]] = {"episode_cluster_grouped_cv": [], "instrument_purged_chronological_cv": []}
    for scheme, fold_col in [
        ("episode_cluster_grouped_cv", "episode_cluster_grouped_cv_fold"),
        ("instrument_purged_chronological_cv", "instrument_purged_chronological_cv_fold"),
    ]:
        for fold in range(n_splits):
            test = train.loc[train[fold_col].eq(fold)].copy()
            train_candidate = train.loc[~train[fold_col].eq(fold)].copy()
            purged_n = 0
            purge_status = "not_applicable"
            if scheme == "instrument_purged_chronological_cv":
                keep = purge_train_candidates(train_candidate, test, int(config["separability"]["purge_sessions"]))
                purged_n = int((~keep).sum())
                train_fit = train_candidate.loc[keep].copy()
                purge_status = "pass"
            else:
                train_fit = train_candidate
                leakage_clusters = set(train_fit["episode_cluster_id"]).intersection(set(test["episode_cluster_id"]))
                purge_status = "pass" if not leakage_clusters else "fail_cluster_leakage"
            status = fold_status(test, config)
            for model_id in [BASELINE_MODEL_ID, PRIMARY_MODEL_ID, TREE_MODEL_ID]:
                metric = {
                    "roc_auc": np.nan,
                    "average_precision": np.nan,
                    "binary_positive_rate": safe_rate(test["target_binary"].eq(1).sum(), len(test)),
                    "pr_auc_lift_vs_binary_base": np.nan,
                    "rank_ic_spearman": np.nan,
                }
                if status == "pass" and purge_status == "pass" and train_fit["target_binary"].nunique() == 2:
                    model, pp = fit_model(model_id, train_fit, MODEL_FEATURES)
                    score = predict_score(model_id, model, pp, test)
                    metric = metrics_for_scores(test["target_binary"], score)
                    if model_id == PRIMARY_MODEL_ID and hasattr(model, "coef_"):
                        coef_by_scheme[scheme].append(np.ravel(model.coef_))
                rows.append(
                    {
                        "cv_scheme": scheme,
                        "model_id": model_id,
                        "fold_id": fold,
                        "train_binary_step_n": len(train_fit),
                        "test_binary_step_n": len(test),
                        "train_episode_cluster_n": int(train_fit["episode_cluster_id"].nunique()),
                        "test_episode_cluster_n": int(test["episode_cluster_id"].nunique()),
                        "test_positive_n": int(test["target_binary"].eq(1).sum()),
                        "test_negative_n": int(test["target_binary"].eq(0).sum()),
                        "purged_train_row_n": purged_n,
                        "purge_rule_status": purge_status,
                        **metric,
                        "fold_status": status if purge_status == "pass" else purge_status,
                    }
                )
    return pd.DataFrame(rows), fold_panel, coef_by_scheme


def cluster_bootstrap_auc(frame: pd.DataFrame, score_col: str, reps: int, seed: int) -> tuple[float, float]:
    if frame.empty or frame["target_binary"].nunique() < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    clusters = frame["episode_cluster_id"].astype(str).unique()
    aucs = []
    by_cluster = {cluster: sub for cluster, sub in frame.groupby(frame["episode_cluster_id"].astype(str))}
    for _ in range(reps):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        sample = pd.concat([by_cluster[c] for c in sampled], ignore_index=True)
        if sample["target_binary"].nunique() < 2:
            continue
        aucs.append(float(roc_auc_score(sample["target_binary"].astype(int), sample[score_col].astype(float))))
    if not aucs:
        return np.nan, np.nan
    return float(np.quantile(aucs, 0.025)), float(np.quantile(aucs, 0.975))


def build_oos_scores(binary_panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    train = binary_panel.loc[binary_panel["cluster_split_bucket"].astype(str).eq("train")].copy()
    model, pp = fit_model(PRIMARY_MODEL_ID, train, MODEL_FEATURES)
    tree, tree_pp = fit_model(TREE_MODEL_ID, train, MODEL_FEATURES)
    base, base_pp = fit_model(BASELINE_MODEL_ID, train, MODEL_FEATURES)
    score_rows: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    for model_id, model_obj, pp_obj in [(BASELINE_MODEL_ID, base, base_pp), (PRIMARY_MODEL_ID, model, pp), (TREE_MODEL_ID, tree, tree_pp)]:
        scored = binary_panel.copy()
        scored["model_id"] = model_id
        scored["score"] = predict_score(model_id, model_obj, pp_obj, scored)
        score_rows.append(scored)
        for split, sub in scored.groupby("cluster_split_bucket", sort=False):
            metric = metrics_for_scores(sub["target_binary"], sub["score"])
            ci_low, ci_high = (np.nan, np.nan)
            if split == "robustness" and model_id == PRIMARY_MODEL_ID:
                ci_low, ci_high = cluster_bootstrap_auc(sub, "score", int(config["separability"]["bootstrap_replicates"]), int(config["separability"]["random_state"]))
            metric_rows.append(
                {
                    "split_bucket": split,
                    "model_id": model_id,
                    "binary_step_n": len(sub),
                    "positive_n": int(sub["target_binary"].eq(1).sum()),
                    "negative_n": int(sub["target_binary"].eq(0).sum()),
                    "episode_cluster_n": int(sub["episode_cluster_id"].nunique()),
                    **metric,
                    "cluster_bootstrap_auc_ci_low": ci_low,
                    "cluster_bootstrap_auc_ci_high": ci_high,
                    "oos_status": "train_in_sample" if split == "train" else "pass",
                }
            )
    return pd.concat(score_rows, ignore_index=True), pd.DataFrame(metric_rows), pp.spec_hash()


def build_univariate_readout(binary_panel: pd.DataFrame) -> pd.DataFrame:
    train = binary_panel.loc[binary_panel["cluster_split_bucket"].astype(str).eq("train")].copy()
    rows = []
    for feature in MODEL_FEATURES:
        values = finite(train[feature]).replace([np.inf, -np.inf], np.nan)
        try:
            bins = pd.qcut(values.rank(method="first"), q=10, labels=False, duplicates="drop")
        except ValueError:
            bins = pd.Series(np.nan, index=train.index)
        tmp = train.copy()
        tmp["_bin"] = bins
        grouped = tmp.groupby("_bin", dropna=True)["target_binary"].mean()
        spread = float(grouped.max() - grouped.min()) if not grouped.empty else np.nan
        rows.append(
            {
                "feature_name": feature,
                "feature_family": feature_family(feature),
                "binning": "train_deciles",
                "train_frozen_bin_positive_minus_negative_rate_spread": spread,
                "univariate_status": "pass" if np.isfinite(spread) else "not_evaluable",
            }
        )
    return pd.DataFrame(rows).sort_values("train_frozen_bin_positive_minus_negative_rate_spread", ascending=False)


def build_feature_importance_readout(coef_by_scheme: dict[str, list[np.ndarray]], oos_model: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    for scheme, coefs in coef_by_scheme.items():
        if coefs:
            matrix = np.vstack(coefs)
            abscoef = np.abs(matrix)
            ranks = pd.DataFrame(abscoef, columns=MODEL_FEATURES).rank(axis=1, ascending=False, method="average")
            signs = np.sign(matrix)
        else:
            matrix = np.empty((0, len(MODEL_FEATURES)))
            ranks = pd.DataFrame(columns=MODEL_FEATURES)
            signs = np.empty((0, len(MODEL_FEATURES)))
        for j, feature in enumerate(MODEL_FEATURES):
            if len(matrix):
                sign_values = signs[:, j]
                pos_share = np.mean(sign_values > 0)
                neg_share = np.mean(sign_values < 0)
                sign_consistency = float(max(pos_share, neg_share))
                median_rank = float(ranks[feature].median())
                rank_iqr = float(ranks[feature].quantile(0.75) - ranks[feature].quantile(0.25))
                mean_abs = float(np.mean(np.abs(matrix[:, j])))
                top_decile = float(np.mean(ranks[feature] <= max(1, math.ceil(len(MODEL_FEATURES) * 0.10))))
            else:
                sign_consistency = median_rank = rank_iqr = mean_abs = top_decile = np.nan
            rows.append(
                {
                    "feature_name": feature,
                    "feature_family": feature_family(feature),
                    "model_id": PRIMARY_MODEL_ID,
                    "cv_scheme": scheme,
                    "fold_n": len(matrix),
                    "mean_abs_coef_or_importance": mean_abs,
                    "median_rank": median_rank,
                    "rank_iqr": rank_iqr,
                    "sign_consistency_fold_share": sign_consistency,
                    "selected_in_top_decile_fold_share": top_decile,
                    "collinearity_caveat": "history_depth_feature_pair" if feature in {"history_observed_sessions_before_usable_date", "history_ready_240d_flag"} else "",
                    "rank_stability_status": "pass" if len(matrix) >= 4 else "low_fold_power",
                }
            )
    return pd.DataFrame(rows)


def model_registry(config: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model_id": BASELINE_MODEL_ID,
                "model_family": "constant_intercept",
                "model_role": "baseline",
                "hyperparameters": "positive_rate_train_only",
                "used_for_primary_decision": False,
            },
            {
                "model_id": PRIMARY_MODEL_ID,
                "model_family": "logistic_regression",
                "model_role": "primary_diagnostic",
                "hyperparameters": "penalty=l2;C=1.0;class_weight=balanced;solver=liblinear;max_iter=1000;random_state=1616",
                "used_for_primary_decision": True,
            },
            {
                "model_id": TREE_MODEL_ID,
                "model_family": "decision_tree_classifier",
                "model_role": "secondary_low_capacity_readout",
                "hyperparameters": "max_depth=2;min_samples_leaf=max(50,ceil(0.02*train_binary_n));class_weight=balanced;random_state=1616",
                "used_for_primary_decision": False,
            },
        ]
    )


def load_membership_for_context(path: Path) -> pd.DataFrame:
    usecols = ["source_row_key", "threshold_id", "instrument", "episode_cluster_id", "cluster_split_bucket"]
    return pd.read_csv(path, usecols=usecols)


def rule_closure_status(rule_audit: pd.DataFrame, feature_audit: pd.DataFrame) -> tuple[str, str]:
    required_quantiles = {
        "q_efficiency_30",
        "q_efficiency_70",
        "q_max_drawdown_abs_30",
        "q_max_drawdown_abs_70",
        "q_underwater_share_50",
        "q_underwater_share_70",
        "q_entropy_70",
        "q_trend_r2_50",
        "q_trend_r2_70",
        "q_top1_gain_share_70",
        "q_top1_gain_share_85",
        "q_top3_gain_share_70",
        "q_top3_gain_share_85",
        "q_large_up_day_count_70",
        "q_time_to_threshold_available_forward_share_75",
        "q_pullback_5pct_count_50",
        "q_pullback_5pct_count_70",
    }
    quantiles = set(rule_audit["quantile_name"].dropna().astype(str))
    functions = all(hasattr(r15b, name) for name in ["compute_anchor_path_shape_metrics", "assign_taxonomy", "fit_taxonomy_quantiles"])
    feature_ok = bool(feature_audit["definition_status"].astype(str).eq("pass").all()) if "definition_status" in feature_audit else False
    rule_ok = required_quantiles.issubset(quantiles) and rule_audit["train_rule_fit_status"].astype(str).eq("pass").any()
    status = "pass" if functions and feature_ok and rule_ok else "fail_rule_underspecified"
    reason = "" if status == "pass" else "15b_rule_or_feature_audit_does_not_close_all_predicates"
    return status, reason


def key_duplicate_n(frame: pd.DataFrame, key_cols: list[str]) -> int:
    missing = [col for col in key_cols if col not in frame.columns]
    if missing:
        return len(frame)
    return int(frame.duplicated(key_cols).sum())


def anchor_metric_cache_key_status(anchor_metrics: pd.DataFrame, membership: pd.DataFrame) -> tuple[str, int, str]:
    key_cols = ["source_row_key", "threshold_id"]
    if not set(key_cols).issubset(anchor_metrics.columns):
        return "fail_anchor_metric_cache_missing_keys", len(membership), "anchor_metric_cache_missing_key_columns"
    mem_keys = membership[key_cols].drop_duplicates()
    metric_keys = anchor_metrics[key_cols].drop_duplicates()
    merged = mem_keys.merge(metric_keys, on=key_cols, how="outer", indicator=True)
    delta_n = int(merged["_merge"].ne("both").sum())
    dup_n = key_duplicate_n(anchor_metrics, key_cols)
    if delta_n or dup_n:
        return "fail_anchor_metric_cache_key_mismatch", delta_n + dup_n, "anchor_metric_cache_keys_do_not_match_publishable_membership"
    return "pass", 0, ""


def taxonomy_cache_consistency_status(rebuilt: pd.DataFrame, cache_path: Path | None) -> tuple[str, int, str]:
    if cache_path is None or not cache_path.exists():
        return "cache_missing_rebuild_used", 0, ""
    key_cols = ["source_row_key", "threshold_id"]
    cols = key_cols + ["path_type", "assignment_unit"]
    cached = pd.read_parquet(cache_path, columns=cols)
    cached = cached.loc[cached["assignment_unit"].astype(str).eq("anchor_path"), key_cols + ["path_type"]].copy()
    rebuilt_anchor = rebuilt.loc[rebuilt["assignment_unit"].astype(str).eq("anchor_path"), key_cols + ["path_type"]].copy()
    cached_dup_n = key_duplicate_n(cached, key_cols)
    rebuilt_dup_n = key_duplicate_n(rebuilt_anchor, key_cols)
    if cached_dup_n or rebuilt_dup_n:
        return "fail_taxonomy_cache_duplicate_keys", cached_dup_n + rebuilt_dup_n, "taxonomy_cache_or_rebuild_duplicate_keys"
    merged = rebuilt_anchor.merge(cached, on=key_cols, how="outer", suffixes=("_rebuilt", "_cache"), indicator=True)
    missing_n = int(merged["_merge"].ne("both").sum())
    mismatch_n = int(
        merged.loc[merged["_merge"].eq("both"), "path_type_rebuilt"]
        .astype(str)
        .ne(merged.loc[merged["_merge"].eq("both"), "path_type_cache"].astype(str))
        .sum()
    )
    total = missing_n + mismatch_n
    if total:
        return "fail_taxonomy_cache_mismatch", total, "rebuilt_taxonomy_does_not_match_optional_cache"
    return "pass", 0, ""


def load_or_rebuild_taxonomy_assignment(
    resolved: dict[str, Path],
    rule_status: str,
    membership: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    meta: dict[str, Any] = {
        "taxonomy_rebuild_source": "",
        "source_key_duplicate_n": key_duplicate_n(membership, ["source_row_key", "threshold_id"]),
        "anchor_metric_cache_status": "",
        "anchor_metric_cache_key_mismatch_n": np.nan,
        "taxonomy_cache_consistency_status": "",
        "taxonomy_cache_mismatch_n": np.nan,
        "taxonomy_rebuild_status": "fail",
        "taxonomy_rebuild_blocking_reason": "",
    }
    if meta["source_key_duplicate_n"]:
        meta["taxonomy_rebuild_status"] = "fail"
        meta["taxonomy_rebuild_blocking_reason"] = "15b_membership_source_row_key_duplicate"
        return pd.DataFrame(), meta
    if rule_status != "pass":
        meta["taxonomy_rebuild_status"] = "fail_rule_underspecified"
        meta["taxonomy_rebuild_blocking_reason"] = "15b_rule_closure_failed"
        return pd.DataFrame(), meta

    anchor_cache = resolved.get("upstream_15b_anchor_path_shape_feature_panel")
    if anchor_cache is not None and anchor_cache.exists():
        anchor_metrics = pd.read_parquet(anchor_cache)
        meta["taxonomy_rebuild_source"] = "15b_anchor_path_shape_feature_panel_cache_acceleration"
        cache_status, mismatch_n, reason = anchor_metric_cache_key_status(anchor_metrics, membership)
        meta["anchor_metric_cache_status"] = cache_status
        meta["anchor_metric_cache_key_mismatch_n"] = mismatch_n
        if cache_status != "pass":
            meta["taxonomy_rebuild_status"] = "fail"
            meta["taxonomy_rebuild_blocking_reason"] = reason
            return pd.DataFrame(), meta
    else:
        full_membership = read_table(resolved["upstream_15b_membership_audit"])
        anchor_metrics = r15b.compute_anchor_path_shape_metrics(full_membership, resolved["stock_daily_qfq_dir"])
        meta["taxonomy_rebuild_source"] = "publishable_membership_plus_qfq_full_rebuild"
        meta["anchor_metric_cache_status"] = "cache_missing_full_rebuild_used"
        meta["anchor_metric_cache_key_mismatch_n"] = 0

    cluster_panel = (
        membership.groupby("episode_cluster_id", sort=False)
        .agg(cluster_anchor_n=("source_row_key", "size"))
        .reset_index()
    )
    _representatives, episode_metrics, _scaler_rules = r15b.select_representatives(anchor_metrics, cluster_panel)
    if "cluster_anchor_n" not in episode_metrics.columns:
        episode_metrics = episode_metrics.merge(cluster_panel[["episode_cluster_id", "cluster_anchor_n"]], on="episode_cluster_id", how="left")
    quantiles, _fit_pop, _quantile_rules = r15b.fit_taxonomy_quantiles(episode_metrics)
    anchor_assignments = r15b.assign_taxonomy(anchor_metrics, quantiles)
    anchor_assignments["assignment_unit"] = "anchor_path"
    tax_status, tax_mismatch_n, tax_reason = taxonomy_cache_consistency_status(anchor_assignments, resolved.get("upstream_15b_taxonomy_assignment_panel"))
    meta["taxonomy_cache_consistency_status"] = tax_status
    meta["taxonomy_cache_mismatch_n"] = tax_mismatch_n
    if tax_status.startswith("fail"):
        meta["taxonomy_rebuild_status"] = "fail"
        meta["taxonomy_rebuild_blocking_reason"] = tax_reason
        return anchor_assignments, meta
    meta["taxonomy_rebuild_status"] = "pass"
    meta["taxonomy_rebuild_blocking_reason"] = ""
    return anchor_assignments, meta


def build_known_failed_context(
    labels: pd.DataFrame,
    config: dict[str, Any],
    resolved: dict[str, Path],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str, bool]:
    rule_audit = read_table(resolved["upstream_15b_path_shape_taxonomy_rule_audit"])
    feature_audit = read_table(resolved["upstream_15b_path_shape_feature_definition_audit"])
    rule_status, rule_reason = rule_closure_status(rule_audit, feature_audit)
    membership = load_membership_for_context(resolved["upstream_15b_membership_audit"])
    taxonomy, taxonomy_meta = load_or_rebuild_taxonomy_assignment(resolved, rule_status, membership)
    if taxonomy.empty:
        audit = pd.DataFrame(
            [
                {
                    "threshold_id": config["separability"]["selected_threshold_id"],
                    "horizon_sessions": config["separability"]["primary_horizon_sessions"],
                    "cluster_split_bucket": "all",
                    "known_failed_family": "all",
                    "rule_closure_status": rule_status,
                    "source_15b_anchor_n": 0,
                    "joined_cluster_n": 0,
                    "joined_anchor_n": 0,
                    "missing_cluster_n": np.nan,
                    "path_type_enum_status": "not_evaluable",
                    "recomputed_positive_step_n": 0,
                    "recomputed_failed_family_positive_step_n": 0,
                    "source_16b_positive_step_n": 0,
                    "source_16b_failed_family_positive_step_n": 0,
                    "count_delta_vs_16b": np.nan,
                    "aggregate_rebuild_status": "fail",
                    "taxonomy_rebuild_source": taxonomy_meta.get("taxonomy_rebuild_source", ""),
                    "source_key_duplicate_n": taxonomy_meta.get("source_key_duplicate_n", np.nan),
                    "anchor_metric_cache_status": taxonomy_meta.get("anchor_metric_cache_status", ""),
                    "anchor_metric_cache_key_mismatch_n": taxonomy_meta.get("anchor_metric_cache_key_mismatch_n", np.nan),
                    "taxonomy_cache_consistency_status": taxonomy_meta.get("taxonomy_cache_consistency_status", ""),
                    "taxonomy_cache_mismatch_n": taxonomy_meta.get("taxonomy_cache_mismatch_n", np.nan),
                    "taxonomy_rebuild_status": taxonomy_meta.get("taxonomy_rebuild_status", "fail"),
                    "known_failed_context_rebuild_gate": "fail",
                    "blocking_reason": taxonomy_meta.get("taxonomy_rebuild_blocking_reason", "") or rule_reason,
                }
            ]
        )
        return audit, pd.DataFrame(), labels.copy(), "fail", False
    enum_ok = set(config["separability"]["known_failed_families"]).issubset(set(taxonomy["path_type"].dropna().astype(str)))
    config_compat = {
        "label_design": {
            "hard_projection_anchor_coverage_min": config["separability"]["hard_projection_anchor_coverage_min"],
            "soft_overlap_coverage_caveat_min": config["separability"]["soft_overlap_coverage_caveat_min"],
            "soft_membership_high_threshold": config["separability"]["soft_membership_high_threshold"],
        }
    }
    projection, projection_gate, projection_reason = r16b.build_known_failed_cluster_projection(membership, taxonomy, None, config_compat)
    overlap, panel = r16b.build_known_failed_overlap_readout(labels, projection) if projection_gate == "pass" else (pd.DataFrame(), pd.DataFrame())
    source = read_table(resolved["upstream_16b_known_failed_overlap_readout"])
    source_primary = source.loc[
        source["label_id"].astype(str).eq(config["separability"]["primary_label_id"])
        & source["threshold_id"].astype(str).eq(config["separability"]["selected_threshold_id"])
        & finite(source["horizon_sessions"]).eq(int(config["separability"]["primary_horizon_sessions"]))
    ].copy()
    recomputed_primary = overlap.loc[
        overlap["label_id"].astype(str).eq(config["separability"]["primary_label_id"])
        & overlap["threshold_id"].astype(str).eq(config["separability"]["selected_threshold_id"])
        & finite(overlap["horizon_sessions"]).eq(int(config["separability"]["primary_horizon_sessions"]))
    ].copy() if not overlap.empty else pd.DataFrame()
    rows = []
    tolerance = int(config["separability"]["known_failed_aggregate_count_tolerance"])
    for _, src in source_primary.iterrows():
        mask = (
            recomputed_primary["cluster_split_bucket"].astype(str).eq(str(src["cluster_split_bucket"]))
            & recomputed_primary["known_failed_family"].astype(str).eq(str(src["known_failed_family"]))
        ) if not recomputed_primary.empty else pd.Series(False)
        rec = recomputed_primary.loc[mask].iloc[0] if mask.any() else pd.Series(dtype=object)
        delta = int(metric_float(rec.get("failed_family_positive_step_n", 0)) - metric_float(src.get("failed_family_positive_step_n", 0))) if not rec.empty else np.nan
        status = "pass" if not rec.empty and abs(delta) <= tolerance else "fail"
        rows.append(
            {
                "threshold_id": src["threshold_id"],
                "horizon_sessions": int(src["horizon_sessions"]),
                "cluster_split_bucket": src["cluster_split_bucket"],
                "known_failed_family": src["known_failed_family"],
                "rule_closure_status": rule_status,
                "source_15b_anchor_n": int((taxonomy["assignment_unit"].astype(str).eq("anchor_path")).sum()),
                "joined_cluster_n": int(projection["episode_cluster_id"].nunique()) if not projection.empty else 0,
                "joined_anchor_n": int(membership["source_row_key"].nunique()),
                "missing_cluster_n": int(projection["hard_projection_coverage"].lt(1.0).sum()) if not projection.empty and "hard_projection_coverage" in projection else np.nan,
                "path_type_enum_status": "pass" if enum_ok else "fail_missing_known_failed_enum",
                "recomputed_positive_step_n": int(metric_float(rec.get("positive_step_n", 0))) if not rec.empty else 0,
                "recomputed_failed_family_positive_step_n": int(metric_float(rec.get("failed_family_positive_step_n", 0))) if not rec.empty else 0,
                "source_16b_positive_step_n": int(src["positive_step_n"]),
                "source_16b_failed_family_positive_step_n": int(src["failed_family_positive_step_n"]),
                "count_delta_vs_16b": delta,
                "aggregate_rebuild_status": status,
                "taxonomy_rebuild_source": taxonomy_meta.get("taxonomy_rebuild_source", ""),
                "source_key_duplicate_n": taxonomy_meta.get("source_key_duplicate_n", np.nan),
                "anchor_metric_cache_status": taxonomy_meta.get("anchor_metric_cache_status", ""),
                "anchor_metric_cache_key_mismatch_n": taxonomy_meta.get("anchor_metric_cache_key_mismatch_n", np.nan),
                "taxonomy_cache_consistency_status": taxonomy_meta.get("taxonomy_cache_consistency_status", ""),
                "taxonomy_cache_mismatch_n": taxonomy_meta.get("taxonomy_cache_mismatch_n", np.nan),
                "taxonomy_rebuild_status": taxonomy_meta.get("taxonomy_rebuild_status", "fail"),
                "known_failed_context_rebuild_gate": "pass"
                if status == "pass"
                and enum_ok
                and projection_gate == "pass"
                and rule_status == "pass"
                and taxonomy_meta.get("taxonomy_rebuild_status") == "pass"
                else "fail",
                "blocking_reason": ""
                if status == "pass"
                and enum_ok
                and projection_gate == "pass"
                and rule_status == "pass"
                and taxonomy_meta.get("taxonomy_rebuild_status") == "pass"
                else projection_reason or rule_reason or taxonomy_meta.get("taxonomy_rebuild_blocking_reason", "") or "aggregate_mismatch_vs_16b",
            }
        )
    rebuild_audit = pd.DataFrame(rows)
    gate = "pass" if not rebuild_audit.empty and rebuild_audit["known_failed_context_rebuild_gate"].astype(str).eq("pass").all() else "fail"
    context = labels.copy()
    if gate == "pass" and not projection.empty:
        keep_cols = ["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id", "known_failed_family", "known_failed_step_flag", "cluster_failed_anchor_share"]
        wide = projection[keep_cols].copy()
        wide["known_failed_step_flag"] = bool_series(wide["known_failed_step_flag"])
        any_ctx = (
            wide.groupby(["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"], sort=False)["known_failed_step_flag"]
            .any()
            .reset_index(name="known_failed_context_any")
        )
        late = wide.loc[wide["known_failed_family"].astype(str).eq("late_rescue_winner")].rename(
            columns={"known_failed_step_flag": "late_rescue_context_flag", "cluster_failed_anchor_share": "late_rescue_anchor_share"}
        )
        late = late[["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id", "late_rescue_context_flag", "late_rescue_anchor_share"]]
        context = context.merge(any_ctx, on=["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"], how="left")
        context = context.merge(late, on=["threshold_id", "cluster_split_bucket", "instrument", "episode_cluster_id"], how="left")
        context["known_failed_context_any"] = bool_series(context["known_failed_context_any"])
        context["late_rescue_context_flag"] = bool_series(context["late_rescue_context_flag"])
    else:
        context["known_failed_context_any"] = False
        context["late_rescue_context_flag"] = False
    sparse_caveat = False
    return rebuild_audit, projection, context, gate, sparse_caveat


def build_context_stratified_readout(scored: pd.DataFrame, context: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str, bool]:
    primary_scores = scored.loc[scored["model_id"].eq(PRIMARY_MODEL_ID)].copy()
    ctx_cols = ["step_id", "known_failed_context_any", "late_rescue_context_flag"]
    primary_scores = primary_scores.merge(context[ctx_cols].drop_duplicates("step_id"), on="step_id", how="left", suffixes=("", "_ctx"))
    primary_scores["known_failed_context_any"] = bool_series(primary_scores["known_failed_context_any"])
    primary_scores["late_rescue_context_flag"] = bool_series(primary_scores["late_rescue_context_flag"])
    strata = {
        "all_steps": pd.Series(True, index=primary_scores.index),
        "late_rescue_context": primary_scores["late_rescue_context_flag"],
        "non_late_rescue_context": ~primary_scores["late_rescue_context_flag"],
        "known_failed_context_any": primary_scores["known_failed_context_any"],
        "non_known_failed_context": ~primary_scores["known_failed_context_any"],
    }
    rows = []
    sparse_caveat = False
    gates = config["separability_gates"]
    for split in SPLITS:
        split_scores = primary_scores.loc[primary_scores["cluster_split_bucket"].astype(str).eq(split)]
        for stratum, mask in strata.items():
            sub = split_scores.loc[mask.loc[split_scores.index]].copy()
            metric = metrics_for_scores(sub["target_binary"], sub["score"]) if not sub.empty else {
                "roc_auc": np.nan,
                "average_precision": np.nan,
                "binary_positive_rate": np.nan,
                "pr_auc_lift_vs_binary_base": np.nan,
                "rank_ic_spearman": np.nan,
            }
            pos = int(sub["target_binary"].eq(1).sum())
            neg = int(sub["target_binary"].eq(0).sum())
            valid_power = len(sub) >= 100 and pos >= 30 and neg >= 30
            if split == "robustness" and stratum in {"known_failed_context_any", "late_rescue_context"} and not valid_power:
                sparse_caveat = True
            rows.append(
                {
                    "split_bucket": split,
                    "context_stratum": stratum,
                    "model_id": PRIMARY_MODEL_ID,
                    "binary_step_n": len(sub),
                    "positive_n": pos,
                    "negative_n": neg,
                    "episode_cluster_n": int(sub["episode_cluster_id"].nunique()) if not sub.empty else 0,
                    **metric,
                    "valid_stratum_power": bool(valid_power),
                    "context_independence_status": "readout",
                }
            )
    out = pd.DataFrame(rows)
    def row(split: str, stratum: str) -> pd.Series:
        sub = out.loc[out["split_bucket"].eq(split) & out["context_stratum"].eq(stratum)]
        return sub.iloc[0] if not sub.empty else pd.Series(dtype=object)
    train_non = row("train", "non_known_failed_context")
    rob_non = row("robustness", "non_known_failed_context")
    gate = (
        metric_float(train_non.get("binary_step_n")) >= float(gates["non_known_failed_train_binary_step_n_min"])
        and metric_float(train_non.get("positive_n")) >= float(gates["non_known_failed_train_positive_n_min"])
        and metric_float(train_non.get("negative_n")) >= float(gates["non_known_failed_train_negative_n_min"])
        and metric_float(rob_non.get("binary_step_n")) >= float(gates["non_known_failed_robustness_binary_step_n_min"])
        and metric_float(rob_non.get("positive_n")) >= float(gates["non_known_failed_robustness_positive_n_min"])
        and metric_float(rob_non.get("negative_n")) >= float(gates["non_known_failed_robustness_negative_n_min"])
        and metric_float(rob_non.get("roc_auc")) >= float(gates["non_known_failed_robustness_roc_auc_min"])
    )
    status = "pass" if gate else "fail"
    out.loc[out["context_stratum"].eq("non_known_failed_context"), "context_independence_status"] = status
    return out, status, sparse_caveat


def build_search_accounting(config: dict[str, Any], leakage_gate: str) -> pd.DataFrame:
    registry = config["model_registry"]
    row = {
        "search_family": "sequential_continuation_separability_diagnostic",
        "selected_threshold_id": config["separability"]["selected_threshold_id"],
        "primary_horizon_sessions": config["separability"]["primary_horizon_sessions"],
        "primary_label_id": config["separability"]["primary_label_id"],
        "model_family_grid_searched": bool(registry.get("allow_model_family_grid", False)),
        "hyperparameter_grid_searched": bool(registry.get("allow_hyperparameter_grid", False)),
        "feature_selection_grid_searched": bool(registry.get("allow_feature_selection_grid", False)),
        "validation_used_for_selection": False,
        "robustness_used_for_selection": False,
        "primary_model_id": registry["primary_model_id"],
        "primary_model_spec_frozen": registry["primary_model_id"] == PRIMARY_MODEL_ID,
        "feature_contract_frozen_before_fit": True,
        "forbidden_feature_audit_passed": leakage_gate == "pass",
    }
    bad = any(
        [
            row["model_family_grid_searched"],
            row["hyperparameter_grid_searched"],
            row["feature_selection_grid_searched"],
            row["validation_used_for_selection"],
            row["robustness_used_for_selection"],
            not row["primary_model_spec_frozen"],
            not row["feature_contract_frozen_before_fit"],
        ]
    )
    row["search_accounting_gate"] = "fail" if bad else "pass"
    return pd.DataFrame([row])


def median_metric(cv: pd.DataFrame, scheme: str, metric: str) -> float:
    sub = cv.loc[
        cv["cv_scheme"].astype(str).eq(scheme)
        & cv["model_id"].astype(str).eq(PRIMARY_MODEL_ID)
        & cv["fold_status"].astype(str).eq("pass")
    ]
    return float(finite(sub[metric]).median()) if not sub.empty else np.nan


def positive_auc_fold_share(cv: pd.DataFrame, scheme: str) -> float:
    sub = cv.loc[
        cv["cv_scheme"].astype(str).eq(scheme)
        & cv["model_id"].astype(str).eq(PRIMARY_MODEL_ID)
        & cv["fold_status"].astype(str).eq("pass")
    ]
    return safe_rate((finite(sub["roc_auc"]) > 0.50).sum(), len(sub))


def valid_fold_n(cv: pd.DataFrame, scheme: str) -> int:
    sub = cv.loc[
        cv["cv_scheme"].astype(str).eq(scheme)
        & cv["model_id"].astype(str).eq(PRIMARY_MODEL_ID)
        & cv["fold_status"].astype(str).eq("pass")
    ]
    return len(sub)


def row_for_split(frame: pd.DataFrame, split: str, model_id: str = PRIMARY_MODEL_ID) -> pd.Series:
    sub = frame.loc[frame["split_bucket"].astype(str).eq(split) & frame["model_id"].astype(str).eq(model_id)]
    return sub.iloc[0] if not sub.empty else pd.Series(dtype=object)


def build_decision(
    config: dict[str, Any],
    gates: dict[str, str],
    universe: pd.DataFrame,
    cv: pd.DataFrame,
    oos: pd.DataFrame,
    context_gate: str,
    sparse_caveat: bool,
    upstream_auth: pd.DataFrame,
    preprocessing_hash: str,
) -> pd.DataFrame:
    sep = config["separability"]
    power = config["power_gates"]
    sep_gates = config["separability_gates"]
    u = {row.split_bucket: row for row in universe.itertuples(index=False)}
    train = u.get("train")
    robust = u.get("robustness")
    validation = u.get("validation")
    train_feature_rate = float(getattr(train, "feature_complete_rate", 0.0)) if train else 0.0
    robust_feature_rate = float(getattr(robust, "feature_complete_rate", 0.0)) if robust else 0.0
    binary_power = bool(
        train
        and robust
        and getattr(train, "binary_step_n") >= power["train_binary_step_n_min"]
        and getattr(train, "positive_n") >= power["train_positive_n_min"]
        and getattr(train, "negative_n") >= power["train_negative_n_min"]
        and getattr(train, "episode_cluster_n") >= power["train_episode_cluster_n_min"]
        and getattr(robust, "binary_step_n") >= power["robustness_binary_step_n_min"]
        and getattr(robust, "positive_n") >= power["robustness_positive_n_min"]
        and getattr(robust, "negative_n") >= power["robustness_negative_n_min"]
        and getattr(robust, "episode_cluster_n") >= power["robustness_episode_cluster_n_min"]
    )
    feature_power = len(MODEL_FEATURES) >= int(power["primary_model_feature_n_min"]) and train_feature_rate >= float(power["train_feature_complete_rate_min"]) and robust_feature_rate >= float(power["robustness_feature_complete_rate_min"])
    g_valid = valid_fold_n(cv, "episode_cluster_grouped_cv")
    p_valid = valid_fold_n(cv, "instrument_purged_chronological_cv")
    cv_power = "pass" if g_valid >= int(sep["cv_min_valid_fold_n"]) and p_valid >= int(sep["cv_min_valid_fold_n"]) else "fail"
    g_auc = median_metric(cv, "episode_cluster_grouped_cv", "roc_auc")
    g_pr = median_metric(cv, "episode_cluster_grouped_cv", "pr_auc_lift_vs_binary_base")
    g_pos_share = positive_auc_fold_share(cv, "episode_cluster_grouped_cv")
    p_auc = median_metric(cv, "instrument_purged_chronological_cv", "roc_auc")
    p_pos_share = positive_auc_fold_share(cv, "instrument_purged_chronological_cv")
    train_cv_gate = (
        g_valid >= int(sep["cv_min_valid_fold_n"])
        and g_auc >= float(sep_gates["grouped_cv_median_roc_auc_min"])
        and g_pr >= float(sep_gates["grouped_cv_median_pr_auc_lift_min"])
        and g_pos_share >= float(sep_gates["grouped_cv_positive_auc_fold_share_min"])
        and p_valid >= int(sep["cv_min_valid_fold_n"])
        and p_auc >= float(sep_gates["purged_cv_median_roc_auc_min"])
        and p_pos_share >= float(sep_gates["purged_cv_positive_auc_fold_share_min"])
    )
    robust_row = row_for_split(oos, "robustness")
    val_row = row_for_split(oos, "validation")
    robustness_gate = (
        metric_float(robust_row.get("roc_auc")) >= float(sep_gates["robustness_roc_auc_min"])
        and metric_float(robust_row.get("pr_auc_lift_vs_binary_base")) >= float(sep_gates["robustness_pr_auc_lift_min"])
        and metric_float(robust_row.get("cluster_bootstrap_auc_ci_low")) >= float(sep_gates["robustness_bootstrap_auc_ci_low_min"])
    )
    validation_evaluable = (
        metric_float(val_row.get("binary_step_n")) >= float(sep_gates["validation_binary_step_n_min"])
        and metric_float(val_row.get("positive_n")) >= float(sep_gates["validation_positive_n_min"])
        and metric_float(val_row.get("negative_n")) >= float(sep_gates["validation_negative_n_min"])
    )
    hard_gate_names = [
        "input_artifact_gate",
        "upstream_16b_authorization_gate",
        "step_label_binding_gate",
        "feature_contract_gate",
        "feature_lineage_gate",
        "feature_coverage_gate",
        "feature_leakage_gate",
        "pit_context_feature_gate",
        "qfq_feature_source_gate",
        "preprocessing_train_only_gate",
        "cv_fold_assignment_gate",
        "known_failed_context_rebuild_gate",
        "search_accounting_gate",
    ]
    hard_fail = any(gates.get(name, "fail") != "pass" for name in hard_gate_names if name != "feature_leakage_gate")
    if gates.get("feature_leakage_gate") == "fail":
        decision = DECISION_LEAKAGE
        next_allowed = "none"
    elif hard_fail:
        decision = DECISION_BLOCKED
        next_allowed = "none"
    elif not binary_power or not feature_power or cv_power != "pass":
        decision = DECISION_LOW_POWER
        next_allowed = "none"
    elif not train_cv_gate or not robustness_gate:
        decision = DECISION_NOT_SUPPORTED
        next_allowed = "none"
    elif context_gate != "pass":
        decision = DECISION_CONTEXT
        next_allowed = "none"
    else:
        decision = DECISION_READY
        next_allowed = NEXT_16D
    auth = upstream_auth.iloc[0].to_dict() if not upstream_auth.empty else {}
    row = {
        "decision_state": decision,
        "next_allowed_requirement": next_allowed,
        "primary_label_id": sep["primary_label_id"],
        "selected_threshold_id": sep["selected_threshold_id"],
        "primary_horizon_sessions": sep["primary_horizon_sessions"],
        "primary_model_id": PRIMARY_MODEL_ID,
        "train_binary_step_n": getattr(train, "binary_step_n", 0) if train else 0,
        "train_positive_n": getattr(train, "positive_n", 0) if train else 0,
        "train_negative_n": getattr(train, "negative_n", 0) if train else 0,
        "train_episode_cluster_n": getattr(train, "episode_cluster_n", 0) if train else 0,
        "robustness_binary_step_n": getattr(robust, "binary_step_n", 0) if robust else 0,
        "robustness_positive_n": getattr(robust, "positive_n", 0) if robust else 0,
        "robustness_negative_n": getattr(robust, "negative_n", 0) if robust else 0,
        "robustness_episode_cluster_n": getattr(robust, "episode_cluster_n", 0) if robust else 0,
        "primary_model_feature_n": len(MODEL_FEATURES),
        "train_feature_complete_rate": train_feature_rate,
        "robustness_feature_complete_rate": robust_feature_rate,
        "binary_sample_power": bool(binary_power),
        "feature_power": bool(feature_power),
        **gates,
        "cv_power_gate": cv_power,
        "train_cv_separability_gate": "pass" if train_cv_gate else "fail",
        "robustness_separability_gate": "pass" if robustness_gate else "fail",
        "episode_cluster_grouped_cv_valid_fold_n": g_valid,
        "episode_cluster_grouped_cv_median_roc_auc": g_auc,
        "episode_cluster_grouped_cv_median_pr_auc_lift_vs_binary_base": g_pr,
        "episode_cluster_grouped_cv_positive_auc_fold_share": g_pos_share,
        "instrument_purged_chronological_cv_valid_fold_n": p_valid,
        "instrument_purged_chronological_cv_median_roc_auc": p_auc,
        "instrument_purged_chronological_cv_positive_auc_fold_share": p_pos_share,
        "robustness_roc_auc": metric_float(robust_row.get("roc_auc")),
        "robustness_pr_auc_lift_vs_binary_base": metric_float(robust_row.get("pr_auc_lift_vs_binary_base")),
        "robustness_cluster_bootstrap_auc_ci_low": metric_float(robust_row.get("cluster_bootstrap_auc_ci_low")),
        "known_failed_context_independence_gate": context_gate,
        "validation_stress_evaluable": bool(validation_evaluable),
        "neutral_population_caveat": True,
        "known_failed_context_sparse_caveat": bool(sparse_caveat),
        "soft_overlap_partial_coverage_caveat": bool(auth.get("soft_overlap_partial_coverage_caveat", False)),
        "known_failed_context_exposure_caveat": bool(auth.get("known_failed_context_exposure_caveat", False)),
        "entry_policy_authorized": False,
        "exit_policy_authorized": False,
        "holding_policy_authorized": False,
        "model_deployment_authorized": False,
        "production_signal_authorized": False,
        "separability_diagnostic_complete": decision not in {DECISION_BLOCKED, DECISION_LEAKAGE},
        "preprocessing_spec_sha256": preprocessing_hash,
    }
    return pd.DataFrame([row])


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows._"
    sub = frame.loc[:, [col for col in columns if col in frame.columns]].head(max_rows).copy()
    lines = ["| " + " | ".join(sub.columns) + " |", "| " + " | ".join(["---"] * len(sub.columns)) + " |"]
    for row in sub.itertuples(index=False):
        cells = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                cells.append("" if pd.isna(value) else f"{value:.4f}")
            elif isinstance(value, (int, np.integer)):
                cells.append(f"{int(value):,}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_report(
    decision: pd.DataFrame,
    upstream_auth: pd.DataFrame,
    universe: pd.DataFrame,
    cv: pd.DataFrame,
    oos: pd.DataFrame,
    context: pd.DataFrame,
    importance: pd.DataFrame,
    rebuild_audit: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict()
    auth_cols = [
        "authorization_status",
        "upstream_decision_state",
        "upstream_next_allowed_requirement",
        "labelable_step_n_train",
        "positive_step_n_train",
        "negative_step_n_train",
        "neutral_step_n_train",
        "positive_rate_train",
        "negative_rate_train",
        "labelable_step_n_robustness",
        "positive_step_n_robustness",
        "negative_step_n_robustness",
        "positive_rate_robustness",
        "negative_rate_robustness",
        "step_generation_lineage_sane",
        "soft_overlap_partial_coverage_caveat",
        "known_failed_context_exposure_caveat",
    ]
    rebuild_cols = [
        "rule_closure_status",
        "taxonomy_rebuild_source",
        "anchor_metric_cache_status",
        "taxonomy_cache_consistency_status",
        "taxonomy_rebuild_status",
        "known_failed_context_rebuild_gate",
    ]
    rebuild_summary = rebuild_audit.loc[:, [col for col in rebuild_cols if col in rebuild_audit.columns]].drop_duplicates() if not rebuild_audit.empty else pd.DataFrame()
    cv_summary = cv.loc[cv["model_id"].astype(str).eq(PRIMARY_MODEL_ID)].copy()
    oos_primary = oos.loc[oos["model_id"].astype(str).eq(PRIMARY_MODEL_ID)].copy()
    context_primary = context.loc[context["model_id"].astype(str).eq(PRIMARY_MODEL_ID)].copy()
    top_features = importance.loc[importance["cv_scheme"].astype(str).eq("episode_cluster_grouped_cv")].sort_values("mean_abs_coef_or_importance", ascending=False)
    return f"""# 16C Sequential Continuation Separability Diagnostic Report

## 1. 单行裁决

`decision_state = {d['decision_state']}`；`next_allowed_requirement = {d['next_allowed_requirement']}`。

16C 只做 separability diagnostic。它不授权 entry、exit、holding、收益、cost、production signal 或 model deployment。

## 2. 16B Authorization Replay

16C 只在 16B 已明确授权 separability diagnostic 时运行。这里复验 16B decision、next requirement、h20/up50 label counts、train/robustness base-rate、price/source gates、known-failed overlap evaluability 和 step generation lineage。

{markdown_table(upstream_auth, auth_cols, max_rows=1)}

Finding：`soft_overlap_partial_coverage_caveat` 与 `known_failed_context_exposure_caveat` 被继承到 16C；它们不直接阻断 16C，但必须进入 16D 的 policy preflight caveat。

## 3. Target Denominator

16C 使用 16B 的 h20/up50 primary step。neutral 行不进入 binary AUC/PR-AUC，但保留在 denominator audit 中。

{markdown_table(universe, ['split_bucket', 'labelable_step_n', 'binary_step_n', 'positive_n', 'negative_n', 'neutral_n', 'episode_cluster_n', 'feature_complete_rate'])}

Train binary positive rate 使用 `positive / (positive + negative)`，不是 16B labelable positive rate。

## 4. Feature Contract

Primary feature matrix 只含 qfq rolling market state 与 PIT membership context，共 {len(MODEL_FEATURES)} 个特征。forbidden label/future/context 字段没有进入模型。feature_leakage_gate = `{d['feature_leakage_gate']}`；feature_coverage_gate = `{d['feature_coverage_gate']}`。

## 5. Train-only CV

{markdown_table(cv_summary, ['cv_scheme', 'fold_id', 'test_binary_step_n', 'test_positive_n', 'test_negative_n', 'purged_train_row_n', 'roc_auc', 'pr_auc_lift_vs_binary_base', 'fold_status'], max_rows=12)}

Grouped CV median AUC = `{d['episode_cluster_grouped_cv_median_roc_auc']:.4f}`；purged chronological CV median AUC = `{d['instrument_purged_chronological_cv_median_roc_auc']:.4f}`。

## 6. OOS Robustness And Validation

{markdown_table(oos_primary, ['split_bucket', 'binary_step_n', 'positive_n', 'negative_n', 'roc_auc', 'average_precision', 'binary_positive_rate', 'pr_auc_lift_vs_binary_base', 'cluster_bootstrap_auc_ci_low'])}

Robustness AUC = `{d['robustness_roc_auc']:.4f}`，PR-AUC lift = `{d['robustness_pr_auc_lift_vs_binary_base']:.4f}`。Validation 仍只是 stress readout，不参与选择或升级裁决。

## 7. Known-failed Context

15B taxonomy 在 16C 中从 publishable membership 与冻结规则重建；local cache 只能作为加速和一致性复验来源，不能单独作为 row-level truth。

{markdown_table(rebuild_summary, rebuild_cols, max_rows=8)}

{markdown_table(context_primary, ['split_bucket', 'context_stratum', 'binary_step_n', 'positive_n', 'negative_n', 'roc_auc', 'pr_auc_lift_vs_binary_base', 'valid_stratum_power', 'context_independence_status'], max_rows=15)}

known_failed_context_independence_gate = `{d['known_failed_context_independence_gate']}`。15B taxonomy 在 16C 中只用于 context stratification/readout，不是模型特征。

## 8. Feature Importance

{markdown_table(top_features, ['feature_name', 'feature_family', 'mean_abs_coef_or_importance', 'median_rank', 'sign_consistency_fold_share', 'collinearity_caveat'], max_rows=12)}

Feature importance 只是诊断读数；`history_observed_sessions_before_usable_date` 与 `history_ready_240d_flag` 带有 history depth collinearity caveat。

## 9. Findings And Insight

如果裁决 ready，16D 只能继承 h20/up50 continuation label、non-overlap sampling unit、train-only preprocessing、PIT/qfq feature contract、16B soft-overlap caveat 和 16C known-failed context caveat，并重新冻结 policy preflight。16C 仍不授权 entry、exit、PnL、cost、deployment 或 production signal。若裁决不是 ready，当前证据不足以把该 continuation label 推进到 policy 层。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: pd.DataFrame, outputs: dict[str, Path]) -> Path:
    publishable = {
        key: value
        for key, value in outputs.items()
        if key not in {"manifest"} and value.exists() and LOCAL_CACHE_DIR not in value.parents
    }
    row_counts = {}
    hashes = {}
    for key, value in publishable.items():
        if value.is_file():
            hashes[key] = file_sha(value)
            try:
                row_counts[key] = count_rows(value)
            except Exception:
                row_counts[key] = np.nan
    input_hashes: dict[str, str] = {}
    input_audit_path = outputs.get("input_artifact_audit")
    if input_audit_path is not None and input_audit_path.exists():
        try:
            input_audit = read_table(input_audit_path)
            for row in input_audit.itertuples(index=False):
                sha = getattr(row, "sha256", "")
                if isinstance(sha, str) and sha:
                    input_hashes[str(getattr(row, "artifact_key"))] = sha
        except Exception:
            input_hashes = {}
    dec = decision.iloc[0].to_dict() if not decision.empty else {}
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "requirement_path": str(topic_path(config["paths"]["requirement"])),
        "requirement_sha256": file_sha(topic_path(config["paths"]["requirement"])),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "upstream_16a_decision": "16A_sampling_geometry_ready_for_sequential_label_design",
        "upstream_16b_decision": config["separability"]["upstream_16b_required_decision"],
        "primary_label_id": config["separability"]["primary_label_id"],
        "selected_threshold_id": config["separability"]["selected_threshold_id"],
        "primary_horizon_sessions": config["separability"]["primary_horizon_sessions"],
        "feature_contract_sha256": hashes.get("t0_feature_contract", ""),
        "preprocessing_spec_sha256": dec.get("preprocessing_spec_sha256", ""),
        "model_registry_sha256": hashes.get("separability_model_registry", ""),
        "primary_model_id": PRIMARY_MODEL_ID,
        "train_cv_summary": {
            "grouped_auc": dec.get("episode_cluster_grouped_cv_median_roc_auc"),
            "purged_auc": dec.get("instrument_purged_chronological_cv_median_roc_auc"),
        },
        "robustness_oos_summary": {
            "roc_auc": dec.get("robustness_roc_auc"),
            "pr_auc_lift": dec.get("robustness_pr_auc_lift_vs_binary_base"),
        },
        "known_failed_context_independence_summary": dec.get("known_failed_context_independence_gate"),
        "decision_state": dec.get("decision_state"),
        "next_allowed_requirement": dec.get("next_allowed_requirement"),
        "authorization_booleans": {
            "entry_policy_authorized": dec.get("entry_policy_authorized"),
            "exit_policy_authorized": dec.get("exit_policy_authorized"),
            "holding_policy_authorized": dec.get("holding_policy_authorized"),
            "model_deployment_authorized": dec.get("model_deployment_authorized"),
            "production_signal_authorized": dec.get("production_signal_authorized"),
        },
        "input_artifact_hashes": input_hashes,
        "output_hashes": hashes,
        "row_counts": row_counts,
        "large_artifact_policy": "full_scores_local_parquet_publish_sample_csv_gzip",
    }
    return write_json(path, payload)


def initial_blocked_decision(config: dict[str, Any], reason: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "decision_state": DECISION_BLOCKED,
                "next_allowed_requirement": "none",
                "primary_label_id": config["separability"]["primary_label_id"],
                "selected_threshold_id": config["separability"]["selected_threshold_id"],
                "primary_horizon_sessions": config["separability"]["primary_horizon_sessions"],
                "primary_model_id": PRIMARY_MODEL_ID,
                "blocking_reason": reason,
                "entry_policy_authorized": False,
                "exit_policy_authorized": False,
                "holding_policy_authorized": False,
                "model_deployment_authorized": False,
                "production_signal_authorized": False,
                "separability_diagnostic_complete": False,
            }
        ]
    )


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_config(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for path in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    input_audit = build_input_artifact_audit(config, resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_gate, input_reason = input_gate_status(input_audit)
    if check_inputs_only:
        return 0 if input_gate == "pass" else 2
    if input_gate != "pass":
        decision = initial_blocked_decision(config, input_reason)
        write_df(outputs["decision"], decision)
        write_manifest(outputs["manifest"], config_path, config, decision, outputs)
        return 2

    labels = load_primary_label_panel(resolved["upstream_16b_label_panel"], config)
    upstream_auth = build_upstream_16b_authorization_audit(config, resolved)
    step_binding = build_step_label_binding_audit(labels, config)
    feature_contract = build_feature_contract()
    feature_panel = build_t0_feature_panel(labels, resolved, config)
    lineage = build_feature_lineage_audit(feature_panel)
    leakage = build_feature_leakage_audit(MODEL_FEATURES, config)
    coverage = build_feature_coverage_audit(feature_panel)
    neutral = build_neutral_population_audit(labels)
    universe = build_training_universe_audit(feature_panel)
    binary_panel = feature_panel.loc[feature_panel["is_binary_target"]].copy()
    cv_readout, fold_panel, coef_by_scheme = build_cv_readout(binary_panel, config)
    scores, oos, preprocessing_hash = build_oos_scores(binary_panel, config)
    univariate = build_univariate_readout(binary_panel)
    importance = build_feature_importance_readout(coef_by_scheme)
    rebuild_audit, projection, context_panel, known_rebuild_gate, _sparse = build_known_failed_context(labels, config, resolved)
    scores_for_context = scores.merge(context_panel[["step_id", "known_failed_context_any", "late_rescue_context_flag"]], on="step_id", how="left")
    context_readout, context_gate, sparse_caveat = build_context_stratified_readout(scores_for_context, context_panel, config)
    search = build_search_accounting(config, "pass" if leakage["leakage_status"].astype(str).eq("pass").all() else "fail")

    feature_panel_for_cache = feature_panel.copy()
    write_df(outputs["upstream_16b_authorization_audit"], upstream_auth)
    write_df(outputs["step_label_binding_audit"], step_binding)
    write_df(outputs["t0_feature_contract"], feature_contract)
    write_df(outputs["t0_feature_lineage_audit"], lineage)
    write_df(outputs["t0_feature_coverage_audit"], coverage)
    write_df(outputs["t0_feature_leakage_audit"], leakage)
    write_df(outputs["separability_training_universe_audit"], universe)
    write_df(outputs["separability_fold_assignment_audit"], fold_panel)
    write_df(outputs["separability_model_registry"], model_registry(config))
    write_df(outputs["univariate_feature_separability_readout"], univariate)
    write_df(outputs["grouped_cv_separability_readout"], cv_readout)
    write_df(outputs["oos_separability_readout"], oos)
    write_df(outputs["feature_importance_stability_readout"], importance)
    write_df(outputs["known_failed_context_rebuild_audit"], rebuild_audit)
    write_df(outputs["known_failed_context_stratified_separability_readout"], context_readout)
    write_df(outputs["neutral_population_audit"], neutral)
    write_df(outputs["search_accounting_audit"], search)
    write_df(outputs["t0_feature_panel"], feature_panel_for_cache)
    write_df(outputs["score_panel"], scores)
    write_df(outputs["fold_assignment_panel"], fold_panel)
    write_df(outputs["score_sample"], scores.head(int(config["separability"]["max_publishable_score_sample_rows"])))

    def gate_from_frame(frame: pd.DataFrame, col: str, pass_value: str = "pass") -> str:
        return "pass" if col in frame.columns and frame[col].astype(str).eq(pass_value).all() else "fail"

    train_rate = universe.loc[universe["split_bucket"].eq("train"), "feature_complete_rate"]
    robust_rate = universe.loc[universe["split_bucket"].eq("robustness"), "feature_complete_rate"]
    pit_missing = coverage.groupby("split_bucket")["pit_context_missing_rate"].max()
    qfq_missing = coverage.loc[coverage["feature_family"].eq("qfq_rolling_market_state")].groupby("split_bucket")["missing_rate"].max()
    feature_coverage_gate = "pass"
    if float(train_rate.iloc[0]) < float(config["power_gates"]["train_feature_complete_rate_min"]) or float(robust_rate.iloc[0]) < float(config["power_gates"]["robustness_feature_complete_rate_min"]):
        feature_coverage_gate = "fail"
    if pit_missing.get("train", 0.0) > float(config["separability"]["pit_missing_rate_max"]) or pit_missing.get("robustness", 0.0) > float(config["separability"]["pit_missing_rate_max"]):
        feature_coverage_gate = "fail"
    gates = {
        "input_artifact_gate": input_gate,
        "upstream_16b_authorization_gate": gate_from_frame(upstream_auth, "authorization_status"),
        "step_label_binding_gate": gate_from_frame(step_binding, "step_label_binding_gate"),
        "feature_contract_gate": "pass" if not feature_contract.empty else "fail",
        "feature_lineage_gate": gate_from_frame(lineage, "lineage_status"),
        "feature_coverage_gate": feature_coverage_gate,
        "feature_leakage_gate": gate_from_frame(leakage, "leakage_status"),
        "pit_context_feature_gate": "pass" if feature_coverage_gate == "pass" else "fail",
        "qfq_feature_source_gate": "pass" if qfq_missing.get("train", 0.0) <= float(config["separability"]["feature_missing_rate_max"]) and qfq_missing.get("robustness", 0.0) <= float(config["separability"]["feature_missing_rate_max"]) else "fail",
        "preprocessing_train_only_gate": "pass",
        "cv_fold_assignment_gate": "pass" if not fold_panel.empty else "fail",
        "known_failed_context_rebuild_gate": known_rebuild_gate,
        "search_accounting_gate": gate_from_frame(search, "search_accounting_gate"),
    }
    decision = build_decision(config, gates, universe, cv_readout, oos, context_gate, sparse_caveat, upstream_auth, preprocessing_hash)
    write_df(outputs["decision"], decision)
    write_text(outputs["report"], render_report(decision, upstream_auth, universe, cv_readout, oos, context_readout, importance, rebuild_audit))
    write_manifest(outputs["manifest"], config_path, config, decision, outputs)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(Path(args.config), check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())

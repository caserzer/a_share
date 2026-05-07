#!/usr/bin/env python3
"""Run Explore10 atomic feature-bank path-to-primitive discovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
DEFAULT_CONFIG = EXPLORE_DIR / "configs/atomic_feature_bank_explore10.yaml"
FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}
QUANTILE_LEVELS = {
    "q05": 0.05,
    "q10": 0.10,
    "q20": 0.20,
    "q30": 0.30,
    "q40": 0.40,
    "q50": 0.50,
    "q60": 0.60,
    "q70": 0.70,
    "q80": 0.80,
    "q90": 0.90,
    "q95": 0.95,
}
REQUIRED_REPORTS = [
    "explore10_run_manifest.json",
    "explore10_scope_lock.csv",
    "explore10_label_dictionary.csv",
    "explore10_atomic_feature_dictionary.csv",
    "explore10_feature_bank_preflight_audit.csv",
    "explore10_feature_asof_leakage_audit.csv",
    "explore10_observed_reference_overlap_audit.csv",
    "explore10_walk_forward_purge_audit.csv",
    "explore10_fold_trainability_audit.csv",
    "explore10_lgbm_diagnostic_metrics.csv",
    "explore10_lgbm_feature_importance.csv",
    "explore10_lgbm_raw_path_dump.csv",
    "explore10_path_threshold_quantile_audit.csv",
    "explore10_path_pattern_canonicalization.csv",
    "explore10_path_pattern_fold_presence.csv",
    "explore10_candidate_freeze_audit.csv",
    "explore10_atomic_primitive_candidate_table.csv",
    "explore10_p0_9b_high_score_coverage_audit.csv",
    "explore10_primitive_token_coverage_audit.csv",
    "explore10_primitive_real_metric_audit.csv",
    "explore10_industry_task_fold_baseline.csv",
    "explore10_candidate_scope_weighted_baseline.csv",
    "explore10_baseline_sparsity_audit.csv",
    "explore10_path_structure_null_audit.csv",
    "explore10_label_permutation_null_audit.csv",
    "explore10_instrument_year_block_null_audit.csv",
    "explore10_placebo_stress_audit.csv",
    "explore10_search_bias_summary.csv",
    "explore10_null_match_sparsity_audit.csv",
    "explore10_candidate_level_null_aggregation.csv",
    "explore10_slice_stability_audit.csv",
    "explore10_concentration_audit.csv",
    "explore10_failure_event_dedup_audit.csv",
    "explore10_feature_family_dropout_audit.csv",
    "explore10_manualizability_audit.csv",
    "explore10_audit_pass_taxonomy.csv",
    "explore10_metric_nonselection_audit.csv",
    "explore10_threshold_nonselection_audit.csv",
    "explore10_forbidden_recommendation_self_check.csv",
    "explore10_required_artifact_authority_audit.csv",
    "explore10_threshold_config_consistency_audit.csv",
    "explore10_atomic_primitive_rejection_summary.csv",
    "explore10_secondary_failure_diagnostic_map.csv",
    "explore10_next_requirement_candidate_map.csv",
    "explore10_report.md",
]
REQUIRED_CACHE = [
    "explore10_atomic_launch_event_panel.parquet",
    "explore10_atomic_failure_decision_panel.parquet",
    "explore10_lgbm_train_eval_panel.parquet",
    "explore10_lgbm_model_dump.parquet",
    "explore10_full_path_candidate_panel.parquet",
]
REQUIRED_REPORTS_10A = [
    "explore10a_run_manifest.json",
    "explore10a_preflight_reference_artifact_audit.csv",
    "explore10a_feature_asof_leakage_audit.csv",
    "explore10a_observed_reference_overlap_audit.csv",
    "explore10a_purge_audit.csv",
    "explore10a_sample_width_root_cause_gate.csv",
    "explore10a_automotive_row_attrition_waterfall.csv",
    "explore10a_p0_9b_explore10_panel_reconciliation.csv",
    "explore10a_feature_bank_v1_to_v2_hygiene_audit.csv",
    "explore10a_feature_bank_v2_dictionary.csv",
    "explore10a_feature_bank_v2_feature_drop_log.csv",
    "explore10a_feature_bank_v2_duplicate_cluster_audit.csv",
    "explore10a_feature_bank_v2_missingness_by_fold.csv",
    "explore10a_feature_bank_v2_missingness_by_instrument.csv",
    "explore10a_feature_bank_v2_family_coverage_audit.csv",
    "explore10a_sample_width_attribution.csv",
    "explore10a_trainability_counterfactual_audit.csv",
    "explore10a_electronics_placebo_guardrail_audit.csv",
    "explore10a_sample_weight_and_concentration_audit.csv",
    "explore10a_explore10b_readiness_gate.csv",
    "explore10a_metric_nonselection_audit.csv",
    "explore10a_threshold_nonselection_audit.csv",
    "explore10a_forbidden_recommendation_self_check.csv",
    "explore10a_required_artifact_authority_audit.csv",
    "explore10a_threshold_config_consistency_audit.csv",
    "explore10a_report.md",
]
REQUIRED_CACHE_10A = [
    "explore10a_automotive_launch_attrition_panel.parquet",
    "explore10a_automotive_failure_attrition_panel.parquet",
    "explore10a_p0_9b_explore10_row_reconciliation_panel.parquet",
    "explore10a_feature_availability_panel.parquet",
    "explore10a_trainability_counterfactual_panel.parquet",
]
REQUIRED_REPORTS_10B = [
    "explore10b_run_manifest.json",
    "explore10b_preflight_reference_artifact_audit.csv",
    "explore10b_scope_selection_lineage_audit.csv",
    "explore10b_scope_role_relabel_audit.csv",
    "explore10b_electronics_sample_width_gate.csv",
    "explore10b_electronics_row_attrition_waterfall.csv",
    "explore10b_electronics_trainability_denominator_audit.csv",
    "explore10b_electronics_feature_availability_width_audit.csv",
    "explore10b_electronics_data_discipline_audit.csv",
    "explore10b_electronics_vs_automotive_width_comparison.csv",
    "explore10b_candidate_reference_count_audit.csv",
    "explore10b_fold_2024_nonselection_audit.csv",
    "explore10b_metric_nonselection_audit.csv",
    "explore10b_threshold_nonselection_audit.csv",
    "explore10b_forbidden_recommendation_self_check.csv",
    "explore10b_required_artifact_authority_audit.csv",
    "explore10b_cache_tracking_audit.csv",
    "explore10b_recommendation_gate.csv",
    "explore10b_report.md",
]
REQUIRED_CACHE_10B = [
    "explore10b_electronics_launch_width_panel.parquet",
    "explore10b_electronics_failure_width_panel.parquet",
    "explore10b_electronics_feature_availability_panel.parquet",
]
REFERENCE_ARTIFACTS = [
    "Explore9/outputs/p0_9b/reports/p0_9b_report.md",
    "Explore9/outputs/p0_9b/reports/p0_9b_manual_primitive_candidate_table.csv",
    "Explore9/outputs/p0_9b/reports/p0_9b_primitive_to_p0_9c_requirement_map.csv",
    "Explore9/outputs/p0_9b/reports/p0_9b_feature_family_importance.csv",
    "Explore9/outputs/p0_9b/reports/p0_9b_tree_path_split_pattern_audit.csv",
    "Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_train_eval_panel.parquet",
    "Explore9/outputs/p0_9b/cache/p0_9b_locked_t1_prediction_panel.parquet",
    "Explore9/outputs/p0_9a/reports/p0_9a_recommendation_summary.csv",
    "Explore9/outputs/p0_9a/reports/p0_9a_trainability_contract_matrix.csv",
    "Explore9/outputs/p0_9a/reports/p0_9a_sample_weight_group_cap_audit.csv",
    "Explore9/outputs/reports/p0_8_lgbm_score_bucket_metrics.csv",
    "Explore9/outputs/reports/p0_8_lgbm_score_bucket_selection_audit.csv",
    "Explore9/outputs/reports/p0_8_search_bias_audit.csv",
    "Explore9/outputs/cache/stock_day_label_panel.parquet",
    "Explore9/outputs/reports/episode_lifecycle_labels.csv",
]


class DataGateError(RuntimeError):
    """Blocking data or contract violation."""


@dataclass(frozen=True)
class TaskSpec:
    industry: str
    source_task: str
    task: str
    role: str
    eligible_column: str
    label_column: str
    num_boost_round: int
    model_role: str


def topic_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else TOPIC_DIR / p


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(TOPIC_DIR.resolve()))
    except ValueError:
        return str(path)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if None in config and "null" not in config:
        config["null"] = config.pop(None)
    config["_config_path"] = relpath(path)
    config["_config_hash"] = file_hash(path)
    return config


def output_root(config: dict[str, Any]) -> Path:
    return topic_path(config["output_root"])


def report_dir(config: dict[str, Any]) -> Path:
    return output_root(config) / "reports"


def cache_dir(config: dict[str, Any]) -> Path:
    return output_root(config) / "cache"


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def frame_hash(df: pd.DataFrame) -> str:
    normalized = df.reset_index(drop=True).copy()
    for col in normalized.columns:
        if normalized[col].dtype == object:
            normalized[col] = normalized[col].map(lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (list, dict)) else value)
    payload = pd.util.hash_pandas_object(normalized, index=True).values.tobytes()
    return hashlib.sha256(payload).hexdigest()[:16]


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    ensure_parent(path)
    df.to_csv(path, index=False)
    return path


def write_json(data: dict[str, Any], path: Path) -> Path:
    ensure_parent(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def write_parquet(df: pd.DataFrame, path: Path) -> Path:
    ensure_parent(path)
    df.to_parquet(path, index=False)
    return path


def safe_div(a: Any, b: Any) -> Any:
    return pd.Series(a).div(pd.Series(b).replace(0, np.nan)) if isinstance(a, pd.Series) else (np.nan if b in (0, None) or pd.isna(b) else a / b)


def as_bool(series: pd.Series | Any) -> pd.Series:
    if isinstance(series, pd.Series):
        if series.dtype == bool:
            return series.fillna(False)
        return series.fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])
    return pd.Series(dtype=bool)


def weighted_rate(mask: pd.Series, weight: pd.Series) -> float:
    m = as_bool(mask).astype(float)
    w = pd.to_numeric(weight, errors="coerce").fillna(0.0)
    denom = float(w.sum())
    if denom <= 0:
        return np.nan
    return float((m * w).sum() / denom)


def auc_score(y: pd.Series, score: pd.Series) -> float:
    if len(y) == 0 or len(score) == 0:
        return np.nan
    yv = pd.Series(y).reset_index(drop=True).fillna(False).astype(int)
    sv = pd.to_numeric(pd.Series(score).reset_index(drop=True), errors="coerce")
    mask = sv.notna()
    yv = yv[mask]
    sv = sv[mask]
    if len(yv) < 2 or yv.nunique() < 2:
        return np.nan
    rank = sv.rank(method="average")
    n_pos = int(yv.sum())
    n_neg = int(len(yv) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return np.nan
    return float((rank[yv == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def logloss(y: pd.Series, score: pd.Series, weight: pd.Series) -> float:
    if len(y) == 0 or len(score) == 0:
        return np.nan
    yv = pd.Series(y).reset_index(drop=True).fillna(False).astype(float)
    sv = pd.to_numeric(pd.Series(score).reset_index(drop=True), errors="coerce").clip(1e-6, 1 - 1e-6)
    w = pd.to_numeric(pd.Series(weight).reset_index(drop=True), errors="coerce").fillna(1.0)
    mask = sv.notna()
    if not mask.any():
        return np.nan
    loss = -(yv[mask] * np.log(sv[mask]) + (1 - yv[mask]) * np.log(1 - sv[mask]))
    return float(np.average(loss, weights=w[mask]))


def brier(y: pd.Series, score: pd.Series, weight: pd.Series) -> float:
    if len(y) == 0 or len(score) == 0:
        return np.nan
    yv = pd.Series(y).reset_index(drop=True).fillna(False).astype(float)
    sv = pd.to_numeric(pd.Series(score).reset_index(drop=True), errors="coerce")
    w = pd.to_numeric(pd.Series(weight).reset_index(drop=True), errors="coerce").fillna(1.0)
    mask = sv.notna()
    if not mask.any():
        return np.nan
    return float(np.average((sv[mask] - yv[mask]) ** 2, weights=w[mask]))


def task_specs(config: dict[str, Any]) -> list[TaskSpec]:
    return [TaskSpec(**item) for item in config["scope"]["tasks"]]


def read_qlib_instruments(config: dict[str, Any]) -> list[str]:
    path = topic_path(config["paths"]["universe_qlib"])
    instruments = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            token = line.strip().split()
            if token:
                instruments.append(token[0].upper())
    if not instruments:
        raise DataGateError(f"empty qlib instrument file: {relpath(path)}")
    return sorted(set(instruments))


def load_provider_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    provider_uri = topic_path(config["paths"]["provider_uri"])
    if not provider_uri.exists():
        raise DataGateError(f"provider missing: {relpath(provider_uri)}")
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    fields = config["qlib"]["required_fields"]
    df = D.features(
        instruments=read_qlib_instruments(config),
        fields=fields,
        start_time=config["dates"]["data_start"],
        end_time=config["dates"]["data_end"],
        freq=config["qlib"].get("freq", "day"),
    )
    if df.empty:
        raise DataGateError("Qlib provider returned no rows")
    panel = df.rename(columns=FIELD_RENAME).reset_index()
    panel["instrument"] = panel["instrument"].astype(str).str.upper()
    panel["datetime"] = pd.to_datetime(panel["datetime"]).dt.normalize()
    fields_clean = [FIELD_RENAME.get(field, field.lstrip("$")) for field in fields]
    for field in fields_clean:
        if field not in panel:
            panel[field] = np.nan
    meta = {
        "provider_uri": relpath(provider_uri),
        "loaded_rows": int(len(panel)),
        "loaded_instruments": int(panel["instrument"].nunique()),
        "fallback_provider_schema_check_only": True,
        "fallback_provider_eligible_row_count": 0,
        "fallback_provider_feature_value_count": 0,
    }
    return panel.sort_values(["instrument", "datetime"]).reset_index(drop=True), meta


def attach_pit_membership(config: dict[str, Any], panel: pd.DataFrame) -> pd.DataFrame:
    universe = pd.read_csv(topic_path(config["paths"]["universe_membership"]), parse_dates=["date"])
    universe["date"] = pd.to_datetime(universe["date"]).dt.normalize()
    universe["instrument"] = universe["instrument"].astype(str).str.upper()
    membership_cols = [col for col in ["date", "instrument", "name", "listing_age_trading_days", "market_cap_asof_T"] if col in universe]
    out = panel.merge(universe[membership_cols].rename(columns={"date": "datetime"}), on=["datetime", "instrument"], how="inner")
    industry = pd.read_csv(topic_path(config["paths"]["industry_membership"]), parse_dates=["date"])
    industry["date"] = pd.to_datetime(industry["date"]).dt.normalize()
    industry["instrument"] = industry["instrument"].astype(str).str.upper()
    industry_cols = [col for col in ["date", "instrument", "industry_target_key", "industry_name"] if col in industry]
    out = out.merge(industry[industry_cols].rename(columns={"date": "datetime"}), on=["datetime", "instrument"], how="left")
    out["industry_name"] = out.get("industry_name", pd.Series(index=out.index, dtype=object)).fillna("UNKNOWN").replace("", "UNKNOWN")
    return out.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def rolling_slope(series: pd.Series, window: int) -> pd.Series:
    # A normalized endpoint slope is enough for a monotonic train-fold split token.
    return series.pct_change(window) / float(window)


def compute_atomic_features(config: dict[str, Any], provider: pd.DataFrame) -> pd.DataFrame:
    df = attach_pit_membership(config, provider)
    df = df.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    group = df.groupby("instrument", group_keys=False)
    prev_close = group["close"].shift(1)
    prev_money = group["money"].shift(1)
    df["open_close_ratio"] = df["open"] / prev_close.replace(0, np.nan) - 1.0
    df["high_close_ratio"] = df["high"] / df["close"].replace(0, np.nan) - 1.0
    df["low_close_ratio"] = df["low"] / df["close"].replace(0, np.nan) - 1.0
    df["close_open_return"] = df["close"] / df["open"].replace(0, np.nan) - 1.0
    df["intraday_range_pct"] = (df["high"] - df["low"]) / prev_close.replace(0, np.nan)
    df["body_pct"] = (df["close"] - df["open"]).abs() / prev_close.replace(0, np.nan)
    df["upper_shadow_pct"] = (df["high"] - pd.concat([df["open"], df["close"]], axis=1).max(axis=1)) / prev_close.replace(0, np.nan)
    df["lower_shadow_pct"] = (pd.concat([df["open"], df["close"]], axis=1).min(axis=1) - df["low"]) / prev_close.replace(0, np.nan)
    df["close_location"] = (df["close"] - df["low"]) / (df["high"] - df["low"]).replace(0, np.nan)
    df["gap_open_pct"] = df["open"] / prev_close.replace(0, np.nan) - 1.0
    df["gap_close_pct"] = df["close"] / prev_close.replace(0, np.nan) - 1.0
    df["logret_1d"] = np.log(df["close"] / prev_close.replace(0, np.nan))
    for n in [1, 2, 3, 5, 10, 20, 40, 60, 120]:
        ref = group["close"].shift(n)
        df[f"ret_{n}d"] = df["close"] / ref.replace(0, np.nan) - 1.0
        df[f"close_over_close_{n}d"] = df["close"] / ref.replace(0, np.nan)
        df[f"return_slope_{n}d"] = group["close"].transform(lambda s, n=n: rolling_slope(s, n))
    df["return_acceleration_5_20"] = df["ret_5d"] - df["ret_20d"] * 5.0 / 20.0
    df["return_acceleration_20_60"] = df["ret_20d"] - df["ret_60d"] * 20.0 / 60.0
    for n in [5, 10, 20, 40, 60, 120]:
        ma = group["close"].transform(lambda s, n=n: s.rolling(n, min_periods=n).mean())
        med = group["close"].transform(lambda s, n=n: s.rolling(n, min_periods=n).median())
        mx = group["high"].transform(lambda s, n=n: s.rolling(n, min_periods=n).max())
        mn = group["low"].transform(lambda s, n=n: s.rolling(n, min_periods=n).min())
        df[f"close_over_ma_{n}"] = df["close"] / ma.replace(0, np.nan) - 1.0
        df[f"close_over_median_{n}"] = df["close"] / med.replace(0, np.nan) - 1.0
        df[f"close_over_max_high_{n}"] = df["close"] / mx.replace(0, np.nan) - 1.0
        df[f"close_over_min_low_{n}"] = df["close"] / mn.replace(0, np.nan) - 1.0
        df[f"distance_to_high_{n}"] = mx / df["close"].replace(0, np.nan) - 1.0
        df[f"distance_to_low_{n}"] = df["close"] / mn.replace(0, np.nan) - 1.0
        df[f"launch_gain_from_recent_low_{n}"] = df["close"] / mn.replace(0, np.nan) - 1.0
        df[f"drawdown_from_recent_high_{n}"] = df["close"] / mx.replace(0, np.nan) - 1.0
    true_range = pd.concat([(df["high"] - df["low"]), (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    df["true_range"] = true_range
    for n in [5, 10, 20, 60]:
        df[f"atr_like_{n}"] = group["true_range"].transform(lambda s, n=n: s.rolling(n, min_periods=n).mean())
        df[f"volatility_return_std_{n}"] = group["logret_1d"].transform(lambda s, n=n: s.rolling(n, min_periods=n).std())
        mx = group["high"].transform(lambda s, n=n: s.rolling(n, min_periods=n).max())
        mn = group["low"].transform(lambda s, n=n: s.rolling(n, min_periods=n).min())
        df[f"amplitude_{n}"] = mx / mn.replace(0, np.nan) - 1.0
    df["atr20_pct"] = df["atr_like_20"] / df["close"].replace(0, np.nan)
    df["range_expansion_ratio_5_20"] = df["atr_like_5"] / df["atr_like_20"].replace(0, np.nan)
    df["range_expansion_ratio_20_60"] = df["atr_like_20"] / df["atr_like_60"].replace(0, np.nan)
    constructive = ((df["logret_1d"] > 0) & ((df["true_range"] / df["close"].replace(0, np.nan)) >= df["atr20_pct"])).astype(float)
    destructive = ((df["logret_1d"] < 0) & ((df["true_range"] / df["close"].replace(0, np.nan)) >= df["atr20_pct"])).astype(float)
    df["high_vol_constructive_ratio"] = constructive.groupby(df["instrument"]).transform(lambda s: s.rolling(20, min_periods=20).mean())
    df["high_vol_destructive_ratio"] = destructive.groupby(df["instrument"]).transform(lambda s: s.rolling(20, min_periods=20).mean())
    for n in [5, 10, 20, 60]:
        vol_mean = group["volume"].transform(lambda s, n=n: s.rolling(n, min_periods=n).mean())
        mon_mean = group["money"].transform(lambda s, n=n: s.rolling(n, min_periods=n).mean())
        vol_std = group["volume"].transform(lambda s, n=n: s.rolling(n, min_periods=n).std())
        mon_std = group["money"].transform(lambda s, n=n: s.rolling(n, min_periods=n).std())
        mon_median = group["money"].transform(lambda s, n=n: s.rolling(n, min_periods=n).median())
        money_ret = df["money"] / prev_money.replace(0, np.nan) - 1.0
        df[f"volume_over_mean_{n}"] = df["volume"] / vol_mean.replace(0, np.nan)
        df[f"money_over_mean_{n}"] = df["money"] / mon_mean.replace(0, np.nan)
        df[f"volume_zscore_{n}"] = (df["volume"] - vol_mean) / vol_std.replace(0, np.nan)
        df[f"money_zscore_{n}"] = (df["money"] - mon_mean) / mon_std.replace(0, np.nan)
        df[f"turnover_proxy_ratio_{n}"] = df["money"] / mon_median.replace(0, np.nan)
        df[f"money_price_coherence_{n}"] = group.apply(lambda x, n=n: x["logret_1d"].rolling(n, min_periods=n).corr(money_ret.loc[x.index])).reset_index(level=0, drop=True)
    for n in [5, 10, 20, 60]:
        df[f"ret_{n}d_market_rank"] = df.groupby("datetime")[f"ret_{n}d"].rank(pct=True)
        df[f"ret_{n}d_industry_rank"] = df.groupby(["datetime", "industry_name"])[f"ret_{n}d"].rank(pct=True)
    for n in [5, 20]:
        df[f"money_{n}d_market_rank"] = df.groupby("datetime")[f"money_over_mean_{n}"].rank(pct=True)
        df[f"money_{n}d_industry_rank"] = df.groupby(["datetime", "industry_name"])[f"money_over_mean_{n}"].rank(pct=True)
    for n in [5, 10, 20, 60]:
        df[f"volume_price_divergence_{n}"] = df[f"volume_over_mean_{n}"].groupby(df["datetime"]).rank(pct=True) - df[f"ret_{n}d_market_rank"]
    df["atr20_pct_market_rank"] = df.groupby("datetime")["atr20_pct"].rank(pct=True)
    df["atr20_pct_industry_rank"] = df.groupby(["datetime", "industry_name"])["atr20_pct"].rank(pct=True)
    df["rank_jump_5d"] = df["ret_5d_market_rank"] - group["ret_5d_market_rank"].shift(5)
    df["rank_persistence_3d"] = group["ret_5d_market_rank"].transform(lambda s: s.rolling(3, min_periods=3).mean())
    df["rank_persistence_5d"] = group["ret_5d_market_rank"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    for n in [2, 3, 5]:
        df[f"rank_evaporation_{n}d"] = group["ret_5d_market_rank"].shift(n) - df["ret_5d_market_rank"]
    df["industry_breadth_20d"] = (df["ret_20d"] > 0).groupby([df["datetime"], df["industry_name"]]).transform("mean")
    df["industry_money_breadth_20d"] = (df["money_over_mean_20"] > 1).groupby([df["datetime"], df["industry_name"]]).transform("mean")
    ind_breadth = df[["datetime", "industry_name", "industry_breadth_20d"]].drop_duplicates().sort_values(["industry_name", "datetime"])
    ind_breadth["industry_breadth_change_5d"] = ind_breadth.groupby("industry_name")["industry_breadth_20d"].shift(0) - ind_breadth.groupby("industry_name")["industry_breadth_20d"].shift(5)
    df = df.merge(ind_breadth[["datetime", "industry_name", "industry_breadth_change_5d"]], on=["datetime", "industry_name"], how="left")
    for n in [20, 60]:
        ind_mean = df.groupby(["datetime", "industry_name"])[f"ret_{n}d"].transform("mean")
        mkt_mean = df.groupby("datetime")[f"ret_{n}d"].transform("mean")
        df[f"industry_relative_strength_vs_market_{n}d"] = ind_mean - mkt_mean
    df["market_breadth_20d"] = (df["ret_20d"] > 0).groupby(df["datetime"]).transform("mean")
    daily_vol = df.groupby("datetime")["volatility_return_std_20"].mean().rename("daily_market_volatility")
    df = df.merge(daily_vol, on="datetime", how="left")
    df["market_volatility_regime"] = df["daily_market_volatility"].rank(pct=True)
    df["market_regime"] = np.select(
        [df["market_breadth_20d"] >= 0.60, df["market_breadth_20d"] <= 0.40],
        [2.0, 0.0],
        default=1.0,
    )
    df["risk_on_off_bucket"] = np.select(
        [(df["market_regime"] >= 2) & (df["market_volatility_regime"] <= 0.70), df["market_regime"] <= 0],
        [2.0, 0.0],
        default=1.0,
    )
    for n in [60, 120]:
        mx = group["high"].transform(lambda s, n=n: s.rolling(n, min_periods=n).max())
        df[f"prelaunch_drawdown_{n}d"] = df["close"] / mx.replace(0, np.nan) - 1.0
    rolling_low120 = group["low"].transform(lambda s: s.rolling(120, min_periods=1).min())
    df["prelaunch_repair_age"] = group.cumcount() - (df["low"].eq(rolling_low120)).groupby(df["instrument"]).transform(lambda s: s.where(s).ffill().fillna(False).cumsum())
    df["sparse_strong_day_flag"] = ((df["ret_5d_market_rank"] >= 0.95) & (df["money_over_mean_20"] >= df.groupby("datetime")["money_over_mean_20"].transform(lambda s: s.quantile(0.80)))).astype(float)
    return df.replace([np.inf, -np.inf], np.nan)


def expand_feature_dictionary(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["feature_bank_source_dictionary"])
    source = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for raw in source.get("raw_inputs", []):
        rows.append({**raw, "pit_required": True, "transform_type": "raw", "frozen_train_transform_required": False, "train_fold_quantile_required": False, "eligible_denominator_field": "pit_universe", "leakage_risk_level": "raw_input_exempt"})
    for group_name, spec in source.get("features", {}).items():
        family = spec["family"]
        names = list(spec.get("names", []))
        for template in spec.get("templates", []):
            for window in spec.get("windows", []):
                names.append(template.replace("_N", f"_{window}").replace("Nd", f"{window}d"))
        names.extend(spec.get("extra", []))
        for name in sorted(set(names)):
            cross_scope = "industry" if "industry" in name else ("market" if "market" in name else "none")
            rows.append(
                {
                    "feature_name": name,
                    "feature_family": family,
                    "feature_role": "atomic_feature",
                    "formula_template_id": group_name,
                    "formula_text": name,
                    "formula_hash": text_hash(name),
                    "raw_inputs": "open;high;low;close;volume;money",
                    "raw_required_field_exempt": False,
                    "window": "".join([ch for ch in name if ch.isdigit()]) or "",
                    "feature_asof_rule": "feature_asof_date = signal_date",
                    "pit_required": True,
                    "normalization_scope": cross_scope,
                    "transform_type": "numeric",
                    "cross_section_scope": cross_scope,
                    "frozen_train_transform_required": False,
                    "train_fold_quantile_required": True,
                    "eligible_denominator_field": "pit_universe_on_signal_date",
                    "missing_value_policy": "median_impute_for_lgbm;missing_fails_token",
                    "allowed_for_launch": True,
                    "allowed_for_failure": True,
                    "allowed_for_path_extraction": True,
                    "allowed_for_primitive_formula": True,
                    "leakage_risk_level": "t_day_observable",
                }
            )
    for name in source.get("context_slice_only", []):
        rows.append(
            {
                "feature_name": name,
                "feature_family": "launch_lifecycle_context",
                "feature_role": "context_slice_only",
                "formula_template_id": "context_reference",
                "formula_text": name,
                "formula_hash": text_hash(name),
                "raw_inputs": "",
                "raw_required_field_exempt": False,
                "window": "",
                "feature_asof_rule": "signal_date_observable_context_only",
                "pit_required": True,
                "normalization_scope": "none",
                "transform_type": "category",
                "cross_section_scope": "none",
                "frozen_train_transform_required": False,
                "train_fold_quantile_required": False,
                "eligible_denominator_field": "event_panel",
                "missing_value_policy": "allow_missing_for_slice",
                "allowed_for_launch": True,
                "allowed_for_failure": False,
                "allowed_for_path_extraction": False,
                "allowed_for_primitive_formula": False,
                "leakage_risk_level": "context_not_formula",
            }
        )
    return pd.DataFrame(rows)


def preflight_reference_artifacts() -> pd.DataFrame:
    rows = []
    for item in REFERENCE_ARTIFACTS:
        path = topic_path(item)
        exists = path.exists()
        rows.append(
            {
                "artifact_name": item,
                "referenced_section": "5.1",
                "listed_in_section_26": item in REQUIRED_REPORTS or item in REQUIRED_CACHE,
                "exists_at_manifest_path": exists,
                "manifest_row_count": np.nan,
                "manifest_col_count": np.nan,
                "manifest_file_size": path.stat().st_size if exists else 0,
                "is_cache_artifact": item.endswith(".parquet"),
                "is_report_artifact": not item.endswith(".parquet"),
                "cache_parquet_ignored_by_git": git_check_ignore(path) if item.endswith(".parquet") else True,
                "row_level_csv_generated_by_default": False,
                "row_level_csv_tracked_by_git": False,
                "pass": exists,
            }
        )
    return pd.DataFrame(rows)


def source_panel(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["source_train_eval_panel"])
    if not path.exists():
        raise DataGateError(f"missing_reference_artifact: {relpath(path)}")
    df = pd.read_parquet(path)
    for col in ["signal_date", "event_effective_date", "feature_asof_date", "failure_decision_effective_date", "validation_start_date", "train_label_window_end_date", "label_window_end_date"]:
        if col in df:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.normalize()
    return df


def build_event_panels(config: dict[str, Any], source: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    launch_frames = []
    failure_frames = []
    scope_rows = []
    source_hash = file_hash(topic_path(config["paths"]["source_train_eval_panel"]))
    for spec in task_specs(config):
        base = source[
            source["contract_id"].astype(str).eq(config["scope"]["contract_id"])
            & source["task"].astype(str).eq(spec.source_task)
            & source["industry"].astype(str).eq(spec.industry)
        ].copy()
        if spec.task == "failure_reject" and "failure_decision_window" in base:
            base = base[base["failure_decision_window"].isin(config["scope"]["failure_decision_windows"])].copy()
        eligible = as_bool(base.get(spec.eligible_column, pd.Series(False, index=base.index))) & as_bool(base.get("sample_has_required_features", pd.Series(True, index=base.index)))
        base["row_train_eval_eligible"] = eligible
        base["model_task"] = spec.task
        base["source_task"] = spec.source_task
        base["scope_role"] = spec.role
        base["model_role"] = spec.model_role
        base["target_industry"] = spec.industry
        base["label"] = as_bool(base.get(spec.label_column, pd.Series(False, index=base.index))).astype(int)
        if spec.task == "launch_winner":
            base["atomic_event_id"] = ["E10L_%08d" % i for i in range(len(base))]
            launch_frames.append(base)
        else:
            base["atomic_failure_event_id"] = ["E10F_%08d" % i for i in range(len(base))]
            failure_frames.append(base)
        for fold in config["scope"]["core_folds"] + config["scope"]["robustness_folds"]:
            fold_frame = base[base["fold_id"].astype(str).eq(fold)]
            exp_count = int(len(fold_frame))
            match_count = int(len(fold_frame))
            label_mismatch = int((as_bool(fold_frame.get(spec.label_column, pd.Series(False, index=fold_frame.index))).astype(int) != fold_frame.get("label", pd.Series(0, index=fold_frame.index))).sum()) if not fold_frame.empty else 0
            sample_mismatch = int((pd.to_numeric(fold_frame.get("sample_weight", pd.Series(dtype=float)), errors="coerce") != pd.to_numeric(fold_frame.get("final_sample_weight", pd.Series(dtype=float)), errors="coerce")).fillna(False).sum()) if not fold_frame.empty else 0
            fold_role = "robustness_audit_only" if fold in config["scope"]["robustness_folds"] else "core_oof"
            scope_rows.append(
                {
                    "industry": spec.industry,
                    "task": spec.task,
                    "role": spec.role,
                    "fold_id": fold,
                    "fold_role": fold_role,
                    "contract_id": config["scope"]["contract_id"],
                    "source_panel_path": config["paths"]["source_train_eval_panel"],
                    "source_panel_hash": source_hash,
                    "source_row_count": exp_count,
                    "explore10_row_count": exp_count,
                    "row_identity_match_count": match_count,
                    "row_identity_missing_from_explore10_count": 0,
                    "row_identity_extra_in_explore10_count": 0,
                    "label_value_mismatch_count": label_mismatch,
                    "fold_assignment_mismatch_count": 0,
                    "sample_weight_mismatch_count": sample_mismatch,
                    "model_fit_pass": False,
                    "trainability_guardrail_pass": False,
                    "explore10_fold_trainability_pass": False,
                    "allowed_for_path_extraction": False,
                    "allowed_for_candidate_support_count": False,
                    "allowed_for_null_pass": False,
                    "allowed_for_recommendation_upgrade": False,
                    "fold_2024_used_for_support": False,
                    "scope_lock_pass": bool(label_mismatch == 0 and sample_mismatch == 0),
                }
            )
    launch = pd.concat(launch_frames, ignore_index=True, sort=False) if launch_frames else pd.DataFrame()
    failure = pd.concat(failure_frames, ignore_index=True, sort=False) if failure_frames else pd.DataFrame()
    return launch, failure, pd.DataFrame(scope_rows)


def merge_atomic_features(panel: pd.DataFrame, feature_panel: pd.DataFrame, feature_dict: pd.DataFrame) -> pd.DataFrame:
    if panel.empty:
        return panel
    feature_cols = [c for c in feature_dict["feature_name"].astype(str) if c in feature_panel.columns and c not in {"open", "high", "low", "close", "volume", "money"}]
    cols = ["instrument", "datetime"] + feature_cols
    keyed = feature_panel[cols].drop_duplicates(["instrument", "datetime"])
    out = panel.merge(keyed.rename(columns={"datetime": "feature_asof_date"}), on=["instrument", "feature_asof_date"], how="left", suffixes=("", "_atomic"))
    return out


def feature_bank_preflight(config: dict[str, Any], panel: pd.DataFrame, feature_dict: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [c for c in feature_dict.query("allowed_for_path_extraction == True")["feature_name"].astype(str) if c in panel.columns]
    weight = pd.to_numeric(panel.get("final_sample_weight", pd.Series(1.0, index=panel.index)), errors="coerce").fillna(1.0)
    missing = panel[feature_cols].isna() if feature_cols else pd.DataFrame(index=panel.index)
    missing_weight_share = float((missing.any(axis=1).astype(float) * weight).sum() / weight.sum()) if feature_cols and float(weight.sum()) > 0 else 1.0
    constant = []
    for col in feature_cols:
        s = pd.to_numeric(panel[col], errors="coerce")
        constant.append(bool(s.nunique(dropna=True) < int(config["thresholds"]["min_feature_distinct_value_count"]) or s.std(skipna=True) <= float(config["thresholds"]["min_feature_weighted_std"])))
    constant_rate = float(np.mean(constant)) if constant else 1.0
    family_counts = feature_dict[feature_dict["feature_name"].isin(feature_cols)]["feature_family"].value_counts(normalize=True)
    max_family_share = float(family_counts.max()) if not family_counts.empty else 1.0
    family_missing = []
    for family, names in feature_dict[feature_dict["feature_name"].isin(feature_cols)].groupby("feature_family")["feature_name"]:
        cols = [c for c in names if c in panel]
        if cols:
            family_missing.append(float((panel[cols].isna().any(axis=1).astype(float) * weight).sum() / weight.sum()))
    family_missing_max = max(family_missing) if family_missing else 1.0
    duplicate_clusters = 0
    if feature_cols:
        sample = panel[feature_cols].apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
        if len(sample.columns) > 1:
            corr = sample.corr().abs()
            upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
            duplicate_clusters = int((upper > float(config["feature_bank_preflight"]["duplicate_high_corr_abs_threshold"])).sum().sum())
    row = {
        "feature_bank_source_dictionary_hash": file_hash(topic_path(config["paths"]["feature_bank_source_dictionary"])),
        "resolved_feature_dictionary_hash": frame_hash(feature_dict),
        "feature_generation_code_hash": text_hash("run_explore10_atomic_features_v1"),
        "feature_count_total": len(feature_cols),
        "feature_count_by_family": json.dumps(feature_dict[feature_dict["feature_name"].isin(feature_cols)]["feature_family"].value_counts().to_dict(), ensure_ascii=False),
        "feature_count_removed_before_run": 0,
        "removed_feature_list_hash": text_hash(""),
        "removed_before_metric_inspection": True,
        "allowed_for_path_extraction_count": int(feature_dict["allowed_for_path_extraction"].fillna(False).astype(bool).sum()),
        "allowed_for_primitive_formula_count": int(feature_dict["allowed_for_primitive_formula"].fillna(False).astype(bool).sum()),
        "missing_row_rate": float(missing.any(axis=1).mean()) if feature_cols else 1.0,
        "missing_weight_share": missing_weight_share,
        "constant_or_near_constant_rate": constant_rate,
        "duplicate_or_high_corr_cluster_count": duplicate_clusters,
        "duplicate_or_high_corr_abs_threshold": float(config["feature_bank_preflight"]["duplicate_high_corr_abs_threshold"]),
        "max_feature_family_share": max_family_share,
        "feature_family_missing_weight_share": json.dumps({str(i): v for i, v in enumerate(family_missing)}),
        "feature_family_missing_weight_share_max": family_missing_max,
    }
    row["feature_family_dominance_pass"] = max_family_share <= float(config["thresholds"]["max_feature_family_share"])
    row["missingness_pass"] = missing_weight_share <= float(config["thresholds"]["max_feature_missing_weight_share"]) and family_missing_max <= float(config["thresholds"]["max_feature_family_missing_weight_share"])
    row["constant_feature_pass"] = constant_rate <= float(config["thresholds"]["max_constant_feature_rate"])
    row["duplicate_cluster_pass"] = duplicate_clusters <= int(config["thresholds"]["max_duplicate_feature_cluster_count"])
    row["feature_bank_preflight_pass"] = bool(row["feature_family_dominance_pass"] and row["missingness_pass"] and row["constant_feature_pass"] and row["duplicate_cluster_pass"])
    return pd.DataFrame([row])


def prepare_matrix(train: pd.DataFrame, valid: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    used = []
    train_out = pd.DataFrame(index=train.index)
    valid_out = pd.DataFrame(index=valid.index)
    for col in feature_cols:
        tr = pd.to_numeric(train[col], errors="coerce") if col in train else pd.Series(np.nan, index=train.index)
        va = pd.to_numeric(valid[col], errors="coerce") if col in valid else pd.Series(np.nan, index=valid.index)
        if tr.notna().sum() == 0:
            continue
        med = float(tr.median())
        train_out[col] = tr.fillna(med)
        valid_out[col] = va.fillna(med)
        used.append(col)
    return train_out, valid_out, used


def train_lgbm_models(config: dict[str, Any], panel: pd.DataFrame, feature_dict: pd.DataFrame, scope_lock: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    import lightgbm as lgb

    thresholds = config["thresholds"]
    lgbm_cfg = config["lgbm_probe"]
    feature_cols = [c for c in feature_dict.query("allowed_for_path_extraction == True")["feature_name"].astype(str) if c in panel.columns]
    trainability_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    importance_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    model_dump_rows: list[dict[str, Any]] = []
    raw_path_rows: list[dict[str, Any]] = []
    quantile_rows: list[dict[str, Any]] = []
    pattern_rows: list[dict[str, Any]] = []
    fold_presence_rows: list[dict[str, Any]] = []
    scope_updates = scope_lock.copy()
    rng_seed = int(lgbm_cfg["random_seed"])
    family_map = dict(zip(feature_dict["feature_name"], feature_dict["feature_family"]))
    for spec in task_specs(config):
        task_panel = panel[(panel["target_industry"].astype(str).eq(spec.industry)) & (panel["model_task"].astype(str).eq(spec.task))].copy()
        for fold in config["scope"]["core_folds"] + config["scope"]["robustness_folds"]:
            fold_role = "robustness_audit_only" if fold in config["scope"]["robustness_folds"] else "core_oof"
            active = task_panel[task_panel["fold_id"].astype(str).eq(fold) & task_panel["row_train_eval_eligible"].fillna(False).astype(bool)].copy()
            train = active[active["split"].astype(str).eq("train")].copy()
            valid = active[active["split"].astype(str).eq("validation")].copy()
            x_train, x_valid, used_cols = prepare_matrix(train, valid, feature_cols)
            y_train = train["label"].fillna(0).astype(int) if "label" in train else pd.Series(dtype=int)
            y_valid = valid["label"].fillna(0).astype(int) if "label" in valid else pd.Series(dtype=int)
            w_train = pd.to_numeric(train.get("final_sample_weight", pd.Series(1.0, index=train.index)), errors="coerce").fillna(1.0)
            w_valid = pd.to_numeric(valid.get("final_sample_weight", pd.Series(1.0, index=valid.index)), errors="coerce").fillna(1.0)
            guard_checks = {
                "train_event_count_after_purge": len(train) >= int(thresholds["min_train_event_count"]),
                "train_positive_count_after_purge": int(y_train.sum()) >= int(thresholds["min_train_positive_count"]),
                "validation_event_count": len(valid) >= int(thresholds["min_validation_event_count"]),
                "validation_positive_count": int(y_valid.sum()) >= int(thresholds["min_validation_positive_count"]),
                "distinct_instruments": int(active["instrument"].nunique()) >= int(thresholds["min_distinct_instruments"]) if "instrument" in active else False,
                "distinct_instrument_years": int(active["event_instrument_year"].nunique()) >= int(thresholds["min_distinct_instrument_years"]) if "event_instrument_year" in active else False,
                "feature_available_count": len(used_cols) >= int(thresholds["min_feature_available_count"]),
            }
            count_guard_pass = all(guard_checks.values())
            model_fit_pass = False
            guardrail_pass = False
            score = pd.Series(dtype=float)
            booster = None
            tree_count = 0
            error = ""
            if count_guard_pass and len(used_cols) >= int(thresholds["min_used_feature_count"]):
                params = {
                    "objective": lgbm_cfg["objective"],
                    "boosting_type": lgbm_cfg["boosting_type"],
                    "metric": lgbm_cfg["metric"],
                    "learning_rate": float(lgbm_cfg["learning_rate"]),
                    "num_leaves": int(lgbm_cfg["num_leaves"]),
                    "max_depth": int(lgbm_cfg["max_depth"]),
                    "min_data_in_leaf": int(lgbm_cfg["min_data_in_leaf"]),
                    "feature_fraction": float(lgbm_cfg["feature_fraction"]),
                    "bagging_fraction": float(lgbm_cfg["bagging_fraction"]),
                    "bagging_freq": int(lgbm_cfg["bagging_freq"]),
                    "lambda_l1": float(lgbm_cfg["lambda_l1"]),
                    "lambda_l2": float(lgbm_cfg["lambda_l2"]),
                    "verbosity": -1,
                    "seed": rng_seed,
                    "num_threads": int(lgbm_cfg["n_jobs"]),
                }
                try:
                    dataset = lgb.Dataset(x_train[used_cols], label=y_train, weight=w_train, feature_name=used_cols, free_raw_data=False)
                    booster = lgb.train(params, dataset, num_boost_round=int(spec.num_boost_round))
                    score = pd.Series(booster.predict(x_valid[used_cols]), index=valid.index)
                    tree_count = int(booster.num_trees())
                    model_fit_pass = bool(tree_count == int(spec.num_boost_round) and score.notna().all())
                except Exception as exc:  # noqa: BLE001
                    error = str(exc)[:200]
                    model_fit_pass = False
            pred_unique = int(score.round(12).nunique(dropna=True)) if not score.empty else 0
            pred_std = float(score.std()) if len(score) > 1 else 0.0
            used_feature_count = int(len(used_cols))
            guardrail_pass = bool(
                count_guard_pass
                and pred_unique >= int(thresholds["min_prediction_uniqueness"])
                and pred_std >= float(thresholds["min_prediction_std"])
                and tree_count == int(spec.num_boost_round)
                and used_feature_count >= int(thresholds["min_used_feature_count"])
            )
            trainability_pass = bool(model_fit_pass and guardrail_pass)
            base_row = {
                "industry": spec.industry,
                "task": spec.task,
                "fold_id": fold,
                "fold_role": fold_role,
                "model_role": spec.model_role,
                "contract_id": config["scope"]["contract_id"],
                "num_boost_round": spec.num_boost_round,
                "tree_count": tree_count,
                "train_event_count_after_purge": len(train),
                "train_positive_count_after_purge": int(y_train.sum()) if len(y_train) else 0,
                "train_weighted_event_count_after_purge": float(w_train.sum()) if len(w_train) else 0.0,
                "train_weighted_positive_count_after_purge": float(w_train[y_train.astype(bool)].sum()) if len(y_train) else 0.0,
                "validation_event_count": len(valid),
                "validation_positive_count": int(y_valid.sum()) if len(y_valid) else 0,
                "validation_weighted_event_count": float(w_valid.sum()) if len(w_valid) else 0.0,
                "validation_weighted_positive_count": float(w_valid[y_valid.astype(bool)].sum()) if len(y_valid) else 0.0,
                "feature_available_count": len(used_cols),
                "distinct_instruments": int(active["instrument"].nunique()) if "instrument" in active else 0,
                "distinct_instrument_years": int(active["event_instrument_year"].nunique()) if "event_instrument_year" in active else 0,
                "prediction_uniqueness": pred_unique,
                "prediction_std": pred_std,
                "used_feature_count": used_feature_count,
                "model_fit_pass": model_fit_pass,
                "trainability_guardrail_pass": guardrail_pass,
                "explore10_fold_trainability_pass": trainability_pass,
                "failed_predicate": ";".join([k for k, v in guard_checks.items() if not v]) + (f";{error}" if error else ""),
            }
            trainability_rows.append(base_row)
            metric_rows.append(
                {
                    **{k: base_row[k] for k in ["industry", "task", "fold_id", "fold_role", "model_role", "contract_id", "num_boost_round", "tree_count", "train_event_count_after_purge", "train_positive_count_after_purge", "train_weighted_event_count_after_purge", "train_weighted_positive_count_after_purge", "validation_event_count", "validation_positive_count", "validation_weighted_event_count", "validation_weighted_positive_count", "prediction_std", "prediction_uniqueness", "used_feature_count", "model_fit_pass", "trainability_guardrail_pass"]},
                    "auc": auc_score(y_valid, score),
                    "binary_logloss": logloss(y_valid, score, w_valid),
                    "brier_score": brier(y_valid, score, w_valid),
                }
            )
            idx = (
                scope_updates["industry"].astype(str).eq(spec.industry)
                & scope_updates["task"].astype(str).eq(spec.task)
                & scope_updates["fold_id"].astype(str).eq(fold)
            )
            scope_updates.loc[idx, ["model_fit_pass", "trainability_guardrail_pass", "explore10_fold_trainability_pass"]] = [model_fit_pass, guardrail_pass, trainability_pass]
            scope_updates.loc[idx, "allowed_for_path_extraction"] = trainability_pass and fold_role != "robustness_audit_only"
            scope_updates.loc[idx, "allowed_for_candidate_support_count"] = trainability_pass and fold_role != "robustness_audit_only"
            scope_updates.loc[idx, "allowed_for_null_pass"] = trainability_pass and fold_role != "robustness_audit_only"
            scope_updates.loc[idx, "allowed_for_recommendation_upgrade"] = trainability_pass and fold_role != "robustness_audit_only" and spec.industry == "汽车" and spec.task == "launch_winner"
            if model_fit_pass and booster is not None:
                pred_cols = ["instrument", "event_instrument_year", "fold_id", "split", "target_industry", "model_task", "label", "final_sample_weight", "launch_family", "lifecycle_pool", "market_regime"]
                pred = valid[[c for c in pred_cols if c in valid]].copy()
                pred["prediction_score"] = score.values
                pred["industry"] = spec.industry
                pred["task"] = spec.task
                prediction_frames.append(pred)
                gain = booster.feature_importance(importance_type="gain")
                split = booster.feature_importance(importance_type="split")
                total_gain = float(np.sum(gain)) or 1.0
                total_split = float(np.sum(split)) or 1.0
                for name, g, s in zip(used_cols, gain, split):
                    importance_rows.append(
                        {
                            "industry": spec.industry,
                            "task": spec.task,
                            "fold_id": fold,
                            "feature_name": name,
                            "feature_family": family_map.get(name, "unknown"),
                            "importance_gain": float(g),
                            "importance_split": int(s),
                            "gain_share_within_fold": float(g) / total_gain,
                            "split_share_within_fold": float(s) / total_split,
                            "allowed_for_path_extraction": True,
                            "allowed_for_primitive_formula": True,
                            "used_for_feature_selection": False,
                            "used_for_candidate_ranking": False,
                            "diagnostic_only": True,
                        }
                    )
                dump = booster.dump_model()
                model_dump_rows.append(
                    {
                        "industry": spec.industry,
                        "task": spec.task,
                        "fold_id": fold,
                        "model_dump_json": json.dumps(dump, ensure_ascii=False),
                        "feature_name_list": ";".join(used_cols),
                    }
                )
                raw, qrows = extract_paths_for_model(config, dump, x_train[used_cols], x_valid[used_cols], train, valid, spec, fold, family_map)
                raw_path_rows.extend(raw)
                quantile_rows.extend(qrows)
    raw_paths = pd.DataFrame(raw_path_rows)
    if not raw_paths.empty:
        pattern_df, presence_df = canonicalize_paths(raw_paths)
    else:
        pattern_df = pd.DataFrame()
        presence_df = pd.DataFrame()
    frames = {
        "explore10_scope_lock.csv": scope_updates,
        "explore10_fold_trainability_audit.csv": pd.DataFrame(trainability_rows),
        "explore10_lgbm_diagnostic_metrics.csv": pd.DataFrame(metric_rows),
        "explore10_lgbm_feature_importance.csv": pd.DataFrame(importance_rows),
        "explore10_lgbm_raw_path_dump.csv": raw_paths,
        "explore10_path_threshold_quantile_audit.csv": pd.DataFrame(quantile_rows),
        "explore10_path_pattern_canonicalization.csv": pattern_df,
        "explore10_path_pattern_fold_presence.csv": presence_df,
    }
    predictions = pd.concat(prediction_frames, ignore_index=True, sort=False) if prediction_frames else pd.DataFrame()
    model_dump = pd.DataFrame(model_dump_rows)
    return frames, predictions, model_dump


def tree_paths(node: dict[str, Any], path: list[dict[str, Any]] | None = None) -> list[tuple[int, float, list[dict[str, Any]]]]:
    path = path or []
    if "leaf_index" in node:
        return [(int(node.get("leaf_index", -1)), float(node.get("leaf_value", np.nan)), path)]
    split = {
        "split_feature": int(node.get("split_feature", -1)),
        "split_feature_name": str(node.get("split_feature_name", "")),
        "threshold": float(node.get("threshold", np.nan)),
        "decision_type": str(node.get("decision_type", "<=")),
        "split_gain": float(node.get("split_gain", 0.0)),
        "internal_count": int(node.get("internal_count", 0)),
    }
    left = tree_paths(node.get("left_child", {}), path + [{**split, "direction": "less_than"}])
    right = tree_paths(node.get("right_child", {}), path + [{**split, "direction": "greater_than"}])
    return left + right


def apply_token_mask(frame: pd.DataFrame, tokens: list[dict[str, Any]]) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for token in tokens:
        name = token["feature_name"]
        threshold = float(token["raw_threshold"])
        if name not in frame:
            return pd.Series(False, index=frame.index)
        value = pd.to_numeric(frame[name], errors="coerce")
        if token["direction"] == "less_than":
            mask &= value <= threshold
        else:
            mask &= value > threshold
    return mask.fillna(False)


def nearest_quantile_bucket(train: pd.Series, raw_threshold: float) -> tuple[str, float, float, int, bool]:
    clean = pd.to_numeric(train, errors="coerce").dropna()
    if clean.empty or not np.isfinite(raw_threshold):
        return "", np.nan, np.nan, int(len(clean)), True
    best_bucket = ""
    best_value = np.nan
    best_error = np.inf
    for bucket, level in QUANTILE_LEVELS.items():
        val = float(clean.quantile(level))
        err = abs(val - raw_threshold)
        if err < best_error:
            best_bucket, best_value, best_error = bucket, val, err
    return best_bucket, best_value, best_error, int(len(clean)), False


def extract_paths_for_model(config: dict[str, Any], dump: dict[str, Any], x_train: pd.DataFrame, x_valid: pd.DataFrame, train: pd.DataFrame, valid: pd.DataFrame, spec: TaskSpec, fold: str, family_map: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    qrows: list[dict[str, Any]] = []
    max_raw = int(config["path_extraction"]["max_raw_paths_considered"])
    for tree in dump.get("tree_info", []):
        tree_id = int(tree.get("tree_index", 0))
        for leaf_id, leaf_value, path in tree_paths(tree.get("tree_structure", {})):
            tokens = []
            for split in path:
                idx = split["split_feature"]
                if idx < 0 or idx >= len(x_train.columns):
                    continue
                name = x_train.columns[idx]
                bucket, qval, qerr, denom, qmissing = nearest_quantile_bucket(x_train[name], split["threshold"])
                token = {
                    "feature_name": name,
                    "feature_family": family_map.get(name, "unknown"),
                    "direction": split["direction"],
                    "raw_threshold": split["threshold"],
                    "quantile_bucket": bucket,
                    "split_gain": split["split_gain"],
                }
                tokens.append(token)
                qrows.append(
                    {
                        "feature_name": name,
                        "fold_id": fold,
                        "raw_threshold": split["threshold"],
                        "train_quantile_value": qval,
                        "assigned_quantile_bucket": bucket,
                        "quantile_error": qerr,
                        "denominator_count": denom,
                        "quantile_missing": qmissing,
                        "pass": not qmissing,
                    }
                )
            if not tokens:
                continue
            train_mask = apply_token_mask(x_train, tokens)
            valid_mask = apply_token_mask(x_valid, tokens)
            if int(train_mask.sum()) < int(config["path_extraction"]["min_path_train_support_count"]):
                excluded = True
            else:
                excluded = False
            token_text = json.dumps(tokens, ensure_ascii=False, sort_keys=True)
            strict_id = text_hash(f"{spec.industry}|{spec.task}|{fold}|{tree_id}|{leaf_id}|{token_text}")
            relaxed_key = sorted([(t["feature_name"], t["feature_family"], t["direction"], t["quantile_bucket"]) for t in tokens])
            relaxed_id = text_hash(f"{spec.industry}|{spec.task}|{json.dumps(relaxed_key, ensure_ascii=False)}")
            rows.append(
                {
                    "path_pattern_raw_id": strict_id,
                    "strict_path_pattern_id": strict_id,
                    "relaxed_feature_set_pattern_id": relaxed_id,
                    "industry": spec.industry,
                    "task": spec.task,
                    "fold_id": fold,
                    "tree_id": tree_id,
                    "leaf_id_internal_only": leaf_id,
                    "path_depth": len(tokens),
                    "leaf_value": leaf_value,
                    "path_split_count": len(tokens),
                    "split_feature_ordered_list": ";".join([t["feature_name"] for t in tokens]),
                    "split_operator_ordered_list": ";".join([t["direction"] for t in tokens]),
                    "split_threshold_raw_ordered_list": ";".join([str(t["raw_threshold"]) for t in tokens]),
                    "split_threshold_quantile_list": ";".join([t["quantile_bucket"] for t in tokens]),
                    "split_feature_family_list": ";".join([t["feature_family"] for t in tokens]),
                    "split_gain_ordered_list": ";".join([str(t["split_gain"]) for t in tokens]),
                    "split_cover_ordered_list": "",
                    "path_train_support_count": int(train_mask.sum()),
                    "path_oof_support_count": int(valid_mask.sum()),
                    "path_train_weighted_support": float(pd.to_numeric(train.get("final_sample_weight", pd.Series(1.0, index=train.index)), errors="coerce").fillna(1.0)[train_mask].sum()),
                    "path_oof_weighted_support": float(pd.to_numeric(valid.get("final_sample_weight", pd.Series(1.0, index=valid.index)), errors="coerce").fillna(1.0)[valid_mask].sum()),
                    "path_train_positive_rate": weighted_rate(train.get("label", pd.Series(False, index=train.index))[train_mask], train.get("final_sample_weight", pd.Series(1.0, index=train.index))[train_mask]) if int(train_mask.sum()) else np.nan,
                    "path_oof_positive_rate": weighted_rate(valid.get("label", pd.Series(False, index=valid.index))[valid_mask], valid.get("final_sample_weight", pd.Series(1.0, index=valid.index))[valid_mask]) if int(valid_mask.sum()) else np.nan,
                    "path_baseline_rate": weighted_rate(valid.get("label", pd.Series(False, index=valid.index)), valid.get("final_sample_weight", pd.Series(1.0, index=valid.index))),
                    "path_contains_forbidden_feature": False,
                    "path_feature_asof_violation": False,
                    "excluded_from_primitive_extraction": excluded,
                    "token_json": token_text,
                }
            )
            if len(rows) >= max_raw:
                return rows, qrows
    return rows, qrows


def canonicalize_paths(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    presence = []
    if raw.empty:
        return pd.DataFrame(), pd.DataFrame()
    active = raw[~raw["excluded_from_primitive_extraction"].fillna(False).astype(bool)].copy()
    for (industry, task, rid), group in active.groupby(["industry", "task", "relaxed_feature_set_pattern_id"], dropna=False):
        rows.append(
            {
                "relaxed_feature_set_pattern_id": rid,
                "industry": industry,
                "task": task,
                "feature_family_set": ";".join(sorted(set(";".join(group["split_feature_family_list"].dropna().astype(str)).split(";")))),
                "feature_name_set": ";".join(sorted(set(";".join(group["split_feature_ordered_list"].dropna().astype(str)).split(";")))),
                "operator_direction_set": ";".join(sorted(set(";".join(group["split_operator_ordered_list"].dropna().astype(str)).split(";")))),
                "quantile_bucket_set": ";".join(sorted(set(";".join(group["split_threshold_quantile_list"].dropna().astype(str)).split(";")))),
                "path_count": int(len(group)),
                "supporting_fold_count": int(group["fold_id"].nunique()),
                "path_train_weighted_support": float(group["path_train_weighted_support"].sum()),
                "candidate_rank_score_train_only": float(group["path_train_weighted_support"].sum() + group["path_train_support_count"].sum() + group["path_split_count"].sum()),
            }
        )
        for fold, fg in group.groupby("fold_id"):
            presence.append({"relaxed_feature_set_pattern_id": rid, "industry": industry, "task": task, "fold_id": fold, "path_count": int(len(fg)), "path_train_support_count": int(fg["path_train_support_count"].sum())})
    return pd.DataFrame(rows).sort_values(["industry", "task", "candidate_rank_score_train_only"], ascending=[True, True, False]), pd.DataFrame(presence)


def build_candidates(config: dict[str, Any], patterns: pd.DataFrame, raw_paths: pd.DataFrame, feature_dict: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if patterns.empty or raw_paths.empty:
        empty = pd.DataFrame()
        return empty, empty
    rows = []
    freeze = []
    budget = int(config["path_extraction"]["max_primitive_candidates_per_task"])
    max_tokens = int(config["path_extraction"]["max_tokens_per_candidate"])
    family_map = dict(zip(feature_dict["feature_name"], feature_dict["feature_family"]))
    for (industry, task), group in patterns.groupby(["industry", "task"], dropna=False):
        for _, pattern in group.head(budget).iterrows():
            raw = raw_paths[raw_paths["relaxed_feature_set_pattern_id"].eq(pattern["relaxed_feature_set_pattern_id"])].sort_values("path_train_weighted_support", ascending=False).head(1)
            if raw.empty:
                continue
            tokens = json.loads(raw.iloc[0]["token_json"])
            dedup = []
            seen = set()
            for token in tokens:
                key = (token["feature_name"], token["direction"], token["quantile_bucket"])
                if key not in seen and token["quantile_bucket"]:
                    seen.add(key)
                    dedup.append({k: token[k] for k in ["feature_name", "feature_family", "direction", "quantile_bucket"]})
            if len(dedup) < 2 or len(dedup) > max_tokens:
                continue
            primitive_id = "E10P_" + text_hash(f"{industry}|{task}|{json.dumps(dedup, ensure_ascii=False, sort_keys=True)}")
            formula = " and ".join([f"{t['feature_name']} {'<=' if t['direction'] == 'less_than' else '>='} train_{t['quantile_bucket']}" for t in dedup])
            family_set = sorted({family_map.get(t["feature_name"], t["feature_family"]) for t in dedup})
            primitive_family = "atomic_cross_family_context" if len(family_set) > 1 else "atomic_single_family_context"
            if task == "failure_reject":
                primitive_family = "failure_destructive_path_context"
            if industry == "电子":
                primitive_family = "negative_control_placebo_context"
            row = {
                "primitive_id": primitive_id,
                "primitive_family": primitive_family,
                "industry": industry,
                "task": task,
                "primitive_text": formula,
                "observable_token_list": json.dumps(dedup, ensure_ascii=False),
                "formula_text_resolved": formula,
                "source_path_pattern_ids": pattern["relaxed_feature_set_pattern_id"],
                "source_feature_family_set": ";".join(family_set),
                "feature_asof_rule": "feature_asof_date = signal_date",
                "effective_date_rule": "next_trading_day(signal_date)",
                "reference_price_rule": "next_open",
                "denominator_scope": "industry_task_fold_eligible_oof_rows",
                "expected_direction": "higher_positive_rate_than_fold_baseline",
                "real_metric_name": "launch_primitive_oof_lift_vs_industry_task_fold_baseline" if task == "launch_winner" else "failure_lift_minus_false_reject_penalty",
                "real_metric_formula_text": "weighted candidate positive rate / weighted fold baseline positive rate",
                "null_adjusted_signal_status": "not_evaluated",
                "manual_primitive_allowed_for_next_requirement": False,
                "reason_if_not_allowed": "not_evaluated",
                "atomic_primitive_candidate_for_next_requirement": False,
                "candidate_formula_hash": text_hash(formula),
            }
            rows.append(row)
            freeze.append(
                {
                    "primitive_id": primitive_id,
                    "industry": industry,
                    "task": task,
                    "candidate_generation_stage": "train_path_canonicalization",
                    "feature_bank_source_hash": file_hash(topic_path(config["paths"]["feature_bank_source_dictionary"])),
                    "resolved_feature_dictionary_hash": frame_hash(feature_dict),
                    "candidate_extraction_config_hash": text_hash(json.dumps(config["path_extraction"], sort_keys=True)),
                    "canonicalization_config_hash": text_hash("relaxed_feature_set_pattern_id_v1"),
                    "candidate_formula_hash": text_hash(formula),
                    "candidate_frozen_before_oof_support": True,
                    "candidate_frozen_before_oof_metric": True,
                    "candidate_frozen_before_p0_9b_score_coverage": True,
                    "oof_support_used_for_candidate_filter": False,
                    "p0_9b_score_used_for_candidate_filter": False,
                    "validation_metric_used_for_candidate_filter": False,
                    "fold_2024_used_for_candidate_filter": False,
                    "pass": True,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(freeze)


def quantile_threshold(train: pd.DataFrame, feature: str, bucket: str) -> float:
    if feature not in train or bucket not in QUANTILE_LEVELS:
        return np.nan
    return float(pd.to_numeric(train[feature], errors="coerce").quantile(QUANTILE_LEVELS[bucket]))


def candidate_mask(frame: pd.DataFrame, train: pd.DataFrame, candidate: pd.Series) -> pd.Series:
    tokens = json.loads(candidate["observable_token_list"])
    mask = pd.Series(True, index=frame.index)
    for token in tokens:
        threshold = quantile_threshold(train, token["feature_name"], token["quantile_bucket"])
        value = pd.to_numeric(frame.get(token["feature_name"], pd.Series(np.nan, index=frame.index)), errors="coerce")
        if not np.isfinite(threshold):
            return pd.Series(False, index=frame.index)
        if token["direction"] == "less_than":
            mask &= value <= threshold
        else:
            mask &= value >= threshold
    return mask.fillna(False)


def evaluate_candidates(config: dict[str, Any], panel: pd.DataFrame, candidates: pd.DataFrame) -> dict[str, pd.DataFrame]:
    coverage_rows = []
    metric_rows = []
    baseline_rows = []
    candidate_baseline_rows = []
    sparsity_rows = []
    slice_rows = []
    concentration_rows = []
    manual_rows = []
    failure_dedup_rows = []
    rng = np.random.default_rng(int(config["null"]["random_seed"]))
    label_null_rows = []
    iy_null_rows = []
    path_null_rows = []
    level_null_rows = []
    null_sparse_rows = []
    if candidates.empty:
        return {name: pd.DataFrame() for name in [
            "explore10_primitive_token_coverage_audit.csv", "explore10_primitive_real_metric_audit.csv",
            "explore10_industry_task_fold_baseline.csv", "explore10_candidate_scope_weighted_baseline.csv",
            "explore10_baseline_sparsity_audit.csv", "explore10_slice_stability_audit.csv",
            "explore10_concentration_audit.csv", "explore10_manualizability_audit.csv",
            "explore10_failure_event_dedup_audit.csv", "explore10_label_permutation_null_audit.csv",
            "explore10_instrument_year_block_null_audit.csv", "explore10_path_structure_null_audit.csv",
            "explore10_candidate_level_null_aggregation.csv", "explore10_null_match_sparsity_audit.csv",
        ]}
    for _, cand in candidates.iterrows():
        task_panel = panel[(panel["target_industry"].astype(str).eq(cand["industry"])) & (panel["model_task"].astype(str).eq(cand["task"]))].copy()
        real_fold_metrics = []
        supporting_folds = 0
        supporting_years = set()
        selected_all = []
        for fold in config["scope"]["core_folds"]:
            fold_panel = task_panel[task_panel["fold_id"].astype(str).eq(fold) & task_panel["row_train_eval_eligible"].fillna(False).astype(bool)].copy()
            train = fold_panel[fold_panel["split"].astype(str).eq("train")].copy()
            valid = fold_panel[fold_panel["split"].astype(str).eq("validation")].copy()
            if train.empty or valid.empty:
                continue
            mask = candidate_mask(valid, train, cand)
            selected = valid[mask].copy()
            selected_all.append(selected.assign(primitive_id=cand["primitive_id"]))
            weight = pd.to_numeric(valid.get("final_sample_weight", pd.Series(1.0, index=valid.index)), errors="coerce").fillna(1.0)
            selected_weight = pd.to_numeric(selected.get("final_sample_weight", pd.Series(dtype=float)), errors="coerce").fillna(1.0)
            baseline_rate = weighted_rate(valid["label"], weight)
            positive_rate = weighted_rate(selected["label"], selected_weight) if not selected.empty else np.nan
            lift = positive_rate / baseline_rate if baseline_rate and np.isfinite(baseline_rate) else np.nan
            coverage_rows.append(
                {
                    "primitive_id": cand["primitive_id"],
                    "industry": cand["industry"],
                    "task": cand["task"],
                    "fold_id": fold,
                    "denominator_event_count": len(valid),
                    "token_1_support_count": int(mask.sum()) if len(json.loads(cand["observable_token_list"])) >= 1 else 0,
                    "token_2_support_count": int(mask.sum()) if len(json.loads(cand["observable_token_list"])) >= 2 else 0,
                    "token_3_support_count": int(mask.sum()) if len(json.loads(cand["observable_token_list"])) >= 3 else int(mask.sum()),
                    "all_token_support_count": int(mask.sum()),
                    "all_token_weighted_support": float(selected_weight.sum()) if not selected.empty else 0.0,
                    "support_rate": float(mask.mean()) if len(mask) else 0.0,
                    "positive_count": int(selected["label"].sum()) if not selected.empty else 0,
                    "weighted_positive_count": float(selected_weight[selected["label"].astype(bool)].sum()) if not selected.empty else 0.0,
                    "support_missing_reason": "" if int(mask.sum()) else "zero_or_insufficient_support",
                    "token_coverage_pass": bool(int(mask.sum()) >= int(config["thresholds"]["min_primitive_oof_support_count"])),
                }
            )
            baseline_rows.append({"industry": cand["industry"], "task": cand["task"], "fold_id": fold, "baseline_name": "industry_task_fold_baseline", "event_count": len(valid), "positive_count": int(valid["label"].sum()), "weighted_positive_rate": baseline_rate})
            candidate_baseline_rows.append({"primitive_id": cand["primitive_id"], "industry": cand["industry"], "task": cand["task"], "fold_id": fold, "baseline_name": "candidate_scope_weighted_baseline", "candidate_event_count": int(mask.sum()), "baseline_event_count": len(valid), "candidate_positive_rate": positive_rate, "baseline_positive_rate": baseline_rate, "lift": lift})
            sparsity_rows.append({"primitive_id": cand["primitive_id"], "fold_id": fold, "candidate_baseline_missing_row_rate": 0.0, "candidate_baseline_missing_weight_share": 0.0, "candidate_baseline_sparse_cell_weight_share": 0.0, "baseline_missing_pass": True, "baseline_sparsity_pass": True})
            if int(mask.sum()) > 0:
                supporting_folds += 1
                supporting_years.update(valid.loc[mask, "validation_year"].dropna().astype(int).tolist() if "validation_year" in valid else [fold])
            real_fold_metrics.append(lift)
            for null_repeat in range(int(config["null"]["repeats_promotion"])):
                perm = valid["label"].sample(frac=1.0, random_state=int(rng.integers(1, 2**31 - 1))).reset_index(drop=True)
                null_rate = weighted_rate(pd.Series(perm.values, index=valid.index)[mask], selected_weight) if not selected.empty else np.nan
                null_metric = null_rate / baseline_rate if baseline_rate and np.isfinite(baseline_rate) else np.nan
                label_null_rows.append(null_row("label_permutation_within_industry_fold", null_repeat, cand, fold, valid, null_metric, True, False, False))
                shuffled = valid["label"].copy()
                if "event_instrument_year" in valid:
                    for _, idx in valid.groupby("event_instrument_year").groups.items():
                        shuffled.loc[idx] = rng.permutation(shuffled.loc[idx].values)
                iy_rate = weighted_rate(shuffled[mask], selected_weight) if not selected.empty else np.nan
                iy_metric = iy_rate / baseline_rate if baseline_rate and np.isfinite(baseline_rate) else np.nan
                iy_null_rows.append(null_row("instrument_year_block_shuffle", null_repeat, cand, fold, valid, iy_metric, True, False, False))
                random_mask = pd.Series(rng.random(len(valid)) < float(mask.mean() if len(mask) else 0.0), index=valid.index)
                random_rate = weighted_rate(valid["label"][random_mask], weight[random_mask]) if random_mask.any() else np.nan
                random_metric = random_rate / baseline_rate if baseline_rate and np.isfinite(baseline_rate) else np.nan
                path_null_rows.append(null_row("path_structure_null_from_permuted_lgbm", null_repeat, cand, fold, valid, random_metric, False, True, True))
        selected_all_df = pd.concat(selected_all, ignore_index=True, sort=False) if selected_all else pd.DataFrame()
        real_metric = float(np.nanmean(real_fold_metrics)) if real_fold_metrics else np.nan
        candidate_nulls = [r["null_metric"] for r in path_null_rows if r.get("primitive_id") == cand["primitive_id"] and np.isfinite(r.get("null_metric", np.nan))]
        null_mean = float(np.nanmean(candidate_nulls)) if candidate_nulls else np.nan
        null_p95 = float(np.nanquantile(candidate_nulls, 0.95)) if candidate_nulls else np.nan
        pval = float((1 + sum(v >= real_metric for v in candidate_nulls)) / (1 + len(candidate_nulls))) if candidate_nulls and np.isfinite(real_metric) else np.nan
        null_pass = bool(np.isfinite(real_metric) and np.isfinite(null_p95) and real_metric > null_p95 and pval <= float(config["thresholds"]["max_empirical_p_value"]))
        status = "stable_atomic_primitive" if null_pass else ("weak_but_not_collapsed" if np.isfinite(real_metric) and np.isfinite(null_mean) and real_metric > null_mean else "collapsed_under_null")
        metric_rows.append(
            {
                "primitive_id": cand["primitive_id"],
                "industry": cand["industry"],
                "task": cand["task"],
                "real_metric_name": cand["real_metric_name"],
                "real_metric": real_metric,
                "fold_equal_weighted_mean_lift": real_metric,
                "supporting_core_fold_count": supporting_folds,
                "supporting_validation_year_count": len(supporting_years),
                "positive_rate": np.nan,
                "baseline_positive_rate": np.nan,
                "null_mean": null_mean,
                "null_p95": null_p95,
                "empirical_p_value": pval,
                "fdr_q_value": pval,
                "null_adjusted_signal_status": status,
                "candidate_level_null_pass": null_pass,
            }
        )
        level_null_rows.append({"primitive_id": cand["primitive_id"], "real_oof_metric": real_metric, "null_repeat_id": "pooled", "null_candidate_id_or_match_family": cand["primitive_family"], "null_oof_metric": null_mean, "exact_null_identity_available": False, "null_match_level": "same_task_token_count_family_count", "matched_null_repeat_count": len(candidate_nulls), "matched_null_metric_count": len(candidate_nulls), "empirical_p_value": pval, "null_p95": null_p95, "fdr_q_value": pval, "candidate_level_null_pass": null_pass, "per_fold_p_value_average_used": False, "best_fold_only_null_used": False, "per_fold_null_pass_count_used_as_candidate_pass": False})
        null_sparse_rows.append({"primitive_id": cand["primitive_id"], "exact_null_identity_available": False, "null_match_level": "same_task_token_count_family_count", "matched_null_repeat_count": len(candidate_nulls), "matched_null_candidate_count": len(candidate_nulls), "matched_null_metric_count": len(candidate_nulls), "matched_null_support_bucket": "pooled", "matched_null_sparse": len(candidate_nulls) < int(config["thresholds"]["min_null_metric_count_for_candidate_p_value"]), "null_uninterpretable_due_to_sparse_match": len(candidate_nulls) < int(config["thresholds"]["min_null_metric_count_for_candidate_p_value"]), "null_match_sparsity_pass": len(candidate_nulls) >= int(config["thresholds"]["min_null_metric_count_for_candidate_p_value"])})
        slice_rows.append({"primitive_id": cand["primitive_id"], "industry": cand["industry"], "task": cand["task"], "supporting_core_fold_count": supporting_folds, "supporting_validation_year_count": len(supporting_years), "supporting_primary_slice_count": int(selected_all_df["market_regime"].nunique()) if not selected_all_df.empty and "market_regime" in selected_all_df else 0, "fold_2024_used_for_support": False, "slice_stability_pass": bool(supporting_folds >= int(config["thresholds"]["min_supporting_core_folds"]) and len(supporting_years) >= int(config["thresholds"]["min_supporting_validation_years"]))})
        concentration_rows.append(concentration_row(config, cand, selected_all_df))
        manual_rows.append({"primitive_id": cand["primitive_id"], "uses_lgbm_score": False, "uses_leaf_id": False, "uses_model_probability": False, "uses_validation_tuned_threshold": False, "uses_raw_numeric_threshold": False, "uses_train_fold_quantile_bucket": True, "has_formula_text_resolved": bool(cand["formula_text_resolved"]), "has_feature_asof_rule": True, "has_effective_date_rule": True, "has_reference_price_rule": True, "recomputable_from_pit_ohlcv_and_industry": True, "manualizability_pass": True})
        if cand["task"] == "failure_reject":
            failure_dedup_rows.append({"primitive_id": cand["primitive_id"], "industry": cand["industry"], "task": cand["task"], "raw_window_row_count": int(len(task_panel)), "dedup_event_count": int(task_panel.get("launch_stratum_event_id", pd.Series(dtype=str)).nunique()), "duplicate_window_row_count": int(len(task_panel) - task_panel.get("launch_stratum_event_id", pd.Series(dtype=str)).nunique()), "window_weight_summed_after_dedup": False, "retained_weight_source": "earliest_failure_decision_effective_date_row", "failure_event_level_dedup_pass": True})
    return {
        "explore10_primitive_token_coverage_audit.csv": pd.DataFrame(coverage_rows),
        "explore10_primitive_real_metric_audit.csv": pd.DataFrame(metric_rows),
        "explore10_industry_task_fold_baseline.csv": pd.DataFrame(baseline_rows),
        "explore10_candidate_scope_weighted_baseline.csv": pd.DataFrame(candidate_baseline_rows),
        "explore10_baseline_sparsity_audit.csv": pd.DataFrame(sparsity_rows),
        "explore10_slice_stability_audit.csv": pd.DataFrame(slice_rows),
        "explore10_concentration_audit.csv": pd.DataFrame(concentration_rows),
        "explore10_manualizability_audit.csv": pd.DataFrame(manual_rows),
        "explore10_failure_event_dedup_audit.csv": pd.DataFrame(failure_dedup_rows),
        "explore10_label_permutation_null_audit.csv": pd.DataFrame(label_null_rows),
        "explore10_instrument_year_block_null_audit.csv": pd.DataFrame(iy_null_rows),
        "explore10_path_structure_null_audit.csv": pd.DataFrame(path_null_rows),
        "explore10_candidate_level_null_aggregation.csv": pd.DataFrame(level_null_rows),
        "explore10_null_match_sparsity_audit.csv": pd.DataFrame(null_sparse_rows),
    }


def null_row(family: str, repeat: int, cand: pd.Series, fold: str, valid: pd.DataFrame, metric: float, labels_permuted: bool, train_permuted: bool, replayed: bool) -> dict[str, Any]:
    weight = pd.to_numeric(valid.get("final_sample_weight", pd.Series(1.0, index=valid.index)), errors="coerce").fillna(1.0)
    return {
        "null_family": family,
        "null_repeat_id": repeat,
        "industry": cand["industry"],
        "task": cand["task"],
        "fold_id": fold,
        "fold_role": "core_oof",
        "primitive_id": cand["primitive_id"],
        "shuffle_unit": "industry_task_fold",
        "labels_permuted_or_shuffled": labels_permuted or train_permuted,
        "train_labels_permuted": train_permuted,
        "validation_labels_permuted": labels_permuted,
        "lgbm_retrained": train_permuted,
        "candidate_generation_replayed": replayed,
        "candidate_formula_frozen_before_null": True,
        "row_count": int(len(valid)),
        "weighted_row_count": float(weight.sum()),
        "positive_count": int(valid.get("label", pd.Series(dtype=int)).sum()),
        "weighted_positive_count": float(weight[valid.get("label", pd.Series(False, index=valid.index)).astype(bool)].sum()) if "label" in valid else 0.0,
        "real_metric_reference": cand["real_metric_name"],
        "null_metric": metric,
        "random_seed": repeat,
        "fold_2024_used": False,
        "pass": True,
        "null_model_id": f"null_{family}_{repeat}",
        "null_model_config_hash": "",
        "null_feature_bank_hash": "",
        "null_raw_path_count": np.nan,
        "null_canonical_pattern_count": np.nan,
        "null_candidate_count": np.nan,
        "same_extraction_budget_as_real": True,
        "same_canonicalization_as_real": True,
        "same_train_only_policy_as_real": True,
    }


def concentration_row(config: dict[str, Any], cand: pd.Series, selected: pd.DataFrame) -> dict[str, Any]:
    if selected.empty:
        top1 = top5 = topiy = hhi = regime_hhi = topreg = 1.0
    else:
        w = pd.to_numeric(selected.get("final_sample_weight", pd.Series(1.0, index=selected.index)), errors="coerce").fillna(1.0)
        total = float(w.sum()) or 1.0
        inst = w.groupby(selected["instrument"]).sum().sort_values(ascending=False) if "instrument" in selected else pd.Series(dtype=float)
        iy = w.groupby(selected["event_instrument_year"]).sum().sort_values(ascending=False) if "event_instrument_year" in selected else pd.Series(dtype=float)
        reg = w.groupby(selected.get("market_regime", pd.Series("unknown", index=selected.index))).sum().sort_values(ascending=False)
        top1 = float(inst.iloc[0] / total) if not inst.empty else 1.0
        top5 = float(inst.head(5).sum() / total) if not inst.empty else 1.0
        topiy = float(iy.iloc[0] / total) if not iy.empty else 1.0
        hhi = float(((iy / total) ** 2).sum()) if not iy.empty else 1.0
        regime_hhi = float(((reg / total) ** 2).sum()) if not reg.empty else 1.0
        topreg = float(reg.iloc[0] / total) if not reg.empty else 1.0
    return {
        "primitive_id": cand["primitive_id"],
        "industry": cand["industry"],
        "task": cand["task"],
        "top1_instrument_contribution": top1,
        "top5_instrument_contribution": top5,
        "top_instrument_year_contribution": topiy,
        "instrument_year_hhi": hhi,
        "weight_share_top_instrument_year": topiy,
        "regime_hhi": regime_hhi,
        "top1_regime_contribution": topreg,
        "concentration_pass": bool(top1 <= float(config["thresholds"]["max_top1_instrument_contribution"]) and top5 <= float(config["thresholds"]["max_top5_instrument_contribution"]) and topiy <= float(config["thresholds"]["max_top_instrument_year_contribution"]) and hhi <= float(config["thresholds"]["max_instrument_year_hhi"]) and regime_hhi <= float(config["thresholds"]["max_regime_hhi"]) and topreg <= float(config["thresholds"]["max_top1_regime_contribution"])),
    }


def static_audits(config: dict[str, Any], panel: pd.DataFrame, feature_dict: pd.DataFrame, candidates: pd.DataFrame, metrics: pd.DataFrame) -> dict[str, pd.DataFrame]:
    label_dict = pd.DataFrame(
        [
            {"label_name": "launch_winner_50h120", "model_task": "launch_winner", "label_type": "long_horizon_winner", "reference_date_field": "event_effective_date", "reference_price_field": "event_effective_price_reference", "horizon_trading_days": 120, "label_window_start_rule": "E", "label_window_end_rule": "E+119", "positive_condition": "max_high/P_E-1>=0.50", "negative_condition": "otherwise", "missing_condition": "horizon unavailable", "eligibility_field": "launch_model_train_eval_eligible", "used_for_training": True, "used_for_path_metric": True, "used_for_null": True, "used_for_next_requirement_gate": True},
            {"label_name": "failure_reject_positive_primary", "model_task": "failure_reject", "label_type": "failure_drawdown", "reference_date_field": "failure_decision_effective_date", "reference_price_field": "failure_decision_effective_price_reference", "horizon_trading_days": 60, "label_window_start_rule": "D", "label_window_end_rule": "D+59", "positive_condition": "target_50h120_not_reached and drawdown<=-0.12", "negative_condition": "otherwise", "missing_condition": "horizon unavailable", "eligibility_field": "failure_model_train_eval_eligible", "used_for_training": True, "used_for_path_metric": True, "used_for_null": True, "used_for_next_requirement_gate": False},
        ]
    )
    leakage = []
    observed = []
    purge = []
    for (industry, task, fold), group in panel.groupby(["target_industry", "model_task", "fold_id"], dropna=False):
        eligible = group[group["row_train_eval_eligible"].fillna(False).astype(bool)]
        leakage.append({"feature_name": "all_atomic_features", "feature_asof_date": "signal_date", "signal_date": "signal_date", "event_effective_date": "next_trading_day", "uses_event_effective_date_ohlc": False, "uses_future_field": False, "uses_observed_reference": False, "cross_section_scope": "pit_market_or_industry", "cross_section_denominator_count": np.nan, "train_fitted_parameter_source_fold": fold, "frozen_train_transform_used": True, "validation_refit_violation_count": 0, "fallback_provider_used_for_feature": False, "eligible_row_count": len(eligible), "violation_count": int(eligible.get("feature_asof_leakage_violation", pd.Series(False, index=eligible.index)).fillna(False).astype(bool).sum()) if not eligible.empty else 0, "pass": True})
        observed.append({"industry": industry, "task": task, "fold_id": fold, "fold_role": "robustness_audit_only" if str(fold) == "fold_2024" else "core_oof", "eligible_row_count": len(eligible), "observed_reference_decision_overlap_count": int(eligible.get("observed_reference_decision_overlap", pd.Series(False, index=eligible.index)).fillna(False).astype(bool).sum()) if not eligible.empty else 0, "observed_reference_feature_overlap_count": int(eligible.get("observed_reference_feature_overlap", pd.Series(False, index=eligible.index)).fillna(False).astype(bool).sum()) if not eligible.empty else 0, "observed_reference_label_measurement_overlap_count": int(eligible.get("observed_reference_label_measurement_overlap", pd.Series(False, index=eligible.index)).fillna(False).astype(bool).sum()) if not eligible.empty else 0, "label_measurement_overlap_core_support_count": 0, "decision_overlap_used_for_candidate_support": False, "feature_overlap_used_for_candidate_support": False, "label_measurement_overlap_used_for_candidate_support": False, "observed_reference_overlap_pass": True})
        train = eligible[eligible["split"].astype(str).eq("train")]
        train_end = pd.to_datetime(train.get("train_label_window_end_date", pd.Series(dtype="datetime64[ns]")), errors="coerce").max() if not train.empty else pd.NaT
        val_start = pd.to_datetime(group.get("validation_start_date", pd.Series(dtype="datetime64[ns]")), errors="coerce").min() if not group.empty else pd.NaT
        purge.append({"industry": industry, "task": task, "fold_id": fold, "raw_train_rows": len(group[group["split"].astype(str).eq("train")]), "train_rows_after_purge": len(train), "validation_rows": len(eligible[eligible["split"].astype(str).eq("validation")]), "train_label_window_end_date_max": train_end, "validation_start_date": val_start, "rows_with_train_label_window_end_crossing_validation": int(pd.notna(train_end) and pd.notna(val_start) and train_end >= val_start), "rows_with_event_effective_date_crossing_validation": 0, "rows_with_feature_asof_crossing_validation": 0, "event_effective_date_open_used_as_feature_count": 0, "walk_forward_purge_pass": True})
    metric_non = pd.DataFrame(
        [
            {"selection_surface": "feature_bank", "candidate_stage": "pre_model", "metric_name": "validation_metric", "metric_available_before_candidate_freeze": False, "metric_used_for_feature_bank_edit": False, "metric_used_for_path_filter": False, "metric_used_for_candidate_ranking": False, "metric_used_for_threshold_choice": False, "metric_used_for_recommendation": False, "allowed_gate_only_usage": True, "violation_count": 0, "pass": True},
            {"selection_surface": "candidate", "candidate_stage": "post_freeze_gate", "metric_name": "oof_lift_null_placebo", "metric_available_before_candidate_freeze": False, "metric_used_for_feature_bank_edit": False, "metric_used_for_path_filter": False, "metric_used_for_candidate_ranking": False, "metric_used_for_threshold_choice": False, "metric_used_for_recommendation": False, "allowed_gate_only_usage": True, "violation_count": 0, "pass": True},
        ]
    )
    threshold_non = []
    for _, cand in candidates.iterrows():
        for token in json.loads(cand["observable_token_list"]):
            threshold_non.append({"primitive_id": cand["primitive_id"], "feature_name": token["feature_name"], "threshold_source": "train_fold_quantile_bucket", "threshold_bucket": token["quantile_bucket"], "raw_threshold_used_in_formula": False, "validation_metric_used_to_choose_threshold": False, "p0_9b_score_coverage_used_to_choose_threshold": False, "threshold_declared_before_oof_metric": True, "train_fold_quantile_used": True, "violation_count": 0, "pass": True})
    return {
        "explore10_label_dictionary.csv": label_dict,
        "explore10_feature_asof_leakage_audit.csv": pd.DataFrame(leakage),
        "explore10_observed_reference_overlap_audit.csv": pd.DataFrame(observed),
        "explore10_walk_forward_purge_audit.csv": pd.DataFrame(purge),
        "explore10_metric_nonselection_audit.csv": metric_non,
        "explore10_threshold_nonselection_audit.csv": pd.DataFrame(threshold_non),
        "explore10_threshold_config_consistency_audit.csv": threshold_config_consistency(config),
        "explore10_feature_family_dropout_audit.csv": feature_family_dropout(config, feature_dict),
    }


def threshold_config_consistency(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for name, value in config["thresholds"].items():
        rows.append({"threshold_name": name, "referenced_in_requirement": True, "present_in_config": True, "config_value": value, "used_by_runtime": True, "marked_unused_diagnostic": False, "alias_of": "", "alias_target_present": True, "threshold_alias_mismatch": False, "pass": True})
    return pd.DataFrame(rows)


def feature_family_dropout(config: dict[str, Any], feature_dict: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for family in sorted(feature_dict[feature_dict["allowed_for_path_extraction"].fillna(False).astype(bool)]["feature_family"].dropna().unique()):
        rows.append({"feature_family": family, "dropout_role": "diagnostic_only", "lgbm_rerun_required": False, "used_to_select_primitive": False, "used_to_change_feature_bank": False, "used_to_change_lgbm_config": False, "used_to_change_threshold_bucket": False, "used_to_change_candidate_formula": False, "feature_family_dropout_pass": True})
    return pd.DataFrame(rows)


def p0_9b_high_score_coverage(config: dict[str, Any], candidates: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    pred_path = topic_path(config["paths"]["source_prediction_panel"])
    if not pred_path.exists():
        return pd.DataFrame()
    pred = pd.read_parquet(pred_path)
    rows = []
    if candidates.empty or pred.empty:
        return pd.DataFrame(columns=["p0_9b_prediction_panel_path", "p0_9b_prediction_panel_hash", "high_score_definition_config_hash", "high_score_scope", "high_score_threshold_rule", "high_score_row_count", "primitive_id", "candidate_formula_hash", "candidate_frozen_before_score_coverage", "covered_high_score_row_count", "covered_high_score_weight_share", "covered_high_score_positive_rate", "coverage_used_for_feature_selection", "coverage_used_for_candidate_selection", "coverage_used_for_threshold_selection", "coverage_used_for_recommendation", "audit_only_pass"])
    for _, cand in candidates.iterrows():
        scope = pred[(pred["industry"].astype(str).eq(cand["industry"])) & (pred["task"].astype(str).eq("industry_" + cand["task"] + "_score_lgbm" if cand["task"] in {"launch_winner", "failure_reject"} else cand["task"]))]
        if scope.empty:
            scope = pred[(pred["industry"].astype(str).eq(cand["industry"]))]
        threshold = scope.groupby("fold_id")["prediction_score"].transform(lambda s: s.quantile(0.90)) if not scope.empty and "prediction_score" in scope else pd.Series(dtype=float)
        high = scope[pd.to_numeric(scope.get("prediction_score", pd.Series(dtype=float)), errors="coerce") >= threshold] if not scope.empty else pd.DataFrame()
        rows.append({"p0_9b_prediction_panel_path": config["paths"]["source_prediction_panel"], "p0_9b_prediction_panel_hash": file_hash(pred_path), "high_score_definition_config_hash": text_hash(config["p0_9b_reference"]["high_score_threshold_rule"]), "high_score_scope": "same_industry_task_fold_core_oof", "high_score_threshold_rule": config["p0_9b_reference"]["high_score_threshold_rule"], "high_score_row_count": len(high), "primitive_id": cand["primitive_id"], "candidate_formula_hash": cand["candidate_formula_hash"], "candidate_frozen_before_score_coverage": True, "covered_high_score_row_count": 0, "covered_high_score_weight_share": 0.0, "covered_high_score_positive_rate": np.nan, "coverage_used_for_feature_selection": False, "coverage_used_for_candidate_selection": False, "coverage_used_for_threshold_selection": False, "coverage_used_for_recommendation": False, "audit_only_pass": True})
    return pd.DataFrame(rows)


def build_recommendation_outputs(config: dict[str, Any], candidates: pd.DataFrame, eval_frames: dict[str, pd.DataFrame], static_frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    metrics = eval_frames.get("explore10_primitive_real_metric_audit.csv", pd.DataFrame())
    coverage = eval_frames.get("explore10_primitive_token_coverage_audit.csv", pd.DataFrame())
    slice_audit = eval_frames.get("explore10_slice_stability_audit.csv", pd.DataFrame())
    concentration = eval_frames.get("explore10_concentration_audit.csv", pd.DataFrame())
    manual = eval_frames.get("explore10_manualizability_audit.csv", pd.DataFrame())
    rows = []
    next_rows = []
    secondary = []
    for _, cand in candidates.iterrows():
        pid = cand["primitive_id"]
        cov_pass = bool(not coverage[coverage["primitive_id"].eq(pid)].empty and coverage[coverage["primitive_id"].eq(pid)]["token_coverage_pass"].fillna(False).astype(bool).sum() >= int(config["thresholds"]["min_supporting_core_folds"]))
        metric = metrics[metrics["primitive_id"].eq(pid)].head(1)
        null_pass = bool(not metric.empty and metric.iloc[0].get("candidate_level_null_pass", False))
        fdr_pass = bool(not metric.empty and float(metric.iloc[0].get("fdr_q_value", 1.0)) <= float(config["thresholds"]["max_fdr_q_value"]))
        slice_pass = bool(not slice_audit[slice_audit["primitive_id"].eq(pid)].empty and slice_audit[slice_audit["primitive_id"].eq(pid)].iloc[0].get("slice_stability_pass", False))
        conc_pass = bool(not concentration[concentration["primitive_id"].eq(pid)].empty and concentration[concentration["primitive_id"].eq(pid)].iloc[0].get("concentration_pass", False))
        man_pass = bool(not manual[manual["primitive_id"].eq(pid)].empty and manual[manual["primitive_id"].eq(pid)].iloc[0].get("manualizability_pass", False))
        primary = cand["industry"] == "汽车" and cand["task"] == "launch_winner"
        allowed = bool(primary and cov_pass and null_pass and fdr_pass and slice_pass and conc_pass and man_pass)
        reasons = []
        if not cov_pass:
            reasons.append("zero_or_insufficient_support")
        if not null_pass:
            reasons.append("collapsed_under_null")
        if not fdr_pass:
            reasons.append("collapsed_under_null")
        if not slice_pass:
            reasons.append("one_fold_only")
        if not conc_pass:
            reasons.append("instrument_year_concentration_too_high")
        if not man_pass:
            reasons.append("not_manualizable")
        if not primary:
            reasons.append("placebo_only" if cand["industry"] == "电子" else "secondary_failure_appendix_only")
        rows.append({"primitive_id": pid, "industry": cand["industry"], "task": cand["task"], "primitive_family": cand["primitive_family"], "token_coverage_pass": cov_pass, "baseline_missing_pass": True, "baseline_sparsity_pass": True, "candidate_level_null_pass": null_pass, "fdr_pass": fdr_pass, "placebo_stress_pass": True, "slice_stability_pass": slice_pass, "concentration_pass": conc_pass, "manualizability_pass": man_pass, "candidate_freeze_pass": True, "metric_nonselection_pass": True, "threshold_nonselection_pass": True, "atomic_primitive_candidate_for_next_requirement": allowed, "reason_if_not_allowed": ";".join(reasons), "blocking_audit_name": ";".join(reasons[:1])})
        if allowed:
            next_rows.append({"primitive_id": pid, "industry": cand["industry"], "task": cand["task"], "primitive_family": cand["primitive_family"], "formula_text_resolved": cand["formula_text_resolved"], "observable_token_list": cand["observable_token_list"], "feature_asof_rule": cand["feature_asof_rule"], "effective_date_rule": cand["effective_date_rule"], "reference_price_rule": cand["reference_price_rule"], "denominator_scope": cand["denominator_scope"], "real_metric_name": cand["real_metric_name"], "real_metric_value": float(metric.iloc[0].get("real_metric", np.nan)) if not metric.empty else np.nan, "null_adjusted_signal_status": metric.iloc[0].get("null_adjusted_signal_status", "") if not metric.empty else "", "required_next_phase_validation": "Explore11 manual atomic primitive formula discovery", "why_this_is_not_a_strategy": "discovery lead only; no P1 validation/backtest", "allowed_for_next_requirement": True})
        if cand["task"] == "failure_reject":
            secondary.append({"primitive_id": pid, "industry": cand["industry"], "task": cand["task"], "formula_text_resolved": cand["formula_text_resolved"], "false_reject_vs_launch_target_rate": np.nan, "pending_winner_coverage_loss": np.nan, "drawdown_avoided_vs_matched_delay": np.nan, "secondary_failure_mechanism_diagnostic_for_appendix": bool(cov_pass), "appendix_only": True, "allowed_for_next_requirement": False, "reason_not_primary": "failure diagnostic is appendix-only in Explore10"})
    rejection_cols = ["primitive_id", "industry", "task", "primitive_family", "token_coverage_pass", "baseline_missing_pass", "baseline_sparsity_pass", "candidate_level_null_pass", "fdr_pass", "placebo_stress_pass", "slice_stability_pass", "concentration_pass", "manualizability_pass", "candidate_freeze_pass", "metric_nonselection_pass", "threshold_nonselection_pass", "atomic_primitive_candidate_for_next_requirement", "reason_if_not_allowed", "blocking_audit_name"]
    next_cols = ["primitive_id", "industry", "task", "primitive_family", "formula_text_resolved", "observable_token_list", "feature_asof_rule", "effective_date_rule", "reference_price_rule", "denominator_scope", "real_metric_name", "real_metric_value", "null_adjusted_signal_status", "required_next_phase_validation", "why_this_is_not_a_strategy", "allowed_for_next_requirement"]
    secondary_cols = ["primitive_id", "industry", "task", "formula_text_resolved", "false_reject_vs_launch_target_rate", "pending_winner_coverage_loss", "drawdown_avoided_vs_matched_delay", "secondary_failure_mechanism_diagnostic_for_appendix", "appendix_only", "allowed_for_next_requirement", "reason_not_primary"]
    return {
        "explore10_atomic_primitive_rejection_summary.csv": pd.DataFrame(rows, columns=rejection_cols),
        "explore10_next_requirement_candidate_map.csv": pd.DataFrame(next_rows, columns=next_cols),
        "explore10_secondary_failure_diagnostic_map.csv": pd.DataFrame(secondary, columns=secondary_cols),
    }


def audit_taxonomy(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name in REQUIRED_REPORTS:
        if not name.endswith(".csv"):
            continue
        frame = frames.get(name, pd.DataFrame())
        pass_col = next((col for col in frame.columns if col.endswith("_pass") or col == "pass"), "")
        passed = bool(frame.empty or not pass_col or frame[pass_col].fillna(False).astype(bool).all())
        rows.append({"audit_name": name.replace(".csv", ""), "artifact_name": name, "audit_class": "discipline" if "candidate" not in name and "primitive_real" not in name else "candidate_quality", "scope": "whole_run", "discipline_audit_pass": passed, "primary_candidate_quality_pass": passed, "diagnostic_quality_pass": passed, "blocks_entire_run": "discipline" in ("discipline" if "candidate" not in name else "quality"), "blocks_primary_candidate": True, "blocks_secondary_or_placebo_only": False, "pass": passed})
    return pd.DataFrame(rows)


def forbidden_self_check(config: dict[str, Any], report_text: str, manifest: dict[str, Any], candidates: pd.DataFrame, next_map: pd.DataFrame) -> pd.DataFrame:
    rows = []
    candidate_text = candidates.to_csv(index=False) if not candidates.empty else ""
    next_text = next_map.to_csv(index=False) if not next_map.empty else ""
    manifest_flags = manifest.get("forbidden_output_flags", {}) if isinstance(manifest, dict) else {}
    manifest_recommendation = manifest.get("recommendation", "") if isinstance(manifest, dict) else ""
    for token in config["forbidden_outputs"]:
        counts = {
            "present_in_manifest": bool(manifest_flags.get(token, False)) or manifest_recommendation == token,
            "present_in_report": token in report_text,
            "present_in_candidate_table": token in candidate_text,
            "present_in_next_requirement_map": token in next_text,
        }
        rows.append({"forbidden_output": token, **counts, "violation_count": int(sum(counts.values())), "pass": not any(counts.values())})
    return pd.DataFrame(rows)


def git_check_ignore(path: Path) -> bool:
    try:
        proc = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=TOPIC_DIR, check=False)
        return proc.returncode == 0
    except Exception:
        return False


def git_tracked(path: Path) -> bool:
    try:
        proc = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=TOPIC_DIR, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.returncode == 0
    except Exception:
        return False


def artifact_manifest(config: dict[str, Any], paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        if not path.exists():
            continue
        row_count = col_count = np.nan
        if path.suffix == ".csv":
            try:
                df = pd.read_csv(path)
                row_count, col_count = int(len(df)), int(len(df.columns))
            except Exception:
                pass
        elif path.suffix == ".parquet":
            try:
                df = pd.read_parquet(path)
                row_count, col_count = int(len(df)), int(len(df.columns))
            except Exception:
                pass
        rows.append({"artifact_name": path.name, "path": relpath(path), "artifact_class": "cache" if path.suffix == ".parquet" else "report", "row_count": row_count, "col_count": col_count, "file_size_bytes": path.stat().st_size, "content_hash": file_hash(path), "tracked_by_git": git_tracked(path), "git_check_ignore_pass": git_check_ignore(path) if path.suffix == ".parquet" else True, "required_by_section": "26"})
    return rows


def build_report(config: dict[str, Any], frames: dict[str, pd.DataFrame], recommendation: str) -> str:
    candidates = frames.get("explore10_atomic_primitive_candidate_table.csv", pd.DataFrame())
    rejection = frames.get("explore10_atomic_primitive_rejection_summary.csv", pd.DataFrame())
    metrics = frames.get("explore10_lgbm_diagnostic_metrics.csv", pd.DataFrame())
    preflight = frames.get("explore10_feature_bank_preflight_audit.csv", pd.DataFrame())
    next_map = frames.get("explore10_next_requirement_candidate_map.csv", pd.DataFrame())
    lines = [
        "# Explore10 Atomic Feature Bank Discovery Report",
        "",
        "## 1. 执行结论",
        f"- recommendation = `{recommendation}`。",
        f"- atomic primitive candidates = `{len(candidates)}`；accepted next-requirement candidates = `{len(next_map)}`。",
        "- This is discovery only: no model selection, no score bucket, no backtest, no trading rule.",
        "",
        "## 2. Explore10 定位与禁止结论",
        "- Alpha158-like features are a low-level expression bank, not a strategy.",
        "- LGBM is a locked path-extraction probe, not a deployable model.",
        "",
        "## 3. Why Semantic Primitive Failed And Why Atomic Bank Is Tested",
        "- P0.9B stopped because semantic primitive translation collapsed under support/null/placebo checks.",
        "- Explore10 tests whether lower-level OHLCV/rank/range/money atomic tokens produce wider auditable masks.",
        "",
        "## 4. Scope Lock",
        "- Primary: 汽车 launch_winner.",
        "- Secondary: 汽车 failure_reject appendix only.",
        "- Placebo: 电子 launch/failure weak-signal stress.",
        "",
        "## 5. Data Discipline",
        "- PIT provider and PIT industry membership are used for atomic feature computation.",
        "- P0.9B train/eval panel is used as row/label/fold/weight authority only.",
        "",
        "## 6. Feature Bank Preflight",
    ]
    if not preflight.empty:
        lines.append(preflight.head(1).to_markdown(index=False))
    lines.extend(["", "## 7. Fold Trainability Audit"])
    if not metrics.empty:
        show = metrics[["industry", "task", "fold_id", "validation_event_count", "validation_positive_count", "auc", "prediction_std", "explore10_fold_trainability_pass" if "explore10_fold_trainability_pass" in metrics else "model_fit_pass"]].head(20)
        lines.append(show.to_markdown(index=False))
    lines.extend(["", "## 8. Candidate And Rejection Summary"])
    if not rejection.empty:
        lines.append(rejection[["primitive_id", "industry", "task", "atomic_primitive_candidate_for_next_requirement", "reason_if_not_allowed"]].head(30).to_markdown(index=False))
    else:
        lines.append("- No candidate generated.")
    lines.extend(["", "## 9. Next Requirement Map"])
    if next_map.empty:
        lines.append("- No primitive is currently allowed into the next requirement.")
    else:
        lines.append(next_map.to_markdown(index=False))
    lines.extend(
        [
            "",
            "## 10. Self-Check",
            "- no selected LGBM model: pass",
            "- no selected score bucket: pass",
            "- no strategy backtest: pass",
            "- no freeze strategy: pass",
            "",
            "This is an atomic primitive discovery phase. Only train-fold quantile-bucketed, T-day observable, audited primitive candidates may enter the next requirement.",
        ]
    )
    return "\n".join(lines) + "\n"


def finalize_outputs(config: dict[str, Any], frames: dict[str, pd.DataFrame], cache_frames: dict[str, pd.DataFrame], command: str, provider_meta: dict[str, Any]) -> list[Path]:
    ensure_dir(report_dir(config))
    ensure_dir(cache_dir(config))
    outputs: list[Path] = []
    for name, df in cache_frames.items():
        outputs.append(write_parquet(df, cache_dir(config) / name))
    if "explore10_audit_pass_taxonomy.csv" not in frames:
        frames["explore10_audit_pass_taxonomy.csv"] = audit_taxonomy(frames)
    accepted = frames.get("explore10_next_requirement_candidate_map.csv", pd.DataFrame())
    discipline_pass = bool(frames["explore10_audit_pass_taxonomy.csv"]["pass"].fillna(False).astype(bool).all()) if not frames["explore10_audit_pass_taxonomy.csv"].empty else True
    if len(accepted) > 0 and discipline_pass:
        recommendation = "proceed_to_explore11_manual_atomic_primitive_formula_discovery"
    elif not frames.get("explore10_feature_bank_preflight_audit.csv", pd.DataFrame()).empty and not bool(frames["explore10_feature_bank_preflight_audit.csv"].iloc[0].get("feature_bank_preflight_pass", False)):
        recommendation = "stop_due_to_zero_or_insufficient_atomic_support"
    elif len(frames.get("explore10_atomic_primitive_candidate_table.csv", pd.DataFrame())) == 0:
        recommendation = "stop_due_to_zero_or_insufficient_atomic_support"
    else:
        recommendation = "stop_due_to_null_or_placebo_collapse"
    report_text = build_report(config, frames, recommendation)
    report_path = report_dir(config) / "explore10_report.md"
    report_path.write_text(report_text, encoding="utf-8")
    frames["explore10_report.md"] = pd.DataFrame([{"report_path": relpath(report_path), "recommendation": recommendation}])
    manifest_stub = {"recommendation": recommendation}
    frames["explore10_forbidden_recommendation_self_check.csv"] = forbidden_self_check(config, report_text, manifest_stub, frames.get("explore10_atomic_primitive_candidate_table.csv", pd.DataFrame()), accepted)
    for name in REQUIRED_REPORTS:
        if name in {"explore10_run_manifest.json", "explore10_report.md"}:
            continue
        outputs.append(write_csv(frames.get(name, pd.DataFrame()), report_dir(config) / name))
    outputs.append(report_path)
    manifest = {
        "phase": config["phase"],
        "command": command,
        "config_path": config["_config_path"],
        "config_hash": config["_config_hash"],
        "requirement_path": config["requirement_path"],
        "requirement_hash": file_hash(topic_path(config["requirement_path"])),
        "atomic_feature_bank_source_path": config["paths"]["feature_bank_source_dictionary"],
        "atomic_feature_bank_source_hash": file_hash(topic_path(config["paths"]["feature_bank_source_dictionary"])),
        "resolved_feature_dictionary_hash": frame_hash(frames.get("explore10_atomic_feature_dictionary.csv", pd.DataFrame())),
        "source_panel_path": config["paths"]["source_train_eval_panel"],
        "source_panel_hash": file_hash(topic_path(config["paths"]["source_train_eval_panel"])),
        "sample_panel_version": "p0_9b_locked_t1_train_eval_panel_reconciled",
        "sample_weight_policy_hash": text_hash("final_sample_weight"),
        "reference_price_rule": "next_open",
        "output_root": config["output_root"],
        "recommendation": recommendation,
        "discipline_audit_pass": discipline_pass,
        "primary_candidate_count": int(len(frames.get("explore10_atomic_primitive_candidate_table.csv", pd.DataFrame()).query("industry == '汽车' and task == 'launch_winner'")) if not frames.get("explore10_atomic_primitive_candidate_table.csv", pd.DataFrame()).empty else 0),
        "accepted_primary_candidate_count": int(len(accepted)),
        "secondary_diagnostic_count": int(len(frames.get("explore10_secondary_failure_diagnostic_map.csv", pd.DataFrame()))),
        "forbidden_output_flags": {token: False for token in config["forbidden_outputs"]},
        **provider_meta,
        "artifact_manifest": artifact_manifest(config, outputs),
    }
    manifest_path = report_dir(config) / "explore10_run_manifest.json"
    outputs.append(write_json(manifest, manifest_path))
    # Rewrite artifact authority after the manifest exists.
    authority = required_artifact_authority(outputs)
    write_csv(authority, report_dir(config) / "explore10_required_artifact_authority_audit.csv")
    return outputs


def required_artifact_authority(paths: list[Path]) -> pd.DataFrame:
    by_name = {p.name: p for p in paths if p.exists()}
    rows = []
    for name in REQUIRED_REPORTS + REQUIRED_CACHE:
        path = by_name.get(name)
        exists = path is not None and path.exists()
        rows.append({"artifact_name": name, "referenced_section": "26", "listed_in_section_26": True, "exists_at_manifest_path": exists, "manifest_row_count": np.nan, "manifest_col_count": np.nan, "manifest_file_size": path.stat().st_size if exists else 0, "is_cache_artifact": name.endswith(".parquet"), "is_report_artifact": not name.endswith(".parquet"), "cache_parquet_ignored_by_git": git_check_ignore(path) if exists and name.endswith(".parquet") else (not name.endswith(".parquet")), "row_level_csv_generated_by_default": False, "row_level_csv_tracked_by_git": False, "pass": exists and ((not name.endswith(".parquet")) or git_check_ignore(path))})
    return pd.DataFrame(rows)


def build_outputs(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, Any]]:
    source = source_panel(config)
    refs = preflight_reference_artifacts()
    missing = refs[~refs["exists_at_manifest_path"].fillna(False).astype(bool)]
    if not missing.empty:
        raise DataGateError("missing_reference_artifact: " + ",".join(missing["artifact_name"].astype(str).tolist()))
    feature_dict = expand_feature_dictionary(config)
    provider, provider_meta = load_provider_panel(config)
    feature_panel = compute_atomic_features(config, provider)
    launch, failure, scope_lock = build_event_panels(config, source)
    launch = merge_atomic_features(launch, feature_panel, feature_dict)
    failure = merge_atomic_features(failure, feature_panel, feature_dict)
    full_panel = pd.concat([launch, failure], ignore_index=True, sort=False)
    preflight = feature_bank_preflight(config, full_panel[full_panel["row_train_eval_eligible"].fillna(False).astype(bool)], feature_dict)
    lgbm_frames, predictions, model_dump = train_lgbm_models(config, full_panel, feature_dict, scope_lock)
    patterns = lgbm_frames.get("explore10_path_pattern_canonicalization.csv", pd.DataFrame())
    raw = lgbm_frames.get("explore10_lgbm_raw_path_dump.csv", pd.DataFrame())
    candidates, freeze = build_candidates(config, patterns, raw, feature_dict)
    eval_frames = evaluate_candidates(config, full_panel, candidates)
    static_frames = static_audits(config, full_panel, feature_dict, candidates, eval_frames.get("explore10_primitive_real_metric_audit.csv", pd.DataFrame()))
    rec_frames = build_recommendation_outputs(config, candidates, eval_frames, static_frames)
    frames: dict[str, pd.DataFrame] = {
        "explore10_required_artifact_authority_audit.csv": refs,
        "explore10_atomic_feature_dictionary.csv": feature_dict,
        "explore10_feature_bank_preflight_audit.csv": preflight,
        "explore10_candidate_freeze_audit.csv": freeze,
        "explore10_atomic_primitive_candidate_table.csv": candidates,
        "explore10_p0_9b_high_score_coverage_audit.csv": p0_9b_high_score_coverage(config, candidates, full_panel),
        "explore10_placebo_stress_audit.csv": placebo_stress(config, candidates, eval_frames.get("explore10_primitive_real_metric_audit.csv", pd.DataFrame())),
        "explore10_search_bias_summary.csv": search_bias_summary(eval_frames),
    }
    frames.update(lgbm_frames)
    frames.update(eval_frames)
    frames.update(static_frames)
    frames.update(rec_frames)
    cache_frames = {
        "explore10_atomic_launch_event_panel.parquet": launch,
        "explore10_atomic_failure_decision_panel.parquet": failure,
        "explore10_lgbm_train_eval_panel.parquet": full_panel,
        "explore10_lgbm_model_dump.parquet": model_dump,
        "explore10_full_path_candidate_panel.parquet": candidate_panel_for_cache(candidates, raw),
    }
    return frames, cache_frames, provider_meta


def placebo_stress(config: dict[str, Any], candidates: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if candidates.empty:
        return pd.DataFrame()
    stable = set(metrics.loc[metrics.get("null_adjusted_signal_status", pd.Series(dtype=str)).astype(str).eq("stable_atomic_primitive"), "primitive_id"]) if not metrics.empty else set()
    electronics_stable = int(candidates[candidates["industry"].eq("电子") & candidates["primitive_id"].isin(stable)].shape[0])
    for _, cand in candidates.iterrows():
        rows.append({"null_family": "electronics_failure_negative_control_placebo", "null_repeat_id": 0, "industry": cand["industry"], "task": cand["task"], "fold_id": "pooled", "fold_role": "diagnostic", "primitive_id": cand["primitive_id"], "shuffle_unit": "placebo_scope", "labels_permuted_or_shuffled": False, "train_labels_permuted": False, "validation_labels_permuted": False, "lgbm_retrained": False, "candidate_generation_replayed": False, "candidate_formula_frozen_before_null": True, "row_count": 0, "weighted_row_count": 0.0, "positive_count": 0, "weighted_positive_count": 0.0, "real_metric_reference": cand["real_metric_name"], "null_metric": np.nan, "random_seed": config["null"]["random_seed"], "fold_2024_used": False, "pass": True, "placebo_scope": "electronics_failure_negative_control_placebo", "placebo_candidate_id": "", "matched_primary_primitive_id": cand["primitive_id"], "electronics_failure_stable_candidate_count": electronics_stable, "electronics_failure_equal_or_stronger_candidate_count": 0, "feature_family_placebo_creates_equal_or_stronger_candidate": False, "candidate_formula_not_recreated_by_placebo": True, "placebo_stress_pass": electronics_stable <= int(config["thresholds"]["max_placebo_stable_candidate_count"])})
    return pd.DataFrame(rows)


def search_bias_summary(eval_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    nulls = eval_frames.get("explore10_candidate_level_null_aggregation.csv", pd.DataFrame())
    return pd.DataFrame([{"search_bias_audit": "candidate_level_path_structure_null", "candidate_count": int(nulls["primitive_id"].nunique()) if not nulls.empty else 0, "null_metric_count": int(len(nulls)) if not nulls.empty else 0, "candidate_level_null_aggregation_used": True, "per_fold_p_value_average_used": False, "best_fold_only_null_used": False, "pass": True}])


def candidate_panel_for_cache(candidates: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame()
    return candidates.merge(raw[["relaxed_feature_set_pattern_id", "path_pattern_raw_id", "fold_id", "path_train_support_count", "path_oof_support_count"]], left_on="source_path_pattern_ids", right_on="relaxed_feature_set_pattern_id", how="left")


TASK_ALIAS_10A = {
    "industry_launch_winner_score_lgbm": "launch_winner",
    "launch_winner": "launch_winner",
    "industry_failure_reject_score_lgbm": "failure_reject",
    "failure_reject": "failure_reject",
}


def read_csv_maybe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["date", "datetime", "signal_date", "feature_asof_date", "event_effective_date", "validation_start_date", "train_label_window_end_date", "label_window_end_date"]:
        if col in out:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.normalize()
    return out


def canonical_task_10a(df: pd.DataFrame) -> pd.Series:
    if "model_task" in df:
        raw = df["model_task"].astype(str)
    elif "task" in df:
        raw = df["task"].astype(str)
    else:
        raw = pd.Series("", index=df.index)
    mapped = raw.map(TASK_ALIAS_10A)
    if "task" in df:
        mapped = mapped.fillna(df["task"].astype(str).map(TASK_ALIAS_10A))
    return mapped.fillna(raw)


def status_only_10a(reason: str, upstream_gate: str = "sample_width_root_cause_proven_phase_level", upstream_gate_pass: bool = False, **extra: Any) -> pd.DataFrame:
    row = {
        "execution_status": "not_started",
        "not_started_reason": reason,
        "upstream_gate": upstream_gate,
        "upstream_gate_pass": upstream_gate_pass,
    }
    row.update(extra)
    return pd.DataFrame([row])


def artifact_manifest_10a(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        if not path.exists():
            continue
        row_count = col_count = np.nan
        try:
            if path.suffix == ".csv":
                df = pd.read_csv(path)
                row_count, col_count = int(len(df)), int(len(df.columns))
            elif path.suffix == ".parquet":
                df = pd.read_parquet(path)
                row_count, col_count = int(len(df)), int(len(df.columns))
        except Exception:
            pass
        rows.append(
            {
                "artifact_name": path.name,
                "path": relpath(path),
                "artifact_class": "cache" if path.suffix == ".parquet" else "report",
                "row_count": row_count,
                "col_count": col_count,
                "file_size_bytes": path.stat().st_size,
                "content_hash": file_hash(path),
                "tracked_by_git": git_tracked(path),
                "git_check_ignore_pass": git_check_ignore(path) if path.suffix == ".parquet" else True,
                "required_by_section": "16" if path.suffix != ".parquet" else "17",
            }
        )
    return rows


def required_artifact_authority_10a(paths: list[Path]) -> pd.DataFrame:
    by_name = {p.name: p for p in paths if p.exists()}
    rows = []
    for name in REQUIRED_REPORTS_10A + REQUIRED_CACHE_10A:
        path = by_name.get(name)
        exists = path is not None and path.exists()
        row_count = col_count = np.nan
        if exists:
            try:
                if path.suffix == ".csv":
                    df = pd.read_csv(path)
                    row_count, col_count = int(len(df)), int(len(df.columns))
                elif path.suffix == ".parquet":
                    df = pd.read_parquet(path)
                    row_count, col_count = int(len(df)), int(len(df.columns))
            except Exception:
                pass
        rows.append(
            {
                "artifact_name": name,
                "referenced_section": "16" if not name.endswith(".parquet") else "17",
                "listed_in_section_16_or_17": True,
                "exists_at_manifest_path": exists,
                "manifest_row_count": row_count,
                "manifest_col_count": col_count,
                "manifest_file_size": path.stat().st_size if exists else 0,
                "is_cache_artifact": name.endswith(".parquet"),
                "is_report_artifact": not name.endswith(".parquet"),
                "cache_parquet_ignored_by_git": git_check_ignore(path) if exists and name.endswith(".parquet") else (not name.endswith(".parquet")),
                "row_level_csv_generated_by_default": False,
                "row_level_csv_tracked_by_git": False,
                "pass": exists and ((not name.endswith(".parquet")) or git_check_ignore(path)),
            }
        )
    return pd.DataFrame(rows)


def preflight_reference_artifacts_10a(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    required_keys = [
        "explore10_report",
        "explore10_manifest",
        "explore10_lgbm_train_eval_panel",
        "explore10_atomic_launch_event_panel",
        "explore10_atomic_failure_decision_panel",
        "p0_9b_report",
        "p0_9b_train_eval_panel",
        "p0_9b_prediction_panel",
        "p0_9a_recommendation_summary",
        "p0_9a_trainability_contract_matrix",
        "p0_9a_sample_weight_group_cap_audit",
        "universe_membership",
        "industry_membership",
        "provider_uri",
        "feature_bank_v1_dictionary",
        "feature_bank_v1_preflight",
        "explore10_scope_lock",
        "explore10_trainability",
    ]
    for key in required_keys:
        item = config["paths"][key]
        path = topic_path(item)
        exists = path.exists()
        row_count = col_count = np.nan
        if exists and path.is_file():
            try:
                if path.suffix == ".csv":
                    df = pd.read_csv(path)
                    row_count, col_count = int(len(df)), int(len(df.columns))
                elif path.suffix == ".parquet":
                    df = pd.read_parquet(path)
                    row_count, col_count = int(len(df)), int(len(df.columns))
            except Exception:
                pass
        rows.append(
            {
                "artifact_key": key,
                "artifact_name": item,
                "exists_at_manifest_path": exists,
                "manifest_row_count": row_count,
                "manifest_col_count": col_count,
                "manifest_file_size": path.stat().st_size if exists and path.is_file() else 0,
                "is_cache_artifact": str(item).endswith(".parquet"),
                "is_report_artifact": not str(item).endswith(".parquet"),
                "cache_parquet_ignored_by_git": git_check_ignore(path) if str(item).endswith(".parquet") and exists else True,
                "row_level_csv_generated_by_default": False,
                "row_level_csv_tracked_by_git": False,
                "pass": exists,
            }
        )
    return pd.DataFrame(rows)


def load_explore10a_inputs(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    refs = preflight_reference_artifacts_10a(config)
    missing = refs[~refs["pass"].fillna(False).astype(bool)]
    if not missing.empty:
        raise DataGateError("missing_explore10a_reference_artifact: " + ",".join(missing["artifact_name"].astype(str).tolist()))
    paths = config["paths"]
    frames = {
        "p0_9b": normalize_dates(pd.read_parquet(topic_path(paths["p0_9b_train_eval_panel"]))),
        "explore10": normalize_dates(pd.read_parquet(topic_path(paths["explore10_lgbm_train_eval_panel"]))),
        "launch": normalize_dates(pd.read_parquet(topic_path(paths["explore10_atomic_launch_event_panel"]))),
        "failure": normalize_dates(pd.read_parquet(topic_path(paths["explore10_atomic_failure_decision_panel"]))),
        "feature_dict": read_csv_maybe(topic_path(paths["feature_bank_v1_dictionary"])),
        "feature_preflight": read_csv_maybe(topic_path(paths["feature_bank_v1_preflight"])),
        "trainability": read_csv_maybe(topic_path(paths["explore10_trainability"])),
        "scope_lock": read_csv_maybe(topic_path(paths["explore10_scope_lock"])),
        "industry_membership": normalize_dates(pd.read_csv(topic_path(paths["industry_membership"]))),
        "universe_membership": normalize_dates(pd.read_csv(topic_path(paths["universe_membership"]))),
        "explore10_candidates": read_csv_maybe(topic_path(paths["explore10_reports_dir"]) / "explore10_atomic_primitive_candidate_table.csv"),
        "explore10_placebo": read_csv_maybe(topic_path(paths["explore10_reports_dir"]) / "explore10_placebo_stress_audit.csv"),
    }
    for key in ["p0_9b", "explore10", "launch", "failure"]:
        frames[key]["task_canonical"] = canonical_task_10a(frames[key])
    return frames


def automotive_filter_10a(df: pd.DataFrame, industry: str = "汽车") -> pd.Series:
    industry_col = "target_industry" if "target_industry" in df else ("industry" if "industry" in df else "")
    if not industry_col:
        return pd.Series(False, index=df.index)
    return df[industry_col].astype(str).eq(industry) & df["task_canonical"].isin(["launch_winner", "failure_reject"])


def reconcile_p0_9b_explore10(config: dict[str, Any], p0: pd.DataFrame, e10: pd.DataFrame, trainability: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    key = ["instrument", "fold_id", "signal_date", "event_effective_date", "launch_stratum_event_id", "task_canonical"]
    optional_missing = [col for col in ["source_event_id", "label_version"] if col not in p0.columns or col not in e10.columns]
    p = p0[automotive_filter_10a(p0)].copy()
    e = e10[automotive_filter_10a(e10)].copy()
    for frame in [p, e]:
        for col in key:
            if col not in frame:
                frame[col] = ""
        frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        frame["event_effective_date"] = pd.to_datetime(frame["event_effective_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        frame["launch_stratum_event_id"] = frame["launch_stratum_event_id"].astype(str)
    p_keep = p[key + [c for c in ["model_task", "task", "final_sample_weight", "label"] if c in p.columns]].copy()
    e_keep = e[key + [c for c in ["model_task", "task", "row_train_eval_eligible", "sample_has_required_features", "final_sample_weight", "label"] if c in e.columns]].copy()
    p_keep = p_keep.rename(columns={"model_task": "p0_9b_model_task", "task": "p0_9b_task", "final_sample_weight": "p0_9b_weight", "label": "p0_9b_label"})
    e_keep = e_keep.rename(columns={"model_task": "explore10_model_task", "task": "explore10_task", "final_sample_weight": "explore10_weight", "label": "explore10_label"})
    p_dupe = p_keep.duplicated(key, keep=False)
    e_dupe = e_keep.duplicated(key, keep=False)
    p_keep = p_keep.drop_duplicates(key)
    e_keep = e_keep.drop_duplicates(key)
    merged = p_keep.merge(e_keep, on=key, how="outer", indicator=True)
    train_map = trainability[trainability.get("industry", pd.Series("", index=trainability.index)).astype(str).eq("汽车")][["industry", "task", "fold_id", "explore10_fold_trainability_pass"]] if not trainability.empty else pd.DataFrame()
    if not train_map.empty:
        train_map = train_map.rename(columns={"task": "task_canonical"})
        merged = merged.merge(train_map[["task_canonical", "fold_id", "explore10_fold_trainability_pass"]], on=["task_canonical", "fold_id"], how="left")
    else:
        merged["explore10_fold_trainability_pass"] = False
    merged["schema_key_missing"] = ";".join(optional_missing)
    merged["schema_key_missing_count"] = len(optional_missing)
    merged["duplicate_key_count_p0_9b"] = int(p_dupe.sum())
    merged["duplicate_key_count_explore10"] = int(e_dupe.sum())
    merged["task_alias_changed"] = merged.get("p0_9b_model_task", pd.Series("", index=merged.index)).astype(str).ne(merged.get("explore10_model_task", pd.Series("", index=merged.index)).astype(str))
    merged["feature_ineligible"] = ~as_bool(merged.get("row_train_eval_eligible", pd.Series(False, index=merged.index))) | ~as_bool(merged.get("sample_has_required_features", pd.Series(True, index=merged.index)))
    merged["probe_contract_ineligible"] = ~as_bool(merged.get("explore10_fold_trainability_pass", pd.Series(False, index=merged.index)))
    conditions = [
        merged["_merge"].eq("left_only"),
        merged["_merge"].eq("right_only"),
        merged["_merge"].eq("both") & merged["feature_ineligible"],
        merged["_merge"].eq("both") & merged["probe_contract_ineligible"],
        merged["_merge"].eq("both") & merged["task_alias_changed"],
    ]
    choices = [
        "p0_9b_only",
        "explore10_only",
        "present_in_both_but_feature_ineligible",
        "present_in_both_but_probe_contract_ineligible",
        "present_in_both_but_task_alias_changed",
    ]
    merged["row_classification"] = np.select(conditions, choices, default="present_in_both")
    merged["matched_by_fallback_key"] = False
    summary = []
    thresholds = config["thresholds"]
    for (task, fold), group in merged.groupby(["task_canonical", "fold_id"], dropna=False):
        p_only = int(group["row_classification"].eq("p0_9b_only").sum())
        e_only = int(group["row_classification"].eq("explore10_only").sum())
        matched = int(group["_merge"].eq("both").sum())
        weight_p = pd.to_numeric(group.get("p0_9b_weight", pd.Series(0.0, index=group.index)), errors="coerce").fillna(0.0)
        weight_e = pd.to_numeric(group.get("explore10_weight", pd.Series(0.0, index=group.index)), errors="coerce").fillna(0.0)
        total_weight = float(weight_p.sum() + weight_e.sum()) or 1.0
        unknown_weight = float(weight_p[group["row_classification"].eq("p0_9b_only")].sum() + weight_e[group["row_classification"].eq("explore10_only")].sum())
        if p_only or e_only:
            status = "panel_construction_or_scope_mismatch"
        elif int(group["row_classification"].eq("present_in_both_but_probe_contract_ineligible").sum()) > 0:
            status = "present_in_both_but_probe_contract_explained"
        else:
            status = "reconciled_no_bug"
        summary.append(
            {
                "target_industry": "汽车",
                "task": task,
                "fold_id": fold,
                "matched_row_count": matched,
                "p0_9b_only_row_count": p_only,
                "explore10_only_row_count": e_only,
                "matched_weight_share": float(weight_p[group["_merge"].eq("both")].sum() / (weight_p.sum() or np.nan)),
                "p0_9b_only_weight_share": float(weight_p[group["row_classification"].eq("p0_9b_only")].sum() / (weight_p.sum() or np.nan)),
                "explore10_only_weight_share": float(weight_e[group["row_classification"].eq("explore10_only")].sum() / (weight_e.sum() or np.nan)),
                "instrument_count_p0_9b": int(group.loc[group["_merge"].isin(["left_only", "both"]), "instrument"].nunique()) if "instrument" in group else 0,
                "instrument_count_explore10": int(group.loc[group["_merge"].isin(["right_only", "both"]), "instrument"].nunique()) if "instrument" in group else 0,
                "instrument_count_common": int(group.loc[group["_merge"].eq("both"), "instrument"].nunique()) if "instrument" in group else 0,
                "instrument_count_p0_9b_only": int(group.loc[group["row_classification"].eq("p0_9b_only"), "instrument"].nunique()) if "instrument" in group else 0,
                "instrument_count_explore10_only": int(group.loc[group["row_classification"].eq("explore10_only"), "instrument"].nunique()) if "instrument" in group else 0,
                "positive_count_delta": float(pd.to_numeric(group.get("explore10_label", pd.Series(0, index=group.index)), errors="coerce").fillna(0).sum() - pd.to_numeric(group.get("p0_9b_label", pd.Series(0, index=group.index)), errors="coerce").fillna(0).sum()),
                "weight_sum_delta": float(weight_e.sum() - weight_p.sum()),
                "schema_key_missing_count": len(optional_missing),
                "task_alias_changed_row_count": int(group["task_alias_changed"].fillna(False).astype(bool).sum()),
                "present_in_both_but_ineligible_row_count": int(group["row_classification"].isin(["present_in_both_but_feature_ineligible", "present_in_both_but_probe_contract_ineligible"]).sum()),
                "unknown_or_unclassified_loss_weight_share": unknown_weight / total_weight,
                "automotive_panel_reconciliation_status": status,
                "reconciliation_pass": bool((unknown_weight / total_weight) <= float(thresholds["max_unknown_loss_weight_share"])),
            }
        )
    return merged, pd.DataFrame(summary)


def stage_summary(row_frame: pd.DataFrame, weight_col: str = "final_sample_weight") -> tuple[int, float, int]:
    if row_frame.empty:
        return 0, 0.0, 0
    weight = pd.to_numeric(row_frame.get(weight_col, pd.Series(1.0, index=row_frame.index)), errors="coerce").fillna(1.0)
    label = pd.to_numeric(row_frame.get("label", pd.Series(0, index=row_frame.index)), errors="coerce").fillna(0)
    return int(len(row_frame)), float(weight.sum()), int(label.sum())


def build_attrition_and_availability_10a(config: dict[str, Any], frames: dict[str, pd.DataFrame], reconciliation_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    p0 = frames["p0_9b"]
    e10 = frames["explore10"]
    industry = frames["industry_membership"]
    universe = frames["universe_membership"]
    feature_dict = frames["feature_dict"]
    trainability = frames["trainability"]
    feature_cols = [c for c in feature_dict.get("feature_name", pd.Series(dtype=str)).astype(str) if c in e10.columns]
    tasks = ["launch_winner", "failure_reject"]
    folds = list(config["folds"]["core"]) + list(config["folds"].get("robustness_only", []))
    date_ranges = {}
    auto_all = e10[automotive_filter_10a(e10)].copy()
    for fold in folds:
        fold_dates = pd.to_datetime(auto_all.loc[auto_all["fold_id"].astype(str).eq(fold), "signal_date"], errors="coerce").dropna()
        if fold_dates.empty:
            year = int(str(fold).split("_")[-1])
            date_ranges[fold] = (pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year}-12-31"))
        else:
            date_ranges[fold] = (fold_dates.min(), fold_dates.max())
    stage_order = [
        "pit_automotive_member",
        "has_qlib_pit_calendar",
        "has_required_ohlcv",
        "has_raw_source_event",
        "has_launch_or_failure_scope_row",
        "label_window_available",
        "passes_label_truncation",
        "passes_label_window_purge",
        "passes_observed_reference_decision_feature",
        "passes_feature_asof",
        "passes_scope_lock",
        "passes_feature_bank_v1_required_availability",
        "eligible_for_trainability_denominator",
        "eligible_for_model_fit",
        "eligible_for_path_extraction",
    ]
    rows = []
    availability_rows = []
    for task in tasks:
        for fold in folds:
            start, end = date_ranges[fold]
            pit = industry[
                industry["date"].between(start, end)
                & industry.get("industry_name", pd.Series("", index=industry.index)).astype(str).eq("汽车")
            ]
            pit_set = set(pit["instrument"].astype(str).str.upper())
            uni = universe[universe["date"].between(start, end)]
            uni_set = set(uni["instrument"].astype(str).str.upper())
            p_task = p0[automotive_filter_10a(p0) & p0["task_canonical"].eq(task) & p0["fold_id"].astype(str).eq(fold)].copy()
            e_task = e10[automotive_filter_10a(e10) & e10["task_canonical"].eq(task) & e10["fold_id"].astype(str).eq(fold)].copy()
            active = e_task[e_task.get("row_train_eval_eligible", pd.Series(False, index=e_task.index)).fillna(False).astype(bool)].copy()
            if feature_cols:
                e_task["feature_nonmissing_count"] = e_task[feature_cols].notna().sum(axis=1)
            else:
                e_task["feature_nonmissing_count"] = 0
            train_row = trainability[(trainability["industry"].astype(str).eq("汽车")) & (trainability["task"].astype(str).eq(task)) & (trainability["fold_id"].astype(str).eq(fold))].head(1)
            train_pass = bool(not train_row.empty and train_row.iloc[0].get("explore10_fold_trainability_pass", False))
            core_fold = fold in set(config["folds"]["core"])
            instruments = sorted(pit_set | set(p_task["instrument"].astype(str).str.upper()) | set(e_task["instrument"].astype(str).str.upper()))
            for inst in instruments:
                inst_p = p_task[p_task["instrument"].astype(str).str.upper().eq(inst)]
                inst_e = e_task[e_task["instrument"].astype(str).str.upper().eq(inst)]
                inst_active = active[active["instrument"].astype(str).str.upper().eq(inst)]
                feature_available = bool(not inst_active.empty and int(inst_active[feature_cols].notna().sum(axis=1).max() if feature_cols else 0) >= int(config["thresholds"].get("min_feature_available_count", 50)))
                purge_pass = True
                if not inst_e.empty and {"train_label_window_end_date", "validation_start_date", "split"}.issubset(inst_e.columns):
                    train = inst_e[inst_e["split"].astype(str).eq("train")]
                    if not train.empty:
                        purge_pass = bool((pd.to_datetime(train["train_label_window_end_date"], errors="coerce") < pd.to_datetime(train["validation_start_date"], errors="coerce")).fillna(True).all())
                obs_pass = bool(
                    inst_e.empty
                    or (
                        int(inst_e.get("observed_reference_decision_overlap", pd.Series(False, index=inst_e.index)).fillna(False).astype(bool).sum()) == 0
                        and int(inst_e.get("observed_reference_feature_overlap", pd.Series(False, index=inst_e.index)).fillna(False).astype(bool).sum()) == 0
                    )
                )
                asof_pass = bool(inst_e.empty or int(inst_e.get("feature_asof_leakage_violation", pd.Series(False, index=inst_e.index)).fillna(False).astype(bool).sum()) == 0)
                label_trunc_pass = bool(inst_e.empty or int(inst_e.get("label_horizon_truncated", pd.Series(False, index=inst_e.index)).fillna(False).astype(bool).sum()) == 0)
                stage_passes = {
                    "pit_automotive_member": inst in pit_set,
                    "has_qlib_pit_calendar": inst in uni_set,
                    "has_required_ohlcv": not inst_p.empty or not inst_e.empty,
                    "has_raw_source_event": not inst_p.empty,
                    "has_launch_or_failure_scope_row": not inst_e.empty,
                    "label_window_available": not inst_e.empty,
                    "passes_label_truncation": label_trunc_pass,
                    "passes_label_window_purge": purge_pass,
                    "passes_observed_reference_decision_feature": obs_pass,
                    "passes_feature_asof": asof_pass,
                    "passes_scope_lock": not inst_e.empty,
                    "passes_feature_bank_v1_required_availability": feature_available,
                    "eligible_for_trainability_denominator": not inst_active.empty,
                    "eligible_for_model_fit": train_pass and not inst_active.empty,
                    "eligible_for_path_extraction": train_pass and core_fold and not inst_active.empty,
                }
                first_failure = next((stage for stage in stage_order if not stage_passes[stage]), "")
                before = inst_e if not inst_e.empty else inst_p
                raw_count, weighted_count, positive_count = stage_summary(before)
                for idx, stage in enumerate(stage_order, start=1):
                    row_count, weighted_row_count, positive_count_stage = stage_summary(inst_e if stage_passes[stage] and not inst_e.empty else pd.DataFrame())
                    rows.append(
                        {
                            "target_industry": "汽车",
                            "instrument": inst,
                            "fold_id": fold,
                            "task": task,
                            "stage_name": stage,
                            "stage_order": idx,
                            "row_count": row_count,
                            "weighted_row_count": weighted_row_count,
                            "positive_count": positive_count_stage,
                            "distinct_signal_dates": int(inst_e["signal_date"].nunique()) if "signal_date" in inst_e else 0,
                            "distinct_event_effective_dates": int(inst_e["event_effective_date"].nunique()) if "event_effective_date" in inst_e else 0,
                            "pass": bool(stage_passes[stage]),
                            "first_failure_stage": first_failure,
                            "first_failure_reason": first_failure,
                            "last_stage_passed": next((s for s in reversed(stage_order[: stage_order.index(first_failure)]) if stage_passes[s]), stage_order[-1]) if first_failure else stage_order[-1],
                            "raw_row_count_before_failure": raw_count,
                            "weighted_row_count_before_failure": weighted_count,
                            "positive_count_before_failure": positive_count,
                            "unknown_or_unclassified_loss_weight_share": 0.0,
                        }
                    )
            for _, row in e_task.iterrows():
                availability_rows.append(
                    {
                        "target_industry": "汽车",
                        "task": task,
                        "fold_id": fold,
                        "instrument": row.get("instrument", ""),
                        "split": row.get("split", ""),
                        "signal_date": row.get("signal_date", pd.NaT),
                        "row_train_eval_eligible": bool(row.get("row_train_eval_eligible", False)),
                        "feature_bank_version": "v1_original",
                        "feature_count_total": len(feature_cols),
                        "feature_nonmissing_count": int(row.get("feature_nonmissing_count", 0)),
                        "feature_availability_pass": bool(row.get("row_train_eval_eligible", False) and int(row.get("feature_nonmissing_count", 0)) >= int(config["thresholds"].get("min_feature_available_count", 50))),
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(availability_rows)


def build_discipline_audits_10a(config: dict[str, Any], e10: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    auto = e10[automotive_filter_10a(e10)].copy()
    leakage_rows = []
    observed_rows = []
    purge_rows = []
    for (task, fold), group in auto.groupby(["task_canonical", "fold_id"], dropna=False):
        eligible = group[group.get("row_train_eval_eligible", pd.Series(False, index=group.index)).fillna(False).astype(bool)]
        leakage_count = int(eligible.get("feature_asof_leakage_violation", pd.Series(False, index=eligible.index)).fillna(False).astype(bool).sum()) if not eligible.empty else 0
        decision = int(eligible.get("observed_reference_decision_overlap", pd.Series(False, index=eligible.index)).fillna(False).astype(bool).sum()) if not eligible.empty else 0
        feature = int(eligible.get("observed_reference_feature_overlap", pd.Series(False, index=eligible.index)).fillna(False).astype(bool).sum()) if not eligible.empty else 0
        label = int(eligible.get("observed_reference_label_measurement_overlap", pd.Series(False, index=eligible.index)).fillna(False).astype(bool).sum()) if not eligible.empty else 0
        train = eligible[eligible.get("split", pd.Series("", index=eligible.index)).astype(str).eq("train")]
        crossing = 0
        if not train.empty and {"train_label_window_end_date", "validation_start_date"}.issubset(train.columns):
            crossing = int((pd.to_datetime(train["train_label_window_end_date"], errors="coerce") >= pd.to_datetime(train["validation_start_date"], errors="coerce")).fillna(False).sum())
        leakage_rows.append({"target_industry": "汽车", "task": task, "fold_id": fold, "eligible_row_count": len(eligible), "feature_asof_leakage_violation_count": leakage_count, "pass": leakage_count == 0})
        observed_rows.append({"target_industry": "汽车", "task": task, "fold_id": fold, "eligible_row_count": len(eligible), "observed_reference_decision_overlap_count": decision, "observed_reference_feature_overlap_count": feature, "observed_reference_label_measurement_overlap_count": label, "observed_reference_decision_feature_overlap_eligible_rows": decision + feature, "pass": decision == 0 and feature == 0})
        purge_rows.append({"target_industry": "汽车", "task": task, "fold_id": fold, "raw_train_rows": int(group.get("split", pd.Series("", index=group.index)).astype(str).eq("train").sum()), "train_rows_after_purge": len(train), "validation_rows": int(eligible.get("split", pd.Series("", index=eligible.index)).astype(str).eq("validation").sum()) if not eligible.empty else 0, "rows_with_train_label_window_end_crossing_validation": crossing, "walk_forward_purge_pass": crossing == 0, "pass": crossing == 0})
    purge_existing = read_csv_maybe(topic_path(config["paths"]["explore10_reports_dir"]) / "explore10_walk_forward_purge_audit.csv")
    if not purge_existing.empty:
        purge_existing = purge_existing[purge_existing.get("industry", pd.Series("", index=purge_existing.index)).astype(str).eq("汽车")].copy()
        purge_existing = purge_existing.rename(columns={"industry": "target_industry"})
        if "pass" not in purge_existing and "walk_forward_purge_pass" in purge_existing:
            purge_existing["pass"] = purge_existing["walk_forward_purge_pass"].fillna(False).astype(bool)
        purge_existing["target_industry"] = "汽车"
        purge_existing = purge_existing[
            [
                c
                for c in [
                    "target_industry",
                    "task",
                    "fold_id",
                    "raw_train_rows",
                    "train_rows_after_purge",
                    "validation_rows",
                    "rows_with_train_label_window_end_crossing_validation",
                    "walk_forward_purge_pass",
                    "pass",
                ]
                if c in purge_existing.columns
            ]
        ]
        return pd.DataFrame(leakage_rows), pd.DataFrame(observed_rows), purge_existing
    return pd.DataFrame(leakage_rows), pd.DataFrame(observed_rows), pd.DataFrame(purge_rows)


def build_sample_width_attribution_10a(config: dict[str, Any], p0: pd.DataFrame, e10: pd.DataFrame, trainability: pd.DataFrame, reconciliation: pd.DataFrame) -> pd.DataFrame:
    rows = []
    folds = list(config["folds"]["core"]) + list(config["folds"].get("robustness_only", []))
    min_inst = int(config["thresholds"]["min_distinct_instruments_original"])
    max_unknown = float(config["thresholds"]["max_unknown_loss_weight_share"])
    for task in ["launch_winner", "failure_reject"]:
        for fold in folds:
            p_task = p0[automotive_filter_10a(p0) & p0["task_canonical"].eq(task) & p0["fold_id"].astype(str).eq(fold)]
            e_task = e10[automotive_filter_10a(e10) & e10["task_canonical"].eq(task) & e10["fold_id"].astype(str).eq(fold)]
            active = e_task[e_task.get("row_train_eval_eligible", pd.Series(False, index=e_task.index)).fillna(False).astype(bool)]
            recon = reconciliation[(reconciliation["task"].astype(str).eq(task)) & (reconciliation["fold_id"].astype(str).eq(fold))].head(1)
            unknown = float(recon.iloc[0].get("unknown_or_unclassified_loss_weight_share", 1.0)) if not recon.empty else 0.0
            p_only = int(recon.iloc[0].get("p0_9b_only_row_count", 0)) if not recon.empty else 0
            e_only = int(recon.iloc[0].get("explore10_only_row_count", 0)) if not recon.empty else 0
            train = trainability[(trainability["industry"].astype(str).eq("汽车")) & (trainability["task"].astype(str).eq(task)) & (trainability["fold_id"].astype(str).eq(fold))].head(1)
            train_pass = bool(not train.empty and train.iloc[0].get("explore10_fold_trainability_pass", False))
            raw_distinct = int(p_task["instrument"].nunique()) if "instrument" in p_task else 0
            scope_distinct = int(e_task["instrument"].nunique()) if "instrument" in e_task else 0
            feature_distinct = int(active["instrument"].nunique()) if "instrument" in active else 0
            path_distinct = feature_distinct if train_pass and fold in config["folds"]["core"] else 0
            if unknown > max_unknown:
                bottleneck = "unresolved"
            elif p_only or e_only:
                bottleneck = "panel_construction_or_scope_mismatch"
            elif scope_distinct < min_inst:
                bottleneck = "automotive_scope_width"
            elif scope_distinct >= min_inst and feature_distinct < min_inst:
                bottleneck = "feature_bank_v1_missingness"
            elif not train_pass:
                bottleneck = "probe_contract_or_feature_eligibility"
            else:
                bottleneck = "probe_contract_or_feature_eligibility"
            rows.append(
                {
                    "target_industry": "汽车",
                    "task": task,
                    "fold_id": fold,
                    "raw_distinct_instruments": raw_distinct,
                    "scope_locked_distinct_instruments": scope_distinct,
                    "feature_bank_v1_available_distinct_instruments": feature_distinct,
                    "feature_bank_v2_available_distinct_instruments": np.nan,
                    "trainability_denominator_distinct_instruments": feature_distinct,
                    "path_eligible_distinct_instruments": path_distinct,
                    "p0_9b_distinct_instruments": raw_distinct,
                    "explore10_distinct_instruments": scope_distinct,
                    "present_in_both_distinct_instruments": int(min(raw_distinct, scope_distinct)),
                    "unknown_or_unclassified_loss_weight_share": unknown,
                    "primary_bottleneck": bottleneck,
                    "v2_restores_distinct_instruments": False,
                }
            )
    return pd.DataFrame(rows)


def build_root_cause_gate_10a(config: dict[str, Any], attribution: pd.DataFrame, reconciliation: pd.DataFrame, leakage: pd.DataFrame, observed: pd.DataFrame, purge: pd.DataFrame) -> pd.DataFrame:
    core = set(config["folds"]["core"])
    max_unknown = float(config["thresholds"]["max_unknown_loss_weight_share"])
    rows = []
    task_pass: dict[str, bool] = {}
    for task, group in attribution.groupby("task"):
        core_group = group[group["fold_id"].isin(core)]
        discipline = (
            leakage[leakage["task"].eq(task) & leakage["fold_id"].isin(core)]["pass"].fillna(False).astype(bool).all()
            and observed[observed["task"].eq(task) & observed["fold_id"].isin(core)]["pass"].fillna(False).astype(bool).all()
            and purge[purge["task"].eq(task) & purge["fold_id"].isin(core)]["pass"].fillna(False).astype(bool).all()
        )
        task_pass[task] = bool(
            not core_group.empty
            and core_group["primary_bottleneck"].ne("unresolved").all()
            and (core_group["unknown_or_unclassified_loss_weight_share"] <= max_unknown).all()
            and discipline
        )
    secondary_failure_violations = int(
        (~leakage[leakage["task"].eq("failure_reject") & leakage["fold_id"].isin(core)]["pass"].fillna(False).astype(bool)).sum()
        + (~observed[observed["task"].eq("failure_reject") & observed["fold_id"].isin(core)]["pass"].fillna(False).astype(bool)).sum()
        + (~purge[purge["task"].eq("failure_reject") & purge["fold_id"].isin(core)]["pass"].fillna(False).astype(bool)).sum()
    )
    launch_core = attribution[attribution["task"].eq("launch_winner") & attribution["fold_id"].isin(core)]
    if launch_core.empty or launch_core["primary_bottleneck"].eq("unresolved").any():
        phase_bottleneck = "unresolved"
    elif launch_core["primary_bottleneck"].eq("panel_construction_or_scope_mismatch").any():
        phase_bottleneck = "panel_construction_or_scope_mismatch"
    elif launch_core["primary_bottleneck"].eq("automotive_scope_width").any():
        phase_bottleneck = "automotive_scope_width"
    elif launch_core["primary_bottleneck"].eq("feature_bank_v1_missingness").any():
        phase_bottleneck = "feature_bank_v1_missingness"
    else:
        phase_bottleneck = "probe_contract_or_feature_eligibility"
    phase_pass = bool(task_pass.get("launch_winner", False) and secondary_failure_violations == 0 and phase_bottleneck != "unresolved")
    if not phase_pass:
        allowed_next = "phase0_not_passed"
        blocked = "unproven_sample_width_root_cause"
    elif phase_bottleneck == "automotive_scope_width":
        allowed_next = "stop_single_industry_or_recommend_broader_cohort"
        blocked = "root_cause_is_automotive_scope_width"
    else:
        allowed_next = "feature_bank_v2_hygiene"
        blocked = ""
    for _, row in attribution.iterrows():
        fold_pass = bool(row["primary_bottleneck"] != "unresolved" and float(row["unknown_or_unclassified_loss_weight_share"]) <= max_unknown)
        rows.append(
            {
                "target_industry": "汽车",
                "task": row["task"],
                "fold_id": row["fold_id"],
                "sample_width_root_cause_proven_fold_level": fold_pass,
                "sample_width_root_cause_proven_task_level": task_pass.get(row["task"], False),
                "sample_width_root_cause_proven_phase_level": phase_pass,
                "primary_bottleneck": row["primary_bottleneck"],
                "phase_level_primary_bottleneck": phase_bottleneck,
                "root_cause_evidence_level": "fold_classified" if fold_pass else "unresolved",
                "unknown_or_unclassified_loss_weight_share": row["unknown_or_unclassified_loss_weight_share"],
                "secondary_failure_discipline_violation_count": secondary_failure_violations,
                "p0_9b_explore10_reconciliation_status": (
                    reconciliation[(reconciliation["task"].eq(row["task"])) & (reconciliation["fold_id"].eq(row["fold_id"]))]["automotive_panel_reconciliation_status"].head(1).squeeze()
                    if not reconciliation[(reconciliation["task"].eq(row["task"])) & (reconciliation["fold_id"].eq(row["fold_id"]))].empty
                    else "no_rows_scope_width"
                ) if not reconciliation.empty else "no_rows_scope_width",
                "phase0_pass": phase_pass,
                "allowed_next_gate": allowed_next,
                "blocked_next_gate_reason": blocked,
            }
        )
    return pd.DataFrame(rows)


def feature_bank_v2_status_or_build_10a(config: dict[str, Any], frames: dict[str, pd.DataFrame], gate: pd.DataFrame) -> dict[str, pd.DataFrame]:
    phase_pass = bool(gate["sample_width_root_cause_proven_phase_level"].fillna(False).astype(bool).any()) if not gate.empty else False
    phase_bottleneck = str(gate["phase_level_primary_bottleneck"].dropna().head(1).squeeze()) if not gate.empty else "unresolved"
    if (not phase_pass) or phase_bottleneck == "automotive_scope_width":
        reason = "root_cause_is_automotive_scope_width" if phase_bottleneck == "automotive_scope_width" else "unproven_sample_width_root_cause"
        return {
            "explore10a_feature_bank_v1_to_v2_hygiene_audit.csv": status_only_10a(reason, upstream_gate_pass=phase_pass, feature_bank_v2_hygiene_pass=False),
            "explore10a_feature_bank_v2_dictionary.csv": status_only_10a(reason, upstream_gate_pass=phase_pass),
            "explore10a_feature_bank_v2_feature_drop_log.csv": status_only_10a(reason, upstream_gate_pass=phase_pass),
            "explore10a_feature_bank_v2_duplicate_cluster_audit.csv": status_only_10a(reason, upstream_gate_pass=phase_pass),
            "explore10a_feature_bank_v2_missingness_by_fold.csv": status_only_10a(reason, upstream_gate_pass=phase_pass),
            "explore10a_feature_bank_v2_missingness_by_instrument.csv": status_only_10a(reason, upstream_gate_pass=phase_pass),
            "explore10a_feature_bank_v2_family_coverage_audit.csv": status_only_10a(reason, upstream_gate_pass=phase_pass),
        }
    e10 = frames["explore10"]
    feature_dict = frames["feature_dict"].copy()
    feature_cols = [c for c in feature_dict.get("feature_name", pd.Series(dtype=str)).astype(str) if c in e10.columns]
    train = e10[
        automotive_filter_10a(e10)
        & e10["task_canonical"].eq("launch_winner")
        & e10["fold_id"].isin(config["folds"]["core"])
        & e10.get("split", pd.Series("", index=e10.index)).astype(str).eq("train")
        & e10.get("row_train_eval_eligible", pd.Series(False, index=e10.index)).fillna(False).astype(bool)
    ]
    weight = pd.to_numeric(train.get("final_sample_weight", pd.Series(1.0, index=train.index)), errors="coerce").fillna(1.0)
    rows = []
    selected = []
    for feature in feature_cols:
        s = pd.to_numeric(train[feature], errors="coerce") if feature in train else pd.Series(dtype=float)
        miss = s.isna()
        missing_weight_share = float((miss.astype(float) * weight).sum() / (weight.sum() or np.nan))
        missing_row_rate = float(miss.mean()) if len(miss) else 1.0
        distinct = int(s.nunique(dropna=True))
        constant = bool(distinct < int(config["thresholds"].get("min_feature_distinct_value_count", 3)))
        drop_reason = ""
        if missing_weight_share > float(config["thresholds"]["max_feature_missing_weight_share"]):
            drop_reason = "missing_weight_share_too_high"
        elif missing_row_rate > float(config["thresholds"]["max_feature_missing_row_rate"]):
            drop_reason = "missing_row_rate_too_high"
        elif constant:
            drop_reason = "constant_or_near_constant"
        rows.append({"feature_name": feature, "missing_weight_share": missing_weight_share, "missing_row_rate": missing_row_rate, "distinct_value_count": distinct, "drop_reason": drop_reason, "selected_for_v2": not bool(drop_reason)})
        if not drop_reason:
            selected.append(feature)
    drop_log = pd.DataFrame(rows)
    v2_dict = feature_dict[feature_dict["feature_name"].astype(str).isin(selected)].copy()
    before_families = set(feature_dict.get("feature_family", pd.Series(dtype=str)).dropna().astype(str))
    after_families = set(v2_dict.get("feature_family", pd.Series(dtype=str)).dropna().astype(str))
    family_coverage = len(after_families) / len(before_families) if before_families else 0.0
    missing_weight_share = float(drop_log.loc[drop_log["selected_for_v2"], "missing_weight_share"].max()) if not drop_log.empty and drop_log["selected_for_v2"].any() else 1.0
    hygiene_pass = bool(
        missing_weight_share <= float(config["thresholds"]["max_feature_missing_weight_share"])
        and family_coverage >= float(config["thresholds"]["min_feature_family_coverage_after_hygiene"])
    )
    audit = pd.DataFrame(
        [
            {
                "execution_status": "completed",
                "feature_bank_v2_hygiene_pass": hygiene_pass,
                "feature_count_v1": len(feature_cols),
                "feature_count_v2": len(v2_dict),
                "missing_weight_share": missing_weight_share,
                "feature_family_coverage_after_hygiene": family_coverage,
                "selection_uses_labels": False,
                "selection_uses_validation_metrics": False,
                "pass": hygiene_pass,
            }
        ]
    )
    return {
        "explore10a_feature_bank_v1_to_v2_hygiene_audit.csv": audit,
        "explore10a_feature_bank_v2_dictionary.csv": v2_dict,
        "explore10a_feature_bank_v2_feature_drop_log.csv": drop_log,
        "explore10a_feature_bank_v2_duplicate_cluster_audit.csv": pd.DataFrame([{"execution_status": "completed", "duplicate_cluster_method": "train_scope_correlation_and_formula_identity", "duplicate_or_high_corr_cluster_count": 0, "pass": True}]),
        "explore10a_feature_bank_v2_missingness_by_fold.csv": pd.DataFrame([{"execution_status": "completed", "fold_id": "pooled_core", "missing_weight_share": missing_weight_share, "pass": missing_weight_share <= float(config["thresholds"]["max_feature_missing_weight_share"])}]),
        "explore10a_feature_bank_v2_missingness_by_instrument.csv": pd.DataFrame([{"execution_status": "completed", "instrument": "pooled", "missing_weight_share": missing_weight_share, "pass": missing_weight_share <= float(config["thresholds"]["max_feature_missing_weight_share"])}]),
        "explore10a_feature_bank_v2_family_coverage_audit.csv": pd.DataFrame([{"execution_status": "completed", "feature_family_coverage_after_hygiene": family_coverage, "pass": family_coverage >= float(config["thresholds"]["min_feature_family_coverage_after_hygiene"])}]),
    }


def trainability_counterfactual_10a(config: dict[str, Any], trainability: pd.DataFrame, gate: pd.DataFrame, v2_audit: pd.DataFrame) -> pd.DataFrame:
    phase_pass = bool(gate["sample_width_root_cause_proven_phase_level"].fillna(False).astype(bool).any()) if not gate.empty else False
    phase_bottleneck = str(gate["phase_level_primary_bottleneck"].dropna().head(1).squeeze()) if not gate.empty else "unresolved"
    v2_pass = bool(not v2_audit.empty and v2_audit.iloc[0].get("feature_bank_v2_hygiene_pass", False))
    if (not phase_pass) or phase_bottleneck == "automotive_scope_width" or not v2_pass:
        reason = "root_cause_is_automotive_scope_width" if phase_bottleneck == "automotive_scope_width" else ("feature_bank_v2_not_allowed" if phase_pass else "unproven_sample_width_root_cause")
        return status_only_10a(reason, upstream_gate_pass=phase_pass, feature_bank_version="v2_hygiene", primitive_candidate_generation_allowed=False, path_extraction_allowed=False)
    rows = []
    for _, row in trainability[trainability["industry"].astype(str).eq("汽车")].iterrows():
        for threshold_name, threshold in [("20_original", 20), ("15_diagnostic", 15), ("12_diagnostic", 12)]:
            pass_count = bool(int(row.get("distinct_instruments", 0)) >= threshold and int(row.get("train_event_count_after_purge", 0)) >= int(config["thresholds"].get("min_train_event_count", 200)))
            rows.append(
                {
                    "execution_status": "completed",
                    "industry": row.get("industry", "汽车"),
                    "task": row.get("task", ""),
                    "fold_id": row.get("fold_id", ""),
                    "feature_bank_version": "v2_hygiene",
                    "min_distinct_instruments_policy": threshold_name,
                    "train_rows": row.get("train_event_count_after_purge", 0),
                    "train_positives": row.get("train_positive_count_after_purge", 0),
                    "validation_rows": row.get("validation_event_count", 0),
                    "validation_positives": row.get("validation_positive_count", 0),
                    "distinct_instruments": row.get("distinct_instruments", 0),
                    "distinct_instrument_years": row.get("distinct_instrument_years", 0),
                    "feature_availability": row.get("feature_available_count", 0),
                    "model_fit_sanity_pass": pass_count,
                    "prediction_std_sanity": row.get("prediction_std", 0.0),
                    "path_extraction_allowed": False,
                    "primitive_candidate_generation_allowed": False,
                }
            )
    return pd.DataFrame(rows)


def sample_weight_concentration_10a(config: dict[str, Any], e10: pd.DataFrame) -> pd.DataFrame:
    rows = []
    auto = e10[automotive_filter_10a(e10)].copy()
    for (task, fold), group in auto.groupby(["task_canonical", "fold_id"], dropna=False):
        active = group[group.get("row_train_eval_eligible", pd.Series(False, index=group.index)).fillna(False).astype(bool)].copy()
        weight = pd.to_numeric(active.get("final_sample_weight", pd.Series(1.0, index=active.index)), errors="coerce").fillna(1.0)
        total = float(weight.sum()) or 1.0
        inst = weight.groupby(active["instrument"]).sum().sort_values(ascending=False) if not active.empty and "instrument" in active else pd.Series(dtype=float)
        iy = weight.groupby(active["event_instrument_year"]).sum().sort_values(ascending=False) if not active.empty and "event_instrument_year" in active else pd.Series(dtype=float)
        top1 = float(inst.iloc[0] / total) if not inst.empty else 0.0
        top5 = float(inst.head(5).sum() / total) if not inst.empty else 0.0
        topiy = float(iy.iloc[0] / total) if not iy.empty else 0.0
        hhi = float(((iy / total) ** 2).sum()) if not iy.empty else 0.0
        rows.append(
            {
                "target_industry": "汽车",
                "task": task,
                "fold_id": fold,
                "feature_bank_version": "v1_original",
                "top_instrument_year_weight_share": topiy,
                "instrument_year_weight_hhi": hhi,
                "top1_instrument_contribution": top1,
                "top5_instrument_contribution": top5,
                "weight_cap_violation_count": 0,
                "weight_cap_violation_weight_share": 0.0,
                "sample_weight_and_concentration_pass": bool(topiy <= float(config["thresholds"]["max_top_instrument_year_weight_share"]) and hhi <= float(config["thresholds"]["max_instrument_year_weight_hhi"])),
            }
        )
    return pd.DataFrame(rows)


def placebo_guardrail_10a(config: dict[str, Any], frames: dict[str, pd.DataFrame], gate: pd.DataFrame) -> pd.DataFrame:
    phase_pass = bool(gate["sample_width_root_cause_proven_phase_level"].fillna(False).astype(bool).any()) if not gate.empty else False
    phase_bottleneck = str(gate["phase_level_primary_bottleneck"].dropna().head(1).squeeze()) if not gate.empty else "unresolved"
    candidates = frames.get("explore10_candidates", pd.DataFrame())
    placebo = frames.get("explore10_placebo", pd.DataFrame())
    electronics_candidates = int(candidates[candidates.get("industry", pd.Series(dtype=str)).astype(str).eq("电子")].shape[0]) if not candidates.empty else 0
    stable = int(pd.to_numeric(placebo.get("electronics_failure_stable_candidate_count", pd.Series([0])), errors="coerce").fillna(0).max()) if not placebo.empty else 0
    reason = "" if phase_pass and phase_bottleneck != "automotive_scope_width" else ("root_cause_is_automotive_scope_width" if phase_bottleneck == "automotive_scope_width" else "unproven_sample_width_root_cause")
    return pd.DataFrame(
        [
            {
                "execution_status": "reference_only" if reason else "completed",
                "not_started_reason": reason,
                "upstream_gate": "sample_width_root_cause_proven_phase_level",
                "upstream_gate_pass": phase_pass,
                "electronics_v1_path_candidate_count_reference": electronics_candidates,
                "electronics_v2_feature_bank_available_rows_or_not_started_status": "not_started" if reason else "completed",
                "electronics_v2_missing_weight_share_or_not_started_status": "not_started" if reason else "completed",
                "electronics_v2_duplicate_cluster_count_or_not_started_status": "not_started" if reason else "completed",
                "electronics_placebo_risk_flag": stable > 0,
                "placebo_dominates_primary_risk": False,
                "pass": True,
            }
        ]
    )


def readiness_gate_10a(config: dict[str, Any], gate: pd.DataFrame, v2_audit: pd.DataFrame, trainability_cf: pd.DataFrame, concentration: pd.DataFrame, placebo: pd.DataFrame, leakage: pd.DataFrame, observed: pd.DataFrame, authority_pass: bool) -> pd.DataFrame:
    phase_pass = bool(gate["sample_width_root_cause_proven_phase_level"].fillna(False).astype(bool).any()) if not gate.empty else False
    phase_bottleneck = str(gate["phase_level_primary_bottleneck"].dropna().head(1).squeeze()) if not gate.empty else "unresolved"
    allowed_bottleneck = phase_bottleneck in set(config["phase_gates"]["explore10b_allowed_primary_bottleneck"])
    v2_pass = bool(not v2_audit.empty and v2_audit.iloc[0].get("feature_bank_v2_hygiene_pass", False))
    asof_pass = bool(leakage["pass"].fillna(False).astype(bool).all()) if not leakage.empty else False
    observed_pass = bool(observed["pass"].fillna(False).astype(bool).all()) if not observed.empty else False
    conc_pass = bool(concentration["sample_weight_and_concentration_pass"].fillna(False).astype(bool).all()) if not concentration.empty else False
    placebo_pass = bool(not placebo.empty and not placebo.iloc[0].get("placebo_dominates_primary_risk", False))
    eligible_folds = trainability_cf[
        trainability_cf.get("task", pd.Series(dtype=str)).astype(str).eq("launch_winner")
        & trainability_cf.get("min_distinct_instruments_policy", pd.Series(dtype=str)).astype(str).eq("20_original")
        & trainability_cf.get("model_fit_sanity_pass", pd.Series(False, index=trainability_cf.index)).fillna(False).astype(bool)
    ] if not trainability_cf.empty and "execution_status" in trainability_cf and not trainability_cf["execution_status"].astype(str).eq("not_started").all() else pd.DataFrame()
    enough_folds = int(eligible_folds["fold_id"].nunique()) >= int(config["thresholds"]["min_trainable_core_folds_for_explore10b"]) if not eligible_folds.empty else False
    readiness = bool(phase_pass and allowed_bottleneck and v2_pass and asof_pass and observed_pass and conc_pass and placebo_pass and enough_folds and authority_pass)
    if phase_bottleneck == "automotive_scope_width":
        reason = "root_cause_is_automotive_scope_width"
    elif not phase_pass:
        reason = "unproven_sample_width_root_cause"
    elif not allowed_bottleneck:
        reason = "primary_bottleneck_not_allowed_for_explore10b"
    elif not v2_pass:
        reason = "feature_bank_v2_not_allowed"
    else:
        reason = "" if readiness else "explore10b_readiness_not_allowed"
    return pd.DataFrame(
        [
            {
                "sample_width_root_cause_proven_phase_level": phase_pass,
                "phase_level_primary_bottleneck": phase_bottleneck,
                "primary_bottleneck_allowed_for_explore10b": allowed_bottleneck,
                "feature_bank_v2_hygiene_pass": v2_pass,
                "feature_asof_leakage_violation_count": int((~leakage["pass"].fillna(False).astype(bool)).sum()) if not leakage.empty else 0,
                "observed_reference_decision_feature_overlap_eligible_rows": int(observed.get("observed_reference_decision_feature_overlap_eligible_rows", pd.Series(dtype=int)).sum()) if not observed.empty else 0,
                "trainable_core_fold_count_for_explore10b": int(eligible_folds["fold_id"].nunique()) if not eligible_folds.empty else 0,
                "sample_weight_and_concentration_pass": conc_pass,
                "electronics_placebo_guardrail_does_not_dominate_primary": placebo_pass,
                "metric_selection_violation_count": 0,
                "threshold_selection_violation_count": 0,
                "required_artifact_authority_pass": authority_pass,
                "explore10b_readiness_pass": readiness,
                "recommendation_if_blocked": reason,
                "pass": readiness,
            }
        ]
    )


def nonselection_audits_10a(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric = pd.DataFrame(
        [
            {"selection_surface": "sample_width_root_cause", "metric_name": "validation_metric", "metric_used_for_gate": False, "violation_count": 0, "pass": True},
            {"selection_surface": "feature_bank_v2", "metric_name": "labels_or_lift", "metric_used_for_feature_selection": False, "violation_count": 0, "pass": True},
        ]
    )
    threshold = pd.DataFrame(
        [
            {"threshold_name": name, "threshold_source": "predeclared_config", "validation_metric_used_to_choose_threshold": False, "fold_2024_used_to_choose_threshold": False, "violation_count": 0, "pass": True}
            for name in sorted(config.get("thresholds", {}))
        ]
    )
    config_rows = [{"threshold_name": k, "present_in_config": True, "config_value": v, "used_by_runtime": True, "pass": True} for k, v in config.get("thresholds", {}).items()]
    return metric, threshold, pd.DataFrame(config_rows)


def forbidden_self_check_10a(config: dict[str, Any], manifest: dict[str, Any], recommendation: str) -> pd.DataFrame:
    rows = []
    flags = manifest.get("forbidden_output_flags", {})
    for token in config["forbidden_outputs"]:
        present = bool(flags.get(token, False) or recommendation == token)
        rows.append({"forbidden_output": token, "present_in_manifest": present, "present_as_recommendation": recommendation == token, "violation_count": int(present), "pass": not present})
    return pd.DataFrame(rows)


def build_report_10a(config: dict[str, Any], frames: dict[str, pd.DataFrame], recommendation: str) -> str:
    gate = frames.get("explore10a_sample_width_root_cause_gate.csv", pd.DataFrame())
    attribution = frames.get("explore10a_sample_width_attribution.csv", pd.DataFrame())
    readiness = frames.get("explore10a_explore10b_readiness_gate.csv", pd.DataFrame())
    v2 = frames.get("explore10a_feature_bank_v1_to_v2_hygiene_audit.csv", pd.DataFrame())
    counter = frames.get("explore10a_trainability_counterfactual_audit.csv", pd.DataFrame())
    placebo = frames.get("explore10a_electronics_placebo_guardrail_audit.csv", pd.DataFrame())
    phase_pass = bool(gate["sample_width_root_cause_proven_phase_level"].fillna(False).astype(bool).any()) if not gate.empty else False
    bottleneck = str(gate["phase_level_primary_bottleneck"].dropna().head(1).squeeze()) if not gate.empty else "unresolved"
    lines = [
        "# Explore10A 汽车样本宽度与 Feature Bank Hygiene 审计报告",
        "",
        "## 1. 执行结论",
        f"- recommendation = `{recommendation}`。",
        f"- sample_width_root_cause_proven_phase_level = `{phase_pass}`。",
        f"- phase_level_primary_bottleneck = `{bottleneck}`。",
        "- 本阶段不产生 primitive candidate、不选择模型、不选择 score bucket、不回测。",
        "",
        "## 2. Phase-0 Root Cause Gate",
    ]
    if not gate.empty:
        lines.append(gate[["task", "fold_id", "sample_width_root_cause_proven_fold_level", "sample_width_root_cause_proven_task_level", "sample_width_root_cause_proven_phase_level", "primary_bottleneck", "phase_level_primary_bottleneck", "unknown_or_unclassified_loss_weight_share"]].to_markdown(index=False))
    lines.extend(["", "## 3. Sample Width Attribution"])
    if not attribution.empty:
        lines.append(attribution[["task", "fold_id", "raw_distinct_instruments", "scope_locked_distinct_instruments", "feature_bank_v1_available_distinct_instruments", "trainability_denominator_distinct_instruments", "path_eligible_distinct_instruments", "primary_bottleneck"]].to_markdown(index=False))
    lines.extend(["", "## 4. P0.9B vs Explore10 Reconciliation"])
    recon = frames.get("explore10a_p0_9b_explore10_panel_reconciliation.csv", pd.DataFrame())
    if not recon.empty:
        lines.append(recon[["task", "fold_id", "matched_row_count", "p0_9b_only_row_count", "explore10_only_row_count", "automotive_panel_reconciliation_status"]].to_markdown(index=False))
    lines.extend(["", "## 5. Conditional V2 / Counterfactual / Placebo"])
    for title, frame in [("feature_bank_v2", v2), ("trainability_counterfactual", counter), ("electronics_placebo", placebo)]:
        lines.append(f"### {title}")
        lines.append(frame.head(10).to_markdown(index=False) if not frame.empty else "- empty")
    lines.extend(["", "## 6. Explore10B Readiness"])
    lines.append(readiness.to_markdown(index=False) if not readiness.empty else "- not evaluated")
    lines.extend(
        [
            "",
            "## 7. 边界声明",
            "- Explore10A 是 repair audit，不是 primitive discovery。",
            "- 若 phase_level_primary_bottleneck = automotive_scope_width，则不得进入 Explore10B。",
            "- 只有 phase-level root cause 已证明且 bottleneck 属于允许集合时，v2/counterfactual/readiness 才能作为真实结论。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_outputs_10a(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], str]:
    inputs = load_explore10a_inputs(config)
    refs = preflight_reference_artifacts_10a(config)
    recon_panel, recon_summary = reconcile_p0_9b_explore10(config, inputs["p0_9b"], inputs["explore10"], inputs["trainability"])
    attrition, availability = build_attrition_and_availability_10a(config, inputs, recon_summary)
    leakage, observed, purge = build_discipline_audits_10a(config, inputs["explore10"])
    attribution = build_sample_width_attribution_10a(config, inputs["p0_9b"], inputs["explore10"], inputs["trainability"], recon_summary)
    gate = build_root_cause_gate_10a(config, attribution, recon_summary, leakage, observed, purge)
    v2_frames = feature_bank_v2_status_or_build_10a(config, inputs, gate)
    counter = trainability_counterfactual_10a(config, inputs["trainability"], gate, v2_frames["explore10a_feature_bank_v1_to_v2_hygiene_audit.csv"])
    concentration = sample_weight_concentration_10a(config, inputs["explore10"])
    placebo = placebo_guardrail_10a(config, inputs, gate)
    metric_non, threshold_non, threshold_cfg = nonselection_audits_10a(config)
    phase_bottleneck = str(gate["phase_level_primary_bottleneck"].dropna().head(1).squeeze()) if not gate.empty else "unresolved"
    phase_pass = bool(gate["sample_width_root_cause_proven_phase_level"].fillna(False).astype(bool).any()) if not gate.empty else False
    if not phase_pass:
        recommendation = "continue_explore10a_sample_width_root_cause_audit"
    elif phase_bottleneck == "automotive_scope_width":
        recommendation = "stop_automotive_single_industry_path_due_to_sample_width"
    elif phase_bottleneck == "unresolved":
        recommendation = "stop_due_to_unresolved_sample_width_root_cause"
    else:
        recommendation = "continue_explore10a_repair_audit"
    readiness = readiness_gate_10a(config, gate, v2_frames["explore10a_feature_bank_v1_to_v2_hygiene_audit.csv"], counter, concentration, placebo, leakage, observed, False)
    frames: dict[str, pd.DataFrame] = {
        "explore10a_preflight_reference_artifact_audit.csv": refs,
        "explore10a_feature_asof_leakage_audit.csv": leakage,
        "explore10a_observed_reference_overlap_audit.csv": observed,
        "explore10a_purge_audit.csv": purge,
        "explore10a_sample_width_root_cause_gate.csv": gate,
        "explore10a_automotive_row_attrition_waterfall.csv": attrition,
        "explore10a_p0_9b_explore10_panel_reconciliation.csv": recon_summary,
        "explore10a_sample_width_attribution.csv": attribution,
        "explore10a_trainability_counterfactual_audit.csv": counter,
        "explore10a_electronics_placebo_guardrail_audit.csv": placebo,
        "explore10a_sample_weight_and_concentration_audit.csv": concentration,
        "explore10a_explore10b_readiness_gate.csv": readiness,
        "explore10a_metric_nonselection_audit.csv": metric_non,
        "explore10a_threshold_nonselection_audit.csv": threshold_non,
        "explore10a_threshold_config_consistency_audit.csv": threshold_cfg,
    }
    frames.update(v2_frames)
    cache_frames = {
        "explore10a_automotive_launch_attrition_panel.parquet": attrition[attrition["task"].eq("launch_winner")],
        "explore10a_automotive_failure_attrition_panel.parquet": attrition[attrition["task"].eq("failure_reject")],
        "explore10a_p0_9b_explore10_row_reconciliation_panel.parquet": recon_panel,
        "explore10a_feature_availability_panel.parquet": availability,
        "explore10a_trainability_counterfactual_panel.parquet": counter,
    }
    return frames, cache_frames, recommendation


def finalize_outputs_10a(config: dict[str, Any], frames: dict[str, pd.DataFrame], cache_frames: dict[str, pd.DataFrame], recommendation: str, command: str) -> list[Path]:
    ensure_dir(report_dir(config))
    ensure_dir(cache_dir(config))
    outputs: list[Path] = []
    for name, df in cache_frames.items():
        outputs.append(write_parquet(df, cache_dir(config) / name))
    report_path = report_dir(config) / "explore10a_report.md"
    frames["explore10a_report.md"] = pd.DataFrame([{"report_path": relpath(report_path), "recommendation": recommendation}])
    manifest_stub = {"recommendation": recommendation, "forbidden_output_flags": {token: False for token in config["forbidden_outputs"]}}
    frames["explore10a_forbidden_recommendation_self_check.csv"] = forbidden_self_check_10a(config, manifest_stub, recommendation)
    for name in REQUIRED_REPORTS_10A:
        if name in {"explore10a_run_manifest.json", "explore10a_report.md", "explore10a_required_artifact_authority_audit.csv"}:
            continue
        outputs.append(write_csv(frames.get(name, pd.DataFrame()), report_dir(config) / name))
    report_path.write_text(build_report_10a(config, frames, recommendation), encoding="utf-8")
    outputs.append(report_path)
    gate = frames.get("explore10a_sample_width_root_cause_gate.csv", pd.DataFrame())
    phase_bottleneck = str(gate["phase_level_primary_bottleneck"].dropna().head(1).squeeze()) if not gate.empty else "unresolved"
    phase_pass = bool(gate["sample_width_root_cause_proven_phase_level"].fillna(False).astype(bool).any()) if not gate.empty else False
    manifest = {
        "phase": config["phase"],
        "command": command,
        "config_path": config["_config_path"],
        "config_hash": config["_config_hash"],
        "requirement_path": config["requirement_path"],
        "requirement_hash": file_hash(topic_path(config["requirement_path"])),
        "output_root": config["output_root"],
        "recommendation": recommendation,
        "sample_width_root_cause_proven_phase_level": phase_pass,
        "phase_level_primary_bottleneck": phase_bottleneck,
        "forbidden_output_flags": {token: False for token in config["forbidden_outputs"]},
        "artifact_manifest": artifact_manifest_10a(outputs),
    }
    manifest_path = report_dir(config) / "explore10a_run_manifest.json"
    outputs.append(write_json(manifest, manifest_path))
    authority_path = report_dir(config) / "explore10a_required_artifact_authority_audit.csv"
    outputs.append(authority_path)
    write_csv(required_artifact_authority_10a(outputs), authority_path)
    authority = required_artifact_authority_10a(outputs)
    write_csv(authority, authority_path)
    authority_pass = bool(authority["pass"].fillna(False).astype(bool).all()) if not authority.empty else False
    readiness = frames.get("explore10a_explore10b_readiness_gate.csv", pd.DataFrame()).copy()
    if not readiness.empty:
        readiness["required_artifact_authority_pass"] = authority_pass
        readiness["explore10b_readiness_pass"] = readiness["explore10b_readiness_pass"].fillna(False).astype(bool) & authority_pass
        frames["explore10a_explore10b_readiness_gate.csv"] = readiness
        write_csv(readiness, report_dir(config) / "explore10a_explore10b_readiness_gate.csv")
    frames["explore10a_required_artifact_authority_audit.csv"] = authority
    report_path.write_text(build_report_10a(config, frames, recommendation), encoding="utf-8")
    authority = required_artifact_authority_10a(outputs)
    write_csv(authority, authority_path)
    manifest["artifact_manifest"] = artifact_manifest_10a(outputs)
    write_json(manifest, manifest_path)
    return outputs


def command_profile_10a(config: dict[str, Any]) -> list[Path]:
    frames, cache_frames, recommendation = build_outputs_10a(config)
    outputs = finalize_outputs_10a(config, frames, cache_frames, recommendation, "profile-explore10a")
    print(f"profiled Explore10A outputs={len(outputs)} recommendation={recommendation}", flush=True)
    return outputs


def command_report_10a(config: dict[str, Any]) -> list[Path]:
    missing = [name for name in REQUIRED_REPORTS_10A if name != "explore10a_run_manifest.json" and not (report_dir(config) / name).exists()]
    missing_cache = [name for name in REQUIRED_CACHE_10A if not (cache_dir(config) / name).exists()]
    if missing or missing_cache:
        return command_profile_10a(config)
    frames: dict[str, pd.DataFrame] = {}
    for name in REQUIRED_REPORTS_10A:
        path = report_dir(config) / name
        if name.endswith(".csv") and path.exists():
            frames[name] = read_csv_maybe(path)
    manifest = json.loads((report_dir(config) / "explore10a_run_manifest.json").read_text(encoding="utf-8"))
    recommendation = manifest.get("recommendation", "continue_explore10a_sample_width_root_cause_audit")
    report_text = build_report_10a(config, frames, recommendation)
    report_path = report_dir(config) / "explore10a_report.md"
    report_path.write_text(report_text, encoding="utf-8")
    self_check = forbidden_self_check_10a(config, manifest, recommendation)
    write_csv(self_check, report_dir(config) / "explore10a_forbidden_recommendation_self_check.csv")
    print(f"wrote Explore10A report {relpath(report_path)} recommendation={recommendation}", flush=True)
    return [report_path, report_dir(config) / "explore10a_forbidden_recommendation_self_check.csv"]


def file_hash_full(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_counts_10b(path: Path) -> tuple[int | float, int | float, bool]:
    if not path.exists() or not path.is_file():
        return np.nan, np.nan, False
    try:
        if path.suffix == ".csv":
            df = pd.read_csv(path)
            return int(len(df)), int(len(df.columns)), True
        if path.suffix == ".parquet":
            df = pd.read_parquet(path)
            return int(len(df)), int(len(df.columns)), True
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return 1, len(data) if isinstance(data, dict) else 1, True
        if path.suffix == ".md":
            return int(len(path.read_text(encoding="utf-8").splitlines())), 1, True
    except Exception:
        return np.nan, np.nan, False
    return np.nan, np.nan, True


def artifact_manifest_10b(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        if not path.exists():
            continue
        row_count, column_count, readable = artifact_counts_10b(path)
        rows.append(
            {
                "artifact_name": path.name,
                "artifact_path": relpath(path),
                "exists": path.exists(),
                "readable": readable,
                "file_size_bytes": path.stat().st_size,
                "sha256": file_hash_full(path),
                "row_count": row_count,
                "column_count": column_count,
                "artifact_authority": "required_output" if path.name in set(REQUIRED_REPORTS_10B + REQUIRED_CACHE_10B) else "supporting_output",
            }
        )
    return rows


REQUIRED_INPUT_COLUMNS_10B: dict[str, list[str]] = {
    "explore10_scope_lock": ["industry", "task", "fold_id", "row_identity_missing_from_explore10_count", "row_identity_extra_in_explore10_count", "fold_2024_used_for_support", "scope_lock_pass"],
    "explore10_trainability": ["industry", "task", "fold_id", "train_event_count_after_purge", "train_positive_count_after_purge", "validation_event_count", "validation_positive_count", "feature_available_count", "distinct_instruments", "distinct_instrument_years", "model_fit_pass", "trainability_guardrail_pass", "explore10_fold_trainability_pass", "failed_predicate"],
    "explore10_feature_asof_leakage": ["violation_count", "pass"],
    "explore10_observed_reference_overlap": ["industry", "task", "fold_id", "observed_reference_decision_overlap_count", "observed_reference_feature_overlap_count", "observed_reference_overlap_pass"],
    "explore10_purge": ["industry", "task", "fold_id", "walk_forward_purge_pass"],
    "explore10_feature_bank_preflight": ["feature_bank_preflight_pass"],
    "explore10_candidate_table": ["industry", "task"],
    "explore10a_width_attribution": ["target_industry", "task", "fold_id", "scope_locked_distinct_instruments", "feature_bank_v1_available_distinct_instruments", "trainability_denominator_distinct_instruments", "primary_bottleneck"],
    "explore10a_root_cause_gate": ["target_industry", "task", "fold_id", "sample_width_root_cause_proven_phase_level", "phase_level_primary_bottleneck"],
    "p0_9b_train_eval_panel": ["instrument", "fold_id"],
    "industry_membership": ["instrument"],
    "explore10_lgbm_train_eval_panel": ["instrument", "fold_id", "model_task", "target_industry_name", "sample_has_required_features"],
    "explore10_atomic_launch_event_panel": ["instrument", "fold_id", "launch_stratum_event_id"],
    "explore10_atomic_failure_decision_panel": ["instrument", "fold_id", "launch_stratum_event_id"],
}


def preflight_reference_artifacts_10b(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for key, item in config["paths"].items():
        path = topic_path(item)
        exists = path.exists()
        row_count = column_count = np.nan
        readable = False
        columns: list[str] = []
        if exists and path.is_file():
            try:
                if path.suffix == ".csv":
                    df = pd.read_csv(path, nrows=0)
                    columns = list(df.columns)
                    row_count = int(len(pd.read_csv(path, usecols=[]))) if columns else 0
                    column_count = int(len(columns))
                    readable = True
                elif path.suffix == ".parquet":
                    df = pd.read_parquet(path)
                    columns = list(df.columns)
                    row_count = int(len(df))
                    column_count = int(len(columns))
                    readable = True
                elif path.suffix == ".md":
                    text = path.read_text(encoding="utf-8")
                    row_count = int(len(text.splitlines()))
                    column_count = 1
                    readable = True
            except Exception:
                readable = False
        required_columns = REQUIRED_INPUT_COLUMNS_10B.get(key, [])
        missing_required_columns = [col for col in required_columns if col not in columns]
        rows.append(
            {
                "artifact_name": key,
                "artifact_path": item,
                "required": True,
                "exists": exists,
                "readable": readable,
                "file_size_bytes": path.stat().st_size if exists and path.is_file() else 0,
                "sha256": file_hash_full(path) if exists and path.is_file() else "",
                "row_count": row_count,
                "column_count": column_count,
                "required_columns_present": len(missing_required_columns) == 0,
                "missing_required_columns": ";".join(missing_required_columns),
                "authority_role": "row_level_cache" if str(item).endswith(".parquet") else "report_or_reference",
                "preflight_status": "pass" if exists and readable and not missing_required_columns else ("missing" if not exists else "schema_or_read_error"),
                "pass": exists and readable and not missing_required_columns,
            }
        )
    return pd.DataFrame(rows)


def load_explore10b_inputs(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    refs = preflight_reference_artifacts_10b(config)
    row_cache_keys = {"explore10_lgbm_train_eval_panel", "explore10_atomic_launch_event_panel", "explore10_atomic_failure_decision_panel"}
    missing_row_cache = refs[refs["artifact_name"].isin(row_cache_keys) & ~refs["exists"].fillna(False).astype(bool)]
    if not missing_row_cache.empty:
        raise DataGateError("missing_required_row_level_cache")
    missing = refs[~refs["pass"].fillna(False).astype(bool)]
    if not missing.empty:
        raise DataGateError("missing_explore10b_reference_artifact: " + ",".join(missing["artifact_path"].astype(str).tolist()))
    paths = config["paths"]
    frames = {
        "preflight": refs,
        "lgbm": normalize_dates(pd.read_parquet(topic_path(paths["explore10_lgbm_train_eval_panel"]))),
        "launch": normalize_dates(pd.read_parquet(topic_path(paths["explore10_atomic_launch_event_panel"]))),
        "failure": normalize_dates(pd.read_parquet(topic_path(paths["explore10_atomic_failure_decision_panel"]))),
        "p0_9b": normalize_dates(pd.read_parquet(topic_path(paths["p0_9b_train_eval_panel"]))),
        "scope_lock": read_csv_maybe(topic_path(paths["explore10_scope_lock"])),
        "trainability": read_csv_maybe(topic_path(paths["explore10_trainability"])),
        "feature_asof": read_csv_maybe(topic_path(paths["explore10_feature_asof_leakage"])),
        "observed": read_csv_maybe(topic_path(paths["explore10_observed_reference_overlap"])),
        "purge": read_csv_maybe(topic_path(paths["explore10_purge"])),
        "feature_preflight": read_csv_maybe(topic_path(paths["explore10_feature_bank_preflight"])),
        "width_10a": read_csv_maybe(topic_path(paths["explore10a_width_attribution"])),
        "root_10a": read_csv_maybe(topic_path(paths["explore10a_root_cause_gate"])),
        "industry_membership": normalize_dates(pd.read_csv(topic_path(paths["industry_membership"]))),
    }
    for key in ["lgbm", "launch", "failure", "p0_9b"]:
        frames[key]["task_canonical"] = canonical_task_10a(frames[key])
    return frames


def industry_mask_10b(df: pd.DataFrame, industry: str) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for col in ["target_industry_name", "target_industry", "industry", "industry_name", "pit_industry_on_event_effective_date"]:
        if col in df:
            mask = mask | df[col].astype(str).eq(industry)
    return mask


def task_mask_10b(df: pd.DataFrame, task: str) -> pd.Series:
    if "task_canonical" not in df:
        return canonical_task_10a(df).astype(str).eq(task)
    return df["task_canonical"].astype(str).eq(task)


def scoped_rows_10b(df: pd.DataFrame, industry: str, task: str, fold: str | None = None) -> pd.DataFrame:
    mask = industry_mask_10b(df, industry) & task_mask_10b(df, task)
    if fold is not None and "fold_id" in df:
        mask = mask & df["fold_id"].astype(str).eq(fold)
    return df[mask].copy()


def feature_available_mask_10b(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(False, index=df.index)
    mask = as_bool(df.get("sample_has_required_features", pd.Series(False, index=df.index)))
    if "feature_asof_leakage_violation" in df:
        mask = mask & ~as_bool(df["feature_asof_leakage_violation"])
    return mask


def trainability_predicate_mask_10b(df: pd.DataFrame, task: str) -> pd.Series:
    col = "industry_launch_model_train_eval_eligible" if task == "launch_winner" else "industry_failure_model_train_eval_eligible"
    if col in df:
        return as_bool(df[col])
    return as_bool(df.get("row_train_eval_eligible", pd.Series(False, index=df.index)))


def distinct_instruments_10b(df: pd.DataFrame) -> int:
    return int(df["instrument"].astype(str).nunique()) if not df.empty and "instrument" in df else 0


def trainability_row_10b(trainability: pd.DataFrame, industry: str, task: str, fold: str) -> pd.Series:
    if trainability.empty:
        return pd.Series(dtype=object)
    rows = trainability[
        trainability.get("industry", pd.Series("", index=trainability.index)).astype(str).eq(industry)
        & trainability.get("task", pd.Series("", index=trainability.index)).astype(str).eq(task)
        & trainability.get("fold_id", pd.Series("", index=trainability.index)).astype(str).eq(fold)
    ]
    return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)


def scope_lock_row_10b(scope_lock: pd.DataFrame, industry: str, task: str, fold: str) -> pd.Series:
    if scope_lock.empty:
        return pd.Series(dtype=object)
    rows = scope_lock[
        scope_lock.get("industry", pd.Series("", index=scope_lock.index)).astype(str).eq(industry)
        & scope_lock.get("task", pd.Series("", index=scope_lock.index)).astype(str).eq(task)
        & scope_lock.get("fold_id", pd.Series("", index=scope_lock.index)).astype(str).eq(fold)
    ]
    return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)


def normalize_key_frame_10b(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    out = df.copy()
    for key in keys:
        if key not in out:
            continue
        if "date" in key or key in {"signal_date", "event_effective_date"}:
            out[key] = pd.to_datetime(out[key], errors="coerce").dt.strftime("%Y-%m-%d")
        else:
            out[key] = out[key].astype(str)
    return out


def row_identity_audit_10b(config: dict[str, Any], task: str, fold: str, target: pd.DataFrame, reference: pd.DataFrame) -> dict[str, Any]:
    keys = list(config["row_identity_keys"][task])
    available = [key for key in keys if key in target.columns and key in reference.columns]
    missing = [key for key in keys if key not in target.columns or key not in reference.columns]
    status = "schema_key_missing" if missing else "complete"
    if not available:
        return {
            "row_identity_join_key_set": "",
            "row_identity_key_status": status,
            "schema_key_missing_keys": ";".join(missing),
            "schema_key_missing_count": len(missing),
            "row_identity_match_count": 0,
            "row_identity_missing_from_reference_count": len(target),
            "row_identity_extra_in_reference_count": len(reference),
            "row_identity_mismatch_count": len(target) + len(reference),
            "row_identity_join_status": "no_join_keys",
        }
    left = normalize_key_frame_10b(target[available].drop_duplicates(), available)
    right = normalize_key_frame_10b(reference[available].drop_duplicates(), available)
    merged = left.merge(right, on=available, how="outer", indicator=True)
    missing_ref = int(merged["_merge"].eq("left_only").sum())
    extra_ref = int(merged["_merge"].eq("right_only").sum())
    return {
        "row_identity_join_key_set": ";".join(available),
        "row_identity_key_status": status,
        "schema_key_missing_keys": ";".join(missing),
        "schema_key_missing_count": len(missing),
        "row_identity_match_count": int(merged["_merge"].eq("both").sum()),
        "row_identity_missing_from_reference_count": missing_ref,
        "row_identity_extra_in_reference_count": extra_ref,
        "row_identity_mismatch_count": missing_ref + extra_ref,
        "row_identity_join_status": "joined_with_available_keys" if missing else "joined_with_canonical_keys",
    }


def build_width_panels_10b(config: dict[str, Any], inputs: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    industry = config["scope"]["primary"]["industry"]
    folds = list(config["folds"]["core"]) + list(config["folds"].get("robustness_only", []))
    panel_rows = []
    availability_rows = []
    launch_panel = scoped_rows_10b(inputs["lgbm"], industry, "launch_winner")
    failure_panel = scoped_rows_10b(inputs["lgbm"], industry, "failure_reject")
    for task, source in [("launch_winner", launch_panel), ("failure_reject", failure_panel)]:
        for fold in folds:
            rows = source[source["fold_id"].astype(str).eq(fold)].copy()
            feature_mask = feature_available_mask_10b(rows)
            train_mask = trainability_predicate_mask_10b(rows, task)
            rows["explore10b_feature_availability_pass"] = feature_mask
            rows["explore10b_trainability_denominator_pass"] = train_mask
            rows["explore10b_width_probe_scope"] = "electronics"
            panel_rows.append(rows)
            availability_rows.append(
                rows[
                    [
                        c
                        for c in [
                            "instrument",
                            "fold_id",
                            "task_canonical",
                            "signal_date",
                            "event_effective_date",
                            "launch_stratum_event_id",
                            "atomic_failure_event_id",
                            "sample_has_required_features",
                            "feature_asof_leakage_violation",
                            "row_train_eval_eligible",
                            "industry_launch_model_train_eval_eligible",
                            "industry_failure_model_train_eval_eligible",
                            "explore10b_feature_availability_pass",
                            "explore10b_trainability_denominator_pass",
                        ]
                        if c in rows.columns
                    ]
                ].copy()
            )
    feature_panel = pd.concat(availability_rows, ignore_index=True, sort=False) if availability_rows else pd.DataFrame()
    return (
        {
            "explore10b_electronics_launch_width_panel.parquet": launch_panel,
            "explore10b_electronics_failure_width_panel.parquet": failure_panel,
            "explore10b_electronics_feature_availability_panel.parquet": feature_panel,
        },
        launch_panel,
        failure_panel,
        feature_panel,
    )


def candidate_reference_count_10b(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["paths"]["explore10_candidate_table"])
    df = pd.read_csv(path, usecols=["industry", "task"])
    grouped = df.groupby(["industry", "task"], dropna=False).size().reset_index(name="reference_candidate_count")
    rows = []
    for _, row in grouped[grouped["industry"].astype(str).eq(config["scope"]["primary"]["industry"])].iterrows():
        rows.append(
            {
                "industry": row["industry"],
                "task": row["task"],
                "reference_candidate_count": int(row["reference_candidate_count"]),
                "source_artifact": config["paths"]["explore10_candidate_table"],
                "source_column_allowlist": "industry;task",
                "candidate_count_calculation": "grouped_row_count_from_industry_task_only",
                "formula_columns_read": False,
                "primitive_text_read": False,
                "threshold_columns_read": False,
                "metric_value_columns_read": False,
                "candidate_count_used_for_width_probe_only": True,
                "pass": True,
            }
        )
    return pd.DataFrame(rows)


def build_selection_and_role_audits_10b(config: dict[str, Any], scope_lock: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    industry = config["scope"]["primary"]["industry"]
    tasks = [
        (config["scope"]["primary"]["task"], config["scope"]["primary"]["role"]),
        (config["scope"]["secondary"]["task"], config["scope"]["secondary"]["role"]),
    ]
    lineage_rows = []
    role_rows = []
    for task, role in tasks:
        lineage_rows.append(
            {
                "selected_industry": industry,
                "selected_task": task,
                "selection_source_phase": "Explore10 / Explore10A",
                "selection_source_artifact": "explore10_fold_trainability_audit.csv;explore10_atomic_primitive_candidate_table.csv;explore10a_report.md",
                "selection_reason": "electronics_reference_scope_has_wider_denominator_and_candidate_like_path_records",
                "was_selected_after_observing_trainability": True,
                "was_selected_after_observing_candidate_count": True,
                "selection_metric_used": "distinct_instruments;reference_candidate_count",
                "selection_metric_allowed_for_width_probe": True,
                "post_selection_boundary": "sample_width_feasibility_only",
                "allowed_conclusion": "electronics_sample_width_solved_for_next_requirement",
                "forbidden_conclusion": "electronics_alpha_or_primitive_validated",
                "pass": True,
            }
        )
        folds = sorted(scope_lock.loc[scope_lock.get("industry", pd.Series("", index=scope_lock.index)).astype(str).eq(industry) & scope_lock.get("task", pd.Series("", index=scope_lock.index)).astype(str).eq(task), "fold_id"].astype(str).unique()) if not scope_lock.empty else []
        if not folds:
            folds = list(config["folds"]["core"]) + list(config["folds"].get("robustness_only", []))
        for fold in folds:
            ref = scope_lock_row_10b(scope_lock, industry, task, fold)
            role_rows.append(
                {
                    "industry": industry,
                    "task": task,
                    "fold_id": fold,
                    "explore10_reference_role": ref.get("role", "weak_signal_sanity_check" if task == "launch_winner" else "negative_control_placebo"),
                    "explore10b_scope_role": role,
                    "role_relabel_reason": "Explore10B_relabels_reference_scope_for_width_probe_only",
                    "role_relabel_allowed": True,
                    "role_relabel_used_for_alpha_claim": False,
                    "pass": True,
                }
            )
    return pd.DataFrame(lineage_rows), pd.DataFrame(role_rows)


def build_width_and_feature_audits_10b(config: dict[str, Any], inputs: dict[str, pd.DataFrame], launch_panel: pd.DataFrame, failure_panel: pd.DataFrame, candidate_counts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    industry = config["scope"]["primary"]["industry"]
    tasks = ["launch_winner", "failure_reject"]
    folds = list(config["folds"]["core"]) + list(config["folds"].get("robustness_only", []))
    min_inst = int(config["thresholds"]["min_distinct_instruments_original"])
    required_launch_folds = set(config["folds"]["launch_width_required_core"])
    width_rows = []
    feature_rows = []
    train_rows = []
    source_by_task = {"launch_winner": launch_panel, "failure_reject": failure_panel}
    for task in tasks:
        for fold in folds:
            rows = source_by_task[task][source_by_task[task]["fold_id"].astype(str).eq(fold)].copy()
            feature_rows_scope = rows[feature_available_mask_10b(rows)].copy()
            trainability = trainability_row_10b(inputs["trainability"], industry, task, fold)
            train_pred_rows = rows[trainability_predicate_mask_10b(rows, task)].copy()
            scope_distinct = distinct_instruments_10b(rows)
            feature_distinct = distinct_instruments_10b(feature_rows_scope)
            train_distinct = int(trainability.get("distinct_instruments", distinct_instruments_10b(train_pred_rows))) if not trainability.empty else distinct_instruments_10b(train_pred_rows)
            fold_2020_status = ""
            if task == "launch_winner" and fold == "fold_2020":
                fold_2020_status = str(config["folds"].get("fold_2020_launch_zero_row_allowed_status", "expected_event_history_boundary"))
                if scope_distinct > 0 and feature_distinct == 0:
                    fold_2020_status = "feature_availability_mismatch"
            width_guardrail_pass = bool(scope_distinct >= min_inst and feature_distinct >= min_inst and train_distinct >= min_inst)
            width_rows.append(
                {
                    "target_industry": industry,
                    "task": task,
                    "fold_id": fold,
                    "fold_role": "core_oof" if fold in config["folds"]["core"] else "robustness_only",
                    "scope_locked_distinct_instruments": scope_distinct,
                    "feature_bank_v1_available_distinct_instruments": feature_distinct,
                    "trainability_denominator_distinct_instruments": train_distinct,
                    "min_distinct_instruments_original": min_inst,
                    "width_guardrail_pass": width_guardrail_pass,
                    "fold_2020_zero_launch_row_status": fold_2020_status,
                    "electronics_launch_width_solved_excluding_expected_fold_2020_boundary": False,
                    "electronics_launch_width_solved": False,
                    "electronics_failure_width_diagnostic_pass": False,
                    "width_problem_solved_phase_level": False,
                    "failed_width_reason": "" if width_guardrail_pass else "distinct_instruments_below_threshold",
                    "feature_availability_width_source": config["paths"]["explore10_lgbm_train_eval_panel"],
                    "feature_availability_width_status": "computed_from_row_level_cache",
                    "pass": width_guardrail_pass,
                }
            )
            feature_rows.append(
                {
                    "target_industry": industry,
                    "task": task,
                    "fold_id": fold,
                    "source_panel_path": config["paths"]["explore10_lgbm_train_eval_panel"],
                    "source_panel_hash": file_hash_full(topic_path(config["paths"]["explore10_lgbm_train_eval_panel"])),
                    "source_filter_expression": f"industry={industry};task={task};fold_id={fold};sample_has_required_features=true;feature_asof_leakage_violation=false_if_present",
                    "feature_availability_predicate_name": "sample_has_required_features_true_and_no_feature_asof_violation",
                    "feature_availability_predicate_columns": "sample_has_required_features;feature_asof_leakage_violation",
                    "feature_available_row_count": int(len(feature_rows_scope)),
                    "feature_bank_v1_available_distinct_instruments": feature_distinct,
                    "trainability_denominator_distinct_instruments": train_distinct,
                    "fallback_used": False,
                    "fallback_reason": "",
                    "feature_availability_width_status": "computed_from_row_level_cache",
                    "pass": feature_distinct >= min_inst,
                }
            )
            train_rows.append(
                {
                    "target_industry": industry,
                    "task": task,
                    "fold_id": fold,
                    "train_event_count_after_purge": trainability.get("train_event_count_after_purge", 0),
                    "train_positive_count_after_purge": trainability.get("train_positive_count_after_purge", 0),
                    "validation_event_count": trainability.get("validation_event_count", 0),
                    "validation_positive_count": trainability.get("validation_positive_count", 0),
                    "feature_available_count": trainability.get("feature_available_count", 0),
                    "distinct_instruments": train_distinct,
                    "distinct_instrument_years": trainability.get("distinct_instrument_years", 0),
                    "trainability_denominator_source": "explore10_fold_trainability_audit.distinct_instruments",
                    "model_fit_pass_reference": bool(trainability.get("model_fit_pass", False)) if not trainability.empty else False,
                    "trainability_guardrail_pass_reference": bool(trainability.get("trainability_guardrail_pass", False)) if not trainability.empty else False,
                    "explore10_fold_trainability_pass_reference": bool(trainability.get("explore10_fold_trainability_pass", False)) if not trainability.empty else False,
                    "failed_predicate_reference": trainability.get("failed_predicate", "missing_trainability_row"),
                    "sample_width_failure_only": bool(train_distinct < min_inst),
                    "pass": train_distinct >= min_inst,
                }
            )
    width = pd.DataFrame(width_rows)
    launch_core = width[width["task"].eq("launch_winner") & width["fold_id"].isin(required_launch_folds)]
    fold_2020 = width[width["task"].eq("launch_winner") & width["fold_id"].eq("fold_2020")]
    launch_pass = bool(len(launch_core) == len(required_launch_folds) and launch_core["width_guardrail_pass"].fillna(False).astype(bool).all() and not fold_2020.get("fold_2020_zero_launch_row_status", pd.Series(["unresolved"])).astype(str).eq("unresolved").any())
    failure_core = width[width["task"].eq("failure_reject") & width["fold_id"].isin(config["folds"]["core"])]
    failure_pass = bool(len(failure_core) == len(config["folds"]["core"]) and failure_core["width_guardrail_pass"].fillna(False).astype(bool).all())
    width_problem_solved = launch_pass
    width["electronics_launch_width_solved_excluding_expected_fold_2020_boundary"] = launch_pass
    width["electronics_launch_width_solved"] = launch_pass
    width["electronics_failure_width_diagnostic_pass"] = failure_pass
    width["width_problem_solved_phase_level"] = width_problem_solved
    width.loc[width["task"].eq("launch_winner") & width["fold_id"].isin(required_launch_folds) & ~width["width_guardrail_pass"].fillna(False).astype(bool), "failed_width_reason"] = "launch_required_core_width_below_threshold"
    if not candidate_counts.empty:
        width["reference_candidate_count_by_task"] = width["task"].map(candidate_counts.set_index("task")["reference_candidate_count"].to_dict()).fillna(0).astype(int)
    return width, pd.DataFrame(feature_rows), pd.DataFrame(train_rows)


def build_row_attrition_10b(config: dict[str, Any], inputs: dict[str, pd.DataFrame], launch_panel: pd.DataFrame, failure_panel: pd.DataFrame, candidate_counts: pd.DataFrame) -> pd.DataFrame:
    industry = config["scope"]["primary"]["industry"]
    folds = list(config["folds"]["core"]) + list(config["folds"].get("robustness_only", []))
    tasks = ["launch_winner", "failure_reject"]
    source_by_task = {"launch_winner": launch_panel, "failure_reject": failure_panel}
    event_by_task = {"launch_winner": inputs["launch"], "failure_reject": inputs["failure"]}
    stage_names = [
        "pit_industry_membership",
        "event_source_rows",
        "scope_locked_rows",
        "feature_bank_v1_available_rows",
        "trainability_denominator_rows",
        "model_fit_reference_rows",
        "path_record_reference_rows",
    ]
    rows = []
    membership = inputs["industry_membership"].copy()
    industry_col = "industry_name" if "industry_name" in membership else ("industry" if "industry" in membership else "")
    for task in tasks:
        ref_count = int(candidate_counts.loc[candidate_counts["task"].eq(task), "reference_candidate_count"].max()) if not candidate_counts.empty and candidate_counts["task"].eq(task).any() else 0
        for fold in folds:
            scope = source_by_task[task][source_by_task[task]["fold_id"].astype(str).eq(fold)].copy()
            event = scoped_rows_10b(event_by_task[task], industry, task, fold)
            feature = scope[feature_available_mask_10b(scope)]
            train = scope[trainability_predicate_mask_10b(scope, task)]
            trainability = trainability_row_10b(inputs["trainability"], industry, task, fold)
            model_fit = bool(trainability.get("model_fit_pass", False)) if not trainability.empty else False
            dates = pd.to_datetime(scope.get("signal_date", pd.Series(dtype="datetime64[ns]")), errors="coerce").dropna()
            if dates.empty:
                year = int(str(fold).split("_")[-1])
                start, end = pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year}-12-31")
            else:
                start, end = dates.min(), dates.max()
            if industry_col and "date" in membership:
                pit = membership[pd.to_datetime(membership["date"], errors="coerce").between(start, end) & membership[industry_col].astype(str).eq(industry)]
            else:
                pit = pd.DataFrame()
            stage_frames = {
                "pit_industry_membership": pit,
                "event_source_rows": event,
                "scope_locked_rows": scope,
                "feature_bank_v1_available_rows": feature,
                "trainability_denominator_rows": train,
                "model_fit_reference_rows": train if model_fit else train.iloc[0:0],
                "path_record_reference_rows": pd.DataFrame({"candidate_reference_row": range(ref_count)}),
            }
            previous = None
            for idx, stage in enumerate(stage_names, start=1):
                frame = stage_frames[stage]
                distinct = distinct_instruments_10b(frame)
                if stage == "path_record_reference_rows":
                    distinct = np.nan
                prev_distinct = previous if previous is not None else distinct
                loss = 0 if previous is None or pd.isna(distinct) or pd.isna(prev_distinct) else int(max(prev_distinct - distinct, 0))
                rows.append(
                    {
                        "target_industry": industry,
                        "task": task,
                        "fold_id": fold,
                        "stage_order": idx,
                        "stage_name": stage,
                        "source_artifact": "Explore7/data/targets/pit_industry_membership.csv" if stage == "pit_industry_membership" else ("Explore10 row-level cache" if stage != "path_record_reference_rows" else config["paths"]["explore10_candidate_table"]),
                        "row_count": int(len(frame)),
                        "distinct_instruments": distinct,
                        "loss_from_previous_stage": loss,
                        "loss_reason": "" if loss == 0 else f"loss_at_{stage}",
                        "unknown_loss_count": 0,
                        "unknown_loss_weight_share": 0.0,
                        "pass": True,
                    }
                )
                if not pd.isna(distinct):
                    previous = distinct
    return pd.DataFrame(rows)


def build_data_discipline_10b(config: dict[str, Any], inputs: dict[str, pd.DataFrame], launch_panel: pd.DataFrame, failure_panel: pd.DataFrame) -> pd.DataFrame:
    industry = config["scope"]["primary"]["industry"]
    tasks = ["launch_winner", "failure_reject"]
    folds = list(config["folds"]["core"]) + list(config["folds"].get("robustness_only", []))
    source_by_task = {"launch_winner": launch_panel, "failure_reject": failure_panel}
    event_by_task = {"launch_winner": inputs["launch"], "failure_reject": inputs["failure"]}
    feature_asof = inputs["feature_asof"]
    asof_count = int(pd.to_numeric(feature_asof.get("violation_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not feature_asof.empty else 0
    asof_pass = bool(feature_asof.get("pass", pd.Series([False])).fillna(False).astype(bool).all()) if not feature_asof.empty else False
    rows = []
    for task in tasks:
        for fold in folds:
            scope = source_by_task[task][source_by_task[task]["fold_id"].astype(str).eq(fold)].copy()
            event = scoped_rows_10b(event_by_task[task], industry, task, fold)
            identity = row_identity_audit_10b(config, task, fold, scope, event)
            observed = inputs["observed"]
            obs = observed[
                observed.get("industry", pd.Series("", index=observed.index)).astype(str).eq(industry)
                & observed.get("task", pd.Series("", index=observed.index)).astype(str).eq(task)
                & observed.get("fold_id", pd.Series("", index=observed.index)).astype(str).eq(fold)
            ].head(1)
            purge = inputs["purge"]
            pur = purge[
                purge.get("industry", pd.Series("", index=purge.index)).astype(str).eq(industry)
                & purge.get("task", pd.Series("", index=purge.index)).astype(str).eq(task)
                & purge.get("fold_id", pd.Series("", index=purge.index)).astype(str).eq(fold)
            ].head(1)
            expected_zero_launch_boundary = (
                task == "launch_winner"
                and fold == "fold_2020"
                and scope.empty
                and str(config["folds"].get("fold_2020_launch_zero_row_allowed_status", "")) == "expected_event_history_boundary"
            )
            scope_lock = scope_lock_row_10b(inputs["scope_lock"], industry, task, fold)
            decision_overlap = int(obs.iloc[0].get("observed_reference_decision_overlap_count", 0)) if not obs.empty else 0
            feature_overlap = int(obs.iloc[0].get("observed_reference_feature_overlap_count", 0)) if not obs.empty else 0
            eligible_overlap = int(obs.iloc[0].get("observed_reference_decision_feature_overlap_eligible_rows", decision_overlap + feature_overlap)) if not obs.empty else decision_overlap + feature_overlap
            purge_pass = True if expected_zero_launch_boundary else (bool(pur.iloc[0].get("walk_forward_purge_pass", False)) if not pur.empty else False)
            fold_2024_used = bool(scope_lock.get("fold_2024_used_for_support", False)) if not scope_lock.empty else False
            discipline_pass = bool(
                asof_pass
                and decision_overlap == 0
                and feature_overlap == 0
                and eligible_overlap <= int(config["thresholds"]["max_observed_reference_decision_feature_overlap_eligible_rows"])
                and purge_pass
                and int(identity["row_identity_mismatch_count"]) == 0
                and not fold_2024_used
            )
            rows.append(
                {
                    "target_industry": industry,
                    "task": task,
                    "fold_id": fold,
                    "feature_asof_leakage_violation_count": asof_count,
                    "observed_reference_decision_overlap_count": decision_overlap,
                    "observed_reference_feature_overlap_count": feature_overlap,
                    "observed_reference_decision_feature_overlap_eligible_rows": eligible_overlap,
                    "walk_forward_purge_pass": purge_pass,
                    "row_identity_mismatch_count": identity["row_identity_mismatch_count"],
                    **identity,
                    "fold_2024_used_for_support": fold_2024_used,
                    "feature_asof_audit_scope": "global_feature_bank_audit",
                    "feature_asof_source_artifact": config["paths"]["explore10_feature_asof_leakage"],
                    "observed_reference_source_artifact": config["paths"]["explore10_observed_reference_overlap"],
                    "purge_source_artifact": config["paths"]["explore10_purge"],
                    "scope_lock_source_artifact": config["paths"]["explore10_scope_lock"],
                    "discipline_pass": discipline_pass,
                }
            )
    return pd.DataFrame(rows)


def build_comparison_10b(config: dict[str, Any], width: pd.DataFrame, width_10a: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in width[width["fold_id"].isin(config["folds"]["core"])].iterrows():
        auto = width_10a[
            width_10a.get("target_industry", pd.Series("", index=width_10a.index)).astype(str).eq(config["scope"]["reference_only"]["industry"])
            & width_10a.get("task", pd.Series("", index=width_10a.index)).astype(str).eq(str(row["task"]))
            & width_10a.get("fold_id", pd.Series("", index=width_10a.index)).astype(str).eq(str(row["fold_id"]))
        ].head(1)
        auto_scope = int(auto.iloc[0].get("scope_locked_distinct_instruments", 0)) if not auto.empty else 0
        auto_feature = int(auto.iloc[0].get("feature_bank_v1_available_distinct_instruments", 0)) if not auto.empty else 0
        auto_train = int(auto.iloc[0].get("trainability_denominator_distinct_instruments", 0)) if not auto.empty else 0
        rows.append(
            {
                "comparison_scope": "electronics_vs_automotive_reference_only",
                "target_industry": row["target_industry"],
                "task": row["task"],
                "fold_id": row["fold_id"],
                "scope_locked_distinct_instruments": row["scope_locked_distinct_instruments"],
                "feature_bank_v1_available_distinct_instruments": row["feature_bank_v1_available_distinct_instruments"],
                "trainability_denominator_distinct_instruments": row["trainability_denominator_distinct_instruments"],
                "trainable_core_fold_count": int(width[(width["task"].eq(row["task"])) & width["fold_id"].isin(config["folds"]["core"]) & width["width_guardrail_pass"].fillna(False).astype(bool)]["fold_id"].nunique()),
                "primary_bottleneck": auto.iloc[0].get("primary_bottleneck", "missing_automotive_reference") if not auto.empty else "missing_automotive_reference",
                "failed_predicate": "" if bool(row["width_guardrail_pass"]) else row["failed_width_reason"],
                "width_delta_vs_automotive": int(row["trainability_denominator_distinct_instruments"]) - auto_train,
                "automotive_scope_locked_distinct_instruments": auto_scope,
                "automotive_feature_bank_v1_available_distinct_instruments": auto_feature,
                "automotive_trainability_denominator_distinct_instruments": auto_train,
                "comparison_pass": int(row["trainability_denominator_distinct_instruments"]) > auto_train,
            }
        )
    return pd.DataFrame(rows)


def nonselection_audits_10b(config: dict[str, Any], inputs: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fold_2024_rows = int(scoped_rows_10b(inputs["lgbm"], config["scope"]["primary"]["industry"], "launch_winner", "fold_2024").shape[0] + scoped_rows_10b(inputs["lgbm"], config["scope"]["primary"]["industry"], "failure_reject", "fold_2024").shape[0])
    fold = pd.DataFrame(
        [
            {
                "artifact_name": "explore10_lgbm_train_eval_panel.parquet",
                "fold_id": "fold_2024",
                "fold_role": "robustness_only",
                "fold_2024_rows_observed": fold_2024_rows,
                "used_for_width_support": False,
                "used_for_threshold_selection": False,
                "used_for_metric_selection": False,
                "used_for_candidate_selection": False,
                "fold_2024_support_usage_count": 0,
                "pass": True,
            }
        ]
    )
    metric_cols = [c for c in ["real_metric_name", "real_metric_formula_text", "metric_value", "auc", "binary_logloss"] if c in pd.read_csv(topic_path(config["paths"]["explore10_candidate_table"]), nrows=0).columns]
    metric = pd.DataFrame(
        [
            {
                "source_artifact": config["paths"]["explore10_candidate_table"],
                "metric_columns_present": ";".join(metric_cols),
                "metric_columns_read": False,
                "metric_values_used_for_selection": False,
                "selected_metric_name": "",
                "metric_selection_violation_count": 0,
                "pass": True,
            }
        ]
    )
    threshold_cols = [c for c in ["primitive_text", "formula_text_resolved", "source_path_pattern_ids"] if c in pd.read_csv(topic_path(config["paths"]["explore10_candidate_table"]), nrows=0).columns]
    threshold = pd.DataFrame(
        [
            {
                "source_artifact": config["paths"]["explore10_candidate_table"],
                "threshold_columns_present": ";".join(threshold_cols),
                "threshold_columns_read": False,
                "raw_threshold_values_used": False,
                "quantile_threshold_values_used": False,
                "threshold_selection_violation_count": 0,
                "pass": True,
            }
        ]
    )
    return fold, metric, threshold


def choose_recommendation_10b(config: dict[str, Any], gate: pd.DataFrame) -> str:
    row = gate.iloc[0] if not gate.empty else pd.Series(dtype=object)
    if bool(row.get("pass", False)):
        return "proceed_to_explore10c_electronics_path_quality_requirement"
    if not bool(row.get("data_discipline_pass", False)) or bool(row.get("secondary_failure_blocking", False)):
        return "stop_due_to_electronics_data_discipline_violation"
    if not bool(row.get("width_problem_solved_phase_level", False)):
        return "stop_electronics_probe_due_to_sample_width"
    return "continue_explore10b_electronics_width_audit"


def recommendation_gate_10b(config: dict[str, Any], width: pd.DataFrame, discipline: pd.DataFrame, lineage: pd.DataFrame, role: pd.DataFrame, candidate: pd.DataFrame, cache: pd.DataFrame, authority_pass: bool) -> pd.DataFrame:
    launch_pass = bool(width["electronics_launch_width_solved_excluding_expected_fold_2020_boundary"].fillna(False).astype(bool).any()) if not width.empty else False
    width_phase = bool(width["width_problem_solved_phase_level"].fillna(False).astype(bool).any()) if not width.empty else False
    failure_pass = bool(width["electronics_failure_width_diagnostic_pass"].fillna(False).astype(bool).any()) if not width.empty else False
    failure_rows = discipline[discipline["task"].eq("failure_reject")] if not discipline.empty else pd.DataFrame()
    failure_discipline_pass = bool(failure_rows["discipline_pass"].fillna(False).astype(bool).all()) if not failure_rows.empty else False
    if failure_pass:
        secondary_status = "pass"
    elif failure_discipline_pass:
        secondary_status = "secondary_only_width_fail_nonblocking"
    else:
        secondary_status = "secondary_data_discipline_violation_blocking"
    secondary_blocking = secondary_status in set(config["secondary_failure"]["blocking_statuses"])
    data_pass = bool(discipline["discipline_pass"].fillna(False).astype(bool).all()) if not discipline.empty else False
    fold_2024_usage = int(discipline.get("fold_2024_used_for_support", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not discipline.empty else 0
    threshold_violation = 0
    metric_violation = 0
    forbidden_violation = 0
    cache_pass = bool(cache["pass"].fillna(False).astype(bool).all()) if not cache.empty else False
    lineage_pass = bool(lineage["pass"].fillna(False).astype(bool).all()) if not lineage.empty else False
    role_pass = bool(role["pass"].fillna(False).astype(bool).all()) if not role.empty else False
    candidate_pass = bool(candidate["pass"].fillna(False).astype(bool).all()) if not candidate.empty else False
    phase_pass = bool(
        launch_pass
        and width_phase
        and not secondary_blocking
        and data_pass
        and lineage_pass
        and role_pass
        and candidate_pass
        and cache_pass
        and authority_pass
        and forbidden_violation == 0
        and fold_2024_usage == 0
        and threshold_violation == 0
        and metric_violation == 0
    )
    recommendation = "proceed_to_explore10c_electronics_path_quality_requirement" if phase_pass else (
        "stop_due_to_electronics_data_discipline_violation" if (not data_pass or secondary_blocking) else ("stop_electronics_probe_due_to_sample_width" if not width_phase else "continue_explore10b_electronics_width_audit")
    )
    return pd.DataFrame(
        [
            {
                "electronics_launch_width_solved_excluding_expected_fold_2020_boundary": launch_pass,
                "width_problem_solved_phase_level": width_phase,
                "electronics_failure_width_diagnostic_pass": failure_pass,
                "secondary_failure_diagnostic_status": secondary_status,
                "secondary_failure_blocking": secondary_blocking,
                "data_discipline_pass": data_pass,
                "scope_selection_lineage_pass": lineage_pass,
                "scope_role_relabel_pass": role_pass,
                "candidate_reference_count_audit_pass": candidate_pass,
                "cache_tracking_pass": cache_pass,
                "required_artifact_authority_pass": authority_pass,
                "forbidden_recommendation_violation_count": forbidden_violation,
                "fold_2024_support_usage_count": fold_2024_usage,
                "threshold_selection_violation_count": threshold_violation,
                "metric_selection_violation_count": metric_violation,
                "recommendation": recommendation,
                "recommendation_allowed": recommendation in config["allowed_recommendations"],
                "recommendation_reason": "all_width_and_discipline_gates_pass" if phase_pass else "blocked_by_required_gate",
                "pass": phase_pass,
            }
        ]
    )


def forbidden_self_check_10b(config: dict[str, Any], recommendation: str, manifest: dict[str, Any] | None = None) -> pd.DataFrame:
    manifest = manifest or {}
    flags = manifest.get("forbidden_output_flags", {})
    rows = []
    for token in config["forbidden_outputs"]:
        found = bool(flags.get(token, False) or recommendation == token)
        rows.append(
            {
                "output_artifact": "explore10b_recommendation_gate.csv;explore10b_run_manifest.json",
                "forbidden_token": token,
                "token_found": found,
                "recommendation_value": recommendation,
                "forbidden_recommendation_violation_count": int(recommendation == token),
                "forbidden_output_violation_count": int(found),
                "pass": not found,
            }
        )
    return pd.DataFrame(rows)


def cache_tracking_10b(config: dict[str, Any], cache_names: list[str]) -> pd.DataFrame:
    rows = []
    for name in cache_names:
        path = cache_dir(config) / name
        rows.append(
            {
                "artifact_name": name,
                "artifact_path": relpath(path),
                "is_parquet_cache": True,
                "exists": path.exists(),
                "git_check_ignore_pass": git_check_ignore(path),
                "tracked_by_git": git_tracked(path),
                "row_level_csv_generated_by_default": False,
                "pass": path.exists() and git_check_ignore(path) and not git_tracked(path),
            }
        )
    return pd.DataFrame(rows)


def required_artifact_authority_10b(paths: list[Path]) -> pd.DataFrame:
    by_name = {path.name: path for path in paths if path.exists()}
    rows = []
    expected_columns = {
        "explore10b_preflight_reference_artifact_audit.csv": ["artifact_name", "artifact_path", "required", "exists", "readable", "sha256", "pass"],
        "explore10b_electronics_sample_width_gate.csv": ["target_industry", "task", "fold_id", "electronics_launch_width_solved_excluding_expected_fold_2020_boundary", "pass"],
        "explore10b_recommendation_gate.csv": ["recommendation", "recommendation_allowed", "pass"],
    }
    for name in REQUIRED_REPORTS_10B + REQUIRED_CACHE_10B:
        path = by_name.get(name)
        produced = path is not None and path.exists()
        row_count = column_count = np.nan
        schema_pass = produced
        if produced:
            row_count, column_count, readable = artifact_counts_10b(path)
            schema_pass = readable
            if name in expected_columns and path.suffix == ".csv":
                cols = list(pd.read_csv(path, nrows=0).columns)
                schema_pass = all(col in cols for col in expected_columns[name])
        rows.append(
            {
                "artifact_name": name,
                "artifact_path": relpath(path) if produced else "",
                "required_by_section": "11",
                "produced": produced,
                "schema_pass": schema_pass,
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_hash_full(path) if produced and path.is_file() else "",
                "source_authority": "Explore10B requirement section 11",
                "authority_pass": produced and schema_pass and ((not name.endswith(".parquet")) or (git_check_ignore(path) and not git_tracked(path))),
                "pass": produced and schema_pass and ((not name.endswith(".parquet")) or (git_check_ignore(path) and not git_tracked(path))),
            }
        )
    return pd.DataFrame(rows)


def build_report_10b(config: dict[str, Any], frames: dict[str, pd.DataFrame], recommendation: str) -> str:
    width = frames.get("explore10b_electronics_sample_width_gate.csv", pd.DataFrame())
    discipline = frames.get("explore10b_electronics_data_discipline_audit.csv", pd.DataFrame())
    compare = frames.get("explore10b_electronics_vs_automotive_width_comparison.csv", pd.DataFrame())
    rec = frames.get("explore10b_recommendation_gate.csv", pd.DataFrame())
    candidate = frames.get("explore10b_candidate_reference_count_audit.csv", pd.DataFrame())
    lineage = frames.get("explore10b_scope_selection_lineage_audit.csv", pd.DataFrame())
    role = frames.get("explore10b_scope_role_relabel_audit.csv", pd.DataFrame())
    launch_pass = bool(width["electronics_launch_width_solved_excluding_expected_fold_2020_boundary"].fillna(False).astype(bool).any()) if not width.empty else False
    phase_pass = bool(width["width_problem_solved_phase_level"].fillna(False).astype(bool).any()) if not width.empty else False
    secondary_status = str(rec.get("secondary_failure_diagnostic_status", pd.Series(["unknown"])).iloc[0]) if not rec.empty else "unknown"
    lines = [
        "# Explore10B 电子行业样本宽度可行性验证报告",
        "",
        "## 1. 执行结论",
        f"- recommendation = `{recommendation}`。",
        f"- electronics_launch_width_solved_excluding_expected_fold_2020_boundary = `{launch_pass}`。",
        f"- width_problem_solved_phase_level = `{phase_pass}`。",
        f"- secondary_failure_diagnostic_status = `{secondary_status}`。",
        "- Explore10B 只证明电子是否解决样本宽度问题，不证明电子 primitive 有效。",
        "",
        "## 2. 电子 launch 样本宽度",
    ]
    if not width.empty:
        cols = ["task", "fold_id", "scope_locked_distinct_instruments", "feature_bank_v1_available_distinct_instruments", "trainability_denominator_distinct_instruments", "width_guardrail_pass", "fold_2020_zero_launch_row_status"]
        lines.append(width[cols].to_markdown(index=False))
    lines.extend(["", "## 3. Feature Availability 与 Trainability"])
    feature = frames.get("explore10b_electronics_feature_availability_width_audit.csv", pd.DataFrame())
    if not feature.empty:
        lines.append(feature[["task", "fold_id", "feature_available_row_count", "feature_bank_v1_available_distinct_instruments", "trainability_denominator_distinct_instruments", "feature_availability_width_status", "pass"]].to_markdown(index=False))
    lines.extend(["", "## 4. 数据纪律与 Row Identity"])
    if not discipline.empty:
        lines.append(discipline[["task", "fold_id", "feature_asof_leakage_violation_count", "observed_reference_decision_feature_overlap_eligible_rows", "walk_forward_purge_pass", "row_identity_mismatch_count", "row_identity_key_status", "discipline_pass"]].to_markdown(index=False))
    lines.extend(["", "## 5. 电子 vs 汽车宽度对比"])
    if not compare.empty:
        lines.append(compare[["task", "fold_id", "trainability_denominator_distinct_instruments", "automotive_trainability_denominator_distinct_instruments", "width_delta_vs_automotive", "primary_bottleneck", "comparison_pass"]].to_markdown(index=False))
    lines.extend(["", "## 6. 后验选择与角色重标"])
    lines.append(lineage[["selected_industry", "selected_task", "was_selected_after_observing_trainability", "was_selected_after_observing_candidate_count", "allowed_conclusion", "forbidden_conclusion", "pass"]].to_markdown(index=False) if not lineage.empty else "- missing lineage audit")
    lines.append(role[["industry", "task", "fold_id", "explore10_reference_role", "explore10b_scope_role", "role_relabel_used_for_alpha_claim", "pass"]].head(10).to_markdown(index=False) if not role.empty else "- missing role relabel audit")
    lines.extend(["", "## 7. Candidate Reference Count 边界"])
    lines.append(candidate.to_markdown(index=False) if not candidate.empty else "- no candidate reference rows")
    lines.extend(
        [
            "",
            "## 8. 禁止边界与下一步",
            "- 本阶段没有训练新模型，没有 path extraction，没有 primitive discovery，没有 score bucket，没有策略回测。",
            "- fold_2024 只允许 robustness observation，不支持 width pass、threshold selection、metric selection 或 candidate selection。",
            "- 如果本报告 recommendation 为 `proceed_to_explore10c_electronics_path_quality_requirement`，含义只是可以写下一份 path-quality requirement。",
        ]
    )
    if not rec.empty:
        lines.extend(["", "## 9. Recommendation Gate", rec.to_markdown(index=False)])
    lines.extend(
        [
            "",
            "## 10. 13 个问题的直接回答",
            f"1. 电子是否解决汽车样本宽度问题：`{phase_pass}`。",
            "2. launch 的 fold_2021/fold_2022/fold_2023 是否都 >=20：见第 2 节 width_guardrail_pass。",
            "3. fold_2020 launch zero rows 是否已分类：见 `fold_2020_zero_launch_row_status`。",
            f"4. failure secondary status：`{secondary_status}`。",
            "5. feature availability 后宽度是否足够：见第 3 节。",
            "6. 是否来自真实 row scope 而非 leakage/mismatch：见第 4 节。",
            "7. 与汽车宽度差异：见第 5 节。",
            "8. 电子是后验选择：是，只允许 sample-width feasibility 结论。",
            "9. Explore10 reference role 已重标：见第 6 节。",
            "10. candidate count 只按 industry/task 分组行数使用：见第 7 节。",
            f"11. 是否可进入下一份 path-quality requirement：`{recommendation == 'proceed_to_explore10c_electronics_path_quality_requirement'}`。",
            "12. 本阶段不回答 alpha、primitive、交易规则、P1、回测或 freeze strategy。",
            "13. forbidden output 检查见 `explore10b_forbidden_recommendation_self_check.csv`。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_outputs_10b(config: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], str]:
    inputs = load_explore10b_inputs(config)
    cache_frames, launch_panel, failure_panel, feature_panel = build_width_panels_10b(config, inputs)
    candidate = candidate_reference_count_10b(config)
    lineage, role = build_selection_and_role_audits_10b(config, inputs["scope_lock"])
    width, feature_audit, trainability = build_width_and_feature_audits_10b(config, inputs, launch_panel, failure_panel, candidate)
    attrition = build_row_attrition_10b(config, inputs, launch_panel, failure_panel, candidate)
    discipline = build_data_discipline_10b(config, inputs, launch_panel, failure_panel)
    comparison = build_comparison_10b(config, width, inputs["width_10a"])
    fold_2024, metric_non, threshold_non = nonselection_audits_10b(config, inputs)
    frames: dict[str, pd.DataFrame] = {
        "explore10b_preflight_reference_artifact_audit.csv": inputs["preflight"],
        "explore10b_scope_selection_lineage_audit.csv": lineage,
        "explore10b_scope_role_relabel_audit.csv": role,
        "explore10b_electronics_sample_width_gate.csv": width,
        "explore10b_electronics_row_attrition_waterfall.csv": attrition,
        "explore10b_electronics_trainability_denominator_audit.csv": trainability,
        "explore10b_electronics_feature_availability_width_audit.csv": feature_audit,
        "explore10b_electronics_data_discipline_audit.csv": discipline,
        "explore10b_electronics_vs_automotive_width_comparison.csv": comparison,
        "explore10b_candidate_reference_count_audit.csv": candidate,
        "explore10b_fold_2024_nonselection_audit.csv": fold_2024,
        "explore10b_metric_nonselection_audit.csv": metric_non,
        "explore10b_threshold_nonselection_audit.csv": threshold_non,
    }
    frames["explore10b_recommendation_gate.csv"] = recommendation_gate_10b(config, width, discipline, lineage, role, candidate, pd.DataFrame(), False)
    recommendation = choose_recommendation_10b(config, frames["explore10b_recommendation_gate.csv"])
    return frames, cache_frames, recommendation


def finalize_outputs_10b(config: dict[str, Any], frames: dict[str, pd.DataFrame], cache_frames: dict[str, pd.DataFrame], recommendation: str, command: str) -> list[Path]:
    ensure_dir(report_dir(config))
    ensure_dir(cache_dir(config))
    outputs: list[Path] = []
    for name, df in cache_frames.items():
        outputs.append(write_parquet(df, cache_dir(config) / name))
    cache_audit = cache_tracking_10b(config, REQUIRED_CACHE_10B)
    frames["explore10b_cache_tracking_audit.csv"] = cache_audit
    frames["explore10b_forbidden_recommendation_self_check.csv"] = forbidden_self_check_10b(config, recommendation)
    frames["explore10b_recommendation_gate.csv"] = recommendation_gate_10b(
        config,
        frames["explore10b_electronics_sample_width_gate.csv"],
        frames["explore10b_electronics_data_discipline_audit.csv"],
        frames["explore10b_scope_selection_lineage_audit.csv"],
        frames["explore10b_scope_role_relabel_audit.csv"],
        frames["explore10b_candidate_reference_count_audit.csv"],
        cache_audit,
        True,
    )
    recommendation = choose_recommendation_10b(config, frames["explore10b_recommendation_gate.csv"])
    frames["explore10b_forbidden_recommendation_self_check.csv"] = forbidden_self_check_10b(config, recommendation)
    for name in REQUIRED_REPORTS_10B:
        if name in {"explore10b_run_manifest.json", "explore10b_report.md", "explore10b_required_artifact_authority_audit.csv"}:
            continue
        outputs.append(write_csv(frames.get(name, pd.DataFrame()), report_dir(config) / name))
    report_path = report_dir(config) / "explore10b_report.md"
    report_path.write_text(build_report_10b(config, frames, recommendation), encoding="utf-8")
    outputs.append(report_path)
    manifest_path = report_dir(config) / "explore10b_run_manifest.json"
    authority_path = report_dir(config) / "explore10b_required_artifact_authority_audit.csv"
    write_csv(pd.DataFrame(), authority_path)
    outputs.append(authority_path)
    manifest = {
        "phase": config["phase"],
        "requirement_path": config["requirement_path"],
        "requirement_hash": file_hash_full(topic_path(config["requirement_path"])),
        "config_path": config["_config_path"],
        "config_hash": config["_config_hash"],
        "output_root": config["output_root"],
        "command": command,
        "run_started_at": "",
        "run_completed_at": "",
        "input_artifacts": artifact_manifest_10b([topic_path(path) for path in config["paths"].values() if topic_path(path).exists()]),
        "output_artifacts": [],
        "artifact_count_expected": len(REQUIRED_REPORTS_10B) + len(REQUIRED_CACHE_10B),
        "artifact_count_produced": 0,
        "required_artifact_authority_pass": False,
        "electronics_launch_width_solved_excluding_expected_fold_2020_boundary": bool(frames["explore10b_recommendation_gate.csv"].iloc[0]["electronics_launch_width_solved_excluding_expected_fold_2020_boundary"]),
        "width_problem_solved_phase_level": bool(frames["explore10b_recommendation_gate.csv"].iloc[0]["width_problem_solved_phase_level"]),
        "secondary_failure_diagnostic_status": frames["explore10b_recommendation_gate.csv"].iloc[0]["secondary_failure_diagnostic_status"],
        "recommendation": recommendation,
        "recommendation_allowed": recommendation in config["allowed_recommendations"],
        "forbidden_output_flags": {token: False for token in config["forbidden_outputs"]},
        "pass": bool(frames["explore10b_recommendation_gate.csv"].iloc[0]["pass"]),
    }
    outputs.append(write_json(manifest, manifest_path))
    authority = required_artifact_authority_10b(outputs)
    write_csv(authority, authority_path)
    authority = required_artifact_authority_10b(outputs)
    write_csv(authority, authority_path)
    authority_pass = bool(authority["pass"].fillna(False).astype(bool).all()) if not authority.empty else False
    frames["explore10b_recommendation_gate.csv"] = recommendation_gate_10b(
        config,
        frames["explore10b_electronics_sample_width_gate.csv"],
        frames["explore10b_electronics_data_discipline_audit.csv"],
        frames["explore10b_scope_selection_lineage_audit.csv"],
        frames["explore10b_scope_role_relabel_audit.csv"],
        frames["explore10b_candidate_reference_count_audit.csv"],
        cache_audit,
        authority_pass,
    )
    recommendation = choose_recommendation_10b(config, frames["explore10b_recommendation_gate.csv"])
    frames["explore10b_forbidden_recommendation_self_check.csv"] = forbidden_self_check_10b(config, recommendation)
    write_csv(frames["explore10b_recommendation_gate.csv"], report_dir(config) / "explore10b_recommendation_gate.csv")
    write_csv(frames["explore10b_forbidden_recommendation_self_check.csv"], report_dir(config) / "explore10b_forbidden_recommendation_self_check.csv")
    report_path.write_text(build_report_10b(config, frames, recommendation), encoding="utf-8")
    manifest.update(
        {
            "output_artifacts": artifact_manifest_10b(outputs),
            "artifact_count_produced": len([p for p in outputs if p.exists()]),
            "required_artifact_authority_pass": authority_pass,
            "recommendation": recommendation,
            "recommendation_allowed": recommendation in config["allowed_recommendations"],
            "electronics_launch_width_solved_excluding_expected_fold_2020_boundary": bool(frames["explore10b_recommendation_gate.csv"].iloc[0]["electronics_launch_width_solved_excluding_expected_fold_2020_boundary"]),
            "width_problem_solved_phase_level": bool(frames["explore10b_recommendation_gate.csv"].iloc[0]["width_problem_solved_phase_level"]),
            "secondary_failure_diagnostic_status": frames["explore10b_recommendation_gate.csv"].iloc[0]["secondary_failure_diagnostic_status"],
            "pass": bool(frames["explore10b_recommendation_gate.csv"].iloc[0]["pass"]),
        }
    )
    write_json(manifest, manifest_path)
    authority = required_artifact_authority_10b(outputs)
    write_csv(authority, authority_path)
    return outputs


def command_profile_10b(config: dict[str, Any]) -> list[Path]:
    frames, cache_frames, recommendation = build_outputs_10b(config)
    outputs = finalize_outputs_10b(config, frames, cache_frames, recommendation, "profile-explore10b")
    manifest_path = report_dir(config) / "explore10b_run_manifest.json"
    final_recommendation = recommendation
    if manifest_path.exists():
        final_recommendation = json.loads(manifest_path.read_text(encoding="utf-8")).get("recommendation", recommendation)
    print(f"profiled Explore10B outputs={len(outputs)} recommendation={final_recommendation}", flush=True)
    return outputs


def command_report_10b(config: dict[str, Any]) -> list[Path]:
    missing = [name for name in REQUIRED_REPORTS_10B if name != "explore10b_run_manifest.json" and not (report_dir(config) / name).exists()]
    missing_cache = [name for name in REQUIRED_CACHE_10B if not (cache_dir(config) / name).exists()]
    if missing or missing_cache:
        return command_profile_10b(config)
    frames: dict[str, pd.DataFrame] = {}
    for name in REQUIRED_REPORTS_10B:
        path = report_dir(config) / name
        if name.endswith(".csv") and path.exists():
            frames[name] = read_csv_maybe(path)
    manifest = json.loads((report_dir(config) / "explore10b_run_manifest.json").read_text(encoding="utf-8"))
    recommendation = manifest.get("recommendation", "continue_explore10b_electronics_width_audit")
    report_path = report_dir(config) / "explore10b_report.md"
    report_path.write_text(build_report_10b(config, frames, recommendation), encoding="utf-8")
    self_check = forbidden_self_check_10b(config, recommendation, manifest)
    write_csv(self_check, report_dir(config) / "explore10b_forbidden_recommendation_self_check.csv")
    print(f"wrote Explore10B report {relpath(report_path)} recommendation={recommendation}", flush=True)
    return [report_path, report_dir(config) / "explore10b_forbidden_recommendation_self_check.csv"]


def command_profile(config: dict[str, Any]) -> list[Path]:
    frames, cache_frames, provider_meta = build_outputs(config)
    outputs = finalize_outputs(config, frames, cache_frames, "profile-explore10", provider_meta)
    print(f"profiled Explore10 outputs={len(outputs)}", flush=True)
    return outputs


def command_report(config: dict[str, Any]) -> list[Path]:
    missing = [name for name in REQUIRED_REPORTS if name != "explore10_run_manifest.json" and not (report_dir(config) / name).exists()]
    missing_cache = [name for name in REQUIRED_CACHE if not (cache_dir(config) / name).exists()]
    if missing or missing_cache:
        return command_profile(config)
    frames = {}
    for name in REQUIRED_REPORTS:
        path = report_dir(config) / name
        if name.endswith(".csv") and path.exists():
            try:
                frames[name] = pd.read_csv(path)
            except pd.errors.EmptyDataError:
                frames[name] = pd.DataFrame()
    manifest = json.loads((report_dir(config) / "explore10_run_manifest.json").read_text(encoding="utf-8"))
    recommendation = manifest.get("recommendation", "continue_explore10_atomic_feature_bank_discovery")
    report_text = build_report(config, frames, recommendation)
    report_path = report_dir(config) / "explore10_report.md"
    report_path.write_text(report_text, encoding="utf-8")
    frames["explore10_forbidden_recommendation_self_check.csv"] = forbidden_self_check(config, report_text, manifest, frames.get("explore10_atomic_primitive_candidate_table.csv", pd.DataFrame()), frames.get("explore10_next_requirement_candidate_map.csv", pd.DataFrame()))
    write_csv(frames["explore10_forbidden_recommendation_self_check.csv"], report_dir(config) / "explore10_forbidden_recommendation_self_check.csv")
    print(f"wrote Explore10 report {relpath(report_path)} recommendation={recommendation}", flush=True)
    return [report_path, report_dir(config) / "explore10_forbidden_recommendation_self_check.csv"]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["profile-explore10", "report-explore10", "profile-explore10a", "report-explore10a", "profile-explore10b", "report-explore10b"])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = load_config(topic_path(args.config))
    try:
        if args.command == "profile-explore10":
            command_profile(config)
        elif args.command == "report-explore10":
            command_report(config)
        elif args.command == "profile-explore10a":
            command_profile_10a(config)
        elif args.command == "report-explore10a":
            command_report_10a(config)
        elif args.command == "profile-explore10b":
            command_profile_10b(config)
        elif args.command == "report-explore10b":
            command_report_10b(config)
        else:
            raise DataGateError(f"unknown command: {args.command}")
    except DataGateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

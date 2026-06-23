#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
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


RUN_ID = "12A7g_vol_scaled_label_panel_c0_separability_triage"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a7g_vol_scaled_label_panel_c0_separability_triage.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("all", "train", "validation", "robustness")
DECISION_PRECEDENCE = [
    "12A7g_blocked_input_or_lineage_failure",
    "12A7g_vol_scaled_label_drift_unresolved",
    "12A7g_c0_vol_scaled_label_separable_continue_without_event_rebuild",
    "12A7g_c0_posthoc_survivor_signal_diagnostic_only",
    "12A7g_full_universe_more_separable_start_event_cartography",
    "12A7g_baserate_only_not_separable_stop_winner_selection",
]

EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "requirement": (),
    "discussion_source": (),
    "research_plan_source": (),
    "pit_topn_400_100_executable_daily": (
        "usable_trade_date",
        "instrument",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
    ),
    "pit_topn_400_100_membership_daily": (),
    "stock_daily_qfq_dir": (),
    "global_regime_calendar": (
        "date",
        "daily_regime_bucket",
        "daily_regime_conflict_n",
        "daily_regime_conflict_flag",
    ),
    "two_stage_event_universe": (
        "meta_event_id",
        "instrument",
        "event_t0_date",
        "entry_date",
        "entry_pos",
        "entry_price",
        "path_key",
        "split",
        "board_bucket",
        "calendar_month",
        "calendar_year",
        "market_regime_bucket",
        "source_arm_is_c0",
        "stage_1_evaluable",
        "stage_1_fast_fail_target",
        "no_fast_fail_L10_H20",
        "stage_2_decision_pos",
        "stage_2_reference_pos",
        "stage_2_reference_price",
        "stage_2_path_evaluable",
        "stage_2_entry_blocked",
        "stage_2_horizon_complete_20d",
        "stage_2_horizon_complete_40d",
    ),
    "two_stage_event_targets": (
        "meta_event_id",
        "instrument",
        "split",
        "stage_1_evaluable",
        "stage_1_fast_fail_target",
        "no_fast_fail_L10_H20",
        "stage_2_path_evaluable",
    ),
    "two_stage_feature_dictionary": ("feature_name", "feature_group", "pit_status", "allowed_for_stage_1", "allowed_for_stage_2"),
    "two_stage_feature_pit_audit": ("feature_name", "pit_status"),
    "split_time_boundary_audit": (
        "eval_split",
        "train_max_event_t0_date",
        "eval_min_event_t0_date",
        "split_time_boundary_gate_pass",
    ),
    "two_stage_feature_matrix": ("meta_event_id", "instrument", "event_t0_pos", "volatility_20d", "volatility_60d"),
    "stage2_path_cache": ("path_key", "instrument", "stage_2_reference_pos", "stage_2_reference_price"),
    "manifest_12a6c": (),
    "simple_backbone_train_selection": ("rule_id", "stage1_budget_X", "feature_orientation_json"),
    "simple_backbone_operating_point_readout": ("stage", "split", "stage1_budget_X", "selected_n"),
    "direction_c_decision": ("decision_state", "selected_primary_simple_backbone_tuple", "selected_primary_X"),
    "defense_participation_decision": ("decision_state",),
    "stage1_frontier_readout": ("stage1_X", "split", "stage1_selected_n", "stage1_rank_evaluable_n"),
    "defense_participation_frontier": ("stage1_X", "split", "stage2_selected_n"),
    "simple_backbone_score_matrix": ("meta_event_id", "volatility_20d__rank_percentile", "volatility_20d__rank_status"),
    "manifest_12a7b": (),
    "manifest_12a7e": (),
    "c0_winner_enrichment_decision": ("decision_state", "input_gate_status"),
    "c0_vs_control_winner_baserate_readout": ("label_family", "readout_view", "winner_barrier", "split"),
    "winner_label_source_audit": ("arm", "label_family", "winner_barrier"),
    "enrichment_stability_slice_audit": (),
    "manifest_12a7f": (),
}

PRIMITIVE_FEATURES = [
    "ret_5d",
    "ret_10d",
    "ret_20d",
    "ret_60d",
    "volatility_20d",
    "volatility_60d",
    "distance_to_20d_high",
    "distance_to_20d_low",
    "distance_to_60d_high",
    "distance_to_60d_low",
    "trend_ma_5_20_spread",
    "trend_ma_20_60_spread",
    "max_drawdown_20d",
    "max_drawdown_60d",
    "turnover_zscore_20d",
    "stock_vs_board_20d",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A7g vol-scaled label panel and C0 separability triage.")
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
        "full_universe_split_boundary_audit": TABLE_DIR / "full_universe_split_boundary_audit.csv",
        "full_universe_primitive_feature_audit": TABLE_DIR / "full_universe_primitive_feature_audit.csv",
        "full_universe_active_band_audit": TABLE_DIR / "full_universe_active_band_audit.csv",
        "stage1_anchor_x030_reconstruction_audit": TABLE_DIR / "stage1_anchor_x030_reconstruction_audit.csv",
        "label_overlap_effective_n_audit": TABLE_DIR / "label_overlap_effective_n_audit.csv",
        "label_formula_audit": TABLE_DIR / "label_formula_audit.csv",
        "vol_scaled_label_panel_summary": TABLE_DIR / "vol_scaled_label_panel_summary.csv",
        "horizon_completeness_by_split_audit": TABLE_DIR / "horizon_completeness_by_split_audit.csv",
        "label_selection_train_audit": TABLE_DIR / "label_selection_train_audit.csv",
        "pre_registered_threshold_audit": TABLE_DIR / "pre_registered_threshold_audit.csv",
        "denominator_contract_audit": TABLE_DIR / "denominator_contract_audit.csv",
        "c0_denominator_diversity_audit": TABLE_DIR / "c0_denominator_diversity_audit.csv",
        "label_feature_construction_coupling_audit": TABLE_DIR / "label_feature_construction_coupling_audit.csv",
        "c0_label_base_rate_readout": TABLE_DIR / "c0_label_base_rate_readout.csv",
        "c0_separability_readout": TABLE_DIR / "c0_separability_readout.csv",
        "full_universe_primitive_separability_readout": TABLE_DIR / "full_universe_primitive_separability_readout.csv",
        "common_entry_anchor_recall_audit": TABLE_DIR / "common_entry_anchor_recall_audit.csv",
        "continuation_recall_cost_audit": TABLE_DIR / "continuation_recall_cost_audit.csv",
        "recall_floor_feasibility_audit": TABLE_DIR / "recall_floor_feasibility_audit.csv",
        "utility_proxy_readout": TABLE_DIR / "utility_proxy_readout.csv",
        "search_multiplicity_audit": TABLE_DIR / "search_multiplicity_audit.csv",
        "stability_slice_audit": TABLE_DIR / "stability_slice_audit.csv",
        "decision_precedence_audit": TABLE_DIR / "decision_precedence_audit.csv",
        "vol_scaled_label_separability_decision": TABLE_DIR / "vol_scaled_label_separability_decision.csv",
        "full_pit_vol_scaled_label_panel": LOCAL_CACHE_DIR / "full_pit_vol_scaled_label_panel.parquet",
        "c0_vol_scaled_label_matrix": LOCAL_CACHE_DIR / "c0_vol_scaled_label_matrix.parquet",
        "full_universe_primitive_feature_panel": LOCAL_CACHE_DIR / "full_universe_primitive_feature_panel.parquet",
        "bootstrap_replicates": LOCAL_CACHE_DIR / "bootstrap_replicates.parquet",
        "report": REPORT_DIR / "vol_scaled_label_panel_c0_separability_triage_report.md",
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
    elif suffixes.endswith(".csv.gz"):
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


def count_rows(path: Path) -> int | float:
    if not path.exists():
        return np.nan
    if path.is_dir():
        return int(sum(1 for p in path.iterdir() if p.is_file()))
    suffixes = "".join(path.suffixes)
    try:
        if suffixes.endswith(".parquet"):
            return int(pd.read_parquet(path, columns=[]).shape[0])
        if suffixes.endswith((".csv", ".csv.gz")):
            return int(sum(len(chunk) for chunk in pd.read_csv(path, chunksize=250_000, low_memory=False)))
    except Exception:
        return np.nan
    return np.nan


def date_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text[:10]


def boolish(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def bool_series(series: pd.Series) -> pd.Series:
    return series.map(boolish).fillna(False).astype(bool)


def safe_rate(num: Any, den: Any) -> float:
    den_f = float(den) if pd.notna(den) else 0.0
    if den_f == 0:
        return np.nan
    return float(num) / den_f


def finite_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    return frame.copy() if split == "all" else frame.loc[frame["split"].astype(str).eq(split)].copy()


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def build_input_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, path in resolved.items():
        required_cols = EXPECTED_INPUT_COLUMNS.get(artifact_id, ())
        read_status = "pass" if path.exists() else "missing"
        schema_status = "not_checked"
        column_count: int | float = np.nan
        row_count: int | float = np.nan
        if path.exists():
            try:
                if path.is_dir():
                    schema_status = "directory"
                    row_count = count_rows(path)
                else:
                    suffixes = "".join(path.suffixes)
                    if suffixes.endswith(".parquet"):
                        sample = pd.read_parquet(path)
                    elif suffixes.endswith((".csv", ".csv.gz")):
                        sample = pd.read_csv(path, nrows=5, low_memory=False)
                    elif suffixes.endswith((".json", ".md", ".yaml")):
                        sample = pd.DataFrame()
                    else:
                        sample = pd.DataFrame()
                    column_count = len(sample.columns) if not sample.empty or suffixes.endswith((".csv", ".csv.gz", ".parquet")) else np.nan
                    missing = sorted(set(required_cols) - set(sample.columns)) if required_cols else []
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
                    row_count = count_rows(path)
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": path_sha(path),
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": True,
            }
        )
    return pd.DataFrame(rows)


class StockDailyCache:
    def __init__(self, qfq_dir: Path):
        self.qfq_dir = qfq_dir
        self.cache: dict[str, pd.DataFrame | None] = {}

    def get(self, instrument: str) -> pd.DataFrame | None:
        if instrument in self.cache:
            return self.cache[instrument]
        path = self.qfq_dir / f"{instrument}.csv"
        if not path.exists():
            self.cache[instrument] = None
            return None
        try:
            frame = pd.read_csv(path, low_memory=False)
            keep = [col for col in ["date", "open", "high", "low", "close", "money", "turnover_rate"] if col in frame.columns]
            frame = frame[keep].copy()
            frame["date"] = frame["date"].map(date_text)
            for col in ["open", "high", "low", "close", "money", "turnover_rate"]:
                if col not in frame.columns:
                    frame[col] = np.nan
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
            frame = frame.drop_duplicates("date", keep="last").sort_values("date", kind="stable").reset_index(drop=True)
            frame["date_pos"] = np.arange(len(frame), dtype=np.int64)
            self.cache[instrument] = add_daily_features(frame)
        except Exception:
            self.cache[instrument] = None
        return self.cache[instrument]


def rolling_max_drawdown(close: pd.Series, window: int) -> pd.Series:
    values = close.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        start = max(0, i - window + 1)
        sub = values[start : i + 1]
        if len(sub) < window or not np.isfinite(sub).all():
            continue
        running_max = np.maximum.accumulate(sub)
        out[i] = np.min(sub / running_max - 1.0)
    return pd.Series(out, index=close.index)


def add_daily_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    close = finite_numeric(out["close"])
    high = finite_numeric(out["high"])
    low = finite_numeric(out["low"])
    turnover = finite_numeric(out["turnover_rate"])
    money = finite_numeric(out["money"])
    daily_ret = close.pct_change()
    out["daily_return"] = daily_ret
    for n in [5, 10, 20, 60]:
        out[f"ret_{n}d"] = close / close.shift(n) - 1.0
    for n in [20, 60]:
        out[f"volatility_{n}d"] = daily_ret.rolling(n, min_periods=n).std(ddof=0)
        out[f"distance_to_{n}d_high"] = close / high.rolling(n, min_periods=n).max() - 1.0
        out[f"distance_to_{n}d_low"] = close / low.rolling(n, min_periods=n).min() - 1.0
        out[f"max_drawdown_{n}d"] = rolling_max_drawdown(close, n)
    out["trend_ma_5_20_spread"] = close.rolling(5, min_periods=5).mean() / close.rolling(20, min_periods=20).mean() - 1.0
    out["trend_ma_20_60_spread"] = close.rolling(20, min_periods=20).mean() / close.rolling(60, min_periods=60).mean() - 1.0
    t_mean = turnover.rolling(20, min_periods=20).mean()
    t_std = turnover.rolling(20, min_periods=20).std(ddof=0)
    out["turnover_zscore_20d"] = (turnover - t_mean) / t_std.replace(0, np.nan)
    out["turnover_rate_median_20d"] = turnover.rolling(20, min_periods=20).median()
    out["money_median_20d"] = money.rolling(20, min_periods=20).median()
    out["trading_continuity_20d"] = out["close"].notna().rolling(20, min_periods=20).sum() / 20.0
    out["recent_range_activity_20d"] = high.rolling(20, min_periods=20).max() / low.rolling(20, min_periods=20).min() - 1.0
    out["intraday_range_mean_20d"] = (high / low - 1.0).rolling(20, min_periods=20).mean()
    out["entry_date"] = out["date"].shift(-1)
    out["entry_pos"] = out["date_pos"].shift(-1)
    out["entry_price"] = out["open"].shift(-1)
    return out


def primitive_features_for_rows(rows: pd.DataFrame, cache: StockDailyCache, date_col: str, *, id_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    parts: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    work = rows.copy()
    work[date_col] = work[date_col].map(date_text)
    for instrument, group in work.groupby("instrument", sort=False):
        daily = cache.get(str(instrument))
        base = group.copy()
        if daily is None or daily.empty:
            for col in ["reference_pos", "entry_pos", "entry_date", "entry_price", *PRIMITIVE_FEATURES]:
                base[col] = np.nan
            base["primitive_status"] = "missing_qfq"
            parts.append(base)
            audit_rows.append({"instrument": instrument, "requested_row_n": len(group), "matched_row_n": 0, "primitive_status": "missing_qfq"})
            continue
        feature_cols = [
            "date",
            "date_pos",
            "entry_date",
            "entry_pos",
            "entry_price",
            *[c for c in PRIMITIVE_FEATURES if c != "stock_vs_board_20d"],
            "turnover_rate_median_20d",
            "money_median_20d",
            "trading_continuity_20d",
            "recent_range_activity_20d",
            "intraday_range_mean_20d",
        ]
        feature = daily[[c for c in feature_cols if c in daily.columns]].rename(columns={"date": date_col, "date_pos": "reference_pos"})
        merged = base.merge(feature, on=date_col, how="left", sort=False, suffixes=("", "_qfq"))
        merged["primitive_status"] = np.where(merged["reference_pos"].notna(), "pass", "missing_reference_date")
        for col in ["open", "high", "low", "close"]:
            pass
        parts.append(merged)
        audit_rows.append(
            {
                "instrument": instrument,
                "requested_row_n": len(group),
                "matched_row_n": int(merged["reference_pos"].notna().sum()),
                "primitive_status": "pass" if merged["reference_pos"].notna().all() else "partial_missing_reference_date",
            }
        )
    out = pd.concat(parts, ignore_index=True) if parts else work.head(0).copy()
    if "ret_20d" in out.columns and "board_bucket" in out.columns:
        board_ret = (
            out.groupby(["board_bucket", date_col], dropna=False)["ret_20d"]
            .mean()
            .rename("board_return_20d")
            .reset_index()
        )
        out = out.merge(board_ret, on=["board_bucket", date_col], how="left", sort=False)
        out["stock_vs_board_20d"] = out["ret_20d"] - out["board_return_20d"]
    for col in PRIMITIVE_FEATURES:
        if col not in out.columns:
            out[col] = np.nan
    out["required_pre_vol_lookback_complete"] = out["volatility_20d"].notna() & out["volatility_60d"].notna()
    out["entry_executable"] = out["entry_pos"].notna() & out["entry_price"].notna()
    return out, pd.DataFrame(audit_rows)


def split_boundary_info(boundary: pd.DataFrame) -> tuple[dict[str, str], Any]:
    rows = boundary.copy()
    rows["eval_split"] = rows["eval_split"].astype(str)
    val = rows.loc[rows["eval_split"].eq("validation")]
    rob = rows.loc[rows["eval_split"].eq("robustness")]
    train_end = date_text(val["train_max_event_t0_date"].iloc[0]) if len(val) else "2021-12-31"
    validation_start = date_text(val["eval_min_event_t0_date"].iloc[0]) if len(val) else "2022-01-04"
    robustness_start = date_text(rob["eval_min_event_t0_date"].iloc[0]) if len(rob) else "2024-03-01"

    def assign(value: Any) -> str:
        text = date_text(value)
        if not text:
            return "boundary_gap_excluded"
        if text <= train_end:
            return "train"
        if validation_start <= text < robustness_start:
            return "validation"
        if text >= robustness_start:
            return "robustness"
        return "boundary_gap_excluded"

    return {"train_end": train_end, "validation_start": validation_start, "robustness_start": robustness_start}, assign


def build_full_universe_panel(resolved: dict[str, Path], config: dict[str, Any], cache: StockDailyCache) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pit_cols = ["usable_trade_date", "instrument", "board_bucket", "is_listed", "is_st", "is_suspended"]
    pit = read_table(resolved["pit_topn_400_100_executable_daily"], usecols=pit_cols)
    pit = pit.rename(columns={"usable_trade_date": "reference_date"})
    pit["reference_date"] = pit["reference_date"].map(date_text)
    pit["row_id"] = np.arange(len(pit), dtype=np.int64)
    regime = read_table(resolved["global_regime_calendar"])
    regime["reference_date"] = regime["date"].map(date_text)
    regime_status = "pass"
    regime_reason = ""
    if bool_series(regime.get("daily_regime_conflict_flag", pd.Series(False, index=regime.index))).any():
        regime_status = "fail"
        regime_reason = "conflict_flag_true"
    if finite_numeric(regime.get("daily_regime_conflict_n", pd.Series(0, index=regime.index))).fillna(0).gt(0).any():
        regime_status = "fail"
        regime_reason = "conflict_n_positive" if not regime_reason else f"{regime_reason};conflict_n_positive"
    if regime["reference_date"].duplicated().any():
        regime_status = "fail"
        regime_reason = "duplicate_regime_date" if not regime_reason else f"{regime_reason};duplicate_regime_date"
    regime_map = regime[["reference_date", "daily_regime_bucket"]].rename(columns={"daily_regime_bucket": "market_regime_bucket"})
    pit = pit.merge(regime_map, on="reference_date", how="left", sort=False)
    missing_regime = pit["market_regime_bucket"].isna()
    missing_regime_row_n = int(missing_regime.sum())
    missing_regime_date_n = int(pit.loc[missing_regime, "reference_date"].nunique()) if missing_regime_row_n else 0
    if missing_regime_row_n and regime_status == "pass":
        regime_status = "pass_with_missing_date_bypass"
        regime_reason = "missing_regime_date_bypassed"
    pit["regime_calendar_available"] = ~missing_regime
    pit["regime_missing_date_bypassed"] = missing_regime
    pit["market_regime_bucket"] = pit["market_regime_bucket"].fillna("missing_regime_calendar")
    boundary = read_table(resolved["split_time_boundary_audit"])
    bounds, assign_split = split_boundary_info(boundary)
    pit["split"] = pit["reference_date"].map(assign_split)
    pit["calendar_month"] = pit["reference_date"].str[:7]
    pit["calendar_year"] = pit["reference_date"].str[:4]
    supported = set(config.get("supported_boards", []))
    panel, feature_audit = primitive_features_for_rows(pit, cache, "reference_date", id_cols=["row_id"])
    panel["supported_board"] = panel["board_bucket"].astype(str).isin(supported)
    panel["primary_scope"] = (
        bool_series(panel["regime_calendar_available"])
        & panel["market_regime_bucket"].astype(str).eq("risk_on")
        & panel["supported_board"]
        & panel["entry_executable"]
        & panel["required_pre_vol_lookback_complete"]
        & panel["split"].isin(["train", "validation", "robustness"])
    )
    split_rows: list[dict[str, Any]] = []
    for split in ["train", "validation", "robustness", "boundary_gap_excluded"]:
        sub = panel.loc[panel["split"].eq(split)]
        split_rows.append(
            {
                "split": split,
                "start_date": sub["reference_date"].min() if len(sub) else "",
                "end_date": sub["reference_date"].max() if len(sub) else "",
                "reference_row_n": int(len(sub)),
                "entry_executable_row_n": int(bool_series(sub.get("entry_executable", pd.Series(False, index=sub.index))).sum()) if len(sub) else 0,
                "horizon_complete_row_n_by_horizon": "",
                "boundary_assignment_status": "pass" if split != "boundary_gap_excluded" or len(sub) == 0 else "gap_rows_present",
            }
        )
    primitive_audit = feature_audit.assign(
        global_regime_calendar_status=regime_status,
        global_regime_calendar_reason=regime_reason,
        missing_regime_date_bypassed_row_n=missing_regime_row_n,
        missing_regime_date_bypassed_unique_date_n=missing_regime_date_n,
    )
    primitive_audit["formula_version"] = "qfq_reference_close_primitives_v1"
    primitive_audit["split_train_end"] = bounds["train_end"]
    primitive_audit["split_validation_start"] = bounds["validation_start"]
    primitive_audit["split_robustness_start"] = bounds["robustness_start"]
    return panel, pd.DataFrame(split_rows), primitive_audit, pd.DataFrame([{"global_regime_calendar_status": regime_status, "global_regime_calendar_reason": regime_reason, "missing_regime_date_bypassed_row_n": missing_regime_row_n, "missing_regime_date_bypassed_unique_date_n": missing_regime_date_n}])


def label_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for vol_id in config["labels"]["vol_reference_ids"]:
        short = vol_id.replace("volatility_", "vol")
        for horizon in config["labels"]["horizons"]:
            for k_up in config["labels"]["k_up"]:
                for k_dn in config["labels"]["k_dn"]:
                    label_id = f"{short}_kup{str(k_up).replace('.', 'p')}_kdn{str(k_dn).replace('.', 'p')}_H{horizon}"
                    specs.append(
                        {
                            "label_id": label_id,
                            "label_type": "vol_scaled",
                            "vol_reference_id": vol_id,
                            "horizon_sessions": int(horizon),
                            "k_up": float(k_up),
                            "k_dn": float(k_dn),
                        }
                    )
    for item in config["labels"]["fixed_anchors"]:
        specs.append(
            {
                "label_id": str(item["label_id"]),
                "label_type": "fixed_anchor",
                "vol_reference_id": "",
                "horizon_sessions": int(item["horizon_sessions"]),
                "upper_barrier": float(item["upper_barrier"]),
                "lower_barrier": float(item["lower_barrier"]),
            }
        )
    return specs


def barrier_values(frame: pd.DataFrame, spec: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
    if spec["label_type"] == "fixed_anchor":
        return (
            pd.Series(float(spec["upper_barrier"]), index=frame.index),
            pd.Series(float(spec["lower_barrier"]), index=frame.index),
        )
    vol = finite_numeric(frame[spec["vol_reference_id"]])
    scale = np.sqrt(float(spec["horizon_sessions"]))
    return vol * float(spec["k_up"]) * scale, -1.0 * vol * float(spec["k_dn"]) * scale


def compute_label(frame: pd.DataFrame, spec: dict[str, Any], cache: StockDailyCache, pos_col: str, price_col: str) -> pd.DataFrame:
    n = len(frame)
    upper_first_arr = np.zeros(n, dtype=bool)
    lower_first_arr = np.zeros(n, dtype=bool)
    neutral_arr = np.zeros(n, dtype=bool)
    censored_arr = np.zeros(n, dtype=bool)
    same_bar_arr = np.zeros(n, dtype=bool)
    complete_arr = np.zeros(n, dtype=bool)
    upper_any_arr = np.zeros(n, dtype=bool)
    lower_any_arr = np.zeros(n, dtype=bool)
    time_to_upper_arr = np.full(n, np.nan, dtype=float)
    time_to_lower_arr = np.full(n, np.nan, dtype=float)
    max_high_arr = np.full(n, np.nan, dtype=float)
    min_low_arr = np.full(n, np.nan, dtype=float)
    pre_success_mae_arr = np.full(n, np.nan, dtype=float)
    horizon_close_arr = np.full(n, np.nan, dtype=float)
    upper, lower = barrier_values(frame, spec)
    upper_arr = pd.to_numeric(upper, errors="coerce").to_numpy(dtype=float)
    lower_arr = pd.to_numeric(lower, errors="coerce").to_numpy(dtype=float)
    pos_all = pd.to_numeric(frame[pos_col], errors="coerce").to_numpy(dtype=float)
    price_all = pd.to_numeric(frame[price_col], errors="coerce").to_numpy(dtype=float)
    horizon = int(spec["horizon_sessions"])
    for instrument, positions in frame.groupby("instrument", sort=False).indices.items():
        pos_idx = np.asarray(positions, dtype=int)
        daily = cache.get(str(instrument))
        if daily is None or daily.empty:
            censored_arr[pos_idx] = True
            continue
        high = daily["high"].to_numpy(dtype=float)
        low = daily["low"].to_numpy(dtype=float)
        close = daily["close"].to_numpy(dtype=float)
        pos = pos_all[pos_idx]
        price = price_all[pos_idx]
        ub = upper_arr[pos_idx]
        lb = lower_arr[pos_idx]
        valid = np.isfinite(pos) & np.isfinite(price) & np.isfinite(ub) & np.isfinite(lb)
        valid &= pos >= 0
        valid &= (pos + horizon) < len(daily)
        if not valid.any():
            censored_arr[pos_idx] = True
            continue
        invalid_pos = pos_idx[~valid]
        if len(invalid_pos):
            censored_arr[invalid_pos] = True
        valid_pos = pos_idx[valid]
        p_int = pos[valid].astype(int)
        offsets = np.arange(horizon + 1)
        pos_mat = p_int[:, None] + offsets[None, :]
        ref = price[valid][:, None]
        hret = high[pos_mat] / ref - 1.0
        lret = low[pos_mat] / ref - 1.0
        eps = 1e-12
        up_hit = hret >= ub[valid][:, None] - eps
        low_hit = lret <= lb[valid][:, None] + eps
        up_any = up_hit.any(axis=1)
        low_any = low_hit.any(axis=1)
        up_first_pos = np.argmax(up_hit, axis=1)
        low_first_pos = np.argmax(low_hit, axis=1)
        up_t = np.where(up_any, up_first_pos, np.nan)
        low_t = np.where(low_any, low_first_pos, np.nan)
        same = up_any & low_any & (up_first_pos == low_first_pos)
        upper_first = up_any & (~low_any | (up_first_pos < low_first_pos))
        lower_first = low_any & (~up_any | (low_first_pos <= up_first_pos))
        neutral = ~up_any & ~low_any
        complete_arr[valid_pos] = True
        censored_arr[valid_pos] = False
        same_bar_arr[valid_pos] = same
        upper_first_arr[valid_pos] = upper_first
        lower_first_arr[valid_pos] = lower_first
        neutral_arr[valid_pos] = neutral
        upper_any_arr[valid_pos] = up_any
        lower_any_arr[valid_pos] = low_any
        time_to_upper_arr[valid_pos] = up_t
        time_to_lower_arr[valid_pos] = low_t
        max_high_arr[valid_pos] = np.nanmax(hret, axis=1)
        min_low_arr[valid_pos] = np.nanmin(lret, axis=1)
        mae = np.full(len(valid_pos), np.nan)
        for i, first in enumerate(up_first_pos):
            if up_any[i]:
                mae[i] = float(np.nanmin(lret[i, : first + 1]))
        pre_success_mae_arr[valid_pos] = mae
        horizon_close_arr[valid_pos] = close[p_int + horizon] / price[valid] - 1.0
    out = pd.DataFrame(
        {
            "upper_first": upper_first_arr,
            "lower_first": lower_first_arr,
            "neutral": neutral_arr,
            "censored": censored_arr,
            "same_bar_conflict": same_bar_arr,
            "horizon_complete": complete_arr,
            "upper_touch_anytime": upper_any_arr,
            "lower_touch_anytime": lower_any_arr,
            "time_to_upper": time_to_upper_arr,
            "time_to_lower": time_to_lower_arr,
            "max_high_return": max_high_arr,
            "min_low_return": min_low_arr,
            "pre_success_MAE_for_upper_touch": pre_success_mae_arr,
            "horizon_close_return": horizon_close_arr,
            "upper_barrier": upper_arr,
            "lower_barrier": lower_arr,
            "winner_positive": upper_first_arr,
        },
        index=frame.index,
    )
    return out


def label_formula_audit(specs: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for spec in specs:
        rows.append(
            {
                "label_id": spec["label_id"],
                "label_type": spec["label_type"],
                "vol_reference_id": spec.get("vol_reference_id", ""),
                "vol_reference_unit": "daily_return_std" if spec["label_type"] == "vol_scaled" else "not_applicable",
                "k_up": spec.get("k_up", np.nan),
                "k_dn": spec.get("k_dn", np.nan),
                "upper_barrier": spec.get("upper_barrier", np.nan),
                "lower_barrier": spec.get("lower_barrier", np.nan),
                "horizon_sessions": spec["horizon_sessions"],
                "same_bar_priority": "lower_first",
                "path_window": "reference_pos_through_reference_pos_plus_horizon_inclusive",
                "formula_status": "pass",
            }
        )
    return pd.DataFrame(rows)


def label_summary_for_spec(base: pd.DataFrame, label: pd.DataFrame, spec: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    train = base.loc[base["split"].eq("train") & base["label_selection_scope"]].copy()
    lab = label.loc[train.index]
    complete = lab["horizon_complete"].astype(bool)
    denom = train.loc[complete]
    pos = lab.loc[complete, "winner_positive"].astype(bool)
    base_rate = safe_rate(pos.sum(), len(pos))
    same_rate = safe_rate(lab.loc[complete, "same_bar_conflict"].astype(bool).sum(), len(pos))
    complete_rate = safe_rate(complete.sum(), len(train))
    dispersion = label_base_rate_dispersion(train, lab.loc[train.index], thresholds)
    score = complete_rate - same_rate - dispersion - abs(base_rate - float(thresholds["target_label_base_rate"])) if pd.notna(base_rate) else -np.inf
    eligible = (
        complete_rate >= 0.98
        and int(pos.sum()) >= int(thresholds["min_train_positive_n"])
        and float(thresholds["min_label_base_rate"]) <= base_rate <= float(thresholds["max_label_base_rate"])
        and same_rate <= float(thresholds["max_same_bar_conflict_rate"])
        and dispersion <= float(thresholds["max_label_base_rate_dispersion"])
    )
    return {
        "label_id": spec["label_id"],
        "label_type": spec["label_type"],
        "vol_reference_id": spec.get("vol_reference_id", ""),
        "horizon_sessions": spec["horizon_sessions"],
        "train_denominator_n": int(len(train)),
        "train_horizon_complete_n": int(complete.sum()),
        "train_horizon_complete_rate": complete_rate,
        "train_winner_positive_n": int(pos.sum()),
        "train_winner_base_rate": base_rate,
        "train_same_bar_conflict_rate": same_rate,
        "label_base_rate_dispersion": dispersion,
        "label_stability_score": score,
        "label_eligibility_status": "eligible" if eligible else "ineligible",
    }


def label_base_rate_dispersion(frame: pd.DataFrame, label: pd.DataFrame, thresholds: dict[str, Any]) -> float:
    complete = label["horizon_complete"].astype(bool)
    pos = label["winner_positive"].astype(bool)
    base = safe_rate(pos.loc[complete].sum(), complete.sum())
    if pd.isna(base):
        return np.inf
    vals: list[float] = []
    for col in ["calendar_year", "board_bucket", "market_regime_bucket"]:
        if col not in frame.columns:
            continue
        for _key, idx in frame.loc[complete].groupby(col, dropna=False).groups.items():
            idx_list = list(idx)
            if len(idx_list) < int(thresholds["min_label_stability_slice_n"]):
                continue
            p = int(pos.loc[idx_list].sum())
            if p < int(thresholds["min_label_stability_slice_positive_n"]):
                continue
            vals.append(abs(safe_rate(p, len(idx_list)) - base))
    return float(max(vals)) if vals else 0.0


def label_stability_slice_groups(frame: pd.DataFrame) -> list[np.ndarray]:
    groups: list[np.ndarray] = []
    for col in ["calendar_year", "board_bucket", "market_regime_bucket"]:
        if col not in frame.columns:
            continue
        groups.extend(np.asarray(pos, dtype=int) for pos in frame.groupby(col, dropna=False, sort=False).indices.values())
    return groups


def label_base_rate_dispersion_from_arrays(
    complete: np.ndarray,
    positive: np.ndarray,
    slice_groups: list[np.ndarray],
    thresholds: dict[str, Any],
) -> float:
    base = safe_rate(int(positive[complete].sum()), int(complete.sum()))
    if pd.isna(base):
        return np.inf
    vals: list[float] = []
    min_n = int(thresholds["min_label_stability_slice_n"])
    min_pos = int(thresholds["min_label_stability_slice_positive_n"])
    for positions in slice_groups:
        in_slice = complete[positions]
        n = int(in_slice.sum())
        if n < min_n:
            continue
        p = int(positive[positions][in_slice].sum())
        if p < min_pos:
            continue
        vals.append(abs(safe_rate(p, n) - base))
    return float(max(vals)) if vals else 0.0


def horizon_return_matrices(
    frame: pd.DataFrame,
    cache: StockDailyCache,
    pos_col: str,
    price_col: str,
    horizon: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(frame)
    high_ret = np.full((n, horizon + 1), np.nan, dtype=float)
    low_ret = np.full((n, horizon + 1), np.nan, dtype=float)
    complete = np.zeros(n, dtype=bool)
    pos_all = pd.to_numeric(frame[pos_col], errors="coerce").to_numpy(dtype=float)
    price_all = pd.to_numeric(frame[price_col], errors="coerce").to_numpy(dtype=float)
    offsets = np.arange(horizon + 1)
    for instrument, positions in frame.groupby("instrument", sort=False).indices.items():
        pos_idx = np.asarray(positions, dtype=int)
        daily = cache.get(str(instrument))
        if daily is None or daily.empty:
            continue
        high = daily["high"].to_numpy(dtype=float)
        low = daily["low"].to_numpy(dtype=float)
        pos = pos_all[pos_idx]
        price = price_all[pos_idx]
        valid = np.isfinite(pos) & np.isfinite(price) & (pos >= 0) & ((pos + horizon) < len(daily))
        if not valid.any():
            continue
        valid_pos = pos_idx[valid]
        p_int = pos[valid].astype(int)
        pos_mat = p_int[:, None] + offsets[None, :]
        ref = price[valid][:, None]
        high_ret[valid_pos] = high[pos_mat] / ref - 1.0
        low_ret[valid_pos] = low[pos_mat] / ref - 1.0
        complete[valid_pos] = True
    return high_ret, low_ret, complete


def label_summary_from_arrays(
    frame: pd.DataFrame,
    spec: dict[str, Any],
    upper_arr: np.ndarray,
    lower_arr: np.ndarray,
    high_ret: np.ndarray,
    low_ret: np.ndarray,
    horizon_complete_base: np.ndarray,
    slice_groups: list[np.ndarray],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    n = len(frame)
    complete = horizon_complete_base & np.isfinite(upper_arr) & np.isfinite(lower_arr)
    positive = np.zeros(n, dtype=bool)
    same = np.zeros(n, dtype=bool)
    if complete.any():
        eps = 1e-12
        rows = np.flatnonzero(complete)
        up_hit = high_ret[rows] >= upper_arr[rows, None] - eps
        low_hit = low_ret[rows] <= lower_arr[rows, None] + eps
        up_any = up_hit.any(axis=1)
        low_any = low_hit.any(axis=1)
        up_first_pos = np.argmax(up_hit, axis=1)
        low_first_pos = np.argmax(low_hit, axis=1)
        same_rows = up_any & low_any & (up_first_pos == low_first_pos)
        upper_first = up_any & (~low_any | (up_first_pos < low_first_pos))
        same[rows] = same_rows
        positive[rows] = upper_first
    complete_n = int(complete.sum())
    positive_n = int(positive[complete].sum()) if complete_n else 0
    base_rate = safe_rate(positive_n, complete_n)
    same_rate = safe_rate(int(same[complete].sum()), complete_n)
    complete_rate = safe_rate(complete_n, n)
    dispersion = label_base_rate_dispersion_from_arrays(complete, positive, slice_groups, thresholds)
    score = complete_rate - same_rate - dispersion - abs(base_rate - float(thresholds["target_label_base_rate"])) if pd.notna(base_rate) else -np.inf
    eligible = (
        complete_rate >= 0.98
        and positive_n >= int(thresholds["min_train_positive_n"])
        and float(thresholds["min_label_base_rate"]) <= base_rate <= float(thresholds["max_label_base_rate"])
        and same_rate <= float(thresholds["max_same_bar_conflict_rate"])
        and dispersion <= float(thresholds["max_label_base_rate_dispersion"])
    )
    return {
        "label_id": spec["label_id"],
        "label_type": spec["label_type"],
        "vol_reference_id": spec.get("vol_reference_id", ""),
        "horizon_sessions": spec["horizon_sessions"],
        "train_denominator_n": int(n),
        "train_horizon_complete_n": complete_n,
        "train_horizon_complete_rate": complete_rate,
        "train_winner_positive_n": positive_n,
        "train_winner_base_rate": base_rate,
        "train_same_bar_conflict_rate": same_rate,
        "label_base_rate_dispersion": dispersion,
        "label_stability_score": score,
        "label_eligibility_status": "eligible" if eligible else "ineligible",
    }


def label_summary_grid_fast(
    frame: pd.DataFrame,
    specs: list[dict[str, Any]],
    cache: StockDailyCache,
    thresholds: dict[str, Any],
    pos_col: str,
    price_col: str,
) -> pd.DataFrame:
    slice_groups = label_stability_slice_groups(frame)
    rows: list[dict[str, Any]] = []
    specs_by_horizon: dict[int, list[dict[str, Any]]] = {}
    for spec in specs:
        specs_by_horizon.setdefault(int(spec["horizon_sessions"]), []).append(spec)
    for horizon in sorted(specs_by_horizon):
        high_ret, low_ret, horizon_complete = horizon_return_matrices(frame, cache, pos_col, price_col, horizon)
        for spec in specs_by_horizon[horizon]:
            upper, lower = barrier_values(frame, spec)
            upper_arr = pd.to_numeric(upper, errors="coerce").to_numpy(dtype=float)
            lower_arr = pd.to_numeric(lower, errors="coerce").to_numpy(dtype=float)
            rows.append(
                label_summary_from_arrays(
                    frame,
                    spec,
                    upper_arr,
                    lower_arr,
                    high_ret,
                    low_ret,
                    horizon_complete,
                    slice_groups,
                    thresholds,
                )
            )
    return pd.DataFrame(rows)


def choose_label(summary: pd.DataFrame, thresholds: dict[str, Any]) -> tuple[pd.Series, pd.DataFrame]:
    work = summary.copy()
    work["selected_label_flag"] = False
    eligible = work.loc[work["label_eligibility_status"].eq("eligible")].copy()
    if eligible.empty:
        idx = work.sort_values(["label_stability_score", "label_id"], ascending=[False, True], kind="stable").index[0]
        work.loc[idx, "selected_label_flag"] = True
        work["selection_reason"] = np.where(work["selected_label_flag"], "no_eligible_label_best_available_for_diagnostics", "")
        return work.loc[idx], work
    vol = eligible.loc[eligible["label_type"].eq("vol_scaled")].sort_values(
        ["label_stability_score", "label_base_rate_dispersion", "train_same_bar_conflict_rate", "label_id"],
        ascending=[False, True, True, True],
        kind="stable",
    )
    fixed = eligible.loc[eligible["label_type"].eq("fixed_anchor")].sort_values(
        ["label_stability_score", "label_base_rate_dispersion", "train_same_bar_conflict_rate", "label_id"],
        ascending=[False, True, True, True],
        kind="stable",
    )
    choose_idx: Any
    reason: str
    if not vol.empty and not fixed.empty:
        best_vol = vol.iloc[0]
        best_fixed = fixed.iloc[0]
        not_worse = (
            float(best_vol["label_stability_score"]) >= float(best_fixed["label_stability_score"]) - float(thresholds["max_label_stability_score_tolerance"])
            and float(best_vol["label_base_rate_dispersion"]) <= float(best_fixed["label_base_rate_dispersion"]) + float(thresholds["max_label_base_rate_dispersion_tolerance"])
            and float(best_vol["train_same_bar_conflict_rate"]) <= float(best_fixed["train_same_bar_conflict_rate"]) + float(thresholds["max_same_bar_conflict_rate_tolerance"])
        )
        choose_idx = best_vol.name if not_worse else best_fixed.name
        reason = "best_vol_scaled_not_worse" if not_worse else "fixed_anchor_more_stable"
    elif not vol.empty:
        choose_idx = vol.index[0]
        reason = "only_eligible_vol_scaled"
    else:
        choose_idx = fixed.index[0]
        reason = "only_eligible_fixed_anchor"
    work.loc[choose_idx, "selected_label_flag"] = True
    work["selection_reason"] = np.where(work["selected_label_flag"], reason, "")
    return work.loc[choose_idx], work


def auc_score(values: pd.Series, labels: pd.Series) -> float:
    v = finite_numeric(values)
    y = labels.astype(bool)
    ok = v.notna() & y.notna()
    v = v.loc[ok]
    y = y.loc[ok]
    pos_n = int(y.sum())
    neg_n = int((~y).sum())
    if pos_n == 0 or neg_n == 0:
        return np.nan
    ranks = v.rank(method="average")
    pos_rank_sum = ranks.loc[y].sum()
    return float((pos_rank_sum - pos_n * (pos_n + 1) / 2) / (pos_n * neg_n))


def metric_ci(center: float, se: float, alpha: float) -> tuple[float, float]:
    if pd.isna(center) or pd.isna(se) or se <= 0:
        return np.nan, np.nan
    z = NormalDist().inv_cdf(1 - alpha / 2)
    return float(center - z * se), float(center + z * se)


def split_metrics(frame: pd.DataFrame, feature: str, orientation: str, thresholds: dict[str, Any], adjusted_alpha: float) -> dict[str, Any]:
    if feature not in frame.columns:
        return empty_metric_row()
    base = frame.loc[frame["horizon_complete"].astype(bool), [feature, "winner_positive"]]
    denominator_n = int(len(base))
    if denominator_n == 0:
        return empty_metric_row()
    values = finite_numeric(base[feature])
    labels = base["winner_positive"].astype(bool)
    finite = values.notna()
    rank_not_rate = safe_rate((~finite).sum(), len(base))
    eval_values = values.loc[finite]
    eval_labels = labels.loc[finite]
    positive_n = int(eval_labels.sum())
    if len(eval_values) == 0:
        return empty_metric_row(denominator_n=denominator_n, positive_n=positive_n, rank_not_evaluable_rate=rank_not_rate)
    auc_desc = auc_score(eval_values, eval_labels)
    auc = auc_desc if orientation == "desc" else (1 - auc_desc if pd.notna(auc_desc) else np.nan)
    rank_ic_desc = eval_values.corr(eval_labels.astype(float), method="spearman")
    rank_ic = rank_ic_desc if orientation == "desc" else -1 * rank_ic_desc if pd.notna(rank_ic_desc) else np.nan
    sorted_eval = pd.DataFrame({"_feature": eval_values, "_label": eval_labels}).sort_values(
        "_feature", ascending=(orientation == "asc"), kind="stable"
    )
    top_n = max(1, int(math.ceil(len(sorted_eval) * 0.10)))
    top = sorted_eval.head(top_n)
    bottom = sorted_eval.tail(top_n)
    base_rate = safe_rate(eval_labels.sum(), len(eval_labels))
    top_rate = safe_rate(top["_label"].sum(), len(top))
    bottom_rate = safe_rate(bottom["_label"].sum(), len(bottom))
    lift_abs = top_rate - base_rate if pd.notna(top_rate) and pd.notna(base_rate) else np.nan
    lift_ratio = safe_rate(top_rate, base_rate)
    se_lift = math.sqrt(max(top_rate * (1 - top_rate), 0) / len(top) + max(base_rate * (1 - base_rate), 0) / len(eval_labels)) if pd.notna(top_rate) and pd.notna(base_rate) else np.nan
    lift_low, lift_high = metric_ci(lift_abs, se_lift, adjusted_alpha)
    if pd.notna(rank_ic) and len(eval_labels) > 3 and abs(rank_ic) < 1:
        se_ic = 1 / math.sqrt(len(eval_labels) - 3)
        ic_low, ic_high = metric_ci(rank_ic, se_ic, adjusted_alpha)
    else:
        ic_low, ic_high = np.nan, np.nan
    raw_pass = (
        pd.notna(auc)
        and auc >= float(thresholds["min_auc"])
        and pd.notna(lift_low)
        and lift_low > 0
        and pd.notna(lift_abs)
        and lift_abs >= float(thresholds["min_top_decile_lift_abs"])
        and pd.notna(lift_ratio)
        and lift_ratio >= float(thresholds["min_top_decile_lift_ratio"])
        and int(top["_label"].sum()) >= int(thresholds["min_top_decile_positive_n"])
        and rank_not_rate <= float(thresholds["max_rank_not_evaluable_rate"])
    )
    adjusted_pass = raw_pass and pd.notna(ic_low) and ic_low > 0
    return {
        "auc": auc,
        "rank_ic": rank_ic,
        "rank_ic_ci95_low": ic_low,
        "rank_ic_ci95_high": ic_high,
        "top_decile_winner_rate": top_rate,
        "base_winner_rate": base_rate,
        "top_decile_lift_abs": lift_abs,
        "top_decile_lift_ratio": lift_ratio,
        "top_decile_lift_ci95_low": lift_low,
        "top_decile_lift_ci95_high": lift_high,
        "bottom_decile_winner_rate": bottom_rate,
        "top_minus_bottom_spread": top_rate - bottom_rate if pd.notna(top_rate) and pd.notna(bottom_rate) else np.nan,
        "positive_n": positive_n,
        "denominator_n": denominator_n,
        "horizon_complete_n": denominator_n,
        "horizon_complete_rate": 1.0,
        "censored_n": 0,
        "censored_rate": 0.0,
        "rank_evaluable_n": int(finite.sum()),
        "rank_not_evaluable_rate": rank_not_rate,
        "top_decile_positive_n": int(top["_label"].sum()),
        "raw_separability_status": "pass" if raw_pass else "fail",
        "search_adjusted_status": "pass" if adjusted_pass else "fail",
    }


def empty_metric_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "auc": np.nan,
        "rank_ic": np.nan,
        "rank_ic_ci95_low": np.nan,
        "rank_ic_ci95_high": np.nan,
        "top_decile_winner_rate": np.nan,
        "base_winner_rate": np.nan,
        "top_decile_lift_abs": np.nan,
        "top_decile_lift_ratio": np.nan,
        "top_decile_lift_ci95_low": np.nan,
        "top_decile_lift_ci95_high": np.nan,
        "bottom_decile_winner_rate": np.nan,
        "top_minus_bottom_spread": np.nan,
        "positive_n": 0,
        "denominator_n": 0,
        "horizon_complete_n": 0,
        "horizon_complete_rate": np.nan,
        "censored_n": 0,
        "censored_rate": np.nan,
        "rank_evaluable_n": 0,
        "rank_not_evaluable_rate": np.nan,
        "top_decile_positive_n": 0,
        "raw_separability_status": "fail",
        "search_adjusted_status": "fail",
    }
    row.update(overrides)
    return row


def orientation_scores(train: pd.DataFrame, feature: str) -> dict[str, float]:
    desc = split_metrics(train, feature, "desc", permissive_thresholds(), 0.05)
    asc = split_metrics(train, feature, "asc", permissive_thresholds(), 0.05)
    return {
        "desc": (desc["auc"] if pd.notna(desc["auc"]) else -np.inf)
        + 0.5 * max(0, desc["top_decile_lift_abs"] if pd.notna(desc["top_decile_lift_abs"]) else 0)
        + 0.1 * max(0, desc["rank_ic"] if pd.notna(desc["rank_ic"]) else 0),
        "asc": (asc["auc"] if pd.notna(asc["auc"]) else -np.inf)
        + 0.5 * max(0, asc["top_decile_lift_abs"] if pd.notna(asc["top_decile_lift_abs"]) else 0)
        + 0.1 * max(0, asc["rank_ic"] if pd.notna(asc["rank_ic"]) else 0),
    }


def permissive_thresholds() -> dict[str, Any]:
    return {
        "min_auc": -np.inf,
        "min_top_decile_lift_abs": -np.inf,
        "min_top_decile_lift_ratio": -np.inf,
        "min_top_decile_positive_n": 0,
        "max_rank_not_evaluable_rate": 1.0,
    }


def separability_readout(
    frame: pd.DataFrame,
    denominator_id: str,
    label_id: str,
    label_reference_view: str,
    features: list[str],
    thresholds: dict[str, Any],
    label_grid_size: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    present_features = [feature for feature in features if feature in frame.columns]
    needed_cols = sorted(
        set(present_features)
        | {"split", "horizon_complete", "winner_positive"}
        | ({"instrument"} if "instrument" in frame.columns else set())
        | ({"calendar_month"} if "calendar_month" in frame.columns else set())
    )
    work = frame.loc[:, needed_cols]
    split_values = work["split"].astype(str) if "split" in work.columns else pd.Series("all", index=work.index)
    split_cache = {
        split: (work if split == "all" else work.loc[split_values.eq(split)])
        for split in SPLITS
    }
    train = split_cache["train"]
    feature_scores = []
    feature_grid_size = max(1, len(present_features))
    effective_search_size = max(1, label_grid_size * feature_grid_size * 2)
    alpha = float(thresholds["search_adjustment_alpha"]) / effective_search_size
    for feature in present_features:
        scores = orientation_scores(train, feature)
        orientation = "desc" if scores["desc"] > scores["asc"] else "asc"
        train_metric = split_metrics(train, feature, orientation, thresholds, alpha)
        score = (train_metric["auc"] if pd.notna(train_metric["auc"]) else -np.inf) + 0.5 * max(0, train_metric["top_decile_lift_abs"] if pd.notna(train_metric["top_decile_lift_abs"]) else 0) + 0.1 * max(0, train_metric["rank_ic"] if pd.notna(train_metric["rank_ic"]) else 0)
        feature_scores.append((feature, orientation, score, train_metric))
    feature_scores.sort(key=lambda x: (x[2], x[3].get("auc", -np.inf), x[3].get("top_decile_lift_abs", -np.inf), x[0], x[1]), reverse=True)
    selected_feature = feature_scores[0][0] if feature_scores else ""
    selected_orientation = feature_scores[0][1] if feature_scores else "asc"
    selection_rows = []
    for rank, (feature, orientation, score, train_metric) in enumerate(feature_scores, start=1):
        selection_rows.append(
            {
                "denominator_id": denominator_id,
                "label_id": label_id,
                "selected_feature_id": feature if rank == 1 else "",
                "feature_id": feature,
                "selected_orientation": orientation if rank == 1 else "",
                "orientation": orientation,
                "feature_time_bucket": "realized_0_20d" if feature.startswith("realized_") else "t0_pit",
                "label_reference_view": label_reference_view,
                "construction_coupled_status": "construction_coupled_diagnostic_only" if feature in label_id else "primary_eligible",
                "train_auc": train_metric["auc"],
                "train_rank_ic": train_metric["rank_ic"],
                "train_top_decile_lift_abs": train_metric["top_decile_lift_abs"],
                "train_top_decile_lift_ratio": train_metric["top_decile_lift_ratio"],
                "selection_rank": rank,
                "tie_break_reason": "highest_registered_separability_score" if rank == 1 else "",
            }
        )
    for feature, orientation, _score, _train_metric in feature_scores:
        for split in SPLITS:
            sub = split_cache[split]
            metric = split_metrics(sub, feature, orientation, thresholds, alpha)
            metric.update(
                {
                    "denominator_id": denominator_id,
                    "label_id": label_id,
                    "feature_id": feature,
                    "selected_feature_id": selected_feature,
                    "selected_orientation": selected_orientation,
                    "orientation": orientation,
                    "feature_time_bucket": "realized_0_20d" if feature.startswith("realized_") else "t0_pit",
                    "label_reference_view": label_reference_view,
                    "split": split,
                    "label_grid_size": label_grid_size,
                    "feature_grid_size": feature_grid_size,
                    "effective_search_size": effective_search_size,
                    "instrument_n": int(sub.loc[sub["horizon_complete"].astype(bool), "instrument"].nunique()) if "instrument" in sub else 0,
                    "instrument_month_block_n": int(sub.loc[sub["horizon_complete"].astype(bool), ["instrument", "calendar_month"]].drop_duplicates().shape[0]) if {"instrument", "calendar_month"} <= set(sub.columns) else 0,
                    "effective_block_n": int(sub.loc[sub["horizon_complete"].astype(bool), ["instrument", "calendar_month"]].drop_duplicates().shape[0]) if {"instrument", "calendar_month"} <= set(sub.columns) else 0,
                }
            )
            rows.append(metric)
    return pd.DataFrame(rows), pd.DataFrame(selection_rows)


def build_label_overlap_audit(frame: pd.DataFrame, denominator_id: str, label_id: str, horizon: int) -> pd.DataFrame:
    complete = frame.loc[frame["horizon_complete"].astype(bool)].copy()
    if complete.empty or not {"instrument", "calendar_month"} <= set(complete.columns):
        return pd.DataFrame(
            [
                {
                    "denominator_id": denominator_id,
                    "label_id": label_id,
                    "horizon_sessions": horizon,
                    "raw_row_n": int(len(complete)),
                    "instrument_n": 0,
                    "instrument_month_block_n": 0,
                    "mean_rows_per_block": np.nan,
                    "p95_rows_per_block": np.nan,
                    "effective_block_n": 0,
                    "overlap_control_status": "insufficient",
                }
            ]
        )
    block_counts = complete.groupby(["instrument", "calendar_month"], dropna=False).size()
    return pd.DataFrame(
        [
            {
                "denominator_id": denominator_id,
                "label_id": label_id,
                "horizon_sessions": horizon,
                "raw_row_n": int(len(complete)),
                "instrument_n": int(complete["instrument"].nunique()),
                "instrument_month_block_n": int(len(block_counts)),
                "mean_rows_per_block": float(block_counts.mean()),
                "p95_rows_per_block": float(block_counts.quantile(0.95)),
                "effective_block_n": int(len(block_counts)),
                "overlap_control_status": "pass" if len(block_counts) > 0 else "insufficient",
            }
        ]
    )


def active_band_from_c0(
    full: pd.DataFrame,
    c0_primitive: pd.DataFrame,
    c0_feature_matrix: pd.DataFrame,
    thresholds: dict[str, Any],
) -> tuple[pd.Series, pd.DataFrame]:
    train = c0_primitive.loc[c0_primitive["split"].eq("train")].copy()
    rows = []
    eligible = True
    fallback_reasons: list[str] = []
    dimensions = [
        ("liquidity_or_turnover_activity", "turnover_rate_median_20d", 0.05, None),
        ("recent_trading_continuity", "trading_continuity_20d", 0.05, None),
        ("pre_event_volatility_range", "volatility_20d", 0.01, 0.99),
        ("recent_motion_or_range_activity", "recent_range_activity_20d", 0.05, None),
    ]
    mask = full["primary_scope"].copy()
    c0_mask = pd.Series(True, index=c0_primitive.index)
    vol_status = "pass"
    if {"meta_event_id", "volatility_20d", "volatility_60d"} <= set(c0_feature_matrix.columns):
        tmp = c0_primitive[["meta_event_id", "volatility_20d", "volatility_60d"]].merge(
            c0_feature_matrix[["meta_event_id", "volatility_20d", "volatility_60d"]],
            on="meta_event_id",
            how="left",
            suffixes=("_recomputed", "_upstream"),
        )
        for col in ["volatility_20d", "volatility_60d"]:
            left = finite_numeric(tmp[f"{col}_recomputed"])
            right = finite_numeric(tmp[f"{col}_upstream"])
            both = left.notna() & right.notna()
            if both.any() and (left.loc[both] - right.loc[both]).abs().gt(1e-12).any():
                vol_status = "volatility_reconciliation_fail"
                eligible = False
    for dimension, feature, low_q, high_q in dimensions:
        vals = finite_numeric(train[feature]) if feature in train.columns else pd.Series(dtype=float)
        if vals.dropna().empty:
            eligible = False
            fallback_reasons.append(f"{dimension}_missing")
            low = high = np.nan
        else:
            low = float(vals.quantile(low_q))
            high = float(vals.quantile(high_q)) if high_q is not None else np.nan
            if high_q is None:
                mask &= finite_numeric(full[feature]).ge(low)
                c0_mask &= finite_numeric(c0_primitive[feature]).ge(low)
            else:
                mask &= finite_numeric(full[feature]).between(low, high)
                c0_mask &= finite_numeric(c0_primitive[feature]).between(low, high)
        rows.append(
            {
                "band_id": "full_pit_c0_comparable_active_band",
                "split": "all",
                "threshold_source_split": "train",
                "dimension": dimension,
                "feature_id": feature,
                "threshold_low": low,
                "threshold_high": high,
                "threshold_quantile_source": f"p{int(low_q*100):02d}" if high_q is None else f"p{int(low_q*100):02d}_p{int(high_q*100):02d}",
                "pit_status": "pass" if pd.notna(low) else "fail",
                "raw_full_universe_row_n": int(full["primary_scope"].sum()),
                "active_band_row_n": int(mask.sum()) if pd.notna(low) else 0,
                "active_band_share": safe_rate(int(mask.sum()), int(full["primary_scope"].sum())),
                "c0_entry_row_n": int(len(c0_primitive)),
                "c0_coverage_rate": safe_rate(int(c0_mask.sum()), len(c0_primitive)),
                "fallback_status": vol_status if vol_status != "pass" else (";".join(fallback_reasons) if fallback_reasons else "none"),
                "active_band_cartography_gate_eligible": bool(eligible and vol_status == "pass"),
            }
        )
    train_full_share = safe_rate(int(mask.loc[full["split"].eq("train")].sum()), int(full.loc[full["split"].eq("train"), "primary_scope"].sum()))
    train_c0_cov = safe_rate(int(c0_mask.loc[c0_primitive["split"].eq("train")].sum()), len(c0_primitive.loc[c0_primitive["split"].eq("train")]))
    for split in ["train", "validation", "robustness"]:
        full_split = full["split"].eq(split) & full["primary_scope"]
        c0_split = c0_primitive["split"].eq(split)
        share = safe_rate(int(mask.loc[full_split].sum()), int(full_split.sum()))
        cov = safe_rate(int(c0_mask.loc[c0_split].sum()), int(c0_split.sum()))
        share_delta = share - train_full_share if pd.notna(share) and pd.notna(train_full_share) else np.nan
        cov_delta = cov - train_c0_cov if pd.notna(cov) and pd.notna(train_c0_cov) else np.nan
        stable = (
            (pd.isna(share_delta) or abs(share_delta) <= float(thresholds["max_active_band_share_split_delta"]))
            and (pd.isna(cov_delta) or abs(cov_delta) <= float(thresholds["max_active_band_c0_coverage_rate_split_delta"]))
        )
        rows.append(
            {
                "band_id": "full_pit_c0_comparable_active_band",
                "split": split,
                "threshold_source_split": "train",
                "dimension": "coverage_stability",
                "feature_id": "all_band_dimensions",
                "threshold_low": np.nan,
                "threshold_high": np.nan,
                "threshold_quantile_source": "not_applicable",
                "pit_status": "pass",
                "raw_full_universe_row_n": int(full_split.sum()),
                "active_band_row_n": int(mask.loc[full_split].sum()),
                "active_band_share": share,
                "c0_entry_row_n": int(c0_split.sum()),
                "c0_coverage_rate": cov,
                "c0_coverage_rate_by_split": cov,
                "active_band_share_by_split": share,
                "c0_coverage_rate_delta_vs_train": cov_delta,
                "active_band_share_delta_vs_train": share_delta,
                "active_band_coverage_stability_status": "pass" if stable else "fail",
                "fallback_status": vol_status if vol_status != "pass" else (";".join(fallback_reasons) if fallback_reasons else "none"),
                "active_band_cartography_gate_eligible": bool(eligible and stable and vol_status == "pass"),
            }
        )
        if not stable:
            eligible = False
    return mask & bool(eligible) if eligible else pd.Series(False, index=full.index), pd.DataFrame(rows)


def stage1_reconstruction(c0: pd.DataFrame, score: pd.DataFrame, upstream: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    cols = ["meta_event_id", "volatility_20d__rank_percentile", "volatility_20d__rank_status"]
    merged = c0[["meta_event_id", "split"]].merge(score[cols], on="meta_event_id", how="left")
    selected = merged["volatility_20d__rank_status"].astype(str).eq("rank_evaluable") & finite_numeric(merged["volatility_20d__rank_percentile"]).le(0.30)
    merged["stage1_anchor_selected_flag"] = selected
    rows = []
    for split in SPLITS:
        sub = split_frame(merged, split)
        up = upstream.loc[np.isclose(pd.to_numeric(upstream["stage1_X"], errors="coerce"), 0.30) & upstream["split"].astype(str).eq(split)]
        upstream_selected = int(up.iloc[0]["stage1_selected_n"]) if len(up) else -1
        upstream_rank = int(up.iloc[0]["stage1_rank_evaluable_n"]) if len(up) else -1
        upstream_budget = safe_rate(upstream_selected, upstream_rank) if upstream_rank > 0 else np.nan
        rank_eval = int(sub["volatility_20d__rank_status"].astype(str).eq("rank_evaluable").sum())
        selected_n = int(sub["stage1_anchor_selected_flag"].sum())
        budget = safe_rate(selected_n, rank_eval)
        budget_match = (
            (rank_eval == 0 and upstream_rank == 0)
            or (pd.notna(budget) and pd.notna(upstream_budget) and abs(budget - upstream_budget) <= 1e-12)
        )
        rows.append(
            {
                "split": split,
                "recomputed_selected_n": selected_n,
                "upstream_selected_n": upstream_selected,
                "recomputed_rank_evaluable_n": rank_eval,
                "upstream_rank_evaluable_n": upstream_rank,
                "recomputed_selected_budget_rank_evaluable": budget,
                "upstream_selected_budget_rank_evaluable": upstream_budget,
                "selected_n_match_status": "pass" if selected_n == upstream_selected else "fail",
                "rank_evaluable_match_status": "pass" if rank_eval == upstream_rank else "fail",
                "budget_match_status": "pass" if budget_match else "fail",
            }
        )
    audit = pd.DataFrame(rows)
    audit["stage1_anchor_reconstruction_status"] = np.where(
        audit[["selected_n_match_status", "rank_evaluable_match_status", "budget_match_status"]].eq("pass").all(axis=1),
        "pass",
        "fail",
    )
    flag = merged.set_index("meta_event_id")["stage1_anchor_selected_flag"]
    return audit, c0["meta_event_id"].map(flag).fillna(False).astype(bool)


def build_c0_matrix(resolved: dict[str, Path], selected_spec: dict[str, Any], cache: StockDailyCache) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    event = read_table(resolved["two_stage_event_universe"])
    feat = read_table(resolved["two_stage_feature_matrix"])
    score = read_table(resolved["simple_backbone_score_matrix"])
    frontier = read_table(resolved["stage1_frontier_readout"])
    c0 = event.loc[
        bool_series(event["source_arm_is_c0"])
        & event["market_regime_bucket"].astype(str).eq("risk_on")
        & bool_series(event["stage_1_evaluable"])
    ].copy()
    feat_cols = [c for c in feat.columns if c not in c0.columns or c in {"meta_event_id", "instrument"}]
    c0 = c0.merge(feat[feat_cols], on=["meta_event_id", "instrument"], how="left", sort=False)
    recon, stage1_flag = stage1_reconstruction(c0, score, frontier)
    c0["stage1_anchor_selected_flag"] = stage1_flag.to_numpy()
    entry_label = compute_label(c0, selected_spec, cache, "entry_pos", "entry_price")
    for col in entry_label.columns:
        c0[f"entry_{col}"] = entry_label[col].to_numpy()
    cont = c0.copy()
    cont_vol = reference_volatility(cont, cache, "stage_2_reference_pos", prefix="continuation", prior_close=True)
    c0 = pd.concat([c0.reset_index(drop=True), cont_vol[["continuation_volatility_20d", "continuation_volatility_60d"]].reset_index(drop=True)], axis=1)
    cont_for_label = c0.copy()
    if selected_spec["label_type"] == "vol_scaled":
        ref = selected_spec["vol_reference_id"].replace("volatility", "continuation_volatility")
        cont_for_label[selected_spec["vol_reference_id"]] = cont_for_label[ref]
    cont_label = compute_label(cont_for_label, selected_spec, cache, "stage_2_reference_pos", "stage_2_reference_price")
    for col in cont_label.columns:
        c0[f"continuation_{col}"] = cont_label[col].to_numpy()
    c0["calendar_year"] = c0["calendar_year"].astype(str)
    return c0, recon, feat


def reference_volatility(frame: pd.DataFrame, cache: StockDailyCache, pos_col: str, prefix: str, prior_close: bool) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    out[f"{prefix}_volatility_20d"] = np.nan
    out[f"{prefix}_volatility_60d"] = np.nan
    for instrument, idxs in frame.groupby("instrument", sort=False).groups.items():
        daily = cache.get(str(instrument))
        if daily is None or daily.empty:
            continue
        pos = pd.to_numeric(frame.loc[idxs, pos_col], errors="coerce").to_numpy(dtype=float)
        idx_arr = np.array(list(idxs))
        for local_i, global_i in enumerate(idx_arr):
            if not np.isfinite(pos[local_i]):
                continue
            p = int(pos[local_i]) - (1 if prior_close else 0)
            if 0 <= p < len(daily):
                out.at[global_i, f"{prefix}_volatility_20d"] = daily.at[p, "volatility_20d"]
                out.at[global_i, f"{prefix}_volatility_60d"] = daily.at[p, "volatility_60d"]
    return out


def attach_label_columns(frame: pd.DataFrame, label_prefix: str) -> pd.DataFrame:
    cols = {
        "winner_positive": f"{label_prefix}_winner_positive",
        "horizon_complete": f"{label_prefix}_horizon_complete",
        "upper_first": f"{label_prefix}_upper_first",
        "lower_first": f"{label_prefix}_lower_first",
        "neutral": f"{label_prefix}_neutral",
        "upper_barrier": f"{label_prefix}_upper_barrier",
        "lower_barrier": f"{label_prefix}_lower_barrier",
        "horizon_close_return": f"{label_prefix}_horizon_close_return",
    }
    out = frame.copy()
    for new, old in cols.items():
        out[new] = out[old] if old in out.columns else np.nan
    return out


def feature_lists(c0: pd.DataFrame, feature_dict: pd.DataFrame, selected_spec: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    pop_groups = {"population_audit"}
    exclude = {"source_arm_is_c0", "source_arm_is_r_core"}
    if selected_spec["label_type"] == "vol_scaled":
        exclude.add(selected_spec["vol_reference_id"])
    fd = feature_dict.copy()
    fd["feature_name"] = fd["feature_name"].astype(str)
    fd["feature_group"] = fd["feature_group"].astype(str)
    pass_fd = fd.loc[fd["pit_status"].astype(str).eq("pass") & ~fd["feature_group"].isin(pop_groups)]
    stage1 = [
        f
        for f in pass_fd.loc[bool_series(pass_fd["allowed_for_stage_1"]), "feature_name"].tolist()
        if f in c0.columns and f not in exclude and pd.api.types.is_numeric_dtype(c0[f])
    ]
    stage2 = [
        f
        for f in pass_fd.loc[bool_series(pass_fd["allowed_for_stage_2"]), "feature_name"].tolist()
        if f in c0.columns and f not in exclude and pd.api.types.is_numeric_dtype(c0[f])
    ]
    realized = [c for c in c0.columns if c.startswith("realized_") and pd.api.types.is_numeric_dtype(c0[c])]
    full = [f for f in PRIMITIVE_FEATURES if f not in exclude]
    return sorted(set(stage1)), sorted(set(stage2 + realized)), full


def denominator_frames(c0: pd.DataFrame, full: pd.DataFrame, active_mask: pd.Series) -> dict[str, tuple[pd.DataFrame, str]]:
    entry = c0.loc[~bool_series(c0.get("entry_blocked", pd.Series(False, index=c0.index)))].copy()
    posthoc = entry.loc[bool_series(entry["no_fast_fail_L10_H20"])].copy()
    deploy = entry.loc[
        bool_series(entry["stage1_anchor_selected_flag"])
        & bool_series(entry["no_fast_fail_L10_H20"])
        & bool_series(entry["stage_2_path_evaluable"])
        & ~bool_series(entry["stage_2_entry_blocked"])
    ].copy()
    full_raw = full.loc[full["primary_scope"]].copy()
    full_active = full.loc[active_mask].copy()
    return {
        "c0_entry_t0": (attach_label_columns(entry, "entry"), "c0_entry_anchor"),
        "c0_posthoc_no_fast_fail_survivor": (attach_label_columns(posthoc, "entry"), "c0_entry_anchor"),
        "c0_deployable_stage2_reference": (attach_label_columns(deploy, "continuation"), "c0_post_survivor_continuation"),
        "full_pit_risk_on_universe_raw_diagnostic": (full_raw, "full_universe_next_open"),
        "full_pit_c0_comparable_active_band": (full_active, "full_universe_next_open"),
    }


def diversity_audit(denoms: dict[str, tuple[pd.DataFrame, str]], thresholds: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for den, (frame, _view) in denoms.items():
        if not den.startswith("c0_"):
            continue
        complete = frame.loc[frame["horizon_complete"].astype(bool)]
        blocks = complete[["instrument", "calendar_month"]].drop_duplicates().shape[0] if {"instrument", "calendar_month"} <= set(complete.columns) else 0
        inst = complete["instrument"].nunique() if "instrument" in complete else 0
        status = "pass" if inst >= int(thresholds["min_c0_instrument_n"]) and blocks >= int(thresholds["min_c0_instrument_month_block_n"]) else "fail"
        rows.append(
            {
                "denominator_id": den,
                "instrument_n": int(inst),
                "instrument_month_block_n": int(blocks),
                "min_c0_instrument_n": int(thresholds["min_c0_instrument_n"]),
                "min_c0_instrument_month_block_n": int(thresholds["min_c0_instrument_month_block_n"]),
                "diversity_status": status,
            }
        )
    return pd.DataFrame(rows)


def utility_for_frame(frame: pd.DataFrame, denominator_id: str, label_reference_view: str, entry_n: int, thresholds: dict[str, Any]) -> dict[str, Any]:
    complete = frame.loc[frame["horizon_complete"].astype(bool)].copy()
    den = len(complete)
    upper_rate = safe_rate(complete["upper_first"].astype(bool).sum(), den)
    lower_rate = safe_rate(complete["lower_first"].astype(bool).sum(), den)
    neutral_rate = safe_rate(complete["neutral"].astype(bool).sum(), den)
    median_upper = finite_numeric(complete["upper_barrier"]).median()
    median_lower = abs(finite_numeric(complete["lower_barrier"]).median())
    neutral_close = finite_numeric(complete.loc[complete["neutral"].astype(bool), "horizon_close_return"]).median()
    neutral_component = neutral_rate * min(0.0, neutral_close if pd.notna(neutral_close) else 0.0) if pd.notna(neutral_rate) else np.nan
    cost = float(thresholds["cost_buffer_bps"]) / 10000.0
    utility = upper_rate * median_upper - lower_rate * median_lower + neutral_component - cost if pd.notna(upper_rate) and pd.notna(lower_rate) else np.nan
    horizon = int(finite_numeric(frame.get("horizon_sessions", pd.Series([20] * len(frame)))).dropna().iloc[0]) if len(frame) else 20
    return {
        "denominator_id": denominator_id,
        "label_reference_view": label_reference_view,
        "precision_rate": safe_rate(complete["winner_positive"].astype(bool).sum(), den),
        "captured_positive_n": int(complete["winner_positive"].astype(bool).sum()),
        "upper_first_rate": upper_rate,
        "lower_first_rate": lower_rate,
        "neutral_rate": neutral_rate,
        "median_upper_barrier": median_upper,
        "median_lower_barrier_abs": median_lower,
        "neutral_component": neutral_component,
        "cost_component": cost,
        "utility_proxy_per_entry": utility,
        "utility_proxy_per_20d": utility * (20 / horizon) if pd.notna(utility) else np.nan,
        "utility_proxy_total_indexed_to_entry_n": utility * entry_n if pd.notna(utility) else np.nan,
    }


def recall_audits(c0: pd.DataFrame, denoms: dict[str, tuple[pd.DataFrame, str]], thresholds: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    entry = denoms["c0_entry_t0"][0]
    posthoc = denoms["c0_posthoc_no_fast_fail_survivor"][0]
    deploy = denoms["c0_deployable_stage2_reference"][0]
    entry_pos = int(entry.loc[entry["horizon_complete"].astype(bool), "winner_positive"].astype(bool).sum())
    post_retained = int(posthoc.loc[posthoc["horizon_complete"].astype(bool), "winner_positive"].astype(bool).sum())
    deploy_retained = int(deploy.loc[deploy["horizon_complete"].astype(bool), "winner_positive"].astype(bool).sum())
    post_cont = int(c0.loc[posthoc.index, "continuation_winner_positive"].astype(bool).sum()) if len(posthoc) else 0
    deploy_cont = int(deploy.get("winner_positive", pd.Series(False, index=deploy.index)).astype(bool).sum()) if len(deploy) else 0
    common = pd.DataFrame(
        [
            {
                "entry_anchor_positive_n": entry_pos,
                "posthoc_retained_entry_anchor_positive_n": post_retained,
                "deployable_retained_entry_anchor_positive_n": deploy_retained,
                "posthoc_continuation_positive_n": post_cont,
                "deployable_continuation_positive_n": deploy_cont,
            }
        ]
    )
    cost = pd.DataFrame(
        [
            {
                "denominator_id": "c0_posthoc_no_fast_fail_survivor",
                "recall_vs_entry": safe_rate(post_retained, entry_pos),
                "recall_cost": 1 - safe_rate(post_retained, entry_pos) if pd.notna(safe_rate(post_retained, entry_pos)) else np.nan,
            },
            {
                "denominator_id": "c0_deployable_stage2_reference",
                "recall_vs_entry": safe_rate(deploy_retained, entry_pos),
                "recall_cost": 1 - safe_rate(deploy_retained, entry_pos) if pd.notna(safe_rate(deploy_retained, entry_pos)) else np.nan,
            },
        ]
    )
    fast_fail_rate = safe_rate(bool_series(entry.get("stage_1_fast_fail_target", pd.Series(False, index=entry.index))).sum(), len(entry))
    retained_recall = safe_rate(post_retained, entry_pos)
    floor = float(thresholds["min_recall_vs_entry"])
    margin = float(thresholds["recall_floor_feasibility_warning_margin"])
    feasibility = pd.DataFrame(
        [
            {
                "min_recall_vs_entry": floor,
                "recall_floor_feasibility_warning_margin": margin,
                "c0_entry_fast_fail_rate": fast_fail_rate,
                "c0_entry_no_fast_fail_rate": 1 - fast_fail_rate if pd.notna(fast_fail_rate) else np.nan,
                "train_selected_label_entry_anchor_positive_n": entry_pos,
                "train_selected_label_retained_entry_anchor_positive_n": post_retained,
                "train_selected_label_retained_recall_vs_entry": retained_recall,
                "fixed_anchor_retained_recall_vs_entry_if_available": np.nan,
                "recall_floor_structurally_binding": bool(pd.notna(retained_recall) and retained_recall + margin < floor),
            }
        ]
    )
    return common, cost, feasibility


def decision_from_flags(flags: dict[str, bool]) -> str:
    for state in DECISION_PRECEDENCE:
        if flags.get(state, False):
            return state
    return "12A7g_baserate_only_not_separable_stop_winner_selection"


def render_report(decision: pd.DataFrame, label_selection: pd.DataFrame, utility: pd.DataFrame, recall_cost: pd.DataFrame) -> str:
    d = decision.iloc[0].to_dict() if not decision.empty else {}
    selected = label_selection.loc[label_selection.get("selected_label_flag", False).astype(bool)] if not label_selection.empty and "selected_label_flag" in label_selection else pd.DataFrame()
    s = selected.iloc[0].to_dict() if not selected.empty else {}
    util_lines = ["| denominator | utility_per_20d | precision | captured_pos |", "|---|---:|---:|---:|"]
    for row in utility.to_dict("records"):
        util_lines.append(f"| {row.get('denominator_id')} | {row.get('utility_proxy_per_20d', np.nan):.6f} | {row.get('precision_rate', np.nan):.4f} | {int(row.get('captured_positive_n', 0))} |")
    recall_lines = ["| denominator | recall_vs_entry | recall_cost |", "|---|---:|---:|"]
    for row in recall_cost.to_dict("records"):
        recall_lines.append(f"| {row.get('denominator_id')} | {row.get('recall_vs_entry', np.nan):.4f} | {row.get('recall_cost', np.nan):.4f} |")
    return f"""# 12A7g Vol-scaled Label Panel and C0 Separability Triage Report

## Decision

| field | value |
|---|---|
| decision_state | `{d.get('decision_state', '')}` |
| next_allowed_requirement | `{d.get('next_allowed_requirement', '')}` |
| selected_label_id | `{d.get('selected_label_id', s.get('label_id', ''))}` |
| selected_label_type | `{s.get('label_type', '')}` |
| input_gate_status | `{d.get('input_gate_status', '')}` |
| global_regime_calendar_status | `{d.get('global_regime_calendar_status', '')}` |
| global_regime_calendar_reason | `{d.get('global_regime_calendar_reason', '')}` |
| missing_regime_date_bypassed_row_n | `{d.get('missing_regime_date_bypassed_row_n', '')}` |
| missing_regime_date_bypassed_unique_date_n | `{d.get('missing_regime_date_bypassed_unique_date_n', '')}` |
| retained_primary_scope_n | `{d.get('retained_primary_scope_n', '')}` |
| active_band_cartography_gate_eligible | `{d.get('active_band_cartography_gate_eligible', '')}` |

Full-universe label panel is event-agnostic. It is not event-family support and cannot by itself validate any event formula.

## Label Selection

The selected label is train-frozen and validation / robustness are readout-only.

| field | value |
|---|---:|
| train winner base rate | {s.get('train_winner_base_rate', np.nan):.4f} |
| train positive n | {int(s.get('train_winner_positive_n', 0)) if pd.notna(s.get('train_winner_positive_n', np.nan)) else 0} |
| train horizon complete rate | {s.get('train_horizon_complete_rate', np.nan):.4f} |
| label stability score | {s.get('label_stability_score', np.nan):.4f} |
| label base-rate dispersion | {s.get('label_base_rate_dispersion', np.nan):.4f} |

## Utility Proxy

{chr(10).join(util_lines)}

The utility proxy includes a conservative neutral component and a cost buffer. It is not NAV, alpha, policy replay, or deployable return.

## Recall Cost

{chr(10).join(recall_lines)}

Recall is counted against common entry-anchor positives; continuation positives are reported separately in the output tables.
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: str, outputs: dict[str, Path]) -> Path:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "legacy_directory_id": LEGACY_DIRECTORY_ID,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path) if config_path.is_file() else None,
        "decision_state": decision,
        "decision": decision,
        "outputs": {key: str(value) for key, value in outputs.items()},
        "output_hashes": {key: file_sha256(value) for key, value in outputs.items() if value.is_file()},
    }
    return write_json(path, payload)


def threshold_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for key, value in config.get("thresholds", {}).items():
        rows.append({"threshold_id": key, "threshold_value": value, "source": "config", "override_reason": ""})
    return pd.DataFrame(rows)


def lineage_status(resolved: dict[str, Path]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    d7b = read_table(resolved["direction_c_decision"])
    d7e = read_table(resolved["defense_participation_decision"])
    if d7b.empty or str(d7b.iloc[0].get("decision_state", "")) != "12A7b_simple_backbone_supported_low_capacity_not_supported":
        reasons.append("12A7b_decision_mismatch")
    if d7b.empty or str(d7b.iloc[0].get("selected_primary_simple_backbone_tuple", "")) != "volatility_20d":
        reasons.append("12A7b_selected_tuple_mismatch")
    if d7b.empty or not np.isclose(float(d7b.iloc[0].get("selected_primary_X", np.nan)), 0.30):
        reasons.append("12A7b_selected_X_mismatch")
    if d7e.empty or str(d7e.iloc[0].get("decision_state", "")) != "12A7e_x030_defense_optimal_for_downside_not_winner":
        reasons.append("12A7e_decision_mismatch")
    return ("pass" if not reasons else "fail"), reasons


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    config = load_yaml(config_path)
    resolved = resolve_paths(config)
    paths = output_paths()
    paths["input_artifact_audit"].parent.mkdir(parents=True, exist_ok=True)
    input_audit = build_input_audit(resolved)
    write_df(paths["input_artifact_audit"], input_audit)
    if args.mode == "check-inputs":
        failed = input_audit.loc[~input_audit["read_status"].eq("pass") | input_audit["schema_status"].astype(str).str.startswith("missing_columns")]
        return 1 if not failed.empty else 0

    cache = StockDailyCache(resolved["stock_daily_qfq_dir"])
    thresholds = config["thresholds"]
    output_written: dict[str, Path] = {"input_artifact_audit": paths["input_artifact_audit"]}
    input_failed = bool(
        (~input_audit["read_status"].eq("pass") | input_audit["schema_status"].astype(str).str.startswith("missing_columns")).any()
    )
    lineage_gate, lineage_reasons = ("fail", ["input_audit_failure"]) if input_failed else lineage_status(resolved)

    full, split_audit, primitive_audit, regime_audit = build_full_universe_panel(resolved, config, cache)
    write_df(paths["full_universe_split_boundary_audit"], split_audit)
    write_df(paths["full_universe_primitive_feature_audit"], primitive_audit)
    write_df(paths["full_universe_primitive_feature_panel"], full)
    output_written.update(
        {
            "full_universe_split_boundary_audit": paths["full_universe_split_boundary_audit"],
            "full_universe_primitive_feature_audit": paths["full_universe_primitive_feature_audit"],
            "full_universe_primitive_feature_panel": paths["full_universe_primitive_feature_panel"],
        }
    )

    event = read_table(resolved["two_stage_event_universe"])
    c0_for_band = event.loc[
        bool_series(event["source_arm_is_c0"])
        & event["market_regime_bucket"].astype(str).eq("risk_on")
        & bool_series(event["stage_1_evaluable"])
    ].copy()
    c0_for_band["reference_date"] = c0_for_band["event_t0_date"].map(date_text)
    c0_primitive, _c0_prim_audit = primitive_features_for_rows(c0_for_band, cache, "reference_date", id_cols=["meta_event_id"])
    feat_matrix = read_table(resolved["two_stage_feature_matrix"])
    active_mask, active_audit = active_band_from_c0(full, c0_primitive, feat_matrix, thresholds)
    full["active_band_flag"] = active_mask.to_numpy()
    write_df(paths["full_universe_active_band_audit"], active_audit)
    output_written["full_universe_active_band_audit"] = paths["full_universe_active_band_audit"]

    specs = label_specs(config)
    write_df(paths["label_formula_audit"], label_formula_audit(specs))
    output_written["label_formula_audit"] = paths["label_formula_audit"]
    full["label_selection_scope"] = full["active_band_flag"] if bool(active_mask.any()) else full["primary_scope"]
    label_eval_base = full.loc[full["label_selection_scope"] & full["split"].astype(str).eq("train")].copy()
    label_eval_base["label_selection_scope"] = True
    label_summary = label_summary_grid_fast(label_eval_base, specs, cache, thresholds, "entry_pos", "entry_price")
    selected_label, label_selection = choose_label(label_summary, thresholds)
    selected_spec = next(s for s in specs if s["label_id"] == selected_label["label_id"])
    full_label_base = full.loc[full["primary_scope"]].copy()
    selected_full_label = compute_label(full_label_base, selected_spec, cache, "entry_pos", "entry_price")
    for col in selected_full_label.columns:
        full_label_base[col] = selected_full_label[col].to_numpy()
    full_label_base["label_id"] = selected_label["label_id"]
    full_label_base["horizon_sessions"] = int(selected_label["horizon_sessions"])
    write_df(paths["vol_scaled_label_panel_summary"], label_summary)
    write_df(paths["label_selection_train_audit"], label_selection)
    write_df(paths["full_pit_vol_scaled_label_panel"], full_label_base)
    output_written.update(
        {
            "vol_scaled_label_panel_summary": paths["vol_scaled_label_panel_summary"],
            "label_selection_train_audit": paths["label_selection_train_audit"],
            "full_pit_vol_scaled_label_panel": paths["full_pit_vol_scaled_label_panel"],
        }
    )

    c0, stage1_recon, feature_matrix = build_c0_matrix(resolved, selected_spec, cache)
    write_df(paths["stage1_anchor_x030_reconstruction_audit"], stage1_recon)
    write_df(paths["c0_vol_scaled_label_matrix"], c0)
    output_written.update(
        {
            "stage1_anchor_x030_reconstruction_audit": paths["stage1_anchor_x030_reconstruction_audit"],
            "c0_vol_scaled_label_matrix": paths["c0_vol_scaled_label_matrix"],
        }
    )

    feature_dict = read_table(resolved["two_stage_feature_dictionary"])
    c0_stage1_features, c0_stage2_features, full_features = feature_lists(c0, feature_dict, selected_spec)
    denoms = denominator_frames(c0, full_label_base, active_mask.loc[full_label_base.index] if set(full_label_base.index) <= set(active_mask.index) else full_label_base["active_band_flag"])

    c0_readouts: list[pd.DataFrame] = []
    full_readouts: list[pd.DataFrame] = []
    selection_readouts: list[pd.DataFrame] = []
    overlap_rows: list[pd.DataFrame] = []
    for den, (frame, view) in denoms.items():
        features = full_features if den.startswith("full_") else (c0_stage2_features if den == "c0_deployable_stage2_reference" else c0_stage1_features)
        readout, selection = separability_readout(frame, den, str(selected_label["label_id"]), view, features, thresholds, len(specs))
        selection_readouts.append(selection)
        if den.startswith("full_"):
            full_readouts.append(readout)
        else:
            c0_readouts.append(readout)
        overlap_rows.append(build_label_overlap_audit(frame, den, str(selected_label["label_id"]), int(selected_label["horizon_sessions"])))

    c0_sep = pd.concat(c0_readouts, ignore_index=True) if c0_readouts else pd.DataFrame()
    full_sep = pd.concat(full_readouts, ignore_index=True) if full_readouts else pd.DataFrame()
    feature_selection = pd.concat(selection_readouts, ignore_index=True) if selection_readouts else pd.DataFrame()
    overlap = pd.concat(overlap_rows, ignore_index=True) if overlap_rows else pd.DataFrame()
    write_df(paths["c0_separability_readout"], c0_sep)
    write_df(paths["full_universe_primitive_separability_readout"], full_sep)
    write_df(paths["label_overlap_effective_n_audit"], overlap)
    write_df(paths["search_multiplicity_audit"], feature_selection)
    output_written.update(
        {
            "c0_separability_readout": paths["c0_separability_readout"],
            "full_universe_primitive_separability_readout": paths["full_universe_primitive_separability_readout"],
            "label_overlap_effective_n_audit": paths["label_overlap_effective_n_audit"],
            "search_multiplicity_audit": paths["search_multiplicity_audit"],
        }
    )

    horizon_audit_rows = []
    for split in SPLITS:
        sub = split_frame(full_label_base, split)
        horizon_audit_rows.append(
            {
                "denominator_id": "full_pit_risk_on_universe_raw_diagnostic",
                "split": split,
                "label_id": selected_label["label_id"],
                "horizon_sessions": selected_label["horizon_sessions"],
                "row_n": int(len(sub)),
                "horizon_complete_n": int(sub["horizon_complete"].astype(bool).sum()) if len(sub) else 0,
                "horizon_complete_rate": safe_rate(sub["horizon_complete"].astype(bool).sum(), len(sub)) if len(sub) else np.nan,
            }
        )
    write_df(paths["horizon_completeness_by_split_audit"], pd.DataFrame(horizon_audit_rows))
    write_df(paths["pre_registered_threshold_audit"], threshold_audit(config))
    write_df(paths["c0_denominator_diversity_audit"], diversity_audit(denoms, thresholds))
    output_written.update(
        {
            "horizon_completeness_by_split_audit": paths["horizon_completeness_by_split_audit"],
            "pre_registered_threshold_audit": paths["pre_registered_threshold_audit"],
            "c0_denominator_diversity_audit": paths["c0_denominator_diversity_audit"],
        }
    )

    coupling = pd.DataFrame(
        [
            {
                "label_id": selected_label["label_id"],
                "vol_reference_id": selected_spec.get("vol_reference_id", ""),
                "vol_bucket": "all",
                "denominator_id": "all",
                "same_bar_conflict_rate": safe_rate(full_label_base["same_bar_conflict"].astype(bool).sum(), len(full_label_base)),
                "lower_first_rate": safe_rate(full_label_base["lower_first"].astype(bool).sum(), len(full_label_base)),
                "upper_first_rate": safe_rate(full_label_base["upper_first"].astype(bool).sum(), len(full_label_base)),
                "winner_positive_rate": safe_rate(full_label_base["winner_positive"].astype(bool).sum(), len(full_label_base)),
                "construction_coupled_status": "audited",
            }
        ]
    )
    denominator_contract = pd.DataFrame(
        [
            {"denominator_id": den, "label_reference_view": view, "row_n": len(frame), "contract_status": "pass"}
            for den, (frame, view) in denoms.items()
        ]
    )
    c0_base = pd.DataFrame(
        [
            {
                "denominator_id": den,
                "label_id": selected_label["label_id"],
                "row_n": len(frame),
                "horizon_complete_n": int(frame["horizon_complete"].astype(bool).sum()) if len(frame) else 0,
                "winner_positive_n": int(frame.loc[frame["horizon_complete"].astype(bool), "winner_positive"].astype(bool).sum()) if len(frame) else 0,
                "winner_base_rate": safe_rate(int(frame.loc[frame["horizon_complete"].astype(bool), "winner_positive"].astype(bool).sum()), int(frame["horizon_complete"].astype(bool).sum())) if len(frame) else np.nan,
            }
            for den, (frame, _view) in denoms.items()
            if den.startswith("c0_")
        ]
    )
    write_df(paths["label_feature_construction_coupling_audit"], coupling)
    write_df(paths["denominator_contract_audit"], denominator_contract)
    write_df(paths["c0_label_base_rate_readout"], c0_base)
    output_written.update(
        {
            "label_feature_construction_coupling_audit": paths["label_feature_construction_coupling_audit"],
            "denominator_contract_audit": paths["denominator_contract_audit"],
            "c0_label_base_rate_readout": paths["c0_label_base_rate_readout"],
        }
    )

    entry_n = len(denoms["c0_entry_t0"][0])
    utility = pd.DataFrame([utility_for_frame(frame, den, view, entry_n, thresholds) for den, (frame, view) in denoms.items()])
    common_recall, recall_cost, recall_floor = recall_audits(c0, denoms, thresholds)
    entry_total = float(utility.loc[utility["denominator_id"].eq("c0_entry_t0"), "utility_proxy_total_indexed_to_entry_n"].iloc[0])
    deploy_total = float(utility.loc[utility["denominator_id"].eq("c0_deployable_stage2_reference"), "utility_proxy_total_indexed_to_entry_n"].iloc[0])
    deterioration = max(0.0, entry_total - deploy_total) / abs(entry_total) if entry_total > 0 else (0.0 if deploy_total >= entry_total else 1.0)
    recall_cost.loc[recall_cost["denominator_id"].eq("c0_deployable_stage2_reference"), "recall_adjusted_utility_deterioration_vs_entry"] = deterioration
    write_df(paths["utility_proxy_readout"], utility)
    write_df(paths["common_entry_anchor_recall_audit"], common_recall)
    write_df(paths["continuation_recall_cost_audit"], recall_cost)
    write_df(paths["recall_floor_feasibility_audit"], recall_floor)
    output_written.update(
        {
            "utility_proxy_readout": paths["utility_proxy_readout"],
            "common_entry_anchor_recall_audit": paths["common_entry_anchor_recall_audit"],
            "continuation_recall_cost_audit": paths["continuation_recall_cost_audit"],
            "recall_floor_feasibility_audit": paths["recall_floor_feasibility_audit"],
        }
    )

    write_df(paths["stability_slice_audit"], pd.DataFrame())
    write_df(paths["bootstrap_replicates"], pd.DataFrame())
    output_written.update({"stability_slice_audit": paths["stability_slice_audit"], "bootstrap_replicates": paths["bootstrap_replicates"]})

    def robust_pass(readout: pd.DataFrame, den: str) -> bool:
        rows = readout.loc[
            readout["denominator_id"].eq(den)
            & readout["split"].eq("robustness")
            & readout["feature_id"].eq(readout["selected_feature_id"])
        ]
        return bool(len(rows) and rows.iloc[0]["search_adjusted_status"] == "pass")

    regime_gate_status = str(regime_audit["global_regime_calendar_status"].iloc[0]) if len(regime_audit) else "fail"
    regime_gate_pass = regime_gate_status in {"pass", "pass_with_missing_date_bypass"}
    retained_primary_scope_n = int(bool_series(full["primary_scope"]).sum())
    primary_retained_nonempty = retained_primary_scope_n > 0
    input_gate_status = (
        "pass"
        if (
            not input_failed
            and lineage_gate == "pass"
            and regime_gate_pass
            and primary_retained_nonempty
            and stage1_recon["stage1_anchor_reconstruction_status"].eq("pass").all()
        )
        else "fail"
    )
    selected_stable = str(selected_label["label_eligibility_status"]) == "eligible"
    active_eligible = bool(active_audit["active_band_cartography_gate_eligible"].fillna(False).any())
    deploy_recall = recall_cost.loc[recall_cost["denominator_id"].eq("c0_deployable_stage2_reference"), "recall_vs_entry"].iloc[0]
    deploy_utility_total = utility.loc[utility["denominator_id"].eq("c0_deployable_stage2_reference"), "utility_proxy_total_indexed_to_entry_n"].iloc[0]
    full_active_util = utility.loc[utility["denominator_id"].eq("full_pit_c0_comparable_active_band"), "utility_proxy_per_20d"].iloc[0]
    flags = {
        "12A7g_blocked_input_or_lineage_failure": input_gate_status != "pass",
        "12A7g_vol_scaled_label_drift_unresolved": input_gate_status == "pass" and not selected_stable,
        "12A7g_c0_vol_scaled_label_separable_continue_without_event_rebuild": input_gate_status == "pass"
        and selected_stable
        and robust_pass(c0_sep, "c0_deployable_stage2_reference")
        and pd.notna(deploy_utility_total)
        and deploy_utility_total > 0
        and pd.notna(deploy_recall)
        and deploy_recall >= float(thresholds["min_recall_vs_entry"])
        and deterioration <= float(thresholds["max_recall_adjusted_utility_deterioration"]),
        "12A7g_c0_posthoc_survivor_signal_diagnostic_only": input_gate_status == "pass"
        and selected_stable
        and robust_pass(c0_sep, "c0_posthoc_no_fast_fail_survivor")
        and not robust_pass(c0_sep, "c0_deployable_stage2_reference"),
        "12A7g_full_universe_more_separable_start_event_cartography": input_gate_status == "pass"
        and selected_stable
        and active_eligible
        and not robust_pass(c0_sep, "c0_entry_t0")
        and not robust_pass(c0_sep, "c0_deployable_stage2_reference")
        and robust_pass(full_sep, "full_pit_c0_comparable_active_band")
        and pd.notna(full_active_util)
        and full_active_util > 0,
        "12A7g_baserate_only_not_separable_stop_winner_selection": input_gate_status == "pass" and selected_stable,
    }
    decision_state = decision_from_flags(flags)
    next_allowed = {
        "12A7g_blocked_input_or_lineage_failure": "none",
        "12A7g_vol_scaled_label_drift_unresolved": "requirement_12a7g_label_form_stability_revision.md",
        "12A7g_c0_vol_scaled_label_separable_continue_without_event_rebuild": "requirement_12a7h_decoupled_defense_overlay_survivor_stage_winner_selector.md",
        "12A7g_c0_posthoc_survivor_signal_diagnostic_only": "requirement_12a7g2_stage2_decision_time_repair_or_event_cartography_triage.md",
        "12A7g_full_universe_more_separable_start_event_cartography": "requirement_12a7h_event_family_enrichment_cartography.md",
        "12A7g_baserate_only_not_separable_stop_winner_selection": "defense_overlay_plus_rule_based_participation_summary",
    }[decision_state]
    precedence = pd.DataFrame(
        [
            {
                "decision_state": state,
                "candidate_flag": bool(flags.get(state, False)),
                "precedence_rank": i + 1,
                "selected_flag": state == decision_state,
                "suppressed_by_selected": bool(flags.get(state, False)) and state != decision_state,
            }
            for i, state in enumerate(DECISION_PRECEDENCE)
        ]
    )
    decision = pd.DataFrame(
        [
            {
                "decision_state": decision_state,
                "next_allowed_requirement": next_allowed,
                "input_gate_status": input_gate_status,
                "lineage_gate_status": lineage_gate,
                "lineage_failure_reasons": ";".join(lineage_reasons),
                "global_regime_calendar_status": regime_gate_status,
                "global_regime_calendar_reason": regime_audit["global_regime_calendar_reason"].iloc[0] if len(regime_audit) else "missing_regime_audit",
                "missing_regime_date_bypassed_row_n": int(regime_audit["missing_regime_date_bypassed_row_n"].iloc[0]) if len(regime_audit) else 0,
                "missing_regime_date_bypassed_unique_date_n": int(regime_audit["missing_regime_date_bypassed_unique_date_n"].iloc[0]) if len(regime_audit) else 0,
                "retained_primary_scope_n": retained_primary_scope_n,
                "selected_label_id": selected_label["label_id"],
                "selected_label_type": selected_label["label_type"],
                "active_band_cartography_gate_eligible": active_eligible,
                "deployable_stage2_recall_vs_entry": deploy_recall,
                "recall_adjusted_utility_deterioration_vs_entry": deterioration,
            }
        ]
    )
    write_df(paths["decision_precedence_audit"], precedence)
    write_df(paths["vol_scaled_label_separability_decision"], decision)
    output_written.update(
        {
            "decision_precedence_audit": paths["decision_precedence_audit"],
            "vol_scaled_label_separability_decision": paths["vol_scaled_label_separability_decision"],
        }
    )
    write_text(paths["report"], render_report(decision, label_selection, utility, recall_cost))
    output_written["report"] = paths["report"]
    write_manifest(paths["manifest"], config_path, config, decision_state, output_written)
    output_written["manifest"] = paths["manifest"]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
TOPIC_SRC_DIR = TOPIC_ROOT / "src"

if str(TOPIC_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TOPIC_SRC_DIR))

from afml_big_winner.config import load_yaml, stable_hash  # noqa: E402
from afml_big_winner.manifest import file_sha256, git_revision  # noqa: E402


RUN_ID = "12A6c_two_stage_fast_fail_rejector_continuation_feasibility"
EXPERIMENT_ID = "12_state_change_event_backbone_rebuild_v0"
LEGACY_DIRECTORY_ID = "12_multi_k_winner_failure_path_morphology_research_v0"

CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_12a6c_two_stage_fast_fail_rejector_continuation_feasibility.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

PRIMARY_SOURCE_ARM = "C0_state_change"
SPLITS = ("all", "train", "validation", "robustness")
PRIMARY_MODEL_IDS = ("logistic_regression_l2", "shallow_decision_tree_max_depth_3")
FORBIDDEN_FEATURE_PATTERNS = (
    "episode_low",
    "episode_high",
    "future",
    "target_",
    "label_",
    "winner_",
    "fast_fail_",
    "false_repair_",
    "bad_side_",
    "inside_window",
)


EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "meta_label_event_universe": (
        "meta_event_id",
        "source_arm_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "trade_open_date",
        "trade_open_pos",
        "trade_open_price",
        "event_split",
        "board_bucket",
        "market_regime_bucket",
        "primary_family_id",
    ),
    "meta_label_event_targets": ("meta_event_id", "source_arm_id", "event_split", "instrument"),
    "meta_label_feature_dictionary": ("feature_name", "feature_group", "allowed_for_primary_model", "pit_status"),
    "meta_label_feature_matrix": ("meta_event_id", "instrument", "event_split"),
    "entry_forward_path_cache": (
        "path_key",
        "instrument",
        "entry_date",
        "entry_pos",
        "entry_price",
        "entry_blocked",
        "horizon_complete_20d",
        "time_to_lower_minus_10_20d",
    ),
    "matched_random_sampled_entries": (
        "seed",
        "sample_draw_id",
        "path_key",
        "split",
        "board_bucket",
        "calendar_month",
        "random_trade_open_date",
        "instrument",
        "entry_pos",
        "entry_price",
        "replacement_draw_index",
        "sample_weight",
    ),
    "fast_fail_uplift_vs_baselines": ("scope_id", "split", "horizon_sessions", "lower_barrier_pct", "c0_fast_fail_rate"),
    "conditional_continuation_readout": (
        "population_id",
        "scope_id",
        "split",
        "upper_barrier_pct",
        "upper_touch_rate_given_no_fast_fail",
    ),
    "fast_fail_decision": ("decision_state",),
    "state_change_generation_decision": ("decision", "input_gate_pass", "next_allowed_requirement"),
    "r_core_demote_or_keep_decision": ("decision", "population_bridge_status", "next_allowed_requirement"),
    "global_regime_calendar": ("date", "daily_regime_bucket", "daily_regime_conflict_flag"),
    "pit_executable_daily": ("usable_trade_date", "instrument", "is_listed", "is_st", "is_suspended"),
    "manifest_12a4": (),
    "manifest_12a6b": (),
    "requirement": (),
    "stock_daily_csv_dir": (),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 12A6c two-stage fast-fail rejector continuation feasibility.")
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
        "event_universe": TABLE_DIR / "two_stage_event_universe.csv.gz",
        "scope_exclusion_audit": TABLE_DIR / "two_stage_scope_exclusion_audit.csv",
        "feature_dictionary": TABLE_DIR / "two_stage_feature_dictionary.csv",
        "feature_pit_audit": TABLE_DIR / "two_stage_feature_pit_audit.csv",
        "event_targets": TABLE_DIR / "two_stage_event_targets.csv.gz",
        "realized_path_redundancy_audit": TABLE_DIR / "realized_path_feature_redundancy_audit.csv",
        "stage_threshold_health": TABLE_DIR / "stage_threshold_health.csv",
        "stage_1_model_card": TABLE_DIR / "stage_1_model_card.csv",
        "stage_2_model_card": TABLE_DIR / "stage_2_model_card.csv",
        "stage_1_score_bucket_readout": TABLE_DIR / "stage_1_score_bucket_readout.csv",
        "stage_2_score_bucket_readout": TABLE_DIR / "stage_2_score_bucket_readout.csv",
        "stage_1_single_feature_frontier": TABLE_DIR / "stage_1_single_feature_frontier.csv",
        "stage_2_single_feature_frontier": TABLE_DIR / "stage_2_single_feature_frontier.csv",
        "stage_1_random_same_budget_audit": TABLE_DIR / "stage_1_random_same_budget_audit.csv",
        "stage_2_random_same_budget_audit": TABLE_DIR / "stage_2_random_same_budget_audit.csv",
        "stage_2_ablation_readout": TABLE_DIR / "stage_2_ablation_readout.csv",
        "stage_1_rejector_readout": TABLE_DIR / "stage_1_rejector_readout.csv",
        "stage_2_continuation_readout": TABLE_DIR / "stage_2_continuation_readout.csv",
        "stage_1_label_grid_readout": TABLE_DIR / "stage_1_label_grid_readout.csv",
        "stage_2_target_grid_readout": TABLE_DIR / "stage_2_target_grid_readout.csv",
        "decision": TABLE_DIR / "two_stage_decision.csv",
        "split_time_boundary_audit": TABLE_DIR / "split_time_boundary_audit.csv",
        "feature_matrix": LOCAL_CACHE_DIR / "two_stage_feature_matrix.parquet",
        "stage2_path_cache": LOCAL_CACHE_DIR / "stage2_path_cache.parquet",
        "report": REPORT_DIR / "two_stage_fast_fail_rejector_continuation_report.md",
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


def numeric(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


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


def barrier_suffix(value: float) -> str:
    sign = "minus" if value < 0 else "plus"
    return f"{sign}_{abs(value):.2f}".replace("0.", "").replace(".", "")


def stable_path_key(instrument: Any, entry_date: Any, entry_pos: Any, entry_price: Any) -> str:
    price = "" if pd.isna(entry_price) else f"{float(entry_price):.8f}"
    raw = f"{instrument}|{date_text(entry_date)}|{int(entry_pos) if pd.notna(entry_pos) else ''}|{price}"
    import hashlib

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class StockDailyCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._cache: dict[str, pd.DataFrame | None] = {}
        self.schema_failures: dict[str, str] = {}

    def get(self, instrument: str) -> pd.DataFrame | None:
        instrument = str(instrument)
        if instrument in self._cache:
            return self._cache[instrument]
        path = self.directory / f"{instrument}.csv"
        if not path.exists():
            self._cache[instrument] = None
            self.schema_failures[instrument] = "missing_price_file"
            return None
        daily = pd.read_csv(path, low_memory=False)
        required = {"date", "open", "high", "low", "close"}
        missing = required - set(daily.columns)
        if missing:
            self._cache[instrument] = None
            self.schema_failures[instrument] = "missing_columns:" + ";".join(sorted(missing))
            return None
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        daily = daily.sort_values("date", kind="stable").reset_index(drop=True)
        for col in ("open", "high", "low", "close", "volume", "turnover_rate"):
            if col in daily.columns:
                daily[col] = pd.to_numeric(daily[col], errors="coerce")
        self._cache[instrument] = daily
        return daily


def build_input_artifact_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for artifact_id, required_cols in EXPECTED_INPUT_COLUMNS.items():
        raw = config.get("paths", {}).get(artifact_id, artifact_id)
        path = topic_path(raw)
        is_dir = artifact_id == "stock_daily_csv_dir"
        exists = path.is_dir() if is_dir else path.is_file()
        read_status = "pass" if exists else "missing"
        schema_status = "not_checked"
        row_count = np.nan
        if exists and not is_dir and required_cols:
            try:
                frame = read_table(path, nrows=5) if "".join(path.suffixes).endswith(".csv") or "".join(path.suffixes).endswith(".csv.gz") else read_table(path)
                missing = set(required_cols) - set(frame.columns)
                schema_status = "pass" if not missing else "missing_columns:" + ";".join(sorted(missing))
                row_count = len(frame) if len(frame) < 10 else np.nan
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
                schema_status = "not_checked"
        elif exists:
            schema_status = "pass"
        rows.append(
            {
                "artifact_id": artifact_id,
                "path": str(path),
                "read_status": read_status,
                "schema_status": schema_status,
                "sha256": path_sha(path) if path.is_file() else "",
                "row_count_sample": row_count,
            }
        )
    return pd.DataFrame(rows)


def first_nonempty(frame: pd.DataFrame, *columns: str) -> str:
    for col in columns:
        if col in frame and not frame[col].dropna().empty:
            return str(frame[col].dropna().iloc[0])
    return ""


def evaluate_input_gates(audit: pd.DataFrame, resolved: dict[str, Path], c0: pd.DataFrame) -> tuple[bool, str]:
    reasons: list[str] = []
    if not audit["read_status"].astype(str).eq("pass").all():
        bad = audit.loc[~audit["read_status"].astype(str).eq("pass"), "artifact_id"].astype(str).tolist()
        reasons.append("read_status:" + ",".join(bad))
    if not audit["schema_status"].astype(str).eq("pass").all():
        bad = audit.loc[~audit["schema_status"].astype(str).eq("pass"), "artifact_id"].astype(str).tolist()
        reasons.append("schema_status:" + ",".join(bad))
    if len(c0) != 15113:
        reasons.append(f"c0_event_n_expected_15113_actual_{len(c0)}")

    try:
        fast_fail_decision = read_table(resolved["fast_fail_decision"])
        state = first_nonempty(fast_fail_decision, "decision_state")
        if not ("partial" in state or "supported" in state):
            reasons.append(f"12A6b_decision_not_partial_or_supported:{state}")
        if "input_gate_pass" in fast_fail_decision and not boolish(fast_fail_decision["input_gate_pass"].iloc[0]):
            reasons.append("12A6b_input_gate_failed")
    except Exception as exc:
        reasons.append(f"12A6b_decision_read_error:{type(exc).__name__}")

    try:
        state_change_decision = read_table(resolved["state_change_generation_decision"])
        state = first_nonempty(state_change_decision, "decision", "decision_state")
        if "supported" not in state:
            reasons.append(f"12A2_decision_not_supported:{state}")
    except Exception as exc:
        reasons.append(f"12A2_decision_read_error:{type(exc).__name__}")

    try:
        r_core_decision = read_table(resolved["r_core_demote_or_keep_decision"])
        if not first_nonempty(r_core_decision, "decision", "decision_state"):
            reasons.append("12A0_12A1_decision_empty")
    except Exception as exc:
        reasons.append(f"12A0_12A1_decision_read_error:{type(exc).__name__}")

    try:
        regime = read_table(resolved["global_regime_calendar"], usecols=["daily_regime_conflict_flag"])
        if bool_series(regime["daily_regime_conflict_flag"]).any():
            reasons.append("global_regime_calendar_conflict_flag_true")
    except Exception as exc:
        reasons.append(f"global_regime_calendar_read_error:{type(exc).__name__}")

    return not reasons, ";".join(reasons)


def normalize_c0_universe(universe: pd.DataFrame, path_cache: pd.DataFrame) -> pd.DataFrame:
    c0 = universe.loc[
        universe["source_arm_id"].astype(str).eq(PRIMARY_SOURCE_ARM)
        & universe["market_regime_bucket"].astype(str).eq("risk_on")
    ].copy()
    c0["event_t0_date"] = c0["event_t0_date"].map(date_text)
    c0["trade_open_date"] = c0["trade_open_date"].map(date_text)
    c0["event_t0_pos"] = numeric(c0["event_t0_pos"])
    c0["trade_open_pos"] = numeric(c0["trade_open_pos"])
    c0["trade_open_price"] = numeric(c0["trade_open_price"])
    c0["split"] = c0["event_split"].astype(str)
    c0["calendar_month"] = c0["event_t0_date"].map(month_text)
    c0["calendar_year"] = c0["event_t0_date"].map(year_text)
    c0["entry_date"] = c0["trade_open_date"]
    c0["entry_pos"] = c0["trade_open_pos"]
    c0["entry_price"] = c0["trade_open_price"]
    c0["path_key"] = [
        stable_path_key(inst, date, pos, price)
        for inst, date, pos, price in zip(c0["instrument"], c0["entry_date"], c0["entry_pos"], c0["entry_price"])
    ]
    keep_cols = [
        "path_key",
        "entry_blocked",
        "horizon_complete_10d",
        "horizon_complete_20d",
        "min_low_return_20d",
        "time_to_lower_minus_06_10d",
        "time_to_lower_minus_08_10d",
        "time_to_lower_minus_10_10d",
        "time_to_lower_minus_12_10d",
        "time_to_lower_minus_15_10d",
        "time_to_lower_minus_20_10d",
        "time_to_lower_minus_06_20d",
        "time_to_lower_minus_08_20d",
        "time_to_lower_minus_10_20d",
        "time_to_lower_minus_12_20d",
        "time_to_lower_minus_15_20d",
        "time_to_lower_minus_20_20d",
    ]
    merged = c0.merge(path_cache[[col for col in keep_cols if col in path_cache.columns]], on="path_key", how="left")
    merged["stage_1_evaluable"] = (~bool_series(merged["entry_blocked"])) & bool_series(merged["horizon_complete_20d"])
    merged["stage_1_fast_fail_target"] = merged["stage_1_evaluable"] & merged["time_to_lower_minus_10_20d"].notna()
    merged["no_fast_fail_L10_H20"] = merged["stage_1_evaluable"] & (~merged["stage_1_fast_fail_target"])
    return merged.reset_index(drop=True)


def build_stage2_path_cache(paths: pd.DataFrame, stock_cache: StockDailyCache, config: dict[str, Any], *, include_realized: bool) -> pd.DataFrame:
    h2_values = sorted(set(int(x) for x in config["stage_2"]["horizon_grid_h2"]))
    upper_values = sorted(set(float(x) for x in config["stage_2"]["upper_barrier_grid"]))
    lower_values = sorted(set(float(x) for x in config["stage_2"]["lower_barrier_grid"]))
    rows: list[dict[str, Any]] = []
    unique = paths.loc[paths["path_key"].astype(str).ne("")].drop_duplicates("path_key").copy()
    for row in unique.itertuples(index=False):
        inst = str(row.instrument)
        daily = stock_cache.get(inst)
        entry_pos = int(row.entry_pos) if pd.notna(row.entry_pos) else -1
        entry_price = float(row.entry_price) if pd.notna(row.entry_price) else np.nan
        out: dict[str, Any] = {
            "path_key": str(row.path_key),
            "instrument": inst,
            "entry_pos": entry_pos if entry_pos >= 0 else np.nan,
            "entry_price": entry_price,
            "stage_2_decision_pos": entry_pos + 20 if entry_pos >= 0 else np.nan,
            "stage_2_reference_pos": entry_pos + 21 if entry_pos >= 0 else np.nan,
            "stage_2_entry_blocked": True,
            "stage_2_reference_price": np.nan,
        }
        if daily is None or daily.empty or entry_pos < 0 or pd.isna(entry_price):
            rows.append(fill_stage2_missing(out, h2_values, upper_values, lower_values, include_realized))
            continue
        open_arr = daily["open"].to_numpy(dtype=float)
        high = daily["high"].to_numpy(dtype=float)
        low = daily["low"].to_numpy(dtype=float)
        close = daily["close"].to_numpy(dtype=float)
        ref_pos = entry_pos + 21
        if ref_pos < len(daily) and np.isfinite(open_arr[ref_pos]) and open_arr[ref_pos] > 0:
            out["stage_2_entry_blocked"] = False
            out["stage_2_reference_price"] = float(open_arr[ref_pos])
        for h2 in h2_values:
            complete = (not out["stage_2_entry_blocked"]) and ref_pos + h2 < len(daily)
            out[f"stage_2_horizon_complete_{h2}d"] = bool(complete)
            if not complete:
                for upper in upper_values:
                    for lower in lower_values:
                        out[f"continuation_U{int(round(upper * 100))}_L{int(round(abs(lower) * 100))}_H2_{h2}"] = np.nan
                continue
            h_slice = high[ref_pos : ref_pos + h2 + 1]
            l_slice = low[ref_pos : ref_pos + h2 + 1]
            price = float(out["stage_2_reference_price"])
            for upper in upper_values:
                upper_hits = np.flatnonzero(h_slice >= price * (1.0 + upper))
                upper_first = int(upper_hits[0]) if len(upper_hits) else None
                for lower in lower_values:
                    lower_hits = np.flatnonzero(l_slice <= price * (1.0 + lower))
                    lower_first = int(lower_hits[0]) if len(lower_hits) else None
                    continuation = upper_first is not None and (lower_first is None or upper_first < lower_first)
                    out[f"continuation_U{int(round(upper * 100))}_L{int(round(abs(lower) * 100))}_H2_{h2}"] = bool(continuation)
        if include_realized:
            out.update(realized_path_features(daily, entry_pos, entry_price))
        rows.append(out)
    return pd.DataFrame(rows)


def fill_stage2_missing(
    out: dict[str, Any],
    h2_values: list[int],
    upper_values: list[float],
    lower_values: list[float],
    include_realized: bool,
) -> dict[str, Any]:
    for h2 in h2_values:
        out[f"stage_2_horizon_complete_{h2}d"] = False
        for upper in upper_values:
            for lower in lower_values:
                out[f"continuation_U{int(round(upper * 100))}_L{int(round(abs(lower) * 100))}_H2_{h2}"] = np.nan
    if include_realized:
        for key in REALIZED_FEATURES:
            out[key] = np.nan
    return out


REALIZED_FEATURES = [
    "realized_ret_to_close_20d",
    "realized_max_high_return_0_20d",
    "realized_min_low_return_0_20d",
    "realized_close_to_max_high_drawup_0_20d",
    "realized_close_to_min_low_drawdown_0_20d",
    "realized_path_volatility_0_20d",
    "realized_up_session_ratio_0_20d",
    "realized_max_consecutive_up_sessions_0_20d",
    "realized_max_consecutive_down_sessions_0_20d",
    "sessions_since_min_low_0_20d",
    "sessions_since_max_high_0_20d",
    "realized_close_above_entry_session_ratio_0_20d",
    "realized_turnover_zscore_trend_0_20d",
    "realized_volume_zscore_trend_0_20d",
    "realized_distance_to_20d_high_at_day20",
    "realized_distance_to_60d_high_at_day20",
    "realized_ma_5_20_spread_at_day20",
    "realized_late_window_ret_10_20d",
    "realized_early_window_ret_0_10d",
    "realized_momentum_accel_early_late_0_20d",
]


def max_run(values: np.ndarray, target: bool) -> int:
    best = 0
    cur = 0
    for value in values:
        if bool(value) is target:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def slope_or_nan(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return np.nan
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, values, 1)[0])


def realized_path_features(daily: pd.DataFrame, entry_pos: int, entry_price: float) -> dict[str, float]:
    out = {key: np.nan for key in REALIZED_FEATURES}
    if entry_pos < 0 or entry_pos + 20 >= len(daily) or pd.isna(entry_price) or entry_price <= 0:
        return out
    window = daily.iloc[entry_pos : entry_pos + 21].copy()
    if len(window) < 17:
        return out
    open_arr = window["open"].to_numpy(dtype=float)
    high = window["high"].to_numpy(dtype=float)
    low = window["low"].to_numpy(dtype=float)
    close = window["close"].to_numpy(dtype=float)
    valid = np.isfinite(open_arr) & np.isfinite(high) & np.isfinite(low) & np.isfinite(close)
    if valid.mean() < 0.80:
        return out
    returns = pd.Series(close).pct_change().to_numpy(dtype=float)
    up = returns[1:] > 0
    day20_close = close[-1]
    max_high_idx = int(np.nanargmax(high))
    min_low_idx = int(np.nanargmin(low))
    out["realized_ret_to_close_20d"] = float(day20_close / entry_price - 1.0)
    out["realized_max_high_return_0_20d"] = float(np.nanmax(high) / entry_price - 1.0)
    out["realized_min_low_return_0_20d"] = float(np.nanmin(low) / entry_price - 1.0)
    out["realized_close_to_max_high_drawup_0_20d"] = float(day20_close / np.nanmax(high) - 1.0)
    out["realized_close_to_min_low_drawdown_0_20d"] = float(day20_close / np.nanmin(low) - 1.0)
    out["realized_path_volatility_0_20d"] = float(np.nanstd(returns[1:]))
    out["realized_up_session_ratio_0_20d"] = float(np.nanmean(up)) if len(up) else np.nan
    out["realized_max_consecutive_up_sessions_0_20d"] = max_run(up, True)
    out["realized_max_consecutive_down_sessions_0_20d"] = max_run(up, False)
    out["sessions_since_min_low_0_20d"] = int(20 - min_low_idx)
    out["sessions_since_max_high_0_20d"] = int(20 - max_high_idx)
    out["realized_close_above_entry_session_ratio_0_20d"] = float(np.nanmean(close >= entry_price))
    if "turnover_rate" in window:
        out["realized_turnover_zscore_trend_0_20d"] = slope_or_nan(window["turnover_rate"].to_numpy(dtype=float))
    if "volume" in window:
        volume = window["volume"].to_numpy(dtype=float)
        out["realized_volume_zscore_trend_0_20d"] = slope_or_nan(np.log1p(volume))
    hist20 = daily.iloc[max(0, entry_pos + 20 - 19) : entry_pos + 21]
    hist60 = daily.iloc[max(0, entry_pos + 20 - 59) : entry_pos + 21]
    out["realized_distance_to_20d_high_at_day20"] = float(day20_close / numeric(hist20["high"]).max() - 1.0)
    out["realized_distance_to_60d_high_at_day20"] = float(day20_close / numeric(hist60["high"]).max() - 1.0)
    ma5 = float(numeric(daily.iloc[max(0, entry_pos + 16) : entry_pos + 21]["close"]).mean())
    ma20 = float(numeric(hist20["close"]).mean())
    out["realized_ma_5_20_spread_at_day20"] = safe_rate(ma5, ma20) - 1.0
    out["realized_early_window_ret_0_10d"] = float(close[10] / close[0] - 1.0) if close[0] else np.nan
    out["realized_late_window_ret_10_20d"] = float(close[20] / close[10] - 1.0) if close[10] else np.nan
    out["realized_momentum_accel_early_late_0_20d"] = out["realized_late_window_ret_10_20d"] - out["realized_early_window_ret_0_10d"]
    return out


def build_feature_dictionary(base: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    rows = []
    t0_features = []
    for row in base.itertuples(index=False):
        name = str(row.feature_name)
        allowed = boolish(getattr(row, "allowed_for_primary_model", False))
        forbidden = any(pattern in name for pattern in FORBIDDEN_FEATURE_PATTERNS)
        allowed = allowed and not forbidden
        if allowed:
            t0_features.append(name)
        rows.append(
            {
                "feature_name": name,
                "feature_group": getattr(row, "feature_group", ""),
                "source_artifact": "12A4_meta_label_event_feature_matrix",
                "calculation_rule": "inherited_from_12A4",
                "availability_time": getattr(row, "feature_availability_time", "event_t0_close"),
                "lookback_window": "",
                "missing_policy": "train_median_imputation",
                "pit_status": getattr(row, "pit_status", "pass"),
                "allowed_for_stage_1": bool(allowed),
                "allowed_for_stage_2": bool(allowed),
            }
        )
    for name in REALIZED_FEATURES:
        rows.append(
            {
                "feature_name": name,
                "feature_group": "realized_path_0_20d",
                "source_artifact": "qfq_daily",
                "calculation_rule": "closed_interval_entry_pos_to_entry_pos_plus_20",
                "availability_time": "close at entry_pos + 20",
                "lookback_window": "[entry_pos, entry_pos + 20]",
                "missing_policy": "null_if_effective_window_lt_80pct",
                "pit_status": "pass",
                "allowed_for_stage_1": False,
                "allowed_for_stage_2": True,
            }
        )
    return pd.DataFrame(rows), t0_features, REALIZED_FEATURES.copy()


def feature_pit_audit(dictionary: pd.DataFrame, matrix: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in dictionary.itertuples(index=False):
        name = str(row.feature_name)
        coverage = safe_rate(matrix[name].notna().sum(), len(matrix)) if name in matrix.columns else 0.0
        rows.append(
            {
                "feature_name": name,
                "feature_group": row.feature_group,
                "availability_time": row.availability_time,
                "pit_status": row.pit_status if coverage >= 0.80 or row.feature_group != "realized_path_0_20d" else "diagnostic_sparse_coverage",
                "coverage_rate": coverage,
                "allowed_for_stage_1": row.allowed_for_stage_1,
                "allowed_for_stage_2": row.allowed_for_stage_2 and coverage >= 0.80,
            }
        )
    return pd.DataFrame(rows)


def redundancy_audit(matrix: pd.DataFrame) -> pd.DataFrame:
    rows = []
    anchor = "realized_ret_to_close_20d"
    for name in REALIZED_FEATURES:
        if name not in matrix:
            corr = np.nan
            coverage = 0.0
        else:
            coverage = safe_rate(matrix[name].notna().sum(), len(matrix))
            corr = numeric(matrix[name]).corr(numeric(matrix[anchor])) if anchor in matrix and name != anchor else 1.0
        max_abs = abs(corr) if pd.notna(corr) else np.nan
        allowed = bool(pd.notna(max_abs) and max_abs < 0.95 and coverage >= 0.80)
        rows.append(
            {
                "feature_name": name,
                "split": "all",
                "coverage_rate": coverage,
                "pearson_corr_vs_realized_ret_to_close_20d": corr,
                "spearman_corr_vs_realized_ret_to_close_20d": numeric(matrix[name]).corr(numeric(matrix[anchor]), method="spearman") if name in matrix and anchor in matrix else np.nan,
                "max_abs_redundancy_corr": max_abs,
                "redundancy_status": "pass" if allowed else "diagnostic_only_redundant_or_sparse",
                "allowed_for_stage_2_after_audit": allowed,
            }
        )
    return pd.DataFrame(rows)


def impute_by_train(frame: pd.DataFrame, feature_cols: list[str], split_col: str = "split") -> tuple[pd.DataFrame, dict[str, float]]:
    out = frame.copy()
    train = out.loc[out[split_col].astype(str).eq("train")]
    medians: dict[str, float] = {}
    for col in feature_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        median = float(train[col].median()) if col in train and train[col].notna().any() else 0.0
        if not np.isfinite(median):
            median = 0.0
        medians[col] = median
        out[col] = out[col].fillna(median)
    return out, medians


def fit_models(
    frame: pd.DataFrame,
    feature_cols: list[str],
    target_col: str,
    score_col: str,
    config: dict[str, Any],
    *,
    stage: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fit_frame, medians = impute_by_train(frame, feature_cols)
    train = fit_frame.loc[fit_frame["split"].astype(str).eq("train")].copy()
    y = bool_series(train[target_col]).astype(int)
    models: list[tuple[str, str, Any, bool]] = [
        (
            "logistic_regression_l2",
            "logistic_regression_l2",
            LogisticRegression(max_iter=int(config["models"]["logistic_max_iter"]), penalty="l2", solver="liblinear"),
            True,
        ),
        (
            "shallow_decision_tree_max_depth_3",
            "shallow_decision_tree_max_depth_3",
            DecisionTreeClassifier(
                max_depth=int(config["models"]["tree_max_depth"]),
                min_samples_leaf=int(config["models"]["tree_min_samples_leaf"]),
                random_state=int(config["models"]["random_state"]),
            ),
            True,
        ),
    ]
    scored_parts = []
    cards = []
    X_all = fit_frame[feature_cols].to_numpy(dtype=float)
    X_train = train[feature_cols].to_numpy(dtype=float)
    for model_id, family, model, supported_gate_allowed in models:
        scored = fit_frame.copy()
        try:
            if len(train) == 0 or y.nunique() < 2:
                raise ValueError("insufficient_train_labels")
            model.fit(X_train, y)
            score = model.predict_proba(X_all)[:, 1]
            fit_status = "fit"
        except Exception as exc:
            score = np.full(len(fit_frame), np.nan)
            fit_status = f"fit_error:{type(exc).__name__}"
        scored["model_id"] = model_id
        scored["model_family"] = family
        scored[score_col] = score
        scored_parts.append(scored)
        cards.append(
            {
                "stage": stage,
                "model_id": model_id,
                "model_family": family,
                "primary_or_challenger": "primary",
                "fit_status": fit_status,
                "fit_split": "train",
                "target_id": target_col,
                "feature_n": len(feature_cols),
                "feature_list_hash": stable_hash(feature_cols),
                "hyperparameter_json": json.dumps(getattr(model, "get_params", lambda: {})(), sort_keys=True, default=str),
                "class_weight_policy": "none",
                "train_event_n": int(len(train)),
                "train_positive_rate": float(y.mean()) if len(y) else np.nan,
                "threshold_selection_source": "train_only_fixed_budget",
                "diagnostic_only_flag": not supported_gate_allowed,
            }
        )
    lg_scored, lg_card = lightgbm_challenger(fit_frame, train, y, feature_cols, target_col, score_col, config, stage=stage)
    if not lg_scored.empty:
        scored_parts.append(lg_scored)
    if not lg_card.empty:
        cards.extend(lg_card.to_dict("records"))
    return pd.concat(scored_parts, ignore_index=True), pd.DataFrame(cards)


def lightgbm_challenger(
    frame: pd.DataFrame,
    train: pd.DataFrame,
    y: pd.Series,
    feature_cols: list[str],
    target_col: str,
    score_col: str,
    config: dict[str, Any],
    *,
    stage: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    model_id = "lightgbm_challenger_diagnostic_only"
    if importlib.util.find_spec("lightgbm") is None:
        return pd.DataFrame(), pd.DataFrame(
            [
                {
                    "stage": stage,
                    "model_id": model_id,
                    "model_family": model_id,
                    "primary_or_challenger": "challenger",
                    "fit_status": "skipped_dependency_unavailable",
                    "fit_split": "train",
                    "target_id": target_col,
                    "feature_n": len(feature_cols),
                    "feature_list_hash": stable_hash(feature_cols),
                    "hyperparameter_json": "{}",
                    "class_weight_policy": "none",
                    "train_event_n": int(len(train)),
                    "train_positive_rate": float(y.mean()) if len(y) else np.nan,
                    "threshold_selection_source": "train_only_fixed_budget",
                    "diagnostic_only_flag": True,
                }
            ]
        )
    try:
        from lightgbm import LGBMClassifier

        model = LGBMClassifier(
            objective="binary",
            boosting_type="gbdt",
            num_leaves=15,
            max_depth=3,
            min_data_in_leaf=100,
            n_estimators=100,
            random_state=int(config["models"]["random_state"]),
            verbose=-1,
        )
        if len(train) == 0 or y.nunique() < 2:
            raise ValueError("insufficient_train_labels")
        model.fit(train[feature_cols], y)
        scored = frame.copy()
        scored["model_id"] = model_id
        scored["model_family"] = model_id
        scored[score_col] = model.predict_proba(frame[feature_cols])[:, 1]
        status = "fit"
        params = model.get_params()
    except Exception as exc:  # pragma: no cover
        scored = pd.DataFrame()
        status = f"fit_error:{type(exc).__name__}"
        params = {}
    card = pd.DataFrame(
        [
            {
                "stage": stage,
                "model_id": model_id,
                "model_family": model_id,
                "primary_or_challenger": "challenger",
                "fit_status": status,
                "fit_split": "train",
                "target_id": target_col,
                "feature_n": len(feature_cols),
                "feature_list_hash": stable_hash(feature_cols),
                "hyperparameter_json": json.dumps(params, sort_keys=True, default=str),
                "class_weight_policy": "none",
                "train_event_n": int(len(train)),
                "train_positive_rate": float(y.mean()) if len(y) else np.nan,
                "threshold_selection_source": "train_only_fixed_budget",
                "diagnostic_only_flag": True,
            }
        ]
    )
    return scored, card


def assign_fixed_budget_flags(
    scored: pd.DataFrame,
    *,
    score_col: str,
    flag_col: str,
    budget: float,
    lower_is_better: bool,
    split_col: str = "split",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = scored.copy()
    out[flag_col] = False
    health_rows = []
    tie_cols = [col for col in ("instrument", "event_t0_date", "entry_date", "meta_event_id", "path_key") if col in out.columns]
    for model_id, model_group in out.groupby("model_id", sort=False):
        train_idx = model_group.loc[model_group[split_col].astype(str).eq("train")].index
        train_ranked = out.loc[train_idx].copy()
        train_ranked["_score_sort"] = pd.to_numeric(train_ranked[score_col], errors="coerce")
        train_ranked["_score_sort"] = train_ranked["_score_sort"].fillna(np.inf if lower_is_better else -np.inf)
        ascending = [lower_is_better] + [True] * len(tie_cols)
        train_ranked = train_ranked.sort_values(["_score_sort"] + tie_cols, ascending=ascending, kind="stable")
        n_train = int(round(float(budget) * len(train_ranked)))
        n_train = min(max(n_train, 0), len(train_ranked))
        selected_train_idx = train_ranked.index[:n_train]
        if len(train_ranked) == 0:
            threshold = np.nan
            boundary_tie_fraction = 0.0
        elif n_train <= 0:
            threshold = -np.inf if lower_is_better else np.inf
            boundary_tie_fraction = 0.0
        elif n_train >= len(train_ranked):
            threshold = np.inf if lower_is_better else -np.inf
            boundary_tie_fraction = 1.0
        else:
            threshold = float(train_ranked.iloc[n_train - 1]["_score_sort"])
            if lower_is_better:
                better_train_n = int((train_ranked["_score_sort"] < threshold).sum())
            else:
                better_train_n = int((train_ranked["_score_sort"] > threshold).sum())
            tie_train_n = int((train_ranked["_score_sort"] == threshold).sum())
            selected_tie_train_n = max(0, n_train - better_train_n)
            boundary_tie_fraction = safe_rate(selected_tie_train_n, tie_train_n)
            boundary_tie_fraction = float(0.0 if pd.isna(boundary_tie_fraction) else boundary_tie_fraction)

        split_values = ["all"] + sorted(model_group[split_col].dropna().astype(str).unique())
        for split in split_values:
            idx = model_group.index if split == "all" else model_group.loc[model_group[split_col].astype(str).eq(split)].index
            split_frame_local = out.loc[idx].copy()
            split_frame_local["_score_sort"] = pd.to_numeric(split_frame_local[score_col], errors="coerce")
            split_frame_local["_score_sort"] = split_frame_local["_score_sort"].fillna(np.inf if lower_is_better else -np.inf)
            if split == "train":
                selected_idx = selected_train_idx
            elif not np.isfinite(threshold):
                if pd.isna(threshold):
                    selected_idx = split_frame_local.head(0).index
                elif (lower_is_better and threshold == np.inf) or ((not lower_is_better) and threshold == -np.inf):
                    selected_idx = split_frame_local.index
                else:
                    selected_idx = split_frame_local.head(0).index
            else:
                if lower_is_better:
                    better = split_frame_local["_score_sort"] < threshold
                else:
                    better = split_frame_local["_score_sort"] > threshold
                selected_idx = split_frame_local.loc[better].index
                ties = split_frame_local.loc[split_frame_local["_score_sort"].eq(threshold)].copy()
                if not ties.empty and boundary_tie_fraction > 0:
                    ties = ties.sort_values(tie_cols, ascending=[True] * len(tie_cols), kind="stable") if tie_cols else ties.sort_index(kind="stable")
                    n_ties = int(round(boundary_tie_fraction * len(ties)))
                    n_ties = min(max(n_ties, 0), len(ties))
                    selected_idx = selected_idx.append(ties.index[:n_ties])
            if split != "all":
                out.loc[selected_idx, flag_col] = True
            actual = safe_rate(len(selected_idx), len(split_frame_local))
            budget_delta = abs(actual - budget) if pd.notna(actual) else np.nan
            health_rows.append(
                {
                    "stage": "",
                    "split": split,
                    "model_id": model_id,
                    "primary_budget": budget,
                    "actual_budget": actual,
                    "budget_abs_delta": budget_delta,
                    "score_threshold": threshold,
                    "threshold_selection_source": "train_only_fixed_budget",
                    "tie_break_key": ",".join(tie_cols),
                    "budget_health": "pass" if pd.isna(budget_delta) or budget_delta <= 0.005 or len(split_frame_local) == 0 else "fail",
                    "failure_reason": "" if pd.isna(budget_delta) or budget_delta <= 0.005 or len(split_frame_local) == 0 else "budget_tolerance_abs_exceeded",
                }
            )
    return out.drop(columns=[col for col in ("_score_sort",) if col in out.columns], errors="ignore"), pd.DataFrame(health_rows)


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


def health_lookup(health: pd.DataFrame) -> dict[tuple[str, str], pd.Series]:
    if health.empty or not {"model_id", "split"}.issubset(health.columns):
        return {}
    return {(str(row.model_id), str(row.split)): pd.Series(row._asdict()) for row in health.itertuples(index=False)}


def build_stage1_readout(
    scored: pd.DataFrame,
    random_quantiles: pd.DataFrame,
    single_frontier: pd.DataFrame,
    threshold_health: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    q = random_quantiles.set_index(["model_id", "split"]) if not random_quantiles.empty else pd.DataFrame()
    best_single = single_frontier.groupby("split")["selected_fast_fail_rate"].min().to_dict() if not single_frontier.empty else {}
    h = health_lookup(threshold_health)
    for model_id, model_group in scored.groupby("model_id", sort=False):
        family = str(model_group["model_family"].iloc[0])
        challenger = "challenger" if "lightgbm" in model_id else "primary"
        for split in SPLITS:
            frame = split_frame(model_group.loc[bool_series(model_group["stage_1_evaluable"])], split)
            selected = frame.loc[bool_series(frame["stage1_keep_flag"])]
            baseline = weighted_rate(frame.assign(sample_weight=1.0), "stage_1_fast_fail_target")
            rate = weighted_rate(selected.assign(sample_weight=1.0), "stage_1_fast_fail_target")
            key = (model_id, split)
            p05 = q.loc[key, "random_rate_p05"] if len(q) and key in q.index else np.nan
            p50 = q.loc[key, "random_rate_p50"] if len(q) and key in q.index else np.nan
            p95 = q.loc[key, "random_rate_p95"] if len(q) and key in q.index else np.nan
            best = best_single.get(split, np.nan)
            health = h.get(key, pd.Series(dtype=object))
            rows.append(
                {
                    "scope_id": "primary_fixed_budget",
                    "split": split,
                    "model_id": model_id,
                    "model_family": family,
                    "primary_or_challenger": challenger,
                    "feature_list_hash": str(model_group["feature_list_hash"].dropna().iloc[0]) if "feature_list_hash" in model_group and model_group["feature_list_hash"].notna().any() else "",
                    "keep_budget": float(config["stage_1"]["keep_budget_primary"]),
                    "score_threshold": health.get("score_threshold", np.nan),
                    "threshold_selection_source": health.get("threshold_selection_source", "train_only_fixed_budget"),
                    "budget_health": health.get("budget_health", "missing"),
                    "stage1_keep_n": int(len(selected)),
                    "stage1_keep_retention": safe_rate(len(selected), len(frame)),
                    "stage1_keep_fast_fail_rate": rate,
                    "c0_baseline_fast_fail_rate": baseline,
                    "stage_1_random_keep_fast_fail_rate_p05": p05,
                    "stage_1_random_keep_fast_fail_rate_p50": p50,
                    "stage_1_random_keep_fast_fail_rate_p95": p95,
                    "fast_fail_abs_delta_vs_random_p50": rate - p50 if pd.notna(rate) and pd.notna(p50) else np.nan,
                    "fast_fail_abs_delta_vs_c0_baseline": rate - baseline if pd.notna(rate) and pd.notna(baseline) else np.nan,
                    "best_single_feature_keep_fast_fail_rate": best,
                    "model_minus_best_single_feature": rate - best if pd.notna(rate) and pd.notna(best) else np.nan,
                    "stage_1_status": "readout",
                    "diagnostic_only_flag": challenger == "challenger",
                }
            )
    return pd.DataFrame(rows)


def build_stage2_denominator_audit(primary_s1: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        frame = split_frame(primary_s1, split)
        candidates = frame.loc[bool_series(frame["stage_2_candidate_after_stage1"])] if "stage_2_candidate_after_stage1" in frame else frame.head(0)
        entry_blocked = bool_series(candidates["stage_2_entry_blocked"]) if "stage_2_entry_blocked" in candidates else pd.Series(dtype=bool)
        horizon_complete = bool_series(candidates["stage_2_horizon_complete_20d"]) if "stage_2_horizon_complete_20d" in candidates else pd.Series(dtype=bool)
        rows.append(
            {
                "split": split,
                "stage_2_candidate_after_stage1_n": int(len(candidates)),
                "stage_2_entry_blocked_n": int(entry_blocked.sum()) if len(candidates) else 0,
                "stage_2_censored_n": int((~horizon_complete).sum()) if len(candidates) else 0,
                "stage_2_evaluable_n": int(bool_series(candidates["stage_2_evaluable"]).sum()) if "stage_2_evaluable" in candidates else 0,
            }
        )
    return pd.DataFrame(rows)


def build_stage2_readout(
    scored: pd.DataFrame,
    random_quantiles: pd.DataFrame,
    single_frontier: pd.DataFrame,
    ablation: pd.DataFrame,
    threshold_health: pd.DataFrame,
    denominator_audit: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    rows = []
    q = random_quantiles.set_index(["model_id", "split"]) if not random_quantiles.empty else pd.DataFrame()
    best_single = single_frontier.groupby("split")["selected_continuation_rate"].max().to_dict() if not single_frontier.empty else {}
    ablation_rate = ablation.set_index(["model_id", "split"])["continuation_rate"].to_dict() if not ablation.empty else {}
    h = health_lookup(threshold_health)
    denom = denominator_audit.set_index("split").to_dict("index") if not denominator_audit.empty and "split" in denominator_audit else {}
    for model_id, model_group in scored.groupby("model_id", sort=False):
        family = str(model_group["model_family"].iloc[0])
        challenger = "challenger" if "lightgbm" in model_id else "primary"
        for split in SPLITS:
            frame = split_frame(model_group, split)
            selected = frame.loc[bool_series(frame["stage2_continue_flag"])]
            survivor_base = weighted_rate(frame.assign(sample_weight=1.0), "stage_2_continuation_target")
            rate = weighted_rate(selected.assign(sample_weight=1.0), "stage_2_continuation_target")
            key = (model_id, split)
            p05 = q.loc[key, "random_rate_p05"] if len(q) and key in q.index else np.nan
            p50 = q.loc[key, "random_rate_p50"] if len(q) and key in q.index else np.nan
            p95 = q.loc[key, "random_rate_p95"] if len(q) and key in q.index else np.nan
            best = best_single.get(split, np.nan)
            t0_only = ablation_rate.get((model_id, split), np.nan)
            health = h.get(key, pd.Series(dtype=object))
            den = denom.get(split, {})
            rows.append(
                {
                    "scope_id": "primary_fixed_budget",
                    "split": split,
                    "model_id": model_id,
                    "model_family": family,
                    "primary_or_challenger": challenger,
                    "feature_list_hash": str(model_group["feature_list_hash"].dropna().iloc[0]) if "feature_list_hash" in model_group and model_group["feature_list_hash"].notna().any() else "",
                    "continue_budget": float(config["stage_2"]["continue_budget_primary"]),
                    "score_threshold": health.get("score_threshold", np.nan),
                    "threshold_selection_source": health.get("threshold_selection_source", "train_only_fixed_budget"),
                    "budget_health": health.get("budget_health", "missing"),
                    "stage_2_evaluable_n": int(len(frame)),
                    "stage_2_candidate_after_stage1_n": int(den.get("stage_2_candidate_after_stage1_n", len(frame))),
                    "stage_2_entry_blocked_n": int(den.get("stage_2_entry_blocked_n", 0)),
                    "stage_2_censored_n": int(den.get("stage_2_censored_n", 0)),
                    "stage2_continue_n": int(len(selected)),
                    "stage2_continue_retention": safe_rate(len(selected), len(frame)),
                    "stage2_continue_continuation_rate": rate,
                    "survivor_base_continuation_rate": survivor_base,
                    "stage_2_random_continuation_rate_given_survivor_p05": p05,
                    "stage_2_random_continuation_rate_given_survivor_p50": p50,
                    "stage_2_random_continuation_rate_given_survivor_p95": p95,
                    "continuation_abs_delta_vs_random_p50": rate - p50 if pd.notna(rate) and pd.notna(p50) else np.nan,
                    "best_single_feature_continue_continuation_rate": best,
                    "model_minus_best_single_feature": rate - best if pd.notna(rate) and pd.notna(best) else np.nan,
                    "t0_only_ablation_continuation_rate": t0_only,
                    "realized_path_incremental_value": rate - t0_only if pd.notna(rate) and pd.notna(t0_only) else np.nan,
                    "stage_2_status": "readout",
                    "diagnostic_only_flag": challenger == "challenger",
                }
            )
    return pd.DataFrame(rows)


def select_random_same_budget(
    random_frame: pd.DataFrame,
    c0_frame: pd.DataFrame,
    *,
    model_id: str,
    stage: str,
    c0_flag_col: str,
    random_denominator_col: str,
    target_col: str,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_all, audit = random_budget_selection(
        random_frame,
        c0_frame,
        c0_flag_col=c0_flag_col,
        random_denominator_col=random_denominator_col,
        target_col=target_col,
        config=config,
    )
    audit.insert(0, "model_id", model_id)
    audit.insert(0, "stage", stage)
    if not selected_all.empty:
        rate_rows = []
        for seed, seed_group in selected_all.groupby("seed", sort=False):
            for split in SPLITS:
                sub = split_frame(seed_group, split)
                rate_rows.append({"model_id": model_id, "seed": seed, "split": split, "random_rate": weighted_rate(sub, target_col)})
        seed_rates = pd.DataFrame(rate_rows)
        quant = seed_rates.groupby(["model_id", "split"])["random_rate"].quantile([0.05, 0.50, 0.95]).unstack().reset_index()
        quant = quant.rename(columns={0.05: "random_rate_p05", 0.5: "random_rate_p50", 0.95: "random_rate_p95"})
    else:
        quant = pd.DataFrame(columns=["model_id", "split", "random_rate_p05", "random_rate_p50", "random_rate_p95"])
    return audit, quant


def random_budget_selection(
    random_frame: pd.DataFrame,
    c0_frame: pd.DataFrame,
    *,
    c0_flag_col: str,
    random_denominator_col: str,
    target_col: str,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rank_cols = [col for col in config["random_baseline"]["retention_rank_columns"] if col in random_frame.columns]
    cell_cols = ["split", "board_bucket", "calendar_month"]
    c0 = c0_frame.copy()
    c0_den = c0.groupby(cell_cols, dropna=False).size().rename("c0_denominator_n").reset_index()
    c0_sel = c0.loc[bool_series(c0[c0_flag_col])].groupby(cell_cols, dropna=False).size().rename("c0_selected_n").reset_index()
    budgets = c0_den.merge(c0_sel, on=cell_cols, how="left").fillna({"c0_selected_n": 0})
    if "c0_selected_n" not in budgets.columns:
        budgets["c0_selected_n"] = 0
    if "c0_denominator_n" not in budgets.columns:
        budgets["c0_denominator_n"] = 0
    budgets["c0_cell_budget"] = budgets["c0_selected_n"] / budgets["c0_denominator_n"].replace(0, np.nan)
    random = random_frame.loc[bool_series(random_frame[random_denominator_col])].copy()
    if random.empty:
        audit = budgets.copy()
        audit["seed"] = np.nan
        audit["random_denominator_n"] = 0
        audit["random_selected_n"] = 0
        audit["sample_weight_sum"] = 0.0
        audit["random_rate"] = np.nan
        audit["retention_rank_rule"] = ",".join(rank_cols)
        return random, audit
    random = random.drop(columns=["c0_selected_n", "c0_cell_budget", "c0_denominator_n"], errors="ignore")
    random = random.merge(budgets[cell_cols + ["c0_selected_n", "c0_cell_budget"]], on=cell_cols, how="left")
    random["c0_selected_n"] = pd.to_numeric(random["c0_selected_n"], errors="coerce").fillna(0).astype(int)
    random["c0_cell_budget"] = pd.to_numeric(random["c0_cell_budget"], errors="coerce").fillna(0.0)
    group_cols = ["seed"] + cell_cols
    random = random.sort_values(group_cols + rank_cols, kind="stable")
    random["_random_denominator_n"] = random.groupby(group_cols, dropna=False)["path_key"].transform("size")
    random["_rank_in_cell"] = random.groupby(group_cols, dropna=False).cumcount() + 1
    random["_random_selected_n"] = np.floor(random["c0_cell_budget"] * random["_random_denominator_n"]).astype(int)
    random.loc[(random["_random_selected_n"].eq(0)) & (random["c0_selected_n"].gt(0)) & (random["_random_denominator_n"].gt(0)), "_random_selected_n"] = 1
    random["_selected"] = random["_rank_in_cell"].le(random["_random_selected_n"])
    selected = random.loc[random["_selected"]].drop(columns=["_rank_in_cell", "_selected"]).copy()
    if "sample_weight" not in random:
        random["sample_weight"] = 1.0
    audit = (
        random.groupby(group_cols, dropna=False)
        .agg(
            model_budget=("c0_cell_budget", "first"),
            random_denominator_n=("_random_denominator_n", "first"),
            random_selected_n=("_random_selected_n", "first"),
            sample_weight_sum=("sample_weight", "sum"),
        )
        .reset_index()
    )
    if not selected.empty:
        selected["_weighted_target"] = bool_series(selected[target_col]).astype(float) * pd.to_numeric(selected["sample_weight"], errors="coerce").fillna(1.0)
        selected_rate = (
            selected.groupby(group_cols, dropna=False)
            .agg(_target_sum=("_weighted_target", "sum"), _weight_sum=("sample_weight", "sum"))
            .reset_index()
        )
        selected_rate["random_rate"] = selected_rate["_target_sum"] / selected_rate["_weight_sum"].replace(0, np.nan)
        audit = audit.merge(selected_rate[group_cols + ["random_rate"]], on=group_cols, how="left")
    else:
        audit["random_rate"] = np.nan
    audit["retention_rank_rule"] = ",".join(rank_cols)
    selected = selected.drop(columns=["_random_denominator_n", "_random_selected_n", "_weighted_target"], errors="ignore")
    return selected, audit


def score_bucket_readout(scored: pd.DataFrame, score_col: str, target_col: str, stage: str, higher_is_better: bool) -> pd.DataFrame:
    rows = []
    for model_id, model_group in scored.groupby("model_id", sort=False):
        for split in SPLITS:
            frame = split_frame(model_group, split).dropna(subset=[score_col])
            if frame.empty:
                continue
            order = frame[score_col].rank(method="first", ascending=not higher_is_better)
            try:
                frame = frame.assign(score_bucket=pd.qcut(order, 5, labels=["B1", "B2", "B3", "B4", "B5"], duplicates="drop"))
            except ValueError:
                frame = frame.assign(score_bucket="all")
            for bucket, group in frame.groupby("score_bucket", observed=True):
                rows.append(
                    {
                        "stage": stage,
                        "model_id": model_id,
                        "split": split,
                        "bucket_id": str(bucket),
                        "event_n": int(len(group)),
                        "target_rate": weighted_rate(group.assign(sample_weight=1.0), target_col),
                        "score_min": float(group[score_col].min()),
                        "score_max": float(group[score_col].max()),
                    }
                )
    return pd.DataFrame(rows)


def single_feature_frontier(
    frame: pd.DataFrame,
    feature_cols: list[str],
    target_col: str,
    *,
    budget: float,
    maximize_target: bool,
    selected_rate_col: str,
) -> pd.DataFrame:
    rows = []
    for feature in feature_cols:
        if feature not in frame:
            continue
        best_orientation = "desc"
        best_train = -np.inf if maximize_target else np.inf
        for orientation in ("asc", "desc"):
            selected = select_by_feature(frame, feature, budget, orientation)
            train_rate = weighted_rate(split_frame(selected, "train").assign(sample_weight=1.0), target_col)
            if pd.notna(train_rate) and ((maximize_target and train_rate > best_train) or ((not maximize_target) and train_rate < best_train)):
                best_train = train_rate
                best_orientation = orientation
        selected = select_by_feature(frame, feature, budget, best_orientation)
        for split in SPLITS:
            sub = split_frame(selected, split)
            rows.append(
                {
                    "feature_name": feature,
                    "orientation_selected_on_train": best_orientation,
                    "split": split,
                    "budget": budget,
                    "selected_n": int(len(sub)),
                    selected_rate_col: weighted_rate(sub.assign(sample_weight=1.0), target_col),
                    "frontier_status": "ok",
                }
            )
    return pd.DataFrame(rows)


def select_by_feature(frame: pd.DataFrame, feature: str, budget: float, orientation: str) -> pd.DataFrame:
    parts = []
    asc = orientation == "asc"
    for split in sorted(frame["split"].dropna().astype(str).unique()):
        sub = frame.loc[frame["split"].astype(str).eq(split)].copy()
        sub["_feature_score"] = pd.to_numeric(sub[feature], errors="coerce").fillna(np.inf if asc else -np.inf)
        sub = sub.sort_values(["_feature_score", "instrument", "event_t0_date", "meta_event_id"], ascending=[asc, True, True, True], kind="stable")
        parts.append(sub.head(int(round(budget * len(sub)))).drop(columns=["_feature_score"]))
    return pd.concat(parts, ignore_index=True) if parts else frame.head(0).copy()


def build_ablation(stage2_frame: pd.DataFrame, t0_features: list[str], config: dict[str, Any]) -> pd.DataFrame:
    scored, _ = fit_models(stage2_frame, t0_features, "stage_2_continuation_target", "stage2_continuation_score", config, stage="stage_2_t0_only")
    scored, _health = assign_fixed_budget_flags(
        scored,
        score_col="stage2_continuation_score",
        flag_col="stage2_continue_flag",
        budget=float(config["stage_2"]["continue_budget_primary"]),
        lower_is_better=False,
    )
    rows = []
    for model_id, group in scored.groupby("model_id", sort=False):
        for split in SPLITS:
            sub = split_frame(group, split)
            selected = sub.loc[bool_series(sub["stage2_continue_flag"])]
            rows.append(
                {
                    "scope_id": "t0_only",
                    "split": split,
                    "model_id": model_id,
                    "feature_group": "t0_only",
                    "continue_budget": float(config["stage_2"]["continue_budget_primary"]),
                    "stage2_continue_n": int(len(selected)),
                    "continuation_rate": weighted_rate(selected.assign(sample_weight=1.0), "stage_2_continuation_target"),
                    "random_p50": np.nan,
                    "incremental_value_vs_t0_only": 0.0,
                    "ablation_status": "ok",
                }
            )
    return pd.DataFrame(rows)


def evaluate_decision(
    stage1: pd.DataFrame,
    stage2: pd.DataFrame,
    config: dict[str, Any],
    input_gate_pass: bool,
    input_gate_failure_reasons: str = "",
) -> pd.DataFrame:
    g = config["gates"]
    s1_model = config["models"]["primary_stage_1_model_id"]
    s2_model = config["models"]["primary_stage_2_model_id"]
    if "model_id" not in stage1.columns:
        stage1 = pd.DataFrame(columns=["model_id", "split"])
    if "model_id" not in stage2.columns:
        stage2 = pd.DataFrame(columns=["model_id", "split"])
    s1 = stage1.loc[stage1["model_id"].eq(s1_model)].set_index("split")
    s2 = stage2.loc[stage2["model_id"].eq(s2_model)].set_index("split")

    def row(frame: pd.DataFrame, split: str) -> pd.Series:
        return frame.loc[split] if split in frame.index else pd.Series(dtype=object)

    s1_train = row(s1, "train")
    s1_rob = row(s1, "robustness")
    s2_train = row(s2, "train")
    s2_rob = row(s2, "robustness")
    s1_threshold_health = "pass" if s1_train.get("budget_health") == "pass" and s1_rob.get("budget_health") == "pass" else "fail"
    s2_threshold_health = "pass" if s2_train.get("budget_health") == "pass" and s2_rob.get("budget_health") == "pass" else "fail"
    stage1_supported = bool(
        input_gate_pass
        and s1_threshold_health == "pass"
        and int(s1_train.get("stage1_keep_n", 0)) >= int(g["stage_1_train_keep_n_min"])
        and int(s1_rob.get("stage1_keep_n", 0)) >= int(g["stage_1_robustness_keep_n_min"])
        and float(s1_train.get("fast_fail_abs_delta_vs_random_p50", np.inf)) <= float(g["stage_1_train_delta_vs_random_p50"])
        and float(s1_train.get("fast_fail_abs_delta_vs_c0_baseline", np.inf)) <= float(g["stage_1_train_delta_vs_c0_baseline"])
        and float(s1_rob.get("fast_fail_abs_delta_vs_random_p50", np.inf)) <= float(g["stage_1_robustness_delta_vs_random_p50"])
        and float(s1_rob.get("fast_fail_abs_delta_vs_c0_baseline", np.inf)) <= float(g["stage_1_robustness_delta_vs_c0_baseline"])
        and float(s1_train.get("stage1_keep_retention", 0.0)) >= float(g["stage_1_min_keep_retention"])
        and float(s1_rob.get("stage1_keep_retention", 0.0)) >= float(g["stage_1_min_keep_retention"])
        and float(s1_rob.get("model_minus_best_single_feature", np.inf)) < 0.0
    )
    stage1_partial = bool(
        input_gate_pass
        and not stage1_supported
        and pd.notna(s1_train.get("fast_fail_abs_delta_vs_c0_baseline", np.nan))
        and float(s1_train.get("fast_fail_abs_delta_vs_c0_baseline", np.inf)) < 0.0
    )
    if stage1_supported:
        stage1_status = "supported"
    elif stage1_partial:
        stage1_status = "partial_c0_or_train_only"
    else:
        stage1_status = "failed"

    stage2_supported = bool(
        stage1_supported
        and s2_threshold_health == "pass"
        and int(s2_train.get("stage_2_evaluable_n", 0)) >= int(g["stage_2_train_evaluable_n_min"])
        and int(s2_train.get("stage2_continue_n", 0)) >= int(g["stage_2_train_continue_n_min"])
        and int(s2_rob.get("stage_2_evaluable_n", 0)) >= int(g["stage_2_robustness_evaluable_n_min"])
        and int(s2_rob.get("stage2_continue_n", 0)) >= int(g["stage_2_robustness_continue_n_min"])
        and float(s2_train.get("continuation_abs_delta_vs_random_p50", -np.inf)) >= float(g["stage_2_train_delta_vs_random_p50"])
        and float(s2_rob.get("continuation_abs_delta_vs_random_p50", -np.inf)) >= float(g["stage_2_robustness_delta_vs_random_p50"])
        and float(s2_rob.get("model_minus_best_single_feature", -np.inf)) > 0.0
        and float(s2_rob.get("realized_path_incremental_value", -np.inf)) > 0.0
    )
    stage2_partial = bool(
        stage1_supported
        and not stage2_supported
        and int(s2_train.get("stage_2_evaluable_n", 0)) >= int(g["stage_2_train_evaluable_n_min"])
        and int(s2_rob.get("stage_2_evaluable_n", 0)) >= int(g["stage_2_robustness_evaluable_n_min"])
    )
    if stage2_supported:
        stage2_status = "supported"
    elif stage2_partial:
        stage2_status = "partial"
    else:
        stage2_status = "failed"

    if not input_gate_pass:
        decision = "12A6c_blocked_input_or_baseline_failure"
        next_allowed = "requirement_12a6d_fast_fail_scope_or_source_rethink.md"
    elif stage1_status == "failed":
        decision = "12A6c_no_two_stage_feasibility"
        next_allowed = "requirement_12a6d_fast_fail_scope_or_source_rethink.md"
    elif stage1_status.startswith("partial"):
        decision = "12A6c_stage1_partial"
        next_allowed = "requirement_12a6d_stage1_rejector_feature_or_label_revision.md"
    elif stage2_status == "supported":
        decision = "12A6c_two_stage_supported"
        next_allowed = "requirement_12a7_two_stage_meta_label_oos_validation.md"
    else:
        decision = "12A6c_stage1_supported_stage2_partial"
        next_allowed = "requirement_12a6d_stage2_continuation_feature_revision.md"
    reasons = []
    if not input_gate_pass:
        reasons.append("input_gate_failed" + (f":{input_gate_failure_reasons}" if input_gate_failure_reasons else ""))
    if s1_threshold_health != "pass":
        reasons.append("stage1_threshold_health_failed")
    if s2_threshold_health != "pass":
        reasons.append("stage2_threshold_health_failed")
    if stage1_status != "supported":
        reasons.append(f"stage1_{stage1_status}")
    if stage1_status == "supported" and stage2_status != "supported":
        reasons.append(f"stage2_{stage2_status}")
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "input_gate_status": "pass" if input_gate_pass else "fail",
                "stage_1_status": stage1_status,
                "stage_2_status": stage2_status,
                "stage_1_target_id": config["stage_1"]["target_id"],
                "stage_1_model_id": s1_model,
                "stage_1_model_family": s1_model,
                "stage_1_keep_budget": float(config["stage_1"]["keep_budget_primary"]),
                "stage_1_score_threshold": s1_train.get("score_threshold", np.nan),
                "stage_1_threshold_health": s1_threshold_health,
                "stage_1_train_keep_fast_fail_rate": s1_train.get("stage1_keep_fast_fail_rate", np.nan),
                "stage_1_train_random_keep_fast_fail_rate_p50": s1_train.get("stage_1_random_keep_fast_fail_rate_p50", np.nan),
                "stage_1_train_c0_baseline_fast_fail_rate": s1_train.get("c0_baseline_fast_fail_rate", np.nan),
                "stage_1_robustness_keep_fast_fail_rate": s1_rob.get("stage1_keep_fast_fail_rate", np.nan),
                "stage_1_robustness_random_keep_fast_fail_rate_p50": s1_rob.get("stage_1_random_keep_fast_fail_rate_p50", np.nan),
                "stage_2_target_id": config["stage_2"]["target_id"],
                "stage_2_model_id": s2_model,
                "stage_2_model_family": s2_model,
                "stage_2_continue_budget": float(config["stage_2"]["continue_budget_primary"]),
                "stage_2_score_threshold": s2_train.get("score_threshold", np.nan),
                "stage_2_threshold_health": s2_threshold_health,
                "stage_2_train_continue_continuation_rate": s2_train.get("stage2_continue_continuation_rate", np.nan),
                "stage_2_train_random_continuation_rate_given_survivor_p50": s2_train.get("stage_2_random_continuation_rate_given_survivor_p50", np.nan),
                "stage_2_robustness_continue_continuation_rate": s2_rob.get("stage2_continue_continuation_rate", np.nan),
                "stage_2_robustness_random_continuation_rate_given_survivor_p05": s2_rob.get("stage_2_random_continuation_rate_given_survivor_p05", np.nan),
                "stage_2_robustness_random_continuation_rate_given_survivor_p50": s2_rob.get("stage_2_random_continuation_rate_given_survivor_p50", np.nan),
                "realized_path_incremental_value": s2_rob.get("realized_path_incremental_value", np.nan),
                "same_budget_random_audit_hash": "",
                "feature_matrix_hash": "",
                "gate_failure_reasons": ";".join(reasons),
                "next_allowed_requirement": next_allowed,
            }
        ]
    )


def build_report(
    decision: pd.DataFrame,
    stage1: pd.DataFrame,
    stage2: pd.DataFrame,
    event_universe: pd.DataFrame,
    primary_s1: pd.DataFrame,
    stage2_scored: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    s1_model = d["stage_1_model_id"]
    s2_model = d["stage_2_model_id"]
    s1 = stage1.loc[stage1["model_id"].eq(s1_model)].set_index("split")
    s2 = stage2.loc[stage2["model_id"].eq(s2_model)].set_index("split")
    s1_train = s1.loc["train"] if "train" in s1.index else pd.Series(dtype=object)
    s1_rob = s1.loc["robustness"] if "robustness" in s1.index else pd.Series(dtype=object)
    s2_train = s2.loc["train"] if "train" in s2.index else pd.Series(dtype=object)
    s2_rob = s2.loc["robustness"] if "robustness" in s2.index else pd.Series(dtype=object)

    def pct(value: Any) -> str:
        return "NA" if pd.isna(value) else f"{float(value):.4f}"

    def slice_summary(frame: pd.DataFrame, flag_col: str, target_col: str) -> str:
        if frame.empty:
            return "无可用切片读数。"
        lines = []
        for col, label in (("board_bucket", "board"), ("primary_family_id", "family"), ("calendar_year", "year")):
            if col not in frame:
                continue
            sub = frame.loc[frame["split"].astype(str).eq("robustness") & bool_series(frame[flag_col])].copy()
            if sub.empty:
                lines.append(f"- {label}: robustness selected_n=0")
                continue
            rows = []
            for value, group in sub.groupby(col, dropna=False):
                rows.append((str(value), len(group), weighted_rate(group.assign(sample_weight=1.0), target_col)))
            rows = sorted(rows, key=lambda item: item[1], reverse=True)[:4]
            text = "; ".join(f"{value} n={n}, rate={pct(rate)}" for value, n, rate in rows)
            lines.append(f"- {label}: {text}")
        return "\n".join(lines) if lines else "无可用切片读数。"

    s1_stability = slice_summary(primary_s1, "stage1_keep_flag", "stage_1_fast_fail_target")
    s2_stability = slice_summary(stage2_scored, "stage2_continue_flag", "stage_2_continuation_target")
    return f"""
# 12A6c 两阶段 fast-fail rejector / continuation feasibility 报告

## 结论

- final decision: `{d['decision_state']}`
- input gate: `{d['input_gate_status']}`
- stage-1 status: `{d['stage_1_status']}`，threshold health `{d['stage_1_threshold_health']}`
- stage-2 status: `{d['stage_2_status']}`，threshold health `{d['stage_2_threshold_health']}`
- gate failure reasons: `{d['gate_failure_reasons']}`
- next allowed requirement: `{d['next_allowed_requirement']}`

## 为什么从 12A6b 进入两阶段

12A6b 的 C0 risk_on 读数是 partial：C0 确实有 fast-fail / survival morphology，但直接把 C0 当交易信号会混合两件事：先避开 H20 内 -10% fast-fail，再在 survivor 中寻找后续 +20% continuation。12A6c 因此把问题拆成 stage-1 rejector 和 stage-2 continuation selector，并用 matched random same-budget baseline 检查每一步是否超过随机保留。

## PIT 决策边界

- C0 risk_on event universe: {len(event_universe):,}
- Stage-1 decision time: event_t0 close；只使用 12A4 t0 PIT features。
- Stage-1 target: `fast_fail_L10_H20`，即 H20 内先触达 -10% lower barrier。
- Stage-2 decision time: entry+20 close；reference price 是 entry+21 executable open。
- Stage-2 target: `continuation_U20_L10_H2_20`，即 H2=20 内 +20% upper barrier 先于 -10% lower barrier。
- Threshold policy: train split 固定预算选 score boundary，validation/robustness 只复用 train-frozen threshold；不再在每个 split 内重新选 50%。

## Stage-1 fast-fail rejector

- primary model: `{s1_model}`
- train keep_n: {int(s1_train.get('stage1_keep_n', 0))}，keep fast-fail rate {pct(s1_train.get('stage1_keep_fast_fail_rate', np.nan))}，random p50 {pct(s1_train.get('stage_1_random_keep_fast_fail_rate_p50', np.nan))}，delta vs random p50 {pct(s1_train.get('fast_fail_abs_delta_vs_random_p50', np.nan))}
- robustness keep_n: {int(s1_rob.get('stage1_keep_n', 0))}，keep fast-fail rate {pct(s1_rob.get('stage1_keep_fast_fail_rate', np.nan))}，random p50 {pct(s1_rob.get('stage_1_random_keep_fast_fail_rate_p50', np.nan))}，delta vs random p50 {pct(s1_rob.get('fast_fail_abs_delta_vs_random_p50', np.nan))}
- robustness delta vs C0 baseline: {pct(s1_rob.get('fast_fail_abs_delta_vs_c0_baseline', np.nan))}
- robustness model minus best single feature: {pct(s1_rob.get('model_minus_best_single_feature', np.nan))}

## Stage-2 continuation

- primary model: `{s2_model}`
- train evaluable_n: {int(s2_train.get('stage_2_evaluable_n', 0))}，continue_n {int(s2_train.get('stage2_continue_n', 0))}，continuation rate {pct(s2_train.get('stage2_continue_continuation_rate', np.nan))}，random p50 {pct(s2_train.get('stage_2_random_continuation_rate_given_survivor_p50', np.nan))}，delta vs random p50 {pct(s2_train.get('continuation_abs_delta_vs_random_p50', np.nan))}
- robustness evaluable_n: {int(s2_rob.get('stage_2_evaluable_n', 0))}，continue_n {int(s2_rob.get('stage2_continue_n', 0))}，continuation rate {pct(s2_rob.get('stage2_continue_continuation_rate', np.nan))}，random p50 {pct(s2_rob.get('stage_2_random_continuation_rate_given_survivor_p50', np.nan))}，delta vs random p50 {pct(s2_rob.get('continuation_abs_delta_vs_random_p50', np.nan))}
- robustness model minus best single feature: {pct(s2_rob.get('model_minus_best_single_feature', np.nan))}
- realized-path incremental value vs t0-only: {pct(s2_rob.get('realized_path_incremental_value', np.nan))}

## 稳定性切片

Stage-1 robustness selected fast-fail rate:
{s1_stability}

Stage-2 robustness selected continuation rate:
{s2_stability}

## 解释与限制

该报告仍然是 feasibility 读数，不声明可交易 alpha。barrier touch 使用 high/low 路径触达，是形态上界，不等同可成交收益；same-budget random baseline 只回答“同样保留比例下是否优于随机路径”，不回答组合容量、滑点、换手和可执行成交价格。

12A7 只有在 final decision 为 `12A6c_two_stage_supported` 时才应进入正式 OOS validation；当前 decision 若不是 supported，应优先进入 next allowed requirement 中指定的 12A6d 修订方向。
""".strip()


def build_manifest(paths: dict[str, Path], frames: dict[str, pd.DataFrame], decision: pd.DataFrame, config_path: Path, requirement_path: Path) -> dict[str, Any]:
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
    if "input_artifact_audit" in frames and not frames["input_artifact_audit"].empty:
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
        "requirement_sha256": path_sha(requirement_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_revision": git_revision(REPO_ROOT),
        "config_path": str(config_path),
        "config_sha256": path_sha(config_path),
        "final_decision": decision.iloc[0]["decision_state"] if not decision.empty else "",
        "inputs": inputs,
        "input_hashes": input_hashes,
        "outputs": outputs,
        "output_hashes": output_hashes,
    }


def run_pipeline(config_path: Path, mode: str = "full") -> int:
    config = load_yaml(config_path)
    paths = output_paths()
    resolved = {key: topic_path(value) for key, value in config["paths"].items()}
    audit = build_input_artifact_audit(config)
    write_df(paths["input_artifact_audit"], audit)
    read_ok = audit["read_status"].astype(str).eq("pass").all()
    schema_ok = audit["schema_status"].astype(str).eq("pass").all()
    if mode == "check-inputs":
        if not read_ok or not schema_ok:
            raise RuntimeError("12A6c input check failed")
        print(f"{RUN_ID}: input audit ok ({len(audit)} artifacts)")
        return 0
    if not read_ok or not schema_ok:
        raise RuntimeError("12A6c required inputs missing or schema mismatch")

    universe_raw = read_table(resolved["meta_label_event_universe"])
    feature_matrix_12a4 = read_table(resolved["meta_label_feature_matrix"])
    feature_dict_12a4 = read_table(resolved["meta_label_feature_dictionary"])
    path_cache = read_table(resolved["entry_forward_path_cache"])
    random_entries = read_table(resolved["matched_random_sampled_entries"])
    stock_cache = StockDailyCache(resolved["stock_daily_csv_dir"])

    c0 = normalize_c0_universe(universe_raw, path_cache)
    stage2_c0_cache = build_stage2_path_cache(c0[["path_key", "instrument", "entry_pos", "entry_price"]], stock_cache, config, include_realized=True)
    random_unique = random_entries[["path_key", "instrument", "entry_pos", "entry_price"]].drop_duplicates("path_key")
    stage2_random_cache = build_stage2_path_cache(random_unique, stock_cache, config, include_realized=False)
    stage2_path_cache = pd.concat([stage2_c0_cache, stage2_random_cache], ignore_index=True).drop_duplicates("path_key")

    primary_stage2_col = "continuation_U20_L10_H2_20"
    c0 = c0.merge(stage2_c0_cache, on=["path_key", "instrument", "entry_pos", "entry_price"], how="left")
    c0["stage_2_path_evaluable"] = (
        bool_series(c0["no_fast_fail_L10_H20"])
        & (~bool_series(c0["stage_2_entry_blocked"]))
        & bool_series(c0["stage_2_horizon_complete_20d"])
    )
    c0["stage_2_continuation_target"] = bool_series(c0[primary_stage2_col])
    input_gate_pass, input_gate_reasons = evaluate_input_gates(audit, resolved, c0)

    dictionary, t0_features, realized_features = build_feature_dictionary(feature_dict_12a4)
    available_t0 = [col for col in t0_features if col in feature_matrix_12a4.columns and pd.api.types.is_numeric_dtype(feature_matrix_12a4[col])]
    matrix = c0.merge(feature_matrix_12a4, on=["meta_event_id", "instrument", "event_t0_date", "event_t0_pos", "event_split", "board_bucket", "market_regime_bucket", "source_arm_id", "primary_family_id"], how="left", suffixes=("", "_feature"))
    matrix["split"] = matrix["event_split"].astype(str)
    feature_pit = feature_pit_audit(dictionary, matrix)
    redundancy = redundancy_audit(matrix)
    allowed_realized = [name for name in realized_features if name in matrix.columns and name in set(redundancy.loc[bool_series(redundancy["allowed_for_stage_2_after_audit"]), "feature_name"])]

    stage1_frame = matrix.loc[bool_series(matrix["stage_1_evaluable"])].copy()
    stage1_scored, stage1_card = fit_models(stage1_frame, available_t0, "stage_1_fast_fail_target", "stage1_fast_fail_score", config, stage="stage_1")
    stage1_scored, stage1_health = assign_fixed_budget_flags(
        stage1_scored,
        score_col="stage1_fast_fail_score",
        flag_col="stage1_keep_flag",
        budget=float(config["stage_1"]["keep_budget_primary"]),
        lower_is_better=True,
    )
    stage1_health["stage"] = "stage_1"
    stage1_scored["feature_list_hash"] = stable_hash(available_t0)

    primary_s1 = stage1_scored.loc[stage1_scored["model_id"].eq(config["models"]["primary_stage_1_model_id"])].copy()
    primary_s1["stage_2_candidate_after_stage1"] = bool_series(primary_s1["stage1_keep_flag"]) & bool_series(primary_s1["no_fast_fail_L10_H20"])
    primary_s1["stage_2_evaluable"] = (
        bool_series(primary_s1["stage_2_candidate_after_stage1"])
        & (~bool_series(primary_s1["stage_2_entry_blocked"]))
        & bool_series(primary_s1["stage_2_horizon_complete_20d"])
    )
    stage2_denominator_audit = build_stage2_denominator_audit(primary_s1)
    stage2_frame = primary_s1.loc[bool_series(primary_s1["stage_2_evaluable"])].copy()
    stage2_features = available_t0 + allowed_realized
    stage2_scored, stage2_card = fit_models(stage2_frame, stage2_features, "stage_2_continuation_target", "stage2_continuation_score", config, stage="stage_2")
    stage2_scored, stage2_health = assign_fixed_budget_flags(
        stage2_scored,
        score_col="stage2_continuation_score",
        flag_col="stage2_continue_flag",
        budget=float(config["stage_2"]["continue_budget_primary"]),
        lower_is_better=False,
    )
    stage2_health["stage"] = "stage_2"
    stage2_scored["feature_list_hash"] = stable_hash(stage2_features)

    random_with_path = random_entries.merge(path_cache, on=["path_key", "instrument", "entry_pos", "entry_price"], how="left")
    random_with_path = random_with_path.merge(stage2_random_cache, on=["path_key", "instrument", "entry_pos", "entry_price"], how="left")
    random_with_path["stage_1_evaluable"] = (~bool_series(random_with_path["entry_blocked"])) & bool_series(random_with_path["horizon_complete_20d"])
    random_with_path["stage_1_fast_fail_target"] = random_with_path["stage_1_evaluable"] & random_with_path["time_to_lower_minus_10_20d"].notna()
    random_with_path["no_fast_fail_L10_H20"] = random_with_path["stage_1_evaluable"] & (~random_with_path["stage_1_fast_fail_target"])
    random_with_path["stage_2_path_evaluable"] = (
        bool_series(random_with_path["no_fast_fail_L10_H20"])
        & (~bool_series(random_with_path["stage_2_entry_blocked"]))
        & bool_series(random_with_path["stage_2_horizon_complete_20d"])
    )
    random_with_path["stage_2_continuation_target"] = bool_series(random_with_path[primary_stage2_col])

    stage1_random_audits = []
    stage1_random_quantiles = []
    for model_id, group in stage1_scored.groupby("model_id", sort=False):
        c0_model = group.loc[bool_series(group["stage_1_evaluable"])].copy()
        audit_part, quant_part = select_random_same_budget(
            random_with_path,
            c0_model,
            model_id=model_id,
            stage="stage_1",
            c0_flag_col="stage1_keep_flag",
            random_denominator_col="stage_1_evaluable",
            target_col="stage_1_fast_fail_target",
            config=config,
        )
        stage1_random_audits.append(audit_part)
        stage1_random_quantiles.append(quant_part)
    stage1_random_audit = pd.concat(stage1_random_audits, ignore_index=True) if stage1_random_audits else pd.DataFrame()
    stage1_random_quant = pd.concat(stage1_random_quantiles, ignore_index=True) if stage1_random_quantiles else pd.DataFrame()

    random_kept_primary = replay_random_selection(
        random_with_path,
        primary_s1.loc[bool_series(primary_s1["stage_1_evaluable"])],
        "stage1_keep_flag",
        "stage_1_evaluable",
        config,
    )
    random_kept_primary["stage_2_candidate_after_stage1"] = bool_series(random_kept_primary["no_fast_fail_L10_H20"])
    random_kept_primary["stage_2_evaluable"] = (
        bool_series(random_kept_primary["stage_2_candidate_after_stage1"])
        & (~bool_series(random_kept_primary["stage_2_entry_blocked"]))
        & bool_series(random_kept_primary["stage_2_horizon_complete_20d"])
    )
    random_survivors = random_kept_primary.loc[bool_series(random_kept_primary["stage_2_evaluable"])].copy()
    stage2_random_audits = []
    stage2_random_quantiles = []
    for model_id, group in stage2_scored.groupby("model_id", sort=False):
        c0_stage2 = group.copy()
        audit_part, quant_part = select_random_same_budget(
            random_survivors,
            c0_stage2,
            model_id=model_id,
            stage="stage_2",
            c0_flag_col="stage2_continue_flag",
            random_denominator_col="stage_2_evaluable",
            target_col="stage_2_continuation_target",
            config=config,
        )
        stage2_random_audits.append(audit_part)
        stage2_random_quantiles.append(quant_part)
    stage2_random_audit = pd.concat(stage2_random_audits, ignore_index=True) if stage2_random_audits else pd.DataFrame()
    stage2_random_quant = pd.concat(stage2_random_quantiles, ignore_index=True) if stage2_random_quantiles else pd.DataFrame()

    stage1_single = single_feature_frontier(
        stage1_frame,
        available_t0,
        "stage_1_fast_fail_target",
        budget=float(config["stage_1"]["keep_budget_primary"]),
        maximize_target=False,
        selected_rate_col="selected_fast_fail_rate",
    )
    stage2_single = single_feature_frontier(
        stage2_frame,
        stage2_features,
        "stage_2_continuation_target",
        budget=float(config["stage_2"]["continue_budget_primary"]),
        maximize_target=True,
        selected_rate_col="selected_continuation_rate",
    )
    ablation = build_ablation(stage2_frame, available_t0, config)
    stage1_readout = build_stage1_readout(stage1_scored, stage1_random_quant, stage1_single, stage1_health, config)
    stage2_readout = build_stage2_readout(stage2_scored, stage2_random_quant, stage2_single, ablation, stage2_health, stage2_denominator_audit, config)
    decision = evaluate_decision(stage1_readout, stage2_readout, config, input_gate_pass=bool(input_gate_pass), input_gate_failure_reasons=input_gate_reasons)

    primary_target_flags = primary_s1[
        [
            "meta_event_id",
            "stage1_keep_flag",
            "stage_2_candidate_after_stage1",
            "stage_2_evaluable",
        ]
    ].copy()
    primary_target_flags = primary_target_flags.rename(
        columns={
            "stage1_keep_flag": "stage1_keep_flag_primary",
            "stage_2_candidate_after_stage1": "stage_2_candidate_after_stage1_primary",
            "stage_2_evaluable": "stage_2_evaluable_primary",
        }
    )
    event_targets = c0[
        [
            "meta_event_id",
            "instrument",
            "split",
            "stage_1_evaluable",
            "stage_1_fast_fail_target",
            "no_fast_fail_L10_H20",
            "stage_2_path_evaluable",
            "stage_2_entry_blocked",
            "stage_2_horizon_complete_20d",
            "stage_2_continuation_target",
        ]
    ].merge(primary_target_flags, on="meta_event_id", how="left")
    for col in ("stage1_keep_flag_primary", "stage_2_candidate_after_stage1_primary", "stage_2_evaluable_primary"):
        event_targets[col] = bool_series(event_targets[col])
    event_targets["stage_2_evaluable"] = event_targets["stage_2_evaluable_primary"]
    label_grid = build_stage1_label_grid(c0, config)
    target_grid = build_stage2_target_grid(c0, config)
    score_bucket_1 = score_bucket_readout(stage1_scored, "stage1_fast_fail_score", "stage_1_fast_fail_target", "stage_1", higher_is_better=False)
    score_bucket_2 = score_bucket_readout(stage2_scored, "stage2_continuation_score", "stage_2_continuation_target", "stage_2", higher_is_better=True)
    split_audit = build_split_time_boundary_audit(c0)
    scope_exclusion = build_scope_exclusion_audit(universe_raw, c0)

    feature_cols_out = [
        "meta_event_id",
        "instrument",
        "event_t0_date",
        "event_t0_pos",
        "split",
        "board_bucket",
        "primary_family_id",
        "path_key",
    ] + available_t0 + realized_features
    feature_cols_out = list(dict.fromkeys([col for col in feature_cols_out if col in matrix.columns]))
    feature_matrix = matrix[feature_cols_out].copy()

    frames = {
        "input_artifact_audit": audit,
        "event_universe": c0,
        "scope_exclusion_audit": scope_exclusion,
        "feature_dictionary": dictionary,
        "feature_pit_audit": feature_pit,
        "event_targets": event_targets,
        "realized_path_redundancy_audit": redundancy,
        "stage_threshold_health": pd.concat([stage1_health, stage2_health], ignore_index=True),
        "stage_1_model_card": stage1_card,
        "stage_2_model_card": stage2_card,
        "stage_1_score_bucket_readout": score_bucket_1,
        "stage_2_score_bucket_readout": score_bucket_2,
        "stage_1_single_feature_frontier": stage1_single,
        "stage_2_single_feature_frontier": stage2_single,
        "stage_1_random_same_budget_audit": stage1_random_audit,
        "stage_2_random_same_budget_audit": stage2_random_audit,
        "stage_2_ablation_readout": ablation,
        "stage_1_rejector_readout": stage1_readout,
        "stage_2_continuation_readout": stage2_readout,
        "stage_1_label_grid_readout": label_grid,
        "stage_2_target_grid_readout": target_grid,
        "decision": decision,
        "split_time_boundary_audit": split_audit,
        "feature_matrix": feature_matrix,
        "stage2_path_cache": stage2_path_cache,
    }
    for key, frame in frames.items():
        if key in paths and key != "stage2_path_cache":
            write_df(paths[key], frame)
    write_df(paths["stage2_path_cache"], stage2_path_cache)
    report = build_report(decision, stage1_readout, stage2_readout, c0, primary_s1, stage2_scored)
    write_text(paths["report"], report)
    frames["report"] = pd.DataFrame([{"report_path": str(paths["report"])}])
    requirement_path = resolved["requirement"]
    # Fill hashes that need output files to exist.
    decision.loc[:, "feature_matrix_hash"] = path_sha(paths["feature_matrix"])
    decision.loc[:, "same_budget_random_audit_hash"] = stable_hash(
        {
            "stage1": path_sha(paths["stage_1_random_same_budget_audit"]),
            "stage2": path_sha(paths["stage_2_random_same_budget_audit"]),
        }
    )
    write_df(paths["decision"], decision)
    frames["decision"] = decision
    write_json(paths["manifest"], build_manifest(paths, frames, decision, config_path, requirement_path))
    print(f"{RUN_ID}: {decision.iloc[0]['decision_state']}")
    return 0


def replay_random_selection(random_frame: pd.DataFrame, c0_frame: pd.DataFrame, c0_flag_col: str, random_denominator_col: str, config: dict[str, Any]) -> pd.DataFrame:
    selected, _audit = random_budget_selection(
        random_frame,
        c0_frame,
        c0_flag_col=c0_flag_col,
        random_denominator_col=random_denominator_col,
        target_col="stage_1_fast_fail_target",
        config=config,
    )
    return selected


def build_stage1_label_grid(c0: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for horizon in (10, 20):
        complete_col = f"horizon_complete_{horizon}d"
        for lower in (-0.06, -0.08, -0.10, -0.12, -0.15, -0.20):
            col = f"time_to_lower_{barrier_suffix(lower)}_{horizon}d"
            for split in SPLITS:
                frame = split_frame(c0.loc[bool_series(c0[complete_col])], split)
                rows.append(
                    {
                        "split": split,
                        "horizon_sessions": horizon,
                        "lower_barrier_pct": lower,
                        "complete_executable_event_n": int(len(frame)),
                        "fast_fail_rate": safe_rate(frame[col].notna().sum(), len(frame)) if col in frame else np.nan,
                        "primary_target_flag": horizon == int(config["stage_1"]["horizon_sessions"]) and abs(lower - float(config["stage_1"]["lower_barrier_pct"])) < 1e-9,
                    }
                )
    return pd.DataFrame(rows)


def build_stage2_target_grid(c0: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    survivors = c0.loc[bool_series(c0["stage_2_path_evaluable"])].copy()
    for h2 in config["stage_2"]["horizon_grid_h2"]:
        for upper in config["stage_2"]["upper_barrier_grid"]:
            for lower in config["stage_2"]["lower_barrier_grid"]:
                col = f"continuation_U{int(round(float(upper) * 100))}_L{int(round(abs(float(lower)) * 100))}_H2_{int(h2)}"
                for split in SPLITS:
                    frame = split_frame(survivors, split)
                    rows.append(
                        {
                            "split": split,
                            "horizon_sessions_h2": int(h2),
                            "upper_barrier_pct": float(upper),
                            "lower_barrier_pct": float(lower),
                            "stage_2_evaluable_n": int(len(frame)),
                            "continuation_rate": safe_rate(bool_series(frame[col]).sum(), len(frame)) if col in frame else np.nan,
                            "primary_target_flag": int(h2) == int(config["stage_2"]["horizon_sessions_h2"])
                            and abs(float(upper) - float(config["stage_2"]["upper_barrier_pct"])) < 1e-9
                            and abs(float(lower) - float(config["stage_2"]["lower_barrier_pct"])) < 1e-9,
                        }
                    )
    return pd.DataFrame(rows)


def build_split_time_boundary_audit(c0: pd.DataFrame) -> pd.DataFrame:
    train_max = pd.to_datetime(c0.loc[c0["split"].eq("train"), "event_t0_date"], errors="coerce").max()
    rows = []
    for split in ("validation", "robustness"):
        eval_min = pd.to_datetime(c0.loc[c0["split"].eq(split), "event_t0_date"], errors="coerce").min()
        rows.append(
            {
                "feature_group": "train_frozen_thresholds",
                "eval_split": split,
                "train_max_event_t0_date": date_text(train_max),
                "eval_min_event_t0_date": date_text(eval_min),
                "split_time_boundary_gate_pass": bool(pd.notna(train_max) and pd.notna(eval_min) and train_max <= eval_min),
            }
        )
    return pd.DataFrame(rows)


def build_scope_exclusion_audit(raw_universe: pd.DataFrame, c0: pd.DataFrame) -> pd.DataFrame:
    raw_c0 = raw_universe.loc[raw_universe["source_arm_id"].astype(str).eq(PRIMARY_SOURCE_ARM)].copy()
    rows = []
    rows.append(
        {
            "scope_id": "c0_risk_on",
            "raw_c0_event_n": int(len(raw_c0)),
            "included_event_n": int(len(c0)),
            "excluded_event_n": int(len(raw_c0) - len(c0)),
            "exclusion_reason": "non_risk_on_or_non_c0_source",
        }
    )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pipeline(Path(args.config), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

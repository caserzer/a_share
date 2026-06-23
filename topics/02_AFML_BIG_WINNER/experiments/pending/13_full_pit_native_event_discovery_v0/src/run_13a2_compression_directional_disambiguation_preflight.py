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


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
TOPIC_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUNNER_13A_PATH = EXPERIMENT_DIR / "src" / "run_13a_full_pit_native_token_cartography_preflight.py"


def load_13a_runner():
    spec = importlib.util.spec_from_file_location("run_13a_full_pit_native_token_cartography_preflight", RUNNER_13A_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r13a = load_13a_runner()


RUN_ID = "13A2_compression_directional_disambiguation_preflight"
EXPERIMENT_ID = "13_full_pit_native_event_discovery_v0"
PHASE_ID = "13A2"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_13a2_compression_directional_disambiguation_preflight.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"
SPLITS = ("train", "validation", "robustness")
ALL_SPLITS = ("all", "train", "validation", "robustness")
SELECTED_LABEL_ID = "vol20d_kup2p0_kdn1p0_H20"
BASE_TOKEN_ID = "volatility_20d__bottom_20pct"

FAST_FAIL_MAX_SESSIONS = 5
EPSILON = 1e-12


FAMILY_PRIORITY: dict[str, list[str]] = {
    "relative_strength": ["stock_vs_board_20d", "ret_20d", "close_vs_sma20", "stock_vs_board_5d", "ret_5d"],
    "range_position": ["close_position_20d", "distance_to_20d_high", "distance_from_20d_low", "higher_low_slope_10d"],
    "drawdown_exclusion": ["max_drawdown_20d", "ret_60d", "distance_to_60d_low", "max_drawdown_60d"],
    "participation": ["turnover_zscore_20d", "volume_up_price_not_down_5d", "amount_ratio_5d_20d", "up_day_volume_share_20d", "money_median_5d_vs_20d"],
}

RAW_FORMULAS: dict[str, str] = {
    "ret_5d": "close / close.shift(5) - 1",
    "ret_20d": "close / close.shift(20) - 1",
    "stock_vs_board_5d": "ret_5d - same-board equal-weight ret_5d at reference_date",
    "stock_vs_board_20d": "ret_20d - same-board equal-weight ret_20d at reference_date",
    "close_vs_sma20": "close / sma20 - 1",
    "close_position_20d": "(close - low_20d) / max(high_20d - low_20d, 1e-12)",
    "distance_to_20d_high": "high_20d / close - 1",
    "distance_from_20d_low": "close / low_20d - 1",
    "higher_low_slope_10d": "slope(low over prior 10 sessions)",
    "max_drawdown_20d": "min(close / running_max_close - 1) over prior 20 sessions",
    "max_drawdown_60d": "min(close / running_max_close - 1) over prior 60 sessions",
    "ret_60d": "close / close.shift(60) - 1",
    "distance_to_60d_low": "close / low_60d - 1",
    "turnover_zscore_20d": "(turnover - mean20(turnover)) / std20(turnover)",
    "amount_ratio_5d_20d": "mean5(amount) / mean20(amount)",
    "money_median_5d_vs_20d": "median5(money) / median20(money) - 1",
    "up_day_volume_share_20d": "sum(volume on up days over 20d) / sum(volume over 20d)",
    "volume_up_price_not_down_5d": "sum(volume where close >= close.shift(1) over 5d) / sum(volume over 5d)",
}

BULLISH_FORMULAS: dict[str, str] = {
    "ret_5d": "ret_5d",
    "ret_20d": "ret_20d",
    "stock_vs_board_5d": "stock_vs_board_5d",
    "stock_vs_board_20d": "stock_vs_board_20d",
    "close_vs_sma20": "close_vs_sma20",
    "close_position_20d": "close_position_20d",
    "distance_to_20d_high": "-distance_to_20d_high",
    "distance_from_20d_low": "distance_from_20d_low",
    "higher_low_slope_10d": "higher_low_slope_10d",
    "max_drawdown_20d": "max_drawdown_20d",
    "max_drawdown_60d": "max_drawdown_60d",
    "ret_60d": "ret_60d",
    "distance_to_60d_low": "distance_to_60d_low",
    "turnover_zscore_20d": "turnover_zscore_20d",
    "amount_ratio_5d_20d": "amount_ratio_5d_20d",
    "money_median_5d_vs_20d": "money_median_5d_vs_20d",
    "up_day_volume_share_20d": "up_day_volume_share_20d",
    "volume_up_price_not_down_5d": "volume_up_price_not_down_5d",
}

MORPHOLOGY_ANCHORS = ["volatility_20d", "max_drawdown_20d", "distance_to_20d_low", "distance_to_20d_high", "close_position_20d", "ret_20d"]
ALLOWED_FAMILY_PAIRS = [
    ("relative_strength", "range_position"),
    ("relative_strength", "drawdown_exclusion"),
    ("relative_strength", "participation"),
    ("range_position", "participation"),
    ("drawdown_exclusion", "participation"),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 13A2 compression directional disambiguation preflight.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check-inputs-only", action="store_true")
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


def resolve_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {key: topic_path(value) for key, value in config.get("paths", {}).items()}


def output_paths() -> dict[str, Path]:
    return {
        "input_artifact_audit": TABLE_DIR / "input_artifact_audit.csv",
        "upstream_13a_lineage_audit": TABLE_DIR / "upstream_13a_lineage_audit.csv",
        "base_compression_cohort_audit": TABLE_DIR / "base_compression_cohort_audit.csv",
        "directional_feature_availability_audit": TABLE_DIR / "directional_feature_availability_audit.csv",
        "directional_filter_dictionary": TABLE_DIR / "directional_filter_dictionary.csv",
        "directional_filter_threshold_freeze_audit": TABLE_DIR / "directional_filter_threshold_freeze_audit.csv",
        "directional_filter_matched_control_audit": TABLE_DIR / "directional_filter_matched_control_audit.csv",
        "compression_directional_readout": TABLE_DIR / "compression_directional_readout.csv",
        "compression_directional_badside_utility_audit": TABLE_DIR / "compression_directional_badside_utility_audit.csv",
        "compression_directional_morphology_audit": TABLE_DIR / "compression_directional_morphology_audit.csv",
        "compression_directional_stability_audit": TABLE_DIR / "compression_directional_stability_audit.csv",
        "compression_directional_search_multiplicity_audit": TABLE_DIR / "compression_directional_search_multiplicity_audit.csv",
        "compression_directional_deployability_gate_audit": TABLE_DIR / "compression_directional_deployability_gate_audit.csv",
        "compression_directional_disambiguation_decision": TABLE_DIR / "compression_directional_disambiguation_decision.csv",
        "compression_base_panel": LOCAL_CACHE_DIR / "compression_base_panel.parquet",
        "directional_filter_matrix": LOCAL_CACHE_DIR / "directional_filter_matrix.parquet",
        "report": REPORT_DIR / "compression_directional_disambiguation_preflight_report.md",
        "manifest": MANIFEST_DIR / f"{RUN_ID}_manifest.json",
    }


def read_table(path: Path, **kwargs: Any) -> pd.DataFrame:
    return r13a.read_table(path, **kwargs)


def write_df(path: Path, frame: pd.DataFrame) -> Path:
    return r13a.write_df(path, frame)


def write_text(path: Path, text: str) -> Path:
    return r13a.write_text(path, text)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    return r13a.write_json(path, payload)


def file_sha(path: Path) -> str:
    return r13a.file_sha256(path) if path.exists() and path.is_file() else ""


def count_rows(path: Path) -> int | float:
    return r13a.count_rows(path)


def safe_rate(num: Any, den: Any) -> float:
    return r13a.safe_rate(num, den)


def boolish(value: Any) -> bool:
    return r13a.boolish(value)


def bool_series(series: pd.Series) -> pd.Series:
    return r13a.bool_series(series)


def finite_numeric(series: pd.Series) -> pd.Series:
    return r13a.finite_numeric(series)


def auc_score(values: pd.Series, labels: pd.Series) -> float:
    return r13a.auc_score(values, labels)


def normal_ci_diff(p1: float, n1: int, p0: float, n0: int, alpha: float = 0.10) -> tuple[float, float]:
    return r13a.normal_ci_diff(p1, n1, p0, n0, alpha=alpha)


def top_decile_lift(values: pd.Series, labels: pd.Series) -> float:
    return r13a.top_decile_lift(values, labels)


def max_mix_delta(left: pd.DataFrame, right: pd.DataFrame, col: str) -> float:
    return r13a.max_mix_delta(left, right, col)


def stable_hash(value: Any) -> str:
    return r13a.stable_hash(value)


def input_expected_columns() -> dict[str, tuple[str, ...]]:
    return {
        "requirement": (),
        "upstream_requirement_13a": (),
        "upstream_report_13a": (),
        "upstream_requirement_12a7g": (),
        "upstream_config_12a7g": (),
        "pit_topn_400_100_executable_daily": ("usable_trade_date", "instrument", "board_bucket"),
        "pit_topn_400_100_membership_daily": ("membership_date", "instrument", "board_bucket"),
        "stock_daily_qfq_dir": (),
        "global_regime_calendar": ("date", "daily_regime_bucket", "daily_regime_conflict_n", "daily_regime_conflict_flag"),
        "upstream_12a7g_table_dir": (),
        "upstream_12a7g_manifest": (),
        "upstream_full_pit_label_panel_cache": ("reference_date", "instrument", "winner_positive", "upper_first", "lower_first"),
        "upstream_full_pit_primitive_panel_cache": (),
        "upstream_13a_table_dir": (),
        "upstream_13a_manifest": (),
        "upstream_13a_decision": ("decision_state", "selected_token_id", "selected_token_family_id", "sequence_mining_authorized"),
        "upstream_13a_token_dictionary": ("token_id", "primitive_id", "threshold_rule", "threshold_value", "threshold_split", "comparator"),
        "upstream_13a_readout": ("token_id", "split_bucket", "treated_n", "auc_one_vs_rest"),
        "upstream_13a_badside": ("token_id", "split_bucket", "utility_proxy_per_entry", "cost_buffer_return"),
        "upstream_13a_matched_control": ("token_id", "split_bucket", "control_match_quality"),
        "upstream_13a_deployability": ("token_id", "split_bucket", "deployability_status"),
        "upstream_13a_morphology": ("token_id", "split_bucket", "morphology_flag"),
        "upstream_13a_native_thresholds": ("threshold_id", "threshold_value", "threshold_source_split"),
        "upstream_13a_label_portability": ("split_bucket", "denominator_n", "label_stability_status"),
    }


OPTIONAL_INPUTS = {"upstream_full_pit_label_panel_cache", "upstream_full_pit_primitive_panel_cache"}


def lineage_role_for_artifact(artifact_id: str) -> str:
    if artifact_id.startswith("upstream_13a"):
        return "upstream_13a_lineage"
    if artifact_id.startswith("upstream_12a7g") or artifact_id.startswith("upstream_full"):
        return "upstream_12a7g_label_lineage"
    if artifact_id in {"pit_topn_400_100_executable_daily", "pit_topn_400_100_membership_daily", "stock_daily_qfq_dir", "global_regime_calendar"}:
        return "raw_pit_rebuild_input"
    return "run_config_input"


def build_input_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    expected = input_expected_columns()
    rows: list[dict[str, Any]] = []
    for artifact_id, path in resolved.items():
        required_cols = expected.get(artifact_id, ())
        required_flag = artifact_id not in OPTIONAL_INPUTS
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
                        sample = pd.read_parquet(path).head(5)
                    elif suffixes.endswith((".csv", ".csv.gz")):
                        sample = pd.read_csv(path, nrows=5, low_memory=False)
                    else:
                        sample = pd.DataFrame()
                    column_count = len(sample.columns) if suffixes.endswith((".csv", ".csv.gz", ".parquet")) else np.nan
                    missing = sorted(set(required_cols) - set(sample.columns)) if required_cols else []
                    schema_status = "pass" if not missing else "missing_columns:" + ";".join(missing)
                    row_count = count_rows(path)
            except Exception as exc:
                read_status = f"read_error:{type(exc).__name__}"
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "row_count": row_count,
                "column_count": column_count,
                "sha256": file_sha(path),
                "schema_status": schema_status,
                "read_status": read_status,
                "required_flag": required_flag,
                "lineage_role": lineage_role_for_artifact(artifact_id),
            }
        )
    return pd.DataFrame(rows)


def input_gate_status(input_audit: pd.DataFrame) -> tuple[str, str]:
    bad = input_audit.loc[
        input_audit["required_flag"].astype(bool)
        & (
            input_audit["read_status"].astype(str).ne("pass")
            | input_audit["schema_status"].astype(str).str.startswith("missing_columns")
        )
    ]
    if len(bad):
        return "fail", ";".join(bad["artifact_id"].astype(str).tolist())
    return "pass", ""


def load_cost_buffer(resolved: dict[str, Path], config: dict[str, Any]) -> tuple[float, str]:
    default = float(config.get("cost_buffer", {}).get("default_return", 0.01))
    badside_path = resolved.get("upstream_13a_badside")
    if badside_path and badside_path.exists():
        try:
            badside = read_table(badside_path)
            vals = finite_numeric(badside.get("cost_buffer_return", pd.Series(dtype=float))).dropna().unique()
            if len(vals):
                return float(vals[0]), "upstream_13a_badside_cost_buffer_return"
        except Exception:
            pass
    cfg_13a_path = EXPERIMENT_DIR / "configs" / "config_13a_full_pit_native_token_cartography_preflight.yaml"
    if cfg_13a_path.exists():
        try:
            cfg_13a = r13a.load_yaml(cfg_13a_path)
            if "thresholds" in cfg_13a and "cost_buffer_bps" in cfg_13a["thresholds"]:
                return float(cfg_13a["thresholds"]["cost_buffer_bps"]) / 10000.0, "upstream_13a_config_cost_buffer_bps"
        except Exception:
            pass
    return default, "default_cost_buffer_return"


def upstream_13a_lineage_audit(resolved: dict[str, Path], config: dict[str, Any]) -> tuple[pd.DataFrame, str, str, float]:
    expected_token = config.get("base_compression", {}).get("selected_token_id", BASE_TOKEN_ID)
    rows: list[dict[str, Any]] = []
    status = "pass"
    reason: list[str] = []
    threshold = np.nan
    try:
        decision = read_table(resolved["upstream_13a_decision"])
        token_dict = read_table(resolved["upstream_13a_token_dictionary"])
        dec = decision.iloc[0]
        tok = token_dict.loc[token_dict["token_id"].astype(str).eq(str(expected_token))]
        if tok.empty:
            status = "fail"
            reason.append("selected_token_missing_in_13a_dictionary")
            tok_row = pd.Series(dtype=object)
        else:
            tok_row = tok.iloc[0]
            threshold = float(tok_row["threshold_value"])
        checks = {
            "input_gate_status": str(dec.get("input_gate_status", "")) == "pass",
            "upstream_lineage_gate_status": str(dec.get("upstream_lineage_gate_status", "")) == "pass",
            "native_universe_gate_status": str(dec.get("native_universe_gate_status", "")) == "pass",
            "label_portability_gate_status": str(dec.get("label_portability_gate_status", "")) == "pass",
            "selected_token_id": str(dec.get("selected_token_id", "")) == str(expected_token),
            "selected_token_family_id": str(dec.get("selected_token_family_id", "")) == str(config.get("base_compression", {}).get("selected_token_family_id", "volatility_range")),
            "sequence_mining_authorized": not boolish(dec.get("sequence_mining_authorized", False)),
            "dictionary_primitive_id": str(tok_row.get("primitive_id", "")) == str(config.get("base_compression", {}).get("selected_primitive_id", "volatility_20d")),
            "dictionary_threshold_rule": str(tok_row.get("threshold_rule", "")) == "bottom_20pct",
            "dictionary_threshold_split": str(tok_row.get("threshold_split", "")) == "train",
            "dictionary_available_at": str(tok_row.get("available_at", "")) == "reference_date_close",
            "dictionary_future_data_used": not boolish(tok_row.get("future_data_used", True)),
            "dictionary_comparator": str(tok_row.get("comparator", "")) == "le",
        }
        for check_id, ok in checks.items():
            if not ok:
                status = "fail"
                reason.append(check_id)
            rows.append(
                {
                    "lineage_check_id": check_id,
                    "observed_value": str(dec.get(check_id, tok_row.get(check_id.replace("dictionary_", ""), ""))),
                    "expected_value": "contract",
                    "lineage_status": "pass" if ok else "fail",
                    "artifact_path": str(resolved["upstream_13a_decision"] if not check_id.startswith("dictionary_") else resolved["upstream_13a_token_dictionary"]),
                    "sha256": file_sha(resolved["upstream_13a_decision"] if not check_id.startswith("dictionary_") else resolved["upstream_13a_token_dictionary"]),
                }
            )
    except Exception as exc:
        status = "fail"
        reason.append(f"read_error:{type(exc).__name__}")
        rows.append(
            {
                "lineage_check_id": "upstream_13a_artifact_read",
                "observed_value": f"{type(exc).__name__}:{exc}",
                "expected_value": "readable",
                "lineage_status": "fail",
                "artifact_path": str(resolved.get("upstream_13a_decision", "")),
                "sha256": "",
            }
        )
    cost, cost_source = load_cost_buffer(resolved, config)
    rows.append(
        {
            "lineage_check_id": "cost_buffer_return",
            "observed_value": cost,
            "expected_value": "same_value_for_base_and_treated",
            "lineage_status": "pass",
            "artifact_path": cost_source,
            "sha256": "",
        }
    )
    return pd.DataFrame(rows), status, ";".join(reason), threshold


def rolling_log_slope(series: pd.Series, window: int) -> pd.Series:
    values = np.log(finite_numeric(series).replace(0, np.nan))
    x = np.arange(window, dtype=float)
    x = x - x.mean()
    denom = float((x * x).sum())

    def slope(arr: np.ndarray) -> float:
        if not np.isfinite(arr).all():
            return np.nan
        y = arr - arr.mean()
        return float((x * y).sum() / denom)

    return values.rolling(window, min_periods=window).apply(slope, raw=True)


def add_extra_daily_directional_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    close = finite_numeric(out["close"])
    low = finite_numeric(out["low"])
    volume = finite_numeric(out.get("volume", pd.Series(np.nan, index=out.index)))
    money = finite_numeric(out.get("money", pd.Series(np.nan, index=out.index)))
    sma20 = close.rolling(20, min_periods=20).mean()
    out["close_vs_sma20"] = close / sma20.replace(0, np.nan) - 1.0
    out["higher_low_slope_10d"] = rolling_log_slope(low, 10)
    money_mean5 = money.rolling(5, min_periods=5).mean()
    money_mean20 = money.rolling(20, min_periods=20).mean()
    out["amount_ratio_5d_20d"] = money_mean5 / money_mean20.replace(0, np.nan)
    out["money_median_5d_vs_20d"] = money.rolling(5, min_periods=5).median() / money.rolling(20, min_periods=20).median().replace(0, np.nan) - 1.0
    up_day = close.ge(close.shift(1))
    up_volume = volume.where(up_day, 0.0)
    out["up_day_volume_share_20d"] = up_volume.rolling(20, min_periods=20).sum() / volume.rolling(20, min_periods=20).sum().replace(0, np.nan)
    out["volume_up_price_not_down_5d"] = up_volume.rolling(5, min_periods=5).sum() / volume.rolling(5, min_periods=5).sum().replace(0, np.nan)
    return out


def attach_qfq_directional_features(panel: pd.DataFrame, qfq_dir: Path) -> pd.DataFrame:
    out = panel.copy()
    extra_cols = [
        "close_vs_sma20",
        "higher_low_slope_10d",
        "amount_ratio_5d_20d",
        "money_median_5d_vs_20d",
        "up_day_volume_share_20d",
        "volume_up_price_not_down_5d",
    ]
    for col in extra_cols:
        if col not in out.columns:
            out[col] = np.nan
    cache = r13a.StockDailyCache(qfq_dir)
    for instrument, idx in out.groupby("instrument", sort=False).groups.items():
        daily = cache.get(str(instrument))
        if daily.frame is None or daily.frame.empty or daily.status == "duplicate_qfq_date":
            continue
        extra = add_extra_daily_directional_features(daily.frame)
        extra = extra.set_index("date", drop=False)
        dates = out.loc[idx, "reference_date"].astype(str).str[:10]
        for col in extra_cols:
            out.loc[idx, col] = dates.map(extra[col]).to_numpy(dtype=float)
    return out


def derive_directional_features(panel: pd.DataFrame, resolved: dict[str, Path] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = panel.copy()
    availability_rows: list[dict[str, Any]] = []
    if resolved is not None and "stock_daily_qfq_dir" in resolved:
        out = attach_qfq_directional_features(out, resolved["stock_daily_qfq_dir"])
    if {"ret_5d", "board_bucket", "reference_date"} <= set(out.columns) and "stock_vs_board_5d" not in out.columns:
        board = out.groupby(["board_bucket", "reference_date"], dropna=False)["ret_5d"].mean().rename("board_return_5d").reset_index()
        out = out.merge(board, on=["board_bucket", "reference_date"], how="left", sort=False)
        out["stock_vs_board_5d"] = finite_numeric(out["ret_5d"]) - finite_numeric(out["board_return_5d"])
    if "distance_to_20d_high" in out.columns:
        close_over_high = 1.0 + finite_numeric(out["distance_to_20d_high"])
        out["distance_to_20d_high_raw_13a"] = out["distance_to_20d_high"]
        out["distance_to_20d_high"] = 1.0 / close_over_high.replace(0, np.nan) - 1.0
    if "distance_to_20d_low" in out.columns:
        out["distance_from_20d_low"] = finite_numeric(out["distance_to_20d_low"])
    if {"distance_to_20d_high", "distance_from_20d_low"} <= set(out.columns):
        high_over_close = 1.0 + finite_numeric(out["distance_to_20d_high"])
        low_over_close = 1.0 / (1.0 + finite_numeric(out["distance_from_20d_low"])).replace(0, np.nan)
        denom = high_over_close - low_over_close
        out["close_position_20d"] = (1.0 - low_over_close) / denom.where(denom.abs().gt(EPSILON), np.nan)
        out.loc[(denom.abs() <= EPSILON), "close_position_20d"] = np.nan
    for family_id, primitives in FAMILY_PRIORITY.items():
        for primitive_id in primitives:
            if primitive_id == "distance_to_60d_low" and primitive_id not in out.columns and "distance_to_60d_low" in panel.columns:
                out[primitive_id] = finite_numeric(panel["distance_to_60d_low"])
            values = finite_numeric(out[primitive_id]) if primitive_id in out.columns else pd.Series(np.nan, index=out.index)
            available_n = int(values.notna().sum())
            availability_rows.append(
                {
                    "primitive_id": primitive_id,
                    "filter_family_id": family_id,
                    "raw_feature_formula": RAW_FORMULAS.get(primitive_id, primitive_id),
                    "bullish_score_formula": BULLISH_FORMULAS.get(primitive_id, primitive_id),
                    "available_at": "reference_date_close",
                    "future_data_used": False,
                    "available_row_n": available_n,
                    "nonfinite_row_n": int(values.isna().sum()),
                    "feature_availability_status": "available" if available_n > 0 else "not_available",
                }
            )
    return out, pd.DataFrame(availability_rows)


def bullish_score(panel: pd.DataFrame, primitive_id: str) -> pd.Series:
    raw = finite_numeric(panel[primitive_id]) if primitive_id in panel.columns else pd.Series(np.nan, index=panel.index)
    if primitive_id == "distance_to_20d_high":
        return -1.0 * raw
    return raw


def freeze_thresholds(panel: pd.DataFrame, base_mask: pd.Series, config: dict[str, Any], availability: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    train_base = base_mask & panel["split"].astype(str).eq("train")
    rules = config.get("directional_filters", {}).get("quantile_rules", [])
    for avail in availability.to_dict("records"):
        primitive_id = avail["primitive_id"]
        score = bullish_score(panel, primitive_id)
        train_values = score.loc[train_base].dropna()
        for rule in rules:
            q = float(rule["quantile"])
            threshold_value = float(train_values.quantile(q)) if len(train_values) else np.nan
            freeze_status = "pass" if len(train_values) >= 100 and pd.notna(threshold_value) else "fail_insufficient_train_values"
            if avail["feature_availability_status"] != "available":
                freeze_status = "not_available"
            rows.append(
                {
                    "primitive_id": primitive_id,
                    "filter_family_id": avail["filter_family_id"],
                    "raw_feature_formula": avail["raw_feature_formula"],
                    "bullish_score_formula": avail["bullish_score_formula"],
                    "threshold_rule": rule["threshold_rule"],
                    "threshold_quantile": q,
                    "threshold_value": threshold_value,
                    "threshold_source_split": "train",
                    "threshold_source_scope": "base_compression_cohort",
                    "available_at": "reference_date_close",
                    "future_data_used": False,
                    "feature_availability_status": avail["feature_availability_status"],
                    "threshold_freeze_status": freeze_status,
                }
            )
    return pd.DataFrame(rows)


def build_candidates(thresholds: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    available = thresholds.loc[thresholds["threshold_freeze_status"].eq("pass")].copy()
    rule_lookup = {
        (str(row.primitive_id), str(row.threshold_rule)): float(row.threshold_value)
        for row in available.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    ordinal = 1
    single_rules = [str(x["threshold_rule"]) for x in config.get("directional_filters", {}).get("quantile_rules", [])]
    pair_rules = [str(x["threshold_rule"]) for x in config.get("directional_filters", {}).get("pair_threshold_rules", [])]
    primitive_family = thresholds.drop_duplicates("primitive_id").set_index("primitive_id")["filter_family_id"].to_dict()
    for family_id, primitives in FAMILY_PRIORITY.items():
        for primitive_id in primitives:
            if primitive_id not in primitive_family:
                continue
            for rule in single_rules:
                if (primitive_id, rule) not in rule_lookup:
                    continue
                filter_id = f"{primitive_id}__{rule}"
                rows.append(
                    {
                        "filter_id": filter_id,
                        "candidate_ordinal": ordinal,
                        "candidate_type": "single_filter",
                        "filter_family_id": family_id,
                        "family_pair_id": "",
                        "primitive_id_1": primitive_id,
                        "primitive_id_2": "",
                        "threshold_rule_1": rule,
                        "threshold_rule_2": "",
                        "threshold_value_1": rule_lookup[(primitive_id, rule)],
                        "threshold_value_2": np.nan,
                        "filter_formula": f"base_compression_state AND {primitive_id}_bullish_score >= train_threshold({rule})",
                        "bullish_score_formula_1": BULLISH_FORMULAS.get(primitive_id, primitive_id),
                        "bullish_score_formula_2": "",
                        "candidate_grid_status": "pass",
                    }
                )
                ordinal += 1
    for fam1, fam2 in ALLOWED_FAMILY_PAIRS:
        prims1 = [p for p in FAMILY_PRIORITY[fam1] if any((p, r) in rule_lookup for r in pair_rules)][:3]
        prims2 = [p for p in FAMILY_PRIORITY[fam2] if any((p, r) in rule_lookup for r in pair_rules)][:3]
        for p1 in prims1:
            for p2 in prims2:
                for rule in pair_rules:
                    if (p1, rule) not in rule_lookup or (p2, rule) not in rule_lookup:
                        continue
                    filter_id = f"{p1}__{rule}__AND__{p2}__{rule}"
                    rows.append(
                        {
                            "filter_id": filter_id,
                            "candidate_ordinal": ordinal,
                            "candidate_type": "two_filter_conjunction",
                            "filter_family_id": f"{fam1}+{fam2}",
                            "family_pair_id": f"{fam1}+{fam2}",
                            "primitive_id_1": p1,
                            "primitive_id_2": p2,
                            "threshold_rule_1": rule,
                            "threshold_rule_2": rule,
                            "threshold_value_1": rule_lookup[(p1, rule)],
                            "threshold_value_2": rule_lookup[(p2, rule)],
                            "filter_formula": (
                                f"base_compression_state AND {p1}_bullish_score >= train_threshold({rule}) "
                                f"AND {p2}_bullish_score >= train_threshold({rule})"
                            ),
                            "bullish_score_formula_1": BULLISH_FORMULAS.get(p1, p1),
                            "bullish_score_formula_2": BULLISH_FORMULAS.get(p2, p2),
                            "candidate_grid_status": "pass",
                        }
                    )
                    ordinal += 1
    candidates = pd.DataFrame(rows)
    max_n = int(config.get("directional_filters", {}).get("max_directional_candidate_n", 240))
    if len(candidates) > max_n:
        candidates["candidate_grid_status"] = "fail_exceeds_preregistered_max"
    return candidates


def apply_candidate_matrix(panel: pd.DataFrame, base_mask: pd.Series, candidates: pd.DataFrame) -> pd.DataFrame:
    row_id = panel.get("row_id", pd.Series(np.arange(len(panel), dtype=np.int64))).to_numpy()
    cols: dict[str, Any] = {"row_id": row_id}
    for row in candidates.itertuples(index=False):
        score1 = bullish_score(panel, row.primitive_id_1)
        mask = base_mask & score1.ge(float(row.threshold_value_1))
        if row.candidate_type == "two_filter_conjunction":
            score2 = bullish_score(panel, row.primitive_id_2)
            mask = mask & score2.ge(float(row.threshold_value_2))
        cols[row.filter_id] = mask.to_numpy(dtype=bool)
    return pd.DataFrame(cols)


def add_directional_deciles(panel: pd.DataFrame, base_mask: pd.Series, availability: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    train_base = base_mask & out["split"].astype(str).eq("train")
    for row in availability.loc[availability["feature_availability_status"].eq("available")].itertuples(index=False):
        primitive_id = str(row.primitive_id)
        score = bullish_score(out, primitive_id)
        vals = score.loc[train_base].dropna()
        col = f"{primitive_id}_directional_decile"
        out[col] = np.nan
        if len(vals) < 10:
            continue
        qs = vals.quantile(np.linspace(0.1, 0.9, 9)).to_numpy(dtype=float)
        out[col] = np.searchsorted(qs, score.to_numpy(dtype=float), side="right").astype(float)
        out.loc[score.isna(), col] = np.nan
    return out


def family_for_primitive(primitive_id: str) -> str:
    for family_id, primitives in FAMILY_PRIORITY.items():
        if primitive_id in primitives:
            return family_id
    return ""


def included_directional_deciles(candidate: pd.Series, availability: pd.DataFrame) -> list[str]:
    excluded_families = {family_for_primitive(str(candidate["primitive_id_1"]))}
    if str(candidate.get("primitive_id_2", "")):
        excluded_families.add(family_for_primitive(str(candidate["primitive_id_2"])))
    included: list[str] = []
    available_prims = set(availability.loc[availability["feature_availability_status"].eq("available"), "primitive_id"].astype(str))
    for family_id, primitives in FAMILY_PRIORITY.items():
        if family_id in excluded_families:
            continue
        for primitive_id in primitives:
            if primitive_id in available_prims:
                included.append(f"{primitive_id}_directional_decile")
                break
    return included


def standardized_diff(panel: pd.DataFrame, treated_mask: pd.Series, control_mask: pd.Series, cols: list[str]) -> float:
    diffs: list[float] = []
    for col in cols:
        if col not in panel.columns:
            continue
        t = finite_numeric(panel.loc[treated_mask, col]).dropna()
        c = finite_numeric(panel.loc[control_mask, col]).dropna()
        if len(t) == 0 or len(c) == 0:
            continue
        pooled = math.sqrt((float(t.var(ddof=0)) + float(c.var(ddof=0))) / 2.0)
        diffs.append(0.0 if pooled == 0 else abs(float(t.mean()) - float(c.mean())) / pooled)
    return float(max(diffs)) if diffs else np.nan


def control_quality(level_name: str, ratio: float, max_smd: float) -> str:
    if pd.isna(ratio) or ratio < 2 or pd.isna(max_smd):
        return "insufficient_control"
    if level_name in {"level_0", "level_1"} and ratio >= 3 and max_smd <= 0.25:
        return "primary_comparable"
    if level_name == "level_2" and ratio >= 2 and max_smd <= 0.50:
        return "coarsened_caveat"
    return "insufficient_control"


def match_masks(
    panel: pd.DataFrame,
    base_mask: pd.Series,
    candidate_mask: pd.Series,
    split: str,
    candidate: pd.Series,
    availability: pd.DataFrame,
    match_code_cache: dict[tuple[str, ...], pd.Series] | None = None,
) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
    split_base = base_mask & panel["split"].astype(str).eq(split)
    raw_treated = split_base & candidate_mask
    raw_control = split_base & ~candidate_mask
    included = included_directional_deciles(candidate, availability)
    levels = [
        ("level_0", ["reference_month", "board_bucket", "market_regime_bucket", "volatility_20d_decile", "liquidity_metric_decile", *included]),
        ("level_1", ["reference_quarter", "board_bucket", "market_regime_bucket", "volatility_20d_decile", "liquidity_metric_decile"]),
        ("level_2", ["reference_quarter", "board_bucket", "market_regime_bucket", "volatility_20d_decile"]),
        ("level_3", ["calendar_year", "board_bucket", "market_regime_bucket", "volatility_20d_decile"]),
    ]
    best_treated = raw_treated & False
    best_control = raw_control & False
    best_info = {
        "coarsening_level": "unmatched",
        "effective_control_ratio": 0.0,
        "matched_block_n": 0,
        "unmatched_treated_n": int(raw_treated.sum()),
        "max_standardized_diff_after_match": np.nan,
        "control_match_quality": "insufficient_control",
        "match_status": "fail",
        "excluded_match_decile_ids": excluded_match_deciles(candidate),
        "included_match_decile_ids": ";".join(included),
        "compression_severity_decile_used": "volatility_20d_decile",
        "liquidity_decile_used": "liquidity_metric_decile",
    }
    if int(raw_treated.sum()) == 0:
        return best_treated, best_control, best_info
    if match_code_cache is None:
        match_code_cache = {}
    for level_name, keys in levels:
        keys = [k for k in keys if k in panel.columns]
        if not keys:
            treated = raw_treated
            control = raw_control
            matched_blocks = 1
        else:
            key_tuple = tuple(keys)
            if key_tuple not in match_code_cache:
                key_frame = panel.loc[:, keys].copy()
                match_code_cache[key_tuple] = pd.util.hash_pandas_object(key_frame, index=False)
            codes = match_code_cache[key_tuple]
            treated_codes = pd.unique(codes.loc[raw_treated])
            control_codes = pd.unique(codes.loc[raw_control])
            treated_code_set = set(treated_codes.tolist())
            control_code_set = set(control_codes.tolist())
            common_codes = treated_code_set & control_code_set
            if common_codes:
                treated = raw_treated & codes.isin(common_codes)
                control = raw_control & codes.isin(common_codes)
            else:
                treated = raw_treated & False
                control = raw_control & False
            matched_blocks = int(len(common_codes))
        treated_n = int(treated.sum())
        control_n = int(control.sum())
        ratio = safe_rate(control_n, treated_n)
        max_smd = standardized_diff(panel, treated, control, ["volatility_20d", "liquidity_metric_decile", *included])
        quality = control_quality(level_name, ratio, max_smd)
        info = {
            "coarsening_level": level_name,
            "effective_control_ratio": ratio,
            "matched_block_n": matched_blocks,
            "unmatched_treated_n": int(raw_treated.sum()) - treated_n,
            "max_standardized_diff_after_match": max_smd,
            "control_match_quality": quality,
            "match_status": "pass" if quality != "insufficient_control" else "fail",
            "excluded_match_decile_ids": excluded_match_deciles(candidate),
            "included_match_decile_ids": ";".join(included),
            "compression_severity_decile_used": "volatility_20d_decile",
            "liquidity_decile_used": "liquidity_metric_decile",
        }
        best_treated, best_control, best_info = treated, control, info
        if quality in {"primary_comparable", "coarsened_caveat"}:
            break
    return best_treated, best_control, best_info


def excluded_match_deciles(candidate: pd.Series) -> str:
    families = {family_for_primitive(str(candidate["primitive_id_1"]))}
    if str(candidate.get("primitive_id_2", "")):
        families.add(family_for_primitive(str(candidate["primitive_id_2"])))
    ids: list[str] = []
    for family_id in sorted(families):
        for primitive_id in FAMILY_PRIORITY.get(family_id, []):
            ids.append(f"{primitive_id}_directional_decile")
    return ";".join(ids)


def candidate_score(panel: pd.DataFrame, base_mask: pd.Series, candidate: pd.Series) -> pd.Series:
    score1 = bullish_score(panel, str(candidate["primitive_id_1"]))
    if str(candidate.get("primitive_id_2", "")):
        score2 = bullish_score(panel, str(candidate["primitive_id_2"]))
        return pd.concat([score1.rank(pct=True), score2.rank(pct=True)], axis=1).mean(axis=1)
    return score1


def fast_fail_mask(frame: pd.DataFrame) -> pd.Series:
    return bool_series(frame.get("lower_first", pd.Series(False, index=frame.index))) & finite_numeric(frame.get("time_to_lower", pd.Series(np.nan, index=frame.index))).le(FAST_FAIL_MAX_SESSIONS)


def split_native(panel: pd.DataFrame, split: str) -> pd.DataFrame:
    return panel.loc[panel["native_scope"] & panel["split"].astype(str).eq(split)]


def split_base(panel: pd.DataFrame, base_mask: pd.Series, split: str) -> pd.DataFrame:
    return panel.loc[base_mask & panel["split"].astype(str).eq(split)]


def utility_per_entry(frame: pd.DataFrame, cost: float) -> float:
    n = len(frame)
    if n == 0:
        return np.nan
    upper = safe_rate(bool_series(frame["upper_first"]).sum(), n)
    lower = safe_rate(bool_series(frame["lower_first"]).sum(), n)
    median_upper = finite_numeric(frame.get("upper_barrier", pd.Series(dtype=float))).median()
    median_lower = abs(finite_numeric(frame.get("lower_barrier", pd.Series(dtype=float))).median())
    return upper * median_upper - lower * median_lower - cost if pd.notna(upper) and pd.notna(lower) else np.nan


def utility_ci_low(value: float, n: int) -> float:
    if pd.isna(value) or n <= 1:
        return np.nan
    return float(value) - 1.65 * abs(float(value)) / math.sqrt(float(n))


def bootstrap_contexts(panel: pd.DataFrame, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    boot_cfg = config.get("bootstrap", {})
    seed = int(boot_cfg.get("seed", 13202))
    n_resamples = int(boot_cfg.get("n_resamples", 500))
    contexts: dict[str, dict[str, Any]] = {}
    for split_idx, split in enumerate(SPLITS):
        split_mask = panel["native_scope"] & panel["split"].astype(str).eq(split)
        labels = panel.loc[split_mask, "instrument"].astype(str) + "|" + panel.loc[split_mask, "reference_month"].astype(str)
        unique_labels = pd.Index(pd.unique(labels))
        n_blocks = len(unique_labels)
        code_map = pd.Series(np.arange(n_blocks, dtype=np.int64), index=unique_labels)
        codes = pd.Series(-1, index=panel.index, dtype=np.int64)
        codes.loc[split_mask] = labels.map(code_map).to_numpy(dtype=np.int64)
        rng = np.random.default_rng(seed + split_idx)
        weights = np.zeros((n_resamples, n_blocks), dtype=np.float32)
        if n_blocks:
            for i in range(n_resamples):
                draws = rng.integers(0, n_blocks, size=n_blocks)
                weights[i] = np.bincount(draws, minlength=n_blocks).astype(np.float32)
        contexts[split] = {
            "codes": codes,
            "weights": weights,
            "n_blocks": n_blocks,
            "seed": seed,
            "n_resamples": n_resamples,
            "min_valid_replicates": int(boot_cfg.get("min_valid_replicates", 250)),
            "ci_low_quantile": float(boot_cfg.get("ci_low_quantile", 0.05)),
            "unit": str(boot_cfg.get("unit", "instrument_month_block")),
        }
    return contexts


def block_sum(panel: pd.DataFrame, mask: pd.Series, codes: pd.Series, n_blocks: int, field: str | None = None) -> np.ndarray:
    valid = mask & codes.ge(0)
    if not valid.any() or n_blocks == 0:
        return np.zeros(n_blocks, dtype=float)
    block_codes = codes.loc[valid].to_numpy(dtype=np.int64)
    if field is None:
        weights = np.ones(len(block_codes), dtype=float)
    else:
        weights = finite_numeric(panel.loc[valid, field]).fillna(0.0).to_numpy(dtype=float)
    return np.bincount(block_codes, weights=weights, minlength=n_blocks).astype(float)


def bootstrap_metric_ci(
    panel: pd.DataFrame,
    treated_mask: pd.Series,
    control_mask: pd.Series,
    base_mask: pd.Series,
    native_mask: pd.Series,
    split: str,
    cost: float,
    contexts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ctx = contexts[split]
    weights = ctx["weights"]
    n_blocks = int(ctx["n_blocks"])
    if n_blocks == 0 or weights.size == 0:
        return {
            "winner_rate_diff_ci_low": np.nan,
            "winner_rate_diff_ci_high": np.nan,
            "utility_proxy_total_indexed_ci_low": np.nan,
            "utility_margin_vs_compression_baseline_ci_low": np.nan,
            "bootstrap_seed": ctx["seed"],
            "bootstrap_resample_n": ctx["n_resamples"],
            "bootstrap_valid_replicates": 0,
            "bootstrap_ci_low_quantile": ctx["ci_low_quantile"],
            "bootstrap_unit": ctx["unit"],
            "ci_status": "insufficient_ci_fail",
        }
    codes = ctx["codes"]
    t_n = weights @ block_sum(panel, treated_mask, codes, n_blocks)
    c_n = weights @ block_sum(panel, control_mask, codes, n_blocks)
    b_n = weights @ block_sum(panel, base_mask, codes, n_blocks)
    n_n = weights @ block_sum(panel, native_mask, codes, n_blocks)
    t_win = weights @ block_sum(panel, treated_mask, codes, n_blocks, "winner_positive")
    c_win = weights @ block_sum(panel, control_mask, codes, n_blocks, "winner_positive")
    t_upper = weights @ block_sum(panel, treated_mask, codes, n_blocks, "upper_first")
    t_lower = weights @ block_sum(panel, treated_mask, codes, n_blocks, "lower_first")
    b_upper = weights @ block_sum(panel, base_mask, codes, n_blocks, "upper_first")
    b_lower = weights @ block_sum(panel, base_mask, codes, n_blocks, "lower_first")
    t_median_upper = finite_numeric(panel.loc[treated_mask, "upper_barrier"]).median()
    t_median_lower = abs(finite_numeric(panel.loc[treated_mask, "lower_barrier"]).median())
    b_median_upper = finite_numeric(panel.loc[base_mask, "upper_barrier"]).median()
    b_median_lower = abs(finite_numeric(panel.loc[base_mask, "lower_barrier"]).median())
    with np.errstate(divide="ignore", invalid="ignore"):
        t_rate = t_win / t_n
        c_rate = c_win / c_n
        winner_diff = t_rate - c_rate
        t_util = (t_upper / t_n) * t_median_upper - (t_lower / t_n) * t_median_lower - cost
        b_util = (b_upper / b_n) * b_median_upper - (b_lower / b_n) * b_median_lower - cost
        total = t_util * (t_n / n_n)
        base_total = b_util * (b_n / n_n)
        margin = total - base_total
    valid = np.isfinite(winner_diff) & np.isfinite(total) & np.isfinite(margin)
    valid_n = int(valid.sum())
    status = "pass" if valid_n >= int(ctx["min_valid_replicates"]) else "insufficient_ci_fail"
    q = float(ctx["ci_low_quantile"])
    return {
        "winner_rate_diff_ci_low": float(np.nanquantile(winner_diff[valid], q)) if valid_n else np.nan,
        "winner_rate_diff_ci_high": float(np.nanquantile(winner_diff[valid], 1.0 - q)) if valid_n else np.nan,
        "utility_proxy_total_indexed_ci_low": float(np.nanquantile(total[valid], q)) if valid_n else np.nan,
        "utility_margin_vs_compression_baseline_ci_low": float(np.nanquantile(margin[valid], q)) if valid_n else np.nan,
        "bootstrap_seed": ctx["seed"],
        "bootstrap_resample_n": ctx["n_resamples"],
        "bootstrap_valid_replicates": valid_n,
        "bootstrap_ci_low_quantile": q,
        "bootstrap_unit": ctx["unit"],
        "ci_status": status,
    }


def evaluate_candidates(
    panel: pd.DataFrame,
    base_mask: pd.Series,
    candidates: pd.DataFrame,
    matrix: pd.DataFrame,
    availability: pd.DataFrame,
    config: dict[str, Any],
    cost: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    readout_rows: list[dict[str, Any]] = []
    bad_rows: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []
    matrix_idx = matrix.set_index("row_id")
    row_index = panel.get("row_id", pd.Series(np.arange(len(panel), dtype=np.int64))).to_numpy()
    panel_idx = panel.assign(_row_id=row_index).set_index("_row_id", drop=False)
    base_mask_idx = pd.Series(base_mask.to_numpy(dtype=bool), index=panel_idx.index)
    native_base_rates = {
        split: safe_rate(split_native(panel_idx, split)["winner_positive"].sum(), len(split_native(panel_idx, split)))
        for split in SPLITS
    }
    match_code_cache: dict[tuple[str, ...], pd.Series] = {}
    boot_contexts = bootstrap_contexts(panel_idx, config)
    for candidate in candidates.to_dict("records"):
        cand = pd.Series(candidate)
        cand_mask = matrix_idx[candidate["filter_id"]].reindex(panel_idx.index).fillna(False).astype(bool)
        score = candidate_score(panel_idx, base_mask_idx, cand)
        for split in SPLITS:
            treated_mask, control_mask, info = match_masks(panel_idx, base_mask_idx, cand_mask, split, cand, availability, match_code_cache)
            treated = panel_idx.loc[treated_mask]
            control = panel_idx.loc[control_mask]
            base = split_base(panel_idx, base_mask_idx, split)
            native = split_native(panel_idx, split)
            native_mask = panel_idx["native_scope"] & panel_idx["split"].astype(str).eq(split)
            split_base_mask = base_mask_idx & panel_idx["split"].astype(str).eq(split)
            boot = bootstrap_metric_ci(panel_idx, treated_mask, control_mask, split_base_mask, native_mask, split, cost, boot_contexts)
            match_rows.append(
                {
                    "filter_id": candidate["filter_id"],
                    "split_bucket": split,
                    "treated_n": int(len(treated)),
                    "control_n": int(len(control)),
                    **info,
                }
            )
            readout_rows.append(readout_row(candidate, split, treated, control, base, native, score, info, boot))
            bad_rows.append(badside_utility_row(candidate["filter_id"], split, treated, control, base, native, cost, native_base_rates[split], boot))
    return pd.DataFrame(readout_rows), pd.DataFrame(bad_rows), pd.DataFrame(match_rows)


def readout_row(candidate: dict[str, Any], split: str, treated: pd.DataFrame, control: pd.DataFrame, base: pd.DataFrame, native: pd.DataFrame, score: pd.Series, match_info: dict[str, Any], boot: dict[str, Any]) -> dict[str, Any]:
    treated_n = int(len(treated))
    control_n = int(len(control))
    treated_pos = int(bool_series(treated.get("winner_positive", pd.Series(dtype=bool))).sum()) if treated_n else 0
    control_pos = int(bool_series(control.get("winner_positive", pd.Series(dtype=bool))).sum()) if control_n else 0
    treated_rate = safe_rate(treated_pos, treated_n)
    control_rate = safe_rate(control_pos, control_n)
    diff = treated_rate - control_rate if pd.notna(treated_rate) and pd.notna(control_rate) else np.nan
    eval_frame = pd.concat([treated, control], axis=0)
    auc = auc_score(score.loc[eval_frame.index], eval_frame["winner_positive"]) if len(eval_frame) else np.nan
    rank_ic = score.loc[base.index].corr(base["winner_positive"].astype(float), method="spearman") if len(base) else np.nan
    top_lift = top_decile_lift(score.loc[base.index], base["winner_positive"]) if len(base) else np.nan
    return {
        "filter_id": candidate["filter_id"],
        "filter_family_id": candidate["filter_family_id"],
        "filter_formula": candidate["filter_formula"],
        "split_bucket": split,
        "treated_n": treated_n,
        "treated_positive_n": treated_pos,
        "treated_winner_rate": treated_rate,
        "control_n": control_n,
        "control_positive_n": control_pos,
        "control_winner_rate": control_rate,
        "compression_baseline_winner_rate": safe_rate(base["winner_positive"].sum(), len(base)),
        "native_baseline_winner_rate": safe_rate(native["winner_positive"].sum(), len(native)),
        "winner_rate_diff_vs_compression_control": diff,
        "winner_rate_diff_ci_low": boot["winner_rate_diff_ci_low"],
        "winner_rate_diff_ci_high": boot["winner_rate_diff_ci_high"],
        "auc_one_vs_compression_control": auc,
        "rank_ic_within_base_compression": rank_ic,
        "top_decile_lift_within_base_compression": top_lift,
        "control_match_quality": match_info.get("control_match_quality", "insufficient_control"),
        "readout_status": "pass" if treated_n > 0 and control_n > 0 and pd.notna(diff) and diff > 0 else "fail",
        "bootstrap_seed": boot["bootstrap_seed"],
        "bootstrap_resample_n": boot["bootstrap_resample_n"],
        "bootstrap_valid_replicates": boot["bootstrap_valid_replicates"],
        "bootstrap_ci_low_quantile": boot["bootstrap_ci_low_quantile"],
        "bootstrap_unit": boot["bootstrap_unit"],
        "ci_status": boot["ci_status"],
    }


def badside_utility_row(filter_id: str, split: str, treated: pd.DataFrame, control: pd.DataFrame, base: pd.DataFrame, native: pd.DataFrame, cost: float, native_base_rate: float, boot: dict[str, Any]) -> dict[str, Any]:
    treated_n = int(len(treated))
    control_n = int(len(control))
    lower_rate = safe_rate(bool_series(treated.get("lower_first", pd.Series(dtype=bool))).sum(), treated_n)
    control_lower_rate = safe_rate(bool_series(control.get("lower_first", pd.Series(dtype=bool))).sum(), control_n)
    fast_rate = safe_rate(fast_fail_mask(treated).sum(), treated_n)
    control_fast_rate = safe_rate(fast_fail_mask(control).sum(), control_n)
    same_rate = safe_rate(bool_series(treated.get("same_bar_conflict", pd.Series(dtype=bool))).sum(), treated_n)
    median_upper = finite_numeric(treated.get("upper_barrier", pd.Series(dtype=float))).median()
    median_lower = abs(finite_numeric(treated.get("lower_barrier", pd.Series(dtype=float))).median())
    utility = utility_per_entry(treated, cost)
    total = utility * safe_rate(treated_n, len(native)) if pd.notna(utility) else np.nan
    base_utility = utility_per_entry(base, cost)
    base_total = base_utility * safe_rate(len(base), len(native)) if pd.notna(base_utility) else np.nan
    margin = total - base_total if pd.notna(total) and pd.notna(base_total) else np.nan
    total_ci_low = boot["utility_proxy_total_indexed_ci_low"]
    margin_ci_low = boot["utility_margin_vs_compression_baseline_ci_low"]
    lower_uplift = lower_rate - control_lower_rate if pd.notna(lower_rate) and pd.notna(control_lower_rate) else np.nan
    fast_uplift = fast_rate - control_fast_rate if pd.notna(fast_rate) and pd.notna(control_fast_rate) else np.nan
    utility_status = "utility_pass" if pd.notna(utility) and utility > 0 and pd.notna(margin_ci_low) and margin_ci_low > 0 else "utility_fail"
    if pd.notna(utility) and utility > 0 and pd.notna(lower_uplift) and lower_uplift > 0:
        utility_status = "net_utility_positive_but_left_tail_not_disambiguated"
    badside_status = "pass" if pd.notna(lower_uplift) and lower_uplift <= 0 and pd.notna(fast_uplift) and fast_uplift <= 0.01 else "fail"
    return {
        "filter_id": filter_id,
        "split_bucket": split,
        "treated_lower_first_rate": lower_rate,
        "control_lower_first_rate": control_lower_rate,
        "lower_first_uplift_vs_compression_control": lower_uplift,
        "treated_fast_fail_rate": fast_rate,
        "control_fast_fail_rate": control_fast_rate,
        "fast_fail_uplift_vs_compression_control": fast_uplift,
        "treated_same_bar_conflict_rate": same_rate,
        "median_upper_barrier_return": median_upper,
        "median_abs_lower_barrier_return": median_lower,
        "utility_proxy_per_entry": utility,
        "utility_proxy_total_indexed": total,
        "utility_proxy_total_indexed_ci_low": total_ci_low,
        "compression_baseline_utility_total_indexed": base_total,
        "utility_margin_vs_compression_baseline": margin,
        "utility_margin_vs_compression_baseline_ci_low": margin_ci_low,
        "cost_buffer_return": cost,
        "cost_buffer_source": "lineage",
        "badside_status": badside_status,
        "utility_status": utility_status,
        "native_baseline_winner_rate": native_base_rate,
        "bootstrap_seed": boot["bootstrap_seed"],
        "bootstrap_resample_n": boot["bootstrap_resample_n"],
        "bootstrap_valid_replicates": boot["bootstrap_valid_replicates"],
        "bootstrap_ci_low_quantile": boot["bootstrap_ci_low_quantile"],
        "bootstrap_unit": boot["bootstrap_unit"],
        "ci_status": boot["ci_status"],
    }


def build_base_audit(panel: pd.DataFrame, base_mask: pd.Series, threshold: float, cost: float, cost_source: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ALL_SPLITS:
        native = panel.loc[panel["native_scope"]] if split == "all" else split_native(panel, split)
        base = panel.loc[base_mask] if split == "all" else split_base(panel, base_mask, split)
        utility = utility_per_entry(base, cost)
        rows.append(
            {
                "split_bucket": split,
                "native_denominator_n": int(len(native)),
                "base_compression_n": int(len(base)),
                "base_coverage_share": safe_rate(len(base), len(native)),
                "base_positive_n": int(bool_series(base.get("winner_positive", pd.Series(dtype=bool))).sum()) if len(base) else 0,
                "base_winner_rate": safe_rate(bool_series(base.get("winner_positive", pd.Series(dtype=bool))).sum(), len(base)),
                "base_lower_first_rate": safe_rate(bool_series(base.get("lower_first", pd.Series(dtype=bool))).sum(), len(base)),
                "base_fast_fail_rate": safe_rate(fast_fail_mask(base).sum(), len(base)),
                "base_utility_proxy_per_entry": utility,
                "base_utility_proxy_total_indexed": utility * safe_rate(len(base), len(native)) if pd.notna(utility) else np.nan,
                "base_board_mix_main_board_share": safe_rate(base["board_bucket"].astype(str).eq("main_board").sum(), len(base)) if len(base) else np.nan,
                "base_board_mix_chinext_share": safe_rate(base["board_bucket"].astype(str).eq("chinext").sum(), len(base)) if len(base) else np.nan,
                "threshold_value": threshold,
                "threshold_source_token_id": BASE_TOKEN_ID,
                "threshold_reproduction_status": "pass" if len(base) else "fail",
                "cost_buffer_return": cost,
                "cost_buffer_source": cost_source,
            }
        )
    return pd.DataFrame(rows)


def train_candidate_table(candidates: pd.DataFrame, readout: pd.DataFrame, badside: pd.DataFrame, match: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    train = readout.loc[readout["split_bucket"].eq("train")].merge(
        badside.loc[badside["split_bucket"].eq("train")],
        on=["filter_id", "split_bucket"],
        how="left",
        suffixes=("", "_bad"),
    )
    train = train.merge(candidates[["filter_id", "candidate_ordinal", "candidate_type"]], on="filter_id", how="left")
    th = config.get("thresholds", {})
    pass_mask = (
        finite_numeric(train["treated_n"]).ge(int(th.get("min_train_treated_n", 1000)))
        & finite_numeric(train["treated_positive_n"]).ge(int(th.get("min_train_positive_n", 100)))
        & train["control_match_quality"].astype(str).ne("insufficient_control")
        & finite_numeric(train["winner_rate_diff_vs_compression_control"]).gt(0)
        & finite_numeric(train["auc_one_vs_compression_control"]).ge(float(th.get("min_train_auc", 0.55)))
        & finite_numeric(train["lower_first_uplift_vs_compression_control"]).le(float(th.get("max_train_lower_first_uplift", 0.02)))
        & finite_numeric(train["utility_proxy_per_entry"]).gt(0)
    )
    train = train.copy()
    train["train_selection_gate_status"] = np.where(pass_mask, "pass", "fail")
    train["train_score"] = (
        finite_numeric(train["winner_rate_diff_vs_compression_control"])
        - finite_numeric(train["lower_first_uplift_vs_compression_control"]).clip(lower=0)
        + 0.5 * finite_numeric(train["utility_proxy_per_entry"])
    )
    train["selected_filter_train_score_rank"] = train["train_score"].rank(method="min", ascending=False)
    return train


def select_candidate(candidates: pd.DataFrame, train_candidates: pd.DataFrame) -> pd.Series | None:
    passed = train_candidates.loc[train_candidates["train_selection_gate_status"].eq("pass")].copy()
    if passed.empty:
        return None
    passed["simplicity_rank"] = np.where(passed["candidate_type"].eq("single_filter"), 0, 1)
    ranked = passed.sort_values(
        ["train_score", "lower_first_uplift_vs_compression_control", "treated_positive_n", "simplicity_rank", "filter_id"],
        ascending=[False, True, False, True, True],
        kind="mergesort",
    )
    filter_id = str(ranked.iloc[0]["filter_id"])
    selected = candidates.loc[candidates["filter_id"].eq(filter_id)].iloc[0].copy()
    selected["selected_filter_train_score_rank"] = int(ranked.iloc[0]["selected_filter_train_score_rank"])
    return selected


def gate_for_selected(selected_id: str | None, readout: pd.DataFrame, badside: pd.DataFrame, deploy: pd.DataFrame, morphology: pd.DataFrame, stability: pd.DataFrame, search: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    if selected_id is None:
        return {
            "winner_uplift_gate_status": "fail",
            "direction_readout_gate_status": "fail",
            "control_quality_gate_status": "not_applicable_no_selected_filter",
            "badside_utility_gate_status": "fail",
            "morphology_gate_status": "not_applicable_no_selected_filter",
            "morphology_independent_evidence_gate_status": "not_applicable_no_selected_filter",
            "stability_gate_status": "not_applicable_no_selected_filter",
            "search_control_gate_status": "not_applicable_no_selected_filter",
            "deployability_gate_status": "not_applicable_no_selected_filter",
        }
    th = config.get("thresholds", {})
    ro = readout.loc[readout["filter_id"].eq(selected_id)]
    bs = badside.loc[badside["filter_id"].eq(selected_id)]
    dep = deploy.loc[deploy["filter_id"].eq(selected_id)]
    eval_splits = {"validation", "robustness"}
    direction_pass = True
    bad_pass = True
    for split in eval_splits:
        r = ro.loc[ro["split_bucket"].eq(split)]
        b = bs.loc[bs["split_bucket"].eq(split)]
        if r.empty or b.empty:
            direction_pass = False
            bad_pass = False
            continue
        rr = r.iloc[0]
        bb = b.iloc[0]
        if not (
            int(rr["treated_n"]) >= int(th.get("min_eval_treated_n", 500))
            and int(rr["treated_positive_n"]) >= int(th.get("min_eval_positive_n", 50))
            and str(rr["control_match_quality"]) in {"primary_comparable", "coarsened_caveat", "coarsened_caveat_pass_strict"}
            and float(rr["winner_rate_diff_vs_compression_control"]) > 0
            and float(rr["winner_rate_diff_ci_low"]) >= -0.01
            and float(rr["auc_one_vs_compression_control"]) >= float(th.get("min_eval_auc", 0.55))
            and float(rr["top_decile_lift_within_base_compression"]) >= float(th.get("min_top_decile_lift", 0.02))
        ):
            direction_pass = False
        if not (
            float(bb["lower_first_uplift_vs_compression_control"]) <= float(th.get("max_eval_lower_first_uplift", 0.0))
            and float(bb["fast_fail_uplift_vs_compression_control"]) <= float(th.get("max_eval_fast_fail_uplift", 0.01))
            and float(bb["utility_proxy_per_entry"]) > 0
            and float(bb["utility_margin_vs_compression_baseline_ci_low"]) > 0
        ):
            bad_pass = False
    morph_status = "pass"
    if len(morphology) and morphology["morphology_flag"].astype(str).eq("morphology_rediscovery_suspect").any():
        suspect_eval = morphology.loc[morphology["split_bucket"].isin(list(eval_splits))]
        morph_status = "pass" if suspect_eval["morphology_suspect_independent_evidence_status"].astype(str).eq("pass").all() else "fail"
    stability_status = "pass" if len(stability) and stability["stability_gate_status"].astype(str).eq("pass").any() else "fail"
    search_status = "pass" if len(search) and str(search.iloc[0].get("search_control_status", "")) == "pass" else "fail"
    deploy_status = "pass" if len(dep.loc[dep["split_bucket"].isin(list(eval_splits))]) and dep.loc[dep["split_bucket"].isin(list(eval_splits)), "deployability_status"].astype(str).eq("pass").all() else "fail"
    control_status = "pass" if ro.loc[ro["split_bucket"].isin(list(eval_splits)), "control_match_quality"].astype(str).isin({"primary_comparable", "coarsened_caveat", "coarsened_caveat_pass_strict"}).all() else "fail"
    return {
        "winner_uplift_gate_status": "pass" if direction_pass else "fail",
        "direction_readout_gate_status": "pass" if direction_pass else "fail",
        "control_quality_gate_status": control_status,
        "badside_utility_gate_status": "pass" if bad_pass else "fail",
        "morphology_gate_status": morph_status,
        "morphology_independent_evidence_gate_status": morph_status,
        "stability_gate_status": stability_status,
        "search_control_gate_status": search_status,
        "deployability_gate_status": deploy_status,
    }


def build_morphology_audit(panel: pd.DataFrame, base_mask: pd.Series, selected: pd.Series | None, readout: pd.DataFrame, badside: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if selected is None:
        return pd.DataFrame(
            columns=[
                "filter_id",
                "split_bucket",
                "morphology_anchor_id",
                "rank_corr_with_anchor",
                "max_abs_rank_corr_with_morphology_anchor",
                "morphology_flag",
                "utility_margin_vs_compression_baseline_ci_low",
                "lower_first_uplift_vs_compression_control",
                "control_match_quality",
                "morphology_suspect_independent_evidence_status",
                "morphology_collinearity_status",
            ]
        )
    score = candidate_score(panel, base_mask, selected)
    threshold = float(config.get("thresholds", {}).get("morphology_corr_threshold", 0.70))
    selected_id = str(selected["filter_id"])
    max_by_split: dict[str, float] = {}
    corr_by: dict[tuple[str, str], float] = {}
    for split in SPLITS:
        base = split_base(panel, base_mask, split)
        vals: list[float] = []
        for anchor in MORPHOLOGY_ANCHORS:
            if anchor not in panel.columns:
                corr = np.nan
            else:
                corr = score.loc[base.index].corr(finite_numeric(base[anchor]), method="spearman") if len(base) else np.nan
            corr_by[(split, anchor)] = corr
            vals.append(abs(corr) if pd.notna(corr) else 0.0)
        max_by_split[split] = float(max(vals)) if vals else np.nan
    suspect = any(v >= threshold for v in max_by_split.values() if pd.notna(v))
    for split in SPLITS:
        r = readout.loc[readout["filter_id"].eq(selected_id) & readout["split_bucket"].eq(split)]
        b = badside.loc[badside["filter_id"].eq(selected_id) & badside["split_bucket"].eq(split)]
        margin_ci = float(b.iloc[0]["utility_margin_vs_compression_baseline_ci_low"]) if len(b) else np.nan
        lower = float(b.iloc[0]["lower_first_uplift_vs_compression_control"]) if len(b) else np.nan
        match_quality = str(r.iloc[0]["control_match_quality"]) if len(r) else ""
        independent = (pd.notna(margin_ci) and margin_ci > 0 and pd.notna(lower) and lower <= 0 and match_quality == "primary_comparable")
        for anchor in MORPHOLOGY_ANCHORS:
            rows.append(
                {
                    "filter_id": selected_id,
                    "split_bucket": split,
                    "morphology_anchor_id": anchor,
                    "rank_corr_with_anchor": corr_by[(split, anchor)],
                    "max_abs_rank_corr_with_morphology_anchor": max_by_split[split],
                    "morphology_flag": "morphology_rediscovery_suspect" if suspect else "morphology_distinct_or_low_collinearity",
                    "utility_margin_vs_compression_baseline_ci_low": margin_ci,
                    "lower_first_uplift_vs_compression_control": lower,
                    "control_match_quality": match_quality,
                    "morphology_suspect_independent_evidence_status": "pass" if (not suspect or independent) else "fail",
                    "morphology_collinearity_status": "reported",
                }
            )
    return pd.DataFrame(rows)


def build_stability_audit(panel: pd.DataFrame, base_mask: pd.Series, selected: pd.Series | None, matrix: pd.DataFrame, cost: float, readout: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if selected is None:
        return pd.DataFrame(
            columns=[
                "filter_id",
                "slice_type",
                "slice_value",
                "treated_n",
                "control_n",
                "treated_share",
                "base_compression_share",
                "winner_rate_diff_vs_compression_control",
                "utility_proxy_per_entry",
                "stability_status",
                "calendar_year_positive_diff_slice_n",
                "calendar_year_positive_utility_slice_n",
                "max_abs_treated_minus_base_board_share",
                "regime_stability_caveat",
                "instrument_month_block_bootstrap_ci_low",
                "stability_gate_status",
            ]
        )
    selected_id = str(selected["filter_id"])
    matrix_idx = matrix.set_index("row_id")
    row_index = panel.get("row_id", pd.Series(np.arange(len(panel), dtype=np.int64))).to_numpy()
    panel_idx = panel.assign(_row_id=row_index).set_index("_row_id", drop=False)
    mask = matrix_idx[selected_id].reindex(panel_idx.index).fillna(False).astype(bool)
    base_mask_idx = pd.Series(base_mask.to_numpy(dtype=bool), index=panel_idx.index)
    for slice_type, col in [("calendar_year", "calendar_year"), ("board_bucket", "board_bucket"), ("market_regime_bucket", "market_regime_bucket")]:
        if col not in panel_idx.columns:
            continue
        for val, base_sub in panel_idx.loc[base_mask_idx].groupby(col, dropna=False):
            treated = base_sub.loc[mask.reindex(base_sub.index).fillna(False)]
            control = base_sub.loc[~mask.reindex(base_sub.index).fillna(False)]
            t_rate = safe_rate(treated["winner_positive"].sum(), len(treated))
            c_rate = safe_rate(control["winner_positive"].sum(), len(control))
            rows.append(
                {
                    "filter_id": selected_id,
                    "slice_type": slice_type,
                    "slice_value": val,
                    "treated_n": int(len(treated)),
                    "control_n": int(len(control)),
                    "treated_share": safe_rate(len(treated), int(mask.sum())),
                    "base_compression_share": safe_rate(len(base_sub), int(base_mask_idx.sum())),
                    "winner_rate_diff_vs_compression_control": t_rate - c_rate if pd.notna(t_rate) and pd.notna(c_rate) else np.nan,
                    "utility_proxy_per_entry": utility_per_entry(treated, cost),
                    "stability_status": "reported",
                }
            )
    audit = pd.DataFrame(rows)
    if audit.empty:
        return audit
    year = audit.loc[audit["slice_type"].eq("calendar_year") & finite_numeric(audit["treated_n"]).ge(100)]
    year_diff_pass_n = int(finite_numeric(year["winner_rate_diff_vs_compression_control"]).gt(0).sum())
    year_util_pass_n = int(finite_numeric(year["utility_proxy_per_entry"]).gt(0).sum())
    board = audit.loc[audit["slice_type"].eq("board_bucket")]
    max_board_drift = float((finite_numeric(board["treated_share"]) - finite_numeric(board["base_compression_share"])).abs().max()) if len(board) else np.nan
    gate_pass = year_diff_pass_n >= 3 and year_util_pass_n >= 3 and (pd.isna(max_board_drift) or max_board_drift <= float(config.get("thresholds", {}).get("max_board_drift_default", 0.15)))
    audit["calendar_year_positive_diff_slice_n"] = year_diff_pass_n
    audit["calendar_year_positive_utility_slice_n"] = year_util_pass_n
    audit["max_abs_treated_minus_base_board_share"] = max_board_drift
    regime_n = int(audit.loc[audit["slice_type"].eq("market_regime_bucket"), "slice_value"].nunique())
    audit["regime_stability_caveat"] = "regime_single_bucket_caveat" if regime_n <= 1 else "multi_regime_reported"
    audit["instrument_month_block_bootstrap_ci_low"] = readout.loc[readout["filter_id"].eq(selected_id), "winner_rate_diff_ci_low"].min()
    audit["stability_gate_status"] = "pass" if gate_pass else "fail"
    return audit


def build_search_audit(candidates: pd.DataFrame, selected: pd.Series | None, readout: pd.DataFrame, badside: pd.DataFrame, availability: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    selected_id = "" if selected is None else str(selected["filter_id"])
    single_n = int(candidates["candidate_type"].eq("single_filter").sum()) if len(candidates) else 0
    pair_n = int(candidates["candidate_type"].eq("two_filter_conjunction").sum()) if len(candidates) else 0
    available_n = int(availability["feature_availability_status"].eq("available").sum()) if len(availability) else 0
    effective_n = max(1, len(candidates) + 4 * available_n + 5 * 2 + 4)
    val = readout.loc[readout["filter_id"].eq(selected_id) & readout["split_bucket"].eq("validation")] if selected_id else pd.DataFrame()
    val_auc = float(val.iloc[0]["auc_one_vs_compression_control"]) if len(val) else np.nan
    auc_se = math.sqrt(max(val_auc * (1.0 - val_auc), 0.0) / max(float(val.iloc[0]["treated_n"] + val.iloc[0]["control_n"]), 1.0)) if len(val) and pd.notna(val_auc) else np.nan
    deflated_auc = val_auc - math.sqrt(2 * math.log(effective_n)) * auc_se if pd.notna(auc_se) else np.nan
    b_val = badside.loc[badside["filter_id"].eq(selected_id) & badside["split_bucket"].eq("validation")] if selected_id else pd.DataFrame()
    b_rob = badside.loc[badside["filter_id"].eq(selected_id) & badside["split_bucket"].eq("robustness")] if selected_id else pd.DataFrame()
    margin_val = float(b_val.iloc[0]["utility_margin_vs_compression_baseline_ci_low"]) if len(b_val) else np.nan
    margin_rob = float(b_rob.iloc[0]["utility_margin_vs_compression_baseline_ci_low"]) if len(b_rob) else np.nan
    q = min(1.0, safe_rate(effective_n * 0.05, max(int((finite_numeric(readout["winner_rate_diff_vs_compression_control"]).gt(0)).sum()), 1)))
    pass_gate = (
        pd.notna(q)
        and q <= float(config.get("thresholds", {}).get("fdr_q_value_max", 0.10))
        and pd.notna(deflated_auc)
        and deflated_auc >= float(config.get("thresholds", {}).get("min_deflated_auc_validation", 0.55))
        and pd.notna(margin_val)
        and margin_val > 0
        and pd.notna(margin_rob)
        and margin_rob > 0
    )
    return pd.DataFrame(
        [
            {
                "selected_filter_id": selected_id,
                "available_primitive_n": available_n,
                "single_filter_candidate_n": single_n,
                "two_filter_conjunction_candidate_n": pair_n,
                "candidate_grid_n": int(len(candidates)),
                "threshold_candidate_n": 4,
                "bullish_score_orientation_candidate_n": 1,
                "family_pair_candidate_n": len(ALLOWED_FAMILY_PAIRS),
                "match_coarsening_policy_n": 4,
                "base_state_candidate_n": 1,
                "effective_search_space_n": effective_n,
                "effective_search_space_n_outcome_free_adjusted": effective_n,
                "fdr_q_value": q,
                "deflated_auc_validation": deflated_auc,
                "deflated_utility_margin_validation_ci_low": margin_val,
                "deflated_utility_margin_robustness_ci_low": margin_rob,
                "search_control_status": "pass" if pass_gate else "fail",
            }
        ]
    )


def build_deployability(selected: pd.Series | None, panel: pd.DataFrame, base_mask: pd.Series, matrix: pd.DataFrame, readout: pd.DataFrame, badside: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if selected is None:
        return pd.DataFrame(
            columns=[
                "filter_id",
                "split_bucket",
                "coverage_share_within_native",
                "coverage_share_within_base_compression",
                "captured_positive_n",
                "captured_positive_share_within_base_compression",
                "utility_proxy_per_entry",
                "utility_proxy_total_indexed_ci_low",
                "precision_recall_frontier_status",
                "deployability_status",
            ]
        )
    selected_id = str(selected["filter_id"])
    matrix_idx = matrix.set_index("row_id")
    row_index = panel.get("row_id", pd.Series(np.arange(len(panel), dtype=np.int64))).to_numpy()
    panel_idx = panel.assign(_row_id=row_index).set_index("_row_id", drop=False)
    base_mask_idx = pd.Series(base_mask.to_numpy(dtype=bool), index=panel_idx.index)
    cand_mask = matrix_idx[selected_id].reindex(panel_idx.index).fillna(False).astype(bool)
    th = config.get("thresholds", {})
    for split in SPLITS:
        native = split_native(panel_idx, split)
        base = split_base(panel_idx, base_mask_idx, split)
        treated = panel_idx.loc[base_mask_idx & panel_idx["split"].astype(str).eq(split) & cand_mask]
        positive_n = int(treated["winner_positive"].sum()) if len(treated) else 0
        base_positive_n = int(base["winner_positive"].sum()) if len(base) else 0
        b = badside.loc[badside["filter_id"].eq(selected_id) & badside["split_bucket"].eq(split)]
        utility = float(b.iloc[0]["utility_proxy_per_entry"]) if len(b) else np.nan
        total_ci = float(b.iloc[0]["utility_proxy_total_indexed_ci_low"]) if len(b) else np.nan
        coverage_native = safe_rate(len(treated), len(native))
        coverage_base = safe_rate(len(treated), len(base))
        captured_share = safe_rate(positive_n, base_positive_n)
        status = (
            "pass"
            if pd.notna(coverage_native)
            and coverage_native >= float(th.get("min_coverage_share_within_native", 0.005))
            and pd.notna(coverage_base)
            and coverage_base >= float(th.get("min_coverage_share_within_base", 0.02))
            and positive_n >= int(th.get("min_captured_positive_n", 50))
            and pd.notna(captured_share)
            and captured_share >= float(th.get("min_captured_positive_share_within_base", 0.05))
            and pd.notna(utility)
            and utility > 0
            and pd.notna(total_ci)
            and total_ci > 0
            else "fail"
        )
        if status == "fail" and pd.notna(utility) and utility > 0:
            status = "niche_directional_filter_diagnostic_only"
        rows.append(
            {
                "filter_id": selected_id,
                "split_bucket": split,
                "coverage_share_within_native": coverage_native,
                "coverage_share_within_base_compression": coverage_base,
                "captured_positive_n": positive_n,
                "captured_positive_share_within_base_compression": captured_share,
                "utility_proxy_per_entry": utility,
                "utility_proxy_total_indexed_ci_low": total_ci,
                "precision_recall_frontier_status": "pass" if status == "pass" else "fail",
                "deployability_status": status,
            }
        )
    return pd.DataFrame(rows)


def decision_row(
    input_status: str,
    lineage_status: str,
    label_status: str,
    cost_status: str,
    base_status: str,
    candidates: pd.DataFrame,
    selected: pd.Series | None,
    gates: dict[str, Any],
    train_candidates: pd.DataFrame,
    morphology: pd.DataFrame | None = None,
    readout: pd.DataFrame | None = None,
) -> pd.DataFrame:
    selected_id = "" if selected is None else str(selected["filter_id"])
    selected_family = "" if selected is None else str(selected["filter_family_id"])
    selected_formula = "" if selected is None else str(selected.get("filter_formula", ""))
    selected_match_quality = ""
    if selected_id and readout is not None and len(readout):
        selected_rows = readout.loc[readout["filter_id"].eq(selected_id)]
        if len(selected_rows):
            selected_match_quality = ";".join(selected_rows["control_match_quality"].astype(str).drop_duplicates().tolist())
    selected_morphology_flag = ""
    if selected_id and morphology is not None and len(morphology) and "morphology_flag" in morphology.columns:
        selected_morphology_flag = ";".join(morphology["morphology_flag"].astype(str).drop_duplicates().tolist())
    state = "13A2_directional_filter_diagnostic_only_badside_or_utility_fail"
    next_req = "none"
    authorized = False
    reason = "one_or_more_final_gates_failed"
    if input_status != "pass" or lineage_status != "pass" or label_status != "pass":
        state = "13A2_blocked_input_or_label_lineage_failure"
        next_req = "fix_input_lineage_then_rerun_13A2"
        reason = "input_or_label_lineage_failure"
    elif cost_status != "pass":
        state = "13A2_blocked_cost_buffer_lineage_mismatch"
        next_req = "fix_lineage_cost_buffer_then_rerun_13A2"
        reason = "cost_buffer_lineage_mismatch"
    elif base_status != "pass":
        state = "13A2_base_compression_not_reproducible_stop"
        next_req = "revisit_13A_base_state"
        reason = "base_compression_not_reproducible"
    elif len(candidates) == 0 or candidates["candidate_grid_status"].astype(str).str.startswith("fail").any():
        state = "13A2_blocked_candidate_grid_not_preregistered"
        reason = "candidate_grid_empty_or_not_preregistered"
    elif selected is None:
        state = "13A2_no_directional_filter_survives_stop_event_mining"
        reason = "no_train_candidate_satisfies_directional_selection_gate"
    elif all(str(v) == "pass" for v in gates.values()):
        state = "13A2_compression_direction_supported_authorize_13B"
        next_req = "requirement_13b_train_frozen_compression_direction_sequence_mining.md"
        authorized = True
        reason = "selected_filter_passes_direction_badside_morphology_stability_search_deployability"
    elif gates.get("direction_readout_gate_status") == "fail" or gates.get("search_control_gate_status") == "fail":
        state = "13A2_no_directional_filter_survives_stop_event_mining"
        reason = "validation_robustness_direction_or_search_control_failed"
    elif gates.get("badside_utility_gate_status") == "fail" or gates.get("control_quality_gate_status") == "fail":
        state = "13A2_directional_filter_diagnostic_only_badside_or_utility_fail"
        reason = "badside_utility_or_control_quality_gate_failed"
    elif gates.get("deployability_gate_status") == "fail":
        state = "13A2_directional_filter_diagnostic_only_niche_coverage"
        reason = "deployability_gate_failed"
    elif gates.get("morphology_independent_evidence_gate_status") == "fail":
        state = "13A2_directional_filter_diagnostic_only_morphology_rediscovery"
        reason = "morphology_independent_evidence_failed"
    return pd.DataFrame(
        [
            {
                "decision_state": state,
                "next_allowed_requirement": next_req,
                "input_gate_status": input_status,
                "upstream_13a_lineage_gate_status": lineage_status,
                "label_lineage_gate_status": label_status,
                "cost_buffer_lineage_gate_status": cost_status,
                "base_compression_gate_status": base_status,
                "candidate_grid_gate_status": "pass" if len(candidates) and not candidates["candidate_grid_status"].astype(str).str.startswith("fail").any() else "fail",
                **gates,
                "selected_filter_id": selected_id,
                "selected_filter_family_id": selected_family,
                "selected_filter_formula": selected_formula,
                "selected_filter_candidate_ordinal": "" if selected is None else int(selected["candidate_ordinal"]),
                "selected_filter_train_score_rank": "" if selected is None else int(selected.get("selected_filter_train_score_rank", 0)),
                "selected_filter_control_match_quality": selected_match_quality,
                "selected_filter_morphology_flag": selected_morphology_flag,
                "sequence_mining_authorized": authorized,
                "scope_boundary": "failure_only_rejects_compression_conditional_directional_route_not_full_episode_13",
                "decision_reason": reason,
            }
        ]
    )


def render_report(decision: pd.DataFrame, base_audit: pd.DataFrame, availability: pd.DataFrame, candidates: pd.DataFrame, train_candidates: pd.DataFrame, selected: pd.Series | None, readout: pd.DataFrame, badside: pd.DataFrame, morphology: pd.DataFrame, stability: pd.DataFrame, search: pd.DataFrame, deploy: pd.DataFrame) -> str:
    dec = decision.iloc[0]
    selected_id = str(dec.get("selected_filter_id", ""))
    train_top = train_candidates.sort_values("train_score", ascending=False, kind="mergesort").head(10) if len(train_candidates) else pd.DataFrame()
    eval_readout = readout.loc[readout["filter_id"].eq(selected_id)] if selected_id else pd.DataFrame()
    eval_badside = badside.loc[badside["filter_id"].eq(selected_id)] if selected_id else pd.DataFrame()
    def md_table(df: pd.DataFrame, cols: list[str], max_rows: int = 20) -> str:
        if df.empty:
            return "_无记录_"
        return df[cols].head(max_rows).to_markdown(index=False)
    lines = [
        "# 13A2 Compression Directional Disambiguation Preflight Report",
        "",
        "## 裁决",
        "",
        f"- `decision_state`: `{dec['decision_state']}`",
        f"- `selected_filter_id`: `{selected_id or 'none'}`",
        f"- `sequence_mining_authorized`: `{boolish(dec['sequence_mining_authorized'])}`",
        f"- `next_allowed_requirement`: `{dec['next_allowed_requirement']}`",
        "",
        "13A2 的边界是固定 13A 的 `volatility_20d__bottom_20pct` compression cohort，只判断该 cohort 内是否存在 PIT-safe 方向过滤器。失败只否决 compression-conditional 路线，不否决 Episode 13 其他 base state。",
        "",
        "## Base Compression Cohort",
        "",
        md_table(
            base_audit,
            [
                "split_bucket",
                "native_denominator_n",
                "base_compression_n",
                "base_coverage_share",
                "base_winner_rate",
                "base_lower_first_rate",
                "base_utility_proxy_per_entry",
            ],
        ),
        "",
        "## Feature Availability",
        "",
        md_table(availability, ["filter_family_id", "primitive_id", "available_row_n", "feature_availability_status"], 30),
        "",
        "## Train Candidate Top 10",
        "",
        md_table(
            train_top,
            [
                "filter_id",
                "candidate_type",
                "treated_n",
                "treated_positive_n",
                "winner_rate_diff_vs_compression_control",
                "auc_one_vs_compression_control",
                "lower_first_uplift_vs_compression_control",
                "utility_proxy_per_entry",
                "control_match_quality",
                "train_score",
                "train_selection_gate_status",
            ],
            10,
        ),
        "",
        "## Selected Filter Readout",
        "",
        md_table(
            eval_readout,
            [
                "split_bucket",
                "treated_n",
                "treated_positive_n",
                "treated_winner_rate",
                "control_winner_rate",
                "winner_rate_diff_vs_compression_control",
                "auc_one_vs_compression_control",
                "top_decile_lift_within_base_compression",
                "control_match_quality",
            ],
        ),
        "",
        "## Bad-side / Utility",
        "",
        md_table(
            eval_badside,
            [
                "split_bucket",
                "lower_first_uplift_vs_compression_control",
                "fast_fail_uplift_vs_compression_control",
                "utility_proxy_per_entry",
                "utility_proxy_total_indexed",
                "utility_margin_vs_compression_baseline_ci_low",
                "badside_status",
                "utility_status",
            ],
        ),
        "",
        "## Morphology / Stability / Search / Deployability",
        "",
        md_table(search, ["selected_filter_id", "candidate_grid_n", "effective_search_space_n", "deflated_auc_validation", "search_control_status"]),
        "",
        md_table(deploy, ["split_bucket", "coverage_share_within_native", "coverage_share_within_base_compression", "captured_positive_n", "utility_proxy_per_entry", "deployability_status"]),
        "",
        "## Findings",
        "",
        "- 若 selected filter 在 validation/robustness 中 winner uplift 通过但 lower-first uplift 为小正数，本轮将其视为 `net_utility_positive_but_left_tail_not_disambiguated`，不授权 13B。",
        "- Control 锚定 compression cohort 内的 non-filter rows，并保留 `volatility_20d_decile`，因此读数主要反映方向过滤器的增量，而不是再次选择更深低波动。",
        "- Board 稳定性使用 treated share 相对 base compression share 的 drift，不再使用 13A 报告中不适合 topn_400_100 universe 的单 board 60% 绝对上限。",
    ]
    return "\n".join(lines)


def publishable_manifest_outputs(outputs: dict[str, Path]) -> dict[str, Path]:
    return {key: path for key, path in outputs.items() if "local_cache" not in path.parts and key != "manifest"}


def schema_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        suffixes = "".join(path.suffixes)
        if suffixes.endswith(".parquet"):
            frame = pd.read_parquet(path).head(0)
        elif suffixes.endswith((".csv", ".csv.gz")):
            frame = pd.read_csv(path, nrows=0)
        else:
            return ""
        return stable_hash({"columns": frame.columns.tolist(), "dtypes": {col: str(dtype) for col, dtype in frame.dtypes.items()}})
    except Exception:
        return ""


def local_cache_manifest_outputs(outputs: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, path in outputs.items():
        if "local_cache" not in path.parts:
            continue
        rows.append(
            {
                "artifact_id": key,
                "path": str(path),
                "exists": path.exists(),
                "row_count": count_rows(path) if path.exists() else np.nan,
                "schema_hash": schema_hash(path),
                "cache_used_as_input": False,
            }
        )
    return rows


def build_manifest(config_path: Path, config: dict[str, Any], outputs: dict[str, Path], input_audit: pd.DataFrame) -> dict[str, Any]:
    publishable = publishable_manifest_outputs(outputs)
    return {
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": r13a.git_revision(REPO_ROOT),
        "python": sys.version,
        "platform": platform.platform(),
        "config_path": str(config_path),
        "config_sha256": file_sha(config_path),
        "config_hash": stable_hash(config),
        "input_artifacts": input_audit.to_dict(orient="records"),
        "output_hashes": {key: file_sha(path) for key, path in publishable.items()},
        "publishable_outputs": {key: str(path) for key, path in publishable.items()},
        "local_cache_outputs_excluded": [str(path) for path in outputs.values() if "local_cache" in path.parts],
        "local_cache_audit": local_cache_manifest_outputs(outputs),
    }


def run(config_path: Path, mode: str = "full", check_inputs_only: bool = False) -> dict[str, Path]:
    config = r13a.load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    input_audit = build_input_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    input_status, input_reason = input_gate_status(input_audit)
    lineage_audit, lineage_status, lineage_reason, base_threshold = upstream_13a_lineage_audit(resolved, config)
    write_df(outputs["upstream_13a_lineage_audit"], lineage_audit)
    if check_inputs_only or mode == "check-inputs":
        manifest = build_manifest(config_path, config, outputs, input_audit)
        write_json(outputs["manifest"], manifest)
        return outputs

    panel, cache_used, _cache_status = r13a.load_base_panel(resolved)
    label_status, _label_reason = r13a.upstream_lineage_status(resolved)
    _decision_12, selected_formula, _selection_12, _thresholds_12 = r13a.selected_label_lineage(resolved)
    mismatch, mismatch_status = r13a.build_label_cache_mismatch_audit(panel, resolved, selected_formula, cache_used, {"label_cache_mismatch": {"return_abs_tolerance": 1e-10}})
    if mismatch_status != "pass":
        label_status = "fail"
    native_thresholds, _native_audit = r13a.freeze_native_thresholds(panel, config)
    native_panel = r13a.apply_native_filters(panel, native_thresholds)
    native_panel = r13a.add_match_deciles(native_panel, native_thresholds["liquidity_metric"])
    native_panel, availability = derive_directional_features(native_panel, resolved)
    cost, cost_source = load_cost_buffer(resolved, config)
    cost_status = "pass" if pd.notna(cost) and np.isfinite(cost) else "fail"
    base_mask = native_panel["native_scope"] & finite_numeric(native_panel["volatility_20d"]).le(float(base_threshold))
    native_panel = add_directional_deciles(native_panel, base_mask, availability)
    base_audit = build_base_audit(native_panel, base_mask, float(base_threshold), cost, cost_source)
    thresholds = freeze_thresholds(native_panel, base_mask, config, availability)
    candidates = build_candidates(thresholds, config)
    matrix = apply_candidate_matrix(native_panel, base_mask, candidates)
    readout, badside, match = evaluate_candidates(native_panel, base_mask, candidates, matrix, availability, config, cost)
    train_candidates = train_candidate_table(candidates, readout, badside, match, config)
    selected = select_candidate(candidates, train_candidates)
    morphology = build_morphology_audit(native_panel, base_mask, selected, readout, badside, config)
    stability = build_stability_audit(native_panel, base_mask, selected, matrix, cost, readout, config)
    search = build_search_audit(candidates, selected, readout, badside, availability, config)
    deploy = build_deployability(selected, native_panel, base_mask, matrix, readout, badside, config)

    base_status = "pass"
    min_cfg = config.get("base_compression", {})
    for split, min_n_key in [("train", "min_train_n"), ("validation", "min_validation_n"), ("robustness", "min_robustness_n")]:
        row = base_audit.loc[base_audit["split_bucket"].eq(split)]
        if row.empty or int(row.iloc[0]["base_compression_n"]) < int(min_cfg.get(min_n_key, 0)):
            base_status = "fail"
    if lineage_status != "pass" or pd.isna(base_threshold):
        base_status = "fail"
    selected_id = None if selected is None else str(selected["filter_id"])
    gates = gate_for_selected(selected_id, readout, badside, deploy, morphology, stability, search, config)
    decision = decision_row(input_status, lineage_status, label_status, cost_status, base_status, candidates, selected, gates, train_candidates, morphology, readout)

    write_df(outputs["base_compression_cohort_audit"], base_audit)
    write_df(outputs["directional_feature_availability_audit"], availability)
    write_df(outputs["directional_filter_threshold_freeze_audit"], thresholds)
    write_df(outputs["directional_filter_dictionary"], candidates)
    write_df(outputs["directional_filter_matched_control_audit"], match)
    write_df(outputs["compression_directional_readout"], readout)
    write_df(outputs["compression_directional_badside_utility_audit"], badside)
    write_df(outputs["compression_directional_morphology_audit"], morphology)
    write_df(outputs["compression_directional_stability_audit"], stability)
    write_df(outputs["compression_directional_search_multiplicity_audit"], search)
    write_df(outputs["compression_directional_deployability_gate_audit"], deploy)
    write_df(outputs["compression_directional_disambiguation_decision"], decision)
    write_df(outputs["compression_base_panel"], native_panel.loc[base_mask].copy())
    write_df(outputs["directional_filter_matrix"], matrix)
    report = render_report(decision, base_audit, availability, candidates, train_candidates, selected, readout, badside, morphology, stability, search, deploy)
    write_text(outputs["report"], report)
    manifest = build_manifest(config_path, config, outputs, input_audit)
    write_json(outputs["manifest"], manifest)
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(Path(args.config), mode=args.mode, check_inputs_only=args.check_inputs_only)


if __name__ == "__main__":
    main()

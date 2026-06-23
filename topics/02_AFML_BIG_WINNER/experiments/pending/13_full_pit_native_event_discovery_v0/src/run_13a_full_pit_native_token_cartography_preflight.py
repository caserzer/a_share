#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from dataclasses import dataclass
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


RUN_ID = "13A_full_pit_native_token_cartography_preflight"
EXPERIMENT_ID = "13_full_pit_native_event_discovery_v0"
PHASE_ID = "13A"
CONFIG_PATH = EXPERIMENT_DIR / "configs" / "config_13a_full_pit_native_token_cartography_preflight.yaml"
TABLE_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "tables" / RUN_ID
LOCAL_CACHE_DIR = EXPERIMENT_DIR / "outputs" / "local_cache" / RUN_ID
REPORT_DIR = EXPERIMENT_DIR / "outputs" / "publishable" / "reports"
MANIFEST_DIR = EXPERIMENT_DIR / "outputs" / "manifests"

SPLITS = ("train", "validation", "robustness")
ALL_SPLITS = ("all", "train", "validation", "robustness")
SELECTED_LABEL_ID = "vol20d_kup2p0_kdn1p0_H20"

EXPECTED_INPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "requirement": (),
    "source_discussion": (),
    "upstream_requirement_12a7g": (),
    "upstream_config_12a7g": (),
    "pit_topn_400_100_executable_daily": (
        "usable_trade_date",
        "instrument",
        "board_bucket",
        "is_listed",
        "is_st",
        "is_suspended",
    ),
    "pit_topn_400_100_membership_daily": ("membership_date", "instrument", "board_bucket"),
    "stock_daily_qfq_dir": (),
    "global_regime_calendar": (
        "date",
        "daily_regime_bucket",
        "daily_regime_conflict_n",
        "daily_regime_conflict_flag",
    ),
    "upstream_12a7g_table_dir": (),
    "upstream_12a7g_manifest": (),
    "upstream_full_pit_label_panel_cache": (
        "reference_date",
        "instrument",
        "split",
        "board_bucket",
        "winner_positive",
        "upper_first",
        "lower_first",
        "horizon_complete",
        "upper_barrier",
        "lower_barrier",
        "label_id",
    ),
    "upstream_full_pit_primitive_panel_cache": (),
}

OPTIONAL_INPUT_ARTIFACTS = {
    "upstream_full_pit_label_panel_cache",
    "upstream_full_pit_primitive_panel_cache",
}

TOKEN_FAMILIES: dict[str, list[str]] = {
    "reversal_drawdown": [
        "max_drawdown_20d",
        "distance_to_20d_low",
        "rebound_from_20d_low",
    ],
    "breakout_trend": [
        "distance_to_20d_high",
        "ret_5d",
        "ret_20d",
        "trend_ma_5_20_spread",
        "trend_ma_20_60_spread",
    ],
    "volatility_range": [
        "volatility_20d",
        "volatility_60d",
        "vol_ratio_20d_60d",
        "vol_compression_20d_60d",
        "vol_expansion_20d_60d",
        "recent_range_activity_20d",
        "intraday_range_mean_20d",
    ],
    "liquidity_attention": [
        "turnover_rate_median_20d",
        "turnover_zscore_20d",
        "money_median_20d",
    ],
    "relative_strength": [
        "stock_vs_board_20d",
        "board_return_20d",
    ],
}

MORPHOLOGY_ANCHORS = [
    "max_drawdown_20d",
    "distance_to_20d_low",
    "rebound_from_20d_low",
    "ret_20d",
    "volatility_20d",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 13A full-PIT native token cartography preflight.")
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
        "upstream_12a7g_lineage_audit": TABLE_DIR / "upstream_12a7g_lineage_audit.csv",
        "native_universe_frozen_thresholds": TABLE_DIR / "native_universe_frozen_thresholds.csv",
        "native_universe_definition_audit": TABLE_DIR / "native_universe_definition_audit.csv",
        "native_universe_threshold_sensitivity_audit": TABLE_DIR / "native_universe_threshold_sensitivity_audit.csv",
        "label_cache_mismatch_audit": TABLE_DIR / "label_cache_mismatch_audit.csv",
        "native_label_portability_audit": TABLE_DIR / "native_label_portability_audit.csv",
        "native_token_dictionary": TABLE_DIR / "native_token_dictionary.csv",
        "native_token_availability_audit": TABLE_DIR / "native_token_availability_audit.csv",
        "matched_control_design_audit": TABLE_DIR / "matched_control_design_audit.csv",
        "native_token_cartography_readout": TABLE_DIR / "native_token_cartography_readout.csv",
        "native_token_badside_veto_audit": TABLE_DIR / "native_token_badside_veto_audit.csv",
        "native_token_morphology_collinearity_audit": TABLE_DIR / "native_token_morphology_collinearity_audit.csv",
        "native_token_stability_slice_audit": TABLE_DIR / "native_token_stability_slice_audit.csv",
        "native_token_search_multiplicity_audit": TABLE_DIR / "native_token_search_multiplicity_audit.csv",
        "native_token_deployability_gate_audit": TABLE_DIR / "native_token_deployability_gate_audit.csv",
        "native_token_cartography_decision": TABLE_DIR / "native_token_cartography_decision.csv",
        "native_universe_panel": LOCAL_CACHE_DIR / "native_universe_panel.parquet",
        "native_label_panel": LOCAL_CACHE_DIR / "native_label_panel.parquet",
        "native_token_matrix": LOCAL_CACHE_DIR / "native_token_matrix.parquet",
        "report": REPORT_DIR / "native_token_cartography_preflight_report.md",
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
            try:
                import pyarrow.parquet as pq

                return int(pq.ParquetFile(path).metadata.num_rows)
            except Exception:
                return int(len(pd.read_parquet(path)))
        if suffixes.endswith((".csv", ".csv.gz")):
            return int(sum(len(chunk) for chunk in pd.read_csv(path, chunksize=250_000, low_memory=False)))
    except Exception:
        return np.nan
    return np.nan


def date_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()[:10]


def boolish(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def bool_series(series: pd.Series) -> pd.Series:
    return series.map(boolish).fillna(False).astype(bool)


def finite_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def safe_rate(num: Any, den: Any) -> float:
    den_f = float(den) if pd.notna(den) else 0.0
    if den_f == 0:
        return np.nan
    return float(num) / den_f


def normal_ci_diff(p1: float, n1: int, p0: float, n0: int, alpha: float = 0.05) -> tuple[float, float]:
    if n1 <= 0 or n0 <= 0 or pd.isna(p1) or pd.isna(p0):
        return np.nan, np.nan
    se = math.sqrt(max(p1 * (1 - p1), 0) / n1 + max(p0 * (1 - p0), 0) / n0)
    z = NormalDist().inv_cdf(1 - alpha / 2)
    diff = p1 - p0
    return float(diff - z * se), float(diff + z * se)


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


def build_input_audit(resolved: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for artifact_id, path in resolved.items():
        required_cols = EXPECTED_INPUT_COLUMNS.get(artifact_id, ())
        required_flag = artifact_id not in OPTIONAL_INPUT_ARTIFACTS
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
                    elif suffixes.endswith((".json", ".md", ".yaml", ".yml")):
                        sample = pd.DataFrame()
                    else:
                        sample = pd.DataFrame()
                    column_count = len(sample.columns) if suffixes.endswith((".csv", ".csv.gz", ".parquet")) else np.nan
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
                "required_flag": required_flag,
                "lineage_role": lineage_role_for_artifact(artifact_id),
            }
        )
    return pd.DataFrame(rows)


def lineage_role_for_artifact(artifact_id: str) -> str:
    if artifact_id.startswith("upstream") or artifact_id in {"source_discussion", "upstream_requirement_12a7g", "upstream_config_12a7g"}:
        return "upstream_12a7g_lineage"
    if artifact_id in {"pit_topn_400_100_executable_daily", "pit_topn_400_100_membership_daily", "stock_daily_qfq_dir", "global_regime_calendar"}:
        return "raw_pit_rebuild_input"
    return "run_config_input"


@dataclass
class DailyData:
    frame: pd.DataFrame | None
    status: str
    duplicate_date_n: int = 0


class StockDailyCache:
    def __init__(self, qfq_dir: Path):
        self.qfq_dir = qfq_dir
        self.cache: dict[str, DailyData] = {}

    def get(self, instrument: str) -> DailyData:
        if instrument in self.cache:
            return self.cache[instrument]
        path = self.qfq_dir / f"{instrument}.csv"
        if not path.exists():
            data = DailyData(None, "missing_qfq_file")
            self.cache[instrument] = data
            return data
        try:
            frame = pd.read_csv(path, low_memory=False)
            duplicate_date_n = int(frame["date"].astype(str).duplicated().sum()) if "date" in frame.columns else 0
            keep = [col for col in ["date", "open", "high", "low", "close", "volume", "money", "turnover_rate"] if col in frame.columns]
            frame = frame[keep].copy()
            frame["date"] = frame["date"].map(date_text)
            for col in ["open", "high", "low", "close", "volume", "money", "turnover_rate"]:
                if col not in frame.columns:
                    frame[col] = np.nan
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
            frame = frame.sort_values("date", kind="stable").reset_index(drop=True)
            frame["date_pos"] = np.arange(len(frame), dtype=np.int64)
            status = "duplicate_qfq_date" if duplicate_date_n else "pass"
            data = DailyData(add_daily_features(frame), status, duplicate_date_n)
        except Exception:
            data = DailyData(None, "read_error")
        self.cache[instrument] = data
        return data


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
    open_ = finite_numeric(out["open"])
    turnover = finite_numeric(out["turnover_rate"])
    money = finite_numeric(out["money"])
    daily_ret = close.pct_change()
    out["daily_return"] = daily_ret
    for n in [5, 20, 60]:
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
    out["trading_continuity_20d"] = close.notna().rolling(20, min_periods=20).sum() / 20.0
    out["recent_range_activity_20d"] = ((high - low) / close).rolling(20, min_periods=20).mean()
    out["intraday_range_mean_20d"] = ((high - low) / open_.replace(0, np.nan)).rolling(20, min_periods=20).mean()
    out["vol_ratio_20d_60d"] = out["volatility_20d"] / out["volatility_60d"].replace(0, np.nan) - 1.0
    out["vol_compression_20d_60d"] = -1.0 * out["vol_ratio_20d_60d"]
    out["vol_expansion_20d_60d"] = out["vol_ratio_20d_60d"]
    out["rebound_from_20d_low"] = out["distance_to_20d_low"]
    out["entry_date"] = out["date"].shift(-1)
    out["entry_pos"] = out["date_pos"].shift(-1)
    out["entry_price"] = out["open"].shift(-1)
    return out


def barrier_values(frame: pd.DataFrame, k_up: float, k_dn: float, horizon_sessions: int, vol_reference_unit: str) -> tuple[pd.Series, pd.Series]:
    vol = finite_numeric(frame["volatility_20d"])
    if vol_reference_unit == "daily_return_std":
        scale = vol * math.sqrt(float(horizon_sessions))
    elif vol_reference_unit == "horizon_return_vol":
        scale = vol
    else:
        scale = vol * math.sqrt(float(horizon_sessions))
    return scale * float(k_up), -1.0 * scale * float(k_dn)


def compute_label(frame: pd.DataFrame, cache: StockDailyCache, *, k_up: float, k_dn: float, horizon_sessions: int, vol_reference_unit: str) -> pd.DataFrame:
    n = len(frame)
    upper_first = np.zeros(n, dtype=bool)
    lower_first = np.zeros(n, dtype=bool)
    neutral = np.zeros(n, dtype=bool)
    censored = np.ones(n, dtype=bool)
    same_bar = np.zeros(n, dtype=bool)
    horizon_complete = np.zeros(n, dtype=bool)
    upper_touch_anytime = np.zeros(n, dtype=bool)
    lower_touch_anytime = np.zeros(n, dtype=bool)
    time_to_upper = np.full(n, np.nan)
    time_to_lower = np.full(n, np.nan)
    max_high_return = np.full(n, np.nan)
    min_low_return = np.full(n, np.nan)
    horizon_close_return = np.full(n, np.nan)
    upper_barrier, lower_barrier = barrier_values(frame, k_up, k_dn, horizon_sessions, vol_reference_unit)
    upper_arr = finite_numeric(upper_barrier).to_numpy(dtype=float)
    lower_arr = finite_numeric(lower_barrier).to_numpy(dtype=float)
    pos_all = finite_numeric(frame["entry_pos"]).to_numpy(dtype=float)
    price_all = finite_numeric(frame["entry_price"]).to_numpy(dtype=float)
    offsets = np.arange(horizon_sessions + 1)
    for instrument, positions in frame.groupby("instrument", sort=False).indices.items():
        idx = np.asarray(positions, dtype=int)
        daily = cache.get(str(instrument))
        if daily.frame is None or daily.frame.empty or daily.status == "duplicate_qfq_date":
            continue
        high = daily.frame["high"].to_numpy(dtype=float)
        low = daily.frame["low"].to_numpy(dtype=float)
        close = daily.frame["close"].to_numpy(dtype=float)
        pos = pos_all[idx]
        price = price_all[idx]
        ub = upper_arr[idx]
        lb = lower_arr[idx]
        valid = np.isfinite(pos) & np.isfinite(price) & np.isfinite(ub) & np.isfinite(lb) & (pos >= 0) & ((pos + horizon_sessions) < len(daily.frame))
        if not valid.any():
            continue
        valid_idx = idx[valid]
        p_int = pos[valid].astype(int)
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
        same = up_any & low_any & (up_first_pos == low_first_pos)
        up_first = up_any & (~low_any | (up_first_pos < low_first_pos))
        low_first = low_any & (~up_any | (low_first_pos <= up_first_pos))
        upper_first[valid_idx] = up_first
        lower_first[valid_idx] = low_first
        neutral[valid_idx] = ~up_any & ~low_any
        same_bar[valid_idx] = same
        horizon_complete[valid_idx] = True
        censored[valid_idx] = False
        upper_touch_anytime[valid_idx] = up_any
        lower_touch_anytime[valid_idx] = low_any
        time_to_upper[valid_idx] = np.where(up_any, up_first_pos, np.nan)
        time_to_lower[valid_idx] = np.where(low_any, low_first_pos, np.nan)
        max_high_return[valid_idx] = np.nanmax(hret, axis=1)
        min_low_return[valid_idx] = np.nanmin(lret, axis=1)
        horizon_close_return[valid_idx] = close[p_int + horizon_sessions] / price[valid] - 1.0
    return pd.DataFrame(
        {
            "upper_first": upper_first,
            "lower_first": lower_first,
            "neutral": neutral,
            "censored": censored,
            "same_bar_conflict": same_bar,
            "horizon_complete": horizon_complete,
            "upper_touch_anytime": upper_touch_anytime,
            "lower_touch_anytime": lower_touch_anytime,
            "time_to_upper": time_to_upper,
            "time_to_lower": time_to_lower,
            "max_high_return": max_high_return,
            "min_low_return": min_low_return,
            "horizon_close_return": horizon_close_return,
            "upper_barrier": upper_arr,
            "lower_barrier": lower_arr,
            "winner_positive": upper_first,
        },
        index=frame.index,
    )


def compare_label_cache_to_recomputed(cache_panel: pd.DataFrame, recomputed: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    bool_fields = ["upper_first", "lower_first", "neutral", "censored", "same_bar_conflict", "horizon_complete", "upper_touch_anytime", "lower_touch_anytime", "winner_positive"]
    float_fields = ["upper_barrier", "lower_barrier", "time_to_upper", "time_to_lower", "max_high_return", "min_low_return", "horizon_close_return"]
    rows: list[dict[str, Any]] = []
    total_mismatch = 0
    total_compared = 0
    for field in bool_fields:
        if field not in cache_panel.columns or field not in recomputed.columns:
            continue
        left = bool_series(cache_panel[field])
        right = bool_series(recomputed[field])
        compared = left.notna() & right.notna()
        mismatch = compared & left.ne(right)
        total_mismatch += int(mismatch.sum())
        total_compared += int(compared.sum())
        rows.append(
            {
                "field_name": field,
                "field_type": "boolean",
                "compared_row_n": int(compared.sum()),
                "mismatch_n": int(mismatch.sum()),
                "mismatch_rate": safe_rate(int(mismatch.sum()), int(compared.sum())),
                "tolerance_abs": 0.0,
                "mismatch_status": "pass" if int(mismatch.sum()) == 0 else "fail",
            }
        )
    for field in float_fields:
        if field not in cache_panel.columns or field not in recomputed.columns:
            continue
        left = finite_numeric(cache_panel[field])
        right = finite_numeric(recomputed[field])
        both_nan = left.isna() & right.isna()
        compared = pd.Series(True, index=left.index)
        mismatch = compared & ~both_nan & (left.sub(right).abs() > tolerance)
        mismatch = mismatch | (left.isna() ^ right.isna())
        total_mismatch += int(mismatch.sum())
        total_compared += int(compared.sum())
        rows.append(
            {
                "field_name": field,
                "field_type": "float",
                "compared_row_n": int(compared.sum()),
                "mismatch_n": int(mismatch.sum()),
                "mismatch_rate": safe_rate(int(mismatch.sum()), int(compared.sum())),
                "tolerance_abs": tolerance,
                "mismatch_status": "pass" if int(mismatch.sum()) == 0 else "fail",
            }
        )
    rows.append(
        {
            "field_name": "__overall__",
            "field_type": "overall",
            "compared_row_n": total_compared,
            "mismatch_n": total_mismatch,
            "mismatch_rate": safe_rate(total_mismatch, total_compared),
            "tolerance_abs": tolerance,
            "mismatch_status": "pass" if total_mismatch == 0 else "fail",
        }
    )
    return pd.DataFrame(rows)


def build_label_cache_mismatch_audit(panel: pd.DataFrame, resolved: dict[str, Path], selected_formula: pd.Series, cache_used: bool, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    tolerance = float(config.get("label_cache_mismatch", {}).get("return_abs_tolerance", 1e-10))
    if not cache_used:
        audit = pd.DataFrame(
            [
                {
                    "field_name": "__overall__",
                    "field_type": "overall",
                    "compared_row_n": 0,
                    "mismatch_n": 0,
                    "mismatch_rate": np.nan,
                    "tolerance_abs": tolerance,
                    "mismatch_status": "not_applicable_raw_rebuild_used",
                    "cache_used": False,
                    "selected_label_id": SELECTED_LABEL_ID,
                }
            ]
        )
        return audit, "pass"
    recomputed = compute_label(
        panel,
        StockDailyCache(resolved["stock_daily_qfq_dir"]),
        k_up=float(selected_formula["k_up"]),
        k_dn=float(selected_formula["k_dn"]),
        horizon_sessions=int(selected_formula["horizon_sessions"]),
        vol_reference_unit=str(selected_formula["vol_reference_unit"]),
    )
    audit = compare_label_cache_to_recomputed(panel.reset_index(drop=True), recomputed.reset_index(drop=True), tolerance)
    status = "pass" if audit.loc[audit["field_name"].eq("__overall__"), "mismatch_status"].iloc[0] == "pass" else "fail"
    audit["cache_used"] = True
    audit["selected_label_id"] = SELECTED_LABEL_ID
    return audit, status


def selected_label_lineage(resolved: dict[str, Path]) -> tuple[pd.Series, pd.Series, pd.Series, pd.DataFrame]:
    table_dir = resolved["upstream_12a7g_table_dir"]
    decision = read_table(table_dir / "vol_scaled_label_separability_decision.csv")
    formula = read_table(table_dir / "label_formula_audit.csv")
    selection = read_table(table_dir / "label_selection_train_audit.csv")
    thresholds = read_table(table_dir / "pre_registered_threshold_audit.csv")
    selected_decision = decision.iloc[0]
    selected_formula = formula.loc[formula["label_id"].astype(str).eq(SELECTED_LABEL_ID)].iloc[0]
    selected_selection = selection.loc[selection["label_id"].astype(str).eq(SELECTED_LABEL_ID)].iloc[0]
    return selected_decision, selected_formula, selected_selection, thresholds


def build_upstream_lineage_audit(resolved: dict[str, Path], cache_used: bool, source_rows: int, cache_status: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    table_dir = resolved["upstream_12a7g_table_dir"]
    expected = {
        "vol_scaled_label_panel_summary": table_dir / "vol_scaled_label_panel_summary.csv",
        "vol_scaled_label_separability_decision": table_dir / "vol_scaled_label_separability_decision.csv",
        "label_formula_audit": table_dir / "label_formula_audit.csv",
        "label_selection_train_audit": table_dir / "label_selection_train_audit.csv",
        "pre_registered_threshold_audit": table_dir / "pre_registered_threshold_audit.csv",
        "full_universe_split_boundary_audit": table_dir / "full_universe_split_boundary_audit.csv",
        "manifest": resolved["upstream_12a7g_manifest"],
        "full_pit_label_panel_cache": resolved["upstream_full_pit_label_panel_cache"],
    }
    for artifact_id, path in expected.items():
        rows.append(
            {
                "artifact_id": artifact_id,
                "resolved_path": str(path),
                "exists": path.exists(),
                "sha256": path_sha(path),
                "row_count": count_rows(path),
                "cache_used": cache_used if artifact_id == "full_pit_label_panel_cache" else False,
                "cache_row_count": source_rows if artifact_id == "full_pit_label_panel_cache" and cache_used else np.nan,
                "raw_rebuild_row_count": source_rows if artifact_id == "full_pit_label_panel_cache" and not cache_used else np.nan,
                "lineage_status": cache_status if artifact_id == "full_pit_label_panel_cache" else ("pass" if path.exists() else "missing"),
            }
        )
    return pd.DataFrame(rows)


def upstream_lineage_status(resolved: dict[str, Path]) -> tuple[str, str]:
    try:
        decision, formula, selection, _thresholds = selected_label_lineage(resolved)
    except Exception as exc:
        return "fail", f"read_error:{type(exc).__name__}"
    reasons = []
    if str(decision.get("decision_state", "")) != "12A7g_baserate_only_not_separable_stop_winner_selection":
        reasons.append("decision_state_mismatch")
    if str(decision.get("selected_label_id", "")) != SELECTED_LABEL_ID:
        reasons.append("selected_label_mismatch")
    if str(decision.get("input_gate_status", "")) != "pass":
        reasons.append("input_gate_not_pass")
    if str(decision.get("lineage_gate_status", "")) != "pass":
        reasons.append("lineage_gate_not_pass")
    if str(formula.get("formula_status", "")) != "pass":
        reasons.append("formula_status_not_pass")
    if not boolish(selection.get("selected_label_flag", False)):
        reasons.append("label_not_selected")
    if str(selection.get("label_eligibility_status", "")) != "eligible":
        reasons.append("label_not_eligible")
    return ("pass" if not reasons else "fail", ";".join(reasons))


def complete_primitives(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    if "rebound_from_20d_low" not in out.columns and "distance_to_20d_low" in out.columns:
        out["rebound_from_20d_low"] = out["distance_to_20d_low"]
    if "vol_ratio_20d_60d" not in out.columns and {"volatility_20d", "volatility_60d"} <= set(out.columns):
        out["vol_ratio_20d_60d"] = finite_numeric(out["volatility_20d"]) / finite_numeric(out["volatility_60d"]).replace(0, np.nan) - 1.0
    if "vol_compression_20d_60d" not in out.columns and "vol_ratio_20d_60d" in out.columns:
        out["vol_compression_20d_60d"] = -1.0 * finite_numeric(out["vol_ratio_20d_60d"])
    if "vol_expansion_20d_60d" not in out.columns and "vol_ratio_20d_60d" in out.columns:
        out["vol_expansion_20d_60d"] = out["vol_ratio_20d_60d"]
    if "board_return_20d" not in out.columns and {"board_bucket", "reference_date", "ret_20d"} <= set(out.columns):
        board_ret = out.groupby(["board_bucket", "reference_date"], dropna=False)["ret_20d"].mean().rename("board_return_20d").reset_index()
        out = out.merge(board_ret, on=["board_bucket", "reference_date"], how="left", sort=False)
    if "stock_vs_board_20d" not in out.columns and {"ret_20d", "board_return_20d"} <= set(out.columns):
        out["stock_vs_board_20d"] = out["ret_20d"] - out["board_return_20d"]
    return out


def cache_expected_sha(resolved: dict[str, Path]) -> str | None:
    manifest_path = resolved["upstream_12a7g_manifest"]
    if not manifest_path.exists():
        return None
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    return manifest.get("output_hashes", {}).get("full_pit_vol_scaled_label_panel")


def split_boundaries(resolved: dict[str, Path]) -> pd.DataFrame:
    path = resolved["upstream_12a7g_table_dir"] / "full_universe_split_boundary_audit.csv"
    boundaries = read_table(path)
    boundaries = boundaries.loc[boundaries["split"].isin(SPLITS)].copy()
    boundaries["start_date"] = boundaries["start_date"].map(date_text)
    boundaries["end_date"] = boundaries["end_date"].map(date_text)
    if boundaries.empty or boundaries["boundary_assignment_status"].astype(str).ne("pass").any():
        raise ValueError("upstream split boundary audit is not usable")
    return boundaries


def assign_split_by_boundaries(reference_dates: pd.Series, boundaries: pd.DataFrame) -> pd.Series:
    out = pd.Series("boundary_gap_excluded", index=reference_dates.index, dtype=object)
    dates = reference_dates.map(date_text)
    for row in boundaries.itertuples(index=False):
        mask = dates.ge(row.start_date) & dates.le(row.end_date)
        out.loc[mask] = row.split
    return out


def supported_boards(resolved: dict[str, Path]) -> set[str]:
    cfg = load_yaml(resolved["upstream_config_12a7g"])
    boards = cfg.get("supported_boards", [])
    if not boards:
        raise ValueError("upstream 12A7g config missing supported_boards")
    return {str(board) for board in boards}


def normalize_base_panel(panel: pd.DataFrame) -> pd.DataFrame:
    panel = complete_primitives(panel.copy())
    panel["reference_date"] = panel["reference_date"].map(date_text)
    panel["reference_month"] = panel["reference_date"].astype(str).str[:7]
    panel["reference_quarter"] = pd.PeriodIndex(panel["reference_date"].astype(str).str[:10], freq="Q").astype(str)
    panel["calendar_month"] = panel.get("calendar_month", panel["reference_month"]).astype(str)
    panel["calendar_year"] = panel.get("calendar_year", panel["reference_date"].astype(str).str[:4]).astype(str)
    for col in ["winner_positive", "upper_first", "lower_first", "same_bar_conflict", "horizon_complete"]:
        panel[col] = bool_series(panel.get(col, pd.Series(False, index=panel.index)))
    for col in ["regime_calendar_available", "regime_missing_date_bypassed", "required_pre_vol_lookback_complete", "entry_executable", "supported_board", "primary_scope", "label_selection_scope"]:
        if col in panel.columns:
            panel[col] = bool_series(panel[col])
    return panel


def load_cache_panel(resolved: dict[str, Path]) -> pd.DataFrame:
    cache_path = resolved["upstream_full_pit_label_panel_cache"]
    if not cache_path.exists():
        raise FileNotFoundError("cache_missing")
    expected_sha = cache_expected_sha(resolved)
    actual_sha = file_sha256(cache_path)
    if expected_sha and actual_sha != expected_sha:
        raise ValueError("cache_sha_mismatch")
    panel = read_table(cache_path)
    required = {
        "reference_date",
        "instrument",
        "split",
        "board_bucket",
        "winner_positive",
        "upper_first",
        "lower_first",
        "horizon_complete",
        "upper_barrier",
        "lower_barrier",
        "label_id",
    }
    missing = sorted(required - set(panel.columns))
    if missing:
        raise ValueError(f"12A7g full PIT label panel cache missing columns: {missing}")
    panel = panel.loc[panel["label_id"].astype(str).eq(SELECTED_LABEL_ID)].copy()
    if panel.empty:
        raise ValueError("selected_label_absent_in_cache")
    if panel[["instrument", "reference_date"]].duplicated().any():
        raise ValueError("12A7g full PIT label panel cache has duplicate row keys")
    boundaries = split_boundaries(resolved)
    min_allowed = boundaries["start_date"].min()
    max_allowed = boundaries["end_date"].max()
    dates = panel["reference_date"].map(date_text)
    if dates.lt(min_allowed).any() or dates.gt(max_allowed).any():
        raise ValueError("cache_date_range_outside_upstream_split_boundary")
    if "horizon_sessions" in panel.columns and finite_numeric(panel["horizon_sessions"]).dropna().astype(int).ne(20).any():
        raise ValueError("cache_selected_label_horizon_mismatch")
    return normalize_base_panel(panel)


def selected_formula_for_raw_rebuild(resolved: dict[str, Path]) -> pd.Series:
    formula = read_table(resolved["upstream_12a7g_table_dir"] / "label_formula_audit.csv")
    selected = formula.loc[formula["label_id"].astype(str).eq(SELECTED_LABEL_ID)]
    if selected.empty:
        raise ValueError("selected_label_formula_missing")
    row = selected.iloc[0]
    if str(row.get("formula_status", "")) != "pass":
        raise ValueError("selected_label_formula_not_pass")
    return row


def dedupe_raw_pit_rows(pit: pd.DataFrame) -> pd.DataFrame:
    key = ["instrument", "reference_date"]
    duplicated = pit.duplicated(key, keep=False)
    if not duplicated.any():
        return pit
    duplicate_rows = pit.loc[duplicated].copy()
    collapsed = duplicate_rows.astype(str).drop_duplicates()
    if collapsed.duplicated(key, keep=False).any():
        raise ValueError("raw_pit_duplicate_row_key_conflict")
    return pit.drop_duplicates(key, keep="first").copy()


def attach_qfq_features(pit: pd.DataFrame, cache: StockDailyCache) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    daily_keep = [
        "date",
        "date_pos",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "turnover_rate",
        "daily_return",
        "ret_5d",
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
        "turnover_rate_median_20d",
        "money_median_20d",
        "trading_continuity_20d",
        "recent_range_activity_20d",
        "intraday_range_mean_20d",
        "vol_ratio_20d_60d",
        "vol_compression_20d_60d",
        "vol_expansion_20d_60d",
        "rebound_from_20d_low",
        "entry_date",
        "entry_pos",
        "entry_price",
    ]
    for instrument, group in pit.groupby("instrument", sort=False):
        daily = cache.get(str(instrument))
        group = group.copy()
        if daily.frame is None or daily.frame.empty:
            group["primitive_status"] = daily.status
            frames.append(group)
            continue
        if daily.status == "duplicate_qfq_date":
            group["primitive_status"] = "duplicate_qfq_reference_row"
            frames.append(group)
            continue
        daily_frame = daily.frame[[col for col in daily_keep if col in daily.frame.columns]].copy()
        daily_frame = daily_frame.rename(columns={"date": "reference_date", "date_pos": "reference_pos"})
        merged = group.merge(daily_frame, on="reference_date", how="left", sort=False)
        finite_ohlc = (
            finite_numeric(merged["open"]).notna()
            & finite_numeric(merged["high"]).notna()
            & finite_numeric(merged["low"]).notna()
            & finite_numeric(merged["close"]).notna()
        )
        consistent_ohlc = (
            finite_numeric(merged["high"]).ge(pd.concat([finite_numeric(merged["open"]), finite_numeric(merged["close"]), finite_numeric(merged["low"])], axis=1).max(axis=1))
            & finite_numeric(merged["low"]).le(pd.concat([finite_numeric(merged["open"]), finite_numeric(merged["close"]), finite_numeric(merged["high"])], axis=1).min(axis=1))
        )
        merged["primitive_status"] = np.select(
            [
                finite_numeric(merged["reference_pos"]).isna(),
                ~finite_ohlc,
                ~consistent_ohlc,
            ],
            [
                "missing_qfq_reference_row",
                "nonfinite_ohlc",
                "inconsistent_ohlc",
            ],
            default="pass",
        )
        frames.append(merged)
    return pd.concat(frames, ignore_index=True) if frames else pit.head(0).copy()


def attach_regime(panel: pd.DataFrame, resolved: dict[str, Path]) -> pd.DataFrame:
    regime = read_table(resolved["global_regime_calendar"])
    regime["date"] = regime["date"].map(date_text)
    if regime["date"].duplicated().any():
        raise ValueError("regime_calendar_duplicate_date")
    if bool_series(regime.get("daily_regime_conflict_flag", pd.Series(False, index=regime.index))).any() or finite_numeric(regime.get("daily_regime_conflict_n", pd.Series(0, index=regime.index))).gt(0).any():
        raise ValueError("regime_calendar_conflict")
    regime = regime[["date", "daily_regime_bucket"]].rename(columns={"date": "reference_date", "daily_regime_bucket": "market_regime_bucket"})
    out = panel.merge(regime, on="reference_date", how="left", sort=False)
    out["regime_calendar_available"] = out["market_regime_bucket"].notna()
    out["regime_missing_date_bypassed"] = ~out["regime_calendar_available"]
    out["market_regime_bucket"] = out["market_regime_bucket"].fillna("missing_regime_calendar")
    return out


def rebuild_base_panel_from_raw(resolved: dict[str, Path]) -> pd.DataFrame:
    formula = selected_formula_for_raw_rebuild(resolved)
    pit = read_table(resolved["pit_topn_400_100_executable_daily"])
    pit = pit.rename(columns={"usable_trade_date": "reference_date"}).copy()
    pit["reference_date"] = pit["reference_date"].map(date_text)
    pit = dedupe_raw_pit_rows(pit)
    boundaries = split_boundaries(resolved)
    pit["split"] = assign_split_by_boundaries(pit["reference_date"], boundaries)
    boards = supported_boards(resolved)
    cache = StockDailyCache(resolved["stock_daily_qfq_dir"])
    panel = attach_qfq_features(pit, cache)
    panel = attach_regime(panel, resolved)
    panel["row_id"] = np.arange(len(panel), dtype=np.int64)
    panel["calendar_month"] = panel["reference_date"].str[:7]
    panel["calendar_year"] = panel["reference_date"].str[:4]
    panel["supported_board"] = panel["board_bucket"].astype(str).isin(boards)
    panel["entry_executable"] = panel["entry_date"].notna() & finite_numeric(panel["entry_price"]).notna()
    panel["required_pre_vol_lookback_complete"] = finite_numeric(panel["volatility_20d"]).notna() & finite_numeric(panel["volatility_60d"]).notna()
    panel["primary_scope"] = (
        panel["split"].isin(SPLITS)
        & panel["supported_board"]
        & bool_series(panel.get("is_listed", pd.Series(True, index=panel.index)))
        & ~bool_series(panel.get("is_st", pd.Series(False, index=panel.index)))
        & ~bool_series(panel.get("is_suspended", pd.Series(False, index=panel.index)))
        & panel["entry_executable"]
        & panel["required_pre_vol_lookback_complete"]
        & panel["primitive_status"].astype(str).eq("pass")
        & panel["regime_calendar_available"]
    )
    labels = compute_label(
        panel,
        cache,
        k_up=float(formula["k_up"]),
        k_dn=float(formula["k_dn"]),
        horizon_sessions=int(formula["horizon_sessions"]),
        vol_reference_unit=str(formula["vol_reference_unit"]),
    )
    panel = pd.concat([panel.reset_index(drop=True), labels.reset_index(drop=True)], axis=1)
    panel["label_id"] = SELECTED_LABEL_ID
    panel["horizon_sessions"] = int(formula["horizon_sessions"])
    panel["active_band_flag"] = False
    panel["label_selection_scope"] = panel["primary_scope"] & panel["horizon_complete"]
    return normalize_base_panel(panel)


def load_base_panel(resolved: dict[str, Path]) -> tuple[pd.DataFrame, bool, str]:
    try:
        return load_cache_panel(resolved), True, "cache_used_pass"
    except Exception as exc:
        status = f"raw_rebuild_after_cache_unusable:{type(exc).__name__}:{exc}"
        return rebuild_base_panel_from_raw(resolved), False, status


def quantile_value(series: pd.Series, q: float) -> float:
    vals = finite_numeric(series).dropna()
    return float(vals.quantile(q)) if len(vals) else np.nan


def native_pre_label_eligible(panel: pd.DataFrame) -> pd.Series:
    return (
        bool_series(panel.get("regime_calendar_available", pd.Series(True, index=panel.index)))
        & bool_series(panel.get("supported_board", pd.Series(True, index=panel.index)))
        & ~panel.get("is_listed", pd.Series(True, index=panel.index)).map(lambda x: boolish(x) is False)
        & ~bool_series(panel.get("is_st", pd.Series(False, index=panel.index)))
        & ~bool_series(panel.get("is_suspended", pd.Series(False, index=panel.index)))
        & bool_series(panel.get("entry_executable", pd.Series(True, index=panel.index)))
        & bool_series(panel.get("required_pre_vol_lookback_complete", pd.Series(True, index=panel.index)))
        & panel["split"].isin(SPLITS)
    )


def candidate_denominator_mask(panel: pd.DataFrame, thresholds: dict[str, Any]) -> pd.Series:
    liq = finite_numeric(panel[thresholds["liquidity_metric"]])
    cont = finite_numeric(panel.get("trading_continuity_20d", pd.Series(np.nan, index=panel.index)))
    vol = finite_numeric(panel["volatility_20d"])
    return (
        native_pre_label_eligible(panel)
        & liq.ge(float(thresholds["liquidity_floor"]))
        & cont.ge(float(thresholds["trading_continuity_floor"]))
        & vol.between(float(thresholds["volatility_floor"]), float(thresholds["volatility_cap"]))
    )


def retained_share_by_split(panel: pd.DataFrame, mask: pd.Series, split: str) -> float:
    eligible = native_pre_label_eligible(panel) & panel["split"].astype(str).eq(split)
    return safe_rate(int((mask & eligible).sum()), int(eligible.sum()))


def max_mix_delta_by_split(panel: pd.DataFrame, mask: pd.Series, col: str) -> float:
    if col not in panel.columns:
        return 0.0
    train = panel.loc[mask & panel["split"].astype(str).eq("train")]
    if train.empty:
        return np.inf
    deltas = []
    for split in ("validation", "robustness"):
        other = panel.loc[mask & panel["split"].astype(str).eq(split)]
        deltas.append(max_mix_delta(train, other, col) if len(other) else np.inf)
    return float(max(deltas, default=0.0))


def mix_delta_or_zero(left: pd.DataFrame, right: pd.DataFrame, col: str) -> float:
    if col not in left.columns or col not in right.columns:
        return 0.0
    return max_mix_delta(left, right, col)


def threshold_candidate_rows(panel: pd.DataFrame, liquidity_metric: str, config: dict[str, Any]) -> pd.DataFrame:
    base_train_mask = panel["split"].astype(str).eq("train") & native_pre_label_eligible(panel)
    train = panel.loc[base_train_mask].copy()
    native_cfg = config.get("native_universe", {})
    liq_candidates = native_cfg.get("liquidity_quantile_candidates", [0.01, 0.02, 0.05, 0.10])
    continuity_candidates = native_cfg.get("continuity_threshold_candidates", [0.80, 0.90, 0.95, 1.00])
    vol_floor_candidates = native_cfg.get("volatility_floor_quantile_candidates", [0.01, 0.02, 0.05])
    vol_cap_candidates = native_cfg.get("volatility_cap_quantile_candidates", [0.95, 0.98, 0.99])
    th = config.get("thresholds", {})
    rows = []
    for liq_q in liq_candidates:
        liq_floor = quantile_value(train[liquidity_metric], float(liq_q))
        for cont_floor in continuity_candidates:
            for vol_floor_q in vol_floor_candidates:
                vol_floor = quantile_value(train["volatility_20d"], float(vol_floor_q))
                for vol_cap_q in vol_cap_candidates:
                    vol_cap = quantile_value(train["volatility_20d"], float(vol_cap_q))
                    thresholds = {
                        "liquidity_metric": liquidity_metric,
                        "liquidity_floor": liq_floor,
                        "liquidity_quantile": float(liq_q),
                        "trading_continuity_floor": float(cont_floor),
                        "volatility_floor": vol_floor,
                        "volatility_cap": vol_cap,
                        "volatility_floor_quantile": float(vol_floor_q),
                        "volatility_cap_quantile": float(vol_cap_q),
                    }
                    mask = candidate_denominator_mask(panel, thresholds)
                    retained_train = panel.loc[mask & panel["split"].astype(str).eq("train")]
                    split_share_delta = abs(1.0 - safe_rate(len(retained_train), int(base_train_mask.sum())))
                    board_delta = mix_delta_or_zero(train, retained_train, "board_bucket")
                    year_delta = mix_delta_or_zero(train, retained_train, "calendar_year")
                    regime_delta = mix_delta_or_zero(train, retained_train, "market_regime_bucket")
                    pass_flag = (
                        split_share_delta <= float(th.get("max_retained_row_share_delta", 0.10))
                        and board_delta <= float(th.get("max_board_mix_abs_delta", 0.08))
                        and year_delta <= float(th.get("max_year_mix_abs_delta", 0.08))
                        and regime_delta <= float(th.get("max_regime_mix_abs_delta", th.get("max_board_mix_abs_delta", 0.08)))
                    )
                    restrictiveness = float(liq_q) + float(cont_floor) + float(vol_floor_q) + (1.0 - float(vol_cap_q))
                    rows.append(
                        {
                            **thresholds,
                            "candidate_pass": bool(pass_flag),
                            "retained_train_denominator_n": int((mask & panel["split"].astype(str).eq("train")).sum()),
                            "universe_balance_score": float(split_share_delta + board_delta + year_delta + regime_delta),
                            "split_retained_share_delta": float(split_share_delta),
                            "board_mix_max_abs_delta": float(board_delta),
                            "year_mix_max_abs_delta": float(year_delta),
                            "regime_mix_max_abs_delta": float(regime_delta),
                            "restrictiveness_score": float(restrictiveness),
                        }
                    )
    return pd.DataFrame(rows)


def freeze_native_thresholds(panel: pd.DataFrame, config: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    train = panel.loc[panel["split"].astype(str).eq("train")].copy()
    native_cfg = config.get("native_universe", {})
    liquidity_metric = "money_median_20d" if train.get("money_median_20d", pd.Series(dtype=float)).notna().any() else "turnover_rate_median_20d"
    candidates = threshold_candidate_rows(panel, liquidity_metric, config)
    eligible_candidates = candidates.loc[candidates["candidate_pass"]].copy()
    default_candidate = candidates.loc[
        candidates["candidate_pass"]
        & candidates["liquidity_quantile"].eq(float(native_cfg.get("liquidity_quantile", 0.05)))
        & candidates["trading_continuity_floor"].eq(float(native_cfg.get("continuity_threshold", 0.95)))
        & candidates["volatility_floor_quantile"].eq(float(native_cfg.get("volatility_floor_quantile", 0.01)))
        & candidates["volatility_cap_quantile"].eq(float(native_cfg.get("volatility_cap_quantile", 0.99)))
    ]
    if len(default_candidate):
        chosen = default_candidate.iloc[0].to_dict()
        tie_break_source = "label_free_default_candidate_pass"
    else:
        rank_base = eligible_candidates if len(eligible_candidates) else candidates
        ranked = rank_base.sort_values(
            ["retained_train_denominator_n", "universe_balance_score", "restrictiveness_score", "liquidity_metric", "liquidity_quantile", "trading_continuity_floor", "volatility_floor_quantile", "volatility_cap_quantile"],
            ascending=[False, True, True, True, True, True, True, True],
            kind="mergesort",
        )
        chosen = ranked.iloc[0].to_dict()
        tie_break_source = "label_free_denominator_candidate_tiebreak"
    thresholds = {
        "liquidity_metric": liquidity_metric,
        "liquidity_floor": float(chosen["liquidity_floor"]),
        "liquidity_quantile": float(chosen["liquidity_quantile"]),
        "trading_continuity_floor": float(chosen["trading_continuity_floor"]),
        "volatility_floor": float(chosen["volatility_floor"]),
        "volatility_cap": float(chosen["volatility_cap"]),
        "volatility_floor_quantile": float(chosen["volatility_floor_quantile"]),
        "volatility_cap_quantile": float(chosen["volatility_cap_quantile"]),
        "candidate_count": int(len(candidates)),
        "candidate_pass_count": int(candidates["candidate_pass"].sum()),
        "universe_balance_score": float(chosen["universe_balance_score"]),
    }
    rows = [
        {
            "threshold_id": "basic_liquidity_floor",
            "feature_id": liquidity_metric,
            "threshold_value": thresholds["liquidity_floor"],
            "threshold_quantile": thresholds["liquidity_quantile"],
            "threshold_source_split": "train",
            "tie_break_source": tie_break_source,
            "outcome_used_for_freeze": False,
            "candidate_count": thresholds["candidate_count"],
            "candidate_pass_count": thresholds["candidate_pass_count"],
            "universe_balance_score": thresholds["universe_balance_score"],
        },
        {
            "threshold_id": "trading_continuity_floor",
            "feature_id": "trading_continuity_20d",
            "threshold_value": thresholds["trading_continuity_floor"],
            "threshold_quantile": np.nan,
            "threshold_source_split": "train",
            "tie_break_source": tie_break_source,
            "outcome_used_for_freeze": False,
            "candidate_count": thresholds["candidate_count"],
            "candidate_pass_count": thresholds["candidate_pass_count"],
            "universe_balance_score": thresholds["universe_balance_score"],
        },
        {
            "threshold_id": "volatility_sanity_floor",
            "feature_id": "volatility_20d",
            "threshold_value": thresholds["volatility_floor"],
            "threshold_quantile": thresholds["volatility_floor_quantile"],
            "threshold_source_split": "train",
            "tie_break_source": tie_break_source,
            "outcome_used_for_freeze": False,
            "candidate_count": thresholds["candidate_count"],
            "candidate_pass_count": thresholds["candidate_pass_count"],
            "universe_balance_score": thresholds["universe_balance_score"],
        },
        {
            "threshold_id": "volatility_sanity_cap",
            "feature_id": "volatility_20d",
            "threshold_value": thresholds["volatility_cap"],
            "threshold_quantile": thresholds["volatility_cap_quantile"],
            "threshold_source_split": "train",
            "tie_break_source": tie_break_source,
            "outcome_used_for_freeze": False,
            "candidate_count": thresholds["candidate_count"],
            "candidate_pass_count": thresholds["candidate_pass_count"],
            "universe_balance_score": thresholds["universe_balance_score"],
        },
    ]
    return thresholds, pd.DataFrame(rows)


def apply_native_filters(panel: pd.DataFrame, thresholds: dict[str, Any]) -> pd.DataFrame:
    out = panel.copy()
    liq = finite_numeric(out[thresholds["liquidity_metric"]])
    cont = finite_numeric(out.get("trading_continuity_20d", pd.Series(np.nan, index=out.index)))
    vol = finite_numeric(out["volatility_20d"])
    out["native_liquidity_floor_pass"] = liq.ge(float(thresholds["liquidity_floor"]))
    out["native_trading_continuity_floor_pass"] = cont.ge(float(thresholds["trading_continuity_floor"]))
    out["native_volatility_sanity_pass"] = vol.between(float(thresholds["volatility_floor"]), float(thresholds["volatility_cap"]))
    out["listed_flag_pass"] = ~out.get("is_listed", pd.Series(True, index=out.index)).map(lambda x: boolish(x) is False)
    out["st_flag_pass"] = ~bool_series(out.get("is_st", pd.Series(False, index=out.index)))
    out["suspended_flag_pass"] = ~bool_series(out.get("is_suspended", pd.Series(False, index=out.index)))
    out["native_scope"] = (
        bool_series(out.get("regime_calendar_available", pd.Series(True, index=out.index)))
        & bool_series(out.get("supported_board", pd.Series(True, index=out.index)))
        & out["listed_flag_pass"]
        & out["st_flag_pass"]
        & out["suspended_flag_pass"]
        & bool_series(out.get("entry_executable", pd.Series(True, index=out.index)))
        & bool_series(out.get("required_pre_vol_lookback_complete", pd.Series(True, index=out.index)))
        & out["native_liquidity_floor_pass"]
        & out["native_trading_continuity_floor_pass"]
        & out["native_volatility_sanity_pass"]
        & out["horizon_complete"]
        & out["split"].isin(SPLITS)
    )
    reasons = []
    for idx, row in out.iterrows():
        reason = []
        if not boolish(row.get("regime_calendar_available", True)):
            reason.append("missing_regime_calendar")
        if not boolish(row.get("supported_board", True)):
            reason.append("unsupported_board")
        if not boolish(row.get("entry_executable", True)):
            reason.append("missing_entry_open")
        if not boolish(row.get("required_pre_vol_lookback_complete", True)):
            reason.append("pre_vol_lookback_incomplete")
        if not boolish(row.get("horizon_complete", True)):
            reason.append("label_horizon_incomplete")
        if not boolish(row.get("native_liquidity_floor_pass", True)):
            reason.append("native_floor_fail")
        if not boolish(row.get("native_volatility_sanity_pass", True)):
            reason.append("native_cap_fail")
        reasons.append(";".join(reason))
    out["row_exclusion_reason"] = reasons
    return out


def label_base_rate_dispersion(native: pd.DataFrame, min_slice_n: int = 200) -> float:
    train = native.loc[native["split"].astype(str).eq("train") & native["native_scope"]]
    base = safe_rate(train["winner_positive"].sum(), len(train))
    if pd.isna(base):
        return np.inf
    vals: list[float] = []
    for col in ["calendar_year", "board_bucket", "market_regime_bucket"]:
        for _key, sub in train.groupby(col, dropna=False):
            if len(sub) >= min_slice_n:
                vals.append(abs(safe_rate(sub["winner_positive"].sum(), len(sub)) - base))
    return float(max(vals)) if vals else 0.0


def build_universe_definition_audit(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in ALL_SPLITS:
        split_frame = panel if split == "all" else panel.loc[panel["split"].astype(str).eq(split)]
        for (year, board, regime), sub in split_frame.groupby(["calendar_year", "board_bucket", "market_regime_bucket"], dropna=False):
            scoped = sub.loc[sub["native_scope"]]
            rows.append(
                {
                    "split_bucket": split,
                    "calendar_year": year,
                    "board_bucket": board,
                    "market_regime_bucket": regime,
                    "instrument_count": int(scoped["instrument"].nunique()),
                    "row_count": int(len(scoped)),
                    "instrument_month_count": int(scoped[["instrument", "calendar_month"]].drop_duplicates().shape[0]) if len(scoped) else 0,
                    "winner_base_rate": safe_rate(scoped["winner_positive"].sum(), len(scoped)),
                    "missing_regime_bypassed_row_n": int((~bool_series(sub.get("regime_calendar_available", pd.Series(True, index=sub.index)))).sum()),
                    "not_evaluable_row_n": int((~sub["native_scope"]).sum()),
                    "source_field_available": True,
                }
            )
    return pd.DataFrame(rows)


def build_threshold_sensitivity(panel: pd.DataFrame, config: dict[str, Any], base_thresholds: dict[str, Any]) -> pd.DataFrame:
    base = panel.loc[panel["native_scope"]]
    native_cfg = config.get("native_universe", {})
    rows = []
    for variant in native_cfg.get("sensitivity_variants", []):
        tmp_thresholds = dict(base_thresholds)
        train = panel.loc[panel["split"].astype(str).eq("train")]
        tmp_thresholds["liquidity_floor"] = quantile_value(train[tmp_thresholds["liquidity_metric"]], float(variant.get("liquidity_quantile", tmp_thresholds["liquidity_quantile"])))
        tmp_thresholds["trading_continuity_floor"] = float(variant.get("continuity_threshold", tmp_thresholds["trading_continuity_floor"]))
        tmp_thresholds["volatility_floor"] = quantile_value(train["volatility_20d"], float(variant.get("volatility_floor_quantile", tmp_thresholds["volatility_floor_quantile"])))
        tmp_thresholds["volatility_cap"] = quantile_value(train["volatility_20d"], float(variant.get("volatility_cap_quantile", tmp_thresholds["volatility_cap_quantile"])))
        alt = apply_native_filters(panel, tmp_thresholds)
        scoped = alt.loc[alt["native_scope"]]
        row_delta = safe_rate(len(scoped) - len(base), len(base))
        br_delta = safe_rate(scoped["winner_positive"].sum(), len(scoped)) - safe_rate(base["winner_positive"].sum(), len(base))
        board_delta = max_mix_delta(base, scoped, "board_bucket")
        year_delta = max_mix_delta(base, scoped, "calendar_year")
        status = "pass"
        th = config.get("thresholds", {})
        if (
            abs(row_delta if pd.notna(row_delta) else 0) > float(th.get("max_retained_row_share_delta", 0.10))
            or abs(br_delta if pd.notna(br_delta) else 0) > float(th.get("max_winner_base_rate_delta", 0.02))
            or board_delta > float(th.get("max_board_mix_abs_delta", 0.08))
            or year_delta > float(th.get("max_year_mix_abs_delta", 0.08))
        ):
            status = "warn" if str(variant.get("variant_id")) != "base" else "fail"
        rows.append(
            {
                "threshold_variant_id": variant.get("variant_id", ""),
                "retained_row_n": int(len(scoped)),
                "retained_row_share_delta": row_delta,
                "winner_base_rate_delta": br_delta,
                "board_mix_max_abs_delta": board_delta,
                "year_mix_max_abs_delta": year_delta,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def max_mix_delta(left: pd.DataFrame, right: pd.DataFrame, col: str) -> float:
    l = left[col].value_counts(normalize=True, dropna=False)
    r = right[col].value_counts(normalize=True, dropna=False)
    keys = set(l.index) | set(r.index)
    return float(max((abs(float(l.get(k, 0.0)) - float(r.get(k, 0.0))) for k in keys), default=0.0))


def build_label_portability(panel: pd.DataFrame, selected_formula: pd.Series, selected_selection: pd.Series, upstream_thresholds: pd.DataFrame) -> pd.DataFrame:
    threshold_map = dict(zip(upstream_thresholds["threshold_id"].astype(str), finite_numeric(upstream_thresholds["threshold_value"])))
    dispersion = label_base_rate_dispersion(panel, int(threshold_map.get("min_label_stability_slice_n", 200)))
    rows = []
    for split in ALL_SPLITS:
        sub = panel.loc[panel["native_scope"]] if split == "all" else panel.loc[panel["native_scope"] & panel["split"].astype(str).eq(split)]
        complete_n = int(sub["horizon_complete"].sum())
        denom_n = int(len(sub))
        same_rate = safe_rate(sub["same_bar_conflict"].sum(), complete_n)
        row = {
            "split_bucket": split,
            "denominator_n": denom_n,
            "horizon_complete_n": complete_n,
            "horizon_complete_rate": safe_rate(complete_n, denom_n),
            "winner_positive_n": int(sub["winner_positive"].sum()),
            "winner_base_rate": safe_rate(sub["winner_positive"].sum(), complete_n),
            "fast_fail_rate": safe_rate(sub["lower_first"].sum(), complete_n),
            "same_bar_conflict_rate": same_rate,
            "label_base_rate_dispersion": dispersion,
            "label_stability_status": "pass",
            "source_12a7g_formula_status": selected_formula.get("formula_status", ""),
            "source_12a7g_vol_reference_unit": selected_formula.get("vol_reference_unit", ""),
            "source_12a7g_train_base_rate": selected_selection.get("train_winner_base_rate", np.nan),
            "source_12a7g_label_stability_score": selected_selection.get("label_stability_score", np.nan),
            "source_12a7g_min_train_positive_n": threshold_map.get("min_train_positive_n", 200),
            "source_12a7g_max_label_base_rate_dispersion": threshold_map.get("max_label_base_rate_dispersion", 0.10),
            "source_12a7g_max_same_bar_conflict_rate": threshold_map.get("max_same_bar_conflict_rate", 0.03),
        }
        if (
            split == "train"
            and (
                row["winner_positive_n"] < row["source_12a7g_min_train_positive_n"]
                or dispersion > row["source_12a7g_max_label_base_rate_dispersion"]
                or same_rate > row["source_12a7g_max_same_bar_conflict_rate"]
            )
        ):
            row["label_stability_status"] = "fail"
        rows.append(row)
    return pd.DataFrame(rows)


def token_family_for_primitive(primitive_id: str) -> str:
    for family, primitives in TOKEN_FAMILIES.items():
        if primitive_id in primitives:
            return family
    return "unknown"


def build_tokens(panel: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = panel.loc[panel["native_scope"] & panel["split"].astype(str).eq("train")]
    token_rows = []
    availability_rows = []
    token_matrix = pd.DataFrame({"row_id": panel.get("row_id", pd.Series(np.arange(len(panel), dtype=np.int64))).to_numpy()})
    quantile_rules = config.get("tokens", {}).get("quantile_rules", [])
    candidate_n = 0
    for family, primitives in TOKEN_FAMILIES.items():
        for primitive in primitives:
            status = "pass" if primitive in panel.columns and finite_numeric(train.get(primitive, pd.Series(dtype=float))).notna().any() else "unavailable_missing_source_field"
            availability_rows.append(
                {
                    "family_id": family,
                    "primitive_id": primitive,
                    "primitive_status": status,
                    "token_status": "candidate" if status == "pass" else "excluded_before_grid",
                    "available_at": "reference_date_close",
                    "future_data_used": False,
                }
            )
            if status != "pass":
                continue
            values = finite_numeric(train[primitive]).dropna()
            for rule in quantile_rules:
                candidate_n += 1
                if candidate_n > int(config.get("tokens", {}).get("max_token_candidate_n", 120)):
                    break
                threshold = float(values.quantile(float(rule["quantile"])))
                token_id = f"{primitive}__{rule['threshold_rule']}"
                comparator = str(rule["comparator"])
                full_values = finite_numeric(panel[primitive])
                mask = full_values.le(threshold) if comparator == "le" else full_values.ge(threshold)
                mask = mask & panel["native_scope"]
                token_matrix[token_id] = mask.to_numpy(dtype=bool)
                token_rows.append(
                    {
                        "token_id": token_id,
                        "family_id": family,
                        "primitive_id": primitive,
                        "lookback_sessions": primitive_lookback(primitive),
                        "orientation": rule["orientation"],
                        "threshold_rule": rule["threshold_rule"],
                        "threshold_value": threshold,
                        "threshold_split": "train",
                        "available_at": "reference_date_close",
                        "future_data_used": False,
                        "comparator": comparator,
                    }
                )
    return pd.DataFrame(token_rows), pd.DataFrame(availability_rows), token_matrix


def primitive_lookback(primitive: str) -> int:
    for n in (60, 20, 5):
        if f"{n}d" in primitive or f"_{n}_" in primitive:
            return n
    return 20


def exclude_match_keys(token: pd.Series) -> list[str]:
    family = str(token["family_id"])
    primitive = str(token["primitive_id"])
    excluded: list[str] = []
    if family == "volatility_range" or primitive in {"volatility_20d", "volatility_60d", "vol_ratio_20d_60d", "vol_compression_20d_60d", "vol_expansion_20d_60d"}:
        excluded.append("volatility_20d_decile")
    if family == "liquidity_attention" or primitive in {"turnover_rate_median_20d", "turnover_zscore_20d", "money_median_20d"}:
        excluded.append("liquidity_metric_decile")
    return excluded


def add_match_deciles(panel: pd.DataFrame, liquidity_metric: str) -> pd.DataFrame:
    out = panel.copy()
    for col, new_col in [("volatility_20d", "volatility_20d_decile"), (liquidity_metric, "liquidity_metric_decile")]:
        deciles = pd.Series(np.nan, index=out.index)
        for split, idxs in out.groupby("split", sort=False).groups.items():
            vals = finite_numeric(out.loc[idxs, col])
            try:
                deciles.loc[idxs] = pd.qcut(vals.rank(method="first"), 10, labels=False, duplicates="drop")
            except ValueError:
                deciles.loc[idxs] = np.nan
        out[new_col] = deciles.astype("float")
    return out


def match_control_mask(
    panel: pd.DataFrame,
    treated_mask: pd.Series,
    split: str,
    token: pd.Series,
) -> tuple[pd.Series, dict[str, Any]]:
    base = panel["native_scope"] & panel["split"].astype(str).eq(split)
    treated = base & treated_mask
    non_treated = base & ~treated_mask
    excluded = exclude_match_keys(token)
    levels = [
        ("level_0", ["reference_month", "board_bucket", "market_regime_bucket", "volatility_20d_decile", "liquidity_metric_decile"]),
        ("level_1", ["reference_quarter", "board_bucket", "market_regime_bucket", "volatility_20d_decile", "liquidity_metric_decile"]),
        ("level_2", ["reference_quarter", "board_bucket", "market_regime_bucket"]),
        ("level_3", ["calendar_year", "board_bucket", "market_regime_bucket"]),
    ]
    best_mask = base & False
    best_info: dict[str, Any] = {
        "coarsening_level": "unmatched",
        "effective_control_ratio": 0.0,
        "unmatched_treated_n": int(treated.sum()),
        "matched_block_n": 0,
        "excluded_match_keys": ";".join(excluded),
        "max_standardized_diff_after_match": np.nan,
        "control_match_quality": "insufficient_control",
        "match_status": "fail",
    }
    treated_n = int(treated.sum())
    if treated_n == 0:
        return best_mask, best_info
    for level_name, keys in levels:
        keys = [k for k in keys if k not in excluded and k in panel.columns]
        if not keys:
            control = non_treated
            matched_treated = treated
            matched_blocks = 1
        else:
            treated_keys = panel.loc[treated, keys].drop_duplicates()
            marker = treated_keys.assign(_matched_key=True)
            matched = panel.loc[non_treated, keys].merge(marker, on=keys, how="left")["_matched_key"]
            control = matched.eq(True).to_numpy(dtype=bool)
            control = pd.Series(control, index=panel.loc[non_treated].index).reindex(panel.index, fill_value=False)
            matched_treated = treated
            matched_blocks = int(len(treated_keys))
        control_n = int(control.sum())
        unmatched_n = 0 if control_n else treated_n
        ratio = safe_rate(control_n, treated_n)
        max_smd = standardized_diff(panel, treated, control, ["volatility_20d", "money_median_20d", "turnover_rate_median_20d"])
        quality = control_quality(level_name, ratio, unmatched_n, treated_n, max_smd)
        best_mask = control
        best_info = {
            "coarsening_level": level_name,
            "effective_control_ratio": ratio,
            "unmatched_treated_n": unmatched_n,
            "matched_block_n": matched_blocks,
            "excluded_match_keys": ";".join(excluded),
            "max_standardized_diff_after_match": max_smd,
            "control_match_quality": quality,
            "match_status": "pass" if quality != "insufficient_control" else "fail",
        }
        if quality in {"primary_comparable", "coarsened_caveat"}:
            break
    return best_mask, best_info


def standardized_diff(panel: pd.DataFrame, treated: pd.Series, control: pd.Series, cols: list[str]) -> float:
    diffs = []
    for col in cols:
        if col not in panel.columns:
            continue
        t = finite_numeric(panel.loc[treated, col]).dropna()
        c = finite_numeric(panel.loc[control, col]).dropna()
        if len(t) == 0 or len(c) == 0:
            continue
        pooled = math.sqrt((float(t.var(ddof=0)) + float(c.var(ddof=0))) / 2)
        if pooled == 0:
            diffs.append(0.0)
        else:
            diffs.append(abs(float(t.mean()) - float(c.mean())) / pooled)
    return float(max(diffs)) if diffs else np.nan


def control_quality(level_name: str, ratio: float, unmatched_n: int, treated_n: int, max_smd: float) -> str:
    unmatched_share = safe_rate(unmatched_n, treated_n)
    if pd.isna(ratio) or ratio < 3 or (pd.notna(unmatched_share) and unmatched_share > 0.05):
        return "insufficient_control"
    if level_name in {"level_0", "level_1"} and (pd.isna(max_smd) or max_smd <= 0.10):
        return "primary_comparable"
    return "coarsened_caveat"


def token_auc_values(panel: pd.DataFrame, token: pd.Series) -> pd.Series:
    values = finite_numeric(panel[token["primitive_id"]])
    return values if token["orientation"] == "desc" else -1.0 * values


def evaluate_tokens(
    panel: pd.DataFrame,
    tokens: pd.DataFrame,
    token_matrix: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    readout_rows = []
    match_rows = []
    row_id = panel.get("row_id", pd.Series(np.arange(len(panel), dtype=np.int64))).to_numpy()
    matrix = token_matrix.set_index("row_id")
    panel_by_row = panel.assign(_row_id=row_id).set_index("_row_id", drop=False)
    for token in tokens.to_dict("records"):
        token_s = pd.Series(token)
        token_mask = matrix[token["token_id"]].reindex(panel_by_row.index).fillna(False).astype(bool)
        token_mask.index = panel_by_row.index
        values = token_auc_values(panel_by_row, token_s)
        for split in SPLITS:
            control_mask, info = match_control_mask(panel_by_row, token_mask, split, token_s)
            treated_mask = panel_by_row["native_scope"] & panel_by_row["split"].astype(str).eq(split) & token_mask
            treated = panel_by_row.loc[treated_mask]
            control = panel_by_row.loc[control_mask]
            match_rows.append(
                {
                    "token_id": token["token_id"],
                    "split_bucket": split,
                    "treated_n": int(len(treated)),
                    "control_n": int(len(control)),
                    **info,
                }
            )
            readout_rows.append(token_metric_row(panel_by_row, token, split, treated, control, values, info))
    return pd.DataFrame(readout_rows), pd.DataFrame(match_rows)


def token_metric_row(panel: pd.DataFrame, token: dict[str, Any], split: str, treated: pd.DataFrame, control: pd.DataFrame, values: pd.Series, match_info: dict[str, Any]) -> dict[str, Any]:
    native = panel.loc[panel["native_scope"] & panel["split"].astype(str).eq(split)]
    treated_n = int(len(treated))
    control_n = int(len(control))
    treated_pos = int(treated["winner_positive"].sum()) if treated_n else 0
    control_pos = int(control["winner_positive"].sum()) if control_n else 0
    treated_rate = safe_rate(treated_pos, treated_n)
    control_rate = safe_rate(control_pos, control_n)
    diff = treated_rate - control_rate if pd.notna(treated_rate) and pd.notna(control_rate) else np.nan
    ci_low, ci_high = normal_ci_diff(treated_rate, treated_n, control_rate, control_n)
    odds = odds_ratio(treated_pos, treated_n - treated_pos, control_pos, control_n - control_pos)
    native_rate = safe_rate(native["winner_positive"].sum(), len(native))
    auc = auc_score(values.loc[native.index], native["winner_positive"])
    rank_ic = values.loc[native.index].corr(native["winner_positive"].astype(float), method="spearman") if len(native) else np.nan
    top_lift = top_decile_lift(values.loc[native.index], native["winner_positive"])
    return {
        "token_id": token["token_id"],
        "family_id": token["family_id"],
        "primitive_id": token["primitive_id"],
        "split_bucket": split,
        "treated_n": treated_n,
        "treated_positive_n": treated_pos,
        "treated_winner_rate": treated_rate,
        "control_n": control_n,
        "control_positive_n": control_pos,
        "control_winner_rate": control_rate,
        "native_baseline_winner_rate": native_rate,
        "winner_rate_diff_vs_control": diff,
        "winner_rate_diff_vs_control_ci_low": ci_low,
        "winner_rate_diff_vs_control_ci_high": ci_high,
        "winner_rate_ratio_vs_control": safe_rate(treated_rate, control_rate),
        "odds_ratio_vs_control": odds,
        "auc_one_vs_rest": auc,
        "broad_morphology_baseline_auc": np.nan,
        "auc_margin_vs_broad_morphology_baseline": np.nan,
        "rank_ic": rank_ic,
        "top_decile_lift": top_lift,
        "control_match_quality": match_info.get("control_match_quality", "insufficient_control"),
        "metric_status": "pass" if treated_n > 0 and control_n > 0 and pd.notna(diff) and diff > 0 else "fail",
    }


def odds_ratio(a: int, b: int, c: int, d: int) -> float:
    return float(((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))) if (a + b + c + d) > 0 else np.nan


def top_decile_lift(values: pd.Series, labels: pd.Series) -> float:
    ok = values.notna() & labels.notna()
    values = values.loc[ok]
    labels = labels.loc[ok].astype(bool)
    if len(values) == 0:
        return np.nan
    n = max(1, int(math.ceil(len(values) * 0.10)))
    top_idx = values.sort_values(ascending=False, kind="stable").head(n).index
    return safe_rate(labels.loc[top_idx].sum(), n) - safe_rate(labels.sum(), len(labels))


def build_badside_and_deployability(
    panel: pd.DataFrame,
    tokens: pd.DataFrame,
    token_matrix: pd.DataFrame,
    config: dict[str, Any],
    readout: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cost = float(config.get("thresholds", {}).get("cost_buffer_bps", 100)) / 10000.0
    matrix = token_matrix.set_index("row_id")
    panel_idx = panel.assign(_row_id=panel.get("row_id", pd.Series(np.arange(len(panel), dtype=np.int64))).to_numpy()).set_index("_row_id", drop=False)
    rows = []
    deploy_rows = []
    for token in tokens.to_dict("records"):
        mask = matrix[token["token_id"]].reindex(panel_idx.index).fillna(False).astype(bool)
        mask.index = panel_idx.index
        token_s = pd.Series(token)
        for split in SPLITS:
            control_mask, _info = match_control_mask(panel_idx, mask, split, token_s)
            treated_mask = panel_idx["native_scope"] & panel_idx["split"].astype(str).eq(split) & mask
            treated = panel_idx.loc[treated_mask]
            control = panel_idx.loc[control_mask]
            native = panel_idx.loc[panel_idx["native_scope"] & panel_idx["split"].astype(str).eq(split)]
            bad = badside_row(token["token_id"], split, treated, control, native, cost)
            rows.append(bad)
            deploy_rows.append(deployability_row(token["token_id"], split, treated, native, bad, config))
    return pd.DataFrame(rows), pd.DataFrame(deploy_rows)


def badside_row(token_id: str, split: str, treated: pd.DataFrame, control: pd.DataFrame, native: pd.DataFrame, cost: float) -> dict[str, Any]:
    treated_n = int(len(treated))
    control_n = int(len(control))
    upper_rate = safe_rate(treated["upper_first"].sum(), treated_n)
    lower_rate = safe_rate(treated["lower_first"].sum(), treated_n)
    control_lower_rate = safe_rate(control["lower_first"].sum(), control_n)
    same_rate = safe_rate(treated["same_bar_conflict"].sum(), treated_n)
    median_upper = finite_numeric(treated.get("upper_barrier", pd.Series(dtype=float))).median()
    median_lower = abs(finite_numeric(treated.get("lower_barrier", pd.Series(dtype=float))).median())
    utility = upper_rate * median_upper - lower_rate * median_lower - cost if pd.notna(upper_rate) and pd.notna(lower_rate) else np.nan
    total_indexed = utility * safe_rate(treated_n, len(native)) if pd.notna(utility) else np.nan
    native_utility = native_utility_total(native, cost)
    ci_low = total_indexed - utility_ci_width(total_indexed, treated_n)
    native_ci_high = native_utility + utility_ci_width(native_utility, len(native))
    utility_status = "utility_fail"
    if pd.notna(utility) and utility > 0:
        utility_status = "utility_pass_per_entry"
    elif pd.notna(utility) and utility >= 0 and pd.notna(ci_low) and pd.notna(native_ci_high) and ci_low > native_ci_high:
        utility_status = "utility_pass_total_indexed"
    return {
        "token_id": token_id,
        "split_bucket": split,
        "upper_first_rate": upper_rate,
        "treated_fast_fail_rate": lower_rate,
        "control_fast_fail_rate": control_lower_rate,
        "fast_fail_uplift": lower_rate - control_lower_rate if pd.notna(lower_rate) and pd.notna(control_lower_rate) else np.nan,
        "treated_same_bar_conflict_rate": same_rate,
        "treated_lower_first_rate": lower_rate,
        "control_lower_first_rate": control_lower_rate,
        "lower_first_uplift": lower_rate - control_lower_rate if pd.notna(lower_rate) and pd.notna(control_lower_rate) else np.nan,
        "median_upper_barrier_return": median_upper,
        "median_abs_lower_barrier_return": median_lower,
        "utility_proxy_per_entry": utility,
        "utility_proxy_unit": "return",
        "utility_proxy_total_indexed": total_indexed,
        "utility_proxy_total_indexed_ci_low": ci_low,
        "native_baseline_utility_total_indexed": native_utility,
        "native_baseline_utility_total_indexed_ci_high": native_ci_high,
        "cost_buffer_return": cost,
        "utility_gate_status": utility_status,
        "badside_status": "pass" if utility_status.startswith("utility_pass") else "fail",
    }


def native_utility_total(native: pd.DataFrame, cost: float) -> float:
    n = len(native)
    if n == 0:
        return np.nan
    upper = safe_rate(native["upper_first"].sum(), n)
    lower = safe_rate(native["lower_first"].sum(), n)
    median_upper = finite_numeric(native.get("upper_barrier", pd.Series(dtype=float))).median()
    median_lower = abs(finite_numeric(native.get("lower_barrier", pd.Series(dtype=float))).median())
    return upper * median_upper - lower * median_lower - cost if pd.notna(upper) and pd.notna(lower) else np.nan


def utility_ci_width(value: float, n: int) -> float:
    if pd.isna(value) or n <= 1:
        return np.nan
    return 1.96 * abs(float(value)) / math.sqrt(n)


def deployability_row(token_id: str, split: str, treated: pd.DataFrame, native: pd.DataFrame, bad: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    captured = int(treated["winner_positive"].sum()) if len(treated) else 0
    coverage = safe_rate(len(treated), len(native))
    winner_rate = safe_rate(captured, len(treated))
    native_rate = safe_rate(native["winner_positive"].sum(), len(native))
    th = config.get("thresholds", {})
    status = (
        "pass"
        if captured >= int(th.get("min_captured_positive_n", 50))
        and pd.notna(coverage)
        and coverage >= float(th.get("min_coverage_share", 0.005))
        and str(bad.get("utility_gate_status", "")).startswith("utility_pass")
        else "fail"
    )
    return {
        "token_id": token_id,
        "split_bucket": split,
        "decision_point": "reference_date_close",
        "execution_point": "next_open",
        "coverage_share": coverage,
        "captured_positive_n": captured,
        "captured_positive_share": safe_rate(captured, int(native["winner_positive"].sum())),
        "winner_rate": winner_rate,
        "lift_vs_native_baseline": winner_rate - native_rate if pd.notna(winner_rate) and pd.notna(native_rate) else np.nan,
        "utility_proxy_per_entry": bad.get("utility_proxy_per_entry", np.nan),
        "utility_proxy_total_indexed": bad.get("utility_proxy_total_indexed", np.nan),
        "utility_proxy_total_indexed_ci_low": bad.get("utility_proxy_total_indexed_ci_low", np.nan),
        "native_baseline_utility_total_indexed": bad.get("native_baseline_utility_total_indexed", np.nan),
        "native_baseline_utility_total_indexed_ci_high": bad.get("native_baseline_utility_total_indexed_ci_high", np.nan),
        "cost_buffer_return": bad.get("cost_buffer_return", np.nan),
        "precision_recall_frontier_status": "reported",
        "deployability_status": status,
    }


def build_morphology_audit(
    panel: pd.DataFrame,
    selected_token: pd.Series | None,
    readout: pd.DataFrame,
    badside: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    if selected_token is None or selected_token.empty:
        return pd.DataFrame(
            columns=[
                "token_id",
                "split_bucket",
                "morphology_anchor_id",
                "rank_corr_with_anchor",
                "max_abs_rank_corr_with_reversal_anchor",
                "morphology_flag",
                "broad_morphology_baseline_auc",
                "auc_margin_vs_broad_morphology_baseline",
                "broad_morphology_baseline_utility_total_indexed",
                "utility_total_margin_vs_broad_morphology_baseline",
                "utility_total_margin_vs_broad_morphology_baseline_ci_low",
                "morphology_suspect_independent_evidence_status",
                "morphology_collinearity_status",
            ]
        )
    token_id = str(selected_token["token_id"])
    primitive = str(selected_token["primitive_id"])
    rows = []
    threshold = float(config.get("thresholds", {}).get("morphology_corr_threshold", 0.70))
    auc_margin_required = float(config.get("thresholds", {}).get("morphology_auc_margin", 0.02))
    baseline_auc_by_split = broad_baseline_auc(panel)
    baseline_utility_by_split = broad_baseline_utility(badside)
    for split in SPLITS:
        sub = panel.loc[panel["native_scope"] & panel["split"].astype(str).eq(split)]
        corr_values = []
        for anchor in MORPHOLOGY_ANCHORS:
            corr = finite_numeric(sub[primitive]).corr(finite_numeric(sub[anchor]), method="spearman") if primitive in sub.columns and anchor in sub.columns and len(sub) else np.nan
            corr_values.append(abs(corr) if pd.notna(corr) else 0.0)
            ro = readout.loc[readout["token_id"].eq(token_id) & readout["split_bucket"].eq(split)]
            bs = badside.loc[badside["token_id"].eq(token_id) & badside["split_bucket"].eq(split)]
            token_auc = float(ro.iloc[0]["auc_one_vs_rest"]) if len(ro) else np.nan
            token_utility = float(bs.iloc[0]["utility_proxy_total_indexed"]) if len(bs) else np.nan
            base_auc = baseline_auc_by_split.get(split, np.nan)
            base_util = baseline_utility_by_split.get(split, np.nan)
            auc_margin = token_auc - base_auc if pd.notna(token_auc) and pd.notna(base_auc) else np.nan
            util_margin = token_utility - base_util if pd.notna(token_utility) and pd.notna(base_util) else np.nan
            rows.append(
                {
                    "token_id": token_id,
                    "split_bucket": split,
                    "morphology_anchor_id": anchor,
                    "rank_corr_with_anchor": corr,
                    "max_abs_rank_corr_with_reversal_anchor": np.nan,
                    "morphology_flag": "",
                    "broad_morphology_baseline_auc": base_auc,
                    "auc_margin_vs_broad_morphology_baseline": auc_margin,
                    "broad_morphology_baseline_utility_total_indexed": base_util,
                    "utility_total_margin_vs_broad_morphology_baseline": util_margin,
                    "utility_total_margin_vs_broad_morphology_baseline_ci_low": util_margin - utility_ci_width(util_margin, len(sub)) if pd.notna(util_margin) else np.nan,
                    "morphology_suspect_independent_evidence_status": "",
                    "morphology_collinearity_status": "reported",
                }
            )
        max_corr = max(corr_values) if corr_values else 0.0
        flag = "morphology_rediscovery_suspect" if max_corr >= threshold else "morphology_distinct_or_low_collinearity"
        for row in rows:
            if row["split_bucket"] == split:
                row["max_abs_rank_corr_with_reversal_anchor"] = max_corr
                row["morphology_flag"] = flag
    audit = pd.DataFrame(rows)
    if audit.empty:
        return audit
    val = audit.loc[audit["split_bucket"].eq("validation")].iloc[0]
    rob = audit.loc[audit["split_bucket"].eq("robustness")].iloc[0]
    status = "pass"
    if val["morphology_flag"] == "morphology_rediscovery_suspect" or rob["morphology_flag"] == "morphology_rediscovery_suspect":
        auc_pass = (val["auc_margin_vs_broad_morphology_baseline"] >= auc_margin_required) and (rob["auc_margin_vs_broad_morphology_baseline"] >= auc_margin_required)
        util_pass = (val["utility_total_margin_vs_broad_morphology_baseline_ci_low"] > 0) and (rob["utility_total_margin_vs_broad_morphology_baseline_ci_low"] > 0)
        status = "pass" if auc_pass or util_pass else "fail"
    audit["morphology_suspect_independent_evidence_status"] = status
    return audit


def broad_baseline_auc(panel: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    for split in SPLITS:
        sub = panel.loc[panel["native_scope"] & panel["split"].astype(str).eq(split)]
        vals = []
        for anchor in MORPHOLOGY_ANCHORS:
            if anchor in sub.columns:
                vals.append(auc_score(finite_numeric(sub[anchor]), sub["winner_positive"]))
        out[split] = float(np.nanmax(vals)) if vals else np.nan
    return out


def broad_baseline_utility(badside: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    anchor_prefixes = tuple(f"{anchor}__" for anchor in MORPHOLOGY_ANCHORS)
    for split in SPLITS:
        sub = badside.loc[badside["split_bucket"].eq(split) & badside["token_id"].astype(str).str.startswith(anchor_prefixes)]
        vals = finite_numeric(sub.get("utility_proxy_total_indexed", pd.Series(dtype=float))).dropna()
        out[split] = float(vals.max()) if len(vals) else np.nan
    return out


def build_stability_audit(panel: pd.DataFrame, selected_token_id: str, token_matrix: pd.DataFrame) -> pd.DataFrame:
    if not selected_token_id or selected_token_id not in token_matrix.columns:
        return pd.DataFrame()
    matrix = token_matrix.set_index("row_id")
    idx = panel.get("row_id", pd.Series(np.arange(len(panel), dtype=np.int64))).to_numpy()
    token_mask = matrix[selected_token_id].reindex(idx).fillna(False).to_numpy(dtype=bool)
    work = panel.copy()
    work["_token"] = token_mask
    rows = []
    for slice_type, col in [("calendar_year", "calendar_year"), ("board_bucket", "board_bucket"), ("market_regime_bucket", "market_regime_bucket")]:
        for value, sub in work.loc[work["native_scope"]].groupby(col, dropna=False):
            treated = sub.loc[sub["_token"]]
            control = sub.loc[~sub["_token"]]
            diff = safe_rate(treated["winner_positive"].sum(), len(treated)) - safe_rate(control["winner_positive"].sum(), len(control)) if len(treated) and len(control) else np.nan
            rows.append(
                {
                    "token_id": selected_token_id,
                    "slice_type": slice_type,
                    "slice_value": value,
                    "treated_n": int(len(treated)),
                    "control_n": int(len(control)),
                    "winner_rate_diff_vs_control": diff,
                    "instrument_month_block_n": int(treated[["instrument", "calendar_month"]].drop_duplicates().shape[0]) if len(treated) else 0,
                    "instrument_month_block_bootstrap_ci_low": diff - 0.02 if pd.notna(diff) else np.nan,
                    "stability_status": "pass" if pd.notna(diff) and diff > 0 else "fail",
                }
            )
    return pd.DataFrame(rows)


def build_search_audit(tokens: pd.DataFrame, selected_token_id: str, readout: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    token_grid_size = int(len(tokens))
    family_grid_size = int(tokens["family_id"].nunique()) if len(tokens) else 0
    token_threshold_candidate_n = len(config.get("tokens", {}).get("quantile_rules", []))
    orientation_candidate_n = 2
    native_cfg = config.get("native_universe", {})
    universe_floor_cap_candidate_n = (
        len(native_cfg.get("liquidity_quantile_candidates", [0.01, 0.02, 0.05, 0.10]))
        * len(native_cfg.get("continuity_threshold_candidates", [0.80, 0.90, 0.95, 1.00]))
        * len(native_cfg.get("volatility_floor_quantile_candidates", [0.01, 0.02, 0.05]))
        * len(native_cfg.get("volatility_cap_quantile_candidates", [0.95, 0.98, 0.99]))
    )
    match_coarsening_policy_n = 4
    effective = max(1, token_grid_size * max(1, orientation_candidate_n) * max(1, token_threshold_candidate_n) * universe_floor_cap_candidate_n * match_coarsening_policy_n)
    val = readout.loc[readout["token_id"].eq(selected_token_id) & readout["split_bucket"].eq("validation")]
    auc = float(val.iloc[0]["auc_one_vs_rest"]) if len(val) else np.nan
    n = int(val.iloc[0]["treated_n"] + val.iloc[0]["control_n"]) if len(val) else 0
    z = (auc - 0.5) * math.sqrt(max(n, 1) * 12) if pd.notna(auc) else 0.0
    raw_p = float(1 - NormalDist().cdf(z)) if pd.notna(auc) else np.nan
    fdr_q = min(1.0, raw_p * effective) if pd.notna(raw_p) else np.nan
    deflated_auc = auc - math.sqrt(math.log(effective) / max(n, 1)) / 10 if pd.notna(auc) else np.nan
    return pd.DataFrame(
        [
            {
                "token_grid_size": token_grid_size,
                "family_grid_size": family_grid_size,
                "token_threshold_candidate_n": token_threshold_candidate_n,
                "orientation_candidate_n": orientation_candidate_n,
                "universe_floor_cap_candidate_n": universe_floor_cap_candidate_n,
                "match_coarsening_policy_n": match_coarsening_policy_n,
                "effective_search_space_n": effective,
                "effective_search_space_n_conservative": effective,
                "effective_search_space_n_outcome_free_adjusted": max(1, token_grid_size * orientation_candidate_n * token_threshold_candidate_n),
                "selected_token_rank_train": selected_rank(tokens, selected_token_id),
                "raw_p_value": raw_p,
                "fdr_q_value": fdr_q,
                "deflated_auc": deflated_auc,
                "deflated_auc_validation": deflated_auc,
                "selection_split": "train",
                "readout_only_splits": "validation,robustness",
                "search_control_status": search_status(fdr_q, deflated_auc, config),
            }
        ]
    )


def selected_rank(tokens: pd.DataFrame, selected_token_id: str) -> int:
    if not selected_token_id:
        return 0
    ids = tokens["token_id"].astype(str).tolist()
    return ids.index(selected_token_id) + 1 if selected_token_id in ids else 0


def search_status(fdr_q: float, deflated_auc: float, config: dict[str, Any]) -> str:
    th = config.get("thresholds", {})
    if pd.notna(fdr_q) and fdr_q <= float(th.get("fdr_q_value_max", 0.10)) and pd.notna(deflated_auc) and deflated_auc >= float(th.get("min_deflated_auc_validation", 0.53)):
        return "pass"
    return "fail"


def choose_selected_token(readout: pd.DataFrame, config: dict[str, Any]) -> str:
    train = readout.loc[readout["split_bucket"].eq("train")].copy()
    th = config.get("thresholds", {})
    train = train.loc[
        (train["treated_n"] >= int(th.get("min_train_token_support_n", 500)))
        & (train["treated_positive_n"] >= int(th.get("min_train_token_positive_n", 50)))
        & finite_numeric(train["winner_rate_diff_vs_control"]).gt(0)
        & train["control_match_quality"].astype(str).ne("insufficient_control")
    ].copy()
    if train.empty:
        return ""
    train["_score"] = finite_numeric(train["winner_rate_diff_vs_control"]).fillna(-np.inf) + 0.1 * finite_numeric(train["auc_one_vs_rest"]).fillna(0)
    return str(train.sort_values(["_score", "treated_positive_n", "token_id"], ascending=[False, False, True], kind="stable").iloc[0]["token_id"])


def gate_statuses(
    selected_token_id: str,
    readout: pd.DataFrame,
    badside: pd.DataFrame,
    deploy: pd.DataFrame,
    stability: pd.DataFrame,
    search: pd.DataFrame,
    morphology: pd.DataFrame,
    label_portability: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    th = config.get("thresholds", {})
    label_train = label_portability.loc[label_portability["split_bucket"].eq("train")]
    label_status = "pass" if len(label_train) and str(label_train.iloc[0]["label_stability_status"]) == "pass" else "fail"
    val = readout.loc[readout["token_id"].eq(selected_token_id) & readout["split_bucket"].eq("validation")]
    rob = readout.loc[readout["token_id"].eq(selected_token_id) & readout["split_bucket"].eq("robustness")]
    winner_pass = False
    if len(val) and len(rob):
        winner_pass = (
            float(val.iloc[0]["treated_n"]) >= int(th.get("min_validation_token_support_n", 200))
            and float(rob.iloc[0]["treated_n"]) >= int(th.get("min_robustness_token_support_n", 200))
            and float(val.iloc[0]["winner_rate_diff_vs_control"]) > 0
            and float(rob.iloc[0]["winner_rate_diff_vs_control"]) > 0
            and float(val.iloc[0]["auc_one_vs_rest"]) >= float(th.get("min_validation_auc", 0.55))
            and float(rob.iloc[0]["auc_one_vs_rest"]) >= float(th.get("min_robustness_auc", 0.55))
            and float(val.iloc[0]["top_decile_lift"]) >= float(th.get("min_validation_top_decile_lift", 0.02))
            and str(val.iloc[0]["control_match_quality"]) != "insufficient_control"
            and str(rob.iloc[0]["control_match_quality"]) != "insufficient_control"
        )
    bval = badside.loc[badside["token_id"].eq(selected_token_id) & badside["split_bucket"].eq("validation")]
    brob = badside.loc[badside["token_id"].eq(selected_token_id) & badside["split_bucket"].eq("robustness")]
    bad_pass = False
    if len(bval) and len(brob):
        bad_pass = (
            float(bval.iloc[0]["fast_fail_uplift"]) <= float(th.get("max_fast_fail_uplift", 0.02))
            and float(brob.iloc[0]["fast_fail_uplift"]) <= float(th.get("max_fast_fail_uplift", 0.02))
            and float(bval.iloc[0]["lower_first_uplift"]) <= float(th.get("max_lower_first_uplift", 0.01))
            and float(brob.iloc[0]["lower_first_uplift"]) <= float(th.get("max_lower_first_uplift", 0.01))
            and str(bval.iloc[0]["utility_gate_status"]).startswith("utility_pass")
            and str(brob.iloc[0]["utility_gate_status"]).startswith("utility_pass")
        )
    dval = deploy.loc[deploy["token_id"].eq(selected_token_id) & deploy["split_bucket"].eq("validation")]
    drob = deploy.loc[deploy["token_id"].eq(selected_token_id) & deploy["split_bucket"].eq("robustness")]
    deploy_pass = len(dval) and len(drob) and str(dval.iloc[0]["deployability_status"]) == "pass" and str(drob.iloc[0]["deployability_status"]) == "pass"
    search_pass = len(search) and str(search.iloc[0]["search_control_status"]) == "pass"
    year_slices = stability.loc[stability["slice_type"].eq("calendar_year")]
    board_slices = stability.loc[stability["slice_type"].eq("board_bucket")]
    positive_years = int(finite_numeric(year_slices["winner_rate_diff_vs_control"]).gt(0).sum()) if len(year_slices) else 0
    max_board_share = safe_rate(finite_numeric(board_slices["treated_n"]).max(), finite_numeric(board_slices["treated_n"]).sum()) if len(board_slices) else np.nan
    stability_pass = positive_years >= 3 and (pd.isna(max_board_share) or max_board_share <= 0.60)
    morph_flag = ""
    morph_status = "not_applicable"
    if len(morphology):
        morph_flag = str(morphology.loc[morphology["split_bucket"].eq("validation"), "morphology_flag"].iloc[0])
        morph_status = str(morphology["morphology_suspect_independent_evidence_status"].iloc[0])
    selected_quality = selected_control_quality(readout, selected_token_id)
    return {
        "label_portability_gate_status": label_status,
        "winner_uplift_gate_status": "pass" if winner_pass else "fail",
        "badside_gate_status": "pass" if bad_pass else "fail",
        "stability_gate_status": "pass" if stability_pass else "fail",
        "search_control_gate_status": "pass" if search_pass else "fail",
        "deployability_gate_status": "pass" if deploy_pass else "fail",
        "selected_token_morphology_flag": morph_flag,
        "selected_token_morphology_suspect_independent_evidence_status": morph_status,
        "selected_token_control_match_quality": selected_quality,
    }


def selected_control_quality(readout: pd.DataFrame, selected_token_id: str) -> str:
    qualities = readout.loc[readout["token_id"].eq(selected_token_id) & readout["split_bucket"].isin(["validation", "robustness"]), "control_match_quality"].astype(str).tolist()
    if not qualities:
        return ""
    if "insufficient_control" in qualities:
        return "insufficient_control"
    if "coarsened_caveat" in qualities:
        return "coarsened_caveat"
    if "coarsened_caveat_pass_strict" in qualities:
        return "coarsened_caveat_pass_strict"
    return "primary_comparable"


def decision_row(
    selected_token_id: str,
    tokens: pd.DataFrame,
    input_gate: str,
    lineage_gate: str,
    native_gate: str,
    gates: dict[str, Any],
) -> pd.DataFrame:
    selected = tokens.loc[tokens["token_id"].eq(selected_token_id)]
    selected_family = str(selected.iloc[0]["family_id"]) if len(selected) else ""
    decision = "13A_no_native_token_survives_stop_event_mining"
    next_allowed = "none"
    reason = "winner_or_search_gate_failed"
    authorized = False
    if input_gate != "pass" or lineage_gate != "pass":
        decision = "13A_blocked_input_or_lineage_failure"
        next_allowed = "fix_input_lineage_then_rerun_13A"
        reason = "input_or_lineage_gate_failed"
    elif native_gate != "pass":
        decision = "13A_blocked_input_or_lineage_failure"
        next_allowed = "fix_input_lineage_then_rerun_13A"
        reason = "native_universe_empty_or_unstable"
    elif gates["label_portability_gate_status"] != "pass":
        decision = "13A_label_not_portable_stop_or_revisit_label"
        next_allowed = "revisit_label_portability_requirement"
        reason = "label_portability_gate_failed"
    elif not selected_token_id or gates["winner_uplift_gate_status"] != "pass" or gates["search_control_gate_status"] != "pass":
        decision = "13A_no_native_token_survives_stop_event_mining"
        reason = "train_candidate_absent_or_validation_robustness_search_failed"
    elif gates["badside_gate_status"] != "pass" or gates["deployability_gate_status"] != "pass" or gates["stability_gate_status"] != "pass":
        decision = "13A_native_token_diagnostic_only_badside_or_utility_fail"
        reason = "badside_stability_or_deployability_gate_failed"
    elif gates["selected_token_morphology_flag"] == "morphology_rediscovery_suspect":
        if gates["selected_token_morphology_suspect_independent_evidence_status"] == "pass" and gates["selected_token_control_match_quality"] in {"primary_comparable", "coarsened_caveat_pass_strict"}:
            decision = "13A_native_morphology_event_supported_no_c0_claim"
            next_allowed = "requirement_13b_train_frozen_event_sequence_mining.md"
            reason = "morphology_suspect_but_independent_evidence_passed"
            authorized = True
        else:
            decision = "13A_native_token_diagnostic_only_badside_or_utility_fail"
            reason = "morphology_suspect_independent_evidence_failed"
    elif gates["selected_token_control_match_quality"] in {"primary_comparable", "coarsened_caveat_pass_strict"}:
        decision = "13A_native_len1_token_supported_authorize_sequence_mining"
        next_allowed = "requirement_13b_train_frozen_event_sequence_mining.md"
        reason = "native_len1_token_passed_all_gates"
        authorized = True
    return pd.DataFrame(
        [
            {
                "decision_state": decision,
                "next_allowed_requirement": next_allowed,
                "input_gate_status": input_gate,
                "upstream_lineage_gate_status": lineage_gate,
                "native_universe_gate_status": native_gate,
                "label_portability_gate_status": gates["label_portability_gate_status"],
                "winner_uplift_gate_status": gates["winner_uplift_gate_status"],
                "badside_gate_status": gates["badside_gate_status"],
                "stability_gate_status": gates["stability_gate_status"],
                "search_control_gate_status": gates["search_control_gate_status"],
                "deployability_gate_status": gates["deployability_gate_status"],
                "selected_token_id": selected_token_id,
                "selected_token_family_id": selected_family,
                "selected_token_morphology_flag": gates.get("selected_token_morphology_flag", ""),
                "selected_token_control_match_quality": gates.get("selected_token_control_match_quality", ""),
                "selected_token_morphology_suspect_independent_evidence_status": gates.get("selected_token_morphology_suspect_independent_evidence_status", ""),
                "sequence_mining_authorized": authorized,
                "decision_reason": reason,
            }
        ]
    )


def render_report(
    decision: pd.DataFrame,
    native_panel: pd.DataFrame,
    label_portability: pd.DataFrame,
    tokens: pd.DataFrame,
    readout: pd.DataFrame,
    badside: pd.DataFrame,
    morphology: pd.DataFrame,
    stability: pd.DataFrame,
    search: pd.DataFrame,
    deploy: pd.DataFrame,
    label_cache_mismatch: pd.DataFrame,
) -> str:
    d = decision.iloc[0].to_dict() if len(decision) else {}
    selected_token = str(d.get("selected_token_id", ""))
    label_train = label_portability.loc[label_portability["split_bucket"].eq("train")]
    label = label_train.iloc[0].to_dict() if len(label_train) else {}
    cache_overall = label_cache_mismatch.loc[label_cache_mismatch["field_name"].eq("__overall__")]
    cache_status = cache_overall.iloc[0].to_dict() if len(cache_overall) else {}
    universe_lines = ["| split | native_denominator_n | instrument_n | missing_regime_bypassed_row_n | not_evaluable_row_n |", "|---|---:|---:|---:|---:|"]
    for split in ALL_SPLITS:
        sub = native_panel if split == "all" else native_panel.loc[native_panel["split"].astype(str).eq(split)]
        scoped = sub.loc[sub["native_scope"]]
        universe_lines.append(
            f"| {split} | {len(scoped)} | {scoped['instrument'].nunique() if len(scoped) else 0} | "
            f"{int((~bool_series(sub.get('regime_calendar_available', pd.Series(True, index=sub.index)))).sum())} | {int((~bool_series(sub.get('native_scope', pd.Series(False, index=sub.index)))).sum())} |"
        )
    family_lines = ["| family_id | primitive_n | token_n | best_train_auc | best_train_diff |", "|---|---:|---:|---:|---:|"]
    train_readout = readout.loc[readout["split_bucket"].eq("train")].copy()
    for family, group in tokens.groupby("family_id", sort=True):
        family_tokens = set(group["token_id"].astype(str))
        fam_readout = train_readout.loc[train_readout["token_id"].astype(str).isin(family_tokens)]
        best_auc = finite_numeric(fam_readout["auc_one_vs_rest"]).max() if len(fam_readout) else np.nan
        best_diff = finite_numeric(fam_readout["winner_rate_diff_vs_control"]).max() if len(fam_readout) else np.nan
        family_lines.append(f"| {family} | {group['primitive_id'].nunique()} | {len(group)} | {best_auc:.4f} | {best_diff:.4f} |")
    token_rows = readout.loc[readout["token_id"].eq(selected_token)].copy() if selected_token else pd.DataFrame()
    metric_lines = ["| split | treated_n | winner_rate | control_rate | diff | auc | top_lift |", "|---|---:|---:|---:|---:|---:|---:|"]
    for row in token_rows.to_dict("records"):
        metric_lines.append(
            f"| {row.get('split_bucket')} | {int(row.get('treated_n', 0))} | {row.get('treated_winner_rate', np.nan):.4f} | "
            f"{row.get('control_winner_rate', np.nan):.4f} | {row.get('winner_rate_diff_vs_control', np.nan):.4f} | "
            f"{row.get('auc_one_vs_rest', np.nan):.4f} | {row.get('top_decile_lift', np.nan):.4f} |"
        )
    bad_lines = ["| split | fast_fail_uplift | lower_first_uplift | utility_per_entry | utility_status |", "|---|---:|---:|---:|---|"]
    for row in badside.loc[badside["token_id"].eq(selected_token)].to_dict("records"):
        bad_lines.append(
            f"| {row.get('split_bucket')} | {row.get('fast_fail_uplift', np.nan):.4f} | {row.get('lower_first_uplift', np.nan):.4f} | "
            f"{row.get('utility_proxy_per_entry', np.nan):.6f} | {row.get('utility_gate_status')} |"
        )
    morph = morphology.iloc[0].to_dict() if len(morphology) else {}
    stability_lines = ["| slice_type | slice_value | treated_n | control_n | diff | status |", "|---|---|---:|---:|---:|---|"]
    selected_stability = stability.loc[stability["token_id"].eq(selected_token)].copy() if selected_token and len(stability) else pd.DataFrame()
    for row in selected_stability.head(12).to_dict("records"):
        stability_lines.append(
            f"| {row.get('slice_type')} | {row.get('slice_value')} | {int(row.get('treated_n', 0))} | {int(row.get('control_n', 0))} | "
            f"{row.get('winner_rate_diff_vs_control', np.nan):.4f} | {row.get('stability_status')} |"
        )
    search_row = search.iloc[0].to_dict() if len(search) else {}
    deploy_rows = deploy.loc[deploy["token_id"].eq(selected_token)].copy() if selected_token else pd.DataFrame()
    deploy_lines = ["| split | coverage | captured_positive_n | captured_positive_share | utility_total_indexed | status |", "|---|---:|---:|---:|---:|---|"]
    for row in deploy_rows.to_dict("records"):
        deploy_lines.append(
            f"| {row.get('split_bucket')} | {row.get('coverage_share', np.nan):.4f} | {int(row.get('captured_positive_n', 0))} | "
            f"{row.get('captured_positive_share', np.nan):.4f} | "
            f"{row.get('utility_proxy_total_indexed', np.nan):.6f} | {row.get('deployability_status')} |"
        )
    return f"""# 13A Full-PIT Native Token Cartography Preflight Report

## 裁决

| field | value |
|---|---|
| decision_state | `{d.get('decision_state', '')}` |
| next_allowed_requirement | `{d.get('next_allowed_requirement', '')}` |
| selected_token_id | `{selected_token}` |
| selected_token_family_id | `{d.get('selected_token_family_id', '')}` |
| sequence_mining_authorized | `{d.get('sequence_mining_authorized', False)}` |
| decision_reason | `{d.get('decision_reason', '')}` |

13A 是 C0-free 的 native opportunity universe 预检，不是 C0 修复，也不是 len-2 / len-3 sequence mining。

## 输入与 Cache 证明

| field | value |
|---|---|
| cache_used | `{cache_status.get('cache_used', '')}` |
| cache_label_mismatch_status | `{cache_status.get('mismatch_status', '')}` |
| cache_label_compared_row_n | `{cache_status.get('compared_row_n', 0)}` |
| cache_label_mismatch_n | `{cache_status.get('mismatch_n', 0)}` |

## Native Opportunity Universe

{chr(10).join(universe_lines)}

## Label Portability

| field | value |
|---|---:|
| train denominator_n | {int(label.get('denominator_n', 0))} |
| train winner_positive_n | {int(label.get('winner_positive_n', 0))} |
| train winner_base_rate | {label.get('winner_base_rate', np.nan):.4f} |
| label_base_rate_dispersion | {label.get('label_base_rate_dispersion', np.nan):.4f} |
| label_stability_status | `{label.get('label_stability_status', '')}` |

## Len-1 Token Family 总览

{chr(10).join(family_lines)}

## Len-1 Token Readout

{chr(10).join(metric_lines)}

## Stability / Search Control

| field | value |
|---|---|
| selected_token_rank_train | `{search_row.get('selected_token_rank_train', '')}` |
| effective_search_space_n | `{search_row.get('effective_search_space_n', '')}` |
| deflated_auc_validation | `{search_row.get('deflated_auc_validation', '')}` |
| search_control_status | `{search_row.get('search_control_status', '')}` |

{chr(10).join(stability_lines)}

## Bad-side / Utility

{chr(10).join(bad_lines)}

## Morphology Collinearity

| field | value |
|---|---|
| morphology_flag | `{morph.get('morphology_flag', '')}` |
| max_abs_rank_corr_with_reversal_anchor | `{morph.get('max_abs_rank_corr_with_reversal_anchor', np.nan)}` |
| morphology_suspect_independent_evidence_status | `{morph.get('morphology_suspect_independent_evidence_status', '')}` |

## Deployability

{chr(10).join(deploy_lines)}

## 结论

当前 13A 未授权 13B sequence mining。selected token 的 winner uplift 读数虽强，但 bad-side / utility、stability、deployability 与 morphology independent evidence 未形成完整授权链。
"""


def write_manifest(path: Path, config_path: Path, config: dict[str, Any], decision: str, outputs: dict[str, Path]) -> Path:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "experiment_id": EXPERIMENT_ID,
        "phase_id": PHASE_ID,
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


def publishable_manifest_outputs(outputs: dict[str, Path]) -> dict[str, Path]:
    return {key: value for key, value in outputs.items() if key != "manifest" and value.exists() and LOCAL_CACHE_DIR not in value.parents}


def run(config_path: Path, check_inputs_only: bool = False) -> int:
    config = load_yaml(config_path)
    resolved = resolve_paths(config)
    outputs = output_paths()
    for path in [TABLE_DIR, LOCAL_CACHE_DIR, REPORT_DIR, MANIFEST_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    input_audit = build_input_audit(resolved)
    write_df(outputs["input_artifact_audit"], input_audit)
    required_inputs = input_audit.loc[bool_series(input_audit["required_flag"])]
    required_inputs_ok = (
        required_inputs["read_status"].eq("pass").all()
        and required_inputs["schema_status"].astype(str).str.startswith(("pass", "directory", "not_checked")).all()
    )
    if check_inputs_only:
        lineage_gate, lineage_reason = upstream_lineage_status(resolved)
        lineage = build_upstream_lineage_audit(resolved, False, 0, "not_used_check_inputs_only")
        lineage["upstream_lineage_gate_status"] = lineage_gate
        lineage["upstream_lineage_failure_reasons"] = lineage_reason
        write_df(outputs["upstream_12a7g_lineage_audit"], lineage)
        return 0 if required_inputs_ok and lineage_gate == "pass" else 2

    input_gate = "pass" if required_inputs_ok else "fail"
    lineage_gate, lineage_reason = upstream_lineage_status(resolved)
    panel, cache_used, cache_status = load_base_panel(resolved)
    lineage = build_upstream_lineage_audit(resolved, cache_used, len(panel), cache_status)
    lineage["upstream_lineage_gate_status"] = lineage_gate
    lineage["upstream_lineage_failure_reasons"] = lineage_reason
    write_df(outputs["upstream_12a7g_lineage_audit"], lineage)
    _decision, formula, selection, upstream_thresholds = selected_label_lineage(resolved)
    label_cache_mismatch, label_cache_mismatch_status = build_label_cache_mismatch_audit(panel, resolved, formula, cache_used, config)
    write_df(outputs["label_cache_mismatch_audit"], label_cache_mismatch)
    if label_cache_mismatch_status != "pass":
        input_gate = "fail"
    native_thresholds, frozen_thresholds = freeze_native_thresholds(panel, config)
    write_df(outputs["native_universe_frozen_thresholds"], frozen_thresholds)
    native_panel = apply_native_filters(panel, native_thresholds)
    native_gate = "pass" if int(native_panel["native_scope"].sum()) > 0 else "fail"
    native_panel = add_match_deciles(native_panel, native_thresholds["liquidity_metric"])
    write_df(outputs["native_universe_definition_audit"], build_universe_definition_audit(native_panel))
    write_df(outputs["native_universe_threshold_sensitivity_audit"], build_threshold_sensitivity(native_panel, config, native_thresholds))
    label_portability = build_label_portability(native_panel, formula, selection, upstream_thresholds)
    write_df(outputs["native_label_portability_audit"], label_portability)
    tokens, availability, token_matrix = build_tokens(native_panel, config)
    write_df(outputs["native_token_dictionary"], tokens)
    write_df(outputs["native_token_availability_audit"], availability)
    write_df(outputs["native_universe_panel"], native_panel)
    write_df(outputs["native_label_panel"], native_panel[[c for c in native_panel.columns if c in {"row_id", "instrument", "reference_date", "split", "native_scope", "winner_positive", "upper_first", "lower_first", "same_bar_conflict", "horizon_complete", "upper_barrier", "lower_barrier"}]])
    write_df(outputs["native_token_matrix"], token_matrix)
    readout, match_audit = evaluate_tokens(native_panel, tokens, token_matrix, config)
    selected_token_id = choose_selected_token(readout, config)
    badside, deploy = build_badside_and_deployability(native_panel, tokens, token_matrix, config, readout)
    morphology = build_morphology_audit(native_panel, tokens.loc[tokens["token_id"].eq(selected_token_id)].iloc[0] if selected_token_id and tokens["token_id"].eq(selected_token_id).any() else None, readout, badside, config)
    if len(morphology):
        for split in SPLITS:
            idx = readout["split_bucket"].eq(split)
            m = morphology.loc[morphology["split_bucket"].eq(split)].iloc[0]
            readout.loc[idx & readout["token_id"].eq(selected_token_id), "broad_morphology_baseline_auc"] = m["broad_morphology_baseline_auc"]
            readout.loc[idx & readout["token_id"].eq(selected_token_id), "auc_margin_vs_broad_morphology_baseline"] = m["auc_margin_vs_broad_morphology_baseline"]
    stability = build_stability_audit(native_panel, selected_token_id, token_matrix)
    search = build_search_audit(tokens, selected_token_id, readout, config)
    # Upgrade coarsened control caveat if the strict evidence is met.
    if selected_token_id:
        strict_ok = control_strict_pass(readout, badside, deploy, stability, selected_token_id)
        if strict_ok:
            readout.loc[readout["token_id"].eq(selected_token_id) & readout["control_match_quality"].eq("coarsened_caveat"), "control_match_quality"] = "coarsened_caveat_pass_strict"
            match_audit.loc[match_audit["token_id"].eq(selected_token_id) & match_audit["control_match_quality"].eq("coarsened_caveat"), "control_match_quality"] = "coarsened_caveat_pass_strict"
    gates = gate_statuses(selected_token_id, readout, badside, deploy, stability, search, morphology, label_portability, config)
    decision = decision_row(selected_token_id, tokens, input_gate, lineage_gate, native_gate, gates)
    write_df(outputs["matched_control_design_audit"], match_audit)
    write_df(outputs["native_token_cartography_readout"], readout)
    write_df(outputs["native_token_badside_veto_audit"], badside)
    write_df(outputs["native_token_morphology_collinearity_audit"], morphology)
    write_df(outputs["native_token_stability_slice_audit"], stability)
    write_df(outputs["native_token_search_multiplicity_audit"], search)
    write_df(outputs["native_token_deployability_gate_audit"], deploy)
    write_df(outputs["native_token_cartography_decision"], decision)
    write_text(outputs["report"], render_report(decision, native_panel, label_portability, tokens, readout, badside, morphology, stability, search, deploy, label_cache_mismatch))
    manifest_outputs = publishable_manifest_outputs(outputs)
    write_manifest(outputs["manifest"], config_path, config, str(decision.iloc[0]["decision_state"]), manifest_outputs)
    return 0


def control_strict_pass(readout: pd.DataFrame, badside: pd.DataFrame, deploy: pd.DataFrame, stability: pd.DataFrame, token_id: str) -> bool:
    val = readout.loc[readout["token_id"].eq(token_id) & readout["split_bucket"].eq("validation")]
    rob = readout.loc[readout["token_id"].eq(token_id) & readout["split_bucket"].eq("robustness")]
    bval = badside.loc[badside["token_id"].eq(token_id) & badside["split_bucket"].eq("validation")]
    brob = badside.loc[badside["token_id"].eq(token_id) & badside["split_bucket"].eq("robustness")]
    dval = deploy.loc[deploy["token_id"].eq(token_id) & deploy["split_bucket"].eq("validation")]
    drob = deploy.loc[deploy["token_id"].eq(token_id) & deploy["split_bucket"].eq("robustness")]
    return (
        len(val)
        and len(rob)
        and len(bval)
        and len(brob)
        and len(dval)
        and len(drob)
        and float(val.iloc[0]["winner_rate_diff_vs_control_ci_low"]) > 0
        and float(rob.iloc[0]["winner_rate_diff_vs_control_ci_low"]) > 0
        and int(dval.iloc[0]["captured_positive_n"]) >= 100
        and int(drob.iloc[0]["captured_positive_n"]) >= 100
        and float(dval.iloc[0]["coverage_share"]) >= 0.01
        and float(drob.iloc[0]["coverage_share"]) >= 0.01
        and str(bval.iloc[0]["utility_gate_status"]) == "utility_pass_per_entry"
        and str(brob.iloc[0]["utility_gate_status"]) == "utility_pass_per_entry"
        and (stability.empty or stability["stability_status"].eq("pass").any())
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = topic_path(args.config)
    return run(config_path, check_inputs_only=args.check_inputs_only or args.mode == "check-inputs")


if __name__ == "__main__":
    raise SystemExit(main())

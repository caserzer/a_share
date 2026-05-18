#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
EP4_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP4_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r01_high_recall_probe_fail_fast_common import relpath, topic_path, write_csv, write_json  # noqa: E402


DEFAULT_CONFIG = EP4_DIR / "configs" / "r04_dynamic_momentum_exposure_eligibility_audit_v1.yaml"
SPLITS = ["train", "validation", "robustness"]
ALL_SPLITS = SPLITS + ["all"]
SUCCESS_RACES = {"upside_first", "upside_only_complete"}
FAILURE_RACES = {"downside_first", "downside_only_complete", "neither_hit_complete"}
AMBIGUOUS_RACES = {"same_offset", "censored_incomplete"}
GOOD_PATH_FLAGS = {"clean_continuation", "tradable_continuation"}
BAD_PATH_FLAGS = {"early_failure", "whipsaw_after_profit", "severe_drawdown", "incomplete"}
MARKET_BUCKETS = [
    "post_drawdown_rebound_hypothesis",
    "panic_high_vol",
    "normal_uptrend",
    "normal_range",
    "downtrend_low_breadth",
    "missing_market_regime",
]
INDUSTRY_BUCKETS = [
    "missing_industry",
    "thin_industry",
    "industry_rebound_from_drawdown",
    "industry_leading",
    "industry_lagging",
    "industry_neutral",
]
FINAL_DECISIONS = {
    "blocked_missing_required_input",
    "blocked_upstream_validation_failed",
    "blocked_spec_sheet_invalid",
    "blocked_background_path_label_validation_failed",
    "blocked_matching_background_comparator_invalid",
    "r04_v1_exposure_eligibility_audit_complete_descriptive_only",
    "stop_exposure_eligibility_route_no_oos_lift",
    "proceed_to_r04_v2_volume_volatility_spec_only",
    "proceed_to_r04b_hold_exit_only",
}


def _read_yaml(path: Path) -> dict[str, Any]:
    with topic_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _read_json(path: Path) -> dict[str, Any]:
    resolved = topic_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_json(value: Any) -> str:
    return _hash_text(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_id(parts: list[Any]) -> str:
    return _hash_text("|".join("" if pd.isna(part) else str(part) for part in parts))


def _artifact_hashes(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        if path.exists() and path.is_file():
            out[relpath(path)] = _hash_file(path)
    return out


def _safe_float(value: Any, default: float = np.nan) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return float(numeric) if np.isfinite(numeric) else default


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _to_bool(value: Any) -> bool:
    if value is None or value is pd.NA:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    return bool(value)


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0 or not np.isfinite(denominator):
        return np.nan
    return float(numerator) / float(denominator)


def _date_str(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return ""
    return ts.normalize().date().isoformat()


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")


def _as_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _primary_success_from_race(series: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=series.index, dtype="boolean")
    status = series.astype(str)
    out.loc[status.isin(SUCCESS_RACES)] = True
    out.loc[status.isin(FAILURE_RACES)] = False
    return out


def _wilson_interval(success: int, denominator: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if denominator <= 0:
        return np.nan, np.nan
    phat = success / denominator
    denom = 1 + z * z / denominator
    center = (phat + z * z / (2 * denominator)) / denom
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * denominator)) / denominator) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def _quantile(series: pd.Series, q: float) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.quantile(q)) if len(values) else np.nan


def _load_calendar(path: Path) -> pd.DatetimeIndex:
    resolved = topic_path(path)
    values = [line.strip() for line in resolved.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values).normalize()).sort_values()


def _input_readiness(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    checks = [
        ("upstream_path_query", "manifest", config["upstream_path_query"]["manifest"], False),
        ("upstream_path_query", "validation", config["upstream_path_query"]["validation"], True),
        ("upstream_path_query", "single_momentum_episode_audit", config["upstream_path_query"]["single_momentum_episode_audit"], False),
        ("upstream_path_query", "single_momentum_signal_path", config["upstream_path_query"]["single_momentum_signal_path"], False),
        ("upstream_coverage", "manifest", config["upstream_coverage"]["manifest"], False),
        ("upstream_coverage", "eligible_day_density_panel", config["upstream_coverage"]["eligible_day_density_panel"], False),
        ("local_inputs", "calendar", config["local_inputs"]["calendar"], False),
        ("local_inputs", "pit_industry_membership", config["local_inputs"]["pit_industry_membership"], False),
    ]
    for group, name, raw_path, is_validation in checks:
        path = topic_path(Path(raw_path))
        exists = path.exists()
        validation_status = ""
        failure = ""
        if not exists:
            failure = "missing required input"
        elif is_validation:
            validation_status = _read_json(Path(raw_path)).get("validation_status", "")
            if validation_status != "passed":
                failure = "upstream validation not passed"
        rows.append(
            {
                "input_group": group,
                "input_name": name,
                "input_path": relpath(path),
                "status": "present" if exists else "missing",
                "validation_status": validation_status,
                "failure_reason": failure,
            }
        )
    return pd.DataFrame(rows)


def _blocked_decision_from_readiness(readiness: pd.DataFrame) -> str | None:
    if readiness["status"].eq("missing").any():
        return "blocked_missing_required_input"
    failed_validation = readiness["validation_status"].ne("") & readiness["validation_status"].ne("passed")
    if failed_validation.any():
        return "blocked_upstream_validation_failed"
    return None


def _load_coverage_panel(config: dict[str, Any], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    panel = pd.read_parquet(topic_path(Path(config["upstream_coverage"]["eligible_day_density_panel"])))
    required = {
        "instrument_id",
        "trade_date",
        "split",
        "is_r01_pit_executable_eligible",
        "suspended_or_dirty_bar",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "source_price_hash",
        "source_calendar_hash",
    }
    missing = sorted(required - set(panel.columns))
    if missing:
        raise RuntimeError(f"coverage panel missing columns: {missing}")
    cal_map = {pd.Timestamp(date).normalize(): idx for idx, date in enumerate(calendar)}
    out = panel.copy()
    out["instrument_id"] = out["instrument_id"].astype(str).str.upper()
    out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.normalize()
    out["calendar_index"] = out["trade_date"].map(cal_map)
    if out["calendar_index"].isna().any():
        raise RuntimeError("coverage panel contains trade_date outside local calendar")
    out["calendar_index"] = out["calendar_index"].astype(int)
    out["is_r01_pit_executable_eligible"] = _as_bool_series(out["is_r01_pit_executable_eligible"])
    out["suspended_or_dirty_bar"] = _as_bool_series(out["suspended_or_dirty_bar"])
    for col in ["open", "high", "low", "close", "volume", "money"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)
    out["clean_eligible"] = out["is_r01_pit_executable_eligible"] & ~out["suspended_or_dirty_bar"] & (out["close"] > 0)
    group = out.groupby("instrument_id", sort=False)
    out["prior_close"] = group["close"].shift(1)
    out["prior_suspended_or_dirty_bar"] = group["suspended_or_dirty_bar"].shift(1).fillna(True).astype(bool)
    out["prior_calendar_index"] = group["calendar_index"].shift(1)
    out["prior_is_immediate"] = out["calendar_index"].eq(out["prior_calendar_index"] + 1)
    valid_return = out["clean_eligible"] & out["prior_is_immediate"] & ~out["prior_suspended_or_dirty_bar"] & (out["prior_close"] > 0)
    out["daily_return"] = np.where(valid_return, out["close"] / out["prior_close"] - 1.0, np.nan)

    clean_price = ~out["suspended_or_dirty_bar"] & (out["close"] > 0)
    out["_clean_close_for_ma60"] = out["close"].where(clean_price)
    out["_clean_count60"] = group["_clean_close_for_ma60"].transform(lambda s: s.rolling(60, min_periods=60).count())
    out["_ma60_raw"] = group["_clean_close_for_ma60"].transform(lambda s: s.rolling(60, min_periods=60).mean())
    out["_calendar_lag59"] = group["calendar_index"].shift(59)
    out["ma60_complete"] = out["_clean_count60"].eq(60) & out["calendar_index"].eq(out["_calendar_lag59"] + 59)
    out["ma60"] = out["_ma60_raw"].where(out["ma60_complete"])
    out["stock_ret_60d"] = np.nan
    lag_close = group["close"].shift(60)
    lag_suspended = group["suspended_or_dirty_bar"].shift(60).fillna(True).astype(bool)
    lag_calendar = group["calendar_index"].shift(60)
    stock_ret_valid = out["clean_eligible"] & out["calendar_index"].eq(lag_calendar + 60) & ~lag_suspended & (lag_close > 0)
    out.loc[stock_ret_valid, "stock_ret_60d"] = out.loc[stock_ret_valid, "close"] / lag_close.loc[stock_ret_valid] - 1.0
    out["stock_rps_60d"] = out.groupby("trade_date", group_keys=False)["stock_ret_60d"].apply(_percentile_rank)
    return out


def _percentile_rank(series: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=series.index, dtype=float)
    valid = pd.to_numeric(series, errors="coerce").dropna()
    n = len(valid)
    if n < 2:
        return out
    ranks = valid.rank(method="average", ascending=True)
    out.loc[valid.index] = (ranks - 1.0) / (n - 1.0)
    return out


def _rolling_product_return(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).apply(
        lambda values: float(np.prod(1.0 + values) - 1.0) if np.isfinite(values).all() else np.nan,
        raw=True,
    )


def _build_market_panel(stock: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, float]:
    market_cfg = config["market"]
    eligible = stock["clean_eligible"]
    grouped = stock.groupby("trade_date", sort=True)
    rows: list[dict[str, Any]] = []
    for trade_date, part in grouped:
        elig = part.loc[part["clean_eligible"]]
        valid_returns = pd.to_numeric(elig["daily_return"], errors="coerce").dropna()
        calendar_hashes = sorted(part["source_calendar_hash"].dropna().astype(str).unique())
        if len(calendar_hashes) > 1:
            raise RuntimeError(f"multiple source_calendar_hash values on {trade_date.date()}: {calendar_hashes[:5]}")
        price_hashes = sorted(elig["source_price_hash"].dropna().astype(str).unique())
        eligible_count = int(len(elig))
        valid_count = int(len(valid_returns))
        market_return = float(valid_returns.mean()) if eligible_count >= market_cfg["min_eligible_count"] and valid_count >= market_cfg["min_return_valid_count"] else np.nan
        rows.append(
            {
                "trade_date": trade_date,
                "split": str(part["split"].dropna().iloc[0]) if len(part) else "",
                "eligible_count": eligible_count,
                "market_return_valid_count": valid_count,
                "market_return_missing_count": int(max(eligible_count - valid_count, 0)),
                "market_proxy_complete_flag": bool(np.isfinite(market_return)),
                "market_proxy_return": market_return,
                "source_price_hash_aggregate": _hash_text("|".join(price_hashes)),
                "source_calendar_hash": calendar_hashes[0] if calendar_hashes else "",
            }
        )
    market = pd.DataFrame(rows).sort_values("trade_date").reset_index(drop=True)
    index_values: list[float] = []
    last_index = 1.0
    for value in market["market_proxy_return"]:
        if np.isfinite(value):
            last_index *= 1.0 + float(value)
            index_values.append(last_index)
        else:
            index_values.append(np.nan)
    market["market_proxy_index"] = index_values
    for window in [20, 60, 120, 252]:
        market[f"market_ret_{window}d"] = _rolling_product_return(market["market_proxy_return"], window)
    complete_252 = market["market_proxy_return"].rolling(252, min_periods=252).count().eq(252)
    market["market_drawdown_252d"] = 1.0 - market["market_proxy_index"] / market["market_proxy_index"].rolling(252, min_periods=252).max()
    market.loc[~complete_252, "market_drawdown_252d"] = np.nan
    complete_60 = market["market_proxy_return"].rolling(60, min_periods=60).count().eq(60)
    market["market_realized_vol_60d"] = market["market_proxy_return"].rolling(60, min_periods=60).std(ddof=0) * math.sqrt(252)
    market.loc[~complete_60, "market_realized_vol_60d"] = np.nan

    breadth_source = stock.loc[eligible & stock["ma60_complete"], ["trade_date", "close", "ma60"]].copy()
    breadth = breadth_source.groupby("trade_date").agg(
        market_breadth_denominator=("close", "size"),
        market_breadth_above_ma60=("close", lambda s: int((s > breadth_source.loc[s.index, "ma60"]).sum())),
    )
    breadth["market_breadth_ma60"] = breadth["market_breadth_above_ma60"] / breadth["market_breadth_denominator"]
    market = market.merge(breadth[["market_breadth_denominator", "market_breadth_ma60"]], left_on="trade_date", right_index=True, how="left")
    market["market_breadth_denominator"] = market["market_breadth_denominator"].fillna(0).astype(int)
    market.loc[market["market_breadth_denominator"] < market_cfg["min_return_valid_count"], "market_breadth_ma60"] = np.nan
    must_have = [
        "market_ret_20d",
        "market_ret_60d",
        "market_ret_120d",
        "market_ret_252d",
        "market_drawdown_252d",
        "market_realized_vol_60d",
        "market_breadth_ma60",
    ]
    market["market_feature_complete_flag"] = market[must_have].notna().all(axis=1)
    market["market_feature_incomplete_reason"] = np.where(market["market_feature_complete_flag"], "", "missing_required_market_feature")
    train_vol = pd.to_numeric(market.loc[market["split"].eq("train"), "market_realized_vol_60d"], errors="coerce").dropna()
    q67 = float(train_vol.quantile(float(market_cfg.get("realized_vol_quantile", 0.67)))) if len(train_vol) else np.nan
    market["train_q67_market_realized_vol_60d"] = q67
    market["market_regime_bucket"] = [
        _market_bucket(row, q67) for row in market.itertuples(index=False)
    ]
    return market, q67


def _market_bucket(row: Any, q67_vol: float) -> str:
    if not bool(row.market_feature_complete_flag) or not np.isfinite(q67_vol):
        return "missing_market_regime"
    if row.market_ret_60d <= -0.10 and row.market_ret_20d >= 0.05 and row.market_realized_vol_60d >= q67_vol:
        return "post_drawdown_rebound_hypothesis"
    if row.market_drawdown_252d >= 0.25 and row.market_realized_vol_60d >= q67_vol:
        return "panic_high_vol"
    if row.market_ret_120d >= 0.0 and row.market_drawdown_252d < 0.10:
        return "normal_uptrend"
    if row.market_ret_120d >= -0.05 and row.market_drawdown_252d < 0.25:
        return "normal_range"
    return "downtrend_low_breadth"


def _load_membership(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(topic_path(path))
    required = {"date", "instrument", "industry_target_key", "industry_ts_code", "industry_name", "source"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise RuntimeError(f"industry membership missing columns: {missing}")
    raw = raw.copy()
    raw["date"] = pd.to_datetime(raw["date"]).dt.normalize()
    raw["instrument"] = raw["instrument"].astype(str).str.upper()
    raw = raw.sort_values(["instrument", "date", "source", "industry_target_key", "industry_ts_code"]).reset_index(drop=True)
    dup_mask = raw.duplicated(["instrument", "date"], keep=False)
    audit = (
        raw.loc[dup_mask]
        .groupby(["instrument", "date"], as_index=False)
        .size()
        .rename(columns={"size": "duplicate_membership_rows"})
    )
    deduped = raw.drop_duplicates(["instrument", "date"], keep="first").reset_index(drop=True)
    return deduped, audit


def _asof_join_membership(events: pd.DataFrame, membership: pd.DataFrame, instrument_col: str, date_col: str) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    frames: list[pd.DataFrame] = []
    mem_groups = {instrument: frame.sort_values("date") for instrument, frame in membership.groupby("instrument", sort=False)}
    for instrument, left in events.groupby(instrument_col, sort=False):
        left_sorted = left.sort_values(date_col).copy()
        mem = mem_groups.get(str(instrument).upper())
        if mem is None or mem.empty:
            for col in ["industry_target_key", "industry_ts_code", "industry_name", "source", "date"]:
                left_sorted[f"membership_{col}" if col == "date" else col] = pd.NA
            frames.append(left_sorted)
            continue
        merged = pd.merge_asof(
            left_sorted,
            mem.rename(columns={"date": "membership_date"}),
            left_on=date_col,
            right_on="membership_date",
            direction="backward",
        )
        frames.append(merged)
    return pd.concat(frames, ignore_index=True).sort_index()


def _build_industry_panel(stock: pd.DataFrame, membership: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    ind_cfg = config["industry"]
    stock_for_join = stock[["instrument_id", "trade_date", "clean_eligible", "daily_return", "close", "ma60", "ma60_complete"]].copy()
    stock_joined = _asof_join_membership(stock_for_join, membership, "instrument_id", "trade_date")
    stock_joined["has_industry_membership"] = stock_joined["industry_target_key"].notna()
    eligible = stock_joined["clean_eligible"] & stock_joined["has_industry_membership"]
    proxy_source = stock_joined.loc[eligible].copy()
    daily = (
        proxy_source.groupby(["trade_date", "industry_target_key"], as_index=False)
        .agg(
            industry_member_count=("instrument_id", "size"),
            industry_return_valid_count=("daily_return", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
            industry_proxy_return_raw=("daily_return", "mean"),
            industry_ts_code=("industry_ts_code", "first"),
            industry_name=("industry_name", "first"),
            industry_membership_source=("source", "first"),
        )
    )
    daily["industry_return_missing_count"] = daily["industry_member_count"] - daily["industry_return_valid_count"]
    complete = (daily["industry_member_count"] >= ind_cfg["min_member_count"]) & (daily["industry_return_valid_count"] >= ind_cfg["min_return_valid_count"])
    daily["industry_proxy_return"] = daily["industry_proxy_return_raw"].where(complete)
    daily["industry_proxy_complete_flag"] = daily["industry_proxy_return"].notna()
    dates = pd.DataFrame({"trade_date": sorted(stock["trade_date"].unique())})
    industries = daily[["industry_target_key", "industry_ts_code", "industry_name", "industry_membership_source"]].drop_duplicates("industry_target_key")
    grid = dates.merge(industries, how="cross")
    industry = grid.merge(
        daily.drop(columns=["industry_ts_code", "industry_name", "industry_membership_source"]),
        on=["trade_date", "industry_target_key"],
        how="left",
    )
    for col in ["industry_member_count", "industry_return_valid_count", "industry_return_missing_count"]:
        industry[col] = industry[col].fillna(0).astype(int)
    industry["industry_proxy_complete_flag"] = industry["industry_proxy_return"].notna()
    industry = industry.sort_values(["industry_target_key", "trade_date"]).reset_index(drop=True)
    industry["industry_proxy_index"] = np.nan
    for _, idx in industry.groupby("industry_target_key", sort=False).groups.items():
        last = 1.0
        values: list[float] = []
        for ret in industry.loc[idx, "industry_proxy_return"]:
            if np.isfinite(ret):
                last *= 1.0 + float(ret)
                values.append(last)
            else:
                values.append(np.nan)
        industry.loc[idx, "industry_proxy_index"] = values
    for window in [20, 60]:
        industry[f"industry_ret_{window}d"] = industry.groupby("industry_target_key", group_keys=False)["industry_proxy_return"].apply(
            lambda s, w=window: _rolling_product_return(s, w)
        )
    industry["thin_industry_flag"] = industry["industry_member_count"] < ind_cfg["min_member_count"]
    rank_source = industry.loc[~industry["thin_industry_flag"]].copy()
    industry["industry_rps_60d"] = np.nan
    industry.loc[rank_source.index, "industry_rps_60d"] = rank_source.groupby("trade_date", group_keys=False)["industry_ret_60d"].apply(_percentile_rank)

    breadth_source = stock_joined.loc[eligible & stock_joined["ma60_complete"]].copy()
    breadth = (
        breadth_source.groupby(["trade_date", "industry_target_key"], as_index=False)
        .agg(
            industry_breadth_denominator=("instrument_id", "size"),
            industry_breadth_above_ma60=("close", lambda s: int((s > breadth_source.loc[s.index, "ma60"]).sum())),
        )
    )
    breadth["industry_breadth_ma60"] = breadth["industry_breadth_above_ma60"] / breadth["industry_breadth_denominator"]
    industry = industry.merge(breadth[["trade_date", "industry_target_key", "industry_breadth_denominator", "industry_breadth_ma60"]], on=["trade_date", "industry_target_key"], how="left")
    industry["industry_breadth_denominator"] = industry["industry_breadth_denominator"].fillna(0).astype(int)
    industry.loc[industry["industry_breadth_denominator"] < ind_cfg["min_return_valid_count"], "industry_breadth_ma60"] = np.nan
    must_have = ["industry_ret_20d", "industry_ret_60d", "industry_rps_60d", "industry_breadth_ma60"]
    industry["industry_feature_complete_flag"] = industry[must_have].notna().all(axis=1) & ~industry["thin_industry_flag"]
    industry["industry_feature_incomplete_reason"] = np.where(
        industry["thin_industry_flag"],
        "thin_industry",
        np.where(industry["industry_feature_complete_flag"], "", "missing_required_industry_feature"),
    )
    industry["industry_regime_bucket"] = [_industry_bucket(row) for row in industry.itertuples(index=False)]
    return industry, stock_joined


def _industry_bucket(row: Any) -> str:
    if int(row.industry_member_count) < 10:
        return "thin_industry"
    if not bool(row.industry_feature_complete_flag):
        return "missing_industry"
    if row.industry_ret_60d < 0 and row.industry_ret_20d >= 0.05:
        return "industry_rebound_from_drawdown"
    if row.industry_rps_60d >= 0.70 and row.industry_breadth_ma60 >= 0.60:
        return "industry_leading"
    if row.industry_rps_60d <= 0.30 or row.industry_breadth_ma60 <= 0.40:
        return "industry_lagging"
    return "industry_neutral"


def _build_candidate_panel(config: dict[str, Any], date_split: dict[pd.Timestamp, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    path = topic_path(Path(config["upstream_path_query"]["single_momentum_episode_audit"]))
    episode = pd.read_csv(path)
    required = {
        "signal_id",
        "family_id",
        "instrument_id",
        "signal_date",
        "split",
        "episode_id",
        "episode_start_signal_date",
        "episode_end_signal_date",
        "episode_trigger_count",
        "episode_entry_date",
        "episode_entry_price",
        "episode_entry_valid",
        "entry_date",
        "entry_price",
        "entry_valid",
        "path_complete_120d",
        "first_plus10_hit_flag",
        "first_plus10_offset",
        "first_minus5_hit_flag",
        "first_minus5_offset",
        "race_plus10_minus5_status",
        "hit_plus10_before_minus5",
        "path_quality_flag",
        "early_failure_flag",
        "max_gain_120d",
        "max_drawdown_120d",
        "close_return_t20",
        "close_return_t60",
        "close_return_t120",
    }
    missing = sorted(required - set(episode.columns))
    if missing:
        raise RuntimeError(f"episode audit missing columns: {missing}")
    episode = episode.loc[episode["signal_id"].eq(config["candidate"]["signal_id"])].copy()
    episode["instrument_id"] = episode["instrument_id"].astype(str).str.upper()
    for col in ["signal_date", "episode_start_signal_date", "episode_end_signal_date", "episode_entry_date", "entry_date"]:
        episode[col] = pd.to_datetime(episode[col], errors="coerce").dt.normalize()
    episode = episode.sort_values(["signal_id", "instrument_id", "episode_start_signal_date", "episode_id"]).reset_index(drop=True)
    duplicate_mask = episode.duplicated("episode_id", keep=False)
    duplicate_audit = (
        episode.loc[duplicate_mask]
        .groupby("episode_id", as_index=False)
        .agg(duplicate_row_count=("episode_id", "size"), first_instrument_id=("instrument_id", "first"), first_episode_start_signal_date=("episode_start_signal_date", "first"))
    )
    deduped = episode.drop_duplicates("episode_id", keep="first").copy()
    deduped["r04_candidate_event_id"] = [
        _hash_id(["r04_episode", row.signal_id, row.instrument_id, row.episode_id, _date_str(row.episode_start_signal_date)])
        for row in deduped.itertuples(index=False)
    ]
    deduped["anchor_signal_date"] = deduped["episode_start_signal_date"]
    deduped["entry_execution_date"] = deduped["episode_entry_date"]
    split_start = deduped["episode_start_signal_date"].map(date_split)
    split_entry = deduped["episode_entry_date"].map(date_split)
    same_split = split_start.eq(deduped["split"]) & split_entry.eq(deduped["split"])
    deduped["r04_inclusion_status"] = "included"
    deduped["r04_exclusion_reason"] = ""
    critical_required = [
        "signal_id",
        "family_id",
        "instrument_id",
        "split",
        "episode_id",
        "episode_start_signal_date",
        "episode_entry_date",
        "episode_entry_price",
        "episode_entry_valid",
        "path_complete_120d",
        "race_plus10_minus5_status",
    ]
    missing_required = deduped[critical_required].isna().any(axis=1)
    invalid_entry = ~_as_bool_series(deduped["episode_entry_valid"])
    incomplete = ~_as_bool_series(deduped["path_complete_120d"])
    out_of_scope = ~deduped["split"].isin(SPLITS)
    cross_split = ~same_split
    rules = [
        (missing_required, "excluded_missing_required_field", "missing required candidate field"),
        (out_of_scope, "excluded_out_of_scope_split", "split outside train/validation/robustness"),
        (invalid_entry, "excluded_invalid_episode_entry", "episode_entry_valid is false"),
        (incomplete, "excluded_incomplete_120d_path", "path_complete_120d is false"),
        (cross_split, "excluded_cross_split", "episode start and entry are not inside same split"),
    ]
    for mask, status, reason in rules:
        apply = mask & deduped["r04_inclusion_status"].eq("included")
        deduped.loc[apply, "r04_inclusion_status"] = status
        deduped.loc[apply, "r04_exclusion_reason"] = reason
    deduped["primary_success_flag"] = _primary_success_from_race(deduped["race_plus10_minus5_status"])
    deduped["race_ambiguous_flag"] = deduped["race_plus10_minus5_status"].astype(str).isin(AMBIGUOUS_RACES)
    deduped["metric_denominator_eligible_flag"] = deduped["r04_inclusion_status"].eq("included") & deduped["primary_success_flag"].notna()
    deduped["good_path_flag"] = deduped["path_quality_flag"].astype(str).isin(GOOD_PATH_FLAGS)
    deduped["bad_path_flag"] = deduped["path_quality_flag"].astype(str).isin(BAD_PATH_FLAGS) | _as_bool_series(deduped["early_failure_flag"])
    deduped["max_gain50_proxy"] = pd.to_numeric(deduped["max_gain_120d"], errors="coerce") >= 0.50
    deduped["source_signal_path"] = config["upstream_path_query"]["single_momentum_signal_path"]
    deduped["source_episode_audit_path"] = config["upstream_path_query"]["single_momentum_episode_audit"]
    deduped["source_signal_hash"] = _hash_file(topic_path(Path(config["upstream_path_query"]["single_momentum_signal_path"])))
    keep_cols = [
        "r04_candidate_event_id",
        "signal_id",
        "family_id",
        "episode_id",
        "instrument_id",
        "signal_date",
        "anchor_signal_date",
        "episode_start_signal_date",
        "episode_end_signal_date",
        "episode_trigger_count",
        "split",
        "entry_execution_date",
        "entry_price",
        "episode_entry_valid",
        "path_complete_120d",
        "r04_inclusion_status",
        "r04_exclusion_reason",
        "first_plus10_hit_flag",
        "first_plus10_offset",
        "first_minus5_hit_flag",
        "first_minus5_offset",
        "race_plus10_minus5_status",
        "hit_plus10_before_minus5",
        "primary_success_flag",
        "race_ambiguous_flag",
        "metric_denominator_eligible_flag",
        "path_quality_flag",
        "good_path_flag",
        "bad_path_flag",
        "early_failure_flag",
        "max_gain_120d",
        "max_drawdown_120d",
        "close_return_t20",
        "close_return_t60",
        "close_return_t120",
        "max_gain50_proxy",
        "source_signal_path",
        "source_episode_audit_path",
        "source_signal_hash",
    ]
    return deduped[keep_cols].reset_index(drop=True), duplicate_audit


def _attach_raw_episode(raw: pd.DataFrame, candidate: pd.DataFrame) -> pd.DataFrame:
    episodes = candidate[["signal_id", "instrument_id", "split", "episode_id", "episode_start_signal_date", "episode_end_signal_date", "episode_trigger_count"]].copy()
    raw = raw.copy()
    raw["signal_date"] = pd.to_datetime(raw["signal_date"], errors="coerce").dt.normalize()
    frames: list[pd.DataFrame] = []
    keys = ["signal_id", "instrument_id", "split"]
    for key, part in raw.groupby(keys, sort=False):
        signal_id, instrument_id, split = key
        ep = episodes[
            episodes["signal_id"].eq(signal_id)
            & episodes["instrument_id"].eq(instrument_id)
            & episodes["split"].eq(split)
        ].sort_values("episode_start_signal_date")
        part_sorted = part.sort_values("signal_date")
        if ep.empty:
            merged = part_sorted.copy()
            for col in ["episode_id", "episode_start_signal_date", "episode_end_signal_date", "episode_trigger_count"]:
                merged[col] = pd.NA
        else:
            merged = pd.merge_asof(
                part_sorted,
                ep,
                by=["signal_id", "instrument_id", "split"],
                left_on="signal_date",
                right_on="episode_start_signal_date",
                direction="backward",
            )
            matched = merged["episode_end_signal_date"].notna() & (merged["signal_date"] <= merged["episode_end_signal_date"])
            for col in ["episode_id", "episode_start_signal_date", "episode_end_signal_date", "episode_trigger_count"]:
                merged.loc[~matched, col] = pd.NA
        frames.append(merged)
    return pd.concat(frames, ignore_index=True) if frames else raw


def _build_raw_panel(config: dict[str, Any], candidate: pd.DataFrame) -> pd.DataFrame:
    path = topic_path(Path(config["upstream_path_query"]["single_momentum_signal_path"]))
    raw = pd.read_csv(path)
    raw = raw.loc[raw["signal_id"].eq(config["candidate"]["signal_id"])].copy()
    raw["instrument_id"] = raw["instrument_id"].astype(str).str.upper()
    raw["signal_date"] = pd.to_datetime(raw["signal_date"], errors="coerce").dt.normalize()
    raw["entry_date"] = pd.to_datetime(raw["entry_date"], errors="coerce").dt.normalize()
    raw = _attach_raw_episode(raw, candidate)
    raw["raw_action_time_event_id"] = [
        _hash_id(["r04_raw", row.signal_id, row.instrument_id, _date_str(row.signal_date)])
        for row in raw.itertuples(index=False)
    ]
    raw["raw_is_episode_first_trigger"] = raw["signal_date"].eq(raw["episode_start_signal_date"])
    raw["source_signal_path"] = config["upstream_path_query"]["single_momentum_signal_path"]
    raw["source_signal_hash"] = _hash_file(path)
    keep_cols = [
        "raw_action_time_event_id",
        "signal_id",
        "family_id",
        "instrument_id",
        "signal_date",
        "split",
        "entry_date",
        "entry_price",
        "entry_valid",
        "path_complete_120d",
        "episode_id",
        "episode_start_signal_date",
        "episode_trigger_count",
        "raw_is_episode_first_trigger",
        "first_plus10_hit_flag",
        "first_plus10_offset",
        "first_minus5_hit_flag",
        "first_minus5_offset",
        "race_plus10_minus5_status",
        "hit_plus10_before_minus5",
        "path_quality_flag",
        "early_failure_flag",
        "max_gain_120d",
        "max_drawdown_120d",
        "source_signal_path",
        "source_signal_hash",
    ]
    for col in keep_cols:
        if col not in raw.columns:
            raw[col] = pd.NA
    return raw[keep_cols].sort_values(["instrument_id", "signal_date"]).reset_index(drop=True)


def _build_arrays(stock: pd.DataFrame) -> dict[str, dict[str, Any]]:
    arrays: dict[str, dict[str, Any]] = {}
    cols = ["trade_date", "split", "open", "high", "low", "close", "calendar_index"]
    for instrument, frame in stock.sort_values(["instrument_id", "trade_date"]).groupby("instrument_id", sort=False):
        data = {col: frame[col].to_numpy() for col in cols}
        data["date_pos"] = {pd.Timestamp(value).normalize(): idx for idx, value in enumerate(frame["trade_date"])}
        arrays[str(instrument)] = data
    return arrays


def _first_threshold_hit(values: np.ndarray, positions: np.ndarray, entry_pos: int, entry_price: float, threshold: float, direction: str, dates: np.ndarray) -> dict[str, Any]:
    returns = values / entry_price - 1.0
    if direction == "up":
        hits = np.flatnonzero(np.isfinite(returns) & (returns >= threshold))
    else:
        hits = np.flatnonzero(np.isfinite(returns) & (returns <= threshold))
    if len(hits) == 0:
        return {"hit": False, "offset": np.nan, "date": pd.NA, "return": np.nan, "pos": None}
    idx = int(hits[0])
    pos = int(positions[idx])
    return {
        "hit": True,
        "offset": int(pos - entry_pos),
        "date": pd.Timestamp(dates[pos]).date().isoformat(),
        "return": float(returns[idx]),
        "pos": pos,
    }


def _race_status(up: dict[str, Any], down: dict[str, Any], path_complete: bool) -> str:
    if up["hit"] and down["hit"]:
        if int(up["offset"]) < int(down["offset"]):
            return "upside_first"
        if int(up["offset"]) > int(down["offset"]):
            return "downside_first"
        return "same_offset"
    if up["hit"] and not down["hit"]:
        return "upside_only_complete" if path_complete else "censored_incomplete"
    if down["hit"] and not up["hit"]:
        return "downside_only_complete" if path_complete else "censored_incomplete"
    return "neither_hit_complete" if path_complete else "censored_incomplete"


def _race_bool(status: str) -> Any:
    if status in SUCCESS_RACES:
        return True
    if status in FAILURE_RACES:
        return False
    return pd.NA


def _empty_path() -> dict[str, Any]:
    return {
        "entry_date": pd.NA,
        "entry_price": np.nan,
        "entry_valid": False,
        "path_complete_120d": False,
        "path_incomplete_reason": "",
        "first_plus10_hit_flag": False,
        "first_plus10_offset": np.nan,
        "first_minus5_hit_flag": False,
        "first_minus5_offset": np.nan,
        "race_plus10_minus5_status": "censored_incomplete",
        "hit_plus10_before_minus5": pd.NA,
        "path_quality_flag": "incomplete",
        "early_failure_flag": pd.NA,
        "max_gain_120d": np.nan,
        "max_drawdown_120d": np.nan,
        "close_return_t20": np.nan,
        "close_return_t60": np.nan,
        "close_return_t120": np.nan,
    }


def _compute_path_from_entry(arrays: dict[str, Any], entry_pos: int, signal_split: str, horizon: int) -> dict[str, Any]:
    payload = _empty_path()
    dates = arrays["trade_date"]
    split = arrays["split"]
    high = arrays["high"].astype(float)
    low = arrays["low"].astype(float)
    close = arrays["close"].astype(float)
    open_ = arrays["open"].astype(float)
    n = len(dates)
    if entry_pos < 0 or entry_pos >= n or not np.isfinite(open_[entry_pos]) or open_[entry_pos] <= 0:
        return payload
    entry_price = float(open_[entry_pos])
    available = max(0, min(horizon, n - entry_pos - 1))
    end_pos = entry_pos + available
    path_complete = bool(available >= horizon and str(split[entry_pos + horizon]) == signal_split)
    if available < horizon:
        incomplete_reason = "insufficient_forward_trading_days"
    elif not path_complete:
        incomplete_reason = "split_boundary"
    else:
        incomplete_reason = ""
    metric_end = entry_pos + min(available, horizon)
    positions = np.arange(entry_pos, metric_end + 1, dtype=int)
    payload.update(
        {
            "entry_date": pd.Timestamp(dates[entry_pos]).date().isoformat(),
            "entry_price": entry_price,
            "entry_valid": True,
            "path_complete_120d": path_complete,
            "path_incomplete_reason": incomplete_reason,
        }
    )
    if len(positions) == 0:
        return payload

    highs = high[positions]
    lows = low[positions]
    closes = close[positions]
    plus10 = _first_threshold_hit(highs, positions, entry_pos, entry_price, 0.10, "up", dates)
    plus20 = _first_threshold_hit(highs, positions, entry_pos, entry_price, 0.20, "up", dates)
    minus5 = _first_threshold_hit(lows, positions, entry_pos, entry_price, -0.05, "down", dates)
    race = _race_status(plus10, minus5, path_complete)
    payload.update(
        {
            "first_plus10_hit_flag": bool(plus10["hit"]),
            "first_plus10_offset": plus10["offset"],
            "first_minus5_hit_flag": bool(minus5["hit"]),
            "first_minus5_offset": minus5["offset"],
            "race_plus10_minus5_status": race,
            "hit_plus10_before_minus5": _race_bool(race),
        }
    )
    if np.isfinite(highs).any():
        payload["max_gain_120d"] = float(np.nanmax(highs / entry_price - 1.0))
    peak_price = entry_price
    best_dd = np.inf
    best_dd_end_offset = np.nan
    for pos in positions:
        if np.isfinite(low[pos]) and peak_price > 0:
            dd = float(low[pos] / peak_price - 1.0)
            if dd < best_dd:
                best_dd = dd
                best_dd_end_offset = int(pos - entry_pos)
        if np.isfinite(high[pos]) and high[pos] > peak_price:
            peak_price = float(high[pos])
    if np.isfinite(best_dd):
        payload["max_drawdown_120d"] = float(best_dd)
    for offset in [20, 60, 120]:
        pos = entry_pos + offset
        if pos <= end_pos and pos < n and str(split[pos]) == signal_split and np.isfinite(close[pos]):
            payload[f"close_return_t{offset}"] = float(close[pos] / entry_price - 1.0)

    plus20_eval_end = int(plus20["pos"]) if plus20["hit"] else metric_end
    max_drawdown_before_plus20 = np.nan
    if plus20_eval_end >= entry_pos:
        local_peak = entry_price
        best = np.inf
        for pos in np.arange(entry_pos, plus20_eval_end + 1, dtype=int):
            if np.isfinite(low[pos]) and local_peak > 0:
                best = min(best, float(low[pos] / local_peak - 1.0))
            if np.isfinite(high[pos]) and high[pos] > local_peak:
                local_peak = float(high[pos])
        if np.isfinite(best):
            max_drawdown_before_plus20 = float(best)
    missing_quality_input = (
        (not path_complete)
        or pd.isna(payload["hit_plus10_before_minus5"])
        or not np.isfinite(payload["close_return_t20"])
        or not np.isfinite(payload["max_gain_120d"])
        or not np.isfinite(payload["close_return_t120"])
        or not np.isfinite(payload["max_drawdown_120d"])
        or not np.isfinite(max_drawdown_before_plus20)
        or pd.isna(best_dd_end_offset)
    )
    early_failure = bool(payload["first_minus5_hit_flag"] and np.isfinite(payload["first_minus5_offset"]) and float(payload["first_minus5_offset"]) <= 10)
    tradable_continuation = bool(payload["hit_plus10_before_minus5"] is True and np.isfinite(payload["close_return_t20"]) and payload["close_return_t20"] >= 0)
    transient_spike = bool(np.isfinite(payload["max_gain_120d"]) and payload["max_gain_120d"] >= 0.20 and np.isfinite(payload["close_return_t120"]) and payload["close_return_t120"] < 0)
    severe_drawdown = bool(np.isfinite(payload["max_drawdown_120d"]) and payload["max_drawdown_120d"] <= -0.20)
    whipsaw = (
        bool(
            payload["first_plus10_hit_flag"]
            and payload["first_minus5_hit_flag"]
            and float(payload["first_plus10_offset"]) < float(payload["first_minus5_offset"])
            and float(payload["first_minus5_offset"]) <= float(payload["first_plus10_offset"]) + 20
        )
        if not (pd.isna(payload["first_plus10_offset"]) or pd.isna(payload["first_minus5_offset"]))
        else False
    )
    clean_continuation = bool(
        payload["hit_plus10_before_minus5"] is True
        and np.isfinite(payload["close_return_t20"])
        and payload["close_return_t20"] >= 0
        and np.isfinite(max_drawdown_before_plus20)
        and max_drawdown_before_plus20 > -0.10
    )
    late_drawdown = (
        bool(
            payload["first_plus10_hit_flag"]
            and np.isfinite(payload["max_drawdown_120d"])
            and payload["max_drawdown_120d"] <= -0.20
            and np.isfinite(best_dd_end_offset)
            and float(best_dd_end_offset) > float(payload["first_plus10_offset"])
        )
        if not pd.isna(payload["first_plus10_offset"])
        else False
    )
    if missing_quality_input:
        quality = "incomplete"
    elif early_failure:
        quality = "early_failure"
    elif clean_continuation:
        quality = "clean_continuation"
    elif whipsaw:
        quality = "whipsaw_after_profit"
    elif tradable_continuation:
        quality = "tradable_continuation"
    elif transient_spike:
        quality = "transient_spike"
    elif late_drawdown:
        quality = "late_drawdown"
    elif severe_drawdown:
        quality = "severe_drawdown"
    else:
        quality = "mixed"
    payload["path_quality_flag"] = quality
    payload["early_failure_flag"] = early_failure
    return payload


def _compute_background_panel(stock: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    horizon = int(config["candidate"]["horizon_trading_days"])
    base = stock.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True).copy()
    group = base.groupby("instrument_id", sort=False)
    base["next_trade_date"] = group["trade_date"].shift(-1)
    base["next_calendar_index"] = group["calendar_index"].shift(-1)
    base["next_split"] = group["split"].shift(-1)
    base["next_open"] = group["open"].shift(-1)
    base["next_eligible"] = group["is_r01_pit_executable_eligible"].shift(-1).fillna(False).astype(bool)
    base["next_suspended_or_dirty_bar"] = group["suspended_or_dirty_bar"].shift(-1).fillna(True).astype(bool)
    base["background_entry_valid"] = (
        base["next_calendar_index"].eq(base["calendar_index"] + 1)
        & base["next_split"].eq(base["split"])
        & base["next_eligible"]
        & ~base["next_suspended_or_dirty_bar"]
        & (base["next_open"] > 0)
    )
    arrays = _build_arrays(base)
    path_by_index: dict[int, dict[str, Any]] = {}
    print(f"computing background path labels for {int(base['background_entry_valid'].sum())} immediate next-open rows", flush=True)
    for instrument, idx in base.groupby("instrument_id", sort=False).groups.items():
        arrays_i = arrays[str(instrument)]
        idx_list = list(idx)
        local_pos = {global_idx: pos for pos, global_idx in enumerate(idx_list)}
        instrument_rows = base.loc[idx]
        valid_idx = instrument_rows.loc[instrument_rows["background_entry_valid"]].index.tolist()
        for global_idx in valid_idx:
            signal_pos = local_pos[global_idx]
            path_by_index[global_idx] = _compute_path_from_entry(arrays_i, signal_pos + 1, str(base.at[global_idx, "split"]), horizon)
    metrics = pd.DataFrame.from_dict(path_by_index, orient="index")
    background = base[
        [
            "instrument_id",
            "trade_date",
            "split",
            "is_r01_pit_executable_eligible",
            "suspended_or_dirty_bar",
            "close",
            "source_price_hash",
            "source_calendar_hash",
            "calendar_index",
            "background_entry_valid",
            "next_trade_date",
            "next_open",
            "next_split",
            "next_calendar_index",
        ]
    ].copy()
    background = background.join(metrics, how="left")
    background["background_event_id"] = [
        _hash_id(["r04_background", row.instrument_id, _date_str(row.trade_date)])
        for row in background.itertuples(index=False)
    ]
    background["background_signal_date"] = background["trade_date"]
    background["anchor_signal_date"] = background["trade_date"]
    background["background_entry_date"] = pd.to_datetime(background["entry_date"], errors="coerce").dt.normalize()
    background["background_entry_price"] = background["entry_price"]
    background["background_path_complete_120d"] = _as_bool_series(background["path_complete_120d"].fillna(False))
    background["background_inclusion_status"] = "included"
    background["background_exclusion_reason"] = ""
    out_of_scope = ~background["split"].isin(SPLITS)
    not_exec = ~background["is_r01_pit_executable_eligible"].astype(bool)
    suspended = background["suspended_or_dirty_bar"].astype(bool)
    nonpositive = pd.to_numeric(background["close"], errors="coerce") <= 0
    missing_close = pd.to_numeric(background["close"], errors="coerce").isna()
    cross_split = background["next_calendar_index"].eq(background["calendar_index"] + 1) if "calendar_index" in background else pd.Series(False, index=background.index)
    cross_split = background["next_trade_date"].notna() & ~background["next_split"].eq(background["split"])
    invalid_next = ~background["background_entry_valid"].astype(bool)
    incomplete = background["background_entry_valid"].astype(bool) & ~background["background_path_complete_120d"].astype(bool)
    split_boundary_path = incomplete & background["path_incomplete_reason"].eq("split_boundary")
    rules = [
        (missing_close, "excluded_missing_required_field", "missing close field"),
        (out_of_scope, "excluded_out_of_scope_split", "split outside train/validation/robustness"),
        (not_exec, "excluded_not_pit_executable", "is_r01_pit_executable_eligible is false"),
        (suspended, "excluded_suspended_or_dirty_bar", "suspended_or_dirty_bar is true"),
        (nonpositive, "excluded_nonpositive_close", "close <= 0"),
        (cross_split, "excluded_cross_split", "immediate next row crosses split"),
        (invalid_next, "excluded_invalid_next_open", "immediate next open is not executable"),
        (split_boundary_path, "excluded_cross_split", "120D path crosses split"),
        (incomplete, "excluded_incomplete_120d_path", "120D path is incomplete"),
    ]
    for mask, status, reason in rules:
        apply = mask & background["background_inclusion_status"].eq("included")
        background.loc[apply, "background_inclusion_status"] = status
        background.loc[apply, "background_exclusion_reason"] = reason
    background["background_first_plus10_hit_flag"] = background["first_plus10_hit_flag"].fillna(False).astype(bool)
    background["background_first_plus10_offset"] = background["first_plus10_offset"]
    background["background_first_minus5_hit_flag"] = background["first_minus5_hit_flag"].fillna(False).astype(bool)
    background["background_first_minus5_offset"] = background["first_minus5_offset"]
    background["background_race_plus10_minus5_status"] = background["race_plus10_minus5_status"].fillna("censored_incomplete")
    background["background_hit_plus10_before_minus5"] = background["hit_plus10_before_minus5"]
    background["background_primary_success_flag"] = _primary_success_from_race(background["background_race_plus10_minus5_status"])
    background["background_race_ambiguous_flag"] = background["background_race_plus10_minus5_status"].astype(str).isin(AMBIGUOUS_RACES)
    background["background_metric_denominator_eligible_flag"] = background["background_inclusion_status"].eq("included") & background["background_primary_success_flag"].notna()
    background["background_path_quality_flag"] = background["path_quality_flag"].fillna("incomplete")
    background["background_good_path_flag"] = background["background_path_quality_flag"].isin(GOOD_PATH_FLAGS)
    background["background_bad_path_flag"] = background["background_path_quality_flag"].isin(BAD_PATH_FLAGS) | _as_bool_series(background["early_failure_flag"].fillna(False))
    background["background_early_failure_flag"] = _as_bool_series(background["early_failure_flag"].fillna(False))
    background["background_max_gain_120d"] = background["max_gain_120d"]
    background["background_max_drawdown_120d"] = background["max_drawdown_120d"]
    background["background_close_return_t20"] = background["close_return_t20"]
    background["background_close_return_t60"] = background["close_return_t60"]
    background["background_close_return_t120"] = background["close_return_t120"]
    background["background_max_gain50_proxy"] = pd.to_numeric(background["background_max_gain_120d"], errors="coerce") >= 0.50
    keep_cols = [
        "background_event_id",
        "instrument_id",
        "background_signal_date",
        "anchor_signal_date",
        "split",
        "is_r01_pit_executable_eligible",
        "suspended_or_dirty_bar",
        "background_entry_date",
        "background_entry_price",
        "background_entry_valid",
        "background_path_complete_120d",
        "background_inclusion_status",
        "background_exclusion_reason",
        "background_first_plus10_hit_flag",
        "background_first_plus10_offset",
        "background_first_minus5_hit_flag",
        "background_first_minus5_offset",
        "background_race_plus10_minus5_status",
        "background_hit_plus10_before_minus5",
        "background_primary_success_flag",
        "background_race_ambiguous_flag",
        "background_metric_denominator_eligible_flag",
        "background_path_quality_flag",
        "background_good_path_flag",
        "background_bad_path_flag",
        "background_early_failure_flag",
        "background_max_gain_120d",
        "background_max_drawdown_120d",
        "background_close_return_t20",
        "background_close_return_t60",
        "background_close_return_t120",
        "background_max_gain50_proxy",
        "source_price_hash",
        "source_calendar_hash",
    ]
    return background[keep_cols].reset_index(drop=True)


def _reconcile_background_labeler(raw: pd.DataFrame, stock: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    sample_size = int(config["validation"]["path_reconciliation_sample_size_per_split"])
    horizon = int(config["candidate"]["horizon_trading_days"])
    raw_valid = raw.loc[_as_bool_series(raw["entry_valid"])].copy()
    raw_valid["sample_key"] = [
        _hash_id(["r04_path_reconcile", row.signal_id, row.instrument_id, _date_str(row.signal_date)])
        for row in raw_valid.itertuples(index=False)
    ]
    samples = []
    for split, part in raw_valid.groupby("split", sort=False):
        samples.append(part.sort_values("sample_key").head(sample_size))
    sample = pd.concat(samples, ignore_index=True) if samples else raw_valid.iloc[0:0].copy()
    arrays = _build_arrays(stock)
    compare_fields = [
        "entry_date",
        "entry_price",
        "path_complete_120d",
        "first_plus10_offset",
        "first_minus5_offset",
        "race_plus10_minus5_status",
        "hit_plus10_before_minus5",
        "path_quality_flag",
        "early_failure_flag",
        "max_gain_120d",
        "max_drawdown_120d",
    ]
    rows: list[dict[str, Any]] = []
    for row in sample.itertuples(index=False):
        arrays_i = arrays.get(str(row.instrument_id))
        mismatch_fields: list[str] = []
        entry_anchor = pd.Timestamp(row.entry_date).normalize() if not pd.isna(row.entry_date) else pd.NaT
        if arrays_i is None or pd.isna(entry_anchor) or entry_anchor not in arrays_i["date_pos"]:
            mismatch_fields = compare_fields
        else:
            entry_pos = int(arrays_i["date_pos"][entry_anchor])
            calc = _compute_path_from_entry(arrays_i, entry_pos, str(row.split), horizon)
            for field in compare_fields:
                expected = getattr(row, field)
                actual = calc.get(field)
                if field in {"entry_price", "max_gain_120d", "max_drawdown_120d", "first_plus10_offset", "first_minus5_offset"}:
                    exp = _safe_float(expected)
                    act = _safe_float(actual)
                    if not ((pd.isna(exp) and pd.isna(act)) or (np.isfinite(exp) and np.isfinite(act) and abs(exp - act) <= float(config["validation"]["float_tolerance"]))):
                        mismatch_fields.append(field)
                elif field == "entry_date":
                    if _date_str(expected) != _date_str(actual):
                        mismatch_fields.append(field)
                elif field in {"path_complete_120d", "hit_plus10_before_minus5", "early_failure_flag"}:
                    exp_na = pd.isna(expected)
                    act_na = pd.isna(actual)
                    if exp_na and act_na:
                        continue
                    if _to_bool(expected) != _to_bool(actual):
                        mismatch_fields.append(field)
                else:
                    exp = "" if pd.isna(expected) else str(expected)
                    act = "" if pd.isna(actual) else str(actual)
                    if exp != act:
                        mismatch_fields.append(field)
        rows.append(
            {
                "split": row.split,
                "raw_action_time_event_id": row.raw_action_time_event_id,
                "instrument_id": row.instrument_id,
                "signal_date": _date_str(row.signal_date),
                "sample_key": row.sample_key,
                "mismatch_count": len(mismatch_fields),
                "mismatch_fields": "|".join(mismatch_fields),
            }
        )
    detail = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for split in SPLITS:
        part = detail.loc[detail["split"].eq(split)]
        summary_rows.append(
            {
                "split": split,
                "sampled_row_count": int(len(part)),
                "mismatch_row_count": int(part["mismatch_count"].gt(0).sum()) if not part.empty else 0,
                "total_mismatch_count": int(part["mismatch_count"].sum()) if not part.empty else 0,
                "reconciliation_status": "passed" if part.empty or int(part["mismatch_count"].sum()) == 0 else "failed",
            }
        )
    return pd.DataFrame(summary_rows)


def _join_regimes(
    candidate: pd.DataFrame,
    raw: pd.DataFrame,
    background: pd.DataFrame,
    market: pd.DataFrame,
    industry: pd.DataFrame,
    stock: pd.DataFrame,
    membership: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    market_cols = [
        "trade_date",
        "market_regime_bucket",
        "market_feature_complete_flag",
    ]
    stock_cols = ["instrument_id", "trade_date", "stock_ret_60d", "stock_rps_60d"]
    industry_cols = [
        "trade_date",
        "industry_target_key",
        "industry_ts_code",
        "industry_name",
        "industry_member_count",
        "industry_rps_60d",
        "industry_regime_bucket",
        "industry_feature_complete_flag",
    ]

    def enrich(events: pd.DataFrame, scope: str) -> pd.DataFrame:
        if events.empty:
            return events.copy()
        events = events.copy()
        events["anchor_signal_date"] = pd.to_datetime(events["anchor_signal_date"], errors="coerce").dt.normalize()
        events["instrument_id"] = events["instrument_id"].astype(str).str.upper()
        out = events.merge(market[market_cols], left_on="anchor_signal_date", right_on="trade_date", how="left").drop(columns=["trade_date"])
        out = _asof_join_membership(out, membership, "instrument_id", "anchor_signal_date")
        out = out.merge(stock[stock_cols], left_on=["instrument_id", "anchor_signal_date"], right_on=["instrument_id", "trade_date"], how="left").drop(columns=["trade_date"])
        out = out.merge(industry[industry_cols], left_on=["anchor_signal_date", "industry_target_key"], right_on=["trade_date", "industry_target_key"], how="left").drop(columns=["trade_date"])
        out["industry_regime_bucket"] = out["industry_regime_bucket"].fillna("missing_industry")
        out["market_regime_bucket"] = out["market_regime_bucket"].fillna("missing_market_regime")
        out["market_feature_complete_flag"] = out["market_feature_complete_flag"].fillna(False).astype(bool)
        out["industry_feature_complete_flag"] = out["industry_feature_complete_flag"].fillna(False).astype(bool)
        out["stock_rps_minus_industry_rps_60d"] = pd.to_numeric(out["stock_rps_60d"], errors="coerce") - pd.to_numeric(out["industry_rps_60d"], errors="coerce")
        out["denominator_scope"] = scope
        return out

    cand = candidate.copy()
    cand["background_event_id"] = pd.NA
    cand["raw_action_time_event_id"] = pd.NA
    cand["background_signal_date"] = pd.NaT
    cand["signal_date"] = cand["episode_start_signal_date"]
    cand["primary_success_flag_generic"] = cand["primary_success_flag"]
    cand["race_ambiguous_flag_generic"] = cand["race_ambiguous_flag"]
    cand["metric_denominator_eligible_flag_generic"] = cand["metric_denominator_eligible_flag"]
    cand["good_path_flag_generic"] = cand["good_path_flag"]
    cand["bad_path_flag_generic"] = cand["bad_path_flag"]
    cand["early_failure_flag_generic"] = cand["early_failure_flag"]
    cand["max_gain50_proxy_generic"] = cand["max_gain50_proxy"]
    cand["max_gain_120d_generic"] = cand["max_gain_120d"]
    cand["max_drawdown_120d_generic"] = cand["max_drawdown_120d"]
    cand["close_return_t20_generic"] = cand["close_return_t20"]
    cand["close_return_t60_generic"] = cand["close_return_t60"]
    cand["close_return_t120_generic"] = cand["close_return_t120"]
    cand["first_plus10_hit_flag_generic"] = cand["first_plus10_hit_flag"]
    cand["first_minus5_hit_flag_generic"] = cand["first_minus5_hit_flag"]
    cand_join = enrich(cand, "rps_episode_primary")

    bg = background.copy()
    bg["r04_candidate_event_id"] = pd.NA
    bg["raw_action_time_event_id"] = pd.NA
    bg["episode_id"] = pd.NA
    bg["signal_date"] = bg["background_signal_date"]
    bg["primary_success_flag_generic"] = bg["background_primary_success_flag"]
    bg["race_ambiguous_flag_generic"] = bg["background_race_ambiguous_flag"]
    bg["metric_denominator_eligible_flag_generic"] = bg["background_metric_denominator_eligible_flag"]
    bg["good_path_flag_generic"] = bg["background_good_path_flag"]
    bg["bad_path_flag_generic"] = bg["background_bad_path_flag"]
    bg["early_failure_flag_generic"] = bg["background_early_failure_flag"]
    bg["max_gain50_proxy_generic"] = bg["background_max_gain50_proxy"]
    bg["max_gain_120d_generic"] = bg["background_max_gain_120d"]
    bg["max_drawdown_120d_generic"] = bg["background_max_drawdown_120d"]
    bg["close_return_t20_generic"] = bg["background_close_return_t20"]
    bg["close_return_t60_generic"] = bg["background_close_return_t60"]
    bg["close_return_t120_generic"] = bg["background_close_return_t120"]
    bg["first_plus10_hit_flag_generic"] = bg["background_first_plus10_hit_flag"]
    bg["first_minus5_hit_flag_generic"] = bg["background_first_minus5_hit_flag"]
    bg_join = enrich(bg, "background_action_time")

    raw2 = raw.copy()
    raw2["r04_candidate_event_id"] = pd.NA
    raw2["background_event_id"] = pd.NA
    raw2["background_signal_date"] = pd.NaT
    raw2["anchor_signal_date"] = raw2["signal_date"]
    raw2["primary_success_flag_generic"] = _primary_success_from_race(raw2["race_plus10_minus5_status"])
    raw2["race_ambiguous_flag_generic"] = raw2["race_plus10_minus5_status"].astype(str).isin(AMBIGUOUS_RACES)
    raw2["metric_denominator_eligible_flag_generic"] = _as_bool_series(raw2["entry_valid"]) & _as_bool_series(raw2["path_complete_120d"]) & raw2["primary_success_flag_generic"].notna()
    raw2["good_path_flag_generic"] = raw2["path_quality_flag"].astype(str).isin(GOOD_PATH_FLAGS)
    raw2["bad_path_flag_generic"] = raw2["path_quality_flag"].astype(str).isin(BAD_PATH_FLAGS) | _as_bool_series(raw2["early_failure_flag"])
    raw2["early_failure_flag_generic"] = _as_bool_series(raw2["early_failure_flag"])
    raw2["max_gain50_proxy_generic"] = pd.to_numeric(raw2["max_gain_120d"], errors="coerce") >= 0.50
    raw2["max_gain_120d_generic"] = raw2["max_gain_120d"]
    raw2["max_drawdown_120d_generic"] = raw2["max_drawdown_120d"]
    raw2["close_return_t20_generic"] = np.nan
    raw2["close_return_t60_generic"] = np.nan
    raw2["close_return_t120_generic"] = np.nan
    raw2["first_plus10_hit_flag_generic"] = raw2["first_plus10_hit_flag"]
    raw2["first_minus5_hit_flag_generic"] = raw2["first_minus5_hit_flag"]
    raw_join = enrich(raw2, "raw_action_time_audit")

    joined = pd.concat([cand_join, bg_join, raw_join], ignore_index=True, sort=False)
    joined["matching_background_rate"] = np.nan
    joined["matching_background_denominator"] = np.nan
    joined["matching_background_status"] = ""
    rename_map = {
        "primary_success_flag_generic": "primary_success_flag",
        "race_ambiguous_flag_generic": "race_ambiguous_flag",
        "metric_denominator_eligible_flag_generic": "metric_denominator_eligible_flag",
        "good_path_flag_generic": "good_path_flag",
        "bad_path_flag_generic": "bad_path_flag",
        "early_failure_flag_generic": "early_failure_flag",
        "max_gain50_proxy_generic": "max_gain50_proxy",
        "max_gain_120d_generic": "max_gain_120d",
        "max_drawdown_120d_generic": "max_drawdown_120d",
        "close_return_t20_generic": "close_return_t20",
        "close_return_t60_generic": "close_return_t60",
        "close_return_t120_generic": "close_return_t120",
        "first_plus10_hit_flag_generic": "first_plus10_hit_flag",
        "first_minus5_hit_flag_generic": "first_minus5_hit_flag",
    }
    for source_col, target_col in rename_map.items():
        if source_col in joined.columns:
            joined[target_col] = joined[source_col]
    joined = joined.drop(columns=[col for col in rename_map if col in joined.columns])
    required_cols = [
        "r04_candidate_event_id",
        "background_event_id",
        "raw_action_time_event_id",
        "denominator_scope",
        "episode_id",
        "instrument_id",
        "signal_date",
        "background_signal_date",
        "anchor_signal_date",
        "split",
        "market_regime_bucket",
        "industry_target_key",
        "industry_regime_bucket",
        "stock_ret_60d",
        "stock_rps_60d",
        "stock_rps_minus_industry_rps_60d",
        "market_feature_complete_flag",
        "industry_feature_complete_flag",
        "primary_success_flag",
        "race_ambiguous_flag",
        "metric_denominator_eligible_flag",
        "good_path_flag",
        "bad_path_flag",
        "early_failure_flag",
        "max_gain50_proxy",
        "matching_background_rate",
        "matching_background_denominator",
        "matching_background_status",
        "max_gain_120d",
        "max_drawdown_120d",
        "close_return_t20",
        "close_return_t60",
        "close_return_t120",
        "first_plus10_hit_flag",
        "first_minus5_hit_flag",
    ]
    for col in required_cols:
        if col not in joined.columns:
            joined[col] = pd.NA
    membership_audit = _membership_join_audit(joined, duplicate_count=0)
    return joined[required_cols].reset_index(drop=True), membership_audit


def _membership_join_audit(joined: pd.DataFrame, duplicate_count: int) -> pd.DataFrame:
    rows = [{"audit_item": "membership_duplicate_instrument_date_rows", "denominator_scope": "all", "split": "all", "count": int(duplicate_count), "rate": np.nan}]
    for scope in ["rps_episode_primary", "background_action_time", "raw_action_time_audit"]:
        scope_df = joined.loc[joined["denominator_scope"].eq(scope)]
        for split in ALL_SPLITS:
            part = scope_df if split == "all" else scope_df.loc[scope_df["split"].eq(split)]
            count = int(len(part))
            missing = int(part["industry_target_key"].isna().sum()) if count else 0
            rows.append(
                {
                    "audit_item": "missing_industry_membership_after_asof_join",
                    "denominator_scope": scope,
                    "split": split,
                    "count": missing,
                    "rate": _safe_div(missing, count),
                }
            )
    return pd.DataFrame(rows)


def _summary_metrics(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "row_count": 0,
            "path_complete_denominator": 0,
            "metric_denominator": 0,
            "success_count": 0,
            "plus10_before_minus5_rate": np.nan,
            "wilson_lower": np.nan,
            "wilson_upper": np.nan,
            "race_ambiguous_count": 0,
            "race_ambiguous_rate": np.nan,
            "good_path_rate": np.nan,
            "bad_path_rate": np.nan,
            "early_failure_rate": np.nan,
            "first_minus5_hit_rate": np.nan,
            "first_plus10_hit_rate": np.nan,
            "max_gain_120d_p50": np.nan,
            "max_gain_120d_p75": np.nan,
            "max_gain_120d_p90": np.nan,
            "max_drawdown_120d_p50": np.nan,
            "max_drawdown_120d_p75": np.nan,
            "max_drawdown_120d_p90": np.nan,
            "close_return_t20_p50": np.nan,
            "close_return_t60_p50": np.nan,
            "close_return_t120_p50": np.nan,
            "max_gain50_proxy_rate": np.nan,
        }
    metric = df.loc[_as_bool_series(df["metric_denominator_eligible_flag"])].copy()
    path_complete_denominator = int((_as_bool_series(df["metric_denominator_eligible_flag"]) | _as_bool_series(df["race_ambiguous_flag"])).sum())
    denom = int(len(metric))
    success = int(_as_bool_series(metric["primary_success_flag"]).sum()) if denom else 0
    lower, upper = _wilson_interval(success, denom)
    ambiguous = int(_as_bool_series(df["race_ambiguous_flag"]).sum())
    return {
        "row_count": int(len(df)),
        "path_complete_denominator": path_complete_denominator,
        "metric_denominator": denom,
        "success_count": success,
        "plus10_before_minus5_rate": _safe_div(success, denom),
        "wilson_lower": lower,
        "wilson_upper": upper,
        "race_ambiguous_count": ambiguous,
        "race_ambiguous_rate": _safe_div(ambiguous, path_complete_denominator),
        "good_path_rate": _safe_div(int(_as_bool_series(metric["good_path_flag"]).sum()), denom),
        "bad_path_rate": _safe_div(int(_as_bool_series(metric["bad_path_flag"]).sum()), denom),
        "early_failure_rate": _safe_div(int(_as_bool_series(metric["early_failure_flag"]).sum()), denom),
        "first_minus5_hit_rate": _safe_div(int(_as_bool_series(metric.get("first_minus5_hit_flag", pd.Series(index=metric.index))).sum()), denom),
        "first_plus10_hit_rate": _safe_div(int(_as_bool_series(metric.get("first_plus10_hit_flag", pd.Series(index=metric.index))).sum()), denom),
        "max_gain_120d_p50": _quantile(metric["max_gain_120d"], 0.50),
        "max_gain_120d_p75": _quantile(metric["max_gain_120d"], 0.75),
        "max_gain_120d_p90": _quantile(metric["max_gain_120d"], 0.90),
        "max_drawdown_120d_p50": _quantile(metric["max_drawdown_120d"], 0.50),
        "max_drawdown_120d_p75": _quantile(metric["max_drawdown_120d"], 0.75),
        "max_drawdown_120d_p90": _quantile(metric["max_drawdown_120d"], 0.90),
        "close_return_t20_p50": _quantile(metric["close_return_t20"], 0.50),
        "close_return_t60_p50": _quantile(metric["close_return_t60"], 0.50),
        "close_return_t120_p50": _quantile(metric["close_return_t120"], 0.50),
        "max_gain50_proxy_rate": _safe_div(int(_as_bool_series(metric["max_gain50_proxy"]).sum()), denom),
    }


def _split_view(df: pd.DataFrame, split: str) -> pd.DataFrame:
    return df if split == "all" else df.loc[df["split"].eq(split)]


def _min_denominator(config: dict[str, Any], split: str, scope: str) -> int:
    thresholds = config["thresholds"]
    if scope == "background_action_time":
        return int(thresholds["minimum_background_denominator"])
    if split == "train":
        return int(thresholds["minimum_train_denominator"])
    if split == "validation":
        return int(thresholds["minimum_validation_denominator"])
    if split == "robustness":
        return int(thresholds["minimum_robustness_denominator"])
    return 0


def _denom_status(rps_denom: int, bg_denom: int, split: str, config: dict[str, Any], needs_bg: bool = True) -> str:
    rps_ok = rps_denom >= _min_denominator(config, split, "rps_episode_primary") if split != "all" else True
    bg_ok = (bg_denom >= _min_denominator(config, split, "background_action_time")) if needs_bg and split != "all" else True
    if rps_ok and bg_ok:
        return "sufficient"
    if not rps_ok and not bg_ok:
        return "insufficient_both"
    if not rps_ok:
        return "insufficient_rps_denominator"
    return "insufficient_background_denominator"


def _matching_background(rps: pd.DataFrame, background: pd.DataFrame, dims: list[str], split: str, config: dict[str, Any]) -> dict[str, Any]:
    rps_metric = rps.loc[_as_bool_series(rps["metric_denominator_eligible_flag"])].copy()
    bg_metric = background.loc[_as_bool_series(background["metric_denominator_eligible_flag"])].copy()
    if split != "all":
        rps_metric = rps_metric.loc[rps_metric["split"].eq(split)]
        bg_metric = bg_metric.loc[bg_metric["split"].eq(split)]
    if rps_metric.empty:
        return {"matching_background_rate": np.nan, "matching_background_denominator": 0, "matching_background_status": "no_rps_cell_weight"}
    if not dims:
        denom = int(len(bg_metric))
        if denom < _min_denominator(config, split, "background_action_time") and split != "all":
            return {"matching_background_rate": np.nan, "matching_background_denominator": denom, "matching_background_status": "insufficient_background_denominator"}
        rate = _safe_div(int(_as_bool_series(bg_metric["primary_success_flag"]).sum()), denom)
        return {"matching_background_rate": rate, "matching_background_denominator": denom, "matching_background_status": "sufficient"}
    cell_counts = rps_metric.groupby(dims, dropna=False).size().reset_index(name="rps_cell_denominator")
    total = int(cell_counts["rps_cell_denominator"].sum())
    if total <= 0:
        return {"matching_background_rate": np.nan, "matching_background_denominator": 0, "matching_background_status": "no_rps_cell_weight"}
    cell_counts["weight"] = cell_counts["rps_cell_denominator"] / total
    if not np.isclose(float(cell_counts["weight"].sum()), 1.0, atol=1e-12):
        return {"matching_background_rate": np.nan, "matching_background_denominator": 0, "matching_background_status": "invalid_comparator"}
    bg_rates = (
        bg_metric.groupby(dims, dropna=False)
        .agg(
            background_denominator=("primary_success_flag", "size"),
            background_success_count=("primary_success_flag", lambda s: int(_as_bool_series(s).sum())),
        )
        .reset_index()
    )
    bg_rates["background_rate"] = bg_rates["background_success_count"] / bg_rates["background_denominator"]
    merged = cell_counts.merge(bg_rates, on=dims, how="left")
    if merged["background_denominator"].isna().any():
        return {"matching_background_rate": np.nan, "matching_background_denominator": int(merged["background_denominator"].fillna(0).sum()), "matching_background_status": "missing_background_cell"}
    min_bg = _min_denominator(config, split, "background_action_time")
    if split != "all" and (merged["background_denominator"] < min_bg).any():
        return {"matching_background_rate": np.nan, "matching_background_denominator": int(merged["background_denominator"].sum()), "matching_background_status": "insufficient_background_denominator"}
    return {
        "matching_background_rate": float((merged["weight"] * merged["background_rate"]).sum()),
        "matching_background_denominator": int(merged["background_denominator"].sum()),
        "matching_background_status": "sufficient",
    }


def _summarize_groups(
    df: pd.DataFrame,
    background: pd.DataFrame,
    config: dict[str, Any],
    denominator_scope: str,
    summary_id: str,
    group_cols: list[str],
    comparator_dims: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    source = df.loc[df["denominator_scope"].eq(denominator_scope)].copy()
    for split in ALL_SPLITS:
        part = _split_view(source, split)
        parent = _summary_metrics(part)
        if group_cols:
            grouped = part.groupby(group_cols, dropna=False)
            iterator = grouped
        else:
            iterator = [((), part)]
        for key, group in iterator:
            metrics = _summary_metrics(group)
            comp = _matching_background(group, background, comparator_dims, split, config) if denominator_scope == "rps_episode_primary" else {
                "matching_background_rate": np.nan,
                "matching_background_denominator": np.nan,
                "matching_background_status": "not_applicable",
            }
            row: dict[str, Any] = {
                "summary_id": summary_id,
                "denominator_scope": denominator_scope,
                "split": split,
                "active_regime_dimensions": "|".join(group_cols) if group_cols else "none",
                "lift_vs_parent": metrics["plus10_before_minus5_rate"] - parent["plus10_before_minus5_rate"] if np.isfinite(metrics["plus10_before_minus5_rate"]) and np.isfinite(parent["plus10_before_minus5_rate"]) else np.nan,
                "matching_background_rate": comp["matching_background_rate"],
                "matching_background_denominator": comp["matching_background_denominator"],
                "matching_background_status": comp["matching_background_status"],
                "lift_vs_matching_background": metrics["plus10_before_minus5_rate"] - comp["matching_background_rate"] if np.isfinite(metrics["plus10_before_minus5_rate"]) and np.isfinite(comp["matching_background_rate"]) else np.nan,
            }
            if group_cols:
                if not isinstance(key, tuple):
                    key = (key,)
                for col, value in zip(group_cols, key, strict=True):
                    row[col] = value
            row.update(metrics)
            row["denominator_sufficiency_status"] = _denom_status(
                int(metrics["metric_denominator"]),
                int(comp["matching_background_denominator"]) if np.isfinite(comp["matching_background_denominator"]) else 0,
                split,
                config,
                needs_bg=denominator_scope == "rps_episode_primary",
            )
            rows.append(row)
    return pd.DataFrame(rows)


def _apply_masks(joined: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_scopes = joined["denominator_scope"].isin(["rps_episode_primary", "background_action_time"])
    base = joined.loc[candidate_scopes].copy()
    constructive = {"normal_uptrend", "normal_range", "post_drawdown_rebound_hypothesis"}
    leadership = {"industry_leading", "industry_rebound_from_drawdown"}
    masks = [
        ("mask_A_all_rps", "rps_mask", "", lambda d: d["denominator_scope"].eq("rps_episode_primary")),
        ("mask_B_market_non_missing", "rps_mask", "mask_A_all_rps", lambda d: d["denominator_scope"].eq("rps_episode_primary") & ~d["market_regime_bucket"].eq("missing_market_regime")),
        ("mask_B_market_constructive_no_default_rebound_penalty", "rps_mask", "mask_A_all_rps", lambda d: d["denominator_scope"].eq("rps_episode_primary") & d["market_regime_bucket"].isin(constructive)),
        ("mask_C_industry_leadership", "rps_mask", "mask_B_market_constructive_no_default_rebound_penalty", lambda d: d["denominator_scope"].eq("rps_episode_primary") & d["market_regime_bucket"].isin(constructive) & d["industry_regime_bucket"].isin(leadership)),
        ("background_all", "background_mask", "", lambda d: d["denominator_scope"].eq("background_action_time")),
        ("background_market_non_missing", "background_mask", "background_all", lambda d: d["denominator_scope"].eq("background_action_time") & ~d["market_regime_bucket"].eq("missing_market_regime")),
        ("background_market_constructive_no_default_rebound_penalty", "background_mask", "background_all", lambda d: d["denominator_scope"].eq("background_action_time") & d["market_regime_bucket"].isin(constructive)),
        ("background_industry_leadership", "background_mask", "background_market_constructive_no_default_rebound_penalty", lambda d: d["denominator_scope"].eq("background_action_time") & d["market_regime_bucket"].isin(constructive) & d["industry_regime_bucket"].isin(leadership)),
    ]
    membership_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []
    background = joined.loc[joined["denominator_scope"].eq("background_action_time")].copy()
    for ablation_id, ablation_type, parent_id, func in masks:
        included = func(base)
        member = base.loc[included].copy()
        member["ablation_id"] = ablation_id
        member["ablation_type"] = ablation_type
        member["parent_ablation_id"] = parent_id
        member["included_flag"] = True
        member["inclusion_reason"] = "pre_registered_mask_match"
        member["exclusion_reason"] = ""
        for split in ALL_SPLITS:
            part = _split_view(member, split)
            metrics = _summary_metrics(part)
            dims = []
            if "market" in ablation_id:
                dims = ["market_regime_bucket"]
            if "industry" in ablation_id:
                dims = ["market_regime_bucket", "industry_regime_bucket"]
            comp = _matching_background(part, background, dims, split, config) if ablation_type == "rps_mask" else {
                "matching_background_rate": np.nan,
                "matching_background_denominator": np.nan,
                "matching_background_status": "not_applicable",
            }
            parent_rate = np.nan
            parent_denom = np.nan
            parent_gain50 = np.nan
            if parent_id:
                parent_mask = next(func2 for aid2, _, _, func2 in masks if aid2 == parent_id)
                parent_part = _split_view(base.loc[parent_mask(base)], split)
                parent_metrics = _summary_metrics(parent_part)
                parent_rate = parent_metrics["plus10_before_minus5_rate"]
                parent_denom = parent_metrics["metric_denominator"]
                parent_gain50 = parent_metrics["max_gain50_proxy_rate"]
            row = {
                "ablation_id": ablation_id,
                "ablation_type": ablation_type,
                "parent_ablation_id": parent_id,
                "split": split,
                "parent_metric_denominator": parent_denom,
                "parent_plus10_before_minus5_rate": parent_rate,
                "lift_vs_parent": metrics["plus10_before_minus5_rate"] - parent_rate if np.isfinite(metrics["plus10_before_minus5_rate"]) and np.isfinite(parent_rate) else np.nan,
                "denominator_shrink_vs_parent": 1.0 - _safe_div(metrics["metric_denominator"], parent_denom) if np.isfinite(parent_denom) and parent_denom else np.nan,
                "max_gain50_proxy_retention_vs_parent": _safe_div(metrics["max_gain50_proxy_rate"], parent_gain50) if np.isfinite(parent_gain50) and parent_gain50 > 0 else np.nan,
                "matching_background_rate": comp["matching_background_rate"],
                "matching_background_denominator": comp["matching_background_denominator"],
                "matching_background_status": comp["matching_background_status"],
                "lift_vs_matching_background": metrics["plus10_before_minus5_rate"] - comp["matching_background_rate"] if np.isfinite(metrics["plus10_before_minus5_rate"]) and np.isfinite(comp["matching_background_rate"]) else np.nan,
                "denominator_sufficiency_status": _denom_status(
                    int(metrics["metric_denominator"]),
                    int(comp["matching_background_denominator"]) if np.isfinite(comp["matching_background_denominator"]) else 0,
                    split,
                    config,
                    needs_bg=ablation_type == "rps_mask",
                ),
            }
            row.update(metrics)
            summary_rows.append(row)
        membership_frames.append(member)
    membership = pd.concat(membership_frames, ignore_index=True, sort=False) if membership_frames else base.iloc[0:0].copy()
    membership["denominator_sufficiency_status"] = ""
    membership["matching_background_status"] = ""
    membership_cols = [
        "r04_candidate_event_id",
        "background_event_id",
        "raw_action_time_event_id",
        "denominator_scope",
        "ablation_id",
        "ablation_type",
        "parent_ablation_id",
        "included_flag",
        "inclusion_reason",
        "exclusion_reason",
        "market_regime_bucket",
        "industry_regime_bucket",
        "split",
        "primary_success_flag",
        "metric_denominator_eligible_flag",
        "bad_path_flag",
        "max_gain50_proxy",
        "denominator_sufficiency_status",
        "matching_background_status",
    ]
    for col in membership_cols:
        if col not in membership.columns:
            membership[col] = pd.NA
    return membership[membership_cols].reset_index(drop=True), pd.DataFrame(summary_rows)


def _candidate_funnel(candidate: pd.DataFrame, duplicate_audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in ALL_SPLITS:
        part = _split_view(candidate, split)
        for status, count in part["r04_inclusion_status"].value_counts(dropna=False).sort_index().items():
            rows.append({"split": split, "r04_inclusion_status": status, "row_count": int(count), "share": _safe_div(int(count), len(part))})
    rows.append({"split": "all", "r04_inclusion_status": "excluded_duplicate_episode", "row_count": int(duplicate_audit["duplicate_row_count"].sum() - len(duplicate_audit)) if not duplicate_audit.empty else 0, "share": np.nan})
    return pd.DataFrame(rows)


def _raw_vs_episode_audit(raw: pd.DataFrame, candidate: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ALL_SPLITS:
        raw_part = _split_view(raw, split)
        ep_part = _split_view(candidate, split)
        raw_metric = raw_part.loc[_as_bool_series(raw_part["entry_valid"]) & _as_bool_series(raw_part["path_complete_120d"])]
        ep_metric = ep_part.loc[_as_bool_series(ep_part["metric_denominator_eligible_flag"])]
        raw_rate = _safe_div(int(_as_bool_series(_primary_success_from_race(raw_metric["race_plus10_minus5_status"])).sum()), len(raw_metric))
        ep_rate = _safe_div(int(_as_bool_series(ep_metric["primary_success_flag"]).sum()), len(ep_metric))
        rows.append(
            {
                "split": split,
                "raw_signal_row_count": int(len(raw_part)),
                "episode_count": int(len(ep_part)),
                "episode_compression_ratio": _safe_div(len(raw_part), len(ep_part)),
                "raw_repeated_trigger_count": int(max(len(raw_part) - len(ep_part), 0)),
                "raw_path_overlap_proxy": _safe_div(max(len(raw_part) - len(ep_part), 0), len(raw_part)),
                "raw_primary_metric": raw_rate,
                "episode_primary_metric": ep_rate,
                "raw_vs_episode_metric_delta": raw_rate - ep_rate if np.isfinite(raw_rate) and np.isfinite(ep_rate) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _status_audit(df: pd.DataFrame, split_col: str, status_col: str, prefix: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split in ALL_SPLITS:
        part = _split_view(df.rename(columns={split_col: "split"}), split)
        for status, count in part[status_col].value_counts(dropna=False).sort_index().items():
            rows.append({"split": split, f"{prefix}_status": status, "row_count": int(count), "share": _safe_div(int(count), len(part))})
    return pd.DataFrame(rows)


def _bucket_summary(joined: pd.DataFrame, bucket_col: str, scope: str, summary_id: str, config: dict[str, Any]) -> pd.DataFrame:
    background = joined.loc[joined["denominator_scope"].eq("background_action_time")]
    dims = [bucket_col]
    return _summarize_groups(joined, background, config, scope, summary_id, dims, dims if scope == "rps_episode_primary" else [])


def _concentration_audit(joined: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rps = joined.loc[joined["denominator_scope"].eq("rps_episode_primary") & _as_bool_series(joined["metric_denominator_eligible_flag"])].copy()
    rps["year"] = pd.to_datetime(rps["anchor_signal_date"], errors="coerce").dt.year
    for split in ALL_SPLITS:
        part = _split_view(rps, split)
        denom = len(part)
        for group_id, group_cols in [
            ("baseline_A_rps_only", []),
            ("baseline_B_market_bucket", ["market_regime_bucket"]),
            ("baseline_C_market_industry_bucket", ["market_regime_bucket", "industry_regime_bucket"]),
        ]:
            if group_cols:
                groups = part.groupby(group_cols, dropna=False)
            else:
                groups = [((), part)]
            for key, group in groups:
                metric_denom = len(group)
                if metric_denom == 0:
                    continue
                top1_year = _safe_div(group["year"].value_counts(dropna=True).max() if not group["year"].dropna().empty else 0, metric_denom)
                top1_industry = _safe_div(group["industry_target_key"].value_counts(dropna=True).max() if not group["industry_target_key"].dropna().empty else 0, metric_denom)
                inst_counts = group["instrument_id"].value_counts()
                top1_inst = _safe_div(inst_counts.iloc[0] if len(inst_counts) else 0, metric_denom)
                top5_inst = _safe_div(inst_counts.head(5).sum() if len(inst_counts) else 0, metric_denom)
                row = {
                    "split": split,
                    "group_id": group_id,
                    "metric_denominator": metric_denom,
                    "top1_year_share": top1_year,
                    "top1_industry_share": top1_industry,
                    "top1_instrument_share": top1_inst,
                    "top5_instrument_share": top5_inst,
                    "concentration_warning": bool(
                        top1_year > config["thresholds"]["max_top1_year_share_of_lift"]
                        or top1_industry > config["thresholds"]["max_top1_industry_share_of_lift"]
                        or top1_inst > config["thresholds"]["max_top1_instrument_share"]
                        or top5_inst > config["thresholds"]["max_top5_instrument_share"]
                    ),
                    "share_of_scope_denominator": _safe_div(metric_denom, denom),
                }
                if group_cols:
                    if not isinstance(key, tuple):
                        key = (key,)
                    for col, value in zip(group_cols, key, strict=True):
                        row[col] = value
                rows.append(row)
    return pd.DataFrame(rows)


def _split_stability(outcome: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ablation_id, part in outcome.groupby("ablation_id", sort=False):
        val = part.loc[part["split"].eq("validation")]
        rob = part.loc[part["split"].eq("robustness")]
        val_lift = _safe_float(val["lift_vs_parent"].iloc[0]) if len(val) else np.nan
        rob_lift = _safe_float(rob["lift_vs_parent"].iloc[0]) if len(rob) else np.nan
        rows.append(
            {
                "ablation_id": ablation_id,
                "validation_lift_vs_parent": val_lift,
                "robustness_lift_vs_parent": rob_lift,
                "oos_direction_consistent": bool(np.isfinite(val_lift) and np.isfinite(rob_lift) and np.sign(val_lift) == np.sign(rob_lift)),
            }
        )
    return pd.DataFrame(rows)


def _make_decision(outcome: pd.DataFrame, concentration: pd.DataFrame, reconciliation: pd.DataFrame, config: dict[str, Any]) -> tuple[str, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    if int(reconciliation["total_mismatch_count"].sum()) > 0:
        rows.append({"criteria_id": "background_path_reconciliation", "status": "failed", "details": "total_mismatch_count > 0"})
        return "blocked_background_path_label_validation_failed", pd.DataFrame(rows)
    mask_c = outcome.loc[outcome["ablation_id"].eq("mask_C_industry_leadership") & outcome["split"].isin(["validation", "robustness"])].copy()
    mask_a = outcome.loc[outcome["ablation_id"].eq("mask_A_all_rps") & outcome["split"].isin(["validation", "robustness"])].copy()
    invalid_comparator = mask_c["matching_background_status"].eq("invalid_comparator").any()
    if invalid_comparator:
        rows.append({"criteria_id": "matching_background_comparator", "status": "failed", "details": "invalid comparator"})
        return "blocked_matching_background_comparator_invalid", pd.DataFrame(rows)
    insufficient = (
        mask_c["denominator_sufficiency_status"].ne("sufficient").any()
        or mask_c["matching_background_status"].isin(["insufficient_background_denominator", "missing_background_cell", "no_rps_cell_weight"]).any()
    )
    thresholds = config["thresholds"]
    pass_rows: list[bool] = []
    for row in mask_c.itertuples(index=False):
        parent = mask_a.loc[mask_a["split"].eq(row.split)]
        parent_bad = _safe_float(parent["bad_path_rate"].iloc[0]) if len(parent) else np.nan
        bad_increase = row.bad_path_rate - parent_bad if np.isfinite(row.bad_path_rate) and np.isfinite(parent_bad) else np.nan
        pass_row = bool(
            row.denominator_sufficiency_status == "sufficient"
            and row.matching_background_status == "sufficient"
            and np.isfinite(row.lift_vs_parent)
            and row.lift_vs_parent >= thresholds["minimum_oos_primary_lift"]
            and np.isfinite(bad_increase)
            and bad_increase <= thresholds["max_allowed_p_bad_increase"]
            and np.isfinite(row.max_gain50_proxy_retention_vs_parent)
            and row.max_gain50_proxy_retention_vs_parent >= thresholds["min_max_gain50_proxy_retention"]
            and np.isfinite(row.denominator_shrink_vs_parent)
            and row.denominator_shrink_vs_parent <= thresholds["max_denominator_shrink_vs_parent"]
            and row.race_ambiguous_rate <= thresholds["max_race_ambiguous_rate"]
            and np.isfinite(row.lift_vs_matching_background)
            and row.lift_vs_matching_background > 0
        )
        pass_rows.append(pass_row)
        rows.append(
            {
                "criteria_id": f"mask_C_hard_constraints_{row.split}",
                "status": "passed" if pass_row else "failed",
                "details": json.dumps(
                    {
                        "lift_vs_parent": row.lift_vs_parent,
                        "bad_path_rate_increase": bad_increase,
                        "max_gain50_proxy_retention_vs_parent": row.max_gain50_proxy_retention_vs_parent,
                        "denominator_shrink_vs_parent": row.denominator_shrink_vs_parent,
                        "race_ambiguous_rate": row.race_ambiguous_rate,
                        "lift_vs_matching_background": row.lift_vs_matching_background,
                    },
                    default=str,
                ),
            }
        )
    if insufficient:
        rows.append({"criteria_id": "denominator_or_matching_background_sufficiency", "status": "failed", "details": "insufficient denominator or comparator"})
        return "r04_v1_exposure_eligibility_audit_complete_descriptive_only", pd.DataFrame(rows)
    if len(pass_rows) == 2 and all(pass_rows):
        return "proceed_to_r04_v2_volume_volatility_spec_only", pd.DataFrame(rows)
    persistent = False
    for row in mask_a.itertuples(index=False):
        split_persistent = bool(
            (np.isfinite(row.max_gain50_proxy_rate) and row.max_gain50_proxy_rate >= config["r04b"]["min_mask_A_oos_max_gain50_proxy_rate"])
            or (np.isfinite(row.max_gain_120d_p90) and row.max_gain_120d_p90 >= config["r04b"]["min_mask_A_oos_max_gain_120d_p90"])
        )
        rows.append({"criteria_id": f"mask_A_persistent_upside_{row.split}", "status": "passed" if split_persistent else "failed", "details": f"max_gain50_proxy_rate={row.max_gain50_proxy_rate}; max_gain_120d_p90={row.max_gain_120d_p90}"})
        persistent = persistent or split_persistent
    if persistent:
        return "proceed_to_r04b_hold_exit_only", pd.DataFrame(rows)
    return "stop_exposure_eligibility_route_no_oos_lift", pd.DataFrame(rows)


def _build_spec_sheet(config: dict[str, Any], q67_vol: float) -> pd.DataFrame:
    thresholds = config["thresholds"]
    base = {
        "feature_asof_rule": "feature_asof_date <= anchor_signal_date",
        "minimum_train_denominator": thresholds["minimum_train_denominator"],
        "minimum_validation_denominator": thresholds["minimum_validation_denominator"],
        "minimum_robustness_denominator": thresholds["minimum_robustness_denominator"],
        "minimum_background_denominator": thresholds["minimum_background_denominator"],
        "primary_metric": "plus10_before_minus5_rate",
        "secondary_metrics": "good_path_rate|bad_path_rate|early_failure_rate|max_gain50_proxy_rate|max_gain_120d_p50_p75_p90|max_drawdown_120d_p50_p75_p90|close_return_t20_t60_t120_p50",
        "race_ambiguous_policy": "same_offset_and_censored_incomplete_excluded_from_metric_denominator_and_reported",
        "matching_background_comparator": "same_split_same_active_regime_cell_weighted_by_rps_cell_weight",
    }
    rows: list[dict[str, Any]] = []
    market_formulas = {
        "post_drawdown_rebound_hypothesis": f"market_ret_60d <= -0.10 AND market_ret_20d >= 0.05 AND market_realized_vol_60d >= {q67_vol}",
        "panic_high_vol": f"market_drawdown_252d >= 0.25 AND market_realized_vol_60d >= {q67_vol} AND NOT post_drawdown_rebound_hypothesis",
        "normal_uptrend": "market_ret_120d >= 0 AND market_drawdown_252d < 0.10",
        "normal_range": "market_ret_120d >= -0.05 AND market_drawdown_252d < 0.25",
        "downtrend_low_breadth": "all remaining complete market rows",
        "missing_market_regime": "incomplete market feature rows",
    }
    for order, bucket in enumerate(MARKET_BUCKETS, start=1):
        row = {
            **base,
            "feature_name": "market_regime_bucket",
            "feature_group": "market",
            "feature_formula": "market_ret_Nd, market_drawdown_252d, market_realized_vol_60d, market_breadth_ma60 from eligible stock-day equal-weight proxy",
            "lookback_window": "20|60|120|252",
            "required_input_fields": "close|source_price_hash|source_calendar_hash|is_r01_pit_executable_eligible|suspended_or_dirty_bar",
            "bucket_name": bucket,
            "bucket_formula": market_formulas[bucket],
            "bucket_cutpoints": json.dumps({"train_q67_market_realized_vol_60d": q67_vol}, sort_keys=True),
            "bucket_priority_order": order,
            "bucket_count_cap": len(MARKET_BUCKETS),
            "missing_value_policy": "missing_market_regime",
            "kill_criteria_id": "r04_mask_C_hard_constraints",
        }
        row["formula_hash"] = _hash_json(row)
        rows.append(row)
    industry_formulas = {
        "missing_industry": "missing membership or incomplete industry feature",
        "thin_industry": "industry_member_count < min_member_count",
        "industry_rebound_from_drawdown": "industry_ret_60d < 0 AND industry_ret_20d >= 0.05",
        "industry_leading": "industry_rps_60d >= 0.70 AND industry_breadth_ma60 >= 0.60",
        "industry_lagging": "industry_rps_60d <= 0.30 OR industry_breadth_ma60 <= 0.40",
        "industry_neutral": "complete industry rows not matched above",
    }
    for order, bucket in enumerate(INDUSTRY_BUCKETS, start=1):
        row = {
            **base,
            "feature_name": "industry_regime_bucket",
            "feature_group": "industry",
            "feature_formula": "industry equal-weight proxy, industry_rps_60d, industry_breadth_ma60, stock_rps_minus_industry_rps_60d",
            "lookback_window": "20|60",
            "required_input_fields": "pit_industry_membership|close|is_r01_pit_executable_eligible|suspended_or_dirty_bar",
            "bucket_name": bucket,
            "bucket_formula": industry_formulas[bucket],
            "bucket_cutpoints": json.dumps({"industry_leading_rps": 0.70, "industry_lagging_rps": 0.30, "breadth_high": 0.60, "breadth_low": 0.40}, sort_keys=True),
            "bucket_priority_order": order,
            "bucket_count_cap": len(INDUSTRY_BUCKETS),
            "missing_value_policy": "missing_industry",
            "kill_criteria_id": "r04_mask_C_hard_constraints",
        }
        row["formula_hash"] = _hash_json(row)
        rows.append(row)
    return pd.DataFrame(rows)


def _feature_dictionary() -> pd.DataFrame:
    rows = []
    for feature in ["market_ret_20d", "market_ret_60d", "market_ret_120d", "market_ret_252d", "market_drawdown_252d", "market_realized_vol_60d", "market_breadth_ma60"]:
        rows.append({"feature_name": feature, "feature_group": "market", "asof_rule": "trade_date <= anchor_signal_date", "status": "r04_v1_primary_feature"})
    for feature in ["industry_ret_20d", "industry_ret_60d", "industry_rps_60d", "industry_breadth_ma60", "stock_ret_60d", "stock_rps_60d", "stock_rps_minus_industry_rps_60d"]:
        rows.append({"feature_name": feature, "feature_group": "industry", "asof_rule": "trade_date <= anchor_signal_date and membership.date <= anchor_signal_date", "status": "r04_v1_primary_feature"})
    rows.append({"feature_name": "EV_R", "feature_group": "risk", "asof_rule": "not_used", "status": "out_of_scope_for_r04_v1"})
    return pd.DataFrame(rows)


def _write_final_report(path: Path, manifest: dict[str, Any], readiness: pd.DataFrame, funnel: pd.DataFrame, raw_audit: pd.DataFrame, background_audit: pd.DataFrame, outcome: pd.DataFrame, kill: pd.DataFrame) -> None:
    mask_a = outcome.loc[outcome["ablation_id"].eq("mask_A_all_rps") & outcome["split"].isin(["validation", "robustness"])]
    mask_c = outcome.loc[outcome["ablation_id"].eq("mask_C_industry_leadership") & outcome["split"].isin(["validation", "robustness"])]
    lines = [
        "# R04 Dynamic Momentum Exposure Eligibility Audit",
        "",
        f"Final decision: {manifest['final_decision']}",
        "",
        "R04 v1 scope is fixed to RPS + market + industry exposure eligibility only. It is not an entry-signal search, production gate, position sizing rule, stop rule, or CTA/trailing-exit experiment.",
        "",
        "R03 anti-patterns remain excluded: same-day multi-signal AND as independent evidence, seed-anchor probability as action-time edge, fresh-count waiting rules, denominator shrink as posterior improvement, and outcome-tuned bucket edits.",
        "",
        f"spec_sheet_hash: {manifest['spec_sheet_hash']}",
        f"train_q67_market_realized_vol_60d: {manifest['train_q67_market_realized_vol_60d']}",
        "ev_r_status = out_of_scope_for_r04_v1",
        "big_winner_status = proxy_only",
        "",
        "## Input Readiness",
        readiness.to_markdown(index=False),
        "",
        "## Candidate Funnel",
        funnel.to_markdown(index=False),
        "",
        "## Raw Trigger Vs Episode",
        raw_audit.to_markdown(index=False),
        "",
        "## Background Denominator",
        background_audit.to_markdown(index=False),
        "",
        "## Background Path Label Reconciliation",
        "See `r04_background_path_label_reconciliation_audit.csv`; the validator requires total_mismatch_count == 0.",
        "",
        "## Industry Membership Join",
        "See `r04_industry_membership_join_audit.csv`; PIT membership is joined by instrument with membership.date <= anchor_signal_date.",
        "",
        "## Baseline A/B/C And Negative Ablation",
        "See `r04_nested_baseline_ablation_summary.csv`, `r04_negative_ablation_summary.csv`, `r04_matching_background_comparator_audit.csv`, and `r04_outcome_hierarchy_summary.csv`.",
        "",
        "## Market And Industry Buckets",
        "See `r04_market_regime_bucket_summary.csv`, `r04_post_drawdown_rebound_audit.csv`, and `r04_industry_regime_bucket_summary.csv`; `post_drawdown_rebound_hypothesis` and `industry_rebound_from_drawdown` are hypotheses, not default bad gates.",
        "",
        "## Denominator, Race, Stability, Concentration",
        "See `r04_denominator_shrink_audit.csv`, `r04_denominator_sufficiency_audit.csv`, `r04_race_ambiguity_audit.csv`, `r04_split_stability_audit.csv`, and `r04_year_industry_concentration_audit.csv`.",
        "",
        "## OOS Mask A Baseline",
        mask_a.to_markdown(index=False),
        "",
        "## OOS Mask C Eligibility Hypothesis",
        mask_c.to_markdown(index=False),
        "",
        "## Kill Criteria",
        kill.to_markdown(index=False),
        "",
        "No production gate, position size, or CTA exit rule is emitted by this audit.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path) -> dict[str, Any]:
    config = _read_yaml(config_path)
    output_root = topic_path(Path(config["output_root"]))
    cache_dir = output_root / "cache"
    reports_dir = output_root / "reports"
    manifests_dir = output_root / "manifests"
    for directory in [cache_dir, reports_dir, manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    readiness = _input_readiness(config)
    write_csv(readiness, reports_dir / "r04_input_readiness_audit.csv")
    blocked = _blocked_decision_from_readiness(readiness)
    if blocked:
        manifest = {
            "phase": config["phase"],
            "requirement_id": config["requirement_id"],
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": relpath(topic_path(config_path)),
            "requirement_path": config["requirement_path"],
            "output_root": relpath(output_root),
            "final_decision": blocked,
        }
        write_json(manifest, manifests_dir / "r04_dynamic_momentum_exposure_eligibility_manifest.json")
        return manifest

    calendar = _load_calendar(Path(config["local_inputs"]["calendar"]))
    print("loading R02 coverage eligible-day panel", flush=True)
    stock = _load_coverage_panel(config, calendar)
    date_split = stock.drop_duplicates("trade_date").set_index("trade_date")["split"].to_dict()
    print("building market regime panel", flush=True)
    market, q67_vol = _build_market_panel(stock, config)
    print("loading and joining PIT industry membership", flush=True)
    membership, duplicate_membership = _load_membership(Path(config["local_inputs"]["pit_industry_membership"]))
    industry, stock_with_membership = _build_industry_panel(stock, membership, config)
    print("building RPS candidate and raw audit panels", flush=True)
    candidate, duplicate_candidates = _build_candidate_panel(config, date_split)
    raw = _build_raw_panel(config, candidate)
    background_cache_path = cache_dir / "r04_background_action_time_panel.parquet"
    if background_cache_path.exists():
        print("reusing existing full background action-time panel", flush=True)
        background = pd.read_parquet(background_cache_path)
    else:
        print("building full background action-time panel", flush=True)
        background = _compute_background_panel(stock, config)
    print("running background path-label reconciliation", flush=True)
    reconciliation = _reconcile_background_labeler(raw, stock, config)
    print("joining candidate/background/raw panels to regimes", flush=True)
    joined, membership_audit = _join_regimes(candidate, raw, background, market, industry, stock, membership)
    if not duplicate_membership.empty:
        membership_audit.loc[membership_audit["audit_item"].eq("membership_duplicate_instrument_date_rows"), "count"] = int(duplicate_membership["duplicate_membership_rows"].sum())

    print("building ablation membership and outcome reports", flush=True)
    ablation_membership, outcome = _apply_masks(joined, config)
    background_scope = joined.loc[joined["denominator_scope"].eq("background_action_time")]
    nested = pd.concat(
        [
            _summarize_groups(joined, background_scope, config, "rps_episode_primary", "baseline_A_rps_only", [], []),
            _summarize_groups(joined, background_scope, config, "rps_episode_primary", "baseline_B_market_bucket", ["market_regime_bucket"], ["market_regime_bucket"]),
            _summarize_groups(joined, background_scope, config, "rps_episode_primary", "baseline_C_market_industry_bucket", ["market_regime_bucket", "industry_regime_bucket"], ["market_regime_bucket", "industry_regime_bucket"]),
        ],
        ignore_index=True,
        sort=False,
    )
    negative = pd.concat(
        [
            _summarize_groups(joined, background_scope, config, "background_action_time", "full_background_component", [], []),
            _summarize_groups(joined, background_scope, config, "background_action_time", "background_market_bucket", ["market_regime_bucket"], []),
            _summarize_groups(joined, background_scope, config, "background_action_time", "background_industry_bucket", ["industry_regime_bucket"], []),
            _summarize_groups(joined, background_scope, config, "background_action_time", "background_market_industry_bucket", ["market_regime_bucket", "industry_regime_bucket"], []),
            _summarize_groups(joined, background_scope, config, "rps_episode_primary", "rps_market_only", ["market_regime_bucket"], ["market_regime_bucket"]),
            _summarize_groups(joined, background_scope, config, "rps_episode_primary", "rps_industry_only", ["industry_regime_bucket"], ["industry_regime_bucket"]),
            _summarize_groups(joined, background_scope, config, "rps_episode_primary", "rps_market_industry", ["market_regime_bucket", "industry_regime_bucket"], ["market_regime_bucket", "industry_regime_bucket"]),
        ],
        ignore_index=True,
        sort=False,
    )
    market_summary = _bucket_summary(joined, "market_regime_bucket", "rps_episode_primary", "market_regime_bucket", config)
    industry_summary = _bucket_summary(joined, "industry_regime_bucket", "rps_episode_primary", "industry_regime_bucket", config)
    rebound_audit = market_summary.loc[market_summary["market_regime_bucket"].eq("post_drawdown_rebound_hypothesis")].copy()
    comparator_audit = outcome[["ablation_id", "split", "matching_background_rate", "matching_background_denominator", "matching_background_status", "lift_vs_matching_background"]].copy()
    shrink_audit = outcome[["ablation_id", "split", "parent_metric_denominator", "metric_denominator", "denominator_shrink_vs_parent"]].copy()
    sufficiency_audit = outcome[["ablation_id", "split", "metric_denominator", "matching_background_denominator", "denominator_sufficiency_status"]].copy()
    race_audit = outcome[["ablation_id", "split", "path_complete_denominator", "metric_denominator", "race_ambiguous_count", "race_ambiguous_rate"]].copy()
    split_stability = _split_stability(outcome)
    concentration = _concentration_audit(joined, config)
    decision, kill = _make_decision(outcome, concentration, reconciliation, config)

    spec = _build_spec_sheet(config, q67_vol)
    feature_dictionary = _feature_dictionary()
    candidate_funnel = _candidate_funnel(candidate, duplicate_candidates)
    raw_vs_episode = _raw_vs_episode_audit(raw, candidate)
    background_audit = _status_audit(background, "split", "background_inclusion_status", "background_inclusion")

    cache_paths = {
        "candidate": cache_dir / "r04_rps_candidate_action_panel.parquet",
        "raw": cache_dir / "r04_raw_action_time_audit_panel.parquet",
        "background": cache_dir / "r04_background_action_time_panel.parquet",
        "market": cache_dir / "r04_market_regime_panel.parquet",
        "industry": cache_dir / "r04_industry_regime_panel.parquet",
        "join": cache_dir / "r04_candidate_regime_join_panel.parquet",
        "ablation": cache_dir / "r04_ablation_membership_panel.parquet",
    }
    for df, path in [
        (candidate, cache_paths["candidate"]),
        (raw, cache_paths["raw"]),
        (background, cache_paths["background"]),
        (market, cache_paths["market"]),
        (industry, cache_paths["industry"]),
        (joined, cache_paths["join"]),
        (ablation_membership, cache_paths["ablation"]),
    ]:
        _write_parquet(df, path)

    report_paths = {
        "spec": reports_dir / "r04_spec_sheet_frozen.csv",
        "feature_dictionary": reports_dir / "r04_feature_dictionary.csv",
        "candidate_funnel": reports_dir / "r04_candidate_funnel_audit.csv",
        "raw_vs_episode": reports_dir / "r04_raw_vs_episode_audit.csv",
        "background_denominator": reports_dir / "r04_background_denominator_audit.csv",
        "reconciliation": reports_dir / "r04_background_path_label_reconciliation_audit.csv",
        "membership": reports_dir / "r04_industry_membership_join_audit.csv",
        "market_summary": reports_dir / "r04_market_regime_bucket_summary.csv",
        "industry_summary": reports_dir / "r04_industry_regime_bucket_summary.csv",
        "rebound": reports_dir / "r04_post_drawdown_rebound_audit.csv",
        "nested": reports_dir / "r04_nested_baseline_ablation_summary.csv",
        "negative": reports_dir / "r04_negative_ablation_summary.csv",
        "comparator": reports_dir / "r04_matching_background_comparator_audit.csv",
        "outcome": reports_dir / "r04_outcome_hierarchy_summary.csv",
        "shrink": reports_dir / "r04_denominator_shrink_audit.csv",
        "sufficiency": reports_dir / "r04_denominator_sufficiency_audit.csv",
        "race": reports_dir / "r04_race_ambiguity_audit.csv",
        "stability": reports_dir / "r04_split_stability_audit.csv",
        "concentration": reports_dir / "r04_year_industry_concentration_audit.csv",
        "kill": reports_dir / "r04_kill_criteria_audit.csv",
    }
    for df, path in [
        (spec, report_paths["spec"]),
        (feature_dictionary, report_paths["feature_dictionary"]),
        (candidate_funnel, report_paths["candidate_funnel"]),
        (raw_vs_episode, report_paths["raw_vs_episode"]),
        (background_audit, report_paths["background_denominator"]),
        (reconciliation, report_paths["reconciliation"]),
        (membership_audit, report_paths["membership"]),
        (market_summary, report_paths["market_summary"]),
        (industry_summary, report_paths["industry_summary"]),
        (rebound_audit, report_paths["rebound"]),
        (nested, report_paths["nested"]),
        (negative, report_paths["negative"]),
        (comparator_audit, report_paths["comparator"]),
        (outcome, report_paths["outcome"]),
        (shrink_audit, report_paths["shrink"]),
        (sufficiency_audit, report_paths["sufficiency"]),
        (race_audit, report_paths["race"]),
        (split_stability, report_paths["stability"]),
        (concentration, report_paths["concentration"]),
        (kill, report_paths["kill"]),
    ]:
        write_csv(df, path)

    artifact_paths = [*cache_paths.values(), *report_paths.values(), reports_dir / "r04_input_readiness_audit.csv"]
    spec_hash = _hash_file(report_paths["spec"])
    manifest = {
        "phase": config["phase"],
        "requirement_id": config["requirement_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": relpath(topic_path(config_path)),
        "requirement_path": config["requirement_path"],
        "output_root": relpath(output_root),
        "train_q67_market_realized_vol_60d": q67_vol,
        "spec_sheet_hash": spec_hash,
        "rps_candidate_row_count": int(len(candidate)),
        "rps_candidate_included_count": int(candidate["r04_inclusion_status"].eq("included").sum()),
        "raw_action_time_row_count": int(len(raw)),
        "background_row_count": int(len(background)),
        "background_included_count": int(background["background_inclusion_status"].eq("included").sum()),
        "final_decision": decision,
        "artifact_hashes": _artifact_hashes(artifact_paths),
    }
    report_path = reports_dir / "r04_dynamic_momentum_exposure_eligibility_final_report.md"
    _write_final_report(report_path, manifest, readiness, candidate_funnel, raw_vs_episode, background_audit, outcome, kill)
    artifact_paths.append(report_path)
    manifest["artifact_hashes"] = _artifact_hashes(artifact_paths)
    write_json(manifest, manifests_dir / "r04_dynamic_momentum_exposure_eligibility_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    manifest = run(Path(args.config))
    print(json.dumps({"final_decision": manifest.get("final_decision"), "output_root": manifest.get("output_root")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

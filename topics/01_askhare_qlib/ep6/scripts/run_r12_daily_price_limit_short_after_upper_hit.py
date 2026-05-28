#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
EP6_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP6_DIR.parent
DEFAULT_CONFIG = EP6_DIR / "configs" / "r12_daily_price_limit_short_after_upper_hit_v0.yaml"
SPLITS = ["train", "validation", "robustness"]
PRIMARY_EVENT = "regular_10pct_upper_close_hit"
COMPARATOR_EVENT = "nonlimit_high_return"
ST_EVENT = "st_5pct_upper_close_hit_diagnostic"


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path


def topic_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return TOPIC_DIR / path


def rel(path: str | Path) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(TOPIC_DIR.resolve()))
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EP6 R12 daily price-limit short-after-upper-hit diagnostic")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def load_config(path: str | Path) -> tuple[dict[str, Any], Paths]:
    config_path = topic_path(path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = topic_path(config["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    return config, Paths(config_path=config_path, output_root=output_root)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format="%.8g")


def file_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def directory_hash(path: Path) -> str:
    if not path.exists() or not path.is_dir():
        return ""
    h = hashlib.sha256()
    for child in sorted(path.rglob("*")):
        if child.is_file():
            h.update(str(child.relative_to(path)).encode("utf-8"))
            h.update(file_hash(child).encode("utf-8"))
    return h.hexdigest()


def git_commit_or_status() -> str:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
        status = subprocess.check_output(["git", "status", "--short"], cwd=TOPIC_DIR, text=True).strip()
        return f"{commit} ({'dirty' if status else 'clean'})"
    except Exception:  # noqa: BLE001
        return "unavailable"


def load_calendar(path: Path) -> pd.DatetimeIndex:
    values = pd.read_csv(path, header=None)[0]
    return pd.DatetimeIndex(pd.to_datetime(values).dt.normalize())


def qlib_feature_path(provider_uri: Path, instrument: str, field: str) -> Path:
    return provider_uri / "features" / instrument.lower() / f"{field}.day.bin"


def read_qlib_series(provider_uri: Path, calendar: pd.DatetimeIndex, instrument: str, field: str) -> pd.Series:
    path = qlib_feature_path(provider_uri, instrument, field)
    if not path.exists():
        return pd.Series(dtype="float64", name=instrument.upper())
    arr = np.fromfile(path, dtype="<f4")
    if len(arr) == 0:
        return pd.Series(dtype="float64", name=instrument.upper())
    start_index = int(arr[0])
    values = arr[1:].astype("float64")
    dates = calendar[start_index : start_index + len(values)]
    return pd.Series(values[: len(dates)], index=dates, name=instrument.upper())


def load_feature_wide(provider_uri: Path, calendar: pd.DatetimeIndex, instruments: list[str], field: str) -> pd.DataFrame:
    series = []
    for instrument in instruments:
        s = read_qlib_series(provider_uri, calendar, instrument, field)
        if not s.empty:
            series.append(s)
    if not series:
        return pd.DataFrame(index=calendar)
    out = pd.concat(series, axis=1).reindex(calendar)
    out.columns = [str(c).upper() for c in out.columns]
    return out.sort_index()


def value_lookup(frame: pd.DataFrame, dates: pd.Series, instruments: pd.Series) -> np.ndarray:
    date_pos = frame.index.get_indexer(pd.DatetimeIndex(pd.to_datetime(dates).dt.normalize()))
    inst_pos = frame.columns.get_indexer(instruments.astype(str).str.upper())
    out = np.full(len(dates), np.nan, dtype="float64")
    ok = (date_pos >= 0) & (inst_pos >= 0)
    if ok.any():
        out[ok] = frame.to_numpy(dtype="float64", copy=False)[date_pos[ok], inst_pos[ok]]
    return out


def date_lookup_from_pos(calendar: pd.DatetimeIndex, pos: np.ndarray) -> list[str]:
    out: list[str] = []
    for value in pos:
        if np.isfinite(value):
            idx = int(value)
            if 0 <= idx < len(calendar):
                out.append(pd.Timestamp(calendar[idx]).date().isoformat())
            else:
                out.append("")
        else:
            out.append("")
    return out


def split_for_date(date: pd.Timestamp, config: dict[str, Any]) -> str:
    d = pd.Timestamp(date).normalize()
    split = config["sample_split"]
    if pd.Timestamp(split["train_start"]) <= d <= pd.Timestamp(split["train_end"]):
        return "train"
    if pd.Timestamp(split["validation_start"]) <= d <= pd.Timestamp(split["validation_end"]):
        return "validation"
    if pd.Timestamp(split["robustness_start"]) <= d <= pd.Timestamp(split["robustness_end"]):
        return "robustness"
    return "out_of_split"


def fmt_pct(value: Any, digits: int = 2) -> str:
    try:
        v = float(value)
    except Exception:  # noqa: BLE001
        return "NA"
    if not np.isfinite(v):
        return "NA"
    return f"{v * 100:.{digits}f}%"


def fmt_num(value: Any, digits: int = 4) -> str:
    try:
        v = float(value)
    except Exception:  # noqa: BLE001
        return "NA"
    if not np.isfinite(v):
        return "NA"
    return f"{v:.{digits}f}"


def newey_west_tstat(values: pd.Series | np.ndarray, lag: int) -> float:
    arr = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna().astype(float).to_numpy()
    n = len(arr)
    if n < 2:
        return math.nan
    mean = float(arr.mean())
    centered = arr - mean
    lag = max(0, min(int(lag), n - 1))
    gamma0 = float(np.dot(centered, centered) / n)
    var = gamma0
    for l in range(1, lag + 1):
        gamma = float(np.dot(centered[l:], centered[:-l]) / n)
        var += 2.0 * (1.0 - l / (lag + 1.0)) * gamma
    var_mean = var / n
    if not np.isfinite(var_mean) or var_mean <= 0:
        return math.nan
    return float(mean / math.sqrt(var_mean))


def finite_positive(arr: np.ndarray) -> np.ndarray:
    return np.isfinite(arr) & (arr > 0)


def tercile_from_percentile(percentile: pd.Series) -> pd.Series:
    out = pd.Series("unavailable", index=percentile.index, dtype="object")
    out.loc[percentile <= 1 / 3] = "low"
    out.loc[(percentile > 1 / 3) & (percentile <= 2 / 3)] = "middle"
    out.loc[percentile > 2 / 3] = "high"
    out.loc[percentile.isna()] = "unavailable"
    return out


def load_inputs(config: dict[str, Any]) -> dict[str, Any]:
    ds = config["data_sources"]
    provider_uri = topic_path(ds["qlib_provider_uri"])
    calendar = load_calendar(topic_path(ds["trading_calendar_path"]))
    provider_end = pd.Timestamp(ds["provider_load_end_date"])
    calendar = calendar[calendar <= provider_end]
    pit = pd.read_csv(
        topic_path(ds["pit_universe_path"]),
        usecols=["date", "instrument", "name", "market", "listing_age_trading_days", "market_cap_asof_T"],
        low_memory=False,
    )
    pit["date"] = pd.to_datetime(pit["date"]).dt.normalize()
    pit["instrument"] = pit["instrument"].astype(str).str.upper()
    pit = pit.loc[pit["date"].le(provider_end)].copy()
    industry = pd.read_csv(
        topic_path(ds["pit_industry_path"]),
        usecols=["date", "instrument", "industry_name"],
        low_memory=False,
    )
    industry["date"] = pd.to_datetime(industry["date"]).dt.normalize()
    industry["instrument"] = industry["instrument"].astype(str).str.upper()
    pit = pit.merge(industry, on=["date", "instrument"], how="left")
    pit["industry"] = pit["industry_name"].fillna("unknown")
    instruments = sorted(pit["instrument"].dropna().unique().tolist())
    fields = {}
    for field in ["open", "high", "low", "close", "volume", "money", "factor"]:
        fields[field] = load_feature_wide(provider_uri, calendar, instruments, field)
    benchmark = {
        "open": read_qlib_series(provider_uri, calendar, ds["index_instrument"], "open").reindex(calendar),
        "close": read_qlib_series(provider_uri, calendar, ds["index_instrument"], "close").reindex(calendar),
    }
    return {
        "provider_uri": provider_uri,
        "calendar": calendar,
        "pit": pit,
        "instruments": instruments,
        "fields": fields,
        "benchmark": benchmark,
    }


def build_previous_trade_fields(
    calendar: pd.DatetimeIndex,
    close: pd.DataFrame,
    volume: pd.DataFrame,
    money: pd.DataFrame,
    factor: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    valid_trade = close.gt(0) & np.isfinite(close) & volume.gt(0) & money.gt(0)
    pos = pd.DataFrame(
        np.broadcast_to(np.arange(len(calendar), dtype="float64")[:, None], close.shape),
        index=calendar,
        columns=close.columns,
    )
    prev_pos = pos.where(valid_trade).shift(1).ffill()
    prev_close = close.where(valid_trade).shift(1).ffill()
    prev_factor = factor.where(valid_trade).shift(1).ffill()
    gap = pos - prev_pos
    return {"prev_pos": prev_pos, "prev_close": prev_close, "prev_factor": prev_factor, "prev_gap": gap}


def market_state_by_date(calendar: pd.DatetimeIndex, benchmark_close: pd.Series) -> pd.Series:
    out = {}
    close = benchmark_close.reindex(calendar)
    for i, date in enumerate(calendar):
        if i < 20:
            out[date] = "unavailable"
            continue
        now = close.iloc[i]
        old = close.iloc[i - 20]
        if np.isfinite(now) and np.isfinite(old) and old > 0:
            out[date] = "up" if now / old - 1 >= 0 else "down"
        else:
            out[date] = "unavailable"
    return pd.Series(out)


def build_detection_audit(config: dict[str, Any], inputs: dict[str, Any]) -> pd.DataFrame:
    calendar = inputs["calendar"]
    fields = inputs["fields"]
    pit = inputs["pit"].copy()
    split = config["sample_split"]
    eval_start = pd.Timestamp(split["train_start"])
    eval_end = pd.Timestamp(split["robustness_end"])
    pit = pit.loc[pit["date"].between(eval_start, eval_end)].copy()
    pit["split"] = pit["date"].map(lambda d: split_for_date(pd.Timestamp(d), config))
    pit = pit.loc[pit["split"].isin(SPLITS)].copy()
    pit["candidate_scope"] = "pit_universe_candidate"
    pit["pit_member_on_date"] = True

    previous = build_previous_trade_fields(calendar, fields["close"], fields["volume"], fields["money"], fields["factor"])
    for field in ["open", "high", "low", "close", "volume", "money", "factor"]:
        pit[f"{field}_D"] = value_lookup(fields[field], pit["date"], pit["instrument"])
    pit["prev_close"] = value_lookup(previous["prev_close"], pit["date"], pit["instrument"])
    pit["prev_factor"] = value_lookup(previous["prev_factor"], pit["date"], pit["instrument"])
    pit["prev_pos"] = value_lookup(previous["prev_pos"], pit["date"], pit["instrument"])
    pit["prev_gap"] = value_lookup(previous["prev_gap"], pit["date"], pit["instrument"])
    pit["prev_traded_day"] = date_lookup_from_pos(calendar, pit["prev_pos"].to_numpy(dtype="float64"))
    pit["limit_detection_price_source"] = "provider_ohlc_with_factor_continuity_guard"
    pit["ret_to_prev_traded_close"] = pit["close_D"] / pit["prev_close"] - 1.0
    pit["close_high_gap"] = (pit["close_D"] / pit["high_D"] - 1.0).abs()
    pit["st_status_proxy"] = pit["name"].astype(str).str.upper().str.contains("ST", na=False)
    pit["market_cap_asof_T"] = pd.to_numeric(pit["market_cap_asof_T"], errors="coerce")
    pit["turnover_money"] = pit["money_D"] / pit["market_cap_asof_T"]
    pit["money_liquidity"] = pit["money_D"]
    pit["event_detection_status"] = "not_detected_not_upper_hit_or_comparator"
    pit["event_type"] = "not_event"
    pit["detection_block_reason"] = "none"
    pit["factor_continuity_status"] = "passed_provider_factor_continuity_guard"

    ohlcv_ok = (
        np.isfinite(pit["open_D"])
        & np.isfinite(pit["high_D"])
        & np.isfinite(pit["low_D"])
        & np.isfinite(pit["close_D"])
        & np.isfinite(pit["volume_D"])
        & np.isfinite(pit["money_D"])
    )
    liquidity_ok = pit["volume_D"].gt(0) & pit["money_D"].gt(0)
    max_gap = int(config["limit_detection"]["max_prev_trade_gap"])
    prev_ok = np.isfinite(pit["prev_close"]) & pit["prev_close"].gt(0) & np.isfinite(pit["prev_gap"]) & pit["prev_gap"].le(max_gap)
    factor_d_ok = np.isfinite(pit["factor_D"])
    factor_prev_ok = np.isfinite(pit["prev_factor"])
    tol = float(config["limit_detection"]["factor_continuity_tolerance"])
    factor_ratio = pit["factor_D"] / pit["prev_factor"]
    factor_cont_ok = factor_d_ok & factor_prev_ok & np.isfinite(factor_ratio) & ((factor_ratio - 1.0).abs() <= tol)

    missing_ohlcv = ~ohlcv_ok
    invalid_liq = ohlcv_ok & ~liquidity_ok
    missing_prev = ohlcv_ok & liquidity_ok & ~prev_ok
    missing_factor = ohlcv_ok & liquidity_ok & prev_ok & ~(factor_d_ok & factor_prev_ok)
    bad_factor = ohlcv_ok & liquidity_ok & prev_ok & (factor_d_ok & factor_prev_ok) & ~factor_cont_ok

    blockers = [
        (missing_ohlcv, "blocked_missing_event_day_ohlcv"),
        (invalid_liq, "blocked_invalid_event_day_liquidity"),
        (missing_prev, "blocked_missing_previous_traded_close"),
        (missing_factor, "blocked_missing_factor_for_limit_detection"),
        (bad_factor, "blocked_factor_discontinuity_for_limit_detection"),
    ]
    for mask, reason in blockers:
        pit.loc[mask, "event_detection_status"] = reason
        pit.loc[mask, "detection_block_reason"] = reason
        pit.loc[mask, "event_type"] = "not_event"
    pit.loc[missing_factor, "factor_continuity_status"] = "blocked_missing_factor_for_limit_detection"
    pit.loc[bad_factor, "factor_continuity_status"] = "blocked_factor_discontinuity_for_limit_detection"

    classifiable = ohlcv_ok & liquidity_ok & prev_ok & factor_cont_ok
    close_at_high = pit["close_high_gap"].le(float(config["limit_detection"]["close_high_tolerance"]))
    ret = pit["ret_to_prev_traded_close"]
    regular = (
        classifiable
        & ~pit["st_status_proxy"]
        & ret.ge(float(config["limit_detection"]["regular_lower_bound"]))
        & ret.le(float(config["limit_detection"]["regular_upper_bound"]))
        & close_at_high
    )
    st = (
        classifiable
        & pit["st_status_proxy"]
        & ret.ge(float(config["limit_detection"]["st_lower_bound"]))
        & ret.le(float(config["limit_detection"]["st_upper_bound"]))
        & close_at_high
    )
    nonlimit = (
        classifiable
        & ~pit["st_status_proxy"]
        & ret.ge(float(config["limit_detection"]["nonlimit_lower_bound"]))
        & ret.lt(float(config["limit_detection"]["nonlimit_upper_bound"]))
        & ~regular
    )
    pit.loc[regular, "event_type"] = PRIMARY_EVENT
    pit.loc[regular, "event_detection_status"] = "detected_regular_10pct_upper_close_hit"
    pit.loc[st, "event_type"] = ST_EVENT
    pit.loc[st, "event_detection_status"] = "detected_st_5pct_upper_close_hit_diagnostic"
    pit.loc[nonlimit, "event_type"] = COMPARATOR_EVENT
    pit.loc[nonlimit, "event_detection_status"] = "detected_nonlimit_high_return"
    pit["return_bucket_type"] = ""
    pit.loc[nonlimit & ret.ge(0.08) & ret.lt(0.09), "return_bucket_type"] = "return_bucket_8_9"
    pit.loc[nonlimit & ret.ge(0.09) & ret.lt(0.098), "return_bucket_type"] = "return_bucket_9_near_limit"

    pit["market_cap_percentile"] = pit.groupby("date")["market_cap_asof_T"].rank(method="first", pct=True)
    pit["turnover_percentile"] = pit.groupby("date")["turnover_money"].rank(method="first", pct=True)
    pit["money_liquidity_percentile"] = pit.groupby("date")["money_liquidity"].rank(method="first", pct=True)
    pit["size_bucket"] = tercile_from_percentile(pit["market_cap_percentile"])
    pit["turnover_bucket"] = tercile_from_percentile(pit["turnover_percentile"])
    pit["money_liquidity_bucket"] = tercile_from_percentile(pit["money_liquidity_percentile"])
    market_state = market_state_by_date(calendar, inputs["benchmark"]["close"])
    pit["market_state"] = pit["date"].map(market_state).fillna("unavailable")
    pit["event_month"] = pit["date"].dt.to_period("M").astype(str)
    pit["event_year"] = pit["date"].dt.year.astype(int)

    detected_regular = pit.loc[pit["event_type"].eq(PRIMARY_EVENT), ["date", "instrument"]].copy()
    cluster_map: dict[tuple[pd.Timestamp, str], tuple[str, str]] = {}
    for inst, group in detected_regular.sort_values(["instrument", "date"]).groupby("instrument", sort=True):
        last_pos = -999
        cluster_num = 0
        for _, row in group.iterrows():
            pos = int(calendar.get_loc(pd.Timestamp(row["date"])))
            if pos != last_pos + 1:
                cluster_num += 1
                position = "first_hit"
            else:
                position = "continuation_hit"
            cluster_id = f"{inst}_cluster_{cluster_num:04d}"
            cluster_map[(pd.Timestamp(row["date"]), inst)] = (cluster_id, position)
            last_pos = pos
    pit["cluster_id"] = ""
    pit["cluster_position"] = ""
    for idx, row in pit.loc[pit["event_type"].eq(PRIMARY_EVENT), ["date", "instrument"]].iterrows():
        cluster_id, position = cluster_map.get((pd.Timestamp(row["date"]), str(row["instrument"])), ("", ""))
        pit.at[idx, "cluster_id"] = cluster_id
        pit.at[idx, "cluster_position"] = position
    return pit


def next_calendar_date(calendar: pd.DatetimeIndex, date: pd.Timestamp, offset: int) -> pd.Timestamp | None:
    try:
        pos = int(calendar.get_loc(pd.Timestamp(date)))
    except KeyError:
        return None
    target = pos + offset
    if target < 0 or target >= len(calendar):
        return None
    return pd.Timestamp(calendar[target])


def one_price_locked(row: dict[str, float], tolerance: float) -> bool:
    values = np.array([row.get("open", np.nan), row.get("high", np.nan), row.get("low", np.nan), row.get("close", np.nan)], dtype="float64")
    if not np.isfinite(values).all() or np.nanmin(values) <= 0:
        return False
    return (float(np.nanmax(values) / np.nanmin(values) - 1.0) <= tolerance) and row.get("volume", 0.0) > 0


def scalar_lookup(frame: pd.DataFrame, date: pd.Timestamp | None, instrument: str) -> float:
    if date is None or instrument not in frame.columns or date not in frame.index:
        return math.nan
    try:
        return float(frame.at[date, instrument])
    except Exception:  # noqa: BLE001
        return math.nan


def benchmark_entry_price(benchmark: dict[str, pd.Series], variant: str, date: pd.Timestamp, d1: pd.Timestamp | None) -> float:
    if variant == "d0_close_oracle":
        return float(benchmark["close"].get(date, math.nan))
    if d1 is None:
        return math.nan
    if variant == "d1_open":
        return float(benchmark["open"].get(d1, math.nan))
    return float(benchmark["close"].get(d1, math.nan))


def build_event_path(config: dict[str, Any], inputs: dict[str, Any], detection: pd.DataFrame) -> pd.DataFrame:
    fields = inputs["fields"]
    calendar = inputs["calendar"]
    benchmark = inputs["benchmark"]
    detected = detection.loc[detection["event_type"].isin([PRIMARY_EVENT, ST_EVENT, COMPARATOR_EVENT])].copy()
    horizons = sorted(set(map(int, config["events"]["primary_report_horizons"] + config["events"]["primary_decision_horizons"] + config["events"]["diagnostic_horizons"])))
    entry_variants = list(config["events"]["entry_variants"])
    stresses = list(map(float, config["events"]["borrow_fee_stress_bps_per_trading_day"]))
    one_price_tol = float(config["limit_detection"]["one_price_lock_tolerance"])
    short_cost = float(config["execution"]["short_sell_cost_bps"]) / 10000.0
    cover_cost = float(config["execution"]["buy_to_cover_cost_bps"]) / 10000.0

    rows: list[dict[str, Any]] = []
    for event in detected.itertuples(index=False):
        date = pd.Timestamp(event.date)
        inst = str(event.instrument)
        d1 = next_calendar_date(calendar, date, 1)
        d1_values = {
            "open": scalar_lookup(fields["open"], d1, inst),
            "high": scalar_lookup(fields["high"], d1, inst),
            "low": scalar_lookup(fields["low"], d1, inst),
            "close": scalar_lookup(fields["close"], d1, inst),
            "volume": scalar_lookup(fields["volume"], d1, inst),
            "money": scalar_lookup(fields["money"], d1, inst),
        }
        d0_close = scalar_lookup(fields["close"], date, inst)
        d1_locked = one_price_locked(d1_values, one_price_tol)
        for variant in entry_variants:
            if variant == "d0_close_oracle":
                entry_date = date
                entry_price = d0_close
                entry_status = "complete" if np.isfinite(entry_price) and entry_price > 0 else "blocked_entry_missing_d1_open"
            else:
                entry_date = d1
                entry_price = d1_values["open"] if variant == "d1_open" else d1_values["close"]
                if d1 is None:
                    entry_status = "blocked_entry_nontrading_d1"
                elif not (np.isfinite(entry_price) and entry_price > 0):
                    entry_status = "blocked_entry_missing_d1_open"
                elif not (np.isfinite(d1_values["volume"]) and np.isfinite(d1_values["money"]) and d1_values["volume"] > 0 and d1_values["money"] > 0):
                    entry_status = "blocked_entry_nontrading_d1"
                elif d1_locked:
                    entry_status = "blocked_one_price_limit_locked"
                else:
                    entry_status = "complete"
            b_entry = benchmark_entry_price(benchmark, variant, date, d1)
            for horizon in horizons:
                exit_date = next_calendar_date(calendar, date, horizon)
                exit_price = scalar_lookup(fields["close"], exit_date, inst)
                b_exit = float(benchmark["close"].get(exit_date, math.nan)) if exit_date is not None else math.nan
                if exit_date is None:
                    exit_status = "blocked_incomplete_future_return_label"
                elif not (np.isfinite(exit_price) and exit_price > 0):
                    exit_status = "blocked_exit_missing_price"
                else:
                    exit_status = "complete"
                if entry_status == "complete" and exit_status == "complete" and np.isfinite(entry_price) and entry_price > 0:
                    stock_long = exit_price / entry_price - 1.0
                    gross_short = 1.0 - exit_price / entry_price
                    if np.isfinite(b_entry) and b_entry > 0 and np.isfinite(b_exit):
                        benchmark_long = b_exit / b_entry - 1.0
                    else:
                        benchmark_long = math.nan
                    market_hedged = gross_short + benchmark_long if np.isfinite(benchmark_long) else math.nan
                    after_cost = gross_short - short_cost - cover_cost
                else:
                    stock_long = math.nan
                    gross_short = math.nan
                    market_hedged = math.nan
                    after_cost = math.nan
                base = {
                    "split": event.split,
                    "date": date.date().isoformat(),
                    "instrument": inst,
                    "event_type": event.event_type,
                    "event_detection_status": event.event_detection_status,
                    "limit_detection_price_source": event.limit_detection_price_source,
                    "factor_continuity_status": event.factor_continuity_status,
                    "entry_variant": variant,
                    "entry_status": entry_status,
                    "horizon": int(horizon),
                    "exit_label_status": exit_status,
                    "prev_traded_day": event.prev_traded_day,
                    "ret_to_prev_traded_close": event.ret_to_prev_traded_close,
                    "close_high_gap": event.close_high_gap,
                    "cluster_id": event.cluster_id,
                    "cluster_position": event.cluster_position,
                    "st_status_proxy": bool(event.st_status_proxy),
                    "market_cap_asof_T": event.market_cap_asof_T,
                    "industry": event.industry,
                    "turnover_money": event.turnover_money,
                    "entry_date": entry_date.date().isoformat() if entry_date is not None else "",
                    "exit_date": exit_date.date().isoformat() if exit_date is not None else "",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "stock_long_return": stock_long,
                    "gross_short_return": gross_short,
                    "market_hedged_short_return": market_hedged,
                    "after_cost_short_return_ex_borrow": after_cost,
                }
                for stress in stresses:
                    row = dict(base)
                    row["borrow_fee_stress_bps_per_trading_day"] = int(stress)
                    row["after_cost_short_return_with_borrow_stress"] = after_cost - stress * horizon / 10000.0 if np.isfinite(after_cost) else math.nan
                    rows.append(row)
    return pd.DataFrame(rows)


def complete_base(event_path: pd.DataFrame) -> pd.DataFrame:
    return event_path.loc[
        event_path["borrow_fee_stress_bps_per_trading_day"].eq(0)
        & event_path["entry_status"].eq("complete")
        & event_path["exit_label_status"].eq("complete")
    ].copy()


def summarize_event_returns(event_path: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    base = complete_base(event_path)
    if base.empty:
        return pd.DataFrame()
    group_cols = ["split", "event_type", "entry_variant", "horizon"]
    for keys, group in base.groupby(group_cols, dropna=False):
        split, event_type, entry_variant, horizon = keys
        date_means = group.groupby("date", sort=True).agg(
            gross_short_return=("gross_short_return", "mean"),
            market_hedged_short_return=("market_hedged_short_return", "mean"),
            after_cost_short_return_ex_borrow=("after_cost_short_return_ex_borrow", "mean"),
        )
        stress_means = {}
        for stress in [2, 5, 10]:
            stress_values = group["after_cost_short_return_ex_borrow"] - stress * int(horizon) / 10000.0
            stress_means[stress] = float(stress_values.groupby(group["date"]).mean().mean()) if len(stress_values) else math.nan
        rows.append(
            {
                "split": split,
                "event_type": event_type,
                "entry_variant": entry_variant,
                "horizon": int(horizon),
                "event_count": int(len(group)),
                "instrument_count": int(group["instrument"].nunique()),
                "event_month_count": int(pd.to_datetime(group["date"]).dt.to_period("M").nunique()),
                "event_date_count": int(group["date"].nunique()),
                "event_weighted_mean_gross_short_return": float(group["gross_short_return"].mean()),
                "event_weighted_median_gross_short_return": float(group["gross_short_return"].median()),
                "event_weighted_positive_event_share": float((group["gross_short_return"] > 0).mean()),
                "date_weighted_mean_gross_short_return": float(date_means["gross_short_return"].mean()),
                "date_weighted_positive_event_date_share": float((date_means["gross_short_return"] > 0).mean()),
                "date_weighted_mean_market_hedged_short_return": float(date_means["market_hedged_short_return"].mean()),
                "date_weighted_mean_after_cost_short_return_ex_borrow": float(date_means["after_cost_short_return_ex_borrow"].mean()),
                "date_weighted_mean_after_cost_short_return_borrow_2bps": stress_means[2],
                "date_weighted_mean_after_cost_short_return_borrow_5bps": stress_means[5],
                "date_weighted_mean_after_cost_short_return_borrow_10bps": stress_means[10],
                "newey_west_observation_unit": "event_date_mean_return_series",
                "newey_west_lag": int(min(int(horizon), 20)),
                "newey_west_tstat_date_weighted_mean_gross_short_return": newey_west_tstat(date_means["gross_short_return"], min(int(horizon), 20)),
                "newey_west_tstat_date_weighted_mean_market_hedged_short_return": newey_west_tstat(date_means["market_hedged_short_return"], min(int(horizon), 20)),
                "newey_west_tstat_date_weighted_mean_after_cost_ex_borrow": newey_west_tstat(date_means["after_cost_short_return_ex_borrow"], min(int(horizon), 20)),
            }
        )
    return pd.DataFrame(rows)


def build_event_count_by_split(detection: pd.DataFrame) -> pd.DataFrame:
    return (
        detection.groupby(["split", "candidate_scope", "event_type", "event_detection_status", "detection_block_reason"], dropna=False)
        .size()
        .reset_index(name="candidate_count")
    )


def build_entry_exit_block_audit(event_path: pd.DataFrame) -> pd.DataFrame:
    base = event_path.loc[event_path["borrow_fee_stress_bps_per_trading_day"].eq(0)].copy()
    return (
        base.groupby(["split", "event_type", "entry_variant", "horizon", "entry_status", "exit_label_status"], dropna=False)
        .size()
        .reset_index(name="event_path_row_count")
    )


def build_cluster_diagnostics(detection: pd.DataFrame) -> pd.DataFrame:
    reg = detection.loc[detection["event_type"].eq(PRIMARY_EVENT)].copy()
    if reg.empty:
        return pd.DataFrame(columns=["split", "cluster_position", "event_count", "cluster_count", "mean_cluster_length", "max_cluster_length"])
    cluster_lengths = reg.groupby(["split", "cluster_id"]).size().reset_index(name="cluster_length")
    rows = []
    for keys, group in reg.groupby(["split", "cluster_position"], dropna=False):
        split, position = keys
        split_clusters = cluster_lengths.loc[cluster_lengths["split"].eq(split)]
        rows.append(
            {
                "split": split,
                "cluster_position": position,
                "event_count": int(len(group)),
                "cluster_count": int(split_clusters["cluster_id"].nunique()),
                "mean_cluster_length": float(split_clusters["cluster_length"].mean()) if not split_clusters.empty else math.nan,
                "max_cluster_length": int(split_clusters["cluster_length"].max()) if not split_clusters.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def build_match_map(detection: pd.DataFrame) -> pd.DataFrame:
    events = detection.loc[detection["event_type"].isin([PRIMARY_EVENT, COMPARATOR_EVENT])].copy()
    rows: list[dict[str, Any]] = []
    for date, group in events.groupby("date", sort=True):
        uppers = group.loc[group["event_type"].eq(PRIMARY_EVENT)].sort_values("instrument").copy()
        comps = group.loc[group["event_type"].eq(COMPARATOR_EVENT)].sort_values("instrument").copy()
        if uppers.empty:
            continue
        if comps.empty:
            for upper in uppers.itertuples(index=False):
                rows.append(
                    {
                        "split": upper.split,
                        "date": pd.Timestamp(date).date().isoformat(),
                        "upper_hit_instrument": upper.instrument,
                        "matched_instrument": "",
                        "match_status": "unmatched_no_same_date_candidate",
                        "unmatched_reason": "no_same_date_nonlimit_high_return_candidate",
                        "same_industry_match": False,
                        "upper_hit_market_cap_percentile": upper.market_cap_percentile,
                        "matched_market_cap_percentile": math.nan,
                        "size_percentile_abs_diff": math.nan,
                    }
                )
            continue
        valid_upper = uppers[np.isfinite(uppers["market_cap_percentile"])]
        invalid_upper = uppers.loc[~uppers.index.isin(valid_upper.index)]
        used_upper: set[str] = set()
        used_comp: set[str] = set()

        def greedy_assign(candidate_pairs: list[dict[str, Any]], status: str) -> None:
            for pair in sorted(candidate_pairs, key=lambda x: (x["size_percentile_abs_diff"], x["upper_hit_instrument"], x["matched_instrument"])):
                if pair["upper_hit_instrument"] in used_upper or pair["matched_instrument"] in used_comp:
                    continue
                used_upper.add(pair["upper_hit_instrument"])
                used_comp.add(pair["matched_instrument"])
                pair["match_status"] = status
                pair["unmatched_reason"] = ""
                rows.append(pair)

        same_pairs = []
        for upper in valid_upper.itertuples(index=False):
            comp_subset = comps.loc[
                comps["industry"].eq(upper.industry)
                & np.isfinite(comps["market_cap_percentile"])
            ]
            for comp in comp_subset.itertuples(index=False):
                same_pairs.append(
                    {
                        "split": upper.split,
                        "date": pd.Timestamp(date).date().isoformat(),
                        "upper_hit_instrument": upper.instrument,
                        "matched_instrument": comp.instrument,
                        "same_industry_match": True,
                        "upper_hit_market_cap_percentile": upper.market_cap_percentile,
                        "matched_market_cap_percentile": comp.market_cap_percentile,
                        "size_percentile_abs_diff": abs(float(upper.market_cap_percentile) - float(comp.market_cap_percentile)),
                    }
                )
        greedy_assign(same_pairs, "matched_same_industry")

        size_pairs = []
        for upper in valid_upper.itertuples(index=False):
            if upper.instrument in used_upper:
                continue
            for comp in comps.loc[np.isfinite(comps["market_cap_percentile"])].itertuples(index=False):
                if comp.instrument in used_comp:
                    continue
                size_pairs.append(
                    {
                        "split": upper.split,
                        "date": pd.Timestamp(date).date().isoformat(),
                        "upper_hit_instrument": upper.instrument,
                        "matched_instrument": comp.instrument,
                        "same_industry_match": False,
                        "upper_hit_market_cap_percentile": upper.market_cap_percentile,
                        "matched_market_cap_percentile": comp.market_cap_percentile,
                        "size_percentile_abs_diff": abs(float(upper.market_cap_percentile) - float(comp.market_cap_percentile)),
                    }
                )
        greedy_assign(size_pairs, "matched_same_date_size_only")

        for upper in invalid_upper.itertuples(index=False):
            rows.append(
                {
                    "split": upper.split,
                    "date": pd.Timestamp(date).date().isoformat(),
                    "upper_hit_instrument": upper.instrument,
                    "matched_instrument": "",
                    "match_status": "unmatched_missing_match_fields",
                    "unmatched_reason": "upper_hit_missing_market_cap_percentile",
                    "same_industry_match": False,
                    "upper_hit_market_cap_percentile": upper.market_cap_percentile,
                    "matched_market_cap_percentile": math.nan,
                    "size_percentile_abs_diff": math.nan,
                }
            )
        for upper in valid_upper.itertuples(index=False):
            if upper.instrument in used_upper:
                continue
            reason = "same_date_candidates_already_used" if len(comps) else "no_same_date_nonlimit_high_return_candidate"
            rows.append(
                {
                    "split": upper.split,
                    "date": pd.Timestamp(date).date().isoformat(),
                    "upper_hit_instrument": upper.instrument,
                    "matched_instrument": "",
                    "match_status": "unmatched_candidate_already_used" if len(comps) else "unmatched_no_same_date_candidate",
                    "unmatched_reason": reason,
                    "same_industry_match": False,
                    "upper_hit_market_cap_percentile": upper.market_cap_percentile,
                    "matched_market_cap_percentile": math.nan,
                    "size_percentile_abs_diff": math.nan,
                }
            )
    return pd.DataFrame(rows)


def build_matched_pairs(event_path: pd.DataFrame, match_map: pd.DataFrame) -> pd.DataFrame:
    if match_map.empty:
        return pd.DataFrame()
    base = event_path.loc[event_path["borrow_fee_stress_bps_per_trading_day"].eq(0)].copy()
    returns = base.set_index(["date", "instrument", "event_type", "entry_variant", "horizon"])["gross_short_return"].to_dict()
    variants = sorted(base["entry_variant"].dropna().unique().tolist())
    horizons = sorted(base["horizon"].dropna().astype(int).unique().tolist())
    rows = []
    for match in match_map.itertuples(index=False):
        for variant in variants:
            for horizon in horizons:
                upper_ret = returns.get((match.date, match.upper_hit_instrument, PRIMARY_EVENT, variant, horizon), math.nan)
                matched_ret = (
                    returns.get((match.date, match.matched_instrument, COMPARATOR_EVENT, variant, horizon), math.nan)
                    if match.matched_instrument
                    else math.nan
                )
                rows.append(
                    {
                        "split": match.split,
                        "date": match.date,
                        "entry_variant": variant,
                        "upper_hit_instrument": match.upper_hit_instrument,
                        "matched_instrument": match.matched_instrument,
                        "match_status": match.match_status,
                        "unmatched_reason": match.unmatched_reason,
                        "same_industry_match": bool(match.same_industry_match),
                        "upper_hit_market_cap_percentile": match.upper_hit_market_cap_percentile,
                        "matched_market_cap_percentile": match.matched_market_cap_percentile,
                        "size_percentile_abs_diff": match.size_percentile_abs_diff,
                        "horizon": int(horizon),
                        "upper_hit_gross_short_return": upper_ret,
                        "matched_gross_short_return": matched_ret,
                        "incremental_short_return": upper_ret - matched_ret if np.isfinite(upper_ret) and np.isfinite(matched_ret) else math.nan,
                    }
                )
    return pd.DataFrame(rows)


def summarize_comparator(matched_pairs: pd.DataFrame, event_path: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    base = complete_base(event_path)
    upper_complete = base.loc[base["event_type"].eq(PRIMARY_EVENT)]
    min_share = float(config["gates"]["comparator_matched_event_share_min"])
    group_cols = ["split", "entry_variant", "horizon"]
    all_keys = upper_complete[group_cols].drop_duplicates().itertuples(index=False)
    for key in all_keys:
        split, entry_variant, horizon = key
        denom_events = upper_complete.loc[
            upper_complete["split"].eq(split)
            & upper_complete["entry_variant"].eq(entry_variant)
            & upper_complete["horizon"].eq(horizon)
        ][["date", "instrument"]].drop_duplicates()
        denom = int(len(denom_events))
        pairs = matched_pairs.loc[
            matched_pairs["split"].eq(split)
            & matched_pairs["entry_variant"].eq(entry_variant)
            & matched_pairs["horizon"].eq(horizon)
        ].copy()
        complete_pairs = pairs.loc[
            pairs["match_status"].isin(["matched_same_industry", "matched_same_date_size_only"])
            & np.isfinite(pairs["upper_hit_gross_short_return"])
            & np.isfinite(pairs["matched_gross_short_return"])
        ].copy()
        matched_count = int(len(complete_pairs))
        share = matched_count / denom if denom else math.nan
        if denom == 0:
            status = "not_evaluable_no_upper_hit_events"
        elif matched_count == 0:
            status = "fail_no_same_date_candidates"
        elif share >= min_share:
            status = "pass"
        else:
            status = "fail_insufficient_matched_event_share"
        if complete_pairs.empty:
            event_weighted = math.nan
            date_weighted = math.nan
            nw = math.nan
            same_ind_share = math.nan
            median_diff = math.nan
        else:
            event_weighted = float(complete_pairs["incremental_short_return"].mean())
            date_series = complete_pairs.groupby("date")["incremental_short_return"].mean()
            date_weighted = float(date_series.mean())
            nw = newey_west_tstat(date_series, min(int(horizon), 20))
            same_ind_share = float(complete_pairs["same_industry_match"].mean())
            median_diff = float(complete_pairs["size_percentile_abs_diff"].median())
        rows.append(
            {
                "split": split,
                "entry_variant": entry_variant,
                "horizon": int(horizon),
                "upper_hit_event_count_for_comparator": denom,
                "matched_upper_hit_event_count": matched_count,
                "matched_event_share": share,
                "matched_same_industry_share": same_ind_share,
                "median_size_percentile_abs_diff": median_diff,
                "comparator_coverage_status": status,
                "event_weighted_mean_incremental_short_return_vs_nonlimit_high_return": event_weighted,
                "date_weighted_mean_incremental_short_return_vs_nonlimit_high_return": date_weighted,
                "newey_west_tstat_date_weighted_mean_incremental_short_return": nw,
            }
        )
    return pd.DataFrame(rows)


def build_calendar_time_returns(config: dict[str, Any], inputs: dict[str, Any], event_path: pd.DataFrame) -> pd.DataFrame:
    fields = inputs["fields"]
    calendar = inputs["calendar"]
    max_weight = float(config["calendar_time"]["max_abs_weight_per_instrument"])
    rows = []
    events = event_path.loc[
        event_path["borrow_fee_stress_bps_per_trading_day"].eq(0)
        & event_path["event_type"].eq(PRIMARY_EVENT)
        & event_path["entry_variant"].eq("d1_open")
        & event_path["horizon"].isin(config["calendar_time"]["horizons"])
        & event_path["entry_status"].eq("complete")
        & event_path["exit_label_status"].eq("complete")
    ].copy()
    if events.empty:
        return pd.DataFrame()
    events["entry_date_ts"] = pd.to_datetime(events["entry_date"])
    events["exit_date_ts"] = pd.to_datetime(events["exit_date"])
    for horizon, hgroup in events.groupby("horizon", sort=True):
        date_min = hgroup["entry_date_ts"].min()
        date_max = hgroup["exit_date_ts"].max()
        for date in calendar[(calendar >= date_min) & (calendar <= date_max)]:
            active = hgroup.loc[hgroup["entry_date_ts"].le(date) & hgroup["exit_date_ts"].ge(date)].copy()
            if active.empty:
                continue
            inst_returns: dict[str, float] = {}
            inst_weight: dict[str, float] = {}
            raw_weight = 1.0 / len(active)
            prev_date = next_calendar_date(calendar, pd.Timestamp(date), -1)
            for event in active.itertuples(index=False):
                inst = str(event.instrument)
                if pd.Timestamp(date) == pd.Timestamp(event.entry_date_ts):
                    entry = scalar_lookup(fields["open"], pd.Timestamp(date), inst)
                    close = scalar_lookup(fields["close"], pd.Timestamp(date), inst)
                    daily_short = 1.0 - close / entry if np.isfinite(entry) and entry > 0 and np.isfinite(close) else math.nan
                else:
                    prev_close = scalar_lookup(fields["close"], prev_date, inst)
                    close = scalar_lookup(fields["close"], pd.Timestamp(date), inst)
                    daily_short = 1.0 - close / prev_close if np.isfinite(prev_close) and prev_close > 0 and np.isfinite(close) else math.nan
                if not np.isfinite(daily_short):
                    continue
                inst_returns[inst] = daily_short
                inst_weight[inst] = inst_weight.get(inst, 0.0) + raw_weight
            if not inst_weight:
                continue
            gross = sum(inst_weight[k] * inst_returns[k] for k in inst_weight)
            capped = {k: min(v, max_weight) for k, v in inst_weight.items()}
            scale = sum(capped.values())
            if scale > 0 and bool(config["calendar_time"]["renormalize_after_name_cap"]):
                capped = {k: v / scale for k, v in capped.items()}
            capped_return = sum(capped[k] * inst_returns[k] for k in capped)
            rows.append(
                {
                    "date": pd.Timestamp(date).date().isoformat(),
                    "calendar_date_split": split_for_date(pd.Timestamp(date), config),
                    "horizon": int(horizon),
                    "active_event_count": int(len(active)),
                    "active_instrument_count": int(len(inst_weight)),
                    "max_abs_weight_per_instrument": max_weight,
                    "gross_short_return": gross,
                    "name_capped_gross_short_return": capped_return,
                }
            )
    return pd.DataFrame(rows)


def build_attribution(detection: pd.DataFrame, event_path: pd.DataFrame) -> pd.DataFrame:
    attrs = [
        "cluster_position",
        "market_state",
        "industry",
        "size_bucket",
        "turnover_bucket",
        "money_liquidity_bucket",
        "event_month",
        "event_year",
    ]
    det_cols = ["date", "instrument"] + attrs
    det = detection.loc[detection["event_type"].eq(PRIMARY_EVENT), det_cols].copy()
    det["date"] = pd.to_datetime(det["date"]).dt.date.astype(str)
    base = complete_base(event_path)
    base = base.loc[base["event_type"].eq(PRIMARY_EVENT) & base["entry_variant"].eq("d1_open") & base["horizon"].isin([5, 10, 20])].copy()
    if base.empty:
        return pd.DataFrame()
    base = base.drop(columns=[c for c in attrs if c in base.columns])
    merged = base.merge(det, on=["date", "instrument"], how="left")
    rows = []
    for axis in attrs:
        for keys, group in merged.groupby(["split", "horizon", axis], dropna=False):
            split, horizon, value = keys
            date_means = group.groupby("date")["gross_short_return"].mean()
            rows.append(
                {
                    "state_axis": axis,
                    "state_value": str(value),
                    "split": split,
                    "entry_variant": "d1_open",
                    "horizon": int(horizon),
                    "event_count": int(len(group)),
                    "event_date_count": int(group["date"].nunique()),
                    "date_weighted_mean_gross_short_return": float(date_means.mean()),
                    "date_weighted_positive_event_date_share": float((date_means > 0).mean()),
                    "date_weighted_mean_after_cost_short_return_ex_borrow": float(group.groupby("date")["after_cost_short_return_ex_borrow"].mean().mean()),
                }
            )
    return pd.DataFrame(rows)


def build_availability_manifest(config: dict[str, Any], detection: pd.DataFrame) -> pd.DataFrame:
    split_days = detection.groupby("split")["date"].nunique().to_dict()
    cols = [
        "input_id",
        "paper_required_input",
        "local_source",
        "source_path",
        "source_sha256",
        "availability_status",
        "official_unadjusted_daily_ohlc_status",
        "replication_action",
        "local_proxy_id",
        "asof_policy",
        "coverage_train_days",
        "coverage_validation_days",
        "coverage_robustness_days",
        "fallback_reason",
        "block_reason",
    ]
    official_path = str(config["data_sources"].get("official_unadjusted_daily_ohlc_path", "") or "")
    official_absent = not official_path
    rows = [
        {
            "input_id": "official_unadjusted_daily_ohlc_for_limit_detection",
            "paper_required_input": "official unadjusted daily OHLC for exchange price-limit detection",
            "local_source": official_path or "not available locally",
            "source_path": official_path,
            "source_sha256": file_hash(topic_path(official_path)) if official_path else "",
            "availability_status": "missing_required_price_fields" if official_absent else "available_full",
            "official_unadjusted_daily_ohlc_status": "absent_used_provider_fallback" if official_absent else "available_full_range",
            "replication_action": "remove" if official_absent else "retain",
            "local_proxy_id": "provider_ohlc_with_factor_continuity_guard" if official_absent else "official_unadjusted_daily_ohlc_if_available",
            "asof_policy": "event day OHLC only",
            "fallback_reason": "use_provider_ohlc_with_factor_continuity_guard" if official_absent else "",
            "block_reason": "official_unadjusted_daily_ohlc_absent" if official_absent else "",
        },
        {
            "input_id": "provider_daily_ohlcv",
            "paper_required_input": "daily stock OHLCV",
            "local_source": "data/qlib/cn_data_pit/features/*",
            "source_path": config["data_sources"]["qlib_provider_uri"],
            "source_sha256": directory_hash(topic_path(config["data_sources"]["qlib_provider_uri"]) / "calendars"),
            "availability_status": "available_full",
            "official_unadjusted_daily_ohlc_status": "absent_used_provider_fallback",
            "replication_action": "retain_local_proxy",
            "local_proxy_id": "provider_adjusted_ohlcv_factor_guarded_limit_detection",
            "asof_policy": "event day and path label dates only",
            "fallback_reason": "",
            "block_reason": "",
        },
        {
            "input_id": "pit_mcap500_mainboard_universe",
            "paper_required_input": "stock universe and listing status",
            "local_source": config["data_sources"]["pit_universe_path"],
            "source_path": config["data_sources"]["pit_universe_path"],
            "source_sha256": file_hash(topic_path(config["data_sources"]["pit_universe_path"])),
            "availability_status": "available_full",
            "official_unadjusted_daily_ohlc_status": "absent_used_provider_fallback",
            "replication_action": "retain_local_proxy",
            "local_proxy_id": "PIT_mcap500_mainboard_not_full_SZSE_sample",
            "asof_policy": "PIT membership on event date",
            "fallback_reason": "",
            "block_reason": "full 2012-2015 SZSE account sample unavailable",
        },
        {
            "input_id": "large_investor_netbuy",
            "paper_required_input": "account-level NetBuy by investor group",
            "local_source": "not available locally",
            "source_path": "",
            "source_sha256": "",
            "availability_status": "missing_required_account_level_data",
            "official_unadjusted_daily_ohlc_status": "absent_used_provider_fallback",
            "replication_action": "remove",
            "local_proxy_id": "",
            "asof_policy": "",
            "fallback_reason": "",
            "block_reason": "account-level trading data absent",
        },
        {
            "input_id": "borrow_availability_and_fee",
            "paper_required_input": "short-sale borrow availability and borrow fees",
            "local_source": "not available locally",
            "source_path": "",
            "source_sha256": "",
            "availability_status": "missing_required_borrow_data",
            "official_unadjusted_daily_ohlc_status": "absent_used_provider_fallback",
            "replication_action": "diagnostic_only",
            "local_proxy_id": "borrow_fee_stress_only",
            "asof_policy": "",
            "fallback_reason": "",
            "block_reason": "borrow data absent",
        },
        {
            "input_id": "intraday_limit_queue",
            "paper_required_input": "intraday limit-order-book queue position",
            "local_source": "not available locally",
            "source_path": "",
            "source_sha256": "",
            "availability_status": "missing_required_intraday_data",
            "official_unadjusted_daily_ohlc_status": "absent_used_provider_fallback",
            "replication_action": "remove",
            "local_proxy_id": "",
            "asof_policy": "",
            "fallback_reason": "",
            "block_reason": "intraday order book absent",
        },
        {
            "input_id": "market_to_book_for_dgtw",
            "paper_required_input": "market-to-book ratio for DGTW adjustment",
            "local_source": "not available locally",
            "source_path": "",
            "source_sha256": "",
            "availability_status": "missing_required_fundamental_control",
            "official_unadjusted_daily_ohlc_status": "absent_used_provider_fallback",
            "replication_action": "retain_local_proxy",
            "local_proxy_id": "size_industry_turnover_attribution",
            "asof_policy": "event-date controls only",
            "fallback_reason": "",
            "block_reason": "market-to-book unavailable",
        },
    ]
    for row in rows:
        row["coverage_train_days"] = int(split_days.get("train", 0))
        row["coverage_validation_days"] = int(split_days.get("validation", 0))
        row["coverage_robustness_days"] = int(split_days.get("robustness", 0))
    return pd.DataFrame(rows, columns=cols)


def get_summary_row(summary: pd.DataFrame, split: str, horizon: int) -> pd.Series | None:
    part = summary.loc[
        summary["split"].eq(split)
        & summary["event_type"].eq(PRIMARY_EVENT)
        & summary["entry_variant"].eq("d1_open")
        & summary["horizon"].eq(horizon)
    ]
    return part.iloc[0] if not part.empty else None


def get_comparator_row(comp: pd.DataFrame, split: str, horizon: int) -> pd.Series | None:
    part = comp.loc[comp["split"].eq(split) & comp["entry_variant"].eq("d1_open") & comp["horizon"].eq(horizon)]
    return part.iloc[0] if not part.empty else None


def gate_item(
    gate_id: str,
    gate_group: str,
    split: str,
    event_type: str,
    entry_variant: str,
    horizon: int | str,
    metric_name: str,
    observed_value: Any,
    threshold_value: Any,
    comparison_operator: str,
    denominator: Any,
    numerator: Any,
    gate_status: str,
    block_reason: str,
    source_artifact: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "gate_group": gate_group,
        "split": split,
        "event_type": event_type,
        "entry_variant": entry_variant,
        "horizon": horizon,
        "metric_name": metric_name,
        "observed_value": observed_value,
        "threshold_value": threshold_value,
        "comparison_operator": comparison_operator,
        "denominator": denominator,
        "numerator": numerator,
        "gate_status": gate_status,
        "block_reason": block_reason,
        "source_artifact": source_artifact,
    }


def determine_validation(
    config: dict[str, Any],
    detection: pd.DataFrame,
    event_path: pd.DataFrame,
    summary: pd.DataFrame,
    comparator: pd.DataFrame,
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    gate_results: list[dict[str, Any]] = []
    min_events = int(config["gates"]["minimum_regular_upper_hit_event_count"])
    min_months = int(config["gates"]["minimum_event_month_count"])
    min_entry_share = float(config["gates"]["primary_entry_complete_share_min"])
    min_label_share = float(config["gates"]["primary_horizon_label_complete_share_min"])
    pos_share_min = float(config["gates"]["date_weighted_positive_event_date_share_min"])
    nw_min = float(config["gates"]["validation_newey_west_tstat_min"])
    comp_share_min = float(config["gates"]["comparator_matched_event_share_min"])
    regular = detection.loc[detection["event_type"].eq(PRIMARY_EVENT)].copy()
    base = event_path.loc[event_path["borrow_fee_stress_bps_per_trading_day"].eq(0)].copy()
    entry_unique = base.loc[base["event_type"].eq(PRIMARY_EVENT) & base["entry_variant"].eq("d1_open") & base["horizon"].eq(5)]
    min_sample_pass = True
    support_pass: dict[tuple[str, int], bool] = {}
    comparator_coverage_pass: dict[tuple[str, int], bool] = {}
    comparator_direction_pass: dict[tuple[str, int], bool] = {}
    validation_directional_pass: dict[int, bool] = {}

    for split in ["validation", "robustness"]:
        reg_split = regular.loc[regular["split"].eq(split)]
        event_count = int(len(reg_split))
        event_months = int(pd.to_datetime(reg_split["date"]).dt.to_period("M").nunique()) if event_count else 0
        status = "pass" if event_count >= min_events else "fail"
        min_sample_pass &= status == "pass"
        gate_results.append(gate_item(f"{split}_regular_upper_hit_event_count", "minimum_sample", split, PRIMARY_EVENT, "d1_open", "all", "regular_upper_hit_event_count", event_count, min_events, ">=", event_count, event_count, status, "" if status == "pass" else "insufficient_regular_upper_hit_events", "r12_detection_candidate_audit.csv"))
        status = "pass" if event_months >= min_months else "fail"
        min_sample_pass &= status == "pass"
        gate_results.append(gate_item(f"{split}_event_month_count", "minimum_sample", split, PRIMARY_EVENT, "d1_open", "all", "event_month_count", event_months, min_months, ">=", event_count, event_months, status, "" if status == "pass" else "insufficient_event_months", "r12_detection_candidate_audit.csv"))

        entry_split = entry_unique.loc[entry_unique["split"].eq(split)]
        entry_complete = int(entry_split["entry_status"].eq("complete").sum())
        entry_denom = event_count
        entry_share = entry_complete / entry_denom if entry_denom else math.nan
        status = "pass" if np.isfinite(entry_share) and entry_share >= min_entry_share else "fail"
        min_sample_pass &= status == "pass"
        gate_results.append(gate_item(f"{split}_primary_entry_complete_share", "minimum_sample", split, PRIMARY_EVENT, "d1_open", "all", "primary_entry_complete_share", entry_share, min_entry_share, ">=", entry_denom, entry_complete, status, "" if status == "pass" else "insufficient_primary_entry_completeness", "r12_event_path_returns.csv"))

        for horizon in [5, 10, 20]:
            h_rows = base.loc[
                base["split"].eq(split)
                & base["event_type"].eq(PRIMARY_EVENT)
                & base["entry_variant"].eq("d1_open")
                & base["horizon"].eq(horizon)
            ]
            label_num = int((h_rows["entry_status"].eq("complete") & h_rows["exit_label_status"].eq("complete")).sum())
            label_denom = entry_complete
            label_share = label_num / label_denom if label_denom else math.nan
            status = "pass" if np.isfinite(label_share) and label_share >= min_label_share else "fail"
            min_sample_pass &= status == "pass"
            gate_results.append(gate_item(f"{split}_primary_horizon_label_complete_share_H{horizon}", "minimum_sample", split, PRIMARY_EVENT, "d1_open", horizon, "primary_horizon_label_complete_share", label_share, min_label_share, ">=", label_denom, label_num, status, "" if status == "pass" else "insufficient_horizon_label_completeness", "r12_event_path_returns.csv"))

    for split in ["validation", "robustness"]:
        for horizon in [10, 20]:
            row = get_summary_row(summary, split, horizon)
            metrics = {
                "date_weighted_mean_gross_short_return": (row["date_weighted_mean_gross_short_return"] if row is not None else math.nan, 0.0, ">"),
                "date_weighted_mean_after_cost_short_return_ex_borrow": (row["date_weighted_mean_after_cost_short_return_ex_borrow"] if row is not None else math.nan, 0.0, ">"),
                "date_weighted_positive_event_date_share": (row["date_weighted_positive_event_date_share"] if row is not None else math.nan, pos_share_min, ">="),
            }
            split_support = True
            for metric, (obs, threshold, op) in metrics.items():
                passed = bool(np.isfinite(obs) and (obs > threshold if op == ">" else obs >= threshold))
                split_support &= passed
                gate_results.append(gate_item(f"{split}_H{horizon}_{metric}", "support", split, PRIMARY_EVENT, "d1_open", horizon, metric, obs, threshold, op, row["event_date_count"] if row is not None else 0, "", "pass" if passed else "fail", "" if passed else "support_metric_failed", "r12_short_return_summary_by_horizon.csv"))
            if split == "validation":
                obs = row["newey_west_tstat_date_weighted_mean_gross_short_return"] if row is not None else math.nan
                passed = bool(np.isfinite(obs) and obs >= nw_min)
                split_support &= passed
                gate_results.append(gate_item(f"{split}_H{horizon}_newey_west_tstat", "support", split, PRIMARY_EVENT, "d1_open", horizon, "newey_west_tstat_date_weighted_mean_gross_short_return", obs, nw_min, ">=", row["event_date_count"] if row is not None else 0, "", "pass" if passed else "fail", "" if passed else "validation_tstat_failed", "r12_short_return_summary_by_horizon.csv"))
            support_pass[(split, horizon)] = split_support

            comp_row = get_comparator_row(comparator, split, horizon)
            comp_status = str(comp_row["comparator_coverage_status"]) if comp_row is not None else "not_evaluable_no_upper_hit_events"
            matched_share = comp_row["matched_event_share"] if comp_row is not None else math.nan
            comp_cov = bool(comp_status == "pass" and np.isfinite(matched_share) and matched_share >= comp_share_min)
            comparator_coverage_pass[(split, horizon)] = comp_cov
            gate_results.append(gate_item(f"{split}_H{horizon}_comparator_coverage", "comparator_coverage", split, PRIMARY_EVENT, "d1_open", horizon, "matched_event_share", matched_share, comp_share_min, ">=", comp_row["upper_hit_event_count_for_comparator"] if comp_row is not None else 0, comp_row["matched_upper_hit_event_count"] if comp_row is not None else 0, "pass" if comp_cov else "fail", "" if comp_cov else comp_status, "r12_upper_hit_vs_nonlimit_high_return_summary.csv"))
            inc = comp_row["date_weighted_mean_incremental_short_return_vs_nonlimit_high_return"] if comp_row is not None else math.nan
            comp_dir = bool(np.isfinite(inc) and inc > 0)
            comparator_direction_pass[(split, horizon)] = comp_dir
            gate_results.append(gate_item(f"{split}_H{horizon}_comparator_direction", "comparator_direction", split, PRIMARY_EVENT, "d1_open", horizon, "date_weighted_mean_incremental_short_return_vs_nonlimit_high_return", inc, 0.0, ">", comp_row["matched_upper_hit_event_count"] if comp_row is not None else 0, "", "pass" if comp_dir else "fail", "" if comp_dir else "comparator_direction_failed", "r12_upper_hit_vs_nonlimit_high_return_summary.csv"))

    for horizon in [10, 20]:
        val_row = get_summary_row(summary, "validation", horizon)
        comp_row = get_comparator_row(comparator, "validation", horizon)
        gross_ok = val_row is not None and np.isfinite(val_row["date_weighted_mean_gross_short_return"]) and val_row["date_weighted_mean_gross_short_return"] > 0
        inc_ok = comp_row is not None and np.isfinite(comp_row["date_weighted_mean_incremental_short_return_vs_nonlimit_high_return"]) and comp_row["date_weighted_mean_incremental_short_return_vs_nonlimit_high_return"] > 0
        validation_directional_pass[horizon] = bool(gross_ok and inc_ok)

    if not min_sample_pass:
        decision = "r12_not_evaluable_insufficient_limit_up_events"
    elif not all(comparator_coverage_pass.get((split, h), False) for split in ["validation", "robustness"] for h in [10, 20]):
        decision = "r12_not_evaluable_insufficient_comparator_coverage"
    elif all(
        support_pass.get((split, h), False)
        and comparator_coverage_pass.get((split, h), False)
        and comparator_direction_pass.get((split, h), False)
        for split in ["validation", "robustness"]
        for h in [10, 20]
    ):
        decision = "r12_short_after_limit_up_diagnostic_supported_not_executable"
    elif any(validation_directional_pass.values()):
        decision = "r12_short_after_limit_up_descriptive_only"
    else:
        decision = "r12_short_after_limit_up_not_supported"

    meta = {
        "minimum_sample_pass": min_sample_pass,
        "support_pass": {f"{k[0]}_H{k[1]}": v for k, v in support_pass.items()},
        "comparator_coverage_pass": {f"{k[0]}_H{k[1]}": v for k, v in comparator_coverage_pass.items()},
        "comparator_direction_pass": {f"{k[0]}_H{k[1]}": v for k, v in comparator_direction_pass.items()},
        "validation_directional_pass": {f"H{k}": v for k, v in validation_directional_pass.items()},
    }
    return decision, gate_results, meta


def final_report(
    paths: Paths,
    config: dict[str, Any],
    decision: str,
    detection: pd.DataFrame,
    summary: pd.DataFrame,
    comparator: pd.DataFrame,
    gate_results: list[dict[str, Any]],
    run_meta: dict[str, Any],
) -> None:
    gates = pd.DataFrame(gate_results)
    primary = summary.loc[
        summary["event_type"].eq(PRIMARY_EVENT)
        & summary["entry_variant"].eq("d1_open")
        & summary["horizon"].isin([5, 10, 20])
        & summary["split"].isin(["validation", "robustness"])
    ].copy()
    comp = comparator.loc[
        comparator["entry_variant"].eq("d1_open")
        & comparator["horizon"].isin([10, 20])
        & comparator["split"].isin(["validation", "robustness"])
    ].copy()

    def md_table(df: pd.DataFrame, cols: list[str]) -> str:
        if df.empty:
            return "_empty_"
        out = df[cols].copy()
        for col in out.columns:
            if pd.api.types.is_float_dtype(out[col]):
                if "tstat" in col or "t_stat" in col:
                    out[col] = out[col].map(lambda x: fmt_num(x, 3))
                elif "return" in col or "share" in col:
                    out[col] = out[col].map(lambda x: fmt_pct(x, 3))
                else:
                    out[col] = out[col].map(lambda x: fmt_num(x, 3))
        return out.to_markdown(index=False)

    event_counts = detection.loc[detection["event_type"].eq(PRIMARY_EVENT)].groupby("split").size().to_dict()
    blocked_factor = int(detection["event_detection_status"].eq("blocked_factor_discontinuity_for_limit_detection").sum())
    lines = [
        "# R12 Daily Price Limit Short After Upper Hit 本地诊断报告",
        "",
        "## 1. 结论",
        "",
        f"`final_decision = {decision}`",
        "",
        "`authorized_strategy_requirement = false`",
        "",
        "本报告只检验公共日频价格中的“涨停后反转”代理，不识别论文中的账户级大户交易，也不证明 A 股融券卖空可执行。",
        "",
        "Required caveat: `local_short_after_limit_up_proxy_not_account_level_paper_replication`",
        "",
        "## 2. 样本与检测口径",
        "",
        f"- limit_detection_price_source: `{run_meta['limit_detection_price_source']}`",
        f"- official_unadjusted_daily_ohlc_status: `{run_meta['official_unadjusted_daily_ohlc_status']}`",
        f"- factor_discontinuity_blocked_count: `{blocked_factor}`",
        f"- regular upper-hit event count by split: `{event_counts}`",
        "",
        "## 3. Primary d1_open 结果",
        "",
        md_table(
            primary,
            [
                "split",
                "horizon",
                "event_count",
                "event_date_count",
                "date_weighted_mean_gross_short_return",
                "date_weighted_mean_after_cost_short_return_ex_borrow",
                "date_weighted_positive_event_date_share",
                "newey_west_tstat_date_weighted_mean_gross_short_return",
            ],
        ),
        "",
        "## 4. Non-limit high-return comparator",
        "",
        md_table(
            comp,
            [
                "split",
                "horizon",
                "upper_hit_event_count_for_comparator",
                "matched_upper_hit_event_count",
                "matched_event_share",
                "comparator_coverage_status",
                "date_weighted_mean_incremental_short_return_vs_nonlimit_high_return",
                "newey_west_tstat_date_weighted_mean_incremental_short_return",
            ],
        ),
        "",
        "## 5. Gate replay",
        "",
        md_table(
            gates,
            [
                "gate_id",
                "gate_group",
                "split",
                "horizon",
                "metric_name",
                "observed_value",
                "threshold_value",
                "gate_status",
                "block_reason",
            ],
        ),
        "",
        "## 6. 解释边界",
        "",
        "- paper mechanism: large investors buy D and sell D+1, causing overreaction and reversal.",
        "- local proxy: public-price short after D close upper-limit event.",
        "- strategy feasibility: not evaluated because borrow data and intraday execution data are absent.",
        "",
        "Failure of the local short-after-limit-up proxy does not refute the paper. The local test differs on sample period, universe, data source, account-level information, short-sale feasibility, and entry timing.",
        "",
    ]
    (paths.output_root / "r12_final_report.md").write_text("\n".join(lines), encoding="utf-8")


def validation_manifest(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    decision: str,
    gate_results: list[dict[str, Any]],
    run_started_at: str,
    run_completed_at: str,
) -> dict[str, Any]:
    calendar = inputs["calendar"]
    ds = config["data_sources"]
    return {
        "requirement_id": config["requirement_id"],
        "short_name": config["short_name"],
        "config_path": rel(paths.config_path),
        "config_sha256": file_hash(paths.config_path),
        "requirement_path": config["requirement_path"],
        "requirement_sha256": file_hash(topic_path(config["requirement_path"])),
        "run_started_at": run_started_at,
        "run_completed_at": run_completed_at,
        "provider_uri": ds["qlib_provider_uri"],
        "provider_calendar_min": pd.Timestamp(calendar.min()).date().isoformat(),
        "provider_calendar_max": pd.Timestamp(calendar.max()).date().isoformat(),
        "provider_load_end": ds["provider_load_end_date"],
        "pit_universe_path": ds["pit_universe_path"],
        "pit_universe_sha256": file_hash(topic_path(ds["pit_universe_path"])),
        "event_detection_method_id": "provider_ohlc_factor_continuity_guard_regular10_st5_nonlimit8_9p8_v0",
        "limit_detection_price_source": "provider_ohlc_with_factor_continuity_guard",
        "outside_pit_audit_status": "not_evaluable_local_source_absent",
        "entry_variant_primary": "d1_open",
        "primary_report_horizons": config["events"]["primary_report_horizons"],
        "primary_decision_horizons": config["events"]["primary_decision_horizons"],
        "final_decision": decision,
        "authorized_strategy_requirement": bool(config["execution"]["authorized_strategy_requirement"]),
        "gate_results": gate_results,
    }


def run_manifest(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    decision: str,
    run_started_at: str,
    run_completed_at: str,
    detection: pd.DataFrame,
) -> dict[str, Any]:
    ds = config["data_sources"]
    calendar = inputs["calendar"]
    factor_blocked = int(detection["event_detection_status"].eq("blocked_factor_discontinuity_for_limit_detection").sum())
    payload = {
        "created_at": run_completed_at,
        "run_started_at": run_started_at,
        "run_completed_at": run_completed_at,
        "git_commit_or_worktree_status": git_commit_or_status(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "requirement_id": config["requirement_id"],
        "short_name": config["short_name"],
        "config_path": rel(paths.config_path),
        "config_sha256": file_hash(paths.config_path),
        "requirement_path": config["requirement_path"],
        "requirement_sha256": file_hash(topic_path(config["requirement_path"])),
        "provider_uri": ds["qlib_provider_uri"],
        "provider_calendar_min": pd.Timestamp(calendar.min()).date().isoformat(),
        "provider_calendar_max": pd.Timestamp(calendar.max()).date().isoformat(),
        "provider_load_end": ds["provider_load_end_date"],
        "pit_universe_path": ds["pit_universe_path"],
        "pit_universe_sha256": file_hash(topic_path(ds["pit_universe_path"])),
        "pit_industry_path": ds["pit_industry_path"],
        "pit_industry_sha256": file_hash(topic_path(ds["pit_industry_path"])),
        "benchmark_feature_dir": ds["benchmark_feature_dir"],
        "benchmark_feature_dir_hash": directory_hash(topic_path(ds["benchmark_feature_dir"])),
        "price_adjustment_mode": config["price_adjustment"]["mode"],
        "limit_detection_price_source": "provider_ohlc_with_factor_continuity_guard",
        "official_unadjusted_daily_ohlc_status": "absent_used_provider_fallback",
        "outside_pit_audit_status": "not_evaluable_local_source_absent",
        "factor_continuity_tolerance": config["limit_detection"]["factor_continuity_tolerance"],
        "factor_discontinuity_blocked_count": factor_blocked,
        "factor_discontinuity_blocked_share": factor_blocked / len(detection) if len(detection) else math.nan,
        "entry_variant_primary": "d1_open",
        "primary_report_horizons": config["events"]["primary_report_horizons"],
        "primary_decision_horizons": config["events"]["primary_decision_horizons"],
        "diagnostic_horizons": config["events"]["diagnostic_horizons"],
        "borrow_fee_stress_bps_per_trading_day": config["events"]["borrow_fee_stress_bps_per_trading_day"],
        "final_decision": decision,
        "authorized_strategy_requirement": bool(config["execution"]["authorized_strategy_requirement"]),
    }
    return payload


def main() -> None:
    args = parse_args()
    config, paths = load_config(args.config)
    run_started_at = datetime.now(timezone.utc).isoformat()
    print("loading inputs")
    inputs = load_inputs(config)
    shutil.copy2(paths.config_path, paths.output_root / "r12_daily_price_limit_short_after_upper_hit_v0.yaml")
    print("detecting upper-limit and comparator events")
    detection = build_detection_audit(config, inputs)
    availability = build_availability_manifest(config, detection)
    print("building event path returns")
    event_path = build_event_path(config, inputs, detection)
    print("summarizing event returns")
    summary = summarize_event_returns(event_path)
    print("matching comparator events")
    match_map = build_match_map(detection)
    matched_pairs = build_matched_pairs(event_path, match_map)
    comparator = summarize_comparator(matched_pairs, event_path, config)
    print("building diagnostics")
    event_count = build_event_count_by_split(detection)
    block_audit = build_entry_exit_block_audit(event_path)
    cluster_diag = build_cluster_diagnostics(detection)
    calendar_time = build_calendar_time_returns(config, inputs, event_path)
    attribution = build_attribution(detection, event_path)
    decision, gate_results, _ = determine_validation(config, detection, event_path, summary, comparator)
    run_completed_at = datetime.now(timezone.utc).isoformat()
    manifest_payload = run_manifest(config, paths, inputs, decision, run_started_at, run_completed_at, detection)
    final_report(paths, config, decision, detection, summary, comparator, gate_results, manifest_payload)
    validation_payload = validation_manifest(config, paths, inputs, decision, gate_results, run_started_at, run_completed_at)

    print("writing artifacts")
    write_json(manifest_payload, paths.output_root / "r12_run_manifest.json")
    write_csv(availability, paths.output_root / "r12_input_availability_manifest.csv")
    audit_cols = [
        "split",
        "date",
        "instrument",
        "candidate_scope",
        "pit_member_on_date",
        "limit_detection_price_source",
        "factor_continuity_status",
        "event_detection_status",
        "event_type",
        "prev_traded_day",
        "ret_to_prev_traded_close",
        "close_high_gap",
        "st_status_proxy",
        "market_cap_asof_T",
        "industry",
        "turnover_money",
        "detection_block_reason",
    ]
    write_csv(detection[audit_cols], paths.output_root / "r12_detection_candidate_audit.csv")
    write_csv(event_count, paths.output_root / "r12_event_count_by_split.csv")
    write_csv(block_audit, paths.output_root / "r12_entry_exit_block_audit.csv")
    write_csv(cluster_diag, paths.output_root / "r12_upper_hit_cluster_diagnostics.csv")
    write_csv(event_path, paths.output_root / "r12_event_path_returns.csv")
    write_csv(summary, paths.output_root / "r12_short_return_summary_by_horizon.csv")
    write_csv(comparator, paths.output_root / "r12_upper_hit_vs_nonlimit_high_return_summary.csv")
    write_csv(matched_pairs, paths.output_root / "r12_matched_comparator_pairs.csv")
    write_csv(calendar_time, paths.output_root / "r12_calendar_time_short_returns.csv")
    write_csv(attribution, paths.output_root / "r12_attribution_by_state.csv")
    write_json(validation_payload, paths.output_root / "r12_validation_manifest.json")
    print(f"final_decision={decision}")
    print(f"output_root={rel(paths.output_root)}")


if __name__ == "__main__":
    main()

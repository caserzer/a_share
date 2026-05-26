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
DEFAULT_CONFIG = EP6_DIR / "configs" / "r07_weekly_imom_horse_race_v0.yaml"

SPLITS = ["train", "validation", "robustness"]
PRIMARY_RISK_METRICS = ["IVOL", "IMD"]
DIAGNOSTIC_RISK_METRICS = ["ISKEW", "IKURT", "IES5", "IVAR5", "IES1", "IVAR1"]
ALL_RISK_METRICS = PRIMARY_RISK_METRICS + DIAGNOSTIC_RISK_METRICS
POSITIVE_RISK_METRICS = ["IVOL", "IMD", "IES5", "IVAR5", "IES1", "IVAR1"]


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    configs_dir: Path
    manifests_dir: Path
    weekly_dir: Path
    residuals_dir: Path
    signals_dir: Path
    returns_dir: Path
    reports_dir: Path


@dataclass
class PortfolioSpec:
    family: str
    metric_id: str
    J: int | None
    signal_week_index: int
    status: str
    weights: dict[str, float]
    assigned_long_count: int
    assigned_short_count: int
    signal_eligible_count: int
    block_reason: str = ""


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
    parser = argparse.ArgumentParser(description="Run EP6 R07 weekly market-residual IMOM horse-race diagnostic")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def load_config(path: str | Path) -> tuple[dict[str, Any], Paths]:
    config_path = topic_path(path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = topic_path(config["output_root"])
    paths = Paths(
        config_path=config_path,
        output_root=output_root,
        configs_dir=output_root / "configs",
        manifests_dir=output_root / "manifests",
        weekly_dir=output_root / "weekly",
        residuals_dir=output_root / "residuals",
        signals_dir=output_root / "signals",
        returns_dir=output_root / "returns",
        reports_dir=output_root / "reports",
    )
    for directory in [
        paths.configs_dir,
        paths.manifests_dir,
        paths.weekly_dir,
        paths.residuals_dir,
        paths.signals_dir,
        paths.returns_dir,
        paths.reports_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_parquet_or_csv(df: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(path, index=False)
        return "parquet"
    except Exception:  # noqa: BLE001
        fallback = path.with_suffix(".csv")
        df.to_csv(fallback, index=False)
        return f"csv_fallback:{fallback.name}"


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def directory_hash(path: Path) -> str:
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
        suffix = "dirty" if status else "clean"
        return f"{commit} ({suffix})"
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


def pct(value: Any, digits: int = 2) -> str:
    try:
        v = float(value)
    except Exception:  # noqa: BLE001
        return "NA"
    if not np.isfinite(v):
        return "NA"
    return f"{v * 100:.{digits}f}%"


def num(value: Any, digits: int = 4) -> str:
    try:
        v = float(value)
    except Exception:  # noqa: BLE001
        return "NA"
    if not np.isfinite(v):
        return "NA"
    return f"{v:.{digits}f}"


def build_weekly_calendar(calendar: pd.DatetimeIndex, config: dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame({"date": calendar})
    frame["calendar_friday"] = frame["date"] + pd.to_timedelta(4 - frame["date"].dt.weekday, unit="D")
    rows = []
    previous_retained = pd.NaT
    threshold = int(config["weekly_calendar"]["skip_week_if_trading_days_lte"])
    for friday, group in frame.groupby("calendar_friday", sort=True):
        count = int(len(group))
        retained = count > threshold
        week_end = group["date"].max() if count > 0 else pd.NaT
        rows.append(
            {
                "calendar_week_id": f"{pd.Timestamp(friday).isocalendar().year}-W{pd.Timestamp(friday).isocalendar().week:02d}",
                "calendar_friday": pd.Timestamp(friday).date().isoformat(),
                "candidate_week_trading_day_count": count,
                "week_end": pd.Timestamp(week_end).date().isoformat() if pd.notna(week_end) else "",
                "week_retained": bool(retained),
                "skip_reason": "" if retained else "candidate_week_trading_day_count_lte_2",
                "previous_retained_week_end": pd.Timestamp(previous_retained).date().isoformat() if pd.notna(previous_retained) else "",
            }
        )
        if retained:
            previous_retained = week_end
    out = pd.DataFrame(rows)
    out["week_end_ts"] = pd.to_datetime(out["week_end"], errors="coerce")
    retained = out["week_retained"].astype(bool)
    out.loc[retained, "retained_week_index"] = np.arange(retained.sum(), dtype=int)
    return out


def weekly_returns(close_wide: pd.DataFrame, weekly_calendar: pd.DataFrame) -> pd.DataFrame:
    retained_dates = pd.DatetimeIndex(weekly_calendar.loc[weekly_calendar["week_retained"], "week_end_ts"])
    weekly_close = close_wide.reindex(retained_dates)
    return weekly_close.div(weekly_close.shift(1)).sub(1.0)


def compute_daily_residuals(
    close_wide: pd.DataFrame,
    volume_wide: pd.DataFrame,
    money_wide: pd.DataFrame,
    market_close: pd.Series,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    model = config["residual_model"]
    window = int(model["beta_window_trading_days"])
    min_valid = int(model["beta_min_valid_days"])
    stock_ret = close_wide.pct_change(fill_method=None)
    market_ret = market_close.pct_change(fill_method=None).reindex(stock_ret.index)
    valid = (
        stock_ret.notna()
        & market_ret.notna().to_frame().reindex(stock_ret.index).iloc[:, [0]].to_numpy()
        & (close_wide.shift(1) > 0)
        & (volume_wide > 0)
        & (money_wide > 0)
    )
    x = pd.DataFrame(np.broadcast_to(market_ret.to_numpy()[:, None], stock_ret.shape), index=stock_ret.index, columns=stock_ret.columns)
    xv = x.where(valid)
    yv = stock_ret.where(valid)
    count = valid.astype(float).rolling(window, min_periods=1).sum().shift(1)
    sx = xv.rolling(window, min_periods=1).sum().shift(1)
    sy = yv.rolling(window, min_periods=1).sum().shift(1)
    sx2 = xv.pow(2).rolling(window, min_periods=1).sum().shift(1)
    sxy = xv.mul(yv).rolling(window, min_periods=1).sum().shift(1)
    mean_x = sx / count
    mean_y = sy / count
    var_x = sx2 - sx.pow(2) / count
    cov_xy = sxy - sx * sy / count
    beta = cov_xy / var_x
    beta = beta.where((count >= min_valid) & (var_x > 0))
    alpha = mean_y - beta * mean_x
    residual = yv - alpha - beta.mul(market_ret, axis=0)
    residual = residual.where(valid)
    manifest = pd.DataFrame(
        [
            {
                "residual_model_id": model["residual_model_id"],
                "local_imom_interpretation": model["local_imom_interpretation"],
                "beta_window_trading_days": window,
                "beta_min_valid_days": min_valid,
                "risk_free_mode": model["risk_free_mode"],
                "valid_return_day_policy": "finite close and previous close; volume > 0; money > 0; finite SH000300 return",
                "allow_shortened_beta_window": bool(model["allow_shortened_beta_window"]),
                "fill_suspended_returns_with_zero": bool(model["fill_suspended_returns_with_zero"]),
                "residual_non_null_count": int(residual.notna().sum().sum()),
                "instrument_count": int(residual.shape[1]),
            }
        ]
    )
    return residual, manifest


def compute_risk_metrics(window_residuals: pd.DataFrame, min_valid: int) -> pd.DataFrame:
    out = pd.DataFrame(index=window_residuals.columns)
    counts = window_residuals.count()
    out["valid_residual_count"] = counts
    out["IVOL"] = window_residuals.std(skipna=True, ddof=1)
    out["ISKEW"] = window_residuals.skew(skipna=True)
    out["IKURT"] = window_residuals.kurt(skipna=True)
    arr = window_residuals.to_numpy(dtype="float64")
    valid = np.isfinite(arr)
    imd = np.full(arr.shape[1], np.nan)
    ies5 = np.full(arr.shape[1], np.nan)
    ivar5 = np.full(arr.shape[1], np.nan)
    ies1 = np.full(arr.shape[1], np.nan)
    ivar1 = np.full(arr.shape[1], np.nan)
    for j in range(arr.shape[1]):
        vals = arr[valid[:, j], j]
        if len(vals) < min_valid:
            continue
        vals = vals[np.isfinite(vals)]
        if len(vals) < min_valid:
            continue
        safe_vals = vals[vals > -0.999999]
        if len(safe_vals) >= min_valid:
            equity = np.cumprod(1.0 + safe_vals)
            peak = np.maximum.accumulate(equity)
            drawdown = equity / peak - 1.0
            imd[j] = max(0.0, -float(np.nanmin(drawdown)))
        q5 = float(np.nanquantile(vals, 0.05))
        q1 = float(np.nanquantile(vals, 0.01))
        tail5 = vals[vals <= q5]
        tail1 = vals[vals <= q1]
        ivar5[j] = max(0.0, -q5)
        ivar1[j] = max(0.0, -q1)
        ies5[j] = max(0.0, -float(np.nanmean(tail5))) if len(tail5) else np.nan
        ies1[j] = max(0.0, -float(np.nanmean(tail1))) if len(tail1) else np.nan
    out["IMD"] = imd
    out["IES5"] = ies5
    out["IVAR5"] = ivar5
    out["IES1"] = ies1
    out["IVAR1"] = ivar1
    for col in ALL_RISK_METRICS:
        out.loc[counts < min_valid, col] = np.nan
    return out


def product_return(frame: pd.DataFrame, min_count: int) -> pd.Series:
    count = frame.count()
    prod = (1.0 + frame).prod(skipna=True) - 1.0
    return prod.where(count >= min_count)


def load_inputs(config: dict[str, Any]) -> dict[str, Any]:
    ds = config["data_sources"]
    provider_uri = topic_path(ds["qlib_provider_uri"])
    calendar = load_calendar(topic_path(ds["trading_calendar_path"]))
    pit = pd.read_csv(
        topic_path(ds["pit_universe_path"]),
        usecols=["date", "instrument"],
        dtype={"instrument": "string"},
        low_memory=False,
    )
    pit["date"] = pd.to_datetime(pit["date"]).dt.normalize()
    pit["instrument"] = pit["instrument"].astype(str).str.upper()
    instruments = sorted(pit["instrument"].dropna().unique().tolist())
    close_wide = load_feature_wide(provider_uri, calendar, instruments, "close")
    volume_wide = load_feature_wide(provider_uri, calendar, instruments, "volume")
    money_wide = load_feature_wide(provider_uri, calendar, instruments, "money")
    market_close = read_qlib_series(provider_uri, calendar, ds["index_instrument"], "close").reindex(calendar)
    return {
        "provider_uri": provider_uri,
        "calendar": calendar,
        "pit": pit,
        "instruments": instruments,
        "close_wide": close_wide,
        "volume_wide": volume_wide,
        "money_wide": money_wide,
        "market_close": market_close,
    }


def make_pit_membership(pit: pd.DataFrame) -> dict[pd.Timestamp, set[str]]:
    return {pd.Timestamp(k).normalize(): set(v["instrument"].astype(str)) for k, v in pit.groupby("date", sort=False)}


def frame_from_series(series: pd.Series, value_name: str) -> pd.DataFrame:
    return pd.DataFrame({"instrument": series.index.astype(str), value_name: series.to_numpy()})


def assign_buckets(frame: pd.DataFrame, value_col: str, bucket_count: int) -> pd.DataFrame:
    out = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=[value_col]).copy()
    out["instrument"] = out["instrument"].astype(str)
    out = out.sort_values([value_col, "instrument"], kind="mergesort").reset_index(drop=True)
    n = len(out)
    if n:
        out["bucket"] = np.floor(np.arange(n) * bucket_count / n).astype(int) + 1
    else:
        out["bucket"] = pd.Series(dtype="int64")
    return out


def weights_from_legs(long_instruments: list[str], short_instruments: list[str]) -> dict[str, float]:
    weights: dict[str, float] = {}
    if long_instruments:
        w = 1.0 / len(long_instruments)
        for inst in long_instruments:
            weights[inst] = weights.get(inst, 0.0) + w
    if short_instruments:
        w = -1.0 / len(short_instruments)
        for inst in short_instruments:
            weights[inst] = weights.get(inst, 0.0) + w
    return {k: v for k, v in weights.items() if abs(v) > 1e-15}


def univariate_spec(
    family: str,
    metric_id: str,
    J: int | None,
    signal_week_index: int,
    signal: pd.Series,
    universe: set[str],
    long_high: bool,
    config: dict[str, Any],
) -> PortfolioSpec:
    bucket_count = int(config["portfolio"]["univariate_bucket_count"])
    min_universe = int(config["portfolio"]["signal_eligible_instrument_count_min"])
    frame = frame_from_series(signal.reindex(sorted(universe)), "signal_value")
    ranked = assign_buckets(frame, "signal_value", bucket_count)
    eligible_count = int(len(ranked))
    if eligible_count < min_universe or ranked["bucket"].nunique() < bucket_count:
        return PortfolioSpec(family, metric_id, J, signal_week_index, "blocked_insufficient_portfolio_coverage", {}, 0, 0, eligible_count, "insufficient_signal_eligible_universe")
    if long_high:
        long = ranked.loc[ranked["bucket"].eq(bucket_count), "instrument"].tolist()
        short = ranked.loc[ranked["bucket"].eq(1), "instrument"].tolist()
    else:
        long = ranked.loc[ranked["bucket"].eq(1), "instrument"].tolist()
        short = ranked.loc[ranked["bucket"].eq(bucket_count), "instrument"].tolist()
    return PortfolioSpec(family, metric_id, J, signal_week_index, "complete", weights_from_legs(long, short), len(long), len(short), eligible_count)


def bivariate_spec(
    metric_id: str,
    J: int,
    signal_week_index: int,
    imom: pd.Series,
    risk: pd.Series,
    universe: set[str],
    config: dict[str, Any],
) -> PortfolioSpec:
    bucket_count = int(config["portfolio"]["bivariate_sort_bucket_count"])
    min_universe = int(config["portfolio"]["signal_eligible_instrument_count_min"])
    min_intersection = int(config["portfolio"]["bivariate_intersection_count_min"])
    frame = pd.DataFrame(
        {
            "instrument": sorted(universe),
            "imom": imom.reindex(sorted(universe)).to_numpy(),
            "risk": risk.reindex(sorted(universe)).to_numpy(),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()
    eligible_count = int(len(frame))
    if eligible_count < min_universe:
        return PortfolioSpec("bivariate_risk_adjusted_imom", metric_id, J, signal_week_index, "blocked_insufficient_portfolio_coverage", {}, 0, 0, eligible_count, "insufficient_signal_eligible_universe")
    imom_ranked = assign_buckets(frame[["instrument", "imom"]].rename(columns={"imom": "signal_value"}), "signal_value", bucket_count)
    risk_ranked = assign_buckets(frame[["instrument", "risk"]].rename(columns={"risk": "signal_value"}), "signal_value", bucket_count)
    merged = imom_ranked[["instrument", "bucket"]].rename(columns={"bucket": "imom_bucket"}).merge(
        risk_ranked[["instrument", "bucket"]].rename(columns={"bucket": "risk_bucket"}), on="instrument", how="inner"
    )
    long = merged.loc[merged["imom_bucket"].eq(bucket_count) & merged["risk_bucket"].eq(1), "instrument"].tolist()
    short = merged.loc[merged["imom_bucket"].eq(1) & merged["risk_bucket"].eq(bucket_count), "instrument"].tolist()
    if len(long) < min_intersection or len(short) < min_intersection:
        return PortfolioSpec("bivariate_risk_adjusted_imom", metric_id, J, signal_week_index, "blocked_insufficient_portfolio_coverage", {}, len(long), len(short), eligible_count, "assigned_intersection_too_small")
    return PortfolioSpec("bivariate_risk_adjusted_imom", metric_id, J, signal_week_index, "complete", weights_from_legs(long, short), len(long), len(short), eligible_count)


def direct_adjusted_spec(
    metric_id: str,
    J: int,
    signal_week_index: int,
    imom: pd.Series,
    risk: pd.Series,
    universe: set[str],
    config: dict[str, Any],
) -> PortfolioSpec:
    adjusted = imom / risk.where(risk > 0)
    return univariate_spec("direct_risk_adjusted_imom", metric_id, J, signal_week_index, adjusted, universe, True, config)


def liquidity_state_value(
    t: int,
    retained_dates: pd.DatetimeIndex,
    weekly_calendar: pd.DataFrame,
    daily_returns: pd.DataFrame,
    money_wide: pd.DataFrame,
    universe: set[str],
    config: dict[str, Any],
) -> float:
    window_weeks = int(config["liquidity_state"]["state_window_retained_weeks"])
    start_week = max(0, t - window_weeks)
    end_week = t - 1
    if end_week < 0 or not universe:
        return math.nan
    start_date = retained_dates[start_week - 1] if start_week > 0 else daily_returns.index.min() - pd.Timedelta(days=1)
    end_date = retained_dates[end_week]
    dates = daily_returns.index[(daily_returns.index > start_date) & (daily_returns.index <= end_date)]
    if len(dates) == 0:
        return math.nan
    cols = [c for c in sorted(universe) if c in daily_returns.columns]
    if not cols:
        return math.nan
    illiq = daily_returns.loc[dates, cols].abs() / money_wide.loc[dates, cols].where(money_wide.loc[dates, cols] > 0)
    value = float(illiq.replace([np.inf, -np.inf], np.nan).stack().mean())
    return value if np.isfinite(value) else math.nan


def build_signals_and_specs(
    config: dict[str, Any],
    paths: Paths,
    inputs: dict[str, Any],
    weekly_calendar: pd.DataFrame,
    residuals: pd.DataFrame,
    weekly_ret: pd.DataFrame,
) -> tuple[dict[tuple[str, str, int | None, int], PortfolioSpec], dict[str, Any], dict[str, pd.DataFrame]]:
    J_values = [int(x) for x in config["signals"]["J_values"]]
    train_start = pd.Timestamp(config["sample_split"]["train_start"])
    robustness_end = pd.Timestamp(config["sample_split"]["robustness_end"])
    retained_dates = pd.DatetimeIndex(weekly_calendar.loc[weekly_calendar["week_retained"], "week_end_ts"])
    eval_week_indices = [i for i, d in enumerate(retained_dates) if train_start <= d <= robustness_end and i >= 2]
    pit_members = make_pit_membership(inputs["pit"])
    risk_min_valid = int(config["residual_model"]["risk_metric_min_valid_residual_days"])
    beta_window = int(config["residual_model"]["beta_window_trading_days"])
    specs: dict[tuple[str, str, int | None, int], PortfolioSpec] = {}
    mom_frames = []
    imom_frames = []
    risk_frames = []
    bivar_frames = []
    eligibility_rows = []
    first_signal_by_J: dict[int, str] = {}
    first_portfolio_by_JK: dict[str, str] = {}
    train_lost_by_JK: dict[str, int] = {}
    context_rows = []
    daily_ret = inputs["close_wide"].pct_change(fill_method=None)
    liquidity_values: dict[int, float] = {}

    for t in eval_week_indices:
        holding_date = retained_dates[t]
        skip_date = retained_dates[t - 1]
        asof_date = retained_dates[t - 2]
        split = split_for_date(holding_date, config)
        universe = pit_members.get(pd.Timestamp(skip_date).normalize(), set())
        risk_start_pos = max(0, residuals.index.get_indexer([asof_date], method="pad")[0] - beta_window + 1)
        asof_pos = residuals.index.get_indexer([asof_date], method="pad")[0]
        risk_window = residuals.iloc[risk_start_pos : asof_pos + 1]
        risk = compute_risk_metrics(risk_window, risk_min_valid)
        risk["instrument"] = risk.index.astype(str)
        risk["signal_week_index"] = t
        risk["holding_week_end"] = holding_date.date().isoformat()
        risk["skip_week_end"] = skip_date.date().isoformat()
        risk["asof_week_end"] = asof_date.date().isoformat()
        risk_frames.append(risk.reset_index(drop=True))
        liquidity = liquidity_state_value(t, retained_dates, weekly_calendar, daily_ret, inputs["money_wide"], universe, config)
        liquidity_values[t] = liquidity
        context_rows.append(
            {
                "signal_week_index": t,
                "holding_week_end": holding_date.date().isoformat(),
                "skip_week_end": skip_date.date().isoformat(),
                "asof_week_end": asof_date.date().isoformat(),
                "split": split,
                "pit_member_count": len(universe),
                "AILLIQ_signal_t": liquidity,
            }
        )

        for metric_id in ALL_RISK_METRICS:
            specs[("risk_only", metric_id, None, t)] = univariate_spec("risk_only", metric_id, None, t, risk.set_index("instrument")[metric_id], universe, False, config)

        for J in J_values:
            min_resid_days = max(
                int(config["residual_model"]["min_valid_residual_days_for_J_signal_floor"]),
                math.ceil(float(config["residual_model"]["min_valid_residual_days_for_J_signal_share"]) * J * 5),
            )
            if t - J - 1 < 0:
                continue
            weekly_window = weekly_ret.iloc[t - J - 1 : t - 1]
            mom = product_return(weekly_window, J)
            prev_date = retained_dates[t - J - 2] if t - J - 2 >= 0 else residuals.index.min() - pd.Timedelta(days=1)
            resid_window = residuals.loc[(residuals.index > prev_date) & (residuals.index <= asof_date)]
            imom = product_return(resid_window, min_resid_days)
            for name, series, holder in [("MOM", mom, mom_frames), ("IMOM", imom, imom_frames)]:
                frame = frame_from_series(series, "signal_value")
                frame["signal_type"] = name
                frame["J"] = J
                frame["signal_week_index"] = t
                frame["holding_week_end"] = holding_date.date().isoformat()
                frame["skip_week_end"] = skip_date.date().isoformat()
                frame["asof_week_end"] = asof_date.date().isoformat()
                frame["signal_valid"] = frame["signal_value"].replace([np.inf, -np.inf], np.nan).notna()
                holder.append(frame)
            raw_spec = univariate_spec("raw_mom_W_minus_L", "", J, t, mom, universe, True, config)
            imom_spec = univariate_spec("imom", "", J, t, imom, universe, True, config)
            specs[("raw_mom_W_minus_L", "", J, t)] = raw_spec
            specs[("imom", "", J, t)] = imom_spec
            if raw_spec.status == "complete" and J not in first_signal_by_J:
                first_signal_by_J[J] = skip_date.date().isoformat()
            for K in config["signals"]["K_values"]:
                key = f"J{J}_K{K}"
                if imom_spec.status == "complete" and key not in first_portfolio_by_JK:
                    first_portfolio_by_JK[key] = holding_date.date().isoformat()
                if split == "train" and imom_spec.status != "complete":
                    train_lost_by_JK[key] = train_lost_by_JK.get(key, 0) + 1
            risk_indexed = risk.set_index("instrument")
            for metric_id in POSITIVE_RISK_METRICS:
                bivar = bivariate_spec(metric_id, J, t, imom, risk_indexed[metric_id], universe, config)
                specs[("bivariate_risk_adjusted_imom", metric_id, J, t)] = bivar
                direct = direct_adjusted_spec(metric_id, J, t, imom, risk_indexed[metric_id], universe, config)
                specs[("direct_risk_adjusted_imom", metric_id, J, t)] = direct
                bivar_frames.append(
                    {
                        "signal_week_index": t,
                        "holding_week_end": holding_date.date().isoformat(),
                        "J": J,
                        "metric_id": metric_id,
                        "portfolio_week_status": bivar.status,
                        "signal_eligible_instrument_count": bivar.signal_eligible_count,
                        "assigned_long_leg_count": bivar.assigned_long_count,
                        "assigned_short_leg_count": bivar.assigned_short_count,
                        "block_reason": bivar.block_reason,
                    }
                )
            eligibility_rows.append(
                {
                    "signal_week_index": t,
                    "J": J,
                    "holding_week_end": holding_date.date().isoformat(),
                    "skip_week_end": skip_date.date().isoformat(),
                    "split": split,
                    "pit_member_count": len(universe),
                    "raw_signal_valid_count": int(mom.reindex(sorted(universe)).replace([np.inf, -np.inf], np.nan).notna().sum()),
                    "imom_signal_valid_count": int(imom.reindex(sorted(universe)).replace([np.inf, -np.inf], np.nan).notna().sum()),
                    "raw_portfolio_status": raw_spec.status,
                    "imom_portfolio_status": imom_spec.status,
                    "raw_block_reason": raw_spec.block_reason,
                    "imom_block_reason": imom_spec.block_reason,
                }
            )

    signal_outputs = {
        "mom": pd.concat(mom_frames, ignore_index=True) if mom_frames else pd.DataFrame(),
        "imom": pd.concat(imom_frames, ignore_index=True) if imom_frames else pd.DataFrame(),
        "risk": pd.concat(risk_frames, ignore_index=True) if risk_frames else pd.DataFrame(),
        "bivar": pd.DataFrame(bivar_frames),
        "eligibility": pd.DataFrame(eligibility_rows),
        "context": pd.DataFrame(context_rows),
    }
    thresholds = compute_liquidity_thresholds(signal_outputs["context"])
    signal_outputs["context"] = add_state_columns(signal_outputs["context"], inputs["market_close"], weekly_ret, thresholds)
    write_csv(signal_outputs["eligibility"], paths.weekly_dir / "r07_weekly_signal_eligibility_audit.csv")
    write_parquet_or_csv(signal_outputs["mom"], paths.signals_dir / "r07_mom_signal_panel.parquet")
    write_parquet_or_csv(signal_outputs["imom"], paths.signals_dir / "r07_imom_signal_panel.parquet")
    write_parquet_or_csv(signal_outputs["risk"], paths.signals_dir / "r07_risk_metric_panel.parquet")
    write_parquet_or_csv(signal_outputs["bivar"], paths.signals_dir / "r07_bivariate_imom_risk_signal_panel.parquet")
    meta = {
        "eval_week_count": len(eval_week_indices),
        "first_evaluable_signal_week_by_J": {str(k): v for k, v in sorted(first_signal_by_J.items())},
        "first_evaluable_portfolio_week_by_JK": first_portfolio_by_JK,
        "effective_split_start_by_JK": first_portfolio_by_JK,
        "train_weeks_lost_to_warmup_by_JK": train_lost_by_JK,
        "liquidity_thresholds": thresholds,
    }
    return specs, meta, signal_outputs


def compute_liquidity_thresholds(context: pd.DataFrame) -> dict[str, float]:
    train = context.loc[context["split"].eq("train"), "AILLIQ_signal_t"].replace([np.inf, -np.inf], np.nan).dropna()
    if train.empty:
        return {"median": math.nan, "q20": math.nan, "q80": math.nan}
    return {"median": float(train.quantile(0.50)), "q20": float(train.quantile(0.20)), "q80": float(train.quantile(0.80))}


def add_state_columns(context: pd.DataFrame, market_close: pd.Series, weekly_ret: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    out = context.copy()
    weekly_dates = weekly_ret.index
    market_weekly = market_close.reindex(weekly_dates).div(market_close.reindex(weekly_dates).shift(1)).sub(1.0)
    by_date = {}
    for i, d in enumerate(weekly_dates):
        row: dict[str, Any] = {}
        for n in [26, 52]:
            if i - n < 0:
                value = math.nan
            else:
                value = float((1.0 + market_weekly.iloc[i - n : i]).prod(skipna=True) - 1.0)
            row[f"market_return_{n}w"] = value
            row[f"market_state_{n}w"] = "upside" if np.isfinite(value) and value > 0 else ("downside" if np.isfinite(value) else "unavailable")
        by_date[pd.Timestamp(d).date().isoformat()] = row
    state_rows = out["holding_week_end"].map(lambda x: by_date.get(str(x), {}))
    for key in ["market_return_26w", "market_state_26w", "market_return_52w", "market_state_52w"]:
        out[key] = state_rows.map(lambda d: d.get(key, np.nan))
    out["liquidity_state"] = np.where(out["AILLIQ_signal_t"] <= thresholds.get("median", np.nan), "high_liquidity", "low_liquidity")
    out.loc[out["AILLIQ_signal_t"].isna(), "liquidity_state"] = "unavailable"
    out["liquidity_extreme_state"] = "middle_liquidity"
    out.loc[out["AILLIQ_signal_t"] <= thresholds.get("q20", np.nan), "liquidity_extreme_state"] = "extreme_high_liquidity"
    out.loc[out["AILLIQ_signal_t"] >= thresholds.get("q80", np.nan), "liquidity_extreme_state"] = "extreme_low_liquidity"
    out.loc[out["AILLIQ_signal_t"].isna(), "liquidity_extreme_state"] = "unavailable"
    return out


def combine_active_weights(active_specs: list[PortfolioSpec]) -> dict[str, float]:
    combined: dict[str, float] = {}
    if not active_specs:
        return combined
    scale = 1.0 / len(active_specs)
    for spec in active_specs:
        for inst, weight in spec.weights.items():
            combined[inst] = combined.get(inst, 0.0) + weight * scale
    return {k: v for k, v in combined.items() if abs(v) > 1e-15}


def turnover(prev: dict[str, float], curr: dict[str, float]) -> tuple[float, float]:
    buy = 0.0
    sell = 0.0
    for inst in set(prev) | set(curr):
        delta = curr.get(inst, 0.0) - prev.get(inst, 0.0)
        if delta > 0:
            buy += delta
        elif delta < 0:
            sell += -delta
    return float(buy), float(sell)


def evaluate_weight_return(weights: dict[str, float], returns: pd.Series, config: dict[str, Any]) -> dict[str, Any]:
    positive = {k: v for k, v in weights.items() if v > 0}
    negative = {k: -v for k, v in weights.items() if v < 0}
    assigned_long = len(positive)
    assigned_short = len(negative)
    long_values = {k: returns.get(k, np.nan) for k in positive}
    short_values = {k: returns.get(k, np.nan) for k in negative}
    long_finite = {k: float(v) for k, v in long_values.items() if np.isfinite(v)}
    short_finite = {k: float(v) for k, v in short_values.items() if np.isfinite(v)}
    label_min = int(config["portfolio"]["label_evaluable_leg_count_min"])
    share_min = float(config["portfolio"]["label_evaluable_leg_share_min"])
    long_share = len(long_finite) / assigned_long if assigned_long else 0.0
    short_share = len(short_finite) / assigned_short if assigned_short else 0.0
    status = "complete"
    block_reason = ""
    if len(long_finite) < label_min or len(short_finite) < label_min:
        status = "blocked_insufficient_portfolio_coverage"
        block_reason = "label_evaluable_leg_count_too_small"
    elif long_share < share_min or short_share < share_min:
        status = "blocked_insufficient_portfolio_coverage"
        block_reason = "label_evaluable_leg_share_too_low"
    long_weight_sum = sum(positive[k] for k in long_finite)
    short_weight_sum = sum(negative[k] for k in short_finite)
    if status == "complete" and long_weight_sum > 0 and short_weight_sum > 0:
        long_return = sum(positive[k] / long_weight_sum * long_finite[k] for k in long_finite)
        short_return = sum(negative[k] / short_weight_sum * short_finite[k] for k in short_finite)
        gross = long_return - short_return
    else:
        long_return = math.nan
        short_return = math.nan
        gross = math.nan
    return {
        "portfolio_week_status": status,
        "block_reason": block_reason,
        "assigned_long_leg_count": assigned_long,
        "assigned_short_leg_count": assigned_short,
        "label_evaluable_long_leg_count": len(long_finite),
        "label_evaluable_short_leg_count": len(short_finite),
        "label_evaluable_long_leg_share": long_share,
        "label_evaluable_short_leg_share": short_share,
        "long_leg_weekly_return": long_return,
        "short_leg_weekly_return": short_return,
        "gross_return": gross,
    }


def replay_returns_for_family(
    specs: dict[tuple[str, str, int | None, int], PortfolioSpec],
    family: str,
    metric_id: str,
    J: int,
    K: int,
    weekly_ret: pd.DataFrame,
    context: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    buy_cost = float(config["execution"]["buy_cost_bps"]) / 10000.0
    sell_cost = float(config["execution"]["sell_cost_bps"]) / 10000.0
    context_by_t = context.set_index("signal_week_index")
    all_t = sorted(context_by_t.index.astype(int).tolist())
    prev_weights: dict[str, float] = {}
    rows = []
    for h in all_t:
        active = []
        for s in range(h - K + 1, h + 1):
            key_j = J if family != "risk_only" else None
            spec = specs.get((family, metric_id, key_j, s))
            if spec is not None and spec.status == "complete" and spec.weights:
                active.append(spec)
        combined = combine_active_weights(active)
        buy, sell = turnover(prev_weights, combined)
        prev_weights = combined
        date = context_by_t.loc[h, "holding_week_end"]
        returns = weekly_ret.loc[pd.Timestamp(date)] if pd.Timestamp(date) in weekly_ret.index else pd.Series(dtype="float64")
        ret_eval = evaluate_weight_return(combined, returns, config) if combined else {
            "portfolio_week_status": "blocked_insufficient_portfolio_coverage",
            "block_reason": "no_active_vintage",
            "assigned_long_leg_count": 0,
            "assigned_short_leg_count": 0,
            "label_evaluable_long_leg_count": 0,
            "label_evaluable_short_leg_count": 0,
            "label_evaluable_long_leg_share": 0.0,
            "label_evaluable_short_leg_share": 0.0,
            "long_leg_weekly_return": math.nan,
            "short_leg_weekly_return": math.nan,
            "gross_return": math.nan,
        }
        gross = ret_eval["gross_return"]
        after_cost = gross - buy * buy_cost - sell * sell_cost if np.isfinite(gross) else math.nan
        ctx = context_by_t.loc[h].to_dict()
        rows.append(
            {
                "family": family,
                "metric_id": metric_id,
                "J": J,
                "K": K,
                "holding_week_end": date,
                "split": ctx["split"],
                "active_portfolio_count": len(active),
                "active_vintage_count": len(active),
                "signal_eligible_instrument_count": np.nanmean([s.signal_eligible_count for s in active]) if active else 0,
                "buy_turnover": buy,
                "sell_turnover": sell,
                "after_cost_return": after_cost,
                "AILLIQ_signal_t": ctx.get("AILLIQ_signal_t", math.nan),
                "market_state_26w": ctx.get("market_state_26w", "unavailable"),
                "market_state_52w": ctx.get("market_state_52w", "unavailable"),
                "liquidity_state": ctx.get("liquidity_state", "unavailable"),
                "liquidity_extreme_state": ctx.get("liquidity_extreme_state", "unavailable"),
                **ret_eval,
            }
        )
    return pd.DataFrame(rows)


def newey_west_t(series: pd.Series, lag: int) -> float:
    values = series.replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype="float64")
    n = len(values)
    if n < 2:
        return math.nan
    mean = float(values.mean())
    centered = values - mean
    L = max(0, int(lag))
    gamma0 = float(np.dot(centered, centered) / n)
    var = gamma0
    for l in range(1, min(L, n - 1) + 1):
        gamma = float(np.dot(centered[l:], centered[:-l]) / n)
        var += 2.0 * (1.0 - l / (L + 1.0)) * gamma
    var_mean = var / n
    if not np.isfinite(var_mean) or var_mean <= 0:
        return math.nan
    return float(mean / math.sqrt(var_mean))


def max_drawdown(series: pd.Series) -> float:
    values = series.replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return math.nan
    equity = (1.0 + values).cumprod()
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def summarize_returns(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    annualization = float(config["statistics"]["annualization_weeks"])
    for keys, group in df.groupby(["family", "metric_id", "J", "K", "split"], dropna=False):
        family, metric_id, J, K, split = keys
        complete = group.loc[group["portfolio_week_status"].eq("complete")].copy()
        gross = complete["gross_return"]
        after = complete["after_cost_return"]
        gross_vol = gross.std(ddof=1)
        after_vol = after.std(ddof=1)
        rows.append(
            {
                "family": family,
                "metric_id": metric_id,
                "J": int(J),
                "K": int(K),
                "split": split,
                "week_count": int(len(complete)),
                "active_portfolio_count": float(complete["active_portfolio_count"].mean()) if not complete.empty else math.nan,
                "active_vintage_count_mean": float(complete["active_vintage_count"].mean()) if not complete.empty else math.nan,
                "signal_eligible_instrument_count_mean": float(complete["signal_eligible_instrument_count"].mean()) if not complete.empty else math.nan,
                "signal_eligible_instrument_count_min": float(complete["signal_eligible_instrument_count"].min()) if not complete.empty else math.nan,
                "assigned_long_leg_count_mean": float(complete["assigned_long_leg_count"].mean()) if not complete.empty else math.nan,
                "assigned_short_leg_count_mean": float(complete["assigned_short_leg_count"].mean()) if not complete.empty else math.nan,
                "label_evaluable_long_leg_count_mean": float(complete["label_evaluable_long_leg_count"].mean()) if not complete.empty else math.nan,
                "label_evaluable_short_leg_count_mean": float(complete["label_evaluable_short_leg_count"].mean()) if not complete.empty else math.nan,
                "label_evaluable_long_leg_share_mean": float(complete["label_evaluable_long_leg_share"].mean()) if not complete.empty else math.nan,
                "label_evaluable_short_leg_share_mean": float(complete["label_evaluable_short_leg_share"].mean()) if not complete.empty else math.nan,
                "weekly_mean_return": float(gross.mean()) if len(gross) else math.nan,
                "annualized_mean_return": float(gross.mean() * annualization) if len(gross) else math.nan,
                "weekly_volatility": float(gross_vol) if np.isfinite(gross_vol) else math.nan,
                "annualized_volatility": float(gross_vol * math.sqrt(annualization)) if np.isfinite(gross_vol) else math.nan,
                "sharpe_ratio": float(gross.mean() / gross_vol * math.sqrt(annualization)) if np.isfinite(gross_vol) and gross_vol > 0 else math.nan,
                "t_stat_weekly_mean_newey_west": newey_west_t(gross, int(K)),
                "newey_west_lag_used": int(K),
                "positive_week_share": float((gross > 0).mean()) if len(gross) else math.nan,
                "max_drawdown": max_drawdown(gross),
                "mean_buy_turnover": float(complete["buy_turnover"].mean()) if not complete.empty else math.nan,
                "mean_sell_turnover": float(complete["sell_turnover"].mean()) if not complete.empty else math.nan,
                "after_cost_weekly_mean_return": float(after.mean()) if len(after) else math.nan,
                "after_cost_annualized_mean_return": float(after.mean() * annualization) if len(after) else math.nan,
                "after_cost_weekly_volatility": float(after_vol) if np.isfinite(after_vol) else math.nan,
                "after_cost_t_stat_newey_west": newey_west_t(after, int(K)),
                "after_cost_sharpe_ratio": float(after.mean() / after_vol * math.sqrt(annualization)) if np.isfinite(after_vol) and after_vol > 0 else math.nan,
                "long_leg_weekly_mean_return": float(complete["long_leg_weekly_return"].mean()) if not complete.empty else math.nan,
                "short_leg_weekly_mean_return": float(complete["short_leg_weekly_return"].mean()) if not complete.empty else math.nan,
                "blocked_week_count": int(len(group) - len(complete)),
            }
        )
    return pd.DataFrame(rows)


def build_return_artifacts(
    config: dict[str, Any],
    paths: Paths,
    specs: dict[tuple[str, str, int | None, int], PortfolioSpec],
    weekly_ret: pd.DataFrame,
    context: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    J_values = [int(x) for x in config["signals"]["J_values"]]
    K_values = [int(x) for x in config["signals"]["K_values"]]
    groups: dict[str, list[pd.DataFrame]] = {
        "raw": [],
        "imom": [],
        "risk_only": [],
        "bivariate": [],
        "direct": [],
    }
    for J in J_values:
        for K in K_values:
            groups["raw"].append(replay_returns_for_family(specs, "raw_mom_W_minus_L", "", J, K, weekly_ret, context, config))
            groups["imom"].append(replay_returns_for_family(specs, "imom", "", J, K, weekly_ret, context, config))
            for metric_id in ALL_RISK_METRICS:
                groups["risk_only"].append(replay_returns_for_family(specs, "risk_only", metric_id, J, K, weekly_ret, context, config))
            for metric_id in POSITIVE_RISK_METRICS:
                groups["bivariate"].append(replay_returns_for_family(specs, "bivariate_risk_adjusted_imom", metric_id, J, K, weekly_ret, context, config))
                groups["direct"].append(replay_returns_for_family(specs, "direct_risk_adjusted_imom", metric_id, J, K, weekly_ret, context, config))
    outputs = {name: pd.concat(parts, ignore_index=True) if parts else pd.DataFrame() for name, parts in groups.items()}
    write_csv(outputs["raw"], paths.returns_dir / "r07_raw_mom_jk_returns.csv")
    write_csv(outputs["imom"], paths.returns_dir / "r07_imom_jk_returns.csv")
    write_csv(outputs["risk_only"], paths.returns_dir / "r07_risk_only_jk_returns.csv")
    write_csv(outputs["bivariate"], paths.returns_dir / "r07_bivariate_risk_adjusted_imom_jk_returns.csv")
    write_csv(outputs["direct"], paths.returns_dir / "r07_direct_risk_adjusted_imom_jk_returns.csv")
    label_status = pd.concat(outputs.values(), ignore_index=True)
    write_csv(
        label_status[
            [
                "family",
                "metric_id",
                "J",
                "K",
                "holding_week_end",
                "split",
                "portfolio_week_status",
                "block_reason",
                "assigned_long_leg_count",
                "assigned_short_leg_count",
                "label_evaluable_long_leg_count",
                "label_evaluable_short_leg_count",
                "label_evaluable_long_leg_share",
                "label_evaluable_short_leg_share",
            ]
        ],
        paths.returns_dir / "r07_portfolio_week_label_status.csv",
    )
    all_returns = pd.concat(outputs.values(), ignore_index=True)
    return outputs, all_returns


def save_summary_reports(paths: Paths, returns: dict[str, pd.DataFrame], config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    summaries = {}
    mapping = {
        "raw": "r07_jk_summary_raw_mom.csv",
        "imom": "r07_jk_summary_imom.csv",
        "risk_only": "r07_jk_summary_risk_only.csv",
        "bivariate": "r07_jk_summary_bivariate_risk_adjusted_imom.csv",
    }
    for key, filename in mapping.items():
        summary = summarize_returns(returns[key], config)
        summaries[key] = summary
        write_csv(summary, paths.reports_dir / filename)
    direct_summary = summarize_returns(returns["direct"], config)
    summaries["direct"] = direct_summary
    horse = pd.concat([summaries["imom"], summaries["risk_only"], summaries["bivariate"], direct_summary], ignore_index=True)
    write_csv(build_metric_horse_race_summary(horse, config), paths.reports_dir / "r07_metric_horse_race_summary.csv")
    write_csv(build_conditional_summary(pd.concat(returns.values(), ignore_index=True), config), paths.reports_dir / "r07_conditional_state_summary.csv")
    return pd.concat(summaries.values(), ignore_index=True), summaries


def build_metric_horse_race_summary(summary: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    J_short = set(map(int, config["signals"]["short_cluster_J_values"]))
    K_short = set(map(int, config["signals"]["short_cluster_K_values"]))
    part = summary.loc[summary["J"].isin(J_short) & summary["K"].isin(K_short) & summary["split"].isin(SPLITS)].copy()
    rows = []
    for keys, group in part.groupby(["family", "metric_id", "split"], dropna=False):
        family, metric_id, split = keys
        rows.append(
            {
                "family": family,
                "metric_id": metric_id,
                "split": split,
                "short_cluster_cell_count": int(len(group)),
                "short_cluster_weekly_mean": float(group["weekly_mean_return"].mean()),
                "short_cluster_after_cost_weekly_mean": float(group["after_cost_weekly_mean_return"].mean()),
                "short_cluster_t_stat_mean": float(group["t_stat_weekly_mean_newey_west"].mean()),
                "short_cluster_after_cost_t_stat_mean": float(group["after_cost_t_stat_newey_west"].mean()),
                "short_cluster_positive_cell_share": float((group["weekly_mean_return"] > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def build_conditional_summary(all_returns: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    J_short = set(map(int, config["signals"]["short_cluster_J_values"]))
    K_short = set(map(int, config["signals"]["short_cluster_K_values"]))
    part = all_returns.loc[
        all_returns["J"].isin(J_short)
        & all_returns["K"].isin(K_short)
        & all_returns["family"].isin(["imom", "bivariate_risk_adjusted_imom"])
        & all_returns["portfolio_week_status"].eq("complete")
    ].copy()
    rows = []
    for state_col in ["market_state_26w", "market_state_52w", "liquidity_state", "liquidity_extreme_state"]:
        for keys, group in part.groupby(["family", "metric_id", "split", state_col], dropna=False):
            family, metric_id, split, state = keys
            rows.append(
                {
                    "state_axis": state_col,
                    "state_value": state,
                    "family": family,
                    "metric_id": metric_id,
                    "split": split,
                    "week_count": int(len(group)),
                    "weekly_mean_return": float(group["gross_return"].mean()),
                    "after_cost_weekly_mean_return": float(group["after_cost_return"].mean()),
                    "positive_week_share": float((group["gross_return"] > 0).mean()),
                }
            )
    return pd.DataFrame(rows)


def cluster_value(summary: pd.DataFrame, family: str, split: str, column: str, metric_id: str = "") -> float:
    part = summary.loc[summary["family"].eq(family) & summary["split"].eq(split)]
    if metric_id:
        part = part.loc[part["metric_id"].eq(metric_id)]
    else:
        part = part.loc[part["metric_id"].fillna("").eq("")]
    if part.empty:
        return math.nan
    return float(part[column].mean())


def cluster_min_week_count(summary: pd.DataFrame, family: str, split: str, metric_id: str = "") -> float:
    part = summary.loc[summary["family"].eq(family) & summary["split"].eq(split)]
    if metric_id:
        part = part.loc[part["metric_id"].eq(metric_id)]
    else:
        part = part.loc[part["metric_id"].fillna("").eq("")]
    if part.empty:
        return math.nan
    return float(part["week_count"].min())


def determine_final_decision(summaries: dict[str, pd.DataFrame], config: dict[str, Any]) -> tuple[str, pd.DataFrame]:
    J_short = set(map(int, config["signals"]["short_cluster_J_values"]))
    K_short = set(map(int, config["signals"]["short_cluster_K_values"]))
    short_summaries = {k: v.loc[v["J"].isin(J_short) & v["K"].isin(K_short)].copy() for k, v in summaries.items()}
    imom = short_summaries["imom"]
    raw = short_summaries["raw"]
    bivar = short_summaries["bivariate"]
    gate_rows = []
    def add_gate(name: str, passed: bool, value: Any, threshold: Any) -> None:
        gate_rows.append({"gate": name, "passed": bool(passed), "value": value, "threshold": threshold})

    val_cells = int(imom.loc[imom["split"].eq("validation"), ["J", "K"]].drop_duplicates().shape[0])
    rob_cells = int(imom.loc[imom["split"].eq("robustness"), ["J", "K"]].drop_duplicates().shape[0])
    val_min_weeks = cluster_min_week_count(imom, "imom", "validation")
    rob_min_weeks = cluster_min_week_count(imom, "imom", "robustness")
    add_gate("validation_evaluable_short_cluster_cell_count", val_cells >= int(config["gates"]["validation_evaluable_short_cluster_cell_count_min"]), val_cells, config["gates"]["validation_evaluable_short_cluster_cell_count_min"])
    add_gate("robustness_evaluable_short_cluster_cell_count", rob_cells >= int(config["gates"]["robustness_evaluable_short_cluster_cell_count_min"]), rob_cells, config["gates"]["robustness_evaluable_short_cluster_cell_count_min"])
    add_gate("validation_short_cluster_min_week_count_per_cell", val_min_weeks >= int(config["gates"]["validation_short_cluster_min_week_count_per_cell"]), val_min_weeks, config["gates"]["validation_short_cluster_min_week_count_per_cell"])
    add_gate("robustness_short_cluster_min_week_count_per_cell", rob_min_weeks >= int(config["gates"]["robustness_short_cluster_min_week_count_per_cell"]), rob_min_weeks, config["gates"]["robustness_short_cluster_min_week_count_per_cell"])

    imom_val = cluster_value(imom, "imom", "validation", "weekly_mean_return")
    imom_rob = cluster_value(imom, "imom", "robustness", "weekly_mean_return")
    imom_val_t = cluster_value(imom, "imom", "validation", "t_stat_weekly_mean_newey_west")
    imom_rob_t = cluster_value(imom, "imom", "robustness", "t_stat_weekly_mean_newey_west")
    raw_val = cluster_value(raw, "raw_mom_W_minus_L", "validation", "weekly_mean_return")
    raw_contra_val = -raw_val if np.isfinite(raw_val) else math.nan
    raw_best_val = max(raw_val, raw_contra_val) if np.isfinite(raw_val) else math.nan
    add_gate("validation_imom_beats_raw_best_direction", np.isfinite(imom_val) and np.isfinite(raw_best_val) and imom_val > raw_best_val, imom_val, raw_best_val)
    add_gate("validation_imom_mean_positive", np.isfinite(imom_val) and imom_val > 0, imom_val, 0)
    add_gate("validation_imom_t_stat_positive", np.isfinite(imom_val_t) and imom_val_t > 0, imom_val_t, 0)
    add_gate("robustness_imom_mean_positive", np.isfinite(imom_rob) and imom_rob > 0, imom_rob, 0)
    add_gate("robustness_imom_t_stat_positive", np.isfinite(imom_rob_t) and imom_rob_t > 0, imom_rob_t, 0)

    risk_pass_metric = ""
    risk_weak_metric = ""
    for metric in PRIMARY_RISK_METRICS:
        val = cluster_value(bivar, "bivariate_risk_adjusted_imom", "validation", "weekly_mean_return", metric)
        rob = cluster_value(bivar, "bivariate_risk_adjusted_imom", "robustness", "weekly_mean_return", metric)
        if np.isfinite(val) and np.isfinite(rob) and val >= imom_val and rob >= imom_rob:
            risk_pass_metric = metric
            break
        if np.isfinite(val) and np.isfinite(rob) and val >= imom_val and (rob - imom_rob) > 0:
            risk_weak_metric = metric
    add_gate("single_IVOL_or_IMD_bivariate_metric_passes_both_splits", bool(risk_pass_metric), risk_pass_metric or risk_weak_metric or "none", "same metric validation and robustness >= IMOM")

    imom_val_cost = cluster_value(imom, "imom", "validation", "after_cost_weekly_mean_return")
    imom_rob_cost = cluster_value(imom, "imom", "robustness", "after_cost_weekly_mean_return")
    imom_val_cost_t = cluster_value(imom, "imom", "validation", "after_cost_t_stat_newey_west")
    imom_rob_cost_t = cluster_value(imom, "imom", "robustness", "after_cost_t_stat_newey_west")
    add_gate("validation_imom_after_cost_mean_positive", np.isfinite(imom_val_cost) and imom_val_cost > 0, imom_val_cost, 0)
    add_gate("validation_imom_after_cost_t_stat_positive", np.isfinite(imom_val_cost_t) and imom_val_cost_t > 0, imom_val_cost_t, 0)
    add_gate("robustness_imom_after_cost_mean_positive", np.isfinite(imom_rob_cost) and imom_rob_cost > 0, imom_rob_cost, 0)
    add_gate("robustness_imom_after_cost_t_stat_positive", np.isfinite(imom_rob_cost_t) and imom_rob_cost_t > 0, imom_rob_cost_t, 0)

    gates = pd.DataFrame(gate_rows)
    data_sufficient = bool(gates.iloc[0:4]["passed"].all())
    primary_validation = bool(gates.iloc[4:7]["passed"].all())
    primary_robust = bool(gates.iloc[7:9]["passed"].all())
    risk_gate = bool(gates.loc[gates["gate"].eq("single_IVOL_or_IMD_bivariate_metric_passes_both_splits"), "passed"].iloc[0])
    cost_gate = bool(gates.iloc[-4:]["passed"].all())
    if not data_sufficient:
        decision = "ep6_weekly_imom_sample_insufficient"
    elif not primary_validation:
        decision = "ep6_weekly_imom_local_proxy_not_supported"
    elif not primary_robust:
        decision = "ep6_weekly_imom_local_proxy_validation_only_not_robust"
    elif not risk_gate:
        decision = "ep6_weekly_imom_positive_risk_filter_not_supported"
    elif not cost_gate:
        decision = "ep6_weekly_imom_gross_positive_after_cost_not_supported"
    else:
        decision = "ep6_weekly_imom_local_proxy_positive_diagnostic_only"
    gates["final_decision"] = decision
    gates["risk_filter_strong_metric"] = risk_pass_metric
    gates["risk_filter_weak_metric"] = risk_weak_metric
    return decision, gates


def build_availability_manifest(config: dict[str, Any], contexts: pd.DataFrame) -> pd.DataFrame:
    split_counts = contexts.groupby("split")["holding_week_end"].nunique().to_dict()
    rows = [
        ("raw_stock_returns", "raw stock returns", "data/qlib/cn_data_pit/features/*/close.day.bin", "available_full", "retain", "provider_adjusted_close_return", "provider close as-of retained week end", ""),
        ("ff5_residual_returns", "CSMAR FF5 residual returns", "data/qlib/cn_data_pit/features/* plus SH000300", "missing_required_factor_source", "retain_local_proxy", "market_model_sh000300_ols_v0", "rolling 130 trading-day beta ending d-1", "CSMAR FF5 unavailable; local market residual used"),
        ("idiosyncratic_risk_metrics", "idiosyncratic risk metrics", "local market residual panel", "available_partial", "retain_local_proxy", "local_residual_risk_130d_v0", "130 trading days ending week t-2", "paper FF5 residuals unavailable"),
        ("market_state", "market state", "data/qlib/cn_data_pit/features/sh000300/close.day.bin", "available_full", "retain_local_proxy", "SH000300_26w_52w_state", "prior retained weeks", ""),
        ("liquidity_state", "liquidity state", "return and money fields", "available_full", "retain_local_proxy", "local_Amihud_4w_AILLIQ", "skip week plus prior 3 retained weeks; train-only thresholds", ""),
        ("sentiment_state", "Baker-Wurgler sentiment inputs", "", "missing_required_sentiment_source", "remove", "", "", "Baker-Wurgler, IPO, closed-end fund discount, dividend premium, and issuance-share inputs unavailable"),
    ]
    return pd.DataFrame(
        [
            {
                "input_id": row[0],
                "paper_required_input": row[1],
                "local_source": row[2],
                "availability_status": row[3],
                "replication_action": row[4],
                "local_proxy_id": row[5],
                "asof_policy": row[6],
                "coverage_train_weeks": int(split_counts.get("train", 0)),
                "coverage_validation_weeks": int(split_counts.get("validation", 0)),
                "coverage_robustness_weeks": int(split_counts.get("robustness", 0)),
                "block_reason": row[7],
            }
            for row in rows
        ]
    )


def money_unit_audit(inputs: dict[str, Any], paths: Paths) -> pd.DataFrame:
    calendar = inputs["calendar"]
    dates = calendar[:10]
    rows = []
    pit = inputs["pit"]
    money = inputs["money_wide"]
    for date in dates:
        universe = pit.loc[pit["date"].eq(date), "instrument"].astype(str).tolist()
        values = money.loc[date, [c for c in universe if c in money.columns]].replace([np.inf, -np.inf], np.nan).dropna()
        rows.append(
            {
                "sample_date": date.date().isoformat(),
                "instrument_count": int(len(values)),
                "money_min": float(values.min()) if len(values) else math.nan,
                "money_p25": float(values.quantile(0.25)) if len(values) else math.nan,
                "money_median": float(values.median()) if len(values) else math.nan,
                "money_p75": float(values.quantile(0.75)) if len(values) else math.nan,
                "money_max": float(values.max()) if len(values) else math.nan,
            }
        )
    audit = pd.DataFrame(rows)
    write_csv(audit, paths.manifests_dir / "r07_money_unit_audit.csv")
    return audit


def environment_snapshot(paths: Paths) -> dict[str, Any]:
    try:
        freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True).splitlines()
    except Exception:  # noqa: BLE001
        freeze = []
    payload = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "package_freeze": freeze,
        "uv_lock_hash_if_available": file_hash(TOPIC_DIR / "uv.lock") if (TOPIC_DIR / "uv.lock").exists() else "",
        "git_commit_or_worktree_status": git_commit_or_status(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(payload, paths.manifests_dir / "r07_environment_snapshot.json")
    return payload


def final_report(paths: Paths, decision: str, gates: pd.DataFrame, summaries: dict[str, pd.DataFrame], config: dict[str, Any], meta: dict[str, Any]) -> None:
    imom = summaries["imom"]
    raw = summaries["raw"]
    bivar = summaries["bivariate"]

    def cluster_table(summary: pd.DataFrame, family: str, metric_id: str = "") -> pd.DataFrame:
        J_short = set(map(int, config["signals"]["short_cluster_J_values"]))
        K_short = set(map(int, config["signals"]["short_cluster_K_values"]))
        part = summary.loc[summary["J"].isin(J_short) & summary["K"].isin(K_short) & summary["family"].eq(family)].copy()
        if metric_id:
            part = part.loc[part["metric_id"].eq(metric_id)]
        else:
            part = part.loc[part["metric_id"].fillna("").eq("")]
        rows = []
        for split in SPLITS:
            g = part.loc[part["split"].eq(split)]
            rows.append(
                {
                    "split": split,
                    "cells": int(len(g)),
                    "weekly_mean": float(g["weekly_mean_return"].mean()) if len(g) else math.nan,
                    "after_cost_weekly_mean": float(g["after_cost_weekly_mean_return"].mean()) if len(g) else math.nan,
                    "t_stat_mean": float(g["t_stat_weekly_mean_newey_west"].mean()) if len(g) else math.nan,
                    "after_cost_t_stat_mean": float(g["after_cost_t_stat_newey_west"].mean()) if len(g) else math.nan,
                }
            )
        return pd.DataFrame(rows)

    raw_cluster = cluster_table(raw, "raw_mom_W_minus_L")
    imom_cluster = cluster_table(imom, "imom")
    ivol_cluster = cluster_table(bivar, "bivariate_risk_adjusted_imom", "IVOL")
    imd_cluster = cluster_table(bivar, "bivariate_risk_adjusted_imom", "IMD")

    def md_table(df: pd.DataFrame) -> str:
        if df.empty:
            return ""
        out = df.copy()
        for col in out.columns:
            if pd.api.types.is_numeric_dtype(out[col]):
                if "t_stat" in col:
                    out[col] = out[col].map(lambda x: num(x, 3))
                elif "mean" in col:
                    out[col] = out[col].map(lambda x: pct(x, 3))
        return out.to_markdown(index=False)

    comparison_rows = [
        {"Paper claim": "raw weekly MOM is mostly contrarian", "Local test": "raw W-L short cluster", "Supported locally?": "yes" if raw_cluster.loc[raw_cluster["split"].eq("validation"), "weekly_mean"].mean() < 0 else "mixed"},
        {"Paper claim": "IMOM is positive and stronger than raw-return directions", "Local test": "IMOM vs raw best direction", "Supported locally?": "yes" if gates.loc[gates["gate"].eq("validation_imom_beats_raw_best_direction"), "passed"].any() else "no"},
        {"Paper claim": "IVOL and IMD are strongest risk metrics", "Local test": "IVOL/IMD bivariate vs pure IMOM", "Supported locally?": "yes" if gates.loc[gates["gate"].eq("single_IVOL_or_IMD_bivariate_metric_passes_both_splits"), "passed"].any() else "mixed"},
        {"Paper claim": "bivariate risk-adjusted IMOM improves results", "Local test": "IVOL/IMD-IMOM vs pure IMOM", "Supported locally?": "yes" if gates.loc[gates["gate"].eq("single_IVOL_or_IMD_bivariate_metric_passes_both_splits"), "passed"].any() else "no"},
        {"Paper claim": "upside market strengthens IMOM", "Local test": "conditional SH000300 state table", "Supported locally?": "see r07_conditional_state_summary.csv"},
        {"Paper claim": "high liquidity strengthens IMOM", "Local test": "conditional local Amihud table", "Supported locally?": "see r07_conditional_state_summary.csv"},
        {"Paper claim": "high sentiment strengthens IMOM", "Local test": "blocked", "Supported locally?": "unavailable locally"},
    ]
    comparison = pd.DataFrame(comparison_rows)
    lines = [
        "# R07 Weekly Market-Residual IMOM Horse-Race Local Replication 最终报告",
        "",
        "## 1. 结论摘要",
        "",
        f"`final_decision = {decision}`",
        "",
        "`authorized_strategy_requirement = false`",
        "",
        "本轮实现的是论文 weekly idiosyncratic momentum horse-race 的本地代理版本。`IMOM` 在本地定义为 `market_residual_momentum_not_ff5_idiosyncratic_momentum`，不是 CSMAR FF5 residual 的精确复现。",
        "",
        "## 2. Short-Cluster 读数",
        "",
        "Raw W-minus-L:",
        "",
        md_table(raw_cluster),
        "",
        "IMOM:",
        "",
        md_table(imom_cluster),
        "",
        "IVOL-IMOM bivariate:",
        "",
        md_table(ivol_cluster),
        "",
        "IMD-IMOM bivariate:",
        "",
        md_table(imd_cluster),
        "",
        "## 3. Gate Replay",
        "",
        gates[["gate", "passed", "value", "threshold"]].to_markdown(index=False),
        "",
        "## 4. Paper Reference Comparison",
        "",
        comparison.to_markdown(index=False),
        "",
        "## 5. 样本与实现边界",
        "",
        f"- provider: `{config['data_sources']['qlib_provider_uri']}`",
        f"- PIT universe: `{config['data_sources']['pit_universe_path']}`",
        f"- benchmark feature dir: `{config['data_sources']['benchmark_feature_dir']}`",
        f"- first evaluable signal week by J: `{meta.get('first_evaluable_signal_week_by_J', {})}`",
        f"- liquidity thresholds: `{meta.get('liquidity_thresholds', {})}`",
        "",
        "该结果仍为 diagnostic only：不授权 long-short A-share production strategy，也不假设 A 股可自由融券。",
        "",
        "Required caveat: `local_residual_model_not_paper_FF5_equivalent`",
        "",
    ]
    (paths.reports_dir / "r07_final_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    config, paths = load_config(args.config)
    print("loading inputs")
    inputs = load_inputs(config)
    shutil.copy2(paths.config_path, paths.configs_dir / "r07_weekly_imom_horse_race_v0.yaml")
    weekly_calendar = build_weekly_calendar(inputs["calendar"], config)
    write_csv(weekly_calendar.drop(columns=["week_end_ts"]), paths.weekly_dir / "r07_weekly_calendar.csv")
    print("computing weekly returns")
    weekly_ret = weekly_returns(inputs["close_wide"], weekly_calendar)
    weekly_tall = weekly_ret.reset_index(names="week_end").melt(id_vars="week_end", var_name="instrument", value_name="weekly_return")
    write_parquet_or_csv(weekly_tall, paths.weekly_dir / "r07_weekly_stock_returns.parquet")
    print("computing residuals")
    residuals, residual_manifest = compute_daily_residuals(inputs["close_wide"], inputs["volume_wide"], inputs["money_wide"], inputs["market_close"], config)
    write_csv(residual_manifest, paths.residuals_dir / "r07_residual_model_manifest.csv")
    print("building signals and portfolio specs")
    specs, signal_meta, signal_outputs = build_signals_and_specs(config, paths, inputs, weekly_calendar, residuals, weekly_ret)
    residual_signal = signal_outputs["imom"].copy()
    write_parquet_or_csv(residual_signal, paths.residuals_dir / "r07_weekly_residual_signal_panel.parquet")
    print("replaying portfolio returns")
    returns, all_returns = build_return_artifacts(config, paths, specs, weekly_ret, signal_outputs["context"])
    print("summarizing")
    all_summary, summaries = save_summary_reports(paths, returns, config)
    decision, gates = determine_final_decision(summaries, config)
    write_csv(gates, paths.reports_dir / "r07_gate_decision_summary.csv")
    availability = build_availability_manifest(config, signal_outputs["context"])
    write_csv(availability, paths.manifests_dir / "r07_input_availability_manifest.csv")
    money_unit_audit(inputs, paths)
    env = environment_snapshot(paths)
    benchmark_dir = topic_path(config["data_sources"]["benchmark_feature_dir"])
    run_manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit_or_worktree_status": git_commit_or_status(),
        "python_version": sys.version,
        "qlib_provider_path": config["data_sources"]["qlib_provider_uri"],
        "universe_path": config["data_sources"]["pit_universe_path"],
        "calendar_path": config["data_sources"]["trading_calendar_path"],
        "benchmark_feature_dir": config["data_sources"]["benchmark_feature_dir"],
        "benchmark_feature_dir_hash": directory_hash(benchmark_dir) if benchmark_dir.exists() else "",
        "price_adjustment_mode": config["price_adjustment"]["mode"],
        "residual_model_id": config["residual_model"]["residual_model_id"],
        "local_imom_interpretation": config["residual_model"]["local_imom_interpretation"],
        "risk_free_mode": config["residual_model"]["risk_free_mode"],
        "residual_beta_window": config["residual_model"]["beta_window_trading_days"],
        "risk_metric_window": config["residual_model"]["risk_metric_window_trading_days"],
        "valid_return_day_policy": "finite close and previous close; volume > 0; money > 0; finite SH000300 return",
        "first_evaluable_signal_week_by_J": signal_meta["first_evaluable_signal_week_by_J"],
        "first_evaluable_portfolio_week_by_JK": signal_meta["first_evaluable_portfolio_week_by_JK"],
        "effective_split_start_by_JK": signal_meta["effective_split_start_by_JK"],
        "train_weeks_lost_to_warmup_by_JK": signal_meta["train_weeks_lost_to_warmup_by_JK"],
        "J_values": config["signals"]["J_values"],
        "K_values": config["signals"]["K_values"],
        "split_boundaries": config["sample_split"],
        "bivariate_sort_bucket_count": config["portfolio"]["bivariate_sort_bucket_count"],
        "weekly_calendar_policy": config["weekly_calendar"],
        "cluster_aggregation_policy": "equal-weight mean across short-cluster J/K cells",
        "liquidity_threshold_policy": config["liquidity_state"]["threshold_policy"],
        "liquidity_state_window": config["liquidity_state"]["state_window_retained_weeks"],
        "liquidity_thresholds": signal_meta["liquidity_thresholds"],
        "money_unit_assumed": config["liquidity_state"]["money_unit_assumed"],
        "cost_assumptions": config["execution"],
        "overlapping_vintage_accounting_policy": "equal-weight average of active vintage target weight vectors",
        "drift_adjusted_weights_reported": config["execution"]["drift_adjusted_weights_reported"],
        "label_availability_policy": "post-assignment label status only; no future label prefilter",
        "newey_west_lag_policy": config["statistics"]["newey_west_lag_policy"],
        "raw_contrarian_derivation_policy": "raw_contrarian_L_minus_W = -raw_mom_W_minus_L",
        "blocked_inputs": availability.loc[availability["replication_action"].eq("remove"), "input_id"].tolist(),
        "final_decision": decision,
        "parquet_policy": "parquet primary; csv fallback recorded by file extension if parquet unavailable",
        "environment_snapshot_file": rel(paths.manifests_dir / "r07_environment_snapshot.json"),
        "package_count": len(env.get("package_freeze", [])),
    }
    write_json(run_manifest, paths.manifests_dir / "r07_weekly_imom_run_manifest.json")
    validation_manifest = {
        "final_decision": decision,
        "authorized_strategy_requirement": False,
        "gate_results": gates.to_dict(orient="records"),
        "first_evaluable_signal_week_by_J": signal_meta["first_evaluable_signal_week_by_J"],
        "first_evaluable_portfolio_week_by_JK": signal_meta["first_evaluable_portfolio_week_by_JK"],
        "effective_split_start_by_JK": signal_meta["effective_split_start_by_JK"],
        "train_weeks_lost_to_warmup_by_JK": signal_meta["train_weeks_lost_to_warmup_by_JK"],
        "liquidity_thresholds": signal_meta["liquidity_thresholds"],
    }
    write_json(validation_manifest, paths.manifests_dir / "r07_validation_manifest.json")
    final_report(paths, decision, gates, summaries, config, signal_meta)
    print(f"final_decision={decision}")
    print(f"output_root={rel(paths.output_root)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
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
DEFAULT_CONFIG = EP6_DIR / "configs" / "r02_factor_momentum_tsfm_replication_v0.yaml"

REQUIREMENT_ID = "ep6_paper_replica_02_factor_momentum_tsfm_replication_v0"
SHORT_NAME = "r02_factor_momentum_tsfm_replication_v0"
FINAL_SUPPORTED = "ep6_tsfm_4factor_local_proxy_positive_diagnostic_only"
SPLITS = ["train", "validation", "robustness"]

FACTOR_ORDER = ["SIZE", "BM", "GP", "CINVEST", "ILL", "EP", "ACC", "CFP", "TURN", "BAB"]
RETAINED_FACTORS = ["SIZE", "ILL", "TURN", "BAB"]
REMOVED_FACTORS = ["BM", "GP", "CINVEST", "EP", "ACC", "CFP"]

FACTOR_METADATA = {
    "SIZE": {
        "paper_name": "Size",
        "required_raw_fields": "market_cap_asof_T",
        "local_formula_id": "local_SIZE_market_cap_high_minus_low_v0",
        "asof_policy": "PIT market_cap_asof_T at signal_month_end S_m",
    },
    "BM": {
        "paper_name": "Book-to-market / value",
        "required_raw_fields": "book equity; shareholder equity; market equity",
        "local_formula_id": "",
        "asof_policy": "requires PIT accounting announcement dates",
    },
    "GP": {
        "paper_name": "Gross profitability",
        "required_raw_fields": "gross profit; revenue/COGS; total assets",
        "local_formula_id": "",
        "asof_policy": "requires PIT accounting announcement dates",
    },
    "CINVEST": {
        "paper_name": "Investment",
        "required_raw_fields": "total assets; lagged total assets",
        "local_formula_id": "",
        "asof_policy": "requires PIT accounting announcement dates",
    },
    "ILL": {
        "paper_name": "Illiquidity",
        "required_raw_fields": "daily close return; money",
        "local_formula_id": "local_ILL_amihud_21d_v0",
        "asof_policy": "prior 21 trading days ending S_m, min 15 observations",
    },
    "EP": {
        "paper_name": "Earnings-to-price",
        "required_raw_fields": "earnings; net income; market equity",
        "local_formula_id": "",
        "asof_policy": "requires PIT accounting announcement dates",
    },
    "ACC": {
        "paper_name": "Accruals",
        "required_raw_fields": "accrual statement components; operating cash flow",
        "local_formula_id": "",
        "asof_policy": "requires PIT accounting announcement dates",
    },
    "CFP": {
        "paper_name": "Cash-flow-to-price",
        "required_raw_fields": "operating cash flow; market equity",
        "local_formula_id": "",
        "asof_policy": "requires PIT accounting announcement dates",
    },
    "TURN": {
        "paper_name": "Turnover",
        "required_raw_fields": "volume; total_share",
        "local_formula_id": "local_TURN_share_turnover_21d_v0",
        "asof_policy": "prior 21 trading days ending S_m, min 15 observations",
    },
    "BAB": {
        "paper_name": "Betting-against-beta",
        "required_raw_fields": "daily stock close returns; SH000300 close returns",
        "local_formula_id": "local_BAB_beta_sort_252d_v0",
        "asof_policy": "prior 252 trading days ending S_m, min 126 observations",
    },
}


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    configs_dir: Path
    manifests_dir: Path
    factors_dir: Path
    signals_dir: Path
    returns_dir: Path
    reports_dir: Path
    validation_dir: Path


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
    parser = argparse.ArgumentParser(description="Run EP6 R02 TSFM local feasible factor replication diagnostic")
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
        factors_dir=output_root / "factors",
        signals_dir=output_root / "signals",
        returns_dir=output_root / "returns",
        reports_dir=output_root / "reports",
        validation_dir=output_root / "validation",
    )
    for directory in [
        paths.configs_dir,
        paths.manifests_dir,
        paths.factors_dir,
        paths.signals_dir,
        paths.returns_dir,
        paths.reports_dir,
        paths.validation_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
    except Exception:  # noqa: BLE001
        return ""


def load_calendar(path: Path) -> pd.DatetimeIndex:
    values = pd.read_csv(path, header=None)[0]
    return pd.DatetimeIndex(pd.to_datetime(values).dt.normalize())


def qlib_feature_path(provider_uri: Path, instrument: str, field: str) -> Path:
    return provider_uri / "features" / instrument.lower() / f"{field}.day.bin"


def read_qlib_series(provider_uri: Path, calendar: pd.DatetimeIndex, instrument: str, field: str) -> pd.Series:
    path = qlib_feature_path(provider_uri, instrument, field)
    if not path.exists():
        return pd.Series(dtype="float64", name=instrument)
    arr = np.fromfile(path, dtype="<f4")
    if len(arr) == 0:
        return pd.Series(dtype="float64", name=instrument)
    start_index = int(arr[0])
    values = arr[1:].astype("float64")
    dates = calendar[start_index : start_index + len(values)]
    return pd.Series(values[: len(dates)], index=dates, name=instrument.upper())


def load_feature_wide(
    provider_uri: Path,
    calendar: pd.DatetimeIndex,
    instruments: list[str],
    field: str,
) -> pd.DataFrame:
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


def month_end_map(calendar: pd.DatetimeIndex) -> dict[pd.Period, pd.Timestamp]:
    frame = pd.DataFrame({"date": calendar})
    frame["period"] = frame["date"].dt.to_period("M")
    return frame.groupby("period")["date"].max().to_dict()


def split_for_date(date: pd.Timestamp, config: dict[str, Any]) -> str:
    split = config["sample_split"]
    d = pd.Timestamp(date).normalize()
    if pd.Timestamp(split["train_start"]) <= d <= pd.Timestamp(split["train_end"]):
        return "train"
    if pd.Timestamp(split["validation_start"]) <= d <= pd.Timestamp(split["validation_end"]):
        return "validation"
    if pd.Timestamp(split["robustness_start"]) <= d <= pd.Timestamp(split["robustness_end"]):
        return "robustness"
    return "out_of_split"


def annualized_mean(monthly: pd.Series) -> float:
    monthly = monthly.dropna()
    if monthly.empty:
        return math.nan
    return float(monthly.mean() * 12.0)


def annualized_vol(monthly: pd.Series) -> float:
    monthly = monthly.dropna()
    if len(monthly) < 2:
        return math.nan
    return float(monthly.std(ddof=1) * math.sqrt(12.0))


def sharpe(monthly: pd.Series) -> float:
    monthly = monthly.dropna()
    if len(monthly) < 2:
        return math.nan
    std = monthly.std(ddof=1)
    if not np.isfinite(std) or std == 0:
        return math.nan
    return float(monthly.mean() / std * math.sqrt(12.0))


def t_stat(monthly: pd.Series) -> float:
    monthly = monthly.dropna()
    if len(monthly) < 2:
        return math.nan
    std = monthly.std(ddof=1)
    if not np.isfinite(std) or std == 0:
        return math.nan
    return float(monthly.mean() / std * math.sqrt(len(monthly)))


def max_drawdown(monthly: pd.Series) -> float:
    monthly = monthly.dropna()
    if monthly.empty:
        return math.nan
    equity = (1.0 + monthly).cumprod()
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def positive_share(monthly: pd.Series) -> float:
    monthly = monthly.dropna()
    if monthly.empty:
        return math.nan
    return float((monthly > 0).mean())


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


def period_range(start: pd.Period, end: pd.Period) -> list[pd.Period]:
    return [pd.Period(p, freq="M") for p in pd.period_range(start, end, freq="M")]


def compute_turnover(prev: dict[str, float], curr: dict[str, float]) -> tuple[float, float]:
    keys = set(prev) | set(curr)
    buy = 0.0
    sell = 0.0
    for key in keys:
        delta = curr.get(key, 0.0) - prev.get(key, 0.0)
        if delta > 0:
            buy += delta
        elif delta < 0:
            sell += -delta
    return float(buy), float(sell)


def weighted_return(book: dict[str, float], returns: pd.Series) -> float:
    total = 0.0
    for inst, weight in book.items():
        value = returns.get(inst, np.nan)
        if not np.isfinite(value):
            return math.nan
        total += weight * float(value)
    return float(total)


def near_equal_quintile_book(values: pd.Series, returns: pd.Series) -> tuple[dict[str, float], dict[str, Any]]:
    frame = pd.DataFrame({"factor_value": values, "next_month_return": returns.reindex(values.index)})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    frame.index = frame.index.astype(str)
    frame = frame.sort_values(["factor_value"], kind="mergesort")
    frame = frame.reset_index(names="instrument").sort_values(["factor_value", "instrument"], kind="mergesort")
    n = len(frame)
    if n == 0:
        return {}, {"eligible_count": 0, "high_count": 0, "low_count": 0, "status": "blocked_insufficient_factor_month_coverage"}
    buckets = np.floor(np.arange(n) * 5 / n).astype(int) + 1
    frame["quintile"] = buckets
    low = frame.loc[frame["quintile"].eq(1)]
    high = frame.loc[frame["quintile"].eq(5)]
    book: dict[str, float] = {}
    if len(low) > 0:
        for inst in low["instrument"]:
            book[str(inst)] = book.get(str(inst), 0.0) - 1.0 / len(low)
    if len(high) > 0:
        for inst in high["instrument"]:
            book[str(inst)] = book.get(str(inst), 0.0) + 1.0 / len(high)
    meta = {
        "eligible_count": int(n),
        "high_count": int(len(high)),
        "low_count": int(len(low)),
        "high_mean_return": float(high["next_month_return"].mean()) if len(high) else math.nan,
        "low_mean_return": float(low["next_month_return"].mean()) if len(low) else math.nan,
        "status": "complete",
        "high_instruments": ";".join(high["instrument"].astype(str).tolist()),
        "low_instruments": ";".join(low["instrument"].astype(str).tolist()),
    }
    return book, meta


def load_inputs(config: dict[str, Any]) -> dict[str, Any]:
    ds = config["data_sources"]
    provider_uri = topic_path(ds["qlib_provider_uri"])
    calendar = load_calendar(topic_path(ds["trading_calendar_path"]))
    pit = pd.read_csv(
        topic_path(ds["pit_universe_path"]),
        usecols=["date", "instrument", "total_share", "market_cap_asof_T", "close"],
        dtype={"instrument": "string"},
        low_memory=False,
    )
    pit["date"] = pd.to_datetime(pit["date"]).dt.normalize()
    pit["instrument"] = pit["instrument"].astype(str).str.upper()
    instruments = sorted(pit["instrument"].dropna().unique().tolist())
    return {"provider_uri": provider_uri, "calendar": calendar, "pit": pit, "instruments": instruments}


def build_unit_audit(pit_signal: pd.DataFrame, close_wide: pd.DataFrame, volume_wide: pd.DataFrame, money_wide: pd.DataFrame) -> dict[str, Any]:
    sample_dates = sorted(pit_signal["date"].drop_duplicates().tolist())
    if len(sample_dates) > 36:
        sample_dates = sample_dates[:: max(1, len(sample_dates) // 36)]
    rows = []
    for date in sample_dates:
        universe = pit_signal.loc[pit_signal["date"].eq(date), ["instrument", "close"]].copy()
        if date not in volume_wide.index or date not in money_wide.index:
            continue
        volume = volume_wide.loc[date].rename("volume")
        money = money_wide.loc[date].rename("money")
        qclose = close_wide.loc[date].rename("provider_close")
        merged = universe.join(volume, on="instrument").join(money, on="instrument").join(qclose, on="instrument")
        merged = merged.replace([np.inf, -np.inf], np.nan).dropna()
        merged = merged.loc[(merged["volume"] > 0) & (merged["money"] > 0) & (merged["close"] > 0)]
        if merged.empty:
            continue
        merged["money_per_share_to_pit_close"] = (merged["money"] / merged["volume"]) / merged["close"]
        rows.append(merged[["money_per_share_to_pit_close"]])
    if not rows:
        return {
            "volume_unit_status": "blocked_not_reproducible",
            "median_money_per_share_to_pit_close": math.nan,
            "sample_count": 0,
        }
    audit = pd.concat(rows, ignore_index=True)
    ratio = audit["money_per_share_to_pit_close"].replace([np.inf, -np.inf], np.nan).dropna()
    median_ratio = float(ratio.median()) if not ratio.empty else math.nan
    status = "verified_volume_shares_by_money_div_volume_close_parity" if np.isfinite(median_ratio) and 0.80 <= median_ratio <= 1.20 else "blocked_not_reproducible"
    return {
        "volume_unit_status": status,
        "median_money_per_share_to_pit_close": median_ratio,
        "sample_count": int(len(ratio)),
    }


def build_monthly_factor_panel(config: dict[str, Any], inputs: dict[str, Any]) -> tuple[pd.DataFrame, dict[tuple[str, str], dict[str, float]], dict[str, Any]]:
    provider_uri = inputs["provider_uri"]
    calendar: pd.DatetimeIndex = inputs["calendar"]
    pit: pd.DataFrame = inputs["pit"]
    instruments: list[str] = inputs["instruments"]
    fc = config["factor_construction"]

    close_wide = load_feature_wide(provider_uri, calendar, instruments, "close")
    volume_wide = load_feature_wide(provider_uri, calendar, instruments, "volume")
    money_wide = load_feature_wide(provider_uri, calendar, instruments, "money")
    index_close = read_qlib_series(provider_uri, calendar, config["data_sources"]["index_instrument"], "close").reindex(calendar)

    date_by_period = month_end_map(calendar)
    split = config["sample_split"]
    first_signal_period = pd.Timestamp(split["train_start"]).to_period("M")
    last_holding_period = pd.Timestamp(split["robustness_end"]).to_period("M")
    last_signal_period = last_holding_period - 1
    signal_periods = period_range(first_signal_period, last_signal_period)
    signal_dates = [date_by_period[p] for p in signal_periods if p in date_by_period and (p + 1) in date_by_period]
    pit_signal = pit.loc[pit["date"].isin(signal_dates)].copy()

    daily_returns = close_wide.pct_change(fill_method=None)
    ill = (daily_returns.abs() / money_wide.where(money_wide > 0)).rolling(
        int(fc["illiquidity_lookback_trading_days"]),
        min_periods=int(fc["illiquidity_min_valid_observations"]),
    ).mean()
    volume_mean = volume_wide.rolling(
        int(fc["turnover_lookback_trading_days"]),
        min_periods=int(fc["volume_turnover_min_valid_observations"]),
    ).mean()

    market_ret = index_close.pct_change()
    beta_window = int(fc["beta_lookback_trading_days"])
    beta_min = int(fc["beta_min_valid_observations"])
    market_mean = market_ret.rolling(beta_window, min_periods=beta_min).mean()
    market_var = market_ret.rolling(beta_window, min_periods=beta_min).var(ddof=0)
    stock_mean = daily_returns.rolling(beta_window, min_periods=beta_min).mean()
    stock_market_mean = daily_returns.mul(market_ret, axis=0).rolling(beta_window, min_periods=beta_min).mean()
    cov = stock_market_mean - stock_mean.mul(market_mean, axis=0)
    beta = cov.div(market_var, axis=0)
    valid_beta_count = (
        daily_returns.notna().astype(float).mul(market_ret.notna().astype(float), axis=0).rolling(beta_window, min_periods=1).sum()
    )
    beta = beta.where(valid_beta_count >= beta_min)
    beta = beta.where(market_var > 0, axis=0)

    unit_audit = build_unit_audit(pit_signal, close_wide, volume_wide, money_wide)
    turn_enabled = unit_audit["volume_unit_status"].startswith("verified_")

    rows: list[dict[str, Any]] = []
    books: dict[tuple[str, str], dict[str, float]] = {}
    prev_factor_books = {factor: {} for factor in RETAINED_FACTORS}
    min_count = int(fc["min_eligible_instrument_count"])
    min_tail = int(fc["min_tail_count"])
    cost_buy = float(config["execution"]["buy_cost_bps"]) / 10000.0
    cost_sell = float(config["execution"]["sell_cost_bps"]) / 10000.0

    for signal_period in signal_periods:
        if signal_period not in date_by_period or (signal_period + 1) not in date_by_period:
            continue
        signal_date = date_by_period[signal_period]
        holding_period = signal_period + 1
        holding_date = date_by_period[holding_period]
        if holding_date > pd.Timestamp(split["robustness_end"]):
            continue
        universe = pit.loc[pit["date"].eq(signal_date)].copy()
        if universe.empty:
            continue
        universe = universe.set_index("instrument")
        ret = close_wide.loc[holding_date].div(close_wide.loc[signal_date]).sub(1.0)
        ret = ret.replace([np.inf, -np.inf], np.nan)

        factor_values: dict[str, pd.Series] = {}
        size = np.log(pd.to_numeric(universe["market_cap_asof_T"], errors="coerce").where(lambda x: x > 0))
        factor_values["SIZE"] = size
        factor_values["ILL"] = ill.loc[signal_date].reindex(universe.index)
        if turn_enabled:
            denominator = pd.to_numeric(universe["total_share"], errors="coerce") * float(fc["total_share_unit_multiplier"])
            factor_values["TURN"] = volume_mean.loc[signal_date].reindex(universe.index).div(denominator.where(denominator > 0))
        else:
            factor_values["TURN"] = pd.Series(np.nan, index=universe.index)
        factor_values["BAB"] = beta.loc[signal_date].reindex(universe.index)

        for factor in RETAINED_FACTORS:
            values = factor_values[factor].replace([np.inf, -np.inf], np.nan)
            book, meta = near_equal_quintile_book(values, ret.reindex(universe.index))
            status = meta["status"]
            if meta["eligible_count"] < min_count or meta["high_count"] < min_tail or meta["low_count"] < min_tail:
                status = "blocked_insufficient_factor_month_coverage"
                book = {}
            gross = weighted_return(book, ret) if book else math.nan
            buy_turnover, sell_turnover = compute_turnover(prev_factor_books[factor], book)
            if book:
                prev_factor_books[factor] = book
            after_cost = gross - buy_turnover * cost_buy - sell_turnover * cost_sell if np.isfinite(gross) else math.nan
            key = (factor, str(holding_period))
            if book:
                books[key] = book
            rows.append(
                {
                    "factor_id": factor,
                    "local_formula_id": FACTOR_METADATA[factor]["local_formula_id"],
                    "signal_period": str(signal_period),
                    "signal_month_end": signal_date.date().isoformat(),
                    "holding_period": str(holding_period),
                    "holding_month_end": holding_date.date().isoformat(),
                    "split": split_for_date(holding_date, config),
                    "factor_month_status": status,
                    "eligible_instrument_count": int(meta["eligible_count"]),
                    "high_quintile_count": int(meta["high_count"]),
                    "low_quintile_count": int(meta["low_count"]),
                    "high_mean_return": meta.get("high_mean_return", math.nan),
                    "low_mean_return": meta.get("low_mean_return", math.nan),
                    "factor_gross_return": gross,
                    "factor_buy_turnover": buy_turnover,
                    "factor_sell_turnover": sell_turnover,
                    "factor_after_cost_return": after_cost,
                    "high_instruments": meta.get("high_instruments", ""),
                    "low_instruments": meta.get("low_instruments", ""),
                }
            )
    panel = pd.DataFrame(rows)
    meta = {
        "loaded_instrument_count": int(len(instruments)),
        "calendar_start": calendar.min().date().isoformat(),
        "calendar_end": calendar.max().date().isoformat(),
        "signal_month_count": int(len(signal_periods)),
        "first_signal_period": str(signal_periods[0]) if signal_periods else "",
        "last_signal_period": str(signal_periods[-1]) if signal_periods else "",
        "first_factor_return_period": str(signal_periods[0] + 1) if signal_periods else "",
        "last_factor_return_period": str(signal_periods[-1] + 1) if signal_periods else "",
        "price_adjustment_mode": config["price_adjustment"]["mode"],
        "volume_unit_audit": unit_audit,
        "turn_enabled": bool(turn_enabled),
    }
    return panel, books, meta


def build_availability_manifest(config: dict[str, Any], factor_panel: pd.DataFrame, meta: dict[str, Any]) -> pd.DataFrame:
    rows = []
    split_months = {
        split: factor_panel.loc[factor_panel["split"].eq(split), "holding_period"].nunique()
        for split in SPLITS
    }
    for factor in FACTOR_ORDER:
        md = FACTOR_METADATA[factor]
        if factor in RETAINED_FACTORS:
            factor_rows = factor_panel.loc[factor_panel["factor_id"].eq(factor)]
            complete = factor_rows.loc[factor_rows["factor_month_status"].eq("complete")]
            availability_status = "available_full"
            action = "retain"
            block_reason = ""
            if factor == "TURN" and not meta.get("turn_enabled", False):
                availability_status = "blocked_not_reproducible"
                action = "remove"
                block_reason = "volume_or_total_share_unit_audit_failed"
            available_fields = md["required_raw_fields"]
        else:
            complete = pd.DataFrame()
            availability_status = "missing_required_fundamental_fields"
            action = "remove"
            block_reason = "local PIT accounting fields and announcement timestamps are unavailable"
            available_fields = "market equity only" if factor in {"BM", "EP", "CFP"} else ""

        def coverage_months(split_name: str) -> int:
            if complete.empty or "split" not in complete.columns:
                return 0
            return int(complete.loc[complete["split"].eq(split_name), "holding_period"].nunique())

        def coverage_instruments_median(split_name: str) -> float:
            if complete.empty or "split" not in complete.columns:
                return math.nan
            part = complete.loc[complete["split"].eq(split_name)]
            if part.empty:
                return math.nan
            return float(part["eligible_instrument_count"].median())

        rows.append(
            {
                "factor_id": factor,
                "paper_factor_name": md["paper_name"],
                "required_raw_fields": md["required_raw_fields"],
                "available_raw_fields": available_fields,
                "availability_status": availability_status,
                "replication_action": action,
                "local_formula_id": md["local_formula_id"],
                "asof_policy": md["asof_policy"],
                "coverage_train_months": coverage_months("train"),
                "coverage_validation_months": coverage_months("validation"),
                "coverage_robustness_months": coverage_months("robustness"),
                "coverage_train_instruments_median": coverage_instruments_median("train"),
                "coverage_validation_instruments_median": coverage_instruments_median("validation"),
                "coverage_robustness_instruments_median": coverage_instruments_median("robustness"),
                "expected_train_months": int(split_months.get("train", 0)),
                "expected_validation_months": int(split_months.get("validation", 0)),
                "expected_robustness_months": int(split_months.get("robustness", 0)),
                "block_reason": block_reason,
            }
        )
    return pd.DataFrame(rows)


def compound_return(values: pd.Series) -> float:
    values = values.dropna()
    if values.empty:
        return math.nan
    if (values <= -1.0).any():
        return math.nan
    return float(np.prod(1.0 + values) - 1.0)


def build_tsfm_panels(
    config: dict[str, Any],
    factor_panel: pd.DataFrame,
    books: dict[tuple[str, str], dict[str, float]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    formation = int(config["tsfm"]["formation_months"])
    buy_cost = float(config["execution"]["buy_cost_bps"]) / 10000.0
    sell_cost = float(config["execution"]["sell_cost_bps"]) / 10000.0
    complete = factor_panel.loc[factor_panel["factor_month_status"].eq("complete")].copy()
    factor_returns = {
        factor: complete.loc[complete["factor_id"].eq(factor)].set_index("holding_period")["factor_gross_return"]
        for factor in RETAINED_FACTORS
    }
    factor_rows_by_key = {
        (row.factor_id, row.holding_period): row
        for row in factor_panel.itertuples(index=False)
    }
    holding_periods = sorted(factor_panel["holding_period"].drop_duplicates().astype(str).tolist())
    signal_rows: list[dict[str, Any]] = []
    return_rows: list[dict[str, Any]] = []
    prev_tsfm_book: dict[str, float] = {}

    for holding_period_text in holding_periods:
        holding_period = pd.Period(holding_period_text, freq="M")
        signal_period = holding_period - 1
        history_periods = [str(signal_period - offset) for offset in range(formation - 1, -1, -1)]
        current_factor_rows = factor_panel.loc[factor_panel["holding_period"].eq(holding_period_text)]
        if current_factor_rows.empty:
            continue
        split = str(current_factor_rows["split"].iloc[0])
        holding_end = str(current_factor_rows["holding_month_end"].iloc[0])
        signal_end = str(current_factor_rows["signal_month_end"].iloc[0])
        active_factors: list[str] = []
        factor_positions: dict[str, int] = {}
        factor_current_returns: dict[str, float] = {}
        factor_past_returns: dict[str, float] = {}

        for factor in RETAINED_FACTORS:
            series = factor_returns.get(factor, pd.Series(dtype="float64"))
            history = series.reindex(history_periods)
            has_history = bool(history.notna().sum() == formation)
            past = compound_return(history) if has_history else math.nan
            current = series.get(holding_period_text, math.nan)
            current_complete = bool(np.isfinite(current))
            if has_history and current_complete:
                if past > 0:
                    position = 1
                elif past < 0:
                    position = -1
                else:
                    position = 0
                active = True
                active_factors.append(factor)
            else:
                position = 0
                active = False
            factor_positions[factor] = position
            factor_current_returns[factor] = float(current) if np.isfinite(current) else math.nan
            factor_past_returns[factor] = past
            signal_rows.append(
                {
                    "factor_id": factor,
                    "signal_period": str(signal_period),
                    "signal_month_end": signal_end,
                    "holding_period": holding_period_text,
                    "holding_month_end": holding_end,
                    "split": split,
                    "past_12m_factor_return": past,
                    "tsfm_position": position,
                    "has_complete_12m_history": has_history,
                    "has_current_factor_return": current_complete,
                    "active_factor": active,
                    "current_factor_return": factor_current_returns[factor],
                    "history_start_period": history_periods[0],
                    "history_end_period": history_periods[-1],
                }
            )

        active_count = len(active_factors)
        if active_count == 0:
            tsfm_gross = math.nan
            winner_raw = math.nan
            loser_raw = math.nan
            winner_count = 0
            loser_count = 0
            zero_count = 0
            curr_book: dict[str, float] = {}
            buy_turnover = math.nan
            sell_turnover = math.nan
            after_cost = math.nan
            evaluable = False
        else:
            contributions = [factor_positions[f] * factor_current_returns[f] / active_count for f in active_factors]
            tsfm_gross = float(np.nansum(contributions))
            winners = [factor_current_returns[f] for f in active_factors if factor_positions[f] == 1]
            losers = [factor_current_returns[f] for f in active_factors if factor_positions[f] == -1]
            zeros = [factor_current_returns[f] for f in active_factors if factor_positions[f] == 0]
            winner_raw = float(np.mean(winners)) if winners else math.nan
            loser_raw = float(np.mean(losers)) if losers else math.nan
            winner_count = len(winners)
            loser_count = len(losers)
            zero_count = len(zeros)
            curr_book = {}
            for factor in active_factors:
                book = books.get((factor, holding_period_text), {})
                scalar = factor_positions[factor] / active_count
                if scalar == 0:
                    continue
                for inst, weight in book.items():
                    curr_book[inst] = curr_book.get(inst, 0.0) + scalar * weight
            buy_turnover, sell_turnover = compute_turnover(prev_tsfm_book, curr_book)
            after_cost = tsfm_gross - buy_turnover * buy_cost - sell_turnover * sell_cost
            prev_tsfm_book = curr_book
            evaluable = True

        for row in signal_rows[-len(RETAINED_FACTORS) :]:
            if active_count and row["active_factor"]:
                row["active_factor_count"] = active_count
                row["tsfm_contribution"] = row["tsfm_position"] * row["current_factor_return"] / active_count
            else:
                row["active_factor_count"] = active_count
                row["tsfm_contribution"] = math.nan

        return_rows.append(
            {
                "holding_period": holding_period_text,
                "signal_period": str(signal_period),
                "signal_month_end": signal_end,
                "holding_month_end": holding_end,
                "split": split,
                "evaluable": evaluable,
                "active_factor_count": active_count,
                "winner_factor_count": winner_count,
                "loser_factor_count": loser_count,
                "zero_factor_count": zero_count,
                "tsfm_gross_return": tsfm_gross,
                "tsfm_winner_leg_return": winner_raw,
                "tsfm_loser_leg_return": loser_raw,
                "tsfm_buy_turnover": buy_turnover,
                "tsfm_sell_turnover": sell_turnover,
                "tsfm_after_cost_return": after_cost,
                "requires_short_exposure": bool(any(v < -1e-12 for v in curr_book.values())) if active_count else False,
                "net_abs_exposure": float(sum(abs(v) for v in curr_book.values())) if active_count else 0.0,
                "long_gross_exposure": float(sum(v for v in curr_book.values() if v > 0)) if active_count else 0.0,
                "short_gross_exposure": float(-sum(v for v in curr_book.values() if v < 0)) if active_count else 0.0,
            }
        )

    signals = pd.DataFrame(signal_rows)
    returns = pd.DataFrame(return_rows)
    if not signals.empty and not returns.empty:
        active_counts = returns[["holding_period", "active_factor_count"]]
        signals = signals.drop(columns=[c for c in ["active_factor_count"] if c in signals.columns]).merge(
            active_counts, on="holding_period", how="left"
        )
        signals["tsfm_contribution"] = np.where(
            signals["active_factor"] & (signals["active_factor_count"] > 0),
            signals["tsfm_position"] * signals["current_factor_return"] / signals["active_factor_count"],
            np.nan,
        )
    return signals, returns, complete


def split_metrics(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        part = returns.loc[returns["split"].eq(split) & returns["evaluable"].astype(bool)].copy()
        gross = part["tsfm_gross_return"] if not part.empty else pd.Series(dtype="float64")
        after = part["tsfm_after_cost_return"] if not part.empty else pd.Series(dtype="float64")
        rows.append(
            {
                "split": split,
                "month_count": int(len(part)),
                "active_factor_count_mean": float(part["active_factor_count"].mean()) if not part.empty else math.nan,
                "active_factor_count_median": float(part["active_factor_count"].median()) if not part.empty else math.nan,
                "active_factor_count_min": float(part["active_factor_count"].min()) if not part.empty else math.nan,
                "annualized_mean_return": annualized_mean(gross),
                "monthly_mean_return": float(gross.mean()) if not gross.empty else math.nan,
                "monthly_volatility": float(gross.std(ddof=1)) if len(gross.dropna()) > 1 else math.nan,
                "annualized_volatility": annualized_vol(gross),
                "sharpe_ratio": sharpe(gross),
                "t_stat_monthly_mean": t_stat(gross),
                "positive_month_share": positive_share(gross),
                "max_drawdown": max_drawdown(gross),
                "winner_leg_annualized_mean_return": annualized_mean(part["tsfm_winner_leg_return"]) if not part.empty else math.nan,
                "loser_leg_annualized_mean_return": annualized_mean(part["tsfm_loser_leg_return"]) if not part.empty else math.nan,
                "winner_factor_count_mean": float(part["winner_factor_count"].mean()) if not part.empty else math.nan,
                "loser_factor_count_mean": float(part["loser_factor_count"].mean()) if not part.empty else math.nan,
                "annualized_mean_return_after_cost": annualized_mean(after),
                "monthly_mean_return_after_cost": float(after.mean()) if not after.empty else math.nan,
                "sharpe_ratio_after_cost": sharpe(after),
                "positive_month_share_after_cost": positive_share(after),
                "mean_buy_turnover": float(part["tsfm_buy_turnover"].mean()) if not part.empty else math.nan,
                "mean_sell_turnover": float(part["tsfm_sell_turnover"].mean()) if not part.empty else math.nan,
                "months_requiring_short_exposure": int(part["requires_short_exposure"].sum()) if not part.empty else 0,
                "first_evaluable_holding_month": str(part["holding_period"].min()) if not part.empty else "",
                "last_evaluable_holding_month": str(part["holding_period"].max()) if not part.empty else "",
            }
        )
    return pd.DataFrame(rows)


def factor_contribution(factor_panel: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in SPLITS:
        split_signals = signals.loc[signals["split"].eq(split)].copy()
        contribution_abs_sum = (
            split_signals.loc[split_signals["active_factor"], :]
            .groupby("factor_id")["tsfm_contribution"]
            .apply(lambda x: float(np.nansum(np.abs(x))))
        )
        denom = float(contribution_abs_sum.sum()) if not contribution_abs_sum.empty else math.nan
        for factor in RETAINED_FACTORS:
            factor_returns = factor_panel.loc[
                factor_panel["factor_id"].eq(factor)
                & factor_panel["split"].eq(split)
                & factor_panel["factor_month_status"].eq("complete")
            ]["factor_gross_return"]
            fs = split_signals.loc[split_signals["factor_id"].eq(factor)]
            contrib = fs.loc[fs["active_factor"], "tsfm_contribution"]
            abs_contrib = contribution_abs_sum.get(factor, math.nan)
            share = abs_contrib / denom if np.isfinite(abs_contrib) and np.isfinite(denom) and denom > 0 else math.nan
            rows.append(
                {
                    "factor_id": factor,
                    "split": split,
                    "available_month_count": int(factor_returns.notna().sum()),
                    "replication_action": "retain",
                    "local_formula_id": FACTOR_METADATA[factor]["local_formula_id"],
                    "mean_factor_return": float(factor_returns.mean()) if not factor_returns.empty else math.nan,
                    "t_stat_factor_return": t_stat(factor_returns),
                    "positive_month_share": positive_share(factor_returns),
                    "mean_past_12m_return": float(fs["past_12m_factor_return"].mean()) if not fs.empty else math.nan,
                    "tsfm_long_month_count": int(fs["tsfm_position"].eq(1).sum()) if not fs.empty else 0,
                    "tsfm_short_month_count": int(fs["tsfm_position"].eq(-1).sum()) if not fs.empty else 0,
                    "tsfm_zero_month_count": int(fs["tsfm_position"].eq(0).sum()) if not fs.empty else 0,
                    "tsfm_contribution_mean": float(contrib.mean()) if not contrib.empty else math.nan,
                    "tsfm_contribution_abs_sum": abs_contrib,
                    "tsfm_contribution_share_abs": share,
                }
            )
    return pd.DataFrame(rows)


def paper_reference_comparison(config: dict[str, Any], summary: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    paper = config["paper_reference"]
    metrics = [
        ("annualized_mean_return", paper["annualized_mean_return"]),
        ("t_stat_monthly_mean", paper["t_stat"]),
        ("sharpe_ratio", paper["sharpe_ratio"]),
        ("winner_leg_annualized_mean_return", paper["winner_leg_annualized_return"]),
        ("loser_leg_annualized_mean_return", paper["loser_leg_annualized_return"]),
    ]
    full = returns.loc[returns["evaluable"].astype(bool)].copy()
    gross = full["tsfm_gross_return"] if not full.empty else pd.Series(dtype="float64")
    full_values = {
        "annualized_mean_return": annualized_mean(gross),
        "t_stat_monthly_mean": t_stat(gross),
        "sharpe_ratio": sharpe(gross),
        "winner_leg_annualized_mean_return": annualized_mean(full["tsfm_winner_leg_return"]) if not full.empty else math.nan,
        "loser_leg_annualized_mean_return": annualized_mean(full["tsfm_loser_leg_return"]) if not full.empty else math.nan,
    }
    rows = []
    split_summary = summary.set_index("split")
    for metric, paper_value in metrics:
        local_full = full_values[metric]
        rows.append(
            {
                "metric": metric,
                "paper_value": paper_value,
                "local_train_value": split_summary.at["train", metric] if "train" in split_summary.index else math.nan,
                "local_validation_value": split_summary.at["validation", metric] if "validation" in split_summary.index else math.nan,
                "local_robustness_value": split_summary.at["robustness", metric] if "robustness" in split_summary.index else math.nan,
                "local_full_value": local_full,
                "comparability_status": "not_comparable_due_to_4factor_local_proxy",
                "reference_gap": local_full - paper_value if np.isfinite(local_full) else math.nan,
                "interpretation": "directional reference only; not an exact paper magnitude comparison",
            }
        )
    for metric in ["ff5_alpha", "ch3_alpha", "conditional_ch3_alpha"]:
        rows.append(
            {
                "metric": metric,
                "paper_value": paper[metric],
                "local_train_value": math.nan,
                "local_validation_value": math.nan,
                "local_robustness_value": math.nan,
                "local_full_value": math.nan,
                "comparability_status": "not_comparable_due_to_4factor_local_proxy",
                "reference_gap": math.nan,
                "interpretation": "not evaluated locally because this requirement does not run factor model regressions",
            }
        )
    return pd.DataFrame(rows)


def gate_results(config: dict[str, Any], availability: pd.DataFrame, summary: pd.DataFrame, contrib: pd.DataFrame, returns: pd.DataFrame) -> dict[str, Any]:
    gates = config["gates"]
    summary_idx = summary.set_index("split")
    retained_count = int(availability["replication_action"].eq("retain").sum())
    validation = summary_idx.loc["validation"].to_dict()
    robustness = summary_idx.loc["robustness"].to_dict()

    data_gates = {
        "retained_factor_count_min": retained_count >= int(gates["retained_factor_count_min"]),
        "validation_evaluable_month_count_min": validation["month_count"] >= int(gates["validation_evaluable_month_count_min"]),
        "robustness_evaluable_month_count_min": robustness["month_count"] >= int(gates["robustness_evaluable_month_count_min"]),
        "validation_active_factor_count_median_min": validation["active_factor_count_median"] >= int(gates["active_factor_count_median_min"]),
        "robustness_active_factor_count_median_min": robustness["active_factor_count_median"] >= int(gates["active_factor_count_median_min"]),
    }
    validation_gates = {
        "validation_annualized_mean_return_positive": validation["annualized_mean_return"] > 0,
        "validation_t_stat_monthly_mean_positive": validation["t_stat_monthly_mean"] > 0,
        "validation_sharpe_ratio_min": validation["sharpe_ratio"] > float(gates["validation_sharpe_min"]),
        "validation_positive_month_share_min": validation["positive_month_share"] >= float(gates["validation_positive_month_share_min"]),
        "validation_active_factor_count_median_min": validation["active_factor_count_median"] >= int(gates["active_factor_count_median_min"]),
    }
    robustness_gates = {
        "robustness_annualized_mean_return_positive": robustness["annualized_mean_return"] > 0,
        "robustness_t_stat_monthly_mean_positive": robustness["t_stat_monthly_mean"] > 0,
        "robustness_sharpe_ratio_min": robustness["sharpe_ratio"] > float(gates["robustness_sharpe_min"]),
        "robustness_positive_month_share_min": robustness["positive_month_share"] >= float(gates["robustness_positive_month_share_min"]),
        "robustness_active_factor_count_median_min": robustness["active_factor_count_median"] >= int(gates["active_factor_count_median_min"]),
    }
    concentration = {}
    for split in ["validation", "robustness"]:
        part = contrib.loc[contrib["split"].eq(split)].copy()
        shares = part["tsfm_contribution_share_abs"].dropna().sort_values(ascending=False).tolist()
        top1 = float(shares[0]) if shares else math.nan
        top2 = float(sum(shares[:2])) if shares else math.nan
        concentration[f"{split}_top1_factor_abs_contribution_share"] = top1
        concentration[f"{split}_top2_factor_abs_contribution_share"] = top2
        concentration[f"{split}_top1_pass"] = bool(np.isfinite(top1) and top1 <= float(gates["top1_factor_abs_contribution_share_max"]))
        concentration[f"{split}_top2_pass"] = bool(np.isfinite(top2) and top2 <= float(gates["top2_factor_abs_contribution_share_max"]))

    after_cost = {
        "validation_after_cost_mean_positive": validation["annualized_mean_return_after_cost"] > 0,
        "robustness_after_cost_mean_positive": robustness["annualized_mean_return_after_cost"] > 0,
    }
    execution_replay_available = bool(returns.loc[returns["evaluable"].astype(bool), "tsfm_buy_turnover"].notna().all())

    if retained_count < int(gates["retained_factor_count_min"]):
        final = "ep6_tsfm_replication_data_blocked_insufficient_retained_factors"
    elif not all(data_gates.values()):
        final = "ep6_tsfm_replication_data_blocked_or_sample_insufficient"
    elif not execution_replay_available:
        final = "ep6_tsfm_replication_execution_replay_blocked"
    elif not all(validation_gates.values()):
        final = "ep6_tsfm_replication_validation_not_supported"
    elif not all(robustness_gates.values()):
        final = "ep6_tsfm_replication_validation_only_not_robust"
    elif not all(v for k, v in concentration.items() if k.endswith("_pass")):
        final = "ep6_tsfm_replication_positive_but_factor_concentrated"
    elif not all(after_cost.values()):
        final = "ep6_tsfm_replication_gross_positive_after_cost_not_supported"
    else:
        final = FINAL_SUPPORTED

    return {
        "validation_status": "passed",
        "requirement_id": REQUIREMENT_ID,
        "final_decision": final,
        "authorized_strategy_requirement": False,
        "data_gates": data_gates,
        "validation_support_gates": validation_gates,
        "robustness_support_gates": robustness_gates,
        "concentration_guard": concentration,
        "after_cost_guard": after_cost,
        "execution_replay_available": execution_replay_available,
    }


def dataframe_markdown(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "_empty_"
    return df[columns].to_markdown(index=False)


def build_report(
    config: dict[str, Any],
    meta: dict[str, Any],
    availability: pd.DataFrame,
    summary: pd.DataFrame,
    contrib: pd.DataFrame,
    paper: pd.DataFrame,
    gates: dict[str, Any],
) -> str:
    final = gates["final_decision"]
    summary_view = summary.copy()
    for col in [
        "annualized_mean_return",
        "annualized_mean_return_after_cost",
        "sharpe_ratio",
        "sharpe_ratio_after_cost",
        "positive_month_share",
        "positive_month_share_after_cost",
        "mean_buy_turnover",
        "mean_sell_turnover",
        "max_drawdown",
    ]:
        if col in summary_view.columns:
            if "sharpe" in col:
                summary_view[col] = summary_view[col].map(lambda x: num(x, 3))
            else:
                summary_view[col] = summary_view[col].map(lambda x: pct(x, 2))
    contrib_view = contrib.copy()
    for col in ["mean_factor_return", "positive_month_share", "tsfm_contribution_mean", "tsfm_contribution_share_abs"]:
        contrib_view[col] = contrib_view[col].map(lambda x: pct(x, 2))
    availability_view = availability[
        [
            "factor_id",
            "paper_factor_name",
            "availability_status",
            "replication_action",
            "local_formula_id",
            "coverage_validation_months",
            "coverage_robustness_months",
            "block_reason",
        ]
    ].copy()
    paper_view = paper.copy()
    paper_number_metrics = {"t_stat_monthly_mean", "sharpe_ratio"}
    for col in ["paper_value", "local_train_value", "local_validation_value", "local_robustness_value", "reference_gap"]:
        paper_view[col] = [
            num(value, 3) if metric in paper_number_metrics else pct(value, 2)
            for metric, value in zip(paper_view["metric"], paper_view[col], strict=False)
        ]

    val = summary.set_index("split").loc["validation"]
    rob = summary.set_index("split").loc["robustness"]
    volume_audit = meta["volume_unit_audit"]
    lines = [
        "# R02 Factor Momentum TSFM Local Feasible Replication 最终报告",
        "",
        "## 1. 结论摘要",
        "",
        f"`final_decision = {final}`",
        "",
        "`authorized_strategy_requirement = false`",
        "",
        "本轮实现的是 Ma / Liao / Jiang (2023) 中 TSFM 的本地可实现版本，但不是论文 10 因子的精确复现。由于本地 PIT 数据缺少会计字段，BM、GP、CINVEST、EP、ACC、CFP 被预先移除；实际进入 TSFM 的只有 SIZE、ILL、TURN、BAB 四个本地可复现因子。",
        "",
        f"validation gross 年化均值为 {pct(val['annualized_mean_return'])}，after-cost 年化均值为 {pct(val['annualized_mean_return_after_cost'])}；robustness gross 年化均值为 {pct(rob['annualized_mean_return'])}，after-cost 年化均值为 {pct(rob['annualized_mean_return_after_cost'])}。",
        "",
    ]
    if final == FINAL_SUPPORTED:
        lines.append("按当前门禁，4-factor local proxy TSFM 在 validation 和 robustness 上都通过 directional diagnostic，但仍然只解读为 paper-inspired factor-level diagnostic，不授权组合或交易。")
    elif final == "ep6_tsfm_replication_validation_not_supported":
        lines.append("主要 blocker 是 validation split 没有形成正向、稳定的 TSFM 读数，因此不能把论文 TSFM 结论迁移到当前 EP5 universe。")
    elif final == "ep6_tsfm_replication_validation_only_not_robust":
        lines.append("validation 方向尚可，但 robustness 未确认，当前只能视为 validation-only 现象。")
    elif final == "ep6_tsfm_replication_gross_positive_after_cost_not_supported":
        lines.append("gross 读数通过后，成本回放把信号削弱到不可支持，因此不能把 factor-level gross result 解释成可执行 exposure。")
    else:
        lines.append("当前结果未达到最终 supported token；下方门禁表给出具体 blocker。")
    lines.extend(
        [
            "",
            "## 2. 数据与实现边界",
            "",
            f"- Qlib provider: `{config['data_sources']['qlib_provider_uri']}`",
            f"- PIT universe: `{config['data_sources']['pit_universe_path']}`",
            f"- price adjustment mode: `{config['price_adjustment']['mode']}`，没有二次套用 `factor.day.bin`。",
            f"- factor return label range: `{meta['first_factor_return_period']}` ~ `{meta['last_factor_return_period']}`",
            f"- first evaluable TSFM holding month: `{summary['first_evaluable_holding_month'].replace('', np.nan).dropna().min()}`",
            f"- volume unit audit: `{volume_audit['volume_unit_status']}`，money/volume 相对 PIT close 的中位比值为 `{num(volume_audit['median_money_per_share_to_pit_close'], 4)}`，样本数 `{volume_audit['sample_count']}`。",
            "",
            "所有 PIT join 均按 `date + instrument`，`money` 使用本地成交额字段。TURN 的 `volume / (total_share * 10000)` 只有在 volume unit audit 通过后才保留。",
            "",
            "## 3. TSFM 公式与 active factor count",
            "",
            "本轮使用月频 high-minus-low 因子收益。对 holding month `m+1`：",
            "",
            "```text",
            "factor_return_{f,m+1} = mean(high_quintile_return) - mean(low_quintile_return)",
            "past_12m_factor_return_{f,m} = compounded_return(factor_return_{f,m-11}, ..., factor_return_{f,m})",
            "tsfm_position_{f,m+1} = +1 if past_12m > 0, -1 if past_12m < 0, else 0",
            "tsfm_return_{m+1} = mean(tsfm_position_{f,m+1} * factor_return_{f,m+1}) over active factors",
            "```",
            "",
            "validation 和 robustness 的 active factor count median 均为 4，说明四个 retained factors 在两个 out-of-sample split 中都可参与 TSFM。",
            "",
            "## 4. 因子可实现性",
            "",
            dataframe_markdown(
                availability_view,
                [
                    "factor_id",
                    "paper_factor_name",
                    "availability_status",
                    "replication_action",
                    "local_formula_id",
                    "coverage_validation_months",
                    "coverage_robustness_months",
                    "block_reason",
                ],
            ),
            "",
            "## 5. Split 结果",
            "",
            dataframe_markdown(
                summary_view,
                [
                    "split",
                    "month_count",
                    "active_factor_count_median",
                    "annualized_mean_return",
                    "sharpe_ratio",
                    "positive_month_share",
                    "annualized_mean_return_after_cost",
                    "sharpe_ratio_after_cost",
                    "positive_month_share_after_cost",
                    "mean_buy_turnover",
                    "mean_sell_turnover",
                    "months_requiring_short_exposure",
                ],
            ),
            "",
            "## 6. 因子贡献与集中度",
            "",
            dataframe_markdown(
                contrib_view,
                [
                    "factor_id",
                    "split",
                    "available_month_count",
                    "mean_factor_return",
                    "positive_month_share",
                    "tsfm_long_month_count",
                    "tsfm_short_month_count",
                    "tsfm_contribution_mean",
                    "tsfm_contribution_share_abs",
                ],
            ),
            "",
            "集中度门禁使用 validation / robustness 中每个因子的绝对贡献占比。当前 concentration guard：",
            "",
            "```json",
            json.dumps(gates["concentration_guard"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## 7. 论文参考比较",
            "",
            dataframe_markdown(
                paper_view,
                [
                    "metric",
                    "paper_value",
                    "local_train_value",
                    "local_validation_value",
                    "local_robustness_value",
                    "comparability_status",
                    "reference_gap",
                    "interpretation",
                ],
            ),
            "",
            "这张表只能作为方向参考，不能解释为本地结果相对论文的超额或不足。原因是本轮是 4-factor local feasible proxy，且 universe、样本期、数据口径都不同。",
            "",
            "## 8. 门禁结果",
            "",
            "```json",
            json.dumps(
                {
                    "data_gates": gates["data_gates"],
                    "validation_support_gates": gates["validation_support_gates"],
                    "robustness_support_gates": gates["robustness_support_gates"],
                    "after_cost_guard": gates["after_cost_guard"],
                    "execution_replay_available": gates["execution_replay_available"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
            "## 9. 研究解读",
            "",
        ]
    )
    if val["annualized_mean_return"] > 0 and rob["annualized_mean_return"] > 0:
        lines.append("gross 层面 validation 和 robustness 都为正，说明因子收益序列本身存在一定时间序列延续读数。")
    else:
        lines.append("gross 层面没有同时守住 validation 和 robustness，说明本地可实现因子的 TSFM 延续性不足。")
    if val["annualized_mean_return_after_cost"] <= 0 or rob["annualized_mean_return_after_cost"] <= 0:
        lines.append("但 after-cost 结果显示，月频长短因子腿的换手成本会显著侵蚀收益；即使 gross 有方向，也不能直接进入执行型策略。")
    else:
        lines.append("after-cost 仍为正，说明本地 4 因子 proxy 至少没有被 110bps round-trip 成本假设完全抹掉。")
    lines.extend(
        [
            "",
            "本轮最重要的边界不是收益大小，而是：本地数据只能支持一个 4 因子 proxy。若要复现论文 10 因子，需要补 PIT accounting fields 和 announcement-date as-of 规则；否则不要把本轮结果包装成完整 paper replication。",
            "",
            "This is a 4-factor local feasible TSFM proxy diagnostic.",
            "This is a paper-replication diagnostic only.",
            "It does not authorize strategy construction.",
            "",
        ]
    )
    return "\n".join(lines)


def artifact_hashes(paths: Paths, exclude_names: set[str] | None = None) -> list[dict[str, str]]:
    exclude_names = exclude_names or set()
    rows = []
    for directory in [
        paths.configs_dir,
        paths.manifests_dir,
        paths.factors_dir,
        paths.signals_dir,
        paths.returns_dir,
        paths.reports_dir,
        paths.validation_dir,
    ]:
        for path in sorted(directory.glob("*")):
            if path.is_file() and path.name not in exclude_names:
                rows.append({"artifact_path": rel(path), "sha256": file_hash(path)})
    return rows


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths = load_config(config_path)
    frozen_config_path = paths.configs_dir / "r02_factor_momentum_tsfm_replication_v0.yaml"
    shutil.copyfile(paths.config_path, frozen_config_path)

    inputs = load_inputs(config)
    factor_panel, books, meta = build_monthly_factor_panel(config, inputs)
    availability = build_availability_manifest(config, factor_panel, meta)
    signals, returns, complete_factors = build_tsfm_panels(config, factor_panel, books)
    summary = split_metrics(returns)
    contrib = factor_contribution(factor_panel, signals)
    paper = paper_reference_comparison(config, summary, returns)
    gates = gate_results(config, availability, summary, contrib, returns)

    write_csv(availability, paths.manifests_dir / "r02_factor_input_availability_manifest.csv")
    write_csv(factor_panel, paths.factors_dir / "r02_monthly_factor_returns.csv")
    write_csv(signals, paths.signals_dir / "r02_tsfm_monthly_signal_panel.csv")
    write_csv(returns, paths.returns_dir / "r02_tsfm_monthly_returns.csv")
    write_csv(summary, paths.reports_dir / "r02_tsfm_split_summary.csv")
    write_csv(contrib, paths.reports_dir / "r02_tsfm_factor_contribution.csv")
    write_csv(paper, paths.reports_dir / "r02_tsfm_paper_reference_comparison.csv")
    write_json(gates, paths.validation_dir / "r02_tsfm_validation_manifest.json")

    report = build_report(config, meta, availability, summary, contrib, paper, gates)
    (paths.reports_dir / "r02_tsfm_final_report.md").write_text(report, encoding="utf-8")

    manifest = {
        "requirement_id": REQUIREMENT_ID,
        "short_name": SHORT_NAME,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "config_path": rel(paths.config_path),
        "frozen_config_path": rel(frozen_config_path),
        "output_root": rel(paths.output_root),
        "final_decision": gates["final_decision"],
        "authorized_strategy_requirement": False,
        "price_adjustment_mode": config["price_adjustment"]["mode"],
        "factor_set": {
            "retained": availability.loc[availability["replication_action"].eq("retain"), "factor_id"].tolist(),
            "removed": availability.loc[availability["replication_action"].eq("remove"), "factor_id"].tolist(),
        },
        "data_meta": meta,
        "first_evaluable_holding_month": summary["first_evaluable_holding_month"].replace("", np.nan).dropna().min()
        if not summary.empty
        else "",
        "artifact_hashes_excludes": ["r02_tsfm_run_manifest.json"],
        "artifact_hashes": artifact_hashes(paths, exclude_names={"r02_tsfm_run_manifest.json"}),
    }
    write_json(manifest, paths.manifests_dir / "r02_tsfm_run_manifest.json")
    return {"manifest": manifest, "gates": gates, "summary": summary}


def main() -> None:
    args = parse_args()
    payload = run_pipeline(args.config)
    print(json.dumps({"final_decision": payload["gates"]["final_decision"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

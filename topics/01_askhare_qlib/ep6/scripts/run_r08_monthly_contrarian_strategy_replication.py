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
DEFAULT_CONFIG = EP6_DIR / "configs" / "r08_monthly_contrarian_strategy_replication_v0.yaml"
SPLITS = ["train", "validation", "robustness"]


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    configs_dir: Path
    manifests_dir: Path
    validation_dir: Path
    calendar_dir: Path
    signals_dir: Path
    returns_dir: Path
    reports_dir: Path


@dataclass(frozen=True)
class VintageSpec:
    vintage_id: str
    grouping: str
    bucket_count: int
    J: int
    K: int
    skip_mode: str
    signal_period: pd.Period
    first_holding_period: pd.Period
    final_holding_period: pd.Period
    split: str
    loser: tuple[str, ...]
    winner: tuple[str, ...]
    signal_eligible_count: int
    status: str
    block_reason: str

    @property
    def family_key(self) -> tuple[str, int, int, str]:
        return (self.grouping, self.J, self.K, self.skip_mode)


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
    parser = argparse.ArgumentParser(description="Run EP6 R08 monthly contrarian strategy replication diagnostic")
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
        validation_dir=output_root / "validation",
        calendar_dir=output_root / "calendar",
        signals_dir=output_root / "signals",
        returns_dir=output_root / "returns",
        reports_dir=output_root / "reports",
    )
    for directory in [
        paths.configs_dir,
        paths.manifests_dir,
        paths.validation_dir,
        paths.calendar_dir,
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
    except Exception as exc:  # noqa: BLE001
        fallback = path.with_suffix(".csv")
        df.to_csv(fallback, index=False)
        return f"csv_fallback:{fallback.name}:{type(exc).__name__}"


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def directory_hash(path: Path) -> str:
    h = hashlib.sha256()
    if not path.exists():
        return ""
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


def month_end_map(calendar: pd.DatetimeIndex) -> pd.Series:
    frame = pd.DataFrame({"date": calendar})
    frame["period"] = frame["date"].dt.to_period("M")
    return frame.groupby("period")["date"].max()


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


def read_qlib_instruments(path: Path) -> list[str]:
    frame = pd.read_csv(path, sep="\t", header=None, names=["instrument", "start", "end"])
    return sorted(frame["instrument"].astype(str).str.upper().unique().tolist())


def split_for_period(period: pd.Period, config: dict[str, Any]) -> str:
    d = period.to_timestamp(how="end").normalize()
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


def stable_hash_value(parts: list[str]) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def near_equal_bucket_labels(n: int, bucket_count: int) -> np.ndarray:
    labels = np.empty(n, dtype=int)
    for bucket, positions in enumerate(np.array_split(np.arange(n), bucket_count)):
        labels[positions] = bucket
    return labels


def newey_west_tstat(values: pd.Series | np.ndarray, lag: int) -> float:
    arr = pd.Series(values).dropna().astype(float).to_numpy()
    n = len(arr)
    if n < 2:
        return np.nan
    mean = float(arr.mean())
    resid = arr - mean
    lag = int(max(0, min(lag, n - 1)))
    gamma0 = float(np.dot(resid, resid) / n)
    var = gamma0
    for l in range(1, lag + 1):
        gamma = float(np.dot(resid[l:], resid[:-l]) / n)
        weight = 1.0 - l / (lag + 1)
        var += 2.0 * weight * gamma
    if var <= 0 or not np.isfinite(var):
        return np.nan
    se = math.sqrt(var / n)
    if se == 0:
        return np.nan
    return mean / se


def max_drawdown(returns: pd.Series | np.ndarray) -> float:
    arr = pd.Series(returns).dropna().astype(float)
    if arr.empty:
        return np.nan
    curve = (1.0 + arr).cumprod()
    peak = curve.cummax()
    dd = curve / peak - 1.0
    return float(dd.min())


def build_monthly_inputs(
    config: dict[str, Any],
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[pd.Period, set[str]]]:
    ds = config["data_sources"]
    provider_uri = topic_path(ds["qlib_provider_uri"])
    calendar = load_calendar(topic_path(ds["trading_calendar_path"]))
    month_ends = month_end_map(calendar)
    instruments = read_qlib_instruments(topic_path(ds["qlib_instrument_path"]))
    close_daily = load_feature_wide(provider_uri, calendar, instruments, "close")
    volume_daily = load_feature_wide(provider_uri, calendar, instruments, "volume")
    money_daily = load_feature_wide(provider_uri, calendar, instruments, "money")
    monthly_dates = pd.DatetimeIndex(month_ends.values)
    periods = pd.PeriodIndex(month_ends.index, freq="M")
    close_m = close_daily.reindex(monthly_dates)
    volume_m = volume_daily.reindex(monthly_dates)
    money_m = money_daily.reindex(monthly_dates)
    close_m.index = periods
    volume_m.index = periods
    money_m.index = periods
    monthly_ret = close_m.div(close_m.shift(1)).sub(1.0)
    pit = pd.read_csv(topic_path(ds["pit_universe_path"]), low_memory=False)
    pit["date"] = pd.to_datetime(pit["date"]).dt.normalize()
    pit["instrument"] = pit["instrument"].astype(str).str.upper()
    pit["period"] = pit["date"].dt.to_period("M")
    period_end_dates = pit.groupby("period")["date"].max()
    members_by_period: dict[pd.Period, set[str]] = {}
    pit_month_end_rows = []
    for period, date in period_end_dates.items():
        rows = pit.loc[pit["date"].eq(date)].copy()
        members_by_period[pd.Period(period, freq="M")] = set(rows["instrument"].unique())
        pit_month_end_rows.append(rows)
    pit_month_end = pd.concat(pit_month_end_rows, ignore_index=True) if pit_month_end_rows else pd.DataFrame()
    inst_map = pd.read_csv(topic_path(ds["pit_qlib_instrument_universe_path"]))
    inst_map["instrument"] = inst_map["instrument"].astype(str).str.upper()
    return month_ends, close_m, volume_m, money_m, monthly_ret, pit, pit_month_end, inst_map, members_by_period


def build_calendar_artifact(month_ends: pd.Series, members_by_period: dict[pd.Period, set[str]]) -> pd.DataFrame:
    rows = []
    prev = None
    for period, date in month_ends.items():
        p = pd.Period(period, freq="M")
        rows.append(
            {
                "calendar_month_id": str(p),
                "month_end": pd.Timestamp(date).date().isoformat(),
                "previous_month_end": pd.Timestamp(prev).date().isoformat() if prev is not None else "",
                "pit_member_count": len(members_by_period.get(p, set())),
            }
        )
        prev = date
    return pd.DataFrame(rows)


def availability_manifest() -> pd.DataFrame:
    rows = [
        ("monthly_adjusted_stock_returns", "monthly adjusted stock returns", "data/qlib/cn_data_pit/features/*/close.day.bin", "available_full", "retain_local_proxy", "provider_adjusted_close_return", "provider close as-of month end", ""),
        ("exchange_split", "SHSE/SZSE exchange split", "data/universe/pit_qlib_instrument_universe.csv.exchange", "available_full", "retain_local_proxy", "SH_SZ_to_SHSE_SZSE_mapping", "static instrument map", ""),
        ("full_all_a_share_universe", "full all-A-share universe", "not available locally", "blocked_not_reproducible", "remove", "", "not local PIT universe", "local PIT mcap500 mainboard universe is mandatory"),
        ("ipo_first_month_exclusion", "IPO first-month exclusion", "data/universe/pit_mcap500_mainboard_daily.csv.listing_age_trading_days", "available_partial", "retain_local_proxy", "listing_age_min_120_audit", "PIT membership as-of signal date", "local universe already filters listing_age_trading_days >= 120; not paper-equivalent raw IPO deletion"),
        ("market_state", "market state", "data/qlib/cn_data_pit/features/sh000300/close.day.bin", "available_full", "retain_local_proxy", "SH000300_prior_return_state", "prior month-end index close", ""),
        ("one_month_skip", "one-month skip robustness", "monthly close panel", "available_full", "retain", "J_equals_K_skip1", "signal month close only", ""),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "input_id",
            "paper_required_input",
            "local_source",
            "availability_status",
            "replication_action",
            "local_proxy_id",
            "asof_policy",
            "block_reason",
        ],
    )


def listing_age_audit(pit: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for split_name in SPLITS:
        start = pd.Timestamp(config["sample_split"][f"{split_name}_start"])
        end = pd.Timestamp(config["sample_split"][f"{split_name}_end"])
        frame = pit.loc[pit["date"].between(start, end)].copy()
        ages = pd.to_numeric(frame.get("listing_age_trading_days"), errors="coerce")
        rows.append(
            {
                "split": split_name,
                "date_min": frame["date"].min().date().isoformat() if not frame.empty else "",
                "date_max": frame["date"].max().date().isoformat() if not frame.empty else "",
                "row_count": int(len(frame)),
                "instrument_count": int(frame["instrument"].nunique()) if not frame.empty else 0,
                "listing_age_min": float(ages.min()) if not ages.dropna().empty else np.nan,
                "listing_age_p01": float(ages.quantile(0.01)) if not ages.dropna().empty else np.nan,
                "listing_age_median": float(ages.median()) if not ages.dropna().empty else np.nan,
                "listing_age_rows_lt_20": int((ages < 20).sum()),
                "listing_age_rows_lt_120": int((ages < 120).sum()),
                "local_ipo_first_month_exclusion_status": "satisfied_by_pit_listing_age_min_120" if int((ages < 120).sum()) == 0 else "listing_age_lt_120_present_requires_review",
            }
        )
    return pd.DataFrame(rows)


def cost_contract_status(config: dict[str, Any]) -> str:
    expected = {
        "buy_cost_bps": config["execution"]["buy_cost_bps"],
        "sell_cost_bps": config["execution"]["sell_cost_bps"],
        "round_trip_cost_bps": config["execution"]["round_trip_cost_bps"],
    }
    statuses = []
    for key in ["ep5_cost_contract_reference", "ep6_cost_contract_reference"]:
        path = topic_path(config["execution"][key])
        if not path.exists():
            statuses.append(f"{key}:missing")
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        execution = loaded.get("execution", {})
        ok = all(execution.get(k) == v for k, v in expected.items())
        statuses.append(f"{key}:{'matched' if ok else 'mismatched'}")
    return "matched" if all(s.endswith(":matched") for s in statuses) else "mismatched_requires_manual_review;" + ";".join(statuses)


def build_vintages(
    config: dict[str, Any],
    month_ends: pd.Series,
    close_m: pd.DataFrame,
    volume_m: pd.DataFrame,
    money_m: pd.DataFrame,
    members_by_period: dict[pd.Period, set[str]],
) -> tuple[list[VintageSpec], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    periods = pd.PeriodIndex(month_ends.index, freq="M")
    period_pos = {p: i for i, p in enumerate(periods)}
    J_values = [int(v) for v in config["signals"]["J_values"]]
    K_values = [int(v) for v in config["signals"]["K_values"]]
    grouping_methods = {k: int(v) for k, v in config["portfolio"]["grouping_methods"].items()}
    tiebreak_seed = str(config["portfolio"]["tiebreak_seed"])
    requirement_id = str(config["requirement_id"])
    min_intermediate_share = float(config["signals"]["min_intermediate_monthly_close_share"])
    min_signal_count = int(config["portfolio"]["signal_eligible_instrument_count_min"])
    rank_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    bucket_rows: list[dict[str, Any]] = []
    vintages: list[VintageSpec] = []

    def leg_min(grouping: str) -> int:
        return int(config["portfolio"][f"{grouping}_leg_assigned_count_min"])

    for t, signal_period in enumerate(periods):
        members = sorted(members_by_period.get(signal_period, set()))
        if not members:
            continue
        signal_close = close_m.loc[signal_period].reindex(members)
        signal_volume = volume_m.loc[signal_period].reindex(members)
        signal_money = money_m.loc[signal_period].reindex(members)
        signal_trade_ok = signal_close.gt(0) & np.isfinite(signal_close) & signal_volume.gt(0) & signal_money.gt(0)
        for J in J_values:
            denom_pos = t - J
            if denom_pos < 0:
                continue
            denom_period = periods[denom_pos]
            denom_close = close_m.loc[denom_period].reindex(members)
            endpoint_ok = signal_trade_ok & denom_close.gt(0) & np.isfinite(denom_close)
            if J <= 1:
                intermediate_ok = pd.Series(True, index=members)
                intermediate_count = 0
                min_intermediate_required = 0
                intermediate_share_by_inst = pd.Series(1.0, index=members)
            else:
                intermediate_periods = periods[denom_pos + 1 : t]
                intermediate_count = len(intermediate_periods)
                min_intermediate_required = min(int(math.ceil(J * min_intermediate_share)), intermediate_count)
                intermediate_valid = close_m.reindex(intermediate_periods)[members].gt(0) & np.isfinite(close_m.reindex(intermediate_periods)[members])
                valid_counts = intermediate_valid.sum(axis=0)
                intermediate_ok = valid_counts.ge(min_intermediate_required)
                intermediate_share_by_inst = valid_counts.div(max(1, intermediate_count))
            eligible_mask = endpoint_ok & intermediate_ok
            eligible = [inst for inst in members if bool(eligible_mask.get(inst, False))]
            rank_return = signal_close.reindex(eligible).div(denom_close.reindex(eligible)).sub(1.0).replace([np.inf, -np.inf], np.nan).dropna()
            eligible = rank_return.index.tolist()
            for inst in eligible:
                rank_rows.append(
                    {
                        "signal_month": str(signal_period),
                        "J": J,
                        "instrument": inst,
                        "rank_return": float(rank_return.loc[inst]),
                        "signal_close": float(signal_close.loc[inst]),
                        "denominator_month": str(denom_period),
                        "denominator_close": float(denom_close.loc[inst]),
                        "intermediate_month_count": intermediate_count,
                        "min_valid_intermediate_monthly_closes_required": min_intermediate_required,
                        "intermediate_month_coverage_share": float(intermediate_share_by_inst.get(inst, np.nan)),
                        "signal_month_pit_member": True,
                        "denominator_month_pit_member": inst in members_by_period.get(denom_period, set()),
                    }
                )
            for K in K_values:
                for skip_mode in ["no_skip"]:
                    first_holding_pos = t + 1
                    final_holding_pos = t + K
                    if first_holding_pos >= len(periods):
                        continue
                    first_holding_period = periods[first_holding_pos]
                    final_holding_period = periods[final_holding_pos] if final_holding_pos < len(periods) else pd.Period("2099-12", freq="M")
                    split = split_for_period(first_holding_period, config)
                    if split == "out_of_split":
                        continue
                    label_complete = final_holding_pos < len(periods)
                    for grouping, bucket_count in grouping_methods.items():
                        status = "complete"
                        block_reason = ""
                        if len(eligible) < min_signal_count:
                            status = "blocked"
                            block_reason = "insufficient_signal_eligible_universe"
                        if not label_complete:
                            status = "blocked"
                            block_reason = "blocked_incomplete_future_return_label"
                        loser: tuple[str, ...] = tuple()
                        winner: tuple[str, ...] = tuple()
                        if status == "complete":
                            order = sorted(
                                eligible,
                                key=lambda inst: (
                                    float(rank_return.loc[inst]),
                                    stable_hash_value([requirement_id, inst, str(signal_period), str(J), grouping, tiebreak_seed]),
                                ),
                            )
                            labels = near_equal_bucket_labels(len(order), bucket_count)
                            loser = tuple(inst for inst, label in zip(order, labels, strict=False) if label == 0)
                            winner = tuple(inst for inst, label in zip(order, labels, strict=False) if label == bucket_count - 1)
                            if len(loser) < leg_min(grouping) or len(winner) < leg_min(grouping):
                                status = "blocked"
                                block_reason = "assigned_leg_too_small"
                            else:
                                for inst, label in zip(order, labels, strict=False):
                                    if label in {0, bucket_count - 1}:
                                        bucket_rows.append(
                                            {
                                                "signal_month": str(signal_period),
                                                "first_holding_month": str(first_holding_period),
                                                "grouping": grouping,
                                                "bucket_count": bucket_count,
                                                "J": J,
                                                "K": K,
                                                "skip_mode": skip_mode,
                                                "instrument": inst,
                                                "bucket": int(label),
                                                "leg": "loser" if label == 0 else "winner",
                                                "rank_return": float(rank_return.loc[inst]),
                                                "intermediate_month_coverage_share": float(intermediate_share_by_inst.get(inst, np.nan)),
                                            }
                                        )
                        vintage_id = f"{grouping}_J{J}_K{K}_{skip_mode}_{signal_period}"
                        vintages.append(
                            VintageSpec(
                                vintage_id=vintage_id,
                                grouping=grouping,
                                bucket_count=bucket_count,
                                J=J,
                                K=K,
                                skip_mode=skip_mode,
                                signal_period=signal_period,
                                first_holding_period=first_holding_period,
                                final_holding_period=final_holding_period,
                                split=split,
                                loser=loser,
                                winner=winner,
                                signal_eligible_count=len(eligible),
                                status=status,
                                block_reason=block_reason,
                            )
                        )
                        label_rows.append(
                            {
                                "signal_month": str(signal_period),
                                "first_holding_month": str(first_holding_period),
                                "final_holding_month": str(final_holding_period) if label_complete else "",
                                "split": split,
                                "grouping": grouping,
                                "J": J,
                                "K": K,
                                "skip_mode": skip_mode,
                                "signal_eligible_instrument_count": len(eligible),
                                "rank_denominator_missing_count": int((~endpoint_ok).sum()),
                                "intermediate_month_count": intermediate_count,
                                "min_valid_intermediate_monthly_closes_required": min_intermediate_required,
                                "min_intermediate_month_coverage_share": float(intermediate_share_by_inst.reindex(eligible).min()) if eligible else np.nan,
                                "assigned_loser_leg_count": len(loser),
                                "assigned_winner_leg_count": len(winner),
                                "signal_eligibility_status": "complete" if len(eligible) >= min_signal_count else "blocked_insufficient_signal_eligible_universe",
                                "holding_label_status": "complete" if label_complete else "blocked_incomplete_future_return_label",
                                "portfolio_month_status": status,
                                "block_reason": block_reason,
                            }
                        )
            # Paper-style skip-one-month diagonal robustness only.
            K = J
            first_holding_pos = t + 2
            final_holding_pos = t + K + 1
            if first_holding_pos < len(periods):
                first_holding_period = periods[first_holding_pos]
                final_holding_period = periods[final_holding_pos] if final_holding_pos < len(periods) else pd.Period("2099-12", freq="M")
                split = split_for_period(first_holding_period, config)
                if split != "out_of_split":
                    label_complete = final_holding_pos < len(periods)
                    for grouping, bucket_count in grouping_methods.items():
                        status = "complete"
                        block_reason = ""
                        if len(eligible) < min_signal_count:
                            status = "blocked"
                            block_reason = "insufficient_signal_eligible_universe"
                        if not label_complete:
                            status = "blocked"
                            block_reason = "blocked_incomplete_future_return_label"
                        loser = tuple()
                        winner = tuple()
                        if status == "complete":
                            order = sorted(
                                eligible,
                                key=lambda inst: (
                                    float(rank_return.loc[inst]),
                                    stable_hash_value([requirement_id, inst, str(signal_period), str(J), grouping, tiebreak_seed]),
                                ),
                            )
                            labels = near_equal_bucket_labels(len(order), bucket_count)
                            loser = tuple(inst for inst, label in zip(order, labels, strict=False) if label == 0)
                            winner = tuple(inst for inst, label in zip(order, labels, strict=False) if label == bucket_count - 1)
                            if len(loser) < leg_min(grouping) or len(winner) < leg_min(grouping):
                                status = "blocked"
                                block_reason = "assigned_leg_too_small"
                            else:
                                for inst, label in zip(order, labels, strict=False):
                                    if label in {0, bucket_count - 1}:
                                        bucket_rows.append(
                                            {
                                                "signal_month": str(signal_period),
                                                "first_holding_month": str(first_holding_period),
                                                "grouping": grouping,
                                                "bucket_count": bucket_count,
                                                "J": J,
                                                "K": K,
                                                "skip_mode": "skip1",
                                                "instrument": inst,
                                                "bucket": int(label),
                                                "leg": "loser" if label == 0 else "winner",
                                                "rank_return": float(rank_return.loc[inst]),
                                                "intermediate_month_coverage_share": float(intermediate_share_by_inst.get(inst, np.nan)),
                                            }
                                        )
                        vintage_id = f"{grouping}_J{J}_K{K}_skip1_{signal_period}"
                        vintages.append(
                            VintageSpec(
                                vintage_id=vintage_id,
                                grouping=grouping,
                                bucket_count=bucket_count,
                                J=J,
                                K=K,
                                skip_mode="skip1",
                                signal_period=signal_period,
                                first_holding_period=first_holding_period,
                                final_holding_period=final_holding_period,
                                split=split,
                                loser=loser,
                                winner=winner,
                                signal_eligible_count=len(eligible),
                                status=status,
                                block_reason=block_reason,
                            )
                        )
                        label_rows.append(
                            {
                                "signal_month": str(signal_period),
                                "first_holding_month": str(first_holding_period),
                                "final_holding_month": str(final_holding_period) if label_complete else "",
                                "split": split,
                                "grouping": grouping,
                                "J": J,
                                "K": K,
                                "skip_mode": "skip1",
                                "signal_eligible_instrument_count": len(eligible),
                                "rank_denominator_missing_count": int((~endpoint_ok).sum()),
                                "intermediate_month_count": intermediate_count,
                                "min_valid_intermediate_monthly_closes_required": min_intermediate_required,
                                "min_intermediate_month_coverage_share": float(intermediate_share_by_inst.reindex(eligible).min()) if eligible else np.nan,
                                "assigned_loser_leg_count": len(loser),
                                "assigned_winner_leg_count": len(winner),
                                "signal_eligibility_status": "complete" if len(eligible) >= min_signal_count else "blocked_insufficient_signal_eligible_universe",
                                "holding_label_status": "complete" if label_complete else "blocked_incomplete_future_return_label",
                                "portfolio_month_status": status,
                                "block_reason": block_reason,
                            }
                        )
    return vintages, pd.DataFrame(label_rows), pd.DataFrame(bucket_rows), pd.DataFrame(rank_rows)


def reset_output_dirs(paths: Paths) -> None:
    if paths.output_root.exists():
        root = paths.output_root.resolve()
        topic = TOPIC_DIR.resolve()
        if topic not in [root, *root.parents]:
            raise RuntimeError(f"Refusing to remove output root outside topic dir: {paths.output_root}")
        shutil.rmtree(paths.output_root)
    for directory in [
        paths.configs_dir,
        paths.manifests_dir,
        paths.validation_dir,
        paths.calendar_dir,
        paths.signals_dir,
        paths.returns_dir,
        paths.reports_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def period_range(start: pd.Period, end: pd.Period) -> list[pd.Period]:
    if end < start:
        return []
    return list(pd.period_range(start, end, freq="M"))


def leg_return_stats(
    monthly_ret: pd.DataFrame,
    period: pd.Period,
    instruments: tuple[str, ...],
    min_count: int,
    min_share: float,
) -> dict[str, Any]:
    if not instruments or period not in monthly_ret.index:
        return {"return": np.nan, "count": 0, "share": 0.0, "status": "blocked_empty_leg_or_month"}
    vals = monthly_ret.loc[period].reindex(list(instruments)).replace([np.inf, -np.inf], np.nan).dropna()
    count = int(len(vals))
    share = count / len(instruments) if instruments else 0.0
    if count < min_count or share < min_share:
        return {"return": np.nan, "count": count, "share": share, "status": "blocked_insufficient_leg_return_coverage"}
    return {"return": float(vals.mean()), "count": count, "share": share, "status": "complete"}


def exchange_map(inst_map: pd.DataFrame) -> dict[str, str]:
    mapping = {"SH": "SHSE", "SZ": "SZSE", "SHSE": "SHSE", "SZSE": "SZSE"}
    frame = inst_map.copy()
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame["exchange_group"] = frame["exchange"].astype(str).str.upper().map(mapping).fillna(frame["exchange"].astype(str))
    return frame.set_index("instrument")["exchange_group"].to_dict()


def compute_vintage_returns(
    vintages: list[VintageSpec],
    monthly_ret: pd.DataFrame,
    inst_map: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    min_count = int(config["portfolio"]["label_evaluable_leg_count_min"])
    min_share = float(config["portfolio"]["label_evaluable_leg_share_min"])
    primary_grouping = str(config["portfolio"]["primary_grouping"])
    exch = exchange_map(inst_map)
    monthly_rows: list[dict[str, Any]] = []

    for spec in vintages:
        if spec.status != "complete":
            continue
        holding_months = period_range(spec.first_holding_period, spec.final_holding_period)
        exchange_groups: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [("ALL", spec.loser, spec.winner)]
        if spec.grouping == primary_grouping and spec.skip_mode == "no_skip":
            for group in ["SHSE", "SZSE"]:
                loser = tuple(inst for inst in spec.loser if exch.get(inst) == group)
                winner = tuple(inst for inst in spec.winner if exch.get(inst) == group)
                exchange_groups.append((group, loser, winner))

        for period in holding_months:
            for group, loser, winner in exchange_groups:
                loser_stats = leg_return_stats(monthly_ret, period, loser, min_count, min_share)
                winner_stats = leg_return_stats(monthly_ret, period, winner, min_count, min_share)
                status = "complete" if loser_stats["status"] == "complete" and winner_stats["status"] == "complete" else "blocked"
                if status == "complete":
                    loser_ret = float(loser_stats["return"])
                    winner_ret = float(winner_stats["return"])
                    contrarian_ret = loser_ret - winner_ret
                    momentum_ret = winner_ret - loser_ret
                    block_reason = ""
                else:
                    loser_ret = np.nan
                    winner_ret = np.nan
                    contrarian_ret = np.nan
                    momentum_ret = np.nan
                    block_reason = ";".join(sorted({loser_stats["status"], winner_stats["status"]}))
                monthly_rows.append(
                    {
                        "vintage_id": spec.vintage_id,
                        "signal_month": str(spec.signal_period),
                        "first_holding_month": str(spec.first_holding_period),
                        "final_holding_month": str(spec.final_holding_period),
                        "calendar_month": str(period),
                        "split": spec.split,
                        "grouping": spec.grouping,
                        "bucket_count": spec.bucket_count,
                        "J": spec.J,
                        "K": spec.K,
                        "skip_mode": spec.skip_mode,
                        "exchange_group": group,
                        "loser_assigned_count": len(loser),
                        "winner_assigned_count": len(winner),
                        "loser_label_count": loser_stats["count"],
                        "winner_label_count": winner_stats["count"],
                        "loser_label_share": loser_stats["share"],
                        "winner_label_share": winner_stats["share"],
                        "loser_return": loser_ret,
                        "winner_return": winner_ret,
                        "contrarian_return": contrarian_ret,
                        "momentum_return": momentum_ret,
                        "vintage_month_status": status,
                        "block_reason": block_reason,
                    }
                )

    monthly_df = pd.DataFrame(monthly_rows)
    holding_rows: list[dict[str, Any]] = []
    if not monthly_df.empty:
        all_scope = monthly_df.loc[monthly_df["exchange_group"].eq("ALL")].copy()
        for vintage_id, frame in all_scope.groupby("vintage_id", sort=True):
            first = frame.iloc[0]
            complete = frame.loc[frame["vintage_month_status"].eq("complete")].sort_values("calendar_month")
            expected_k = int(first["K"])
            if len(complete) == expected_k:
                loser_cum = float((1.0 + complete["loser_return"].astype(float)).prod() - 1.0)
                winner_cum = float((1.0 + complete["winner_return"].astype(float)).prod() - 1.0)
                status = "complete"
                block_reason = ""
            else:
                loser_cum = np.nan
                winner_cum = np.nan
                status = "blocked"
                block_reason = "incomplete_vintage_month_return_labels"
            holding_rows.append(
                {
                    "vintage_id": vintage_id,
                    "signal_month": first["signal_month"],
                    "first_holding_month": first["first_holding_month"],
                    "final_holding_month": first["final_holding_month"],
                    "split": first["split"],
                    "grouping": first["grouping"],
                    "J": int(first["J"]),
                    "K": int(first["K"]),
                    "skip_mode": first["skip_mode"],
                    "vintage_month_count": int(len(complete)),
                    "expected_vintage_month_count": expected_k,
                    "loser_cumulative_return": loser_cum,
                    "winner_cumulative_return": winner_cum,
                    "contrarian_cumulative_spread": loser_cum - winner_cum if np.isfinite(loser_cum) and np.isfinite(winner_cum) else np.nan,
                    "momentum_cumulative_spread": winner_cum - loser_cum if np.isfinite(loser_cum) and np.isfinite(winner_cum) else np.nan,
                    "vintage_holding_status": status,
                    "block_reason": block_reason,
                }
            )
    return pd.DataFrame(holding_rows), monthly_df


def target_weights(spec: VintageSpec, mode: str) -> dict[str, float]:
    weights: dict[str, float] = {}
    if mode in {"contrarian", "loser_long_only"} and spec.loser:
        w = 1.0 / len(spec.loser)
        for inst in spec.loser:
            weights[inst] = weights.get(inst, 0.0) + w
    if mode == "contrarian" and spec.winner:
        w = -1.0 / len(spec.winner)
        for inst in spec.winner:
            weights[inst] = weights.get(inst, 0.0) + w
    return weights


def combine_active_weights(active_specs: list[VintageSpec], mode: str) -> dict[str, float]:
    combined: dict[str, float] = {}
    if not active_specs:
        return combined
    scale = 1.0 / len(active_specs)
    for spec in active_specs:
        for inst, weight in target_weights(spec, mode).items():
            combined[inst] = combined.get(inst, 0.0) + scale * weight
    return {inst: weight for inst, weight in combined.items() if abs(weight) > 1e-15}


def turnover_from_to(previous: dict[str, float], current: dict[str, float]) -> tuple[float, float]:
    buy = 0.0
    sell = 0.0
    for inst in set(previous) | set(current):
        diff = current.get(inst, 0.0) - previous.get(inst, 0.0)
        if diff > 0:
            buy += diff
        elif diff < 0:
            sell += -diff
    return float(buy), float(sell)


def compute_calendar_returns(
    vintages: list[VintageSpec],
    vintage_monthly: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if vintage_monthly.empty:
        return pd.DataFrame(), pd.DataFrame()
    cost_buy = float(config["execution"]["buy_cost_bps"]) / 10000.0
    cost_sell = float(config["execution"]["sell_cost_bps"]) / 10000.0
    complete_specs = [spec for spec in vintages if spec.status == "complete"]
    spec_by_key: dict[tuple[str, int, int, str, str], list[VintageSpec]] = {}
    for spec in complete_specs:
        key = (spec.grouping, spec.J, spec.K, spec.skip_mode, spec.split)
        spec_by_key.setdefault(key, []).append(spec)

    all_monthly = vintage_monthly.loc[vintage_monthly["exchange_group"].eq("ALL")].copy()
    aggregate_cols = ["split", "grouping", "J", "K", "skip_mode", "calendar_month"]
    complete_agg = (
        all_monthly.loc[all_monthly["vintage_month_status"].eq("complete")]
        .groupby(aggregate_cols, as_index=False)
        .agg(
            loser_return=("loser_return", "mean"),
            winner_return=("winner_return", "mean"),
            contrarian_return=("contrarian_return", "mean"),
            momentum_return=("momentum_return", "mean"),
            complete_vintage_return_count=("vintage_id", "count"),
        )
    )
    complete_lookup = {
        (str(row.split), str(row.grouping), int(row.J), int(row.K), str(row.skip_mode), str(row.calendar_month)): row
        for row in complete_agg.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    for key, specs in sorted(spec_by_key.items(), key=lambda kv: (kv[0][4], kv[0][0], kv[0][1], kv[0][2], kv[0][3])):
        grouping, J, K, skip_mode, split = key
        min_period = min(spec.first_holding_period for spec in specs)
        max_period = max(spec.final_holding_period for spec in specs)
        previous_contrarian: dict[str, float] = {}
        previous_loser: dict[str, float] = {}
        for period in period_range(min_period, max_period):
            active = [spec for spec in specs if spec.first_holding_period <= period <= spec.final_holding_period]
            if not active:
                previous_contrarian = {}
                previous_loser = {}
                continue
            complete_row = complete_lookup.get((split, grouping, J, K, skip_mode, str(period)))
            current_contrarian = combine_active_weights(active, "contrarian")
            current_loser = combine_active_weights(active, "loser_long_only")
            buy_turnover, sell_turnover = turnover_from_to(previous_contrarian, current_contrarian)
            loser_buy_turnover, loser_sell_turnover = turnover_from_to(previous_loser, current_loser)
            terminal_settlement = period == max_period
            if terminal_settlement:
                terminal_buy, terminal_sell = turnover_from_to(current_contrarian, {})
                buy_turnover += terminal_buy
                sell_turnover += terminal_sell
                terminal_loser_buy, terminal_loser_sell = turnover_from_to(current_loser, {})
                loser_buy_turnover += terminal_loser_buy
                loser_sell_turnover += terminal_loser_sell

            if complete_row is not None:
                loser_ret = float(complete_row.loser_return)
                winner_ret = float(complete_row.winner_return)
                contrarian_ret = float(complete_row.contrarian_return)
                momentum_ret = float(complete_row.momentum_return)
                complete_count = int(complete_row.complete_vintage_return_count)
            else:
                loser_ret = np.nan
                winner_ret = np.nan
                contrarian_ret = np.nan
                momentum_ret = np.nan
                complete_count = 0
            after_cost = contrarian_ret - buy_turnover * cost_buy - sell_turnover * cost_sell if np.isfinite(contrarian_ret) else np.nan
            loser_after_cost = loser_ret - loser_buy_turnover * cost_buy - loser_sell_turnover * cost_sell if np.isfinite(loser_ret) else np.nan
            row_status = "complete" if complete_count == len(active) and len(active) > 0 else "partial_or_blocked"
            rows.append(
                {
                    "split": split,
                    "calendar_month": str(period),
                    "grouping": grouping,
                    "J": J,
                    "K": K,
                    "skip_mode": skip_mode,
                    "active_vintage_count": int(len(active)),
                    "complete_vintage_return_count": complete_count,
                    "portfolio_month_status": row_status,
                    "loser_return": loser_ret,
                    "winner_return": winner_ret,
                    "contrarian_return": contrarian_ret,
                    "momentum_return": momentum_ret,
                    "buy_turnover": buy_turnover,
                    "sell_turnover": sell_turnover,
                    "turnover": buy_turnover + sell_turnover,
                    "after_cost_return": after_cost,
                    "loser_long_only_buy_turnover": loser_buy_turnover,
                    "loser_long_only_sell_turnover": loser_sell_turnover,
                    "loser_long_only_after_cost_return": loser_after_cost,
                    "terminal_settlement_turnover_included": terminal_settlement,
                    "combined_weight_policy": "combined_weight_i_h = active_vintage_count^-1 * sum_active signed_leg_weight_i",
                    "requires_short_exposure": True,
                }
            )
            previous_contrarian = current_contrarian
            previous_loser = current_loser
    calendar_returns = pd.DataFrame(rows)
    after_cost_cols = [
        "split",
        "calendar_month",
        "grouping",
        "J",
        "K",
        "skip_mode",
        "contrarian_return",
        "buy_turnover",
        "sell_turnover",
        "after_cost_return",
        "loser_return",
        "loser_long_only_buy_turnover",
        "loser_long_only_sell_turnover",
        "loser_long_only_after_cost_return",
        "terminal_settlement_turnover_included",
    ]
    return calendar_returns, calendar_returns[after_cost_cols].copy()


def provider_end_feasibility(month_ends: pd.Series, config: dict[str, Any]) -> pd.DataFrame:
    periods = pd.PeriodIndex(month_ends.index, freq="M")
    provider_end = pd.Timestamp(config["data_sources"]["provider_load_end_date"]).to_period("M")
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        first_holding = [p for p in periods if split_for_period(p, config) == split]
        for K in [int(v) for v in config["signals"]["K_values"]]:
            feasible = [p for p in first_holding if p + K - 1 <= provider_end]
            rows.append(
                {
                    "split": split,
                    "K": K,
                    "candidate_first_holding_month_count": int(len(first_holding)),
                    "provider_end_complete_first_holding_month_count": int(len(feasible)),
                    "first_evaluable_first_holding_month": str(feasible[0]) if feasible else "",
                    "last_evaluable_first_holding_month": str(feasible[-1]) if feasible else "",
                    "provider_end_month": str(provider_end),
                    "blocked_first_holding_month_count": int(len(first_holding) - len(feasible)),
                }
            )
    return pd.DataFrame(rows)


def signal_history_feasibility(label_df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if label_df.empty:
        return pd.DataFrame()
    primary_grouping = str(config["portfolio"]["primary_grouping"])
    primary_J = set(map(int, config["signals"]["primary_local_decision_J_values"]))
    primary_K = set(map(int, config["signals"]["primary_local_decision_K_values"]))
    frame = label_df.loc[label_df["grouping"].eq(primary_grouping) & label_df["skip_mode"].eq("no_skip")].copy()
    rows: list[dict[str, Any]] = []
    for (split, J, K), part in frame.groupby(["split", "J", "K"], sort=True):
        complete = part.loc[part["portfolio_month_status"].eq("complete")].copy()
        rows.append(
            {
                "split": split,
                "J": int(J),
                "K": int(K),
                "first_evaluable_signal_month_by_JK": complete["signal_month"].min() if not complete.empty else "",
                "first_evaluable_first_holding_month_by_JK": complete["first_holding_month"].min() if not complete.empty else "",
                "last_evaluable_first_holding_month_by_JK": complete["first_holding_month"].max() if not complete.empty else "",
                "evaluable_first_holding_month_count": int(complete["first_holding_month"].nunique()) if not complete.empty else 0,
                "candidate_first_holding_month_count": int(part["first_holding_month"].nunique()),
                "min_signal_eligible_instrument_count": float(complete["signal_eligible_instrument_count"].min()) if not complete.empty else np.nan,
                "min_intermediate_month_coverage_share": float(complete["min_intermediate_month_coverage_share"].min()) if not complete.empty else np.nan,
                "primary_local_decision_cell": bool(int(J) in primary_J and int(K) in primary_K),
                "cell_status": "complete" if not complete.empty else "blocked",
            }
        )
    return pd.DataFrame(rows)


def summarize_series(values: pd.Series, K: int, annualization: int) -> dict[str, Any]:
    series = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    n = int(len(series))
    lag = min(max(int(K) - 1, 0), max(n - 1, 0))
    alt_lag = min(int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0))) if n > 0 else 0, max(n - 1, 0))
    if n == 0:
        return {
            "month_count": 0,
            "monthly_mean_return": np.nan,
            "annualized_mean_return": np.nan,
            "monthly_volatility": np.nan,
            "annualized_sharpe": np.nan,
            "positive_month_share": np.nan,
            "t_stat_monthly_mean_newey_west": np.nan,
            "newey_west_lag_used": lag,
            "newey_west_alt_lag_used": alt_lag,
            "t_stat_monthly_mean_newey_west_alt_lag": np.nan,
            "max_drawdown": np.nan,
        }
    mean = float(series.mean())
    vol = float(series.std(ddof=1)) if n > 1 else np.nan
    return {
        "month_count": n,
        "monthly_mean_return": mean,
        "annualized_mean_return": mean * annualization,
        "monthly_volatility": vol,
        "annualized_sharpe": (mean / vol * math.sqrt(annualization)) if np.isfinite(vol) and vol > 0 else np.nan,
        "positive_month_share": float((series > 0).mean()),
        "t_stat_monthly_mean_newey_west": newey_west_tstat(series, lag),
        "newey_west_lag_used": lag,
        "newey_west_alt_lag_used": alt_lag,
        "t_stat_monthly_mean_newey_west_alt_lag": newey_west_tstat(series, alt_lag),
        "max_drawdown": max_drawdown(series),
    }


def summarize_calendar_returns(calendar_returns: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if calendar_returns.empty:
        return pd.DataFrame()
    annualization = int(config["statistics"]["annualization_months"])
    rows: list[dict[str, Any]] = []
    group_cols = ["split", "grouping", "J", "K", "skip_mode"]
    for key, part in calendar_returns.groupby(group_cols, sort=True):
        split, grouping, J, K, skip_mode = key
        usable = part.loc[part["complete_vintage_return_count"].gt(0)].sort_values("calendar_month").copy()
        stats = summarize_series(usable["contrarian_return"], int(K), annualization)
        after = summarize_series(usable["after_cost_return"], int(K), annualization)
        loser_after = summarize_series(usable["loser_long_only_after_cost_return"], int(K), annualization)
        row = {
            "split": split,
            "grouping": grouping,
            "J": int(J),
            "K": int(K),
            "skip_mode": skip_mode,
            "calendar_month_min": usable["calendar_month"].min() if not usable.empty else "",
            "calendar_month_max": usable["calendar_month"].max() if not usable.empty else "",
            "month_count": stats["month_count"],
            "monthly_mean_return": stats["monthly_mean_return"],
            "annualized_mean_return": stats["annualized_mean_return"],
            "monthly_volatility": stats["monthly_volatility"],
            "annualized_sharpe": stats["annualized_sharpe"],
            "positive_month_share": stats["positive_month_share"],
            "t_stat_monthly_mean_newey_west": stats["t_stat_monthly_mean_newey_west"],
            "newey_west_lag_used": stats["newey_west_lag_used"],
            "newey_west_alt_lag_used": stats["newey_west_alt_lag_used"],
            "t_stat_monthly_mean_newey_west_alt_lag": stats["t_stat_monthly_mean_newey_west_alt_lag"],
            "max_drawdown": stats["max_drawdown"],
            "loser_monthly_mean_return": float(usable["loser_return"].mean()) if not usable.empty else np.nan,
            "winner_monthly_mean_return": float(usable["winner_return"].mean()) if not usable.empty else np.nan,
            "after_cost_monthly_mean_return": after["monthly_mean_return"],
            "after_cost_annualized_mean_return": after["annualized_mean_return"],
            "after_cost_t_stat_newey_west": after["t_stat_monthly_mean_newey_west"],
            "after_cost_positive_month_share": after["positive_month_share"],
            "loser_long_only_after_cost_monthly_mean_return": loser_after["monthly_mean_return"],
            "loser_long_only_after_cost_t_stat_newey_west": loser_after["t_stat_monthly_mean_newey_west"],
            "active_vintage_count_median": float(usable["active_vintage_count"].median()) if not usable.empty else np.nan,
            "mean_buy_turnover": float(usable["buy_turnover"].mean()) if not usable.empty else np.nan,
            "mean_sell_turnover": float(usable["sell_turnover"].mean()) if not usable.empty else np.nan,
            "mean_loser_long_only_buy_turnover": float(usable["loser_long_only_buy_turnover"].mean()) if not usable.empty else np.nan,
            "mean_loser_long_only_sell_turnover": float(usable["loser_long_only_sell_turnover"].mean()) if not usable.empty else np.nan,
            "terminal_settlement_months": int(usable["terminal_settlement_turnover_included"].sum()) if not usable.empty else 0,
            "months_requiring_short_exposure": int(usable["requires_short_exposure"].sum()) if not usable.empty else 0,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def grouping_relative_summary(summary: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    frame = summary.loc[summary["skip_mode"].eq("no_skip")].copy()
    pivot = frame.pivot_table(
        index=["split", "J", "K"],
        columns="grouping",
        values=["monthly_mean_return", "after_cost_monthly_mean_return", "month_count"],
        aggfunc="first",
    )
    rows: list[dict[str, Any]] = []
    for idx, values in pivot.iterrows():
        split, J, K = idx
        def get(metric: str, grouping: str) -> float:
            try:
                return float(values[(metric, grouping)])
            except Exception:  # noqa: BLE001
                return np.nan

        decile = get("monthly_mean_return", "decile")
        quintile = get("monthly_mean_return", "quintile")
        tertile = get("monthly_mean_return", "tertile")
        rows.append(
            {
                "split": split,
                "J": int(J),
                "K": int(K),
                "primary_local_decision_cell": bool(
                    int(J) in set(map(int, config["signals"]["primary_local_decision_J_values"]))
                    and int(K) in set(map(int, config["signals"]["primary_local_decision_K_values"]))
                ),
                "decile_monthly_mean_return": decile,
                "quintile_monthly_mean_return": quintile,
                "tertile_monthly_mean_return": tertile,
                "decile_after_cost_monthly_mean_return": get("after_cost_monthly_mean_return", "decile"),
                "quintile_after_cost_monthly_mean_return": get("after_cost_monthly_mean_return", "quintile"),
                "tertile_after_cost_monthly_mean_return": get("after_cost_monthly_mean_return", "tertile"),
                "decile_month_count": get("month_count", "decile"),
                "quintile_month_count": get("month_count", "quintile"),
                "tertile_month_count": get("month_count", "tertile"),
                "decile_ge_tertile": bool(np.isfinite(decile) and np.isfinite(tertile) and decile >= tertile),
                "decile_ge_quintile": bool(np.isfinite(decile) and np.isfinite(quintile) and decile >= quintile),
                "quintile_ge_tertile": bool(np.isfinite(quintile) and np.isfinite(tertile) and quintile >= tertile),
            }
        )
    return pd.DataFrame(rows)


def loser_winner_leg_summary(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    cols = [
        "split",
        "grouping",
        "J",
        "K",
        "skip_mode",
        "month_count",
        "loser_monthly_mean_return",
        "winner_monthly_mean_return",
        "monthly_mean_return",
        "loser_long_only_after_cost_monthly_mean_return",
        "loser_long_only_after_cost_t_stat_newey_west",
    ]
    out = summary[cols].copy()
    out["loser_minus_winner_monthly_mean_return"] = out["loser_monthly_mean_return"] - out["winner_monthly_mean_return"]
    return out


def cluster_monthly_returns(calendar_returns: pd.DataFrame, config: dict[str, Any], grouping: str | None = None) -> pd.DataFrame:
    if calendar_returns.empty:
        return pd.DataFrame()
    primary_grouping = grouping or str(config["portfolio"]["primary_grouping"])
    primary_J = set(map(int, config["signals"]["primary_local_decision_J_values"]))
    primary_K = set(map(int, config["signals"]["primary_local_decision_K_values"]))
    frame = calendar_returns.loc[
        calendar_returns["grouping"].eq(primary_grouping)
        & calendar_returns["skip_mode"].eq("no_skip")
        & calendar_returns["J"].isin(primary_J)
        & calendar_returns["K"].isin(primary_K)
        & calendar_returns["complete_vintage_return_count"].gt(0)
    ].copy()
    if frame.empty:
        return pd.DataFrame()
    return (
        frame.groupby(["split", "calendar_month"], as_index=False)
        .agg(
            contrarian_return=("contrarian_return", "mean"),
            after_cost_return=("after_cost_return", "mean"),
            loser_return=("loser_return", "mean"),
            winner_return=("winner_return", "mean"),
            loser_long_only_after_cost_return=("loser_long_only_after_cost_return", "mean"),
            primary_cell_count=("J", "count"),
            active_vintage_count=("active_vintage_count", "sum"),
            complete_vintage_return_count=("complete_vintage_return_count", "sum"),
        )
        .sort_values(["split", "calendar_month"])
    )


def cluster_stats(calendar_returns: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    cluster = cluster_monthly_returns(calendar_returns, config)
    annualization = int(config["statistics"]["annualization_months"])
    rows: list[dict[str, Any]] = []
    for split in SPLITS:
        part = cluster.loc[cluster["split"].eq(split)].copy() if not cluster.empty else pd.DataFrame()
        stats = summarize_series(part["contrarian_return"] if not part.empty else pd.Series(dtype=float), 1, annualization)
        after = summarize_series(part["after_cost_return"] if not part.empty else pd.Series(dtype=float), 1, annualization)
        loser_after = summarize_series(part["loser_long_only_after_cost_return"] if not part.empty else pd.Series(dtype=float), 1, annualization)
        rows.append(
            {
                "split": split,
                "month_count": stats["month_count"],
                "monthly_mean_return": stats["monthly_mean_return"],
                "annualized_mean_return": stats["annualized_mean_return"],
                "t_stat_monthly_mean_newey_west": stats["t_stat_monthly_mean_newey_west"],
                "after_cost_monthly_mean_return": after["monthly_mean_return"],
                "after_cost_t_stat_newey_west": after["t_stat_monthly_mean_newey_west"],
                "loser_monthly_mean_return": float(part["loser_return"].mean()) if not part.empty else np.nan,
                "winner_monthly_mean_return": float(part["winner_return"].mean()) if not part.empty else np.nan,
                "loser_long_only_after_cost_monthly_mean_return": loser_after["monthly_mean_return"],
                "loser_long_only_after_cost_t_stat_newey_west": loser_after["t_stat_monthly_mean_newey_west"],
                "primary_cell_count_mean_per_month": float(part["primary_cell_count"].mean()) if not part.empty else np.nan,
            }
        )
    return pd.DataFrame(rows)


def build_state_reports(
    calendar_returns: pd.DataFrame,
    config: dict[str, Any],
    month_ends: pd.Series,
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    provider_uri = topic_path(config["data_sources"]["qlib_provider_uri"])
    index_inst = str(config["data_sources"]["index_instrument"])
    close = read_qlib_series(provider_uri, calendar, index_inst, "close")
    monthly_dates = pd.DatetimeIndex(month_ends.values)
    index_close = close.reindex(monthly_dates).astype(float)
    index_close.index = pd.PeriodIndex(month_ends.index, freq="M")
    train_start = pd.Timestamp(config["sample_split"]["train_start"]).to_period("M")
    train_end = pd.Timestamp(config["sample_split"]["train_end"]).to_period("M")
    rng = np.random.default_rng(int(config["state"]["bootstrap_seed"]))
    iterations = int(config["state"]["bootstrap_iterations"])
    quantiles = [float(q) for q in config["state"]["train_percentile_quantiles"]]
    threshold_rows: list[dict[str, Any]] = []
    state_frames: list[pd.DataFrame] = []
    for window in [int(w) for w in config["state"]["sign_state_windows_months"]]:
        prior = index_close.shift(1).div(index_close.shift(window + 1)).sub(1.0)
        train_values = prior.loc[(prior.index >= train_start) & (prior.index <= train_end)].replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        if len(train_values):
            q_values = np.quantile(train_values, quantiles)
            boot = np.empty((iterations, len(quantiles)))
            for i in range(iterations):
                boot[i] = np.quantile(rng.choice(train_values, size=len(train_values), replace=True), quantiles)
        else:
            q_values = np.array([np.nan] * len(quantiles))
            boot = np.empty((0, len(quantiles)))
        for idx, q in enumerate(quantiles):
            threshold_rows.append(
                {
                    "state_window_months": window,
                    "quantile": q,
                    "train_observation_count": int(len(train_values)),
                    "threshold": float(q_values[idx]) if len(q_values) else np.nan,
                    "bootstrap_ci_low": float(np.quantile(boot[:, idx], 0.025)) if len(boot) else np.nan,
                    "bootstrap_ci_high": float(np.quantile(boot[:, idx], 0.975)) if len(boot) else np.nan,
                    "bootstrap_iterations": iterations,
                    "bootstrap_seed": int(config["state"]["bootstrap_seed"]),
                }
            )
        low = q_values[0] if len(q_values) else np.nan
        high = q_values[1] if len(q_values) > 1 else np.nan
        states = pd.DataFrame({"calendar_month": prior.index.astype(str), "state_window_months": window, "prior_index_return": prior.values})
        states["market_state"] = np.where(
            states["prior_index_return"].le(low),
            "down",
            np.where(states["prior_index_return"].ge(high), "up", "middle"),
        )
        states.loc[~np.isfinite(states["prior_index_return"]), "market_state"] = "unavailable"
        state_frames.append(states)

    cluster = cluster_monthly_returns(calendar_returns, config)
    state_table = pd.concat(state_frames, ignore_index=True) if state_frames else pd.DataFrame()
    rows: list[dict[str, Any]] = []
    if not cluster.empty and not state_table.empty:
        merged = cluster.merge(state_table, on="calendar_month", how="left")
        for (split, window, state), part in merged.groupby(["split", "state_window_months", "market_state"], sort=True):
            if state == "unavailable":
                continue
            stats = summarize_series(part["contrarian_return"], 1, int(config["statistics"]["annualization_months"]))
            after = summarize_series(part["after_cost_return"], 1, int(config["statistics"]["annualization_months"]))
            rows.append(
                {
                    "split": split,
                    "state_window_months": int(window),
                    "market_state": state,
                    "month_count": stats["month_count"],
                    "monthly_mean_return": stats["monthly_mean_return"],
                    "t_stat_monthly_mean_newey_west": stats["t_stat_monthly_mean_newey_west"],
                    "after_cost_monthly_mean_return": after["monthly_mean_return"],
                    "after_cost_t_stat_newey_west": after["t_stat_monthly_mean_newey_west"],
                    "positive_month_share": stats["positive_month_share"],
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(threshold_rows)


def build_exchange_summary(vintage_monthly: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if vintage_monthly.empty:
        return pd.DataFrame()
    primary_J = set(map(int, config["signals"]["primary_local_decision_J_values"]))
    primary_K = set(map(int, config["signals"]["primary_local_decision_K_values"]))
    frame = vintage_monthly.loc[
        vintage_monthly["exchange_group"].isin(["SHSE", "SZSE"])
        & vintage_monthly["grouping"].eq(config["portfolio"]["primary_grouping"])
        & vintage_monthly["skip_mode"].eq("no_skip")
        & vintage_monthly["J"].isin(primary_J)
        & vintage_monthly["K"].isin(primary_K)
        & vintage_monthly["vintage_month_status"].eq("complete")
    ].copy()
    if frame.empty:
        return pd.DataFrame()
    monthly = (
        frame.groupby(["split", "exchange_group", "calendar_month"], as_index=False)
        .agg(
            contrarian_return=("contrarian_return", "mean"),
            loser_return=("loser_return", "mean"),
            winner_return=("winner_return", "mean"),
            cell_vintage_count=("vintage_id", "count"),
        )
        .sort_values(["split", "exchange_group", "calendar_month"])
    )
    rows: list[dict[str, Any]] = []
    for (split, group), part in monthly.groupby(["split", "exchange_group"], sort=True):
        stats = summarize_series(part["contrarian_return"], 1, int(config["statistics"]["annualization_months"]))
        rows.append(
            {
                "split": split,
                "exchange_group": group,
                "month_count": stats["month_count"],
                "monthly_mean_return": stats["monthly_mean_return"],
                "t_stat_monthly_mean_newey_west": stats["t_stat_monthly_mean_newey_west"],
                "loser_monthly_mean_return": float(part["loser_return"].mean()),
                "winner_monthly_mean_return": float(part["winner_return"].mean()),
                "mean_cell_vintage_count": float(part["cell_vintage_count"].mean()),
            }
        )
    return pd.DataFrame(rows)


def determine_gate_decision(
    config: dict[str, Any],
    summary: pd.DataFrame,
    calendar_returns: pd.DataFrame,
    grouping_relative: pd.DataFrame,
    cost_contract: str,
) -> tuple[str, pd.DataFrame, dict[str, Any]]:
    gates = config["gates"]
    primary_grouping = str(config["portfolio"]["primary_grouping"])
    primary_J = set(map(int, config["signals"]["primary_local_decision_J_values"]))
    primary_K = set(map(int, config["signals"]["primary_local_decision_K_values"]))
    primary = summary.loc[
        summary["grouping"].eq(primary_grouping)
        & summary["skip_mode"].eq("no_skip")
        & summary["J"].isin(primary_J)
        & summary["K"].isin(primary_K)
    ].copy()
    validation_cells = primary.loc[primary["split"].eq("validation") & primary["month_count"].ge(int(gates["validation_primary_local_decision_min_month_count_per_cell"]))]
    robustness_cells = primary.loc[primary["split"].eq("robustness") & primary["month_count"].ge(int(gates["robustness_primary_local_decision_min_month_count_per_cell"]))]
    cluster = cluster_stats(calendar_returns, config).set_index("split")

    def cluster_value(split: str, col: str) -> float:
        if split not in cluster.index:
            return np.nan
        return float(cluster.loc[split, col])

    grouping_means = (
        summary.loc[summary["skip_mode"].eq("no_skip") & summary["J"].isin(primary_J) & summary["K"].isin(primary_K)]
        .groupby(["split", "grouping"], as_index=False)["monthly_mean_return"]
        .mean()
    )

    def grouping_mean(split: str, grouping: str) -> float:
        part = grouping_means.loc[grouping_means["split"].eq(split) & grouping_means["grouping"].eq(grouping)]
        return float(part["monthly_mean_return"].iloc[0]) if not part.empty else np.nan

    val_decile = grouping_mean("validation", "decile")
    val_tertile = grouping_mean("validation", "tertile")
    rob_decile = grouping_mean("robustness", "decile")
    rob_tertile = grouping_mean("robustness", "tertile")

    bools = {
        "data_inputs_available": True,
        "execution_replay_available": not calendar_returns.empty and cost_contract == "matched",
        "validation_evaluable_primary_local_decision_cell_count": len(validation_cells) >= int(gates["validation_evaluable_primary_local_decision_cell_count_min"]),
        "robustness_evaluable_primary_local_decision_cell_count": len(robustness_cells) >= int(gates["robustness_evaluable_primary_local_decision_cell_count_min"]),
        "validation_primary_local_decision_mean_positive": cluster_value("validation", "monthly_mean_return") > 0,
        "validation_primary_local_decision_t_stat_positive": cluster_value("validation", "t_stat_monthly_mean_newey_west") > 0,
        "validation_loser_leg_beats_winner_leg": cluster_value("validation", "loser_monthly_mean_return") > cluster_value("validation", "winner_monthly_mean_return"),
        "robustness_primary_local_decision_mean_positive": cluster_value("robustness", "monthly_mean_return") > 0,
        "robustness_primary_local_decision_t_stat_positive": cluster_value("robustness", "t_stat_monthly_mean_newey_west") > 0,
        "robustness_loser_leg_beats_winner_leg": cluster_value("robustness", "loser_monthly_mean_return") > cluster_value("robustness", "winner_monthly_mean_return"),
        "validation_decile_mean_ge_tertile_mean": np.isfinite(val_decile) and np.isfinite(val_tertile) and val_decile >= val_tertile,
        "robustness_decile_mean_ge_tertile_mean": np.isfinite(rob_decile) and np.isfinite(rob_tertile) and rob_decile >= rob_tertile,
        "validation_after_cost_decile_L_minus_W_mean_positive": cluster_value("validation", "after_cost_monthly_mean_return") > 0,
        "robustness_after_cost_decile_L_minus_W_mean_positive": cluster_value("robustness", "after_cost_monthly_mean_return") > 0,
        "validation_loser_long_only_after_cost_mean_positive": cluster_value("validation", "loser_long_only_after_cost_monthly_mean_return") > 0,
        "robustness_loser_long_only_after_cost_mean_positive": cluster_value("robustness", "loser_long_only_after_cost_monthly_mean_return") > 0,
    }
    gate_specs = [
        ("data_inputs_available", bools["data_inputs_available"], True),
        ("execution_replay_available", bools["execution_replay_available"], "cost_contract matched and calendar returns non-empty"),
        ("validation_evaluable_primary_local_decision_cell_count", bools["validation_evaluable_primary_local_decision_cell_count"], gates["validation_evaluable_primary_local_decision_cell_count_min"]),
        ("robustness_evaluable_primary_local_decision_cell_count", bools["robustness_evaluable_primary_local_decision_cell_count"], gates["robustness_evaluable_primary_local_decision_cell_count_min"]),
        ("validation_primary_local_decision_mean_positive", bools["validation_primary_local_decision_mean_positive"], 0),
        ("validation_primary_local_decision_t_stat_positive", bools["validation_primary_local_decision_t_stat_positive"], 0),
        ("validation_loser_leg_beats_winner_leg", bools["validation_loser_leg_beats_winner_leg"], "loser > winner"),
        ("robustness_primary_local_decision_mean_positive", bools["robustness_primary_local_decision_mean_positive"], 0),
        ("robustness_primary_local_decision_t_stat_positive", bools["robustness_primary_local_decision_t_stat_positive"], 0),
        ("robustness_loser_leg_beats_winner_leg", bools["robustness_loser_leg_beats_winner_leg"], "loser > winner"),
        ("validation_decile_mean_ge_tertile_mean", bools["validation_decile_mean_ge_tertile_mean"], "decile >= tertile"),
        ("robustness_decile_mean_ge_tertile_mean", bools["robustness_decile_mean_ge_tertile_mean"], "decile >= tertile"),
        ("validation_after_cost_decile_L_minus_W_mean_positive", bools["validation_after_cost_decile_L_minus_W_mean_positive"], 0),
        ("robustness_after_cost_decile_L_minus_W_mean_positive", bools["robustness_after_cost_decile_L_minus_W_mean_positive"], 0),
        ("validation_loser_long_only_after_cost_mean_positive", bools["validation_loser_long_only_after_cost_mean_positive"], "diagnostic label only"),
        ("robustness_loser_long_only_after_cost_mean_positive", bools["robustness_loser_long_only_after_cost_mean_positive"], "diagnostic label only"),
    ]
    values = {
        "validation_evaluable_primary_local_decision_cell_count": len(validation_cells),
        "robustness_evaluable_primary_local_decision_cell_count": len(robustness_cells),
        "validation_primary_local_decision_mean_positive": cluster_value("validation", "monthly_mean_return"),
        "validation_primary_local_decision_t_stat_positive": cluster_value("validation", "t_stat_monthly_mean_newey_west"),
        "validation_loser_leg_beats_winner_leg": f"{cluster_value('validation', 'loser_monthly_mean_return')} > {cluster_value('validation', 'winner_monthly_mean_return')}",
        "robustness_primary_local_decision_mean_positive": cluster_value("robustness", "monthly_mean_return"),
        "robustness_primary_local_decision_t_stat_positive": cluster_value("robustness", "t_stat_monthly_mean_newey_west"),
        "robustness_loser_leg_beats_winner_leg": f"{cluster_value('robustness', 'loser_monthly_mean_return')} > {cluster_value('robustness', 'winner_monthly_mean_return')}",
        "validation_decile_mean_ge_tertile_mean": f"{val_decile} >= {val_tertile}",
        "robustness_decile_mean_ge_tertile_mean": f"{rob_decile} >= {rob_tertile}",
        "validation_after_cost_decile_L_minus_W_mean_positive": cluster_value("validation", "after_cost_monthly_mean_return"),
        "robustness_after_cost_decile_L_minus_W_mean_positive": cluster_value("robustness", "after_cost_monthly_mean_return"),
        "validation_loser_long_only_after_cost_mean_positive": cluster_value("validation", "loser_long_only_after_cost_monthly_mean_return"),
        "robustness_loser_long_only_after_cost_mean_positive": cluster_value("robustness", "loser_long_only_after_cost_monthly_mean_return"),
        "data_inputs_available": True,
        "execution_replay_available": cost_contract,
    }
    gate_rows = [
        {"gate": name, "passed": bool(passed), "value": values.get(name, passed), "threshold": threshold}
        for name, passed, threshold in gate_specs
    ]
    data_sufficient = bools["validation_evaluable_primary_local_decision_cell_count"] and bools["robustness_evaluable_primary_local_decision_cell_count"]
    validation_ok = bools["validation_primary_local_decision_mean_positive"] and bools["validation_primary_local_decision_t_stat_positive"] and bools["validation_loser_leg_beats_winner_leg"]
    robust_ok = bools["robustness_primary_local_decision_mean_positive"] and bools["robustness_primary_local_decision_t_stat_positive"] and bools["robustness_loser_leg_beats_winner_leg"]
    grouping_ok = bools["validation_decile_mean_ge_tertile_mean"] and bools["robustness_decile_mean_ge_tertile_mean"]
    after_cost_ok = bools["validation_after_cost_decile_L_minus_W_mean_positive"] and bools["robustness_after_cost_decile_L_minus_W_mean_positive"]

    if not bools["data_inputs_available"]:
        decision = "ep6_monthly_contrarian_data_inputs_unavailable"
    elif not bools["execution_replay_available"]:
        decision = "ep6_monthly_contrarian_execution_replay_blocked"
    elif not data_sufficient:
        decision = "ep6_monthly_contrarian_sample_insufficient"
    elif not validation_ok:
        decision = "ep6_monthly_contrarian_validation_not_supported"
    elif not robust_ok:
        decision = "ep6_monthly_contrarian_validation_only_not_robust"
    elif not grouping_ok:
        decision = "ep6_monthly_contrarian_grouping_resolution_not_supported"
    elif not after_cost_ok:
        decision = "ep6_monthly_contrarian_gross_positive_after_cost_not_supported"
    else:
        cell_mixed = bool((primary.loc[primary["split"].isin(["validation", "robustness"]), "monthly_mean_return"] <= 0).any())
        decision = "ep6_monthly_contrarian_positive_diagnostic_only_mixed" if cell_mixed else "ep6_monthly_contrarian_positive_diagnostic_only"

    diagnostics = {
        "cluster_stats": cluster.reset_index().to_dict(orient="records"),
        "cost_contract_status": cost_contract,
        "loser_long_only_after_cost_positive_both_oos": bool(
            bools["validation_loser_long_only_after_cost_mean_positive"] and bools["robustness_loser_long_only_after_cost_mean_positive"]
        ),
        "primary_cell_mixed_signs": bool((primary.loc[primary["split"].isin(["validation", "robustness"]), "monthly_mean_return"] <= 0).any()),
    }
    gates_df = pd.DataFrame(gate_rows)
    gates_df["final_decision"] = decision
    return decision, gates_df, diagnostics


def paper_reference_comparison(decision: str, gate_diagnostics: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "paper_table_or_claim": "Table 2/3 long-horizon contrarian profits",
            "local_mapping": "PIT mcap500 mainboard monthly L-W decile, J in 18..48, K in 1/6/12",
            "supported_locally": "see_gate",
            "local_note": decision,
        },
        {
            "paper_table_or_claim": "Finer grouping improves long-horizon contrarian signal",
            "local_mapping": "decile mean >= tertile mean gate; quintile descriptive",
            "supported_locally": "see_r08_grouping_relative_summary.csv",
            "local_note": "strict decile>=quintile>=tertile is intentionally not required",
        },
        {
            "paper_table_or_claim": "Contrarian profits persist after transaction costs",
            "local_mapping": "30/80 bps combined signed-weight replay over overlapping vintages",
            "supported_locally": "yes" if "positive_diagnostic" in decision else "mixed_or_no",
            "local_note": f"cost_contract={gate_diagnostics.get('cost_contract_status')}",
        },
        {
            "paper_table_or_claim": "Long-short portfolios are investable",
            "local_mapping": "diagnostic only under A-share short-sale constraint",
            "supported_locally": "not_authorized",
            "local_note": "authorized_strategy_requirement=false",
        },
        {
            "paper_table_or_claim": "Full RESSET all-A-share 1997-2012 sample",
            "local_mapping": "local PIT mcap500 mainboard 2017-2026 provider sample",
            "supported_locally": "not_exact_replication",
            "local_note": "sample/universe mismatch is structural",
        },
    ]
    return pd.DataFrame(rows)


def environment_snapshot(paths: Paths) -> dict[str, Any]:
    packages: list[str] = []
    try:
        freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True, timeout=20)
        packages = sorted(line.strip() for line in freeze.splitlines() if line.strip())
    except Exception:  # noqa: BLE001
        packages = []
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "pyyaml_version": getattr(yaml, "__version__", "unknown"),
        "git_commit_or_worktree_status": git_commit_or_status(),
        "package_freeze": packages,
    }
    write_json(payload, paths.manifests_dir / "r08_environment_snapshot.json")
    return payload


def md_table(df: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 20) -> str:
    if df.empty:
        return "_empty_"
    out = df.copy()
    if columns is not None:
        out = out[columns]
    out = out.head(max_rows)
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            if "t_stat" in col or "count" in col or "lag" in col or "threshold" in col:
                out[col] = out[col].map(lambda x: fmt_num(x, 4))
            elif "return" in col or "share" in col:
                out[col] = out[col].map(lambda x: fmt_pct(x, 3))
            else:
                out[col] = out[col].map(lambda x: fmt_num(x, 4))
    return out.to_markdown(index=False)


def build_final_report(
    config: dict[str, Any],
    decision: str,
    gates: pd.DataFrame,
    summary: pd.DataFrame,
    cluster: pd.DataFrame,
    grouping_relative: pd.DataFrame,
    provider_feasibility: pd.DataFrame,
    signal_feasibility: pd.DataFrame,
    state_summary: pd.DataFrame,
    exchange_summary: pd.DataFrame,
    paper_comparison: pd.DataFrame,
) -> str:
    primary = summary.loc[
        summary["grouping"].eq(config["portfolio"]["primary_grouping"])
        & summary["skip_mode"].eq("no_skip")
        & summary["J"].isin(config["signals"]["primary_local_decision_J_values"])
        & summary["K"].isin(config["signals"]["primary_local_decision_K_values"])
    ].copy()
    primary_view = (
        primary.groupby("split", as_index=False)
        .agg(
            cell_count=("J", "count"),
            monthly_mean_return=("monthly_mean_return", "mean"),
            after_cost_monthly_mean_return=("after_cost_monthly_mean_return", "mean"),
            loser_long_only_after_cost_monthly_mean_return=("loser_long_only_after_cost_monthly_mean_return", "mean"),
            t_stat_monthly_mean_newey_west=("t_stat_monthly_mean_newey_west", "mean"),
            min_month_count=("month_count", "min"),
        )
        if not primary.empty
        else pd.DataFrame()
    )
    gate_view = gates[["gate", "passed", "value", "threshold"]].copy()
    lines = [
        "# R08 月度反向策略复现 V0 最终报告",
        "",
        "## 1. 结论",
        "",
        f"`final_decision = {decision}`",
        "",
        "`authorized_strategy_requirement = false`",
        "",
        "本实现是 Shi/Jiang/Zhou (2015) 月度反向策略在本地 PIT mcap500 mainboard/Qlib provider 上的可执行代理复现，不是 RESSET 1997-2012 全 A 股样本的精确复刻。主检验使用 `first_holding_month_fixed_vintage_pool`，validation/robustness 只纳入 first holding month 落在对应 split 内且完整 K 月标签可得的 vintage。",
        "",
        "## 2. 主决策簇",
        "",
        md_table(
            primary_view,
            [
                "split",
                "cell_count",
                "monthly_mean_return",
                "after_cost_monthly_mean_return",
                "loser_long_only_after_cost_monthly_mean_return",
                "t_stat_monthly_mean_newey_west",
                "min_month_count",
            ],
        ),
        "",
        "Cluster calendar aggregation:",
        "",
        md_table(
            cluster,
            [
                "split",
                "month_count",
                "monthly_mean_return",
                "after_cost_monthly_mean_return",
                "loser_monthly_mean_return",
                "winner_monthly_mean_return",
                "loser_long_only_after_cost_monthly_mean_return",
                "t_stat_monthly_mean_newey_west",
            ],
        ),
        "",
        "## 3. Gate Replay",
        "",
        gate_view.to_markdown(index=False) if not gate_view.empty else "_empty_",
        "",
        "## 4. 数据可评估性",
        "",
        "Provider end feasibility by K:",
        "",
        md_table(provider_feasibility.loc[provider_feasibility["split"].isin(["validation", "robustness"])], max_rows=30),
        "",
        "Signal history feasibility by J/K (primary grouping/no-skip):",
        "",
        md_table(
            signal_feasibility.loc[signal_feasibility["split"].isin(["validation", "robustness"])],
            [
                "split",
                "J",
                "K",
                "evaluable_first_holding_month_count",
                "candidate_first_holding_month_count",
                "min_signal_eligible_instrument_count",
                "min_intermediate_month_coverage_share",
                "primary_local_decision_cell",
            ],
            max_rows=40,
        ),
        "",
        "## 5. 分组、状态与交易所诊断",
        "",
        "Grouping resolution:",
        "",
        md_table(
            grouping_relative.loc[grouping_relative["primary_local_decision_cell"].astype(bool)]
            if not grouping_relative.empty
            else grouping_relative,
            [
                "split",
                "J",
                "K",
                "decile_monthly_mean_return",
                "quintile_monthly_mean_return",
                "tertile_monthly_mean_return",
                "decile_ge_tertile",
            ],
            max_rows=30,
        ),
        "",
        "Market state summary:",
        "",
        md_table(state_summary, max_rows=30),
        "",
        "Exchange conditional summary:",
        "",
        md_table(exchange_summary, max_rows=20),
        "",
        "## 6. Paper Reference Mapping",
        "",
        paper_comparison.to_markdown(index=False) if not paper_comparison.empty else "_empty_",
        "",
        "## 7. 实现边界",
        "",
        f"- provider: `{config['data_sources']['qlib_provider_uri']}`",
        f"- PIT universe: `{config['data_sources']['pit_universe_path']}`",
        f"- provider end: `{config['data_sources']['provider_load_end_date']}`",
        f"- ranking denominator: `close(M_t) / close(M_t-J) - 1`; denominator month may predate PIT membership if provider price exists, otherwise instrument-month is blocked.",
        f"- intermediate close coverage: `ceil(J * {config['signals']['min_intermediate_monthly_close_share']})`, capped by available intermediate month count.",
        f"- turnover policy: combined signed stock weights are averaged across active vintages; final active month includes terminal settlement turnover.",
        f"- cost contract: buy `{config['execution']['buy_cost_bps']}` bps, sell `{config['execution']['sell_cost_bps']}` bps, round trip `{config['execution']['round_trip_cost_bps']}` bps.",
        "",
    ]
    return "\n".join(lines)


def write_monthly_stock_returns(monthly_ret: pd.DataFrame, path: Path) -> str:
    frame = monthly_ret.copy()
    frame.index = frame.index.astype(str)
    tall = frame.reset_index(names="calendar_month").melt(id_vars="calendar_month", var_name="instrument", value_name="monthly_return")
    return write_parquet_or_csv(tall.dropna(), path)


def save_outputs_and_manifest(config: dict[str, Any], paths: Paths, report_path: Path, env: dict[str, Any], decision: str, artifact_formats: dict[str, str]) -> None:
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requirement_id": config["requirement_id"],
        "requirement_path": config["requirement_path"],
        "git_commit_or_worktree_status": git_commit_or_status(),
        "python_version": sys.version,
        "qlib_provider_path": config["data_sources"]["qlib_provider_uri"],
        "universe_path": config["data_sources"]["pit_universe_path"],
        "calendar_path": config["data_sources"]["trading_calendar_path"],
        "provider_load_end_date": config["data_sources"]["provider_load_end_date"],
        "price_adjustment_mode": config["price_adjustment"]["mode"],
        "do_not_reapply_factor_day_bin_to_ohlc": config["price_adjustment"]["do_not_reapply_factor_day_bin_to_ohlc"],
        "J_values": config["signals"]["J_values"],
        "K_values": config["signals"]["K_values"],
        "primary_local_decision_J_values": config["signals"]["primary_local_decision_J_values"],
        "primary_local_decision_K_values": config["signals"]["primary_local_decision_K_values"],
        "grouping_methods": config["portfolio"]["grouping_methods"],
        "cost_assumptions": config["execution"],
        "overlapping_vintage_accounting_policy": "combined_weight_i_h = active_vintage_count^-1 * sum_active signed_leg_weight_i; entry/exit differences are turnover; final active month includes settlement to zero",
        "split_boundaries": config["sample_split"],
        "final_decision": decision,
        "authorized_strategy_requirement": False,
        "environment_snapshot_file": rel(paths.manifests_dir / "r08_environment_snapshot.json"),
        "package_count": len(env.get("package_freeze", [])),
        "report_file": rel(report_path),
        "report_sha256": file_hash(report_path) if report_path.exists() else "",
        "artifact_formats": artifact_formats,
    }
    write_json(manifest, paths.manifests_dir / "r08_run_manifest.json")


def main() -> None:
    args = parse_args()
    config, paths = load_config(args.config)
    reset_output_dirs(paths)
    print("loading monthly PIT/Qlib inputs")
    month_ends, close_m, volume_m, money_m, monthly_ret, pit, pit_month_end, inst_map, members_by_period = build_monthly_inputs(config)
    shutil.copy2(paths.config_path, paths.configs_dir / Path(paths.config_path).name)

    artifact_formats: dict[str, str] = {}
    write_csv(build_calendar_artifact(month_ends, members_by_period), paths.calendar_dir / "r08_monthly_calendar.csv")
    artifact_formats["r08_monthly_stock_returns"] = write_monthly_stock_returns(monthly_ret, paths.calendar_dir / "r08_monthly_stock_returns.parquet")
    write_csv(availability_manifest(), paths.manifests_dir / "r08_input_availability_manifest.csv")
    write_csv(listing_age_audit(pit, config), paths.manifests_dir / "r08_pit_listing_age_ipo_audit.csv")
    write_csv(provider_end_feasibility(month_ends, config), paths.manifests_dir / "r08_provider_end_feasibility_by_K.csv")

    print("building rank signals and vintage definitions")
    vintages, label_df, bucket_df, rank_df = build_vintages(config, month_ends, close_m, volume_m, money_m, members_by_period)
    write_csv(label_df, paths.calendar_dir / "r08_signal_eligibility_audit.csv")
    write_csv(signal_history_feasibility(label_df, config), paths.manifests_dir / "r08_signal_history_feasibility_by_JK.csv")
    artifact_formats["r08_rank_return_panel"] = write_parquet_or_csv(rank_df, paths.signals_dir / "r08_rank_return_panel.parquet")
    artifact_formats["r08_bucket_assignment_panel"] = write_parquet_or_csv(bucket_df, paths.signals_dir / "r08_bucket_assignment_panel.parquet")

    print("replaying vintage and calendar-time returns")
    vintage_holding, vintage_monthly = compute_vintage_returns(vintages, monthly_ret, inst_map, config)
    write_csv(vintage_holding, paths.returns_dir / "r08_vintage_holding_returns.csv")
    write_csv(vintage_monthly, paths.returns_dir / "r08_vintage_monthly_returns.csv")
    write_csv(label_df, paths.returns_dir / "r08_portfolio_month_label_status.csv")
    calendar_returns, after_cost_returns = compute_calendar_returns(vintages, vintage_monthly, config)
    write_csv(calendar_returns, paths.returns_dir / "r08_calendar_time_portfolio_returns.csv")
    write_csv(after_cost_returns, paths.returns_dir / "r08_after_cost_returns.csv")

    print("summarizing and evaluating gates")
    summary = summarize_calendar_returns(calendar_returns, config)
    for grouping in ["decile", "quintile", "tertile"]:
        write_csv(summary.loc[summary["grouping"].eq(grouping)].copy(), paths.reports_dir / f"r08_jk_summary_{grouping}.csv")
    grouping_relative = grouping_relative_summary(summary, config)
    write_csv(grouping_relative, paths.reports_dir / "r08_grouping_relative_summary.csv")
    write_csv(summary.loc[summary["skip_mode"].eq("skip1")].copy(), paths.reports_dir / "r08_skip1_summary.csv")
    write_csv(loser_winner_leg_summary(summary), paths.reports_dir / "r08_loser_winner_leg_summary.csv")
    state_summary, state_thresholds = build_state_reports(calendar_returns, config, month_ends, load_calendar(topic_path(config["data_sources"]["trading_calendar_path"])))
    write_csv(state_summary, paths.reports_dir / "r08_state_conditional_summary.csv")
    write_csv(state_thresholds, paths.reports_dir / "r08_state_threshold_bootstrap_ci.csv")
    exchange_summary = build_exchange_summary(vintage_monthly, config)
    write_csv(exchange_summary, paths.reports_dir / "r08_exchange_conditional_summary.csv")
    cluster = cluster_stats(calendar_returns, config)
    write_csv(cluster, paths.reports_dir / "r08_primary_cluster_summary.csv")

    cost_contract = cost_contract_status(config)
    decision, gates, gate_diagnostics = determine_gate_decision(config, summary, calendar_returns, grouping_relative, cost_contract)
    paper = paper_reference_comparison(decision, gate_diagnostics)
    write_csv(paper, paths.reports_dir / "r08_paper_reference_comparison.csv")
    write_csv(gates, paths.reports_dir / "r08_gate_decision_summary.csv")
    validation_manifest = {
        "validation_status": "passed",
        "requirement_id": config["requirement_id"],
        "final_decision": decision,
        "authorized_strategy_requirement": False,
        "gate_results": gates.to_dict(orient="records"),
        "gate_diagnostics": gate_diagnostics,
        "cost_contract_status": cost_contract,
        "artifact_contract": "all required R08 csv/json/markdown artifacts generated",
    }
    write_json(validation_manifest, paths.validation_dir / "r08_validation_manifest.json")

    env = environment_snapshot(paths)
    report = build_final_report(
        config,
        decision,
        gates,
        summary,
        cluster,
        grouping_relative,
        pd.read_csv(paths.manifests_dir / "r08_provider_end_feasibility_by_K.csv"),
        pd.read_csv(paths.manifests_dir / "r08_signal_history_feasibility_by_JK.csv"),
        state_summary,
        exchange_summary,
        paper,
    )
    report_path = paths.reports_dir / "r08_final_report.md"
    report_path.write_text(report, encoding="utf-8")
    save_outputs_and_manifest(config, paths, report_path, env, decision, artifact_formats)
    print(f"final_decision={decision}")
    print(f"output_root={rel(paths.output_root)}")


if __name__ == "__main__":
    main()

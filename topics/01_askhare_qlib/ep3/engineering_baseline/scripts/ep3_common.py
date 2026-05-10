#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
TOPIC_DIR = BASE_DIR.parent.parent
DEFAULT_CONFIG = BASE_DIR / "config.yaml"
FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}

CACHE_ARTIFACTS = {
    "ep3_winner_label_panel.parquet",
    "ep3_candidate_anchor_panel.parquet",
    "ep3_matched_baseline_panel.parquet",
}
MANIFEST_ARTIFACTS = {"ep3_engineering_baseline_manifest.json"}
REQUIRED_REPORTS = [
    "ep3_input_authority.csv",
    "ep3_pit_coverage_audit.csv",
    "ep3_winner_lifecycle_profile.csv",
    "ep3_winner_cross_year_audit.csv",
    "ep3_anchor_window_freeze.csv",
    "ep3_observable_anchor_dictionary.csv",
    "ep3_matched_control_bucket_freeze.csv",
    "ep3_anchor_trigger_budget_audit.csv",
    "ep3_anchor_vs_matched_baseline.csv",
    "ep3_failure_lookalike_audit.csv",
    "ep3_instrument_year_lift_audit.csv",
    "ep3_regime_stability_audit.csv",
    "ep3_sensitivity_horizon_audit.csv",
    "ep3_preliminary_anchor_leads.csv",
    "ep3_gate_audit.csv",
    "ep3_discussion_report.md",
    "ep3_stage_order_audit.csv",
]
REQUIRED_ARTIFACTS = [
    "ep3_engineering_baseline_manifest.json",
    "ep3_winner_label_panel.parquet",
    "ep3_candidate_anchor_panel.parquet",
    "ep3_matched_baseline_panel.parquet",
    *REQUIRED_REPORTS,
    "config.yaml",
]
PRIMARY_FAMILIES = {"pullback_hold_restrengthen", "second_breakout"}


class EP3Error(RuntimeError):
    pass


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def load_config(path: str | Path) -> tuple[dict[str, Any], Paths]:
    config_path = topic_path(path)
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    output_root = topic_path(config["output_root"])
    paths = Paths(
        config_path=config_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [paths.cache_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def artifact_path(paths: Paths, name: str) -> Path:
    if name == "config.yaml":
        return paths.config_path
    if name in CACHE_ARTIFACTS:
        return paths.cache_dir / name
    if name in MANIFEST_ARTIFACTS:
        return paths.manifests_dir / name
    return paths.reports_dir / name


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(str(child.relative_to(path)).encode("utf-8"))
            digest.update(child.read_bytes())
    else:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def canonical_hash(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: Any, length: int = 12) -> str:
    digest = hashlib.sha256("|".join("" if pd.isna(x) else str(x) for x in parts).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
    except Exception:
        return ""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def split_for_date(config: dict[str, Any], value: Any) -> str:
    date = as_date(value)
    split = config["split"]
    if as_date(split["train_start"]) <= date <= as_date(split["train_end"]):
        return "train"
    if as_date(split["validation_start"]) <= date <= as_date(split["validation_end"]):
        return "validation"
    if as_date(split["robustness_start"]) <= date <= as_date(split["robustness_end"]):
        return "robustness"
    return "out_of_scope"


def split_end(config: dict[str, Any], split_name: str) -> pd.Timestamp | pd.NaT:
    mapping = {
        "train": "train_end",
        "validation": "validation_end",
        "robustness": "robustness_end",
    }
    key = mapping.get(split_name)
    return as_date(config["split"][key]) if key else pd.NaT


def load_calendar(config: dict[str, Any]) -> pd.DatetimeIndex:
    path = topic_path(config["data_sources"]["trading_calendar_path"])
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values).normalize(), name="date")


def next_trading_day(calendar: pd.DatetimeIndex, date: Any) -> pd.Timestamp | pd.NaT:
    pos = calendar.searchsorted(as_date(date), side="right")
    if pos >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[pos])


def add_trading_days(calendar: pd.DatetimeIndex, date: Any, days: int) -> pd.Timestamp | pd.NaT:
    pos = calendar.searchsorted(as_date(date), side="left")
    target = pos + int(days)
    if pos >= len(calendar) or target >= len(calendar) or target < 0:
        return pd.NaT
    return pd.Timestamp(calendar[target])


def trading_day_distance(calendar: pd.DatetimeIndex, start: Any, end: Any) -> int | None:
    if pd.isna(start) or pd.isna(end):
        return None
    start_pos = calendar.searchsorted(as_date(start), side="left")
    end_pos = calendar.searchsorted(as_date(end), side="left")
    if start_pos >= len(calendar) or end_pos >= len(calendar):
        return None
    return int(end_pos - start_pos)


def bps(value: float) -> float:
    return float(value) / 10000.0


def cost_rates(config: dict[str, Any]) -> dict[str, float]:
    cost = config["cost_model"]
    return {
        "buy_total": bps(cost["derived_buy_cost_bps"]),
        "sell_total": bps(cost["derived_sell_cost_bps"]),
    }


def read_qlib_instruments(config: dict[str, Any]) -> list[str]:
    path = topic_path(config["data_sources"]["pit_qlib_instrument_universe_path"])
    df = pd.read_csv(path)
    instruments = sorted(df["instrument"].astype(str).str.upper().unique())
    if not instruments:
        raise EP3Error(f"empty qlib instrument map: {relpath(path)}")
    return instruments


def load_provider_panel(config: dict[str, Any]) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    provider_uri = topic_path(config["data_sources"]["qlib_provider_uri"])
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    fields = ["$open", "$high", "$low", "$close", "$volume", "$money", "$factor"]
    frame = D.features(
        instruments=read_qlib_instruments(config),
        fields=fields,
        start_time=config["input_contract"]["provider_load_start_date"],
        end_time=config["input_contract"]["provider_load_end_date"],
        freq="day",
    )
    if frame.empty:
        raise EP3Error("Qlib provider returned no rows")
    panel = frame.rename(columns=FIELD_RENAME).reset_index()
    panel["date"] = pd.to_datetime(panel["datetime"]).dt.normalize()
    panel["instrument"] = panel["instrument"].astype(str).str.upper()
    panel = panel.drop(columns=["datetime"])
    for field in FIELD_RENAME.values():
        if field not in panel:
            panel[field] = np.nan
    return panel.sort_values(["instrument", "date"]).reset_index(drop=True)


def load_universe(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["data_sources"]["pit_universe_path"])
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    return df


def load_industry(config: dict[str, Any]) -> pd.DataFrame:
    path = topic_path(config["data_sources"]["pit_industry_path"])
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    return df.sort_values(["instrument", "date"])


def load_market_panel(config: dict[str, Any]) -> pd.DataFrame:
    provider = load_provider_panel(config)
    universe = load_universe(config)
    universe_key = universe[["date", "instrument"]].drop_duplicates()
    provider = provider.merge(universe_key.assign(universe_member_asof_signal_date=True), on=["date", "instrument"], how="left")
    provider["universe_member_asof_signal_date"] = provider["universe_member_asof_signal_date"].fillna(False).astype(bool)
    industry = load_industry(config)
    industry_cols = ["date", "instrument", "industry_target_key", "industry_name"]
    provider = provider.merge(industry[industry_cols].drop_duplicates(["date", "instrument"]), on=["date", "instrument"], how="left")
    provider["industry_target_key"] = provider["industry_target_key"].fillna("UNKNOWN")
    provider["industry_name"] = provider["industry_name"].fillna("UNKNOWN")
    provider["industry_asof_signal_date"] = provider["industry_name"]
    return add_derived_features(provider.sort_values(["instrument", "date"]).reset_index(drop=True), config)


def add_derived_features(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rules = config["observable_reference_rules"]
    df = panel.sort_values(["instrument", "date"]).reset_index(drop=True).copy()
    group = df.groupby("instrument", group_keys=False)
    df["prev_close"] = group["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["prev_close"]).abs()
    tr3 = (df["low"] - df["prev_close"]).abs()
    df["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_n = int(rules["atr_lookback_days"])
    money_n = int(rules["money_ma_lookback_days"])
    accel_n = int(rules["acceleration_lookback_days"])
    df["atr20"] = group["true_range"].transform(lambda s: s.shift(1).rolling(atr_n, min_periods=atr_n).mean())
    df["atr20_pct"] = df["atr20"] / df["prev_close"]
    df["money_ma20"] = group["money"].transform(lambda s: s.shift(1).rolling(money_n, min_periods=money_n).mean())
    df["ret_60d"] = group["close"].transform(lambda s: s / s.shift(accel_n) - 1.0)
    df["vol20"] = group["close"].transform(lambda s: s.pct_change().shift(1).rolling(20, min_periods=20).std())
    df["rolling_max_close_60_prev"] = group["close"].transform(lambda s: s.shift(1).rolling(accel_n, min_periods=accel_n).max())
    df["launch_like_acceleration_raw"] = (
        (df["ret_60d"] >= float(rules["acceleration_min_return"]))
        & (df["close"] >= df["rolling_max_close_60_prev"])
        & (df["money"] >= float(rules["money_multiple_min"]) * df["money_ma20"])
        & (df["money"] >= float(rules["money_min_cny"]))
        & df["universe_member_asof_signal_date"].astype(bool)
    )
    return df


def price_lookup(panel: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], dict[str, Any]]:
    cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "factor",
        "industry_target_key",
        "industry_name",
        "industry_asof_signal_date",
        "universe_member_asof_signal_date",
        "atr20",
        "money_ma20",
        "ret_60d",
        "vol20",
        "launch_like_acceleration_raw",
    ]
    out: dict[tuple[str, pd.Timestamp], dict[str, Any]] = {}
    for row in panel[["instrument", "date", *[c for c in cols if c in panel]]].itertuples(index=False):
        data = row._asdict()
        inst = str(data.pop("instrument")).upper()
        date = as_date(data.pop("date"))
        out[(inst, date)] = data
    return out


def universe_membership_set(config: dict[str, Any]) -> set[tuple[str, pd.Timestamp]]:
    universe = load_universe(config)
    return set(zip(universe["instrument"].astype(str).str.upper(), pd.to_datetime(universe["date"]).dt.normalize()))


def execution_status(
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    instrument: str,
    signal_date: pd.Timestamp | pd.NaT,
    execution_date: pd.Timestamp | pd.NaT,
    limit_pct: float,
) -> dict[str, Any]:
    if pd.isna(execution_date):
        return _blocked_status("missing_calendar_next_day", np.nan)
    info = lookup.get((instrument, as_date(execution_date)))
    prev = lookup.get((instrument, as_date(signal_date))) if not pd.isna(signal_date) else None
    if info is None:
        return _blocked_status("missing_price_row", np.nan)
    open_price = float(info.get("open", np.nan))
    volume = float(info.get("volume", np.nan))
    money = float(info.get("money", np.nan))
    buy_reason = ""
    sell_reason = ""
    if not np.isfinite(open_price):
        buy_reason = sell_reason = "missing_open"
    elif not np.isfinite(volume) or volume <= 0:
        buy_reason = sell_reason = "zero_volume"
    elif not np.isfinite(money) or money <= 0:
        buy_reason = sell_reason = "zero_money"
    elif prev is not None:
        prev_close = float(prev.get("close", np.nan))
        if np.isfinite(prev_close) and prev_close > 0:
            if open_price >= prev_close * (1.0 + limit_pct):
                buy_reason = "limit_up_inferred"
            if open_price <= prev_close * (1.0 - limit_pct):
                sell_reason = "limit_down_inferred"
    if not buy_reason and (instrument, as_date(execution_date)) not in universe_set:
        buy_reason = "not_universe_member"
    buy_ok = not bool(buy_reason)
    sell_ok = not bool(sell_reason)
    summary = ""
    if buy_reason == sell_reason:
        summary = buy_reason
    elif buy_reason or sell_reason:
        summary = "direction_specific_block"
    return {
        "execution_price_reference": open_price,
        "is_buy_executable_next_open": buy_ok,
        "is_sell_executable_next_open": sell_ok,
        "blocked_buy_reason": buy_reason,
        "blocked_sell_reason": sell_reason,
        "blocked_execution_reason": summary,
        "is_executable_next_open": buy_ok and sell_ok,
    }


def _blocked_status(reason: str, price: float) -> dict[str, Any]:
    return {
        "execution_price_reference": price,
        "is_buy_executable_next_open": False,
        "is_sell_executable_next_open": False,
        "blocked_buy_reason": reason,
        "blocked_sell_reason": reason,
        "blocked_execution_reason": reason,
        "is_executable_next_open": False,
    }


def mark_launch_executable(config: dict[str, Any], panel: pd.DataFrame) -> pd.DataFrame:
    calendar = load_calendar(config)
    limit_pct = float(config["execution"]["limit_inference_pct"]["mainboard_default"])
    df = panel.copy()
    next_map = {pd.Timestamp(calendar[i]): pd.Timestamp(calendar[i + 1]) for i in range(len(calendar) - 1)}
    df["execution_date"] = df["date"].map(next_map)
    next_panel = df[
        [
            "instrument",
            "date",
            "open",
            "volume",
            "money",
            "universe_member_asof_signal_date",
        ]
    ].rename(
        columns={
            "date": "execution_date",
            "open": "execution_open",
            "volume": "execution_volume",
            "money": "execution_money",
            "universe_member_asof_signal_date": "execution_universe_member",
        }
    )
    df = df.merge(next_panel, on=["instrument", "execution_date"], how="left")
    df["entry_price_reference"] = df["execution_open"]
    missing_calendar = df["execution_date"].isna()
    missing_price = df["execution_open"].isna()
    zero_volume = df["execution_volume"].fillna(0) <= 0
    zero_money = df["execution_money"].fillna(0) <= 0
    limit_up = df["execution_open"] >= df["close"] * (1.0 + limit_pct)
    not_member = ~df["execution_universe_member"].fillna(False).astype(bool)
    reason = np.select(
        [missing_calendar, missing_price, zero_volume, zero_money, limit_up, not_member],
        ["missing_calendar_next_day", "missing_open", "zero_volume", "zero_money", "limit_up_inferred", "not_universe_member"],
        default="",
    )
    df["blocked_buy_reason"] = reason
    df["is_buy_executable_next_open"] = df["blocked_buy_reason"].eq("")
    df["launch_like_acceleration"] = df["launch_like_acceleration_raw"].astype(bool) & df["is_buy_executable_next_open"].astype(bool)
    df = df.drop(columns=["execution_open", "execution_volume", "execution_money", "execution_universe_member"])
    return df


def build_input_audits(config: dict[str, Any], paths: Paths, panel: pd.DataFrame) -> None:
    rows = []
    for group, values in [
        ("data_sources", config["data_sources"]),
        ("frozen_ep2_inputs", config["frozen_ep2_inputs"]),
    ]:
        for key, value in values.items():
            path = topic_path(value)
            rows.append(
                {
                    "input_group": group,
                    "input_key": key,
                    "path": relpath(path),
                    "exists": path.exists(),
                    "content_hash": file_hash(path),
                    "role": "canonical_input" if group == "data_sources" else "frozen_ep2_reference",
                }
            )
    write_csv(pd.DataFrame(rows), paths.reports_dir / "ep3_input_authority.csv")

    split = config["split"]
    in_scope = panel.loc[(panel["date"] >= as_date(split["train_start"])) & (panel["date"] <= as_date(split["robustness_end"]))]
    coverage = (
        in_scope.groupby(in_scope["date"].dt.year)
        .agg(
            provider_rows=("instrument", "size"),
            pit_universe_rows=("universe_member_asof_signal_date", "sum"),
            instrument_count=("instrument", "nunique"),
            missing_close_rows=("close", lambda s: int(s.isna().sum())),
            missing_money_rows=("money", lambda s: int(s.isna().sum())),
        )
        .reset_index()
        .rename(columns={"date": "year"})
    )
    write_csv(coverage, paths.reports_dir / "ep3_pit_coverage_audit.csv")


def build_winner_label_panel(config: dict[str, Any], paths: Paths, panel: pd.DataFrame) -> pd.DataFrame:
    split = config["split"]
    calendar = load_calendar(config)
    start = as_date(split["train_start"])
    end = as_date(split["robustness_end"])
    base = panel.loc[(panel["date"] >= start) & (panel["date"] <= end) & panel["universe_member_asof_signal_date"].astype(bool)].copy()
    base = base.sort_values(["instrument", "date"]).reset_index(drop=True)
    provider_max = panel["date"].max()
    input_hash = canonical_hash(
        {
            "provider_uri": config["data_sources"]["qlib_provider_uri"],
            "pit_universe": file_hash(topic_path(config["data_sources"]["pit_universe_path"])),
            "provider_max_date": provider_max.date().isoformat(),
        }
    )
    rows = []
    for instrument, group in base.groupby("instrument", sort=True):
        group = group.sort_values("date").reset_index(drop=True)
        high = group["high"].to_numpy(dtype=float)
        close = group["close"].to_numpy(dtype=float)
        dates = pd.to_datetime(group["date"]).dt.normalize().to_numpy()
        n = len(group)
        high_series = pd.Series(high)
        future_high_120 = high_series.shift(-1).iloc[::-1].rolling(120, min_periods=120).max().iloc[::-1].to_numpy()
        future_high_240 = high_series.shift(-1).iloc[::-1].rolling(240, min_periods=240).max().iloc[::-1].to_numpy()
        max120 = np.where(np.isfinite(close) & (close > 0), future_high_120 / close - 1.0, np.nan)
        max240 = np.where(np.isfinite(close) & (close > 0), future_high_240 / close - 1.0, np.nan)
        first50 = np.full(n, "", dtype=object)
        first100 = np.full(n, "", dtype=object)
        complete120 = np.isfinite(future_high_120)
        complete240 = np.isfinite(future_high_240)
        for i in np.flatnonzero(max120 >= 0.50):
            window = high[i + 1 : i + 121]
            hits = np.flatnonzero(window / close[i] - 1.0 >= 0.50)
            if len(hits):
                first50[i] = pd.Timestamp(dates[i + 1 + int(hits[0])]).date().isoformat()
        for i in np.flatnonzero(max240 >= 1.00):
            window = high[i + 1 : i + 241]
            hits = np.flatnonzero(window / close[i] - 1.0 >= 1.00)
            if len(hits):
                first100[i] = pd.Timestamp(dates[i + 1 + int(hits[0])]).date().isoformat()
        out = group[["date", "instrument"]].copy()
        out["split"] = out["date"].map(lambda d: split_for_date(config, d))
        out["winner_50h120"] = max120 >= 0.50
        out["first_50pct_target_date"] = first50
        out["winner_100h240"] = max240 >= 1.00
        out["first_100pct_target_date"] = first100
        out["max_forward_return_120"] = max120
        out["max_forward_return_240"] = max240
        out["label_horizon_complete"] = complete120
        out["label_price_adjustment_mode"] = config["input_contract"]["label_price_adjustment_mode"]
        out["label_input_hash"] = input_hash
        out["horizon_end_date_120"] = out["date"].map(lambda d: add_trading_days(calendar, d, 120))
        out["horizon_contained_in_split"] = (
            (out["split"].eq("train") & (out["horizon_end_date_120"] <= as_date(split["train_end"])))
            | (out["split"].eq("validation") & (out["horizon_end_date_120"] <= as_date(split["validation_end"])))
            | (out["split"].eq("robustness") & (out["horizon_end_date_120"] <= as_date(split["robustness_end"])))
        )
        out["eligible_for_primary_gate"] = out["label_horizon_complete"].astype(bool) & out["horizon_contained_in_split"].astype(bool)
        rows.append(out.drop(columns=["horizon_end_date_120"]))
    label_panel = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    write_parquet(label_panel, paths.cache_dir / "ep3_winner_label_panel.parquet")
    cross = []
    for (year, label_id), group in pd.concat(
        [
            label_panel.assign(year=pd.to_datetime(label_panel["date"]).dt.year, label_id="winner_50h120", label_value=label_panel["winner_50h120"]),
            label_panel.assign(year=pd.to_datetime(label_panel["date"]).dt.year, label_id="winner_100h240", label_value=label_panel["winner_100h240"]),
        ],
        ignore_index=True,
    ).groupby(["year", "label_id"], sort=True):
        eligible = group.loc[group["eligible_for_primary_gate"].astype(bool)]
        cross.append(
            {
                "year": int(year),
                "label_id": label_id,
                "eligible_rows": len(eligible),
                "winner_rows": int(eligible["label_value"].sum()) if not eligible.empty else 0,
                "winner_rate": float(eligible["label_value"].mean()) if not eligible.empty else np.nan,
                "unique_winner_instruments": int(eligible.loc[eligible["label_value"].astype(bool), "instrument"].nunique()) if not eligible.empty else 0,
            }
        )
    write_csv(pd.DataFrame(cross), paths.reports_dir / "ep3_winner_cross_year_audit.csv")
    return label_panel


def build_winner_episodes(config: dict[str, Any], label_panel: pd.DataFrame, label_col: str, target_col: str) -> pd.DataFrame:
    eligible = label_panel.loc[label_panel[label_col].astype(bool) & label_panel["eligible_for_primary_gate"].astype(bool)].copy()
    eligible["date"] = pd.to_datetime(eligible["date"]).dt.normalize()
    calendar = load_calendar(config)
    gap = int(config["winner_episode"]["merge_gap_trading_days"])
    rows = []
    label_id = label_col
    for instrument, group in eligible.groupby("instrument", sort=True):
        group = group.sort_values("date")
        current = []
        last_date = pd.NaT
        for row in group.itertuples(index=False):
            date = as_date(row.date)
            distance = trading_day_distance(calendar, last_date, date) if not pd.isna(last_date) else None
            if current and distance is not None and distance > gap:
                rows.append(_winner_episode_row(config, label_id, target_col, instrument, current))
                current = []
            current.append(row)
            last_date = date
        if current:
            rows.append(_winner_episode_row(config, label_id, target_col, instrument, current))
    return pd.DataFrame(rows)


def _winner_episode_row(config: dict[str, Any], label_id: str, target_col: str, instrument: str, rows: list[Any]) -> dict[str, Any]:
    start = min(as_date(r.date) for r in rows)
    end = max(as_date(r.date) for r in rows)
    targets = [as_date(getattr(r, target_col)) for r in rows if str(getattr(r, target_col))]
    first_target = min(targets) if targets else pd.NaT
    split = split_for_date(config, start)
    return {
        "winner_episode_id": stable_id("EP3_WINNER", label_id, instrument, start.date().isoformat(), end.date().isoformat(), "" if pd.isna(first_target) else first_target.date().isoformat()),
        "instrument": instrument,
        "winner_label_id": label_id,
        "episode_start_date": start,
        "episode_end_date": end,
        "first_target_date": first_target,
        "split": split,
        "eligible_for_primary_gate": True,
    }


def _instrument_frame(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {inst: group.sort_values("date").reset_index(drop=True) for inst, group in panel.groupby("instrument", sort=True)}


def _row_at(inst_df: pd.DataFrame, date: pd.Timestamp) -> pd.Series | None:
    matches = inst_df.index[inst_df["date"].eq(as_date(date))]
    if len(matches) == 0:
        return None
    return inst_df.iloc[int(matches[0])]


def _find_first_launch_before(inst_df: pd.DataFrame, calendar: pd.DatetimeIndex, target_date: pd.Timestamp) -> pd.Timestamp | pd.NaT:
    start = add_trading_days(calendar, target_date, -120)
    if pd.isna(start):
        start = inst_df["date"].min()
    mask = (inst_df["date"] >= start) & (inst_df["date"] <= target_date) & inst_df["launch_like_acceleration"].astype(bool)
    candidates = inst_df.loc[mask, "date"]
    if candidates.empty:
        return pd.NaT
    return as_date(candidates.iloc[0])


def build_lifecycle_profile(config: dict[str, Any], paths: Paths, panel: pd.DataFrame, label_panel: pd.DataFrame) -> pd.DataFrame:
    calendar = load_calendar(config)
    by_inst = _instrument_frame(panel)
    episodes = pd.concat(
        [
            build_winner_episodes(config, label_panel, "winner_50h120", "first_50pct_target_date"),
            build_winner_episodes(config, label_panel, "winner_100h240", "first_100pct_target_date"),
        ],
        ignore_index=True,
    )
    rows = []
    full_window = {"frozen_window_low": 1, "frozen_window_high": int(config["anchor_scope"]["anchor_window_max_trading_days"])}
    for ep in episodes.itertuples(index=False):
        inst_df = by_inst.get(str(ep.instrument))
        if inst_df is None or pd.isna(ep.first_target_date):
            continue
        start_anchor = _find_first_launch_before(inst_df, calendar, as_date(ep.first_target_date))
        status = "found" if not pd.isna(start_anchor) else "no_observable_launch_like_acceleration"
        base = {
            "winner_episode_id": ep.winner_episode_id,
            "instrument": ep.instrument,
            "winner_label_id": ep.winner_label_id,
            "split": ep.split,
            "days_to_first_50pct_target": trading_day_distance(calendar, start_anchor, ep.first_target_date) if not pd.isna(start_anchor) else np.nan,
            "days_from_observable_start": 0,
            "stage_extraction_rule_id": "ep3_p0_v1",
            "stage_extraction_rule_hash": canonical_hash(config["observable_reference_rules"]),
            "winner_start_anchor_status": status,
            "eligible_for_primary_gate": bool(ep.eligible_for_primary_gate),
        }
        rows.append(
            {
                **base,
                "lifecycle_stage_id": "first_acceleration",
                "retrospective_stage_date": "" if pd.isna(start_anchor) else start_anchor.date().isoformat(),
                "observable_signal_date": "" if pd.isna(start_anchor) else start_anchor.date().isoformat(),
                "observable_anchor_candidate": False,
                "anchor_family_id": "",
                "anchor_window_measure": np.nan,
            }
        )
        if pd.isna(start_anchor):
            continue
        for family in config["primary_anchor_families"]:
            candidate = _detect_family_candidate(config, inst_df, calendar, start_anchor, full_window, family)
            if candidate is None:
                continue
            measure = trading_day_distance(calendar, start_anchor, candidate["signal_date"])
            rows.append(
                {
                    **base,
                    "lifecycle_stage_id": "confirmation_anchor",
                    "retrospective_stage_date": candidate["signal_date"].date().isoformat(),
                    "observable_signal_date": candidate["signal_date"].date().isoformat(),
                    "observable_anchor_candidate": True,
                    "anchor_family_id": family,
                    "anchor_window_measure": measure,
                    "days_from_observable_start": measure,
                    "days_to_first_50pct_target": trading_day_distance(calendar, candidate["signal_date"], ep.first_target_date),
                }
            )
        failed = _detect_failed_lookalike(config, inst_df, calendar, start_anchor, full_window, "pullback_hold_restrengthen")
        if failed is not None:
            rows.append(
                {
                    **base,
                    "lifecycle_stage_id": "failure_lookalike",
                    "retrospective_stage_date": failed["signal_date"].date().isoformat(),
                    "observable_signal_date": failed["signal_date"].date().isoformat(),
                    "observable_anchor_candidate": False,
                    "anchor_family_id": "failed_lookalike_avoidance",
                    "anchor_window_measure": trading_day_distance(calendar, start_anchor, failed["signal_date"]),
                }
            )
    profile = pd.DataFrame(rows, columns=lifecycle_columns())
    write_csv(profile, paths.reports_dir / "ep3_winner_lifecycle_profile.csv")
    return profile


def lifecycle_columns() -> list[str]:
    return [
        "winner_episode_id",
        "instrument",
        "winner_label_id",
        "split",
        "lifecycle_stage_id",
        "retrospective_stage_date",
        "observable_signal_date",
        "observable_anchor_candidate",
        "days_to_first_50pct_target",
        "days_from_observable_start",
        "stage_extraction_rule_id",
        "stage_extraction_rule_hash",
        "winner_start_anchor_status",
        "anchor_family_id",
        "anchor_window_measure",
        "eligible_for_primary_gate",
    ]


def freeze_anchor_windows(config: dict[str, Any], paths: Paths, profile: pd.DataFrame) -> pd.DataFrame:
    rows = []
    low_q = float(config["anchor_scope"]["anchor_window_quantile_low"])
    high_q = float(config["anchor_scope"]["anchor_window_quantile_high"])
    min_w = int(config["anchor_scope"]["anchor_window_min_trading_days"])
    max_w = int(config["anchor_scope"]["anchor_window_max_trading_days"])
    measure_names = {
        "pullback_hold_restrengthen": "trading_days_between(winner_start_anchor, first_observable_pullback_low_date)",
        "second_breakout": "trading_days_between(winner_start_anchor, second_breakout_signal_date)",
    }
    for family in config["primary_anchor_families"]:
        sample = profile.loc[
            profile["split"].eq("train")
            & profile["winner_label_id"].eq("winner_50h120")
            & profile["observable_anchor_candidate"].astype(bool)
            & profile["winner_start_anchor_status"].eq("found")
            & profile["anchor_family_id"].eq(family)
            & profile["eligible_for_primary_gate"].astype(bool)
        ]["anchor_window_measure"].dropna()
        if sample.empty:
            row = {
                "anchor_family_id": family,
                "anchor_window_measure": measure_names[family],
                "train_observation_count": 0,
                "raw_quantile_low": np.nan,
                "raw_quantile_high": np.nan,
                "train_median_anchor_window_days": np.nan,
                "frozen_window_low": np.nan,
                "frozen_window_high": np.nan,
                "window_derivation_status": "failed_lifecycle_window_derivation",
            }
        else:
            raw_low = float(sample.quantile(low_q))
            raw_high = float(sample.quantile(high_q))
            frozen_low = int(max(min_w, min(max_w, math.floor(raw_low))))
            frozen_high = int(max(min_w, min(max_w, math.ceil(raw_high))))
            if frozen_high < frozen_low:
                frozen_high = frozen_low
            row = {
                "anchor_family_id": family,
                "anchor_window_measure": measure_names[family],
                "train_observation_count": int(len(sample)),
                "raw_quantile_low": raw_low,
                "raw_quantile_high": raw_high,
                "train_median_anchor_window_days": int(round(float(sample.median()))),
                "frozen_window_low": frozen_low,
                "frozen_window_high": frozen_high,
                "window_derivation_status": "derived",
            }
        row["window_hash"] = canonical_hash(row)
        rows.append(row)
    freeze = pd.DataFrame(rows)
    write_csv(freeze, paths.reports_dir / "ep3_anchor_window_freeze.csv")
    return freeze


def freeze_anchor_dictionary(config: dict[str, Any], paths: Paths, window_freeze: pd.DataFrame) -> pd.DataFrame:
    rules = config["observable_reference_rules"]
    rows = [
        {
            "formula_id": "prev_close",
            "anchor_family_id": "daily_derived",
            "formula_text": "prev_close[t] = close[t - 1 trading day]",
            "lookback_days": 1,
            "asof_rule": "uses data <= signal_date",
            "parameter_hash": canonical_hash({"formula": "prev_close"}),
        },
        {
            "formula_id": "atr20",
            "anchor_family_id": "daily_derived",
            "formula_text": "atr20[t] = mean(true_range, 20 trading days ending t - 1)",
            "lookback_days": int(rules["atr_lookback_days"]),
            "asof_rule": "rolling reference ends at signal_date - 1",
            "parameter_hash": canonical_hash({"atr_lookback_days": rules["atr_lookback_days"]}),
        },
        {
            "formula_id": "money_ma20",
            "anchor_family_id": "daily_derived",
            "formula_text": "money_ma20[t] = mean(money, 20 trading days ending t - 1)",
            "lookback_days": int(rules["money_ma_lookback_days"]),
            "asof_rule": "rolling reference ends at signal_date - 1",
            "parameter_hash": canonical_hash({"money_ma_lookback_days": rules["money_ma_lookback_days"]}),
        },
        {
            "formula_id": "ret_60d",
            "anchor_family_id": "daily_derived",
            "formula_text": "ret_60d[t] = close[t] / close[t - 60 trading days] - 1",
            "lookback_days": int(rules["acceleration_lookback_days"]),
            "asof_rule": "uses close through signal_date",
            "parameter_hash": canonical_hash({"acceleration_lookback_days": rules["acceleration_lookback_days"]}),
        },
        {
            "formula_id": "vol20",
            "anchor_family_id": "daily_derived",
            "formula_text": "vol20[t] = std(daily close-to-close return, 20 trading days ending t - 1)",
            "lookback_days": 20,
            "asof_rule": "rolling reference ends at signal_date - 1",
            "parameter_hash": canonical_hash({"vol20": 20}),
        },
        {
            "formula_id": "launch_like_acceleration",
            "anchor_family_id": "reference_event",
            "formula_text": "close_60d_return >= 12%, close >= prior 60d max close, money >= 2x money_ma20 and >= 50m, PIT universe, next-open executable",
            "lookback_days": 60,
            "asof_rule": "signal_date close-derived; execution_date open is execution only",
            "parameter_hash": canonical_hash(rules),
        },
    ]
    for family in config["primary_anchor_families"]:
        window = window_freeze.loc[window_freeze["anchor_family_id"].eq(family)].iloc[0].to_dict()
        rows.append(
            {
                "formula_id": family,
                "anchor_family_id": family,
                "formula_text": "P0 primary observable anchor, close-derived signal, next-open execution",
                "lookback_days": int(config["anchor_scope"]["anchor_window_max_trading_days"]),
                "asof_rule": "all signal features <= signal_date; execution_date open forbidden as signal",
                "parameter_hash": canonical_hash({"rules": rules, "window": window}),
                "reference_event_rule": "launch_like_acceleration",
                "entry_execution_rule": "next_open",
                "enabled": True,
                "p0_forward_audit_rows_allowed": True,
            }
        )
    for family in config["deferred_anchor_families"]:
        rows.append(
            {
                "formula_id": family,
                "anchor_family_id": family,
                "formula_text": "deferred family placeholder; dictionary-only in EP3-P0",
                "lookback_days": "",
                "asof_rule": "not implemented in P0",
                "parameter_hash": canonical_hash({"family": family, "status": "deferred"}),
                "reference_event_rule": "",
                "entry_execution_rule": "",
                "enabled": False,
                "p0_forward_audit_rows_allowed": False,
            }
        )
    dictionary = pd.DataFrame(rows)
    write_csv(dictionary, paths.reports_dir / "ep3_observable_anchor_dictionary.csv")
    return dictionary


def freeze_bucket_boundaries(config: dict[str, Any], paths: Paths, panel: pd.DataFrame) -> pd.DataFrame:
    cfg = config["matched_controls"]
    train = panel.loc[
        panel["date"].between(as_date(config["split"]["train_start"]), as_date(config["split"]["train_end"]))
        & panel["universe_member_asof_signal_date"].astype(bool)
    ]
    specs = [
        ("money", "money_bucket", cfg["money_bucket_quantiles"]),
        ("vol20", "realized_volatility_bucket", cfg["realized_volatility_bucket_quantiles"]),
        ("ret_60d", "return_60d_bucket", cfg["return_60d_bucket_quantiles"]),
    ]
    rows = []
    for field, bucket_name, quantiles in specs:
        values = train[field].replace([np.inf, -np.inf], np.nan).dropna()
        cuts = np.unique(np.quantile(values, quantiles)) if not values.empty else np.array([np.nan, np.nan])
        if len(cuts) < 2:
            cuts = np.array([-np.inf, np.inf])
        cuts[0] = -np.inf
        cuts[-1] = np.inf
        for idx in range(len(cuts) - 1):
            row = {
                "bucket_field": field,
                "bucket_name": bucket_name,
                "bucket_index": idx,
                "lower_bound": cuts[idx],
                "upper_bound": cuts[idx + 1],
                "bucket_quantile_source": cfg["bucket_quantile_source"],
                "source_split": "train",
            }
            row["bucket_hash"] = canonical_hash(row)
            rows.append(row)
    freeze = pd.DataFrame(rows)
    write_csv(freeze, paths.reports_dir / "ep3_matched_control_bucket_freeze.csv")
    return freeze


def apply_buckets(panel: pd.DataFrame, bucket_freeze: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    for field, group in bucket_freeze.groupby("bucket_field", sort=False):
        cuts = group.sort_values("bucket_index")[["lower_bound", "upper_bound", "bucket_index"]].to_dict("records")
        df[f"{field}_bucket"] = df[field].map(lambda x: _bucket_index(x, cuts))
    df["matched_control_bucket_id"] = (
        "money="
        + df["money_bucket"].fillna(-1).astype(int).astype(str)
        + "|vol20="
        + df["vol20_bucket"].fillna(-1).astype(int).astype(str)
        + "|ret60="
        + df["ret_60d_bucket"].fillna(-1).astype(int).astype(str)
    )
    return df


def _bucket_index(value: Any, cuts: list[dict[str, Any]]) -> float:
    if value is None:
        return np.nan
    try:
        x = float(value)
    except (TypeError, ValueError):
        return np.nan
    if not np.isfinite(x):
        return np.nan
    for row in cuts:
        if float(row["lower_bound"]) <= x <= float(row["upper_bound"]):
            return float(row["bucket_index"])
    return np.nan


def _detect_family_candidate(config: dict[str, Any], inst_df: pd.DataFrame, calendar: pd.DatetimeIndex, ref_date: pd.Timestamp, window: dict[str, Any], family: str) -> dict[str, Any] | None:
    if family == "pullback_hold_restrengthen":
        return _detect_pullback(config, inst_df, calendar, ref_date, window)
    if family == "second_breakout":
        return _detect_second_breakout(config, inst_df, calendar, ref_date, window)
    return None


def _detect_pullback(config: dict[str, Any], inst_df: pd.DataFrame, calendar: pd.DatetimeIndex, ref_date: pd.Timestamp, window: dict[str, Any]) -> dict[str, Any] | None:
    rules = config["observable_reference_rules"]
    a_row = _row_at(inst_df, ref_date)
    if a_row is None or not bool(a_row.get("launch_like_acceleration", False)):
        return None
    ref_pos = int(a_row.name)
    low_w = int(window["frozen_window_low"])
    high_w = int(window["frozen_window_high"])
    candidates = []
    for p_pos in range(ref_pos + low_w, min(len(inst_df), ref_pos + high_w + 1)):
        p = inst_df.iloc[p_pos]
        drawdown = float(p.low) / float(a_row.close) - 1.0 if np.isfinite(float(a_row.close)) and float(a_row.close) > 0 else np.nan
        if not (drawdown <= -float(rules["pullback_min_drawdown_from_acceleration_close"]) and drawdown >= -float(rules["pullback_max_drawdown_from_acceleration_close"])):
            continue
        if not (float(p.low) >= float(a_row.close) - float(rules["pullback_hold_atr_multiple"]) * float(a_row.atr20)):
            continue
        ref_high = inst_df.iloc[max(0, p_pos - int(rules["restrengthen_high_lookback_days"]) + 1) : p_pos + 1]["high"].max()
        for t_pos in range(p_pos + 1, min(len(inst_df), p_pos + 6)):
            t = inst_df.iloc[t_pos]
            prev = inst_df.iloc[t_pos - 1]
            if (
                float(t.close) >= float(ref_high)
                and float(t.close) > float(prev.close)
                and float(t.money) >= float(t.money_ma20)
                and bool(t.is_buy_executable_next_open)
            ):
                candidates.append({"signal_date": as_date(t.date), "pullback_low_date": as_date(p.date), "reference_acceleration_date": ref_date, "tie_low": float(p.low)})
    if not candidates:
        return None
    candidates = sorted(candidates, key=lambda x: (x["signal_date"], x["tie_low"], x["pullback_low_date"]))
    return candidates[0]


def _detect_second_breakout(config: dict[str, Any], inst_df: pd.DataFrame, calendar: pd.DatetimeIndex, ref_date: pd.Timestamp, window: dict[str, Any]) -> dict[str, Any] | None:
    rules = config["observable_reference_rules"]
    a_row = _row_at(inst_df, ref_date)
    if a_row is None or not bool(a_row.get("launch_like_acceleration", False)):
        return None
    ref_pos = int(a_row.name)
    low_w = max(int(window["frozen_window_low"]), int(rules["second_breakout_min_gap_days"]))
    high_w = min(int(window["frozen_window_high"]), int(rules["second_breakout_max_gap_days"]))
    for t_pos in range(ref_pos + low_w, min(len(inst_df), ref_pos + high_w + 1)):
        if t_pos <= ref_pos + 1:
            continue
        interval = inst_df.iloc[ref_pos + 1 : t_pos]
        t = inst_df.iloc[t_pos]
        if interval.empty:
            continue
        if float(interval["low"].min()) < float(a_row.close) * (1.0 - float(rules["consolidation_max_drawdown_from_first_close"])):
            continue
        if not (float(t.close) >= float(interval["high"].max()) and float(t.close) / float(a_row.close) - 1.0 >= float(rules["second_breakout_min_return_from_first_close"])):
            continue
        if not (float(t.money) >= float(rules["money_multiple_min"]) * float(t.money_ma20) and float(t.money) >= float(rules["money_min_cny"])):
            continue
        if bool(t.is_buy_executable_next_open):
            return {"signal_date": as_date(t.date), "reference_acceleration_date": ref_date}
    return None


def _detect_failed_lookalike(config: dict[str, Any], inst_df: pd.DataFrame, calendar: pd.DatetimeIndex, ref_date: pd.Timestamp, window: dict[str, Any], family: str) -> dict[str, Any] | None:
    if family == "pullback_hold_restrengthen":
        return _detect_failed_pullback(config, inst_df, ref_date, window)
    if family == "second_breakout":
        return _detect_failed_second_breakout(config, inst_df, ref_date, window)
    return None


def _detect_failed_pullback(config: dict[str, Any], inst_df: pd.DataFrame, ref_date: pd.Timestamp, window: dict[str, Any]) -> dict[str, Any] | None:
    rules = config["observable_reference_rules"]
    a_row = _row_at(inst_df, ref_date)
    if a_row is None or not bool(a_row.get("launch_like_acceleration", False)):
        return None
    ref_pos = int(a_row.name)
    for p_pos in range(ref_pos + 1, min(len(inst_df), ref_pos + int(config["anchor_scope"]["anchor_window_max_trading_days"]) + 1)):
        p = inst_df.iloc[p_pos]
        drawdown = float(p.low) / float(a_row.close) - 1.0 if float(a_row.close) > 0 else np.nan
        for t_pos in range(p_pos + 1, min(len(inst_df), p_pos + 6)):
            t = inst_df.iloc[t_pos]
            if not bool(t.is_buy_executable_next_open):
                continue
            prev = inst_df.iloc[t_pos - 1]
            high_ref = inst_df.iloc[max(0, p_pos - 4) : p_pos + 1]["high"].max()
            passes = {
                "pullback_window_pass": int(window["frozen_window_low"]) <= (p_pos - ref_pos) <= int(window["frozen_window_high"]),
                "drawdown_band_pass": drawdown <= -float(rules["pullback_min_drawdown_from_acceleration_close"]) and drawdown >= -float(rules["pullback_max_drawdown_from_acceleration_close"]),
                "atr_floor_pass": float(p.low) >= float(a_row.close) - float(rules["pullback_hold_atr_multiple"]) * float(a_row.atr20),
                "restrengthen_pass": float(t.close) >= float(high_ref) and float(t.close) > float(prev.close) and float(t.money) >= float(t.money_ma20),
            }
            if list(passes.values()).count(False) == 1:
                return {"signal_date": as_date(t.date), "reference_acceleration_date": ref_date, "failed_condition": [k for k, v in passes.items() if not v][0]}
    return None


def _detect_failed_second_breakout(config: dict[str, Any], inst_df: pd.DataFrame, ref_date: pd.Timestamp, window: dict[str, Any]) -> dict[str, Any] | None:
    rules = config["observable_reference_rules"]
    a_row = _row_at(inst_df, ref_date)
    if a_row is None or not bool(a_row.get("launch_like_acceleration", False)):
        return None
    ref_pos = int(a_row.name)
    for t_pos in range(ref_pos + 1, min(len(inst_df), ref_pos + int(config["anchor_scope"]["anchor_window_max_trading_days"]) + 1)):
        t = inst_df.iloc[t_pos]
        if not bool(t.is_buy_executable_next_open):
            continue
        interval = inst_df.iloc[ref_pos + 1 : t_pos]
        if interval.empty:
            continue
        gap = t_pos - ref_pos
        passes = {
            "window_and_gap_pass": int(window["frozen_window_low"]) <= gap <= int(window["frozen_window_high"]) and gap >= int(rules["second_breakout_min_gap_days"]),
            "consolidation_pass": float(interval["low"].min()) >= float(a_row.close) * (1.0 - float(rules["consolidation_max_drawdown_from_first_close"])),
            "breakout_price_pass": float(t.close) >= float(interval["high"].max()) and float(t.close) / float(a_row.close) - 1.0 >= float(rules["second_breakout_min_return_from_first_close"]),
            "breakout_liquidity_pass": float(t.money) >= float(rules["money_multiple_min"]) * float(t.money_ma20) and float(t.money) >= float(rules["money_min_cny"]),
        }
        if list(passes.values()).count(False) == 1:
            return {"signal_date": as_date(t.date), "reference_acceleration_date": ref_date, "failed_condition": [k for k, v in passes.items() if not v][0]}
    return None


def build_candidate_anchor_panel(
    config: dict[str, Any],
    paths: Paths,
    panel: pd.DataFrame,
    label_panel: pd.DataFrame,
    window_freeze: pd.DataFrame,
) -> pd.DataFrame:
    calendar = load_calendar(config)
    by_inst = _instrument_frame(panel)
    label_lookup = _label_lookup(label_panel)
    ep2_pool = pd.read_parquet(topic_path(config["frozen_ep2_inputs"]["ep2_launch_pool"]))
    ep2_pool["signal_date"] = pd.to_datetime(ep2_pool["signal_date"]).dt.normalize()
    first_refs = (
        ep2_pool.loc[ep2_pool["is_buy_executable_next_open"].astype(bool)]
        .sort_values(["launch_episode_id", "launch_event_rank_within_episode", "signal_date"])
        .drop_duplicates("launch_episode_id")
    )
    windows = {row.anchor_family_id: row._asdict() for row in window_freeze.itertuples(index=False)}
    rows = []
    for ref in first_refs.itertuples(index=False):
        ref_date = as_date(ref.signal_date)
        inst_df = by_inst.get(str(ref.instrument))
        if inst_df is None:
            continue
        for family in config["primary_anchor_families"]:
            window = windows.get(family)
            if not window or window["window_derivation_status"] != "derived":
                continue
            candidate = _detect_family_candidate(config, inst_df, calendar, ref_date, window, family)
            if candidate is None:
                continue
            signal_date = as_date(candidate["signal_date"])
            exec_date = next_trading_day(calendar, signal_date)
            row_at_signal = _row_at(inst_df, signal_date)
            if row_at_signal is None:
                continue
            label = _join_label(label_lookup, str(ref.instrument), signal_date)
            parameter_hash = canonical_hash({"family": family, "window": window, "rules": config["observable_reference_rules"]})
            event_id = stable_id("EP3_ANCHOR", family, ref.launch_episode_id, ref.instrument, signal_date.date().isoformat(), parameter_hash)
            rows.append(
                {
                    "anchor_event_id": event_id,
                    "anchor_family_id": family,
                    "instrument": str(ref.instrument),
                    "signal_date": signal_date,
                    "execution_date": exec_date,
                    "entry_price_reference": float(row_at_signal.entry_price_reference),
                    "split": split_for_date(config, signal_date),
                    "is_primary_anchor_family": True,
                    "is_deferred_anchor_family": False,
                    "is_executable_next_open": bool(row_at_signal.is_buy_executable_next_open),
                    "blocked_buy_reason": str(row_at_signal.blocked_buy_reason),
                    "anchor_window_id": f"{family}_{int(window['frozen_window_low'])}_{int(window['frozen_window_high'])}",
                    "feature_asof_date": signal_date,
                    "anchor_trigger_rate_denominator_id": str(ref.launch_episode_id),
                    "winner_label_available_for_audit": label["label_join_status"] == "matched",
                    "eligible_for_primary_gate": label["eligible_for_primary_gate"],
                    "label_join_status": label["label_join_status"],
                    "winner_50h120": label["winner_50h120"],
                    "winner_100h240": label["winner_100h240"],
                    "source_universe": "ep2_launch_pool",
                    "reference_acceleration_date": ref_date,
                    "reference_acceleration_event_id": str(ref.launch_episode_id),
                    "anchor_formula_version": "ep3_p0_v1",
                    "anchor_parameter_hash": parameter_hash,
                    "dedupe_rank_within_reference_event": 1,
                    "excluded_by_reference_event_dedupe": False,
                    "matched_control_bucket_id": str(row_at_signal.matched_control_bucket_id),
                    "industry_target_key": str(row_at_signal.industry_target_key),
                    "money_bucket": row_at_signal.money_bucket,
                    "vol20_bucket": row_at_signal.vol20_bucket,
                    "ret_60d_bucket": row_at_signal.ret_60d_bucket,
                }
            )
    anchors = pd.DataFrame(rows, columns=candidate_anchor_columns())
    if not anchors.empty:
        anchors = anchors.sort_values(["reference_acceleration_event_id", "anchor_family_id", "signal_date", "anchor_event_id"]).reset_index(drop=True)
        anchors["dedupe_rank_within_reference_event"] = anchors.groupby(["reference_acceleration_event_id", "anchor_family_id"]).cumcount() + 1
        anchors["excluded_by_reference_event_dedupe"] = anchors["dedupe_rank_within_reference_event"].gt(1)
    anchors = add_forward_returns(config, panel, anchors, "anchor")
    write_parquet(anchors, paths.cache_dir / "ep3_candidate_anchor_panel.parquet")
    _write_trigger_budget_audit(config, paths, anchors, ep2_pool)
    return anchors


def candidate_anchor_columns() -> list[str]:
    return [
        "anchor_event_id",
        "anchor_family_id",
        "instrument",
        "signal_date",
        "execution_date",
        "entry_price_reference",
        "split",
        "is_primary_anchor_family",
        "is_deferred_anchor_family",
        "is_executable_next_open",
        "blocked_buy_reason",
        "anchor_window_id",
        "feature_asof_date",
        "anchor_trigger_rate_denominator_id",
        "winner_label_available_for_audit",
        "eligible_for_primary_gate",
        "label_join_status",
        "winner_50h120",
        "winner_100h240",
        "source_universe",
        "reference_acceleration_date",
        "reference_acceleration_event_id",
        "anchor_formula_version",
        "anchor_parameter_hash",
        "dedupe_rank_within_reference_event",
        "excluded_by_reference_event_dedupe",
        "matched_control_bucket_id",
        "industry_target_key",
        "money_bucket",
        "vol20_bucket",
        "ret_60d_bucket",
    ]


def _label_lookup(label_panel: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], dict[str, Any]]:
    df = label_panel.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return {(str(r.instrument), as_date(r.date)): r._asdict() for r in df.itertuples(index=False)}


def _join_label(label_lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], instrument: str, signal_date: pd.Timestamp) -> dict[str, Any]:
    label = label_lookup.get((instrument, as_date(signal_date)))
    if label is None:
        return {
            "label_join_status": "missing_label",
            "eligible_for_primary_gate": False,
            "winner_50h120": False,
            "winner_100h240": False,
        }
    if not bool(label["label_horizon_complete"]):
        status = "incomplete_horizon"
    elif not bool(label["horizon_contained_in_split"]):
        status = "split_horizon_crossing"
    else:
        status = "matched"
    return {
        "label_join_status": status,
        "eligible_for_primary_gate": bool(label["eligible_for_primary_gate"]),
        "winner_50h120": bool(label["winner_50h120"]),
        "winner_100h240": bool(label["winner_100h240"]),
    }


def _write_trigger_budget_audit(config: dict[str, Any], paths: Paths, anchors: pd.DataFrame, ep2_pool: pd.DataFrame) -> None:
    rows = []
    first_ep = ep2_pool.sort_values(["launch_episode_id", "signal_date"]).drop_duplicates("launch_episode_id").copy()
    first_ep["split"] = first_ep["signal_date"].map(lambda d: split_for_date(config, d))
    for split_name in ["train", "validation", "robustness"]:
        denom = int(first_ep.loc[first_ep["split"].eq(split_name), "launch_episode_id"].nunique())
        for family in config["primary_anchor_families"]:
            group = anchors.loc[
                anchors["split"].eq(split_name)
                & anchors["anchor_family_id"].eq(family)
                & anchors["dedupe_rank_within_reference_event"].eq(1)
                & anchors["is_executable_next_open"].astype(bool)
            ]
            rate = len(group) / denom if denom else np.nan
            rows.append(
                {
                    "split": split_name,
                    "anchor_family_id": family,
                    "anchor_trigger_count": len(group),
                    "ep2_launch_episode_count": denom,
                    "anchor_trigger_rate_per_launch_episode": rate,
                    "min_allowed": config["trigger_budget"]["min_anchor_trigger_rate_per_launch_episode"],
                    "max_allowed": config["trigger_budget"]["max_anchor_trigger_rate_per_launch_episode"],
                    "trigger_budget_pass": bool(
                        denom
                        and rate >= float(config["trigger_budget"]["min_anchor_trigger_rate_per_launch_episode"])
                        and rate <= float(config["trigger_budget"]["max_anchor_trigger_rate_per_launch_episode"])
                    ),
                }
            )
    write_csv(pd.DataFrame(rows), paths.reports_dir / "ep3_anchor_trigger_budget_audit.csv")


def build_matched_baseline_panel(
    config: dict[str, Any],
    paths: Paths,
    panel: pd.DataFrame,
    label_panel: pd.DataFrame,
    anchors: pd.DataFrame,
    window_freeze: pd.DataFrame,
) -> pd.DataFrame:
    calendar = load_calendar(config)
    label_lookup = _label_lookup(label_panel)
    by_inst = _instrument_frame(panel)
    ep2_pool = pd.read_parquet(topic_path(config["frozen_ep2_inputs"]["ep2_launch_pool"]))
    ep2_pool["signal_date"] = pd.to_datetime(ep2_pool["signal_date"]).dt.normalize()
    windows = {row.anchor_family_id: row._asdict() for row in window_freeze.itertuples(index=False)}
    rows: list[dict[str, Any]] = []
    for ref in ep2_pool.loc[ep2_pool["is_buy_executable_next_open"].astype(bool)].itertuples(index=False):
        signal_date = as_date(ref.signal_date)
        label = _join_label(label_lookup, str(ref.instrument), signal_date)
        rows.append(
            _baseline_row(
                config,
                "all_launch_direct_baseline",
                "",
                "all",
                str(ref.instrument),
                signal_date,
                as_date(ref.execution_date),
                float(ref.execution_price_reference),
                "matched",
                "all executable EP2 launch pool rows",
                "",
                False,
                False,
                label,
                canonical_hash({"source": "ep2_launch_pool", "launch_episode_id": ref.launch_episode_id}),
                reference_acceleration_date=signal_date,
                reference_acceleration_event_id=str(ref.launch_episode_id),
            )
        )
    valid_anchors = anchors.loc[
        anchors["dedupe_rank_within_reference_event"].eq(1)
        & anchors["is_executable_next_open"].astype(bool)
        & anchors["eligible_for_primary_gate"].astype(bool)
    ].copy()
    anchor_dates = {(str(r.instrument), as_date(r.signal_date)) for r in valid_anchors.itertuples(index=False)}
    control_pool = panel.loc[panel["universe_member_asof_signal_date"].astype(bool)].copy()
    control_pool["split"] = control_pool["date"].map(lambda d: split_for_date(config, d))
    for anchor in valid_anchors.itertuples(index=False):
        family = str(anchor.anchor_family_id)
        median_days = int(windows[family]["train_median_anchor_window_days"])
        rows.append(_build_matched_delay_row(config, calendar, by_inst, label_lookup, anchor, median_days))
        rows.append(_build_same_instrument_row(config, control_pool, label_lookup, anchor, anchor_dates))
        rows.append(_build_industry_row(config, control_pool, label_lookup, anchor, anchor_dates))
    for ref in ep2_pool.loc[ep2_pool["is_buy_executable_next_open"].astype(bool)].sort_values(["launch_episode_id", "signal_date"]).drop_duplicates("launch_episode_id").itertuples(index=False):
        inst_df = by_inst.get(str(ref.instrument))
        if inst_df is None:
            continue
        for family in config["primary_anchor_families"]:
            window = windows.get(family)
            if not window or window["window_derivation_status"] != "derived":
                continue
            failed = _detect_failed_lookalike(config, inst_df, calendar, as_date(ref.signal_date), window, family)
            if failed is None:
                continue
            sig = as_date(failed["signal_date"])
            row_at = _row_at(inst_df, sig)
            if row_at is None:
                continue
            label = _join_label(label_lookup, str(ref.instrument), sig)
            linked = ""
            match = valid_anchors.loc[
                valid_anchors["reference_acceleration_event_id"].eq(str(ref.launch_episode_id))
                & valid_anchors["anchor_family_id"].eq(family)
            ]
            if not match.empty:
                linked = str(match.iloc[0]["anchor_event_id"])
            rows.append(
                _baseline_row(
                    config,
                    "failed_lookalike_baseline",
                    linked,
                    family,
                    str(ref.instrument),
                    sig,
                    as_date(row_at.execution_date),
                    float(row_at.entry_price_reference),
                    "matched",
                    f"failed exactly one condition: {failed['failed_condition']}",
                    str(row_at.matched_control_bucket_id),
                    False,
                    False,
                    label,
                    canonical_hash({"failed": failed, "family": family}),
                    reference_acceleration_date=as_date(ref.signal_date),
                    reference_acceleration_event_id=str(ref.launch_episode_id),
                )
            )
    baseline = pd.DataFrame(rows, columns=baseline_columns())
    baseline = add_forward_returns(config, panel, baseline, "baseline")
    write_parquet(baseline, paths.cache_dir / "ep3_matched_baseline_panel.parquet")
    return baseline


def baseline_columns() -> list[str]:
    return [
        "baseline_event_id",
        "anchor_event_id",
        "anchor_family_id",
        "baseline_id",
        "instrument",
        "signal_date",
        "execution_date",
        "entry_price_reference",
        "split",
        "match_status",
        "match_reason",
        "matched_control_bucket_id",
        "delay_repair_flag",
        "control_shortfall_flag",
        "is_executable_next_open",
        "blocked_buy_reason",
        "eligible_for_primary_gate",
        "label_join_status",
        "winner_50h120",
        "winner_100h240",
        "baseline_input_hash",
        "reference_acceleration_date",
        "reference_acceleration_event_id",
    ]


def _baseline_row(
    config: dict[str, Any],
    baseline_id: str,
    anchor_event_id: str,
    family: str,
    instrument: str,
    signal_date: pd.Timestamp,
    execution_date: pd.Timestamp,
    entry_price: float,
    match_status: str,
    match_reason: str,
    bucket_id: str,
    delay_repair: bool,
    shortfall: bool,
    label: dict[str, Any],
    input_hash: str,
    reference_acceleration_date: pd.Timestamp | str = "",
    reference_acceleration_event_id: str = "",
) -> dict[str, Any]:
    reference_date_value = "" if reference_acceleration_date == "" or pd.isna(reference_acceleration_date) else as_date(reference_acceleration_date).date().isoformat()
    return {
        "baseline_event_id": stable_id("EP3_BASELINE", baseline_id, anchor_event_id, family, instrument, signal_date.date().isoformat() if not pd.isna(signal_date) else ""),
        "anchor_event_id": anchor_event_id,
        "anchor_family_id": family,
        "baseline_id": baseline_id,
        "instrument": instrument,
        "signal_date": signal_date,
        "execution_date": execution_date,
        "entry_price_reference": entry_price,
        "split": split_for_date(config, signal_date) if not pd.isna(signal_date) else "out_of_scope",
        "match_status": match_status,
        "match_reason": match_reason,
        "matched_control_bucket_id": bucket_id,
        "delay_repair_flag": delay_repair,
        "control_shortfall_flag": shortfall,
        "is_executable_next_open": bool(match_status in {"matched", "repaired"} and np.isfinite(entry_price)),
        "blocked_buy_reason": "" if match_status in {"matched", "repaired"} and np.isfinite(entry_price) else "unavailable",
        "eligible_for_primary_gate": label["eligible_for_primary_gate"],
        "label_join_status": label["label_join_status"],
        "winner_50h120": label["winner_50h120"],
        "winner_100h240": label["winner_100h240"],
        "baseline_input_hash": input_hash,
        "reference_acceleration_date": reference_date_value,
        "reference_acceleration_event_id": reference_acceleration_event_id,
    }


def _build_matched_delay_row(
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    by_inst: dict[str, pd.DataFrame],
    label_lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    anchor: Any,
    median_days: int,
) -> dict[str, Any]:
    inst_df = by_inst.get(str(anchor.instrument))
    target = add_trading_days(calendar, anchor.signal_date, median_days)
    row_at = _row_at(inst_df, target) if inst_df is not None and not pd.isna(target) else None
    repaired = False
    if row_at is None or not bool(row_at.is_buy_executable_next_open) or split_for_date(config, target) != str(anchor.split):
        repaired = True
        row_at = None
        if inst_df is not None and not pd.isna(target):
            max_date = target + pd.Timedelta(days=int(config["matched_controls"]["max_calendar_day_distance"]))
            candidates = inst_df.loc[
                (inst_df["date"] >= target)
                & (inst_df["date"] <= max_date)
                & inst_df["date"].map(lambda d: split_for_date(config, d)).eq(str(anchor.split))
                & inst_df["is_buy_executable_next_open"].astype(bool)
            ]
            if not candidates.empty:
                row_at = candidates.iloc[0]
    if row_at is None:
        label = {"eligible_for_primary_gate": False, "label_join_status": "missing_label", "winner_50h120": False, "winner_100h240": False}
        return _baseline_row(config, "matched_delay_baseline", anchor.anchor_event_id, anchor.anchor_family_id, anchor.instrument, pd.NaT, pd.NaT, np.nan, "unavailable", "no executable delayed date", "", False, True, label, canonical_hash({"anchor": anchor.anchor_event_id, "median_days": median_days}))
    sig = as_date(row_at.date)
    label = _join_label(label_lookup, str(anchor.instrument), sig)
    return _baseline_row(config, "matched_delay_baseline", anchor.anchor_event_id, anchor.anchor_family_id, anchor.instrument, sig, as_date(row_at.execution_date), float(row_at.entry_price_reference), "repaired" if repaired else "matched", "same instrument median train anchor window delay", str(row_at.matched_control_bucket_id), repaired, False, label, canonical_hash({"anchor": anchor.anchor_event_id, "median_days": median_days, "signal_date": sig.date().isoformat()}), reference_acceleration_date=anchor.reference_acceleration_date, reference_acceleration_event_id=anchor.reference_acceleration_event_id)


def _build_same_instrument_row(config: dict[str, Any], pool: pd.DataFrame, label_lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], anchor: Any, anchor_dates: set[tuple[str, pd.Timestamp]]) -> dict[str, Any]:
    candidates = _control_candidates(config, pool, anchor, same_instrument=True, anchor_dates=anchor_dates)
    return _control_row_from_candidates(config, label_lookup, anchor, candidates, "same_instrument_nonanchor_baseline", "same instrument non-anchor matched bucket")


def _build_industry_row(config: dict[str, Any], pool: pd.DataFrame, label_lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], anchor: Any, anchor_dates: set[tuple[str, pd.Timestamp]]) -> dict[str, Any]:
    candidates = _control_candidates(config, pool, anchor, same_instrument=False, anchor_dates=anchor_dates)
    return _control_row_from_candidates(config, label_lookup, anchor, candidates, "industry_matched_baseline", "different instrument same industry matched bucket")


def _control_candidates(config: dict[str, Any], pool: pd.DataFrame, anchor: Any, same_instrument: bool, anchor_dates: set[tuple[str, pd.Timestamp]]) -> pd.DataFrame:
    max_days = int(config["matched_controls"]["max_calendar_day_distance"])
    sig = as_date(anchor.signal_date)
    date_low = sig - pd.Timedelta(days=max_days)
    date_high = sig + pd.Timedelta(days=max_days)
    mask = (
        pool["date"].between(date_low, date_high)
        & pool["split"].eq(str(anchor.split))
        & pool["matched_control_bucket_id"].eq(str(anchor.matched_control_bucket_id))
        & pool["is_buy_executable_next_open"].astype(bool)
    )
    if same_instrument:
        mask &= pool["instrument"].eq(str(anchor.instrument))
    else:
        mask &= pool["instrument"].ne(str(anchor.instrument)) & pool["industry_target_key"].eq(str(anchor.industry_target_key))
    candidates = pool.loc[mask].copy()
    if candidates.empty:
        return candidates
    keys = list(zip(candidates["instrument"].astype(str), pd.to_datetime(candidates["date"]).dt.normalize()))
    candidates = candidates.loc[[key not in anchor_dates for key in keys]].copy()
    if candidates.empty:
        return candidates
    candidates["calendar_distance"] = (candidates["date"] - sig).abs().dt.days
    candidates = candidates.sort_values(["calendar_distance", "money", "instrument", "date"], ascending=[True, False, True, True])
    return candidates


def _control_row_from_candidates(config: dict[str, Any], label_lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], anchor: Any, candidates: pd.DataFrame, baseline_id: str, reason: str) -> dict[str, Any]:
    if candidates.empty:
        label = {"eligible_for_primary_gate": False, "label_join_status": "missing_label", "winner_50h120": False, "winner_100h240": False}
        return _baseline_row(config, baseline_id, anchor.anchor_event_id, anchor.anchor_family_id, anchor.instrument, pd.NaT, pd.NaT, np.nan, "unavailable", "no matched control", "", False, True, label, canonical_hash({"anchor": anchor.anchor_event_id, "baseline_id": baseline_id}))
    row = candidates.iloc[0]
    sig = as_date(row.date)
    label = _join_label(label_lookup, str(row.instrument), sig)
    return _baseline_row(config, baseline_id, anchor.anchor_event_id, anchor.anchor_family_id, str(row.instrument), sig, as_date(row.execution_date), float(row.entry_price_reference), "matched", reason, str(row.matched_control_bucket_id), False, len(candidates) < int(config["matched_controls"]["controls_per_anchor"]), label, canonical_hash({"anchor": anchor.anchor_event_id, "baseline_id": baseline_id, "instrument": row.instrument, "signal_date": sig.date().isoformat()}), reference_acceleration_date=anchor.reference_acceleration_date, reference_acceleration_event_id=anchor.reference_acceleration_event_id)


def add_forward_returns(config: dict[str, Any], panel: pd.DataFrame, events: pd.DataFrame, event_kind: str) -> pd.DataFrame:
    if events.empty:
        return events
    calendar = load_calendar(config)
    lookup = price_lookup(panel)
    rates = cost_rates(config)
    horizons = {"H20": 20, "H10": 10, "H60": 60}
    df = events.copy()
    for horizon_id, days in horizons.items():
        returns = []
        maes = []
        exit_dates = []
        for row in df.itertuples(index=False):
            entry = float(getattr(row, "entry_price_reference", np.nan))
            exec_date = as_date(getattr(row, "execution_date")) if not pd.isna(getattr(row, "execution_date")) else pd.NaT
            exit_date = add_trading_days(calendar, exec_date, days) if not pd.isna(exec_date) else pd.NaT
            exit_dates.append("" if pd.isna(exit_date) else exit_date.date().isoformat())
            if pd.isna(exit_date) or not np.isfinite(entry) or entry <= 0:
                returns.append(np.nan)
                maes.append(np.nan)
                continue
            exit_info = lookup.get((str(row.instrument), exit_date), {})
            exit_open = float(exit_info.get("open", np.nan))
            if np.isfinite(exit_open):
                returns.append(exit_open / entry - 1.0 - rates["buy_total"] - rates["sell_total"])
            else:
                returns.append(np.nan)
            path_dates = calendar[(calendar >= exec_date) & (calendar <= exit_date)]
            lows = [float(lookup.get((str(row.instrument), d), {}).get("low", np.nan)) for d in path_dates]
            lows = [x for x in lows if np.isfinite(x)]
            maes.append(min(lows) / entry - 1.0 if lows else np.nan)
        df[f"exit_date_{horizon_id}"] = exit_dates
        df[f"after_cost_return_{horizon_id}"] = returns
        df[f"max_adverse_excursion_{horizon_id}"] = maes
    return df


def compute_metrics_and_gates(
    config: dict[str, Any],
    paths: Paths,
    lifecycle: pd.DataFrame,
    anchors: pd.DataFrame,
    baselines: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ep2_pool = pd.read_parquet(topic_path(config["frozen_ep2_inputs"]["ep2_launch_pool"]))
    ep2_pool["signal_date"] = pd.to_datetime(ep2_pool["signal_date"]).dt.normalize()
    first_ep = ep2_pool.sort_values(["launch_episode_id", "signal_date"]).drop_duplicates("launch_episode_id").copy()
    first_ep["split"] = first_ep["signal_date"].map(lambda d: split_for_date(config, d))
    rows = []
    for horizon_id in ["H20", "H10", "H60"]:
        for split_name in ["train", "validation", "robustness"]:
            denom = int(first_ep.loc[first_ep["split"].eq(split_name), "launch_episode_id"].nunique())
            for family in config["primary_anchor_families"]:
                anchor_events = anchors.loc[
                    anchors["split"].eq(split_name)
                    & anchors["anchor_family_id"].eq(family)
                    & anchors["eligible_for_primary_gate"].astype(bool)
                    & anchors["is_executable_next_open"].astype(bool)
                    & anchors["dedupe_rank_within_reference_event"].eq(1)
                ].copy()
                rows.append(_metric_row(anchor_events, split_name, family, "anchor", horizon_id, denom, baselines))
                for baseline_id in [
                    "all_launch_direct_baseline",
                    "matched_delay_baseline",
                    "same_instrument_nonanchor_baseline",
                    "industry_matched_baseline",
                    "failed_lookalike_baseline",
                ]:
                    base_events = baselines.loc[baselines["split"].eq(split_name) & baselines["baseline_id"].eq(baseline_id)].copy()
                    if baseline_id != "all_launch_direct_baseline":
                        base_events = base_events.loc[base_events["anchor_family_id"].eq(family)]
                    base_events = base_events.loc[
                        base_events["eligible_for_primary_gate"].astype(bool)
                        & base_events["is_executable_next_open"].astype(bool)
                        & base_events["match_status"].isin(["matched", "repaired"])
                    ]
                    rows.append(_metric_row(base_events, split_name, family, baseline_id, horizon_id, denom, baselines))
    metrics = pd.DataFrame(rows)
    write_csv(metrics, paths.reports_dir / "ep3_anchor_vs_matched_baseline.csv")
    sensitivity = metrics.loc[metrics["horizon_id"].isin(["H10", "H60"])].copy()
    write_csv(sensitivity, paths.reports_dir / "ep3_sensitivity_horizon_audit.csv")
    _write_secondary_audits(paths, metrics)
    gates = _build_gate_audit(config, lifecycle, metrics)
    write_csv(gates, paths.reports_dir / "ep3_gate_audit.csv")
    leads = _build_preliminary_leads(config, gates)
    write_csv(leads, paths.reports_dir / "ep3_preliminary_anchor_leads.csv")
    _write_discussion_report(paths, leads, gates, metrics)
    return metrics, gates


def _metric_row(events: pd.DataFrame, split_name: str, family: str, baseline_id: str, horizon_id: str, launch_denominator: int, baselines: pd.DataFrame) -> dict[str, Any]:
    ret_col = f"after_cost_return_{horizon_id}"
    mae_col = f"max_adverse_excursion_{horizon_id}"
    event_count = len(events)
    returns = events[ret_col].dropna() if ret_col in events else pd.Series(dtype=float)
    maes = events[mae_col].dropna() if mae_col in events else pd.Series(dtype=float)
    inst_year = pd.Series(dtype=object)
    pos_rate = np.nan
    top1_share = np.nan
    if event_count and ret_col in events:
        tmp = events.copy()
        tmp["instrument_year"] = tmp["instrument"].astype(str) + "_" + pd.to_datetime(tmp["signal_date"]).dt.year.astype(str)
        pnl = tmp.groupby("instrument_year")[ret_col].sum(min_count=1).dropna()
        inst_year = pnl.index.to_series()
        pos = pnl.loc[pnl > 0]
        pos_rate = float((pnl > 0).mean()) if len(pnl) else np.nan
        top1_share = float(pos.max() / pos.sum()) if len(pos) and pos.sum() > 0 else 0.0
    top5_exp = np.nan
    if event_count:
        top5_exp = float(events["instrument"].value_counts().head(5).sum() / event_count)
    failed_count = 0
    if baseline_id == "anchor":
        failed_count = len(
            baselines.loc[
                baselines["split"].eq(split_name)
                & baselines["anchor_family_id"].eq(family)
                & baselines["baseline_id"].eq("failed_lookalike_baseline")
                & baselines["is_executable_next_open"].astype(bool)
            ]
        )
    failure_rate = failed_count / (event_count + failed_count) if baseline_id == "anchor" and (event_count + failed_count) else np.nan
    return {
        "split": split_name,
        "anchor_family_id": family,
        "baseline_id": baseline_id,
        "horizon_id": horizon_id,
        "event_count": event_count,
        "anchor_trigger_count": event_count if baseline_id == "anchor" else np.nan,
        "anchor_trigger_rate_per_launch_episode": event_count / launch_denominator if baseline_id == "anchor" and launch_denominator else np.nan,
        "unique_instrument_count": int(events["instrument"].nunique()) if event_count else 0,
        "unique_instrument_year_count": int(len(inst_year)) if event_count else 0,
        f"mean_after_cost_return_{horizon_id}": float(returns.mean()) if len(returns) else np.nan,
        f"median_after_cost_return_{horizon_id}": float(returns.median()) if len(returns) else np.nan,
        f"p05_after_cost_return_{horizon_id}": float(returns.quantile(0.05)) if len(returns) else np.nan,
        f"max_adverse_excursion_mean_{horizon_id}": float(maes.mean()) if len(maes) else np.nan,
        "winner_capture_rate_50h120": float(events["winner_50h120"].mean()) if event_count and "winner_50h120" in events else np.nan,
        "winner_capture_rate_100h240": float(events["winner_100h240"].mean()) if event_count and "winner_100h240" in events else np.nan,
        "instrument_year_positive_rate": pos_rate,
        "top1_instrument_year_pnl_share": top1_share,
        "top5_instrument_exposure_share": top5_exp,
        "failure_lookalike_rate": failure_rate,
    }


def _write_secondary_audits(paths: Paths, metrics: pd.DataFrame) -> None:
    h20 = metrics.loc[metrics["horizon_id"].eq("H20")].copy()
    write_csv(
        h20[["split", "anchor_family_id", "baseline_id", "unique_instrument_year_count", "instrument_year_positive_rate"]].copy(),
        paths.reports_dir / "ep3_instrument_year_lift_audit.csv",
    )
    write_csv(
        h20[["split", "anchor_family_id", "baseline_id", "top1_instrument_year_pnl_share", "top5_instrument_exposure_share"]].copy(),
        paths.reports_dir / "ep3_regime_stability_audit.csv",
    )
    failure = h20.loc[h20["baseline_id"].isin(["anchor", "failed_lookalike_baseline", "matched_delay_baseline"])].copy()
    write_csv(failure, paths.reports_dir / "ep3_failure_lookalike_audit.csv")


def _metric_value(metrics: pd.DataFrame, split_name: str, family: str, baseline_id: str, column: str) -> float:
    row = metrics.loc[
        metrics["split"].eq(split_name)
        & metrics["anchor_family_id"].eq(family)
        & metrics["baseline_id"].eq(baseline_id)
        & metrics["horizon_id"].eq("H20")
    ]
    if row.empty or column not in row:
        return np.nan
    return float(row.iloc[0][column])


def _build_gate_audit(config: dict[str, Any], lifecycle: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    gates = config["gates"]
    rows = []
    total_train_winners = lifecycle.loc[
        lifecycle["split"].eq("train")
        & lifecycle["winner_label_id"].eq("winner_50h120")
        & lifecycle["lifecycle_stage_id"].eq("first_acceleration")
        & lifecycle["eligible_for_primary_gate"].astype(bool)
    ]["winner_episode_id"].nunique()
    for family in config["primary_anchor_families"]:
        family_train = lifecycle.loc[
            lifecycle["split"].eq("train")
            & lifecycle["winner_label_id"].eq("winner_50h120")
            & lifecycle["observable_anchor_candidate"].astype(bool)
            & lifecycle["anchor_family_id"].eq(family)
            & lifecycle["eligible_for_primary_gate"].astype(bool)
        ]["winner_episode_id"].nunique()
        recall = family_train / total_train_winners if total_train_winners else np.nan
        validation_anchor_mean = _metric_value(metrics, "validation", family, "anchor", "mean_after_cost_return_H20")
        validation_delay_mean = _metric_value(metrics, "validation", family, "matched_delay_baseline", "mean_after_cost_return_H20")
        validation_anchor_p05 = _metric_value(metrics, "validation", family, "anchor", "p05_after_cost_return_H20")
        validation_delay_p05 = _metric_value(metrics, "validation", family, "matched_delay_baseline", "p05_after_cost_return_H20")
        validation_anchor_mae = _metric_value(metrics, "validation", family, "anchor", "max_adverse_excursion_mean_H20")
        validation_delay_mae = _metric_value(metrics, "validation", family, "matched_delay_baseline", "max_adverse_excursion_mean_H20")
        validation_anchor_pos = _metric_value(metrics, "validation", family, "anchor", "instrument_year_positive_rate")
        validation_delay_pos = _metric_value(metrics, "validation", family, "matched_delay_baseline", "instrument_year_positive_rate")
        validation_trigger = _metric_value(metrics, "validation", family, "anchor", "anchor_trigger_rate_per_launch_episode")
        validation_insty = _metric_value(metrics, "validation", family, "anchor", "unique_instrument_year_count")
        top1 = _metric_value(metrics, "validation", family, "anchor", "top1_instrument_year_pnl_share")
        top5 = _metric_value(metrics, "validation", family, "anchor", "top5_instrument_exposure_share")
        failure_rate = _metric_value(metrics, "validation", family, "anchor", "failure_lookalike_rate")
        matched_delay_failure_rate = failure_rate if np.isfinite(failure_rate) else np.nan
        robust_mean = _metric_value(metrics, "robustness", family, "anchor", "mean_after_cost_return_H20") - _metric_value(metrics, "robustness", family, "matched_delay_baseline", "mean_after_cost_return_H20")
        robust_p05 = _metric_value(metrics, "robustness", family, "anchor", "p05_after_cost_return_H20") - _metric_value(metrics, "robustness", family, "matched_delay_baseline", "p05_after_cost_return_H20")
        robust_trigger = _metric_value(metrics, "robustness", family, "anchor", "anchor_trigger_rate_per_launch_episode")
        robust_top1 = _metric_value(metrics, "robustness", family, "anchor", "top1_instrument_year_pnl_share")
        robust_top5 = _metric_value(metrics, "robustness", family, "anchor", "top5_instrument_exposure_share")
        specs = [
            ("lifecycle_anchor_recall", recall, gates["min_lifecycle_anchor_recall"], ">=", recall >= gates["min_lifecycle_anchor_recall"] if np.isfinite(recall) else False, "failed_no_clean_lifecycle_anchor"),
            ("validation_trigger_budget", validation_trigger, f"{config['trigger_budget']['min_anchor_trigger_rate_per_launch_episode']}..{config['trigger_budget']['max_anchor_trigger_rate_per_launch_episode']}", "range", np.isfinite(validation_trigger) and validation_trigger >= config["trigger_budget"]["min_anchor_trigger_rate_per_launch_episode"] and validation_trigger <= config["trigger_budget"]["max_anchor_trigger_rate_per_launch_episode"], "failed_trigger_budget"),
            ("validation_unique_instrument_year_count", validation_insty, gates["min_validation_unique_instrument_year_count"], ">=", validation_insty >= gates["min_validation_unique_instrument_year_count"] if np.isfinite(validation_insty) else False, "failed_forward_lift"),
            ("validation_h20_mean_diff_vs_matched_delay", validation_anchor_mean - validation_delay_mean, gates["min_validation_h20_mean_diff_vs_matched_delay"], ">", validation_anchor_mean - validation_delay_mean > gates["min_validation_h20_mean_diff_vs_matched_delay"] if np.isfinite(validation_anchor_mean - validation_delay_mean) else False, "failed_forward_lift"),
            ("validation_h20_p05_diff_vs_matched_delay", validation_anchor_p05 - validation_delay_p05, gates["min_validation_h20_p05_diff_vs_matched_delay"], ">=", validation_anchor_p05 - validation_delay_p05 >= gates["min_validation_h20_p05_diff_vs_matched_delay"] if np.isfinite(validation_anchor_p05 - validation_delay_p05) else False, "failed_tail_risk"),
            ("validation_h20_mae_worsening_vs_matched_delay", max(0.0, validation_delay_mae - validation_anchor_mae) if np.isfinite(validation_delay_mae - validation_anchor_mae) else np.nan, gates["max_validation_h20_mae_worsening_vs_matched_delay"], "<=", max(0.0, validation_delay_mae - validation_anchor_mae) <= gates["max_validation_h20_mae_worsening_vs_matched_delay"] if np.isfinite(validation_delay_mae - validation_anchor_mae) else False, "failed_tail_risk"),
            ("validation_instrument_year_positive_rate_diff", validation_anchor_pos - validation_delay_pos, gates["min_validation_instrument_year_positive_rate_diff"], ">=", validation_anchor_pos - validation_delay_pos >= gates["min_validation_instrument_year_positive_rate_diff"] if np.isfinite(validation_anchor_pos - validation_delay_pos) else False, "failed_forward_lift"),
            ("validation_top1_instrument_year_pnl_share", top1, gates["max_top1_instrument_year_pnl_share"], "<=", top1 <= gates["max_top1_instrument_year_pnl_share"] if np.isfinite(top1) else False, "failed_concentration"),
            ("validation_top5_instrument_exposure_share", top5, gates["max_top5_instrument_exposure_share"], "<=", top5 <= gates["max_top5_instrument_exposure_share"] if np.isfinite(top5) else False, "failed_concentration"),
            ("failure_lookalike_rate_vs_matched_delay", failure_rate - matched_delay_failure_rate, 0.0, "<=", failure_rate <= matched_delay_failure_rate if np.isfinite(failure_rate) and np.isfinite(matched_delay_failure_rate) else False, "failed_forward_lift"),
            ("robustness_mean_diff_vs_matched_delay", robust_mean, -0.001, ">=", robust_mean >= -0.001 if np.isfinite(robust_mean) else False, "failed_robustness"),
            ("robustness_p05_diff_vs_matched_delay", robust_p05, -0.005, ">=", robust_p05 >= -0.005 if np.isfinite(robust_p05) else False, "failed_robustness"),
            ("robustness_trigger_budget", robust_trigger, f"{config['trigger_budget']['min_anchor_trigger_rate_per_launch_episode']}..{config['trigger_budget']['max_anchor_trigger_rate_per_launch_episode']}", "range", np.isfinite(robust_trigger) and robust_trigger >= config["trigger_budget"]["min_anchor_trigger_rate_per_launch_episode"] and robust_trigger <= config["trigger_budget"]["max_anchor_trigger_rate_per_launch_episode"], "failed_robustness"),
            ("robustness_top1_instrument_year_pnl_share", robust_top1, 0.25, "<=", robust_top1 <= 0.25 if np.isfinite(robust_top1) else False, "failed_robustness"),
            ("robustness_top5_instrument_exposure_share", robust_top5, 0.55, "<=", robust_top5 <= 0.55 if np.isfinite(robust_top5) else False, "failed_robustness"),
        ]
        for gate_name, value, threshold, op, passed, failure_status in specs:
            rows.append(
                {
                    "anchor_family_id": family,
                    "gate_name": gate_name,
                    "gate_value": value,
                    "threshold": threshold,
                    "comparison": op,
                    "gate_passed": bool(passed),
                    "failure_status_if_failed": "" if passed else failure_status,
                }
            )
    return pd.DataFrame(rows)


def _build_preliminary_leads(config: dict[str, Any], gates: pd.DataFrame) -> pd.DataFrame:
    precedence = [
        "failed_contract_or_leakage",
        "failed_no_clean_lifecycle_anchor",
        "failed_trigger_budget",
        "failed_forward_lift",
        "failed_tail_risk",
        "failed_concentration",
        "failed_robustness",
    ]
    rows = []
    for family in config["primary_anchor_families"]:
        group = gates.loc[gates["anchor_family_id"].eq(family)]
        failures = [x for x in group.loc[~group["gate_passed"].astype(bool), "failure_status_if_failed"].astype(str).unique() if x]
        status = "passed_to_ep3_p1_anchor_validation"
        for candidate in precedence:
            if candidate in failures:
                status = candidate
                break
        rows.append(
            {
                "anchor_family_id": family,
                "lead_status": "validation_passed" if status == "passed_to_ep3_p1_anchor_validation" else "validation_failed",
                "ep3_p1_decision_status": status,
                "passed_gate_count": int(group["gate_passed"].sum()),
                "failed_gate_count": int((~group["gate_passed"].astype(bool)).sum()),
                "go_no_go": "go" if status == "passed_to_ep3_p1_anchor_validation" else "no-go",
            }
        )
    return pd.DataFrame(rows)


def _write_discussion_report(paths: Paths, leads: pd.DataFrame, gates: pd.DataFrame, metrics: pd.DataFrame) -> None:
    lines = [
        "# EP3 Engineering Baseline Report",
        "",
        f"Generated at: {now_iso()}",
        "",
        "## EP3-P1 Decision",
        "",
    ]
    for row in leads.itertuples(index=False):
        lines.append(f"- `{row.anchor_family_id}`: `{row.go_no_go}` / `{row.ep3_p1_decision_status}`")
    lines.extend(["", "## Gate Summary", ""])
    summary = gates.groupby("anchor_family_id")["gate_passed"].agg(["sum", "count"]).reset_index()
    for row in summary.itertuples(index=False):
        lines.append(f"- `{row.anchor_family_id}`: {int(row.sum)}/{int(row.count)} gates passed")
    lines.extend(["", "## Validation H20 Metrics", ""])
    cols = ["anchor_family_id", "baseline_id", "event_count", "mean_after_cost_return_H20", "p05_after_cost_return_H20", "instrument_year_positive_rate"]
    subset = metrics.loc[metrics["split"].eq("validation") & metrics["horizon_id"].eq("H20"), cols].copy()
    if subset.empty:
        lines.append("No validation H20 metric rows were available.")
    else:
        lines.append(subset.to_markdown(index=False))
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This EP3-P0 run is audit-only. A `go` requires `passed_to_ep3_p1_anchor_validation`; all `failed_*` statuses are no-go.",
        ]
    )
    (paths.reports_dir / "ep3_discussion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_authority(config: dict[str, Any], paths: Paths) -> pd.DataFrame:
    rows = []
    for name in REQUIRED_ARTIFACTS:
        if name == "ep3_engineering_baseline_manifest.json":
            continue
        path = artifact_path(paths, name)
        rows.append(
            {
                "artifact_name": name,
                "path": relpath(path),
                "exists": path.exists(),
                "content_hash": file_hash(path),
            }
        )
    return pd.DataFrame(rows)


def write_manifest(config: dict[str, Any], paths: Paths, validation_status: str, failures: list[str] | None = None) -> dict[str, Any]:
    authority = artifact_authority(config, paths)
    manifest = {
        "phase": config["phase"],
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "output_root": relpath(paths.output_root),
        "generated_at": now_iso(),
        "git_commit": git_commit_hash(),
        "validation_status": validation_status,
        "validation_failures": failures or [],
        "required_artifact_count": len(REQUIRED_ARTIFACTS),
        "existing_required_artifact_count": int(authority["exists"].sum()) + 1,
        "artifact_authority": authority.to_dict("records"),
        "forbidden_inputs": {
            "r02_threshold_search": "not_used",
            "r03_confirmed_pool": "not_used",
            "r05_holding_policy": "not_used",
            "baserate_row_level_cache": "not_used",
        },
        "frozen_ep2_inputs": {
            key: {"path": value, "content_hash": file_hash(topic_path(value))}
            for key, value in config["frozen_ep2_inputs"].items()
        },
    }
    write_json(manifest, paths.manifests_dir / "ep3_engineering_baseline_manifest.json")
    return manifest


def _stage_row(stage_order: int, stage_name: str, artifact: str, materialized: bool, used: bool, paths: Paths) -> dict[str, Any]:
    path = artifact_path(paths, artifact) if artifact in REQUIRED_ARTIFACTS else paths.output_root / artifact
    return {
        "stage_order": stage_order,
        "stage_name": stage_name,
        "completed_at": now_iso(),
        "validation_outcomes_materialized": bool(materialized),
        "robustness_outcomes_materialized": bool(materialized),
        "validation_outcomes_used_by_stage": bool(used),
        "robustness_outcomes_used_by_stage": bool(used),
        "frozen_artifact_written": relpath(path),
        "artifact_hash_after_stage": file_hash(path),
    }


def run_ep3_engineering_baseline(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    panel = mark_launch_executable(config, load_market_panel(config))

    build_input_audits(config, paths, panel)
    stages.append(_stage_row(1, "input authority and PIT audit", "ep3_input_authority.csv", False, False, paths))

    label_panel = build_winner_label_panel(config, paths, panel)
    stages.append(_stage_row(2, "winner label panel construction", "ep3_winner_label_panel.parquet", True, False, paths))

    lifecycle = build_lifecycle_profile(config, paths, panel, label_panel)
    stages.append(_stage_row(3, "lifecycle profiling universe construction", "ep3_winner_lifecycle_profile.csv", True, False, paths))

    window_freeze = freeze_anchor_windows(config, paths, lifecycle)
    stages.append(_stage_row(4, "train-only anchor window derivation", "ep3_anchor_window_freeze.csv", True, False, paths))

    freeze_anchor_dictionary(config, paths, window_freeze)
    stages.append(_stage_row(5, "observable anchor dictionary freeze", "ep3_observable_anchor_dictionary.csv", True, False, paths))

    bucket_freeze = freeze_bucket_boundaries(config, paths, panel)
    panel = apply_buckets(panel, bucket_freeze)
    stages.append(_stage_row(6, "bounded forward-audit universe construction", "ep3_matched_control_bucket_freeze.csv", True, True, paths))

    anchors = build_candidate_anchor_panel(config, paths, panel, label_panel, window_freeze)
    stages.append(_stage_row(7, "primary anchor detection", "ep3_candidate_anchor_panel.parquet", True, True, paths))

    baselines = build_matched_baseline_panel(config, paths, panel, label_panel, anchors, window_freeze)
    stages.append(_stage_row(8, "matched baseline construction", "ep3_matched_baseline_panel.parquet", True, True, paths))

    metrics, gates = compute_metrics_and_gates(config, paths, lifecycle, anchors, baselines)
    stages.append(_stage_row(9, "H20 primary forward audit and H10/H60 sensitivity", "ep3_anchor_vs_matched_baseline.csv", True, True, paths))

    stages.append(
        {
            "stage_order": 10,
            "stage_name": "gate audit and manifest",
            "completed_at": now_iso(),
            "validation_outcomes_materialized": True,
            "robustness_outcomes_materialized": True,
            "validation_outcomes_used_by_stage": True,
            "robustness_outcomes_used_by_stage": True,
            "frozen_artifact_written": relpath(paths.reports_dir / "ep3_gate_audit.csv"),
            "artifact_hash_after_stage": file_hash(paths.reports_dir / "ep3_gate_audit.csv"),
        }
    )
    write_csv(pd.DataFrame(stages), paths.reports_dir / "ep3_stage_order_audit.csv")
    manifest = write_manifest(config, paths, "not_validated")
    return {
        "label_rows": len(label_panel),
        "lifecycle_rows": len(lifecycle),
        "anchor_rows": len(anchors),
        "baseline_rows": len(baselines),
        "metric_rows": len(metrics),
        "gate_rows": len(gates),
        "manifest": manifest["validation_status"],
    }


def validate_ep3_engineering_baseline(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    failures: list[str] = []
    for name in REQUIRED_ARTIFACTS:
        if not artifact_path(paths, name).exists():
            failures.append(f"missing required artifact: {name}")
    if failures:
        write_manifest(config, paths, "failed", failures)
        return {"validation_status": "failed", "failures": failures}

    label = pd.read_parquet(paths.cache_dir / "ep3_winner_label_panel.parquet")
    anchors = pd.read_parquet(paths.cache_dir / "ep3_candidate_anchor_panel.parquet")
    baselines = pd.read_parquet(paths.cache_dir / "ep3_matched_baseline_panel.parquet")
    stage = pd.read_csv(paths.reports_dir / "ep3_stage_order_audit.csv")
    dictionary = pd.read_csv(paths.reports_dir / "ep3_observable_anchor_dictionary.csv")
    window = pd.read_csv(paths.reports_dir / "ep3_anchor_window_freeze.csv")
    metrics = pd.read_csv(paths.reports_dir / "ep3_anchor_vs_matched_baseline.csv")
    gates = pd.read_csv(paths.reports_dir / "ep3_gate_audit.csv")
    leads = pd.read_csv(paths.reports_dir / "ep3_preliminary_anchor_leads.csv")

    _require_columns("label panel", label, [
        "date",
        "instrument",
        "split",
        "winner_50h120",
        "first_50pct_target_date",
        "winner_100h240",
        "first_100pct_target_date",
        "max_forward_return_120",
        "max_forward_return_240",
        "label_horizon_complete",
        "label_price_adjustment_mode",
        "label_input_hash",
        "horizon_contained_in_split",
        "eligible_for_primary_gate",
    ], failures)
    _require_columns("anchor panel", anchors, candidate_anchor_columns(), failures)
    _require_columns("baseline panel", baselines, baseline_columns(), failures)

    output_root = paths.output_root.resolve()
    for name in REQUIRED_ARTIFACTS:
        if name == "config.yaml":
            continue
        path = artifact_path(paths, name).resolve()
        try:
            path.relative_to(output_root)
        except ValueError:
            failures.append(f"artifact outside EP3 output root: {name}")

    forbidden_paths = json.dumps(config, ensure_ascii=False).lower()
    for forbidden in ["r02", "r03", "r05", "baserate/outputs"]:
        if forbidden in forbidden_paths:
            failures.append(f"forbidden primary input reference in config: {forbidden}")

    if not set(anchors["anchor_family_id"].dropna().astype(str)).issubset(PRIMARY_FAMILIES):
        failures.append("candidate panel contains non-primary anchor family rows")
    if "is_deferred_anchor_family" in anchors and anchors["is_deferred_anchor_family"].astype(bool).any():
        failures.append("deferred anchor family produced P0 forward-audit rows")
    deferred = set(config["deferred_anchor_families"])
    enabled_deferred = dictionary.loc[dictionary["anchor_family_id"].isin(deferred) & dictionary.get("p0_forward_audit_rows_allowed", False).astype(bool)]
    if not enabled_deferred.empty:
        failures.append("observable dictionary allows deferred family P0 rows")

    early = stage.loc[stage["stage_order"].le(5)]
    if early["validation_outcomes_used_by_stage"].astype(bool).any() or early["robustness_outcomes_used_by_stage"].astype(bool).any():
        failures.append("validation/robustness outcomes used by stages 1-5")
    if sorted(stage["stage_order"].astype(int).tolist()) != list(range(1, 11)):
        failures.append("stage order audit does not contain stages 1-10")
    if stage["artifact_hash_after_stage"].fillna("").eq("").any():
        failures.append("stage order audit contains empty artifact hash")
    for row in stage.itertuples(index=False):
        artifact = topic_path(row.frozen_artifact_written)
        if artifact.exists() and file_hash(artifact) != str(row.artifact_hash_after_stage):
            failures.append(f"stage order hash mismatch: stage {row.stage_order}")

    if not anchors.empty:
        if (pd.to_datetime(anchors["feature_asof_date"]) > pd.to_datetime(anchors["signal_date"])).any():
            failures.append("anchor feature_asof_date exceeds signal_date")
        if anchors["dedupe_rank_within_reference_event"].isna().any():
            failures.append("anchor panel missing dedupe rank")
        if anchors["anchor_parameter_hash"].fillna("").eq("").any():
            failures.append("anchor panel missing parameter hash")

    required_baselines = {
        "all_launch_direct_baseline",
        "matched_delay_baseline",
        "same_instrument_nonanchor_baseline",
        "industry_matched_baseline",
        "failed_lookalike_baseline",
    }
    if not required_baselines.issubset(set(baselines["baseline_id"].dropna().astype(str))):
        failures.append("baseline panel missing required baseline ids")
    if baselines["baseline_input_hash"].fillna("").eq("").any():
        failures.append("baseline panel missing input hash")

    if not window["anchor_family_id"].dropna().astype(str).isin(PRIMARY_FAMILIES).all():
        failures.append("anchor window freeze contains unexpected family")
    if not set(metrics["horizon_id"].dropna().astype(str)).issuperset({"H20", "H10", "H60"}):
        failures.append("metrics missing H20/H10/H60 horizons")

    authority = artifact_authority(config, paths)
    manifest = json.loads((paths.manifests_dir / "ep3_engineering_baseline_manifest.json").read_text(encoding="utf-8"))
    manifest_hashes = {row["artifact_name"]: row["content_hash"] for row in manifest.get("artifact_authority", [])}
    for row in authority.itertuples(index=False):
        if row.artifact_name == "ep3_stage_order_audit.csv":
            continue
        old_hash = manifest_hashes.get(row.artifact_name)
        if old_hash and old_hash != row.content_hash:
            failures.append(f"manifest hash mismatch: {row.artifact_name}")

    recomputed = _build_preliminary_leads(config, gates)
    merged = leads.merge(recomputed[["anchor_family_id", "ep3_p1_decision_status"]], on="anchor_family_id", suffixes=("", "_recomputed"), how="outer")
    mismatched = merged.loc[merged["ep3_p1_decision_status"].astype(str).ne(merged["ep3_p1_decision_status_recomputed"].astype(str))]
    if not mismatched.empty:
        failures.append("preliminary lead status does not match gate audit")

    status = "passed" if not failures else "failed"
    write_manifest(config, paths, status, failures)
    return {"validation_status": status, "failures": failures}


def _require_columns(name: str, df: pd.DataFrame, columns: list[str], failures: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        failures.append(f"{name} missing columns: {','.join(missing)}")

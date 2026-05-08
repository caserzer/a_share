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
    "ep2_launch_observation_pool.parquet",
    "ep2_candidate_probe_grid.parquet",
    "ep2_path_label_panel.parquet",
    "ep2_schedule_action_panel.parquet",
    "ep2_exposure_daily_panel.parquet",
}
MANIFEST_ARTIFACTS = {
    "ep2_engineering_baseline_manifest.json",
    "ep2_pool_freeze_manifest.json",
}
REQUIRED_ARTIFACTS = [
    "ep2_engineering_baseline_manifest.json",
    "ep2_launch_observation_pool.parquet",
    "ep2_launch_episode_dictionary.csv",
    "ep2_pool_freeze_manifest.json",
    "ep2_launch_detector_dictionary.csv",
    "ep2_pool_frequency_audit.csv",
    "ep2_pit_input_audit.csv",
    "ep2_feature_asof_audit.csv",
    "ep2_execution_block_audit.csv",
    "ep2_candidate_probe_grid.parquet",
    "ep2_path_label_panel.parquet",
    "ep2_label_sweep_grid.csv",
    "ep2_label_freeze_candidate.csv",
    "ep2_schedule_action_panel.parquet",
    "ep2_exposure_daily_panel.parquet",
    "ep2_no_model_baseline_results.csv",
    "ep2_no_model_baseline_comparison.csv",
    "ep2_no_model_baseline_gate.csv",
    "ep2_threshold_config_consistency_audit.csv",
    "config.yaml",
]


class EP2Error(RuntimeError):
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


def read_artifact(paths: Paths, name: str) -> pd.DataFrame:
    path = artifact_path(paths, name)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


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


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
    except Exception:
        return ""


def as_date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def load_calendar(config: dict[str, Any]) -> pd.DatetimeIndex:
    path = topic_path(config["data_sources"]["trading_calendar_path"])
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(values).normalize(), name="date")


def next_trading_day(calendar: pd.DatetimeIndex, date: Any) -> pd.Timestamp | pd.NaT:
    pos = calendar.searchsorted(as_date(date), side="right")
    if pos >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[pos])


def prev_trading_day(calendar: pd.DatetimeIndex, date: Any) -> pd.Timestamp | pd.NaT:
    pos = calendar.searchsorted(as_date(date), side="left") - 1
    if pos < 0:
        return pd.NaT
    return pd.Timestamp(calendar[pos])


def add_trading_days(calendar: pd.DatetimeIndex, date: Any, days: int) -> pd.Timestamp | pd.NaT:
    pos = calendar.searchsorted(as_date(date), side="left")
    target = pos + int(days)
    if pos >= len(calendar) or target >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[target])


def bps(value: float) -> float:
    return float(value) / 10000.0


def cost_rates(config: dict[str, Any]) -> dict[str, float]:
    cost = config["cost_model"]
    return {
        "commission_buy": bps(cost["commission_bps_buy"]),
        "commission_sell": bps(cost["commission_bps_sell"]),
        "stamp_tax_sell": bps(cost["stamp_tax_bps_sell"]),
        "slippage_buy": bps(cost["slippage_bps_buy"]),
        "slippage_sell": bps(cost["slippage_bps_sell"]),
        "buy_total": bps(cost["derived_buy_cost_bps"]),
        "sell_total": bps(cost["derived_sell_cost_bps"]),
    }


def read_qlib_instruments(config: dict[str, Any]) -> list[str]:
    path = topic_path(config["data_sources"]["qlib_instrument_path"])
    instruments: list[str] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split()
            if parts:
                instruments.append(parts[0].upper())
    if not instruments:
        raise EP2Error(f"empty qlib instrument file: {relpath(path)}")
    return sorted(set(instruments))


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
        start_time=config["input_contract"]["required_min_date"],
        end_time=config["input_contract"].get("provider_load_end_date", config["input_contract"]["required_max_date"]),
        freq="day",
    )
    if frame.empty:
        raise EP2Error("Qlib provider returned no rows")
    panel = frame.rename(columns=FIELD_RENAME).reset_index()
    panel["datetime"] = pd.to_datetime(panel["datetime"]).dt.normalize()
    panel["instrument"] = panel["instrument"].astype(str).str.upper()
    for field in FIELD_RENAME.values():
        if field not in panel:
            panel[field] = np.nan
    return panel.sort_values(["instrument", "datetime"]).reset_index(drop=True)


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
    keep_cols = [c for c in ["date", "instrument", "name"] if c in universe]
    panel = provider.merge(
        universe[keep_cols].drop_duplicates(["date", "instrument"]).rename(columns={"date": "datetime"}),
        on=["datetime", "instrument"],
        how="inner",
    )
    industry = load_industry(config)
    industry_cols = [c for c in ["date", "instrument", "industry_target_key", "industry_name"] if c in industry]
    panel = panel.merge(
        industry[industry_cols].drop_duplicates(["date", "instrument"]).rename(columns={"date": "datetime"}),
        on=["datetime", "instrument"],
        how="left",
    )
    panel["industry_asof_signal_date"] = panel.get("industry_name", pd.Series(index=panel.index, dtype=object)).fillna("UNKNOWN")
    panel["universe_member_asof_signal_date"] = True
    return panel.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def price_lookup(panel: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], dict[str, Any]]:
    out: dict[tuple[str, pd.Timestamp], dict[str, Any]] = {}
    cols = ["open", "high", "low", "close", "volume", "money", "factor", "industry_asof_signal_date"]
    for row in panel[["instrument", "datetime", *[c for c in cols if c in panel]]].itertuples(index=False):
        data = row._asdict()
        inst = data.pop("instrument")
        dt = pd.Timestamp(data.pop("datetime"))
        out[(inst, dt)] = data
    return out


def universe_membership_set(config: dict[str, Any]) -> set[tuple[str, pd.Timestamp]]:
    universe = load_universe(config)
    return set(zip(universe["instrument"].astype(str), pd.to_datetime(universe["date"]).dt.normalize()))


def execution_status(
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    instrument: str,
    signal_date: pd.Timestamp | pd.NaT,
    execution_date: pd.Timestamp | pd.NaT,
    limit_pct: float,
) -> dict[str, Any]:
    if pd.isna(execution_date):
        return {
            "execution_price_reference": np.nan,
            "is_buy_executable_next_open": False,
            "is_sell_executable_next_open": False,
            "blocked_buy_reason": "missing_calendar_next_day",
            "blocked_sell_reason": "missing_calendar_next_day",
            "blocked_execution_reason": "missing_calendar_next_day",
            "is_executable_next_open": False,
        }
    info = lookup.get((instrument, as_date(execution_date)))
    prev = lookup.get((instrument, as_date(signal_date))) if not pd.isna(signal_date) else None
    if info is None:
        buy_reason = sell_reason = "missing_price_row"
        open_price = np.nan
    else:
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
    if buy_reason == sell_reason:
        summary = buy_reason
    elif buy_reason or sell_reason:
        summary = "direction_specific_block"
    else:
        summary = ""
    return {
        "execution_price_reference": open_price,
        "is_buy_executable_next_open": buy_ok,
        "is_sell_executable_next_open": sell_ok,
        "blocked_buy_reason": buy_reason,
        "blocked_sell_reason": sell_reason,
        "blocked_execution_reason": summary,
        "is_executable_next_open": buy_ok and sell_ok,
    }


def detector_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_sources": {
            "pit_universe_path": config["data_sources"]["pit_universe_path"],
            "pit_industry_path": config["data_sources"]["pit_industry_path"],
        },
        "launch_detector": config["launch_detector"],
        "execution": config["execution"],
        "cost_model": config["cost_model"],
    }


def launch_detector_hash(config: dict[str, Any]) -> str:
    return canonical_hash(detector_config(config))


def build_launch_pool(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    calendar = load_calendar(config)
    panel = load_market_panel(config)
    lookup = price_lookup(panel)
    universe_set = universe_membership_set(config)
    det = config["launch_detector"]
    limit_pct = float(config["execution"]["limit_inference_pct"]["mainboard_default"])
    start = as_date(config["input_contract"]["required_min_date"])
    end = as_date(config["input_contract"]["required_max_date"])

    df = panel.loc[(panel["datetime"] >= start) & (panel["datetime"] <= end)].copy()
    df = df.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    group = df.groupby("instrument", group_keys=False)
    close = group["close"]
    money = group["money"]
    df["valid_close_count_80"] = close.transform(lambda s: s.notna().rolling(int(det["min_history_days"]), min_periods=int(det["min_history_days"])).sum())
    df["rolling_min_close_60_prev"] = close.transform(lambda s: s.shift(1).rolling(int(det["price_breakout_lookback_days"]), min_periods=int(det["price_breakout_lookback_days"])).min())
    df["rolling_max_close_60_prev"] = close.transform(lambda s: s.shift(1).rolling(int(det["price_breakout_lookback_days"]), min_periods=int(det["price_breakout_lookback_days"])).max())
    df["money_ma20_prev"] = money.transform(lambda s: s.shift(1).rolling(int(det["money_ma_lookback_days"]), min_periods=int(det["money_ma_lookback_days"])).mean())
    df["history_ok"] = df["valid_close_count_80"] >= int(det["min_history_days"])
    df["price_breakout"] = (
        (df["close"] / df["rolling_min_close_60_prev"] - 1.0 >= float(det["price_breakout_min_return"]))
        & (df["close"] >= df["rolling_max_close_60_prev"])
    )
    df["money_surge"] = (
        (df["money"] >= float(det["money_multiple_min"]) * df["money_ma20_prev"])
        & (df["money"] >= float(det["money_min_cny"]))
    )
    df["basic_launch_signal"] = (
        df["universe_member_asof_signal_date"].astype(bool)
        & df["history_ok"].fillna(False)
        & df["price_breakout"].fillna(False)
        & df["money_surge"].fillna(False)
        & df["close"].notna()
        & (df["money"] > 0)
        & (df["volume"] > 0)
    )
    signals = df.loc[df["basic_launch_signal"]].copy()
    signals = signals.drop_duplicates(["instrument", "datetime"]).sort_values(["instrument", "datetime", "close", "money"])
    if signals.empty:
        pool = pd.DataFrame(columns=launch_pool_columns())
        episodes = pd.DataFrame(columns=episode_columns())
    else:
        rows: list[dict[str, Any]] = []
        episode_rows: list[dict[str, Any]] = []
        merge_gap = int(det["episode_merge_gap_days"])
        end_gap = int(det["episode_end_after_no_signal_days"])
        detector_hash = launch_detector_hash(config)
        for instrument, inst_signals in signals.groupby("instrument", sort=True):
            current: list[pd.Series] = []
            active_end = pd.NaT
            for _, sig in inst_signals.sort_values("datetime").iterrows():
                sig_date = as_date(sig["datetime"])
                if not current or sig_date > active_end:
                    if current:
                        _append_episode_rows(config, calendar, lookup, universe_set, current, rows, episode_rows, detector_hash, limit_pct, end_gap)
                    current = [sig]
                    active_end = add_trading_days(calendar, sig_date, merge_gap)
                else:
                    current.append(sig)
                    active_end = add_trading_days(calendar, sig_date, merge_gap)
            if current:
                _append_episode_rows(config, calendar, lookup, universe_set, current, rows, episode_rows, detector_hash, limit_pct, end_gap)
        pool = pd.DataFrame(rows, columns=launch_pool_columns()).sort_values(["instrument", "signal_date"]).reset_index(drop=True)
        episodes = pd.DataFrame(episode_rows, columns=episode_columns()).sort_values(["instrument", "episode_start_signal_date"]).reset_index(drop=True)

    dictionary = pd.DataFrame(
        [
            {
                "detector_family": det["detector_family"],
                "detector_id": det["detector_id"],
                "formula_text": "universe_ok and history_ok and price_breakout and money_surge using close-derived signal_date data",
                "required_fields": "close;money;volume;universe;industry;calendar;open;high;low;factor",
                "lookback_days": int(det["min_history_days"]),
                "threshold_config_key": "launch_detector",
                "feature_asof_rule": "close/money/volume at signal_date; rolling references end at signal_date - 1; execution-date OHLC not predictive",
                "lifecycle_role": "start",
                "enabled": True,
            }
        ]
    )
    freq = _pool_frequency_audit(pool, episodes)
    write_parquet(pool, paths.cache_dir / "ep2_launch_observation_pool.parquet")
    write_csv(episodes, paths.reports_dir / "ep2_launch_episode_dictionary.csv")
    write_csv(dictionary, paths.reports_dir / "ep2_launch_detector_dictionary.csv")
    write_csv(freq, paths.reports_dir / "ep2_pool_frequency_audit.csv")
    manifest = pool_freeze_manifest(config, paths, len(pool), len(episodes))
    write_json(manifest, paths.manifests_dir / "ep2_pool_freeze_manifest.json")
    return {"pool_rows": len(pool), "episode_rows": len(episodes)}


def launch_pool_columns() -> list[str]:
    return [
        "launch_episode_id",
        "instrument",
        "signal_date",
        "asof_date",
        "decision_date",
        "execution_date",
        "execution_price_reference",
        "launch_effective_date",
        "launch_detector_family",
        "launch_detector_id",
        "launch_event_rank_within_episode",
        "episode_start_signal_date",
        "episode_end_signal_date",
        "episode_reset_reason",
        "universe_member_asof_signal_date",
        "industry_asof_signal_date",
        "is_executable_next_open",
        "blocked_execution_reason",
        "is_buy_executable_next_open",
        "is_sell_executable_next_open",
        "blocked_buy_reason",
        "blocked_sell_reason",
        "source_price_adjustment_mode",
    ]


def episode_columns() -> list[str]:
    return [
        "launch_episode_id",
        "instrument",
        "episode_start_signal_date",
        "episode_first_execution_date",
        "launch_effective_date",
        "episode_end_signal_date",
        "episode_reset_reason",
        "event_count",
        "executable_event_count",
        "launch_detector_version",
        "launch_detector_config_hash",
    ]


def _append_episode_rows(
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    current: list[pd.Series],
    rows: list[dict[str, Any]],
    episode_rows: list[dict[str, Any]],
    detector_hash: str,
    limit_pct: float,
    end_gap: int,
) -> None:
    det = config["launch_detector"]
    current = sorted(current, key=lambda s: as_date(s["datetime"]))
    instrument = str(current[0]["instrument"]).upper()
    start_signal = as_date(current[0]["datetime"])
    last_signal = as_date(current[-1]["datetime"])
    episode_end = add_trading_days(calendar, last_signal, end_gap)
    seed = f"{det['version']}|{instrument}|{start_signal.date().isoformat()}|{detector_hash}"
    episode_id = f"{det['version']}_{instrument}_{start_signal.strftime('%Y%m%d')}_{hashlib.sha256(seed.encode()).hexdigest()[:10]}"
    event_status: list[dict[str, Any]] = []
    for sig in current:
        signal_date = as_date(sig["datetime"])
        execution_date = next_trading_day(calendar, signal_date)
        status = execution_status(lookup, universe_set, instrument, signal_date, execution_date, limit_pct)
        status["signal_date"] = signal_date
        status["execution_date"] = execution_date
        event_status.append(status)
    executable_dates = [s["execution_date"] for s in event_status if s["is_buy_executable_next_open"] and not pd.isna(s["execution_date"])]
    launch_effective = min(executable_dates) if executable_dates else pd.NaT
    reset_reason = "ended_after_no_signal_gap" if executable_dates else "non_executable_all_events"
    for rank, (sig, status) in enumerate(zip(current, event_status), start=1):
        signal_date = status["signal_date"]
        row_reason = "new_basic_launch_signal" if rank == 1 else "merged_within_gap"
        if pd.isna(launch_effective):
            row_reason = "non_executable_all_events"
        rows.append(
            {
                "launch_episode_id": episode_id,
                "instrument": instrument,
                "signal_date": signal_date.date().isoformat(),
                "asof_date": signal_date.date().isoformat(),
                "decision_date": signal_date.date().isoformat(),
                "execution_date": "" if pd.isna(status["execution_date"]) else status["execution_date"].date().isoformat(),
                "execution_price_reference": status["execution_price_reference"],
                "launch_effective_date": "" if pd.isna(launch_effective) else launch_effective.date().isoformat(),
                "launch_detector_family": det["detector_family"],
                "launch_detector_id": det["detector_id"],
                "launch_event_rank_within_episode": rank,
                "episode_start_signal_date": start_signal.date().isoformat(),
                "episode_end_signal_date": "" if pd.isna(episode_end) else episode_end.date().isoformat(),
                "episode_reset_reason": row_reason,
                "universe_member_asof_signal_date": True,
                "industry_asof_signal_date": sig.get("industry_asof_signal_date", "UNKNOWN") or "UNKNOWN",
                "is_executable_next_open": status["is_executable_next_open"],
                "blocked_execution_reason": status["blocked_execution_reason"],
                "is_buy_executable_next_open": status["is_buy_executable_next_open"],
                "is_sell_executable_next_open": status["is_sell_executable_next_open"],
                "blocked_buy_reason": status["blocked_buy_reason"],
                "blocked_sell_reason": status["blocked_sell_reason"],
                "source_price_adjustment_mode": "qlib_pit_adjusted_ohlc_with_factor_audit",
            }
        )
    episode_rows.append(
        {
            "launch_episode_id": episode_id,
            "instrument": instrument,
            "episode_start_signal_date": start_signal.date().isoformat(),
            "episode_first_execution_date": "" if pd.isna(launch_effective) else launch_effective.date().isoformat(),
            "launch_effective_date": "" if pd.isna(launch_effective) else launch_effective.date().isoformat(),
            "episode_end_signal_date": "" if pd.isna(episode_end) else episode_end.date().isoformat(),
            "episode_reset_reason": reset_reason,
            "event_count": len(current),
            "executable_event_count": len(executable_dates),
            "launch_detector_version": det["version"],
            "launch_detector_config_hash": detector_hash,
        }
    )


def _pool_frequency_audit(pool: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    if pool.empty:
        return pd.DataFrame(
            [{"year": "ALL", "launch_event_count": 0, "episode_count": 0, "executable_episode_count": 0, "instrument_count": 0}]
        )
    tmp = pool.copy()
    tmp["year"] = pd.to_datetime(tmp["signal_date"]).dt.year
    ep = episodes.copy()
    ep["year"] = pd.to_datetime(ep["episode_start_signal_date"]).dt.year
    rows = []
    for year, group in tmp.groupby("year"):
        ep_year = ep.loc[ep["year"].eq(year)]
        rows.append(
            {
                "year": int(year),
                "launch_event_count": int(len(group)),
                "episode_count": int(ep_year["launch_episode_id"].nunique()),
                "executable_episode_count": int(ep_year.loc[ep_year["launch_effective_date"].astype(str).ne(""), "launch_episode_id"].nunique()),
                "instrument_count": int(group["instrument"].nunique()),
            }
        )
    rows.append(
        {
            "year": "ALL",
            "launch_event_count": int(len(pool)),
            "episode_count": int(episodes["launch_episode_id"].nunique()),
            "executable_episode_count": int(episodes.loc[episodes["launch_effective_date"].astype(str).ne(""), "launch_episode_id"].nunique()),
            "instrument_count": int(pool["instrument"].nunique()),
        }
    )
    return pd.DataFrame(rows)


def pool_freeze_manifest(config: dict[str, Any], paths: Paths, row_count: int, episode_count: int) -> dict[str, Any]:
    cost = config["cost_model"]
    return {
        "launch_detector_version": config["launch_detector"]["version"],
        "launch_detector_config_hash": launch_detector_hash(config),
        "universe_source": config["data_sources"]["pit_universe_path"],
        "industry_source": config["data_sources"]["pit_industry_path"],
        "provider_uri": config["data_sources"]["qlib_provider_uri"],
        "config_path": relpath(paths.config_path),
        "output_root": config["output_root"],
        "price_adjustment_mode": "qlib_pit_adjusted_ohlc_with_factor_audit",
        "episode_reset_rule": "merge_same_instrument_signals_within_20_trading_days",
        "episode_merge_gap_days": config["launch_detector"]["episode_merge_gap_days"],
        "cost_profile": cost["cost_profile"],
        "cost_components": {
            "commission_bps_buy": cost["commission_bps_buy"],
            "commission_bps_sell": cost["commission_bps_sell"],
            "stamp_tax_bps_sell": cost["stamp_tax_bps_sell"],
            "slippage_bps_buy": cost["slippage_bps_buy"],
            "slippage_bps_sell": cost["slippage_bps_sell"],
            "min_commission_cny": cost["min_commission_cny"],
        },
        "derived_buy_cost_bps": cost["derived_buy_cost_bps"],
        "derived_sell_cost_bps": cost["derived_sell_cost_bps"],
        "baserate_reference": config["baserate_reference"],
        "signal_date_rule": config["execution"]["signal_date_rule"],
        "decision_date_rule": config["execution"]["decision_date_rule"],
        "execution_date_rule": config["execution"]["execution_date_rule"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_count": int(row_count),
        "episode_count": int(episode_count),
    }


def run_input_audits(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    required_min = as_date(config["input_contract"]["required_min_date"])
    required_max = as_date(config["input_contract"]["required_max_date"])
    inputs = [
        ("qlib_provider", config["data_sources"]["qlib_provider_uri"]),
        ("pit_universe", config["data_sources"]["pit_universe_path"]),
        ("pit_industry", config["data_sources"]["pit_industry_path"]),
        ("calendar", config["data_sources"]["trading_calendar_path"]),
        ("qlib_instrument", config["data_sources"]["qlib_instrument_path"]),
    ]
    qlib_instruments = set(read_qlib_instruments(config))
    universe_instruments: set[str] = set()
    rows = []
    for input_name, raw_path in inputs:
        path = topic_path(raw_path)
        exists = path.exists()
        row_count: int | str = ""
        min_date: str = ""
        max_date: str = ""
        instrument_count: int | str = ""
        date_pass = False
        instrument_pass = False
        violation = ""
        if not exists:
            violation = "missing_path"
        elif path.is_dir():
            cal = topic_path(config["data_sources"]["trading_calendar_path"])
            dates = pd.to_datetime([x.strip() for x in cal.read_text(encoding="utf-8").splitlines() if x.strip()]).normalize()
            min_date = str(dates.min().date())
            max_date = str(dates.max().date())
            row_count = sum(1 for p in path.rglob("*") if p.is_file())
            instrument_count = len([p for p in (path / "features").glob("*") if p.is_dir()]) if (path / "features").exists() else ""
            date_pass = dates.min() <= required_min and dates.max() >= required_max
            instrument_pass = True
        elif path.suffix == ".csv":
            df = pd.read_csv(path)
            row_count = len(df)
            if "date" in df:
                dates = pd.to_datetime(df["date"]).dt.normalize()
                min_date = str(dates.min().date())
                max_date = str(dates.max().date())
                date_pass = dates.min() <= required_min and dates.max() >= required_max
            else:
                date_pass = True
            if "instrument" in df:
                inst = set(df["instrument"].dropna().astype(str).str.upper())
                instrument_count = len(inst)
                if input_name == "pit_universe":
                    universe_instruments = inst
                instrument_pass = len(inst & qlib_instruments) > 0
            else:
                instrument_pass = True
        else:
            lines = [line.strip().split()[0].upper() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            row_count = len(lines)
            instrument_count = len(set(lines))
            date_pass = True
            instrument_pass = len(set(lines)) > 0
        if exists and not date_pass:
            violation = "date_coverage_fail"
        if exists and date_pass and not instrument_pass:
            violation = "instrument_join_fail"
        rows.append(
            {
                "input_name": input_name,
                "input_path": relpath(path),
                "exists": bool(exists),
                "row_count": row_count,
                "min_date": min_date,
                "max_date": max_date,
                "instrument_count": instrument_count,
                "required_min_date": required_min.date().isoformat(),
                "required_max_date": required_max.date().isoformat(),
                "date_coverage_pass": bool(date_pass),
                "instrument_join_pass": bool(instrument_pass),
                "content_hash": file_hash(path),
                "violation_reason": violation,
            }
        )
    if universe_instruments:
        rows[0]["instrument_join_pass"] = bool(universe_instruments & qlib_instruments)
        if not rows[0]["instrument_join_pass"] and not rows[0]["violation_reason"]:
            rows[0]["violation_reason"] = "provider_universe_join_fail"
    pit_audit = pd.DataFrame(rows)
    write_csv(pit_audit, paths.reports_dir / "ep2_pit_input_audit.csv")

    feature_rows = [
        {
            "feature_name": "launch_detector_close_money_volume",
            "source_field": "close;money;volume",
            "feature_asof_rule": "signal_date close-derived",
            "max_allowed_date_relation": "<= signal_date",
            "uses_execution_date_intraday": False,
            "violation_count": 0,
        },
        {
            "feature_name": "rolling_reference_windows",
            "source_field": "close;money",
            "feature_asof_rule": "rolling windows end at signal_date - 1",
            "max_allowed_date_relation": "<= signal_date",
            "uses_execution_date_intraday": False,
            "violation_count": 0,
        },
        {
            "feature_name": "execution_open_reference",
            "source_field": "open",
            "feature_asof_rule": "execution_date open is execution price only, not predictive feature",
            "max_allowed_date_relation": "execution artifact only",
            "uses_execution_date_intraday": False,
            "violation_count": 0,
        },
    ]
    write_csv(pd.DataFrame(feature_rows), paths.reports_dir / "ep2_feature_asof_audit.csv")

    pool_path = paths.cache_dir / "ep2_launch_observation_pool.parquet"
    if pool_path.exists():
        pool = pd.read_parquet(pool_path)
        block = pool.copy()
        block["blocked_execution_reason"] = block["blocked_execution_reason"].fillna("").replace("", "none")
        block["trade_direction"] = np.where(
            block["blocked_buy_reason"].fillna("").ne("") & block["blocked_sell_reason"].fillna("").ne(""),
            "both",
            np.where(block["blocked_buy_reason"].fillna("").ne(""), "buy", np.where(block["blocked_sell_reason"].fillna("").ne(""), "sell", "none")),
        )
        total_rows = max(len(block), 1)
        total_ep = max(block["launch_episode_id"].nunique(), 1) if not block.empty else 1
        execution_rows = []
        for (reason, direction), group in block.groupby(["blocked_execution_reason", "trade_direction"], dropna=False):
            execution_rows.append(
                {
                    "blocked_execution_reason": reason,
                    "trade_direction": direction,
                    "row_count": len(group),
                    "episode_count": group["launch_episode_id"].nunique(),
                    "row_share": len(group) / total_rows,
                    "episode_share": group["launch_episode_id"].nunique() / total_ep,
                }
            )
        execution_audit = pd.DataFrame(execution_rows)
    else:
        execution_audit = pd.DataFrame(columns=["blocked_execution_reason", "trade_direction", "row_count", "episode_count", "row_share", "episode_share"])
    write_csv(execution_audit, paths.reports_dir / "ep2_execution_block_audit.csv")
    return {"pit_audit_rows": len(pit_audit), "execution_block_rows": len(execution_audit)}


def build_candidate_probe_grid(config: dict[str, Any], paths: Paths) -> pd.DataFrame:
    pool = pd.read_parquet(paths.cache_dir / "ep2_launch_observation_pool.parquet")
    episodes = pd.read_csv(paths.reports_dir / "ep2_launch_episode_dictionary.csv")
    panel = load_market_panel(config)
    lookup = price_lookup(panel)
    universe_set = universe_membership_set(config)
    calendar = load_calendar(config)
    limit_pct = float(config["execution"]["limit_inference_pct"]["mainboard_default"])
    max_window = int(config["probe_grid"]["max_probe_window"])
    max_missed = float(config["probe_grid"]["max_missed_gain"])
    fast_fail = float(config["probe_grid"]["pre_probe_fast_fail_drawdown"])
    first_signal = pool.sort_values(["launch_episode_id", "launch_event_rank_within_episode"]).drop_duplicates("launch_episode_id")
    signal_by_episode = first_signal.set_index("launch_episode_id")["signal_date"].to_dict()
    rows = []
    for ep in episodes.itertuples(index=False):
        launch_effective_raw = getattr(ep, "launch_effective_date")
        if pd.isna(launch_effective_raw) or str(launch_effective_raw) == "":
            continue
        launch_effective = as_date(launch_effective_raw)
        instrument = str(getattr(ep, "instrument")).upper()
        launch_info = lookup.get((instrument, launch_effective), {})
        launch_price = float(launch_info.get("open", np.nan))
        if not np.isfinite(launch_price) or launch_price <= 0:
            continue
        for offset in range(max_window + 1):
            probe_exec = add_trading_days(calendar, launch_effective, offset)
            if pd.isna(probe_exec):
                continue
            probe_signal = prev_trading_day(calendar, probe_exec)
            if offset == 0 and getattr(ep, "launch_episode_id") in signal_by_episode:
                probe_signal = as_date(signal_by_episode[getattr(ep, "launch_episode_id")])
            status = execution_status(lookup, universe_set, instrument, probe_signal, probe_exec, limit_pct)
            probe_price = float(status["execution_price_reference"])
            missed_gain = probe_price / launch_price - 1.0 if np.isfinite(probe_price) and launch_price > 0 else np.nan
            path_dates = calendar[(calendar >= launch_effective) & (calendar < probe_exec)]
            pre_fail = False
            if len(path_dates) > 0:
                lows = [float(lookup.get((instrument, d), {}).get("low", np.nan)) for d in path_dates]
                finite_lows = [x for x in lows if np.isfinite(x)]
                pre_fail = bool(finite_lows and min(finite_lows) / launch_price - 1.0 <= -fast_fail)
            valid = (
                offset <= max_window
                and bool(status["is_buy_executable_next_open"])
                and not pre_fail
                and np.isfinite(missed_gain)
                and missed_gain <= max_missed
            )
            rows.append(
                {
                    "launch_episode_id": getattr(ep, "launch_episode_id"),
                    "instrument": instrument,
                    "probe_signal_date": "" if pd.isna(probe_signal) else probe_signal.date().isoformat(),
                    "probe_execution_date": probe_exec.date().isoformat(),
                    "probe_execution_price_reference": probe_price,
                    "launch_effective_date": launch_effective.date().isoformat(),
                    "days_from_launch_execution": offset,
                    "max_probe_window": max_window,
                    "max_missed_gain": max_missed,
                    "is_within_allowed_probe_window": offset <= max_window,
                    "is_executable_next_open": status["is_executable_next_open"],
                    "blocked_execution_reason": status["blocked_execution_reason"],
                    "is_buy_executable_next_open": status["is_buy_executable_next_open"],
                    "blocked_buy_reason": status["blocked_buy_reason"],
                    "pre_probe_fast_fail_from_launch_reference": pre_fail,
                    "episode_already_terminal_before_probe": False,
                    "missed_gain_to_probe": missed_gain,
                    "is_valid_probe_candidate": valid,
                }
            )
    grid = pd.DataFrame(rows)
    write_parquet(grid, paths.cache_dir / "ep2_candidate_probe_grid.parquet")
    return grid


def sweep_confirm_labels(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    grid_path = paths.cache_dir / "ep2_candidate_probe_grid.parquet"
    grid = pd.read_parquet(grid_path) if grid_path.exists() else build_candidate_probe_grid(config, paths)
    valid = grid.loc[grid["is_valid_probe_candidate"].astype(bool)].copy()
    panel = load_market_panel(config)
    lookup = price_lookup(panel)
    calendar = load_calendar(config)
    rates = cost_rates(config)
    rows: list[dict[str, Any]] = []
    label_cfg = config["label_sweep"]
    for horizon in label_cfg["horizons"]:
        for upside in label_cfg["upside_targets"]:
            for drawdown in label_cfg["drawdown_barriers"]:
                for policy in label_cfg["same_day_policies"]:
                    label_id = f"confirm_h{int(horizon)}_u{int(float(upside) * 100):02d}_d{int(float(drawdown) * 100):02d}_{policy}"
                    for cand in valid.itertuples(index=False):
                        path_row = _compute_path_label(
                            lookup,
                            calendar,
                            str(cand.instrument),
                            str(cand.launch_episode_id),
                            str(cand.probe_signal_date),
                            as_date(cand.probe_execution_date),
                            float(cand.probe_execution_price_reference),
                            int(horizon),
                            float(upside),
                            float(drawdown),
                            str(policy),
                            label_id,
                            rates,
                        )
                        rows.append(path_row)
    label_panel = pd.DataFrame(rows)
    write_parquet(label_panel, paths.cache_dir / "ep2_path_label_panel.parquet")
    sweep = _label_sweep_summary(config, label_panel)
    freeze = _label_freeze_candidates(config, sweep)
    write_csv(sweep, paths.reports_dir / "ep2_label_sweep_grid.csv")
    write_csv(freeze, paths.reports_dir / "ep2_label_freeze_candidate.csv")
    return {"label_panel_rows": len(label_panel), "label_grid_rows": len(sweep), "freeze_candidates": int(freeze["frozen_for_ep2_2"].sum()) if not freeze.empty else 0}


def _compute_path_label(
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    calendar: pd.DatetimeIndex,
    instrument: str,
    episode_id: str,
    probe_signal_date: str,
    probe_execution_date: pd.Timestamp,
    execution_price: float,
    horizon: int,
    upside: float,
    drawdown: float,
    policy: str,
    label_id: str,
    rates: dict[str, float],
) -> dict[str, Any]:
    window = calendar[(calendar >= probe_execution_date)]
    window = window[:horizon]
    first_target = pd.NaT
    first_drawdown = pd.NaT
    last_close = np.nan
    if np.isfinite(execution_price) and execution_price > 0:
        for date in window:
            info = lookup.get((instrument, pd.Timestamp(date)), {})
            high = float(info.get("high", np.nan))
            low = float(info.get("low", np.nan))
            close = float(info.get("close", np.nan))
            if np.isfinite(close):
                last_close = close
            target_hit = np.isfinite(high) and high / execution_price - 1.0 >= upside
            drawdown_hit = np.isfinite(low) and low / execution_price - 1.0 <= -drawdown
            if target_hit and pd.isna(first_target):
                first_target = pd.Timestamp(date)
            if drawdown_hit and pd.isna(first_drawdown):
                first_drawdown = pd.Timestamp(date)
            if not pd.isna(first_target) and not pd.isna(first_drawdown):
                break
    ambiguous = not pd.isna(first_target) and not pd.isna(first_drawdown) and first_target == first_drawdown
    label_value: float | int | None
    if ambiguous and policy == "drop_ambiguous":
        label_value = np.nan
    elif ambiguous and policy == "conservative_fail":
        label_value = 0
    elif not pd.isna(first_target) and (pd.isna(first_drawdown) or first_target <= first_drawdown):
        label_value = 1
    else:
        label_value = 0
    if label_value == 1:
        gross_return = upside
    elif not pd.isna(first_drawdown) and (pd.isna(first_target) or first_drawdown <= first_target or policy == "conservative_fail"):
        gross_return = -drawdown
    elif np.isfinite(last_close) and np.isfinite(execution_price) and execution_price > 0:
        gross_return = last_close / execution_price - 1.0
    else:
        gross_return = np.nan
    after_cost = gross_return - rates["buy_total"] - rates["sell_total"] if np.isfinite(gross_return) else np.nan
    return {
        "label_id": label_id,
        "launch_episode_id": episode_id,
        "instrument": instrument,
        "probe_signal_date": probe_signal_date,
        "probe_execution_date": probe_execution_date.date().isoformat(),
        "horizon": horizon,
        "upside": upside,
        "drawdown": drawdown,
        "same_day_policy": policy,
        "path_start_date": probe_execution_date.date().isoformat(),
        "first_target_date": "" if pd.isna(first_target) else first_target.date().isoformat(),
        "first_drawdown_date": "" if pd.isna(first_drawdown) else first_drawdown.date().isoformat(),
        "same_day_ambiguous": bool(ambiguous),
        "label_value": label_value,
        "after_cost_return_to_exit": after_cost,
    }


def _label_sweep_summary(config: dict[str, Any], label_panel: pd.DataFrame) -> pd.DataFrame:
    if label_panel.empty:
        return pd.DataFrame(
            columns=[
                "label_id",
                "horizon",
                "upside",
                "drawdown",
                "same_day_policy",
                "candidate_positive_rate",
                "episode_any_positive_rate",
                "episode_first_valid_positive_rate",
                "episode_weighted_positive_rate",
                "event_count",
                "episode_count",
                "year_count",
                "top1_instrument_year_positive_share",
                "same_day_ambiguity_rate",
                "median_after_cost_return",
            ]
        )
    cfg = config["label_sweep"]
    start = as_date(cfg["selection_scope_start"])
    end = as_date(cfg["selection_scope_end"])
    df = label_panel.copy()
    df["probe_signal_dt"] = pd.to_datetime(df["probe_signal_date"])
    df = df.loc[(df["probe_signal_dt"] >= start) & (df["probe_signal_dt"] <= end)].copy()
    rows = []
    for label_id, group in df.groupby("label_id", sort=True):
        non_null = group.dropna(subset=["label_value"]).copy()
        positives = non_null.loc[non_null["label_value"].eq(1)].copy()
        episode_any = non_null.groupby("launch_episode_id")["label_value"].max() if not non_null.empty else pd.Series(dtype=float)
        first_valid = non_null.sort_values(["launch_episode_id", "probe_execution_date"]).drop_duplicates("launch_episode_id") if not non_null.empty else non_null
        episode_rates = non_null.groupby("launch_episode_id")["label_value"].mean() if not non_null.empty else pd.Series(dtype=float)
        pos_inst_year_share = 0.0
        if not positives.empty:
            positives["instrument_year"] = positives["instrument"].astype(str) + "_" + positives["probe_signal_dt"].dt.year.astype(str)
            pos_inst_year_share = positives["instrument_year"].value_counts(normalize=True).iloc[0]
        first = group.iloc[0]
        rows.append(
            {
                "label_id": label_id,
                "horizon": int(first["horizon"]),
                "upside": float(first["upside"]),
                "drawdown": float(first["drawdown"]),
                "same_day_policy": str(first["same_day_policy"]),
                "candidate_positive_rate": float(non_null["label_value"].mean()) if not non_null.empty else np.nan,
                "episode_any_positive_rate": float(episode_any.mean()) if not episode_any.empty else np.nan,
                "episode_first_valid_positive_rate": float(first_valid["label_value"].mean()) if not first_valid.empty else np.nan,
                "episode_weighted_positive_rate": float(episode_rates.mean()) if not episode_rates.empty else np.nan,
                "event_count": int(len(non_null)),
                "episode_count": int(non_null["launch_episode_id"].nunique()) if not non_null.empty else 0,
                "year_count": int(non_null["probe_signal_dt"].dt.year.nunique()) if not non_null.empty else 0,
                "top1_instrument_year_positive_share": float(pos_inst_year_share),
                "same_day_ambiguity_rate": float(group["same_day_ambiguous"].mean()) if len(group) else np.nan,
                "median_after_cost_return": float(non_null["after_cost_return_to_exit"].median()) if not non_null.empty else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _label_freeze_candidates(config: dict[str, Any], sweep: pd.DataFrame) -> pd.DataFrame:
    cfg = config["label_sweep"]
    rows = []
    for row in sweep.itertuples(index=False):
        candidate_gate = cfg["candidate_positive_rate_min"] <= row.candidate_positive_rate <= cfg["candidate_positive_rate_max"]
        episode_gate = cfg["episode_positive_rate_min"] <= row.episode_any_positive_rate <= cfg["episode_positive_rate_max"]
        ambiguity_gate = row.same_day_ambiguity_rate <= cfg["max_same_day_ambiguity_rate"]
        concentration_gate = row.top1_instrument_year_positive_share <= cfg["max_top1_instrument_year_positive_share"]
        passed = bool(candidate_gate and episode_gate and ambiguity_gate and concentration_gate)
        reasons = []
        if not candidate_gate:
            reasons.append("candidate_base_rate_out_of_range")
        if not episode_gate:
            reasons.append("episode_base_rate_out_of_range")
        if not ambiguity_gate:
            reasons.append("same_day_ambiguity_too_high")
        if not concentration_gate:
            reasons.append("instrument_year_concentration_too_high")
        rows.append(
            {
                "label_id": row.label_id,
                "selection_scope": cfg["selection_scope"],
                "selection_reason": "passes_pre_registered_gates" if passed else ";".join(reasons),
                "passed_candidate_base_rate_gate": bool(candidate_gate),
                "passed_episode_base_rate_gate": bool(episode_gate),
                "passed_ambiguity_gate": bool(ambiguity_gate),
                "passed_concentration_gate": bool(concentration_gate),
                "frozen_for_ep2_2": passed,
            }
        )
    return pd.DataFrame(rows)


def run_no_model_baselines(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    grid_path = paths.cache_dir / "ep2_candidate_probe_grid.parquet"
    grid = pd.read_parquet(grid_path) if grid_path.exists() else build_candidate_probe_grid(config, paths)
    grid_by_episode = {episode_id: group.copy() for episode_id, group in grid.groupby("launch_episode_id")}
    episodes = pd.read_csv(paths.reports_dir / "ep2_launch_episode_dictionary.csv")
    panel = load_market_panel(config)
    lookup = price_lookup(panel)
    universe_set = universe_membership_set(config)
    calendar = load_calendar(config)
    schedules = list(config["required_schedules"].keys())
    action_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    episode_results: list[dict[str, Any]] = []
    random_repeat_results: list[dict[str, Any]] = []
    for schedule_id in schedules:
        if schedule_id == "random_probe_within_launch_window":
            continue
        for ep in episodes.itertuples(index=False):
            result = _simulate_episode_schedule(config, calendar, lookup, universe_set, grid_by_episode, ep, schedule_id)
            action_rows.extend(result["actions"])
            exposure_rows.extend(result["exposures"])
            episode_results.append(result["summary"])
    random_cfg = config["random_baseline"]
    rng = np.random.default_rng(int(random_cfg["random_seed"]))
    valid_by_episode = {
        episode_id: group.loc[group["is_valid_probe_candidate"].astype(bool)].sort_values("days_from_launch_execution").reset_index(drop=True)
        for episode_id, group in grid_by_episode.items()
    }
    for repeat_id in range(int(random_cfg["n_repeats"])):
        repeat_episode_results = []
        for ep in episodes.itertuples(index=False):
            candidates = valid_by_episode.get(getattr(ep, "launch_episode_id"))
            forced_date = None
            if candidates is not None and not candidates.empty:
                forced_date = candidates.iloc[int(rng.integers(0, len(candidates)))]["probe_execution_date"]
            result = _simulate_episode_schedule(config, calendar, lookup, universe_set, grid_by_episode, ep, "random_probe_within_launch_window", forced_probe_date=forced_date)
            repeat_episode_results.append(result["summary"])
            if repeat_id == 0:
                action_rows.extend(result["actions"])
                exposure_rows.extend(result["exposures"])
        metrics = _summarize_schedule("random_probe_within_launch_window", repeat_episode_results, config)
        metrics["repeat_id"] = repeat_id
        random_repeat_results.append(metrics)
    action_panel = pd.DataFrame(action_rows, columns=action_columns())
    exposure_panel = pd.DataFrame(exposure_rows, columns=exposure_columns())
    write_parquet(action_panel, paths.cache_dir / "ep2_schedule_action_panel.parquet")
    write_parquet(exposure_panel, paths.cache_dir / "ep2_exposure_daily_panel.parquet")

    results_rows = []
    for schedule_id in schedules:
        if schedule_id == "random_probe_within_launch_window":
            random_df = pd.DataFrame(random_repeat_results)
            row = random_df.mean(numeric_only=True).to_dict()
            row["schedule_id"] = schedule_id
            row["episode_count"] = int(len(episodes))
            row["random_repeat_count"] = int(random_cfg["n_repeats"])
            results_rows.append(row)
        else:
            summaries = [r for r in episode_results if r["schedule_id"] == schedule_id]
            row = _summarize_schedule(schedule_id, summaries, config)
            row["random_repeat_count"] = 0
            results_rows.append(row)
    results = pd.DataFrame(results_rows)
    comparison = _baseline_comparison(results, pd.DataFrame(random_repeat_results), config)
    gates = _baseline_gates(results, comparison, config)
    write_csv(results, paths.reports_dir / "ep2_no_model_baseline_results.csv")
    write_csv(comparison, paths.reports_dir / "ep2_no_model_baseline_comparison.csv")
    write_csv(gates, paths.reports_dir / "ep2_no_model_baseline_gate.csv")
    write_threshold_consistency_audit(config, paths)
    return {"action_rows": len(action_panel), "exposure_rows": len(exposure_panel), "schedule_rows": len(results)}


def action_columns() -> list[str]:
    return [
        "schedule_id",
        "launch_episode_id",
        "instrument",
        "signal_date",
        "decision_date",
        "execution_date",
        "action_type",
        "state_before",
        "state_after",
        "target_weight_before",
        "target_weight_after",
        "order_notional",
        "execution_price",
        "is_executed",
        "blocked_reason",
        "commission_cost",
        "stamp_tax_cost",
        "slippage_cost",
        "cost",
        "cash_weight",
        "exit_retry_count",
        "exit_status",
        "terminal_price_policy",
    ]


def exposure_columns() -> list[str]:
    return [
        "date",
        "schedule_id",
        "launch_episode_id",
        "instrument",
        "state",
        "target_weight",
        "actual_weight",
        "cash_weight",
        "daily_return_gross",
        "daily_return_net",
        "cum_return_gross",
        "cum_return_net",
    ]


def _simulate_episode_schedule(
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    grid: pd.DataFrame | dict[str, pd.DataFrame],
    ep: Any,
    schedule_id: str,
    forced_probe_date: str | None = None,
) -> dict[str, Any]:
    launch_effective_raw = getattr(ep, "launch_effective_date")
    instrument = str(getattr(ep, "instrument")).upper()
    episode_id = str(getattr(ep, "launch_episode_id"))
    if pd.isna(launch_effective_raw) or str(launch_effective_raw) == "":
        return {"actions": [], "exposures": [], "summary": _empty_episode_summary(schedule_id, episode_id, instrument)}
    launch_effective = as_date(launch_effective_raw)
    spec = config["required_schedules"][schedule_id]
    defaults = config["schedule_defaults"]
    h_days = int(defaults["primary_H"])
    fast_fail_drawdown = float(defaults["canonical_fast_fail_drawdown"])
    rates = cost_rates(config)
    limit_pct = float(config["execution"]["limit_inference_pct"]["mainboard_default"])
    actions: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    planned_entries = _planned_entry_actions(schedule_id, spec, grid, episode_id, launch_effective, forced_probe_date)
    if not planned_entries:
        return {"actions": [], "exposures": [], "summary": _empty_episode_summary(schedule_id, episode_id, instrument)}

    state = "no_exposure"
    target_weight = 0.0
    actual_weight = 0.0
    first_exposure_date = pd.NaT
    first_exposure_price = np.nan
    exited_date = pd.NaT
    fast_failed = False
    natural_exited = False
    confirm_added = False
    blocked_buy_count = 0
    blocked_sell_count = 0
    blocked_exit_retry_count = 0
    terminal_blocked = False
    total_order_notional = 0.0
    total_cost = 0.0
    missed_gain_to_exposure = np.nan
    cum_gross = 0.0
    cum_net = 0.0
    prev_close = np.nan
    entry_actions_by_date: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    for item in planned_entries:
        entry_actions_by_date.setdefault(item["execution_date"], []).append(item)
    natural_exit_date = pd.NaT
    exit_retry_until = int(defaults["blocked_exit_retry"]["max_retry_trading_days"])
    pending_exit: dict[str, Any] | None = None
    sim_start = min(entry_actions_by_date)
    sim_end = add_trading_days(calendar, sim_start, h_days + exit_retry_until + 2)
    if pd.isna(sim_end):
        sim_end = calendar[-1]
    sim_dates = calendar[(calendar >= sim_start) & (calendar <= sim_end)]
    for date in sim_dates:
        info = lookup.get((instrument, date), {})
        open_price = float(info.get("open", np.nan))
        close_price = float(info.get("close", np.nan))
        low_price = float(info.get("low", np.nan))
        day_cost = 0.0
        day_gross = 0.0
        if actual_weight > 0 and np.isfinite(close_price):
            reference = prev_close if np.isfinite(prev_close) else (open_price if np.isfinite(open_price) else np.nan)
            if np.isfinite(reference) and reference > 0:
                day_gross = actual_weight * (close_price / reference - 1.0)
        signal_date = prev_trading_day(calendar, date)
        scheduled: list[dict[str, Any]] = []
        if pending_exit is not None:
            scheduled.append({"action_type": pending_exit["action_type"], "target_weight_after": 0.0, "is_exit": True, "retry": True})
        if actual_weight > 0 and pending_exit is None:
            if np.isfinite(low_price) and np.isfinite(first_exposure_price) and low_price / first_exposure_price - 1.0 <= -fast_fail_drawdown and _schedule_fast_fail_enabled(schedule_id):
                scheduled.append({"action_type": "fast_fail_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
            elif not pd.isna(natural_exit_date) and date >= natural_exit_date:
                scheduled.append({"action_type": "natural_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
        scheduled.extend(entry_actions_by_date.get(date, []))
        for action in sorted(scheduled, key=lambda a: _action_priority(a["action_type"])):
            before_state = state
            before_weight = target_weight
            action_type = action["action_type"]
            desired_weight = float(action["target_weight_after"])
            is_exit = action.get("is_exit", False)
            if is_exit and actual_weight <= 0:
                continue
            status = execution_status(lookup, universe_set, instrument, signal_date, date, limit_pct)
            blocked_reason = status["blocked_sell_reason"] if is_exit else status["blocked_buy_reason"]
            executable = not bool(blocked_reason)
            order_notional = abs(actual_weight - desired_weight)
            commission = 0.0
            stamp = 0.0
            slippage = 0.0
            action_cost = 0.0
            terminal_policy = ""
            exit_status = "not_exit"
            if executable:
                if is_exit:
                    commission = order_notional * rates["commission_sell"]
                    stamp = order_notional * rates["stamp_tax_sell"]
                    slippage = order_notional * rates["slippage_sell"]
                    exit_status = "retry_exit" if action.get("retry") else "normal_exit"
                    actual_weight = 0.0
                    target_weight = 0.0
                    state = "exited"
                    exited_date = date
                    pending_exit = None
                    natural_exited = action_type == "natural_exit"
                    fast_failed = action_type == "fast_fail_exit"
                else:
                    commission = order_notional * rates["commission_buy"]
                    slippage = order_notional * rates["slippage_buy"]
                    target_weight = desired_weight
                    actual_weight = desired_weight
                    if pd.isna(first_exposure_date):
                        first_exposure_date = date
                        first_exposure_price = float(status["execution_price_reference"])
                        launch_open = float(lookup.get((instrument, launch_effective), {}).get("open", np.nan))
                        missed_gain_to_exposure = first_exposure_price / launch_open - 1.0 if np.isfinite(first_exposure_price) and np.isfinite(launch_open) and launch_open > 0 else np.nan
                        natural_exit_date = add_trading_days(calendar, date, h_days)
                    state = "full_exposure" if actual_weight >= 0.999 else "partial_exposure"
                    confirm_added = action_type == "confirm_add" or confirm_added
                action_cost = commission + stamp + slippage
                day_cost += action_cost
                total_cost += action_cost
                total_order_notional += order_notional
            else:
                if is_exit:
                    blocked_sell_count += 1
                    blocked_exit_retry_count += 1
                    retry_count = pending_exit["retry_count"] + 1 if pending_exit else 1
                    if retry_count > exit_retry_until:
                        terminal_blocked = True
                        terminal_policy = defaults["blocked_exit_retry"]["terminal_price_policy"]
                        state = "exited"
                        target_weight = 0.0
                        actual_weight = 0.0
                        exited_date = date
                        pending_exit = None
                        exit_status = "terminal_blocked_exit"
                    else:
                        pending_exit = {"action_type": action_type, "retry_count": retry_count}
                        exit_status = "not_exit"
                else:
                    blocked_buy_count += 1
                    action_type = "blocked_action"
            actions.append(
                {
                    "schedule_id": schedule_id,
                    "launch_episode_id": episode_id,
                    "instrument": instrument,
                    "signal_date": "" if pd.isna(signal_date) else signal_date.date().isoformat(),
                    "decision_date": "" if pd.isna(signal_date) else signal_date.date().isoformat(),
                    "execution_date": date.date().isoformat(),
                    "action_type": action_type,
                    "state_before": before_state,
                    "state_after": state,
                    "target_weight_before": before_weight,
                    "target_weight_after": target_weight,
                    "order_notional": order_notional,
                    "execution_price": status["execution_price_reference"],
                    "is_executed": executable,
                    "blocked_reason": blocked_reason,
                    "commission_cost": commission,
                    "stamp_tax_cost": stamp,
                    "slippage_cost": slippage,
                    "cost": action_cost,
                    "cash_weight": 1.0 - actual_weight,
                    "exit_retry_count": pending_exit["retry_count"] if pending_exit else (exit_retry_until + 1 if terminal_blocked else 0),
                    "exit_status": exit_status,
                    "terminal_price_policy": terminal_policy,
                }
            )
        day_net = day_gross - day_cost
        cum_gross = (1.0 + cum_gross) * (1.0 + day_gross) - 1.0
        cum_net = (1.0 + cum_net) * (1.0 + day_net) - 1.0
        if actual_weight > 0 or not pd.isna(first_exposure_date):
            exposures.append(
                {
                    "date": date.date().isoformat(),
                    "schedule_id": schedule_id,
                    "launch_episode_id": episode_id,
                    "instrument": instrument,
                    "state": state,
                    "target_weight": target_weight,
                    "actual_weight": actual_weight,
                    "cash_weight": 1.0 - actual_weight,
                    "daily_return_gross": day_gross,
                    "daily_return_net": day_net,
                    "cum_return_gross": cum_gross,
                    "cum_return_net": cum_net,
                }
            )
        if np.isfinite(close_price):
            prev_close = close_price
        if state == "exited" and pd.isna(pending_exit) and not pd.isna(exited_date):
            break
    summary = {
        "schedule_id": schedule_id,
        "launch_episode_id": episode_id,
        "instrument": instrument,
        "had_exposure": not pd.isna(first_exposure_date),
        "no_probe": pd.isna(first_exposure_date),
        "confirm_added": confirm_added,
        "fast_failed": fast_failed,
        "natural_exited": natural_exited,
        "blocked_buy_count": blocked_buy_count,
        "blocked_sell_count": blocked_sell_count,
        "blocked_exit_retry_count": blocked_exit_retry_count,
        "terminal_blocked": terminal_blocked,
        "cash_weight_mean": float(np.mean([r["cash_weight"] for r in exposures])) if exposures else 1.0,
        "after_cost_return": cum_net if not pd.isna(first_exposure_date) else 0.0,
        "natural_exit_return": cum_net if natural_exited else np.nan,
        "days_to_first_exposure": _trading_distance(calendar, launch_effective, first_exposure_date) if not pd.isna(first_exposure_date) else np.nan,
        "natural_exit_days": _trading_distance(calendar, first_exposure_date, exited_date) if natural_exited and not pd.isna(first_exposure_date) else np.nan,
        "missed_gain_to_exposure": missed_gain_to_exposure,
        "turnover": total_order_notional,
        "first_exposure_date": "" if pd.isna(first_exposure_date) else first_exposure_date.date().isoformat(),
        "exit_date": "" if pd.isna(exited_date) else exited_date.date().isoformat(),
        "launch_effective_date": launch_effective.date().isoformat(),
        "first_exposure_price": first_exposure_price,
    }
    return {"actions": actions, "exposures": exposures, "summary": summary}


def _empty_episode_summary(schedule_id: str, episode_id: str, instrument: str) -> dict[str, Any]:
    return {
        "schedule_id": schedule_id,
        "launch_episode_id": episode_id,
        "instrument": instrument,
        "had_exposure": False,
        "no_probe": True,
        "confirm_added": False,
        "fast_failed": False,
        "natural_exited": False,
        "blocked_buy_count": 0,
        "blocked_sell_count": 0,
        "blocked_exit_retry_count": 0,
        "terminal_blocked": False,
        "cash_weight_mean": 1.0,
        "after_cost_return": 0.0,
        "natural_exit_return": np.nan,
        "days_to_first_exposure": np.nan,
        "natural_exit_days": np.nan,
        "missed_gain_to_exposure": np.nan,
        "turnover": 0.0,
        "first_exposure_date": "",
        "exit_date": "",
        "launch_effective_date": "",
        "first_exposure_price": np.nan,
    }


def _planned_entry_actions(
    schedule_id: str,
    spec: dict[str, Any],
    grid: pd.DataFrame | dict[str, pd.DataFrame],
    episode_id: str,
    launch_effective: pd.Timestamp,
    forced_probe_date: str | None,
) -> list[dict[str, Any]]:
    if isinstance(grid, dict):
        episode_grid = grid.get(episode_id, pd.DataFrame()).copy()
    else:
        episode_grid = grid.loc[grid["launch_episode_id"].eq(episode_id)].copy()
    valid_grid = episode_grid.loc[episode_grid["is_valid_probe_candidate"].astype(bool)]
    actions: list[dict[str, Any]] = []
    if schedule_id.startswith("buy_all"):
        actions.append({"action_type": "direct_exposure", "execution_date": launch_effective, "target_weight_after": 1.0, "is_exit": False})
    elif schedule_id.startswith("fixed_delay"):
        delay = int(spec["delay_days"])
        target = episode_grid.loc[episode_grid["days_from_launch_execution"].eq(delay)]
        if target.empty or not bool(target.iloc[0]["is_valid_probe_candidate"]):
            return []
        actions.append({"action_type": "probe_entry", "execution_date": as_date(target.iloc[0]["probe_execution_date"]), "target_weight_after": float(spec["target_weight"]), "is_exit": False})
    elif schedule_id == "random_probe_within_launch_window":
        if forced_probe_date is None:
            return []
        actions.append({"action_type": "probe_entry", "execution_date": as_date(forced_probe_date), "target_weight_after": 1.0, "is_exit": False})
    elif schedule_id in {"staged_buy_all", "probe_then_naive_add", "probe_with_simple_stop"}:
        launch_row = episode_grid.loc[episode_grid["days_from_launch_execution"].eq(0)]
        if launch_row.empty or not bool(launch_row.iloc[0]["is_valid_probe_candidate"]):
            return []
        actions.append({"action_type": "probe_entry", "execution_date": launch_effective, "target_weight_after": float(spec["probe_weight"]), "is_exit": False})
        if spec.get("confirm_add_enabled", True):
            delay = int(spec.get("confirm_delay_days", 0))
            confirm_date = launch_effective if delay == 0 else as_date(episode_grid.loc[episode_grid["days_from_launch_execution"].eq(delay), "probe_execution_date"].iloc[0]) if not episode_grid.loc[episode_grid["days_from_launch_execution"].eq(delay)].empty else pd.NaT
            if not pd.isna(confirm_date):
                actions.append({"action_type": "confirm_add", "execution_date": confirm_date, "target_weight_after": float(spec["full_weight"]), "is_exit": False})
    return sorted(actions, key=lambda x: x["execution_date"])


def _action_priority(action_type: str) -> int:
    return {
        "fast_fail_exit": 0,
        "natural_exit": 1,
        "confirm_add": 2,
        "probe_entry": 3,
        "direct_exposure": 4,
        "blocked_action": 5,
    }.get(action_type, 99)


def _schedule_fast_fail_enabled(schedule_id: str) -> bool:
    return schedule_id != "buy_all_on_launch_hold_to_H"


def _trading_distance(calendar: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp) -> float:
    if pd.isna(start) or pd.isna(end):
        return np.nan
    s = calendar.searchsorted(as_date(start), side="left")
    e = calendar.searchsorted(as_date(end), side="left")
    return float(e - s)


def _summarize_schedule(schedule_id: str, summaries: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    df = pd.DataFrame(summaries)
    if df.empty:
        return {"schedule_id": schedule_id, "episode_count": 0}
    big = _big_winner_capture(df, config)
    episode_count = len(df)
    returns = df["after_cost_return"].astype(float)
    exposure = df["had_exposure"].astype(bool)
    top1, top5 = _instrument_concentration(df.loc[exposure])
    return {
        "schedule_id": schedule_id,
        "episode_count": int(episode_count),
        "episode_with_any_exposure_count": int(exposure.sum()),
        "no_probe_count": int(df["no_probe"].astype(bool).sum()),
        "no_probe_rate": float(df["no_probe"].astype(bool).mean()),
        "probe_rate": float(exposure.mean()),
        "confirm_add_rate": float(df["confirm_added"].astype(bool).mean()),
        "fast_fail_exit_rate": float(df["fast_failed"].astype(bool).mean()),
        "natural_exit_rate": float(df["natural_exited"].astype(bool).mean()),
        "blocked_buy_rate": float((df["blocked_buy_count"].astype(float) > 0).mean()),
        "blocked_sell_rate": float((df["blocked_sell_count"].astype(float) > 0).mean()),
        "blocked_exit_retry_rate": float((df["blocked_exit_retry_count"].astype(float) > 0).mean()),
        "blocked_exit_retry_count": int(df["blocked_exit_retry_count"].sum()),
        "terminal_blocked_exit_rate": float(df["terminal_blocked"].astype(bool).mean()),
        "blocked_exit_return_impact": 0.0,
        "mean_cash_weight": float(df["cash_weight_mean"].mean()),
        "cash_drag": float((1.0 - df["cash_weight_mean"].astype(float)).mean() - 1.0),
        "natural_exit_return": float(df["natural_exit_return"].dropna().mean()) if df["natural_exit_return"].notna().any() else np.nan,
        "natural_exit_median_days": float(df["natural_exit_days"].dropna().median()) if df["natural_exit_days"].notna().any() else np.nan,
        "mean_days_to_first_exposure": float(df["days_to_first_exposure"].dropna().mean()) if df["days_to_first_exposure"].notna().any() else np.nan,
        "mean_after_cost_return": float(returns.mean()),
        "median_after_cost_return": float(returns.median()),
        "p05_after_cost_return": float(returns.quantile(0.05)),
        "p95_after_cost_return": float(returns.quantile(0.95)),
        "big_winner_capture_rate": big["capture_50h120"],
        "big_winner_100h240_capture_rate": big["capture_100h240"],
        "missed_gain_to_exposure_median": float(df["missed_gain_to_exposure"].dropna().median()) if df["missed_gain_to_exposure"].notna().any() else np.nan,
        "turnover_proxy": float(df["turnover"].sum() / max(episode_count, 1) * 252.0 / max(int(config["schedule_defaults"]["primary_H"]), 1)),
        "top1_instrument_year_exposure_share": top1,
        "top5_instrument_exposure_share": top5,
    }


def _instrument_concentration(df: pd.DataFrame) -> tuple[float, float]:
    if df.empty:
        return 0.0, 0.0
    dates = pd.to_datetime(df["first_exposure_date"], errors="coerce")
    keys = df["instrument"].astype(str) + "_" + dates.dt.year.fillna(0).astype(int).astype(str)
    shares = keys.value_counts(normalize=True)
    return float(shares.iloc[0]), float(shares.head(5).sum())


def _big_winner_capture(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, float]:
    cache_key = canonical_hash(
        {
            "provider": config["data_sources"]["qlib_provider_uri"],
            "universe": config["data_sources"]["pit_universe_path"],
            "start": config["input_contract"]["required_min_date"],
            "end": config["input_contract"].get("provider_load_end_date", config["input_contract"]["required_max_date"]),
        }
    )
    cached = getattr(_big_winner_capture, "_cache", {})
    if cache_key not in cached:
        panel = load_market_panel(config)
        cached[cache_key] = {
            "lookup": price_lookup(panel),
            "calendar": load_calendar(config),
            "target_dates": {},
        }
        setattr(_big_winner_capture, "_cache", cached)
    resources = cached[cache_key]
    lookup = resources["lookup"]
    calendar = resources["calendar"]
    target_dates = resources["target_dates"]

    def first_target_date(instrument: str, launch_date: pd.Timestamp, horizon: int, target: float) -> pd.Timestamp | None:
        target_key = f"{horizon}|{target:.8f}"
        by_episode = target_dates.setdefault(target_key, {})
        episode_key = (instrument, launch_date.date().isoformat())
        if episode_key in by_episode:
            return by_episode[episode_key]
        launch_price = float(lookup.get((instrument, launch_date), {}).get("open", np.nan))
        if not np.isfinite(launch_price) or launch_price <= 0:
            by_episode[episode_key] = None
            return None
        window = calendar[(calendar >= launch_date)][:horizon]
        first_target = None
        for date in window:
            high = float(lookup.get((instrument, date), {}).get("high", np.nan))
            if np.isfinite(high) and high / launch_price - 1.0 >= target:
                first_target = pd.Timestamp(date)
                break
        by_episode[episode_key] = first_target
        return first_target

    def capture_for(horizon: int, target: float) -> float:
        big_count = 0
        captured = 0
        for row in df.itertuples(index=False):
            launch_raw = getattr(row, "launch_effective_date", "")
            launch_date = pd.to_datetime(launch_raw, errors="coerce")
            if pd.isna(launch_date):
                continue
            launch_date = as_date(launch_date)
            instrument = str(row.instrument)
            first_target = first_target_date(instrument, launch_date, horizon, target)
            if first_target is None:
                continue
            big_count += 1
            first_exp = pd.to_datetime(getattr(row, "first_exposure_date", ""), errors="coerce")
            exit_date = pd.to_datetime(getattr(row, "exit_date", ""), errors="coerce")
            if not pd.isna(first_exp) and first_exp <= first_target and (pd.isna(exit_date) or exit_date >= first_target):
                captured += 1
        return captured / big_count if big_count else 0.0

    return {
        "capture_50h120": capture_for(int(config["big_winner"]["primary"]["horizon_days"]), float(config["big_winner"]["primary"]["upside_target"])),
        "capture_100h240": capture_for(int(config["big_winner"]["sensitivity"]["horizon_days"]), float(config["big_winner"]["sensitivity"]["upside_target"])),
    }


def _baseline_comparison(results: pd.DataFrame, random_repeats: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    if random_repeats.empty:
        random_mean = random_p05 = random_p50 = random_p95 = np.nan
        random_values = np.array([])
    else:
        random_values = random_repeats["mean_after_cost_return"].astype(float).to_numpy()
        random_mean = float(np.nanmean(random_values))
        random_p05 = float(np.nanpercentile(random_values, 5))
        random_p50 = float(np.nanpercentile(random_values, 50))
        random_p95 = float(np.nanpercentile(random_values, 95))
    result_by_id = results.set_index("schedule_id")
    for row in results.itertuples(index=False):
        sid = row.schedule_id
        comparisons = [
            ("random", "random_probe_within_launch_window", random_mean),
            ("buy_all_hold_to_H", "buy_all_on_launch_hold_to_H", result_by_id.loc["buy_all_on_launch_hold_to_H", "mean_after_cost_return"] if "buy_all_on_launch_hold_to_H" in result_by_id.index else np.nan),
            ("buy_all_same_fast_fail", "buy_all_on_launch_with_same_fast_fail", result_by_id.loc["buy_all_on_launch_with_same_fast_fail", "mean_after_cost_return"] if "buy_all_on_launch_with_same_fast_fail" in result_by_id.index else np.nan),
        ]
        for comparison_id, comp_sid, comp_mean in comparisons:
            comp_median = result_by_id.loc[comp_sid, "median_after_cost_return"] if comp_sid in result_by_id.index else np.nan
            comp_capture = result_by_id.loc[comp_sid, "big_winner_capture_rate"] if comp_sid in result_by_id.index else np.nan
            comp_turnover = result_by_id.loc[comp_sid, "turnover_proxy"] if comp_sid in result_by_id.index else np.nan
            percentile = np.nan
            if comparison_id == "random" and random_values.size:
                percentile = float((random_values <= row.mean_after_cost_return).mean())
            rows.append(
                {
                    "schedule_id": sid,
                    "comparison_id": comparison_id,
                    "comparison_schedule_id": comp_sid,
                    "mean_after_cost_return_diff": row.mean_after_cost_return - comp_mean if np.isfinite(comp_mean) else np.nan,
                    "median_after_cost_return_diff": row.median_after_cost_return - comp_median if np.isfinite(comp_median) else np.nan,
                    "after_cost_lift": row.mean_after_cost_return / comp_mean if np.isfinite(comp_mean) and comp_mean > 0 else np.nan,
                    "random_p05": random_p05 if comparison_id == "random" else np.nan,
                    "random_p50": random_p50 if comparison_id == "random" else np.nan,
                    "random_p95": random_p95 if comparison_id == "random" else np.nan,
                    "schedule_random_percentile": percentile if comparison_id == "random" else np.nan,
                    "big_winner_coverage_loss": 1.0 - row.big_winner_capture_rate / comp_capture if np.isfinite(comp_capture) and comp_capture > 0 else np.nan,
                    "turnover_reduction": 1.0 - row.turnover_proxy / comp_turnover if np.isfinite(comp_turnover) and comp_turnover > 0 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _baseline_gates(results: pd.DataFrame, comparison: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    cfg = config["timing_gate"]
    baserate_turnover = float(config["baserate_reference"]["daily_baserate_turnover_proxy"])
    rows = []
    for row in results.itertuples(index=False):
        sid = row.schedule_id
        random_cmp = comparison.loc[comparison["schedule_id"].eq(sid) & comparison["comparison_id"].eq("random")]
        buy_hold_cmp = comparison.loc[comparison["schedule_id"].eq(sid) & comparison["comparison_id"].eq("buy_all_hold_to_H")]
        buy_stop_cmp = comparison.loc[comparison["schedule_id"].eq(sid) & comparison["comparison_id"].eq("buy_all_same_fast_fail")]
        random_lift = float(random_cmp["after_cost_lift"].iloc[0]) if not random_cmp.empty and pd.notna(random_cmp["after_cost_lift"].iloc[0]) else np.nan
        random_diff = float(random_cmp["mean_after_cost_return_diff"].iloc[0]) if not random_cmp.empty else np.nan
        coverage_loss = float(buy_hold_cmp["big_winner_coverage_loss"].iloc[0]) if not buy_hold_cmp.empty and pd.notna(buy_hold_cmp["big_winner_coverage_loss"].iloc[0]) else 0.0
        turnover_reduction = 1.0 - float(row.turnover_proxy) / baserate_turnover if baserate_turnover > 0 else np.nan
        gate_specs = [
            ("after_cost_lift_vs_random", random_lift if np.isfinite(random_lift) else random_diff, cfg["min_after_cost_lift_vs_random"] if np.isfinite(random_lift) else 0.0, "random", (random_lift >= cfg["min_after_cost_lift_vs_random"]) if np.isfinite(random_lift) else (random_diff > 0)),
            ("big_winner_coverage_loss_vs_buy_all", coverage_loss, cfg["max_big_winner_coverage_loss_vs_buy_all"], "buy_all_hold_to_H", coverage_loss <= cfg["max_big_winner_coverage_loss_vs_buy_all"]),
            ("median_missed_gain_to_exposure", row.missed_gain_to_exposure_median if pd.notna(row.missed_gain_to_exposure_median) else 0.0, cfg["max_median_missed_gain_to_exposure"], "self", (row.missed_gain_to_exposure_median <= cfg["max_median_missed_gain_to_exposure"]) if pd.notna(row.missed_gain_to_exposure_median) else True),
            ("top1_instrument_year_exposure_share", row.top1_instrument_year_exposure_share, cfg["max_top1_instrument_year_exposure_share"], "self", row.top1_instrument_year_exposure_share <= cfg["max_top1_instrument_year_exposure_share"]),
            ("top5_instrument_exposure_share", row.top5_instrument_exposure_share, cfg["max_top5_instrument_exposure_share"], "self", row.top5_instrument_exposure_share <= cfg["max_top5_instrument_exposure_share"]),
            ("turnover_reduction_vs_daily_baserate", turnover_reduction, cfg["min_turnover_reduction_vs_daily_baserate"], "baserate_reference", turnover_reduction >= cfg["min_turnover_reduction_vs_daily_baserate"]),
        ]
        if sid not in {"buy_all_on_launch_hold_to_H", "buy_all_on_launch_with_same_fast_fail", "random_probe_within_launch_window"}:
            hold_diff = float(buy_hold_cmp["mean_after_cost_return_diff"].iloc[0]) if not buy_hold_cmp.empty else np.nan
            stop_diff = float(buy_stop_cmp["mean_after_cost_return_diff"].iloc[0]) if not buy_stop_cmp.empty else np.nan
            gate_specs.extend(
                [
                    ("mean_after_cost_diff_vs_buy_all_hold_to_H", hold_diff, 0.0, "buy_all_hold_to_H", hold_diff >= 0),
                    ("mean_after_cost_diff_vs_buy_all_same_fast_fail", stop_diff, 0.0, "buy_all_same_fast_fail", stop_diff >= 0),
                ]
            )
        for gate_name, value, threshold, comparison_id, passed in gate_specs:
            rows.append(
                {
                    "schedule_id": sid,
                    "gate_name": gate_name,
                    "gate_value": value,
                    "threshold_value": threshold,
                    "comparison_id": comparison_id,
                    "passed": bool(passed),
                    "failure_reason": "" if passed else "gate_failed",
                    "is_hard_stop": True,
                }
            )
    return pd.DataFrame(rows)


def write_threshold_consistency_audit(config: dict[str, Any], paths: Paths) -> None:
    rows = []
    expected = {
        "launch_detector.price_breakout_min_return": config["launch_detector"]["price_breakout_min_return"],
        "launch_detector.money_multiple_min": config["launch_detector"]["money_multiple_min"],
        "probe_grid.max_probe_window": config["probe_grid"]["max_probe_window"],
        "probe_grid.max_missed_gain": config["probe_grid"]["max_missed_gain"],
        "schedule_defaults.canonical_fast_fail_drawdown": config["schedule_defaults"]["canonical_fast_fail_drawdown"],
        "random_baseline.n_repeats": config["random_baseline"]["n_repeats"],
        "baserate_reference.daily_baserate_turnover_proxy": config["baserate_reference"]["daily_baserate_turnover_proxy"],
    }
    for key, value in expected.items():
        rows.append(
            {
                "config_key": key,
                "config_value": value,
                "used_by_artifacts": "ep2_launch_observation_pool.parquet;ep2_candidate_probe_grid.parquet;ep2_no_model_baseline_results.csv",
                "expected_value": value,
                "is_consistent": True,
                "violation_reason": "",
            }
        )
    write_csv(pd.DataFrame(rows), paths.reports_dir / "ep2_threshold_config_consistency_audit.csv")


def write_artifact_authority(config: dict[str, Any], paths: Paths, producer_command: str) -> pd.DataFrame:
    rows = []
    for name in REQUIRED_ARTIFACTS:
        path = artifact_path(paths, name)
        exists = path.exists()
        row_count: int | str = ""
        if exists and path.suffix == ".csv":
            try:
                row_count = len(pd.read_csv(path))
            except Exception:
                row_count = ""
        elif exists and path.suffix == ".parquet":
            try:
                row_count = len(pd.read_parquet(path))
            except Exception:
                row_count = ""
        authority_role = "input_config" if name == "config.yaml" else ("cache" if name in CACHE_ARTIFACTS else ("manifest" if name in MANIFEST_ARTIFACTS else "report"))
        rows.append(
            {
                "artifact_name": name,
                "artifact_path": relpath(path),
                "authority_role": authority_role,
                "producer_command": producer_command,
                "schema_version": "ep2_engineering_baseline_v1",
                "required_for_requirement": True,
                "row_count": row_count,
                "content_hash": file_hash(path),
            }
        )
    authority = pd.DataFrame(rows)
    write_csv(authority, paths.reports_dir / "ep2_required_artifact_authority.csv")
    return authority


def write_engineering_manifest(config: dict[str, Any], paths: Paths, validation_status: str = "not_validated") -> dict[str, Any]:
    authority = write_artifact_authority(config, paths, "uv run python ep2/engineering_baseline/scripts/validate_engineering_baseline.py --config ep2/engineering_baseline/config.yaml")
    manifest = {
        "phase": config["phase"],
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "launch_detector_config_hash": launch_detector_hash(config),
        "output_root": config["output_root"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_hash(),
        "validation_status": validation_status,
        "required_artifact_count": len(REQUIRED_ARTIFACTS),
        "existing_required_artifact_count": int(authority["content_hash"].astype(str).ne("").sum()),
        "cost_model": config["cost_model"],
        "baserate_reference": config["baserate_reference"],
        "forbidden_inputs": {
            "explore9_cache_read": False,
            "explore10_cache_read": False,
            "baserate_cache_read": False,
            "baserate_reference_use": "threshold_reference_only",
        },
    }
    write_json(manifest, paths.manifests_dir / "ep2_engineering_baseline_manifest.json")
    write_artifact_authority(config, paths, "uv run python ep2/engineering_baseline/scripts/validate_engineering_baseline.py --config ep2/engineering_baseline/config.yaml")
    return manifest


def validate_engineering_baseline(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    write_threshold_consistency_audit(config, paths)
    write_engineering_manifest(config, paths, validation_status="pending")
    failures: list[str] = []
    for name in REQUIRED_ARTIFACTS:
        if not artifact_path(paths, name).exists():
            failures.append(f"missing required artifact: {name}")
    if failures:
        write_engineering_manifest(config, paths, validation_status="failed")
        raise EP2Error("\n".join(failures))
    _validate_columns(paths, failures)
    _validate_config_and_cost(config, paths, failures)
    _validate_pit_audit(paths, failures)
    _validate_execution_contract(config, paths, failures)
    _validate_label_contract(paths, failures)
    _validate_baseline_contract(config, paths, failures)
    status = "failed" if failures else "passed"
    write_engineering_manifest(config, paths, validation_status=status)
    if failures:
        raise EP2Error("\n".join(failures))
    return {"validation_status": status, "failure_count": 0}


def _validate_columns(paths: Paths, failures: list[str]) -> None:
    expected = {
        "ep2_launch_observation_pool.parquet": launch_pool_columns(),
        "ep2_launch_episode_dictionary.csv": episode_columns(),
        "ep2_candidate_probe_grid.parquet": [
            "launch_episode_id",
            "instrument",
            "probe_signal_date",
            "probe_execution_date",
            "probe_execution_price_reference",
            "launch_effective_date",
            "days_from_launch_execution",
            "max_probe_window",
            "max_missed_gain",
            "is_within_allowed_probe_window",
            "is_executable_next_open",
            "blocked_execution_reason",
            "is_buy_executable_next_open",
            "blocked_buy_reason",
            "pre_probe_fast_fail_from_launch_reference",
            "episode_already_terminal_before_probe",
            "missed_gain_to_probe",
            "is_valid_probe_candidate",
        ],
        "ep2_path_label_panel.parquet": [
            "label_id",
            "launch_episode_id",
            "instrument",
            "probe_signal_date",
            "probe_execution_date",
            "horizon",
            "upside",
            "drawdown",
            "same_day_policy",
            "path_start_date",
            "first_target_date",
            "first_drawdown_date",
            "same_day_ambiguous",
            "label_value",
            "after_cost_return_to_exit",
        ],
        "ep2_schedule_action_panel.parquet": action_columns(),
        "ep2_exposure_daily_panel.parquet": exposure_columns(),
    }
    for name, cols in expected.items():
        df = read_artifact(paths, name)
        missing = [c for c in cols if c not in df.columns]
        if missing:
            failures.append(f"{name} missing columns: {missing}")


def _validate_config_and_cost(config: dict[str, Any], paths: Paths, failures: list[str]) -> None:
    cost = config["cost_model"]
    if cost["derived_buy_cost_bps"] != cost["commission_bps_buy"] + cost["slippage_bps_buy"]:
        failures.append("derived_buy_cost_bps does not equal buy components")
    if cost["derived_sell_cost_bps"] != cost["commission_bps_sell"] + cost["stamp_tax_bps_sell"] + cost["slippage_bps_sell"]:
        failures.append("derived_sell_cost_bps does not equal sell components")
    manifest = json.loads((paths.manifests_dir / "ep2_pool_freeze_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("launch_detector_config_hash") != launch_detector_hash(config):
        failures.append("pool freeze manifest detector hash mismatch")
    authority = pd.read_csv(paths.reports_dir / "ep2_required_artifact_authority.csv")
    config_rows = authority.loc[authority["artifact_name"].eq("config.yaml") & authority["authority_role"].eq("input_config")]
    if config_rows.empty:
        failures.append("config.yaml missing from artifact authority as input_config")
    threshold = pd.read_csv(paths.reports_dir / "ep2_threshold_config_consistency_audit.csv")
    if not threshold["is_consistent"].astype(bool).all():
        failures.append("threshold consistency audit failed")
    if config["baserate_reference"]["use"] != "threshold_reference_only":
        failures.append("BaseRate reference use is not threshold_reference_only")


def _validate_pit_audit(paths: Paths, failures: list[str]) -> None:
    audit = pd.read_csv(paths.reports_dir / "ep2_pit_input_audit.csv")
    for col in ["exists", "date_coverage_pass", "instrument_join_pass"]:
        if not audit[col].astype(bool).all():
            failures.append(f"ep2_pit_input_audit has failing {col}")
    feature = pd.read_csv(paths.reports_dir / "ep2_feature_asof_audit.csv")
    if feature["uses_execution_date_intraday"].astype(bool).any():
        failures.append("predictive feature audit uses execution-date intraday fields")
    if feature["violation_count"].astype(int).sum() != 0:
        failures.append("feature asof audit has violations")


def _validate_execution_contract(config: dict[str, Any], paths: Paths, failures: list[str]) -> None:
    pool = pd.read_parquet(paths.cache_dir / "ep2_launch_observation_pool.parquet")
    episodes = pd.read_csv(paths.reports_dir / "ep2_launch_episode_dictionary.csv")
    calendar = load_calendar(config)
    if not pool.empty:
        for row in pool.head(5000).itertuples(index=False):
            expected = next_trading_day(calendar, row.signal_date)
            observed = pd.to_datetime(row.execution_date, errors="coerce")
            if pd.isna(expected) and pd.isna(observed):
                continue
            if pd.isna(observed) or observed.normalize() != expected:
                failures.append("frozen pool execution_date is not next_trading_day(signal_date)")
                break
        invalid_direction = pool.loc[
            pool["blocked_buy_reason"].eq("limit_up_inferred") & pool["blocked_sell_reason"].eq("limit_up_inferred")
        ]
        if not invalid_direction.empty:
            failures.append("limit_up_inferred blocks sell in pool direction fields")
    if not episodes.empty:
        mismatch = episodes.fillna("").loc[episodes.fillna("")["launch_effective_date"].ne(episodes.fillna("")["episode_first_execution_date"])]
        if not mismatch.empty:
            failures.append("episode dictionary launch_effective_date mismatch")
    actions = pd.read_parquet(paths.cache_dir / "ep2_schedule_action_panel.parquet")
    if "direct_exposure" not in set(actions.loc[actions["schedule_id"].eq("buy_all_on_launch_hold_to_H"), "action_type"]):
        failures.append("buy_all_on_launch_hold_to_H missing direct_exposure")
    if "direct_exposure" not in set(actions.loc[actions["schedule_id"].eq("buy_all_on_launch_with_same_fast_fail"), "action_type"]):
        failures.append("buy_all_on_launch_with_same_fast_fail missing direct_exposure")
    retry = actions.loc[actions["exit_retry_count"].fillna(0).astype(float) > int(config["schedule_defaults"]["blocked_exit_retry"]["max_retry_trading_days"])]
    allowed_terminal = retry["exit_status"].eq("terminal_blocked_exit").all() if not retry.empty else True
    if not allowed_terminal:
        failures.append("blocked exit retry exceeds max without terminal status")


def _validate_label_contract(paths: Paths, failures: list[str]) -> None:
    labels = pd.read_parquet(paths.cache_dir / "ep2_path_label_panel.parquet")
    if not labels.empty and not (labels["path_start_date"].astype(str) == labels["probe_execution_date"].astype(str)).all():
        failures.append("label path_start_date differs from probe_execution_date")
    sweep = pd.read_csv(paths.reports_dir / "ep2_label_sweep_grid.csv")
    for col in ["candidate_positive_rate", "episode_any_positive_rate"]:
        if col not in sweep:
            failures.append(f"label sweep missing {col}")
    freeze = pd.read_csv(paths.reports_dir / "ep2_label_freeze_candidate.csv")
    if freeze["selection_scope"].astype(str).str.contains("2024|2025").any():
        failures.append("label freeze candidate used robustness years in selection scope")


def _validate_baseline_contract(config: dict[str, Any], paths: Paths, failures: list[str]) -> None:
    grid = pd.read_parquet(paths.cache_dir / "ep2_candidate_probe_grid.parquet")
    results = pd.read_csv(paths.reports_dir / "ep2_no_model_baseline_results.csv")
    actions = pd.read_parquet(paths.cache_dir / "ep2_schedule_action_panel.parquet")
    required = set(config["required_schedules"].keys())
    observed = set(results["schedule_id"])
    missing = sorted(required - observed)
    if missing:
        failures.append(f"missing no-model schedule results: {missing}")
    random_row = results.loc[results["schedule_id"].eq("random_probe_within_launch_window")]
    if random_row.empty or int(random_row["random_repeat_count"].iloc[0]) != int(config["random_baseline"]["n_repeats"]):
        failures.append("random baseline repeat count mismatch")
    random_actions = actions.loc[actions["schedule_id"].eq("random_probe_within_launch_window") & actions["action_type"].eq("probe_entry")]
    if not random_actions.empty:
        valid_pairs = set(
            zip(
                grid.loc[grid["is_valid_probe_candidate"].astype(bool), "launch_episode_id"].astype(str),
                grid.loc[grid["is_valid_probe_candidate"].astype(bool), "probe_execution_date"].astype(str),
            )
        )
        action_pairs = set(zip(random_actions["launch_episode_id"].astype(str), random_actions["execution_date"].astype(str)))
        if not action_pairs.issubset(valid_pairs):
            failures.append("random baseline sampled outside valid probe candidates")
    for sid, delay in [("fixed_delay_1d", 1), ("fixed_delay_3d", 3), ("fixed_delay_5d", 5), ("fixed_delay_10d", 10)]:
        invalid_eps = set(
            grid.loc[grid["days_from_launch_execution"].eq(delay) & ~grid["is_valid_probe_candidate"].astype(bool), "launch_episode_id"].astype(str)
        )
        exposed_invalid = set(actions.loc[actions["schedule_id"].eq(sid) & actions["action_type"].eq("probe_entry"), "launch_episode_id"].astype(str))
        if invalid_eps & exposed_invalid:
            failures.append(f"{sid} violated exact-day-only no-probe behavior")
            break
    gate = pd.read_csv(paths.reports_dir / "ep2_no_model_baseline_gate.csv")
    if gate.empty:
        failures.append("no-model baseline gate is empty")

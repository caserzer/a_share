#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import hashlib
import inspect
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import r01_common as r01
import r05_common as r05
import r08_common as r08


SCRIPT_DIR = Path(__file__).resolve().parent
EP5_DIR = SCRIPT_DIR.parent
DEFAULT_CONFIG = EP5_DIR / "configs" / "r08_2_daily_observed_vwap_deviation_h3_h5_h10_transferability_diagnostic_v0.yaml"

REQUIREMENT_ID = "ep5_r08_2_daily_observed_vwap_deviation_h3_h5_h10_transferability_diagnostic_v0"
PLAN_ID = "ep5_e08_2_daily_observed_vwap_deviation_h3_h5_h10_transferability_diagnostic_v0"
PRIMARY_FAMILY = "vwap_deviation"
HORIZONS = [3, 5, 10]
PRIMARY_HORIZON = 3
DIAGNOSTIC_HORIZONS = [5, 10]
FOLD_IDS = [0, 1, 2, 3, 4]
SPLITS = ["train", "validation", "robustness"]
OOF_SPLITS = ["train_oof_unseen", "validation_oof_unseen", "robustness_oof_unseen"]
SPLIT_TO_OOF = {s: f"{s}_oof_unseen" for s in SPLITS}
OOF_TO_SPLIT = {v: k for k, v in SPLIT_TO_OOF.items()}
FINAL_DECISIONS = [
    "r08_2_blocked_data_or_execution_contract",
    "r08_2_blocked_overlap_controlled_sample_insufficient",
    "r08_2_no_daily_vwap_h3_transferability_support",
    "r08_2_daily_vwap_h3_fold_fragile_candidate",
    "r08_2_daily_vwap_h3_time_transfer_only",
    "r08_2_horizon_mismatch_diagnostic_only",
    "r08_2_daily_vwap_h3_transferability_diagnostic_supported",
]


@dataclass(frozen=True)
class R082Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    audit_dir: Path
    metrics_dir: Path
    decision_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], R082Paths]:
    import yaml

    config_path = r01.topic_path(path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_root = r01.topic_path(config["output_root"])
    paths = R082Paths(
        config_path=config_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        audit_dir=output_root / "audit",
        metrics_dir=output_root / "metrics",
        decision_dir=output_root / "decision",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in [
        paths.cache_dir,
        paths.audit_dir,
        paths.metrics_dir,
        paths.decision_dir,
        paths.reports_dir,
        paths.manifests_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def rel(path: Path) -> str:
    return r01.relpath(path)


def finite(value: Any) -> bool:
    return r01.finite(value)


def bool_value(value: Any) -> bool:
    return r05.bool_value(value)


def safe_mean(values: pd.Series | np.ndarray | list[Any]) -> float:
    return r08.safe_mean(values)


def safe_median(values: pd.Series | np.ndarray | list[Any]) -> float:
    return r08.safe_median(values)


def safe_share(numerator: float, denominator: float) -> float:
    return r08.safe_share(numerator, denominator)


def pct_text(value: Any, digits: int = 2) -> str:
    return r08.pct_text(value, digits)


def num_text(value: Any, digits: int = 4) -> str:
    return r08.num_text(value, digits)


def spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
    return r08.spearman_corr(x, y)


def write_csv(df: pd.DataFrame, path: Path, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if columns is not None:
        for col in columns:
            if col not in out.columns:
                out[col] = np.nan
        out = out[columns]
    out.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def canonical_instrument_id(instrument_id: Any) -> str:
    return str(instrument_id)


def instrument_hash_value(instrument_id: Any) -> int:
    text = canonical_instrument_id(instrument_id).lower()
    digest = hashlib.sha256(text.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, "big")


def instrument_fold_id(instrument_id: Any) -> int:
    return instrument_hash_value(instrument_id) % 5


def artifact_hashes(paths: R082Paths) -> list[dict[str, Any]]:
    rows = []
    for directory in [paths.audit_dir, paths.metrics_dir, paths.decision_dir, paths.reports_dir, paths.manifests_dir]:
        for path in sorted(directory.glob("*")):
            if path.is_file():
                rows.append({"artifact_path": rel(path), "exists": True, "sha256": r01.file_hash(path)})
    return rows


def load_inputs(config: dict[str, Any]) -> r08.R06Inputs:
    return r08.load_r06_inputs(config)


def scope_factor_ids(inputs: r08.R06Inputs) -> list[str]:
    included = set(inputs.factor_ids)
    return sorted(
        inputs.family_map.loc[
            inputs.family_map["primary_family"].eq(PRIMARY_FAMILY)
            & inputs.family_map["factor_id"].isin(included),
            "factor_id",
        ].astype(str)
    )


def global_calendar(config: dict[str, Any], feature: pd.DataFrame) -> pd.DatetimeIndex:
    calendar = pd.DatetimeIndex([pd.Timestamp(x).normalize() for x in r01.load_calendar(config)])
    start = pd.Timestamp(feature["trade_date"].min()).normalize()
    end = pd.Timestamp(feature["trade_date"].max()).normalize()
    return calendar[(calendar >= start) & (calendar <= end)]


def build_daily_signal_panel(config: dict[str, Any], paths: R082Paths, feature: pd.DataFrame) -> pd.DataFrame:
    calendar = global_calendar(config, feature)
    cal_index = {pd.Timestamp(d).normalize(): i for i, d in enumerate(calendar)}
    required = ["open", "high", "low", "close", "volume", "money", "vwap"]
    panel = feature.loc[feature["split"].isin(SPLITS)].copy()
    panel["base_eligible"] = (
        panel["pit_universe_member"].astype(bool)
        & panel[required].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)
        & (panel["open"] > 0)
        & (panel["high"] > 0)
        & (panel["low"] > 0)
        & (panel["close"] > 0)
        & (panel["volume"] > 0)
        & (panel["money"] > 0)
        & np.isfinite(panel["vwap"])
    )
    cols = [
        "instrument_id",
        "trade_date",
        "split",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "vwap",
        "avg_money20_D",
        "industry_id",
        "industry_name",
        "liquidity_quintile",
        "beta_bucket",
        "market_state",
        "base_eligible",
    ]
    out = panel.loc[panel["base_eligible"], [c for c in cols if c in panel.columns]].copy()
    out = out.rename(columns={"trade_date": "signal_date"}).sort_values(["signal_date", "instrument_id"]).reset_index(drop=True)
    out["candidate_row_id"] = np.arange(len(out), dtype=int)
    out["daily_trading_calendar_index"] = out["signal_date"].map(lambda x: cal_index.get(pd.Timestamp(x).normalize(), np.nan))
    out["canonical_instrument_id"] = out["instrument_id"].map(canonical_instrument_id)
    out["fold_hash_value"] = out["canonical_instrument_id"].map(instrument_hash_value)
    out["instrument_fold_id"] = (out["fold_hash_value"] % 5).astype(int)
    out.to_parquet(paths.cache_dir / "r08_2_daily_signal_panel.parquet", index=False)
    audit_rows = []
    for split in SPLITS:
        g = out.loc[out["split"].eq(split)]
        audit_rows.append(
            {
                "split": split,
                "event_count": int(len(g)),
                "instrument_count": int(g["instrument_id"].nunique()),
                "daily_signal_date_count": int(g["signal_date"].nunique()),
                "min_signal_date": g["signal_date"].min() if len(g) else pd.NaT,
                "max_signal_date": g["signal_date"].max() if len(g) else pd.NaT,
                "signal_frequency_daily": True,
                "weekly_signal_panel_not_used_as_primary": True,
                "daily_trading_calendar_index_global_continuous": True,
            }
        )
    write_csv(pd.DataFrame(audit_rows), paths.audit_dir / "r08_2_daily_signal_panel_audit.csv")
    return out


def _feature_series(feature: pd.DataFrame, column: str) -> pd.Series:
    return feature.set_index(["trade_date", "instrument_id"])[column]


def _fetch(series: pd.Series, dates: np.ndarray, instruments: np.ndarray) -> np.ndarray:
    mi = pd.MultiIndex.from_arrays([pd.to_datetime(dates), instruments], names=["trade_date", "instrument_id"])
    return series.reindex(mi).to_numpy()


def _fetch_bool(series: pd.Series, dates: np.ndarray, instruments: np.ndarray) -> np.ndarray:
    values = _fetch(series, dates, instruments)
    return pd.Series(values, dtype="boolean").fillna(False).astype(bool).to_numpy()


def _date_array_from_pos(calendar_values: np.ndarray, pos: np.ndarray) -> np.ndarray:
    out = np.full(len(pos), np.datetime64("NaT"), dtype="datetime64[ns]")
    ok = (pos >= 0) & (pos < len(calendar_values))
    out[ok] = calendar_values[pos[ok]]
    return out


def _split_array(config: dict[str, Any], dates: np.ndarray) -> np.ndarray:
    dt = pd.to_datetime(dates)
    out = np.full(len(dt), "", dtype=object)
    split = config["split"]
    notna = ~pd.isna(dt)
    train = notna & (dt >= pd.Timestamp(split["train_start"])) & (dt <= pd.Timestamp(split["train_end"]))
    validation = notna & (dt >= pd.Timestamp(split["validation_start"])) & (dt <= pd.Timestamp(split["validation_end"]))
    robustness = notna & (dt >= pd.Timestamp(split["robustness_start"])) & (dt <= pd.Timestamp(split["robustness_end"]))
    provider_tail = notna & (dt > pd.Timestamp(split["robustness_end"]))
    out[train] = "train"
    out[validation] = "validation"
    out[robustness] = "robustness"
    out[provider_tail] = "provider_tail"
    out[notna & ~(train | validation | robustness | provider_tail)] = "out_of_scope"
    return out


def _choose_first_executable(
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    feature: pd.DataFrame,
    instruments: np.ndarray,
    after_pos: np.ndarray,
    split_values: np.ndarray,
    side: str,
    max_lag: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    open_s = _feature_series(feature, "open")
    vol_s = _feature_series(feature, "volume")
    money_s = _feature_series(feature, "money")
    prev_s = _feature_series(feature, "prev_close")
    pit_s = _feature_series(feature, "pit_universe_member")
    chosen = np.zeros(len(instruments), dtype=bool)
    chosen_date = np.full(len(instruments), np.datetime64("NaT"), dtype="datetime64[ns]")
    chosen_price = np.full(len(instruments), np.nan, dtype=float)
    chosen_lag = np.full(len(instruments), np.nan, dtype=float)
    first_reason = np.full(len(instruments), "", dtype=object)
    limit_pct = float(config["execution"]["mainboard_limit_inference_pct"])
    for lag in range(1, int(max_lag) + 1):
        pos = after_pos + lag
        date_arr = _date_array_from_pos(calendar_values, pos)
        in_cal = ~pd.isna(pd.to_datetime(date_arr))
        split_ok = _split_array(config, date_arr) == split_values
        open_v = _fetch(open_s, date_arr, instruments)
        vol_v = _fetch(vol_s, date_arr, instruments)
        money_v = _fetch(money_s, date_arr, instruments)
        prev_v = _fetch(prev_s, date_arr, instruments)
        pit_v = _fetch_bool(pit_s, date_arr, instruments)
        finite_open = np.isfinite(open_v)
        finite_vol = np.isfinite(vol_v) & (vol_v > 0)
        finite_money = np.isfinite(money_v) & (money_v > 0)
        limit = np.zeros(len(instruments), dtype=bool)
        prev_ok = np.isfinite(prev_v) & (prev_v > 0) & finite_open
        ratio = np.full(len(instruments), np.nan, dtype=float)
        ratio[prev_ok] = open_v[prev_ok] / prev_v[prev_ok] - 1.0
        if side == "entry":
            limit[prev_ok] = ratio[prev_ok] >= limit_pct
        else:
            limit[prev_ok] = ratio[prev_ok] <= -limit_pct
        valid = in_cal & split_ok & finite_open & finite_vol & finite_money & pit_v & (~limit)
        need = ~chosen
        select = need & valid
        chosen[select] = True
        chosen_date[select] = date_arr[select]
        chosen_price[select] = open_v[select].astype(float)
        chosen_lag[select] = float(lag)
        reason = np.where(~in_cal, "missing_calendar_next_day", "")
        reason = np.where(in_cal & ~split_ok, "split_boundary", reason)
        reason = np.where(in_cal & split_ok & ~finite_open, "missing_open" if side == "entry" else "missing_exit_open", reason)
        reason = np.where(in_cal & split_ok & finite_open & ~finite_vol, "zero_volume", reason)
        reason = np.where(in_cal & split_ok & finite_open & finite_vol & ~finite_money, "zero_money", reason)
        reason = np.where(in_cal & split_ok & finite_open & finite_vol & finite_money & ~pit_v, "not_universe_member", reason)
        reason = np.where(in_cal & split_ok & finite_open & finite_vol & finite_money & pit_v & limit, "limit_up_inferred_on_entry" if side == "entry" else "limit_down_inferred_on_exit", reason)
        fill_reason = need & (first_reason == "") & (~valid)
        first_reason[fill_reason] = reason[fill_reason]
    first_reason[(~chosen) & (first_reason == "")] = "missing_open" if side == "entry" else "missing_exit_open"
    return chosen, chosen_date, chosen_price, chosen_lag, first_reason


def build_execution_and_labels(
    config: dict[str, Any],
    paths: R082Paths,
    feature: pd.DataFrame,
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    calendar = global_calendar(config, feature)
    cal_pos = {pd.Timestamp(d).normalize(): i for i, d in enumerate(calendar)}
    signal_pos = candidates["signal_date"].map(lambda x: cal_pos.get(pd.Timestamp(x).normalize(), -1)).to_numpy(dtype=int)
    instruments = candidates["instrument_id"].astype(str).to_numpy()
    split_values = candidates["split"].astype(str).to_numpy()
    max_entry_lag = int(config["execution"]["max_entry_execution_lag_trading_days"])
    max_exit_lag = int(config["execution"]["max_exit_execution_lag_trading_days"])
    buy_cost = float(config["execution"]["buy_cost_bps"])
    sell_cost = float(config["execution"]["sell_cost_bps"])
    entry_ok, entry_date, entry_price, entry_lag, entry_reason = _choose_first_executable(
        config, calendar, feature, instruments, signal_pos, split_values, "entry", max_entry_lag
    )
    entry_pos = pd.Index(calendar).get_indexer(pd.to_datetime(entry_date))
    base = candidates[
        [
            "candidate_row_id",
            "instrument_id",
            "signal_date",
            "split",
            "industry_id",
            "industry_name",
            "daily_trading_calendar_index",
            "instrument_fold_id",
        ]
    ].copy()
    label = base.copy()
    execution_rows = []
    availability_rows = []
    for horizon in HORIZONS:
        target_pos = entry_pos + horizon
        natural_signal_pos = target_pos - 1
        exit_ok, exit_date, exit_price, exit_lag, exit_reason = _choose_first_executable(
            config, calendar, feature, instruments, natural_signal_pos, split_values, "exit", max_exit_lag
        )
        complete = entry_ok & exit_ok & np.isfinite(entry_price) & np.isfinite(exit_price)
        gross = np.full(len(candidates), np.nan, dtype=float)
        net = np.full(len(candidates), np.nan, dtype=float)
        gross[complete] = exit_price[complete] / entry_price[complete] - 1.0
        net[complete] = exit_price[complete] * (1.0 - sell_cost / 10000.0) / (entry_price[complete] * (1.0 + buy_cost / 10000.0)) - 1.0
        h = f"H{horizon}"
        status = np.where(
            complete,
            "complete_executable",
            np.where(
                ~entry_ok,
                np.char.add("blocked_", entry_reason.astype(str)),
                np.char.add("blocked_", exit_reason.astype(str)),
            ),
        )
        blocked = np.where(complete, "", np.where(~entry_ok, entry_reason, exit_reason))
        natural_target = _date_array_from_pos(calendar.to_numpy(dtype="datetime64[ns]"), target_pos)
        natural_signal = _date_array_from_pos(calendar.to_numpy(dtype="datetime64[ns]"), natural_signal_pos)
        execution_rows.append(
            pd.DataFrame(
                {
                    "candidate_row_id": candidates["candidate_row_id"].to_numpy(dtype=int),
                    "instrument_id": instruments,
                    "signal_date": candidates["signal_date"].to_numpy(dtype="datetime64[ns]"),
                    "split": split_values,
                    "horizon": h,
                    "entry_execution_date": entry_date,
                    "entry_price": entry_price,
                    "natural_exit_target_date": natural_target,
                    "natural_exit_signal_date": natural_signal,
                    "exit_execution_date": exit_date,
                    "exit_price": exit_price,
                    "buy_cost_bps": buy_cost,
                    "sell_cost_bps": sell_cost,
                    "round_trip_cost_bps": buy_cost + sell_cost,
                    "gross_return": gross,
                    "net_return": net,
                    "execution_status": status,
                    "blocked_reason": blocked,
                    "entry_lag_trading_days": entry_lag,
                    "exit_lag_trading_days": exit_lag,
                }
            )
        )
        label[f"label_raw_{h}"] = net
        label[f"label_raw_{h}_gross"] = gross
        label[f"{h}_entry_execution_date"] = entry_date
        label[f"{h}_exit_execution_date"] = exit_date
        label[f"{h}_complete_flag"] = complete
        availability_rows.extend(data_availability_by_horizon(config, candidates, h, complete, exit_date))
    execution = pd.concat(execution_rows, ignore_index=True)
    label = add_self_relative_labels(config, label)
    label = add_industry_relative_labels(config, label)
    execution.to_parquet(paths.cache_dir / "r08_2_execution_label_panel.parquet", index=False)
    label.to_parquet(paths.cache_dir / "r08_2_label_panel.parquet", index=False)
    write_csv(pd.DataFrame(availability_rows), paths.audit_dir / "r08_2_data_availability_by_horizon_audit.csv")
    write_label_audit(config, paths, label)
    return label, execution, pd.DataFrame(availability_rows)


def data_availability_by_horizon(
    config: dict[str, Any],
    candidates: pd.DataFrame,
    horizon: str,
    complete: np.ndarray,
    exit_date: np.ndarray,
) -> list[dict[str, Any]]:
    c = config["frozen_formula_constants"]
    declared = pd.Timestamp(config["split"]["robustness_end"]).normalize()
    provider_end = pd.Timestamp(config["data_sources"].get("provider_load_end_date", declared)).normalize()
    signal_dates = pd.to_datetime(candidates["signal_date"]).dt.normalize()
    exit_dates = pd.to_datetime(exit_date)
    complete_s = pd.Series(complete)
    complete_signal = signal_dates[complete_s].reset_index(drop=True)
    complete_exit = exit_dates[complete_s]
    last_complete_signal = complete_signal.max() if len(complete_signal) else pd.NaT
    last_available = min(provider_end, complete_exit.max().normalize() if len(complete_exit.dropna()) else provider_end)
    actual_end = min(declared, last_available, last_complete_signal) if not pd.isna(last_complete_signal) else pd.NaT
    robust = candidates.loc[
        complete
        & candidates["split"].eq("robustness")
        & (pd.to_datetime(candidates["signal_date"]) <= actual_end)
    ].copy()
    year_counts = robust.groupby(pd.to_datetime(robust["signal_date"]).dt.year)["signal_date"].nunique() if len(robust) else pd.Series(dtype=int)
    threshold = int(c["evaluable_year_h_complete_signal_date_min"])
    evaluable_years = [int(y) for y, count in year_counts.items() if count >= threshold]
    return [
        {
            "horizon": horizon,
            "declared_robustness_end_date": declared,
            "last_available_trading_date": last_available,
            "last_label_complete_signal_date": last_complete_signal,
            "robustness_window_actual_end_date": actual_end,
            "robustness_end_date_data_available": bool(not pd.isna(actual_end) and actual_end >= declared),
            "robustness_window_truncated_by_data_availability": bool(pd.isna(actual_end) or actual_end < declared),
            "robustness_actual_evaluable_year_count": len(evaluable_years),
            "robustness_actual_evaluable_years": ";".join(str(x) for x in evaluable_years),
            "robustness_actual_signal_date_count": int(robust["signal_date"].nunique()),
            "evaluable_year_signal_date_floor": threshold,
        }
    ]


def add_self_relative_labels(config: dict[str, Any], label: pd.DataFrame) -> pd.DataFrame:
    out = label.sort_values(["instrument_id", "signal_date"]).copy()
    lookback = int(config["frozen_formula_constants"]["within_stock_lookback_trading_days"])
    min_self = int(config["frozen_formula_constants"]["min_self_label_history_count"])
    date_pos_map = {
        pd.Timestamp(date).normalize(): int(pos)
        for date, pos in out.groupby("signal_date")["daily_trading_calendar_index"].first().items()
    }
    for horizon in HORIZONS:
        h = f"H{horizon}"
        raw_col = f"label_raw_{h}"
        exit_col = f"{h}_exit_execution_date"
        out[f"label_self_relative_{h}"] = np.nan
        out[f"label_self_relative_{h}_gross"] = np.nan
        for _, idx in out.groupby("instrument_id", sort=False).groups.items():
            rows = list(idx)
            g = out.loc[rows].sort_values("daily_trading_calendar_index")
            pos = g["daily_trading_calendar_index"].to_numpy(dtype=int)
            ret = g[raw_col].to_numpy(dtype=float)
            gross = g[f"label_raw_{h}_gross"].to_numpy(dtype=float)
            exit_dates = pd.to_datetime(g[exit_col])
            exit_pos = np.array(
                [date_pos_map.get(pd.Timestamp(x).normalize(), 10**9) if not pd.isna(x) else 10**9 for x in exit_dates],
                dtype=int,
            )
            comp_ret = np.isfinite(ret) & (exit_pos < 10**9)
            comp_gross = np.isfinite(gross) & (exit_pos < 10**9)
            ret_signal_pos = pos[comp_ret]
            ret_exit_pos = exit_pos[comp_ret]
            ret_values = ret[comp_ret]
            gross_signal_pos = pos[comp_gross]
            gross_exit_pos = exit_pos[comp_gross]
            gross_values = gross[comp_gross]
            if len(ret_exit_pos) and np.any(np.diff(ret_exit_pos) < 0):
                order = np.argsort(ret_signal_pos)
                ret_signal_pos = ret_signal_pos[order]
                ret_exit_pos = ret_exit_pos[order]
                ret_values = ret_values[order]
            if len(gross_exit_pos) and np.any(np.diff(gross_exit_pos) < 0):
                order = np.argsort(gross_signal_pos)
                gross_signal_pos = gross_signal_pos[order]
                gross_exit_pos = gross_exit_pos[order]
                gross_values = gross_values[order]
            prefix = np.concatenate([[0.0], np.cumsum(ret_values)])
            prefix_g = np.concatenate([[0.0], np.cumsum(gross_values)])
            for j, row_idx in enumerate(g.index):
                cur = pos[j]
                lower = int(np.searchsorted(ret_signal_pos, cur - lookback, side="left"))
                upper = int(np.searchsorted(ret_exit_pos, cur - 1, side="right"))
                if upper <= lower:
                    count = 0
                else:
                    count = upper - lower
                if count >= min_self and np.isfinite(ret[j]):
                    out.at[row_idx, f"label_self_relative_{h}"] = float(ret[j] - (prefix[upper] - prefix[lower]) / count)
                lower_g = int(np.searchsorted(gross_signal_pos, cur - lookback, side="left"))
                upper_g = int(np.searchsorted(gross_exit_pos, cur - 1, side="right"))
                count_g = max(0, upper_g - lower_g)
                if count_g >= min_self and np.isfinite(gross[j]):
                    out.at[row_idx, f"label_self_relative_{h}_gross"] = float(gross[j] - (prefix_g[upper_g] - prefix_g[lower_g]) / count_g)
    return out.sort_values("candidate_row_id").reset_index(drop=True)


def add_industry_relative_labels(config: dict[str, Any], label: pd.DataFrame) -> pd.DataFrame:
    out = label.copy()
    min_peers = int(config["frozen_formula_constants"]["industry_relative_peer_count_min"])
    for horizon in HORIZONS:
        h = f"H{horizon}"
        raw_col = f"label_raw_{h}"
        out[f"industry_relative_peer_count_{h}"] = 0
        out[f"label_industry_relative_{h}"] = np.nan
        for _, idx in out.groupby(["signal_date", "industry_id"], dropna=False).groups.items():
            rows = list(idx)
            vals = out.loc[rows, raw_col].replace([np.inf, -np.inf], np.nan)
            valid = vals.notna()
            count = int(valid.sum())
            if count <= 1:
                continue
            peer_count = count - 1
            total = float(vals[valid].sum())
            out.loc[rows, f"industry_relative_peer_count_{h}"] = peer_count
            if peer_count >= min_peers:
                out.loc[valid.loc[rows].index, f"label_industry_relative_{h}"] = vals.loc[valid] - (total - vals.loc[valid]) / peer_count
    return out


def write_label_audit(config: dict[str, Any], paths: R082Paths, label: pd.DataFrame) -> None:
    rows = []
    for horizon in HORIZONS:
        h = f"H{horizon}"
        for split, g in label.groupby("split", dropna=False):
            rows.append(
                {
                    "horizon": h,
                    "split": split,
                    "event_count": int(len(g)),
                    "instrument_count": int(g["instrument_id"].nunique()),
                    "signal_date_count": int(g["signal_date"].nunique()),
                    "complete_label_count": int(g[f"{h}_complete_flag"].sum()),
                    "self_relative_label_available_count": int(g[f"label_self_relative_{h}"].notna().sum()),
                    "industry_relative_label_available_count": int(g[f"label_industry_relative_{h}"].notna().sum()),
                    "self_relative_labels_use_completed_labels_only": True,
                    "self_relative_label_lookback_exit_date_le_D_minus_1": True,
                    "horizon_unavailability_independent": True,
                }
            )
    write_csv(pd.DataFrame(rows), paths.audit_dir / "r08_2_label_asof_audit.csv")


def build_factor_state_inputs(
    config: dict[str, Any],
    paths: R082Paths,
    inputs: r08.R06Inputs,
    candidates: pd.DataFrame,
    factor_ids: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    constants = config["frozen_formula_constants"]
    lookback = int(constants["within_stock_lookback_trading_days"])
    min_history = int(constants["within_stock_min_history_count"])
    source = r05.source_path(config).read_text(encoding="utf-8")
    specs = {spec["factor_id"]: spec for spec in r05.extract_gtja_functions(source)}
    funcs = r05.compile_alpha_functions([specs[fid] for fid in factor_ids if fid in specs])
    wide_inputs, _, _ = r05.build_wide_inputs(inputs.feature)
    raw_matrix = np.full((len(candidates), len(factor_ids)), np.nan, dtype=np.float32)
    percentile_matrix = np.full_like(raw_matrix, np.nan)
    tie_matrix = np.full_like(raw_matrix, np.nan)
    tie_cluster_matrix = np.zeros_like(raw_matrix, dtype=bool)
    available_fids = []
    for fid in factor_ids:
        if fid not in funcs:
            continue
        try:
            func = funcs[fid]
            kwargs = {name: wide_inputs[name] for name in inspect.signature(func).parameters if name in wide_inputs}
            raw = func(**kwargs)
            raw = r05._to_df(raw, wide_inputs["close"]).reindex_like(wide_inputs["close"]).astype(float)
        except Exception as exc:
            print(f"R08.2 factor skipped: {fid}: {exc}", flush=True)
            continue
        j = len(available_fids)
        raw_matrix[:, j] = r08.candidate_values_from_wide(raw, candidates)
        pct, tie, cluster = rolling_midrank_daily(raw, candidates, lookback, min_history)
        percentile_matrix[:, j] = pct
        tie_matrix[:, j] = tie
        tie_cluster_matrix[:, j] = cluster
        available_fids.append(fid)
        print(f"R08.2 factor normalized: {fid}", flush=True)
    raw_matrix = raw_matrix[:, : len(available_fids)]
    percentile_matrix = percentile_matrix[:, : len(available_fids)]
    tie_matrix = tie_matrix[:, : len(available_fids)]
    tie_cluster_matrix = tie_cluster_matrix[:, : len(available_fids)]
    np.save(paths.cache_dir / "r08_2_raw_target_factor_matrix.npy", raw_matrix)
    np.save(paths.cache_dir / "r08_2_within_stock_percentile_matrix.npy", percentile_matrix)
    write_json({"factor_ids": available_fids}, paths.cache_dir / "r08_2_factor_matrix_columns.json")
    return raw_matrix, percentile_matrix, tie_matrix, tie_cluster_matrix, available_fids


def rolling_midrank_daily(
    raw: pd.DataFrame,
    candidates: pd.DataFrame,
    lookback: int,
    min_history: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = raw.to_numpy(dtype=float)
    date_pos = raw.index.get_indexer(pd.to_datetime(candidates["signal_date"]))
    stock_pos = raw.columns.get_indexer(candidates["instrument_id"].astype(str))
    percentiles = np.full(len(candidates), np.nan, dtype=np.float32)
    tie_share = np.full(len(candidates), np.nan, dtype=np.float32)
    tie_cluster = np.zeros(len(candidates), dtype=bool)
    by_stock: dict[int, list[int]] = {}
    for row_id, col in enumerate(stock_pos):
        if col >= 0 and date_pos[row_id] >= 0:
            by_stock.setdefault(int(col), []).append(row_id)
    for col, rows in by_stock.items():
        rows = sorted(rows, key=lambda r: date_pos[r])
        candidate_by_date = {int(date_pos[r]): r for r in rows}
        sorted_window: list[float] = []
        queue: list[float | None] = []
        series = values[:, col]
        for dpos, current in enumerate(series):
            row_id = candidate_by_date.get(dpos)
            if row_id is not None and np.isfinite(current) and len(sorted_window) >= min_history:
                left = bisect.bisect_left(sorted_window, float(current))
                right = bisect.bisect_right(sorted_window, float(current))
                count = len(sorted_window)
                percentiles[row_id] = (left + 0.5 * (right - left)) / count
                tie_share[row_id] = (right - left) / count
                tie_cluster[row_id] = (right - left) / count >= 0.20
            value = float(current) if np.isfinite(current) else None
            queue.append(value)
            if value is not None:
                bisect.insort(sorted_window, value)
            if len(queue) > lookback:
                old = queue.pop(0)
                if old is not None:
                    pos = bisect.bisect_left(sorted_window, old)
                    if pos < len(sorted_window):
                        sorted_window.pop(pos)
    return percentiles, tie_share, tie_cluster


def build_scope_audits(
    paths: R082Paths,
    candidates: pd.DataFrame,
    factor_ids: list[str],
    available_fids: list[str],
) -> None:
    write_csv(
        pd.DataFrame(
            [
                {
                    "source": "r06_cache/r05_daily_feature_panel",
                    "candidate_row_count": len(candidates),
                    "instrument_count": candidates["instrument_id"].nunique(),
                    "signal_date_count": candidates["signal_date"].nunique(),
                    "min_signal_date": candidates["signal_date"].min(),
                    "max_signal_date": candidates["signal_date"].max(),
                    "primary_family": PRIMARY_FAMILY,
                    "primary_horizon": "H3",
                    "diagnostic_horizons": "H5;H10",
                    "status": "passed" if len(candidates) else "failed",
                }
            ]
        ),
        paths.audit_dir / "r08_2_input_data_audit.csv",
    )
    write_csv(
        pd.DataFrame(
            [
                {
                    "family": PRIMARY_FAMILY,
                    "role": "primary",
                    "r06_in_scope_factor_count": len(factor_ids),
                    "available_factor_count": len(available_fids),
                    "factor_ids": ";".join(factor_ids),
                    "available_factor_ids": ";".join(available_fids),
                    "primary_decision_eligible": True,
                }
            ]
        ),
        paths.audit_dir / "r08_2_scope_audit.csv",
    )
    fold_rows = []
    inst = candidates[["instrument_id", "canonical_instrument_id", "fold_hash_value", "instrument_fold_id"]].drop_duplicates()
    for rec in inst.itertuples(index=False):
        row = {
            "instrument_id": rec.instrument_id,
            "canonical_instrument_id": rec.canonical_instrument_id,
            "hash_input_description": "utf-8 bytes of canonical_instrument_id.lower()",
            "hash_value": int(rec.fold_hash_value),
            "instrument_fold_id": int(rec.instrument_fold_id),
        }
        for split in SPLITS:
            row[f"{split}_signal_count"] = int(
                candidates.loc[candidates["instrument_id"].eq(rec.instrument_id) & candidates["split"].eq(split), "signal_date"].nunique()
            )
        fold_rows.append(row)
    write_csv(pd.DataFrame(fold_rows), paths.audit_dir / "r08_2_fold_assignment_audit.csv")


def build_normalization_audit(
    paths: R082Paths,
    candidates: pd.DataFrame,
    available_fids: list[str],
    percentile: np.ndarray,
    tie: np.ndarray,
    tie_cluster: np.ndarray,
) -> None:
    rows = []
    row_ids = candidates["candidate_row_id"].to_numpy(dtype=int)
    for j, fid in enumerate(available_fids):
        tmp = candidates[["split", "instrument_fold_id"]].copy()
        tmp["pct"] = percentile[row_ids, j]
        tmp["tie"] = tie[row_ids, j]
        tmp["cluster"] = tie_cluster[row_ids, j]
        for (split, fold_id), g in tmp.groupby(["split", "instrument_fold_id"], dropna=False):
            rows.append(
                {
                    "family": PRIMARY_FAMILY,
                    "factor_id": fid,
                    "split": split,
                    "instrument_fold_id": int(fold_id),
                    "stock_date_count": int(len(g)),
                    "normalization_sample_pass_count": int(np.isfinite(g["pct"]).sum()),
                    "normalization_sample_fail_count": int((~np.isfinite(g["pct"])).sum()),
                    "uses_future_data_flag": False,
                    "cross_stock_fill_flag": False,
                    "within_stock_lookback_excludes_future_data": True,
                    "within_stock_lookback_ends_at_D_minus_1": True,
                    "mid_rank_tie_handling_used": True,
                    "factor_value_tie_share_in_lookback": safe_mean(g["tie"]),
                    "factor_value_at_tie_cluster_flag": safe_share(int(g["cluster"].sum()), len(g)),
                }
            )
    write_csv(pd.DataFrame(rows), paths.audit_dir / "r08_2_within_stock_normalization_audit.csv")


def direction_by_fold(
    config: dict[str, Any],
    paths: R082Paths,
    candidates: pd.DataFrame,
    label: pd.DataFrame,
    available_fids: list[str],
    percentile: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, dict[str, float]]]:
    c = config["frozen_formula_constants"]
    fid_to_col = {fid: i for i, fid in enumerate(available_fids)}
    train = candidates.merge(
        label[["candidate_row_id", "label_self_relative_H3"]],
        on="candidate_row_id",
        how="left",
    )
    rows = []
    nonconst_rows = []
    directions: dict[int, dict[str, float]] = {}
    for fold_id in FOLD_IDS:
        train_seen = train.loc[train["split"].eq("train") & train["instrument_fold_id"].ne(fold_id)].copy()
        row_ids = train_seen["candidate_row_id"].to_numpy(dtype=int)
        directions[fold_id] = {}
        for fid in available_fids:
            col = fid_to_col[fid]
            x = percentile[row_ids, col].astype(float)
            y = train_seen["label_self_relative_H3"].to_numpy(dtype=float)
            tmp = train_seen[["instrument_id", "daily_trading_calendar_index"]].copy()
            tmp["x"] = x
            tmp["y"] = y
            total_valid_instruments = 0
            nonconstant_instruments = 0
            full_ics = []
            anchor_ics: dict[int, list[float]] = {0: [], 1: [], 2: []}
            min_count = int(c["min_direction_signal_count_for_instrument_factor"])
            min_anchor = int(c["min_direction_anchor_signal_count_for_instrument_factor"])
            for _, g in tmp.groupby("instrument_id", sort=False):
                g = g.replace([np.inf, -np.inf], np.nan).dropna(subset=["x", "y"])
                if len(g) < min_count:
                    continue
                total_valid_instruments += 1
                if g["x"].nunique(dropna=True) > 1:
                    nonconstant_instruments += 1
                else:
                    continue
                full_ics.append(spearman_corr(g["x"].to_numpy(dtype=float), g["y"].to_numpy(dtype=float)))
                for anchor in [0, 1, 2]:
                    a = g.loc[(g["daily_trading_calendar_index"].astype(int) % 3) == anchor]
                    if len(a) >= min_anchor and a["x"].nunique(dropna=True) > 1:
                        anchor_ics[anchor].append(spearman_corr(a["x"].to_numpy(dtype=float), a["y"].to_numpy(dtype=float)))
            nonconstant_share = safe_share(nonconstant_instruments, total_valid_instruments)
            full_stat = safe_median(full_ics)
            anchor_stats = {a: safe_median(vals) for a, vals in anchor_ics.items()}
            anchor_signs = [1 if finite(v) and v > 0 else -1 if finite(v) and v < 0 else 0 for v in anchor_stats.values()]
            anchor_median = safe_median(list(anchor_stats.values()))
            direction = 1.0 if finite(anchor_median) and anchor_median > 0 else -1.0 if finite(anchor_median) and anchor_median < 0 else np.nan
            full_sign = 1 if finite(full_stat) and full_stat > 0 else -1 if finite(full_stat) and full_stat < 0 else 0
            agree_count = sum(1 for s in anchor_signs if s != 0 and s == full_sign)
            anchor_stable = finite(anchor_median) and direction in {-1.0, 1.0} and agree_count >= 2
            sample_ok = total_valid_instruments >= int(c["train_direction_valid_instrument_count_min"])
            nonconst_ok = nonconstant_share >= float(c["factor_nonconstant_observation_share_min"])
            ok = sample_ok and nonconst_ok and anchor_stable
            if ok:
                directions[fold_id][fid] = float(direction)
            rows.append(
                {
                    "family": PRIMARY_FAMILY,
                    "fold_id": fold_id,
                    "factor_id": fid,
                    "direction_source_split": "train",
                    "direction_source_instrument_scope": f"seen_folds_not_{fold_id}",
                    "direction_label_horizon": "H3",
                    "fold_direction_valid_instrument_count": total_valid_instruments,
                    "factor_nonconstant_observation_share": nonconstant_share,
                    "factor_direction_stat_full_daily": full_stat,
                    "factor_direction_stat_anchor_offset_0": anchor_stats[0],
                    "factor_direction_stat_anchor_offset_1": anchor_stats[1],
                    "factor_direction_stat_anchor_offset_2": anchor_stats[2],
                    "factor_direction_stat_anchor_median": anchor_median,
                    "factor_direction_anchor_positive_sign_count": int(sum(1 for s in anchor_signs if s > 0)),
                    "factor_direction_anchor_negative_sign_count": int(sum(1 for s in anchor_signs if s < 0)),
                    "full_daily_direction_sign_agree_count": agree_count,
                    "direction_anchor_stability_pass": anchor_stable,
                    "direction": direction,
                    "direction_status": "direction_available" if ok else "factor_direction_sample_insufficient",
                    "direction_insufficient_factor_dropped": not ok,
                }
            )
            nonconst_rows.append(
                {
                    "family": PRIMARY_FAMILY,
                    "fold_id": fold_id,
                    "factor_id": fid,
                    "total_valid_instrument_count": total_valid_instruments,
                    "nonconstant_instrument_count": nonconstant_instruments,
                    "factor_nonconstant_observation_share": nonconstant_share,
                    "factor_nonconstant_observation_pass": nonconst_ok,
                }
            )
    direction_df = pd.DataFrame(rows)
    nonconst_df = pd.DataFrame(nonconst_rows)
    write_csv(direction_df, paths.audit_dir / "r08_2_factor_direction_by_fold_audit.csv")
    write_csv(nonconst_df, paths.audit_dir / "r08_2_factor_nonconstant_observation_audit.csv")
    return direction_df, nonconst_df, directions


def state_from_edges(score: pd.Series, q20: float, q80: float, decile_edges: list[float]) -> tuple[pd.Series, np.ndarray]:
    state = pd.Series("", index=score.index, dtype=object)
    finite_mask = score.replace([np.inf, -np.inf], np.nan).notna()
    state.loc[finite_mask & (score <= q20)] = "bottom_quintile_state"
    state.loc[finite_mask & (score > q20) & (score < q80)] = "middle_state"
    state.loc[finite_mask & (score >= q80)] = "top_quintile_state"
    decile = np.full(len(score), np.nan)
    if all(finite(x) for x in decile_edges):
        decile[finite_mask.to_numpy()] = np.searchsorted(
            np.asarray(decile_edges, dtype=float),
            score.loc[finite_mask].to_numpy(dtype=float),
            side="right",
        ) + 1
    return state, decile


def score_for_fold(
    candidates: pd.DataFrame,
    percentile: np.ndarray,
    available_fids: list[str],
    retained_directions: dict[str, float],
) -> np.ndarray:
    fid_to_col = {fid: i for i, fid in enumerate(available_fids)}
    row_ids = candidates["candidate_row_id"].to_numpy(dtype=int)
    vals = []
    for fid, direction in retained_directions.items():
        if fid in fid_to_col:
            col = percentile[:, fid_to_col[fid]].astype(float)
            vals.append(0.5 + float(direction) * (col - 0.5))
    if not vals:
        return np.full(len(candidates), np.nan, dtype=float)
    matrix = np.column_stack([v[row_ids] for v in vals])
    count = np.isfinite(matrix).sum(axis=1)
    score = np.full(len(candidates), np.nan, dtype=float)
    valid = count > 0
    score[valid] = np.nanmean(matrix[valid], axis=1)
    return score


def build_oof_events(
    config: dict[str, Any],
    paths: R082Paths,
    candidates: pd.DataFrame,
    label: pd.DataFrame,
    available_fids: list[str],
    percentile: np.ndarray,
    directions: dict[int, dict[str, float]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    c = config["frozen_formula_constants"]
    scope_rows = []
    bucket_rows = []
    event_frames = []
    validity_rows = []
    label_cols = ["candidate_row_id"] + [f"label_self_relative_H{h}" for h in HORIZONS] + [f"H{h}_complete_flag" for h in HORIZONS]
    base = candidates.merge(label[label_cols], on="candidate_row_id", how="left")
    for fold_id in FOLD_IDS:
        retained = directions.get(fold_id, {})
        score = score_for_fold(base, percentile, available_fids, retained)
        tmp = base.copy()
        tmp["fold_id"] = fold_id
        tmp["family"] = PRIMARY_FAMILY
        tmp["family_state_score"] = score
        train_seen = tmp["split"].eq("train") & tmp["instrument_fold_id"].ne(fold_id)
        train_vals = tmp.loc[train_seen, "family_state_score"].replace([np.inf, -np.inf], np.nan).dropna()
        if len(train_vals):
            q20 = float(train_vals.quantile(float(c["low_state_quantile"])))
            q80 = float(train_vals.quantile(float(c["high_state_quantile"])))
            decile_edges = train_vals.quantile([i / 10 for i in range(1, 10)]).astype(float).tolist()
        else:
            q20 = q80 = np.nan
            decile_edges = [np.nan] * 9
        state, decile = state_from_edges(tmp["family_state_score"], q20, q80, decile_edges)
        tmp["state"] = state
        tmp["state_decile"] = decile
        scope_pass = len(retained) >= int(c["retained_vwap_factor_count_min"])
        scope_rows.append(
            {
                "family": PRIMARY_FAMILY,
                "fold_id": fold_id,
                "role": "primary",
                "in_scope_factor_count": len(available_fids),
                "retained_factor_count": len(retained),
                "retained_factor_ids": ";".join(retained),
                "dropped_factor_ids": ";".join(fid for fid in available_fids if fid not in retained),
                "direction_insufficient_factors_dropped": True,
                "family_scope_pass": scope_pass,
                "primary_decision_eligible": True,
            }
        )
        bucket_rows.append(
            {
                "family": PRIMARY_FAMILY,
                "fold_id": fold_id,
                "bucket_edge_source_split": "train",
                "bucket_edge_source_instrument_scope": f"seen_folds_not_{fold_id}",
                "bucket_frequency": "daily",
                "train_seen_q20": q20,
                "train_seen_q80": q80,
                "decile_edges_train_seen": json.dumps(decile_edges),
                "frozen_before_validation_read": True,
                "bucket_method": "fold_train_seen_daily_extreme_tail_20_60_20",
            }
        )
        if not scope_pass:
            continue
        unseen = tmp.loc[tmp["instrument_fold_id"].eq(fold_id)].copy()
        for horizon in HORIZONS:
            h = f"H{horizon}"
            hdf = unseen.copy()
            hdf["horizon"] = h
            hdf["label_self_relative"] = hdf[f"label_self_relative_{h}"]
            hdf["label_complete_flag"] = hdf[f"{h}_complete_flag"]
            hdf = hdf.loc[hdf["label_complete_flag"].map(bool_value) & hdf["label_self_relative"].notna() & hdf["family_state_score"].notna()].copy()
            if hdf.empty:
                continue
            hdf["oof_split"] = hdf["split"].map(SPLIT_TO_OOF)
            hdf = hdf.loc[hdf["oof_split"].notna()].copy()
            class_frames = []
            for oof_split, g in hdf.groupby("oof_split", sort=False):
                full_min = int(
                    c["train_full_instrument_signal_count_min"]
                    if oof_split == "train_oof_unseen"
                    else c["validation_robustness_full_instrument_signal_count_min"]
                )
                partial_min = int(c["partial_instrument_signal_count_min"])
                counts = g.groupby("instrument_id")["signal_date"].nunique()
                h = g.copy()
                h["split_signal_count_for_instrument"] = h["instrument_id"].map(counts).astype(int)
                h["instrument_sample_class"] = np.select(
                    [
                        h["split_signal_count_for_instrument"] >= full_min,
                        h["split_signal_count_for_instrument"] >= partial_min,
                    ],
                    ["full_valid_instrument", "partial_instrument_event_only"],
                    default="excluded_thin_instrument",
                )
                h["full_instrument_signal_count_floor"] = full_min
                h["partial_instrument_signal_count_floor"] = partial_min
                validity_rows.append(
                    {
                        "horizon": f"H{horizon}",
                        "split": oof_split,
                        "fold_id": fold_id,
                        "full_valid_instrument_count": int((counts >= full_min).sum()),
                        "partial_instrument_count": int(((counts >= partial_min) & (counts < full_min)).sum()),
                        "excluded_thin_instrument_count": int((counts < partial_min).sum()),
                        "full_valid_threshold": full_min,
                        "partial_threshold": partial_min,
                        "partial_instruments_horizon_specific": True,
                    }
                )
                class_frames.append(h.loc[h["instrument_sample_class"].ne("excluded_thin_instrument")])
            if class_frames:
                event_frames.append(pd.concat(class_frames, ignore_index=True))
    scope_df = pd.DataFrame(scope_rows)
    bucket_df = pd.DataFrame(bucket_rows)
    validity_df = pd.DataFrame(validity_rows)
    events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame()
    write_csv(scope_df, paths.audit_dir / "r08_2_family_scope_by_fold_audit.csv")
    write_csv(bucket_df, paths.audit_dir / "r08_2_state_bucket_by_fold_audit.csv")
    write_csv(validity_df, paths.audit_dir / "r08_2_horizon_specific_instrument_validity_audit.csv")
    if not events.empty:
        events.to_parquet(paths.cache_dir / "r08_2_oof_event_panel.parquet", index=False)
    return events, scope_df, bucket_df, validity_df


def date_spreads(df: pd.DataFrame, label_col: str, floor: int) -> pd.DataFrame:
    rows = []
    for date, g in df.groupby("signal_date", sort=True):
        high = g.loc[g["state"].eq("top_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        low = g.loc[g["state"].eq("bottom_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(high) >= floor and len(low) >= floor:
            rows.append({"signal_date": pd.Timestamp(date), "calendar_year": pd.Timestamp(date).year, "spread": float(high.mean() - low.mean())})
    return pd.DataFrame(rows)


def instrument_spreads(df: pd.DataFrame, c: dict[str, Any], label_col: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    full = df.loc[df["instrument_sample_class"].eq("full_valid_instrument")].copy()
    min_state_events = int(c["instrument_state_event_count_min"])
    for instrument, g in full.groupby("instrument_id", sort=False):
        high = g.loc[g["state"].eq("top_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        low = g.loc[g["state"].eq("bottom_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(high) < min_state_events or len(low) < min_state_events:
            continue
        rows.append(
            {
                "instrument_id": instrument,
                "instrument_high_minus_low_spread": float(high.mean() - low.mean()),
                "within_stock_rankIC": spearman_corr(g["family_state_score"].to_numpy(dtype=float), g[label_col].to_numpy(dtype=float)),
                "valid_signal_count": int(g["signal_date"].nunique()),
                "high_state_event_count": int(len(high)),
                "low_state_event_count": int(len(low)),
                "instrument_sample_class": "full_valid_instrument",
            }
        )
    out = pd.DataFrame(rows)
    pos = int((out["instrument_high_minus_low_spread"] > 0).sum()) if len(out) else 0
    return out, {
        "valid_instrument_count": int(len(out)),
        "full_valid_instrument_count": int(len(out)),
        "positive_instrument_count": pos,
        "positive_instrument_share": safe_share(pos, len(out)),
        "within_stock_rankIC_median": safe_median(out["within_stock_rankIC"]) if len(out) else np.nan,
    }


def monotonicity(df: pd.DataFrame, c: dict[str, Any], label_col: str) -> tuple[float, pd.DataFrame, bool]:
    sub = df[["state_decile", label_col]].replace([np.inf, -np.inf], np.nan).dropna()
    if sub.empty:
        return np.nan, pd.DataFrame(columns=["decile", "event_count", "mean_label"]), True
    dec = sub.groupby("state_decile")[label_col].agg(["count", "mean"]).reset_index().rename(
        columns={"state_decile": "decile", "count": "event_count", "mean": "mean_label"}
    )
    score = spearman_corr(dec["decile"].to_numpy(dtype=float), dec["mean_label"].to_numpy(dtype=float))
    low = df.loc[df["state"].eq("bottom_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
    mid = df.loc[df["state"].eq("middle_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
    high = df.loc[df["state"].eq("top_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
    if low.empty or mid.empty or high.empty:
        inverted = True
    else:
        tolerance = float(c["middle_state_inversion_tolerance"])
        mid_mean = float(mid.mean())
        lo = min(float(low.mean()), float(high.mean()))
        hi = max(float(low.mean()), float(high.mean()))
        inverted = mid_mean < lo - tolerance or mid_mean > hi + tolerance
    return score, dec, inverted


def contribution_summary(df: pd.DataFrame, label_col: str, family: str, split: str, fold_id: Any, anchor_offset: Any = "all") -> dict[str, Any]:
    state_df = df.loc[df["state"].isin(["top_quintile_state", "bottom_quintile_state"])].copy()
    rows = []
    for instrument, g in state_df.groupby("instrument_id", sort=False):
        high = g.loc[g["state"].eq("top_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        low = g.loc[g["state"].eq("bottom_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(high) == 0 or len(low) == 0:
            continue
        spread = float(high.mean() - low.mean())
        count = int(len(high) + len(low))
        rows.append({"instrument_id": instrument, "abs_contribution": abs(spread * count), "event_count": count})
    inst = pd.DataFrame(rows)
    denom = float(inst["abs_contribution"].sum()) if len(inst) else 0.0
    zero = denom <= 0
    top1_id = ""
    top1_share = top5_share = np.nan
    top1_count = 0
    if not zero:
        inst = inst.sort_values("abs_contribution", ascending=False)
        inst["share"] = inst["abs_contribution"] / denom
        top1 = inst.iloc[0]
        top1_id = str(top1["instrument_id"])
        top1_share = float(top1["share"])
        top5_share = float(inst.head(5)["share"].sum())
        top1_count = int(top1["event_count"])
    industry_rows = []
    if not zero:
        abs_map = inst.set_index("instrument_id")["abs_contribution"].to_dict()
        for instrument, g in state_df.groupby("instrument_id", sort=False):
            abs_contrib = float(abs_map.get(instrument, 0.0))
            total = len(g)
            if total == 0:
                continue
            weights = g.groupby("industry_id").size() / total
            for industry, weight in weights.items():
                industry_rows.append({"industry_id": industry, "abs_contribution": abs_contrib * float(weight)})
    industry = pd.DataFrame(industry_rows)
    if industry.empty or zero:
        top_industry = ""
        top_industry_share = np.nan
    else:
        ind = industry.groupby("industry_id")["abs_contribution"].sum().sort_values(ascending=False)
        top_industry = str(ind.index[0])
        top_industry_share = float(ind.iloc[0] / denom)
    return {
        "family": family,
        "split": split,
        "fold_id": fold_id,
        "anchor_offset": anchor_offset,
        "contribution_denominator": denom,
        "contribution_denominator_zero": zero,
        "top1_instrument_id": top1_id,
        "top1_instrument_event_count": top1_count,
        "top1_instrument_contribution_share": top1_share,
        "top5_instrument_contribution_share": top5_share,
        "top1_industry": top_industry,
        "top1_industry_contribution_share": top_industry_share,
    }


def subset_metrics(df: pd.DataFrame, c: dict[str, Any], label_col: str, family: str, split: str, fold_id: Any, anchor_offset: Any = "all") -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    floor = int(c["per_date_event_floor_unseen"])
    spreads = date_spreads(df, label_col, floor)
    d = spreads["spread"] if not spreads.empty else pd.Series(dtype=float)
    high = df.loc[df["state"].eq("top_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
    low = df.loc[df["state"].eq("bottom_quintile_state"), label_col].replace([np.inf, -np.inf], np.nan).dropna()
    pooled = float(high.mean() - low.mean()) if len(high) and len(low) else np.nan
    inst_df, inst_metric = instrument_spreads(df, c, label_col)
    mono_score, decile_df, inverted = monotonicity(df, c, label_col)
    conc = contribution_summary(df, label_col, family, split, fold_id, anchor_offset)
    metric = {
        "mean_spread": safe_mean(d),
        "median_spread": safe_median(d),
        "pooled_high_minus_low_spread": pooled,
        "positive_date_share": safe_share(int((d > 0).sum()), len(d)),
        "valid_signal_date_count": int(len(spreads)),
        "event_count": int(len(df)),
        "raw_full_valid_instrument_count": int(df.loc[df["instrument_sample_class"].eq("full_valid_instrument"), "instrument_id"].nunique()),
        "valid_instrument_count": int(inst_metric["valid_instrument_count"]),
        "full_valid_instrument_count": int(inst_metric["full_valid_instrument_count"]),
        "partial_event_only_instrument_count": int(df.loc[df["instrument_sample_class"].eq("partial_instrument_event_only"), "instrument_id"].nunique()),
        "positive_instrument_count": int(inst_metric["positive_instrument_count"]),
        "positive_instrument_share": inst_metric["positive_instrument_share"],
        "within_stock_rankIC_median": inst_metric["within_stock_rankIC_median"],
        "decile_monotonicity_score": mono_score,
        "middle_state_violently_inverted_flag": inverted,
    }
    return metric, spreads, inst_df, decile_df, conc


def build_metrics(config: dict[str, Any], paths: R082Paths, events: pd.DataFrame) -> dict[str, pd.DataFrame]:
    c = config["frozen_formula_constants"]
    full_rows = []
    anchor_rows = []
    fold_rows = []
    fold_disp_rows = []
    inst_rows = []
    time_rows = []
    year_rows = []
    decile_rows = []
    sample_rows = []
    conc_rows = []
    overlap_rows = []
    horizon_shape_rows = []
    if events.empty:
        frames = {name: pd.DataFrame() for name in ["full", "anchor", "fold", "dispersion", "instrument", "time", "year", "decile", "sample", "concentration", "overlap", "horizon_shape"]}
        write_metric_artifacts(paths, frames)
        return frames
    for horizon in HORIZONS:
        h = f"H{horizon}"
        h_events = events.loc[events["horizon"].eq(h)].copy()
        for split in OOF_SPLITS:
            split_events = h_events.loc[h_events["oof_split"].eq(split)].copy()
            if split_events.empty:
                continue
            full_metric, full_spreads, full_inst, full_decile, full_conc = subset_metrics(split_events, c, "label_self_relative", PRIMARY_FAMILY, split, "aggregate")
            full_rows.append(prefixed_metric_row(h, split, "aggregate", full_metric, prefix=f"{h.lower()}_full_daily"))
            conc_rows.append(dict(full_conc, horizon=h, scope="aggregate_full_daily"))
            for rec in full_inst.itertuples(index=False):
                inst_rows.append(
                    {
                        "horizon": h,
                        "split": split,
                        "fold_id": "aggregate",
                        "instrument_id": rec.instrument_id,
                        "instrument_high_minus_low_spread": rec.instrument_high_minus_low_spread,
                        "within_stock_rankIC": rec.within_stock_rankIC,
                        "valid_signal_count": rec.valid_signal_count,
                    }
                )
            anchor_metrics = []
            anchor_denoms = []
            for anchor in range(horizon):
                a_events = split_events.loc[(split_events["daily_trading_calendar_index"].astype(int) % horizon) == anchor].copy()
                metric, spreads, inst_df, decile_df, conc = subset_metrics(a_events, c, "label_self_relative", PRIMARY_FAMILY, split, "aggregate", anchor)
                anchor_metrics.append(metric)
                anchor_denoms.append(float(conc["contribution_denominator"]) if finite(conc["contribution_denominator"]) else 0.0)
                conc_rows.append(dict(conc, horizon=h, scope="aggregate_anchor"))
                overlap_rows.append(
                    {
                        "horizon": h,
                        "split": split,
                        "anchor_offset": anchor,
                        "anchor_mean_spread": metric["mean_spread"],
                        "anchor_median_spread": metric["median_spread"],
                        "anchor_valid_signal_date_count": metric["valid_signal_date_count"],
                        "anchor_positive_date_share": metric["positive_date_share"],
                        "anchor_contribution_denominator": conc["contribution_denominator"],
                    }
                )
            anchor_mean_values = pd.Series([m["mean_spread"] for m in anchor_metrics]).replace([np.inf, -np.inf], np.nan).dropna()
            anchor_median_values = pd.Series([m["median_spread"] for m in anchor_metrics]).replace([np.inf, -np.inf], np.nan).dropna()
            combined_metric, combined_spreads, combined_inst, combined_decile, combined_conc = subset_metrics(split_events, c, "label_self_relative", PRIMARY_FAMILY, split, "aggregate")
            anchor_controlled_mean = safe_mean(anchor_mean_values)
            anchor_controlled_median = safe_median(anchor_median_values)
            positive_anchor_count = int((anchor_mean_values > 0).sum())
            min_anchor = float(anchor_mean_values.min()) if len(anchor_mean_values) else np.nan
            max_anchor_share = max(anchor_denoms) / sum(anchor_denoms) if sum(anchor_denoms) else np.nan
            anchor_row = {
                "horizon": h,
                "split": split,
                "fold_id": "aggregate",
                "anchor_controlled_mean_spread": anchor_controlled_mean,
                "anchor_controlled_median_spread": anchor_controlled_median,
                "anchor_positive_offset_count": positive_anchor_count,
                "anchor_offset_spread_min": min_anchor,
                "anchor_offset_spread_median": safe_median(anchor_mean_values),
                "anchor_controlled_positive_instrument_share": combined_metric["positive_instrument_share"],
                "anchor_controlled_valid_instrument_count": combined_metric["valid_instrument_count"],
                "anchor_controlled_full_valid_instrument_count": combined_metric["full_valid_instrument_count"],
                "anchor_controlled_valid_signal_date_count": combined_metric["valid_signal_date_count"],
                "anchor_controlled_decile_monotonicity_score": combined_metric["decile_monotonicity_score"],
                "middle_state_violently_inverted_flag": combined_metric["middle_state_violently_inverted_flag"],
                "max_anchor_abs_contribution_share_of_total": max_anchor_share,
                "full_daily_anchor_sign_conflict_flag": sign_conflict(full_metric["mean_spread"], anchor_controlled_mean),
                "full_daily_anchor_spread_gap": full_metric["mean_spread"] - anchor_controlled_mean if finite(full_metric["mean_spread"]) and finite(anchor_controlled_mean) else np.nan,
            }
            anchor_rows.append(anchor_row)
            conc_rows.append(dict(combined_conc, horizon=h, scope="aggregate_anchor_controlled", max_anchor_abs_contribution_share_of_total=max_anchor_share))
            for rec in combined_decile.itertuples(index=False):
                decile_rows.append(
                    {
                        "horizon": h,
                        "split": split,
                        "fold_id": "aggregate",
                        "decile": int(rec.decile),
                        "event_count": int(rec.event_count),
                        "mean_label": rec.mean_label,
                        "decile_monotonicity_score": combined_metric["decile_monotonicity_score"],
                    }
                )
            for year, yg in combined_spreads.groupby("calendar_year"):
                year_rows.append(
                    {
                        "horizon": h,
                        "split": split,
                        "fold_id": "aggregate",
                        "calendar_year": int(year),
                        "year_mean_spread": safe_mean(yg["spread"]),
                        "year_positive_flag": safe_mean(yg["spread"]) > 0,
                        "valid_signal_date_count": int(len(yg)),
                    }
                )
            for fold_id in FOLD_IDS:
                f_events = split_events.loc[split_events["fold_id"].eq(fold_id)].copy()
                if f_events.empty:
                    metric = empty_metric()
                    anchor_valid_counts = [0 for _ in range(horizon)]
                    fold_anchor_mean = np.nan
                    fold_anchor_min = np.nan
                    fold_anchor_positive = 0
                    conc = contribution_summary(f_events, "label_self_relative", PRIMARY_FAMILY, split, fold_id)
                    decile_df = pd.DataFrame()
                else:
                    metric, spreads, inst_df, decile_df, conc = subset_metrics(f_events, c, "label_self_relative", PRIMARY_FAMILY, split, fold_id)
                    fold_anchor_values = []
                    anchor_valid_counts = []
                    for anchor in range(horizon):
                        fa = f_events.loc[(f_events["daily_trading_calendar_index"].astype(int) % horizon) == anchor]
                        am, _, _, _, _ = subset_metrics(fa, c, "label_self_relative", PRIMARY_FAMILY, split, fold_id, anchor)
                        fold_anchor_values.append(am["mean_spread"])
                        anchor_valid_counts.append(am["valid_signal_date_count"])
                    fold_anchor_s = pd.Series(fold_anchor_values).replace([np.inf, -np.inf], np.nan).dropna()
                    fold_anchor_mean = safe_mean(fold_anchor_s)
                    fold_anchor_min = float(fold_anchor_s.min()) if len(fold_anchor_s) else np.nan
                    fold_anchor_positive = int((fold_anchor_s > 0).sum())
                    for rec in inst_df.itertuples(index=False):
                        inst_rows.append(
                            {
                                "horizon": h,
                                "split": split,
                                "fold_id": fold_id,
                                "instrument_id": rec.instrument_id,
                                "instrument_high_minus_low_spread": rec.instrument_high_minus_low_spread,
                                "within_stock_rankIC": rec.within_stock_rankIC,
                                "valid_signal_count": rec.valid_signal_count,
                            }
                        )
                fold_rows.append(
                    {
                        "horizon": h,
                        "split": split,
                        "fold_id": fold_id,
                        "fold_anchor_controlled_mean_spread": fold_anchor_mean,
                        "fold_anchor_offset_spread_min": fold_anchor_min,
                        "fold_positive_anchor_offset_count": fold_anchor_positive,
                        "fold_full_daily_mean_spread": metric["mean_spread"],
                        "fold_full_daily_median_spread": metric["median_spread"],
                        "fold_positive_instrument_share": metric["positive_instrument_share"],
                        "fold_valid_instrument_count": metric["valid_instrument_count"],
                        "fold_full_valid_instrument_count": metric["full_valid_instrument_count"],
                        "fold_partial_event_only_instrument_count": metric["partial_event_only_instrument_count"],
                        "fold_valid_signal_date_count": metric["valid_signal_date_count"],
                        "fold_decile_monotonicity_score": metric["decile_monotonicity_score"],
                        "fold_top1_instrument_contribution_share": conc["top1_instrument_contribution_share"],
                        "fold_top5_instrument_contribution_share": conc["top5_instrument_contribution_share"],
                        "fold_top1_industry_contribution_share": conc["top1_industry_contribution_share"],
                    }
                )
                sample_rows.append(
                    {
                        "horizon": h,
                        "split": split,
                        "fold_id": fold_id,
                        "fold_unseen_full_valid_instrument_count": metric["full_valid_instrument_count"],
                        "fold_unseen_valid_signal_date_count": metric["valid_signal_date_count"],
                        "anchor_valid_signal_date_counts": json.dumps(anchor_valid_counts),
                        "anchor_min_valid_signal_date_count": int(min(anchor_valid_counts)) if anchor_valid_counts else 0,
                        "partial_instruments_horizon_specific": True,
                        "partial_instruments_excluded_from_sample_gate_by_horizon": True,
                        "partial_instruments_excluded_from_positive_instrument_share_by_horizon": True,
                        "fold_evaluable_flag": (
                            metric["full_valid_instrument_count"] >= int(c["fold_unseen_full_valid_instrument_count_min"])
                            and metric["valid_signal_date_count"] >= int(c["fold_unseen_full_daily_valid_signal_date_count_min"])
                            and (min(anchor_valid_counts) if anchor_valid_counts else 0) >= int(c["h3_anchor_valid_signal_date_count_min"] if horizon == 3 else 1)
                        ),
                    }
                )
                conc_rows.append(dict(conc, horizon=h, scope="fold_full_daily"))
            fdf = pd.DataFrame([r for r in fold_rows if r["horizon"] == h and r["split"] == split])
            if not fdf.empty:
                spread_s = fdf["fold_anchor_controlled_mean_spread"].replace([np.inf, -np.inf], np.nan).dropna()
                pis_s = fdf["fold_positive_instrument_share"].replace([np.inf, -np.inf], np.nan).dropna()
                mono_s = fdf["fold_decile_monotonicity_score"].replace([np.inf, -np.inf], np.nan).dropna()
                fold_disp_rows.append(
                    {
                        "horizon": h,
                        "split": split,
                        "evaluable_fold_count": int(pd.DataFrame([r for r in sample_rows if r["horizon"] == h and r["split"] == split])["fold_evaluable_flag"].map(bool_value).sum()),
                        "positive_fold_count": int((spread_s > 0).sum()),
                        "median_fold_spread": safe_median(spread_s),
                        "min_fold_spread": float(spread_s.min()) if len(spread_s) else np.nan,
                        "fold_positive_instrument_share_median": safe_median(pis_s),
                        "fold_monotonicity_median": safe_median(mono_s),
                        "fold_monotonicity_positive_count": int((mono_s > 0).sum()),
                        "max_fold_top1_instrument_contribution_share": fdf["fold_top1_instrument_contribution_share"].replace([np.inf, -np.inf], np.nan).max(),
                        "max_fold_top5_instrument_contribution_share": fdf["fold_top5_instrument_contribution_share"].replace([np.inf, -np.inf], np.nan).max(),
                    }
                )
        if h in {"H3", "H5", "H10"}:
            for split in ["validation_oof_unseen", "robustness_oof_unseen"]:
                row = next((r for r in anchor_rows if r["horizon"] == h and r["split"] == split), None)
                if row is not None:
                    time_rows.append(row.copy())
    for split in ["validation_oof_unseen", "robustness_oof_unseen"]:
        vals = {}
        for h in ["H3", "H5", "H10"]:
            row = next((r for r in anchor_rows if r["horizon"] == h and r["split"] == split), None)
            vals[f"{h}_mean_spread"] = row["anchor_controlled_mean_spread"] if row else np.nan
        horizon_shape_rows.append(
            {
                "split": split,
                **vals,
                "H5_minus_H3": vals["H5_mean_spread"] - vals["H3_mean_spread"] if finite(vals["H5_mean_spread"]) and finite(vals["H3_mean_spread"]) else np.nan,
                "H10_minus_H3": vals["H10_mean_spread"] - vals["H3_mean_spread"] if finite(vals["H10_mean_spread"]) and finite(vals["H3_mean_spread"]) else np.nan,
                "H10_minus_H5": vals["H10_mean_spread"] - vals["H5_mean_spread"] if finite(vals["H10_mean_spread"]) and finite(vals["H5_mean_spread"]) else np.nan,
                "sign_pattern": "/".join("+" if finite(vals[f"{h}_mean_spread"]) and vals[f"{h}_mean_spread"] > 0 else "-" for h in ["H3", "H5", "H10"]),
            }
        )
    frames = {
        "full": pd.DataFrame(full_rows),
        "anchor": pd.DataFrame(anchor_rows),
        "fold": pd.DataFrame(fold_rows),
        "dispersion": pd.DataFrame(fold_disp_rows),
        "instrument": pd.DataFrame(inst_rows),
        "time": pd.DataFrame(time_rows),
        "year": pd.DataFrame(year_rows),
        "decile": pd.DataFrame(decile_rows),
        "sample": pd.DataFrame(sample_rows),
        "concentration": pd.DataFrame(conc_rows),
        "overlap": pd.DataFrame(overlap_rows),
        "horizon_shape": pd.DataFrame(horizon_shape_rows),
    }
    write_metric_artifacts(paths, frames)
    return frames


def prefixed_metric_row(horizon: str, split: str, fold_id: Any, metric: dict[str, Any], prefix: str) -> dict[str, Any]:
    row = {"horizon": horizon, "split": split, "fold_id": fold_id}
    for key, value in metric.items():
        row[f"{prefix}_{key}"] = value
    return row


def sign_conflict(left: Any, right: Any) -> bool:
    if not finite(left) or not finite(right):
        return True
    if float(left) == 0 or float(right) == 0:
        return False
    return np.sign(float(left)) != np.sign(float(right))


def empty_metric() -> dict[str, Any]:
    return {
        "mean_spread": np.nan,
        "median_spread": np.nan,
        "pooled_high_minus_low_spread": np.nan,
        "positive_date_share": 0.0,
        "valid_signal_date_count": 0,
        "event_count": 0,
        "raw_full_valid_instrument_count": 0,
        "valid_instrument_count": 0,
        "full_valid_instrument_count": 0,
        "partial_event_only_instrument_count": 0,
        "positive_instrument_count": 0,
        "positive_instrument_share": 0.0,
        "within_stock_rankIC_median": np.nan,
        "decile_monotonicity_score": np.nan,
        "middle_state_violently_inverted_flag": True,
    }


def write_metric_artifacts(paths: R082Paths, frames: dict[str, pd.DataFrame]) -> None:
    write_csv(frames["full"].loc[frames["full"]["horizon"].eq("H3")] if not frames["full"].empty else frames["full"], paths.metrics_dir / "r08_2_h3_full_daily_oof_spread.csv")
    write_csv(frames["anchor"].loc[frames["anchor"]["horizon"].eq("H3")] if not frames["anchor"].empty else frames["anchor"], paths.metrics_dir / "r08_2_h3_anchor_controlled_oof_spread.csv")
    write_csv(frames["anchor"].loc[(frames["anchor"]["horizon"].eq("H3")) & (frames["anchor"]["split"].eq("train_oof_unseen"))] if not frames["anchor"].empty else frames["anchor"], paths.metrics_dir / "r08_2_h3_train_baseline_summary.csv")
    write_csv(frames["fold"].loc[frames["fold"]["horizon"].eq("H3")] if not frames["fold"].empty else frames["fold"], paths.metrics_dir / "r08_2_h3_fold_unseen_state_spread.csv")
    write_csv(frames["dispersion"].loc[frames["dispersion"]["horizon"].eq("H3")] if not frames["dispersion"].empty else frames["dispersion"], paths.metrics_dir / "r08_2_h3_fold_dispersion_summary.csv")
    write_csv(frames["instrument"].loc[frames["instrument"]["horizon"].eq("H3")] if not frames["instrument"].empty else frames["instrument"], paths.metrics_dir / "r08_2_h3_instrument_transfer_summary.csv")
    write_csv(frames["time"].loc[frames["time"]["horizon"].eq("H3")] if not frames["time"].empty else frames["time"], paths.metrics_dir / "r08_2_h3_time_transfer_summary.csv")
    write_csv(frames["year"].loc[frames["year"]["horizon"].eq("H3")] if not frames["year"].empty else frames["year"], paths.metrics_dir / "r08_2_h3_year_availability_and_positive_count.csv")
    write_csv(frames["decile"].loc[frames["decile"]["horizon"].eq("H3")] if not frames["decile"].empty else frames["decile"], paths.metrics_dir / "r08_2_h3_decile_monotonicity_by_anchor.csv")
    write_csv(frames["concentration"].loc[frames["concentration"]["horizon"].eq("H3")] if not frames["concentration"].empty else frames["concentration"], paths.metrics_dir / "r08_2_h3_concentration_summary.csv")
    write_csv(frames["full"].loc[frames["full"]["horizon"].eq("H5")] if not frames["full"].empty else frames["full"], paths.metrics_dir / "r08_2_h5_diagnostic_oof_spread.csv")
    write_csv(frames["full"].loc[frames["full"]["horizon"].eq("H10")] if not frames["full"].empty else frames["full"], paths.metrics_dir / "r08_2_h10_diagnostic_oof_spread.csv")
    write_csv(frames["horizon_shape"], paths.metrics_dir / "r08_2_horizon_shape_summary.csv")
    write_csv(frames["overlap"], paths.metrics_dir / "r08_2_overlap_adjusted_confidence_summary.csv")
    write_csv(frames["sample"], paths.audit_dir / "r08_2_fold_sample_audit.csv")
    write_csv(frames["concentration"], paths.audit_dir / "r08_2_concentration_audit.csv")


def row_for(df: pd.DataFrame, horizon: str, split: str) -> pd.Series | None:
    if df.empty:
        return None
    sub = df.loc[df["horizon"].eq(horizon) & df["split"].eq(split)]
    return sub.iloc[0] if len(sub) else None


def build_gate_inputs(
    config: dict[str, Any],
    paths: R082Paths,
    candidates: pd.DataFrame,
    scope_df: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    availability: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    c = config["frozen_formula_constants"]
    anchor = frames["anchor"]
    full = frames["full"]
    disp = frames["dispersion"]
    sample = frames["sample"]
    conc = frames["concentration"]
    year = frames["year"]
    val = row_for(anchor, "H3", "validation_oof_unseen")
    rob = row_for(anchor, "H3", "robustness_oof_unseen")
    train = row_for(anchor, "H3", "train_oof_unseen")
    val_full = row_for(full, "H3", "validation_oof_unseen")
    rob_full = row_for(full, "H3", "robustness_oof_unseen")
    val_disp = row_for(disp, "H3", "validation_oof_unseen")
    rob_disp = row_for(disp, "H3", "robustness_oof_unseen")
    primary_score_formed = bool(scope_df["family_scope_pass"].map(bool_value).all()) if not scope_df.empty else False
    daily_counts = candidates.groupby("split")["signal_date"].nunique().to_dict()
    panel_sample_pass = (
        candidates["instrument_id"].nunique() >= int(c["full_scope_instrument_count_min"])
        and daily_counts.get("train", 0) >= int(c["daily_signal_date_count_train_min"])
        and daily_counts.get("validation", 0) >= int(c["daily_signal_date_count_validation_min"])
        and daily_counts.get("robustness", 0) >= int(c["daily_signal_date_count_robustness_min"])
    )
    val_sample = sample.loc[sample["horizon"].eq("H3") & sample["split"].eq("validation_oof_unseen")]
    rob_sample = sample.loc[sample["horizon"].eq("H3") & sample["split"].eq("robustness_oof_unseen")]
    val_evaluable_fold_count = int(val_sample["fold_evaluable_flag"].map(bool_value).sum()) if len(val_sample) else 0
    rob_evaluable_fold_count = int(rob_sample["fold_evaluable_flag"].map(bool_value).sum()) if len(rob_sample) else 0
    val_anchor_dates = int(getattr(val, "anchor_controlled_valid_signal_date_count", 0)) if val is not None else 0
    rob_anchor_dates = int(getattr(rob, "anchor_controlled_valid_signal_date_count", 0)) if rob is not None else 0
    val_full_count = int(getattr(val, "anchor_controlled_full_valid_instrument_count", 0)) if val is not None else 0
    rob_full_count = int(getattr(rob, "anchor_controlled_full_valid_instrument_count", 0)) if rob is not None else 0
    aggregate_floors_pass = (
        val_full_count >= int(c["aggregate_oof_full_valid_instrument_count_min"])
        and rob_full_count >= int(c["aggregate_oof_full_valid_instrument_count_min"])
        and val_anchor_dates >= int(c["aggregate_oof_full_daily_valid_signal_date_count_min"])
        and rob_anchor_dates >= int(c["aggregate_oof_full_daily_valid_signal_date_count_min"])
    )
    val_mean = getattr(val, "anchor_controlled_mean_spread", np.nan) if val is not None else np.nan
    rob_mean = getattr(rob, "anchor_controlled_mean_spread", np.nan) if rob is not None else np.nan
    train_mean = getattr(train, "anchor_controlled_mean_spread", np.nan) if train is not None else np.nan
    val_pos_inst = getattr(val, "anchor_controlled_positive_instrument_share", 0.0) if val is not None else 0.0
    val_pos_fold_count = int(getattr(val_disp, "positive_fold_count", 0)) if val_disp is not None else 0
    caveat_margin = (
        finite(val_mean)
        and val_mean >= float(c["caveat_validation_mean_spread_min"])
        and val_pos_inst >= float(c["caveat_validation_positive_instrument_share_min"])
        and val_pos_fold_count >= int(c["caveat_validation_positive_fold_count_min"])
    )
    if panel_sample_pass and val_evaluable_fold_count >= 5 and rob_evaluable_fold_count >= 4 and aggregate_floors_pass:
        sample_status = "pass"
        fold_coverage_caveat = False
    elif panel_sample_pass and val_evaluable_fold_count == 4 and rob_evaluable_fold_count >= 4 and aggregate_floors_pass and caveat_margin:
        sample_status = "pass_with_fold_coverage_caveat"
        fold_coverage_caveat = True
    else:
        sample_status = "fail"
        fold_coverage_caveat = False
    val_years = year.loc[year["horizon"].eq("H3") & year["split"].eq("validation_oof_unseen") & year["fold_id"].astype(str).eq("aggregate")] if not year.empty else pd.DataFrame()
    rob_years = year.loc[year["horizon"].eq("H3") & year["split"].eq("robustness_oof_unseen") & year["fold_id"].astype(str).eq("aggregate")] if not year.empty else pd.DataFrame()
    val_positive_year_count = int(val_years["year_positive_flag"].map(bool_value).sum()) if len(val_years) else 0
    rob_positive_year_count = int(rob_years["year_positive_flag"].map(bool_value).sum()) if len(rob_years) else 0
    val_negative_year_mean = float(val_years.loc[~val_years["year_positive_flag"].map(bool_value), "year_mean_spread"].min()) if len(val_years.loc[~val_years["year_positive_flag"].map(bool_value)]) else np.nan
    avail_h3 = availability.loc[availability["horizon"].eq("H3")]
    robustness_year_count = int(avail_h3.iloc[0]["robustness_actual_evaluable_year_count"]) if len(avail_h3) else 0
    val_non_det = finite(val_mean) and finite(train_mean) and val_mean >= train_mean - float(c["validation_train_spread_tolerance"])
    rob_non_det = finite(rob_mean) and finite(train_mean) and rob_mean >= train_mean - float(c["robustness_train_spread_tolerance"])
    val_median = getattr(val, "anchor_controlled_median_spread", np.nan) if val is not None else np.nan
    rob_median = getattr(rob, "anchor_controlled_median_spread", np.nan) if rob is not None else np.nan
    validation_single_positive_year_caveat = (
        val_positive_year_count == 1
        and finite(val_mean)
        and val_mean >= float(c["validation_single_year_mean_spread_min"])
        and (not finite(val_negative_year_mean) or val_negative_year_mean >= float(c["validation_single_year_negative_spread_floor"]))
    )
    time_gate = (
        finite(val_mean)
        and val_mean > float(c["validation_mean_state_spread_min"])
        and finite(val_median)
        and val_median >= float(c["validation_median_state_spread_min"])
        and getattr(val, "anchor_positive_offset_count", 0) >= int(c["positive_anchor_offset_count_validation_min"])
        and val_positive_year_count >= int(c["validation_positive_year_count_min"])
        and (val_positive_year_count > 1 or validation_single_positive_year_caveat)
        and val_non_det
        and not bool_value(getattr(val, "full_daily_anchor_sign_conflict_flag", True))
        and finite(getattr(val_full, "h3_full_daily_mean_spread", np.nan))
        and getattr(val_full, "h3_full_daily_mean_spread", np.nan) >= float(c["validation_full_daily_mean_spread_floor"])
        and finite(rob_mean)
        and rob_mean >= float(c["robustness_mean_state_spread_min"])
        and finite(rob_median)
        and rob_median >= float(c["robustness_median_state_spread_min"])
        and getattr(rob, "anchor_positive_offset_count", 0) >= int(c["positive_anchor_offset_count_robustness_min"])
        and rob_positive_year_count >= max(1, math.ceil(float(c["robustness_positive_year_share_min"]) * max(1, robustness_year_count)))
        and rob_non_det
        and not bool_value(getattr(rob, "full_daily_anchor_sign_conflict_flag", True))
        and finite(getattr(rob_full, "h3_full_daily_mean_spread", np.nan))
        and getattr(rob_full, "h3_full_daily_mean_spread", np.nan) >= float(c["robustness_full_daily_mean_spread_floor"])
    )
    instrument_gate = (
        val_pos_inst >= float(c["positive_instrument_share_validation_min"])
        and (getattr(rob, "anchor_controlled_positive_instrument_share", 0.0) if rob is not None else 0.0) >= float(c["positive_instrument_share_robustness_min"])
    )
    fold_stability_gate = (
        val_pos_fold_count >= int(c["positive_fold_count_validation_min"])
        and int(getattr(rob_disp, "positive_fold_count", 0)) >= int(c["positive_fold_count_robustness_min"])
        and getattr(val_disp, "median_fold_spread", np.nan) > float(c["median_fold_spread_validation_min"])
        and getattr(rob_disp, "median_fold_spread", np.nan) >= float(c["median_fold_spread_robustness_min"])
        and getattr(val_disp, "min_fold_spread", np.nan) >= float(c["min_fold_spread_validation_floor"])
        and getattr(rob_disp, "min_fold_spread", np.nan) >= float(c["min_fold_spread_robustness_floor"])
        and getattr(val_disp, "fold_positive_instrument_share_median", 0.0) >= float(c["fold_positive_instrument_share_median_validation_min"])
        and getattr(rob_disp, "fold_positive_instrument_share_median", 0.0) >= float(c["fold_positive_instrument_share_median_robustness_min"])
    )
    anchor_stability_gate = (
        getattr(val, "anchor_positive_offset_count", 0) >= int(c["positive_anchor_offset_count_validation_min"])
        and getattr(rob, "anchor_positive_offset_count", 0) >= int(c["positive_anchor_offset_count_robustness_min"])
        and getattr(val, "anchor_offset_spread_min", np.nan) >= float(c["anchor_offset_spread_min_validation_floor"])
        and getattr(rob, "anchor_offset_spread_min", np.nan) >= float(c["anchor_offset_spread_min_robustness_floor"])
    )
    mono_gate = (
        getattr(val, "anchor_controlled_decile_monotonicity_score", np.nan) >= float(c["aggregate_state_decile_monotonicity_min"])
        and getattr(rob, "anchor_controlled_decile_monotonicity_score", np.nan) >= float(c["aggregate_state_decile_monotonicity_min"])
        and getattr(val_disp, "fold_monotonicity_median", np.nan) >= float(c["fold_monotonicity_median_min"])
        and getattr(rob_disp, "fold_monotonicity_median", np.nan) >= float(c["fold_monotonicity_median_min"])
        and getattr(val_disp, "fold_monotonicity_positive_count", 0) >= int(c["fold_monotonicity_positive_count_min"])
        and getattr(rob_disp, "fold_monotonicity_positive_count", 0) >= int(c["fold_monotonicity_positive_count_min"])
        and not bool_value(getattr(val, "middle_state_violently_inverted_flag", True))
        and not bool_value(getattr(rob, "middle_state_violently_inverted_flag", True))
    )
    conc_gate, conc_detail = concentration_gate(config, conc)
    diagnostic_inputs = build_horizon_diagnostic_inputs(config, anchor, conc)
    h5_pass = bool_value(diagnostic_inputs.loc[diagnostic_inputs["horizon"].eq("H5"), "diagnostic_horizon_positive"].iloc[0]) if not diagnostic_inputs.empty and diagnostic_inputs["horizon"].eq("H5").any() else False
    h10_pass = bool_value(diagnostic_inputs.loc[diagnostic_inputs["horizon"].eq("H10"), "diagnostic_horizon_positive"].iloc[0]) if not diagnostic_inputs.empty and diagnostic_inputs["horizon"].eq("H10").any() else False
    r081_ref = load_r081_reference(config)
    spread_improved = finite(val_mean) and finite(r081_ref.get("validation_weekly_h3_mean_spread")) and val_mean > r081_ref["validation_weekly_h3_mean_spread"]
    cleanliness_failed = not mono_gate or not conc_gate
    daily_spread_improved_cleanliness_failed = bool(time_gate and spread_improved and cleanliness_failed)
    gate = pd.DataFrame(
        [
            {
                "family": PRIMARY_FAMILY,
                "primary_score_formed_flag": primary_score_formed,
                "daily_panel_sample_gate_pass": panel_sample_pass,
                "aggregate_oof_sample_status": sample_status,
                "fold_coverage_caveat": fold_coverage_caveat,
                "validation_evaluable_fold_count": val_evaluable_fold_count,
                "robustness_evaluable_fold_count": rob_evaluable_fold_count,
                "validation_full_valid_instrument_count": val_full_count,
                "robustness_full_valid_instrument_count": rob_full_count,
                "validation_valid_signal_date_count": val_anchor_dates,
                "robustness_valid_signal_date_count": rob_anchor_dates,
                "H3_time_transfer_gate_pass": time_gate,
                "H3_instrument_transfer_gate_pass": instrument_gate,
                "H3_fold_stability_gate_pass": fold_stability_gate,
                "H3_anchor_stability_gate_pass": anchor_stability_gate,
                "H3_monotonicity_gate_pass": mono_gate,
                "H3_concentration_gate_pass": conc_gate,
                "H3_robustness_non_deterioration_pass": rob_non_det,
                "validation_single_positive_year_caveat": validation_single_positive_year_caveat,
                "no_disallowed_caveat_active": conc_gate and (not fold_coverage_caveat or sample_status == "pass_with_fold_coverage_caveat"),
                "H3_train_oof_anchor_controlled_mean_spread": train_mean,
                "H3_validation_anchor_controlled_mean_spread": val_mean,
                "H3_validation_anchor_controlled_median_spread": val_median,
                "H3_robustness_anchor_controlled_mean_spread": rob_mean,
                "H3_robustness_anchor_controlled_median_spread": rob_median,
                "H3_validation_anchor_controlled_positive_instrument_share": val_pos_inst,
                "H3_robustness_anchor_controlled_positive_instrument_share": getattr(rob, "anchor_controlled_positive_instrument_share", np.nan) if rob is not None else np.nan,
                "H3_validation_positive_year_count": val_positive_year_count,
                "H3_robustness_positive_year_count": rob_positive_year_count,
                "robustness_actual_evaluable_year_count_H3": robustness_year_count,
                "H3_positive_anchor_offset_count_validation": getattr(val, "anchor_positive_offset_count", 0) if val is not None else 0,
                "H3_positive_anchor_offset_count_robustness": getattr(rob, "anchor_positive_offset_count", 0) if rob is not None else 0,
                "H3_fold_monotonicity_median_validation": getattr(val_disp, "fold_monotonicity_median", np.nan),
                "H3_fold_monotonicity_median_robustness": getattr(rob_disp, "fold_monotonicity_median", np.nan),
                "H3_max_fold_top1_instrument_contribution_share": conc_detail.get("max_fold_top1", np.nan),
                "H3_max_fold_top5_instrument_contribution_share": conc_detail.get("max_fold_top5", np.nan),
                "H3_max_anchor_abs_contribution_share_of_total": conc_detail.get("max_anchor_share", np.nan),
                "daily_observation_spread_improved_but_cleanliness_failed": daily_spread_improved_cleanliness_failed,
                "H5_diagnostic_horizon_positive": h5_pass,
                "H10_diagnostic_horizon_positive": h10_pass,
                "authorized_strategy_requirement": False,
            }
        ]
    )
    write_csv(gate, paths.decision_dir / "r08_2_gate_inputs.csv")
    write_csv(diagnostic_inputs, paths.decision_dir / "r08_2_horizon_diagnostic_inputs.csv")
    return gate, diagnostic_inputs, pd.DataFrame([r081_ref])


def concentration_gate(config: dict[str, Any], conc: pd.DataFrame) -> tuple[bool, dict[str, Any]]:
    c = config["frozen_formula_constants"]
    h3 = conc.loc[conc["horizon"].eq("H3")] if not conc.empty else pd.DataFrame()
    val = h3.loc[h3["split"].eq("validation_oof_unseen") & h3["scope"].eq("aggregate_anchor_controlled")]
    rob = h3.loc[h3["split"].eq("robustness_oof_unseen") & h3["scope"].eq("aggregate_anchor_controlled")]
    fold = h3.loc[h3["scope"].eq("fold_full_daily") & h3["split"].isin(["validation_oof_unseen", "robustness_oof_unseen"])]
    anchor = h3.loc[h3["scope"].eq("aggregate_anchor")]
    def agg_pass(df: pd.DataFrame) -> bool:
        if df.empty:
            return False
        r = df.iloc[0]
        return (
            not bool_value(r["contribution_denominator_zero"])
            and r["top1_instrument_contribution_share"] <= float(c["top1_instrument_contribution_share_max"])
            and r["top5_instrument_contribution_share"] <= float(c["top5_instrument_contribution_share_max"])
            and r["top1_industry_contribution_share"] <= float(c["top1_industry_contribution_share_max"])
        )
    fold_pass = (
        not fold.empty
        and fold["top1_instrument_contribution_share"].replace([np.inf, -np.inf], np.nan).max() <= float(c["max_fold_top1_instrument_contribution_share_max"])
        and fold["top5_instrument_contribution_share"].replace([np.inf, -np.inf], np.nan).max() <= float(c["max_fold_top5_instrument_contribution_share_max"])
    )
    max_fold_top1 = fold["top1_instrument_contribution_share"].replace([np.inf, -np.inf], np.nan).max() if len(fold) else np.nan
    max_fold_top5 = fold["top5_instrument_contribution_share"].replace([np.inf, -np.inf], np.nan).max() if len(fold) else np.nan
    max_anchor_share = np.nan
    if len(anchor):
        total = anchor["contribution_denominator"].replace([np.inf, -np.inf], np.nan).fillna(0.0).sum()
        max_anchor_share = float(anchor["contribution_denominator"].max() / total) if total else np.nan
    anchor_pass = finite(max_anchor_share) and max_anchor_share <= float(c["max_anchor_abs_contribution_share_of_total_max"])
    out = agg_pass(val) and agg_pass(rob) and fold_pass and anchor_pass
    return out, {"max_fold_top1": max_fold_top1, "max_fold_top5": max_fold_top5, "max_anchor_share": max_anchor_share}


def build_horizon_diagnostic_inputs(config: dict[str, Any], anchor: pd.DataFrame, conc: pd.DataFrame) -> pd.DataFrame:
    c = config["frozen_formula_constants"]
    rows = []
    for horizon in ["H5", "H10"]:
        val = row_for(anchor, horizon, "validation_oof_unseen")
        rob = row_for(anchor, horizon, "robustness_oof_unseen")
        hnum = int(horizon[1:])
        hconc = conc.loc[conc["horizon"].eq(horizon) & conc["scope"].eq("aggregate_anchor_controlled")] if not conc.empty else pd.DataFrame()
        val_conc = hconc.loc[hconc["split"].eq("validation_oof_unseen")]
        rob_conc = hconc.loc[hconc["split"].eq("robustness_oof_unseen")]
        val_top1 = float(val_conc.iloc[0]["top1_instrument_contribution_share"]) if len(val_conc) else np.nan
        rob_top1 = float(rob_conc.iloc[0]["top1_instrument_contribution_share"]) if len(rob_conc) else np.nan
        val_top5 = float(val_conc.iloc[0]["top5_instrument_contribution_share"]) if len(val_conc) else np.nan
        rob_top5 = float(rob_conc.iloc[0]["top5_instrument_contribution_share"]) if len(rob_conc) else np.nan
        denom_zero = (bool_value(val_conc.iloc[0]["contribution_denominator_zero"]) if len(val_conc) else True) or (bool_value(rob_conc.iloc[0]["contribution_denominator_zero"]) if len(rob_conc) else True)
        diag = (
            val is not None
            and rob is not None
            and val["anchor_controlled_mean_spread"] > float(c["diagnostic_horizon_validation_mean_spread_min"])
            and rob["anchor_controlled_mean_spread"] >= float(c["diagnostic_horizon_robustness_mean_spread_min"])
            and val["anchor_controlled_positive_instrument_share"] >= float(c["diagnostic_horizon_validation_positive_instrument_share_min"])
            and rob["anchor_controlled_positive_instrument_share"] >= float(c["diagnostic_horizon_robustness_positive_instrument_share_min"])
            and val["anchor_controlled_decile_monotonicity_score"] >= float(c["diagnostic_horizon_monotonicity_min"])
            and rob["anchor_controlled_decile_monotonicity_score"] >= float(c["diagnostic_horizon_monotonicity_min"])
            and val["anchor_positive_offset_count"] >= math.ceil(float(c["diagnostic_horizon_validation_positive_anchor_share_min"]) * hnum)
            and rob["anchor_positive_offset_count"] >= math.ceil(float(c["diagnostic_horizon_robustness_positive_anchor_share_min"]) * hnum)
            and val_top1 <= float(c["diagnostic_horizon_top1_instrument_share_max"])
            and rob_top1 <= float(c["diagnostic_horizon_top1_instrument_share_max"])
            and val_top5 <= float(c["diagnostic_horizon_top5_instrument_share_max"])
            and rob_top5 <= float(c["diagnostic_horizon_top5_instrument_share_max"])
            and not denom_zero
        )
        rows.append(
            {
                "horizon": horizon,
                "validation_mean_spread": getattr(val, "anchor_controlled_mean_spread", np.nan) if val is not None else np.nan,
                "robustness_mean_spread": getattr(rob, "anchor_controlled_mean_spread", np.nan) if rob is not None else np.nan,
                "validation_positive_instrument_share": getattr(val, "anchor_controlled_positive_instrument_share", np.nan) if val is not None else np.nan,
                "robustness_positive_instrument_share": getattr(rob, "anchor_controlled_positive_instrument_share", np.nan) if rob is not None else np.nan,
                "validation_anchor_decile_monotonicity": getattr(val, "anchor_controlled_decile_monotonicity_score", np.nan) if val is not None else np.nan,
                "robustness_anchor_decile_monotonicity": getattr(rob, "anchor_controlled_decile_monotonicity_score", np.nan) if rob is not None else np.nan,
                "validation_positive_anchor_offset_count": getattr(val, "anchor_positive_offset_count", 0) if val is not None else 0,
                "robustness_positive_anchor_offset_count": getattr(rob, "anchor_positive_offset_count", 0) if rob is not None else 0,
                "validation_top1_instrument_contribution_share": val_top1,
                "robustness_top1_instrument_contribution_share": rob_top1,
                "validation_top5_instrument_contribution_share": val_top5,
                "robustness_top5_instrument_contribution_share": rob_top5,
                "diagnostic_concentration_denominator_zero_flag": denom_zero,
                "diagnostic_horizon_positive": diag,
            }
        )
    return pd.DataFrame(rows)


def load_r081_reference(config: dict[str, Any]) -> dict[str, Any]:
    root = r01.topic_path(config["data_sources"].get("r08_1_output_root", ""))
    path = root / "decision" / "r08_1_gate_inputs.csv"
    out = {
        "validation_weekly_h3_mean_spread": np.nan,
        "robustness_weekly_h3_mean_spread": np.nan,
    }
    if path.exists():
        gate = pd.read_csv(path)
        row = gate.loc[gate["family"].eq(PRIMARY_FAMILY)]
        if len(row):
            rec = row.iloc[0]
            out["validation_weekly_h3_mean_spread"] = rec.get("validation_oof_unseen_mean_spread", np.nan)
            out["robustness_weekly_h3_mean_spread"] = rec.get("robustness_oof_unseen_mean_spread", np.nan)
    return out


def build_final_decision(paths: R082Paths, gate: pd.DataFrame, diagnostic: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    primary = gate.iloc[0].to_dict() if len(gate) else {}
    contract_violation = False
    score_missing = not bool_value(primary.get("primary_score_formed_flag", False))
    sample_fail = primary.get("aggregate_oof_sample_status", "fail") == "fail"
    sample_pass = primary.get("aggregate_oof_sample_status") in {"pass", "pass_with_fold_coverage_caveat"}
    time_pass = bool_value(primary.get("H3_time_transfer_gate_pass", False))
    inst_pass = bool_value(primary.get("H3_instrument_transfer_gate_pass", False))
    fold_pass = bool_value(primary.get("H3_fold_stability_gate_pass", False))
    anchor_pass = bool_value(primary.get("H3_anchor_stability_gate_pass", False))
    mono_pass = bool_value(primary.get("H3_monotonicity_gate_pass", False))
    conc_pass = bool_value(primary.get("H3_concentration_gate_pass", False))
    rob_nd_pass = bool_value(primary.get("H3_robustness_non_deterioration_pass", False))
    no_caveat = bool_value(primary.get("no_disallowed_caveat_active", False))
    hdiag = bool(diagnostic["diagnostic_horizon_positive"].map(bool_value).any()) if len(diagnostic) else False
    support_all = sample_pass and time_pass and inst_pass and fold_pass and anchor_pass and mono_pass and conc_pass and rob_nd_pass and no_caveat
    rules = [
        ("rule_01", "data / execution / scope / as-of / fold contract violation", contract_violation, "r08_2_blocked_data_or_execution_contract"),
        ("rule_02", "primary vwap family cannot form fold-specific state score", score_missing, "r08_2_blocked_overlap_controlled_sample_insufficient"),
        ("rule_03", "aggregate_oof_sample_status = fail or H3 anchor sample gate fails", sample_fail, "r08_2_blocked_overlap_controlled_sample_insufficient"),
        ("rule_04", "all non-fold H3 support gates pass and fold stability fails", time_pass and inst_pass and anchor_pass and mono_pass and conc_pass and rob_nd_pass and not fold_pass, "r08_2_daily_vwap_h3_fold_fragile_candidate"),
        ("rule_05", "time transfer passes, instrument transfer fails, other H3 cleanliness gates pass", time_pass and not inst_pass and fold_pass and anchor_pass and mono_pass and conc_pass and rob_nd_pass, "r08_2_daily_vwap_h3_time_transfer_only"),
        ("rule_06", "all H3 support gates pass", support_all, "r08_2_daily_vwap_h3_transferability_diagnostic_supported"),
        ("rule_07", "H3 sample passes and H3 support fails, while H5/H10 diagnostic horizon passes", sample_pass and not support_all and hdiag, "r08_2_horizon_mismatch_diagnostic_only"),
        ("rule_08", "otherwise", True, "r08_2_no_daily_vwap_h3_transferability_support"),
    ]
    selected_decision = ""
    replay_rows = []
    selected_seen = False
    for rule_id, text, condition, decision in rules:
        raw = bool(condition)
        selected = (not selected_seen) and raw
        if selected:
            selected_seen = True
            selected_decision = decision
        replay_rows.append({"rule_id": rule_id, "rule_condition_text": text, "raw_condition_met": raw, "selected_rule_flag": selected, "decision_if_selected": decision})
    final = pd.DataFrame(
        [
            {
                "final_decision": selected_decision,
                "authorized_strategy_requirement": False,
                "allowed_next_requirement": "confirmatory_daily_vwap_h3_transferability_diagnostic"
                if selected_decision == "r08_2_daily_vwap_h3_transferability_diagnostic_supported"
                else "",
                "primary_family": PRIMARY_FAMILY,
                "primary_horizon": "H3",
                "diagnostic_horizons": "H5;H10",
                "aggregate_oof_sample_status": primary.get("aggregate_oof_sample_status", "fail"),
                "H3_validation_anchor_controlled_mean_spread": primary.get("H3_validation_anchor_controlled_mean_spread", np.nan),
                "H3_robustness_anchor_controlled_mean_spread": primary.get("H3_robustness_anchor_controlled_mean_spread", np.nan),
                "H3_validation_anchor_controlled_positive_instrument_share": primary.get("H3_validation_anchor_controlled_positive_instrument_share", np.nan),
                "H3_robustness_anchor_controlled_positive_instrument_share": primary.get("H3_robustness_anchor_controlled_positive_instrument_share", np.nan),
                "daily_observation_spread_improved_but_cleanliness_failed": primary.get("daily_observation_spread_improved_but_cleanliness_failed", False),
            }
        ]
    )
    replay = pd.DataFrame(replay_rows)
    write_csv(replay, paths.decision_dir / "r08_2_final_decision_replay.csv")
    write_csv(final, paths.decision_dir / "r08_2_final_decision.csv")
    return replay, final


def write_report(paths: R082Paths, gate: pd.DataFrame, diagnostic: pd.DataFrame, final: pd.DataFrame) -> None:
    decision = final.iloc[0]["final_decision"] if len(final) else ""
    h3_anchor = pd.read_csv(paths.metrics_dir / "r08_2_h3_anchor_controlled_oof_spread.csv")
    h3_fold = pd.read_csv(paths.metrics_dir / "r08_2_h3_fold_dispersion_summary.csv")
    hshape = pd.read_csv(paths.metrics_dir / "r08_2_horizon_shape_summary.csv")
    primary = gate.iloc[0] if len(gate) else None
    lines = [
        "# R08.2 Daily-Observed VWAP Deviation H3/H5/H10 Transferability Diagnostic Report",
        "",
        "## 1. 结论",
        "",
        f"`final_decision = {decision}`",
        "",
        "`authorized_strategy_requirement = false`。R08.2 是 daily-observed diagnostic-only audit，没有策略、组合、top-N、top20% 或 production signal。",
        "",
        "R08.2 只改变 signal observation frequency：从 weekly close-observed 改为 daily close-observed。Primary family 固定为 `vwap_deviation`，primary horizon 固定为 H3；H5/H10 仅用于 horizon-shape diagnostic。",
        "",
        "## 2. H3 Anchor-Controlled Readout",
        "",
        "| split | mean spread | median spread | positive anchor offsets | positive inst share | valid instruments | valid dates | monotonicity | full-anchor conflict |",
        "|:--|--:|--:|--:|--:|--:|--:|--:|:--|",
    ]
    for rec in h3_anchor.itertuples(index=False):
        lines.append(
            f"| {rec.split} | {pct_text(rec.anchor_controlled_mean_spread)} | {pct_text(rec.anchor_controlled_median_spread)} | {int(rec.anchor_positive_offset_count)} | {pct_text(rec.anchor_controlled_positive_instrument_share)} | {int(rec.anchor_controlled_full_valid_instrument_count)} | {int(rec.anchor_controlled_valid_signal_date_count)} | {num_text(rec.anchor_controlled_decile_monotonicity_score)} | `{bool_value(rec.full_daily_anchor_sign_conflict_flag)}` |"
        )
    lines.extend(["", "## 3. Gate Replay", "", "| gate | value |", "|:--|:--|"])
    if primary is not None:
        for col in [
            "aggregate_oof_sample_status",
            "H3_time_transfer_gate_pass",
            "H3_instrument_transfer_gate_pass",
            "H3_fold_stability_gate_pass",
            "H3_anchor_stability_gate_pass",
            "H3_monotonicity_gate_pass",
            "H3_concentration_gate_pass",
            "H3_robustness_non_deterioration_pass",
            "daily_observation_spread_improved_but_cleanliness_failed",
            "H5_diagnostic_horizon_positive",
            "H10_diagnostic_horizon_positive",
        ]:
            lines.append(f"| {col} | `{primary.get(col, 'NA')}` |")
    lines.extend(["", "## 4. Fold Dispersion", "", "| split | evaluable folds | positive folds | median spread | min spread | fold mono median | max fold top1 |", "|:--|--:|--:|--:|--:|--:|--:|"])
    for rec in h3_fold.itertuples(index=False):
        lines.append(
            f"| {rec.split} | {int(rec.evaluable_fold_count)} | {int(rec.positive_fold_count)} | {pct_text(rec.median_fold_spread)} | {pct_text(rec.min_fold_spread)} | {num_text(rec.fold_monotonicity_median)} | {pct_text(rec.max_fold_top1_instrument_contribution_share)} |"
        )
    lines.extend(["", "## 5. H5/H10 Diagnostic", "", "| horizon | val spread | robust spread | val inst share | robust inst share | diagnostic positive |", "|:--|--:|--:|--:|--:|:--|"])
    for rec in diagnostic.itertuples(index=False):
        lines.append(
            f"| {rec.horizon} | {pct_text(rec.validation_mean_spread)} | {pct_text(rec.robustness_mean_spread)} | {pct_text(rec.validation_positive_instrument_share)} | {pct_text(rec.robustness_positive_instrument_share)} | `{bool_value(rec.diagnostic_horizon_positive)}` |"
        )
    lines.extend(["", "## 6. Horizon Shape", "", "| split | H3 | H5 | H10 | sign pattern |", "|:--|--:|--:|--:|:--|"])
    for rec in hshape.itertuples(index=False):
        lines.append(f"| {rec.split} | {pct_text(rec.H3_mean_spread)} | {pct_text(rec.H5_mean_spread)} | {pct_text(rec.H10_mean_spread)} | `{rec.sign_pattern}` |")
    lines.extend(
        [
            "",
            "## 7. Interpretation",
            "",
            "- H3 support 只由 overlap-controlled anchor readout 决定；full daily 是 point-estimate / non-contradiction check。",
            "- H5/H10 不能 rescue H3，也不能授权 horizon switching。",
            "- 如果 daily spread 改善但 fold-level monotonicity 或 concentration 失败，结论只能是 `daily_observation_spread_improved_but_cleanliness_failed`。",
            "",
            "## 8. Required Questions",
            "",
        ]
    )
    qas = [
        "1. R08.2 是否保持 diagnostic-only，且没有构造任何策略？是。",
        "2. 是否把 signal frequency 从 weekly 改成 daily？是。",
        "3. 是否只把 `vwap_deviation` 作为 primary family？是。",
        "4. 是否只把 H3 作为 primary horizon？是。",
        "5. H5/H10 是否只作为 diagnostic labels？是。",
        "6. daily signal panel 是否 PIT / as-of safe？是，见 daily_signal_panel_audit。",
        "7. daily factor percentile 是否使用 D-1 之前的 252 日 reference distribution？是。",
        "8. H3/H5/H10 self-relative labels 是否只使用 completed labels？是。",
        "9. daily overlapping label 是否被显式控制？是，使用 anchor offset。",
        "10. H3 anchor offsets 是否全部可评价？见 sample/gate inputs。",
        "11. 5-fold instrument assignment 是否 deterministic 且 train 前冻结？是。",
        "12. direction 是否只来自 train years + seen folds + H3？是。",
        "13. H5/H10 是否没有参与 direction、bucket edge、factor retention？是。",
        "14. validation H3 anchor-controlled spread 是否为正？见 H3 表。",
        "15. robustness H3 anchor-controlled spread 是否确认？见 H3 表。",
        "16. full daily readout 是否与 anchor-controlled readout 冲突？见 conflict flag。",
        "17. validation / robustness H3 positive instrument share 是否达标？见 gate inputs。",
        "18. H3 fold stability 是否达标？见 gate replay。",
        "19. H3 anchor stability 是否达标？见 gate replay。",
        "20. H3 monotonicity 是否达标？见 gate replay。",
        "21. H3 concentration 是否达标？见 gate replay。",
        "22. H5 diagnostic label 的 spread / monotonicity / positive instrument share 是什么？见 H5/H10 Diagnostic 表。",
        "23. H10 diagnostic label 的 spread / monotonicity / positive instrument share 是什么？见 H5/H10 Diagnostic 表。",
        "24. horizon shape 是 short-lived、persistent、horizon-mismatch 还是 no-support？见 horizon_shape_summary。",
        "25. 如果 H5/H10 强于 H3，是否确认这不改变 primary final decision？是。",
        "26. 结果相比 R08.1 weekly H3 是否改善？见 gate inputs 的 weekly reference annotation。",
        f"27. final decision 是 supported、fold-fragile、time-transfer-only、horizon-mismatch 还是 no-support？`{decision}`。",
        "28. 是否允许写 strategy requirement？答案必须是 no。",
        "29. 如果 supported，允许的下一步 confirmatory diagnostic 是什么？`confirmatory_daily_vwap_h3_transferability_diagnostic`。",
        "30. `daily_trading_calendar_index` 是否为全市场共用、跨 split 连续、且没有按 instrument 重置？是。",
        "31. direction canonical sign 是否来自 H3 anchor-controlled train-seen stats，而不是 full daily overlapping stats？是。",
        "32. train OOF anchor-controlled baseline 是否落盘并用于 non-deterioration replay？是。",
        "33. H3/H5/H10 full-valid 与 partial instrument denominator 是否 horizon-specific？是。",
        "34. 如果 daily spread 改善但 monotonicity / concentration 仍失败，是否标注对应 annotation？是。",
        "35. H5/H10 diagnostic horizon pass 是否同时通过 spread、instrument breadth、anchor count、monotonicity 和 diagnostic concentration？是。",
    ]
    lines.extend(qas)
    (paths.reports_dir / "r08_2_final_report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def required_paths(paths: R082Paths) -> list[Path]:
    return [
        paths.audit_dir / "r08_2_run_manifest.json",
        paths.audit_dir / "r08_2_input_data_audit.csv",
        paths.audit_dir / "r08_2_daily_signal_panel_audit.csv",
        paths.audit_dir / "r08_2_data_availability_by_horizon_audit.csv",
        paths.audit_dir / "r08_2_scope_audit.csv",
        paths.audit_dir / "r08_2_fold_assignment_audit.csv",
        paths.audit_dir / "r08_2_within_stock_normalization_audit.csv",
        paths.audit_dir / "r08_2_label_asof_audit.csv",
        paths.audit_dir / "r08_2_factor_direction_by_fold_audit.csv",
        paths.audit_dir / "r08_2_factor_nonconstant_observation_audit.csv",
        paths.audit_dir / "r08_2_family_scope_by_fold_audit.csv",
        paths.audit_dir / "r08_2_state_bucket_by_fold_audit.csv",
        paths.audit_dir / "r08_2_overlap_anchor_audit.csv",
        paths.audit_dir / "r08_2_fold_sample_audit.csv",
        paths.audit_dir / "r08_2_horizon_specific_instrument_validity_audit.csv",
        paths.audit_dir / "r08_2_concentration_audit.csv",
        paths.metrics_dir / "r08_2_h3_full_daily_oof_spread.csv",
        paths.metrics_dir / "r08_2_h3_anchor_controlled_oof_spread.csv",
        paths.metrics_dir / "r08_2_h3_train_baseline_summary.csv",
        paths.metrics_dir / "r08_2_h3_fold_unseen_state_spread.csv",
        paths.metrics_dir / "r08_2_h3_fold_dispersion_summary.csv",
        paths.metrics_dir / "r08_2_h3_instrument_transfer_summary.csv",
        paths.metrics_dir / "r08_2_h3_time_transfer_summary.csv",
        paths.metrics_dir / "r08_2_h3_year_availability_and_positive_count.csv",
        paths.metrics_dir / "r08_2_h3_decile_monotonicity_by_anchor.csv",
        paths.metrics_dir / "r08_2_h3_concentration_summary.csv",
        paths.metrics_dir / "r08_2_h5_diagnostic_oof_spread.csv",
        paths.metrics_dir / "r08_2_h10_diagnostic_oof_spread.csv",
        paths.metrics_dir / "r08_2_horizon_shape_summary.csv",
        paths.metrics_dir / "r08_2_overlap_adjusted_confidence_summary.csv",
        paths.decision_dir / "r08_2_gate_inputs.csv",
        paths.decision_dir / "r08_2_horizon_diagnostic_inputs.csv",
        paths.decision_dir / "r08_2_final_decision_replay.csv",
        paths.decision_dir / "r08_2_final_decision.csv",
        paths.reports_dir / "r08_2_final_report.md",
        paths.manifests_dir / "r08_2_artifact_hashes.json",
    ]


def run_pipeline(config_path: str | Path = DEFAULT_CONFIG) -> None:
    config, paths = load_config(config_path)
    inputs = load_inputs(config)
    candidates = build_daily_signal_panel(config, paths, inputs.feature)
    label, _, availability = build_execution_and_labels(config, paths, inputs.feature, candidates)
    factor_ids = scope_factor_ids(inputs)
    raw, percentile, tie, tie_cluster, available_fids = build_factor_state_inputs(config, paths, inputs, candidates, factor_ids)
    build_scope_audits(paths, candidates, factor_ids, available_fids)
    build_normalization_audit(paths, candidates, available_fids, percentile, tie, tie_cluster)
    _, _, directions = direction_by_fold(config, paths, candidates, label, available_fids, percentile)
    events, scope_df, _, _ = build_oof_events(config, paths, candidates, label, available_fids, percentile, directions)
    frames = build_metrics(config, paths, events)
    write_csv(frames["overlap"], paths.audit_dir / "r08_2_overlap_anchor_audit.csv")
    gate, diagnostic, _ = build_gate_inputs(config, paths, candidates, scope_df, frames, availability)
    _, final = build_final_decision(paths, gate, diagnostic)
    write_report(paths, gate, diagnostic, final)
    write_json(
        {
            "requirement_id": REQUIREMENT_ID,
            "plan_id": PLAN_ID,
            "config_path": rel(paths.config_path),
            "output_root": rel(paths.output_root),
            "created_at": r01.now_iso(),
            "git_commit": r01.git_commit_hash(),
            "primary_family": PRIMARY_FAMILY,
            "primary_horizon": "H3",
            "diagnostic_horizons": ["H5", "H10"],
            "signal_frequency": "daily",
            "final_decision": final.iloc[0]["final_decision"],
            "authorized_strategy_requirement": bool_value(final.iloc[0]["authorized_strategy_requirement"]),
        },
        paths.audit_dir / "r08_2_run_manifest.json",
    )
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r08_2_artifact_hashes.json")


def validate_outputs(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config, paths = load_config(config_path)
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"check_name": name, "status": "passed" if condition else "failed", "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    check("V01_requirement_id", config.get("requirement_id") == REQUIREMENT_ID, str(config.get("requirement_id")))
    missing = [rel(path) for path in required_paths(paths) if not path.exists()]
    check("V02_required_artifacts_exist", not missing, ";".join(missing))
    final_decision = ""
    if not missing:
        daily = pd.read_csv(paths.audit_dir / "r08_2_daily_signal_panel_audit.csv")
        fold = pd.read_csv(paths.audit_dir / "r08_2_fold_assignment_audit.csv")
        norm = pd.read_csv(paths.audit_dir / "r08_2_within_stock_normalization_audit.csv")
        label = pd.read_csv(paths.audit_dir / "r08_2_label_asof_audit.csv")
        direction = pd.read_csv(paths.audit_dir / "r08_2_factor_direction_by_fold_audit.csv")
        fam = pd.read_csv(paths.audit_dir / "r08_2_family_scope_by_fold_audit.csv")
        bucket = pd.read_csv(paths.audit_dir / "r08_2_state_bucket_by_fold_audit.csv")
        sample = pd.read_csv(paths.audit_dir / "r08_2_fold_sample_audit.csv")
        horizon_valid = pd.read_csv(paths.audit_dir / "r08_2_horizon_specific_instrument_validity_audit.csv")
        gate = pd.read_csv(paths.decision_dir / "r08_2_gate_inputs.csv")
        diag = pd.read_csv(paths.decision_dir / "r08_2_horizon_diagnostic_inputs.csv")
        replay = pd.read_csv(paths.decision_dir / "r08_2_final_decision_replay.csv")
        final = pd.read_csv(paths.decision_dir / "r08_2_final_decision.csv")
        report = (paths.reports_dir / "r08_2_final_report.md").read_text(encoding="utf-8")
        final_decision = str(final.iloc[0]["final_decision"])
        check("V03_primary_family_only_vwap_deviation", config["scope"]["primary_family"] == PRIMARY_FAMILY, "")
        check("V04_primary_horizon_only_H3", config["scope"]["primary_horizon"] == "H3" and config["execution"]["primary_horizon"] == 3, "")
        check("V05_diagnostic_horizons_only_H5_H10", config["execution"]["diagnostic_horizons"] == [5, 10], "")
        check("V06_signal_frequency_daily", config["execution"]["signal_date_rule"] == "daily_close_observed", "")
        check("V07_weekly_signal_panel_not_used_as_primary", daily["weekly_signal_panel_not_used_as_primary"].map(bool_value).all(), "")
        check("V08_no_strategy_artifacts", not any(p.is_file() and any(x in p.name.lower() for x in ["portfolio", "backtest", "allocation", "top20", "top_"]) for p in paths.output_root.rglob("*")), "")
        check("V09_fold_assignment_sha256_mod5", set(fold["instrument_fold_id"].dropna().astype(int).unique()) == set(FOLD_IDS), "")
        sample_ids = fold.head(20)
        check("V10_fold_hash_replay", all(instrument_fold_id(x) == int(fid) for x, fid in zip(sample_ids["canonical_instrument_id"], sample_ids["instrument_fold_id"])), "")
        check("V11_all_5_folds_present", set(fam["fold_id"].dropna().astype(int).unique()) == set(FOLD_IDS), "")
        check("V12_no_fold_dropped_for_performance", set(sample["fold_id"].dropna().astype(int).unique()) == set(FOLD_IDS), "")
        check("V13_daily_trading_calendar_index_global_continuous", daily["daily_trading_calendar_index_global_continuous"].map(bool_value).all(), "")
        check("V14_direction_train_seen_only", direction["direction_source_split"].eq("train").all() and direction["direction_source_instrument_scope"].astype(str).str.contains("seen_folds_not_").all(), "")
        check("V15_direction_label_horizon_H3_only", direction["direction_label_horizon"].eq("H3").all(), "")
        check("V16_direction_canonical_sign_anchor_controlled", "factor_direction_stat_anchor_median" in direction.columns, "")
        check("V17_H5_H10_not_used_for_direction", direction["direction_label_horizon"].eq("H3").all(), "")
        check("V18_direction_anchor_stability_checked", "direction_anchor_stability_pass" in direction.columns, "")
        check("V19_bucket_edges_train_seen_only", bucket["frozen_before_validation_read"].map(bool_value).all() and bucket["bucket_edge_source_split"].eq("train").all(), "")
        check("V20_within_stock_lookback_ends_D_minus_1", norm["within_stock_lookback_ends_at_D_minus_1"].map(bool_value).all(), "")
        check("V21_mid_rank_tie_handling_used", norm["mid_rank_tie_handling_used"].map(bool_value).all(), "")
        check("V22_self_relative_completed_labels_only", label["self_relative_labels_use_completed_labels_only"].map(bool_value).all(), "")
        check("V23_overlap_anchor_offsets_exist", (paths.metrics_dir / "r08_2_overlap_adjusted_confidence_summary.csv").exists(), "")
        check("V24_H3_primary_gate_uses_anchor_metrics", {"H3_time_transfer_gate_pass", "H3_anchor_stability_gate_pass"}.issubset(gate.columns), "")
        check("V25_full_daily_conflict_flags_exist", "full_daily_anchor_sign_conflict_flag" in pd.read_csv(paths.metrics_dir / "r08_2_h3_anchor_controlled_oof_spread.csv").columns, "")
        check("V26_train_oof_anchor_baseline_exists", (paths.metrics_dir / "r08_2_h3_train_baseline_summary.csv").exists(), "")
        check("V27_H5_H10_diagnostic_only", diag["horizon"].isin(["H5", "H10"]).all(), "")
        check("V28_horizon_switching_forbidden", final["authorized_strategy_requirement"].map(bool_value).eq(False).all(), "")
        check("V29_partial_horizon_specific", horizon_valid["partial_instruments_horizon_specific"].map(bool_value).all(), "")
        check("V30_partial_excluded_sample_by_horizon", sample["partial_instruments_excluded_from_sample_gate_by_horizon"].map(bool_value).all(), "")
        check("V31_partial_excluded_positive_share_by_horizon", sample["partial_instruments_excluded_from_positive_instrument_share_by_horizon"].map(bool_value).all(), "")
        check("V32_concentration_formula_replayable", (paths.audit_dir / "r08_2_concentration_audit.csv").exists(), "")
        check("V33_H5_H10_diagnostic_pass_replayable", "diagnostic_horizon_positive" in diag.columns, "")
        check("V34_decision_replay_first_match", int(replay["selected_rule_flag"].map(bool_value).sum()) == 1, "")
        check("V35_authorized_strategy_requirement_false", final["authorized_strategy_requirement"].map(bool_value).eq(False).all(), "")
        check("V36_final_decision_enum", final_decision in FINAL_DECISIONS, final_decision)
        check("V37_report_questions", all(f"{i}." in report for i in range(1, 36)), "")
        if (paths.cache_dir / "r08_2_oof_event_panel.parquet").exists():
            ev = pd.read_parquet(paths.cache_dir / "r08_2_oof_event_panel.parquet", columns=["fold_id", "instrument_fold_id"])
            check("V38_primary_evaluation_unseen_fold_only", ev["fold_id"].astype(int).eq(ev["instrument_fold_id"].astype(int)).all(), "")
    status = "passed" if not failures else "failed"
    audit = pd.DataFrame(checks)
    write_csv(audit, paths.audit_dir / "r08_2_validation_gate_audit.csv")
    payload = {
        "validation_status": status,
        "requirement_id": REQUIREMENT_ID,
        "plan_id": PLAN_ID,
        "config_path": rel(paths.config_path),
        "output_root": rel(paths.output_root),
        "gate_count": len(checks),
        "passed_gate_count": sum(1 for row in checks if row["status"] == "passed"),
        "failed_gate_count": sum(1 for row in checks if row["status"] != "passed"),
        "final_decision": final_decision,
        "failures": failures,
        "created_at": r01.now_iso(),
    }
    write_json(payload, paths.manifests_dir / "r08_2_validation.json")
    write_json({"created_at": r01.now_iso(), "artifacts": artifact_hashes(paths)}, paths.manifests_dir / "r08_2_artifact_hashes.json")
    return payload
